"""
Finnish ticker lookup utilities.

Provides lightweight mapping between company names and Nasdaq Helsinki tickers.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_TICKER_RE = re.compile(r"\b([A-Z0-9]{1,10}\.HE)\b")

_TICKER_TO_NAME: dict[str, str] = {}
_NAME_TO_TICKER: dict[str, str] = {}
_NAME_VARIANTS: dict[str, str] = {}

_LEGAL_SUFFIXES = (
    "oyj",
    "abp",
    "plc",
    "ltd",
    "ltd.",
    "ab",
    "oy",
    "corp",
    "corporation",
    "inc",
    "inc.",
)

_NON_WORD_RE = re.compile(r"[^a-z0-9&]+")


def _normalize_name(name: str) -> str:
    cleaned = _NON_WORD_RE.sub(" ", name.lower())
    return " ".join(cleaned.split()).strip()


def _add_name_variant(name: str, ticker: str) -> None:
    if not name:
        return
    normalized = _normalize_name(name)
    if len(normalized) >= 4:
        _NAME_VARIANTS.setdefault(normalized, ticker)

    # Replace & with "and" and vice versa
    if "&" in normalized:
        alt = normalized.replace("&", "and")
        alt = " ".join(alt.split())
        if len(alt) >= 4:
            _NAME_VARIANTS.setdefault(alt, ticker)
    if " and " in normalized:
        alt = normalized.replace(" and ", " & ")
        alt = " ".join(alt.split())
        if len(alt) >= 4:
            _NAME_VARIANTS.setdefault(alt, ticker)

    # Remove common legal suffixes at the end
    for suffix in _LEGAL_SUFFIXES:
        if normalized.endswith(f" {suffix}"):
            trimmed = normalized[: -len(suffix) - 1].strip()
            if len(trimmed) >= 4:
                _NAME_VARIANTS.setdefault(trimmed, ticker)


def _load_fi_tickers() -> None:
    global _TICKER_TO_NAME, _SYMBOL_TO_TICKER, _NAME_TO_TICKER

    tickers_path = Path(__file__).parent.parent / "data" / "fi_tickers.json"
    if not tickers_path.exists():
        logger.warning("fi_tickers.json not found at %s", tickers_path)
        return

    try:
        data = json.loads(tickers_path.read_text(encoding="utf-8"))
        stocks = data.get("stocks", [])
        for stock in stocks:
            ticker = (stock.get("ticker") or "").strip().upper()
            name = (stock.get("name") or "").strip()
            if not ticker:
                continue
            _TICKER_TO_NAME[ticker] = name
            if name:
                _NAME_TO_TICKER[name.lower()] = ticker
                _add_name_variant(name, ticker)
    except Exception as exc:
        logger.error("Failed to load fi_tickers.json: %s", exc)


_load_fi_tickers()


def normalize_ticker(ticker: str) -> Optional[str]:
    if not ticker:
        return None
    normalized = ticker.strip().upper()
    if not normalized.endswith(".HE"):
        normalized = f"{normalized}.HE"
    return normalized


def lookup_company(ticker: str) -> Optional[str]:
    if not ticker:
        return None
    return _TICKER_TO_NAME.get(normalize_ticker(ticker) or "")


def infer_tickers_from_text(text: str) -> list[str]:
    if not text:
        return []

    matches = set()
    for match in _TICKER_RE.findall(text):
        matches.add(match)

    normalized_text = _normalize_name(text)
    padded = f" {normalized_text} "
    for name_variant, ticker in _NAME_VARIANTS.items():
        if f" {name_variant} " in padded:
            matches.add(ticker)

    return sorted(matches)


def infer_ticker_from_text(text: str) -> Optional[str]:
    matches = infer_tickers_from_text(text)
    if len(matches) == 1:
        return matches[0]
    return None

    return None


def get_nasdaq_news_url(ticker: str) -> Optional[str]:
    """Return Nasdaq European share page URL for a Finnish ticker."""
    normalized = normalize_ticker(ticker)
    if not normalized:
        return None
    # Nasdaq company news page (contains issuerId data attributes)
    return f"https://www.nasdaq.com/market-activity/stocks/{normalized}/news-and-insights"
