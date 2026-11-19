import calendar
import os
import sqlite3
from datetime import date, datetime

from flask import Flask, redirect, render_template, request, session, url_for

from database.db import (
    create_user,
    get_category_breakdown,
    get_db,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
    verify_user,
)

app = Flask(__name__)
# The fallback key is for local development only; production must set SECRET_KEY.
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


def is_valid_email(email):
    local, sep, domain = email.partition("@")
    return (
        bool(sep)
        and bool(local)
        and "@" not in domain
        and "." in domain
        and not domain.startswith(".")
        and not domain.endswith(".")
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    def fail(message):
        return render_template("register.html", error=message, name=name, email=email)

    if not name or not email or not password.strip():
        return fail("All fields are required.")
    if not is_valid_email(email):
        return fail("Please enter a valid email address.")
    if len(password) < 8:
        return fail("Password must be at least 8 characters.")
    if password != confirm_password:
        return fail("Passwords do not match.")
    if get_user_by_email(email):
        return fail("An account with that email already exists.")

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        return fail("An account with that email already exists.")

    return redirect(url_for("login", registered=1))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    def fail(message):
        return render_template("login.html", error=message, email=email)

    if not email or not password:
        return fail("Email and password are required.")

    user = verify_user(email, password)
    if user is None:
        return fail("Invalid email or password.")

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

# ------------------------------------------------------------------ #
# Profile helpers — shared                                            #
# ------------------------------------------------------------------ #

def format_inr(amount):
    return f"₹{amount:,.2f}"


def format_date(iso_date):
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d %b %Y")


def make_initials(name):
    parts = name.split()
    return "".join(p[0] for p in parts[:2]).upper() or "?"


# ==== SECTION 1: transaction history (subagent 1 only) ============== #

def build_transactions(user_id, start_date=None, end_date=None):
    return [
        {
            "date": format_date(t["date"]),
            "description": t["description"],
            "category": t["category"],
            "amount": format_inr(t["amount"]),
        }
        for t in get_recent_transactions(
            user_id, start_date=start_date, end_date=end_date
        )
    ]


# ==== SECTION 2: summary stats (subagent 2 only) ==================== #

def build_stats(user_id, start_date=None, end_date=None):
    stats = get_summary_stats(user_id, start_date=start_date, end_date=end_date)
    return {
        "total_spent": format_inr(stats["total_spent"]),
        "transaction_count": stats["transaction_count"],
        "top_category": stats["top_category"],
    }


# ==== SECTION 3: category breakdown (subagent 3 only) =============== #

def build_categories(user_id, start_date=None, end_date=None):
    return [
        {
            "name": item["name"],
            "total": format_inr(item["amount"]),
            "percent": item["pct"],
        }
        for item in get_category_breakdown(
            user_id, start_date=start_date, end_date=end_date
        )
    ]


# ==== END SECTIONS ================================================== #

# ==== Date filter helpers =========================================== #

def parse_date_param(raw):
    """Return (iso_date_or_None, is_invalid). Blank or missing is not invalid."""
    raw = (raw or "").strip()
    if not raw:
        return None, False
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date().isoformat(), False
    except ValueError:
        return None, True


def resolve_date_filter(args):
    """Return (start, end, error_message_or_None) from request query args."""
    start, start_invalid = parse_date_param(args.get("start"))
    end, end_invalid = parse_date_param(args.get("end"))

    if start_invalid or end_invalid:
        return start, end, "Enter dates as YYYY-MM-DD. The invalid date was ignored."
    if start and end and start > end:
        return None, None, "Start date must be on or before the end date."
    return start, end, None


def shift_months(day, months):
    """Return `day` moved back by `months`, clamping to the month's last day."""
    index = day.year * 12 + (day.month - 1) - months
    year, month = index // 12, index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def build_date_presets(start, end):
    """Quick-range tabs ending today; `active` marks the one matching the filter."""
    today = date.today()
    ranges = [
        ("This month", today.replace(day=1)),
        ("3 months", shift_months(today, 3)),
        ("6 months", shift_months(today, 6)),
    ]
    return [
        {
            "label": label,
            "start": first.isoformat(),
            "end": today.isoformat(),
            "active": start == first.isoformat() and end == today.isoformat(),
        }
        for label, first in ranges
    ]


def describe_date_filter(start, end):
    """Return a human-readable label for the active range, or "" if none."""
    if start and end:
        return f"{format_date(start)} – {format_date(end)}"
    if start:
        return f"from {format_date(start)}"
    if end:
        return f"up to {format_date(end)}"
    return ""


def build_date_filter(args):
    """Bundle everything the template needs to render the date filter."""
    start, end, error = resolve_date_filter(args)
    return {
        "start": start or "",
        "end": end or "",
        "active": bool(start or end),
        "label": describe_date_filter(start, end),
        "error": error,
        "presets": build_date_presets(start, end),
    }


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user_row = get_user_by_id(user_id)
    if user_row is None:
        session.clear()
        return redirect(url_for("login"))

    user = {
        "name": user_row["name"],
        "email": user_row["email"],
        "initials": make_initials(user_row["name"]),
        "member_since": user_row["member_since"],
    }
    date_filter = build_date_filter(request.args)
    start, end = date_filter["start"] or None, date_filter["end"] or None
    return render_template(
        "profile.html",
        user=user,
        stats=build_stats(user_id, start, end),
        transactions=build_transactions(user_id, start, end),
        categories=build_categories(user_id, start, end),
        date_filter=date_filter,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
