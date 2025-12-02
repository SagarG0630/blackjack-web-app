# e2e/test_e2e_blackjack.py
import time
import uuid


def test_register_and_login_flow(page, base_url):
    # Use a unique username so tests are repeatable
    username = f"e2euser_{uuid.uuid4().hex[:6]}"
    password = "Secret123!"

    # Go to register page
    page.goto(f"{base_url}/register")

    # Fill out the form
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)

    # Submit
    page.click('button[type="submit"], input[type="submit"]')

    # After register, you redirect to /login
    # Go ahead and log in
    page.goto(f"{base_url}/login")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"], input[type="submit"]')

    # We should now land on the index page (the game)
    page.wait_for_url(f"{base_url}/")

    # Basic assertion that the game page rendered
    assert "Blackjack" in page.title() or "Blackjack" in page.content()


import uuid
import time


def test_game_new_hit_stand(page, base_url):
    """
    Simple smoke E2E:
    - Register & login
    - Reach game page
    - Click Hit
    - Ensure the game page is still valid
    """
    username = f"e2eplayer_{uuid.uuid4().hex[:6]}"
    password = "Secret123!"

    # Register
    page.goto(f"{base_url}/register")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"], input[type="submit"]')

    # Login
    page.goto(f"{base_url}/login")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"], input[type="submit"]')

    # We should now be on the game page
    page.wait_for_url(f"{base_url}/")
    page.wait_for_timeout(500)  # small wait for render

    # Sanity check: game UI is present
    content_before = page.content()
    assert "Blackjack Table" in content_before
    assert "Game started. Hit or stand?" in content_before

    # Click "Hit" button (ensure it exists by role & name)
    page.get_by_role("button", name="Hit").click()
    page.wait_for_timeout(500)

    # Still on the game page, and it should still look like a blackjack table
    content_after = page.content()
    assert "Blackjack Table" in content_after
    assert "Your Hand" in content_after
    assert "Dealer's Hand" in content_after
    # Page should have changed at least a little (cards / totals)
    assert content_before != content_after
