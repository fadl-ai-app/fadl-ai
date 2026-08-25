import sqlite3
from pathlib import Path

DB = Path(__file__).with_name("fadl_users.db")

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            gems INTEGER NOT NULL DEFAULT 0
        )
        """)

init_db()


def get_balance(username):
    with sqlite3.connect(DB) as con:
        row = con.execute(
            "SELECT gems FROM users WHERE username=?",
            (username,)
        ).fetchone()
        return int(row[0]) if row else 0


def add_gems(username, amount):
    amount = int(amount)
    if amount <= 0:
        return get_balance(username)

    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO users(username, gems) VALUES(?, ?) "
            "ON CONFLICT(username) DO UPDATE SET gems=gems+excluded.gems",
            (username, amount)
        )
    return get_balance(username)


def spend_gems(username, amount):
    amount = int(amount)

    if amount <= 0:
        return True, get_balance(username)

    with sqlite3.connect(DB) as con:
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
