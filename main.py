from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models import AuthRequest, AuthResponse, RefreshRequest, UserOut

import auth as _auth

# Для запуска сервера: uvicorn main:app --reload --port 8000
app = FastAPI(tittle='fishmess-server')

sessions = {} # {access_token: {"user_id": int}}
refresh_tokens = {} # {refresh_token: user_id}

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    session = sessions.get(token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return {}

@app.post("/auth", response_model=AuthResponse)
async def auth(request: AuthRequest):
    #user = None
    access_token = request.access_token
    refresh_token = _auth.create_refresh_token(access_token)
    
    sessions[access_token] = {"refresh_token": refresh_token}
    refresh_tokens[refresh_token] = access_token #

    data = {
        "status": "success",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    }

    return data

@app.post("/auth/refresh")
async def refresh(request: RefreshRequest):
    refresh_token = request.refresh_token
    if refresh_token not in refresh_tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    
    access_token = refresh_tokens[refresh_token]
    sessions[access_token] = {"refresh_token": refresh_token}

    return {
        "status": "success",
        "data": {
            "access_token": access_token
        }
    }

#@app.get("/users/me")

"""@app.get("/")
def auth_and_refresh(access_type: str, token: str): 
    if access_type == "auth":
        data = {"isConnected": True, "refresh_token": token+"_refr"}
    elif access_type == "refr":
        data = {"chat_list": {}, "user_info": {}}
    
    return data"""

# Авторизация
# access_type: 'auth', 'refr'
# GET /localhost:port/?access_type=str&token=token
# RESPONSE
# data = {"isConnected": bool, "refresh_token": str}
#
# Обновление (подписка)
# GET /localhost:port/?access_type=str&refresh_token=refresh_token
# RESPONSE
# data = {"chat_list": dict, "user_info": dict}