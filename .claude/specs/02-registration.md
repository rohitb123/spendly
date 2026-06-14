# Spec: Registration

## Overview

Wire up the account-creation flow. Step 01 left the `users` table in place and Step 01 also shipped a static `register.html` form that only renders on GET. This step adds the `POST /register` handler that validates the submitted form, hashes the password with `werkzeug`, inserts a new row into `users`, and shows a success message and redirects the user to `/login` on success. On any validation or uniqueness failure the form re-renders with a friendly error message. This is the first feature that actually mutates the database from a user action, so it sets the pattern (input handling, DB helper, error rendering) that login, profile, and the expense routes will all follow.

## Depends on

- Step 01 — Database setup (`users` table, `get_db()` helper, `werkzeug` available)

## Routes

- `POST /register` — accepts `name`, `email`, `password` from the form, validates them, creates the user, redirects to `/login` with a flash message — public
- `GET /register` — already implemented; will be updated to accept and render an `error` context variable

## Database changes

No database changes. The `users` table from Step 01 already has the required columns (`name`, `email`, `password_hash`, `created_at`) and the `UNIQUE` constraint on `email` is what enforces duplicate detection at the DB layer.

## Templates

- **Create:** none
- **Modify:**
  - `templates/register.html` — switch the form `action` to `url_for('register')` instead of the hardcoded `/register`, and render flashed messages if any. The existing `{% if error %}` block already covers inline errors and stays as-is.
  - `templates/login.html` — render flashed success message (so the "Account created — please sign in" message lands somewhere after redirect)
  - `templates/base.html` — add a single block above `{% block content %}` that renders flashed messages, so every page can show them without per-template duplication

## Files to change

- `app.py` — change `register()` to accept both `GET` and `POST`, add validation + insert logic, import `request`, `redirect`, `url_for`, `flash`, and configure `app.secret_key`
- `database/db.py` — add two helpers: `create_user(name, email, password)` (hashes password, inserts row, returns new user id) and `get_user_by_email(email)` (returns row or `None`) — keeps all SQL out of `app.py`
- `templates/register.html` — replace hardcoded action, render flashed messages
- `templates/login.html` — render flashed messages
- `templates/base.html` — add shared flash-message block

## Files to create

None.

## New dependencies

No new dependencies. `werkzeug.security.generate_password_hash` and `flask.flash` are already available.

## Rules for implementation

- No SQLAlchemy or ORMs — use the existing `sqlite3` connection from `get_db()`
- Parameterised queries only (`?` placeholders); never f-string SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` — never store plaintext
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values (no new CSS expected for this step, but applies if any is added)
- Use `url_for()` for every internal link in templates — no hardcoded paths
- Route function stays one-responsibility: parse form → call DB helper → render or redirect. All SQL lives in `database/db.py`
- Validation rules (server-side, all required):
  - `name` — non-empty after `.strip()`
  - `email` — non-empty, contains `@`, lowercased before insert
  - `password` — at least 8 characters
- Duplicate email is caught by catching `sqlite3.IntegrityError` from the `UNIQUE` constraint, not by a pre-flight `SELECT` — keeps the insert atomic
- On any validation error: re-render `register.html` with `error="..."` and the previously typed `name`/`email` preserved (do **not** preserve the password)
- On success: `flash("Account created — please sign in.")` then `redirect(url_for("login"))`
- `app.secret_key` must be set (read from env var `SPENDLY_SECRET_KEY` with a dev-only fallback) — required for `flash()` to work
- Do not implement login auth in this step — the `/login` POST is Step 03

## Definition of done

- [ ] `GET /register` still renders the form unchanged
- [ ] Submitting valid name + email + 8-char password creates a row in `users` with a hashed `password_hash`
- [ ] After successful registration the browser lands on `/login` and shows the success flash
- [ ] Submitting with an empty name, malformed email, or short password re-renders the form with a visible error and preserves name/email but blanks the password
- [ ] Submitting a duplicate email re-renders the form with an "Email already registered" error — no second row is inserted
- [ ] Password column in the DB contains a hash (starts with `pbkdf2:` or `scrypt:`), never the plaintext
- [ ] Inspecting `app.py` shows no inline SQL — all DB access goes through `database/db.py` helpers
- [ ] `pytest` passes (existing tests, if any, still green)
- [ ] App still starts on port 5001 with no errors
