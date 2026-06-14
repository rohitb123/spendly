# Spec: Login and Logout

## Overview

This step turns the existing static login page into a working
authentication flow and wires up logout. After Step 3, a registered
user can sign in with their email and password, receive a server-side
session cookie, see the navbar update to reflect their signed-in
state, and log out cleanly. This is the gating step before any
logged-in-only feature (profile, expenses) can be built.

## Depends on

- **Step 1 — Database setup:** `users` table, `get_db()`, and
  `PRAGMA foreign_keys = ON` must already exist in `database/db.py`.
- **Step 2 — Registration:** `create_user()` and `get_user_by_email()`
  helpers, werkzeug password hashing, `app.secret_key`, and the
  flash-message block in `base.html` must all be in place.

## Routes

- `GET /login` — already implemented; will be updated to redirect to
  `landing` if a user is already signed in — public
- `POST /login` — accept email + password, verify against the
  `users` table, set `session["user_id"]` on success, flash an error
  on failure — public
- `GET /logout` — clear `session["user_id"]`, flash a confirmation
  message, redirect to landing — logged-in (silently redirects to
  landing if no session)

## Database changes

No schema changes. One new read helper is added in `database/db.py`:

- `get_user_by_id(user_id)` — returns the user row (or `None`),
  used by the navbar / future steps to look up the signed-in user
  from `session["user_id"]`.

## Templates

- **Create:** none
- **Modify:**
  - `templates/base.html` — make the navbar conditional. When a user
    is signed in, show their name and a logout link; otherwise show
    the existing "Sign in" + "Get started" links. Use a Jinja
    context value (e.g. `current_user`) populated by a Flask
    `context_processor` in `app.py`.
  - `templates/login.html` — change the hardcoded `action="/login"`
    to `action="{{ url_for('login') }}"`. No other markup changes;
    existing `.form-input`, `.btn-submit`, `.auth-error`, and
    `.flash-*` styles cover the rest.

## Files to change

- `app.py` — replace the stub `login()` with a `methods=["GET", "POST"]`
  handler; replace the stub `logout()` plain-text return with a real
  session-clearing redirect; add a `@app.context_processor` that
  injects `current_user` into every template.
- `database/db.py` — add `get_user_by_id(user_id)` using a
  parameterised query.
- `templates/base.html` — conditional navbar (see Templates above).
- `templates/login.html` — fix the form action to use `url_for()`.

## Files to create

- `.claude/specs/03-login-and-logout.md` — this spec.

## New dependencies

No new dependencies. `werkzeug.security.check_password_hash` is the
counterpart to the already-used `generate_password_hash` and ships
with the existing `werkzeug==3.1.6`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never f-string SQL
- Passwords verified with `werkzeug.security.check_password_hash`;
  never compare hashes by string equality
- All DB logic lives in `database/db.py`, never inline in routes
- Use CSS variables — never hardcode hex values (existing form,
  button, and flash styles should be reused as-is)
- All templates extend `base.html`
- All internal links use `url_for()` — never hardcoded paths
- Generic error message on failed login ("Invalid email or
  password.") — do not reveal whether the email exists
- Trim and lowercase the submitted email before lookup to match
  the registration-step normalisation
- Use `session.pop("user_id", None)` on logout so it is idempotent
- Use `abort()` for true HTTP errors only; bad credentials are a
  user-flow failure and should re-render `login.html` with a flash
- Do not introduce a `@login_required` decorator yet — it is not
  needed until Step 4 (profile)

## Definition of done

Manual checks against the running app (`python app.py`, port 5001):

- [ ] Visiting `/login` while signed out renders the existing
      login form.
- [ ] Submitting valid credentials (e.g. the seeded
      `demo@spendly.com` / `demo123`) redirects to landing and the
      navbar now shows the user's name and a "Log out" link.
- [ ] Submitting a wrong password re-renders `/login` with a
      flashed error and the email field still populated (or at
      least clearly indicating the failure).
- [ ] Submitting an email that does not exist shows the same
      generic error — no email-enumeration leak.
- [ ] Visiting `/login` while already signed in redirects to
      landing instead of showing the form again.
- [ ] Clicking "Log out" clears the session, flashes a
      confirmation, and the navbar reverts to "Sign in" /
      "Get started".
- [ ] Hitting `/logout` while signed out redirects to landing
      without crashing.
- [ ] `get_user_by_id()` returns a `sqlite3.Row` for a valid id
      and `None` for an unknown id (verified via `pytest` or a
      one-off shell check).
- [ ] No template hardcodes `/login` or `/logout`; every link
      uses `url_for()`.
- [ ] `pytest` still passes.
