"""Read-only query helpers backing the /profile view.

All helpers open a connection via ``database.db.get_db``, run parameterised
SQL filtered by ``user_id``, and close the connection before returning.
Formatting (currency, date, percentages) is done here so ``app.py`` stays thin.
"""

from datetime import datetime

from database.db import get_db


# --- SECTION A: SUMMARY STATS ---
# owner: subagent 2

def get_user_profile(user_id):
    """Return ``{name, email, initials, member_since}`` for the user, or None."""
    raise NotImplementedError  # filled in by subagent 2


def get_summary_stats(user_id):
    """Return ``{total_spent, transaction_count, top_category}``.

    Empty state: ``{"total_spent": "₹0.00", "transaction_count": 0,
    "top_category": "—"}``.
    """
    raise NotImplementedError  # filled in by subagent 2


# --- SECTION B: TRANSACTION HISTORY ---
# owner: subagent 1

def get_recent_transactions(user_id, limit=10):
    """Return up to ``limit`` rows newest-first.

    Each row: ``{date, description, category, amount}`` with date formatted
    ``Mon DD, YYYY`` and amount formatted ``₹XX.XX``.
    """
    raise NotImplementedError  # filled in by subagent 1


# --- SECTION C: CATEGORY BREAKDOWN ---
# owner: subagent 3

def get_category_breakdown(user_id):
    """Return list of ``{name, amount, pct, slug}`` sorted by amount desc.

    ``pct`` values are integers summing to 100; the largest category absorbs
    any rounding remainder. Empty list when the user has no expenses.
    """
    raise NotImplementedError  # filled in by subagent 3
