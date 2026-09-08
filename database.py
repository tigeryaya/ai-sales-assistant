import os
import sqlite3

DB_PATH = os.getenv(
    "CRM_DB_PATH",
    "crm.db"
)


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT NOT NULL,
            email TEXT NOT NULL,
            budget INTEGER NOT NULL,
            interest TEXT NOT NULL,
            lead_status TEXT NOT NULL DEFAULT 'new'
        )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS pending_runs (
        run_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        state_json TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
""")
    conn.commit()
    conn.close()

def create_customer(
    name: str,
    company: str,
    email: str,
    budget: int,
    interest: str
):
    conn = get_db_connection()

    cursor = conn.execute(
        """
        INSERT INTO customers (
            name,
            company,
            email,
            budget,
            interest
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, company, email, budget, interest)
    )

    conn.commit()

    customer_id = cursor.lastrowid

    conn.close()

    return customer_id

def get_all_customers():
    conn = get_db_connection()

    rows = conn.execute(
        "SELECT * FROM customers"
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]

def get_customer_by_id(customer_id: int):
    conn = get_db_connection()

    row = conn.execute(
        "SELECT * FROM customers WHERE id = ?",
        (customer_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return dict(row)


def update_customer_status_in_db(
    customer_id: int,
    lead_status: str
):
    conn = get_db_connection()

    cursor = conn.execute(
        """
        UPDATE customers
        SET lead_status = ?
        WHERE id = ?
        """,
        (lead_status, customer_id)
    )

    conn.commit()

    if cursor.rowcount == 0:
        conn.close()
        return None

    row = conn.execute(
        "SELECT * FROM customers WHERE id = ?",
        (customer_id,)
    ).fetchone()

    conn.close()

    return dict(row)



def save_pending_run(
    run_id: str,
    session_id: str,
    state_json: str
):
    conn = get_db_connection()

    conn.execute(
        """
        INSERT INTO pending_runs (
            run_id,
            session_id,
            state_json
        )
        VALUES (?, ?, ?)
        """,
        (
            run_id,
            session_id,
            state_json
        )
    )

    conn.commit()
    conn.close()


def get_pending_run(run_id: str):
    conn = get_db_connection()

    row = conn.execute(
        """
        SELECT *
        FROM pending_runs
        WHERE run_id = ?
        """,
        (run_id,)
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return dict(row)

def get_all_pending_runs():
    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM pending_runs
        ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


def delete_pending_run(run_id: str):
    conn = get_db_connection()

    conn.execute(
        """
        DELETE FROM pending_runs
        WHERE run_id = ?
        """,
        (run_id,)
    )

    conn.commit()
    conn.close()