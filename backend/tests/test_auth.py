"""Tests for auth endpoints: login, GET /api/auth/me, and dev reset-admin."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, hash_password
from app.models.user import User


def test_auth_me_without_token_returns_401():
    """GET /api/auth/me without Authorization header returns 401."""
    client = TestClient(app)
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_auth_me_with_invalid_token_returns_401():
    """GET /api/auth/me with invalid token returns 401."""
    client = TestClient(app)
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
    assert res.status_code == 401


def test_auth_me_with_valid_token_returns_user(use_test_db):
    """GET /api/auth/me with valid token returns user (id, email, role, etc.)."""
    from app.core.db import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "admin@local").first()
        if not user:
            pytest.skip("No admin user; run POST /api/seed/dev first")
        token = create_access_token(user.id)
    finally:
        db.close()

    client = TestClient(app)
    res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["id"] == user.id
    assert data["email"] == user.email
    assert "role" in data
    assert "visible_menu" in data
    assert isinstance(data["visible_menu"], list)


def test_reset_admin_then_login_works(use_test_db):
    """POST /api/seed/reset-admin then login with admin@local/admin returns token (dev only)."""
    from app.core.config import settings
    if (settings.ENV or "").lower() in ("prod", "production"):
        pytest.skip("reset-admin disabled in production")
    client = TestClient(app)
    res = client.post("/api/seed/reset-admin")
    assert res.status_code == 200, res.text
    assert res.json() == {"ok": True, "email": "admin@local"}
    login_res = client.post(
        "/api/auth/login",
        json={"email": "admin@local", "password": "admin"},
    )
    assert login_res.status_code == 200, login_res.text
    data = login_res.json()
    assert "access_token" in data


def test_auth_me_alias_works(use_test_db):
    """GET /api/me (alias) returns same as /api/auth/me."""
    from app.core.db import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "admin@local").first()
        if not user:
            pytest.skip("No admin user; run POST /api/seed/dev first")
        token = create_access_token(user.id)
    finally:
        db.close()

    client = TestClient(app)
    res_me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    res_auth_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200 and res_auth_me.status_code == 200
    assert res_me.json() == res_auth_me.json()
