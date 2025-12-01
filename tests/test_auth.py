# tests/test_auth.py
from app import User


def test_register_creates_user(client, db_session):
    response = client.post(
        "/register",
        data={"username": "testuser", "password": "secret123"},
        follow_redirects=True,
    )

    # Just assert page loaded and user exists
    assert response.status_code == 200

    user = User.query.filter_by(username="testuser").first()
    assert user is not None


def test_register_rejects_existing_username(client, db_session):
    # First create a user
    user = User(username="existing", password_hash="hash")
    db_session.add(user)
    db_session.commit()

    # Try to register again with same username
    response = client.post(
        "/register",
        data={"username": "existing", "password": "whatever"},
        follow_redirects=True,
    )

    assert b"Username already exists." in response.data


def test_register_requires_username_and_password(client, db_session):
    response = client.post(
        "/register",
        data={"username": "", "password": ""},
        follow_redirects=True,
    )

    assert b"Username and password are required." in response.data


def test_login_success_sets_session_and_redirects(client, db_session):
    from werkzeug.security import generate_password_hash

    # Create user in DB
    password_hash = generate_password_hash("secret123")
    user = User(username="loginuser", password_hash=password_hash)
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/login",
        data={"username": "loginuser", "password": "secret123"},
        follow_redirects=False,
    )

    # Should redirect to index
    assert response.status_code == 302
    assert "/?" in response.location or response.location.endswith("/")

    # Check session via follow_redirects
    response = client.post(
        "/login",
        data={"username": "loginuser", "password": "secret123"},
        follow_redirects=True,
    )
    assert b"Logged in successfully." in response.data


def test_login_failure_shows_error(client, db_session):
    response = client.post(
        "/login",
        data={"username": "nouser", "password": "wrongpass"},
        follow_redirects=True,
    )

    assert b"Invalid username or password." in response.data


def test_login_required_redirects_to_login(client):
    # Not logged in: hitting "/" should redirect to /login
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.location
