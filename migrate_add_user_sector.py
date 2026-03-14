import sqlite3
from pathlib import Path

DB_PATH = Path("instance/intranet_carmel.db")

def column_exists(conn, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Banco não encontrado: {DB_PATH.resolve()}")

    conn = sqlite3.connect(DB_PATH)
    try:
        if column_exists(conn, "user", "sector"):
            print("OK: coluna 'sector' já existe em user.")
            return

        conn.execute("ALTER TABLE user ADD COLUMN sector TEXT;")
        conn.commit()
        print("SUCESSO: coluna 'sector' adicionada na tabela user.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
