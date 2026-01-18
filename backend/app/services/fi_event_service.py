"""
Finnish disclosure/news event ingestion + analysis.

Sources (best-effort):
- Nasdaq RSS (Main + First North) -> disclosure HTML
- Nasdaq company news (per-issuer query API)
- FIVA short positions (FIN-FSA data table)
- yfinance company news (optional fallback)
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from contextlib import contextmanager
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Iterable, List, Optional
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

from app.models.database import SessionLocal, FiNewsEvent
from app.services.fi_llm_service import FiLLMAnalyzer
from app.services.fi_ticker_lookup import (
    infer_ticker_from_text,
    infer_tickers_from_text,
    get_nasdaq_news_url,
    lookup_company,
    normalize_ticker,
)
from app.services.enhanced_news_service import get_enhanced_news_service

logger = logging.getLogger(__name__)


DEFAULT_RSS_URLS = [
    "https://api.news.eu.nasdaq.com/news/rss/mainMarketNotices",
    "https://api.news.eu.nasdaq.com/news/rss/firstNorthNotices",
    "https://api.news.eu.nasdaq.com/news/rss/nasdaqNordicNews",
]

DEFAULT_FIVA_SHORTS_URL = "https://www.finanssivalvonta.fi/api/shortselling/datatable/current"
DEFAULT_CNS_BASE_URL = "https://api.news.eu.nasdaq.com/news/"

FIVA_SHORTS_COLUMNS = [
    "positionHolder",
    "issuerName",
    "isinCode",
    "netShortPositionInPercent",
    "positionDate",
]

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (TradeMasterPro; +https://trademaster.guru)"
}

EXCLUDE_TITLE_KEYWORDS = [
    "structured bond",
    "listing of",
    "admitted to trading",
    "derivatives",
    "fixing information",
    "fixing info",
    "expiration information",
    "weekly exercise",
    "mortgage bond futures",
    "new strikes",
    "warrants",
    "certificates",
    "turbos",
    "mini future",
    "knock-out",
    "bull certificate",
    "bear certificate",
    "tracker certificate",
    "index",
    "benchmark",
    "segment review",
    "trading statistics",
]

INSIDER_KEYWORDS = [
    "managers' transactions",
    "manager's transactions",
    "insider",
    "sisäpiiri",
]

OWNERSHIP_KEYWORDS = [
    "flagging",
    "major holding",
    "major holdings",
    "shareholder",
    "ownership",
    "omistus",
    "liputus",
]

_ISSUER_CACHE: dict[str, dict[str, Any]] = {}
_ISSUER_CACHE_TTL = timedelta(days=7)


@contextmanager
def _db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _hash_event(title: str, body: str, source_url: str, published_at: Optional[datetime]) -> str:
    # Ignore body to avoid duplicate inserts when the same disclosure HTML changes slightly.
    payload = f"{title}|{source_url}|{published_at or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _parse_iso_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone(tz=None).replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _parse_cns_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return _parse_iso_date(value)


def _parse_headline_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in ("%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(cleaned, fmt)
        except Exception:
            continue
    return _parse_iso_date(cleaned)


def _extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    candidates: List[str] = []
    for tag in soup.find_all(["article", "section", "div"]):
        attrs = " ".join(
            [tag.get("id", "")] + tag.get("class", [])
        ).lower()
        if any(key in attrs for key in ["disclosure", "news", "content", "body", "release"]):
            text = tag.get_text(" ", strip=True)
            if len(text) > 200:
                candidates.append(text)

    if candidates:
        return max(candidates, key=len)

    return soup.get_text(" ", strip=True)


def _infer_event_type(title: str, categories: Iterable[str]) -> str:
    text = f"{title} {' '.join(categories)}".lower()
    for keyword in INSIDER_KEYWORDS:
        if keyword in text:
            return "INSIDER_TRANSACTION"
    for keyword in OWNERSHIP_KEYWORDS:
        if keyword in text:
            return "OWNERSHIP_CHANGE"
    return "PRESS_RELEASE"


def _infer_event_type_from_cns(title: str, cns_category: Optional[str]) -> str:
    text = f"{title} {cns_category or ''}".lower()
    if any(keyword in text for keyword in INSIDER_KEYWORDS):
        return "INSIDER_TRANSACTION"
    if any(keyword in text for keyword in OWNERSHIP_KEYWORDS):
        return "OWNERSHIP_CHANGE"
    if "inside information" in text or "sisäpiiritieto" in text:
        return "PRESS_RELEASE"
    return "COMPANY_NEWS"


class FiEventService:
    def __init__(self) -> None:
        urls_raw = os.getenv("FI_NASDAQ_RSS_URLS", "").strip()
        if urls_raw:
            self.rss_urls = [u.strip() for u in urls_raw.split(",") if u.strip()]
        else:
            self.rss_urls = list(DEFAULT_RSS_URLS)

        self.fiva_shorts_url = os.getenv("FI_FIVA_SHORTS_URL", "").strip() or DEFAULT_FIVA_SHORTS_URL
        self.cns_base_url = os.getenv("FI_NASDAQ_CNS_BASE_URL", "").strip() or DEFAULT_CNS_BASE_URL
        self.company_news_limit = int(os.getenv("FI_NASDAQ_COMPANY_NEWS_LIMIT", "5"))
        self.llm = FiLLMAnalyzer()
        self.analysis_batch_limit = int(os.getenv("FI_NEWS_ANALYSIS_BATCH_LIMIT", "5"))

    def ingest_nasdaq_rss(self, analyze_new: bool = True, limit: int = 50, require_ticker: bool = True) -> int:
        total_new = 0
        new_events: List[FiNewsEvent] = []

        for url in self.rss_urls:
            try:
                resp = requests.get(url, timeout=15, headers=REQUEST_HEADERS)
                resp.raise_for_status()
            except Exception as exc:
                logger.warning("Failed to fetch Nasdaq RSS %s: %s", url, exc)
                continue

            try:
                root = ElementTree.fromstring(resp.content)
            except Exception as exc:
                logger.warning("Failed to parse RSS feed %s: %s", url, exc)
                continue

            items = root.findall(".//item")
            for item in items[:limit]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = _parse_date(item.findtext("pubDate"))
                if not pub_date:
                    pub_date = _parse_iso_date(
                        item.findtext("{http://purl.org/dc/elements/1.1/}date")
                    )
                description = (item.findtext("description") or "").strip()
                categories = [c.text or "" for c in item.findall("category")]

                if title and any(keyword in title.lower() for keyword in EXCLUDE_TITLE_KEYWORDS):
                    continue

                body = description
                if link:
                    try:
                        html_resp = requests.get(link, timeout=15, headers=REQUEST_HEADERS)
                        html_resp.raise_for_status()
                        body = _extract_text_from_html(html_resp.text)
                    except Exception as exc:
                        logger.debug("Disclosure fetch failed (%s): %s", link, exc)

                title_matches = infer_tickers_from_text(title)
                if len(title_matches) == 1:
                    ticker = title_matches[0]
                else:
                    text_blob = f"{title}\n{body}"
                    matched_tickers = infer_tickers_from_text(text_blob)
                    ticker = matched_tickers[0] if len(matched_tickers) == 1 else None
                if not ticker:
                    if require_ticker:
                        continue
                company = lookup_company(ticker) if ticker else None

                event = {
                    "ticker": ticker,
                    "company": company,
                    "event_type": _infer_event_type(title, categories),
                    "title": title or "Nasdaq disclosure",
                    "body": body,
                    "source": "Nasdaq",
                    "source_url": link,
                    "published_at": pub_date,
                    "raw_payload": {
                        "categories": categories,
                        "description": description,
                        "rss_url": url,
                    },
                }

                saved = self._save_event(event)
                if saved:
                    total_new += 1
                    new_events.append(saved)

        if analyze_new and new_events:
            self.analyze_events(new_events, limit=self.analysis_batch_limit)

        self.cleanup_duplicates(days=30)
        return total_new

    def _get_cached_issuer_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        normalized = normalize_ticker(ticker)
        if not normalized:
            return None
        cached = _ISSUER_CACHE.get(normalized)
        if cached and cached.get("expires_at") and cached["expires_at"] > datetime.utcnow():
            return cached
        return None

    def _fetch_issuer_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        normalized = normalize_ticker(ticker)
        if not normalized:
            return None

        cached = self._get_cached_issuer_info(normalized)
        if cached:
            return cached

        share_url = get_nasdaq_news_url(normalized)
        if not share_url:
            return None

        def _fetch_issuer_from_url(url: str) -> Optional[Dict[str, Any]]:
            try:
                resp = requests.get(url, timeout=15, headers=REQUEST_HEADERS)
                resp.raise_for_status()
            except Exception as exc:
                logger.debug("Failed to fetch Nasdaq share page %s: %s", url, exc)
                return None

            soup = BeautifulSoup(resp.text, "lxml")
            issuer_tag = soup.find("div", class_="jupiter22-c-company-news-list__issuer-id")
            if not issuer_tag:
                return None

            issuer_id = issuer_tag.get("data-issuerid")
            orderbook_id = issuer_tag.get("data-orderbookid")
            previous_orderbook_id = issuer_tag.get("data-previousorderbookid")
            if not issuer_id:
                return None

            return {
                "issuer_id": issuer_id,
                "orderbook_id": orderbook_id,
                "previous_orderbook_id": previous_orderbook_id,
                "share_url": resp.url or url,
            }

        info = _fetch_issuer_from_url(share_url)
        if not info:
            # Fallback to European share page if needed
            slug = normalized.replace(".HE", "").lower()
            fallback_url = f"https://www.nasdaq.com/european-market-activity/shares/{slug}"
            info = _fetch_issuer_from_url(fallback_url)
        if not info:
            logger.debug("Issuer info not found on Nasdaq share page for %s", normalized)
            return None

        info["expires_at"] = datetime.utcnow() + _ISSUER_CACHE_TTL
        _ISSUER_CACHE[normalized] = info
        return info

    def ingest_nasdaq_company_news_for_ticker(
        self,
        ticker: str,
        analyze_new: bool = True,
        limit: Optional[int] = None,
    ) -> int:
        normalized = normalize_ticker(ticker)
        if not normalized:
            return 0

        issuer_info = self._fetch_issuer_info(normalized)
        if not issuer_info:
            return 0

        limit = limit or self.company_news_limit
        params = {
            "globalName": "NordicAllMarkets",
            "gcfIssuerId": issuer_info.get("issuer_id"),
            "limit": limit,
            "start": 0,
            "dir": "DESC",
            "timeZone": "CET",
            "dateMask": "yyyy-MM-dd HH:mm:ss",
            "displayLanguage": "fi",
            "countResults": "true",
            "globalGroup": "exchangeNotice",
        }

        try:
            resp = requests.get(
                f"{self.cns_base_url}query.action",
                params=params,
                timeout=20,
                headers=REQUEST_HEADERS,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            logger.debug("Failed to fetch Nasdaq company news for %s: %s", normalized, exc)
            return 0

        items = payload.get("results", {}).get("item", [])
        if isinstance(items, dict):
            items = [items]

        new_events: List[FiNewsEvent] = []
        total_new = 0
        company_name = lookup_company(normalized)

        for item in items:
            title = (item.get("headline") or "").strip() or "Company news"
            source_url = item.get("messageUrl") or ""
            published_at = _parse_cns_datetime(item.get("releaseTime") or item.get("published"))
            cns_category = item.get("cnsCategory") or ""

            event_type = _infer_event_type_from_cns(title, cns_category)
            body = ""

            if source_url:
                with _db_session() as db:
                    existing = db.query(FiNewsEvent).filter(FiNewsEvent.source_url == source_url).first()
                if not existing:
                    try:
                        html_resp = requests.get(source_url, timeout=15, headers=REQUEST_HEADERS)
                        html_resp.raise_for_status()
                        body = _extract_text_from_html(html_resp.text)
                    except Exception:
                        body = ""

            event = {
                "ticker": normalized,
                "company": company_name or item.get("company") or normalized.replace(".HE", ""),
                "event_type": event_type,
                "title": title,
                "body": body,
                "source": "Nasdaq",
                "source_url": source_url,
                "published_at": published_at,
                "raw_payload": {
                    **item,
                    "issuerId": issuer_info.get("issuer_id"),
                },
                "allow_update": True,
            }

            saved = self._save_event(event)
            if saved:
                total_new += 1
                new_events.append(saved)

        if analyze_new and new_events:
            self.analyze_events(new_events, limit=self.analysis_batch_limit)

        return total_new

    def ingest_nasdaq_company_news_bulk(
        self,
        analyze_new: bool = True,
        limit: Optional[int] = None,
        tickers: Optional[List[str]] = None,
    ) -> int:
        if tickers is None:
            from app.services.fi_data import get_fi_data_service

            fi_service = get_fi_data_service()
            tickers = fi_service.get_all_tickers()

        total_new = 0

        for idx, ticker in enumerate(tickers):
            added = self.ingest_nasdaq_company_news_for_ticker(
                ticker,
                analyze_new=False,
                limit=limit,
            )
            total_new += added

            if (idx + 1) % 10 == 0:
                # Small delay to avoid rate limits
                import time

                time.sleep(0.3)

        if analyze_new:
            self.analyze_pending(limit=self.analysis_batch_limit)

        self.cleanup_duplicates(days=30)
        return total_new

    def ingest_ir_headlines_for_ticker(self, ticker: str, limit: int = 5, analyze_new: bool = True) -> int:
        normalized = normalize_ticker(ticker)
        if not normalized:
            return 0

        headlines = self.fetch_ir_headlines(normalized, limit=limit)
        if not headlines:
            return 0

        total_new = 0
        company_name = lookup_company(normalized)
        new_events: List[FiNewsEvent] = []

        for headline in headlines:
            title = (headline.get("title") or "").strip()
            if not title:
                continue
            source_url = headline.get("url") or ""
            published_at = _parse_headline_date(headline.get("date"))

            event = {
                "ticker": normalized,
                "company": company_name or normalized.replace(".HE", ""),
                "event_type": "COMPANY_NEWS",
                "title": title,
                "body": "",
                "source": "IR",
                "source_url": source_url,
                "published_at": published_at,
                "raw_payload": headline,
            }

            saved = self._save_event(event)
            if saved:
                total_new += 1
                new_events.append(saved)

        if analyze_new and new_events:
            self.analyze_events(new_events, limit=min(self.analysis_batch_limit, len(new_events)))

        return total_new

    def ingest_ir_headlines_bulk(
        self,
        limit: int = 5,
        tickers: Optional[List[str]] = None,
    ) -> int:
        if tickers is None:
            from app.services.fi_data import get_fi_data_service

            fi_service = get_fi_data_service()
            tickers = fi_service.get_all_tickers()

        total_new = 0

        for idx, ticker in enumerate(tickers):
            total_new += self.ingest_ir_headlines_for_ticker(ticker, limit=limit, analyze_new=False)
            if (idx + 1) % 12 == 0:
                import time

                time.sleep(0.4)

        self.cleanup_duplicates(days=30)
        return total_new

    def ingest_fiva_short_positions(self, analyze_new: bool = True) -> int:
        if not self.fiva_shorts_url:
            logger.info("FI_FIVA_SHORTS_URL not configured; skipping FIVA ingestion")
            return 0

        rows: List[Dict[str, Any]] = []

        if "shortselling/datatable/current" in self.fiva_shorts_url:
            params: Dict[str, Any] = {
                "draw": 1,
                "start": 0,
                "length": 1000,
                "search[value]": "",
                "search[regex]": "false",
                "lang": "fi",
                "order[0][column]": 0,
                "order[0][dir]": "desc",
            }
            for idx, col in enumerate(FIVA_SHORTS_COLUMNS):
                params[f"columns[{idx}][data]"] = col
                params[f"columns[{idx}][name]"] = ""
                params[f"columns[{idx}][searchable]"] = "true"
                params[f"columns[{idx}][orderable]"] = "false"
                params[f"columns[{idx}][search][value]"] = ""
                params[f"columns[{idx}][search][regex]"] = "false"

            try:
                resp = requests.post(
                    self.fiva_shorts_url,
                    data=params,
                    timeout=20,
                    headers=REQUEST_HEADERS,
                )
                resp.raise_for_status()
                payload = resp.json()
                rows = payload.get("data", [])
            except Exception as exc:
                logger.warning("Failed to fetch FIVA short positions JSON: %s", exc)
                rows = []
        else:
            try:
                resp = requests.get(self.fiva_shorts_url, timeout=20, headers=REQUEST_HEADERS)
                resp.raise_for_status()
            except Exception as exc:
                logger.warning("Failed to fetch FIVA short positions: %s", exc)
                return 0

            soup = BeautifulSoup(resp.text, "lxml")
            table = soup.find("table")
            if not table:
                logger.warning("No short positions table found at %s", self.fiva_shorts_url)
                return 0

            headers = [th.get_text(" ", strip=True) for th in table.find_all("th")]
            table_rows = table.find_all("tr")
            for row in table_rows[1:]:
                cols = [td.get_text(" ", strip=True) for td in row.find_all("td")]
                if not cols:
                    continue
                rows.append({headers[i]: cols[i] for i in range(min(len(headers), len(cols)))})

        new_events: List[FiNewsEvent] = []
        total_new = 0

        for row in rows:
            issuer = row.get("issuerName") or row.get("Issuer") or row.get("Company") or row.get("Issuer name") or ""
            holder = row.get("positionHolder") or row.get("Position holder") or row.get("Holder") or ""
            position = row.get("netShortPositionInPercent") or row.get("Net short position") or row.get("Position") or ""
            isin = row.get("isinCode") or row.get("ISIN") or ""
            date_text = row.get("positionDate") or row.get("Position date") or row.get("Date") or ""
            published_at = _parse_iso_date(date_text) or None

            ticker = infer_ticker_from_text(issuer)
            company = lookup_company(ticker) if ticker else issuer

            position_text = f"{position}%" if isinstance(position, (int, float)) else position
            title = f"Short position: {holder} {position_text} in {issuer}".strip()
            body = (
                f"Issuer: {issuer}. Holder: {holder}. Position: {position_text}. "
                f"ISIN: {isin}. Date: {date_text}."
            )

            event = {
                "ticker": ticker,
                "company": company,
                "event_type": "SHORT_POSITION",
                "title": title,
                "body": body,
                "source": "FIVA",
                "source_url": self.fiva_shorts_url,
                "published_at": published_at,
                "raw_payload": row,
            }

            saved = self._save_event(event)
            if saved:
                total_new += 1
                new_events.append(saved)

        if analyze_new and new_events:
            self.analyze_events(new_events, limit=self.analysis_batch_limit)

        return total_new

    def ingest_yfinance_news_for_ticker(self, ticker: str, limit: int = 10) -> int:
        if not ticker:
            return 0

        ticker = ticker.upper()
        enhanced = get_enhanced_news_service()
        articles = enhanced.get_stock_news_yfinance(ticker, limit=limit)

        new_events = []
        total_new = 0
        company_name = lookup_company(ticker)
        for article in articles:
            title = article.get("title") or ""
            body = article.get("description") or ""
            combined = f"{title} {body}".lower()
            symbol = ticker.replace(".HE", "")
            if company_name and company_name.lower() not in combined and symbol.lower() not in combined:
                continue
            if not company_name and symbol.lower() not in combined:
                continue
            published_at = article.get("publishedAt")
            if isinstance(published_at, str):
                try:
                    published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                except Exception:
                    published_at = None

            event = {
                "ticker": ticker,
                "company": lookup_company(ticker),
                "event_type": "NEWS",
                "title": title or "Uutinen",
                "body": body,
                "source": article.get("source") or "Yahoo Finance",
                "source_url": article.get("url"),
                "published_at": published_at,
                "raw_payload": article,
            }

            saved = self._save_event(event)
            if saved:
                total_new += 1
                new_events.append(saved)

        if new_events:
            self.analyze_events(new_events, limit=self.analysis_batch_limit)

        self.cleanup_duplicates(days=30)
        return total_new

    def analyze_pending(self, limit: int = 10) -> int:
        if not self.llm.is_enabled():
            return 0

        with _db_session() as db:
            pending = (
                db.query(FiNewsEvent)
                .filter(FiNewsEvent.analysis.is_(None))
                .order_by(FiNewsEvent.published_at.desc().nullslast(), FiNewsEvent.id.desc())
                .limit(limit)
                .all()
            )

        if not pending:
            return 0

        self.analyze_events(pending, limit=limit)
        return len(pending)

    def get_events(
        self,
        ticker: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        event_types: Optional[List[str]] = None,
        include_analysis: bool = True,
    ) -> List[Dict[str, Any]]:
        with _db_session() as db:
            query = db.query(FiNewsEvent)
            if ticker:
                normalized = normalize_ticker(ticker) or ticker.upper()
                query = query.filter(FiNewsEvent.ticker == normalized)
            if event_types:
                query = query.filter(FiNewsEvent.event_type.in_(event_types))

            query = query.order_by(FiNewsEvent.published_at.desc().nullslast(), FiNewsEvent.id.desc())
            events = query.offset(offset).limit(limit).all()

        return [self._serialize_event(e, include_analysis=include_analysis) for e in events]

    def get_event_summary(self, ticker: str, days: int = 30) -> Dict[str, Any]:
        since = datetime.utcnow() - timedelta(days=days)
        normalized = normalize_ticker(ticker) or ticker.upper()
        with _db_session() as db:
            query = db.query(FiNewsEvent).filter(FiNewsEvent.ticker == normalized)
            query = query.filter(FiNewsEvent.published_at >= since)
            query = query.filter(FiNewsEvent.event_type.notin_(["NEWS", "COMPANY_NEWS"]))
            events = query.all()

        summary = {
            "total": len(events),
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "mixed": 0,
            "last_updated": datetime.utcnow().isoformat(),
        }
        for event in events:
            impact = (event.impact or "").upper()
            if impact == "POSITIVE":
                summary["positive"] += 1
            elif impact == "NEGATIVE":
                summary["negative"] += 1
            elif impact == "MIXED":
                summary["mixed"] += 1
            else:
                summary["neutral"] += 1
        return summary

    def get_significant_events(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get significant events for the dashboard.
        Filters out generic market notices (turbo warrants, fixing info, etc.)
        and returns only company-specific news.
        """
        # Keywords to filter OUT (generic market notices)
        exclude_keywords = [
            "turbo warrant",
            "mini future",
            "fixing information",
            "fixing info",
            "listing of",
            "delisting of",
            "knock-out warrant",
            "bull certificate",
            "bear certificate",
            "tracker certificate",
        ]

        since = datetime.utcnow() - timedelta(days=days)

        with _db_session() as db:
            query = db.query(FiNewsEvent)
            # Only events with a ticker (company-specific)
            query = query.filter(FiNewsEvent.ticker.isnot(None))
            query = query.filter(FiNewsEvent.ticker != "")
            query = query.filter(FiNewsEvent.event_type.notin_(["NEWS", "COMPANY_NEWS"]))
            # Only recent events
            query = query.filter(FiNewsEvent.published_at >= since)
            # Order by date and importance
            query = query.order_by(FiNewsEvent.published_at.desc().nullslast(), FiNewsEvent.id.desc())
            # Fetch more than needed for filtering
            events = query.limit(limit * 5).all()

        # Filter out generic market notices
        filtered = []
        seen_titles = set()  # For deduplication

        for event in events:
            title_lower = (event.title or "").lower()

            # Skip if matches exclude keywords
            if any(kw in title_lower for kw in exclude_keywords):
                continue

            # Skip duplicates (same title)
            title_key = title_lower[:50]  # First 50 chars for dedup
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            # Prioritize events with impact analysis
            filtered.append(event)

            if len(filtered) >= limit:
                break

        # Sort by impact importance: POSITIVE/NEGATIVE first, then MIXED, then NEUTRAL
        def impact_priority(e):
            impact = (e.impact or "").upper()
            if impact in ("POSITIVE", "NEGATIVE"):
                return 0
            elif impact == "MIXED":
                return 1
            else:
                return 2

        filtered.sort(key=lambda e: (impact_priority(e), -(e.published_at.timestamp() if e.published_at else 0)))

        return [self._serialize_event(e, include_analysis=True) for e in filtered[:limit]]

    def analyze_events(self, events: List[FiNewsEvent], limit: int = 5) -> None:
        if not self.llm.is_enabled():
            logger.info("LLM analysis disabled (missing API keys)")
            return

        analyzed = 0
        for event in events:
            if analyzed >= limit:
                break
            if event.analysis:
                continue

            analysis = self.llm.analyze_event(
                {
                    "title": event.title,
                    "body": event.body or "",
                    "event_type": event.event_type,
                    "source": event.source or "",
                },
                language="fi",
            )

            with _db_session() as db:
                stored = db.query(FiNewsEvent).filter(FiNewsEvent.id == event.id).first()
                if not stored:
                    continue
                stored.analysis = analysis
                stored.summary = analysis.get("summary")
                stored.impact = analysis.get("impact")
                stored.sentiment = analysis.get("sentiment")
                provider_info = analysis.get("providers", {})
                stored.analysis_provider = ",".join(provider_info.keys()) if provider_info else None
                stored.analysis_model = (
                    ",".join(
                        [
                            info.get("model")
                            for info in provider_info.values()
                            if isinstance(info, dict) and info.get("model")
                        ]
                    )
                    or None
                )
                stored.analysis_language = analysis.get("language", "fi")
                stored.analyzed_at = datetime.utcnow()
                db.add(stored)
                db.commit()

            analyzed += 1

    def _save_event(self, event: Dict[str, Any]) -> Optional[FiNewsEvent]:
        title = event.get("title") or ""
        body = event.get("body") or ""
        source_url = event.get("source_url") or ""
        published_at = event.get("published_at")
        content_hash = _hash_event(title, body, source_url, published_at)
        allow_update = bool(event.get("allow_update"))

        with _db_session() as db:
            if source_url and (event.get("source") or "").upper() != "FIVA":
                existing_url = db.query(FiNewsEvent).filter(FiNewsEvent.source_url == source_url).first()
                if existing_url:
                    if allow_update:
                        updated = False
                        if event.get("ticker") and existing_url.ticker != event.get("ticker"):
                            existing_url.ticker = event.get("ticker")
                            existing_url.company = event.get("company") or existing_url.company
                            updated = True
                        if event.get("event_type") and existing_url.event_type != event.get("event_type"):
                            existing_url.event_type = event.get("event_type")
                            updated = True
                        if event.get("body") and not existing_url.body:
                            existing_url.body = event.get("body")
                            updated = True
                        if event.get("raw_payload") and not existing_url.raw_payload:
                            existing_url.raw_payload = event.get("raw_payload")
                            updated = True
                        if updated:
                            db.add(existing_url)
                            db.commit()
                            db.refresh(existing_url)
                    return existing_url if allow_update else None

            if title and published_at:
                existing_title = (
                    db.query(FiNewsEvent)
                    .filter(FiNewsEvent.title == title)
                    .filter(FiNewsEvent.published_at == published_at)
                    .first()
                )
                if existing_title:
                    return None

            existing = db.query(FiNewsEvent).filter(FiNewsEvent.content_hash == content_hash).first()
            if existing:
                return None

            record = FiNewsEvent(
                ticker=event.get("ticker"),
                company=event.get("company"),
                event_type=event.get("event_type") or "NEWS",
                title=title,
                body=body,
                summary=event.get("summary"),
                source=event.get("source"),
                source_url=source_url,
                published_at=published_at,
                content_hash=content_hash,
                raw_payload=event.get("raw_payload"),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record

    def cleanup_duplicates(self, days: int = 30) -> int:
        """Remove duplicate or low-confidence events within the last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        removed = 0
        with _db_session() as db:
            events = (
                db.query(FiNewsEvent)
                .filter(FiNewsEvent.published_at >= since)
                .order_by(FiNewsEvent.id.asc())
                .all()
            )

            seen: set[str] = set()
            dup_ids: list[int] = []
            for event in events:
                source = (event.source or "").upper()
                title_lower = (event.title or "").lower()
                if source == "FIVA":
                    continue
                if not event.ticker:
                    dup_ids.append(event.id)
                    continue
                if title_lower and any(keyword in title_lower for keyword in EXCLUDE_TITLE_KEYWORDS):
                    dup_ids.append(event.id)
                    continue

                payload = event.raw_payload or {}
                issuer_hint = payload.get("issuerId") or payload.get("gcfIssuerId") or payload.get("issuer_id")
                if not issuer_hint:
                    matches = infer_tickers_from_text(f"{event.title}\n{event.body or ''}")
                    if len(matches) != 1 or (event.ticker and event.ticker not in matches):
                        dup_ids.append(event.id)
                        continue

                key = event.source_url or f"{event.title}|{event.published_at.date() if event.published_at else ''}"
                if key in seen:
                    dup_ids.append(event.id)
                else:
                    seen.add(key)

            if dup_ids:
                removed = (
                    db.query(FiNewsEvent)
                    .filter(FiNewsEvent.id.in_(dup_ids))
                    .delete(synchronize_session=False)
                )
                db.commit()

        return removed

    @staticmethod
    def _serialize_event(event: FiNewsEvent, include_analysis: bool = True) -> Dict[str, Any]:
        data = {
            "id": event.id,
            "ticker": event.ticker,
            "company": event.company,
            "event_type": event.event_type,
            "title": event.title,
            "summary": event.summary,
            "source": event.source,
            "source_url": event.source_url,
            "published_at": event.published_at.isoformat() if event.published_at else None,
            "impact": event.impact,
            "sentiment": event.sentiment,
        }
        if include_analysis:
            data["analysis"] = event.analysis
        return data


    def fetch_ir_headlines(self, ticker: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Fetch headlines from company IR page using LLM extraction.
        Returns a list of headlines with titles and optional URLs.
        """
        normalized = normalize_ticker(ticker)
        if not normalized:
            return []

        # Get IR/news URL from fi_tickers.json (prefer the news/release page)
        from app.services.fi_data import get_fi_data_service
        fi_service = get_fi_data_service()
        stock_info = fi_service.get_stock_info(normalized)
        ir_news_url = stock_info.get("ir_news_url") if stock_info else None
        ir_url = stock_info.get("ir_url") if stock_info else None
        source_url = ir_news_url or ir_url

        if not source_url:
            logger.debug("No IR URL found for %s", normalized)
            return []

        try:
            resp = requests.get(source_url, timeout=15, headers=REQUEST_HEADERS)
            resp.raise_for_status()
        except Exception as exc:
            logger.debug("Failed to fetch IR page for %s: %s", normalized, exc)
            return []

        # Extract text and links from page
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            tag.decompose()

        # Find potential headline containers
        from urllib.parse import urljoin

        candidates: List[Dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        def _abs_url(href: str) -> str:
            if href.startswith("/"):
                return urljoin(source_url, href)
            return href

        # Blacklist of generic page titles that are NOT news
        BLACKLIST_PATTERNS = [
            "in brief", "lyhyesti", "as an investment", "sijoituskohteena",
            "contact us", "yhteystiedot", "investor relations", "sijoittajat",
            "about us", "meistä", "about", "company", "yritys", "board",
            "hallitus", "management", "johto", "history", "historia",
            "strategy", "strategia", "governance", "hallinnointi", "csr",
            "sustainability", "vastuullisuus", "privacy", "tietosuoja",
            "terms", "ehdot", "career", "ura", "jobs", "työpaikat",
            "products", "tuotteet", "services", "palvelut", "solutions",
            "financial calendar", "talouskalenteri", "share", "osake",
            "shareholders", "osakkeenomistajat", "annual report", "vuosikertomus",
            "reports and presentations", "raportit", "subscribe", "tilaa",
            "newsletter", "uutiskirje", "cookie", "evästeet", "login", "kirjaudu"
        ]

        def _is_blacklisted(title: str) -> bool:
            lower = title.lower()
            for pattern in BLACKLIST_PATTERNS:
                if pattern in lower:
                    return True
            # Check if title has no numbers/dates (real news often has)
            # and is very short generic text
            if len(title) < 30 and not any(c.isdigit() for c in title):
                return True
            return False

        def _add_candidate(title: str, href: Optional[str] = None, date_text: Optional[str] = None) -> None:
            if not title:
                return
            cleaned = " ".join(title.split())
            if len(cleaned) < 15 or len(cleaned) > 220:
                return
            # Skip generic/navigation items
            if _is_blacklisted(cleaned):
                return
            url_val = ""
            if href and isinstance(href, str) and not href.startswith("#"):
                url_val = _abs_url(href)
            key = (cleaned.lower(), url_val)
            if key in seen:
                return
            seen.add(key)
            entry: Dict[str, Any] = {"title": cleaned}
            if url_val:
                entry["url"] = url_val
            if date_text:
                entry["date"] = date_text
            candidates.append(entry)

        # 1) Prefer structured article entries
        for article in soup.find_all("article"):
            time_tag = article.find("time")
            date_text = None
            if time_tag:
                date_text = time_tag.get("datetime") or time_tag.get_text(" ", strip=True)

            link_tag = article.find("a", href=True)
            title_text = None
            for heading in article.find_all(["h1", "h2", "h3", "h4"]):
                heading_text = heading.get_text(" ", strip=True)
                if heading_text:
                    title_text = heading_text
                    if not link_tag:
                        link_tag = heading.find("a", href=True)
                    break
            if not title_text and link_tag:
                title_text = link_tag.get_text(" ", strip=True)

            _add_candidate(title_text or "", link_tag.get("href") if link_tag else None, date_text)

        # 2) Look for news/release sections
        section_keywords = ("news", "release", "press", "tiedote", "stock-exchange", "porssi")
        for container in soup.find_all(["section", "div", "ul", "ol"]):
            attrs = " ".join([container.get("id", "")] + container.get("class", [])).lower()
            if not attrs or not any(k in attrs for k in section_keywords):
                continue
            for link_tag in container.find_all("a", href=True):
                text = link_tag.get_text(" ", strip=True)
                _add_candidate(text, link_tag.get("href"))

        # 3) Fallback to generic anchors/headings
        if len(candidates) < limit:
            for tag in soup.find_all(["a", "h1", "h2", "h3", "h4", "li"]):
                text = tag.get_text(" ", strip=True)
                href = tag.get("href", "")
                _add_candidate(text, href)

        headlines_html = []
        for entry in candidates:
            parts = [entry.get("title", "")]
            if entry.get("url"):
                parts.append(entry["url"])
            if entry.get("date"):
                parts.append(entry["date"])
            headlines_html.append(" | ".join(parts))

        if not headlines_html:
            return []

        # Use LLM to extract actual news headlines
        if not self.llm.is_enabled():
            # Fallback: return first few items that look like headlines
            results = []
            for item in headlines_html[:limit]:
                parts = item.split(" | ")
                title = parts[0]
                url = parts[1] if len(parts) > 1 else None
                date = parts[2] if len(parts) > 2 else None
                results.append({"title": title, "url": url, "date": date})
            return results

        # LLM extraction prompt
        content = "\n".join(headlines_html[:50])  # Limit to 50 items
        prompt = (
            "Etsi sivulta uusimmat lehdistötiedotteet ja uutisotsikot.\n"
            "Palauta JSON-lista (max 5 kpl) muodossa:\n"
            '[{"title": "Otsikko suomeksi", "url": "linkki jos saatavilla", "date": "päivämäärä jos näkyy"}]\n\n'
            "Jätä pois:\n- Navigaatiolinkit\n- Yleiset sivuotsikot\n- Yhteystiedot\n\n"
            f"Sivun sisältö:\n{content}"
        )

        try:
            if self.llm._anthropic_client:
                message = self.llm._anthropic_client.messages.create(
                    model=self.llm.anthropic_model,
                    max_tokens=500,
                    system="Olet tietojenlouhija. Palauta VAIN JSON-lista, ei muuta tekstiä.",
                    messages=[{"role": "user", "content": prompt}],
                )
                text = ""
                if message and message.content:
                    if isinstance(message.content, list):
                        text = "".join(block.text for block in message.content if hasattr(block, "text"))
                    else:
                        text = str(message.content)

                # Parse JSON
                import json
                match = re.search(r"\[.*\]", text, re.DOTALL)
                if match:
                    headlines = json.loads(match.group(0))
                    return headlines[:limit]
        except Exception as exc:
            logger.debug("LLM IR headline extraction failed for %s: %s", normalized, exc)

        return []


_fi_event_service: Optional[FiEventService] = None


def get_fi_event_service() -> FiEventService:
    global _fi_event_service
    if _fi_event_service is None:
        _fi_event_service = FiEventService()
    return _fi_event_service
