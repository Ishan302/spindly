import os
import sqlite3
from datetime import date, datetime

from werkzeug.security import check_password_hash, generate_password_hash

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


def get_user_by_email(email):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    finally:
        conn.close()


def create_user(name, email, password):
    conn = get_db()
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (
                    name,
                    email,
                    generate_password_hash(password, method="pbkdf2:sha256"),
                ),
            )
        return cursor.lastrowid
    finally:
        conn.close()


def verify_user(email, password):
    user = get_user_by_email(email)
    if user is not None and check_password_hash(user["password_hash"], password):
        return user
    return None


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    created = datetime.strptime(row["created_at"][:10], "%Y-%m-%d")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": created.strftime("%B %Y"),
    }


# ==== SECTION 1: transaction history (subagent 1 only) ============== #

def _date_clause(start_date=None, end_date=None):
    """Return (sql_fragment, params) for an optional inclusive date range.

    The fragment is built from fixed strings only; values go in params.
    """
    clause = ""
    params = []
    if start_date:
        clause += " AND date >= ?"
        params.append(start_date)
    if end_date:
        clause += " AND date <= ?"
        params.append(end_date)
    return clause, params


def get_recent_transactions(user_id, limit=10, start_date=None, end_date=None):
    clause, params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + clause + " ORDER BY date DESC, id DESC LIMIT ?",
            [user_id] + params + [limit],
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "date": row["date"],
            "description": row["description"] or "",
            "category": row["category"],
            "amount": float(row["amount"]),
        }
        for row in rows
    ]


# ==== SECTION 2: summary stats (subagent 2 only) ==================== #

def get_summary_stats(user_id, start_date=None, end_date=None):
    clause, params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        totals = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt "
            "FROM expenses WHERE user_id = ?" + clause,
            [user_id] + params,
        ).fetchone()
        top = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ?" + clause +
            " GROUP BY category ORDER BY SUM(amount) DESC, category ASC LIMIT 1",
            [user_id] + params,
        ).fetchone()
    finally:
        conn.close()
    if totals["cnt"] == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}
    return {
        "total_spent": float(totals["total"]),
        "transaction_count": int(totals["cnt"]),
        "top_category": top["category"],
    }


# ==== SECTION 3: category breakdown (subagent 3 only) =============== #

def get_category_breakdown(user_id, start_date=None, end_date=None):
    clause, params = _date_clause(start_date, end_date)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS total FROM expenses "
            "WHERE user_id = ?" + clause + " GROUP BY category "
            "ORDER BY total DESC, category ASC",
            [user_id] + params,
        ).fetchall()
    finally:
        conn.close()

    grand_total = sum(row["total"] for row in rows)
    if not rows or grand_total <= 0:
        return []

    breakdown = [
        {
            "name": row["category"],
            "amount": float(row["total"]),
            "pct": int(round(row["total"] * 100 / grand_total)),
        }
        for row in rows
    ]
    breakdown[0]["pct"] += 100 - sum(item["pct"] for item in breakdown)
    return breakdown


# ==== END SECTIONS ================================================== #

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
