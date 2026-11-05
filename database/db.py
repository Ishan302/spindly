import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "expense_tracker.db",
)

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    name          TEXT NOT NULL,
                    email         TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at    TEXT DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL REFERENCES users(id),
                    amount      REAL NOT NULL,
                    category    TEXT NOT NULL,
                    date        TEXT NOT NULL,
                    description TEXT,
                    created_at  TEXT DEFAULT (datetime('now'))
                )
                """
            )
    finally:
        conn.close()


def seed_db():
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        today = date.today()
        samples = [
            (1, 1500.00, "Bills", "Electricity bill"),
            (3, 420.50, "Food", "Groceries"),
            (6, 180.00, "Transport", "Metro card recharge"),
            (9, 650.00, "Health", "Pharmacy"),
            (12, 499.00, "Entertainment", "Movie and snacks"),
            (15, 2299.00, "Shopping", "T-shirt and shoes"),
            (18, 310.00, "Food", "Dinner with friends"),
            (22, 250.00, "Other", "Gift wrapping and misc"),
        ]

        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                ("Demo User", "demo@spendly.com", generate_password_hash("demo123", method="pbkdf2:sha256"),
                ),
            )
            user_id = cursor.lastrowid
            rows = [
                (
                    user_id,
                    amount,
                    category,
                    today.replace(day=min(day, today.day)).isoformat(),
                    description,
                )
                for day, amount, category, description in samples
            ]
            conn.executemany(
                "INSERT INTO expenses (user_id, amount, category, date, description) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )
    finally:
        conn.close()
