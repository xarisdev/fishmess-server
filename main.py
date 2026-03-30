from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models import AuthRequest, AuthResponse, RefreshRequest, ChatModel, UserModel

# Для запуска сервера: uvicorn main:app --reload --port 8000
app = FastAPI(tittle='fishmess-server')

sessions = {}
refresh_tokens = {}

security = HTTPBearer()

# get user from db
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_token(token) # Проверка токена (внешка)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub")
    user = await get_user_by_id(user_id) # Из БД
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/auth", response_model=AuthResponse)
async def auth(requset: AuthRequest): # Authorization
    access_key = requset.access_key # Private entry key
    
    #
    # generate access token
    #

    #
    # generate refresh token
    #

    data = { # API example
        "access_token": "",
        "refresh_token": "",
        "token_type": "bearer"
    }

    return data

@app.post("/auth/refresh", response_model=AuthResponse)
async def auth_refresh(request: RefreshRequest):
    refresh_token = request.refresh_token

    #
    # Валидация
    #

    #
    # Генерация access токена
    #

    data = {
        "status": "",
        "data": {
            "access_token": ""
        }
    }

"""
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    session = sessions.get(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return {}"""