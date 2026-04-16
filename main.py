import db
import web_models as web_md

from specials import HashManager

from fastapi import FastAPI, HTTPException, Depends, Request

app = FastAPI(title='fishmess-server') # Для запуска сервера: uvicorn main:app --reload --port 8000
#active_connections = {} # Websocket (user_id -> Websocket)

#from fastapi.security import HTTPBearer
#security = HTTPBearer()

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
    response = {
        "access_token": access_token,
        "user": user
    }

    return response

@app.post("/auth/reg")
async def registration(request):
    pass

def extract_access_token(request: Request) -> str | None:
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Authorization header missing or invalid")
    access_token = auth_header.split(' ')[-1]
    return access_token

@app.get("/users/me", response_model=web_md.UserResponse)
async def get_current_user(request: Request):
    access_token = extract_access_token(request)
    login = temporary_access_tokens.get(access_token)
    if not login:
        raise HTTPException(status_code=401, detail="Invalid access token")
    
    user = db.get_user_by_login(login)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    response = {"data": user}
    return response

@app.get("/users/{user_id}", response_model=web_md.UserResponse)
async def get_user_by_id(user_id: int, request: Request):
    access_token = extract_access_token(request)
    if not access_token or access_token not in temporary_access_tokens:
        raise HTTPException(status_code=401, detail="Invalid access token")
    
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    response = {"data": user}
    return response