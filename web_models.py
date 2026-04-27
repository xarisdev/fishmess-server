from pydantic import BaseModel
from datetime import datetime

from db_models import UserModel, ChatModel, MessageModel
# /auth/login
class LoginRequest(BaseModel):
    login:          str
    password:       str
class LoginResponse(BaseModel):
    access_token:   str
# /users
class UserResponse(BaseModel):
    data:           UserModel
# /chats
class ChatsGetResponse(BaseModel):
    chats_count:    int
    data:           list[ChatModel]
# /chats
class ChatsPostRequest(BaseModel):
    name:           str
    to_user_id:     int
class ChatsPostResponse(BaseModel):
    data:           ChatModel
# /chats/chat_id/messages
class MessagesPostRequest(BaseModel):
    text:           str
class MessagesPostResponse(BaseModel):
    data:           MessageModel
# /chats/chat_id/messages
class MessagesGetResponse(BaseModel):
    messages_count: int
    data:           list[MessageModel]