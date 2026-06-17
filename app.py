import os
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, url_for

from database.db import (
    create_user,
    get_db,
    get_user_by_id,
    init_db,
    seed_db,
    verify_user,
)
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_profile,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SPENDLY_SECRET_KEY", "dev-secret-change-me")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name:
        error = "Name is required."
    elif not email or "@" not in email:
        error = "Please enter a valid email address."
    elif len(password) < 8:
        error = "Password must be at least 8 characters."
    else:
        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            return render_template(
                "register.html",
                error="An account with that email already exists.",
                name=name,
                email=email,
            )
        flash("Account created — please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", error=error, name=name, email=email)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template(
            "login.html",
            error="Please enter your email and password.",
            email=email,
        )

    row = verify_user(email, password)
    if row is None:
        return render_template(
            "login.html",
            error="Invalid email or password.",
            email=email,
        )

    session["user_id"] = row["id"]
    flash(f"Welcome back, {row['name']}.", "success")
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    user_id = session.pop("user_id", None)
    if user_id is not None:
        flash("You have been logged out.", "success")
    return redirect(url_for("landing"))


@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return {"current_user": None}
    row = get_user_by_id(user_id)
    if row is None:
        # Stale session — user was deleted while their cookie was still live.
        session.pop("user_id", None)
        return {"current_user": None}
    return {"current_user": row}


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
    if session.get("user_id") is None:
        flash("Please sign in to view that page.", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]
    user = get_user_profile(user_id)

    # --- SECTION A: SUMMARY STATS ---
    # owner: subagent 2
    stats = None  # TODO: replace with get_summary_stats(user_id)

    # --- SECTION B: TRANSACTION HISTORY ---
    # owner: subagent 1
    transactions = []  # TODO: replace with get_recent_transactions(user_id)

    # --- SECTION C: CATEGORY BREAKDOWN ---
    # owner: subagent 3
    categories = []  # TODO: replace with get_category_breakdown(user_id)

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
