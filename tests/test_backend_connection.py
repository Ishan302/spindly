import re

import pytest

import database.db as db

EMAIL = "demo@spendly.com"
PASSWORD = "demo123"

# Known fixture data: total 6330.50, 4 transactions, top category Bills.
EXPENSES = [
    (3200.00, "Bills", "2026-11-05", "Electricity bill"),
    (1850.50, "Food", "2026-11-03", "Groceries"),
    (500.00, "Transport", "2026-11-01", "Metro card"),
    (780.00, "Health", "2026-10-29", "Pharmacy"),
]


@pytest.fixture
def user_id(app, add_expense):
    uid = db.create_user("Demo User", EMAIL, PASSWORD)
    for amount, category, date, description in EXPENSES:
        add_expense(uid, amount, category, date, description)
    return uid


@pytest.fixture
def empty_user_id(app):
    return db.create_user("Empty User", "empty@example.com", PASSWORD)


def login(client, email=EMAIL):
    client.post("/login", data={"email": email, "password": PASSWORD})
    return client


# ------------------------------------------------------------------ #
# Unit tests — query helpers                                          #
# ------------------------------------------------------------------ #

def test_get_user_by_id_returns_user(user_id):
    user = db.get_user_by_id(user_id)
    assert user["name"] == "Demo User"
    assert user["email"] == EMAIL
    assert re.fullmatch(r"[A-Z][a-z]+ \d{4}", user["member_since"])


def test_get_user_by_id_missing_returns_none(app):
    assert db.get_user_by_id(99999) is None


def test_summary_stats_with_expenses(user_id):
    stats = db.get_summary_stats(user_id)
    assert stats["total_spent"] == pytest.approx(6330.50)
    assert stats["transaction_count"] == 4
    assert stats["top_category"] == "Bills"


def test_summary_stats_without_expenses(empty_user_id):
    assert db.get_summary_stats(empty_user_id) == {
        "total_spent": 0,
        "transaction_count": 0,
        "top_category": "—",
    }


def test_recent_transactions_newest_first(user_id):
    rows = db.get_recent_transactions(user_id)
    assert [r["date"] for r in rows] == [
        "2026-11-05", "2026-11-03", "2026-11-01", "2026-10-29",
    ]
    assert set(rows[0]) == {"date", "description", "category", "amount"}


def test_recent_transactions_respects_limit(user_id):
    assert len(db.get_recent_transactions(user_id, limit=2)) == 2


def test_recent_transactions_empty(empty_user_id):
    assert db.get_recent_transactions(empty_user_id) == []


def test_category_breakdown_sorted_and_sums_to_100(user_id):
    rows = db.get_category_breakdown(user_id)
    amounts = [r["amount"] for r in rows]
    assert amounts == sorted(amounts, reverse=True)
    assert all(isinstance(r["pct"], int) for r in rows)
    assert sum(r["pct"] for r in rows) == 100


def test_category_breakdown_rounding_remainder_goes_to_largest(app, add_expense):
    uid = db.create_user("Thirds", "thirds@example.com", PASSWORD)
    for category in ("Food", "Bills", "Health"):
        add_expense(uid, 1.00, category, "2026-11-01")
    rows = db.get_category_breakdown(uid)
    assert sum(r["pct"] for r in rows) == 100
    assert rows[0]["pct"] == 34


def test_category_breakdown_empty(empty_user_id):
    assert db.get_category_breakdown(empty_user_id) == []


def test_queries_are_scoped_to_user(user_id, add_expense):
    other = db.create_user("Other", "other@example.com", PASSWORD)
    add_expense(other, 9999.00, "Shopping", "2026-11-10", "Not yours")
    assert db.get_summary_stats(user_id)["transaction_count"] == 4
    assert len(db.get_recent_transactions(user_id)) == 4
    assert "Shopping" not in [c["name"] for c in db.get_category_breakdown(user_id)]


# ------------------------------------------------------------------ #
# Route tests — GET /profile                                          #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated_redirects(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_shows_real_user_and_stats(client, user_id):
    response = login(client).get("/profile")
    html = response.data.decode()
    assert response.status_code == 200
    assert "Demo User" in html and EMAIL in html
    assert "Priya Sharma" not in html
    assert "₹6,330.50" in html
    assert re.search(r"Transactions</span>\s*<span[^>]*>4<", html)
    assert re.search(r"Top category</span>\s*<span[^>]*>Bills<", html)


def test_profile_transactions_newest_first(client, user_id):
    html = login(client).get("/profile").data.decode()
    dates = ["05 Nov 2026", "03 Nov 2026", "01 Nov 2026", "29 Oct 2026"]
    positions = [html.index(d) for d in dates]
    assert positions == sorted(positions)
    assert "₹3,200.00" in html


def test_profile_category_breakdown_percentages(client, user_id):
    html = login(client).get("/profile").data.decode()
    percents = [int(p) for p in re.findall(r'<progress[^>]*value="(\d+)"', html)]
    assert len(percents) == 4
    assert sum(percents) == 100


def test_profile_new_user_empty_state(client, empty_user_id):
    response = login(client, "empty@example.com").get("/profile")
    html = response.data.decode()
    assert response.status_code == 200
    assert "₹0.00" in html
    assert re.search(r"Transactions</span>\s*<span[^>]*>0<", html)
    assert re.search(r"Top category</span>\s*<span[^>]*>—<", html)
    assert "No transactions yet." in html
    assert "No spending to break down yet." in html


def test_profile_does_not_leak_other_users_expenses(client, user_id, add_expense):
    other = db.create_user("Other", "other@example.com", PASSWORD)
    add_expense(other, 9999.00, "Shopping", "2026-11-10", "Not yours")
    html = login(client).get("/profile").data.decode()
    assert "Not yours" not in html
    assert "₹9,999.00" not in html


def test_profile_with_deleted_user_redirects_and_clears_session(client, user_id):
    login(client)
    conn = db.get_db()
    try:
        with conn:
            conn.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    finally:
        conn.close()
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
