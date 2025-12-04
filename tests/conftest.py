# tests/conftest.py

import os
import tempfile
import pytest

# -----------------------------------------------
# BEFORE importing app.py, override the DB
# -----------------------------------------------
#
# We create a temporary SQLite file for ALL tests.
# This ensures tests never touch your real blackjack.db.
#

db_fd, db_path = tempfile.mkstemp()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")
os.environ.setdefault("DB_DIR", os.path.dirname(db_path))  # ensures consistency

from app import app, db  # noqa: E402


# ---------------------------------------------------------
# GLOBAL TEST DATABASE SETUP (once per test session)
# ---------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Create all DB tables once for the entire test session.
    Drop them once the entire session is done.
    """
    with app.app_context():
        db.create_all()
    yield
    with app.app_context():
        db.drop_all()


# ---------------------------------------------------------
# APP FIXTURE (shared by both unit & integration tests)
# ---------------------------------------------------------
@pytest.fixture
def test_app():
    """
    Provide a configured Flask app for tests.
    Ensures the app runs in TESTING mode and CSRF is disabled.
    """
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )
    return app


# ---------------------------------------------------------
# CLIENT FIXTURE (shared across all tests)
# ---------------------------------------------------------
@pytest.fixture
def client(test_app):
    """
    Provides a Flask test client for sending requests.
    Works for both unit and integration tests.
    """
    return test_app.test_client()


# ---------------------------------------------------------
# CLEAN DB SESSION FIXTURE (per test)
# ---------------------------------------------------------
@pytest.fixture
def db_session():
    """
    Provides a clean database session per test.
    Ensures no data leaks between tests.
    Used by both unit tests & integration tests.
    """
    with app.app_context():
        yield db.session

        # Clean all tables between tests
        for tbl in reversed(db.metadata.sorted_tables):
            db.session.execute(tbl.delete())
        db.session.commit()


# ---------------------------------------------------------
# OPTIONAL: Utility Fixtures (shared helpers)
# ---------------------------------------------------------
@pytest.fixture
def create_user(db_session):
    """
    Helper fixture to create a user quickly.
    Used by many integration tests.
    """

    from werkzeug.security import generate_password_hash
    from app import User

    def _create(username="testuser", password="testpass"):
        user = User(
            username=username,
            password_hash=generate_password_hash(password)
        )
        db_session.add(user)
        db_session.commit()
        return user

    return _create


@pytest.fixture
def login_user(client):
    """
    Helper fixture to log users in via POST /login.
    """

    def _login(username, password):
        return client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    return _login
