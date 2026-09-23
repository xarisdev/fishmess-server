from typing import Optional
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, model_validator

from sqlalchemy import BigInteger, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from ..db.model import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(16), index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), default="")

    password_hash: Mapped[str] = mapped_column(String(255))
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    avatar_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

class UserCreate(BaseModel):
    username: str
    password: str
    first_name: Optional[str] = ""
    avatar_id: Optional[int] = None

class UserCreateInternal(BaseModel):
    username: str
    password_hash: str
    first_name: Optional[str] = ""
    avatar_id: Optional[int] = None

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    first_name: str

    created_at: datetime

    is_online: bool
    avatar_id: int | None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    avatar_id: Optional[int] = None

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("Requires at least 1 field")
        return self