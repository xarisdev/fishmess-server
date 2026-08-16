import asyncio
import asyncpg
from asyncpg import Connection
from asyncpg.pool import Pool

import functools
from typing import Any, Callable

import data_models as models
from specials import HashManager

from logger import Path, setup_logger
from config import DATABASE_POOL_CREATE, DATABASE_USERS

logger = setup_logger(Path(__file__).name)

# ERRORS
class PoolNotInitializedError(Exception): ...

class UserNotVerifiedError(Exception): ...
class UserNotFoundError(Exception): ...

class ChatAlreadyExistsError(Exception): ...
class ChatNotFoundError(Exception): ...
class ChatCreateError(Exception): ...

class NetworkError(Exception): ...
class BadDataError(Exception): ...
class ForbiddenError(Exception): ...

def handle_db_errors(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)

        except asyncpg.PostgresError as exc:
            logger.error('PostgreSQL error', exc_info=exc)
            raise

        except asyncpg.UniqueViolationError as exc:
            logger.error('Key already exists', exc_info=exc)
            raise BadDataError('Key already exists') from exc

        except (asyncio.TimeoutError,
                asyncpg.PostgresConnectionError,
                asyncpg.ConnectionFailureError) as exc:
            logger.error('Network error', exc_info=exc)
            raise NetworkError(f'Network error: {exc}') from exc

    return wrapper

class DatabaseClient:
    def __init__(self):
        self.pool: Pool | None = None

    async def init_pool(self):
        logger.info('Wait to init pool..')

        delay = 1.0
        max_attempts = 5

        for attempt in range(1, max_attempts+1):
            try:
                self.pool = await asyncpg.create_pool(**DATABASE_POOL_CREATE)
                logger.info('Pool init successfully')
                return

            except asyncpg.PostgresError as exc:
                logger.error('PostgreSQL error', exc_info=exc)
                raise

            except (asyncio.TimeoutError,
                    asyncpg.PostgresConnectionError,
                    asyncpg.ConnectionFailureError) as exc:
                logger.warning(f'Network error, attempt {attempt}/{max_attempts}: {exc}')

                if attempt == max_attempts:
                    logger.error('All retry attempts failed')
                    raise NetworkError('Failed to retry connection')

                await asyncio.sleep(delay)
                delay *= 2

            except Exception as exc:
                logger.error("Unexpected error", exc_info=exc)
                raise

    def _ensure_pool(self):
        if self.pool is None or self.pool.is_closing():
            raise PoolNotInitializedError('Pool is not initialized or closed')

    async def transaction(self, coro, *args, **kwargs):
        self._ensure_pool()

        async with self.pool.acquire() as conn:
            conn: Connection
            async with conn.transaction():
                return await coro(conn, *args, **kwargs)

    @handle_db_errors
    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        self._ensure_pool()

        async with self.pool.acquire() as conn:
            conn: Connection
            return await conn.fetch(query, *args)

    @handle_db_errors
    async def fetchval(self, query: str, *args) -> Any:
        self._ensure_pool()

        async with self.pool.acquire() as conn:
            conn: Connection
            return await conn.fetchval(query, *args)

    @handle_db_errors
    async def fetchrow(self, query: str, *args) -> asyncpg.Record | None:
        self._ensure_pool()

        async with self.pool.acquire() as conn:
            conn: Connection
            return await conn.fetchrow(query, *args)    

    @handle_db_errors
    async def execute(self, query: str, *args) -> str:
        self._ensure_pool()

        async with self.pool.acquire() as conn:
            conn: Connection
            return await conn.execute(query, *args)

    async def close(self):
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info('Pool was closed')

# fastapi launch
client = DatabaseClient()
async def init_pool():
    await client.init_pool()
async def close_pool():
    await client.close()

#  USERS
async def verify_user(login: str, password: str) -> models.UserModel:
    logger.info(f'New request to `verify_user` from login: [{login}]')
    query = (
        "SELECT id, username, login, password_hash, avatar_id "
        "FROM users "
        "WHERE login = $1"
    )
    result = await client.fetchrow(query, login)

    if result:
        if HashManager.verify_key(password, result['password_hash']):
            user_model = models.UserModel(**result)
            logger.info(f'Login [{login}] was verified')
            return user_model
        else:
            error = f'Login [{login}] not verified'
            logger.error(error)
            raise UserNotVerifiedError(error)
    else:
        error = f'User with login [{login}] not found'
        logger.error(error)
        raise UserNotFoundError(error)

async def get_user_by_login(login: str) -> models.UserModel:
    query = ("SELECT id, username, login, avatar_id, status "
            "FROM users "
            "WHERE login = $1")
    
    result = await client.fetchrow(query, login)
    if not result:
        error = f'User ({login}) not found'
        logger.error(error)
        raise UserNotFoundError(error)

    logger.info(f'Found user ({login})')

    return models.UserModel(**result)

async def get_user_by_id(user_id: int) -> models.UserModel:
    logger.info(f'Search user for user_id: {user_id}')
    query = ("SELECT id, username, login, avatar_id, status "
            "FROM users "
            "WHERE id = $1")
    
    result = await client.fetchrow(query, user_id)
    if not result:
        error = f'User ({user_id}) not found'
        logger.error(error)
        raise UserNotFoundError(error)
    
    logger.info(f'Found user [{user_id}]')

    return models.UserModel(**result)

# FILES
# ----------------------------------------------------------------------------- Доделать
async def save_file(filename: str, filepath: str, user_id: int) -> int:
    query = ("INSERT INTO media (filename, path, user_id) "
            "VALUES ($1, $2, $3) "
            "RETURNING id")
    #media_id = await client.fetchval(query, filename, filepath, user_id)
    #if media_id:
    #    return media_id

async def get_file(file_id: int, user_id: int) -> models.FileModel:
    query = "SELECT * FROM media WHERE id = $1"
    #result = await client.fetchrow(query, file_id)
    #if result:
    #    if result['id'] != user_id:
    #        return 403
    #    model = models.FileModel(**result)
    #    return model
# -----------------------------------------------------------------------------

# CHATS
async def get_chats_by_user_id(user_id: int) -> list[models.ChatModel]:
    logger.info(f'Searching chats for user_id: {user_id}')
    query = (
        "WITH user_chats AS ("
            "SELECT id, avatar_id, name, first_user_id, second_user_id "
            "FROM chats "
            "WHERE first_user_id = $1 OR second_user_id = $2"
        ") "
        "SELECT "
            "chat.id, "
            "chat.avatar_id, "
            "chat.name, "
            "chat.first_user_id, "
            "chat.second_user_id, "
            "(SELECT text FROM messages WHERE chat_id = chat.id ORDER BY id DESC LIMIT 1) AS last_message "
        "FROM user_chats chat"
    )
    result = await client.fetch(query, user_id, user_id)
    
    logger.info(f'Found {len(result)} chats for user_id: {user_id}')

    return [models.ChatModel(**data) for data in result]

async def create_chat(chat_name: str, owner_id: int, reciever_id: int) -> models.ChatModel:
    logger.info(f'Create chat args: [{chat_name, owner_id, reciever_id}]')

    exists_check_query = (
        "SELECT id "
        "FROM chats "
        "WHERE "
            "(first_user_id = $1 AND second_user_id = $2) OR "
            "(first_user_id = $3 AND second_user_id = $4)"
    )
    
    _chat_exists = await client.fetchval(exists_check_query, owner_id, reciever_id, reciever_id, owner_id)
    if _chat_exists:
        error = 'Chat already exists'
        logger.error(error)
        raise ChatAlreadyExistsError(error)

    insert_query = ("INSERT INTO chats (name, first_user_id, second_user_id) "
                   "VALUES ($1, $2, $3) "
                   "RETURNING id")

    chat_id = await client.fetchval(insert_query, chat_name, owner_id, reciever_id)
    if not chat_id:
        error = 'Failed to create chat'
        logger.error(error)
        raise ChatCreateError(error)
    
    model = models.ChatModel(
        id=chat_id,
        name=chat_name,
        first_user_id=owner_id,
        second_user_id=reciever_id
    )

    logger.info(f'Chat: {chat_name}, created for ({owner_id}, {reciever_id})')

    return model

async def get_chat_by_id(chat_id: int, user_id: int) -> models.ChatModel:
    logger.info(f'Search chat with id: {chat_id}, request from user_id: {user_id}')
    query = ("SELECT * "
             "FROM chats "
             "WHERE id = $1")
    result = await client.fetchrow(query, chat_id)
    if not result:
        logger.error(f'Chat [{chat_id}] not found')
        raise ChatNotFoundError('Chat not found')

    chat = models.ChatModel(**result)
    if chat.first_user_id != user_id and chat.second_user_id != user_id:
        logger.error(f'User [{user_id}] not authorized for chat [{chat_id}]')
        raise ForbiddenError('Forbidden')

    logger.info(f'User [{user_id}] got chat [{chat_id}]')

    return chat

# MESSAGES
async def send_message(chat_id: int, owner_id: int, text: str) -> models.MessageModel:
    logger.info(f'Insert message in chat: {chat_id}, from user: {owner_id}')
    query = ("INSERT INTO messages (text, chat_id, owner_id) "
            "VALUES ($1, $2, $3) "
            "RETURNING id")

    msg_id = await client.fetchval(query, text, chat_id, owner_id)
    if not msg_id:
        error = 'Failed to insert message'
        logger.error(error)
        raise BadDataError(error)

    logger.info(f'Message: {msg_id}, insert in chat: {chat_id}, from user: {owner_id}')

    return models.MessageModel(
        id=msg_id,
        text=text,
        chat_id=chat_id,
        owner_id=owner_id
    )

async def get_messages(chat_id: int, limit: int) -> list[models.MessageModel]:
    logger.info(f'Get last {limit} messages from chat [{chat_id}]')
    query = ("SELECT * "
            "FROM messages "
            "WHERE chat_id = $1 "
            "LIMIT $2")

    result = await client.fetch(query, chat_id, limit)
    msg_models = [models.MessageModel(**msg) for msg in result]

    logger.info(f'Chat: {chat_id}, return {len(msg_models)} messages')

    return msg_models

async def _create_tables():
    users = ("CREATE TABLE IF NOT EXISTS users ("
        "id             SERIAL  PRIMARY KEY,"
        "username       TEXT    NOT NULL,"
        "login          TEXT    NOT NULL UNIQUE,"
        "password_hash  TEXT    NOT NULL,"
        "avatar_id      INT     REFERENCES media(id),"
        "status         TEXT    DEFAULT 'offline')"
    )
    media = ("CREATE TABLE IF NOT EXISTS media ("
        "id             SERIAL  PRIMARY KEY,"
        "filename       TEXT    NOT NULL,"
        "path           TEXT    NOT NULL)"
    )
    chats = ("CREATE TABLE IF NOT EXISTS chats ("
        "id             SERIAL  PRIMARY KEY,"
        "avatar_id      INT     REFERENCES media(id) DEFAULT NULL,"
        "name           TEXT    NOT NULL,"
        "first_user_id  INT     REFERENCES users(id),"
        "second_user_id INT     REFERENCES users(id))"
    )
    messages = ("CREATE TABLE IF NOT EXISTS messages ("
        "id             SERIAL  PRIMARY KEY,"
        "text           TEXT    NOT NULL,"
        "chat_id        INT     REFERENCES chats(id),"
        "owner_id       INT     REFERENCES users(id))"
    )
    chats_last_message_column = (
        "ALTER TABLE chats "
        "ADD COLUMN IF NOT EXISTS "
        "last_message_id INT REFERENCES messages(id) ON DELETE SET NULL"
    )
    media_user_id_column = (
        "ALTER TABLE media "
        "ADD COLUMN IF NOT EXISTS "
        "user_id INT REFERENCES users(id) ON DELETE SET NULL"
    )

    queries = [media, users, media_user_id_column, chats, messages, chats_last_message_column]

    async def _ctq(conn: Connection, queries):
        for q in queries:
            await conn.execute(q)

    logger.info('Create sql tables')
    await client.transaction(_ctq, queries)

async def _new_user(login: str, username: str, password_hash: str, avatar_id: int | None = None):
    logger.info(f'Registration user [{login}, {username}]')
    query = "INSERT INTO users (username, login, password_hash, avatar_id) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING"
    await client.execute(query, username, login, password_hash, avatar_id)

# Only in handle-init mode
async def main(handle_launch: bool = False):
    await client.init_pool()
    await _create_tables()
    if handle_launch:
        if input('reg? (y/n): ').lower() == 'y':
            for login, username, password in zip(*DATABASE_USERS):
                password_hash = HashManager.hash_key(password)
                await _new_user(login, username, password_hash)

# Handle-init
if __name__ == "__main__":
    logger.info('Main file startup mode')
    asyncio.run(main(handle_launch=True))