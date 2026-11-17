import os
import sqlite3

import pytest

import database.db as db


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()

    from app import app as flask_app

    # Importing app seeds the DB on first import; start every test from empty.
    os.remove(db.DB_PATH)
    db.init_db()

    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def get_rows(app):
    def _get_rows():
        conn = sqlite3.connect(db.DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            return conn.execute("SELECT * FROM users").fetchall()
        finally:
            conn.close()

    return _get_rows


@pytest.fixture
def add_expense(app):
    def _add_expense(user_id, amount, category, date, description=""):
        conn = db.get_db()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO expenses (user_id, amount, category, date, description) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (user_id, amount, category, date, description),
                )
        finally:
            conn.close()

    return _add_expense
