# Spec: Delete Expense

## Overview

This feature lets a logged-in user permanently remove one of their own
expenses from the transaction list on the profile page. It completes the
final CRUD operation for expenses (after add in Step 07 and edit in Step 08),
giving users full control over their recorded spending. Deletion is triggered
by a per-row Delete control on the profile transaction table and is guarded so
a user can only ever delete expenses they own.

## Depends on

- **Step 01 — Database Setup** — `expenses` table and `get_db()` helper.
- **Step 05 — Profile Backend Routes** — `/profile` page and the transaction
  table that renders each expense row.
- **Step 07 — Add Expense** — established the logged-in expense route patterns.
- **Step 08 — Edit Expense** — established `get_expense_by_id(id, user_id)`
  ownership scoping and the per-row action link in `profile.html` that this
  feature sits beside.

## Routes

- `POST /expenses/<int:id>/delete` — deletes the expense with the given id if
  it belongs to the current user, flashes a confirmation, and redirects back to
  `/profile` — **logged-in only**.

> The existing stub in `app.py` is registered for `GET`. It will be changed to
> accept `POST` only. Deletion mutates state, so it must not be reachable via a
> plain link/GET (prevents accidental deletion via prefetch/crawlers and
> matches REST conventions). The Delete control on the profile page will be a
> small inline `<form method="POST">`, not an `<a>` link.

## Database changes

No schema changes. One new helper is required in `database/db.py`:

- `delete_expense(expense_id, user_id)` — runs a parameterized
  `DELETE FROM expenses WHERE id = ? AND user_id = ?`, commits, and returns
  `True` if exactly one row was deleted, else `False`. Scoping the `DELETE` to
  `user_id` enforces ownership at the query level (defence in depth alongside
  the route check).

## Templates

- **Create:** None.
- **Modify:** `templates/profile.html` — in the transaction table's
  `tx-actions` cell (currently just the Edit link), add a Delete control: an
  inline `<form method="POST" action="{{ url_for('delete_expense', id=t.id) }}">`
  containing a `<button>` styled as a danger action. The button carries a
  `data-confirm` attribute (or equivalent) so `main.js` can attach a
  confirmation prompt.

## Files to change

- `app.py` — replace the `delete_expense` stub with a real `POST`-only route:
  logged-in guard, `get_expense_by_id(id, user_id)` → `abort(404)` if missing,
  call `delete_expense(id, user_id)` → `abort(404)` if it returns falsy, flash
  `"Expense deleted."`, redirect to `profile`.
- `database/db.py` — add the `delete_expense(expense_id, user_id)` helper.
- `templates/profile.html` — add the per-row Delete form/button.
- `static/css/style.css` — add styling for the inline delete button using the
  existing `--danger` / `--danger-light` variables.
- `static/js/main.js` — add a confirmation handler so clicking Delete prompts
  the user before the form submits.

## Files to create

None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only.
- Parameterised queries only (`?` placeholders) — never f-strings in SQL.
- Passwords hashed with werkzeug — N/A here, but no auth changes that weaken this.
- Use CSS variables — never hardcode hex values; the delete button must use
  `--danger` / `--danger-light`.
- All templates extend `base.html` — `profile.html` already does; preserve it.
- DB logic stays in `database/db.py` — the route must call `delete_expense()`,
  never inline SQL.
- Route function has one responsibility — guard, delete, flash, redirect; no
  inline data shaping.
- Use `abort(404)` for missing/not-owned expenses — never a bare string return,
  and never leak whether the id exists for another user.
- The route accepts `POST` only — a `GET` to the delete URL must not delete.
- Mirror Step 08 conventions: ownership via `get_expense_by_id(id, user_id)`,
  past-tense flash message (`"Expense deleted."`), redirect to `profile`.
- Vanilla JS only for the confirmation prompt — no frameworks.
- App runs on port 5001.

## Definition of done

- [ ] Visiting `/profile` shows a Delete control next to Edit on every
      transaction row, styled in the danger color (not hardcoded hex).
- [ ] Clicking Delete prompts for confirmation; cancelling does nothing.
- [ ] Confirming Delete removes that expense and returns to `/profile` with a
      flash message `"Expense deleted."`; the row no longer appears and the
      profile stats reflect the removal.
- [ ] The deleted row is gone from the `expenses` table (verifiable via the DB).
- [ ] Submitting a `POST` to `/expenses/<id>/delete` for an expense owned by a
      different user returns `404` and does not delete that expense.
- [ ] Submitting a `POST` to `/expenses/<id>/delete` for a non-existent id
      returns `404`.
- [ ] A `GET` request to `/expenses/<id>/delete` does not delete the expense
      (405 / not allowed).
- [ ] Hitting the delete route while logged out flashes
      `"Please sign in to view that page."` and redirects to `/login`.
- [ ] `pytest` passes.
