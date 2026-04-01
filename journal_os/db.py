"""
db.py
─────
All PostgreSQL interactions: connection, schema setup, full CRUD.
No UI or business logic lives here.

Every function that writes to the database returns the affected row's id
so callers can immediately mirror the change in the vector store.
"""

import psycopg2
from datetime import date, datetime, timedelta
from typing import Optional
from logger import get_logger
from config import DB_CONFIG

log = get_logger(__name__)


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
    """Create the journal_entries table if it does not already exist."""
    log.info("Setting up database schema")
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id           SERIAL PRIMARY KEY,
                title        TEXT      NOT NULL,
                content      TEXT      NOT NULL,
                journal_date DATE      NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
    conn.close()
    log.info("Schema ready")


# ──────────────────────────────────────────────
#  WRITE — Create
# ──────────────────────────────────────────────

def insert_entry_returning_id(title: str, content: str, date_str: str) -> int:
    """
    Persist a journal entry and return its generated primary key.
    Callers should immediately call vector_store.upsert_entry() with this id.

    Returns:
        The new row's integer id.
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO journal_entries (title, content, journal_date) "
            "VALUES (%s, %s, %s) RETURNING id",
            (title, content, date_str),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
    conn.close()
    log.info("Inserted entry id=%s title=%r", new_id, title)
    return new_id


# ──────────────────────────────────────────────
#  WRITE — Update
# ──────────────────────────────────────────────

def update_entry(entry_id: int, title: str, content: str, date_str: str) -> None:
    """
    Overwrite an existing journal entry in place.
    Callers should re-upsert the entry to the vector store after calling this.

    Args:
        entry_id: Primary key of the entry to update.
        title, content, date_str: New field values.

    Raises:
        ValueError: If no row with that id exists.
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE journal_entries
               SET title        = %s,
                   content      = %s,
                   journal_date = %s,
                   updated_at   = NOW()
             WHERE id = %s
            """,
            (title, content, date_str, entry_id),
        )
        if cur.rowcount == 0:
            conn.rollback()
            conn.close()
            raise ValueError(f"No entry with id={entry_id}")
        conn.commit()
    conn.close()
    log.info("Updated entry id=%s", entry_id)


# ──────────────────────────────────────────────
#  WRITE — Delete
# ──────────────────────────────────────────────

def delete_entry(entry_id: int) -> None:
    """
    Hard-delete a journal entry from PostgreSQL.
    Callers must also call vector_store.delete_entry() to keep stores in sync.

    Raises:
        ValueError: If no row with that id exists.
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM journal_entries WHERE id = %s", (entry_id,))
        if cur.rowcount == 0:
            conn.rollback()
            conn.close()
            raise ValueError(f"No entry with id={entry_id}")
        conn.commit()
    conn.close()
    log.info("Deleted entry id=%s", entry_id)


# ──────────────────────────────────────────────
#  READ — Single entry
# ──────────────────────────────────────────────

def get_entry_by_id(entry_id: int) -> Optional[tuple]:
    """
    Fetch a single entry by primary key.

    Returns:
        (id, title, content, journal_date) or None if not found.
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, content, journal_date "
            "FROM journal_entries WHERE id = %s",
            (entry_id,),
        )
        row = cur.fetchone()
    conn.close()
    return row


# ──────────────────────────────────────────────
#  READ — Collections
# ──────────────────────────────────────────────

def fetch_all_entries() -> list[tuple]:
    """
    Return every entry ordered newest-first.

    Returns:
        List of (title, content, journal_date) tuples.
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT title, content, journal_date "
            "FROM journal_entries ORDER BY journal_date DESC"
        )
        rows = cur.fetchall()
    conn.close()
    return rows


def fetch_all_entries_with_ids() -> list[tuple]:
    """
    Return every entry including its primary key, ordered by id asc.
    Used for bulk vector-store sync.

    Returns:
        List of (id, title, content, journal_date) tuples.
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, content, journal_date "
            "FROM journal_entries ORDER BY id ASC"
        )
        rows = cur.fetchall()
    conn.close()
    return rows


def fetch_entries_in_range(start: str, end: str) -> Optional[str]:
    """
    Return entries within an inclusive date range as a formatted string.

    Args:
        start: ISO date string 'YYYY-MM-DD' (inclusive).
        end:   ISO date string 'YYYY-MM-DD' (inclusive).

    Returns:
        Multi-line string with each entry prefixed by its title,
        or None if the range is empty.
    """
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT title, content FROM journal_entries "
            "WHERE journal_date BETWEEN %s AND %s "
            "ORDER BY journal_date ASC",
            (start, end),
        )
        rows = cur.fetchall()
    conn.close()
    if not rows:
        return None
    return "\n\n".join(f"[{r[0]}]\n{r[1]}" for r in rows)


# ──────────────────────────────────────────────
#  READ — Statistics
# ──────────────────────────────────────────────

def get_stats() -> dict:
    """
    Return a snapshot of journal statistics for the home screen.

    Returns dict with keys:
        total_entries   int
        total_words     int
        streak_days     int  — current consecutive-day writing streak
        most_active_day str  — weekday name with most entries, e.g. 'Monday'
        oldest_date     str  — ISO date of earliest entry, or ''
        newest_date     str  — ISO date of most recent entry, or ''
    """
    conn = get_connection()
    with conn.cursor() as cur:

        # Entry count + word count approximation
        cur.execute(
            "SELECT COUNT(*), "
            "COALESCE(SUM(array_length(regexp_split_to_array(trim(content), '\\s+'), 1)), 0) "
            "FROM journal_entries"
        )
        total_entries, total_words = cur.fetchone()

        # Date range
        cur.execute(
            "SELECT MIN(journal_date), MAX(journal_date) FROM journal_entries"
        )
        oldest, newest = cur.fetchone()

        # Current streak: count consecutive days ending today or yesterday
        cur.execute(
            "SELECT DISTINCT journal_date FROM journal_entries ORDER BY journal_date DESC"
        )
        all_dates = {r[0] for r in cur.fetchall()}

        streak = 0
        check = date.today()
        # Allow today or yesterday as streak anchor
        if check not in all_dates:
            check = check - timedelta(days=1)
        while check in all_dates:
            streak += 1
            check -= timedelta(days=1)

        # Most active weekday
        cur.execute(
            "SELECT TO_CHAR(journal_date, 'Day'), COUNT(*) "
            "FROM journal_entries "
            "GROUP BY TO_CHAR(journal_date, 'Day') "
            "ORDER BY COUNT(*) DESC LIMIT 1"
        )
        row = cur.fetchone()
        most_active_day = row[0].strip() if row else "—"

    conn.close()

    return {
        "total_entries":   int(total_entries),
        "total_words":     int(total_words),
        "streak_days":     streak,
        "most_active_day": most_active_day,
        "oldest_date":     str(oldest) if oldest else "",
        "newest_date":     str(newest) if newest else "",
    }