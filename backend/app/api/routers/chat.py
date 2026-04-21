import json
import asyncio
import logging
from typing import List

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_llm_service
from app.api.routers.auth import get_current_user, get_current_admin
from app.core.database import get_db
from app.models import User, HumanServiceSession, ChatHistory
from app.schemas import ChatHistoryResponse, ChatMessage, RAGResponse, SessionListItem
from app.services.human_service import human_service
from app.services.llm_service import LLMService
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/chat", tags=["对话"])


@router.post("", response_model=RAGResponse)
async def chat(
    message: ChatMessage,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm_service: LLMService = Depends(get_llm_service)
):
    active_ticket = None
    if message.session_id:
        active_ticket = human_service.get_active_session(db, message.session_id, current_user.id)

    if active_ticket:
        answer = human_service.append_user_follow_up(
            db=db,
            session_id=message.session_id,
            user_id=current_user.id,
            user_message=message.content
        )
        session_id = message.session_id
    else:
        answer, session_id, sources = await rag_service.generate_answer(
            query=message.content,
            db=db,
            llm_service=llm_service,
            user_id=current_user.id,
            session_id=message.session_id
        )

    return RAGResponse(answer=answer, session_id=session_id, sources=sources)


@router.post("/stream")
async def chat_stream(
    message: ChatMessage,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    llm_service: LLMService = Depends(get_llm_service)
):
    active_ticket = None
    if message.session_id:
        active_ticket = human_service.get_active_session(db, message.session_id, current_user.id)

    async def event_generator():
        try:
            yield f"data: {json.dumps({'type': 'session', 'session_id': message.session_id or ''}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)
            
            if active_ticket:
                notice = human_service.append_user_follow_up(
                    db=db,
                    session_id=message.session_id,
                    user_id=current_user.id,
                    user_message=message.content
                )
                yield f"data: {json.dumps({'type': 'handoff', 'content': notice, 'session_id': message.session_id}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'session_id': message.session_id}, ensure_ascii=False)}\n\n"
                return

            async for chunk in rag_service.generate_answer_stream(
                query=message.content,
                db=db,
                llm_service=llm_service,
                user_id=current_user.id,
                session_id=message.session_id
            ):
                yield chunk
                await asyncio.sleep(0)
        except (GeneratorExit, asyncio.CancelledError):
            logger.info(f"SSE connection closed for session {message.session_id}")
        except Exception as e:
            logger.error(f"SSE error for session {message.session_id}: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Pragma": "no-cache",
            "Expires": "0",
            "Transfer-Encoding": "chunked"
        }
    )


@router.get("/sessions")
def get_user_sessions(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "admin":
        return get_admin_sessions(db, limit)
    return rag_service.get_user_sessions(
        db=db,
        user_id=current_user.id,
        limit=limit
    )


def get_admin_sessions(db: Session, limit: int = 20) -> List[dict]:
    tickets = db.query(HumanServiceSession).filter(
        HumanServiceSession.status.in_(["pending", "handling", "closed"])
    ).order_by(HumanServiceSession.last_message_at.desc()).limit(limit).all()
    
    if not tickets:
        return []
    
    session_ids = [t.session_id for t in tickets]
    user_ids = list(set(t.user_id for t in tickets))
    
    chat_messages = db.query(ChatHistory).filter(
        ChatHistory.session_id.in_(session_ids),
        ChatHistory.role.in_(["user", "assistant"])
    ).order_by(ChatHistory.created_at.asc()).all()
    
    session_messages = {}
    for msg in chat_messages:
        if msg.session_id not in session_messages:
            session_messages[msg.session_id] = {"user": [], "assistant": []}
        if msg.role == "user":
            session_messages[msg.session_id]["user"].append(msg)
        else:
            session_messages[msg.session_id]["assistant"].append(msg)
    
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    user_map = {u.id: u for u in users}
    
    user_sessions = {}
    
    for ticket in tickets:
        user_id = ticket.user_id
        session_id = ticket.session_id
        
        if session_id not in session_messages or not session_messages[session_id]["user"]:
            continue
        
        first_msg = session_messages[session_id]["user"][0]
        assistant_msgs = session_messages[session_id]["assistant"]
        last_msg = assistant_msgs[-1] if assistant_msgs else None
        
        if user_id not in user_sessions:
            user = user_map.get(user_id)
            user_sessions[user_id] = {
                "user_id": user_id,
                "username": user.username if user else "未知用户",
                "tickets": [],
                "total_tickets": 0,
                "latest_message_time": ticket.last_message_at
            }
        
        user_sessions[user_id]["tickets"].append({
            "ticket_id": ticket.id,
            "session_id": session_id,
            "status": ticket.status,
            "first_message": first_msg.content[:50] + "..." if len(first_msg.content) > 50 else first_msg.content,
            "last_message": last_msg.content[:50] + "..." if last_msg and len(last_msg.content) > 50 else (last_msg.content if last_msg else ""),
            "created_at": ticket.created_at,
            "updated_at": ticket.last_message_at,
            "transfer_reason": ticket.transfer_reason
        })
        user_sessions[user_id]["total_tickets"] += 1
        user_sessions[user_id]["latest_message_time"] = max(user_sessions[user_id]["latest_message_time"], ticket.last_message_at)
    
    result = sorted(user_sessions.values(), key=lambda x: x["latest_message_time"], reverse=True)
    
    return result


@router.get("/history", response_model=List[ChatHistoryResponse])
def get_chat_history(
    session_id: str = Query(..., description="会话ID"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return rag_service.get_chat_history(
        db=db,
        session_id=session_id,
        user_id=current_user.id,
        limit=limit
    )


@router.delete("/session")
def clear_session(
    session_id: str = Query(..., description="会话ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rag_service.clear_session(
        db=db,
        session_id=session_id,
        user_id=current_user.id
    )
    return {"message": "会话已清除"}
