import math
import os
import sqlite3
from datetime import date, datetime

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from database.db import (
    create_expense,
    create_user,
    delete_expense as delete_expense_row,
    get_db,
    get_expense_by_id,
    get_user_by_id,
    init_db,
    seed_db,
    update_expense,
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

# Fixed expense categories — single source of truth for validation and the
# add-expense dropdown. Must match the cat-* CSS class slugs (lowercased).
CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

# Input bounds for an expense — reject obviously bogus / abusive values at the
# route boundary before they reach the database.
MAX_AMOUNT = 10_000_000
MAX_DESCRIPTION_LEN = 500

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Utilities                                                           #
# ------------------------------------------------------------------ #


def _parse_date_param(raw):
    """Return a canonical ``YYYY-MM-DD`` string, or None for missing/malformed.

    The route is the boundary for untrusted query-string input, so validation
    lives here rather than in the query helpers. The strptime/strftime round
    trip canonicalises non-padded values (e.g. ``2026-6-5`` -> ``2026-06-05``)
    so string comparison against the zero-padded ``date`` column is correct.
    """
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _validate_expense_form(amount_raw, category, date_raw, description):
    """Validate the raw expense form fields shared by add and edit.

    Returns ``(amount, parsed_date, error)``: on the first failing rule the
    amount/date are None and ``error`` is a user-facing message; when every
    rule passes ``error`` is None. ``amount`` is rejected unless it parses to a
    finite float (``float('nan')``/``float('inf')`` parse without raising but
    must never reach the database).
    """
    parsed_date = _parse_date_param(date_raw)
    try:
        amount = float(amount_raw)
        if not math.isfinite(amount):
            amount = None
    except ValueError:
        amount = None

    if amount is None or amount <= 0:
        error = "Please enter an amount greater than zero."
    elif amount > MAX_AMOUNT:
        error = "Amount is too large."
    elif category not in CATEGORIES:
        error = "Please choose a valid category."
    elif parsed_date is None:
        error = "Please enter a valid date (YYYY-MM-DD)."
    elif len(description) > MAX_DESCRIPTION_LEN:
        error = f"Description must be {MAX_DESCRIPTION_LEN} characters or fewer."
    else:
        error = None

    if error is not None:
        return None, None, error
    return amount, parsed_date, None


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

    start = _parse_date_param(request.args.get("start"))
    end = _parse_date_param(request.args.get("end"))
    range_active = start is not None or end is not None
    invalid_range = start is not None and end is not None and start > end

    if invalid_range:
        # start > end can never match a row; skip the DB round-trips.
        stats = {"total_spent": "₹0.00", "transaction_count": 0, "top_category": "—"}
        transactions = []
        categories = []
    else:
        # --- SECTION A: SUMMARY STATS ---
        stats = get_summary_stats(user_id, start=start, end=end)

        # --- SECTION B: TRANSACTION HISTORY ---
        transactions = get_recent_transactions(user_id, start=start, end=end)

        # --- SECTION C: CATEGORY BREAKDOWN ---
        categories = get_category_breakdown(user_id, start=start, end=end)

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        start=start or "",
        end=end or "",
        range_active=range_active,
        invalid_range=invalid_range,
    )


@app.route("/analytics")
def analytics():
    if session.get("user_id") is None:
        flash("Please sign in to view that page.", "error")
        return redirect(url_for("login"))

    return render_template("analytics.html")


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if session.get("user_id") is None:
        flash("Please sign in to view that page.", "error")
        return redirect(url_for("login"))

    today = date.today().isoformat()

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            amount="",
            category="",
            date=today,
            description="",
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    amount, parsed_date, error = _validate_expense_form(
        amount_raw, category, date_raw, description
    )

    if error is not None:
        return render_template(
            "add_expense.html",
            categories=CATEGORIES,
            error=error,
            amount=amount_raw,
            category=category,
            date=date_raw or today,
            description=description,
        )

    # Return value (new row id) is unused now but Step 09 will need it.
    _expense_id = create_expense(
        session.get("user_id"), amount, category, parsed_date, description or None
    )
    flash("Expense added.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if session.get("user_id") is None:
        flash("Please sign in to view that page.", "error")
        return redirect(url_for("login"))

    if request.method == "GET":
        expense = get_expense_by_id(id, session.get("user_id"))
        if expense is None:
            abort(404)
        return render_template(
            "edit_expense.html",
            categories=CATEGORIES,
            expense_id=id,
            amount=expense["amount"],
            category=expense["category"],
            date=expense["date"],
            description=expense["description"] or "",
        )

    amount_raw = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    date_raw = request.form.get("date", "").strip()
    description = request.form.get("description", "").strip()

    amount, parsed_date, error = _validate_expense_form(
        amount_raw, category, date_raw, description
    )

    if error is not None:
        return render_template(
            "edit_expense.html",
            categories=CATEGORIES,
            expense_id=id,
            error=error,
            amount=amount_raw,
            category=category,
            date=date_raw,
            description=description,
        )

    # The user_id-scoped UPDATE is the ownership gate: it touches zero rows for a
    # missing or someone else's expense, so a falsy result means "not yours" -> 404.
    updated = update_expense(
        id, session.get("user_id"), amount, category, parsed_date, description or None
    )
    if not updated:
        abort(404)
    flash("Expense updated.", "success")
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["POST"])
def delete_expense(id):
    if session.get("user_id") is None:
        flash("Please sign in to view that page.", "error")
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, session.get("user_id"))
    if expense is None:
        abort(404)

    # The user_id-scoped DELETE is the ownership gate: it removes zero rows for a
    # missing or someone else's expense, so a falsy result means "not yours" -> 404.
    if not delete_expense_row(id, session.get("user_id")):
        abort(404)

    flash("Expense deleted.", "success")
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5001)
