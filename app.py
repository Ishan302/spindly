import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for

from database.db import (
    create_user,
    get_db,
    get_user_by_email,
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

@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded placeholder data — real queries arrive in Step 5.
    user = {
        "name": "Priya Sharma",
        "email": "priya.sharma@example.com",
        "initials": "PS",
        "member_since": "March 2025",
    }
    stats = {
        "total_spent": "₹12,480.00",
        "transaction_count": 7,
        "top_category": "Bills",
    }
    transactions = [
        {"date": "05 Nov 2026", "description": "Electricity bill",
         "category": "Bills", "amount": "₹3,200.00"},
        {"date": "03 Nov 2026", "description": "Weekly groceries",
         "category": "Food", "amount": "₹1,850.00"},
        {"date": "01 Nov 2026", "description": "Metro card recharge",
         "category": "Transport", "amount": "₹500.00"},
        {"date": "29 Oct 2026", "description": "Pharmacy",
         "category": "Health", "amount": "₹780.00"},
        {"date": "27 Oct 2026", "description": "Movie night",
         "category": "Entertainment", "amount": "₹650.00"},
        {"date": "24 Oct 2026", "description": "Running shoes",
         "category": "Shopping", "amount": "₹4,200.00"},
        {"date": "20 Oct 2026", "description": "Internet bill",
         "category": "Bills", "amount": "₹1,300.00"},
    ]
    categories = [
        {"name": "Bills", "total": "₹4,500.00", "percent": 36},
        {"name": "Shopping", "total": "₹4,200.00", "percent": 34},
        {"name": "Food", "total": "₹1,850.00", "percent": 15},
        {"name": "Health", "total": "₹780.00", "percent": 6},
        {"name": "Entertainment", "total": "₹650.00", "percent": 5},
        {"name": "Transport", "total": "₹500.00", "percent": 4},
    ]
    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
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
