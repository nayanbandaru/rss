"""
Tests for alert API endpoints with authentication.
"""
import pytest
import os
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.dependencies import get_db
from app.utils.security import hash_password, create_access_token
from db import Base, User, Alert

# Test database setup
TEST_DATABASE_PATH = "/tmp/test_api_rss.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DATABASE_PATH}"


@pytest.fixture(scope="function")
def setup_test_db():
    """Set up test database for each test"""
    # Remove old test database if exists
    if os.path.exists(TEST_DATABASE_PATH):
        os.remove(TEST_DATABASE_PATH)

    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield engine, TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(TEST_DATABASE_PATH):
        os.remove(TEST_DATABASE_PATH)


@pytest.fixture
def client(setup_test_db):
    """Create test client"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_user(setup_test_db):
    """Create a test user with password"""
    engine, TestingSessionLocal = setup_test_db
    session = TestingSessionLocal()
    user = User(
        id="testuser@example.com",
        email="testuser@example.com",
        password_hash=hash_password("TestPass123"),
        is_verified=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(user)
    session.commit()
    email = user.email
    session.close()
    return email


@pytest.fixture
def auth_headers(test_user):
    """Create authorization headers for test user"""
    token = create_access_token(data={"sub": test_user})
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, client):
        """Test /health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAlertAPI:
    """Test alert management API endpoints with authentication"""

    def test_create_alert_success(self, client, auth_headers):
        """Test creating a new alert"""
        response = client.post("/api/v1/alerts/", json={
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Alert created successfully"
        assert data["alert"]["subreddit"] == "watchexchange"
        assert data["alert"]["keyword"] == "Seiko"
        assert data["alert"]["is_active"] is True

    def test_create_alert_subreddit_normalization(self, client, auth_headers):
        """Test that r/ prefix is removed from subreddit"""
        response = client.post("/api/v1/alerts/", json={
            "subreddit": "r/mechmarket",
            "keyword": "keycaps"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["alert"]["subreddit"] == "mechmarket"  # r/ removed

    def test_create_duplicate_alert(self, client, auth_headers):
        """Test that duplicate alert returns 409"""
        # Create first alert
        client.post("/api/v1/alerts/", json={
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        }, headers=auth_headers)

        # Try to create duplicate
        response = client.post("/api/v1/alerts/", json={
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        }, headers=auth_headers)
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_alert_no_auth(self, client):
        """Test that creating alert without auth returns 401"""
        response = client.post("/api/v1/alerts/", json={
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        })
        assert response.status_code == 401

    def test_list_alerts(self, client, auth_headers):
        """Test listing user alerts"""
        # Create some alerts
        client.post("/api/v1/alerts/", json={
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        }, headers=auth_headers)
        client.post("/api/v1/alerts/", json={
            "subreddit": "mechmarket",
            "keyword": "keycaps"
        }, headers=auth_headers)

        # List alerts
        response = client.get("/api/v1/alerts/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"
        assert data["count"] == 2
        assert len(data["alerts"]) == 2

    def test_list_alerts_empty(self, client, auth_headers):
        """Test listing alerts when user has no alerts"""
        response = client.get("/api/v1/alerts/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert len(data["alerts"]) == 0

    def test_list_alerts_no_auth(self, client):
        """Test that listing alerts without auth returns 401"""
        response = client.get("/api/v1/alerts/")
        assert response.status_code == 401

    def test_delete_alert_success(self, client, auth_headers):
        """Test deleting an alert"""
        # Create alert
        create_response = client.post("/api/v1/alerts/", json={
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        }, headers=auth_headers)
        alert_id = create_response.json()["alert"]["id"]

        # Delete alert
        response = client.delete(f"/api/v1/alerts/{alert_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["message"] == "Alert deleted successfully"

    def test_delete_alert_wrong_owner(self, client, setup_test_db, auth_headers):
        """Test deleting alert with wrong user returns 403"""
        engine, TestingSessionLocal = setup_test_db

        # Create alert for the test user first
        create_response = client.post("/api/v1/alerts/", json={
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        }, headers=auth_headers)
        alert_id = create_response.json()["alert"]["id"]

        # Create another user
        session = TestingSessionLocal()
        other_user = User(
            id="other@example.com",
            email="other@example.com",
            password_hash=hash_password("TestPass123"),
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(other_user)
        session.commit()
        other_email = other_user.email
        session.close()

        # Try to delete with different user's token
        other_token = create_access_token(data={"sub": other_email})
        response = client.delete(
            f"/api/v1/alerts/{alert_id}",
            headers={"Authorization": f"Bearer {other_token}"}
        )
        assert response.status_code == 403
        assert "own alerts" in response.json()["detail"]

    def test_delete_alert_not_found(self, client, auth_headers):
        """Test deleting non-existent alert returns 404"""
        response = client.delete(
            "/api/v1/alerts/fake-uuid",
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_alert_no_auth(self, client):
        """Test that deleting alert without auth returns 401"""
        response = client.delete("/api/v1/alerts/some-id")
        assert response.status_code == 401
