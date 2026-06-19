# Copia de develop

from datetime import datetime
import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Enum as SAEnum,
    ForeignKey,
    TIMESTAMP,
    Boolean,
)
from sqlalchemy.orm import relationship
from imc.databases.postgres.database import Base


# ==== ENUMS ====
class RiskSeverity(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EventStatus(enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class EventSource(enum.Enum):
    KAFKA = "KAFKA"
    CEP = "CEP"
    DETECTOR = "DETECTOR"
    TEST = "TEST"
    LOGISTICS = "LOGISTICS"  # opzionale, utile per alert tipo “delivery delay”
    USER = "USER"


# ==== MODELS ====


class Plan(Base):
    __tablename__ = "plan"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    instructions = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    risk_types = relationship("RiskType", back_populates="plan")


class RiskType(Base):
    __tablename__ = "risk_type"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    severity = Column(SAEnum(RiskSeverity), nullable=False)
    plan_id = Column(Integer, ForeignKey("plan.id", ondelete="SET NULL"), nullable=True)

    plan = relationship("Plan", back_populates="risk_types")
    events = relationship("Event", back_populates="risk_type")


class Rule(Base):
    __tablename__ = "rule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    expression = Column(Text)
    priority = Column(Integer, nullable=False)
    active = Column(Boolean, nullable=False)


class Plugin(Base):
    __tablename__ = "plugin"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    base_url = Column(String(512))
    openapi_url = Column(String(512))
    active = Column(Boolean, nullable=False)


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    external_id = Column(String(255), nullable=True)
    severity = Column(SAEnum(RiskSeverity))
    status = Column(SAEnum(EventStatus), nullable=False, default=EventStatus.OPEN)
    source = Column(SAEnum(EventSource), nullable=False, default=EventSource.TEST)
    payload = Column(Text)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    risk_type_id = Column(
        Integer, ForeignKey("risk_type.id", ondelete="SET NULL"), nullable=True
    )

    risk_type = relationship("RiskType", back_populates="events")
    chats = relationship("Chat", back_populates="event", cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chat"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    event_id = Column(Integer, ForeignKey("event.id"))
    created_by = Column(Integer, ForeignKey("jhi_user.id"), nullable=True)

    event = relationship("Event", back_populates="chats")
    messages = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan"
    )
    created_by_user = relationship("JhiUser", back_populates="chats")


class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    response_time_ms = Column(Integer)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    chat_id = Column(Integer, ForeignKey("chat.id"))
    created_by = Column(Integer, ForeignKey("jhi_user.id"), nullable=True)

    chat = relationship("Chat", back_populates="messages")
    created_by_user = relationship("JhiUser", back_populates="messages")


# ==== JHI (utenti e ruoli) ====


class JhiAuthority(Base):
    __tablename__ = "jhi_authority"
    name = Column(String(50), primary_key=True)


class JhiUser(Base):
    __tablename__ = "jhi_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(60), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    email = Column(String(191))
    image_url = Column(String(256))
    activated = Column(Boolean, nullable=False)
    lang_key = Column(String(10))
    activation_key = Column(String(20))
    reset_key = Column(String(20))
    created_by = Column(String(50))
    created_date = Column(TIMESTAMP)
    reset_date = Column(TIMESTAMP)
    last_modified_by = Column(String(50))
    last_modified_date = Column(TIMESTAMP)

    messages = relationship("Message", back_populates="created_by_user")
    chats = relationship("Chat", back_populates="created_by_user")


class JhiUserAuthority(Base):
    __tablename__ = "jhi_user_authority"
    user_id = Column(Integer, ForeignKey("jhi_user.id"), primary_key=True)
    authority_name = Column(
        String(50), ForeignKey("jhi_authority.name"), primary_key=True
    )
