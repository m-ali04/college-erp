"""
Database helper module.
All SQL execution goes through execute_query() which uses psycopg2 directly.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from config import Config


def get_connection():
    """Create and return a new database connection."""
    return psycopg2.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        database=Config.DB_NAME,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD
    )


def execute_query(query, params=None, fetch=False, fetchone=False):
    """Execute a SQL query and optionally return results.

    Args:
        query:    SQL string with %s placeholders.
        params:   Tuple of bind parameters.
        fetch:    If True, return all rows as list[dict].
        fetchone: If True, return a single row as dict.

    Returns:
        list[dict] | dict | None
    """
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if fetchone:
                result = cur.fetchone()
            elif fetch:
                result = cur.fetchall()
            else:
                result = None
            conn.commit()
            return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
