from pydantic import BaseModel
from datetime import datetime

from db_models import UserModel, ChatModel, MessageModel

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

# Получение списка чатов
# GET /chats --response_model
class ChatsGetResponse(BaseModel):
    chats_count:    int
    data:           list[ChatModel]

# Создание чата - запрос
# POST /chats --request
class ChatsPostRequest(BaseModel):
    name:           str
    to_user_id:     int

# Создание чата - ответ
# POST /chats --response
class ChatsPostResponse(BaseModel):
    data:           ChatModel


# Отправка сообщения - запрос
# POST /chats/{chat_id}/messages --request
class MessagesPostRequest(BaseModel):
    text:           str

# Отправка сообщения - ответ
# POST /chats/{chat_id}/messages --response
class MessagesPostResponse(BaseModel):
    data:           MessageModel