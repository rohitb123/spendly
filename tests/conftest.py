"""Pytest fixtures backed by an isolated temp SQLite database.

The real ``spendly.db`` in the project root is never touched. Each test session
gets a fresh temp file populated by the existing ``init_db`` / ``seed_db``
helpers, so tests see the same demo user and 8 seeded expenses as production.
"""

import importlib
import os
import sys
import tempfile

import pytest


@pytest.fixture
def app(monkeypatch):
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Repoint the DB path BEFORE importing app so init_db/seed_db write there.
    sys.modules.pop("database.db", None)
    sys.modules.pop("database.queries", None)
    sys.modules.pop("app", None)

    import database.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", db_path)

    import app as app_module
    importlib.reload(app_module)
    monkeypatch.setattr(app_module, "app", app_module.app)
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"

    # Tables already created by app import's init_db()/seed_db() call.
    yield app_module.app

    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_user_id(app):
    """Return the id of the seeded demo user (always 1 in a fresh DB)."""
    from database.db import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    conn.close()
    return row["id"]


@pytest.fixture
def empty_user_id(app):
    """Create a fresh user with zero expenses and return their id."""
    from database.db import create_user
    return create_user("Empty User", "empty@spendly.com", "password123")
