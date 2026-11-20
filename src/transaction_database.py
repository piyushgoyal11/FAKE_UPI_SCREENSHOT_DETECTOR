import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent.parent / "transactions.db"

def create_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL UNIQUE,
                app_name TEXT NOT NULL,
                amount TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                scan_count INTEGER NOT NULL DEFAULT 1,
                last_seen TEXT NOT NULL
            )
        """)

def check_transaction(transaction_id, app_name, amount):
    if transaction_id is None:
        return {
            "status": "NOT_CHECKED",
            "message": "Transaction ID was not extracted"
        }

    transaction_id = str(transaction_id).strip()

    if not transaction_id.isdigit() or len(transaction_id) != 12:
        return {
            "status": "NOT_CHECKED",
            "message": "Transaction ID format not supported"
        }

    if app_name == "Unknown" or amount is None:
        return {
            "status": "NOT_CHECKED",
            "message": "App or amount could not be verified"
        }

    create_database()

    now = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT app_name, amount, scan_count
            FROM transactions
            WHERE transaction_id = ?
            """,
            (transaction_id,)
        ).fetchone()

        if row:
            old_app, old_amount, count = row

            conn.execute(
                """
                UPDATE transactions
                SET scan_count = scan_count + 1,
                    last_seen = ?
                WHERE transaction_id = ?
                """,
                (now, transaction_id)
            )

            if old_app != app_name or old_amount != str(amount):
                return {
                    "status": "MISMATCH",
                    "message": "Previously scanned ID has different details",
                    "scan_count": count + 1
                }

            return {
                "status": "REPEATED",
                "message": "Transaction ID was scanned previously",
                "scan_count": count + 1
            }

        conn.execute(
            """
            INSERT INTO transactions
            (transaction_id, app_name, amount, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?)
            """,
            (transaction_id, app_name, str(amount), now, now)
        )

    return {
        "status": "NEW",
        "message": "Transaction ID not previously recorded",
        "scan_count": 1
    }