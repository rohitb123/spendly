"""Pytest fixtures backed by an isolated temp SQLite database.

The real ``spendly.db`` in the project root is never touched. Each test gets
a fresh temp file populated by ``init_db`` + ``seed_db``. We rely on the fact
that ``get_db()`` reads ``DB_PATH`` from the live ``database.db`` module on
every call, so a single ``monkeypatch.setattr`` flips every later lookup.
"""

import os
import tempfile

import pytest


@pytest.fixture
def app(monkeypatch):
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    import database.db as db_module
    monkeypatch.setattr(db_module, "DB_PATH", db_path)

    db_module.init_db()
    db_module.seed_db()

    import app as app_module
    app_module.app.config["TESTING"] = True
    app_module.app.config["SECRET_KEY"] = "test-secret"

    yield app_module.app

    os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed_user_id(app):
    from database.db import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    conn.close()
    return row["id"]


@pytest.fixture
def empty_user_id(app):
    from database.db import create_user
    return create_user("Empty User", "empty@spendly.com", "password123")
