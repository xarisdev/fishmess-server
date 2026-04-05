from os import getenv
from dotenv import load_dotenv

import psycopg2 as pc2

from specials import handle_db_errors
"""
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_api_key(plain_key: str) -> str: return pwd_context.hash(plain_key)
def verify_api_key(plain_key: str, hashed_key: str) -> bool: return pwd_context.verify(plain_key, hashed_key)
"""
load_dotenv('.env')
#load_dotenv('access.env')

DATABASE_NAME=getenv('DATABASE_NAME')
DATABASE_HOST=getenv('DATABASE_HOST')
DATABASE_USER=getenv('DATABASE_USER')
DATABASE_PASS=getenv('DATABASE_PASS')
DATABASE_PORT=getenv('DATABASE_PORT')

def get_connection():
    conn = pc2.connect(
        dbname=DATABASE_NAME,
        host=DATABASE_HOST,
        user=DATABASE_USER,
        password=DATABASE_PASS,
        port=DATABASE_PORT
    )
    conn.autocommit = True
    return conn

def create_tables():
    conn = get_connection()

    refresh_tokens = "CREATE TABLE IF NOT EXISTS refresh_tokens (" \
        "user_tag        VARCHAR(32) PRIMARY KEY REFERENCES users(tag) ON DELETE CASCADE," \
        "access_token    VARCHAR(128) NOT NULL UNIQUE," \
        "refresh_token   VARCHAR(128) PRIMARY KEY NULL UNIQUE," \
        "created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP," \
        "updated_at      TIMESTAMP," \
        "expiread_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP + INTERVAL '7 days'" \
    ")"
    users = "CREATE TABLE IF NOT EXISTS users (" \
        "id              BIGSERIAL PRIMARY KEY," \
        "tag             VARCHAR(32) PRIMARY KEY NOT NULL," \
        "name            VARCHAR(128) NOT NULL," \
        "avatar_id       BIGINT NULL REFERENCES media(id) ON DELETE SET NULL," \
        "created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP," \
        "updated_at      TIMESTAMP" \
    ")"
    media = "CREATE TABLE IF NOT EXISTS media (" \
        "id              BIGSERIAL PRIMARY KEY," \
        "type            VARCHAR(20) NOT NULL," \
        "url             TEXT NOT NULL," \
        "size            BIGINT," \
        "mime_type       VARCHAR(100)," \
        "width           INT," \
        "height          INT," \
        "duration        INT," \
        "created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP" \
    ")"
    chats = "CREATE TABLE IF NOT EXISTS chats (" \
        "id              BIGSERIAL PRIMARY KEY," \
        "type            VARCHAR(20) NOT NULL," \
        "name            VARCHAR(128) NULL," \
        "created_by      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE," \
        "created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP," \
        "updated_at      TIMESTAMP" \
    ")"
    chat_members = "CREATE TABLE IF NOT EXISTS chat_members (" \
        "chat_id         BIGINT NOT NULL REFERENCES chats(id) ON DELETE CASCADE," \
        "user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE," \
        "joined_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP," \
        "left_at         TIMESTAMP NULL," \
        "PRIMARY KEY (chat_id, user_id)" \
    ")"
    messages = "CREATE TABLE IF NOT EXISTS messages (" \
        "id BIGSERIAL    PRIMARY KEY," \
        "chat_id         BIGINT NOT NULL REFERENCES chats(id) ON DELETE CASCADE," \
        "sender_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE SET NULL," \
        "reply_to_id     BIGINT NULL REFERENCES messages(id) ON DELETE CASCADE," \
        "text            TEXT NULL," \
        "is_deleted      BOOLEAN DEFAULT FALSE," \
        "created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP," \
        "updated_at      TIMESTAMP NULL," \
        "deleted_at      TIMESTAMP NULL" \
    ")"
    messages_media = "CREATE TABLE IF NOT EXISTS message_media (" \
        "message_id      BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE," \
        "media_id        BIGINT NOT NULL REFERENCES media(id) ON DELETE CASCADE," \
        "PRIMARY KEY (message_id, media_id)" \
    ")"
    messages_read = "CREATE TABLE IF NOT EXISTS message_reads (" \
        "message_id      BIGINT NOT NULL REFERENCES messages(id) ON DELETE CASCADE," \
        "user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE," \
        "read_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP," \
        "PRIMARY KEY (message_id, user_id)" \
    ")"

    try:
        with conn.cursor() as cursor:
            cursor.execute(media)
            cursor.execute(users)
            cursor.execute(refresh_tokens) # access/refresh tokens reference users table
            cursor.execute(chats)
            cursor.execute(messages)
            cursor.execute( # need messages table for last_message_id reference
                "ALTER TABLE chats ADD COLUMN IF NOT EXISTS" \
                " last_message_id BIGINT NULL REFERENCES messages(id) ON DELETE SET NULL"
            )
            cursor.execute(chat_members)
            cursor.execute(messages_media)
            cursor.execute(messages_read)
            # index
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_members_user_id ON chat_members(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_reads_user ON message_reads(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chats_last_message_id ON chats(last_message_id)")
    except Exception as exc:
        print(exc)
        conn.rollback()
    finally:
        conn.close() # autocommit

@handle_db_errors # САМОСТОЯТЕЛЬНАЯ ФУНКЦИЯ
def create_user(tag: str, name: str, avatar_id: int = None, hashed_key: str = None) -> int:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (tag, name, avatar_id) VALUES (%s, %s, %s)" \
                "RETURNING id",
                (tag, name, avatar_id)
            )
            user_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO refresh_tokens (user_tag, access_token) VALUES (%s, %s) ",
                (tag, hashed_key))
            conn.commit()
            return user_id
    finally:
        conn.close()

@handle_db_errors # Получение хэша access_token по имени пользователя
def get_hash_ac_from_user(user_tag: str) -> str:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT access_token FROM refresh_tokens WHERE user_tag = %s", (user_tag,))
            hash_api_key = cursor.fetchone()[0]

            return hash_api_key
    finally:
        conn.close()

@handle_db_errors # Сохранение нового хэша refresh_token
def save_refresh_token(user_tag: str, hashed_refresh_token: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE refresh_tokens SET (refresh_token, expired_at, updated_at) " \
                "VALUES (%s, CURRENT_TIMESTAMP + INTERVAL '7 days', CURRENT_TIMESTAMP) " \
                "WHERE user_tag = %s",
                (hashed_refresh_token, user_tag)
            )
            conn.commit()
    finally:
        conn.close()

@handle_db_errors # Получение данных о refresh_token по его хэшу
def get_refresh_data_from_user(refresh_token_hash: str) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT updated_at, expired_at, user_tag FROM refresh_tokens WHERE refresh_token = %s",
                (refresh_token_hash,)
            )
            fetch_data = cursor.fetchone()
            data = {"updated_at": fetch_data[0], "expired_at": fetch_data[1], "user_tag": fetch_data[2]}

            return data
    finally:
        conn.close()

@handle_db_errors
def get_user_data_by_tag(user_tag: str) -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_tag = %s", (user_tag,))
            fetch_data = cursor.fetchone()[0]

            keys_sample = ['id', 'name', 'user_tag', 'avatar_id', 'created_at', 'updated_at']
            user_data = {k: v for k, v in zip(keys_sample, fetch_data)}

            return user_data
    finally:
        conn.close()

if __name__ == "__main__":
    """
    def first_init():
        users = ["kapusta", "yxa"]
        for u in users:
            plain_key = getenv(f'{u}_TOKEN')
            hashed_key = hash_api_key(plain_key)

            print(verify_api_key(plain_key, hashed_key)) # Test

            tag = getenv(f'{u}_TAG')
            name = getenv(f'{u}_NAME')

            create_user(tag, name, hashed_key=hashed_key)
    """
    
    create_tables()
    #first_init()