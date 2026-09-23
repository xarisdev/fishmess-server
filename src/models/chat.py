from typing import Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, model_validator

from sqlalchemy import Integer, BigInteger, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..db.model import Base

class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user_one_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", name="fk_chats_user_one")
    )
    user_two_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", name="fk_chats_user_two")
    )

    avatar_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    last_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_one_id", "user_two_id", name="uq_chat_pair"),
    )

class ChatCreate(BaseModel):
    name: Optional[str] = ""
    user_one_id: int
    user_two_id: int
    avatar_id: Optional[int] = None

    @model_validator(mode="after")
    def sort_user_ids(self) -> "ChatCreate":
        if self.user_one_id == self.user_two_id:
            raise ValueError("User cannot create a chat with themselves")
        if self.user_one_id > self.user_two_id:
            self.user_one_id, self.user_two_id = self.user_two_id, self.user_one_id
        return self

class ChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    user_one_id: int
    user_two_id: int
    avatar_id: int | None
    last_message_id: int | None

class ChatUpdate(BaseModel):
    name: Optional[str] = None
    avatar_id: Optional[int] = None
    last_message_id: Optional[int] = None

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "ChatUpdate":
        if not self.model_fields_set:
            raise ValueError("Requires at least 1 field")
        return self