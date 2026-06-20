# Spec: Add Expense

## Overview

This feature lets a logged-in user record a new expense through a
dedicated form at `/expenses/add`. It is the first expense-creation
feature in the Spendly roadmap and the foundation for the edit (Step 08)
and delete (Step 09) steps that follow. A `GET` request renders an
expense form; a `POST` request validates the submitted values, persists
a new row to the `expenses` table via a DB helper, flashes a
confirmation, and redirects the user to their profile where the new
expense appears in the transaction history. This turns Spendly from a
read-only viewer of seeded data into an app where users own and grow
their own expense records.

## Depends on

- **Step 01 — Database setup** (`expenses` table and `get_db()` must exist)
- **Step 03 — Login and logout** (session-based auth guard, `current_user`)
- **Step 05 — Profile backend routes** (redirect target showing the new expense)

## Routes

- `GET /expenses/add` — render the add-expense form — **logged-in only**
- `POST /expenses/add` — validate input, create the expense, redirect to `/profile` — **logged-in only**

Both behaviours live on the existing `add_expense` route in `app.py`
(currently a stub), upgraded to accept `methods=["GET", "POST"]`.
Unauthenticated requests flash an error and redirect to `/login`,
matching the existing `/profile` guard pattern.

## Database changes

No schema changes. The `expenses` table already exists with all required
columns (`id`, `user_id`, `amount`, `category`, `date`, `description`,
`created_at`). This step adds **one new mutation helper** to
`database/db.py`:

- `create_expense(user_id, amount, category, date, description)` —
  parameterised `INSERT` into `expenses`, returns the new row id
  (`lastrowid`). `description` may be empty/None.

## Templates

- **Create:**
  - `templates/add_expense.html` — extends `base.html`; renders the
    expense form with fields for amount, category (dropdown of the 7
    fixed categories), date (date input, defaults to today), and an
    optional description. Re-renders with an inline error message and
    preserves submitted values when validation fails.

- **Modify:**
  - None required. (The profile page already lists transactions and the
    navbar already exists. Optionally an "Add expense" link may be added
    to the profile/nav, but it is not required by this step's Definition
    of Done.)

## Files to change

- `app.py` — replace the `GET /expenses/add` stub with a combined
  `GET`/`POST` handler that guards auth, validates input, calls
  `create_expense()`, flashes, and redirects.
- `database/db.py` — add the `create_expense()` helper.

## Files to create

- `templates/add_expense.html` — the expense form page.
- `static/css/add-expense.css` — page-specific styles for the form
  (linked via the `head` block).

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — use `sqlite3` via `get_db()` only.
- Parameterised queries only (`?` placeholders) — never f-strings in SQL.
- All DB logic lives in `database/db.py` — no inline SQL in the route.
- Passwords (unrelated here) remain hashed with werkzeug — no change.
- Use CSS variables in `add-expense.css` — never hardcode hex values.
- All templates extend `base.html` and use `url_for()` for every link
  and the form `action`.
- Auth guard must mirror the existing `/profile` pattern: check
  `session.get("user_id")`, flash `"error"`, redirect to `login`.
- Validate on the server: `amount` must parse to a positive number;
  `category` must be one of the 7 fixed categories
  (Food, Transport, Bills, Health, Entertainment, Shopping, Other);
  `date` must validate via `_parse_date_param()` (YYYY-MM-DD);
  `description` is optional.
- On validation failure, re-render `add_expense.html` with an error
  message and the user's submitted values preserved (do not silently
  drop input). Use `abort()` only for genuine HTTP errors.
- The route must scope the insert to the logged-in `session["user_id"]`
  — never trust a user_id from the form.

## Definition of done

- Visiting `/expenses/add` while logged out flashes an error and
  redirects to `/login`.
- Visiting `/expenses/add` while logged in renders a form with: an
  amount field, a category dropdown listing all 7 fixed categories, a
  date field defaulting to today, and an optional description field.
- Submitting a valid expense inserts exactly one row into `expenses`
  scoped to the current user, flashes a success message, and redirects
  to `/profile`.
- The newly added expense is visible in the profile's recent
  transactions table and reflected in the summary stats / category
  breakdown.
- Submitting an invalid amount (empty, zero, negative, non-numeric),
  an invalid/missing category, or a malformed date re-renders the form
  with an error message and preserves the other entered values — no row
  is inserted.
- The SQL insert uses parameterised placeholders (verified by reading
  `database/db.py`).
- `add-expense.css` uses CSS variables and the template extends
  `base.html` with all links via `url_for()`.
