# Spec: Date Filter for Profile Page

## Overview

This feature lets a logged-in user narrow their profile view to a chosen
date range. A small filter form (start date + end date) is added to the
profile page; submitting it reloads `/profile` with the range as query
parameters. The summary stats, transaction history, and category breakdown
all recompute for the selected window, so the whole page reflects one
coherent period instead of always showing all-time data. This is the first
step that introduces user-driven querying on top of the live data wired up
in Step 05, and it sets the pattern (GET query params → parameterised range
queries) that later reporting features can reuse.

## Depends on

- **Step 01 — Database setup** (`expenses` table with a `date` column stored
  as `TEXT` in `YYYY-MM-DD` format).
- **Step 04 — Profile page design** (`templates/profile.html` and the four
  page sections).
- **Step 05 — Profile backend routes** (the `/profile` route and the
  `database/queries.py` helpers: `get_user_profile`, `get_summary_stats`,
  `get_recent_transactions`, `get_category_breakdown`).

## Routes

No new routes.

- `GET /profile` — **modified.** Now accepts two optional query parameters,
  `start` and `end` (each `YYYY-MM-DD`). When present and valid, the route
  passes the range down to the query helpers so stats, transactions, and
  categories are scoped to it. When absent or invalid, behaviour is
  unchanged (all-time view). Access level: logged-in only (existing auth
  guard is preserved).

## Database changes

No schema changes — the existing `expenses.date` column (`TEXT`,
`YYYY-MM-DD`) is sufficient.

The existing read helpers in `database/queries.py` are extended to accept an
optional date range:

- `get_summary_stats(user_id, start=None, end=None)`
- `get_recent_transactions(user_id, limit=10, start=None, end=None)`
- `get_category_breakdown(user_id, start=None, end=None)`

When `start`/`end` are provided, each helper adds a parameterised
`AND date >= ?` / `AND date <= ?` clause (placeholders only — never
f-strings in SQL). When both are `None`, the SQL is identical to today's
behaviour. When a date range is active, `get_recent_transactions` should
return all matching rows in the window rather than capping at `limit`
(the cap exists only for the default all-time view).

## Templates

- **Create:** none.
- **Modify:** `templates/profile.html` — add a date-filter `<form
  method="get" action="{{ url_for('profile') }}">` inside the "Recent
  transactions" card header (`<header class="profile-card-header">`). It
  contains two `<input type="date">` fields (`name="start"`, `name="end"`),
  a submit button, and a "Clear" link back to `url_for('profile')`. The
  inputs are pre-populated from the active range (`value="{{ start }}"` /
  `value="{{ end }}"`) so the selection persists after submit. Add a short
  "Showing <start> – <end>" caption when a range is active. Keep using
  `url_for()` for every link.

## Files to change

- `app.py` — read `request.args.get("start")` / `request.args.get("end")`
  in the `profile()` view, validate them, pass them to the three query
  helpers, and pass `start`/`end` back into `render_template` for the form.
- `database/queries.py` — extend `get_summary_stats`,
  `get_recent_transactions`, and `get_category_breakdown` with the optional
  `start`/`end` range parameters and the parameterised WHERE clauses.
- `templates/profile.html` — add the filter form, persisted input values,
  and the active-range caption.
- `static/css/style.css` — add styles for the filter form
  (`.tx-filter` and friends) using existing CSS variables.

## Files to create

No new files.

## New dependencies

No new dependencies. Date parsing/validation uses the standard-library
`datetime` module already imported in `database/queries.py`; `request` is
already available from Flask in `app.py`.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only.
- Parameterised queries only — `?` placeholders for the date bounds; never
  interpolate query-param values into SQL strings.
- Passwords hashed with werkzeug (unchanged — no auth code is touched here).
- DB logic stays in `database/queries.py`, not inline in the route
  (matches the Step 05 convention; the route only reads params, validates,
  and renders).
- Validate `start`/`end` against `YYYY-MM-DD` (e.g. `datetime.strptime`).
  Treat malformed or empty values as "not provided" and fall back to the
  all-time view rather than `abort()`-ing — a bad date in a URL should not
  500.
- Use `abort()` for genuine HTTP errors only; the existing
  not-logged-in redirect to `/login` is preserved exactly.
- Use CSS variables — never hardcode hex values in the new styles.
- All templates extend `base.html`; use `url_for()` for the form action
  and the Clear link.
- Preserve existing behaviour when no range is supplied: identical output
  to the current profile page.

## Definition of done

- Visiting `/profile` while logged out still redirects to `/login`.
- Visiting `/profile` with no query params shows the same all-time stats,
  transactions, and category breakdown as before this change.
- Visiting `/profile?start=2026-06-05&end=2026-06-10` shows only
  transactions whose `date` is within that inclusive range, and the summary
  stats and category breakdown reflect only that range.
- The date inputs remain populated with the submitted `start`/`end` after
  the page reloads, and an "active range" caption is shown.
- A "Clear" control returns the page to the unfiltered all-time view.
- Supplying a malformed date (e.g. `?start=banana`) does not error — the
  page renders the all-time view.
- No raw SQL string interpolation of the date values (verified by reading
  `database/queries.py`).
- App still runs on port 5001 and `pytest` passes.
