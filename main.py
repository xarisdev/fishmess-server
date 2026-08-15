import asyncio

from typing import Annotated, Any

from datetime import datetime, timezone, timedelta

from contextlib import asynccontextmanager

from fastapi import (FastAPI, HTTPException, Request, status,
                     Header, Depends, File,
                     UploadFile,
                     WebSocket, WebSocketDisconnect, WebSocketException)
from fastapi.responses import FileResponse

import db
import web_models as wmd

from logger import Path, setup_logger
from specials import HashManager, FileManager

logger = setup_logger(Path(__file__).name)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Server startup')
    await db.init_pool()
    yield
    await db.close_pool()
    logger.info('Server shutdown complete')

# uvicorn main:app --reload --port 8000
app = FastAPI(title='fishmess-server', lifespan=lifespan)

"""# Обработчик WebSocket соединений
class ClientsManager:
    def __init__(self):
        self._lock = asyncio.Lock()

        self.active_connections: dict[str, WebSocket] = {}

    def _get_conn_by_login(self, login: str, rm: bool = False) -> WebSocket | None:
        if rm: websocket = self.active_connections.pop(login, None)
        else: websocket = self.active_connections.get(login)
        return websocket

    async def connect(self, websocket: WebSocket, login: str):
        async with self._lock:    
            ws = self._get_conn_by_login(login, True)
            if ws is not None:
                logger.info(f"WebSocket connection for login: {login} already exists. Wait to close..")
                await self.close_connection(ws)
            try:
                await websocket.accept()
                self.active_connections[login] = websocket
                logger.info(f"Accept new WebSocket connection for login: {login}")
            except Exception as exc:
                logger.error(f"Accept error WS for login: {login}", exc_info=exc)
                raise WebSocketException(code=status.WS_1014_BAD_GATEWAY)

    async def close_connection(self, websocket: WebSocket | None = None):
        try:
            await websocket.close()
            logger.info(f"Succes close weboscket connection")
        except Exception as exc:
            logger.error(f"Can't close websocket connection", exc_info=exc)
            raise WebSocketException(code=status.WS_1011_INTERNAL_ERROR)"""

# Хранилище сессий доступа
class AccessManager:
    # access_token: {'login': str, 'is_active': bool, 'expired_at': timestamp}
    sessions: dict[str, dict[str, Any]] = {}

    def set_expired_at(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(minutes=30)
    
    def is_token_available(self, expired_at: datetime, is_active: bool) -> bool:
        return is_active and expired_at > datetime.now(timezone.utc)

    def _extract_access_token(self, authorization: str) -> str:
        if not authorization: # header
            logger.warning("Missing|Invalid 'Authorization' header")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Missing Authorization header ')

        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Invalid Authorization header')
        return parts[1]

    def refresh_session(self, old_token: str, new_token: str):
        if new_token in self.sessions:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail='Data conflict, please retry')
        
        old_session = self.sessions.pop(old_token, None)
        if not old_session:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Session not found')

        if not self.is_token_available(old_session['expired_at'], old_session['is_active']):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Access token expired or revoked')

        old_session['is_active'] = True
        old_session['expired_at'] = self.set_expired_at()
        self.sessions[new_token] = old_session
        logger.info(f'Session refreshed {old_token[:5]}... -> {new_token[:5]}...')

    def create_session(self, access_token: str, login: str):
        # Проверка на существование сессии
        if access_token in self.sessions:
            logger.info(f"Shutdown session for login: {login}")
            self.shutdown_session(access_token)

        self.sessions[access_token] = {'login': login,
                                       'is_active': True,
                                       'expired_at': self.set_expired_at()}
        logger.info(f"New session for login: {login}")

    def get_session(self, authorization: str) -> tuple[str, dict[str, Any]]:
        access_token = self._extract_access_token(authorization)
        session = self.sessions.get(access_token)

        if session:
            expired_at = session.get('expired_at')

            if self.is_token_available(expired_at, session['is_active']):
                return (access_token, session)
            else:
                self.sessions.pop(access_token)

                logger.warning(f'Access token expired: {access_token[:5]}...')
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail='Access token expired')
            
        logger.warning(f'Invalid access token: {access_token[:5]}...')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Invalid access token')

    def shutdown_session(self, access_token: str):
        session = self.sessions.get(access_token)
        if session:
            session['is_active'] = False
            logger.info(f'Session {access_token[:5]}... was terminated')
        else:
            logger.warning(f'Session {access_token[:5]}... not exists')

#    def ws_depends(self, websocket: WebSocket, authorization: Annotated[str | None, Header(...)] = None):
#        if authorization is None:
#            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
#        login = self.get_login(authorization)
#        return login

access_manager = AccessManager() # Временное хранилище сессий доступа
#clients_manager = ClientsManager() # Временное хранилище websocket клиентов
#file_manager = FileManager() # Работа с файлами

# Обработчики ошибок БД
@app.exception_handler(db.BadDataError)
@app.exception_handler(db.ChatCreateError)
async def bad_data_error(request, exc):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

@app.exception_handler(db.NetworkError)
@app.exception_handler(db.PoolNotInitializedError)
async def network_error_handler(request, exc):
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))

@app.exception_handler(db.UserNotFoundError)
async def user_not_found_error_handler(request, exc):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

@app.exception_handler(db.UserNotVerifiedError)
async def user_not_verified_error(request, exc):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

@app.exception_handler(db.ChatAlreadyExistsError)
async def chat_already_exists_error(request, exc):
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

# вебсок
#@app.websocket("/ws/pp")
#async def websocket_endpoint(websocket: WebSocket, login: Annotated[str, Depends(access_manager.ws_depends)]):
#    await clients_manager.connect(websocket, login)
#    websocket.send_text("ping <-> pong")

# Роуты
# Обновление токена
@app.post("/auth/refresh_token", response_model=wmd.LoginResponse)
async def refresh_token(authorization: str = Header(...)):
    access_token, _ = access_manager.get_session(authorization)

    new_token = HashManager.generate_token()
    access_manager.refresh_session(access_token, new_token)

    response = wmd.LoginResponse(access_token=new_token)
    return response

# Аутентификация пользователя
@app.post("/auth/login", response_model=wmd.LoginResponse)
async def login(request: wmd.LoginRequest):
    login = request.login
    password = request.password
    if not login or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad Request"
        )

    user = await db.verify_user(login, password) # --- Удалить возврат
    
    access_token = HashManager.generate_token()
    access_manager.create_session(access_token, login)
    
    response = wmd.LoginResponse(access_token=access_token)
    return response

@app.get("/users/me", response_model=wmd.UserResponse)
async def get_current_user(authorization: str = Header(...)):
    _, session = access_manager.get_session(authorization)

    user = await db.get_user_by_login(session.get('login'))

    response = wmd.UserResponse(data=user)
    return response

@app.get("/users/{user_id}", response_model=wmd.UserResponse)
async def get_user_by_id(user_id: int, authorization: str = Header(...)):
    _, _ = access_manager.get_session(authorization)
    
    user = await db.get_user_by_id(user_id)
    
    response = wmd.UserResponse(data=user)
    return response

@app.get("/chats", response_model=wmd.ChatsGetResponse)
async def get_chats(authorization: str = Header(...)):
    _, session = access_manager.get_session(authorization)

    user = await db.get_user_by_login(session.get('login'))
    
    chats = await db.get_chats_by_user_id(user.id)
    # ?...

    response = wmd.ChatsGetResponse(chats_count=len(chats), data=chats)
    return response

@app.post("/chats", response_model=wmd.ChatsPostResponse)
async def post_chats(request: wmd.ChatsPostRequest, authorization: str = Header(...)):
    _, session = access_manager.get_session(authorization)

    chat_name = request.name
    to_user_id = request.to_user_id

    if not chat_name or not to_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Bad Request")
    # Исключение создания чата с несуществующим пользователем (внедрить в БД)
    # БД вызовет ошибку если нет одного из пользователей
    ## ------------------------------------------------------------------------
    owner_user_model = await db.get_user_by_login(session.get('login')) # Тот кто создает
    owner_id = owner_user_model.id
    reciever_user_model = await db.get_user_by_id(to_user_id) # Второй участник
    reciever_id = reciever_user_model.id

    if not owner_id or not reciever_id: # Вынести излишки* логики в db.create_chat
        print(f'Data error: owid - {owner_id} || rcid - {reciever_id}')

    chat_model = await db.create_chat(chat_name, owner_id, reciever_id)
    ## ------------------------------------------------------------------------
    response = wmd.ChatsPostResponse(data=chat_model)
    return response

# Отправка сообщения в чат
@app.post("/chats/{chat_id}/messages", response_model=wmd.MessagesPostResponse)
async def post_message(chat_id: int, request: wmd.MessagesPostRequest, authorization: str = Header(...)):
    _, session = access_manager.get_session(authorization)

    text = request.text
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Bad Request")

    user = await db.get_user_by_login(session.get('login'))
    
    message_model = await db.send_message(chat_id, user.id, text)

    response = wmd.MessagesPostResponse(data=message_model)
    return response

# Получение списка сообщений
@app.get("/chats/{chat_id}/messages", response_model=wmd.MessagesGetResponse)
async def get_messages(chat_id: int, limit: int = 50, authorization: str = Header(...)):
    _, session = access_manager.get_session(authorization)

    user = await db.get_user_by_login(session.get('login')) # --- Удалить возврат
    
    messages = await db.get_messages(chat_id, limit)

    response = wmd.MessagesGetResponse(messages_count=len(messages),
                                       data=messages)
    return response

"""
# Отправка файла (серверу)
@app.post("/file")
async def post_file(file: UploadFile = File, authorization: str = Header(...)):
    login = access_manager.get_login(authorization)
    user = await db.get_user_by_login(login)

    if not file:
        raise HTTPException(status_code=400, detail="Bad Request")

    result= file_manager.save(file)
    if result[0] == 201:
        _code, _info, _path = result 
        file_id = await db.save_file(file.filename, _path, user.id)

        return {"info": _info, "file_id": file_id}
# Получение файла (клиент)
@app.get("/file/{file_id}")
async def get_file(file_id: int, authorization: str = Header(...)):
    login = access_manager.get_login(authorization)
    user = await db.get_user_by_login(login)

    file_model = await db.get_file(file_id, user.id)
    if file_model == 403:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "code": 403,
                    "message": "Forbidden",
                    "details": {},
                    "timestamp": dt.timestamp()
                }
            }
        )
    result = file_manager.load(file_model)
    if isinstance(result, tuple):
        raise HTTPException(
            status_code=result[0],
            detail=result[1]
        )
    return result
@app.delete("/file/{file_id}")
async def delete_file(file_id: int, authorization: str = Header(...)):
    _login = access_manager.get_login(authorization)
    
    if not file_id:
        HTTPException(status_code=400, detail="Bad Request")

    # Поиск файла из бд
    # Удаление записи в бд
"""