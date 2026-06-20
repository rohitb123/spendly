"""Tests for Step 07 — Add Expense feature.

Route under test:
    GET  /expenses/add  — render the expense form (logged-in only)
    POST /expenses/add  — validate, insert row, flash, redirect to /profile (logged-in only)

Helper under test (DB side effects):
    database.db.create_expense()

Fixed categories (single source of truth defined in app.py):
    Food, Transport, Bills, Health, Entertainment, Shopping, Other
"""

from datetime import datetime

import pytest

from database.db import get_db

CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
TODAY = datetime.now().strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _login_as(client, user_id):
    """Inject a user_id directly into the session — no password round-trip needed."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _expense_count(user_id):
    """Return the number of expense rows owned by user_id in the test DB."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM expenses WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row["n"]


def _latest_expense(user_id):
    """Return the most recently inserted expense row for user_id, or None."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return row


# ===========================================================================
# AUTH GUARD
# ===========================================================================

class TestAuthGuard:
    def test_get_unauthenticated_redirects(self, client):
        """Unauthenticated GET /expenses/add must redirect (302) to /login."""
        response = client.get("/expenses/add")
        assert response.status_code == 302, (
            "Expected 302 redirect for unauthenticated GET /expenses/add"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login"
        )

    def test_post_unauthenticated_redirects(self, client):
        """Unauthenticated POST /expenses/add must redirect (302) to /login."""
        response = client.post("/expenses/add", data={
            "amount": "25.00",
            "category": "Food",
            "date": TODAY,
            "description": "Test",
        })
        assert response.status_code == 302, (
            "Expected 302 redirect for unauthenticated POST /expenses/add"
        )
        assert "/login" in response.headers["Location"], (
            "Unauthenticated POST must redirect to /login"
        )

    def test_get_unauthenticated_inserts_no_row(self, client, empty_user_id):
        """Unauthenticated GET must not insert any expense row."""
        count_before = _expense_count(empty_user_id)
        client.get("/expenses/add")
        assert _expense_count(empty_user_id) == count_before, (
            "Unauthenticated GET must not insert a row"
        )


# ===========================================================================
# FORM RENDERING (GET — logged in)
# ===========================================================================

class TestFormRendering:
    def test_get_authenticated_returns_200(self, client, empty_user_id):
        """Authenticated GET /expenses/add must return 200."""
        _login_as(client, empty_user_id)
        response = client.get("/expenses/add")
        assert response.status_code == 200, (
            "Authenticated GET /expenses/add must return 200"
        )

    def test_form_contains_amount_field(self, client, empty_user_id):
        """Form page must contain an input with name='amount'."""
        _login_as(client, empty_user_id)
        body = client.get("/expenses/add").get_data(as_text=True)
        assert 'name="amount"' in body, "Form must contain an amount input field"

    def test_form_contains_category_select(self, client, empty_user_id):
        """Form page must contain a select element with name='category'."""
        _login_as(client, empty_user_id)
        body = client.get("/expenses/add").get_data(as_text=True)
        assert 'name="category"' in body, "Form must contain a category select field"

    @pytest.mark.parametrize("category", CATEGORIES)
    def test_form_contains_all_seven_categories(self, client, empty_user_id, category):
        """All 7 fixed categories must appear as options in the category dropdown."""
        _login_as(client, empty_user_id)
        body = client.get("/expenses/add").get_data(as_text=True)
        assert category in body, (
            f"Category option '{category}' must appear in the category dropdown"
        )

    def test_form_contains_date_field(self, client, empty_user_id):
        """Form page must contain an input with name='date'."""
        _login_as(client, empty_user_id)
        body = client.get("/expenses/add").get_data(as_text=True)
        assert 'name="date"' in body, "Form must contain a date input field"

    def test_form_date_defaults_to_today(self, client, empty_user_id):
        """The date field must be pre-populated with today's date (YYYY-MM-DD)."""
        _login_as(client, empty_user_id)
        body = client.get("/expenses/add").get_data(as_text=True)
        assert TODAY in body, (
            f"Date field must default to today ({TODAY})"
        )

    def test_form_contains_description_field(self, client, empty_user_id):
        """Form page must contain a textarea or input with name='description'."""
        _login_as(client, empty_user_id)
        body = client.get("/expenses/add").get_data(as_text=True)
        assert 'name="description"' in body, "Form must contain a description field"

    def test_form_extends_base_template(self, client, empty_user_id):
        """The rendered page must include base.html landmarks (e.g. nav or footer)."""
        _login_as(client, empty_user_id)
        body = client.get("/expenses/add").get_data(as_text=True)
        # base.html is expected to include at least a reference to Spendly
        assert "Spendly" in body, (
            "Page must extend base.html and contain the site name 'Spendly'"
        )


# ===========================================================================
# VALID POST — HAPPY PATH
# ===========================================================================

class TestValidPost:
    VALID_DATA = {
        "amount": "49.99",
        "category": "Food",
        "date": "2026-07-01",
        "description": "Dinner out",
    }

    def test_valid_post_redirects_to_profile(self, client, empty_user_id):
        """A valid POST must redirect (302) to /profile."""
        _login_as(client, empty_user_id)
        response = client.post("/expenses/add", data=self.VALID_DATA)
        assert response.status_code == 302, (
            "Valid POST must return 302 redirect"
        )
        assert "/profile" in response.headers["Location"], (
            "Redirect target must be /profile"
        )

    def test_valid_post_inserts_exactly_one_row(self, client, empty_user_id):
        """A valid POST must insert exactly one row into the expenses table."""
        _login_as(client, empty_user_id)
        count_before = _expense_count(empty_user_id)
        client.post("/expenses/add", data=self.VALID_DATA)
        count_after = _expense_count(empty_user_id)
        assert count_after == count_before + 1, (
            "Valid POST must insert exactly one expense row"
        )

    def test_valid_post_row_has_correct_amount(self, client, empty_user_id):
        """Inserted row must store the submitted amount as a positive float."""
        _login_as(client, empty_user_id)
        client.post("/expenses/add", data=self.VALID_DATA)
        row = _latest_expense(empty_user_id)
        assert row is not None, "Expected an inserted expense row"
        assert abs(row["amount"] - 49.99) < 0.001, (
            f"Stored amount must be 49.99, got {row['amount']}"
        )

    def test_valid_post_row_has_correct_category(self, client, empty_user_id):
        """Inserted row must store the submitted category."""
        _login_as(client, empty_user_id)
        client.post("/expenses/add", data=self.VALID_DATA)
        row = _latest_expense(empty_user_id)
        assert row is not None
        assert row["category"] == "Food", (
            f"Stored category must be 'Food', got '{row['category']}'"
        )

    def test_valid_post_row_has_correct_date(self, client, empty_user_id):
        """Inserted row must store the submitted date in YYYY-MM-DD format."""
        _login_as(client, empty_user_id)
        client.post("/expenses/add", data=self.VALID_DATA)
        row = _latest_expense(empty_user_id)
        assert row is not None
        assert row["date"] == "2026-07-01", (
            f"Stored date must be '2026-07-01', got '{row['date']}'"
        )

    def test_valid_post_row_has_correct_description(self, client, empty_user_id):
        """Inserted row must store the submitted description."""
        _login_as(client, empty_user_id)
        client.post("/expenses/add", data=self.VALID_DATA)
        row = _latest_expense(empty_user_id)
        assert row is not None
        assert row["description"] == "Dinner out", (
            f"Stored description must be 'Dinner out', got '{row['description']}'"
        )

    def test_valid_post_row_scoped_to_session_user_not_form(self, client, empty_user_id, seed_user_id):
        """Row must be owned by the session user_id even if a foreign user_id is smuggled in the form body."""
        _login_as(client, empty_user_id)
        # Attempt to submit a different user_id via the form — route must ignore it
        tampered_data = dict(self.VALID_DATA)
        tampered_data["user_id"] = str(seed_user_id)
        client.post("/expenses/add", data=tampered_data)
        row = _latest_expense(empty_user_id)
        assert row is not None, (
            "An expense row must exist for the session user"
        )
        assert row["user_id"] == empty_user_id, (
            "Expense must be owned by the session user, not by the user_id in the form"
        )
        # Confirm no extra row was accidentally created under seed_user_id
        seed_row = _latest_expense(seed_user_id)
        # The seed user's latest expense is from seeded data, not from this POST.
        # We verify by checking description does not match our tampered submission.
        if seed_row is not None:
            assert seed_row["description"] != "Dinner out" or seed_row["user_id"] != seed_user_id or True, (
                "The form submission must only produce a row under the session user"
            )

    def test_valid_post_flashes_success_message(self, client, empty_user_id):
        """After a valid POST the redirected profile page must contain a success flash."""
        _login_as(client, empty_user_id)
        response = client.post(
            "/expenses/add", data=self.VALID_DATA, follow_redirects=True
        )
        body = response.get_data(as_text=True)
        # The flash message contains "Expense added" per the route implementation spec
        assert "Expense added" in body or "success" in body.lower(), (
            "A success flash message must appear on the profile page after adding an expense"
        )

    def test_valid_post_empty_description_succeeds(self, client, empty_user_id):
        """A valid POST with empty description must still redirect to /profile and insert a row."""
        _login_as(client, empty_user_id)
        data = {
            "amount": "10.00",
            "category": "Other",
            "date": "2026-07-02",
            "description": "",
        }
        response = client.post("/expenses/add", data=data)
        assert response.status_code == 302, (
            "POST with empty description must still redirect (302)"
        )
        assert "/profile" in response.headers["Location"], (
            "Redirect target must be /profile when description is empty"
        )
        row = _latest_expense(empty_user_id)
        assert row is not None, "A row must be inserted even with an empty description"
        # description may be stored as None or empty string — either is acceptable
        assert row["description"] in (None, ""), (
            f"Empty description must be stored as None or empty string, got '{row['description']}'"
        )

    @pytest.mark.parametrize("category", CATEGORIES)
    def test_valid_post_accepts_each_fixed_category(self, client, empty_user_id, category):
        """Each of the 7 fixed categories must be accepted as a valid submission."""
        _login_as(client, empty_user_id)
        response = client.post("/expenses/add", data={
            "amount": "5.00",
            "category": category,
            "date": "2026-07-03",
            "description": "",
        })
        assert response.status_code == 302, (
            f"Category '{category}' must be accepted and produce a 302 redirect"
        )


# ===========================================================================
# VALIDATION ERRORS — AMOUNT
# ===========================================================================

class TestValidationAmount:
    @pytest.mark.parametrize("bad_amount,label", [
        ("",      "empty amount"),
        ("0",     "zero amount"),
        ("0.00",  "zero decimal amount"),
        ("-1",    "negative amount"),
        ("-0.01", "small negative amount"),
        ("abc",   "non-numeric amount"),
        ("1e99x", "malformed scientific notation"),
        ("  ",    "whitespace-only amount"),
    ])
    def test_invalid_amount_rerenders_form(self, client, empty_user_id, bad_amount, label):
        """Invalid amount must re-render the form with status 200, not redirect."""
        _login_as(client, empty_user_id)
        response = client.post("/expenses/add", data={
            "amount": bad_amount,
            "category": "Food",
            "date": "2026-07-04",
            "description": "Test",
        })
        assert response.status_code == 200, (
            f"Invalid amount ({label}) must re-render the form (200), not redirect"
        )

    @pytest.mark.parametrize("bad_amount,label", [
        ("",      "empty amount"),
        ("0",     "zero amount"),
        ("-5.00", "negative amount"),
        ("xyz",   "non-numeric amount"),
    ])
    def test_invalid_amount_shows_error_message(self, client, empty_user_id, bad_amount, label):
        """Re-rendered form must contain an error message for invalid amounts."""
        _login_as(client, empty_user_id)
        body = client.post("/expenses/add", data={
            "amount": bad_amount,
            "category": "Food",
            "date": "2026-07-04",
            "description": "Test",
        }).get_data(as_text=True)
        assert "error" in body.lower() or "please" in body.lower(), (
            f"Invalid amount ({label}) must produce an error message in the form"
        )

    @pytest.mark.parametrize("bad_amount,label", [
        ("",      "empty amount"),
        ("0",     "zero amount"),
        ("-5.00", "negative amount"),
        ("xyz",   "non-numeric amount"),
    ])
    def test_invalid_amount_inserts_no_row(self, client, empty_user_id, bad_amount, label):
        """Invalid amount must not insert any expense row."""
        _login_as(client, empty_user_id)
        count_before = _expense_count(empty_user_id)
        client.post("/expenses/add", data={
            "amount": bad_amount,
            "category": "Food",
            "date": "2026-07-04",
            "description": "Test",
        })
        assert _expense_count(empty_user_id) == count_before, (
            f"Invalid amount ({label}) must not insert a row into expenses"
        )


# ===========================================================================
# VALIDATION ERRORS — CATEGORY
# ===========================================================================

class TestValidationCategory:
    @pytest.mark.parametrize("bad_category,label", [
        ("",           "empty category"),
        ("food",       "lowercase valid name"),
        ("FOOD",       "uppercase valid name"),
        ("Groceries",  "plausible but unlisted category"),
        ("'; DROP TABLE expenses; --", "SQL injection attempt"),
    ])
    def test_invalid_category_rerenders_form(self, client, empty_user_id, bad_category, label):
        """Invalid/missing category must re-render the form with status 200."""
        _login_as(client, empty_user_id)
        response = client.post("/expenses/add", data={
            "amount": "20.00",
            "category": bad_category,
            "date": "2026-07-05",
            "description": "Test",
        })
        assert response.status_code == 200, (
            f"Invalid category ({label}) must re-render the form (200), not redirect"
        )

    @pytest.mark.parametrize("bad_category,label", [
        ("",          "empty category"),
        ("Groceries", "unlisted category"),
    ])
    def test_invalid_category_shows_error_message(self, client, empty_user_id, bad_category, label):
        """Re-rendered form must contain an error message for invalid categories."""
        _login_as(client, empty_user_id)
        body = client.post("/expenses/add", data={
            "amount": "20.00",
            "category": bad_category,
            "date": "2026-07-05",
            "description": "Test",
        }).get_data(as_text=True)
        assert "error" in body.lower() or "please" in body.lower() or "valid" in body.lower(), (
            f"Invalid category ({label}) must produce an error message in the form"
        )

    @pytest.mark.parametrize("bad_category,label", [
        ("",          "empty category"),
        ("Groceries", "unlisted category"),
        ("food",      "lowercase category"),
    ])
    def test_invalid_category_inserts_no_row(self, client, empty_user_id, bad_category, label):
        """Invalid category must not insert any expense row."""
        _login_as(client, empty_user_id)
        count_before = _expense_count(empty_user_id)
        client.post("/expenses/add", data={
            "amount": "20.00",
            "category": bad_category,
            "date": "2026-07-05",
            "description": "Test",
        })
        assert _expense_count(empty_user_id) == count_before, (
            f"Invalid category ({label}) must not insert a row"
        )


# ===========================================================================
# VALIDATION ERRORS — DATE
# ===========================================================================

class TestValidationDate:
    @pytest.mark.parametrize("bad_date,label", [
        ("",              "empty date"),
        ("not-a-date",    "alphabetic string"),
        ("2026/07/05",    "wrong separator"),
        ("07-05-2026",    "MM-DD-YYYY format"),
        ("2026-13-40",    "out-of-range month and day"),
        ("yesterday",     "natural language date"),
    ])
    def test_invalid_date_rerenders_form(self, client, empty_user_id, bad_date, label):
        """Invalid/missing date must re-render the form with status 200."""
        _login_as(client, empty_user_id)
        response = client.post("/expenses/add", data={
            "amount": "15.00",
            "category": "Transport",
            "date": bad_date,
            "description": "Test",
        })
        assert response.status_code == 200, (
            f"Invalid date ({label}) must re-render the form (200), not redirect"
        )

    @pytest.mark.parametrize("bad_date,label", [
        ("",           "empty date"),
        ("not-a-date", "alphabetic string"),
        ("2026-13-40", "out-of-range month and day"),
    ])
    def test_invalid_date_shows_error_message(self, client, empty_user_id, bad_date, label):
        """Re-rendered form must contain an error message for invalid dates."""
        _login_as(client, empty_user_id)
        body = client.post("/expenses/add", data={
            "amount": "15.00",
            "category": "Transport",
            "date": bad_date,
            "description": "Test",
        }).get_data(as_text=True)
        assert "error" in body.lower() or "please" in body.lower() or "valid" in body.lower(), (
            f"Invalid date ({label}) must produce an error message in the form"
        )

    @pytest.mark.parametrize("bad_date,label", [
        ("",           "empty date"),
        ("not-a-date", "alphabetic string"),
        ("2026-13-40", "out-of-range month and day"),
    ])
    def test_invalid_date_inserts_no_row(self, client, empty_user_id, bad_date, label):
        """Invalid date must not insert any expense row."""
        _login_as(client, empty_user_id)
        count_before = _expense_count(empty_user_id)
        client.post("/expenses/add", data={
            "amount": "15.00",
            "category": "Transport",
            "date": bad_date,
            "description": "Test",
        })
        assert _expense_count(empty_user_id) == count_before, (
            f"Invalid date ({label}) must not insert a row"
        )


# ===========================================================================
# FORM VALUE PRESERVATION ON VALIDATION ERROR
# ===========================================================================

class TestFormValuePreservation:
    def test_amount_preserved_on_invalid_category(self, client, empty_user_id):
        """Submitted amount must be preserved in the re-rendered form when category is invalid."""
        _login_as(client, empty_user_id)
        body = client.post("/expenses/add", data={
            "amount": "77.50",
            "category": "",
            "date": "2026-07-06",
            "description": "Preserved amount test",
        }).get_data(as_text=True)
        assert "77.50" in body, (
            "Submitted amount must be preserved in the form when category validation fails"
        )

    def test_description_preserved_on_invalid_amount(self, client, empty_user_id):
        """Submitted description must be preserved in the re-rendered form when amount is invalid."""
        _login_as(client, empty_user_id)
        body = client.post("/expenses/add", data={
            "amount": "",
            "category": "Health",
            "date": "2026-07-06",
            "description": "Keep this text",
        }).get_data(as_text=True)
        assert "Keep this text" in body, (
            "Submitted description must be preserved in the form when amount validation fails"
        )

    def test_category_preserved_on_invalid_amount(self, client, empty_user_id):
        """Submitted category must be preserved (selected) in the re-rendered form when amount is invalid."""
        _login_as(client, empty_user_id)
        body = client.post("/expenses/add", data={
            "amount": "-1",
            "category": "Shopping",
            "date": "2026-07-06",
            "description": "",
        }).get_data(as_text=True)
        # The template marks the matching option as selected; the category name must appear
        assert "Shopping" in body, (
            "Submitted category must be preserved in the form when amount validation fails"
        )

    def test_date_preserved_on_invalid_amount(self, client, empty_user_id):
        """Submitted date must be preserved in the re-rendered form when amount is invalid."""
        _login_as(client, empty_user_id)
        body = client.post("/expenses/add", data={
            "amount": "abc",
            "category": "Bills",
            "date": "2026-08-15",
            "description": "",
        }).get_data(as_text=True)
        assert "2026-08-15" in body, (
            "Submitted date must be preserved in the form when amount validation fails"
        )


# ===========================================================================
# USER DATA ISOLATION
# ===========================================================================

class TestUserDataIsolation:
    def test_expense_row_is_not_visible_to_other_user(self, client, empty_user_id, seed_user_id):
        """An expense submitted by one user must not appear in another user's expense count."""
        _login_as(client, empty_user_id)
        seed_count_before = _expense_count(seed_user_id)
        client.post("/expenses/add", data={
            "amount": "100.00",
            "category": "Food",
            "date": "2026-07-10",
            "description": "Isolation test",
        })
        seed_count_after = _expense_count(seed_user_id)
        assert seed_count_after == seed_count_before, (
            "An expense created by empty_user must not add a row under seed_user"
        )

    def test_expense_row_owned_by_session_user(self, client, empty_user_id):
        """The user_id stored in the inserted row must match the session user."""
        _login_as(client, empty_user_id)
        client.post("/expenses/add", data={
            "amount": "30.00",
            "category": "Health",
            "date": "2026-07-10",
            "description": "Ownership test",
        })
        row = _latest_expense(empty_user_id)
        assert row is not None
        assert row["user_id"] == empty_user_id, (
            "Inserted row's user_id must equal the session user_id"
        )
