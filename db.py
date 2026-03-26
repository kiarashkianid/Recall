"""
db.py
─────
All PostgreSQL interactions: connection, schema setup, and CRUD queries.
No UI or business logic lives here.
"""

import psycopg2
from datetime import datetime, timedelta
from config import DB_CONFIG


# ──────────────────────────────────────────────
#  CONNECTION
# ──────────────────────────────────────────────

def get_connection():
    """Return a live psycopg2 connection using DB_CONFIG."""
    return psycopg2.connect(**DB_CONFIG)


# ──────────────────────────────────────────────
#  SCHEMA
# ──────────────────────────────────────────────

def setup_schema() -> None:
    """Create the journal_entries table if it doesn't already exist."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id           SERIAL PRIMARY KEY,
                title        TEXT      NOT NULL,
                content      TEXT      NOT NULL,
                journal_date DATE      NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    conn.close()


# ──────────────────────────────────────────────
#  WRITE
# ──────────────────────────────────────────────

def insert_entry(title: str, content: str, date: str) -> None:
    """
    Persist a single journal entry.

    Args:
        title:   Entry heading.
        content: Body text.
        date:    ISO date string, e.g. '2025-06-01'.
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO journal_entries (title, content, journal_date) VALUES (%s, %s, %s)",
            (title, content, date),
        )
        conn.commit()
    conn.close()


# ──────────────────────────────────────────────
#  READ
# ──────────────────────────────────────────────

def fetch_all_entries() -> list[tuple]:
    """
    Return every journal entry ordered newest-first.

    Returns:
        List of (title, content, journal_date) tuples.
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT title, content, journal_date "
            "FROM journal_entries "
            "ORDER BY journal_date DESC"
        )
        rows = cur.fetchall()
    conn.close()
    return rows


def fetch_last_week_entries() -> str | None:
    """
    Return entries from the last 7 days as a single formatted string,
    or None if no entries exist in that window.

    Returns:
        Multi-line string with each entry prefixed by its title,
        or None when the result set is empty.
    """
    week_ago = datetime.now() - timedelta(days=7)

    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT title, content "
            "FROM journal_entries "
            "WHERE journal_date >= %s "
            "ORDER BY journal_date ASC",
            (week_ago,),
        )
        rows = cur.fetchall()
    conn.close()

    if not rows:
        return None

    return "\n\n".join(f"[{row[0]}]\n{row[1]}" for row in rows)
