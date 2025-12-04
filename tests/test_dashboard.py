# tests/test_dashboard.py

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

from app import (
    app,
    User,
    HandHistory,
    ActionLog,
    get_user_statistics,
    get_recent_games,
    get_user_game_history,
    get_system_overview,
    get_daily_activity,
    get_action_distribution,
    get_most_active_users,
    get_hourly_activity,
    get_system_health,
    get_security_metrics,
    get_security_score,
    get_performance_metrics,
    get_code_quality_metrics,
    get_infrastructure_health,
    get_ci_cd_status,
    get_critical_issues,
    get_action_items,
    get_system_health_summary,
    is_admin,
)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def create_and_login_user(client, db_session, username="dashboarduser", password="pass123"):
    """Helper to create user and log them in via /login."""
    pw_hash = generate_password_hash(password)
    user = User(username=username, password_hash=pw_hash)
    db_session.add(user)
    db_session.commit()

    client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
    return user


# -------------------------------------------------------------------
# Route-level tests (user dashboard)
# -------------------------------------------------------------------

def test_dashboard_requires_login(client):
    """Dashboard should redirect to login if not authenticated."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.location


def test_dashboard_displays_for_logged_in_user(client, db_session):
    """Dashboard should render successfully for a logged-in user."""
    user = create_and_login_user(client, db_session)

    # Add a little history so the template has something to show
    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.commit()

    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    # Content will depend on your template; just assert something reasonable
    assert b"dashboard" in response.data.lower() or b"game" in response.data.lower()


def test_dashboard_handles_missing_user_gracefully(client, db_session):
    """If the session user is deleted, dashboard should not 500."""
    user = create_and_login_user(client, db_session)
    # Delete the user to simulate edge case
    db_session.delete(user)
    db_session.commit()

    response = client.get("/dashboard", follow_redirects=True)
    # Either redirect or show a friendly message, but no 500
    assert response.status_code in (200, 302)


# -------------------------------------------------------------------
# Gameplay stats helper tests
# -------------------------------------------------------------------

def test_get_user_statistics_with_games(client, db_session):
    user = create_and_login_user(client, db_session)

    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.add(HandHistory(user_id=user.id, result="loss"))
    db_session.commit()

    stats = get_user_statistics(user.id)

    assert stats["total_games"] == 3
    assert stats["wins"] == 2
    assert stats["losses"] == 1
    assert stats["pushes"] == 0
    assert stats["win_rate"] > 0


def test_get_user_statistics_no_games(client, db_session):
    user = create_and_login_user(client, db_session)

    stats = get_user_statistics(user.id)

    assert stats["total_games"] == 0
    assert stats["wins"] == 0
    assert stats["losses"] == 0
    assert stats["pushes"] == 0
    assert stats["win_rate"] == 0


def test_get_recent_games_limit(client, db_session):
    user = create_and_login_user(client, db_session)

    for _ in range(5):
        db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.commit()

    recent = get_recent_games(user.id, limit=3)
    assert len(recent) <= 3
    assert len(recent) > 0


def test_get_user_game_history_returns_days(client, db_session):
    user = create_and_login_user(client, db_session)

    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.commit()

    history = get_user_game_history(user.id, days=7)
    assert isinstance(history, list)
    assert len(history) > 0
    assert "date" in history[0]
    assert "games" in history[0]


# -------------------------------------------------------------------
# System / activity metrics
# -------------------------------------------------------------------

def test_get_system_overview_basic(client, db_session):
    user = create_and_login_user(client, db_session)
    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.add(ActionLog(user_id=user.id, action="login"))
    db_session.commit()

    overview = get_system_overview()
    assert "total_users" in overview
    assert "total_games" in overview
    assert "total_actions" in overview
    assert overview["total_users"] >= 1
    assert overview["total_games"] >= 1
    assert overview["total_actions"] >= 1


def test_get_daily_activity(client, db_session):
    user = create_and_login_user(client, db_session)
    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.commit()

    activity = get_daily_activity(days=3)
    assert isinstance(activity, list)
    assert len(activity) > 0
    assert "date" in activity[0]
    assert "games" in activity[0]
    assert "logins" in activity[0]
    assert "new_users" in activity[0]


def test_get_action_distribution(client, db_session):
    user = create_and_login_user(client, db_session)
    db_session.add(ActionLog(user_id=user.id, action="login"))
    db_session.add(ActionLog(user_id=user.id, action="hit"))
    db_session.add(ActionLog(user_id=user.id, action="stand"))
    db_session.commit()

    dist = get_action_distribution()
    assert isinstance(dist, dict)
    assert any(action in dist for action in ("login", "hit", "stand"))


def test_get_most_active_users(client, db_session):
    user = create_and_login_user(client, db_session, username="activeuser")
    for _ in range(3):
        db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.commit()

    active = get_most_active_users(limit=5)
    assert isinstance(active, list)
    assert len(active) >= 1
    assert any(u["username"] == "activeuser" for u in active)


def test_get_hourly_activity(client, db_session):
    user = create_and_login_user(client, db_session)
    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.add(ActionLog(user_id=user.id, action="login"))
    db_session.commit()

    hourly = get_hourly_activity()
    assert isinstance(hourly, list)
    assert len(hourly) == 24
    assert "hour" in hourly[0]
    assert "games" in hourly[0]
    assert "logins" in hourly[0]


def test_get_system_health(client, db_session):
    user = create_and_login_user(client, db_session)
    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.commit()

    health = get_system_health()
    assert "database_status" in health
    assert "total_records" in health
    assert "avg_games_per_user" in health
    assert "overall_win_rate" in health
    assert health["database_status"] in ("connected", "disconnected")


# -------------------------------------------------------------------
# Security / DevSecOps metrics
# -------------------------------------------------------------------

def test_is_admin_function(db_session):
    admin_pw = generate_password_hash("adminpass")
    user_pw = generate_password_hash("userpass")

    admin_user = User(username="admin", password_hash=admin_pw)
    regular_user = User(username="bob", password_hash=user_pw)
    db_session.add(admin_user)
    db_session.add(regular_user)
    db_session.commit()

    assert is_admin(admin_user) is True
    assert is_admin(regular_user) is False
    assert is_admin(None) is False


def test_get_security_metrics(client, db_session):
    user = create_and_login_user(client, db_session)
    db_session.add(ActionLog(user_id=user.id, action="login"))
    db_session.add(ActionLog(user_id=user.id, action="login"))
    db_session.commit()

    metrics = get_security_metrics()
    assert isinstance(metrics, dict)
    assert "logins_24h" in metrics
    assert "logins_7d" in metrics
    assert "secret_key_secure" in metrics
    assert "https_enforced" in metrics


def test_get_security_score(client, db_session):
    user = create_and_login_user(client, db_session)
    db_session.add(ActionLog(user_id=user.id, action="login"))
    db_session.commit()

    score = get_security_score()
    assert isinstance(score, dict)
    assert "score" in score
    assert "max_score" in score
    assert "percentage" in score
    assert "grade" in score
    assert "issues" in score


def test_get_performance_metrics(client, db_session):
    user = create_and_login_user(client, db_session)
    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.add(ActionLog(user_id=user.id, action="hit"))
    db_session.commit()

    metrics = get_performance_metrics()
    assert isinstance(metrics, dict)
    for key in (
        "total_users",
        "total_games",
        "total_actions",
        "avg_games_per_user",
        "games_last_hour",
        "actions_last_hour",
        "activity_rate",
    ):
        assert key in metrics


def test_get_code_quality_metrics():
    metrics = get_code_quality_metrics()
    assert isinstance(metrics, dict)
    assert "total_files" in metrics
    assert "total_lines" in metrics
    assert "test_lines" in metrics
    assert "code_to_test_ratio" in metrics


def test_get_infrastructure_health():
    health = get_infrastructure_health()
    assert isinstance(health, dict)
    for key in ("database_status", "database_type", "python_version",
                "flask_version", "environment", "is_production"):
        assert key in health


def test_get_ci_cd_status():
    status = get_ci_cd_status()
    assert isinstance(status, dict)
    for key in ("is_ci", "github_actions", "has_coverage", "has_test_report", "last_check"):
        assert key in status


# -------------------------------------------------------------------
# Aggregated “issues” helpers (with monkeypatch to avoid subprocess)
# -------------------------------------------------------------------

def test_get_critical_issues_with_mocked_metrics(monkeypatch):
    """Avoid running subprocess pytest/coverage inside tests by mocking helpers.

    We only care that:
    - get_critical_issues returns a list
    - items have the expected structure
    - our mocked coverage/test results don't produce 'low coverage' or 'failing tests' issues.
    """

    def fake_get_test_coverage():
        return 80.0  # above 75% threshold

    def fake_get_test_results():
        return {"total": 10, "failed": 0}  # no failing tests

    monkeypatch.setattr("app.get_test_coverage", fake_get_test_coverage)
    monkeypatch.setattr("app.get_test_results", fake_get_test_results)

    issues = get_critical_issues()
    assert isinstance(issues, list)

    # All issues should have the basic expected fields
    for issue in issues:
        assert "severity" in issue
        assert "title" in issue
        assert "description" in issue
        assert "fix" in issue
        assert "time" in issue

    # With our mocked coverage/results, we should NOT see coverage/test-failure issues
    titles = [issue["title"] for issue in issues]
    assert not any("Coverage Below 75" in t for t in titles)
    assert not any("Test(s) Failing" in t for t in titles)



def test_get_action_items_wraps_critical_issues(monkeypatch):
    fake_issues = [
        {
            "severity": "critical",
            "title": "Insecure Secret Key",
            "description": "Bad key",
            "fix": "Set SECRET_KEY",
            "time": "5 minutes",
            "file": "app.py",
        }
    ]

    monkeypatch.setattr("app.get_critical_issues", lambda: fake_issues)

    items = get_action_items()
    assert isinstance(items, list)
    assert len(items) == 1
    item = items[0]
    assert item["title"] == "Insecure Secret Key"
    assert item["severity"] == "critical"
    assert item["completed"] is False


def test_get_system_health_summary_with_mocked_subhelpers(monkeypatch):
    """Mock heavy helpers so this stays fast and deterministic."""

    monkeypatch.setattr(
        "app.get_security_score",
        lambda: {"percentage": 80.0, "grade": "B", "score": 80, "max_score": 100, "issues": []},
    )
    monkeypatch.setattr("app.get_test_coverage", lambda: 80.0)
    monkeypatch.setattr(
        "app.get_test_results",
        lambda: {"total": 10, "failed": 0, "passed": 10, "skipped": 0, "duration": 1},
    )
    monkeypatch.setattr(
        "app.get_performance_metrics",
        lambda: {"total_users": 1, "total_games": 1, "total_actions": 1,
                 "avg_games_per_user": 1.0, "games_last_hour": 1,
                 "actions_last_hour": 1, "activity_rate": 1.0},
    )

    summary = get_system_health_summary()
    assert isinstance(summary, dict)
    assert "overall_status" in summary
    assert "overall_message" in summary
    assert "health_score" in summary
    assert "components" in summary
    assert "last_check" in summary
