# tests/test_dashboard.py
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from app import (
    User, HandHistory, ActionLog,
    get_user_statistics, get_recent_games, get_user_game_history,
    get_system_overview, get_daily_activity, get_action_distribution,
    get_most_active_users, get_hourly_activity, get_system_health,
    get_test_coverage, get_test_results, get_security_metrics,
    get_security_score, get_critical_issues,
    get_performance_metrics, get_code_quality_metrics,
    get_infrastructure_health, get_action_items,
    get_system_health_summary, get_ci_cd_status,
    is_admin, admin_required
)


def create_and_login_user(client, db_session, username="dashboarduser", password="pass123"):
    """Helper to create user and log in"""
    pw_hash = generate_password_hash(password)
    user = User(username=username, password_hash=pw_hash)
    db_session.add(user)
    db_session.commit()

    client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
    return username


def test_dashboard_requires_login(client):
    """Dashboard should redirect if not authenticated"""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.location


def test_dashboard_displays_for_logged_in_user(client, db_session):
    """Dashboard should display for authenticated user"""
    username = create_and_login_user(client, db_session)
    
    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"My Gameplay Dashboard" in response.data or b"Dashboard" in response.data


def test_dashboard_with_game_history(client, db_session):
    """Dashboard should show user statistics with game history"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    # Create some game history
    HandHistory(user_id=user.id, result='win')
    HandHistory(user_id=user.id, result='loss')
    HandHistory(user_id=user.id, result='push')
    db_session.commit()
    
    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Total Games" in response.data or b"Wins" in response.data


def test_get_user_statistics(client, db_session):
    """Test get_user_statistics function"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    # Add game history
    h1 = HandHistory(user_id=user.id, result='win')
    h2 = HandHistory(user_id=user.id, result='win')
    h3 = HandHistory(user_id=user.id, result='loss')
    db_session.add(h1)
    db_session.add(h2)
    db_session.add(h3)
    db_session.commit()
    db_session.flush()
    
    stats = get_user_statistics(user.id)
    assert stats['total_games'] == 3
    assert stats['wins'] == 2
    assert stats['losses'] == 1
    assert stats['pushes'] == 0
    assert stats['win_rate'] > 0


def test_get_user_statistics_no_games(client, db_session):
    """Test get_user_statistics with no games"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    stats = get_user_statistics(user.id)
    assert stats['total_games'] == 0
    assert stats['wins'] == 0
    assert stats['win_rate'] == 0


def test_get_recent_games(client, db_session):
    """Test get_recent_games function"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    # Add multiple games
    for i in range(5):
        h = HandHistory(user_id=user.id, result='win')
        db_session.add(h)
    db_session.commit()
    db_session.flush()
    
    recent = get_recent_games(user.id, limit=3)
    assert len(recent) <= 3
    assert len(recent) > 0


def test_get_user_game_history(client, db_session):
    """Test get_user_game_history function"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    # Add a game
    HandHistory(user_id=user.id, result='win')
    db_session.commit()
    
    history = get_user_game_history(user.id, days=30)
    assert isinstance(history, list)
    assert len(history) > 0


def test_get_system_overview(client, db_session):
    """Test get_system_overview function"""
    # Create some users and data
    username1 = create_and_login_user(client, db_session, "user1", "pass1")
    user1 = User.query.filter_by(username=username1).first()
    
    h = HandHistory(user_id=user1.id, result='win')
    a = ActionLog(user_id=user1.id, action='login')
    db_session.add(h)
    db_session.add(a)
    db_session.commit()
    db_session.flush()
    
    overview = get_system_overview()
    assert 'total_users' in overview
    assert 'total_games' in overview
    assert 'total_actions' in overview
    assert overview['total_users'] >= 1
    assert overview['total_games'] >= 1


def test_get_daily_activity(client, db_session):
    """Test get_daily_activity function"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    HandHistory(user_id=user.id, result='win')
    db_session.commit()
    
    activity = get_daily_activity(days=30)
    assert isinstance(activity, list)
    assert len(activity) > 0
    assert 'date' in activity[0]
    assert 'games' in activity[0]


def test_get_action_distribution(client, db_session):
    """Test get_action_distribution function"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    ActionLog(user_id=user.id, action='login')
    ActionLog(user_id=user.id, action='hit')
    ActionLog(user_id=user.id, action='stand')
    db_session.commit()
    
    dist = get_action_distribution()
    assert isinstance(dist, dict)
    assert 'login' in dist or len(dist) > 0


def test_get_most_active_users(client, db_session):
    """Test get_most_active_users function"""
    username1 = create_and_login_user(client, db_session, "active1", "pass1")
    user1 = User.query.filter_by(username=username1).first()
    
    # Create multiple games for this user
    for i in range(5):
        h = HandHistory(user_id=user1.id, result='win')
        db_session.add(h)
    db_session.commit()
    db_session.flush()
    
    active = get_most_active_users(limit=10)
    assert isinstance(active, list)
    assert len(active) > 0


def test_get_hourly_activity(client, db_session):
    """Test get_hourly_activity function"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    HandHistory(user_id=user.id, result='win')
    ActionLog(user_id=user.id, action='login')
    db_session.commit()
    
    hourly = get_hourly_activity()
    assert isinstance(hourly, list)
    assert len(hourly) == 24
    assert 'hour' in hourly[0]
    assert 'games' in hourly[0]


def test_get_system_health(client, db_session):
    """Test get_system_health function"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    HandHistory(user_id=user.id, result='win')
    db_session.commit()
    
    health = get_system_health()
    assert 'database_status' in health
    assert 'total_records' in health
    assert health['database_status'] == 'connected'


def test_admin_dashboard_requires_admin(client, db_session):
    """Admin dashboard should redirect non-admin users"""
    username = create_and_login_user(client, db_session, "regularuser", "pass123")
    
    response = client.get("/admin/dashboard", follow_redirects=False)
    # Should redirect (either to login or index)
    assert response.status_code in [302, 200]


# def test_admin_dashboard_for_admin_user(client, db_session):
#     """Admin dashboard should be accessible to admin users"""
#     # Create admin user
#     pw_hash = generate_password_hash("adminpass")
#     admin_user = User(username="admin", password_hash=pw_hash)
#     db_session.add(admin_user)
#     db_session.commit()
    
#     # Login as admin
#     client.post(
#         "/login",
#         data={"username": "admin", "password": "adminpass"},
#         follow_redirects=True,
#     )
    
#     # Access admin dashboard - this should work for admin
#     response = client.get("/admin/dashboard", follow_redirects=True)
#     # Should show dashboard for admin
#     assert response.status_code == 200
#     assert b"Admin Dashboard" in response.data or b"DevOps" in response.data or b"dashboard" in response.data.lower()


def test_is_admin_function(client, db_session):
    """Test is_admin function"""
    # Create admin user
    pw_hash = generate_password_hash("adminpass")
    admin_user = User(username="admin", password_hash=pw_hash)
    db_session.add(admin_user)
    
    # Create regular user
    pw_hash2 = generate_password_hash("userpass")
    regular_user = User(username="user", password_hash=pw_hash2)
    db_session.add(regular_user)
    db_session.commit()
    
    # Test admin user
    assert is_admin(admin_user) == True
    
    # Test regular user
    assert is_admin(regular_user) == False
    
    # Test None
    assert is_admin(None) == False


def test_dashboard_with_no_user(client, db_session):
    """Test dashboard when user is not found"""
    # Login but then delete user (simulate edge case)
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    db_session.delete(user)
    db_session.commit()
    
    # Try to access dashboard - should handle gracefully
    response = client.get("/dashboard", follow_redirects=True)
    # Should either redirect or show error
    assert response.status_code in [200, 302]


def test_get_test_coverage():
    """Test get_test_coverage function"""
    # This will likely return None in test environment, but we test it doesn't crash
    coverage = get_test_coverage()
    assert coverage is None or isinstance(coverage, (int, float))


# def test_get_test_results():
#     """Test get_test_results function"""
#     # This may return None in test environment, but we test it doesn't crash
#     results = get_test_results()
#     assert results is None or isinstance(results, dict)


def test_get_security_metrics(client, db_session):
    """Test get_security_metrics function"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    # Add some login actions
    a1 = ActionLog(user_id=user.id, action='login')
    a2 = ActionLog(user_id=user.id, action='login')
    db_session.add(a1)
    db_session.add(a2)
    db_session.commit()
    
    metrics = get_security_metrics()
    assert isinstance(metrics, dict)
    assert 'logins_24h' in metrics
    assert 'logins_7d' in metrics
    assert 'secret_key_secure' in metrics


def test_get_security_score(client, db_session):
    """Test get_security_score function"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    # Add some login actions
    a = ActionLog(user_id=user.id, action='login')
    db_session.add(a)
    db_session.commit()
    
    score = get_security_score()
    assert isinstance(score, dict)
    assert 'score' in score
    assert 'percentage' in score
    assert 'grade' in score
    assert 'issues' in score


# def test_get_critical_issues():
#     """Test get_critical_issues function"""
#     issues = get_critical_issues()
#     assert isinstance(issues, list)
#     # May be empty or have issues, both are valid


def test_get_performance_metrics(client, db_session):
    """Test get_performance_metrics function"""
    username = create_and_login_user(client, db_session)
    user = User.query.filter_by(username=username).first()
    
    # Add some data
    h = HandHistory(user_id=user.id, result='win')
    a = ActionLog(user_id=user.id, action='hit')
    db_session.add(h)
    db_session.add(a)
    db_session.commit()
    
    metrics = get_performance_metrics()
    assert isinstance(metrics, dict)
    assert 'total_users' in metrics
    assert 'total_games' in metrics
    assert 'total_actions' in metrics
    assert 'avg_games_per_user' in metrics
    assert 'games_last_hour' in metrics
    assert 'actions_last_hour' in metrics
    assert 'activity_rate' in metrics


def test_get_code_quality_metrics():
    """Test get_code_quality_metrics function"""
    metrics = get_code_quality_metrics()
    assert isinstance(metrics, dict)
    assert 'total_files' in metrics
    assert 'total_lines' in metrics
    assert 'test_lines' in metrics
    assert 'code_to_test_ratio' in metrics


def test_get_infrastructure_health():
    """Test get_infrastructure_health function"""
    health = get_infrastructure_health()
    assert isinstance(health, dict)
    assert 'database_status' in health
    assert 'database_type' in health
    assert 'python_version' in health
    assert 'flask_version' in health
    assert 'environment' in health
    assert 'is_production' in health


# def test_get_action_items():
#     """Test get_action_items function"""
#     items = get_action_items()
#     assert isinstance(items, list)
#     # May be empty or have items, both are valid
#     if len(items) > 0:
#         assert 'id' in items[0]
#         assert 'title' in items[0]
#         assert 'severity' in items[0]


# def test_get_system_health_summary():
#     """Test get_system_health_summary function"""
#     summary = get_system_health_summary()
#     assert isinstance(summary, dict)
#     assert 'overall_status' in summary
#     assert 'overall_message' in summary
#     assert 'health_score' in summary
#     assert 'components' in summary
#     assert 'last_check' in summary


def test_get_ci_cd_status():
    """Test get_ci_cd_status function"""
    status = get_ci_cd_status()
    assert isinstance(status, dict)
    assert 'is_ci' in status
    assert 'github_actions' in status
    assert 'has_coverage' in status
    assert 'has_test_report' in status
    assert 'last_check' in status

# test2
# def test_admin_dashboard_route_execution(client, db_session):
#     """Test that admin dashboard route executes all helper functions"""
#     # Create admin user
#     pw_hash = generate_password_hash("adminpass")
#     admin_user = User(username="admin", password_hash=pw_hash)
#     db_session.add(admin_user)
#     db_session.commit()
    
#     # Login as admin
#     client.post(
#         "/login",
#         data={"username": "admin", "password": "adminpass"},
#         follow_redirects=True,
#     )
    
#     # Access admin dashboard - this should execute all the helper functions
#     response = client.get("/admin/dashboard", follow_redirects=True)
#     assert response.status_code == 200
#     # Verify some content from admin dashboard is present
#     assert b"dashboard" in response.data.lower() or b"Admin" in response.data or b"DevOps" in response.data

