# tests/test_integration.py

from datetime import datetime

import pytest
from werkzeug.security import generate_password_hash

from app import (
    app,
    db,
    User,
    HandHistory,
    ActionLog,
    get_user_statistics,
)

# Mark this entire module as "integration" so CI can select or skip it via:
#   pytest -m "integration"
#   pytest -m "not integration"
pytestmark = pytest.mark.integration

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def create_user(db_session, username="player1", password="secret"):
    pw_hash = generate_password_hash(password)
    user = User(username=username, password_hash=pw_hash)
    db_session.add(user)
    db_session.commit()
    return user


def login_user(client, username, password):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


# ---------------------------------------------------------
# Auth / Registration Integration
# ---------------------------------------------------------


def test_register_and_login_happy_path(client, db_session):
    """
    Full flow:
    - Register a new user
    - Confirm user exists in DB
    - Log in
    - Access index successfully
    """
    # Register
    resp = client.post(
        "/register",
        data={"username": "integ_user", "password": "supersecret"},
        follow_redirects=True,
    )
    assert resp.status_code == 200  # Should end on login page or similar

    # User should exist in DB
    user = User.query.filter_by(username="integ_user").first()
    assert user is not None
    assert user.password_hash != "supersecret"  # hashed

    # Login with correct credentials
    resp = login_user(client, "integ_user", "supersecret")
    assert resp.status_code == 200

    # Index should now be accessible
    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200
    assert (
        b"integ_user" in resp.data
        or b"Blackjack" in resp.data
        or b"Game" in resp.data
    )


def test_login_rejects_invalid_password(client, db_session):
    """
    Existing user with wrong password should not be logged in.
    No login ActionLog should be recorded.
    """
    user = create_user(db_session, "loginuser", "correctpass")

    resp = client.post(
        "/login",
        data={"username": "loginuser", "password": "wrongpass"},
        follow_redirects=True,
    )
    assert resp.status_code == 200  # stays on login page

    # No ActionLog for login
    logs = ActionLog.query.filter_by(user_id=user.id, action="login").all()
    assert len(logs) == 0


def test_login_rejects_nonexistent_user(client, db_session):
    """
    Logging in with a user that doesn't exist should not crash or log.
    """
    resp = client.post(
        "/login",
        data={"username": "ghost", "password": "whatever"},
        follow_redirects=True,
    )
    assert resp.status_code == 200  # login page again

    # No user, so obviously no ActionLog for 'ghost'
    assert User.query.filter_by(username="ghost").first() is None


# ---------------------------------------------------------
# Dashboard Integration (User & Admin)
# ---------------------------------------------------------


def test_user_dashboard_shows_for_logged_in_user(client, db_session):
    """
    User should be able to see /dashboard and stats should reflect DB data.
    """
    user = create_user(db_session, "dashuser", "pw")
    login_user(client, "dashuser", "pw")

    # Add some game history
    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.add(HandHistory(user_id=user.id, result="loss"))
    db_session.commit()

    # Hit dashboard
    resp = client.get("/dashboard", follow_redirects=True)
    assert resp.status_code == 200
    assert b"dashboard" in resp.data.lower() or b"stats" in resp.data.lower()

    # Also verify helper returns correct stats (integration with DB)
    stats = get_user_statistics(user.id)
    assert stats["total_games"] == 3
    assert stats["wins"] == 2
    assert stats["losses"] == 1
    assert stats["pushes"] == 0


def test_user_cannot_access_admin_dashboard(client, db_session):
    """
    Normal user should be redirected away from /admin/dashboard.
    """
    create_user(db_session, "normal", "pw")
    login_user(client, "normal", "pw")

    resp = client.get("/admin/dashboard", follow_redirects=False)
    # admin_required decorator should redirect (likely to index)
    assert resp.status_code == 302
    assert resp.location.endswith("/") or "/?" in resp.location


def test_admin_can_access_admin_dashboard(client, db_session, monkeypatch):
    """
    Admin user should see /admin/dashboard.
    We monkeypatch heavy metrics so this stays fast and doesn't run subprocesses.
    """
    # Create default admin user (username == 'admin')
    create_user(db_session, "admin", "adminpw")
    login_user(client, "admin", "adminpw")

    # Monkeypatch heavy helper functions to avoid subprocess calls
    monkeypatch.setattr("app.get_test_coverage", lambda: 90.0)
    monkeypatch.setattr(
        "app.get_test_results",
        lambda: {"total": 10, "passed": 10, "failed": 0, "skipped": 0, "duration": 1},
    )
    monkeypatch.setattr(
        "app.get_security_metrics",
        lambda: {
            "logins_24h": 1,
            "logins_7d": 2,
            "secret_key_secure": False,
            "https_enforced": False,
            "using_orm": True,
            "xss_protected": True,
        },
    )
    monkeypatch.setattr(
        "app.get_security_score",
        lambda: {
            "score": 80,
            "max_score": 100,
            "percentage": 80.0,
            "grade": "B",
            "issues": [],
        },
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
    assert b"dashboard" in resp.data.lower() or b"devops" in resp.data.lower()


def test_admin_login_with_default_credentials_can_access_admin_dashboard(client, db_session, monkeypatch):
    """
    Admin should be able to log in with the default credentials
    (username: admin, password: Admin123) and access /admin/dashboard.

    This uses the same heavy-metric monkeypatching as the other admin test
    so it stays fast and doesn't trigger subprocesses.
    """
    # Create admin user in the test DB with the same creds as production
    create_user(db_session, "admin", "Admin123")

    # Log in with the default admin credentials
    login_user(client, "admin", "Admin123")

    # Monkeypatch heavy helper functions to avoid subprocess calls / external deps
    monkeypatch.setattr("app.get_test_coverage", lambda: 90.0)
    monkeypatch.setattr(
        "app.get_test_results",
        lambda: {"total": 10, "passed": 10, "failed": 0, "skipped": 0, "duration": 1},
    )
    monkeypatch.setattr(
        "app.get_security_metrics",
        lambda: {
            "logins_24h": 1,
            "logins_7d": 2,
            "secret_key_secure": False,
            "https_enforced": False,
            "using_orm": True,
            "xss_protected": True,
        },
    )
    monkeypatch.setattr(
        "app.get_security_score",
        lambda: {
            "score": 80,
            "max_score": 100,
            "percentage": 80.0,
            "grade": "B",
            "issues": [],
        },
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

    # Hit the admin dashboard
    resp = client.get("/admin/dashboard", follow_redirects=True)

    assert resp.status_code == 200
    # Page should look like an admin/devops dashboard
    assert b"dashboard" in resp.data.lower() or b"devops" in resp.data.lower()


# ---------------------------------------------------------
# Gameplay Integration
# ---------------------------------------------------------


def test_gameplay_flow_hit_stand_records_history(client, db_session):
    """
    Full gameplay flow:
    - Login as user
    - Visit index to initialize game
    - Hit once
    - Stand
    - Verify ActionLog and HandHistory records are present
    """
    user = create_user(db_session, "gamer", "pw")
    login_user(client, "gamer", "pw")

    # Visiting index sets up game in memory
    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200

    # Perform a hit
    resp = client.get("/hit", follow_redirects=True)
    assert resp.status_code == 200

    # There should be at least one 'hit' action logged
    hit_logs = ActionLog.query.filter_by(user_id=user.id, action="hit").all()
    assert len(hit_logs) >= 1

    # Now stand to finish the hand and record a game result
    resp = client.get("/stand", follow_redirects=True)
    assert resp.status_code == 200

    # 'stand' should be logged
    stand_logs = ActionLog.query.filter_by(user_id=user.id, action="stand").all()
    assert len(stand_logs) >= 1

    # There should be at least one HandHistory record with a valid result.
    # In bust scenarios, there may be 2 (one from /hit, one from /stand).
    hands = HandHistory.query.filter_by(user_id=user.id).all()
    assert len(hands) >= 1
    for h in hands:
        assert h.result in ("win", "loss", "push")


def test_new_game_starts_fresh_and_logs_action(client, db_session):
    """
    /new should start a fresh game and log 'new_game' for the user.
    """
    user = create_user(db_session, "newgamer", "pw")
    login_user(client, "newgamer", "pw")

    # Call /new
    resp = client.get("/new", follow_redirects=True)
    assert resp.status_code == 200

    logs = ActionLog.query.filter_by(user_id=user.id, action="new_game").all()
    assert len(logs) == 1


def test_index_uses_session_timer(client, db_session, monkeypatch):
    """
    Index should handle session_start in session and not crash when computing time.
    This also indirectly tests format_seconds_hhmmss and session logic.
    """
    create_user(db_session, "timeruser", "pw")
    login_user(client, "timeruser", "pw")

    # Manually tweak session_start to a fixed past time
    with client.session_transaction() as sess:
        sess["session_start"] = datetime.utcnow().isoformat()

    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200
    # We don't assert exact timer string, but page should load fine with timer logic executed.
