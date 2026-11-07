import re
from pathlib import Path

import pytest

import database.db as db

EMAIL = "demo@spendly.com"
PASSWORD = "demo123"
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "profile.html"


@pytest.fixture
def logged_in(client, app):
    db.create_user("Demo User", EMAIL, PASSWORD)
    client.post("/login", data={"email": EMAIL, "password": PASSWORD})
    return client


def test_profile_redirects_when_logged_out(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_ok_when_logged_in(logged_in):
    assert logged_in.get("/profile").status_code == 200


def test_profile_shows_user_card(logged_in):
    data = logged_in.get("/profile").data
    assert b"Priya Sharma" in data
    assert b"priya.sharma@example.com" in data
    assert b"Member since" in data


def test_profile_shows_stats(logged_in):
    data = logged_in.get("/profile").data
    for label in (b"Total spent", b"Transactions", b"Top category"):
        assert label in data
    assert "₹".encode() in data


def test_profile_table_has_rows(logged_in):
    html = logged_in.get("/profile").data.decode()
    body = html.split("<tbody>")[1].split("</tbody>")[0]
    assert body.count("<tr>") >= 3


def test_profile_breakdown_has_categories(logged_in):
    data = logged_in.get("/profile").data
    assert data.count(b'class="profile-bar-row"') >= 3


def test_profile_badges_use_css_class(logged_in):
    assert b"cat-badge cat-badge--" in logged_in.get("/profile").data


def test_profile_links_stylesheet(logged_in):
    assert b"css/profile.css" in logged_in.get("/profile").data


def test_profile_template_has_no_hex_or_inline_style():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", source)
    assert "style=" not in source


def test_navbar_shows_username_and_logout(logged_in):
    data = logged_in.get("/profile").data
    assert b"Demo User" in data
    assert b"Sign out" in data


def test_navbar_logged_out_has_no_username(client):
    data = client.get("/").data
    assert b"nav-user" not in data
    assert b"Sign in" in data


def test_login_sets_user_name_in_session(logged_in):
    with logged_in.session_transaction() as sess:
        assert sess.get("user_name") == "Demo User"
