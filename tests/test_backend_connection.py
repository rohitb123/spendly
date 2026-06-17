"""Tests for Step 5 — backend wiring of /profile.

Each data concern owns one section below. Subagents append their tests to
their assigned section; the integrator adds the route tests at the bottom.
"""

from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_profile,
)


# --- SECTION A: SUMMARY STATS + USER PROFILE TESTS ---
# owner: subagent 2


# --- SECTION B: TRANSACTION HISTORY TESTS ---
# owner: subagent 1


# --- SECTION C: CATEGORY BREAKDOWN TESTS ---
# owner: subagent 3


# --- ROUTE INTEGRATION TESTS ---
# owner: integrator (main worktree)
