from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
import json
import os

class Settings(BaseSettings):
    # App
    APP_NAME: str = "TradeMaster Pro"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database
    DATABASE_URL: str = "postgresql://trademaster:trademaster123@postgres:5432/trademaster"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None
    FI_CACHE_ONLY: bool = os.getenv("FI_CACHE_ONLY", "false").lower() == "true"
    US_CACHE_ONLY: bool = os.getenv("US_CACHE_ONLY", "false").lower() == "true"
    FI_NEWS_ON_DEMAND: bool = os.getenv("FI_NEWS_ON_DEMAND", "true").lower() == "true"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://frontend:3000"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in raw.split(",") if item.strip()]
        return value

    # API Keys (to be set in .env)
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    TWITTER_API_KEY: str = ""
    TWITTER_API_SECRET: str = ""
    TWITTER_BEARER_TOKEN: str = ""
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "TradeMaster Pro 1.0"

    # Data API Keys
    FINNHUB_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    POLYGON_API_KEY: str = ""
    FRED_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""

    # Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))
    PASSWORD_HASH_ITERATIONS: int = int(os.getenv("PASSWORD_HASH_ITERATIONS", "120000"))
    ADMIN_API_KEY: str = os.getenv("ADMIN_API_KEY", "")

    # Cache TTL settings (in seconds)
    CACHE_TTL_PRICES: int = 60         # 1 min - Real-time prices
    CACHE_TTL_PREDICTIONS: int = 43200   # 12 hours - legacy AI predictions default
    CACHE_TTL_AI_PICKS: int = 43200      # 12 hours - AI picks (reduced from 4 days for fresher data)
    CACHE_TTL_QUICK_WINS: int = 43200    # 12 hours - quick wins (was 24h)
    CACHE_TTL_HIDDEN_GEMS: int = 43200   # 12 hours - hidden gems (reduced from 4 days)
    CACHE_TTL_SOCIAL: int = 300        # 5 min - Social sentiment
    CACHE_TTL_NEWS: int = 600          # 10 min - News articles
    CACHE_TTL_MACRO: int = 300         # 5 min - Macro indicators (reduced from 1h)
    FINNHUB_COMPANY_NEWS_TTL: int = int(os.getenv("FINNHUB_COMPANY_NEWS_TTL", "21600"))
    FINNHUB_MARKET_NEWS_TTL: int = int(os.getenv("FINNHUB_MARKET_NEWS_TTL", "300"))
    FINNHUB_NEWS_LOCK_TTL: int = int(os.getenv("FINNHUB_NEWS_LOCK_TTL", "120"))
    FINNHUB_CALLS_PER_MINUTE: int = int(os.getenv("FINNHUB_CALLS_PER_MINUTE", "60"))
    FINNHUB_RATE_LIMIT_BUFFER: int = int(os.getenv("FINNHUB_RATE_LIMIT_BUFFER", "5"))
    FINNHUB_RATE_LIMIT_MODE: str = os.getenv("FINNHUB_RATE_LIMIT_MODE", "wait")
    FINNHUB_FUNDAMENTALS_FALLBACK: bool = os.getenv("FINNHUB_FUNDAMENTALS_FALLBACK", "true").lower() == "true"
    FINNHUB_FUNDAMENTALS_CORE_ONLY: bool = os.getenv("FINNHUB_FUNDAMENTALS_CORE_ONLY", "true").lower() == "true"

    # Scan/enrichment limits (0 = no limit)
    UNIVERSE_TICKER_LIMIT: int = int(os.getenv("UNIVERSE_TICKER_LIMIT", "0"))
    AI_PICKS_ENRICH_LIMIT: int = int(os.getenv("AI_PICKS_ENRICH_LIMIT", "30"))
    HIDDEN_GEMS_ENRICH_LIMIT: int = int(os.getenv("HIDDEN_GEMS_ENRICH_LIMIT", "40"))
    SECTOR_PICKS_UNIVERSE_LIMIT: int = int(os.getenv("SECTOR_PICKS_UNIVERSE_LIMIT", "150"))

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
