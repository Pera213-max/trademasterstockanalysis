import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import yfinance as yf
from bs4 import BeautifulSoup


DATA_PATH = Path(__file__).resolve().parents[1] / "backend" / "app" / "data" / "fi_tickers.json"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 12
REQUEST_DELAY = 0.2

KEYWORDS = (
    "investor-relations",
    "investor relations",
    "investors",
    "investor",
    "sijoittaj",
)

KEYWORD_PATTERNS = (
    re.compile(r"/ir(?:/|$)", re.IGNORECASE),
    re.compile(r"/ir[-_]", re.IGNORECASE),
)

EXCLUDES = (
    "career",
    "jobs",
    "recruit",
    "privacy",
    "cookie",
    "terms",
    "sustainability",
)

MANUAL_OVERRIDES = {
    "AALLON.HE": {
        "url": "https://aallon.fi/sijoittajille/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "ALBAV.HE": {
        "url": "https://www.alandsbanken.com/financial-information",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "ALBBV.HE": {
        "url": "https://www.alandsbanken.com/financial-information",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "ATRAV.HE": {
        "url": "https://www.atria.com/en/investors/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "ELEAV.HE": {
        "url": "https://www.elecster.fi/hallinnointi/",
        "type": "ir",
        "note": "manual: investor relations content",
    },
    "EQV1V.HE": {
        "url": "https://www.eq.fi/fi/about-eq-group/sijoittajat",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "FIA1S.HE": {
        "url": "https://investors.finnair.com/en/as_an_investment",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "KREATE.HE": {
        "url": "https://kreategroup.fi/en/contact-information-and-ir-calendar/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "LEHTO.HE": {
        "url": "https://lehto.fi/en/investors/investor-relations/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "MEKKO.HE": {
        "url": "https://company.marimekko.com/sijoittajat/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "MODULIG.HE": {
        "url": "https://modulight.com/investor-relations/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "NDA-FI.HE": {
        "url": "https://www.nordea.com/en/investors/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "NPANIMO.HE": {
        "url": "https://sijoittajat.nokianpanimo.fi/fi/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "SUNBORN.HE": {
        "url": "https://www.sbih.group/investor-contacts",
        "type": "ir",
        "note": "manual: investor relations contact",
    },
    "TALLINK.HE": {
        "url": "https://company.tallink.com/for-investors/investor-relations",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "TAMTRON.HE": {
        "url": "https://tamtrongroup.com/fi/sijoittajat/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "TEM1V.HE": {
        "url": "https://investors.tecnotree.com/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "TELIA1.HE": {
        "url": "https://www.teliacompany.com/en/investors",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "TULAV.HE": {
        "url": "https://tulikivigroup.com/sijoittajat/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "VERK.HE": {
        "url": "https://investors.verkkokauppa.com/",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "STEAV.HE": {
        "url": "https://www.storaenso.com/en/investors",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "STERV.HE": {
        "url": "https://www.storaenso.com/en/investors",
        "type": "ir",
        "note": "manual: investor relations landing",
    },
    "WITH.HE": {
        "url": "https://www.withsecure.com/fi/about-us/investor-relations",
        "type": "ir",
        "note": "manual: prefer FI investor relations page",
    },
    "VIK1V.HE": {
        "url": "https://www.vikingline.com/fi/sijoittajat/",
        "type": "ir",
        "note": "manual: prefer FI investors page",
    },
    "PON1V.HE": {
        "url": "https://www.ponsse.com/sijoittajat#/",
        "type": "ir",
        "note": "manual: general IR landing",
    },
    "PAMPALO.HE": {
        "url": "https://endomines.com/en/for-investors/endomines-as-an-investment/",
        "type": "ir",
        "note": "manual: Endomines Finland Oyj",
    },
}


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return "https://" + url
    return url


def _score_link(
    url: str, text: str | None, root_domain: str | None
) -> tuple[int, int, int]:
    url_l = url.lower()
    text_l = (text or "").lower()
    score = 0
    url_hits = 0
    text_hits = 0
    for kw in KEYWORDS:
        if kw in url_l:
            score += 4
            url_hits += 1
        if kw in text_l:
            score += 2
            text_hits += 1
    for pattern in KEYWORD_PATTERNS:
        if pattern.search(url_l):
            score += 3
            url_hits += 1
    if any(bad in url_l for bad in EXCLUDES):
        score -= 3
    if root_domain:
        try:
            if urlparse(url).netloc.endswith(root_domain):
                score += 1
        except Exception:
            pass
    if url_l.endswith(".pdf"):
        score -= 2
    return score, url_hits, text_hits


def _strip_trailing(url: str) -> str:
    return url.rstrip("/")


def _find_ir_link(website: str, session: requests.Session) -> str | None:
    try:
        resp = session.get(website, timeout=REQUEST_TIMEOUT)
        if resp.status_code >= 400:
            return None
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    root_domain = urlparse(website).netloc
    best_url = None
    best_score = 0
    best_url_hits = 0
    best_text_hits = 0

    for link in soup.find_all("a"):
        href = link.get("href")
        if not href:
            continue
        if href.startswith("mailto:") or href.startswith("tel:"):
            continue
        absolute = urljoin(website, href)
        if not absolute.startswith("http"):
            continue
        score, url_hits, text_hits = _score_link(
            absolute, link.get_text(strip=True), root_domain
        )
        if score > best_score:
            best_score = score
            best_url_hits = url_hits
            best_text_hits = text_hits
            best_url = absolute

    if best_score <= 0:
        return None
    if best_url_hits > 0:
        return best_url
    if best_text_hits > 0 and best_url:
        base = _strip_trailing(website)
        candidate = _strip_trailing(best_url)
        if candidate != base:
            return best_url
    return None


def _get_company_website(ticker: str) -> str | None:
    try:
        info = yf.Ticker(ticker).get_info()
        return info.get("website")
    except Exception:
        return None


def _nasdaq_share_url(ticker: str) -> str:
    slug = ticker.replace(".HE", "").lower()
    return f"https://www.nasdaq.com/european-market-activity/shares/{slug}"


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    stocks = payload.get("stocks", [])

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    website_cache: dict[str, str | None] = {}
    ir_cache: dict[str, str | None] = {}

    for idx, stock in enumerate(stocks, start=1):
        ticker = stock.get("ticker", "")

        if ticker in MANUAL_OVERRIDES:
            override = MANUAL_OVERRIDES[ticker]
            stock["ir_url"] = override["url"]
            stock["ir_type"] = override["type"]
            stock["ir_note"] = override["note"]
            stock["ir_source"] = "manual"
            continue

        website = _get_company_website(ticker)
        website = _normalize_url(website)
        if website in website_cache:
            website = website_cache[website]
        else:
            website_cache[website] = website

        ir_url = None
        if website:
            if website in ir_cache:
                ir_url = ir_cache[website]
            else:
                ir_url = _find_ir_link(website, session)
                ir_cache[website] = ir_url

        if ir_url:
            stock["ir_url"] = ir_url
            stock["ir_type"] = "ir"
            stock["ir_note"] = "auto: found investor link"
            stock["ir_source"] = "auto"
        elif website:
            stock["ir_url"] = website
            stock["ir_type"] = "company"
            stock["ir_note"] = "auto: company homepage fallback"
            stock["ir_source"] = "auto"
        else:
            stock["ir_url"] = _nasdaq_share_url(ticker)
            stock["ir_type"] = "nasdaq"
            stock["ir_note"] = "auto: nasdaq share page fallback"
            stock["ir_source"] = "auto"

        if idx % 10 == 0:
            time.sleep(REQUEST_DELAY)

    payload["metadata"]["updated"] = time.strftime("%Y-%m-%d")
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
