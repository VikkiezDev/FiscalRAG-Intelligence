import psycopg
from pgvector.psycopg import register_vector

from app.config import settings


def get_conn() -> psycopg.Connection:
    conn = psycopg.connect(settings.database_url)
    register_vector(conn)
    return conn
