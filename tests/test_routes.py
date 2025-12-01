# tests/test_routes.py
from werkzeug.security import generate_password_hash
from app import User, get_game_for_user, GAMES, BlackjackGame, Card, hand_value


def create_and_login_user(client, db_session, username="routeuser", password="pass123"):
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


def test_logout_clears_session_and_redirects(client, db_session):
    username = create_and_login_user(client, db_session)

    # Now log out
    response = client.get("/logout", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.location

    # After logout, hitting "/" should redirect to login again
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.location


def test_index_renders_for_logged_in_user(client, db_session):
    username = create_and_login_user(client, db_session)

    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    # basic sanity check that template rendered with username somewhere
    assert username.encode("utf-8") in response.data


def test_new_game_route_starts_game(client, db_session):
    username = create_and_login_user(client, db_session)

    # Start a new game
    response = client.get("/new", follow_redirects=True)
    assert response.status_code == 200

    # Index page should show some cards in HTML
    assert b"hearts" in response.data or b"spades" in response.data or b"diamonds" in response.data or b"clubs" in response.data


def test_hit_route_progresses_game(client, db_session):
    username = create_and_login_user(client, db_session)

    # Ensure game exists
    client.get("/new", follow_redirects=True)
    response_before = client.get("/", follow_redirects=True)
    # We don't parse HTML deeply; we just hit the route
    response_hit = client.get("/hit", follow_redirects=True)
    assert response_hit.status_code == 200


def test_stand_route_finishes_game(client, db_session):
    username = create_and_login_user(client, db_session)

    client.get("/new", follow_redirects=True)
    response = client.get("/stand", follow_redirects=True)
    assert response.status_code == 200
    # After stand, message should mention win/lose/push
    assert b"You win!" in response.data or b"Dealer wins." in response.data or b"Push" in response.data
