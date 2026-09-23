from typing import Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from sqlalchemy import Integer, BigInteger, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from ..db.model import Base

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False
    )
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    media_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("media.id", ondelete="CASCADE"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    text: Mapped[str] = mapped_column(String(900))

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

class MessageCreate(BaseModel):
    chat_id: int
    owner_id: int

    text: str = Field(default="", max_length=900)

    media_id: Optional[int] = None

class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chat_id: int
    owner_id: int
    media_id: int | None
    created_at: datetime
    text: str
    is_read: bool

class MessageUpdate(BaseModel):
    text: Optional[str] = None
    is_read: Optional[bool] = None