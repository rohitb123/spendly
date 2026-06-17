"""Tests for Step 5 — backend wiring of /profile."""

import re

from database.db import create_user
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_profile,
)


# --- SECTION A: SUMMARY STATS + USER PROFILE TESTS ---

def test_get_user_profile_returns_dict(app, seed_user_id):
    profile = get_user_profile(seed_user_id)
    assert profile is not None
    assert profile["name"] == "Demo User"
    assert profile["email"] == "demo@spendly.com"
    assert profile["initials"] == "DU"
    assert re.match(r"^[A-Z][a-z]+ \d{4}$", profile["member_since"])


def test_get_user_profile_unknown_id_returns_none(app):
    assert get_user_profile(99999) is None


def test_get_user_profile_single_word_name(app):
    uid = create_user("Cher", "cher@spendly.com", "password123")
    profile = get_user_profile(uid)
    assert profile is not None
    assert profile["initials"] == "CH"


def test_get_summary_stats_seed_user_totals(app, seed_user_id):
    stats = get_summary_stats(seed_user_id)
    assert stats["total_spent"] == "₹390.65"
    assert stats["transaction_count"] == 8
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_empty_user_zeros(app, empty_user_id):
    stats = get_summary_stats(empty_user_id)
    assert stats == {
        "total_spent": "₹0.00",
        "transaction_count": 0,
        "top_category": "—",
    }


# --- SECTION B: TRANSACTION HISTORY TESTS ---

def test_get_recent_transactions_ordered_newest_first(app, seed_user_id):
    transactions = get_recent_transactions(seed_user_id)
    assert len(transactions) == 8
    assert transactions[0]["description"] == "Lunch with team"
    assert transactions[0]["date"] == "Jun 13, 2026"
    assert transactions[-1]["description"] == "Coffee and bagel"


def test_get_recent_transactions_default_limit_is_10(app, seed_user_id):
    transactions = get_recent_transactions(seed_user_id)
    assert len(transactions) <= 10
    assert len(transactions) == 8


def test_get_recent_transactions_empty_user(app, empty_user_id):
    assert get_recent_transactions(empty_user_id) == []


def test_get_recent_transactions_amount_format(app, seed_user_id):
    transactions = get_recent_transactions(seed_user_id)
    first_amount = transactions[0]["amount"]
    assert first_amount.startswith("₹")
    assert re.fullmatch(r"₹\d+\.\d{2}", first_amount)
    assert first_amount == "₹22.40"


def test_get_recent_transactions_date_format(app, seed_user_id):
    transactions = get_recent_transactions(seed_user_id)
    first_date = transactions[0]["date"]
    assert re.fullmatch(r"[A-Z][a-z]{2} \d{2}, \d{4}", first_date)


# --- SECTION C: CATEGORY BREAKDOWN TESTS ---

def test_get_category_breakdown_sorted_desc(app, seed_user_id):
    result = get_category_breakdown(seed_user_id)
    assert result, "Expected non-empty breakdown for the seeded user."
    assert result[0]["name"] == "Bills"
    assert result[0]["amount"] == "₹120.00"
    assert result[-1]["name"] == "Other"
    assert result[-1]["amount"] == "₹15.00"


def test_get_category_breakdown_all_7_seed_categories(app, seed_user_id):
    result = get_category_breakdown(seed_user_id)
    assert len(result) == 7
    names = {row["name"] for row in result}
    assert names == {
        "Bills",
        "Shopping",
        "Entertainment",
        "Transport",
        "Food",
        "Health",
        "Other",
    }


def test_get_category_breakdown_pct_sums_to_100(app, seed_user_id):
    result = get_category_breakdown(seed_user_id)
    assert sum(row["pct"] for row in result) == 100


def test_get_category_breakdown_slug_is_lower(app, seed_user_id):
    result = get_category_breakdown(seed_user_id)
    for row in result:
        assert row["slug"] == row["name"].lower()


def test_get_category_breakdown_empty_user(app, empty_user_id):
    assert get_category_breakdown(empty_user_id) == []


def test_get_category_breakdown_amount_format(app, seed_user_id):
    result = get_category_breakdown(seed_user_id)
    for row in result:
        assert row["amount"].startswith("₹")
        decimals = row["amount"].split(".")[-1]
        assert len(decimals) == 2
        assert decimals.isdigit()


# --- ROUTE INTEGRATION TESTS ---

def test_profile_unauthenticated_redirects_to_login(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_seed_user_shows_real_data(client, seed_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id

    response = client.get("/profile")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Demo User" in body
    assert "demo@spendly.com" in body
    assert "₹" in body
    assert "₹390.65" in body
    assert "Bills" in body
    # Eight seeded transactions should each appear by description.
    for desc in [
        "Lunch with team",
        "Stamps",
        "T-shirts",
        "Movie night",
        "Pharmacy",
        "Electricity bill",
        "Uber to airport",
        "Coffee and bagel",
    ]:
        assert desc in body


def test_profile_data_does_not_leak_between_users(client, seed_user_id, empty_user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = empty_user_id

    response = client.get("/profile")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    # The empty user must NOT see the seed user's expense descriptions.
    assert "Lunch with team" not in body
    assert "Electricity bill" not in body
    # Empty state: zero rupees, em-dash top category.
    assert "₹0.00" in body
    assert "—" in body
