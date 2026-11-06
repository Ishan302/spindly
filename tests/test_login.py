import pytest

import database.db as db

EMAIL = "demo@spendly.com"
PASSWORD = "demo123"


@pytest.fixture
def demo_user(app):
    return db.create_user("Demo User", EMAIL, PASSWORD)


def post_login(client, email=EMAIL, password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def session_user_id(client):
    with client.session_transaction() as sess:
        return sess.get("user_id")


# --- verify_user -------------------------------------------------------


def test_verify_user_correct_password(demo_user):
    user = db.verify_user(EMAIL, PASSWORD)
    assert user is not None
    assert user["id"] == demo_user


def test_verify_user_wrong_password(demo_user):
    assert db.verify_user(EMAIL, "wrong-password") is None


def test_verify_user_unknown_email(demo_user):
    assert db.verify_user("nobody@example.com", PASSWORD) is None


def test_verify_user_normalises_email(demo_user):
    assert db.verify_user("  Demo@Spendly.com ", PASSWORD) is not None


# --- GET /login --------------------------------------------------------


def test_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Welcome back" in response.data
    assert b"Account created" not in response.data


def test_login_page_shows_registered_message(client):
    response = client.get("/login?registered=1")
    assert b"Account created. Please sign in." in response.data


def test_login_form_action_uses_login_url(client):
    response = client.get("/login")
    assert b'action="/login"' in response.data


def test_logged_in_get_login_redirects(client, demo_user):
    post_login(client)
    response = client.get("/login")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


# --- POST /login -------------------------------------------------------


def test_login_success(client, demo_user):
    response = post_login(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert session_user_id(client) == demo_user
    assert any(
        h.startswith("session=") for h in response.headers.getlist("Set-Cookie")
    )


def test_session_holds_only_user_id(client, demo_user):
    post_login(client)
    with client.session_transaction() as sess:
        assert set(sess.keys()) == {"user_id"}


def test_register_then_login(client):
    client.post(
        "/register",
        data={
            "name": "New Person",
            "email": "new@example.com",
            "password": "longenough1",
            "confirm_password": "longenough1",
        },
    )
    response = post_login(client, "new@example.com", "longenough1")
    assert response.status_code == 302
    assert session_user_id(client) is not None


def test_login_email_normalised(client, demo_user):
    response = post_login(client, "  Demo@Spendly.com ", PASSWORD)
    assert response.status_code == 302
    assert session_user_id(client) == demo_user


def test_login_wrong_password(client, demo_user):
    response = post_login(client, EMAIL, "wrong-password")
    assert response.status_code == 200
    assert b"Invalid email or password." in response.data
    assert session_user_id(client) is None


def test_login_unknown_email_same_message(client, demo_user):
    wrong_pw = post_login(client, EMAIL, "wrong-password")
    unknown = post_login(client, "nobody@example.com", PASSWORD)
    assert b"Invalid email or password." in unknown.data
    assert session_user_id(client) is None
    assert b"Invalid email or password." in wrong_pw.data


@pytest.mark.parametrize(
    "email,password",
    [("", PASSWORD), (EMAIL, ""), ("", ""), ("   ", PASSWORD)],
)
def test_login_empty_fields(client, demo_user, email, password):
    response = post_login(client, email, password)
    assert response.status_code == 200
    assert b"Email and password are required." in response.data
    assert session_user_id(client) is None


def test_failed_login_refills_email_not_password(client, demo_user):
    response = post_login(client, EMAIL, "wrong-password")
    assert f'value="{EMAIL}"'.encode() in response.data
    assert b"wrong-password" not in response.data


def test_post_login_while_logged_in_keeps_session(client, demo_user):
    other_id = db.create_user("Other", "other@example.com", "otherpass1")
    post_login(client)
    response = post_login(client, "other@example.com", "otherpass1")
    assert response.status_code == 302
    assert session_user_id(client) == demo_user
    assert session_user_id(client) != other_id


# --- navbar ------------------------------------------------------------


def test_navbar_logged_out(client):
    html = client.get("/").data
    assert b"Sign in" in html
    assert b"Get started" in html
    assert b"Sign out" not in html


def test_navbar_logged_in(client, demo_user):
    post_login(client)
    html = client.get("/").data
    assert b"Sign out" in html
    assert b'href="/logout"' in html
    assert b"Get started" not in html


# --- logout ------------------------------------------------------------


def test_logout_clears_session(client, demo_user):
    post_login(client)
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    assert session_user_id(client) is None
    assert b"Sign out" not in client.get("/").data


def test_logout_while_logged_out(client):
    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


# --- other stubs unchanged --------------------------------------------


@pytest.mark.parametrize(
    "path,text",
    [
        ("/profile", b"Step 4"),
        ("/expenses/add", b"Step 7"),
        ("/expenses/1/edit", b"Step 8"),
        ("/expenses/1/delete", b"Step 9"),
    ],
)
def test_other_stubs_unchanged(client, path, text):
    response = client.get(path)
    assert response.status_code == 200
    assert text in response.data


# --- /register while logged in ----------------------------------------


def test_logged_in_get_register_redirects(client, demo_user):
    post_login(client)
    response = client.get("/register")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_logged_in_post_register_creates_no_user(client, demo_user, get_rows):
    post_login(client)
    response = client.post(
        "/register",
        data={
            "name": "Another",
            "email": "another@example.com",
            "password": "longenough1",
            "confirm_password": "longenough1",
        },
    )
    assert response.status_code == 302
    assert len(get_rows()) == 1
