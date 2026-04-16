import psycopg2 as pc2

from os import getenv
from dotenv import load_dotenv

from datetime import datetime
from specials import HashManager

from db_models import UserModel

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
                print(res)
                user = UserModel(login=res[2], username=res[1], id=res[0], avatar_id=res[3], status=res[4])
                return user
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
        "id SERIAL PRIMARY KEY," \
        "username TEXT NOT NULL," \
        "login TEXT NOT NULL UNIQUE," \
        "password_hash TEXT NOT NULL," \
        "avatar_id INT REFERENCES media(id)," \
        "status TEXT DEFAULT 'offline'" \
    ")"
    media = "CREATE TABLE IF NOT EXISTS media (" \
        "id SERIAL PRIMARY KEY," \
        "filename text NOT NULL," \
        "url TEXT NOT NULL" \
    ")"

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(media)
            cursor.execute(users)
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