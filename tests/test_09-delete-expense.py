"""Tests for Step 09 — Delete Expense feature.

Route under test:
    POST /expenses/<int:id>/delete  — delete the expense if owned by current user,
                                      flash confirmation, redirect to /profile
                                      (logged-in only; GET returns 405)

DB helpers exercised indirectly:
    database.db.get_expense_by_id(expense_id, user_id)
    database.db.delete_expense(expense_id, user_id)

Spec constants / invariants:
    - Flash message on success : "Expense deleted."
    - Flash message on logout  : contains "sign in" / "please"
    - Missing or cross-user id : abort(404) — never leaks existence
    - GET to delete URL        : 405 Method Not Allowed
"""

import pytest

from database.db import create_expense, create_user, get_db

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
# Fixtures (local; supplement conftest.py which provides app, client,
# seed_user_id, empty_user_id)
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
    def test_post_unauthenticated_redirects_to_login(self, client, owned_expense_id):
        """Unauthenticated POST /expenses/<id>/delete must redirect 302 to /login."""
        response = client.post(f"/expenses/{owned_expense_id}/delete")
        assert (
            response.status_code == 302
        ), "Expected 302 redirect for unauthenticated POST /expenses/<id>/delete"
        assert (
            "/login" in response.headers["Location"]
        ), "Unauthenticated POST must redirect to /login"

    def test_post_unauthenticated_flashes_sign_in_message(
        self, client, owned_expense_id
    ):
        """Unauthenticated POST must flash the sign-in message before redirecting."""
        response = client.post(
            f"/expenses/{owned_expense_id}/delete", follow_redirects=True
        )
        body = response.get_data(as_text=True)
        assert (
            "sign in" in body.lower() or "please" in body.lower()
        ), "Unauthenticated POST must flash 'Please sign in to view that page.' message"

    def test_post_unauthenticated_does_not_delete_expense(
        self, client, owned_expense_id
    ):
        """Unauthenticated POST must not remove the expense row from the DB."""
        client.post(f"/expenses/{owned_expense_id}/delete")
        row = _get_expense_row(owned_expense_id)
        assert (
            row is not None
        ), "Unauthenticated POST must not delete the expense — row must still exist in DB"


# ===========================================================================
# METHOD GUARD — GET IS NOT ALLOWED
# ===========================================================================


class TestMethodGuard:
    def test_get_returns_405(self, client, empty_user_id, owned_expense_id):
        """GET /expenses/<id>/delete must return 405 Method Not Allowed."""
        _login_as(client, empty_user_id)
        response = client.get(f"/expenses/{owned_expense_id}/delete")
        assert (
            response.status_code == 405
        ), "GET to the delete URL must return 405 Method Not Allowed"

    def test_get_does_not_delete_expense(self, client, empty_user_id, owned_expense_id):
        """GET to the delete URL must not remove the expense row from the DB."""
        _login_as(client, empty_user_id)
        client.get(f"/expenses/{owned_expense_id}/delete")
        row = _get_expense_row(owned_expense_id)
        assert (
            row is not None
        ), "GET to the delete URL must not delete the expense — row must still exist in DB"


# ===========================================================================
# VALID DELETE — HAPPY PATH
# ===========================================================================


class TestValidDelete:
    def test_valid_post_redirects_302(self, client, empty_user_id, owned_expense_id):
        """Valid POST to delete own expense must return 302."""
        _login_as(client, empty_user_id)
        response = client.post(f"/expenses/{owned_expense_id}/delete")
        assert response.status_code == 302, "Valid delete POST must return 302 redirect"

    def test_valid_post_redirects_to_profile(
        self, client, empty_user_id, owned_expense_id
    ):
        """Valid POST must redirect to /profile."""
        _login_as(client, empty_user_id)
        response = client.post(f"/expenses/{owned_expense_id}/delete")
        assert (
            "/profile" in response.headers["Location"]
        ), "Valid delete POST must redirect to /profile"

    def test_valid_post_flashes_expense_deleted(
        self, client, empty_user_id, owned_expense_id
    ):
        """Valid POST must flash 'Expense deleted.' on the profile page."""
        _login_as(client, empty_user_id)
        response = client.post(
            f"/expenses/{owned_expense_id}/delete", follow_redirects=True
        )
        body = response.get_data(as_text=True)
        assert (
            "Expense deleted" in body
        ), "Profile page after valid delete must contain 'Expense deleted' flash message"

    def test_valid_post_removes_row_from_db(
        self, client, empty_user_id, owned_expense_id
    ):
        """Valid POST must remove the expense row from the DB."""
        _login_as(client, empty_user_id)
        client.post(f"/expenses/{owned_expense_id}/delete")
        row = _get_expense_row(owned_expense_id)
        assert (
            row is None
        ), "Expense row must no longer exist in the DB after a valid delete"

    def test_valid_post_decreases_expense_count_by_one(
        self, client, empty_user_id, owned_expense_id
    ):
        """Valid POST must decrease the user's expense count by exactly 1."""
        _login_as(client, empty_user_id)
        count_before = _expense_count(empty_user_id)
        client.post(f"/expenses/{owned_expense_id}/delete")
        count_after = _expense_count(empty_user_id)
        assert count_after == count_before - 1, (
            f"Expense count must decrease by exactly 1 after delete "
            f"(before={count_before}, after={count_after})"
        )

    def test_valid_post_deleted_row_absent_from_profile(
        self, client, empty_user_id, owned_expense_id
    ):
        """After a valid delete, the deleted expense must no longer appear on /profile."""
        _login_as(client, empty_user_id)
        # Use a distinctive description to identify the row in profile HTML
        expense_id = _create_test_expense(
            empty_user_id,
            amount=12.34,
            category="Health",
            date="2026-03-03",
            description="Unique expense to delete",
        )
        client.post(f"/expenses/{expense_id}/delete")
        body = client.get("/profile").get_data(as_text=True)
        assert (
            "Unique expense to delete" not in body
        ), "Deleted expense description must not appear on /profile after deletion"

    def test_valid_post_does_not_delete_other_expenses(self, client, empty_user_id):
        """Deleting one expense must not remove other expenses belonging to the same user."""
        _login_as(client, empty_user_id)
        expense_id_a = _create_test_expense(
            empty_user_id,
            amount=10.00,
            category="Food",
            date="2026-04-01",
            description="Expense A",
        )
        expense_id_b = _create_test_expense(
            empty_user_id,
            amount=20.00,
            category="Bills",
            date="2026-04-02",
            description="Expense B",
        )
        client.post(f"/expenses/{expense_id_a}/delete")
        row_b = _get_expense_row(expense_id_b)
        assert (
            row_b is not None
        ), "Deleting expense A must not remove expense B from the DB"


# ===========================================================================
# 404 — NON-EXISTENT ID
# ===========================================================================


class TestNonExistentId:
    def test_post_nonexistent_id_returns_404(self, client, empty_user_id):
        """POST to /expenses/999999/delete for a non-existent id must return 404."""
        _login_as(client, empty_user_id)
        response = client.post("/expenses/999999/delete")
        assert (
            response.status_code == 404
        ), "POST for a non-existent expense id must return 404"


# ===========================================================================
# OWNERSHIP ENFORCEMENT — CROSS-USER
# ===========================================================================


class TestCrossUserOwnership:
    def test_post_to_another_users_expense_returns_404(
        self, client, empty_user_id, other_user_expense_id
    ):
        """POST to delete another user's expense must return 404."""
        _login_as(client, empty_user_id)
        response = client.post(f"/expenses/{other_user_expense_id}/delete")
        assert (
            response.status_code == 404
        ), "POST to another user's expense must return 404"

    def test_post_to_another_users_expense_does_not_delete_row(
        self, client, empty_user_id, other_user_expense_id
    ):
        """POST to another user's expense must not remove that row from the DB."""
        _login_as(client, empty_user_id)
        client.post(f"/expenses/{other_user_expense_id}/delete")
        row = _get_expense_row(other_user_expense_id)
        assert (
            row is not None
        ), "Cross-user delete POST must not remove the target expense from the DB"

    def test_post_to_another_users_expense_count_unchanged(
        self, client, empty_user_id, other_user_id, other_user_expense_id
    ):
        """POST to another user's expense must not change that user's expense count."""
        _login_as(client, empty_user_id)
        count_before = _expense_count(other_user_id)
        client.post(f"/expenses/{other_user_expense_id}/delete")
        count_after = _expense_count(other_user_id)
        assert count_after == count_before, (
            f"Cross-user delete POST must not change the target user's expense count "
            f"(before={count_before}, after={count_after})"
        )


# ===========================================================================
# NO EXISTENCE LEAK — MISSING ID AND CROSS-USER ID RETURN IDENTICAL 404
# ===========================================================================


class TestNoExistenceLeak:
    def test_missing_id_and_cross_user_id_both_return_404(
        self, client, empty_user_id, other_user_expense_id
    ):
        """A POST for a non-existent id and a POST for another user's id must both return 404."""
        _login_as(client, empty_user_id)
        missing_response = client.post("/expenses/888888/delete")
        cross_response = client.post(f"/expenses/{other_user_expense_id}/delete")
        assert missing_response.status_code == cross_response.status_code == 404, (
            "Both a missing expense id and another user's expense id must return 404 "
            "— the route must never leak whether an id exists"
        )


# ===========================================================================
# PROFILE PAGE — DELETE FORM RENDERING
# ===========================================================================


class TestProfileDeleteFormRendering:
    def test_profile_contains_delete_form(self, client, seed_user_id):
        """Profile page must contain at least one <form element for the delete action."""
        _login_as(client, seed_user_id)
        body = client.get("/profile").get_data(as_text=True)
        assert (
            "<form" in body.lower()
        ), "Profile page must contain a <form> element for the delete control"

    def test_profile_delete_form_uses_post_method(self, client, seed_user_id):
        """The delete form on /profile must use method='post' (case-insensitive)."""
        _login_as(client, seed_user_id)
        body = client.get("/profile").get_data(as_text=True).lower()
        # Look for a form tag that specifies method="post"
        assert (
            'method="post"' in body or "method='post'" in body
        ), 'Delete form must declare method="post" (GET forms must not trigger deletion)'

    def test_profile_delete_form_action_targets_delete_route(
        self, client, empty_user_id
    ):
        """The delete form action on /profile must point to /expenses/<id>/delete."""
        _login_as(client, empty_user_id)
        expense_id = _create_test_expense(
            empty_user_id,
            amount=8.00,
            category="Other",
            date="2026-05-05",
            description="Form action test",
        )
        body = client.get("/profile").get_data(as_text=True)
        expected_action = f"/expenses/{expense_id}/delete"
        assert expected_action in body, (
            f"Profile page must contain a form with action='{expected_action}' "
            f"for the delete control"
        )

    def test_profile_delete_form_button_has_data_confirm(self, client, empty_user_id):
        """The delete button in the form must carry a data-confirm attribute."""
        _login_as(client, empty_user_id)
        _create_test_expense(
            empty_user_id,
            amount=15.00,
            category="Food",
            date="2026-06-01",
            description="Confirm attribute test",
        )
        body = client.get("/profile").get_data(as_text=True)
        assert (
            "data-confirm" in body
        ), "Delete button must carry a data-confirm attribute for the JS confirmation prompt"

    def test_profile_delete_form_contains_delete_text(self, client, seed_user_id):
        """Profile page must contain the word 'Delete' (or 'delete') on each transaction row."""
        _login_as(client, seed_user_id)
        body = client.get("/profile").get_data(as_text=True)
        assert (
            "delete" in body.lower()
        ), "Profile page must show 'Delete' text identifying the delete control"

    def test_profile_shows_delete_control_alongside_edit(self, client, seed_user_id):
        """Profile page transaction rows must contain both Edit and Delete controls."""
        _login_as(client, seed_user_id)
        body = client.get("/profile").get_data(as_text=True)
        assert (
            "edit" in body.lower()
        ), "Profile page must still contain the Edit control alongside Delete"
        assert (
            "delete" in body.lower()
        ), "Profile page must contain the Delete control alongside Edit"
