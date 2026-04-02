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
async def get_async_connection():
    conn = await pc2.connect(
        dbname=DATABASE_NAME,
        host=DATABASE_HOST,
        user=DATABASE_USER,
        password=DATABASE_PASS,
        port=DATABASE_PORT,
        async_=True
    )
    conn.autocommit = True
    return conn

def create_tables():
    conn = get_connection()

    users = "CREATE TABLE IF NOT EXISTS users (" \
        "id              BIGSERIAL PRIMARY KEY," \
        "tag             VARCHAR(32) UNIQUE NOT NULL," \
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
            cursor.execute(chats)
            cursor.execute(messages)
            cursor.execute(
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

if __name__ == "__main__":
    create_tables()