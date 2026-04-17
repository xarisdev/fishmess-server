from pydantic import BaseModel
from datetime import datetime

from db_models import UserModel, ChatModel

# POST /auth/login --request
class LoginRequest(BaseModel):
    login:          str
    password:       str
# POST /auth/login --response
class LoginResponse(BaseModel):
    access_token:   str

# GET /users/me OR /users/{id} --response
class UserResponse(BaseModel):
    data:           UserModel

# GET /chats --response
class ChatsGetResponse(BaseModel):
    chats_count:    int
    data:           list[ChatModel]

# POST /chats --request
class ChatsPostRequest(BaseModel):
    owner_id:       int
    members:        list[int]
    