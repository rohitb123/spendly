# Spec: Edit Expense

## Overview

Edit Expense lets a logged-in user correct a previously recorded expense — its
amount, category, date, or description — instead of having to delete and
re-add it. It promotes the existing `GET /expenses/<id>/edit` stub into a fully
implemented `GET`/`POST` route backed by a pre-filled form that mirrors the
add-expense experience. This is the natural follow-up to Step 7 (Add Expense):
once users can create expenses, they need to fix mistakes, which makes the
profile transaction list genuinely editable and sets up Step 9 (Delete).

## Depends on

- **Step 01 — Database Setup** — `expenses` table, `get_db()`.
- **Step 05 — Profile Backend Routes** — `database/queries.py`, `get_recent_transactions()` (the list users edit from).
- **Step 07 — Add Expense** — `create_expense()`, the `CATEGORIES` / `MAX_AMOUNT` / `MAX_DESCRIPTION_LEN` constants, the `_parse_date_param()` helper, and `add_expense.html` (the template this feature mirrors).

## Routes

- `GET /expenses/<int:id>/edit` — render the edit form pre-filled with the expense's current values — **logged-in only** (replaces the current stub).
- `POST /expenses/<int:id>/edit` — validate the submitted values and persist the update, then redirect to profile — **logged-in only**.

Both methods are served by the single `edit_expense(id)` route, replacing the
existing one-line stub. No other routes are added.

## Database changes

No schema changes — the `expenses` table already has every column needed
(`id`, `user_id`, `amount`, `category`, `date`, `description`).

Two new helper functions are required (added to `database/db.py`, never inline
in the route):

- `get_expense_by_id(expense_id, user_id)` — `SELECT` a single expense scoped to **both** `id` and `user_id`; returns a `Row` or `None`. Scoping by `user_id` is what enforces ownership.
- `update_expense(expense_id, user_id, amount, category, expense_date, description)` — parameterised `UPDATE ... WHERE id = ? AND user_id = ?`; the `user_id` clause prevents one user from editing another's expense even if validation is bypassed.

One existing query helper must be extended:

- `get_recent_transactions(user_id, limit, start, end)` in `database/queries.py` — add the expense `id` to each returned dict so `profile.html` can build `url_for('edit_expense', id=...)` links. (Currently it returns only `{date, description, category, amount}`.)

## Templates

- **Create:**
  - `templates/edit_expense.html` — mirrors `add_expense.html`: same fields (amount, category, date, description), same error block, but titled "Edit expense", the submit button reads "Update expense", and the form `action` posts to `url_for('edit_expense', id=expense_id)`. Fields are pre-filled from the existing expense on GET and from submitted values on a validation re-render.

- **Modify:**
  - `templates/profile.html` — add an "Edit" link per transaction row pointing at `url_for('edit_expense', id=t.id)`. Remove "Editing ... coming in later steps" from the coming-soon copy if it now misstates reality.

## Files to change

- `app.py` — replace the `edit_expense` stub with a `GET`/`POST` handler.
- `database/db.py` — add `get_expense_by_id()` and `update_expense()`.
- `database/queries.py` — include `id` in `get_recent_transactions()` rows.
- `templates/profile.html` — add per-row Edit link.

## Files to create

- `templates/edit_expense.html` — the edit form.
- `static/css/edit-expense.css` — optional; reuse `add-expense.css` if styles are identical rather than duplicating. Only create if edit-specific styling is genuinely needed.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` via `get_db()` only.
- Parameterised queries only — `?` placeholders, never f-strings in SQL.
- Passwords hashed with werkzeug (no password handling in this feature, but the project rule stands).
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- Reuse the existing auth guard verbatim: if `session.get("user_id") is None`, flash `"Please sign in to view that page."` and redirect to `login`.
- **Ownership enforcement:** load the expense with `get_expense_by_id(id, session["user_id"])`. If it returns `None` (missing OR owned by another user), `abort(404)` — do not leak whether the id exists. Use `abort()` for HTTP errors, never a bare string return.
- Validation must match Add Expense exactly: positive `amount` ≤ `MAX_AMOUNT`, `category` in `CATEGORIES`, date parses via `_parse_date_param()`, description ≤ `MAX_DESCRIPTION_LEN`. On error, re-render `edit_expense.html` with the error message and the user's submitted values preserved.
- On success, flash `"Expense updated."` (past tense, matching `"Expense added."`) and redirect to `profile`.
- All internal links/actions use `url_for()` — never hardcode URLs.
- DB logic stays in `database/db.py` / `database/queries.py`; the route only fetches, validates, and renders.

## Definition of done

- Visiting `/expenses/<id>/edit` while logged out flashes the sign-in message and redirects to `/login`.
- Visiting `/expenses/<id>/edit` for one of your own expenses shows the form pre-filled with that expense's current amount, category, date, and description.
- Visiting `/expenses/<id>/edit` for a non-existent id, or an id belonging to another user, returns HTTP 404 (and does not reveal whether the id exists).
- Submitting valid changes updates the row in the database, flashes "Expense updated.", and redirects to `/profile` where the new values are visible.
- Submitting an invalid amount / category / date / over-long description re-renders the edit form with a clear error and keeps the values just entered.
- The profile transaction list shows a working "Edit" link on each row that lands on the correct expense's edit form.
- `pytest` passes, including tests covering the logged-out redirect, the ownership 404, a successful update, and at least one validation failure.
