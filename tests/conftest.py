import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-secret")
# Força SQLite em memória antes de qualquer import da app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture
def app():
    _app = create_app()
    _app.config.update(TESTING=True)
    with _app.app_context():
        _db.create_all()
        yield _app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    from app.models import User
    with app.app_context():
        u = User(email="admin@carmelhoteis.com.br", name="Admin", is_admin=True, active=True)
        _db.session.add(u)
        _db.session.commit()
        _db.session.refresh(u)
        return u


@pytest.fixture
def regular_user(app):
    from app.models import User
    with app.app_context():
        u = User(email="user@carmelhoteis.com.br", name="User", is_admin=False, active=True)
        _db.session.add(u)
        _db.session.commit()
        _db.session.refresh(u)
        return u


def login_as(client, user_id):
    """Injeta user_id na sessão do Flask-Login sem fazer OAuth."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
