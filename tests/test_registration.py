import pytest
from werkzeug.security import check_password_hash

import app as app_module

VALID = {
    "name": "Asha Rao",
    "email": "Asha.Rao@Example.com",
    "password": "secret123",
    "confirm_password": "secret123",
}


def post(client, **overrides):
    return client.post("/register", data={**VALID, **overrides})


def test_get_register_renders_form(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Create your account" in response.data


def test_valid_registration_creates_user(client, get_rows):
    post(client)
    rows = get_rows()
    assert len(rows) == 1
    assert rows[0]["name"] == "Asha Rao"
    assert rows[0]["email"] == "asha.rao@example.com"
    assert rows[0]["password_hash"] != VALID["password"]
    assert check_password_hash(rows[0]["password_hash"], VALID["password"])


def test_success_redirects_to_login_with_message(client):
    response = post(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?registered=1")
    followed = client.get(response.headers["Location"])
    assert b"Account created. Please sign in." in followed.data


def test_login_without_flag_shows_no_message(client):
    assert b"Account created" not in client.get("/login").data


def test_duplicate_email_rejected_case_insensitive(client, get_rows):
    post(client)
    response = post(client, email="ASHA.RAO@example.com")
    assert response.status_code == 200
    assert b"already exists" in response.data
    assert len(get_rows()) == 1


def test_short_password_rejected(client, get_rows):
    response = post(client, password="1234567", confirm_password="1234567")
    assert b"at least 8 characters" in response.data
    assert get_rows() == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"name": "   "},
        {"email": ""},
        {"email": "noatsign"},
        {"email": "a@b"},
        {"email": "@x.com"},
        {"email": "a@.com"},
        {"email": "a@x."},
        {"email": "a@@x.com"},
    ],
)
def test_invalid_fields_rejected(client, get_rows, overrides):
    response = post(client, **overrides)
    assert response.status_code == 200
    assert b'class="auth-error"' in response.data
    assert get_rows() == []


def test_error_refills_name_and_email_not_password(client):
    response = post(client, password="short", confirm_password="short")
    assert b'value="Asha Rao"' in response.data
    assert b'value="asha.rao@example.com"' in response.data
    assert b"short" not in response.data.replace(b"Password must", b"")


def test_form_action_uses_url_for(client, app):
    assert b'action="/register"' in client.get("/register").data
    with open("templates/register.html") as f:
        assert 'action="/register"' not in f.read()


def test_integrity_error_race_handled(client, get_rows, monkeypatch):
    post(client)
    monkeypatch.setattr(app_module, "get_user_by_email", lambda email: None)
    response = post(client)
    assert response.status_code == 200
    assert b"already exists" in response.data
    assert len(get_rows()) == 1


def test_other_stub_routes_unchanged(client):
    assert b"coming in Step 4" in client.get("/profile").data


def test_password_mismatch_rejected(client, get_rows):
    response = post(client, confirm_password="different123")
    assert b"Passwords do not match." in response.data
    assert get_rows() == []
    assert b'value="Asha Rao"' in response.data
