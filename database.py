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
            name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS meals (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            meal_time TEXT NOT NULL,
            image_url TEXT NULL,
            protein FLOAT NOT NULL,
            fat FLOAT NOT NULL,
            carbohydrates FLOAT NOT NULL,
            weight FLOAT NOT NULL,
            servings INT NOT NULL,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS ingredients (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            weight FLOAT NOT NULL,
            protein FLOAT NOT NULL,
            fat FLOAT NOT NULL,
            carbohydrates FLOAT NOT NULL,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
        );
        """)
        conn.commit()
    conn.close()
