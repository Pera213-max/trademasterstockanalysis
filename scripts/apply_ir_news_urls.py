import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
TICKERS_PATH = ROOT / "backend" / "app" / "data" / "fi_tickers.json"
URLS_PATH = ROOT / "ir-url.md"


LEGAL_SUFFIXES = {
    "oyj",
    "abp",
    "plc",
    "ab",
    "oy",
    "group",
    "corporation",
    "corp",
    "limited",
    "ltd",
}

SHARE_SUFFIXES = {"a", "b", "c", "r", "1", "2"}

ALIASES = {
    "nordea": "NDA-FI.HE",
    "konecranes": "KCR.HE",
    "kone.com": "KNEBV.HE",
    "nokia": "NOKIA.HE",
    "sampo": "SAMPO.HE",
    "wartsila": "WRT1V.HE",
    "fortum": "FORTUM.HE",
    "neste": "NESTE.HE",
    "telia": "TELIA1.HE",
    "upm": "UPM.HE",
    "metso": "METSO.HE",
    "orion": "ORNBV.HE",
    "storaenso": "STERV.HE",
    "kesko": "KESKOB.HE",
    "elisa": "ELISA.HE",
    "valmet": "VALMT.HE",
    "mandatum": "MANTA.HE",
    "kojamo": "KOJAMO.HE",
    "outokumpu": "OUT1V.HE",
    "tietoevry": "TIETO.HE",
    "metsaboard": "METSB.HE",
    "vaisala": "VAIAS.HE",
    "sanoma": "SANOMA.HE",
    "nokiantyres": "TYRES.HE",
    "terveystalo": "TTALO.HE",
    "almamedia": "ALMA.HE",
    "puuilo": "PUUILO.HE",
    "bittium": "BITTI.HE",
    "fiskars": "FSKRS.HE",
    "aktia": "AKTIA.HE",
    "qt.io": "QTCOM.HE",
    "harvia": "HARVIA.HE",
    "alandsbanken": "ALBAV.HE",
    "citycon": "CTY1S.HE",
    "ponsse": "PON1V.HE",
    "yit": "YIT.HE",
    "finnair": "FIA1S.HE",
    "scanfil": "SCANFL.HE",
    "olvi": "OLVAS.HE",
    "evli": "EVLI.HE",
    "revenio": "REG1V.HE",
    "musti": "MUSTI.HE",
    "marimekko": "MEKKO.HE",
    "tokmanni": "TOKMAN.HE",
    "raisio": "RAIVV.HE",
    "omasp": "OMASP.HE",
    "lindex": "LINDEX.HE",
    "enento": "ENENTO.HE",
    "vikingline": "VIK1V.HE",
    "capman": "CAPMAN.HE",
    "f-secure": "FSECURE.HE",
    "withsecure": "WITH.HE",
    "incap": "ICP1V.HE",
    "canatu": "CANATU.HE",
    "anora": "ANORA.HE",
    "etteplan": "ETTE.HE",
    "faron": "FARON.HE",
    "taaleri": "TAALA.HE",
    "koskisen": "KOSKI.HE",
    "admicom": "ADMCM.HE",
    "aspo": "ASPO.HE",
    "duell": "DUELL.HE",
    "exelcomposites": "EXL1V.HE",
    "gofore": "GOFORE.HE",
    "unitedbankers": "UNITED.HE",
    "remedygames": "REMEDY.HE",
    "verkkokauppa": "VERK.HE",
    "noho": "NOHO.HE",
    "ssh": "SSH1V.HE",
    "talenom": "TNOM.HE",
    "hkfoods": "HKFOODS.HE",
    "nightingale": "NIGHTINGALE.HE",
    "solarfoods": "SFOODS.HE",
    "kreate": "KREATE.HE",
    "alexandria": "ALEX.HE",
    "lemonsoft": "LEMON.HE",
    "suominen": "SUY1V.HE",
    "ilkka": "ILKKA2.HE",
    "nanoform": "NANOFH.HE",
    "nexstim": "NXTMH.HE",
    "summa": "SUMMA.HE",
    "sitowise": "SITOWS.HE",
    "raute": "RAUTE.HE",
    "apetit": "APETIT.HE",
    "kamux": "KAMUX.HE",
    "consti": "CONSTI.HE",
    "aiforia": "AIFORIA.HE",
    "orthex": "ORTHEX.HE",
    "optomed": "OPTOMED.HE",
    "asuntosalkku": "ASUNTO.HE",
    "nurminen": "NLG1V.HE",
    "titanium": "TITAN.HE",
    "srv": "SRV1V.HE",
    "tecnotree": "TEM1V.HE",
    "afarak": "AFAGR.HE",
    "teleste": "TLT1V.HE",
    "viafin": "VIAFIN.HE",
    "loihde": "LOIHDE.HE",
    "enersense": "ESENSE.HE",
    "sotkamo": "SOSI1.HE",
    "lapwall": "LAPWALL.HE",
    "trainershouse": "TRH1V.HE",
    "martela": "MARAS.HE",
    "glaston": "GLA1V.HE",
    "heeros": "HEEROS.HE",
    "wetteri": "WETTERI.HE",
    "boreo": "BOREO.HE",
    "privanet": "PRIVANET.HE",
    "lassila-tikanoja": "LAT1V.HE",
    "lt.fi": "LAT1V.HE",
    "deetee.com": "DWF.HE",
}


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(cleaned.split())


def _company_key(name: str) -> str:
    tokens = [t for t in _normalize(name).split() if t not in LEGAL_SUFFIXES]
    if tokens and tokens[-1] in SHARE_SUFFIXES:
        tokens = tokens[:-1]
    return " ".join(tokens)


def _url_tokens(url: str) -> Tuple[str, List[str]]:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    combined = f"{host} {path}"
    tokens = [t for t in re.split(r"[^a-z0-9]+", combined) if t]
    return combined, tokens


def _score_url(url_text: str, url_tokens: List[str], stock: Dict[str, str]) -> int:
    score = 0
    ticker = stock["ticker"]
    slug = ticker.replace(".HE", "").lower()
    name = stock.get("name", "")
    name_key = _company_key(name)
    if slug and slug in url_tokens:
        score += 10
    if slug and slug in url_text:
        score += 5
    if name_key and name_key in url_text:
        score += 8
    for token in name_key.split():
        if len(token) < 4:
            continue
        if token in url_tokens:
            score += 3
        elif token in url_text:
            score += 1
    return score


def _extract_urls(lines: List[str]) -> List[str]:
    urls = []
    for line in lines:
        for match in re.findall(r"https?://\S+", line.strip()):
            url = match.rstrip(")")
            urls.append(url)
    return urls


def main() -> None:
    data = json.loads(TICKERS_PATH.read_text(encoding="utf-8"))
    stocks = data.get("stocks", [])

    name_groups: Dict[str, List[int]] = {}
    for idx, stock in enumerate(stocks):
        key = _company_key(stock.get("name", ""))
        if not key:
            continue
        name_groups.setdefault(key, []).append(idx)

    raw_lines = URLS_PATH.read_text(encoding="utf-8").splitlines()
    urls = _extract_urls(raw_lines)

    assigned = 0
    unmatched: List[str] = []
    used_urls: Dict[str, str] = {}

    for url in urls:
        url_text, tokens = _url_tokens(url)

        alias_match = None
        for key, ticker in ALIASES.items():
            if key in url_text:
                alias_match = ticker
                break

        best_score = 0
        best_index: Optional[int] = None
        if alias_match:
            for idx, stock in enumerate(stocks):
                if stock["ticker"] == alias_match:
                    best_index = idx
                    best_score = 999
                    break
        else:
            for idx, stock in enumerate(stocks):
                score = _score_url(url_text, tokens, stock)
                if score > best_score:
                    best_score = score
                    best_index = idx

        if best_index is None or best_score < 6:
            unmatched.append(url)
            continue

        stock = stocks[best_index]
        key = _company_key(stock.get("name", ""))
        target_indices = name_groups.get(key, [best_index])

        for idx in target_indices:
            stocks[idx]["ir_news_url"] = url
            stocks[idx]["ir_news_source"] = "ir-url.md"

        used_urls[url] = stock["ticker"]
        assigned += 1

    data["metadata"]["ir_news_updated"] = datetime.now(timezone.utc).date().isoformat()
    TICKERS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"URLs total: {len(urls)}")
    print(f"Assigned: {assigned}")
    print(f"Unmatched: {len(unmatched)}")
    if unmatched:
        print("Unmatched URLs:")
        for url in unmatched:
            print(f" - {url}")


if __name__ == "__main__":
    main()
