# Spec: Login and Logout

## Overview
Make sign-in and sign-out functional. `GET /login` already renders `login.html` and Step 2 redirects new users there, but the form has no backend. This step adds a `POST /login` handler that checks the email and password against the `users` table, stores the user's id in the Flask session, and redirects to the landing page. It also implements `GET /logout`, which clears the session. The navbar changes with the session state. This is the first step that uses sessions, and it unblocks the profile page and expense routes (Steps 4–9), which need to know who is logged in.

## Depends on
- Step 01 — Database setup (`get_db()`, `users` table, seeded demo user).
- Step 02 — Registration (`get_user_by_email()`, hashed passwords created by `create_user()`, the `/login?registered=1` redirect).

## Routes
- `GET /login` — render the login form (already implemented). If the user is already logged in, redirect to `url_for('landing')` — public
- `POST /login` — validate credentials, set `session["user_id"]`, redirect to `url_for('landing')` on success, or re-render `login.html` with an error on failure — public
- `GET /logout` — clear the session and redirect to `url_for('landing')` — logged-in (a logged-out visitor is also just redirected, with no error)

`/profile` is still a Step 4 stub, so a successful login redirects to the landing page for now. Step 4 changes the redirect target.

## Database changes
No database changes. The existing `users` table already has `email` (UNIQUE) and `password_hash`.

New helper in `database/db.py` (no schema change):
- `verify_user(email, password)` — normalise the email, look up the user, return the `users` row if `check_password_hash` passes, otherwise `None`. Uses the existing `get_user_by_email()`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html`
    - Replace the hardcoded `action="/login"` with `action="{{ url_for('login') }}"`.
    - Re-fill `email` with the submitted value after a failed attempt (never re-fill the password).
  - `templates/base.html`
    - In the navbar, when `session.user_id` is set, show a "Sign out" link (`url_for('logout')`) in place of "Sign in" and "Get started".
    - When it is not set, keep the current links.

## Files to change
- `app.py` — set `app.secret_key`; accept `GET` and `POST` on `/login`; implement `/logout`.
- `database/db.py` — add `verify_user()`.
- `templates/login.html` — `url_for` action and email re-fill.
- `templates/base.html` — session-aware navbar links.
- `static/css/style.css` — only if the navbar needs a small style for the "Sign out" link, using CSS variables.

## Files to create
- None

## New dependencies
No new dependencies. `flask.session` and `werkzeug.security` are already available.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug; verify with `check_password_hash`, never compare plain text
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB logic lives in `database/db.py`; the route only reads the form, calls helpers, sets the session and renders or redirects
- Use `url_for()` for every link and redirect
- `app.secret_key` must be set. Read it from the `SECRET_KEY` environment variable, with a clearly marked development fallback. Do not commit a real secret.
- Normalise the email (`strip()`, lowercase) before the lookup
- Failed login renders `login.html` with `error`. Use one generic message, "Invalid email or password.", for both an unknown email and a wrong password, so the response does not reveal which emails are registered.
- Empty email or empty password shows "Email and password are required."
- Store only `user_id` in the session (an int), never the password hash
- Call `session.clear()` before setting `user_id` on login, and on logout
- Keep the `?registered=1` success message working
- Do not implement `/profile`, expense routes or login-required decorators (Steps 4–9)
- Do not change the other stub routes
- Python 3.9 compatible code only

## Definition of done
- [ ] `GET /login` still renders the form, and `/login?registered=1` still shows the success message
- [ ] Logging in as `demo@spendly.com` / `demo123` redirects to `/` and sets a session cookie
- [ ] A user created through `/register` can log in with the password they chose
- [ ] Email matching ignores letter case and surrounding spaces (e.g. `  Demo@Spendly.com `)
- [ ] A wrong password shows "Invalid email or password." and sets no session
- [ ] An unknown email shows the same "Invalid email or password." message
- [ ] An empty email or password shows an error and sets no session
- [ ] After a failed attempt the email field keeps its value and the password field is empty
- [ ] While logged in, the navbar shows "Sign out" and hides "Sign in" and "Get started"
- [ ] While logged out, the navbar shows "Sign in" and "Get started"
- [ ] `GET /logout` clears the session, redirects to `/`, and the navbar returns to the logged-out links
- [ ] Visiting `/logout` while logged out redirects to `/` without an error
- [ ] Visiting `/login` while logged in redirects to `/`
- [ ] The login form `action` is generated with `url_for('login')`, with no hardcoded URL
- [ ] No other stub routes are changed
- [ ] The app starts on port 5001 without errors
