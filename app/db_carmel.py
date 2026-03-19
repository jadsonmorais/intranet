import psycopg2
import psycopg2.extras
from flask import current_app


def get_connection():
    url = current_app.config.get("CARMEL_DB_URL")
    if not url:
        raise RuntimeError("CARMEL_DB_URL não configurado.")
    return psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
