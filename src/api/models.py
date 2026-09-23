from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class GetMultiResponse(BaseModel, Generic[T]):
    data: list[T]
    total_count: int

class RefreshRequest(BaseModel):
    refresh_token: str