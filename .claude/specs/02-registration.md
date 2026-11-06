# Spec: Registration

## Overview
Make the sign-up form functional. `GET /register` already renders `register.html`, but the form has no backend: submitting it does nothing. This step adds a `POST /register` handler that validates the input, hashes the password with werkzeug, stores the new user in the `users` table, and on success redirects to `/login?registered=1`, where the login page shows "Account created. Please sign in." It is the first step that writes user data from the UI, and it unblocks login (Step 3) and everything that depends on a logged-in user.

## Depends on
- Step 01 — Database setup (`get_db()`, `init_db()`, `users` table).

## Routes
- `GET /register` — render the registration form (already implemented, unchanged) — public
- `POST /register` — validate the form, create the user, redirect to `/login?registered=1` (`url_for('login', registered=1)`) on success, or re-render the form with an error on failure — public

Registration does not log the user in. Sessions arrive with login in Step 3.

## Database changes
No database changes. The existing `users` table already has `name`, `email` (UNIQUE), `password_hash` and `created_at`.

New helpers in `database/db.py` (no schema change):
- `get_user_by_email(email)` — return the matching `users` row or `None`.
- `create_user(name, email, password)` — hash the password with werkzeug, insert the row, return the new user id. Raises `sqlite3.IntegrityError` if the email already exists.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html`
    - Replace the hardcoded `action="/register"` with `action="{{ url_for('register') }}"`.
    - Add a "Confirm password" field (`name="confirm_password"`) below the password field.
    - Re-fill `name` and `email` with the submitted values when re-rendering after an error (never re-fill the password).
  - `templates/login.html`
    - Show an `.auth-success` message when the `registered` query parameter is set.

## Files to change
- `app.py` — accept `GET` and `POST` on `/register`; add the POST handler.
- `database/db.py` — add `get_user_by_email()` and `create_user()`.
- `templates/register.html` — `url_for` action and value re-fill.
- `templates/login.html` — success message block.
- `static/css/style.css` — `.auth-success` style using CSS variables.

## Files to create
- None

## New dependencies
No new dependencies. `werkzeug.security` is already installed.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug, using `method="pbkdf2:sha256"` (the venv is Python 3.9 and its `hashlib` has no scrypt)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB logic lives in `database/db.py`; the route only reads the form, calls helpers and renders or redirects
- Use `url_for()` for every link and redirect
- Normalise the email (`strip()`, lowercase) before checking and storing it
- Validation, each failure re-rendering `register.html` with an `error` message:
  - name, email and password are all required (after `strip()`)
  - email must contain `@` and a `.` after it
  - password must be at least 8 characters, which matches the form placeholder
  - `confirm_password` must match `password`, otherwise "Passwords do not match."
  - email must not already be registered
- Catch `sqlite3.IntegrityError` from `create_user()` to cover a race on the UNIQUE email constraint
- Never echo the password back in the response
- Do not implement login, logout or session handling (Step 3)
- The success message uses the `?registered=1` query flag instead of `flash()`, so no secret key or session cookie is added
- Python 3.9 compatible code only

## Definition of done
- [ ] `GET /register` still renders the form
- [ ] Submitting valid details creates a row in `users` with the name, a lowercase email and a hashed password (the `password_hash` column is not the plain text)
- [ ] After a successful registration the browser is redirected to `/login?registered=1`
- [ ] The login page shows the success message when `registered=1` is present, and not otherwise
- [ ] `check_password_hash` on the stored hash returns `True` for the password that was entered
- [ ] Registering the same email again (including with different letter case) shows an error and creates no second row
- [ ] A password shorter than 8 characters shows an error and creates no row
- [ ] A confirm password that differs from the password shows an error and creates no row
- [ ] An empty name, an empty email or an invalid email shows an error and creates no row
- [ ] After an error the name and email fields keep their values and the password field is empty
- [ ] The form `action` is generated with `url_for('register')`, with no hardcoded URL
- [ ] No other stub routes are changed
- [ ] The app starts on port 5001 without errors
