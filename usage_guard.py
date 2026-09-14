import asyncio
import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

USAGE_DB = "usage.db"

DAILY_REVIEW_LIMIT = int(
    os.getenv("DAILY_REVIEW_LIMIT", "20")
)

DAILY_REVIEW_CACHE_SECONDS = int(
    os.getenv("DAILY_REVIEW_CACHE_SECONDS", "900")
)


AGENT_TASK_DAILY_LIMIT = int(
    os.getenv("AGENT_TASK_DAILY_LIMIT", "30")
)


agent_task_lock = asyncio.Lock()

# Prevent many simultaneous requests from launching
# many AI runs at the same time.
daily_review_lock = asyncio.Lock()


def get_connection():
    conn = sqlite3.connect(
        USAGE_DB,
        timeout=10
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_usage_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_usage (
            usage_date TEXT PRIMARY KEY,
            generation_count INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_review_cache (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            generated_at REAL NOT NULL,
            response_json TEXT NOT NULL
        )
        """
    )
    cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS agent_task_usage (
        usage_date TEXT PRIMARY KEY,
        request_count INTEGER NOT NULL DEFAULT 0
    )
    """
    )

    conn.commit()
    conn.close()


def get_today_utc():
    return datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")


def get_daily_usage():
    today = get_today_utc()

    conn = get_connection()

    row = conn.execute(
        """
        SELECT generation_count
        FROM daily_usage
        WHERE usage_date = ?
        """,
        (today,)
    ).fetchone()

    conn.close()

    if row is None:
        return 0

    return row["generation_count"]


def reserve_daily_generation():
    """
    Atomically reserve one generation slot.

    Returns:
        (allowed: bool, current_count: int)
    """

    today = get_today_utc()

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            """
            SELECT generation_count
            FROM daily_usage
            WHERE usage_date = ?
            """,
            (today,)
        ).fetchone()

        current_count = (
            row["generation_count"]
            if row
            else 0
        )

        if current_count >= DAILY_REVIEW_LIMIT:
            conn.rollback()

            return False, current_count

        new_count = current_count + 1

        conn.execute(
            """
            INSERT INTO daily_usage (
                usage_date,
                generation_count
            )
            VALUES (?, ?)
            ON CONFLICT(usage_date)
            DO UPDATE SET
                generation_count =
                    excluded.generation_count
            """,
            (
                today,
                new_count
            )
        )

        conn.commit()

        return True, new_count

    finally:
        conn.close()


def get_cached_daily_review():
    conn = get_connection()

    row = conn.execute(
        """
        SELECT
            generated_at,
            response_json
        FROM daily_review_cache
        WHERE id = 1
        """
    ).fetchone()

    conn.close()

    if row is None:
        return None

    age_seconds = (
        time.time()
        - row["generated_at"]
    )

    if age_seconds > DAILY_REVIEW_CACHE_SECONDS:
        return None

    return json.loads(
        row["response_json"]
    )


def save_daily_review_cache(data):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO daily_review_cache (
            id,
            generated_at,
            response_json
        )
        VALUES (
            1,
            ?,
            ?
        )
        ON CONFLICT(id)
        DO UPDATE SET
            generated_at =
                excluded.generated_at,
            response_json =
                excluded.response_json
        """,
        (
            time.time(),
            json.dumps(data)
        )
    )

    conn.commit()
    conn.close()


def get_agent_task_usage():
    today = get_today_utc()

    conn = get_connection()

    row = conn.execute(
        """
        SELECT request_count
        FROM agent_task_usage
        WHERE usage_date = ?
        """,
        (today,)
    ).fetchone()

    conn.close()

    if row is None:
        return 0

    return row["request_count"]


def reserve_agent_task():
    """
    Atomically reserve one Agent Task execution slot.

    Returns:
        (allowed: bool, current_count: int)
    """

    today = get_today_utc()

    conn = get_connection()

    try:
        conn.execute("BEGIN IMMEDIATE")

        row = conn.execute(
            """
            SELECT request_count
            FROM agent_task_usage
            WHERE usage_date = ?
            """,
            (today,)
        ).fetchone()

        current_count = (
            row["request_count"]
            if row
            else 0
        )

        if current_count >= AGENT_TASK_DAILY_LIMIT:
            conn.rollback()

            return False, current_count

        new_count = current_count + 1

        conn.execute(
            """
            INSERT INTO agent_task_usage (
                usage_date,
                request_count
            )
            VALUES (?, ?)
            ON CONFLICT(usage_date)
            DO UPDATE SET
                request_count =
                    excluded.request_count
            """,
            (
                today,
                new_count
            )
        )

        conn.commit()

        return True, new_count

    finally:
        conn.close()