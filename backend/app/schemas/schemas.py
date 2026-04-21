from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class UserBase(BaseModel):
    username: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    role: str = "user"
    avatar: Optional[str] = ""
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "user"
    username: str


class ProductBase(BaseModel):
    name: str
    category: Optional[str] = None
    price: Decimal
    description: Optional[str] = None
    specs: Optional[dict] = None
    stock: Optional[int] = 0


class ProductResponse(ProductBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class OrderItemBase(BaseModel):
    product_id: int
    quantity: int = 1
    unit_price: Decimal


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    product_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    order_no: str
    total_amount: Decimal
    status: str = "pending"
    payment_method: Optional[str] = None


class OrderResponse(OrderBase):
    id: int
    user_id: int
    payment_time: Optional[datetime] = None
    created_at: datetime
    order_items: List[OrderItemResponse] = []

    class Config:
        from_attributes = True


class LogisticsTrackBase(BaseModel):
    location: Optional[str] = None
    status: Optional[str] = None
    track_time: Optional[datetime] = None


class LogisticsTrackResponse(LogisticsTrackBase):
    id: int
    logistics_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LogisticsBase(BaseModel):
    tracking_no: Optional[str] = None
    carrier: Optional[str] = None
    status: str = "pending"
    current_location: Optional[str] = None
    estimated_arrival: Optional[datetime] = None


class LogisticsResponse(LogisticsBase):
    id: int
    order_id: int
    tracks: List[LogisticsTrackResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    session_id: Optional[str] = None
    content: str


class SourceDocument(BaseModel):
    doc_id: Optional[int] = None
    title: Optional[str] = None
    category: Optional[str] = None
    score: Optional[float] = None
    content: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    source: Optional[str] = "bot"
    sources: List[SourceDocument] = []
    created_at: datetime

    class Config:
        from_attributes = True


class SessionListItem(BaseModel):
    session_id: str
    first_message: str
    last_message: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    ticket_id: Optional[int] = None
    ticket_status: Optional[str] = None
    username: Optional[str] = None

    class Config:
        from_attributes = True


class KnowledgeDocBase(BaseModel):
    title: str
    content: str
    category: str
    source: Optional[str] = None


class KnowledgeDocCreate(KnowledgeDocBase):
    pass


class KnowledgeDocResponse(KnowledgeDocBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RAGResponse(BaseModel):
    answer: str
    session_id: str
    sources: List[SourceDocument] = []


class HumanServiceCreate(BaseModel):
    session_id: str
    content: str
    transfer_reason: Optional[str] = None


class HumanServiceReply(BaseModel):
    content: str


class HumanServiceSessionItem(BaseModel):
    id: int
    session_id: str
    user_id: int
    username: str
    status: str
    transfer_reason: Optional[str] = None
    last_user_message: Optional[str] = None
    assigned_admin_id: Optional[int] = None
    assigned_admin_name: Optional[str] = None
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime


class HumanServiceSessionDetail(HumanServiceSessionItem):
    messages: List[ChatHistoryResponse] = []


class HumanServiceUserStatus(BaseModel):
    exists: bool
    ticket_id: Optional[int] = None
    session_id: Optional[str] = None
    status: Optional[str] = None
    assigned_admin_name: Optional[str] = None
