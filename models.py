from pydantic import BaseModel

class AuthRequest(BaseModel):
    user_tag: str
    access_token: str

class AuthResponse(BaseModel):
    status: str
    data: dict

class ChatCreateRequest(BaseModel):
    type: str
    participants: list[int]
    name: str | None = None

class User(BaseModel):
    id: int
    name: str
    user_tag: str
    avatar_id: int
    created_at: any
    updated_at: any