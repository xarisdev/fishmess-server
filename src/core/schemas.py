import uuid as uuid_pkg
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_serializer

class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str

class TokenData(BaseModel):
    user_id: int