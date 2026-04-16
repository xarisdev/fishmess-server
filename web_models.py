from pydantic import BaseModel
from datetime import datetime

from db_models import UserModel

# POST /auth/login --request
class LoginRequest(BaseModel):
    login: str
    password: str
# POST /auth/login --response
class LoginResponse(BaseModel):
    access_token: str
    user: UserModel

# GET /users/me OR /users/{id} --response
class UserResponse(BaseModel):
    data: UserModel