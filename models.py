from pydantic import BaseModel
from datetime import datetime

# /auth <-
class AuthHeaders(BaseModel):
    client_id: str
    access_token: str
# /auth | (/auth/refresh) ->
class AuthResponse(BaseModel):
    status: str
    data: dict
# /refresh <-
class RefreshHeaders(BaseModel):
    client_id: str
    refresh_token: str
# /refresh <-
class RefreshRequest(BaseModel):
    created_at: datetime
    token_type: str