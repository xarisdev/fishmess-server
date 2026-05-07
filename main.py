import logging
logging.basicConfig(
    level=logging.INFO,
    filename="server.log",
    filemode="w", # "a"
    format="%(asctime)s %(levelname)s %(message)s"
)

import db
import web_models as wmd

from typing import Annotated
from specials import HashManager

from fastapi import (
    FastAPI, HTTPException,
    Request, Header, Depends, status,
    File, UploadFile,
    WebSocket, WebSocketDisconnect, WebSocketException
)

# Для запуска сервера: uvicorn main:app --reload --port 8000
app = FastAPI(title='fishmess-server')
# Обработчик WebSocket соединений
class ClientsManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, login: str, websocket: WebSocket):
        self.active_connections[login] = websocket
        await websocket.accept()

    def disconnect(self, login: str = None) -> WebSocket:
        connection = self.active_connections.pop(login)
        return connection

    async def send_personal_message(self, message: str, login: str):
        connection = await self.active_connections.get(login)
        if connection:
            await connection.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

# Хранилище сессий доступа
class AccessManager:
    sessions: dict[str, str] = {}

    def _extract_access_token(self, authorization: str) -> str:
        if not authorization:
            logging.warning(f"Not found 'Authorization' header | Finding: {authorization}")
            raise HTTPException(
                status_code=401,
                detail="Authorization header missing or invalid"
            )
        access_token = authorization.split(' ')[1]
        return access_token

    def create_session(self, access_token: str, login: str):
        self.sessions[access_token] = login
        logging.info(f"Session created for login: {login}")

    def get_login(self, authorization: str) -> str:
        try:
            access_token = self._extract_access_token(authorization)
            login = self.sessions.get(access_token)
            if not login:
                logging.info(f"Not found user for access_token")
                raise HTTPException(
                    status_code=401,
                    detail="Invalid access token"
                )
            logging.info(f"Access authorization for {login} with access_token")
            return login
        except HTTPException as exc:
            pass
        except Exception as exc:
            logging.error("Critical authorization error", exc_info=True)
    
    def remove_session(self, access_token: str) -> str | None:
        if access_token in self.sessions:
            login = self.sessions.pop(access_token)
            if login:
                logging.info(f"Removed session for {login}")
                return login
            logging.info(f"Session not found")
        else:
            logging.info(f"Session not exists for access_token")

    def ws_depends(self, websocket: WebSocket, authorization: Annotated[str | None, Header(...)] = None):
        if authorization is None:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
        login = self.get_login(authorization)
        return login

access_manager = AccessManager() # Временное хранилище сессий доступа
clients_manager = ClientsManager() # Временное хранилище websocket клиентов

@app.websocket("/ws/broadcast")
async def websocket_endpoint(websocket: WebSocket, login: Annotated[str, Depends(access_manager.ws_depends)]):
    await clients_manager.connect(login, websocket)

    data = await websocket.receive_text() # Тесты
    print(data)

    await websocket.send_text(f"Session by login {login}")

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
    access_manager.create_session(access_token, login)
    
    response = {"access_token": access_token}
    return response

@app.get("/users/me", response_model=wmd.UserResponse)
async def get_current_user(authorization: str = Header(...)):
    login = access_manager.get_login(authorization)

    user = db.get_user_by_login(login)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    response = {"data": user}
    return response

@app.get("/users/{user_id}", response_model=wmd.UserResponse)
async def get_user_by_id(user_id: int, authorization: str = Header(...)):
    _login = access_manager.get_login(authorization)
    
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    response = {"data": user}
    return response

@app.get("/chats", response_model=wmd.ChatsGetResponse)
async def get_chats(authorization: str = Header(...)):
    login = access_manager.get_login(authorization)

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
async def post_chats(request: wmd.ChatsPostRequest, authorization: str = Header(...)):
    login = access_manager.get_login(authorization)

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
async def post_message(chat_id: int, request: wmd.MessagesPostRequest, authorization: str = Header(...)):
    login = access_manager.get_login(authorization)

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
async def get_messages(chat_id: int, limit: int = 50, authorization: str = Header(...)):
    login = access_manager.get_login(authorization)

    user = db.get_user_by_login(login)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    messages = db.get_messages(chat_id, limit)
    response = {
        "messages_count": len(messages),
        "data": messages
    }
    return response
""" Заготовка под файлы
@app.post("/file", response_model=wmd.)
async def post_file(request = wmd., authorization: str = Header(...)):
    pass

@app.get("/file/{file_id}", response_model=wmd.)
async def get_file(file_id: int, authorization: str = Header(...)):
    login = access_manager.get_login(authorization)

    if not file_id:
        raise HTTPException(status_code=400, detail="Bad Request")
"""