import db
import specials as sp

from models import AuthHeaders, AuthResponse, RefreshHeaders, RefreshRequest

from fastapi import FastAPI, HTTPException, Depends

app = FastAPI(title='fishmess-server') # Для запуска сервера: uvicorn main:app --reload --port 8000
active_connections = {} # Websocket (user_id -> Websocket)

from specials import *
@app.exception_handler(ConflictError)
async def conflict_exception_handler(r, e: ConflictError): raise HTTPException(status_code=409, detail=str(e))
@app.exception_handler(BadRequestError)
async def bad_request_handler(r, e: BadRequestError): raise HTTPException(status_code=400, detail=str(e))
@app.exception_handler(DatabaseError)
async def db_error_handler(r, e: DatabaseError): raise HTTPException(status_code=503, detail=str(e))

from fastapi.security import HTTPBearer
security = HTTPBearer()

# POST /auth
# Верификация access_token и получение хранимого хэша
def verify_access_token(client_id: str, access_token: str):
    hashed_access_token = db.get_hashed_access_token(client_id)
    isVerified = sp.verify_api_key(access_token, hashed_access_token)
    if not isVerified:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return hashed_access_token
# Получение данных из заголовка
def get_auth_data(credentials: HTTPBearer = Depends(security)) -> AuthHeaders:
    crd = credentials.credentials
    crd = crd.split()[-1].split(":")
    
    if not crd: return print(crd)
    
    headers = AuthHeaders(client_id=crd[0], access_token=crd[1])
    return headers
#
@app.post("/auth", response_model=AuthResponse)
async def auth(headers: AuthHeaders = Depends(get_auth_data)): # Authorization
    client_id = headers.client_id
    access_token = headers.access_token
    # Хранимый хэш access_token
    hashed_access_token = verify_access_token(client_id, access_token)
    # Новый refresh_token
    refresh_token = sp.generate_refresh_token()
    hashed_refresh_token = hash_api_key(refresh_token)
    # Обновление таблиц с токенами
    created_at = db.auth_set_refresh_token(client_id, hashed_access_token, hashed_refresh_token)
    
    response = {
        "status": "success",
        "data": {
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "created_at": created_at
        }
    }

    return response
# /---/

# POST /auth/refresh
# Верификация refresh_token
def verify_refresh_token(client_id: str, refresh_token: str):
    hashed_refresh_token = db.get_hashed_refresh_token(client_id)
    isVerified = sp.verify_api_key(refresh_token, hashed_refresh_token[0])
    if not isVerified:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return hashed_refresh_token
# Получение данных из заголовка
def get_refresh_data(credentials: HTTPBearer = Depends(security)) -> RefreshHeaders:
    crd = credentials.credentials
    crd = crd.split()[-1].split(":")

    if not crd: return print(crd)

    headers = RefreshHeaders(client_id=crd[0], refresh_token=crd[1])
    return headers
#
@app.post("/auth/refresh", response_model=AuthResponse)
async def refresh(request: RefreshRequest, headers: RefreshHeaders = Depends(get_refresh_data)):
    created_at = request.created_at
    token_type = request.token_type

    client_id     = headers.client_id
    refresh_token = headers.refresh_token

    data = verify_refresh_token(client_id, refresh_token)
    hashed_refresh_token            = data[0]
    hashed_refresh_token_created_at = data[1]

    if created_at != hashed_refresh_token_created_at:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not sp.match_timestamp(hashed_refresh_token_created_at, timedelta(days=7)):
        raise HTTPException(status_code=401, detail="Token expired")
    
    new_refresh_token = sp.generate_refresh_token()
    hashed_new_refresh_token = hash_api_key(new_refresh_token)

    created_at = db.refresh_set_refresh_token(client_id, hashed_new_refresh_token)

    response = {
        "status": "success",
        "data": {
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "created_at": created_at
        }
    }

    return response
# /---/