"""
TradeMaster Pro - Stock Universe
=================================

Comprehensive list of stocks from S&P 500, NASDAQ, NYSE, and other major exchanges.
Primary universe loads from a generated data file when available.
"""

import json
import logging
from pathlib import Path

from .delisted_registry import get_delisted_tickers

logger = logging.getLogger(__name__)
_UNIVERSE_FILE = Path(__file__).resolve().parent.parent / "data" / "universe_tickers.json"
_NASDAQ_100_FILE = Path(__file__).resolve().parent.parent / "data" / "nasdaq_100_tickers.json"
_UNIVERSE_CACHE: list[str] | None = None
_NASDAQ_100_CACHE: list[str] | None = None


def _normalize_ticker(value: str) -> str:
    return value.strip().upper().replace(".", "-")


def _load_universe_file() -> list[str]:
    global _UNIVERSE_CACHE
    if _UNIVERSE_CACHE is not None:
        return list(_UNIVERSE_CACHE)

    if not _UNIVERSE_FILE.exists():
        _UNIVERSE_CACHE = []
        return []

    try:
        raw = json.loads(_UNIVERSE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to read universe tickers file: %s", exc)
        _UNIVERSE_CACHE = []
        return []

    if not isinstance(raw, list):
        logger.warning("Universe tickers file is not a list; ignoring.")
        _UNIVERSE_CACHE = []
        return []

    tickers = []
    for item in raw:
        if not isinstance(item, str):
            continue
        normalized = _normalize_ticker(item)
        if normalized:
            tickers.append(normalized)

    _UNIVERSE_CACHE = sorted(set(tickers))
    return list(_UNIVERSE_CACHE)


def _load_nasdaq_100_file() -> list[str]:
    global _NASDAQ_100_CACHE
    if _NASDAQ_100_CACHE is not None:
        return list(_NASDAQ_100_CACHE)

    if not _NASDAQ_100_FILE.exists():
        _NASDAQ_100_CACHE = []
        return []

    try:
        raw = json.loads(_NASDAQ_100_FILE.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        logger.warning("Failed to read NASDAQ 100 tickers file: %s", exc)
        _NASDAQ_100_CACHE = []
        return []

    if not isinstance(raw, list):
        logger.warning("NASDAQ 100 tickers file is not a list; ignoring.")
        _NASDAQ_100_CACHE = []
        return []

    tickers = []
    for item in raw:
        if not isinstance(item, str):
            continue
        normalized = _normalize_ticker(item)
        if normalized:
            tickers.append(normalized)

    _NASDAQ_100_CACHE = sorted(set(tickers))
    return list(_NASDAQ_100_CACHE)

# S&P 500 Stocks (Full List)
SP500_STOCKS = [
    "MMM", "AOS", "ABT", "ABBV", "ACN", "ADBE", "AMD", "AES", "AFL", "A", "APD", "ABNB",
    "AKAM", "ALB", "ARE", "ALGN", "ALLE", "LNT", "ALL", "GOOGL", "GOOG", "MO", "AMZN", "AMCR",
    "AEE", "AEP", "AXP", "AIG", "AMT", "AWK", "AMP", "AME", "AMGN", "APH", "ADI", "AON",
    "APA", "APO", "AAPL", "AMAT", "APTV", "ACGL", "ADM", "ANET", "AJG", "AIZ", "T", "ATO",
    "ADSK", "ADP", "AZO", "AVB", "AVY", "AXON", "BKR", "BALL", "BAC", "BAX", "BDX", "BRK-B",
    "BBY", "TECH", "BIIB", "BLK", "BX", "XYZ", "BK", "BA", "BKNG", "BSX", "BMY", "AVGO",
    "BR", "BRO", "BF-B", "BLDR", "BG", "BXP", "CHRW", "CDNS", "CZR", "CPT", "CPB", "COF",
    "CAH", "KMX", "CCL", "CARR", "CAT", "CBOE", "CBRE", "CDW", "COR", "CNC", "CNP", "CF",
    "CRL", "SCHW", "CHTR", "CVX", "CMG", "CB", "CHD", "CI", "CINF", "CTAS", "CSCO", "C",
    "CFG", "CLX", "CME", "CMS", "KO", "CTSH", "COIN", "CL", "CMCSA", "CAG", "COP", "ED",
    "STZ", "CEG", "COO", "CPRT", "GLW", "CPAY", "CTVA", "CSGP", "COST", "CTRA", "CRWD", "CCI",
    "CSX", "CMI", "CVS", "DHR", "DRI", "DDOG", "DVA", "DAY", "DECK", "DE", "DELL", "DAL",
    "DVN", "DXCM", "FANG", "DLR", "DG", "DLTR", "D", "DPZ", "DASH", "DOV", "DOW", "DHI",
    "DTE", "DUK", "DD", "EMN", "ETN", "EBAY", "ECL", "EIX", "EW", "EA", "ELV", "EMR",
    "ENPH", "ETR", "EOG", "EPAM", "EQT", "EFX", "EQIX", "EQR", "ERIE", "ESS", "EL", "EG",
    "EVRG", "ES", "EXC", "EXE", "EXPE", "EXPD", "EXR", "XOM", "FFIV", "FDS", "FICO", "FAST",
    "FRT", "FDX", "FIS", "FITB", "FSLR", "FE", "FI", "F", "FTNT", "FTV", "FOXA", "FOX",
    "BEN", "FCX", "GRMN", "IT", "GE", "GEHC", "GEV", "GEN", "GNRC", "GD", "GIS", "GM",
    "GPC", "GILD", "GPN", "GL", "GDDY", "GS", "HAL", "HIG", "HAS", "HCA", "DOC", "HSIC",
    "HSY", "HPE", "HLT", "HOLX", "HD", "HON", "HRL", "HST", "HWM", "HPQ", "HUBB", "HUM",
    "HBAN", "HII", "IBM", "IEX", "IDXX", "ITW", "INCY", "IR", "PODD", "INTC", "ICE", "IFF",
    "IP", "IPG", "INTU", "ISRG", "IVZ", "INVH", "IQV", "IRM", "JBHT", "JBL", "JKHY", "J",
    "JNJ", "JCI", "JPM", "K", "KVUE", "KDP", "KEY", "KEYS", "KMB", "KIM", "KMI", "KKR",
    "KLAC", "KHC", "KR", "LHX", "LH", "LRCX", "LW", "LVS", "LDOS", "LEN", "LII", "LLY",
    "LIN", "LYV", "LKQ", "LMT", "L", "LOW", "LULU", "LYB", "MTB", "MPC", "MKTX", "MAR",
    "MMC", "MLM", "MAS", "MA", "MTCH", "MKC", "MCD", "MCK", "MDT", "MRK", "META", "MET",
    "MTD", "MGM", "MCHP", "MU", "MSFT", "MAA", "MRNA", "MHK", "MOH", "TAP", "MDLZ", "MPWR",
    "MNST", "MCO", "MS", "MOS", "MSI", "MSCI", "NDAQ", "NTAP", "NFLX", "NEM", "NWSA", "NWS",
    "NEE", "NKE", "NI", "NDSN", "NSC", "NTRS", "NOC", "NCLH", "NRG", "NUE", "NVDA", "NVR",
    "NXPI", "ORLY", "OXY", "ODFL", "OMC", "ON", "OKE", "ORCL", "OTIS", "PCAR", "PKG", "PLTR",
    "PANW", "PSKY", "PH", "PAYX", "PAYC", "PYPL", "PNR", "PEP", "PFE", "PCG", "PM", "PSX",
    "PNW", "PNC", "POOL", "PPG", "PPL", "PFG", "PG", "PGR", "PLD", "PRU", "PEG", "PTC",
    "PSA", "PHM", "PWR", "QCOM", "DGX", "RL", "RJF", "RTX", "O", "REG", "REGN", "RF",
    "RSG", "RMD", "RVTY", "ROK", "ROL", "ROP", "ROST", "RCL", "SPGI", "CRM", "SBAC", "SLB",
    "STX", "SRE", "NOW", "SHW", "SPG", "SWKS", "SJM", "SW", "SNA", "SOLV", "SO", "LUV",
    "SWK", "SBUX", "STT", "STLD", "STE", "SYK", "SMCI", "SYF", "SNPS", "SYY", "TMUS", "TROW",
    "TTWO", "TPR", "TRGP", "TGT", "TEL", "TDY", "TER", "TSLA", "TXN", "TPL", "TXT", "TMO",
    "TJX", "TKO", "TTD", "TSCO", "TT", "TDG", "TRV", "TRMB", "TFC", "TYL", "TSN", "USB",
    "UBER", "UDR", "ULTA", "UNP", "UAL", "UPS", "URI", "UNH", "UHS", "VLO", "VTR", "VLTO",
    "VRSN", "VRSK", "VZ", "VRTX", "VTRS", "VICI", "V", "VST", "VMC", "WRB", "GWW", "WAB",
    "WBA", "WMT", "DIS", "WBD", "WM", "WAT", "WEC", "WFC", "WELL", "WST", "WDC", "WY",
    "WSM", "WMB", "WTW", "WDAY", "WYNN", "XEL", "XYL", "YUM", "ZBRA", "ZBH", "ZTS",
]
# NYSE Stocks (100+ major NYSE-listed companies)
NYSE_STOCKS = [
    "A", "AA", "AAM", "AAMI", "AAP", "AAT", "AAUC", "AB", "ABBV", "ABCB", "ABEV", "ABG",
    "ABM", "ABR", "ABT", "ACA", "ACCO", "ACEL", "ACHR", "ACI", "ACLO", "ACM", "ACN", "ACP",
    "ACR", "ACRE", "ACV", "ACVA", "AD", "ADC", "ADCT", "ADM", "ADNT", "ADT", "ADX", "AEE",
    "AEFC", "AEG", "AEM", "AEO", "AER", "AERO", "AES", "AESI", "AEXA", "AFB", "AFG", "AFGB",
    "AFGC", "AFGD", "AFGE", "AFL", "AG", "AGCO", "AGD", "AGI", "AGL", "AGM", "AGO", "AGRO",
    "AGX", "AHH", "AHL", "AHR", "AHT", "AI", "AIG", "AII", "AIIA", "AIN", "AIO", "AIR",
    "AIT", "AIV", "AIZ", "AIZN", "AJG", "AKA", "AKAF", "AKR", "AL", "ALB", "ALC", "ALEX",
    "ALG", "ALH", "ALIT", "ALK", "ALL", "ALLE", "ALLY", "ALSN", "ALTG", "ALUR", "ALV", "ALX",
    "AM", "AMBP", "AMBQ", "AMC", "AMCR", "AME", "AMG", "AMH", "AMN", "AMP", "AMPX", "AMPY",
    "AMR", "AMRC", "AMRZ", "AMT", "AMTB", "AMTD", "AMTM", "AMWL", "AMX", "AN", "ANDG", "ANET",
    "ANF", "ANGX", "ANRO", "ANVS", "AOD", "AOMD", "AOMN", "AOMR", "AON", "AORT", "AOS", "AP",
    "APAM", "APD", "APG", "APH", "APLE", "APO", "APOS", "APTV", "AQN", "AQNB", "AR", "ARCO",
    "ARDC", "ARDT", "ARE", "ARES", "ARI", "ARL", "ARLO", "ARMK", "AROC", "ARR", "ARW", "ARX",
    "AS", "ASA", "ASAN", "ASB", "ASBA", "ASC", "ASG", "ASGI", "ASGN", "ASH", "ASIC", "ASIX",
    "ASPN", "ASR", "ASX", "ATEN", "ATGE", "ATHM", "ATHS", "ATI", "ATKR", "ATMU", "ATO", "ATR",
    "ATS", "AU", "AUB", "AUNA", "AVA", "AVAL", "AVB", "AVBC", "AVD", "AVK", "AVNS", "AVNT",
    "AVTR", "AVY", "AWF", "AWI", "AWK", "AWP", "AWR", "AX", "AXIA", "AXL", "AXP", "AXR",
    "AXS", "AXTA", "AYI", "AZO", "AZZ", "B", "BA", "BABA", "BAC", "BAH", "BAK", "BALL",
    "BALY", "BAM", "BANC", "BAP", "BARK", "BAX", "BB", "BBAI", "BBAR", "BBBY", "BBD", "BBDC",
    "BBDO", "BBN", "BBT", "BBU", "BBUC", "BBVA", "BBW", "BBWI", "BBY", "BC", "BCAT", "BCC",
    "BCE", "BCGD", "BCH", "BCO", "BCS", "BCSF", "BCSM", "BCSS", "BCX", "BDC", "BDJ", "BDN",
    "BDX", "BE", "BEKE", "BEN", "BEP", "BEPC", "BEPH", "BEPI", "BEPJ", "BETA", "BFAM", "BFH",
    "BFK", "BFLY", "BFS", "BFZ", "BG", "BGB", "BGH", "BGR", "BGS", "BGSF", "BGSI", "BGT",
    "BGX", "BGY", "BH", "BHC", "BHE", "BHK", "BHP", "BHR", "BHV", "BHVN", "BILL", "BIO",
    "BIP", "BIPC", "BIPH", "BIPI", "BIPJ", "BIRK", "BIT", "BJ", "BK", "BKD", "BKE", "BKH",
    "BKKT", "BKN", "BKSY", "BKT", "BKU", "BKV", "BLCO", "BLD", "BLDR", "BLE", "BLK", "BLND",
    "BLSH", "BLW", "BLX", "BMA", "BME", "BMEZ", "BMI", "BMN", "BMO", "BMY", "BN", "BNED",
    "BNH", "BNJ", "BNL", "BNS", "BNT", "BNY", "BOC", "BOE", "BOH", "BOND", "BOOT", "BORR",
    "BOW", "BOX", "BP", "BPRE", "BR", "BRBR", "BRC", "BRCC", "BRCE", "BRIE", "BRO", "BROS",
    "BRSL", "BRSP", "BRT", "BRW", "BRX", "BSAC", "BSBR", "BSL", "BSM", "BST", "BSTZ", "BSX",
    "BTA", "BTE", "BTI", "BTO", "BTT", "BTU", "BTX", "BTZ", "BUD", "BUI", "BUR", "BURL",
    "BUXX", "BV", "BVN", "BW", "BWA", "BWG", "BWLP", "BWMX", "BWNB", "BWXT", "BX", "BXC",
    "BXMT", "BXMX", "BXP", "BXSL", "BY", "BYD", "BYM", "BZH", "C", "CAAP", "CABO", "CACI",
    "CADE", "CAE", "CAF", "CAG", "CAH", "CAL", "CALX", "CANG", "CAPL", "CARR", "CARS", "CAT",
    "CATO", "CAVA", "CB", "CBAN", "CBL", "CBNA", "CBRE", "CBT", "CBU", "CBZ", "CC", "CCI",
    "CCID", "CCIF", "CCJ", "CCK", "CCL", "CCM", "CCO", "CCS", "CCU", "CCZ", "CDE", "CDLR",
    "CDP", "CDRE", "CE", "CEE", "CEPU", "CF", "CFG", "CFND", "CFR", "CGAU", "CGV", "CHCT",
    "CHD", "CHE", "CHGG", "CHH", "CHMI", "CHPT", "CHT", "CHWY", "CI", "CIA", "CIB", "CICB",
    "CIEN", "CIF", "CIG", "CII", "CIM", "CIMN", "CIMO", "CIMP", "CINT", "CIO", "CION", "CIVI",
    "CL", "CLB", "CLCO", "CLDT", "CLF", "CLH", "CLPR", "CLS", "CLVT", "CLW", "CLX", "CM",
    "CMA", "CMBT", "CMC", "CMCM", "CMDB", "CMG", "CMI", "CMP", "CMPO", "CMRE", "CMS", "CMSA",
    "CMSC", "CMSD", "CMTG", "CMU", "CNA", "CNC", "CNF", "CNH",
]
# NASDAQ 100 + Additional NASDAQ Stocks
NASDAQ_STOCKS = [
    "AACB", "AACBR", "AACBU", "AACG", "AADR", "AAL", "AALG", "AAME", "AAOI", "AAON", "AAPB", "AAPD",
    "AAPG", "AAPL", "AAPU", "AARD", "AAUS", "AAVM", "AAXJ", "ABAT", "ABCL", "ABCS", "ABEO", "ABI",
    "ABIG", "ABL", "ABLLL", "ABLV", "ABLVW", "ABNB", "ABNG", "ABOS", "ABP", "ABPWW", "ABSI", "ABTC",
    "ABTS", "ABUS", "ABVC", "ABVE", "ABVEW", "ABVX", "ACAD", "ACB", "ACCL", "ACDC", "ACEP", "ACET",
    "ACFN", "ACGL", "ACGLN", "ACGLO", "ACHC", "ACHV", "ACIC", "ACIU", "ACIW", "ACLS", "ACLX", "ACMR",
    "ACNB", "ACNT", "ACOG", "ACON", "ACONW", "ACRS", "ACRV", "ACT", "ACTG", "ACTU", "ACWI", "ACWX",
    "ACXP", "ADAG", "ADAM", "ADAMG", "ADAMH", "ADAMI", "ADAML", "ADAMM", "ADAMN", "ADAMZ", "ADBE", "ADBG",
    "ADEA", "ADGM", "ADI", "ADIL", "ADMA", "ADP", "ADPT", "ADSE", "ADSEW", "ADSK", "ADTN", "ADTX",
    "ADUR", "ADUS", "ADV", "ADVB", "ADVM", "ADXN", "AEBI", "AEC", "AEHL", "AEHR", "AEI", "AEIS",
    "AEMD", "AENT", "AENTW", "AEP", "AERT", "AERTW", "AEVA", "AEVAW", "AEYE", "AFBI", "AFCG", "AFJK",
    "AFJKR", "AFJKU", "AFOS", "AFRI", "AFRIW", "AFRM", "AFSC", "AFYA", "AGAE", "AGCC", "AGEM", "AGEN",
    "AGGA", "AGH", "AGIO", "AGIX", "AGMH", "AGMI", "AGNC", "AGNCL", "AGNCM", "AGNCN", "AGNCO", "AGNCP",
    "AGNCZ", "AGNG", "AGRZ", "AGYS", "AGZD", "AHCO", "AHG", "AHMA", "AIA", "AIFD", "AIFF", "AIFU",
    "AIHS", "AIIO", "AIIOW", "AIMD", "AIMDW", "AIOT", "AIP", "AIPI", "AIPO", "AIQ", "AIRE", "AIRG",
    "AIRJ", "AIRJW", "AIRO", "AIRR", "AIRS", "AIRT", "AIRTP", "AISP", "AISPW", "AIXC", "AIXI", "AKAM",
    "AKAN", "AKBA", "AKRO", "AKTX", "ALAB", "ALAR", "ALBT", "ALCO", "ALCY", "ALCYU", "ALCYW", "ALDF",
    "ALDFU", "ALDFW", "ALDX", "ALEC", "ALF", "ALFUU", "ALFUW", "ALGM", "ALGN", "ALGS", "ALGT", "ALHC",
    "ALIL", "ALIS", "ALISR", "ALISU", "ALKS", "ALKT", "ALLO", "ALLR", "ALLT", "ALLW", "ALM", "ALMS",
    "ALMU", "ALNT", "ALNY", "ALOT", "ALPS", "ALRM", "ALRS", "ALT", "ALTI", "ALTO", "ALTS", "ALTY",
    "ALVO", "ALVOW", "ALXO", "ALZN", "AMAL", "AMAT", "AMBA", "AMBR", "AMCX", "AMD", "AMDD", "AMDG",
    "AMDL", "AMDU", "AMGN", "AMID", "AMIX", "AMKR", "AMLX", "AMOD", "AMODW", "AMPG", "AMPGW", "AMPH",
    "AMPL", "AMRK", "AMRN", "AMRX", "AMSC", "AMSF", "AMST", "AMTX", "AMUN", "AMUU", "AMWD", "AMYY",
    "AMZD", "AMZN", "AMZU", "AMZZ", "ANAB", "ANDE", "ANEB", "ANEL", "ANGH", "ANGHW", "ANGI", "ANGL",
    "ANGO", "ANIK", "ANIP", "ANIX", "ANL", "ANNA", "ANNAW", "ANNX", "ANPA", "ANSC", "ANSCU", "ANSCW",
    "ANTA", "ANTX", "ANY", "AOHY", "AOSL", "AOTG", "AOUT", "APA", "APAC", "APACR", "APACU", "APAD",
    "APADR", "APADU", "APED", "APEI", "APGE", "API", "APLD", "APLM", "APLMW", "APLS", "APLT", "APM",
    "APOG", "APP", "APPF", "APPN", "APPS", "APPX", "APRE", "APVO", "APWC", "APXT", "APXTU", "APXTW",
    "APYX", "AQB", "AQMS", "AQST", "AQWA", "ARAI", "ARAY", "ARBB", "ARBE", "ARBEW", "ARBK", "ARBKL",
    "ARCB", "ARCC", "ARCT", "ARDX", "AREB", "AREBW", "AREC", "ARGX", "ARHS", "ARKO", "ARKOW", "ARKR",
    "ARLP", "ARM", "ARMG", "AROW", "ARQ", "ARQQ", "ARQQW", "ARQT", "ARRY", "ARTL", "ARTNA", "ARTV",
    "ARTW", "ARVN", "ARVR", "ARWR", "ASBP", "ASBPW", "ASCI", "ASLE", "ASMB", "ASMG", "ASML", "ASND",
    "ASNS", "ASO", "ASPC", "ASPCR", "ASPCU", "ASPI", "ASPS", "ASPSW", "ASPSZ", "ASRT", "ASRV", "ASST",
    "ASTC", "ASTE", "ASTH", "ASTI", "ASTL", "ASTLW", "ASTS", "ASUR", "ASYS", "ATAI", "ATAT", "ATEC",
    "ATER", "ATEX", "ATGL", "ATHA", "ATHE", "ATHR", "ATII", "ATIIU", "ATIIW", "ATLC", "ATLCL", "ATLCP",
    "ATLCZ", "ATLN", "ATLO", "ATLX", "ATMC", "ATMCR", "ATMCU", "ATMCW", "ATMV", "ATMVR", "ATMVU", "ATNI",
    "ATOM", "ATON", "ATOS", "ATPC", "ATRA", "ATRC", "ATRO", "ATXG", "ATXS", "ATYR", "AUBN", "AUDC",
    "AUGO", "AUID", "AUMI", "AUPH", "AUR", "AURA", "AURE", "AUROW", "AUTL", "AUUD", "AUUDW", "AVAH",
    "AVAV", "AVBH", "AVBP", "AVDL", "AVGB", "AVGG", "AVGO", "AVGU", "AVGX", "AVIR", "AVL", "AVNW",
    "AVO", "AVPT", "AVR", "AVS", "AVT", "AVTX", "AVUQ", "AVX", "AVXC", "AVXL", "AVXX", "AWRE",
    "AXG", "AXGN", "AXIN", "AXINR", "AXINU", "AXON", "AXSM", "AXTI", "AYTU", "AZ", "AZI", "AZN",
    "AZTA", "AZYY", "BABX", "BACC", "BACCR", "BACCU", "BACQ", "BACQR", "BACQU", "BAER", "BAERW", "BAFE",
    "BAFN", "BAIG", "BAND", "BANF", "BANFP", "BANL", "BANR", "BANX", "BAOS", "BASG", "BASV", "BATRA",
    "BATRK", "BAYA", "BAYAR", "BAYAU", "BBB", "BBCP", "BBGI", "BBH", "BBIO", "BBLG", "BBLGW", "BBNX",
    "BBOT", "BBSI", "BBYY", "BCAB", "BCAL", "BCAR", "BCARU", "BCARW", "BCAX", "BCBP", "BCDA", "BCG",
    "BCGWW", "BCIC", "BCLO", "BCML", "BCPC", "BCRX", "BCTX", "BCTXW", "BCTXZ", "BCYC", "BDCI", "BDCIU",
    "BDCIW", "BDGS", "BDMD", "BDMDW", "BDRX", "BDSX", "BDTX", "BDVL", "BDYN", "BEAG", "BEAGR", "BEAGU",
    "BEAM", "BEAT", "BEATW", "BEEM", "BEEP", "BEEX", "BEEZ", "BELFA", "BELFB", "BELT", "BENF", "BENFW",
    "BETR", "BETRW", "BFC", "BFIN", "BFRG", "BFRGW", "BFRI", "BFRIW", "BFST", "BGC", "BGIN", "BGL",
    "BGLC", "BGLWW", "BGM", "BGMS", "BGMSP", "BGRN", "BGRO", "BHAT", "BHF", "BHFAL", "BHFAM", "BHFAN",
    "BHFAO", "BHFAP", "BHRB", "BHST", "BIAF", "BIAFW", "BIB", "BIDU", "BIIB", "BILI", "BIOA", "BIOX",
    "BIRD", "BIS", "BITF", "BITS", "BIVI", "BIVIW", "BIYA", "BJDX", "BJK", "BJRI", "BKCH", "BKHA",
    "BKHAR", "BKHAU", "BKNG", "BKR", "BKYI", "BL", "BLBD", "BLBX", "BLCN", "BLCR", "BLDP", "BLFS",
    "BLFY", "BLIN", "BLIV", "BLKB", "BLLN", "BLMN", "BLMZ", "BLNE", "BLNK", "BLRX", "BLSG", "BLTE",
    "BLUW", "BLUWU", "BLUWW", "BLZE", "BLZR", "BLZRU", "BLZRW", "BMAX", "BMBL", "BMDL", "BMEA", "BMGL",
    "BMHL", "BMNG", "BMR", "BMRA", "BMRC", "BMRN", "BNAI", "BNAIW", "BNBX", "BNC", "BNCWW", "BND",
    "BNDW", "BNDX", "BNGO", "BNKK", "BNR", "BNRG", "BNTC", "BNTX", "BNZI", "BNZIW", "BODI", "BOED",
    "BOEG", "BOEU", "BOF", "BOKF", "BOLD", "BOLT", "BON", "BOOM", "BOSC", "BOTJ", "BOTT", "BOTZ",
    "BOXL", "BPACU", "BPOP", "BPOPM", "BPRN", "BPYPM", "BPYPN", "BPYPO", "BPYPP", "BRAG", "BRBI", "BRCB",
    "BREM", "BRFH", "BRHY", "BRID", "BRKD", "BRKR", "BRKRP", "BRKU", "BRLS", "BRLSW", "BRLT", "BRNS",
    "BRNY", "BRR", "BRRR", "BRRWU", "BRRWW", "BRTR", "BRTX", "BRY", "BRZE", "BSAA", "BSAAR", "BSAAU",
    "BSBK", "BSCP", "BSCQ", "BSCR", "BSCS", "BSCT", "BSCU", "BSCV", "BSCW", "BSCX", "BSCY", "BSCZ",
    "BSET", "BSJP", "BSJQ", "BSJR", "BSJS", "BSJT", "BSJU", "BSJV", "BSJW", "BSJX", "BSLK", "BSLKW",
    "BSMP", "BSMQ", "BSMR", "BSMS", "BSMT", "BSMU", "BSMV", "BSMW", "BSMY", "BSMZ", "BSRR", "BSSX",
    "BSVN", "BSVO", "BSY", "BTAI", "BTBD", "BTBDW", "BTBT", "BTCS", "BTCT", "BTDR", "BTF", "BTFX",
    "BTGD", "BTM", "BTMD", "BTMWW", "BTOC", "BTOG", "BTQ", "BTSG", "BTSGU", "BTTC", "BU", "BUFC",
    "BUFI", "BUFM", "BUG", "BULD", "BULG", "BULL", "BULLW", "BULX", "BUSE", "BUSEP", "BUUU", "BVFL",
    "BVS", "BWAY", "BWB", "BWBBP", "BWEN", "BWFG", "BWIN", "BWMN", "BYAH", "BYFC", "BYND", "BYRN",
    "BYSI", "BZ", "BZAI", "BZAIW", "BZFD", "BZFDW", "BZUN", "CA", "CAAS", "CABA", "CABR", "CAC",
    "CACC", "CADL", "CAEP", "CAFG", "CAI", "CAIQ", "CAKE", "CALC", "CALI", "CALM", "CAMP", "CAMT",
    "CAN", "CANC", "CANQ", "CAPN", "CAPNR", "CAPNU", "CAPR", "CAPS", "CAPT", "CAPTW", "CAR", "CARE",
    "CARG", "CARL", "CART", "CARV", "CARY", "CARZ", "CASH", "CASI", "CASS", "CASY", "CATH", "CATY",
    "CBAT", "CBC", "CBFV", "CBIO", "CBK", "CBLL", "CBNK", "CBRL", "CBSH", "CBUS", "CCAP", "CCB",
    "CCBG", "CCC", "CCCC", "CCCX", "CCCXU", "CCCXW", "CCD", "CCEC", "CCEP", "CCFE", "CCG", "CCGWW",
    "CCHH", "CCII", "CCIIU", "CCIIW", "CCIX", "CCIXU", "CCIXW", "CCLD", "CCLDO", "CCNE", "CCNEP", "CCNR",
    "CCOI", "CCRN", "CCSB", "CCSI", "CCSO", "CCTG", "CD", "CDC", "CDIG", "CDIO", "CDIOW", "CDL",
    "CDLX", "CDNA", "CDNS", "CDRO", "CDROW", "CDT", "CDTG", "CDTTW", "CDTX", "CDW", "CDXS", "CDZI",
    "CDZIP", "CECO", "CEFA", "CEG", "CELC", "CELH", "CELU", "CELUW", "CELZ", "CENN", "CENT", "CENTA",
    "CENX", "CEP", "CEPF", "CEPI", "CEPO", "CEPT", "CEPV", "CERS", "CERT", "CETX", "CETY", "CEVA",
    "CFA", "CFBK", "CFFI", "CFFN", "CFLT", "CFO", "CG", "CGABL", "CGBD", "CGBDL", "CGC", "CGCT",
    "CGCTU", "CGCTW", "CGEM", "CGEN", "CGNT", "CGNX", "CGO", "CGON", "CGTL", "CGTX", "CHA", "CHAC",
    "CHACR", "CHACU", "CHAI", "CHAR", "CHARR", "CHARU", "CHCI", "CHCO", "CHDN", "CHEC", "CHECU", "CHECW",
    "CHEF", "CHGX", "CHI", "CHKP", "CHMG", "CHNR", "CHPG", "CHPGR", "CHPGU", "CHPS", "CHPX", "CHR",
    "CHRD", "CHRI", "CHRS", "CHRW", "CHSCL", "CHSCM", "CHSCN", "CHSCO", "CHSCP", "CHSN", "CHTR", "CHW",
    "CHY", "CHYM", "CIBR", "CIFR",
]
# International ADRs and Other Major Stocks (200+ more)
INTERNATIONAL_STOCKS = [
    # European ADRs
    "ASML", "NVO", "AZN", "SNY", "GSK", "NVS", "BP", "SHEL", "TTE", "EQNR",
    "SAP", "UL", "DEO", "RIO", "BHP", "VALE", "ABB", "SPOT", "SHOP",
    "ERIC", "NOK", "VOD", "TEF", "TI", "FTE", "ORAN", "CHL", "CHU", "PTR",
    "SNP", "CEO", "E", "IBN", "INFY", "WIT", "HDB", "PAC", "SAN",
    "BBVA", "BCS", "DB", "UBS", "CS", "BN", "RY", "TD", "BMO", "BNS",

    # Asian ADRs (80+ more valid tickers)
    "TSM", "BABA", "JD", "PDD", "BIDU", "NIO", "XPEV", "LI", "NTES", "BILI",
    "TME", "IQ", "VIPS", "ZTO", "YMM", "HTHT", "TCOM", "GDS", "KC", "FUTU",
    "TIGR", "MNSO", "DDL", "QFIN", "LX", "FINV", "MOMO", "YY", "WB", "GOTU",
    "EDU", "BEDU", "TEDU", "COE", "DL", "LITB", "PAGS", "STNE", "GLOB", "DESP",
    "VIST", "ARCO", "SBS", "TV", "SMT", "KB", "LPL", "SID", "GGB", "BBD",
    "BRFS", "ABEV", "CIG", "VIV",

    # Canadian & Australian Stocks (50+ more)
    "TD", "RY", "BNS", "BMO", "CM", "CNQ", "ENB", "TRP", "SU", "CVE",
    "CP", "CNR", "NTR", "BCE", "MFC", "SLF", "GWO", "POW", "BAM", "BEP",
    "TRI", "WCN", "CSU", "ATD", "DOL", "QSR", "L", "AEM",
    "FNV", "WPM", "OR", "BTG", "AUY", "KGC", "IAG", "AG", "HL", "CDE",

    # Emerging Markets (50+ more)
    "EWZ", "FXI", "MCHI", "KWEB", "ASHR", "GXC", "EWY", "EWW", "EWT", "INDA",
    "INDY", "PIN", "SMIN", "EWH", "EWS", "EIDO", "EPHE", "EZA", "ARGT", "ECH",
]

# Small & Mid Cap Growth Stocks (300+ additional high-momentum stocks)
SMALL_MID_CAP_STOCKS = [
    # High-Growth Small Caps
    "SOUN", "IONQ", "RGTI", "QUBT", "QBTS", "BBAI", "AIMD", "SSTI", "CISO", "NNOX",
    "EDIT", "CRSP", "NTLA", "BEAM", "VERV", "FATE", "BLUE", "SNDX", "LEGN", "DCPH",
    "KRTX", "ARVN", "VKTX", "RCKT", "REPL", "VNDA", "NKTX", "TGTX", "INZY", "MRUS",
    "CGEM", "SANA", "KYMR", "IMVT", "LYEL", "ACLX", "ATNM", "RUBY", "PGEN", "MCRB",

    # Fintech & Payments
    "PYPL", "AFRM", "UPST", "LC", "SOFI", "NU", "PAGS", "STNE", "LPRO",
    "FOUR", "BILL", "INTU", "GDDY", "CPAY", "GPN", "FIS", "FISV", "WEX", "EVTC",

    # Cybersecurity & Cloud
    "CRWD", "ZS", "OKTA", "NET", "PANW", "FTNT", "S", "DDOG", "MDB", "SNOW",
    "ESTC", "CFLT", "PATH", "GTLB", "DOCN", "FSLY", "AKAM", "FFIV", "CIEN", "JNPR",

    # E-commerce & Digital (valid tickers only)
    "SHOP", "MELI", "SE", "CPNG", "ETSY", "CVNA", "RVLV", "POSH",

    # EVs & Clean Energy (valid tickers only)
    "RIVN", "LCID", "FSR", "WKHS", "NKLA", "BLNK", "CHPT", "EVGO", "WBX",
    "PLUG", "FCEL", "BE", "BLDP", "CLSK", "RIOT", "MARA", "HUT", "BITF",
    "CIFR", "CORZ", "IREN", "BTBT", "WULF",

    # Cannabis & Alternative Health (valid US-listed tickers)
    "TLRY", "CGC", "CRON", "ACB", "HEXO", "OGI", "SNDL", "GRWG", "IIPR", "SMG",

    # Semiconductors & Hardware
    "NVDA", "AMD", "INTC", "AVGO", "QCOM", "TXN", "AMAT", "LRCX", "KLAC", "ASML",
    "MU", "NXPI", "MRVL", "ADI", "SWKS", "QRVO", "MPWR", "ON", "WOLF", "CRUS",
    "SITM", "RMBS", "FORM", "AEHR", "ACLS", "ALGM", "AOSL", "DIOD", "MTSI", "POWI",

    # Robotics & AI (valid tickers)
    "PLTR", "AI", "BBAI", "SOUN", "IONQ", "RGTI", "QUBT", "AVAV", "KTOS",
    "ISRG", "IRTC", "IRBT", "JOBY", "LILM", "EVTL", "ACHR", "EH",

    # Space & Defense (valid tickers)
    "RKLB", "ASTS", "SPCE", "ASTR", "LUNR", "SPIR", "SATS", "IRDM",
    "LMT", "NOC", "GD", "RTX", "BA", "TXT", "HII", "LHX", "KTOS",

    # Biotech Movers (valid tickers)
    "SAVA", "TBPH", "NVAX", "BNTX", "RXRX", "DNA", "SDGR", "TWST", "PACB",
    "EXAS", "TDOC", "DOCS", "ONEM", "SGFY",

    # Gaming & Entertainment (valid tickers)
    "RBLX", "U", "DKNG", "PENN", "RSI", "CZR", "LNW", "GENI", "FUBO",
    "TTWO", "ATVI", "SKLZ",

    # SaaS & Software (valid tickers)
    "VEEV", "TEAM", "HUBS", "TWLO", "RNG", "PCTY", "TENB", "QLYS",
    "VRNS", "NEWR", "SUMO", "DT", "BOX", "DBX", "SMAR",

    # Food & Beverage (valid tickers)
    "BYND", "TTCF", "OTLY", "KDP", "MNST", "CELH", "FIZZ", "UNFI", "SFM",

    # Real Estate Tech (valid tickers)
    "OPEN", "RDFN", "COMP", "EXPI", "Z",

    # Travel & Hospitality (valid tickers)
    "EXPE", "TRIP", "RCL", "CCL", "NCLH",

    # Fitness & Wellness (valid tickers)
    "PTON", "PLNT", "XPOF",
]

# Combine all stocks into master list (remove duplicates)
# IMPORTANT: Sort to ensure consistent order across API calls
ALL_STOCKS = sorted(list(set(SP500_STOCKS + NYSE_STOCKS + NASDAQ_STOCKS + INTERNATIONAL_STOCKS + SMALL_MID_CAP_STOCKS)))

# Sector mapping for categorization
SECTOR_MAPPING = {
    "tech": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AVGO", "ADBE", "CRM", "CSCO",
             "ORCL", "ACN", "IBM", "INTC", "AMD", "QCOM", "TXN", "AMAT", "ADI", "LRCX",
             "MU", "KLAC", "MCHP", "CDNS", "SNPS", "FTNT", "PANW", "KEYS", "ON",
             "PLTR", "COIN", "NET", "SNOW", "DDOG", "CRWD", "ZS", "OKTA", "MDB"],

    "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY",
               "DVN", "FANG", "HAL", "BKR", "CTRA", "APA", "TRGP", "WMB",
               "KMI", "OKE", "LNG", "BP", "SHEL", "TTE", "EQNR"],

    "healthcare": ["JNJ", "UNH", "PFE", "ABBV", "TMO", "MRK", "ABT", "DHR", "LLY", "BMY",
                   "AMGN", "GILD", "CVS", "CI", "ELV", "HUM", "CNC", "MCK", "CAH", "ABC",
                   "ISRG", "SYK", "BDX", "MDT", "BSX", "MRNA", "REGN", "VRTX", "BIIB"],

    "finance": ["JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP", "C", "USB",
                "PNC", "TFC", "COF", "BK", "STT", "CB", "TRV", "ALL", "PGR", "MET",
                "AIG", "PRU", "AFL", "V", "MA", "PYPL"],

    "consumer": ["AMZN", "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "TJX", "BKNG", "MAR",
                 "PG", "KO", "PEP", "COST", "WMT", "PM", "MO", "CL", "KMB", "EL",
                 "DIS", "NFLX", "CMCSA"],
}


def _filter_delisted(tickers):
    delisted = get_delisted_tickers()
    if not delisted:
        return tickers
    return [ticker for ticker in tickers if ticker not in delisted]

def get_all_stocks():
    """Return complete list of all stocks (delisted filtered)"""
    universe = _load_universe_file()
    source = universe if universe else ALL_STOCKS
    return sorted(_filter_delisted(source))

def get_sp500_stocks():
    """Return S&P 500 stocks"""
    return SP500_STOCKS

def get_nyse_stocks():
    """Return NYSE stocks"""
    return NYSE_STOCKS

def get_nasdaq_stocks():
    """Return NASDAQ stocks"""
    return NASDAQ_STOCKS

def get_nasdaq_100_stocks():
    """Return NASDAQ 100 stocks (from file when available)"""
    return _load_nasdaq_100_file()

def get_core_index_tickers():
    """Return S&P 500 + NASDAQ 100 tickers (normalized, deduped)."""
    core = []
    core.extend(get_sp500_stocks())
    core.extend(get_nasdaq_100_stocks())
    normalized = [_normalize_ticker(ticker) for ticker in core if isinstance(ticker, str)]
    return sorted({ticker for ticker in normalized if ticker})

def get_stocks_by_sector(sector: str):
    """Return stocks for a specific sector (delisted filtered)"""
    sector_list = SECTOR_MAPPING.get(sector.lower(), [])
    return _filter_delisted(sector_list)

def get_stock_count():
    """Return total number of unique stocks (delisted filtered)"""
    return len(get_all_stocks())

def get_detailed_stock_count():
    """Return detailed breakdown of stock counts by exchange"""
    total_with_duplicates = (
        len(SP500_STOCKS)
        + len(NYSE_STOCKS)
        + len(NASDAQ_STOCKS)
        + len(INTERNATIONAL_STOCKS)
        + len(SMALL_MID_CAP_STOCKS)
    )
    universe_file = _load_universe_file()
    return {
        "sp500": len(SP500_STOCKS),
        "nyse": len(NYSE_STOCKS),
        "nasdaq": len(NASDAQ_STOCKS),
        "nasdaq_100": len(get_nasdaq_100_stocks()),
        "international": len(INTERNATIONAL_STOCKS),
        "small_mid_cap": len(SMALL_MID_CAP_STOCKS),
        "total_unique": len(get_all_stocks()),
        "total_with_duplicates": total_with_duplicates,
        "universe_file": len(_filter_delisted(universe_file)) if universe_file else 0,
        "static_total_unique": len(ALL_STOCKS),
        "delisted_filtered": len(get_delisted_tickers())
    }
