import psycopg2 as pc2

from os import getenv
from dotenv import load_dotenv

from datetime import datetime
from specials import HashManager

from db_models import UserModel, ChatModel, MediaModel

load_dotenv('.env')

DATABASE_NAME = getenv('DATABASE_NAME')
DATABASE_HOST = getenv('DATABASE_HOST')
DATABASE_USER = getenv('DATABASE_USER')
DATABASE_PASS = getenv('DATABASE_PASS')
DATABASE_PORT = getenv('DATABASE_PORT')

def get_connection():
    connection = pc2.connect(
        dbname=DATABASE_NAME,
        host=DATABASE_HOST,
        user=DATABASE_USER,
        password=DATABASE_PASS,
        port=DATABASE_PORT
    )
    return connection




def get_user_by_login(login: str) -> UserModel | None:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, login, avatar_id, status FROM users WHERE login = %s", (login,))
            res = cursor.fetchone()
            if res:
                user = UserModel(login=res[2], username=res[1], id=res[0], avatar_id=res[3], status=res[4])
                return user
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> UserModel | None:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, login, avatar_id, status FROM users WHERE id = %s", (user_id,))
            res = cursor.fetchone()
            if res:
                user = UserModel(login=res[2], username=res[1], id=res[0], avatar_id=res[3], status=res[4])
                return user
    finally:
        conn.close()







def get_media(media_id: int) -> MediaModel:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT filename, path FROM media WHERE id = %s", (media_id,))
            res = cursor.fetchone()
            if res:
                model = MediaModel(
                    id=media_id,
                    filename=res[0],
                    path=res[1] 
                )
                return model
    finally:
        conn.close()







def get_chats_by_user_id(user_id: int) -> list[ChatModel]:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
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
            """, (user_id, user_id)
            )
            rows = cursor.fetchall()
            models = [
                ChatModel(
                    id              = row[0],
                    avatar_id       = row[1],
                    name            = row[2],
                    first_user_id   = row[3],
                    second_user_id  = row[4],
                    last_msg_text   = row[5]
                ) for row in rows
            ]
            return models
    finally:
        conn.close()






def create_chat(chat_name: str, owner: UserModel, recipient: UserModel) -> ChatModel:
    conn = get_connection()
    try:
        fu_id = owner.id
        su_id = recipient.id
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO chats (name, first_user_id, second_user_id) VALUES (%s, %s, %s) RETURNING id",
                           (chat_name, fu_id, su_id)
            )
            chat_id = cursor.fetchone()[0]
            conn.commit()
            model = ChatModel(
                    id = chat_id,
                    name = chat_name,
                    first_user_id = fu_id,
                    second_user_id = su_id
                )
            return model
    finally:
        conn.close()






# Верификация пользователя по логину и паролю
def verify_user(login: str, password: str) -> UserModel | None:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, username, login, password_hash, avatar_id FROM users WHERE login = %s", (login,))
            res = cursor.fetchone()
            if res and HashManager.verify_key(password, res[3]):
                user = UserModel(id=res[0], username=res[1], login=res[2], avatar_id=res[4])
                return user
    finally:
        conn.close()

def _create_tables():
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
        "avatar_id      INT     REFERENCES media(id) DEFAULT 1," \
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

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(media)
            cursor.execute(users)
            cursor.execute(chats)
            cursor.execute(messages)
            cursor.execute(chats_last_message_column)
            conn.commit()
    finally:
        conn.close()

def _new_user(username: str, login: str, password_hash: str, avatar_id: int | None = None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO users (username, login, password_hash, avatar_id) VALUES (%s, %s, %s, %s)",
                           (username, login, password_hash, avatar_id))
            conn.commit()
    finally:
        conn.close()

# Первый запуск
if __name__ == "__main__":
    _create_tables()
    if input("reg users? (y/n): ").lower() != 'n':
        load_dotenv('access.env')
        # Заранее определенные пользователи для удобства тестирования
        USERNAMES = getenv('USERNAMES').split(' ')
        LOGINS = getenv('LOGINS').split(' ')
        PASSWORDS = getenv('PASSWORDS').split(' ')
        # Регистрация пользователей из .env
        for username, login, password in zip(USERNAMES, LOGINS, PASSWORDS):
            password_hash = HashManager.hash_key(password)
            _new_user(username, login, password_hash)
        print("Success. (propably)")