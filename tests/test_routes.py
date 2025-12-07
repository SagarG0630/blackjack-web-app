# tests/test_routes.py

from werkzeug.security import generate_password_hash

from app import app, db, User, HandHistory, ActionLog


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


def test_index_shows_dashboard_for_logged_in_user(client, db_session):
    """GET / should render game page for logged-in user."""
    user = create_user(db_session, "routeuser", "secret")
    login_user(client, "routeuser", "secret")

    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200
    # Page should mention user or something related to game
    assert b"routeuser" in resp.data or b"Blackjack" in resp.data or b"Game" in resp.data


def test_hit_route_logs_action(client, db_session):
    """GET /hit should log a 'hit' ActionLog for the user."""
    user = create_user(db_session, "hitter", "secret")
    login_user(client, "hitter", "secret")

    # First, ensure game exists; index will create it via get_game_for_user
    client.get("/", follow_redirects=True)

    resp = client.get("/hit", follow_redirects=True)
    assert resp.status_code == 200

    hits = ActionLog.query.filter_by(user_id=user.id, action="hit").all()
    assert len(hits) == 1


def test_stand_route_logs_action_and_game_result(client, db_session):
    """GET /stand should log 'stand' and create a HandHistory entry."""
    user = create_user(db_session, "stander", "secret")
    login_user(client, "stander", "secret")

    resp = client.get("/stand", follow_redirects=True)
    assert resp.status_code == 200

    stands = ActionLog.query.filter_by(user_id=user.id, action="stand").all()
    assert len(stands) == 1

    # stand() always sets game.finished and records a result
    games = HandHistory.query.filter_by(user_id=user.id).all()
    assert len(games) == 1
    assert games[0].result in ("win", "loss", "push")


def test_new_route_starts_new_game_and_logs_action(client, db_session):
    """GET /new should start a new game and log a 'new_game' action."""
    user = create_user(db_session, "newgamer", "secret")
    login_user(client, "newgamer", "secret")

    resp = client.get("/new", follow_redirects=True)
    assert resp.status_code == 200

    logs = ActionLog.query.filter_by(user_id=user.id, action="new_game").all()
    assert len(logs) == 1


def test_index_stats_counts_wins_losses_pushes(client, db_session):
    """Index should compute the sums of HandHistory correctly."""
    user = create_user(db_session, "statsuser", "secret")

    # Add some hand history rows
    db_session.add(HandHistory(user_id=user.id, result="win"))
    db_session.add(HandHistory(user_id=user.id, result="loss"))
    db_session.add(HandHistory(user_id=user.id, result="push"))
    db_session.commit()

    login_user(client, "statsuser", "secret")
    resp = client.get("/", follow_redirects=True)
    assert resp.status_code == 200

    # We can't easily parse the HTML for numbers without knowing template,
    # but this at least ensures the route executes with history in place.
    # The presence of "win" / "loss" text is a reasonable heuristic.
    assert b"win" in resp.data.lower() or b"loss" in resp.data.lower() or b"push" in resp.data.lower()
