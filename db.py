import psycopg2 as pc2

from os import getenv
from dotenv import load_dotenv

from datetime import datetime
from specials import handle_db_errors

load_dotenv('.env')

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
# Получение данных о refresh_token
@handle_db_errors
def get_hashed_refresh_token(client_id: str) -> tuple[str, datetime]:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT refresh_token, created_at FROM rtokens WHERE client_id = %s", (client_id,))
            res = cursor.fetchone()
            hashed_refresh_token = res[0]
            created_at = res[1]
            return (hashed_refresh_token, created_at)
    finally: conn.close()
# Обновление refresh_token в таблицах atokens и rtokens, а также обновление created_at в rtokens
@handle_db_errors
def refresh_set_refresh_token(client_id, hashed_new_refresh_token) -> datetime:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE atokens SET refresh_token = %s WHERE client_id = %s", (hashed_new_refresh_token, client_id))
            cursor.execute("UPDATE rtokens SET refresh_token = %s, created_at = CURRENT_TIMESTAMP WHERE client_id = %s RETURNING created_at", (hashed_new_refresh_token, client_id))
            created_at = cursor.fetchone()[0]
            conn.commit()
            return created_at
    finally: conn.close()
# Получение хэша access_token по client_id
@handle_db_errors
def get_hashed_access_token(client_id: str):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT access_token FROM atokens WHERE client_id = %s", (client_id,))
            hashed_access_token = cursor.fetchone()[0]
            return hashed_access_token
    finally: conn.close()
# Обновление токенов
@handle_db_errors
def auth_set_refresh_token(client_id, hashed_access_token, hashed_refresh_token) -> datetime:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE atokens SET refresh_token = %s WHERE access_token = %s", (hashed_refresh_token, hashed_access_token))
            cursor.execute("INSERT INTO rtokens (refresh_token, client_id) VALUES (%s, %s) ON CONFLICT (client_id) DO UPDATE SET refresh_token = %s", (hashed_refresh_token, client_id, hashed_refresh_token))
            cursor.execute("UPDATE rtokens SET created_at = CURRENT_TIMESTAMP WHERE client_id = %s", (client_id,))
            cursor.execute("SELECT created_at FROM rtokens WHERE client_id = %s", (client_id,))
            created_at = cursor.fetchone()[0]
            conn.commit()
            return created_at
    finally: conn.close()
# Создание пользователя и его хэша access_token
@handle_db_errors
def create_user(client_id, name, hashed_access_token):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO users (client_id, name) VALUES (%s, %s)", (client_id, name))
            cursor.execute("INSERT INTO atokens (access_token, client_id) VALUES (%s, %s)", (hashed_access_token, client_id))
            conn.commit()
    finally: conn.close()
# Генерация таблиц при первом запуске
@handle_db_errors
def main():
    conn = get_connection()
    # Пользователь + токены
    users = "CREATE TABLE IF NOT EXISTS users (" \
        "client_id      VARCHAR(15)     PRIMARY KEY UNIQUE," \
        "name           VARCHAR(15)     NOT NULL," \
        "avatar_id      INT NULL        REFERENCES media(id) ON DELETE SET NULL," \
        "created_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP," \
        "updated_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP," \
        "status         VARCHAR(8)      DEFAULT 'offline'" \
    ")"
    atokens = "CREATE TABLE IF NOT EXISTS atokens (" \
        "access_token   VARCHAR(64)     PRIMARY KEY NOT NULL," \
        "refresh_token  VARCHAR(64)     NULL," \
        "client_id      VARCHAR(15)     NOT NULL UNIQUE REFERENCES users(client_id) ON DELETE CASCADE," \
        "created_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP" \
    ")"
    rtokens = "CREATE TABLE IF NOT EXISTS rtokens (" \
        "refresh_token  VARCHAR(64)     PRIMARY KEY NOT NULL," \
        "client_id      VARCHAR(15)     NOT NULL UNIQUE REFERENCES users(client_id) ON DELETE CASCADE," \
        "created_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP," \
        "expired_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP + INTERVAL '7 days'" \
    ")"
    # Вспомогательные таблицы
    media = "CREATE TABLE IF NOT EXISTS media (" \
        "id             SERIAL          PRIMARY KEY NOT NULL," \
        "filename       text            NOT NULL," \
        "url            TEXT            NOT NULL," \
        "created_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP" \
    ")"
    # Основная логика
    chats = "CREATE TABLE IF NOT EXISTS chats (" \
        "id             SERIAL          PRIMARY KEY," \
        "name           VARCHAR(128)    NOT NULL," \
        "created_by     VARCHAR(15)     NOT NULL REFERENCES users(client_id) ON DELETE CASCADE," \
        "created_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP" \
    ")"
    chat_members = "CREATE TABLE IF NOT EXISTS chat_members (" \
        "chat_id        INT             NOT NULL REFERENCES chats(id) ON DELETE CASCADE," \
        "client_id      VARCHAR(15)     NOT NULL REFERENCES users(client_id) ON DELETE CASCADE," \
        "joined_at      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP," \
        "left_at        TIMESTAMP       NULL," \
        "PRIMARY KEY (chat_id, client_id)" \
    ")"
    messages = "CREATE TABLE IF NOT EXISTS messages (" \
        "id             SERIAL          PRIMARY KEY," \
        "chat_id        INT             NOT NULL REFERENCES chats(id) ON DELETE CASCADE," \
        "sender_id      VARCHAR(15)     NOT NULL REFERENCES users(client_id) ON DELETE CASCADE," \
        "reply_to_id    INT             NULL REFERENCES messages(id) ON DELETE CASCADE," \
        "text           TEXT            NULL," \
        "is_deleted     BOOLEAN         DEFAULT FALSE," \
        "created_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP," \
        "updated_at     TIMESTAMP       NULL," \
        "deleted_at     TIMESTAMP       NULL" \
    ")"
    messages_media = "CREATE TABLE IF NOT EXISTS message_media (" \
        "message_id     BIGINT          NOT NULL REFERENCES messages(id) ON DELETE CASCADE," \
        "media_id       BIGINT          NOT NULL REFERENCES media(id) ON DELETE CASCADE," \
        "PRIMARY KEY (message_id, media_id)" \
    ")"
    messages_read = "CREATE TABLE IF NOT EXISTS message_reads (" \
        "message_id     BIGINT          NOT NULL REFERENCES messages(id) ON DELETE CASCADE," \
        "client_id      VARCHAR(15)     NOT NULL REFERENCES users(client_id) ON DELETE CASCADE," \
        "read_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP," \
        "PRIMARY KEY (message_id, client_id)" \
    ")"

    try:
        with conn.cursor() as cursor:
            cursor.execute(media)
            # Связка с media
            cursor.execute(users)
            # Для верификаций
            cursor.execute(atokens)
            cursor.execute(rtokens)
            # Связка с users
            cursor.execute(chats)
            cursor.execute(chat_members)
            # Связка с chats
            cursor.execute(messages)            
            cursor.execute(messages_media)
            cursor.execute(messages_read)
            # index
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)")
    
    except Exception as exc:
        print(exc)
        conn.rollback()
    
    finally: conn.close()

if __name__ == "__main__":
    main() # Создание таблиц
    # Первичная регистрация пользователей из .env
    reg = input("reg user? (y/n): ")
    if reg.lower() != 'n':
        load_dotenv('access.env')

        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        def hash_api_key(plain_key: str) -> str: return pwd_context.hash(plain_key)
        #def verify_api_key(plain_key: str, hashed_key: str) -> bool: return pwd_context.verify(plain_key, hashed_key)

        NAMES = getenv('NAMES').split(' ')
        IDS = getenv('IDS').split(' ')
        TOKENS = getenv('TOKENS').split(' ')

        for name, client_id, token in zip(NAMES, IDS, TOKENS):
              hashed_access_token = hash_api_key(token)
              create_user(client_id, name, hashed_access_token)