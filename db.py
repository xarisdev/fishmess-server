import psycopg2 as pc2

from os import getenv
from dotenv import load_dotenv

from datetime import datetime
from specials import HashManager

from db_models import UserModel, ChatModel, FileModel, MessageModel

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

def _execute_query(
        query: str,
        params: tuple = (),
        fetch_one: bool = False
    ) -> tuple | list[tuple]:
    with get_connection() as conn:
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                result = cursor.fetchone() if fetch_one else cursor.fetchall()
                return result
        except Exception as exc:
            print("Database error:", exc)

#
# Работа с пользователями
#

# Верификация пользователя по логину и паролю
def verify_user(login: str, password: str) -> UserModel | None:
    query = "SELECT id, username, login, password_hash, avatar_id FROM users WHERE login = %s"
    result = _execute_query(query, (login,), fetch_one=True)
    if result and HashManager.verify_key(password, result[3]):
        user = UserModel(id=result[0], username=result[1], login=result[2], avatar_id=result[4])
        return user

def get_user_by_login(login: str) -> UserModel | None:
    query = "SELECT id, username, login, avatar_id, status " \
            "FROM users " \
            "WHERE login = %s"
    result = _execute_query(query, (login,), fetch_one=True)
    if result:
        model = UserModel(
            id=result[0],
            username=result[1],
            login=result[2],
            avatar_id=result[3],
            status=result[4]
        )
        return model

def get_user_by_id(user_id: int) -> UserModel | None:
    query = "SELECT id, username, login, avatar_id, status " \
            "FROM users " \
            "WHERE id = %s"
    result = _execute_query(query, (user_id,), fetch_one=True)
    if result:
        model = UserModel(
            id=result[0],
            username=result[1],
            login=result[2],
            avatar_id=result[3],
            status=result[4]
        )
        return model

#
# Работа с медиа
#
def save_file(filename: str, filepath: str, user_id: int) -> int:
    query = "INSERT INTO media (filename, path, user_id) " \
            "VALUES (%s, %s, %s) " \
            "RETURNING id"
    result = _execute_query(query, (filename, filepath, user_id), fetch_one=True)
    if result:
        media_id = result[0]
        return media_id

def get_file(file_id: int, user_id: int) -> FileModel:
    query = "SELECT * FROM media WHERE id = %s"
    result = _execute_query(query, (file_id,), fetch_one=True)
    if result:
        if result[-1] != user_id:
            return 403
        model = FileModel(*result)
        return model
#
# Работа с чатами
#

def get_chats_by_user_id(user_id: int) -> list[ChatModel]:
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
    results = _execute_query(query, (user_id, user_id))
    return [
        ChatModel(
            id              = row[0],
            avatar_id       = row[1],
            name            = row[2],
            first_user_id   = row[3],
            second_user_id  = row[4],
            last_msg_text   = row[5]
        ) for row in results
    ]

def create_chat(chat_name: str, own_id: int, rec_id: int) -> ChatModel | tuple[int, str]:
    # Проверка на существование чата
    already_exists = _execute_query(
        "SELECT id " \
        "FROM chats " \
        "WHERE "
            "(first_user_id = %s AND second_user_id = %s) OR "
            "(first_user_id = %s AND second_user_id = %s)",
        (own_id, rec_id, rec_id, own_id),
        fetch_one=True
    )
    if already_exists:
        return (400, "Bad Request: Chat already exists")
    # Создание чата
    query = "INSERT INTO chats (name, first_user_id, second_user_id) " \
            "VALUES (%s, %s, %s) " \
            "RETURNING id"
    result = _execute_query(query, (chat_name, own_id, rec_id), fetch_one=True)
    if result:
        chat_id = result[0]
        model = ChatModel(
            id              = chat_id,
            name            = chat_name,
            first_user_id   = own_id,
            second_user_id  = rec_id
        )
        return model

def send_message(chat_id: int, owner_id: int, text: str) -> MessageModel:
    query = "INSERT INTO messages (text, chat_id, owner_id) " \
            "VALUES (%s, %s, %s) " \
            "RETURNING id"
    result = _execute_query(query, (text, chat_id, owner_id), fetch_one=True)
    if result:
        message_id = result[0]
        model = MessageModel(
            id=message_id,
            text=text,
            chat_id=chat_id,
            owner_id=owner_id
        )
        return model

def get_messages(chat_id: int, limit: int) -> list[MessageModel]:
    query = "SELECT * " \
            "FROM messages " \
            "WHERE chat_id = %s"
    result = _execute_query(query, (chat_id,))
    if result:
        messages = result[:limit]
        models = [
            MessageModel(id=message[0], text=message[1], chat_id=message[2], owner_id=message[3])
            for message in messages
        ]
        return models

#
#
# Базовая настройка

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

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(media)
            cursor.execute(users)
            cursor.execute(media_alter)
            cursor.execute(chats)
            cursor.execute(messages)
            cursor.execute(chats_last_message_column)
            conn.commit()
    finally:
        conn.close()

# Добавление пользователя
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