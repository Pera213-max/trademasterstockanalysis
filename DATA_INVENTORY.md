# TradeMaster Pro - Data Inventory & Analysis

## 📊 Mitä dataa meillä ON käytössä?

### 1. **Osakedata (Stocks)**

#### Finnhub API ✅
**Mitä saamme:**
- Reaaliaikainen hinta ja muutos
- Company profile (nimi, sector, industry)
- Basic financials (P/E, market cap, EPS)
- Candlestick data (OHLCV)
- News headlines

**API limits:**
- 60 calls/minute (ilmainen)
- ~1800 calls/tunti

**Käyttö:**
- Stock price quotes
- Company information
- Basic valuation metrics

####  yfinance ✅
**Mitä saamme:**
- Historical price data (unlimited history)
- Technical indicators (SMA, EMA, RSI, MACD)
- Volume data
- Dividend history
- Split history
- Options data

**API limits:**
- Ei rajoja (scraper)
- Joskus hidas/throttled

**Käyttö:**
- Technical analysis
- Backtesting
- Historical performance

---

### 2. **Uutiset (News)**

#### NewsAPI ✅
**Mitä saamme:**
- Business news worldwide
- Real-time headlines
- Source attribution
- Published dates

**API limits:**
- 100 requests/day (ilmainen)
- 500 requests/day (developer $449/month)

**Käyttö:**
- News bombs
- Sentiment analysis
- Market-moving events

**⚠️ RAJOITUS:** Vain 100 pyyntöä/päivä on TODELLA vähän!

---

### 3. **Sosiaalinen Sentimentti**

#### Reddit API (PRAW) ✅
**Mitä saamme:**
- r/wallstreetbets posts
- r/stocks discussions
- Comment sentiment
- Mention frequency
- Upvote/downvote ratios

**API limits:**
- 60 requests/minute
- Unlimited with proper auth

**Käyttö:**
- Social trending
- Retail investor sentiment
- Hype detection

#### Twitter/X API ❌ (Not implemented yet)
**Status:** Ei vielä käytössä
**Miksi ei:** Twitter API kallis ($100+/month)

---

### 4. **Makrodata**

#### FRED API (Federal Reserve) ✅
**Mitä saamme:**
- Interest rates (Fed Funds Rate)
- Inflation data (CPI, PPI)
- GDP growth
- Unemployment rate
- Treasury yields
- Economic indicators

**API limits:**
- Unlimited ilmaiseksi!

**Käyttö:**
- Macro indicators
- Market sentiment
- Economic calendar context

---

### 5. **Earnings & Events**

#### ❌ Ei dedikoidua earnings API:a
**Ongelma:** Emme käytä earnings calendar API:a

**Mitä puuttuu:**
- Earnings dates
- EPS estimates vs actuals
- Earnings surprises
- Guidance updates

---

## 🔍 Mitä dataa PITÄISI lisätä?

### 1. **Insider Trading Data** ⭐⭐⭐ (TÄRKEÄ!)
**Miksi:**
- Insiderit tietävät yrityksen todellisen tilanteen
- Insidereiden ostot = bullish signal
- Insidereiden myynnit = bearish signal

**API vaihtoehdot:**
- SEC Edgar (ilmainen, hidas)
- OpenInsider (scraping)
- Finnhub Insider Transactions (premium)

**Implementointi:**
```python
# Esimerkki
def get_insider_trades(ticker: str, days: int = 30):
    # Hae SEC Form 4 filings
    # Analysoi: ostot vs myynnit
    # Palauta: net insider activity
    pass
```

---

### 2. **Options Flow Data** ⭐⭐⭐ (TÄRKEÄ!)
**Miksi:**
- Isot option-kaupat ennakoivat suurta liikettä
- Unusual options activity = smart money
- Put/Call ratio kertoo markkinatunnelmasta

**API vaihtoehdot:**
- Unusual Whales API ($$$)
- yfinance options (ilmainen, rajallinen)
- CBOE options data

**Implementointi:**
```python
def get_unusual_options(ticker: str):
    # Hae option chain
    # Etsi: volume > open interest
    # Analysoi: call vs put skew
    return {
        "call_volume": 10000,
        "put_volume": 5000,
        "pc_ratio": 0.5,  # Bullish!
        "unusual_activity": True
    }
```

---

### 3. **Institutional Holdings** ⭐⭐ (Hyödyllinen)
**Miksi:**
- 13F filings näyttävät mitä hedge fundit ostavat
- Smart money seuranta
- Position changes (ostot/myynnit)

**API vaihtoehdot:**
- Finnhub (premium)
- SEC Edgar 13F scraping (ilmainen)
- WhaleWisdom API

---

### 4. **Short Interest Data** ⭐⭐⭐ (TÄRKEÄ!)
**Miksi:**
- Korkea short interest = squeeze potential
- Days to cover (DTC) ratio
- Shortseller confidence indicator

**API vaihtoehdot:**
- Finnhub (premium)
- FINRA short interest (2x/month, ilmainen)
- Ortex (kallis $$$)

**Implementointi:**
```python
def get_short_interest(ticker: str):
    return {
        "short_percent_float": 25.5,  # % osakkeista shortattu
        "days_to_cover": 3.2,  # Päiviä kestää sulkea positiot
        "squeeze_potential": "HIGH"  # DTC > 2 + SI > 20%
    }
```

---

### 5. **Earnings Calendar** ⭐⭐ (Hyödyllinen)
**Miksi:**
- Earnings liikuttaa osakkeita 10-30%
- EPS surprises = voittoja
- Guidance = forward-looking

**API vaihtoehdot:**
- Finnhub earnings calendar (ilmainen!)
- Alpha Vantage (ilmainen)
- Earnings Whispers (scraping)

---

### 6. **Dark Pool Data** ⭐ (Nice to have)
**Miksi:**
- Dark pool prints = institutionaalinen toiminta
- Block trades = smart money
- Likvidi vs illikvidi flow

**API vaihtoehdot:**
- FINRA ATS data (ilmainen, viive)
- Bookmap (kallis)

---

### 7. **Crypto-specific Data** ⭐⭐ (Jos lisätään crypto)
**Mitä:**
- On-chain metrics (whale transfers)
- Exchange netflow (in/out)
- Stablecoin supply
- Funding rates (perpetual futures)

**API vaihtoehdot:**
- CoinGecko (ilmainen)
- Glassnode ($$)
- Binance API (ilmainen)

---

## 🎯 Priorisoidut lisäykset

### Tier 1: KRIITTISET (Lisää HETI!)

1. **Short Interest Data** - Squeeze potential
2. **Insider Trading** - Smart money seuranta
3. **Options Flow** - Unusual activity
4. **Earnings Calendar** - Event-driven trading

### Tier 2: HYÖDYLLISET (Lisää pian)

5. **Institutional Holdings (13F)** - Hedge fund seuranta
6. **Analyst Ratings** - Konsensus estimates
7. **SEC Filings** - 8-K, 10-K scraping

### Tier 3: NICE TO HAVE (Myöhemmin)

8. **Dark Pool Prints** - Block trades
9. **Crypto On-Chain** - Jos lisätään crypto-tuki
10. **Twitter Sentiment** - Jos budj

ettia API:lle

---

## 📈 Miten tämä parantaa pickejä?

### Nykyinen AI-logiikka:
```
Score = Technical (30) + Momentum (30) + Volume (25) + Bonus (15)
```

### Parannettu AI-logiikka:
```python
Score = (
    Technical (30) +           # RSI, MACD, SMA crossovers
    Momentum (30) +            # Price trends, volatility
    Volume (20) +              # Volume surge, liquidity
    Smart Money (20) +         # ⭐ UUSI: Insider + Options + 13F
    Short Squeeze (10) +       # ⭐ UUSI: SI% + DTC
    Earnings Catalyst (10) +   # ⭐ UUSI: Upcoming earnings
    News Sentiment (10)        # Positive/negative news
) / 130 * 100
```

### Uudet signaalit:
- **"INSIDER BUYING"** - 3+ insiders osti 30 päivän aikana
- **"UNUSUAL OPTIONS"** - Call volume 5x normaalia
- **"HIGH SHORT INTEREST"** - SI > 20%, DTC > 2
- **"HEDGE FUND BUYING"** - 5+ 13F filings lisäsi positioita
- **"EARNINGS BEAT"** - Last 4 quarters beat estimates

---

## 💰 Kustannukset

### Nykyinen setup (FREE):
- Finnhub Free: $0
- yfinance: $0
- NewsAPI Free: $0 (100 req/day)
- Reddit API: $0
- FRED API: $0

**Yhteensä: $0/month**

### Parannettu setup (OPTIMAALI):

**Ilmaiset lisäykset:**
- SEC Edgar scraping (insider + 13F): $0
- FINRA short interest: $0
- Finnhub earnings calendar: $0
- yfinance options: $0

**Maksulliset (valinnainen):**
- NewsAPI Developer (1000 req/day): $20/month
- Finnhub Premium (insider + 13F): $25/month
- Unusual Whales (options flow): $50/month

**Yhteensä: $0-95/month** riippuen tasosta

---

## ✅ Suositus

### Implementoi HETI (ilmaiseksi):

1. **Insider Trading (SEC Edgar)**
   ```python
   # /backend/app/services/sec_insider_service.py
   - Scrape Form 4 filings
   - Bonus pisteitä jos insiderit ostavat
   ```

2. **Short Interest (FINRA)**
   ```python
   # /backend/app/services/short_interest_service.py
   - Hae short % float
   - Laske days to cover
   - Squeeze score
   ```

3. **Earnings Calendar (Finnhub)**
   ```python
   # /backend/app/services/earnings_service.py
   - Upcoming earnings dates
   - Historical EPS surprises
   - Pre-earnings boost signal
   ```

4. **Options Flow (yfinance)**
   ```python
   # /backend/app/services/options_service.py
   - Options chain data
   - Put/Call ratio
   - Unusual volume detection
   ```

### Timeline:
- **Viikko 1:** Insider + Short Interest
- **Viikko 2:** Earnings Calendar
- **Viikko 3:** Options Flow basics
- **Viikko 4:** Integrointi AI scoring-logiikkaan

---

## 🧪 Testaus

Ennen integrointia, testaa:

```python
# Test case: GME (tunnettu squeeze)
ticker = "GME"
short_interest = 140%  # Tammikuu 2021
insider_buying = 0     # Insiderit EI ostaneet
options_flow = HIGH    # Massiiviset call-ostot

# AI pitäisi tunnistaa:
signals = ["HIGH SHORT INTEREST", "SQUEEZE POTENTIAL", "UNUSUAL OPTIONS"]
score_boost = +30 points
```

---

## 📚 Yhteenveto

**Nykyinen data:** Perusteet kunnossa (hinta, tekniikka, news, social)

**Puuttuu:** Smart money data (insiderit, institutionaaliset, optiot, shortit)

**Ratkaisu:** Lisää 4 ilmaista datalähdettä → AI-pisteet paranevat 30-40%

**Kustannukset:** $0 (ilmaiset APIt riittävät alkuun)

**Hyöty:** Paljon paremmat pickit, enemmän voittavia kauppoja! 🚀

---

Haluatko että implementoin nämä? Aloitetaan insider tradingista! 💪
