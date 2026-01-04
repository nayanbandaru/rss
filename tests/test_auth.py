"""
Tests for authentication endpoints and functionality.
"""
import pytest
from datetime import datetime, timedelta

from db import User, PasswordResetToken
from app.utils.security import (
    hash_password,
    verify_password,
    validate_password,
    create_access_token,
    decode_access_token,
    generate_reset_token
)


class TestPasswordUtilities:
    """Tests for password hashing and validation utilities."""

    def test_hash_password(self):
        """Test password hashing produces different hash than input."""
        password = "TestPass123"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test verifying correct password returns True."""
        password = "TestPass123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password returns False."""
        password = "TestPass123"
        hashed = hash_password(password)
        assert verify_password("WrongPassword", hashed) is False

    def test_validate_password_valid(self):
        """Test valid password passes validation."""
        is_valid, error = validate_password("TestPass123")
        assert is_valid is True
        assert error is None

    def test_validate_password_too_short(self):
        """Test password less than 8 characters fails."""
        is_valid, error = validate_password("Pass1")
        assert is_valid is False
        assert "8 characters" in error

    def test_validate_password_no_uppercase(self):
        """Test password without uppercase fails."""
        is_valid, error = validate_password("testpass123")
        assert is_valid is False
        assert "uppercase" in error

    def test_validate_password_no_lowercase(self):
        """Test password without lowercase fails."""
        is_valid, error = validate_password("TESTPASS123")
        assert is_valid is False
        assert "lowercase" in error

    def test_validate_password_no_digit(self):
        """Test password without digit fails."""
        is_valid, error = validate_password("TestPassABC")
        assert is_valid is False
        assert "digit" in error


class TestJWTUtilities:
    """Tests for JWT token utilities."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        token = create_access_token(data={"sub": "test@example.com"})
        assert token is not None
        assert len(token) > 0

    def test_decode_access_token_valid(self):
        """Test decoding valid JWT token."""
        email = "test@example.com"
        token = create_access_token(data={"sub": email})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload.get("sub") == email

    def test_decode_access_token_invalid(self):
        """Test decoding invalid JWT token returns None."""
        payload = decode_access_token("invalid.token.here")
        assert payload is None

    def test_decode_access_token_expired(self):
        """Test decoding expired JWT token returns None."""
        token = create_access_token(
            data={"sub": "test@example.com"},
            expires_delta=timedelta(seconds=-1)
        )
        payload = decode_access_token(token)
        assert payload is None

    def test_generate_reset_token(self):
        """Test reset token generation."""
        token1 = generate_reset_token()
        token2 = generate_reset_token()
        assert token1 != token2
        assert len(token1) > 20


class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    def test_register_new_user(self, client):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "NewPass123"
        })
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_register_weak_password(self, client):
        """Test registration with weak password fails (422 for pydantic validation)."""
        response = client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "password": "weak"
        })
        # Pydantic validates min_length=8, returns 422
        assert response.status_code == 422

    def test_register_duplicate_with_password(self, client, sample_user_with_password):
        """Test registration fails for user that already has password."""
        response = client.post("/api/v1/auth/register", json={
            "email": "auth@example.com",
            "password": "NewPass123"
        })
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    def test_login_success(self, client, sample_user_with_password):
        """Test successful login."""
        response = client.post("/api/v1/auth/login", json={
            "email": "auth@example.com",
            "password": "TestPass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, sample_user_with_password):
        """Test login with wrong password fails."""
        response = client.post("/api/v1/auth/login", json={
            "email": "auth@example.com",
            "password": "WrongPassword123"
        })
        assert response.status_code == 401
        assert "Invalid" in response.json()["detail"] or "Incorrect" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login for non-existent user fails."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "SomePass123"
        })
        assert response.status_code == 401

    def test_login_user_without_password(self, client, TestSessionLocal):
        """Test login for user without password returns 403."""
        # Create a user without password
        from db import User
        session = TestSessionLocal()
        user = User(
            id="nopass@example.com",
            email="nopass@example.com",
            password_hash=None,
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(user)
        session.commit()
        session.close()

        response = client.post("/api/v1/auth/login", json={
            "email": "nopass@example.com",
            "password": "SomePass123"
        })
        assert response.status_code == 403
        assert "password" in response.json()["detail"].lower()

    def test_setup_password_for_existing_user(self, client, TestSessionLocal):
        """Test setting password for existing user without password."""
        # Create a user without password
        from db import User
        session = TestSessionLocal()
        user = User(
            id="setup@example.com",
            email="setup@example.com",
            password_hash=None,
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(user)
        session.commit()
        session.close()

        response = client.post("/api/v1/auth/setup-password", json={
            "email": "setup@example.com",
            "password": "NewPass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_setup_password_already_set(self, client, sample_user_with_password):
        """Test setup password fails if user already has password."""
        response = client.post("/api/v1/auth/setup-password", json={
            "email": "auth@example.com",
            "password": "AnotherPass123"
        })
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    def test_setup_password_nonexistent_user(self, client):
        """Test setup password fails for non-existent user."""
        response = client.post("/api/v1/auth/setup-password", json={
            "email": "nonexistent@example.com",
            "password": "NewPass123"
        })
        assert response.status_code == 404

    def test_get_me_authenticated(self, client, sample_user_with_password, auth_headers):
        """Test /me endpoint with valid token."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "auth@example.com"
        assert data["has_password"] is True

    def test_get_me_no_token(self, client):
        """Test /me endpoint without token returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        """Test /me endpoint with invalid token returns 401."""
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 401

    def test_forgot_password_existing_user(self, client, sample_user_with_password):
        """Test forgot password endpoint (always returns success)."""
        response = client.post("/api/v1/auth/forgot-password", json={
            "email": "auth@example.com"
        })
        assert response.status_code == 200
        # Should not reveal if user exists
        assert "message" in response.json()

    def test_forgot_password_nonexistent_user(self, client):
        """Test forgot password for non-existent user (still returns success)."""
        response = client.post("/api/v1/auth/forgot-password", json={
            "email": "nonexistent@example.com"
        })
        assert response.status_code == 200
        # Should not reveal if user exists


class TestProtectedAlertEndpoints:
    """Tests for protected alert endpoints requiring authentication."""

    def test_create_alert_authenticated(self, client, sample_user_with_password, auth_headers):
        """Test creating alert with valid auth."""
        response = client.post("/api/v1/alerts/", json={
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert "alert" in data
        assert data["alert"]["subreddit"] == "watchexchange"
        assert data["alert"]["keyword"] == "Seiko"

    def test_create_alert_no_auth(self, client):
        """Test creating alert without auth returns 401."""
        response = client.post("/api/v1/alerts/", json={
            "subreddit": "watchexchange",
            "keyword": "Seiko"
        })
        assert response.status_code == 401

    def test_list_alerts_authenticated(self, client, sample_user_with_password, auth_headers):
        """Test listing alerts with valid auth."""
        # First create an alert
        client.post("/api/v1/alerts/", json={
            "subreddit": "mechmarket",
            "keyword": "keyboard"
        }, headers=auth_headers)

        response = client.get("/api/v1/alerts/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert data["count"] >= 1

    def test_list_alerts_no_auth(self, client):
        """Test listing alerts without auth returns 401."""
        response = client.get("/api/v1/alerts/")
        assert response.status_code == 401

    def test_delete_alert_authenticated(self, client, sample_user_with_password, auth_headers):
        """Test deleting own alert with valid auth."""
        # First create an alert
        create_response = client.post("/api/v1/alerts/", json={
            "subreddit": "watchexchange",
            "keyword": "delete-test"
        }, headers=auth_headers)
        alert_id = create_response.json()["alert"]["id"]

        # Delete it
        response = client.delete(f"/api/v1/alerts/{alert_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_delete_alert_no_auth(self, client):
        """Test deleting alert without auth returns 401."""
        response = client.delete("/api/v1/alerts/some-id")
        assert response.status_code == 401

    def test_delete_alert_not_owner(self, client, TestSessionLocal):
        """Test deleting alert owned by another user returns 403."""
        from db import User, Alert
        import uuid

        session = TestSessionLocal()

        # Create two users
        user1 = User(
            id="user1@example.com",
            email="user1@example.com",
            password_hash=hash_password("TestPass123"),
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        user2 = User(
            id="user2@example.com",
            email="user2@example.com",
            password_hash=hash_password("TestPass123"),
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(user1)
        session.add(user2)
        session.commit()

        # Create alert for user1
        alert = Alert(
            id=str(uuid.uuid4()),
            user_id=user1.id,
            subreddit="test",
            keyword="test",
            is_active=True
        )
        session.add(alert)
        session.commit()

        # Store values before closing session
        alert_id = alert.id
        user2_email = user2.email
        session.close()

        # Try to delete with user2's token
        token2 = create_access_token(data={"sub": user2_email})
        response = client.delete(
            f"/api/v1/alerts/{alert_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response.status_code == 403


class TestUserModel:
    """Tests for User model with auth fields."""

    def test_user_with_password(self, test_session):
        """Test creating user with password fields."""
        user = User(
            id="model@example.com",
            email="model@example.com",
            password_hash=hash_password("TestPass123"),
            is_verified=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_session.add(user)
        test_session.commit()

        fetched = test_session.query(User).filter(User.email == "model@example.com").first()
        assert fetched is not None
        assert fetched.password_hash is not None
        assert fetched.is_verified is True

    def test_user_without_password(self, test_session):
        """Test creating user without password (legacy)."""
        user = User(
            id="legacy@example.com",
            email="legacy@example.com",
            password_hash=None,
            is_verified=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        test_session.add(user)
        test_session.commit()

        fetched = test_session.query(User).filter(User.email == "legacy@example.com").first()
        assert fetched is not None
        assert fetched.password_hash is None


class TestPasswordResetTokenModel:
    """Tests for PasswordResetToken model."""

    def test_create_reset_token(self, test_session, sample_user):
        """Test creating password reset token."""
        token = PasswordResetToken(
            id="reset-token-id",
            user_id=sample_user.id,
            token=generate_reset_token(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            used=False,
            created_at=datetime.utcnow()
        )
        test_session.add(token)
        test_session.commit()

        fetched = test_session.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == sample_user.id
        ).first()
        assert fetched is not None
        assert fetched.used is False
