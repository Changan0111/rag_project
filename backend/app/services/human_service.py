from datetime import datetime
from typing import Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import ChatHistory, HumanServiceSession, User


class HumanService:
    HANDOFF_NOTICE = "当前问题已转人工客服处理，您可以继续发送补充信息，我们会尽快回复。"
    FOLLOW_UP_NOTICE = "人工客服已收到您的补充信息，请您稍候。"

    def get_active_session(
        self,
        db: Session,
        session_id: str,
        user_id: int
    ) -> Optional[HumanServiceSession]:
        return db.query(HumanServiceSession).filter(
            HumanServiceSession.session_id == session_id,
            HumanServiceSession.user_id == user_id,
            HumanServiceSession.status.in_(["pending", "handling"])
        ).first()

    def create_or_reopen_session(
        self,
        db: Session,
        session_id: str,
        user_id: int,
        last_user_message: str,
        transfer_reason: Optional[str] = None
    ) -> HumanServiceSession:
        ticket = db.query(HumanServiceSession).filter(
            HumanServiceSession.session_id == session_id,
            HumanServiceSession.user_id == user_id
        ).first()

        if ticket:
            ticket.status = "pending"
            ticket.transfer_reason = transfer_reason or ticket.transfer_reason
            ticket.last_user_message = last_user_message
            ticket.assigned_admin_id = None
            ticket.resolved_at = None
            ticket.last_message_at = datetime.now()
            return ticket

        ticket = HumanServiceSession(
            session_id=session_id,
            user_id=user_id,
            status="pending",
            transfer_reason=transfer_reason,
            last_user_message=last_user_message,
            last_message_at=datetime.now()
        )
        db.add(ticket)
        db.flush()
        return ticket

    def enqueue_handoff(
        self,
        db: Session,
        session_id: str,
        user_id: int,
        user_message: str,
        transfer_reason: Optional[str] = None
    ) -> str:
        notice = self.HANDOFF_NOTICE
        self.create_or_reopen_session(
            db=db,
            session_id=session_id,
            user_id=user_id,
            last_user_message=user_message,
            transfer_reason=transfer_reason
        )

        db.add(ChatHistory(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=user_message
        ))
        db.add(ChatHistory(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=notice,
            source="system"
        ))
        db.commit()
        return notice

    def append_user_follow_up(
        self,
        db: Session,
        session_id: str,
        user_id: int,
        user_message: str
    ) -> str:
        ticket = self.get_active_session(db, session_id, user_id)
        if not ticket:
            return self.enqueue_handoff(db, session_id, user_id, user_message)

        notice = self.FOLLOW_UP_NOTICE
        ticket.last_user_message = user_message
        ticket.last_message_at = datetime.now()

        db.add(ChatHistory(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=user_message
        ))
        db.add(ChatHistory(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=notice,
            source="system"
        ))
        db.commit()
        return notice

    def list_tickets(
        self,
        db: Session,
        status: Optional[str] = None,
        keyword: Optional[str] = None
    ):
        query = db.query(HumanServiceSession)

        if status:
            query = query.filter(HumanServiceSession.status == status)
        else:
            query = query.filter(HumanServiceSession.status.in_(["pending", "handling"]))

        if keyword:
            query = query.join(User, User.id == HumanServiceSession.user_id).filter(
                (User.username.contains(keyword))
                | (HumanServiceSession.session_id.contains(keyword))
                | (HumanServiceSession.last_user_message.contains(keyword))
            )

        return query.order_by(HumanServiceSession.last_message_at.desc()).all()

    def get_ticket(self, db: Session, ticket_id: int) -> Optional[HumanServiceSession]:
        return db.query(HumanServiceSession).filter(HumanServiceSession.id == ticket_id).first()

    def get_ticket_by_session(self, db: Session, session_id: str) -> Optional[HumanServiceSession]:
        return db.query(HumanServiceSession).filter(
            HumanServiceSession.session_id == session_id
        ).first()

    def get_user_ticket(self, db: Session, session_id: str, user_id: int) -> Optional[HumanServiceSession]:
        return db.query(HumanServiceSession).filter(
            HumanServiceSession.session_id == session_id,
            HumanServiceSession.user_id == user_id
        ).first()

    def get_admin_history(self, db: Session, session_id: str, limit: int = 100):
        ticket = db.query(HumanServiceSession).filter(
            HumanServiceSession.session_id == session_id
        ).first()
        
        if not ticket:
            return []
        
        handoff_time = ticket.created_at
        
        return db.query(ChatHistory).filter(
            ChatHistory.session_id == session_id,
            ChatHistory.created_at >= handoff_time,
            or_(
                ChatHistory.role == "user",
                and_(
                    ChatHistory.role == "assistant",
                    ChatHistory.source == "human"
                ),
                and_(
                    ChatHistory.role == "assistant",
                    ChatHistory.source == "system"
                )
            )
        ).order_by(ChatHistory.created_at.asc()).limit(limit).all()

    def reply(
        self,
        db: Session,
        ticket: HumanServiceSession,
        admin_id: int,
        content: str
    ) -> HumanServiceSession:
        ticket.status = "handling"
        ticket.assigned_admin_id = admin_id
        ticket.last_message_at = datetime.now()
        ticket.resolved_at = None

        db.add(ChatHistory(
            session_id=ticket.session_id,
            user_id=ticket.user_id,
            role="assistant",
            content=content,
            source="human"
        ))
        db.commit()
        db.refresh(ticket)
        return ticket

    def set_handling(
        self,
        db: Session,
        ticket: HumanServiceSession,
        admin_id: int
    ) -> HumanServiceSession:
        ticket.status = "handling"
        ticket.assigned_admin_id = admin_id
        ticket.last_message_at = datetime.now()
        db.commit()
        db.refresh(ticket)
        return ticket

    def close(
        self,
        db: Session,
        ticket: HumanServiceSession,
        admin_id: Optional[int]
    ) -> HumanServiceSession:
        ticket.status = "closed"
        if admin_id is not None:
            ticket.assigned_admin_id = admin_id
        ticket.resolved_at = datetime.now()
        ticket.last_message_at = datetime.now()
        ticket.updated_at = datetime.now()
        db.commit()
        db.refresh(ticket)
        return ticket

    def remove_session(self, db: Session, session_id: str, user_id: int) -> None:
        db.query(HumanServiceSession).filter(
            HumanServiceSession.session_id == session_id,
            HumanServiceSession.user_id == user_id
        ).delete()


human_service = HumanService()
