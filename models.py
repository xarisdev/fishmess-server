from pydantic import BaseModel

class AuthRequest(BaseModel):
    user_tag: str
    access_key: str

class AuthResponse(BaseModel):
    status: str
    data: dict

class RefreshRequest(BaseModel):
    refresh_token: str