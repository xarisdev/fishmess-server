from pydantic import BaseModel

class AuthRequest(BaseModel):
    access_key: str

class AuthResponse(BaseModel):
    status: str
    data: dict

class RefreshRequest(BaseModel):
    refresh_token: str

class ChatModel(BaseModel):
    chat_id: int
    chat_type: str
    chat_name: str
    participants: list[dict[str, any]]
    created_at: str

class UserModel(BaseModel):
    user_id: int
    username: str
    status: str

    chats_list: list