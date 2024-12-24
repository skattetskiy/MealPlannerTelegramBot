import psycopg2
from config import DB_CONFIG

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def init_db():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE NOT NULL,
            name TEXT NOT NULL,     -- Имя пользователя
            diet_preferences TEXT,  -- Диетические предпочтения
            goals TEXT              -- Цели питания
        );
        """)
        conn.commit()
    conn.close()

