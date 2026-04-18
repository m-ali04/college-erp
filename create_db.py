import psycopg2
from config import Config

def create_database():
    try:
        print("Connecting to default postgres database to create application DB...")
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            dbname='postgres'
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE {Config.DB_NAME};")
        print(f"Database '{Config.DB_NAME}' created successfully.")
    except psycopg2.errors.DuplicateDatabase:
        print(f"Database '{Config.DB_NAME}' already exists.")
    except Exception as e:
        print(f"Error creating database: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == '__main__':
    create_database()
