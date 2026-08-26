
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
