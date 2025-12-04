# tests/test_auth.py

from werkzeug.security import generate_password_hash
from flask import session

from app import app, db, User, ActionLog, is_admin


def test_register_creates_user(client, db_session):
    """POST /register should create a new user in the database."""
    resp = client.post(
        "/register",
        data={"username": "alice", "password": "secret"},
        follow_redirects=True,
    )

    # Should redirect to login page on success
    assert resp.status_code == 200

    user = User.query.filter_by(username="alice").first()
    assert user is not None
    assert user.username == "alice"
    assert user.password_hash != "secret"  # should be hashed


def test_register_rejects_empty_fields(client, db_session):
    """Empty username or password should not create a user."""
    resp = client.post(
        "/register",
        data={"username": "", "password": ""},
        follow_redirects=True,
    )
    assert resp.status_code == 200  # stays on or returns to /register

    user = User.query.filter_by(username="").first()
    assert user is None


def test_register_rejects_duplicate_username(client, db_session):
    """Second registration with same username should fail."""
    password_hash = generate_password_hash("secret")
    user = User(username="bob", password_hash=password_hash)
    db_session.add(user)
    db_session.commit()

    resp = client.post(
        "/register",
        data={"username": "bob", "password": "newpass"},
        follow_redirects=True,
    )

    # Should not create another user with same username
    users = User.query.filter_by(username="bob").all()
    assert len(users) == 1


def test_login_success_sets_session_and_logs_action(client, db_session):
    """Valid login should set session['user'] and log a login ActionLog."""
    pw_hash = generate_password_hash("secret")
    user = User(username="carol", password_hash=pw_hash)
    db_session.add(user)
    db_session.commit()

    resp = client.post(
        "/login",
        data={"username": "carol", "password": "secret"},
        follow_redirects=True,
    )

    assert resp.status_code == 200

    # Check session
    with client.session_transaction() as sess:
        assert sess.get("user") == "carol"
        assert "session_start" in sess

    # Check ActionLog entry
    login_logs = ActionLog.query.filter_by(user_id=user.id, action="login").all()
    assert len(login_logs) == 1


def test_login_failure_does_not_set_session(client, db_session):
    """Invalid login should not set session['user']."""
    pw_hash = generate_password_hash("secret")
    user = User(username="dave", password_hash=pw_hash)
    db_session.add(user)
    db_session.commit()

    resp = client.post(
        "/login",
        data={"username": "dave", "password": "wrong"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with client.session_transaction() as sess:
        assert sess.get("user") is None

    # No login ActionLog should be created for failed login
    login_logs = ActionLog.query.filter_by(user_id=user.id, action="login").all()
    assert len(login_logs) == 0


def test_logout_clears_session_and_logs_action(client, db_session):
    """GET /logout should clear session and log a logout ActionLog."""
    pw_hash = generate_password_hash("secret")
    user = User(username="erin", password_hash=pw_hash)
    db_session.add(user)
    db_session.commit()

    # Login first
    client.post(
        "/login",
        data={"username": "erin", "password": "secret"},
        follow_redirects=True,
    )

    # Then logout
    resp = client.get("/logout", follow_redirects=True)
    assert resp.status_code == 200

    with client.session_transaction() as sess:
        assert sess.get("user") is None
        assert sess.get("session_start") is None

    logout_logs = ActionLog.query.filter_by(user_id=user.id, action="logout").all()
    assert len(logout_logs) == 1


def test_index_requires_login(client):
    """The index route is protected by login_required."""
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.location


def test_admin_dashboard_requires_login(client):
    """Admin dashboard should redirect unauthenticated users to login."""
    resp = client.get("/admin/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.location


def test_admin_dashboard_rejects_non_admin(client, db_session):
    """Logged-in non-admin user should be redirected away from admin dashboard."""
    pw_hash = generate_password_hash("userpass")
    user = User(username="normaluser", password_hash=pw_hash)
    db_session.add(user)
    db_session.commit()

    client.post(
        "/login",
        data={"username": "normaluser", "password": "userpass"},
        follow_redirects=True,
    )

    resp = client.get("/admin/dashboard", follow_redirects=False)
    # admin_required should redirect to index
    assert resp.status_code == 302
    assert resp.location.endswith("/") or "/?" in resp.location


def test_is_admin_true_for_admin_user(db_session, monkeypatch):
    """is_admin returns True for 'admin' or users listed in ADMIN_USERS env."""
    pw_hash = generate_password_hash("adminpass")
    admin = User(username="admin", password_hash=pw_hash)
    db_session.add(admin)
    db_session.commit()

    # Default behavior: username == 'admin'
    assert is_admin(admin) is True

    # Test ADMIN_USERS env override
    monkeypatch.setenv("ADMIN_USERS", "alice,bob")
    other_admin = User(username="alice", password_hash=pw_hash)
    assert is_admin(other_admin) is True

    non_admin = User(username="charlie", password_hash=pw_hash)
    assert is_admin(non_admin) is False
    assert is_admin(None) is False

from werkzeug.security import generate_password_hash
from app import (
    app,
    User,
    get_test_coverage,
    get_test_results,
    get_security_metrics,
    get_security_score,
    get_critical_issues,
    get_action_items,
    get_system_health_summary,
    get_ci_cd_status,
    get_performance_metrics,
    get_code_quality_metrics,
    get_infrastructure_health,
)


def test_admin_dashboard_renders_for_admin_user(client, db_session, monkeypatch):
    """Admin user should see /admin/dashboard without heavy subprocess work."""
    # Create admin user
    pw_hash = generate_password_hash("adminpass")
    admin_user = User(username="admin", password_hash=pw_hash)
    db_session.add(admin_user)
    db_session.commit()

    # Log in as admin
    client.post(
        "/login",
        data={"username": "admin", "password": "adminpass"},
        follow_redirects=True,
    )

    # Monkeypatch all heavy helpers so route is fast & deterministic
    monkeypatch.setattr("app.get_test_coverage", lambda: 85.0)
    monkeypatch.setattr(
        "app.get_test_results",
        lambda: {"total": 10, "passed": 10, "failed": 0, "skipped": 0, "duration": 1},
    )
    monkeypatch.setattr("app.get_security_metrics", lambda: {"logins_24h": 1, "logins_7d": 2, "secret_key_secure": False, "https_enforced": False, "using_orm": True, "xss_protected": True})
    monkeypatch.setattr(
        "app.get_security_score",
        lambda: {"score": 80, "max_score": 100, "percentage": 80.0, "grade": "B", "issues": []},
    )
    monkeypatch.setattr("app.get_critical_issues", lambda: [])
    monkeypatch.setattr("app.get_action_items", lambda: [])
    monkeypatch.setattr(
        "app.get_system_health_summary",
        lambda: {
            "overall_status": "healthy",
            "overall_message": "All systems operational",
            "health_score": 100.0,
            "components": {},
            "last_check": "now",
        },
    )
    monkeypatch.setattr(
        "app.get_ci_cd_status",
        lambda: {
            "is_ci": False,
            "github_actions": False,
            "has_coverage": False,
            "has_test_report": False,
            "last_check": "now",
        },
    )
    monkeypatch.setattr(
        "app.get_performance_metrics",
        lambda: {
            "total_users": 1,
            "total_games": 1,
            "total_actions": 1,
            "avg_games_per_user": 1.0,
            "games_last_hour": 1,
            "actions_last_hour": 1,
            "activity_rate": 1.0,
        },
    )
    monkeypatch.setattr(
        "app.get_code_quality_metrics",
        lambda: {
            "total_files": 1,
            "total_lines": 10,
            "test_lines": 5,
            "code_to_test_ratio": 1.0,
        },
    )
    monkeypatch.setattr(
        "app.get_infrastructure_health",
        lambda: {
            "database_status": "connected",
            "database_type": "SQLite",
            "python_version": "3.13.0",
            "flask_version": "3.1.2",
            "environment": "development",
            "is_production": False,
        },
    )

    resp = client.get("/admin/dashboard", follow_redirects=True)
    assert resp.status_code == 200
    # sanity check we rendered something that looks like a dashboard
    assert b"dashboard" in resp.data.lower() or b"devops" in resp.data.lower()
