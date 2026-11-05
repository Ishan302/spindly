# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Spendly is a lightweight personal expense tracker built with Flask and SQLite. It is a step-by-step teaching project: the landing, auth and legal pages are real, and most of the backend is still stubbed.

---

## Commands

```bash
# Setup
python -m venv venv                # a venv is already checked into the working dir (Python 3.9)
source venv/bin/activate           # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run dev server (debug mode, http://localhost:5001)
python app.py

# Tests (pytest + pytest-flask are installed; no tests exist yet)
pytest                             # all tests
pytest tests/test_foo.py           # one file
pytest tests/test_foo.py::test_name  # one test
pytest -k "test_name"              # by name
pytest -s                          # show output
```

No linter or build step is configured, and there is no JS tooling.

---

## Architecture

```
spendly/
├── app.py              # All routes — single file, no blueprints
├── database/
│   └── db.py           # SQLite helpers: get_db(), init_db(), seed_db()
├── templates/
│   ├── base.html       # Shared layout — all templates must extend this
│   └── *.html          # One template per page
├── static/
│   ├── css/
│   │   └── style.css   # Single global stylesheet (landing hero styles live here too)
│   └── js/
│       └── main.js     # Vanilla JS only — currently essentially empty
└── requirements.txt
```

- `app.py` — single Flask app with all routes.
- `database/db.py` — currently a comment-only stub, and nothing calls it yet. It is intended to hold:
  - `get_db()`: SQLite connection with `row_factory` set and foreign keys on.
  - `init_db()`: `CREATE TABLE IF NOT EXISTS ...`.
  - `seed_db()`: sample data.
- `templates/base.html` provides the navbar, footer, fonts, `css/style.css` and `js/main.js`, with `title` and `head` blocks. Page templates extend it.
- `landing.html` has its own inline `<script>` (e.g. the "See how it works" YouTube modal). This is existing code; don't add more inline scripts or styles elsewhere.

**Where things belong:**
- New routes → `app.py` only, no blueprints
- DB logic → `database/db.py` only, never inline in routes
- New pages → new `.html` file extending `base.html`
- Page-specific styles → a new `.css` file, not inline `<style>` tags
- Stub routes → implement them in place in `app.py`; don't create new files for them

---

## Implemented vs stub routes

| Route | Status |
|---|---|
| `GET /` | Implemented — renders `landing.html` |
| `GET /register` | Implemented — renders `register.html` |
| `GET /login` | Implemented — renders `login.html` |
| `GET /terms` | Implemented — renders `terms.html` |
| `GET /privacy` | Implemented — renders `privacy.html` |
| `GET /logout` | Stub — Step 3 |
| `GET /profile` | Stub — Step 4 |
| `GET /expenses/add` | Stub — Step 7 |
| `GET /expenses/<id>/edit` | Stub — Step 8 |
| `GET /expenses/<id>/delete` | Stub — Step 9 |

Stubs currently return placeholder strings labelled with their "Step N".

**Do not implement a stub route unless the active task explicitly targets that step.** When a step is implemented, render a template instead of returning a raw string.

---

## Code style

- Python: PEP 8, snake_case for all variables and functions
- Templates: Jinja2 with `url_for()` for every internal link — never hardcode URLs
- Route functions: one responsibility only — fetch data, render template, done
- DB queries: always use parameterized queries (`?` placeholders) — never f-strings in SQL
- Error handling: use `abort()` for HTTP errors, not bare `return "error string"`
- Legal pages (`terms.html`, `privacy.html`) share styling; keep new static pages consistent with the existing theme

---

## Tech constraints

- **Flask only** — no FastAPI, no Django, no other web frameworks
- **SQLite only** — no PostgreSQL, no SQLAlchemy ORM, no external DB
- **Vanilla JS only** — no React, no jQuery, no npm packages
- **No new pip packages** — work within `requirements.txt` as-is unless explicitly told otherwise
- **Python version** — the checked-in venv is Python 3.9, so don't use 3.10+ features such as `match` statements or `X | Y` type unions. f-strings are fine. If the project moves to 3.10+, update this line.

---

## Git conventions

Commit messages use `area: lowercase description`, e.g. `landing: add terms and conditions page and route`.

---

## Subagent policy

- Always use a builtin explore subagent for codebase exploration before implementing any new feature
- Always use a subagent to verify test results after any implementation
- When asked to plan, delegate codebase research to a subagent before presenting the plan
- Always use a builtin plan subagent in plan mode

---

## Warnings and things to avoid

- **Never hardcode URLs** in templates — always use `url_for()`
- **Never put DB logic in route functions** — it belongs in `database/db.py`
- **Never install new packages** mid-feature without flagging it — keep `requirements.txt` in sync
- **Never use JS frameworks** — the frontend is intentionally vanilla
- **`database/db.py` is currently empty** — do not assume helpers exist until the step that implements them
- **FK enforcement is manual** — SQLite foreign keys are off by default; `get_db()` must run `PRAGMA foreign_keys = ON` on every connection
- **The app runs on port 5001**, not the Flask default 5000 — don't change this
- **`file.txt` is a scratch log of past prompts**, not project documentation — don't treat it as a source of requirements
