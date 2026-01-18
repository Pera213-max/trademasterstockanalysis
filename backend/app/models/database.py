from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from app.config.settings import settings

# Database engine
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    ticker = Column(String, index=True, nullable=False)
    asset_type = Column("type", String, default="stock", nullable=False)
    notes = Column(Text, nullable=True)
    added_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "ticker", "type", name="uq_watchlist_user_ticker_type"),
    )

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    symbol = Column(String, index=True)
    trade_type = Column(String)  # buy/sell
    quantity = Column(Float)
    price = Column(Float)
    total_value = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True)
    total_value = Column(Float, default=0.0)
    cash_balance = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FiNewsEvent(Base):
    __tablename__ = "fi_news_events"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=True)
    company = Column(String, nullable=True)
    event_type = Column(String, index=True, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    source = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    published_at = Column(DateTime, index=True, nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    content_hash = Column(String(64), unique=True, index=True, nullable=False)
    raw_payload = Column(JSON, nullable=True)
    analysis = Column(JSON, nullable=True)
    impact = Column(String, nullable=True)
    sentiment = Column(String, nullable=True)
    analysis_provider = Column(String, nullable=True)
    analysis_model = Column(String, nullable=True)
    analysis_language = Column(String, nullable=True)
    analyzed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_fi_news_events_content_hash"),
    )


class FiFundamentalSnapshot(Base):
    __tablename__ = "fi_fundamental_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    snapshot_at = Column(DateTime, default=datetime.utcnow, index=True)
    data = Column(JSON, nullable=False)
    data_hash = Column(String(64), index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("ticker", "data_hash", name="uq_fi_fundamental_snapshot_hash"),
    )


class FiAiInsight(Base):
    __tablename__ = "fi_ai_insights"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    insight_type = Column(String, index=True, nullable=False)  # FUNDAMENTALS, NEWS, INSIDER, SHORTS
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    bullets = Column(JSON, nullable=True)
    impact = Column(String, nullable=True)
    sentiment = Column(String, nullable=True)
    key_metrics = Column(JSON, nullable=True)
    risks = Column(JSON, nullable=True)
    watch_items = Column(JSON, nullable=True)
    raw_analysis = Column(JSON, nullable=True)
    source_hash = Column(String(64), index=True, nullable=True)
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    language = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint("ticker", "insight_type", "source_hash", name="uq_fi_ai_insight_source"),
    )


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)
