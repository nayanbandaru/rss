import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db import Base, User, Alert, Delivery, Checkpoint

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def test_engine():
    """Create a test database engine"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture
def test_session(test_engine):
    """Create a test database session"""
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    session = TestSessionLocal()
    yield session
    session.close()

@pytest.fixture
def sample_user(test_session):
    """Create a sample user for testing"""
    user = User(id="test@example.com", email="test@example.com")
    test_session.add(user)
    test_session.commit()
    return user

@pytest.fixture
def sample_alert(test_session, sample_user):
    """Create a sample alert for testing"""
    alert = Alert(
        id="test-alert-id",
        user_id=sample_user.id,
        subreddit="testsubreddit",
        keyword="test keyword",
        is_active=True
    )
    test_session.add(alert)
    test_session.commit()
    return alert
