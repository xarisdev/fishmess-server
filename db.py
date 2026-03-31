from os import getenv
from dotenv import load_dotenv

import psycopg2 as pc2

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

def create_table_users():
    conn = get_connection()
    
    with conn.cursor() as cursor:
        cursor.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(50), status VARCHAR(10))")

    conn.close()

def create_new_user(user_id: int, username: str, status: str = "offline"):
    data = (user_id, username[:50], status)

    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO users (id, username, status) VALUES (%s, %s, %s)", data)

    conn.close()

def get_all_users() -> list[dict]:
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM users")
        cdata = cursor.fetchall()
    conn.close()

    data = [{"id": u[0], "username": u[1], "status": u[2]} for u in cdata] # API format `list[dict]`
    return data

def get_user_by_id(ids: list[int]) -> list[dict]:
    if not ids: return
    placeholders = ', '.join(['%s'] * len(ids))
    
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT * FROM users WHERE id IN ({placeholders})", ids)
        cdata = cursor.fetchall()
    conn.close()

    data = [{"id": u[0], "username": u[1], "status": u[2]} for u in cdata] # API format `list[dict]`
    return data