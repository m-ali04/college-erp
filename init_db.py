"""
Database initialization script.
Run once to create all tables and seed the default admin user.

Usage:  python init_db.py
"""
import psycopg2
from config import Config


def init_database():
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )

    try:
        with conn.cursor() as cur:
            # Execute schema
            print("Executing schema.sql ...")
            with open('schema.sql', 'r') as f:
                cur.execute(f.read())

            # Seed default admin user
            print("Creating default admin user ...")
            password = 'admin123'
            cur.execute(
                """INSERT INTO users (full_name, email, password, role)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (email) DO NOTHING""",
                ('System Administrator', 'admin@college.edu', password, 'admin')
            )

            conn.commit()
            print()
            print("=" * 50)
            print("  Database initialized successfully!")
            print("=" * 50)
            print()
            print("  Default Admin Credentials:")
            print("  Email:    admin@college.edu")
            print("  Password: admin123")
            print()
            print("  WARNING: Change the admin password after first login!")
            print("=" * 50)
            print()

    except Exception as e:
        conn.rollback()
        print(f"\nError initializing database: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    init_database()
