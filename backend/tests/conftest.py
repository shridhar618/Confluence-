from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models.user import User


@pytest.fixture()
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "test_work_management.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret")
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.setenv("DEBUG", "0")

    app = create_app()
    app.config.update(TESTING=True)

    with app.app_context():
        if not User.query.filter_by(username="intern_amy").first():
            db.session.add(
                User(
                    username="intern_amy",
                    email="amy@secureai.com",
                    password_hash=generate_password_hash("intern456"),
                    role="intern",
                )
            )
            db.session.commit()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    if Path(db_path).exists():
        Path(db_path).unlink()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def users(app):
    with app.app_context():
        return {
            user.username: user.id
            for user in User.query.all()
        }


@pytest.fixture()
def auth_headers(client):
    def _login(username, password):
        response = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200, response.get_json()
        token = response.get_json()["token"]
        return {"Authorization": f"Bearer {token}"}

    return _login
