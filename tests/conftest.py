import pytest
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from db import Base, User, Alert, Delivery, Checkpoint, PasswordResetToken
from app.dependencies import get_db
from app.utils.security import hash_password, create_access_token

# Use a file-based test database to avoid issues with in-memory database
TEST_DATABASE_PATH = "/tmp/test_rss.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DATABASE_PATH}"


@pytest.fixture(scope="function")
def test_engine():
    """Create a test database engine"""
    # Remove old test database if exists
    if os.path.exists(TEST_DATABASE_PATH):
        os.remove(TEST_DATABASE_PATH)

    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

    # Cleanup
    if os.path.exists(TEST_DATABASE_PATH):
        os.remove(TEST_DATABASE_PATH)


@pytest.fixture(scope="function")
def TestSessionLocal(test_engine):
    """Create a session factory bound to the test engine"""
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="function")
def test_session(TestSessionLocal):
    """Create a test database session for direct DB tests"""
    session = TestSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(test_engine, TestSessionLocal):
    """Create a test client with overridden database dependency"""
    from app.main import app

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# =============================================================================
# Fixtures for direct DB tests (test_db.py) - return actual ORM objects
# =============================================================================

@pytest.fixture
def sample_user(test_session):
    """Create a sample user for direct DB testing.
    Returns actual ORM object bound to test_session.
    """
    user = User(
        id="test@example.com",
        email="test@example.com",
        password_hash=None,
        is_verified=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture
def sample_alert(test_session, sample_user):
    """Create a sample alert for direct DB testing.
    Returns actual ORM object bound to test_session.
    """
    alert = Alert(
        id="test-alert-id",
        user_id=sample_user.id,
        subreddit="testsubreddit",
        keyword="test keyword",
        is_active=True
    )
    test_session.add(alert)
    test_session.commit()
    test_session.refresh(alert)
    return alert


# =============================================================================
# Fixtures for API tests (test_auth.py, test_api.py) - create user in shared DB
# =============================================================================

@pytest.fixture
def sample_user_with_password(TestSessionLocal, test_engine):
    """Create a sample user with password for API testing.
    Creates user in shared DB so it's accessible via client requests.
    """
    session = TestSessionLocal()
    user = User(
        id="auth@example.com",
        email="auth@example.com",
        password_hash=hash_password("TestPass123"),
        is_verified=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(user)
    session.commit()

    # Return a simple namespace with user data
    class UserData:
        pass
    user_data = UserData()
    user_data.id = user.id
    user_data.email = user.email
    user_data.password_hash = user.password_hash
    user_data.is_verified = user.is_verified
    session.close()
    return user_data


@pytest.fixture
def auth_token(sample_user_with_password):
    """Create a valid JWT token for the sample user with password"""
    return create_access_token(data={"sub": sample_user_with_password.email})


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers with valid token"""
    return {"Authorization": f"Bearer {auth_token}"}
