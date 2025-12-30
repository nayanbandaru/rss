import pytest
from datetime import datetime
from db import User, Alert, Delivery, Checkpoint

class TestUserModel:
    """Test cases for User model"""

    def test_create_user(self, test_session):
        """Test creating a user"""
        user = User(id="user1@test.com", email="user1@test.com")
        test_session.add(user)
        test_session.commit()

        retrieved = test_session.query(User).filter(User.id == "user1@test.com").first()
        assert retrieved is not None
        assert retrieved.email == "user1@test.com"

    def test_user_email_unique(self, test_session, sample_user):
        """Test that email must be unique"""
        duplicate_user = User(id="different-id", email=sample_user.email)
        test_session.add(duplicate_user)

        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            test_session.commit()

class TestAlertModel:
    """Test cases for Alert model"""

    def test_create_alert(self, test_session, sample_user):
        """Test creating an alert"""
        alert = Alert(
            id="alert-1",
            user_id=sample_user.id,
            subreddit="watchexchange",
            keyword="Seiko",
            is_active=True
        )
        test_session.add(alert)
        test_session.commit()

        retrieved = test_session.query(Alert).filter(Alert.id == "alert-1").first()
        assert retrieved is not None
        assert retrieved.subreddit == "watchexchange"
        assert retrieved.keyword == "Seiko"
        assert retrieved.is_active is True

    def test_alert_unique_constraint(self, test_session, sample_alert):
        """Test that (user_id, subreddit, keyword) must be unique"""
        duplicate_alert = Alert(
            id="different-alert-id",
            user_id=sample_alert.user_id,
            subreddit=sample_alert.subreddit,
            keyword=sample_alert.keyword,
            is_active=True
        )
        test_session.add(duplicate_alert)

        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            test_session.commit()

    def test_toggle_alert_active(self, test_session, sample_alert):
        """Test toggling alert active status"""
        assert sample_alert.is_active is True

        sample_alert.is_active = False
        test_session.commit()

        retrieved = test_session.query(Alert).filter(Alert.id == sample_alert.id).first()
        assert retrieved.is_active is False

class TestDeliveryModel:
    """Test cases for Delivery model"""

    def test_create_delivery(self, test_session, sample_alert):
        """Test creating a delivery record"""
        delivery = Delivery(
            id="delivery-1",
            alert_id=sample_alert.id,
            reddit_post_id="post123",
            delivered_at=datetime.utcnow()
        )
        test_session.add(delivery)
        test_session.commit()

        retrieved = test_session.query(Delivery).filter(Delivery.id == "delivery-1").first()
        assert retrieved is not None
        assert retrieved.reddit_post_id == "post123"

    def test_delivery_unique_constraint(self, test_session, sample_alert):
        """Test that (alert_id, reddit_post_id) must be unique"""
        delivery1 = Delivery(
            id="delivery-1",
            alert_id=sample_alert.id,
            reddit_post_id="post123",
            delivered_at=datetime.utcnow()
        )
        test_session.add(delivery1)
        test_session.commit()

        delivery2 = Delivery(
            id="delivery-2",
            alert_id=sample_alert.id,
            reddit_post_id="post123",  # Same post, same alert
            delivered_at=datetime.utcnow()
        )
        test_session.add(delivery2)

        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            test_session.commit()

class TestCheckpointModel:
    """Test cases for Checkpoint model"""

    def test_create_checkpoint(self, test_session):
        """Test creating a checkpoint"""
        checkpoint = Checkpoint(
            subreddit="watchexchange",
            keyword="Seiko",
            last_seen_created_utc=1234567890.0
        )
        test_session.add(checkpoint)
        test_session.commit()

        retrieved = test_session.get(Checkpoint, {"subreddit": "watchexchange", "keyword": "Seiko"})
        assert retrieved is not None
        assert retrieved.last_seen_created_utc == 1234567890.0

    def test_update_checkpoint(self, test_session):
        """Test updating checkpoint timestamp"""
        checkpoint = Checkpoint(
            subreddit="watchexchange",
            keyword="Seiko",
            last_seen_created_utc=1234567890.0
        )
        test_session.add(checkpoint)
        test_session.commit()

        checkpoint.last_seen_created_utc = 1234567900.0
        test_session.commit()

        retrieved = test_session.get(Checkpoint, {"subreddit": "watchexchange", "keyword": "Seiko"})
        assert retrieved.last_seen_created_utc == 1234567900.0
