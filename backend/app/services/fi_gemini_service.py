"""
Finnish Daily Market Summary Service using Google Gemini API.

Generates AI-powered daily market summaries after Helsinki market close.
Summaries are stored in Redis with date-based keys for historical access.
"""

from __future__ import annotations

import json
import logging
import os
import redis
from datetime import datetime, date
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

HELSINKI_TZ = ZoneInfo("Europe/Helsinki")

# Redis key pattern for daily summaries
REDIS_KEY_PREFIX = "fi:daily_summary:"

try:
    import google.generativeai as genai
except ImportError:
    genai = None
    logger.warning("google-generativeai not installed")


class FiGeminiService:
    """Service for generating daily market summaries using Gemini API."""

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
        self._model = None

        # Redis connection
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self._redis = redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning("Redis connection failed: %s", e)
            self._redis = None

        if self.api_key and genai is not None:
            try:
                genai.configure(api_key=self.api_key)
                self._model = genai.GenerativeModel(self.model_name)
                logger.info("Gemini service initialized with model: %s", self.model_name)
            except Exception as e:
                logger.warning("Gemini init failed: %s", e)

    def is_enabled(self) -> bool:
        """Check if Gemini API is configured and available."""
        return bool(self._model)

    def _get_redis_key(self, summary_date: date) -> str:
        """Get Redis key for a specific date."""
        return f"{REDIS_KEY_PREFIX}{summary_date.isoformat()}"

    def get_summary(self, summary_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """
        Get daily summary for a specific date.
        
        Args:
            summary_date: Date for summary (default: today in Helsinki time)
            
        Returns:
            Summary dict or None if not found
        """
        if not self._redis:
            return None
            
        if summary_date is None:
            summary_date = datetime.now(HELSINKI_TZ).date()
            
        key = self._get_redis_key(summary_date)
        try:
            data = self._redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error("Failed to get summary from Redis: %s", e)
        return None

    def get_latest_summary(self) -> Optional[Dict[str, Any]]:
        """Get the most recent summary available."""
        if not self._redis:
            return None
            
        # Try today first
        today = datetime.now(HELSINKI_TZ).date()
        summary = self.get_summary(today)
        if summary:
            return summary
            
        # Try yesterday
        from datetime import timedelta
        yesterday = today - timedelta(days=1)
        return self.get_summary(yesterday)

    def generate_daily_summary(self, force: bool = False) -> Optional[Dict[str, Any]]:
        """
        Generate daily market summary using Gemini API.
        
        Args:
            force: If True, regenerate even if summary exists
            
        Returns:
            Generated summary dict or None on failure
        """
        if not self.is_enabled():
            logger.warning("Gemini API not configured, skipping summary generation")
            return None

        today = datetime.now(HELSINKI_TZ).date()
        
        # Check if already generated
        if not force:
            existing = self.get_summary(today)
            if existing:
                logger.info("Summary already exists for %s", today)
                return existing

        # Collect market data
        market_data = self._collect_market_data()
        if not market_data:
            logger.error("Failed to collect market data")
            return None

        # Generate summary with Gemini
        summary = self._generate_with_gemini(market_data, today)
        if not summary:
            return None

        # Store in Redis
        self._store_summary(today, summary)
        
        return summary

    def _collect_market_data(self) -> Optional[Dict[str, Any]]:
        """Collect all market data needed for summary generation."""
        try:
            from app.services.fi_data import get_fi_data_service
            from app.services.fi_macro_service import get_fi_macro_service
            from app.services.fi_event_service import get_fi_event_service

            fi_service = get_fi_data_service()
            macro_service = get_fi_macro_service()
            event_service = get_fi_event_service()

            # Get movers (top gainers/losers)
            movers = fi_service.get_movers(limit=5)
            
            # Get macro indicators
            macro = macro_service.get_macro_indicators()
            
            # Get significant events
            events = event_service.get_significant_events(days=1, limit=5)
            
            # Get sectors summary
            sectors = fi_service.get_sectors_summary()

            return {
                "gainers": movers.get("gainers", [])[:5],
                "losers": movers.get("losers", [])[:5],
                "macro": macro,
                "events": events,
                "sectors": sectors[:5] if sectors else [],
            }
        except Exception as e:
            logger.error("Failed to collect market data: %s", e)
            return None

    def _generate_with_gemini(self, market_data: Dict[str, Any], summary_date: date) -> Optional[Dict[str, Any]]:
        """Generate summary using Gemini API."""
        if not self._model:
            return None

        # Format data for prompt
        gainers_text = "\n".join([
            f"- {g.get('ticker', '').replace('.HE', '')}: {g.get('name', '')} (+{g.get('changePercent', 0):.2f}%)"
            for g in market_data.get("gainers", [])
        ])
        
        losers_text = "\n".join([
            f"- {l.get('ticker', '').replace('.HE', '')}: {l.get('name', '')} ({l.get('changePercent', 0):.2f}%)"
            for l in market_data.get("losers", [])
        ])
        
        events_text = "\n".join([
            f"- {e.get('ticker', '').replace('.HE', '')}: {e.get('title', '')}"
            for e in market_data.get("events", [])[:3]
        ]) or "Ei merkittäviä tiedotteita."

        # Get OMXH25 from macro
        omxh25_change = None
        macro = market_data.get("macro", {})
        indices = macro.get("indices", []) if macro else []
        for idx in indices:
            if "OMXH25" in idx.get("code", "") or "Helsinki" in idx.get("name", ""):
                omxh25_change = idx.get("changePercent")
                break

        prompt = f"""Olet suomalaisen osakemarkkinan analyytikko. Kirjoita lyhyt ja ytimekäs päivän markkinakatsaus suomeksi.

PÄIVÄMÄÄRÄ: {summary_date.strftime('%d.%m.%Y')}

PÄIVÄN NOUSIJAT:
{gainers_text or "Ei merkittäviä nousuja."}

PÄIVÄN LASKIJAT:
{losers_text or "Ei merkittäviä laskuja."}

TIEDOTTEET:
{events_text}

OMXH25 MUUTOS: {f"{omxh25_change:+.2f}%" if omxh25_change else "Ei saatavilla"}

Kirjoita 2-3 kappaleen tiivistelmä päivästä. Mainitse:
1. Yleiskuva markkinatilanteesta
2. Merkittävimmät liikkujat ja syyt jos tiedossa
3. Mielenkiintoiset havainnot

Pidä teksti ammattimaisena mutta helppolukuisena. Maksimipituus 200 sanaa."""

        try:
            response = self._model.generate_content(prompt)
            summary_text = response.text if response else None
            
            if not summary_text:
                return None

            now = datetime.now(HELSINKI_TZ)
            
            return {
                "date": summary_date.isoformat(),
                "summary": summary_text.strip(),
                "gainers": market_data.get("gainers", [])[:3],
                "losers": market_data.get("losers", [])[:3],
                "generated_at": now.isoformat(),
                "next_update": "19:00",
                "model": self.model_name,
            }
        except Exception as e:
            logger.error("Gemini generation failed: %s", e)
            return None

    def _store_summary(self, summary_date: date, summary: Dict[str, Any]) -> bool:
        """Store summary in Redis with 30-day expiry."""
        if not self._redis:
            return False
            
        key = self._get_redis_key(summary_date)
        try:
            self._redis.set(key, json.dumps(summary, ensure_ascii=False), ex=30*24*60*60)  # 30 days
            logger.info("Stored daily summary for %s", summary_date)
            return True
        except Exception as e:
            logger.error("Failed to store summary: %s", e)
            return False

    def get_available_dates(self, limit: int = 14) -> list:
        """Get list of dates with available summaries."""
        if not self._redis:
            return []
            
        try:
            pattern = f"{REDIS_KEY_PREFIX}*"
            keys = self._redis.keys(pattern)
            dates = [k.replace(REDIS_KEY_PREFIX, "") for k in keys]
            dates.sort(reverse=True)
            return dates[:limit]
        except Exception as e:
            logger.error("Failed to get available dates: %s", e)
            return []


# Singleton
_service: Optional[FiGeminiService] = None


def get_fi_gemini_service() -> FiGeminiService:
    """Get singleton instance of FiGeminiService."""
    global _service
    if _service is None:
        _service = FiGeminiService()
    return _service
