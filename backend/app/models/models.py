from sqlalchemy import Column, Integer, String, Text, DECIMAL, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    phone = Column(String(20))
    role = Column(String(20), default="user")
    avatar = Column(String(255), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True, comment='最后登录时间')

    orders = relationship("Order", back_populates="user")
    chat_histories = relationship("ChatHistory", back_populates="user")
    human_service_sessions = relationship(
        "HumanServiceSession",
        foreign_keys="HumanServiceSession.user_id",
        back_populates="user"
    )
    assigned_human_service_sessions = relationship(
        "HumanServiceSession",
        foreign_keys="HumanServiceSession.assigned_admin_id",
        back_populates="assigned_admin"
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100))
    price = Column(DECIMAL(10, 2), nullable=False)
    description = Column(Text)
    specs = Column(JSON)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_no = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(String(20), default="pending")
    payment_method = Column(String(50))
    payment_time = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    logistics = relationship("Logistics", back_populates="order", uselist=False, cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")


class Logistics(Base):
    __tablename__ = "logistics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    tracking_no = Column(String(100))
    carrier = Column(String(50))
    status = Column(String(20), default="pending")
    current_location = Column(String(200))
    estimated_arrival = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    order = relationship("Order", back_populates="logistics")
    tracks = relationship("LogisticsTrack", back_populates="logistics", cascade="all, delete-orphan")


class LogisticsTrack(Base):
    __tablename__ = "logistics_tracks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    logistics_id = Column(Integer, ForeignKey("logistics.id"), nullable=False)
    location = Column(String(200))
    status = Column(String(100))
    track_time = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

    logistics = relationship("Logistics", back_populates="tracks")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(20), default="bot")
    reference_sources = Column(JSON, default=list, comment='参考来源列表')
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="chat_histories")


class HumanServiceSession(Base):
    __tablename__ = "human_service_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    transfer_reason = Column(String(255))
    last_user_message = Column(Text)
    assigned_admin_id = Column(Integer, ForeignKey("users.id"))
    resolved_at = Column(DateTime)
    last_message_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id], back_populates="human_service_sessions")
    assigned_admin = relationship(
        "User",
        foreign_keys=[assigned_admin_id],
        back_populates="assigned_human_service_sessions"
    )


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    source = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class KnowledgeSyncLog(Base):
    __tablename__ = "knowledge_sync_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doc_id = Column(Integer, index=True)
    action = Column(String(20), nullable=False)
    status = Column(String(20), default="pending")
    error_message = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class EvaluationRecord(Base):
    __tablename__ = "evaluation_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), index=True)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    contexts = Column(JSON)
    ground_truth = Column(Text)
    faithfulness_score = Column(DECIMAL(3, 2))
    answer_relevancy_score = Column(DECIMAL(3, 2))
    context_precision_score = Column(DECIMAL(3, 2))
    context_recall_score = Column(DECIMAL(3, 2))
    overall_score = Column(DECIMAL(3, 2))
    evaluation_framework = Column(String(50), default="builtin")
    created_at = Column(DateTime, server_default=func.now())


class EvaluationDataset(Base):
    __tablename__ = "evaluation_dataset"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question = Column(Text, nullable=False)
    ground_truth = Column(Text, nullable=False)
    category = Column(String(50))
    relevant_doc_ids = Column(JSON)
    question_embedding = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
