from pydantic import BaseModel

class AuthRequest(BaseModel):
    access_token: str

class AuthResponse(BaseModel):
    status: str
    data: dict

class RefreshRequest(BaseModel):
    refresh_token: str

class UserOut(BaseModel):
    id: str
    username: str
    status: str