import db
import specials as sp

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models import AuthRequest, AuthResponse, ChatCreateRequest

app = FastAPI(title='fishmess-server') # Для запуска сервера: uvicorn main:app --reload --port 8000
active_connections = {} # Websocket (user_id -> Websocket)

security = HTTPBearer()

# Custom exception (Database)
from specials import *
@app.exception_handler(ConflictError)
async def conflict_exception_handler(r, e: ConflictError): raise HTTPException(status_code=409, detail=str(e))
@app.exception_handler(BadRequestError)
async def bad_request_handler(r, e: BadRequestError): raise HTTPException(status_code=400, detail=str(e))
@app.exception_handler(DatabaseError)
async def db_error_handler(r, e: DatabaseError): raise HTTPException(status_code=503, detail=str(e))

# Только при /auth(access_token)
def verify_access_token(user_tag, access_token) -> bool:
    hashed_key = db.get_hash_ac_from_user(user_tag) # Уже созданный хэшированный ключ
    # Сравнение получаемого и хранимого ключа (постоянный)
    isVerified = sp.verify_api_key(access_token, hashed_key)
    if not isVerified:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Валидация access_token
    return isVerified

# Каждый POST запрос с header <Authorization> - refresh_token
def verify_refresh_token(refresh_token) -> tuple[bool, str]:
    hashed_key = sp.hash_api_key(refresh_token) # Хэшируем получаемый токен
    data = db.get_refresh_data_from_user(hashed_key) # Получаем данные по хэшированному токену
    # Сравнение получаемого и хранимого ключа (refresh)
    isVerified = all(
        [sp.verify_api_key(refresh_token, data.get('refresh_token')),
        match_timestamp(data.get('updated_at'), expired_after=timedelta(days=7))])
    if not isVerified:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Валидация refresh_token
    return (isVerified, data[2])

# Получение объекта пользователя
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    refresh_token = credentials.credentials # токен из header bearer
    # Валидация refresh_token
    data = verify_refresh_token(refresh_token)
    if not data[0]:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # Получение данных о пользователе
    user_data = db.get_user_data_by_tag(data[1])
    user_obj = sp.construct_user(user_data)

    return user_obj

@app.post("/auth", response_model=AuthResponse)
async def auth(request: AuthRequest): # Authorization
    user_tag = request.user_tag
    access_token = request.access_token
    # Валидация данных (исходим из уже созданных пользователей)
    verify_access_token(user_tag, access_token)
    # Генерация и сохранение refresh_token
    refresh_token = sp.generate_refresh_token() # Хэшированный токен
    db.save_refresh_token(user_tag, refresh_token)
    # Возврат
    response = {
        "status": "success",
        "data": {
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    }
    return response

@app.post("/chats")
async def create_chat(request: ChatCreateRequest, current_user: User = Depends(get_current_user)):
    type = request.type
    participants = request.participants
    name = request.name

    user = current_user