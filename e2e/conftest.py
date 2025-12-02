# e2e/conftest.py
import os
import subprocess
import time

import pytest
from playwright.sync_api import sync_playwright

# Default E2E DB URL (override with E2E_DATABASE_URL if needed)
E2E_DATABASE_URL = os.environ.get(
    "E2E_DATABASE_URL",
    "postgresql://blackjack_user:password@localhost:5432/blackjack_dev",
)

TEST_BASE_URL = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:5000")


@pytest.fixture(scope="session", autouse=True)
def start_flask_app():
    """
    Start the Flask app against the E2E Postgres database.
    Creates the schema once before the server starts.
    """

    # 1) Point *this* process and the child at the E2E DB
    os.environ["DATABASE_URL"] = E2E_DATABASE_URL
    env = os.environ.copy()

    # 2) Import app & db AFTER DATABASE_URL is set
    from app import app, db

    # 3) Create tables in the E2E DB
    with app.app_context():
        # optional: start from a clean DB each run
        db.drop_all()
        db.create_all()

    # 4) Start the Flask dev server in the background
    proc = subprocess.Popen(["python", "app.py"], env=env)

    # Give the server a moment to boot
    time.sleep(3)

    yield

    # 5) Teardown
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as p:
        yield p


@pytest.fixture
def browser(playwright_instance):
    browser = playwright_instance.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture(scope="session")
def base_url():
    return TEST_BASE_URL
