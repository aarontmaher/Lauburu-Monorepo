"""
Integration tests for Authentication API routes on Port 4000 Hub.
Tests /api/auth/register, /api/auth/login, /api/auth/shopify-login, and /api/auth/me.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from ..server import app
from ..storage.sqlite_manager import SqliteManager, get_sqlite_manager


@pytest.fixture(autouse=True)
def override_sqlite_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    manager = get_sqlite_manager(db_path=path)
    yield manager
    try:
        os.remove(path)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(path + ext):
                os.remove(path + ext)
    except Exception:
        pass


@pytest.fixture
def client():
    return TestClient(app)


def test_register_flow(client):
    """Test user registration endpoint."""
    payload = {
        "email": "champion@lauburu.ai",
        "password": "ChampionSecurePassword2026",
        "name": "Champion Athlete",
        "role": "user"
    }
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert "session_token" in data
    assert len(data["session_token"]) == 64
    assert data["user"]["email"] == "champion@lauburu.ai"
    assert data["user"]["name"] == "Champion Athlete"
    assert data["user"]["membership_tier"] == "FREE"

    # Duplicate registration returns 400
    dup_resp = client.post("/api/auth/register", json=payload)
    assert dup_resp.status_code == 400
    assert "already registered" in dup_resp.json()["detail"]


def test_login_flow(client):
    """Test user login endpoint."""
    # Register first
    client.post("/api/auth/register", json={
        "email": "boxer@lauburu.ai",
        "password": "BoxerPassword123",
        "name": "Boxer Athlete"
    })

    # Successful login
    login_resp = client.post("/api/auth/login", json={
        "email": "boxer@lauburu.ai",
        "password": "BoxerPassword123"
    })
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "session_token" in data
    assert data["user"]["email"] == "boxer@lauburu.ai"

    # Bad password
    bad_resp = client.post("/api/auth/login", json={
        "email": "boxer@lauburu.ai",
        "password": "WrongPassword"
    })
    assert bad_resp.status_code == 401


def test_shopify_login_flow(client):
    """Test shopify login with dev token and customer credentials."""
    # Dev token login
    resp = client.post("/api/auth/shopify-login", json={
        "token": "tok_dev_998877"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "session_token" in data
    assert data["profile"]["tier"] == "PAID_PRO"
    assert data["membership"]["access_granted"] is True

    # Dev email credentials login
    resp2 = client.post("/api/auth/shopify-login", json={
        "email": "dev@lauburu.ai",
        "password": "AnyDevPassword"
    })
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["success"] is True
    assert data2["profile"]["is_paid_subscriber"] is True


def test_auth_me_resolution(client):
    """Test /api/auth/me session resolution."""
    # Unauthenticated
    unauth_resp = client.get("/api/auth/me")
    assert unauth_resp.status_code == 200
    assert unauth_resp.json()["authenticated"] is False

    # Register and use Bearer token
    reg_resp = client.post("/api/auth/register", json={
        "email": "cyclist@lauburu.ai",
        "password": "BikePassword123",
        "name": "Cyclist Pro"
    })
    token = reg_resp.json()["session_token"]

    # Bearer Header
    auth_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert auth_resp.status_code == 200
    data = auth_resp.json()
    assert data["authenticated"] is True
    assert data["user"]["email"] == "cyclist@lauburu.ai"
    assert data["session"]["session_token"] == token

    # Cookie auth
    cookie_resp = client.get("/api/auth/me", cookies={"lauburu_auth_token": token})
    assert cookie_resp.status_code == 200
    assert cookie_resp.json()["authenticated"] is True
