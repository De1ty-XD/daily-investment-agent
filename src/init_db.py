import sqlite3
from pathlib import Path

DB_PATH = Path("data/db/news.db")

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_name TEXT,
        category TEXT,
        title TEXT,
        url TEXT UNIQUE,
        published_at TEXT,
        summary TEXT,
        content TEXT,
        llm_summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
