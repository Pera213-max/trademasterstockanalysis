"""
Finnish fundamentals insight service.

Creates daily fundamental snapshots and generates LLM insights only
when changes are significant. Uses OpenAI + Claude via FiLLMAnalyzer.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.models.database import SessionLocal, FiAiInsight, FiFundamentalSnapshot
from app.services.fi_llm_service import FiLLMAnalyzer
from app.services.fi_ticker_lookup import lookup_company
from database.redis.config import get_redis_cache

logger = logging.getLogger(__name__)


@contextmanager
def _db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _hash_payload(payload: Dict[str, Any]) -> str:
    raw = "|".join([f"{k}:{payload.get(k)}" for k in sorted(payload.keys())])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        num = float(value)
        if math.isfinite(num):
            return num
    except Exception:
        return None
    return None


class FiInsightService:
    def __init__(self) -> None:
        self.llm = FiLLMAnalyzer()
        self.redis_cache = get_redis_cache()
        self.daily_limit = int(os.getenv("FI_LLM_DAILY_LIMIT", "30"))
        self.max_insights_per_run = int(os.getenv("FI_FUNDAMENTAL_INSIGHTS_PER_RUN", "20"))

    def generate_fundamental_insights(self, tickers: List[str]) -> int:
        """
        Generate fundamental insights for tickers (daily batch).
        Returns number of insights created.
        """
        created = 0
        for ticker in tickers:
            if created >= self.max_insights_per_run:
                break
            try:
                result = self.generate_for_ticker(ticker)
                if result:
                    created += 1
            except Exception as exc:
                logger.debug("Insight generation failed for %s: %s", ticker, exc)
        return created

    def generate_for_ticker(self, ticker: str) -> Optional[FiAiInsight]:
        ticker = (ticker or "").upper()
        if not ticker:
            return None

        snapshot, previous = self._store_snapshot(ticker)
        if not snapshot:
            return None

        if not previous:
            return None

        diff = self._diff_snapshots(previous.data, snapshot.data)
        if not diff or not self._is_significant(diff):
            return None

        if not self._llm_budget_ok():
            logger.info("LLM daily budget exceeded; skipping %s", ticker)
            return None

        analysis = self._analyze_diff(ticker, diff)
        if not analysis:
            return None

        return self._store_insight(ticker, analysis, snapshot.data_hash)

    def get_latest_insight(self, ticker: str, insight_type: str = "FUNDAMENTALS") -> Optional[Dict[str, Any]]:
        with _db_session() as db:
            insight = (
                db.query(FiAiInsight)
                .filter(FiAiInsight.ticker == ticker.upper())
                .filter(FiAiInsight.insight_type == insight_type)
                .order_by(FiAiInsight.created_at.desc())
                .first()
            )
        if not insight:
            return None
        return {
            "id": insight.id,
            "ticker": insight.ticker,
            "insight_type": insight.insight_type,
            "title": insight.title,
            "summary": insight.summary,
            "bullets": insight.bullets or [],
            "impact": insight.impact,
            "sentiment": insight.sentiment,
            "key_metrics": insight.key_metrics or [],
            "risks": insight.risks or [],
            "watch_items": insight.watch_items or [],
            "provider": insight.provider,
            "model": insight.model,
            "language": insight.language,
            "created_at": insight.created_at.isoformat() if insight.created_at else None,
        }

    def _store_snapshot(self, ticker: str) -> tuple[Optional[FiFundamentalSnapshot], Optional[FiFundamentalSnapshot]]:
        from app.services.fi_data import get_fi_data_service

        fi_service = get_fi_data_service()
        fundamentals = fi_service.get_fundamentals(ticker)
        metrics = fi_service.compute_metrics(fi_service.get_history(ticker, range="1y", interval="1d") or [])

        if not fundamentals:
            return None, None

        snapshot_data = {
            "ticker": ticker,
            "marketCap": _safe_float(fundamentals.get("marketCap")),
            "peRatio": _safe_float(fundamentals.get("peRatio")),
            "forwardPE": _safe_float(fundamentals.get("forwardPE")),
            "priceToBook": _safe_float(fundamentals.get("priceToBook")),
            "dividendYield": _safe_float(fundamentals.get("dividendYield")),
            "profitMargins": _safe_float(fundamentals.get("profitMargins")),
            "revenueGrowth": _safe_float(fundamentals.get("revenueGrowth")),
            "earningsGrowth": _safe_float(fundamentals.get("earningsGrowth")),
            "returnOnEquity": _safe_float(fundamentals.get("returnOnEquity")),
            "debtToEquity": _safe_float(fundamentals.get("debtToEquity")),
            "beta": _safe_float(fundamentals.get("beta")),
            "volatility": _safe_float(metrics.get("volatility")),
            "return12m": _safe_float(metrics.get("return12m")),
        }

        data_hash = _hash_payload(snapshot_data)

        with _db_session() as db:
            previous = (
                db.query(FiFundamentalSnapshot)
                .filter(FiFundamentalSnapshot.ticker == ticker)
                .order_by(FiFundamentalSnapshot.snapshot_at.desc())
                .first()
            )

            if previous and previous.data_hash == data_hash:
                return previous, previous

            snapshot = FiFundamentalSnapshot(
                ticker=ticker,
                data=snapshot_data,
                data_hash=data_hash,
                snapshot_at=datetime.utcnow(),
            )
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)
            return snapshot, previous

    def _diff_snapshots(self, old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        diff: Dict[str, Dict[str, float]] = {}
        for key in new.keys():
            old_val = _safe_float(old.get(key))
            new_val = _safe_float(new.get(key))
            if old_val is None or new_val is None:
                continue
            if old_val == 0 and new_val == 0:
                continue
            change = new_val - old_val
            pct = None
            if old_val != 0:
                pct = (change / old_val) * 100
            diff[key] = {"old": old_val, "new": new_val, "change": change, "pct": pct}
        return diff

    def _is_significant(self, diff: Dict[str, Dict[str, float]]) -> bool:
        thresholds = {
            "marketCap": 10.0,
            "peRatio": 20.0,
            "forwardPE": 20.0,
            "priceToBook": 20.0,
            "dividendYield": 20.0,
            "profitMargins": 10.0,
            "revenueGrowth": 15.0,
            "earningsGrowth": 15.0,
            "returnOnEquity": 15.0,
            "debtToEquity": 20.0,
            "beta": 10.0,
            "return12m": 15.0,
            "volatility": 15.0,
        }

        for key, change in diff.items():
            pct = change.get("pct")
            if pct is None:
                continue
            if abs(pct) >= thresholds.get(key, 20.0):
                return True
        return False

    def _llm_budget_ok(self) -> bool:
        if not self.llm.is_enabled():
            return False
        if not self.redis_cache or not self.redis_cache.is_connected():
            return True

        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = f"fi:llm:daily:{today}"
        try:
            current = self.redis_cache.redis_client.get(key)
            current_val = int(current) if current else 0
            if current_val >= self.daily_limit:
                return False
            self.redis_cache.redis_client.setex(key, 86400, current_val + 1)
            return True
        except Exception:
            return True

    def _analyze_diff(self, ticker: str, diff: Dict[str, Dict[str, float]]) -> Optional[Dict[str, Any]]:
        company = lookup_company(ticker) or ticker
        lines = []
        for key, change in diff.items():
            pct = change.get("pct")
            if pct is None:
                continue
            lines.append(f"{key}: {change.get('old')} -> {change.get('new')} ({pct:.1f}%)")

        body = "\n".join(lines)
        event = {
            "title": f"Fundamenttimuutos: {company}",
            "body": body,
            "event_type": "FUNDAMENTALS_UPDATE",
            "source": "System",
        }
        return self.llm.analyze_event(event, language="fi")

    def _store_insight(self, ticker: str, analysis: Dict[str, Any], source_hash: str) -> Optional[FiAiInsight]:
        title = analysis.get("summary") or f"Fundamentit päivitetty: {ticker}"
        with _db_session() as db:
            existing = (
                db.query(FiAiInsight)
                .filter(FiAiInsight.ticker == ticker)
                .filter(FiAiInsight.insight_type == "FUNDAMENTALS")
                .filter(FiAiInsight.source_hash == source_hash)
                .first()
            )
            if existing:
                return None

            insight = FiAiInsight(
                ticker=ticker,
                insight_type="FUNDAMENTALS",
                title=title,
                summary=analysis.get("summary"),
                bullets=analysis.get("bullets"),
                impact=analysis.get("impact"),
                sentiment=analysis.get("sentiment"),
                key_metrics=analysis.get("key_metrics"),
                risks=analysis.get("risks"),
                watch_items=analysis.get("watch_items"),
                raw_analysis=analysis,
                source_hash=source_hash,
                provider=",".join(analysis.get("providers", {}).keys()) if analysis.get("providers") else None,
                model=",".join(
                    [
                        info.get("model")
                        for info in (analysis.get("providers") or {}).values()
                        if isinstance(info, dict) and info.get("model")
                    ]
                )
                or None,
                language=analysis.get("language", "fi"),
            )
            db.add(insight)
            db.commit()
            db.refresh(insight)
            return insight


_fi_insight_service: Optional[FiInsightService] = None


def get_fi_insight_service() -> FiInsightService:
    global _fi_insight_service
    if _fi_insight_service is None:
        _fi_insight_service = FiInsightService()
    return _fi_insight_service
