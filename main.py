from fastapi import FastAPI
# Для запуска сервера: uvicorn main:app --reload --port 8000

app = FastAPI(tittle='fishmess-server')

@app.get("/{access_type}&{token}")
def auth_and_refresh(access_type: str, token: str): 
    if access_type == "auth":
        data = {"isConnected": True, "refresh_token": token+"_refr"}
    elif access_type == "refr":
        data = {"chat_list": {}, "user_info": {}}
    
    return data

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