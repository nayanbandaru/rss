import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.dependencies import get_db
from db import Base

# Test database setup
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    """Override database dependency for testing"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create tables before any tests run
Base.metadata.create_all(bind=engine)

# Override dependency
app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self):
        """Test /health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAlertAPI:
    """Test alert management API endpoints"""

    def test_create_alert_success(self):
        """Test creating a new alert"""
        response = client.post("/api/v1/alerts/", json={
            "email": "test@example.com",
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Alert created successfully"
        assert data["alert"]["subreddit"] == "watchexchange"
        assert data["alert"]["keyword"] == "Seiko"
        assert data["alert"]["is_active"] is True

    def test_create_alert_subreddit_normalization(self):
        """Test that r/ prefix is removed from subreddit"""
        response = client.post("/api/v1/alerts/", json={
            "email": "test2@example.com",
            "subreddit": "r/mechmarket",
            "keyword": "keycaps"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["alert"]["subreddit"] == "mechmarket"  # r/ removed

    def test_create_duplicate_alert(self):
        """Test that duplicate alert returns 409"""
        # Create first alert
        client.post("/api/v1/alerts/", json={
            "email": "test3@example.com",
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        })

        # Try to create duplicate
        response = client.post("/api/v1/alerts/", json={
            "email": "test3@example.com",
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        })
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_alert_invalid_email(self):
        """Test that invalid email returns 422"""
        response = client.post("/api/v1/alerts/", json={
            "email": "not-an-email",
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        })
        assert response.status_code == 422  # Pydantic validation error

    def test_list_alerts(self):
        """Test listing user alerts"""
        # Create some alerts
        client.post("/api/v1/alerts/", json={
            "email": "test4@example.com",
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        })
        client.post("/api/v1/alerts/", json={
            "email": "test4@example.com",
            "subreddit": "mechmarket",
            "keyword": "keycaps"
        })

        # List alerts
        response = client.get("/api/v1/alerts/?email=test4@example.com")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test4@example.com"
        assert data["count"] == 2
        assert len(data["alerts"]) == 2

    def test_list_alerts_empty(self):
        """Test listing alerts for user with no alerts"""
        response = client.get("/api/v1/alerts/?email=nonexistent@example.com")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert len(data["alerts"]) == 0

    def test_delete_alert_success(self):
        """Test deleting an alert"""
        # Create alert
        create_response = client.post("/api/v1/alerts/", json={
            "email": "test5@example.com",
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        })
        alert_id = create_response.json()["alert"]["id"]

        # Delete alert
        response = client.delete(
            f"/api/v1/alerts/{alert_id}?email=test5@example.com"
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Alert deleted successfully"

    def test_delete_alert_wrong_owner(self):
        """Test deleting alert with wrong email returns 403"""
        # Create alert
        create_response = client.post("/api/v1/alerts/", json={
            "email": "test6@example.com",
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        })
        alert_id = create_response.json()["alert"]["id"]

        # Try to delete with different email
        response = client.delete(
            f"/api/v1/alerts/{alert_id}?email=different@example.com"
        )
        assert response.status_code == 403
        assert "own alerts" in response.json()["detail"]

    def test_delete_alert_not_found(self):
        """Test deleting non-existent alert returns 404"""
        response = client.delete(
            "/api/v1/alerts/fake-uuid?email=test@example.com"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
