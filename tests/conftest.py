# tests/conftest.py
import os
import tempfile

import pytest

# Use a temporary SQLite database for tests instead of Postgres
# Make sure this is set BEFORE importing app.py
db_fd, db_path = tempfile.mkstemp()
os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")

from app import app, db, User, BlackjackGame, Card, Deck, hand_value  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once for the test session, drop at the end."""
    with app.app_context():
        db.create_all()
    yield
    with app.app_context():
        db.drop_all()


@pytest.fixture
def test_app():
    """Provide a configured Flask app instance for tests."""
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


@pytest.fixture
def client(test_app):
    """Flask test client."""
    return test_app.test_client()


@pytest.fixture
def db_session():
    """Provide a clean DB session for each test (optionally clear data)."""
    with app.app_context():
        yield db.session
        # Clean up between tests if needed
        for tbl in reversed(db.metadata.sorted_tables):
            db.session.execute(tbl.delete())
        db.session.commit()
