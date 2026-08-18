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
    await websockets_manager.shutdown()
    await db.close_pool()
    logger.info('Server shutdown complete')

# uvicorn main:app --reload --port 8000
app = FastAPI(title='fishmess-server', lifespan=lifespan)

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

    def create_session(self, access_token: str, user: db.models.UserModel):
        # Проверка на существование сессии
        login = user.login
        user_id = user.id
        
        if access_token in self.sessions:
            logger.info(f"Shutdown session for login: {login}")
            self.shutdown_session(access_token)

        self.sessions[access_token] = {'login': login,
                                       'user_id': user_id,
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

    def ws_user_id(self,
                   websocket: WebSocket,
                   authorization: Annotated[str | None, Header(...)] = None) -> int:
        
        if authorization is None:
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION,
                                     reason='Missing Authorization header')

        session = self.get_session(authorization)[1]
        user_id = session.get('user_id')

        return user_id

class WebSocketsManager:
    connections: dict[int, WebSocket] = {}
    notifications_wait_list: dict[int, list[dict]] = {}

    def get_utc_time(self) -> datetime:
        return datetime.now(timezone.utc)

    def notification_expired(self, time: datetime) -> bool:
        diff = self.get_utc_time() - time
        return diff.days >= 7

    async def connect(self, websocket: WebSocket, user_id: int):
        logger.info(f'--ws Connecting user_id: {user_id}')
        try: # Проверка на существование и активность соединения (поддержка 1 коннекта)
            conn = self.connections.get(user_id)
            conn.send_text('--ws-ping')
        except AttributeError:
            pass
        except WebSocketDisconnect as exc:
            logger.info(f'--ws Removed closed duplicate')
            del self.connections[user_id]

        self.connections[user_id] = websocket
        await websocket.accept()

        await websocket.send_text(f'WS://Connected to user_id: {user_id}')

        if user_id in self.notifications_wait_list:
            logger.info(f'--ws [{user_id}] Released wait list..')
            nlist = self.notifications_wait_list.get(user_id)
            await self.release_notifications(user_id, nlist)

    async def disconnect(self, websocket: WebSocket, user_id: int):
        logger.info(f'--ws Disconnecting user_id: {user_id}')
        try:
            await websocket.close()
            del self.connections[user_id]
        except KeyError:
            pass
        except Exception as exc:
            logger.error('--ws Unexpected error while disconnect', exc_info=exc)
            return
        logger.info(f'--ws User [{user_id}] disconnected')

    async def shutdown(self):
        logger.info('--ws Shutdown connections..')
        for user_id, connection in self.connections.items():
            logger.debug(f'--ws Shutdown {user_id}..')
            await connection.close(reason='Server shutdown')
        self.connections.clear()
        logger.info('--ws Shutdown complete')

    async def send_notification(self, reciever_id: int, send_type: str, message: str = '', details: Any = None):
        reciever = self.connections.get(reciever_id)

        json_data = {
            'datetime_utc': self.get_utc_time().isoformat(),
            'type': send_type,
            'data': {
                'message': message,
                'details': details
            }
        }

        try:
            await reciever.send_json(data=json_data)
            logger.info(f'--ws Send notification to user: {reciever_id}')
            return
        except AttributeError as exc:
            pass
        except WebSocketDisconnect as exc:
            logger.error(f'--ws connection closed')

        nlist = self.notifications_wait_list.get(reciever_id)
        nlist = nlist if nlist else []
        nlist.append(json_data)
        self.notifications_wait_list[reciever_id] = nlist
        logger.info('--ws Add notification to wait list')

    async def release_notifications(self, user_id: int, nlist: list[dict[str, Any]]):
        reciever = self.connections.get(user_id)
        if not reciever:
            logger.error('No connection to reciever')
            raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION,
                                     reason='No connection to reciever')
        
        for n in nlist:
            ntime = n.get('datetime_utc')
            if self.notification_expired(datetime.fromisoformat(ntime)):
                logger.info(f'Notification ({ntime}) expired')
                continue

            await reciever.send_json(data=n)

        self.notifications_wait_list.pop(user_id, None)

access_manager = AccessManager() # Временное хранилище сессий доступа
websockets_manager = WebSocketsManager()

#file_manager = FileManager() # Работа с файлами

# Обработчики ошибок БД
@app.exception_handler(db.BadDataError)
@app.exception_handler(db.ChatCreateError)
async def bad_data_error(request, exc):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

@app.exception_handler(db.UserNotVerifiedError)
async def user_not_verified_error(request, exc):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

@app.exception_handler(db.ForbiddenError)
async def forbidden_error(request, exc):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

@app.exception_handler(db.UserNotFoundError)
@app.exception_handler(db.ChatNotFoundError)
async def user_not_found_error_handler(request, exc):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

@app.exception_handler(db.ChatAlreadyExistsError)
async def chat_already_exists_error(request, exc):
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

@app.exception_handler(db.NetworkError)
@app.exception_handler(db.PoolNotInitializedError)
async def network_error_handler(request, exc):
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


# вебсок
@app.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, user_id: Annotated[int, Depends(access_manager.ws_user_id)]):
    await websockets_manager.connect(websocket, user_id)

    try: # переписать мб, мне не нрав
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    finally:
        await websockets_manager.disconnect(websocket, user_id)

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

    user = await db.verify_user(login, password)
    
    access_token = HashManager.generate_token()
    access_manager.create_session(access_token, user)
    
    response = wmd.LoginResponse(access_token=access_token)
    return response

@app.get("/users/me", response_model=wmd.UserResponse)
async def get_current_user(authorization: str = Header(...)):
    _, session = access_manager.get_session(authorization)
    user_id = session.get('user_id')

    user = await db.get_user_by_id(user_id)

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
    user_id = session.get('user_id')

    chats = await db.get_chats_by_user_id(user_id)

    response = wmd.ChatsGetResponse(chats_count=len(chats), data=chats)
    return response

@app.post("/chats", response_model=wmd.ChatsPostResponse)
async def post_chats(request: wmd.ChatsPostRequest, authorization: str = Header(...)):
    _, session = access_manager.get_session(authorization)
    user_id = session.get('user_id')

    chat_name = request.name
    to_user_id = request.to_user_id

    if not chat_name or not to_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Bad Request")

    chat_model = await db.create_chat(chat_name, user_id, to_user_id)

    response = wmd.ChatsPostResponse(data=chat_model)
    return response

# Отправка сообщения в чат
@app.post("/chats/{chat_id}/messages", response_model=wmd.MessagesPostResponse)
async def post_message(chat_id: int, request: wmd.MessagesPostRequest, authorization: str = Header(...)):
    _, session = access_manager.get_session(authorization)
    user_id = session.get('user_id')

    text = request.text
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Bad Request")

    user = await db.get_user_by_id(user_id)
    
    message_model = await db.send_message(chat_id, user.id, text)
    # Уведомление второй стороны о сообщении
    # Подумать как хочу это видеть в будущем и не забываем про права доступа в БД (вписаны)
    chat_model = await db.get_chat_by_id(message_model.chat_id, user.id)
    users_id = [chat_model.first_user_id, chat_model.second_user_id]
    for uid in users_id:
        if uid == user.id:
            continue
        await websockets_manager.send_notification(reciever_id=uid,
                                                   send_type='chat',
                                                   details=message_model.model_dump())

    response = wmd.MessagesPostResponse(data=message_model)
    return response

# Получение списка сообщений
@app.get("/chats/{chat_id}/messages", response_model=wmd.MessagesGetResponse)
async def get_messages(chat_id: int, limit: int = 50, authorization: str = Header(...)):
    _, session = access_manager.get_session(authorization)
    user_id = session.get('user_id')
    
    messages = await db.get_messages(user_id, chat_id, limit)

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