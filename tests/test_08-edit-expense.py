"""Tests for Step 08 — Edit Expense feature.

Routes under test:
    GET  /expenses/<int:id>/edit  — render pre-filled edit form (logged-in only)
    POST /expenses/<int:id>/edit  — validate, update row, flash, redirect to /profile (logged-in only)

DB helpers exercised indirectly:
    database.db.get_expense_by_id(expense_id, user_id)
    database.db.update_expense(expense_id, user_id, amount, category, expense_date, description)

Spec constants:
    CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
    MAX_AMOUNT = 10_000_000
    MAX_DESCRIPTION_LEN = 500
"""

import pytest

from database.db import create_expense, create_user, get_db

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]
MAX_AMOUNT = 10_000_000
MAX_DESCRIPTION_LEN = 500

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _login_as(client, user_id):
    """Inject a user_id directly into the session — no password round-trip needed."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _get_expense_row(expense_id):
    """Return the raw DB row for an expense by its id, regardless of owner."""
    conn = get_db()
    row = conn.execute(
        "SELECT id, user_id, amount, category, date, description FROM expenses WHERE id = ?",
        (expense_id,),
    ).fetchone()
    conn.close()
    return row


def _expense_count(user_id):
    """Return the number of expense rows owned by user_id in the test DB."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row["n"]


def _create_test_expense(
    user_id,
    amount=49.99,
    category="Food",
    date="2026-01-15",
    description="Test expense",
):
    """Insert a single expense row and return its id."""
    return create_expense(user_id, amount, category, date, description)


# ---------------------------------------------------------------------------
# Fixtures (local; supplement conftest.py which provides app, client, seed/empty fixtures)
# ---------------------------------------------------------------------------


@pytest.fixture
def other_user_id(app):
    """A second registered user with no seeded expenses."""
    return create_user("Other User", "other@spendly.com", "otherpass1")


@pytest.fixture
def owned_expense_id(app, empty_user_id):
    """An expense created by empty_user_id — returned as the integer expense id."""
    return _create_test_expense(
        empty_user_id,
        amount=49.99,
        category="Food",
        date="2026-01-15",
        description="Test expense",
    )


@pytest.fixture
def other_user_expense_id(app, other_user_id):
    """An expense created by other_user_id."""
    return _create_test_expense(
        other_user_id,
        amount=75.00,
        category="Transport",
        date="2026-02-10",
        description="Other user expense",
    )


# ===========================================================================
# AUTH GUARD
# ===========================================================================


class TestAuthGuard:
    def test_get_unauthenticated_redirects_to_login(self, client, owned_expense_id):
        """Unauthenticated GET /expenses/<id>/edit must redirect 302 to /login."""
        response = client.get(f"/expenses/{owned_expense_id}/edit")
        assert (
            response.status_code == 302
        ), "Expected 302 redirect for unauthenticated GET /expenses/<id>/edit"
        assert (
            "/login" in response.headers["Location"]
        ), "Unauthenticated GET must redirect to /login"

    def test_get_unauthenticated_flashes_sign_in_message(
        self, client, owned_expense_id
    ):
        """Unauthenticated GET must flash the sign-in message before redirecting."""
        response = client.get(
            f"/expenses/{owned_expense_id}/edit", follow_redirects=True
        )
        body = response.get_data(as_text=True)
        assert (
            "sign in" in body.lower() or "please" in body.lower()
        ), "Unauthenticated GET must flash 'Please sign in to view that page.' message"

    def test_post_unauthenticated_redirects_to_login(self, client, owned_expense_id):
        """Unauthenticated POST /expenses/<id>/edit must redirect 302 to /login."""
        response = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "99.00",
                "category": "Food",
                "date": "2026-03-01",
                "description": "Should not be saved",
            },
        )
        assert (
            response.status_code == 302
        ), "Expected 302 redirect for unauthenticated POST /expenses/<id>/edit"
        assert (
            "/login" in response.headers["Location"]
        ), "Unauthenticated POST must redirect to /login"

    def test_post_unauthenticated_does_not_mutate_db(self, client, owned_expense_id):
        """Unauthenticated POST must not modify the expense row in the DB."""
        original_row = _get_expense_row(owned_expense_id)
        client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "99.00",
                "category": "Bills",
                "date": "2026-03-01",
                "description": "Tampered",
            },
        )
        row_after = _get_expense_row(owned_expense_id)
        assert (
            row_after["amount"] == original_row["amount"]
        ), "Unauthenticated POST must not change the expense amount"
        assert (
            row_after["category"] == original_row["category"]
        ), "Unauthenticated POST must not change the expense category"


# ===========================================================================
# GET — FORM RENDERING (logged-in, own expense)
# ===========================================================================


class TestGetFormRendering:
    def test_get_own_expense_returns_200(self, client, empty_user_id, owned_expense_id):
        """Authenticated GET for own expense must return 200."""
        _login_as(client, empty_user_id)
        response = client.get(f"/expenses/{owned_expense_id}/edit")
        assert (
            response.status_code == 200
        ), "Authenticated GET for own expense must return 200"

    def test_get_form_prefilled_with_amount(
        self, client, empty_user_id, owned_expense_id
    ):
        """Edit form must be pre-filled with the existing expense's amount."""
        _login_as(client, empty_user_id)
        body = client.get(f"/expenses/{owned_expense_id}/edit").get_data(as_text=True)
        # The fixture creates the expense with amount 49.99
        assert (
            "49.99" in body
        ), "Edit form must be pre-filled with the current expense amount (49.99)"

    def test_get_form_prefilled_with_category(
        self, client, empty_user_id, owned_expense_id
    ):
        """Edit form must be pre-filled with the existing expense's category."""
        _login_as(client, empty_user_id)
        body = client.get(f"/expenses/{owned_expense_id}/edit").get_data(as_text=True)
        # The fixture creates the expense with category "Food"
        assert (
            "Food" in body
        ), "Edit form must be pre-filled with the current expense category (Food)"

    def test_get_form_prefilled_with_date(
        self, client, empty_user_id, owned_expense_id
    ):
        """Edit form must be pre-filled with the existing expense's date."""
        _login_as(client, empty_user_id)
        body = client.get(f"/expenses/{owned_expense_id}/edit").get_data(as_text=True)
        # The fixture creates the expense with date "2026-01-15"
        assert (
            "2026-01-15" in body
        ), "Edit form must be pre-filled with the current expense date (2026-01-15)"

    def test_get_form_prefilled_with_description(
        self, client, empty_user_id, owned_expense_id
    ):
        """Edit form must be pre-filled with the existing expense's description."""
        _login_as(client, empty_user_id)
        body = client.get(f"/expenses/{owned_expense_id}/edit").get_data(as_text=True)
        # The fixture creates the expense with description "Test expense"
        assert (
            "Test expense" in body
        ), "Edit form must be pre-filled with the current expense description ('Test expense')"

    def test_get_form_contains_amount_field(
        self, client, empty_user_id, owned_expense_id
    ):
        """Edit form must contain an input with name='amount'."""
        _login_as(client, empty_user_id)
        body = client.get(f"/expenses/{owned_expense_id}/edit").get_data(as_text=True)
        assert 'name="amount"' in body, "Edit form must contain an amount input"

    def test_get_form_contains_category_select(
        self, client, empty_user_id, owned_expense_id
    ):
        """Edit form must contain a select with name='category'."""
        _login_as(client, empty_user_id)
        body = client.get(f"/expenses/{owned_expense_id}/edit").get_data(as_text=True)
        assert 'name="category"' in body, "Edit form must contain a category select"

    def test_get_form_contains_date_field(
        self, client, empty_user_id, owned_expense_id
    ):
        """Edit form must contain an input with name='date'."""
        _login_as(client, empty_user_id)
        body = client.get(f"/expenses/{owned_expense_id}/edit").get_data(as_text=True)
        assert 'name="date"' in body, "Edit form must contain a date input"

    def test_get_form_contains_description_field(
        self, client, empty_user_id, owned_expense_id
    ):
        """Edit form must contain an input or textarea with name='description'."""
        _login_as(client, empty_user_id)
        body = client.get(f"/expenses/{owned_expense_id}/edit").get_data(as_text=True)
        assert (
            'name="description"' in body
        ), "Edit form must contain a description field"

    def test_get_form_extends_base_template(
        self, client, empty_user_id, owned_expense_id
    ):
        """The rendered page must include base.html landmarks (site name 'Spendly')."""
        _login_as(client, empty_user_id)
        body = client.get(f"/expenses/{owned_expense_id}/edit").get_data(as_text=True)
        assert (
            "Spendly" in body
        ), "Edit form page must extend base.html and contain the site name 'Spendly'"

    def test_get_form_has_edit_expense_title(
        self, client, empty_user_id, owned_expense_id
    ):
        """The rendered page must contain text identifying it as the edit form."""
        _login_as(client, empty_user_id)
        body = client.get(f"/expenses/{owned_expense_id}/edit").get_data(as_text=True)
        assert (
            "edit" in body.lower() or "update" in body.lower()
        ), "Edit form page must contain 'edit' or 'update' to identify the page purpose"

    @pytest.mark.parametrize("category", CATEGORIES)
    def test_get_form_lists_all_seven_categories(
        self, client, empty_user_id, owned_expense_id, category
    ):
        """All 7 fixed categories must appear in the category dropdown."""
        _login_as(client, empty_user_id)
        body = client.get(f"/expenses/{owned_expense_id}/edit").get_data(as_text=True)
        assert (
            category in body
        ), f"Category option '{category}' must appear in the edit form dropdown"


# ===========================================================================
# GET — 404 CASES
# ===========================================================================


class TestGet404:
    def test_get_nonexistent_id_returns_404(self, client, empty_user_id):
        """GET for a non-existent expense id must return 404."""
        _login_as(client, empty_user_id)
        response = client.get("/expenses/999999/edit")
        assert (
            response.status_code == 404
        ), "GET for a non-existent expense id must return 404"

    def test_get_other_users_expense_returns_404(
        self, client, empty_user_id, other_user_expense_id
    ):
        """GET for an expense owned by a different user must return 404 (no existence leak)."""
        _login_as(client, empty_user_id)
        response = client.get(f"/expenses/{other_user_expense_id}/edit")
        assert (
            response.status_code == 404
        ), "GET for another user's expense must return 404, not reveal existence"

    def test_get_other_users_expense_same_status_as_missing(
        self, client, empty_user_id, other_user_expense_id
    ):
        """A cross-ownership GET and a genuinely missing id must return the same 404 status (no leak)."""
        _login_as(client, empty_user_id)
        missing_response = client.get("/expenses/888888/edit")
        cross_response = client.get(f"/expenses/{other_user_expense_id}/edit")
        assert (
            missing_response.status_code == cross_response.status_code == 404
        ), "Both a missing id and another user's id must return 404 — no existence information"


# ===========================================================================
# VALID POST — HAPPY PATH
# ===========================================================================


class TestValidPost:
    UPDATED_DATA = {
        "amount": "123.45",
        "category": "Transport",
        "date": "2026-05-20",
        "description": "Updated description",
    }

    def test_valid_post_redirects_302_to_profile(
        self, client, empty_user_id, owned_expense_id
    ):
        """A valid POST must redirect 302 to /profile."""
        _login_as(client, empty_user_id)
        response = client.post(
            f"/expenses/{owned_expense_id}/edit", data=self.UPDATED_DATA
        )
        assert response.status_code == 302, "Valid POST must return 302 redirect"
        assert (
            "/profile" in response.headers["Location"]
        ), "Valid POST must redirect to /profile"

    def test_valid_post_flashes_expense_updated(
        self, client, empty_user_id, owned_expense_id
    ):
        """Valid POST must flash 'Expense updated.' on the profile page."""
        _login_as(client, empty_user_id)
        response = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data=self.UPDATED_DATA,
            follow_redirects=True,
        )
        body = response.get_data(as_text=True)
        assert (
            "Expense updated" in body
        ), "Profile page after valid POST must contain 'Expense updated.' flash message"

    def test_valid_post_persists_new_amount(
        self, client, empty_user_id, owned_expense_id
    ):
        """Valid POST must update the amount in the DB."""
        _login_as(client, empty_user_id)
        client.post(f"/expenses/{owned_expense_id}/edit", data=self.UPDATED_DATA)
        row = _get_expense_row(owned_expense_id)
        assert (
            abs(row["amount"] - 123.45) < 0.001
        ), f"DB row amount must be updated to 123.45, got {row['amount']}"

    def test_valid_post_persists_new_category(
        self, client, empty_user_id, owned_expense_id
    ):
        """Valid POST must update the category in the DB."""
        _login_as(client, empty_user_id)
        client.post(f"/expenses/{owned_expense_id}/edit", data=self.UPDATED_DATA)
        row = _get_expense_row(owned_expense_id)
        assert (
            row["category"] == "Transport"
        ), f"DB row category must be updated to 'Transport', got '{row['category']}'"

    def test_valid_post_persists_new_date(
        self, client, empty_user_id, owned_expense_id
    ):
        """Valid POST must update the date in the DB."""
        _login_as(client, empty_user_id)
        client.post(f"/expenses/{owned_expense_id}/edit", data=self.UPDATED_DATA)
        row = _get_expense_row(owned_expense_id)
        assert (
            row["date"] == "2026-05-20"
        ), f"DB row date must be updated to '2026-05-20', got '{row['date']}'"

    def test_valid_post_persists_new_description(
        self, client, empty_user_id, owned_expense_id
    ):
        """Valid POST must update the description in the DB."""
        _login_as(client, empty_user_id)
        client.post(f"/expenses/{owned_expense_id}/edit", data=self.UPDATED_DATA)
        row = _get_expense_row(owned_expense_id)
        assert (
            row["description"] == "Updated description"
        ), f"DB row description must be updated to 'Updated description', got '{row['description']}'"

    def test_valid_post_does_not_create_extra_row(
        self, client, empty_user_id, owned_expense_id
    ):
        """A valid POST must update the existing row, not insert a new one."""
        _login_as(client, empty_user_id)
        count_before = _expense_count(empty_user_id)
        client.post(f"/expenses/{owned_expense_id}/edit", data=self.UPDATED_DATA)
        count_after = _expense_count(empty_user_id)
        assert (
            count_after == count_before
        ), f"Valid POST must not insert a new expense row (before={count_before}, after={count_after})"

    def test_valid_post_updated_values_visible_on_profile(
        self, client, empty_user_id, owned_expense_id
    ):
        """After a valid POST, the new values must appear on /profile."""
        _login_as(client, empty_user_id)
        client.post(f"/expenses/{owned_expense_id}/edit", data=self.UPDATED_DATA)
        profile_response = client.get("/profile")
        body = profile_response.get_data(as_text=True)
        # The updated amount or description must appear in the transaction list
        assert (
            "123.45" in body or "Updated description" in body
        ), "Updated expense values must appear on /profile after a valid edit"

    def test_valid_post_empty_description_persists_as_null(
        self, client, empty_user_id, owned_expense_id
    ):
        """A valid POST with empty description must store None/null in the DB."""
        _login_as(client, empty_user_id)
        client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "10.00",
                "category": "Other",
                "date": "2026-06-01",
                "description": "",
            },
        )
        row = _get_expense_row(owned_expense_id)
        assert row["description"] in (
            None,
            "",
        ), f"Empty description must be stored as None or empty string, got '{row['description']}'"

    @pytest.mark.parametrize("category", CATEGORIES)
    def test_valid_post_accepts_all_seven_categories(
        self, client, empty_user_id, owned_expense_id, category
    ):
        """Each of the 7 fixed categories must be accepted as a valid update."""
        _login_as(client, empty_user_id)
        response = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "5.00",
                "category": category,
                "date": "2026-06-10",
                "description": "",
            },
        )
        assert (
            response.status_code == 302
        ), f"Category '{category}' must be accepted and produce a 302 redirect"


# ===========================================================================
# INVALID POST — AMOUNT VALIDATION
# ===========================================================================


class TestInvalidPostAmount:
    @pytest.mark.parametrize(
        "bad_amount,label",
        [
            ("", "empty amount"),
            ("0", "zero amount"),
            ("0.00", "zero decimal"),
            ("-1", "negative integer"),
            ("-0.01", "small negative decimal"),
            ("abc", "non-numeric string"),
            ("  ", "whitespace-only"),
        ],
    )
    def test_invalid_amount_rerenders_edit_form(
        self, client, empty_user_id, owned_expense_id, bad_amount, label
    ):
        """Invalid amount must re-render the edit form with status 200, not redirect."""
        _login_as(client, empty_user_id)
        response = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": bad_amount,
                "category": "Food",
                "date": "2026-07-01",
                "description": "Test",
            },
        )
        assert (
            response.status_code == 200
        ), f"Invalid amount ({label}) must re-render the edit form (200), not redirect"

    @pytest.mark.parametrize(
        "bad_amount,label",
        [
            ("", "empty amount"),
            ("0", "zero amount"),
            ("-5.00", "negative amount"),
            ("xyz", "non-numeric string"),
        ],
    )
    def test_invalid_amount_shows_error_message(
        self, client, empty_user_id, owned_expense_id, bad_amount, label
    ):
        """Re-rendered edit form must contain an error message for an invalid amount."""
        _login_as(client, empty_user_id)
        body = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": bad_amount,
                "category": "Food",
                "date": "2026-07-01",
                "description": "Test",
            },
        ).get_data(as_text=True)
        assert (
            "error" in body.lower() or "please" in body.lower()
        ), f"Invalid amount ({label}) must produce an error message in the re-rendered form"

    @pytest.mark.parametrize(
        "bad_amount,label",
        [
            ("", "empty amount"),
            ("0", "zero amount"),
            ("-5.00", "negative amount"),
            ("xyz", "non-numeric string"),
        ],
    )
    def test_invalid_amount_does_not_mutate_db(
        self, client, empty_user_id, owned_expense_id, bad_amount, label
    ):
        """Invalid amount must not update the expense row in the DB."""
        _login_as(client, empty_user_id)
        original_row = _get_expense_row(owned_expense_id)
        client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": bad_amount,
                "category": "Food",
                "date": "2026-07-01",
                "description": "Test",
            },
        )
        row_after = _get_expense_row(owned_expense_id)
        assert (
            row_after["amount"] == original_row["amount"]
        ), f"Invalid amount ({label}) must not change the stored amount"
        assert (
            row_after["category"] == original_row["category"]
        ), f"Invalid amount ({label}) must not change the stored category"

    def test_over_max_amount_rerenders_form(
        self, client, empty_user_id, owned_expense_id
    ):
        """An amount exceeding MAX_AMOUNT must re-render the edit form with status 200."""
        _login_as(client, empty_user_id)
        response = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": str(MAX_AMOUNT + 1),
                "category": "Food",
                "date": "2026-07-01",
                "description": "Too large",
            },
        )
        assert (
            response.status_code == 200
        ), f"Amount > MAX_AMOUNT ({MAX_AMOUNT}) must re-render the edit form (200), not redirect"

    def test_over_max_amount_does_not_mutate_db(
        self, client, empty_user_id, owned_expense_id
    ):
        """An amount exceeding MAX_AMOUNT must not update the DB row."""
        _login_as(client, empty_user_id)
        original_row = _get_expense_row(owned_expense_id)
        client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": str(MAX_AMOUNT + 1),
                "category": "Food",
                "date": "2026-07-01",
                "description": "Too large",
            },
        )
        row_after = _get_expense_row(owned_expense_id)
        assert (
            row_after["amount"] == original_row["amount"]
        ), "Amount > MAX_AMOUNT must not update the stored amount"


# ===========================================================================
# INVALID POST — CATEGORY VALIDATION
# ===========================================================================


class TestInvalidPostCategory:
    @pytest.mark.parametrize(
        "bad_category,label",
        [
            ("", "empty category"),
            ("food", "lowercase valid name"),
            ("FOOD", "uppercase valid name"),
            ("Groceries", "plausible but unlisted"),
            ("'; DROP TABLE expenses; --", "SQL injection attempt"),
        ],
    )
    def test_invalid_category_rerenders_edit_form(
        self, client, empty_user_id, owned_expense_id, bad_category, label
    ):
        """Invalid category must re-render the edit form with status 200."""
        _login_as(client, empty_user_id)
        response = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "20.00",
                "category": bad_category,
                "date": "2026-07-05",
                "description": "Test",
            },
        )
        assert (
            response.status_code == 200
        ), f"Invalid category ({label}) must re-render the edit form (200), not redirect"

    @pytest.mark.parametrize(
        "bad_category,label",
        [
            ("", "empty category"),
            ("Groceries", "unlisted category"),
        ],
    )
    def test_invalid_category_shows_error_message(
        self, client, empty_user_id, owned_expense_id, bad_category, label
    ):
        """Re-rendered edit form must contain an error message for an invalid category."""
        _login_as(client, empty_user_id)
        body = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "20.00",
                "category": bad_category,
                "date": "2026-07-05",
                "description": "Test",
            },
        ).get_data(as_text=True)
        assert (
            "error" in body.lower()
            or "please" in body.lower()
            or "valid" in body.lower()
        ), f"Invalid category ({label}) must produce an error message in the re-rendered form"

    @pytest.mark.parametrize(
        "bad_category,label",
        [
            ("", "empty category"),
            ("Groceries", "unlisted category"),
            ("food", "lowercase category"),
        ],
    )
    def test_invalid_category_does_not_mutate_db(
        self, client, empty_user_id, owned_expense_id, bad_category, label
    ):
        """Invalid category must not update the expense row in the DB."""
        _login_as(client, empty_user_id)
        original_row = _get_expense_row(owned_expense_id)
        client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "20.00",
                "category": bad_category,
                "date": "2026-07-05",
                "description": "Test",
            },
        )
        row_after = _get_expense_row(owned_expense_id)
        assert (
            row_after["category"] == original_row["category"]
        ), f"Invalid category ({label}) must not change the stored category"


# ===========================================================================
# INVALID POST — DATE VALIDATION
# ===========================================================================


class TestInvalidPostDate:
    @pytest.mark.parametrize(
        "bad_date,label",
        [
            ("", "empty date"),
            ("not-a-date", "alphabetic string"),
            ("2026/07/05", "wrong separator"),
            ("07-05-2026", "MM-DD-YYYY format"),
            ("2026-13-40", "out-of-range month/day"),
            ("yesterday", "natural language"),
        ],
    )
    def test_invalid_date_rerenders_edit_form(
        self, client, empty_user_id, owned_expense_id, bad_date, label
    ):
        """Invalid date must re-render the edit form with status 200."""
        _login_as(client, empty_user_id)
        response = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "15.00",
                "category": "Transport",
                "date": bad_date,
                "description": "Test",
            },
        )
        assert (
            response.status_code == 200
        ), f"Invalid date ({label}) must re-render the edit form (200), not redirect"

    @pytest.mark.parametrize(
        "bad_date,label",
        [
            ("", "empty date"),
            ("not-a-date", "alphabetic string"),
            ("2026-13-40", "out-of-range month/day"),
        ],
    )
    def test_invalid_date_shows_error_message(
        self, client, empty_user_id, owned_expense_id, bad_date, label
    ):
        """Re-rendered edit form must contain an error message for an invalid date."""
        _login_as(client, empty_user_id)
        body = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "15.00",
                "category": "Transport",
                "date": bad_date,
                "description": "Test",
            },
        ).get_data(as_text=True)
        assert (
            "error" in body.lower()
            or "please" in body.lower()
            or "valid" in body.lower()
        ), f"Invalid date ({label}) must produce an error message in the re-rendered form"

    @pytest.mark.parametrize(
        "bad_date,label",
        [
            ("", "empty date"),
            ("not-a-date", "alphabetic string"),
            ("2026-13-40", "out-of-range month/day"),
        ],
    )
    def test_invalid_date_does_not_mutate_db(
        self, client, empty_user_id, owned_expense_id, bad_date, label
    ):
        """Invalid date must not update the expense row in the DB."""
        _login_as(client, empty_user_id)
        original_row = _get_expense_row(owned_expense_id)
        client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "15.00",
                "category": "Transport",
                "date": bad_date,
                "description": "Test",
            },
        )
        row_after = _get_expense_row(owned_expense_id)
        assert (
            row_after["date"] == original_row["date"]
        ), f"Invalid date ({label}) must not change the stored date"


# ===========================================================================
# INVALID POST — DESCRIPTION VALIDATION
# ===========================================================================


class TestInvalidPostDescription:
    def test_over_max_description_rerenders_form(
        self, client, empty_user_id, owned_expense_id
    ):
        """A description exceeding MAX_DESCRIPTION_LEN must re-render the edit form (200)."""
        _login_as(client, empty_user_id)
        long_description = "x" * (MAX_DESCRIPTION_LEN + 1)
        response = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "25.00",
                "category": "Food",
                "date": "2026-07-01",
                "description": long_description,
            },
        )
        assert (
            response.status_code == 200
        ), f"Description > {MAX_DESCRIPTION_LEN} chars must re-render the edit form (200)"

    def test_over_max_description_shows_error_message(
        self, client, empty_user_id, owned_expense_id
    ):
        """Re-rendered edit form must contain an error message for an over-long description."""
        _login_as(client, empty_user_id)
        long_description = "x" * (MAX_DESCRIPTION_LEN + 1)
        body = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "25.00",
                "category": "Food",
                "date": "2026-07-01",
                "description": long_description,
            },
        ).get_data(as_text=True)
        assert (
            "error" in body.lower() or "500" in body or str(MAX_DESCRIPTION_LEN) in body
        ), "Over-long description must produce an error message in the re-rendered form"

    def test_over_max_description_does_not_mutate_db(
        self, client, empty_user_id, owned_expense_id
    ):
        """An over-long description must not update the expense row in the DB."""
        _login_as(client, empty_user_id)
        original_row = _get_expense_row(owned_expense_id)
        long_description = "x" * (MAX_DESCRIPTION_LEN + 1)
        client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "25.00",
                "category": "Food",
                "date": "2026-07-01",
                "description": long_description,
            },
        )
        row_after = _get_expense_row(owned_expense_id)
        assert (
            row_after["description"] == original_row["description"]
        ), "Over-long description must not update the stored description"

    def test_exact_max_description_length_is_accepted(
        self, client, empty_user_id, owned_expense_id
    ):
        """A description of exactly MAX_DESCRIPTION_LEN characters must be accepted."""
        _login_as(client, empty_user_id)
        exact_description = "a" * MAX_DESCRIPTION_LEN
        response = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "25.00",
                "category": "Food",
                "date": "2026-07-01",
                "description": exact_description,
            },
        )
        assert (
            response.status_code == 302
        ), f"Description of exactly {MAX_DESCRIPTION_LEN} chars must be accepted (302 redirect)"


# ===========================================================================
# FORM VALUE PRESERVATION ON VALIDATION ERROR
# ===========================================================================


class TestFormValuePreservationOnError:
    def test_submitted_amount_preserved_on_invalid_category(
        self, client, empty_user_id, owned_expense_id
    ):
        """Submitted amount must be echoed back when category is invalid."""
        _login_as(client, empty_user_id)
        body = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "88.88",
                "category": "",
                "date": "2026-07-10",
                "description": "Some description",
            },
        ).get_data(as_text=True)
        assert (
            "88.88" in body
        ), "Submitted amount must be preserved in the re-rendered form when category is invalid"

    def test_submitted_description_preserved_on_invalid_amount(
        self, client, empty_user_id, owned_expense_id
    ):
        """Submitted description must be echoed back when amount is invalid."""
        _login_as(client, empty_user_id)
        body = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "",
                "category": "Health",
                "date": "2026-07-10",
                "description": "Keep this text",
            },
        ).get_data(as_text=True)
        assert (
            "Keep this text" in body
        ), "Submitted description must be preserved in the re-rendered form when amount is invalid"

    def test_submitted_category_preserved_on_invalid_amount(
        self, client, empty_user_id, owned_expense_id
    ):
        """Submitted category must be echoed back when amount is invalid."""
        _login_as(client, empty_user_id)
        body = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "-1",
                "category": "Shopping",
                "date": "2026-07-10",
                "description": "",
            },
        ).get_data(as_text=True)
        assert (
            "Shopping" in body
        ), "Submitted category must be preserved in the re-rendered form when amount is invalid"

    def test_submitted_date_preserved_on_invalid_amount(
        self, client, empty_user_id, owned_expense_id
    ):
        """Submitted date must be echoed back when amount is invalid."""
        _login_as(client, empty_user_id)
        body = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "abc",
                "category": "Bills",
                "date": "2026-08-20",
                "description": "",
            },
        ).get_data(as_text=True)
        assert (
            "2026-08-20" in body
        ), "Submitted date must be preserved in the re-rendered form when amount is invalid"

    def test_submitted_amount_preserved_on_invalid_date(
        self, client, empty_user_id, owned_expense_id
    ):
        """Submitted amount must be echoed back when date is invalid."""
        _login_as(client, empty_user_id)
        body = client.post(
            f"/expenses/{owned_expense_id}/edit",
            data={
                "amount": "55.55",
                "category": "Entertainment",
                "date": "not-a-date",
                "description": "Test",
            },
        ).get_data(as_text=True)
        assert (
            "55.55" in body
        ), "Submitted amount must be preserved in the re-rendered form when date is invalid"


# ===========================================================================
# CROSS-USER OWNERSHIP ENFORCEMENT (POST)
# ===========================================================================


class TestCrossUserOwnershipPost:
    def test_post_to_another_users_expense_returns_404(
        self, client, empty_user_id, other_user_expense_id
    ):
        """POST to an expense owned by a different user must return 404."""
        _login_as(client, empty_user_id)
        response = client.post(
            f"/expenses/{other_user_expense_id}/edit",
            data={
                "amount": "1.00",
                "category": "Food",
                "date": "2026-06-01",
                "description": "Attempted hijack",
            },
        )
        assert (
            response.status_code == 404
        ), "POST to another user's expense must return 404"

    def test_post_to_another_users_expense_does_not_modify_row(
        self, client, empty_user_id, other_user_expense_id
    ):
        """POST to another user's expense must not change any values in the DB."""
        _login_as(client, empty_user_id)
        original_row = _get_expense_row(other_user_expense_id)
        client.post(
            f"/expenses/{other_user_expense_id}/edit",
            data={
                "amount": "1.00",
                "category": "Food",
                "date": "2026-06-01",
                "description": "Attempted hijack",
            },
        )
        row_after = _get_expense_row(other_user_expense_id)
        assert (
            row_after["amount"] == original_row["amount"]
        ), "Cross-user POST must not modify the target expense's amount"
        assert (
            row_after["category"] == original_row["category"]
        ), "Cross-user POST must not modify the target expense's category"
        assert (
            row_after["date"] == original_row["date"]
        ), "Cross-user POST must not modify the target expense's date"
        assert (
            row_after["description"] == original_row["description"]
        ), "Cross-user POST must not modify the target expense's description"

    def test_post_to_another_users_expense_does_not_create_row(
        self, client, empty_user_id, other_user_id, other_user_expense_id
    ):
        """POST to another user's expense must not insert any new expense rows."""
        _login_as(client, empty_user_id)
        count_before = _expense_count(other_user_id)
        client.post(
            f"/expenses/{other_user_expense_id}/edit",
            data={
                "amount": "1.00",
                "category": "Food",
                "date": "2026-06-01",
                "description": "Attempted hijack",
            },
        )
        count_after = _expense_count(other_user_id)
        assert (
            count_after == count_before
        ), "Cross-user POST must not insert a new expense row for the target user"


# ===========================================================================
# PROFILE PAGE — EDIT LINKS
# ===========================================================================


class TestProfileEditLinks:
    def test_profile_contains_edit_link(self, client, seed_user_id):
        """Profile page must contain at least one Edit link for each transaction row."""
        _login_as(client, seed_user_id)
        body = client.get("/profile").get_data(as_text=True)
        assert "Edit" in body, "Profile page must show 'Edit' text for transaction rows"

    def test_profile_edit_link_points_to_edit_route(self, client, seed_user_id):
        """The Edit link href must contain '/expenses/' and '/edit' for the correct route."""
        _login_as(client, seed_user_id)
        body = client.get("/profile").get_data(as_text=True)
        assert (
            "/expenses/" in body and "/edit" in body
        ), "Profile page must contain edit links matching the /expenses/<id>/edit URL pattern"

    def test_profile_edit_link_for_own_expense_is_accessible(
        self, client, empty_user_id
    ):
        """An Edit link on the profile page must resolve to the correct expense's edit form."""
        _login_as(client, empty_user_id)
        expense_id = _create_test_expense(
            empty_user_id,
            amount=30.00,
            category="Bills",
            date="2026-03-10",
            description="Profile edit link test",
        )
        # Confirm the edit URL for this expense is reachable
        response = client.get(f"/expenses/{expense_id}/edit")
        assert (
            response.status_code == 200
        ), "An Edit link on the profile page must lead to a valid 200 edit form"

    def test_profile_edit_link_contains_expense_id(self, client, empty_user_id):
        """The Edit links on the profile page must include the expense's integer id in the href."""
        _login_as(client, empty_user_id)
        expense_id = _create_test_expense(
            empty_user_id,
            amount=55.00,
            category="Health",
            date="2026-04-01",
            description="ID in link test",
        )
        body = client.get("/profile").get_data(as_text=True)
        assert (
            str(expense_id) in body
        ), f"Profile page must contain the expense id ({expense_id}) in the Edit link href"
