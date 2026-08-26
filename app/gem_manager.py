
import os
import sqlite3
from pathlib import Path

DATABASE_URL = os.environ.get("DATABASE_URL")
SQLITE_DB = Path(__file__).with_name("fadl_users.db")


def _use_postgres():
    return bool(DATABASE_URL)


def _pg_connect():
    import psycopg
    return psycopg.connect(DATABASE_URL)


def init_db():
    if _use_postgres():
        with _pg_connect() as con:
            with con.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        gems INTEGER NOT NULL DEFAULT 0
                    )
                """)
        return

    with sqlite3.connect(SQLITE_DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                gems INTEGER NOT NULL DEFAULT 0
            )
        """)


def get_balance(username):
    username = str(username)

    if _use_postgres():
        with _pg_connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    "SELECT gems FROM users WHERE username=%s",
                    (username,)
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0

    with sqlite3.connect(SQLITE_DB) as con:
        row = con.execute(
            "SELECT gems FROM users WHERE username=?",
            (username,)
        ).fetchone()
        return int(row[0]) if row else 0


def add_gems(username, amount):
    username = str(username)
    amount = int(amount)

    if amount <= 0:
        return get_balance(username)

    if _use_postgres():
        with _pg_connect() as con:
            with con.cursor() as cur:
                cur.execute("""
                    INSERT INTO users(username, gems)
                    VALUES(%s, %s)
                    ON CONFLICT(username)
                    DO UPDATE SET gems = users.gems + EXCLUDED.gems
                """, (username, amount))
        return get_balance(username)

    with sqlite3.connect(SQLITE_DB) as con:
        con.execute(
            "INSERT INTO users(username, gems) VALUES(?, ?) "
            "ON CONFLICT(username) DO UPDATE SET gems=gems+excluded.gems",
            (username, amount)
        )
    return get_balance(username)


def spend_gems(username, amount):
    username = str(username)
    amount = int(amount)

    if amount <= 0:
        return True, get_balance(username)

    if _use_postgres():
        with _pg_connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    "SELECT gems FROM users WHERE username=%s FOR UPDATE",
                    (username,)
                )
                row = cur.fetchone()
                balance = int(row[0]) if row else 0

                if balance < amount:
                    return False, balance

                cur.execute(
                    "UPDATE users SET gems=gems-%s WHERE username=%s",
                    (amount, username)
                )

        return True, get_balance(username)

    with sqlite3.connect(SQLITE_DB) as con:
        row = con.execute(
            "SELECT gems FROM users WHERE username=?",
            (username,)
        ).fetchone()

        balance = int(row[0]) if row else 0

        if balance < amount:
            return False, balance

        con.execute(
            "UPDATE users SET gems=gems-? WHERE username=?",
            (amount, username)
        )

    return True, get_balance(username)


def credits_to_gems(credits):
    credits = int(credits)
    return max(0, credits)


init_db()


def refund_gems(username, amount):
    """إرجاع الجواهر للمستخدم عند فشل التوليد."""
    return add_gems(username, amount)


TRIAL_CREDIT_LIMIT = 500


def _init_trial_usage():
    if _use_postgres():
        with _pg_connect() as con:
            with con.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS system_usage (
                        name TEXT PRIMARY KEY,
                        value INTEGER NOT NULL DEFAULT 0
                    )
                """)
                cur.execute("""
                    INSERT INTO system_usage(name, value)
                    VALUES('trial_credits_used', 0)
                    ON CONFLICT(name) DO NOTHING
                """)

                cur.execute("""
                    CREATE TABLE IF NOT EXISTS trial_credit_reservations (
                        job_id TEXT PRIMARY KEY,
                        credits INTEGER NOT NULL
                    )
                """)
        return


def get_trial_credits_used():
    if not _use_postgres():
        return 0

    _init_trial_usage()

    with _pg_connect() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT value FROM system_usage WHERE name=%s",
                ("trial_credits_used",)
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0


def reserve_trial_credits(job_id, credits):
    credits = int(credits)

    if credits <= 0:
        return True, get_trial_credits_used()

    if not _use_postgres():
        return True, 0

    _init_trial_usage()

    with _pg_connect() as con:
        with con.cursor() as cur:

            cur.execute(
                "SELECT credits FROM trial_credit_reservations "
                "WHERE job_id=%s",
                (str(job_id),)
            )
            existing = cur.fetchone()

            if existing:
                return True, get_trial_credits_used()

            cur.execute(
                "SELECT value FROM system_usage "
                "WHERE name=%s FOR UPDATE",
                ("trial_credits_used",)
            )

            row = cur.fetchone()
            used = int(row[0]) if row else 0

            if used + credits > TRIAL_CREDIT_LIMIT:
                return False, used

            cur.execute(
                "UPDATE system_usage SET value=value+%s "
                "WHERE name=%s",
                (credits, "trial_credits_used")
            )

            cur.execute(
                "INSERT INTO trial_credit_reservations(job_id, credits) "
                "VALUES(%s, %s)",
                (str(job_id), credits)
            )

    return True, used + credits


def release_trial_credits(job_id):
    if not _use_postgres():
        return True

    _init_trial_usage()

    with _pg_connect() as con:
        with con.cursor() as cur:
            cur.execute(
                "SELECT credits FROM trial_credit_reservations "
                "WHERE job_id=%s FOR UPDATE",
                (str(job_id),)
            )
            row = cur.fetchone()

            if not row:
                return False

            credits = int(row[0])

            cur.execute(
                "SELECT value FROM system_usage "
                "WHERE name=%s FOR UPDATE",
                ("trial_credits_used",)
            )
            usage = cur.fetchone()
            used = int(usage[0]) if usage else 0

            cur.execute(
                "UPDATE system_usage SET value=%s WHERE name=%s",
                (max(0, used - credits), "trial_credits_used")
            )

            cur.execute(
                "DELETE FROM trial_credit_reservations WHERE job_id=%s",
                (str(job_id),)
            )

    return True
