"""
Delisted tickers registry.

Tracks tickers that no longer return market data and should be excluded
from the universe.
"""

from __future__ import annotations

from pathlib import Path
import json
import logging
from threading import Lock
from typing import Iterable, Set

logger = logging.getLogger(__name__)

_LOCK = Lock()
_CACHE: Set[str] | None = None
_DELISTED_PATH = Path(__file__).resolve().parent.parent / "data" / "delisted_tickers.json"


def _load_delisted() -> Set[str]:
    global _CACHE
    if _CACHE is not None:
        return set(_CACHE)

    if not _DELISTED_PATH.exists():
        _CACHE = set()
        return set()

    try:
        raw = json.loads(_DELISTED_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            logger.warning("Delisted tickers file is not a list; ignoring.")
            _CACHE = set()
            return set()
        _CACHE = {str(ticker).upper() for ticker in raw if str(ticker).strip()}
    except Exception as exc:
        logger.warning("Failed to read delisted tickers file: %s", exc)
        _CACHE = set()

    return set(_CACHE)


def get_delisted_tickers() -> Set[str]:
    return _load_delisted()


def add_delisted_tickers(tickers: Iterable[str]) -> int:
    candidates = {str(ticker).upper().strip() for ticker in tickers if str(ticker).strip()}
    if not candidates:
        return 0

    with _LOCK:
        current = _load_delisted()
        updated = set(current)
        updated.update(candidates)

        if updated == current:
            return 0

        try:
            _DELISTED_PATH.parent.mkdir(parents=True, exist_ok=True)
            _DELISTED_PATH.write_text(
                json.dumps(sorted(updated)),
                encoding="utf-8"
            )
            global _CACHE
            _CACHE = set(updated)
            logger.info("Registered %s delisted tickers", len(updated) - len(current))
            return len(updated) - len(current)
        except Exception as exc:
            logger.warning("Failed to write delisted tickers file: %s", exc)
            return 0


def remove_delisted_tickers(tickers: Iterable[str]) -> int:
    candidates = {str(ticker).upper().strip() for ticker in tickers if str(ticker).strip()}
    if not candidates:
        return 0

    with _LOCK:
        current = _load_delisted()
        updated = set(current)
        updated.difference_update(candidates)

        if updated == current:
            return 0

        try:
            _DELISTED_PATH.parent.mkdir(parents=True, exist_ok=True)
            _DELISTED_PATH.write_text(
                json.dumps(sorted(updated)),
                encoding="utf-8"
            )
            global _CACHE
            _CACHE = set(updated)
            logger.info("Removed %s delisted tickers", len(current) - len(updated))
            return len(current) - len(updated)
        except Exception as exc:
            logger.warning("Failed to write delisted tickers file: %s", exc)
            return 0
