"""Database models for conversations."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Conversation(Base):
    """Conversation model."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=True)
    source = Column(String, default="shortcuts")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Message model."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")


# Database setup
def get_database_url() -> str:
    """Get database URL from config."""
    from app.config import settings

    # Use PostgreSQL if DATABASE_URL is set
    if settings.use_postgresql and settings.database_url:
        return settings.database_url

    # Fallback to SQLite
    db_path = settings.database_path
    return f"sqlite:///{db_path}"


def create_engine_instance():
    """Create SQLAlchemy engine with connection pooling."""
    from app.config import settings

    db_url = get_database_url()

    # SQLite-specific connection args
    if not settings.use_postgresql:
        connect_args = {"check_same_thread": False}
        # SQLite doesn't need pool settings
        return create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
    else:
        # PostgreSQL connection pooling
        connect_args = {}
        return create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=10,  # Number of connections to maintain
            max_overflow=20,  # Additional connections beyond pool_size
            pool_recycle=3600,  # Recycle connections after 1 hour
        )


def get_session_factory():
    """Get session factory."""
    engine = create_engine_instance()
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


SessionLocal = get_session_factory()
