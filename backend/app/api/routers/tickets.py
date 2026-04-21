from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.routers.auth import get_current_admin, get_current_user
from app.core.database import get_db
from app.models import HumanServiceSession, User
from app.schemas import (
    HumanServiceCreate,
    HumanServiceReply,
    HumanServiceSessionDetail,
    HumanServiceSessionItem,
    HumanServiceUserStatus
)
from app.services.human_service import human_service


router = APIRouter(prefix="/tickets", tags=["人工客服"])


def serialize_ticket(ticket: HumanServiceSession, db: Session) -> dict:
    user = db.query(User).filter(User.id == ticket.user_id).first()
    admin = None
    if ticket.assigned_admin_id:
        admin = db.query(User).filter(User.id == ticket.assigned_admin_id).first()

    return {
        "id": ticket.id,
        "session_id": ticket.session_id,
        "user_id": ticket.user_id,
        "username": user.username if user else "未知用户",
        "status": ticket.status,
        "transfer_reason": ticket.transfer_reason,
        "last_user_message": ticket.last_user_message,
        "assigned_admin_id": ticket.assigned_admin_id,
        "assigned_admin_name": admin.username if admin else None,
        "last_message_at": ticket.last_message_at,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at
    }


@router.post("", response_model=HumanServiceSessionItem)
def create_ticket(
    payload: HumanServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if payload.session_id:
        active_ticket = human_service.get_user_ticket(db, payload.session_id, current_user.id)
        if active_ticket and active_ticket.status in ["pending", "handling"]:
            return serialize_ticket(active_ticket, db)

    try:
        human_service.enqueue_handoff(
            db=db,
            session_id=payload.session_id,
            user_id=current_user.id,
            user_message=payload.content,
            transfer_reason=payload.transfer_reason
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建人工会话失败: {exc}")

    ticket = human_service.get_user_ticket(db, payload.session_id, current_user.id)
    return serialize_ticket(ticket, db)


@router.get("", response_model=List[HumanServiceSessionItem])
def get_tickets(
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    tickets = human_service.list_tickets(db, status=status, keyword=keyword)
    return [serialize_ticket(ticket, db) for ticket in tickets]


@router.get("/pending-count")
def get_pending_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    count = db.query(HumanServiceSession).filter(
        HumanServiceSession.status == "pending"
    ).count()
    return {"count": count}


@router.get("/user/check/{session_id}", response_model=HumanServiceUserStatus)
def check_user_ticket(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = human_service.get_user_ticket(db, session_id, current_user.id)
    if not ticket:
        return {
            "exists": False,
            "ticket_id": None,
            "session_id": session_id,
            "status": None,
            "assigned_admin_name": None
        }

    admin_name = None
    if ticket.assigned_admin_id:
        admin = db.query(User).filter(User.id == ticket.assigned_admin_id).first()
        admin_name = admin.username if admin else None

    return {
        "exists": True,
        "ticket_id": ticket.id,
        "session_id": ticket.session_id,
        "status": ticket.status,
        "assigned_admin_name": admin_name
    }


@router.get("/by-session/{session_id}", response_model=HumanServiceSessionItem)
def get_ticket_by_session_lookup(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    ticket = human_service.get_ticket_by_session(db, session_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="人工会话不存在")

    return serialize_ticket(ticket, db)


@router.post("/user/close/{session_id}", response_model=HumanServiceSessionItem)
def close_user_ticket(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = human_service.get_user_ticket(db, session_id, current_user.id)
    if not ticket:
        raise HTTPException(status_code=404, detail="人工会话不存在")

    human_service.close(db, ticket, ticket.assigned_admin_id)
    return serialize_ticket(ticket, db)


@router.get("/{ticket_id}", response_model=HumanServiceSessionDetail)
def get_ticket_detail(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    ticket = human_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="人工会话不存在")

    detail = serialize_ticket(ticket, db)
    detail["messages"] = human_service.get_admin_history(
        db=db,
        session_id=ticket.session_id
    )
    return detail


@router.get("/by-session-legacy/{session_id}", response_model=HumanServiceSessionItem)
def get_ticket_by_session_legacy(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    ticket = human_service.get_ticket_by_session(db, session_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="人工会话不存在")

    return serialize_ticket(ticket, db)


@router.post("/{ticket_id}/reply", response_model=HumanServiceSessionItem)
def reply_ticket(
    ticket_id: int,
    payload: HumanServiceReply,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    ticket = human_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="人工会话不存在")

    try:
        human_service.reply(db, ticket, current_user.id, payload.content)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"发送人工回复失败: {exc}")

    return serialize_ticket(ticket, db)


@router.post("/{ticket_id}/close", response_model=HumanServiceSessionItem)
def close_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    ticket = human_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="人工会话不存在")

    human_service.close(db, ticket, current_user.id)
    return serialize_ticket(ticket, db)


@router.post("/{ticket_id}/handling", response_model=HumanServiceSessionItem)
def set_ticket_handling(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    ticket = human_service.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="人工会话不存在")

    human_service.set_handling(db, ticket, current_user.id)
    return serialize_ticket(ticket, db)
