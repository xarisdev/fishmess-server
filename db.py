from os import getenv
from dotenv import load_dotenv

load_dotenv('.env')

NAME     = getenv('DATABASE_NAME')
HOST     = getenv('DATABASE_HOST')
USER     = getenv('DATABASE_USER')
PORT     = getenv('DATABASE_PORT')
PASSWORD = getenv('DATABASE_PASS')

from typing import Any
from datetime import datetime as dt

import asyncio
import asyncpg
from asyncpg import Connection
from asyncpg.pool import Pool

import db_models as models
from specials import HashManager

class DataBaseClass:
    def __init__(self):
        self.pool: Pool | None = None

    async def init_pool(self):
        self.pool = await asyncpg.create_pool(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=NAME,
            min_size=1,
            max_size=5,
            command_timeout=60
        )
    async def fetch(self, query: str, *args) -> list[asyncpg.Record]:
        # --------------------------------------------------------------------- Нужен логгер + проброска httpexception наверх
        if self.pool is None:
            print('Pool is None')
            return
        async with self.pool.acquire() as conn:
            conn: Connection
            try:
                async with conn.transaction():
                    return await conn.fetch(query, *args)
            except asyncpg.PostgresError as e:
                print(f'Error {e}')
    async def fetchval(self, query: str, *args) -> asyncpg.Record | None:
        # --------------------------------------------------------------------- Нужен логгер + проброска httpexception наверх
        if self.pool is None:
            print('Pool is None')
            return
        async with self.pool.acquire() as conn:
            conn: Connection
            try:
                async with conn.transaction():
                    return await conn.fetchval(query, *args)
            except asyncpg.PostgresError as e:
                print(f'Error {e}')
    async def fetchrow(self, query: str, *args) -> Any:
        # --------------------------------------------------------------------- Нужен логгер + проброска httpexception наверх
        if self.pool is None:
            print('Pool is None')
            return
        async with self.pool.acquire() as conn:
            conn: Connection
            try:
                async with conn.transaction():
                    return await conn.fetchrow(query, *args)
            except asyncpg.PostgresError as e:
                print(f'Error {e}')
    async def execute(self, query: str, *args) -> str:
        # --------------------------------------------------------------------- Нужен логгер + проброска httpexception наверх
        if self.pool is None:
            print('Pool is None')
            return
        async with self.pool.acquire() as conn:
            conn: Connection
            try:
                async with conn.transaction():
                    return await conn.execute(query, *args)
            except asyncpg.PostgresError as e:
                print(f'Error {e}')

    async def close(self):
        if self.pool:
            await self.pool.close()

class DataBaseError:
    def __init__(self):
        pass


db = DataBaseClass()


# USER
async def verify_user(login: str, password: str) -> models.UserModel | None:
    query = "SELECT id, username, login, password_hash, avatar_id " \
            "FROM users " \
            "WHERE login = $1"
    result = await db.fetchrow(query, login)
    print(result)
    if result:
        if HashManager.verify_key(password, result['password_hash']):
            user_model = models.UserModel(**result)
            return user_model # Standart response
        else:
            return # Verify error
    else:
        return # data errror

async def get_user_by_login(login: str) -> models.UserModel | None:
    query = "SELECT id, username, login, avatar_id, status " \
            "FROM users " \
            "WHERE login = $1"
    result = await db.fetchrow(query, login)
    if result:
        user_model = models.UserModel(**result)
        return user_model
    else:
        return # data error

async def get_user_by_id(user_id: int) -> models.UserModel | None:
    query = "SELECT id, username, login, avatar_id, status " \
            "FROM users " \
            "WHERE id = $1"
    result = await db.fetchrow(query, user_id)
    if result:
        user_model = models.UserModel(**result)
        return user_model
    else:
        return # data error


# MEDIA
async def save_file(filename: str, filepath: str, user_id: int) -> int:
    query = "INSERT INTO media (filename, path, user_id) " \
            "VALUES ($1, $2, $3) " \
            "RETURNING id"
    result = await db.fetchval(query, filename, filepath, user_id)
    if result:
        #media_id = result['id']
        media_id = result # Проверить
        return media_id

async def get_file(file_id: int, user_id: int) -> models.FileModel:
    query = "SELECT * FROM media WHERE id = $1"
    result = await db.fetchrow(query, file_id)
    if result:
        if result['id'] != user_id:
            return 403
        model = models.FileModel(**result)
        return model


# CHATS
async def get_chats_by_user_id(user_id: int) -> list[models.ChatModel]:
    query = """
        WITH user_chats AS (
            SELECT id, avatar_id, name, first_user_id, second_user_id
            FROM chats
            WHERE first_user_id = %s OR second_user_id = %s
        )
        SELECT
            chat.id,
            chat.avatar_id,
            chat.name,
            chat.first_user_id,
            chat.second_user_id,
            (SELECT text FROM messages WHERE chat_id = chat.id ORDER BY id DESC LIMIT 1) AS last_message
        FROM user_chats chat
    """
    result = await db.fetch(query, user_id, user_id)
    if result:
        return [models.ChatModel(**data) for data in result]
    else:
        return # chats not found


##########################
##########################
##########################
async def create_chat(chat_name: str, owner_id: int, reciever_id: int) -> models.ChatModel:
#   # exists checking
    exists_check_query = "SELECT id " \
                         "FROM chats " \
                         "WHERE " \
                            "(first_user_id = $1 AND second_user_id = $2) OR " \
                            "(first_user_id = $3 AND second_user_id = $4)"
    result = await db.fetchval(exists_check_query, owner_id, reciever_id, reciever_id, owner_id)
    if result:
        error_message = (400, 'Bad Request: Chat already exists')
        return error_message # 400
    # create
    insert_query = "INSERT INTO chats (name, first_user_id, second_user_id) " \
                   "VALUES ($1, $2, $3) " \
                   "RETURNING id"
    chat_id = await db.fetchval(insert_query, chat_name, owner_id, reciever_id)
    if chat_id:
        model = models.ChatModel(
            id=chat_id,
            name=chat_name,
            first_user_id=owner_id,
            second_user_id=reciever_id
        )
        return model

async def send_message(chat_id: int, owner_id: int, text: str) -> models.MessageModel:
    query = "INSERT INTO messages (text, chat_id, owner_id) " \
            "VALUES ($1, $2, $3) " \
            "RETURNING id"
    # ------------------------------------------------------------------------- Исправить
    msg_id = await db.fetchval(query, text, chat_id, owner_id)
    if msg_id:
        model = models.MessageModel(
            id=msg_id,
            text=text,
            chat_id=chat_id,
            owner_id=owner_id
        ) 
        return model
    # -------------------------------------------------------------------------

# ----------------------------------------------------------------------------- Добавить лимиты в SQL запрос
async def get_messages(chat_id: int, limit: int) -> list[models.MessageModel]:
    query = "SELECT * " \
            "FROM messages " \
            "WHERE chat_id = $1"
    result = await db.fetch(query, chat_id)
    if result:
        messages = result[:limit] # Говнокод
        msg_models = [models.MessageModel(**msg) for msg in messages]
        return msg_models
# -----------------------------------------------------------------------------

# STARTUP
async def _create_tables():
    users = "CREATE TABLE IF NOT EXISTS users (" \
        "id             SERIAL  PRIMARY KEY," \
        "username       TEXT    NOT NULL," \
        "login          TEXT    NOT NULL UNIQUE," \
        "password_hash  TEXT    NOT NULL," \
        "avatar_id      INT     REFERENCES media(id)," \
        "status         TEXT    DEFAULT 'offline'" \
    ")"
    media = "CREATE TABLE IF NOT EXISTS media (" \
        "id             SERIAL  PRIMARY KEY," \
        "filename       TEXT    NOT NULL," \
        "path           TEXT    NOT NULL" \
    ")"
    chats = "CREATE TABLE IF NOT EXISTS chats (" \
        "id             SERIAL  PRIMARY KEY," \
        "avatar_id      INT     REFERENCES media(id) DEFAULT NULL," \
        "name           TEXT    NOT NULL," \
        "first_user_id  INT     REFERENCES users(id)," \
        "second_user_id INT     REFERENCES users(id)" \
    ")"
    messages = "CREATE TABLE IF NOT EXISTS messages (" \
        "id             SERIAL  PRIMARY KEY," \
        "text           TEXT    NOT NULL," \
        "chat_id        INT     REFERENCES chats(id)," \
        "owner_id       INT     REFERENCES users(id)" \
    ")"
    chats_last_message_column = "ALTER TABLE chats ADD COLUMN IF NOT EXISTS " \
        "last_message_id INT REFERENCES messages(id) ON DELETE SET NULL"
    media_alter = "ALTER TABLE media ADD COLUMN IF NOT EXISTS " \
        "user_id INT REFERENCES users(id) ON DELETE SET NULL"

    query_list = [media, users, media_alter, chats, messages, chats_last_message_column]
    for q in query_list:
        result = await db.execute(q)
        if result: print(result)

# Добавление пользователя
async def _new_user(login: str, username: str, password_hash: str, avatar_id: int | None = None):
    query = "INSERT INTO users (username, login, password_hash, avatar_id) VALUES ($1, $2, $3, $4)"
    result = await db.execute(query, username, login, password_hash, avatar_id)

async def main(hand_launch: bool = False):
    await db.init_pool()
    await _create_tables()
    if hand_launch:
        if input('reg? (y/n): ').lower() == 'y':
            load_dotenv('access.env')
            LOGINS     = getenv('LOGINS').split(' ')
            USERNAMES  = getenv('USERNAMES').split(' ')
            PASSWORDS  = getenv('PASSWORDS').split(' ')
            for login, username, password in zip(LOGINS, USERNAMES, PASSWORDS):
                password_hash = HashManager.hash_key(password)
                await _new_user(login, username, password_hash)
    # ------------------------------------------------------------------------- Проверка на существование таблиц
    else:
        pass
    # -------------------------------------------------------------------------

# Ручной запуск
if __name__ == "__main__":
    asyncio.run(main(hand_launch=True))