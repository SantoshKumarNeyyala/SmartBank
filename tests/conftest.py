import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,   # disable csrf in tests
        SECRET_KEY="test-secret"
    )
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_session(client):
    """Helper to simulate logged-in user session."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Test User"
    return client