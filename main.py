from fastapi import FastAPI, HTTPException
# BaseModel
from models import AuthRequest, AuthResponse

from db import get_hash_from_user, save_refresh_token
from specials import generate_refresh_token

app = FastAPI(title='fishmess-server') # Для запуска сервера: uvicorn main:app --reload --port 8000
active_connections = {} # Websocket (user_id -> Websocket)

# Custom exception (Database)
from specials import *
@app.exception_handler(ConflictError)
async def conflict_exception_handler(request, exc: ConflictError): raise HTTPException(status_code=409, detail=str(exc))
@app.exception_handler(BadRequestError)
async def bad_request_handler(request, exc: BadRequestError): raise HTTPException(status_code=400, detail=str(exc))
@app.exception_handler(DatabaseError)
async def db_error_handler(request, exc: DatabaseError): raise HTTPException(status_code=503, detail=str(exc))

# Token security
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_api_key(plain_key: str) -> str: return pwd_context.hash(plain_key)
def verify_api_key(plain_key: str, hashed_key: str) -> bool: return pwd_context.verify(plain_key, hashed_key)

@app.post("/auth", response_model=AuthResponse)
async def auth(request: AuthRequest): # Authorization
    user_tag = request.user_tag
    access_key = request.access_key
    # Валидация данных
    hashed_key = get_hash_from_user(user_tag)
    isVerified = verify_api_key(access_key, hashed_key)
    if not isVerified:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    refresh_token = generate_refresh_token()
    save_refresh_token(user_tag, refresh_token)
    response = {
        "status": "success",
        "data": {
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    }
    return response