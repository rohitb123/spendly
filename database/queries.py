"""Read-only query helpers backing the /profile view.

All helpers open a connection via ``database.db.get_db``, run parameterised
SQL filtered by ``user_id``, and close the connection before returning.
Formatting (currency, date, percentages) is done here so ``app.py`` stays thin.
"""

from datetime import datetime

from database.db import get_db


def get_user_profile(user_id):
    """Return ``{name, email, initials, member_since}`` for the user, or None."""
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    name = row["name"] or ""
    name_stripped = name.strip()

    if not name_stripped:
        initials = "?"
    else:
        parts = name_stripped.split()
        if len(parts) == 1:
            initials = parts[0][:2].upper()
        else:
            initials = (parts[0][0] + parts[-1][0]).upper()

    parsed = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    member_since = parsed.strftime("%B %Y")

    return {
        "name": name,
        "email": row["email"],
        "initials": initials,
        "member_since": member_since,
    }


def get_summary_stats(user_id):
    """Return ``{total_spent, transaction_count, top_category}``.

    Empty state: ``{"total_spent": "₹0.00", "transaction_count": 0,
    "top_category": "—"}``.
    """
    conn = get_db()

    totals = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS n "
        "FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    transaction_count = totals["n"]
    total_value = totals["total"] or 0

    if transaction_count == 0:
        conn.close()
        return {
            "total_spent": "₹0.00",
            "transaction_count": 0,
            "top_category": "—",
        }

    top_row = conn.execute(
        "SELECT category, SUM(amount) AS t FROM expenses "
        "WHERE user_id = ? GROUP BY category ORDER BY t DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()

    return {
        "total_spent": f"₹{total_value:.2f}",
        "transaction_count": transaction_count,
        "top_category": top_row["category"] if top_row is not None else "—",
    }


def get_recent_transactions(user_id, limit=10):
    """Return up to ``limit`` rows newest-first.

    Each row: ``{date, description, category, amount}`` with date formatted
    ``Mon DD, YYYY`` and amount formatted ``₹XX.XX``.
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT date, description, category, amount "
        "FROM expenses "
        "WHERE user_id = ? "
        "ORDER BY date DESC, id DESC "
        "LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()

    transactions = []
    for row in rows:
        formatted_date = datetime.strptime(row["date"], "%Y-%m-%d").strftime("%b %d, %Y")
        transactions.append(
            {
                "date": formatted_date,
                "description": row["description"],
                "category": row["category"],
                "amount": f"₹{row['amount']:.2f}",
            }
        )
    return transactions


def get_category_breakdown(user_id):
    """Return list of ``{name, amount, pct, slug}`` sorted by amount desc.

    ``pct`` values are integers summing to 100; the largest category absorbs
    any rounding remainder. Empty list when the user has no expenses.
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT category AS name, SUM(amount) AS amount "
        "FROM expenses WHERE user_id = ? "
        "GROUP BY category ORDER BY amount DESC",
        (user_id,),
    ).fetchall()
    conn.close()

    if not rows:
        return []

    total = sum(row["amount"] for row in rows)
    if total <= 0:
        return []

    categories = []
    for row in rows:
        raw_amount = row["amount"]
        categories.append(
            {
                "name": row["name"],
                "amount": f"₹{raw_amount:.2f}",
                "pct": round(raw_amount / total * 100),
                "slug": row["name"].lower(),
            }
        )

    pct_sum = sum(c["pct"] for c in categories)
    categories[0]["pct"] += 100 - pct_sum

    return categories
