import db
import web_models as web_md

from specials import HashManager

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import FileResponse

app = FastAPI(title='fishmess-server') # Для запуска сервера: uvicorn main:app --reload --port 8000
#active_connections = {} # Websocket (user_id -> Websocket)

temporary_access_tokens = {} # access_token: login

@app.post("/auth/login", response_model=web_md.LoginResponse)
async def login(request: web_md.LoginRequest):
    login = request.login
    password = request.password
    # Верификация пользователя
    user = db.verify_user(login, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid login or password")
    # Постоянный токен доступа
    access_token = HashManager.generate_token()
    temporary_access_tokens[access_token] = login
    # Ответ 200
    response = {"access_token": access_token}
    return response

def extract_access_token(request: Request) -> str | None:
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    access_token = auth_header.split(' ')[-1]
    return access_token

def validation_by_access_token(access_token: str) -> login:
    login = temporary_access_tokens.get(access_token)
    if not login:
        raise HTTPException(status_code=401, detail="Invalid access token")
    return login

#
@app.get("/media/{media_id}")
async def get_media(media_id: int, request: Request):
    access_token = extract_access_token(request)
    login = validation_by_access_token(access_token)

    user = db.get_user_by_login(login)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    media = db.get_media(media_id)
    """response = FileResponse(
        path=media.path,
        media_type=media.type,
        filename=media.filename
    )"""

    return {}
# ШАБЛОН
@app.post("/media/send") # +
async def send_media(request: Request):
    access_token = extract_access_token(request)
    login = validation_by_access_token(access_token)

    user = db.get_user_by_login(login)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    



@app.get("/users/me", response_model=web_md.UserResponse)
async def get_current_user(request: Request):
    access_token = extract_access_token(request)
    login = validation_by_access_token(access_token)
    
    user = db.get_user_by_login(login)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    response = {"data": user}
    return response

@app.get("/users/{user_id}", response_model=web_md.UserResponse)
async def get_user_by_id(user_id: int, request: Request):
    access_token = extract_access_token(request)
    _login = validation_by_access_token(access_token)
    
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    response = {"data": user}
    return response

@app.get("/chats", response_model=web_md.ChatsGetResponse)
async def get_chats(request: Request):
    access_token = extract_access_token(request)
    login = validation_by_access_token(access_token)

    user = db.get_user_by_login(login)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    chats = db.get_chats_by_user_id(user.id)
    response = {
        "chats_count": len(chats),
        "data": chats
    }

    return response

@app.post("/chats", response_model=web_md.ChatsPostResponse)
async def post_chats(request: web_md.ChatsPostRequest):
    access_token = extract_access_token(request)
    login = validation_by_access_token(access_token)

    chat_name = request.name
    to_user_id = request.to_user_id

    owner = db.get_user_by_login(login)
    recipient = db.get_user_by_id(to_user_id)

    chat_model = db.create_chat(chat_name, owner, recipient)

    response = {"data": chat_model}
    return response