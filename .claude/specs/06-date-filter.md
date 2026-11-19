# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date-range filter to the profile page. A logged-in user can pick a
start date and/or an end date, and the three data sections on `/profile`
(summary stats, recent transactions, category breakdown) are recalculated for
only the expenses inside that range. Without a filter the page behaves exactly
as it does after Step 5. The filter is driven by GET query parameters so a
filtered view is bookmarkable and needs no JavaScript.

## Depends on
- Step 1: Database setup (`expenses.date` stored as ISO `YYYY-MM-DD` text)
- Step 3: Login / Logout (`session["user_id"]`)
- Step 4: Profile page UI
- Step 5: Backend routes for profile (`get_summary_stats`, `get_recent_transactions`,
  `get_category_breakdown` and the `build_*` helpers exist)

## Routes
No new routes. `GET /profile` is modified to accept optional query parameters:
- `start` — inclusive start date, `YYYY-MM-DD`
- `end` — inclusive end date, `YYYY-MM-DD`

Access level: logged-in (unchanged; unauthenticated users redirect to `/login`).

Behaviour:
- Either parameter may be given alone (open-ended range).
- Blank or missing parameter means "no bound".
- A malformed date is ignored (treated as no bound) and an inline error message
  is shown; the page still returns 200.
- If `start` is after `end`, show an inline error and fall back to the
  unfiltered view. Do not raise or return 500.

## Database changes
No database changes. `expenses.date` is already an ISO text column, so
`date >= ?` / `date <= ?` comparisons work lexicographically.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html`
  - Add a filter form (`method="get"`, `action="{{ url_for('profile') }}"`) with
    two `<input type="date">` fields (`start`, `end`), an "Apply" button and a
    "Clear" link back to `url_for('profile')`. Fields are pre-filled with the
    active values.
  - Show an error message when the submitted range is invalid.
  - Show the active range (e.g. "Showing 01 Nov 2026 – 19 Nov 2026") when a
    filter is applied.
  - Empty-state text must make sense when a filter matches nothing
    (e.g. "No transactions in this date range.").
  - Rename the "Recent transactions" heading to "Transactions" when filtered
    (or keep wording neutral).

## Files to change
- `app.py` — read and validate `start`/`end` in `profile()`, pass them to the
  `build_*` helpers, pass filter state and error to the template
- `database/db.py` — add optional `start_date=None, end_date=None` parameters to
  `get_recent_transactions`, `get_summary_stats`, `get_category_breakdown`
- `templates/profile.html` — filter form, error and empty states
- `static/css/profile.css` — styles for the filter form (CSS variables only)

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — build the optional `AND date >= ?` / `AND date <= ?`
  clauses from fixed strings and append values to the params list; never
  interpolate user input into SQL
- Passwords hashed with werkzeug (unchanged; no auth changes in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- DB logic stays in `database/db.py`; date parsing/validation helper lives in
  `app.py` (e.g. `parse_date_param`) using `datetime.strptime(value, "%Y-%m-%d")`
- All new parameters default to `None` so existing callers and Step 5 tests
  keep working unchanged
- Filters apply to all three sections consistently; the category percentages
  must still sum to 100 for the filtered set
- The existing 10-row limit on transactions still applies within the range
- Currency displays as ₹ only
- Python 3.9 compatible — no `match`, no `X | Y` type unions
- No inline styles or scripts; no JS required
- Route function stays thin: parse params, fetch data, render

## Definition of done
- [ ] Visiting `/profile` with no parameters looks and behaves exactly as before (seed user: ₹ total, 8 transactions, 7 categories)
- [ ] The profile page shows a filter form with start date, end date, Apply and Clear
- [ ] Submitting a range updates the URL to `/profile?start=...&end=...` and the form stays pre-filled
- [ ] Total spent, transaction count and top category reflect only expenses inside the range
- [ ] Transaction list shows only expenses inside the range, newest first
- [ ] Category breakdown covers only the range and percentages sum to 100
- [ ] Start and end dates are inclusive (an expense dated exactly on either bound is included)
- [ ] Only `start` given → everything on or after that date; only `end` given → everything on or before
- [ ] A range with no expenses shows ₹0.00, 0 transactions, "—" top category and empty-state messages, with no errors
- [ ] `start` later than `end` shows an inline error and the unfiltered data, status 200
- [ ] `?start=garbage` shows an inline error and does not crash (status 200)
- [ ] `?start=2026-01-01' OR '1'='1` does not alter results or raise an error (SQL injection safe)
- [ ] "Clear" returns to the unfiltered `/profile`
- [ ] Unauthenticated access to `/profile?start=...` still redirects to `/login`
- [ ] Filter form is usable at mobile width and uses only CSS variables for colours
