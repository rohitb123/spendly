"""Tests for Step 06 — date-range filter on /profile.

Seed data (8 expenses for demo@spendly.com):
    2026-06-02  Food           ₹12.50   Coffee and bagel
    2026-06-04  Transport      ₹45.00   Uber to airport
    2026-06-05  Bills         ₹120.00   Electricity bill
    2026-06-07  Health         ₹30.00   Pharmacy
    2026-06-09  Entertainment  ₹60.00   Movie night
    2026-06-10  Shopping       ₹85.75   T-shirts
    2026-06-12  Other          ₹15.00   Stamps
    2026-06-13  Food           ₹22.40   Lunch with team

Inclusive range 2026-06-05 → 2026-06-10 catches 4 rows:
    Bills ₹120.00, Entertainment ₹60.00, Shopping ₹85.75, Health ₹30.00
    Total: ₹295.75, top_category: Bills
"""

import pytest

from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
)

# ---------------------------------------------------------------------------
# Convenience: descriptions inside the 2026-06-05→2026-06-10 window
# ---------------------------------------------------------------------------
IN_RANGE = {"Electricity bill", "Pharmacy", "Movie night", "T-shirts"}
OUT_OF_RANGE = {"Coffee and bagel", "Uber to airport", "Stamps", "Lunch with team"}

RANGE_TOTAL = "₹295.75"
RANGE_COUNT = 4
RANGE_TOP = "Bills"

ALL_TIME_TOTAL = "₹390.65"
ALL_TIME_COUNT = 8


# ===========================================================================
# Helper — log in the seed demo user via the test client session
# ===========================================================================

def _login_seed(client, seed_user_id):
    """Inject the seed user's id directly into the session (no password needed)."""
    with client.session_transaction() as sess:
        sess["user_id"] = seed_user_id


# ===========================================================================
# AUTH GUARD
# ===========================================================================

class TestAuthGuard:
    def test_logged_out_redirects_to_login(self, client):
        """Unauthenticated GET /profile must redirect to /login (spec: auth guard preserved)."""
        response = client.get("/profile")
        assert response.status_code == 302, "Expected redirect for unauthenticated user"
        assert "/login" in response.headers["Location"], (
            "Redirect target must be /login"
        )

    def test_logged_out_with_date_params_still_redirects(self, client):
        """Auth guard must fire even when query params are present."""
        response = client.get("/profile?start=2026-06-05&end=2026-06-10")
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


# ===========================================================================
# REGRESSION — NO PARAMS == ALL-TIME VIEW
# ===========================================================================

class TestNoParamsAllTimeView:
    def test_profile_no_params_returns_200(self, client, seed_user_id):
        """GET /profile with no params must return 200 (regression)."""
        _login_seed(client, seed_user_id)
        response = client.get("/profile")
        assert response.status_code == 200

    def test_profile_no_params_shows_all_time_total(self, client, seed_user_id):
        """All 8 seeded expenses must contribute to total when no filter is active."""
        _login_seed(client, seed_user_id)
        body = client.get("/profile").get_data(as_text=True)
        assert ALL_TIME_TOTAL in body, f"Expected all-time total {ALL_TIME_TOTAL} in page"

    def test_profile_no_params_shows_all_transactions(self, client, seed_user_id):
        """Every seeded description must appear on the unfiltered profile page."""
        _login_seed(client, seed_user_id)
        body = client.get("/profile").get_data(as_text=True)
        for desc in IN_RANGE | OUT_OF_RANGE:
            assert desc in body, f"Expected description '{desc}' in all-time view"

    def test_profile_no_params_summary_stats_correct(self, app, seed_user_id):
        """get_summary_stats with no range must return all-time figures."""
        stats = get_summary_stats(seed_user_id)
        assert stats["total_spent"] == ALL_TIME_TOTAL
        assert stats["transaction_count"] == ALL_TIME_COUNT
        assert stats["top_category"] == "Bills"

    def test_profile_no_params_no_range_active_caption(self, client, seed_user_id):
        """The 'Showing X – Y' caption must NOT appear when no filter is active."""
        _login_seed(client, seed_user_id)
        body = client.get("/profile").get_data(as_text=True)
        assert "Showing" not in body, (
            "Active-range caption must be absent when no filter is supplied"
        )


# ===========================================================================
# HAPPY PATH — VALID INCLUSIVE RANGE
# ===========================================================================

class TestValidDateRange:
    PARAMS = "?start=2026-06-05&end=2026-06-10"

    def test_route_returns_200(self, client, seed_user_id):
        """GET /profile with a valid range must return 200."""
        _login_seed(client, seed_user_id)
        response = client.get(f"/profile{self.PARAMS}")
        assert response.status_code == 200

    def test_in_range_transactions_shown(self, client, seed_user_id):
        """Transactions whose date falls inside the range must appear in the page."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{self.PARAMS}").get_data(as_text=True)
        for desc in IN_RANGE:
            assert desc in body, f"Expected in-range description '{desc}' to be present"

    def test_out_of_range_transactions_absent(self, client, seed_user_id):
        """Transactions outside the range must NOT appear in the page."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{self.PARAMS}").get_data(as_text=True)
        for desc in OUT_OF_RANGE:
            assert desc not in body, (
                f"Out-of-range description '{desc}' must not appear in filtered view"
            )

    def test_filtered_total_is_range_only(self, client, seed_user_id):
        """Summary total must reflect only the filtered window, not all-time."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{self.PARAMS}").get_data(as_text=True)
        assert RANGE_TOTAL in body, f"Expected filtered total {RANGE_TOTAL}"
        assert ALL_TIME_TOTAL not in body, "All-time total must not appear when range is active"

    def test_filtered_transaction_count_via_helper(self, app, seed_user_id):
        """get_summary_stats must count only in-range rows."""
        stats = get_summary_stats(seed_user_id, start="2026-06-05", end="2026-06-10")
        assert stats["transaction_count"] == RANGE_COUNT, (
            f"Expected {RANGE_COUNT} transactions in range, got {stats['transaction_count']}"
        )

    def test_filtered_total_via_helper(self, app, seed_user_id):
        """get_summary_stats must sum only in-range amounts."""
        stats = get_summary_stats(seed_user_id, start="2026-06-05", end="2026-06-10")
        assert stats["total_spent"] == RANGE_TOTAL

    def test_filtered_top_category_via_helper(self, app, seed_user_id):
        """get_summary_stats top_category must reflect only the filtered window."""
        stats = get_summary_stats(seed_user_id, start="2026-06-05", end="2026-06-10")
        assert stats["top_category"] == RANGE_TOP

    def test_filtered_transactions_helper_returns_only_range(self, app, seed_user_id):
        """get_recent_transactions must return exactly the in-range rows."""
        txns = get_recent_transactions(seed_user_id, start="2026-06-05", end="2026-06-10")
        descriptions = {t["description"] for t in txns}
        assert descriptions == IN_RANGE, (
            f"Expected descriptions {IN_RANGE}, got {descriptions}"
        )

    def test_filtered_transactions_ordered_newest_first(self, app, seed_user_id):
        """In-range transactions must still be ordered newest-first."""
        txns = get_recent_transactions(seed_user_id, start="2026-06-05", end="2026-06-10")
        assert txns[0]["description"] == "T-shirts", (
            "Newest in-range transaction (Jun 10) must appear first"
        )
        assert txns[-1]["description"] == "Electricity bill", (
            "Oldest in-range transaction (Jun 05) must appear last"
        )

    def test_filtered_category_breakdown_helper(self, app, seed_user_id):
        """get_category_breakdown must reflect only the filtered window."""
        cats = get_category_breakdown(seed_user_id, start="2026-06-05", end="2026-06-10")
        cat_names = {c["name"] for c in cats}
        assert cat_names == {"Bills", "Health", "Entertainment", "Shopping"}, (
            "Category breakdown must include only categories present in the range"
        )
        # Categories present only outside the range must be absent
        assert all(c["name"] not in ("Food", "Transport", "Other") for c in cats), (
            "Categories outside the date range must not appear in the breakdown"
        )

    def test_active_range_caption_shown(self, client, seed_user_id):
        """A 'Showing <start> – <end>' caption must appear when a range is active."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{self.PARAMS}").get_data(as_text=True)
        assert "Showing" in body, "Active range caption must be visible when range is applied"
        assert "2026-06-05" in body, "Start date must appear in the active range caption"
        assert "2026-06-10" in body, "End date must appear in the active range caption"

    def test_filter_inputs_prepopulated(self, client, seed_user_id):
        """Form inputs must be pre-populated with the submitted start/end values."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{self.PARAMS}").get_data(as_text=True)
        assert 'value="2026-06-05"' in body, "start input must be pre-populated"
        assert 'value="2026-06-10"' in body, "end input must be pre-populated"

    def test_clear_link_present(self, client, seed_user_id):
        """A 'Clear' control linking back to unfiltered /profile must be present."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{self.PARAMS}").get_data(as_text=True)
        # The clear link must point to /profile with no query params
        assert "Clear" in body, "Clear link must be present when a range is active"
        assert 'href="/profile"' in body, "Clear link must href to /profile (no params)"

    def test_range_category_breakdown_pct_sums_to_100(self, app, seed_user_id):
        """Percentage values in the filtered breakdown must still sum to 100."""
        cats = get_category_breakdown(seed_user_id, start="2026-06-05", end="2026-06-10")
        assert sum(c["pct"] for c in cats) == 100, (
            "Category pct values must sum to 100 for a filtered range"
        )

    def test_boundary_dates_are_inclusive(self, app, seed_user_id):
        """Both start and end boundary dates must be included in results."""
        # Jun 05 (Electricity bill) and Jun 10 (T-shirts) are boundary dates
        txns = get_recent_transactions(seed_user_id, start="2026-06-05", end="2026-06-10")
        descriptions = {t["description"] for t in txns}
        assert "Electricity bill" in descriptions, "start boundary date must be inclusive"
        assert "T-shirts" in descriptions, "end boundary date must be inclusive"


# ===========================================================================
# ONE-SIDED RANGES
# ===========================================================================

class TestOneSidedRanges:
    def test_start_only_route_returns_200(self, client, seed_user_id):
        """GET /profile?start=2026-06-10 (no end) must return 200."""
        _login_seed(client, seed_user_id)
        response = client.get("/profile?start=2026-06-10")
        assert response.status_code == 200

    def test_start_only_excludes_earlier_transactions(self, client, seed_user_id):
        """With only start=2026-06-10, expenses before Jun 10 must not appear."""
        _login_seed(client, seed_user_id)
        body = client.get("/profile?start=2026-06-10").get_data(as_text=True)
        # Before Jun 10: Coffee and bagel, Uber, Electricity bill, Pharmacy, Movie night
        for desc in ("Coffee and bagel", "Uber to airport", "Electricity bill",
                     "Pharmacy", "Movie night"):
            assert desc not in body, (
                f"Description '{desc}' is before start date and must be excluded"
            )

    def test_start_only_includes_on_and_after_start(self, client, seed_user_id):
        """With only start=2026-06-10, expenses on/after Jun 10 must appear."""
        _login_seed(client, seed_user_id)
        body = client.get("/profile?start=2026-06-10").get_data(as_text=True)
        for desc in ("T-shirts", "Stamps", "Lunch with team"):
            assert desc in body, (
                f"Description '{desc}' is on/after start date and must be included"
            )

    def test_start_only_helper_stats(self, app, seed_user_id):
        """get_summary_stats with only start must count rows from that date forward."""
        stats = get_summary_stats(seed_user_id, start="2026-06-10", end=None)
        # Jun 10 (₹85.75) + Jun 12 (₹15.00) + Jun 13 (₹22.40) = ₹123.15, 3 rows
        assert stats["transaction_count"] == 3
        assert stats["total_spent"] == "₹123.15"

    def test_end_only_route_returns_200(self, client, seed_user_id):
        """GET /profile?end=2026-06-04 (no start) must return 200."""
        _login_seed(client, seed_user_id)
        response = client.get("/profile?end=2026-06-04")
        assert response.status_code == 200

    def test_end_only_excludes_later_transactions(self, client, seed_user_id):
        """With only end=2026-06-04, expenses after Jun 04 must not appear."""
        _login_seed(client, seed_user_id)
        body = client.get("/profile?end=2026-06-04").get_data(as_text=True)
        for desc in ("Electricity bill", "Pharmacy", "Movie night", "T-shirts",
                     "Stamps", "Lunch with team"):
            assert desc not in body, (
                f"Description '{desc}' is after end date and must be excluded"
            )

    def test_end_only_includes_on_and_before_end(self, client, seed_user_id):
        """With only end=2026-06-04, expenses on/before Jun 04 must appear."""
        _login_seed(client, seed_user_id)
        body = client.get("/profile?end=2026-06-04").get_data(as_text=True)
        for desc in ("Coffee and bagel", "Uber to airport"):
            assert desc in body, (
                f"Description '{desc}' is on/before end date and must be included"
            )

    def test_end_only_helper_stats(self, app, seed_user_id):
        """get_summary_stats with only end must count rows up to that date."""
        stats = get_summary_stats(seed_user_id, start=None, end="2026-06-04")
        # Jun 02 (₹12.50) + Jun 04 (₹45.00) = ₹57.50, 2 rows
        assert stats["transaction_count"] == 2
        assert stats["total_spent"] == "₹57.50"


# ===========================================================================
# INVERTED RANGE (start > end)
# ===========================================================================

class TestInvertedRange:
    PARAMS = "?start=2026-06-30&end=2026-06-01"

    def test_inverted_range_does_not_500(self, client, seed_user_id):
        """start > end must not cause a 500 — page must render."""
        _login_seed(client, seed_user_id)
        response = client.get(f"/profile{self.PARAMS}")
        assert response.status_code == 200, (
            "Inverted range (start > end) must render the page, not 500"
        )

    def test_inverted_range_shows_no_transactions(self, client, seed_user_id):
        """When start > end no transactions should be present in the response."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{self.PARAMS}").get_data(as_text=True)
        for desc in IN_RANGE | OUT_OF_RANGE:
            assert desc not in body, (
                f"Transaction '{desc}' must not appear when start > end"
            )

    def test_inverted_range_shows_warning(self, client, seed_user_id):
        """A warning/notice must be shown when the range is logically inverted."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{self.PARAMS}").get_data(as_text=True)
        # The spec says "shows a warning note" — look for common warning phrases
        warning_present = any(
            phrase in body
            for phrase in ("warning", "Warning", "invalid", "Invalid",
                           "start must be", "before", "no results",
                           "invalid range", "Invalid range")
        )
        assert warning_present, (
            "Page must display a warning when start date is after end date"
        )

    def test_inverted_range_zero_count_via_helper(self, app, seed_user_id):
        """get_summary_stats for an impossible range must return zero transactions."""
        stats = get_summary_stats(seed_user_id, start="2026-06-30", end="2026-06-01")
        assert stats["transaction_count"] == 0
        assert stats["total_spent"] == "₹0.00"

    def test_inverted_range_empty_transactions_via_helper(self, app, seed_user_id):
        """get_recent_transactions for an impossible range must return empty list."""
        txns = get_recent_transactions(seed_user_id, start="2026-06-30", end="2026-06-01")
        assert txns == [], "Impossible range must produce empty transaction list"

    def test_inverted_range_empty_breakdown_via_helper(self, app, seed_user_id):
        """get_category_breakdown for an impossible range must return empty list."""
        cats = get_category_breakdown(seed_user_id, start="2026-06-30", end="2026-06-01")
        assert cats == [], "Impossible range must produce empty category breakdown"


# ===========================================================================
# MALFORMED / INVALID DATE PARAMS
# ===========================================================================

class TestMalformedDates:
    @pytest.mark.parametrize("params,label", [
        ("?start=banana", "alphabetic string for start"),
        ("?end=banana", "alphabetic string for end"),
        ("?start=banana&end=2026-06-10", "alphabetic start with valid end"),
        ("?start=2026-06-05&end=banana", "valid start with alphabetic end"),
        ("?start=2026-13-40", "out-of-range month/day for start"),
        ("?start=2026-13-40&end=2026-06-10", "out-of-range month with valid end"),
        ("?start=notadate&end=alsonotadate", "both params alphabetic"),
        ("?start=&end=", "both params empty string"),
    ])
    def test_malformed_date_does_not_500(self, client, seed_user_id, params, label):
        """Any malformed date param must not cause a 500 — page must render."""
        _login_seed(client, seed_user_id)
        response = client.get(f"/profile{params}")
        assert response.status_code == 200, (
            f"Malformed date ({label}) must render 200, not 500"
        )

    @pytest.mark.parametrize("params,label", [
        ("?start=banana", "alphabetic string for start"),
        ("?start=2026-13-40", "out-of-range month/day"),
        ("?start=notadate&end=alsonotadate", "both params invalid"),
        ("?start=&end=", "both params empty"),
    ])
    def test_malformed_date_falls_back_to_all_time(self, client, seed_user_id, params, label):
        """Invalid dates must fall back to the all-time view (all 8 transactions shown)."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{params}").get_data(as_text=True)
        assert ALL_TIME_TOTAL in body, (
            f"Malformed date ({label}) must fall back to all-time total {ALL_TIME_TOTAL}"
        )
        # All seed descriptions must appear in the fallback all-time view
        for desc in IN_RANGE | OUT_OF_RANGE:
            assert desc in body, (
                f"Malformed date ({label}): expected all-time description '{desc}'"
            )


# ===========================================================================
# NON-ZERO-PADDED DATES
# ===========================================================================

class TestNonPaddedDates:
    def test_non_padded_dates_do_not_500(self, client, seed_user_id):
        """Non-zero-padded dates (?start=2026-6-5&end=2026-6-10) must not 500."""
        _login_seed(client, seed_user_id)
        response = client.get("/profile?start=2026-6-5&end=2026-6-10")
        assert response.status_code == 200

    def test_non_padded_dates_normalized_and_correct_results(self, client, seed_user_id):
        """Non-padded 2026-6-5 to 2026-6-10 must normalize and return the same
        in-range results as the zero-padded 2026-06-05 to 2026-06-10 query."""
        _login_seed(client, seed_user_id)
        body = client.get("/profile?start=2026-6-5&end=2026-6-10").get_data(as_text=True)
        for desc in IN_RANGE:
            assert desc in body, (
                f"Non-padded range must include in-range description '{desc}'"
            )
        for desc in OUT_OF_RANGE:
            assert desc not in body, (
                f"Non-padded range must exclude out-of-range description '{desc}'"
            )

    def test_non_padded_total_matches_padded(self, client, seed_user_id):
        """Non-padded and padded ranges for the same window must produce the same total."""
        _login_seed(client, seed_user_id)
        body_padded = client.get(
            "/profile?start=2026-06-05&end=2026-06-10"
        ).get_data(as_text=True)
        body_nonpadded = client.get(
            "/profile?start=2026-6-5&end=2026-6-10"
        ).get_data(as_text=True)
        assert RANGE_TOTAL in body_padded
        assert RANGE_TOTAL in body_nonpadded, (
            "Non-padded dates must normalize and produce the same total as padded dates"
        )

    def test_non_padded_inputs_show_normalized_values(self, client, seed_user_id):
        """After normalization the form inputs must reflect zero-padded YYYY-MM-DD."""
        _login_seed(client, seed_user_id)
        body = client.get("/profile?start=2026-6-5&end=2026-6-10").get_data(as_text=True)
        assert 'value="2026-06-05"' in body, (
            "Normalized start date must be zero-padded in the form input"
        )
        assert 'value="2026-06-10"' in body, (
            "Normalized end date must be zero-padded in the form input"
        )


# ===========================================================================
# EMPTY-STATE WITHIN A VALID RANGE
# ===========================================================================

class TestEmptyStateWithinRange:
    # Use a range that has no seed data (far future)
    NO_DATA_PARAMS = "?start=2030-01-01&end=2030-01-31"

    def test_empty_range_returns_200(self, client, seed_user_id):
        """A valid range with no matching data must still return 200."""
        _login_seed(client, seed_user_id)
        response = client.get(f"/profile{self.NO_DATA_PARAMS}")
        assert response.status_code == 200

    def test_empty_range_shows_no_transaction_descriptions(self, client, seed_user_id):
        """A valid range matching nothing must not show any seed descriptions."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{self.NO_DATA_PARAMS}").get_data(as_text=True)
        for desc in IN_RANGE | OUT_OF_RANGE:
            assert desc not in body, (
                f"No transactions should appear for a future range; found '{desc}'"
            )

    def test_empty_range_shows_empty_state_message(self, client, seed_user_id):
        """When a filter matches nothing the page must show an empty-state message."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{self.NO_DATA_PARAMS}").get_data(as_text=True)
        empty_indicators = (
            "No transactions",
            "no transactions",
            "No expenses",
            "no expenses",
            "Nothing here",
            "nothing here",
            "no results",
            "No results",
        )
        found = any(phrase in body for phrase in empty_indicators)
        assert found, (
            "An empty-state message must be shown when the active filter matches nothing"
        )

    def test_empty_range_zero_total_via_helper(self, app, seed_user_id):
        """get_summary_stats for an empty but valid range must return zero totals."""
        stats = get_summary_stats(seed_user_id, start="2030-01-01", end="2030-01-31")
        assert stats["transaction_count"] == 0
        assert stats["total_spent"] == "₹0.00"
        assert stats["top_category"] == "—"

    def test_empty_range_empty_transactions_via_helper(self, app, seed_user_id):
        """get_recent_transactions must return [] for a valid range with no data."""
        txns = get_recent_transactions(
            seed_user_id, start="2030-01-01", end="2030-01-31"
        )
        assert txns == []

    def test_empty_range_empty_breakdown_via_helper(self, app, seed_user_id):
        """get_category_breakdown must return [] for a valid range with no data."""
        cats = get_category_breakdown(
            seed_user_id, start="2030-01-01", end="2030-01-31"
        )
        assert cats == []

    def test_empty_range_range_active_caption_still_shown(self, client, seed_user_id):
        """Even when zero results, the 'Showing X – Y' caption must still appear
        (the range is valid; only the data window is empty)."""
        _login_seed(client, seed_user_id)
        body = client.get(f"/profile{self.NO_DATA_PARAMS}").get_data(as_text=True)
        assert "Showing" in body, (
            "Active-range caption must appear even when the filtered window is empty"
        )


# ===========================================================================
# USER DATA SCOPING (range filter must not leak across users)
# ===========================================================================

class TestUserDataScoping:
    def test_filtered_profile_does_not_show_other_user_data(
        self, client, seed_user_id, empty_user_id
    ):
        """A filtered profile for the empty user must never show the seed user's expenses."""
        with client.session_transaction() as sess:
            sess["user_id"] = empty_user_id
        body = client.get(
            "/profile?start=2026-06-05&end=2026-06-10"
        ).get_data(as_text=True)
        for desc in IN_RANGE | OUT_OF_RANGE:
            assert desc not in body, (
                f"Empty user's filtered profile must not show seed user's '{desc}'"
            )

    def test_helper_stats_scoped_to_user(self, app, seed_user_id, empty_user_id):
        """get_summary_stats must not cross user boundaries when a range is given."""
        seed_stats = get_summary_stats(
            seed_user_id, start="2026-06-05", end="2026-06-10"
        )
        empty_stats = get_summary_stats(
            empty_user_id, start="2026-06-05", end="2026-06-10"
        )
        assert seed_stats["transaction_count"] == RANGE_COUNT
        assert empty_stats["transaction_count"] == 0
        assert empty_stats["total_spent"] == "₹0.00"

    def test_helper_transactions_scoped_to_user(self, app, seed_user_id, empty_user_id):
        """get_recent_transactions must return only the requesting user's rows."""
        seed_txns = get_recent_transactions(
            seed_user_id, start="2026-06-05", end="2026-06-10"
        )
        empty_txns = get_recent_transactions(
            empty_user_id, start="2026-06-05", end="2026-06-10"
        )
        assert len(seed_txns) == RANGE_COUNT
        assert empty_txns == []
