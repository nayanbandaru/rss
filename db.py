# db.py
import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Boolean, Text, DateTime, Float,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from dotenv import load_dotenv
load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./watch.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()

# User DB Model
class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)         # uuid-like string (we'll just use email as id for MVP)
    email = Column(String, unique=True, nullable=False)

# Alert DB Model
class Alert(Base):
    __tablename__ = "alerts"
    id = Column(String, primary_key=True)         # uuid string
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subreddit = Column(Text, nullable=False)
    keyword = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    user = relationship("User")
    __table_args__ = (UniqueConstraint("user_id", "subreddit", "keyword", name="uq_user_sub_kw"),)

class Delivery(Base):
    __tablename__ = "deliveries"
    id = Column(String, primary_key=True)         # uuid string
    alert_id = Column(String, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    reddit_post_id = Column(String, nullable=False)
    delivered_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("alert_id", "reddit_post_id", name="uq_alert_post"),)

class Checkpoint(Base):
    __tablename__ = "checkpoints"
    subreddit = Column(Text, primary_key=True)
    keyword = Column(Text, primary_key=True)
    last_seen_created_utc = Column(Float, nullable=False, default=0.0)

def init_db():
    Base.metadata.create_all(engine)
    return SessionLocal
