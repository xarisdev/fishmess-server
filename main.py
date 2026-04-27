import db
import web_models as wmd

from specials import HashManager

from fastapi import (
    FastAPI, HTTPException,
    Request, Header
)

# Для запуска сервера: uvicorn main:app --reload --port 8000
app = FastAPI(title='fishmess-server')

#active_connections = {} # Websocket (user_id -> Websocket)

# access_token: login
temporary_access_tokens = {}

def extract_access_token(auth: str) -> str:
    if not auth:
        raise HTTPException(
            status_code=401,
            detail="Authorization header missing or invalid"
        )

    access_token = auth.split(' ')[1]
    return access_token

def validation_by_access_token(access_token: str) -> login:
    login = temporary_access_tokens.get(access_token)
    if not login:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token"
        )

    return login

# Аутентификация пользователя
@app.post("/auth/login", response_model=wmd.LoginResponse)
async def login(request: wmd.LoginRequest):
    login = request.login
    password = request.password
    if not login or not password:
        raise HTTPException(
            status_code=400,
            detail="Bad Request"
        )
    
    user = db.verify_user(login, password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid login or password"
        )
    
    access_token = HashManager.generate_token()
    temporary_access_tokens[access_token] = login
    
    response = {"access_token": access_token}
    return response

@app.get("/users/me", response_model=wmd.UserResponse)
async def get_current_user(auth: str = Header(...)):
    access_token = extract_access_token(auth)
    login = validation_by_access_token(access_token)
    
    user = db.get_user_by_login(login)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    response = {"data": user}
    return response

@app.get("/users/{user_id}", response_model=wmd.UserResponse)
async def get_user_by_id(user_id: int, auth: str = Header(...)):
    access_token = extract_access_token(auth)
    _login = validation_by_access_token(access_token)
    
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    response = {"data": user}
    return response

@app.get("/chats", response_model=wmd.ChatsGetResponse)
async def get_chats(auth: str = Header(...)):
    access_token = extract_access_token(auth)
    login = validation_by_access_token(access_token)

    user = db.get_user_by_login(login)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    chats = db.get_chats_by_user_id(user.id)
    response = {
        "chats_count": len(chats),
        "data": chats
    }
    return response

@app.post("/chats", response_model=wmd.ChatsPostResponse)
async def post_chats(request: wmd.ChatsPostRequest, auth: str = Header(...)):
    access_token = extract_access_token(auth)
    login = validation_by_access_token(access_token)

    chat_name = request.name
    to_user_id = request.to_user_id

    if not chat_name or not to_user_id:
        raise HTTPException(status_code=400, detail="Bad Request")
    # Исключение создания чата с несуществующим пользователем
    # БД вызовет ошибку если нет одного из пользователей
    own_id = db.get_user_by_login(login).id
    rec_id = db.get_user_by_id(to_user_id).id

    chat_model = db.create_chat(chat_name, own_id, rec_id)

    if isinstance(chat_model, tuple):
        raise HTTPException(*chat_model)

    response = {"data": chat_model}
    return response

# Отправка сообщения в чат
@app.post("/chats/{chat_id}/messages", response_model=wmd.MessagesPostResponse)
async def post_message(chat_id: int, request: wmd.MessagesPostRequest, auth: str = Header(...)):
    access_token = extract_access_token(auth)
    login = validation_by_access_token(access_token)

    chat_id = chat_id
    text = request.text
    if not text:
        raise HTTPException(status_code=400, detail="Bad Request")

    user = db.get_user_by_login(login)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    message_model = db.send_message(chat_id, user.id, text)
    response = {"data": message_model}
    return response

# Получение списка сообщений
@app.get("/chats/{chat_id}/messages", response_model=wmd.MessagesGetResponse)
async def get_messages(chat_id: int, limit: int = 50, auth: str = Header(...)):
    access_token = extract_access_token(auth)
    login = validation_by_access_token(access_token)

    user = db.get_user_by_login(login)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    messages = db.get_messages(chat_id, limit)
    response = {
        "messages_count": len(messages),
        "data": messages
    }
    return response