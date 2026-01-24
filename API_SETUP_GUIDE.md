# TradeMaster Pro - API Setup Guide

## 📋 Yleiskatsaus

TradeMaster Pro käyttää useita ilmaisia ja maksullisia API:ita osakedata, uutiset, sosiaalinen sentimentti, ja makrodata hakuun.

**Kustannukset:**
- **Täysin ilmainen**: Kaikki tärkeimmät API:t toimivat ilmaiseksi
- **Valinnainen premium**: NewsAPI Developer ($20/kk) jos haluat enemmän uutisia

---

## 🔑 API-avainten hankkiminen

### 1. **Finnhub API** ⭐ (PAKOLLINEN)

**Mitä tarjoaa:**
- Reaaliaikaiset osakekurssit
- Company profiles
- Basic financials (P/E, market cap, EPS)
- News headlines
- **Earnings calendar** (FREE!)

**Hinta:** Ilmainen (60 calls/min)

**Hankinta:**

1. Mene: https://finnhub.io/register
2. Luo ilmainen tili (email + salasana)
3. Vahvista sähköposti
4. Siirry Dashboard → API Key
5. Kopioi API-avain (esim. `cr1abc123xyz`)

**Esimerkki API-avain:**
```
cr1abc123xyz456def789ghi
```

**Rajoitukset:**
- 60 API calls / minuutti
- ~1800 calls / tunti
- Riittää hyvin TradeMaster Pro:lle!

---

### 2. **NewsAPI** ⭐ (SUOSITELTU)

**Mitä tarjoaa:**
- Business news headlines
- Real-time news
- Source attribution

**Hinta:**
- Free: 100 requests/day (LIMITED!)
- Developer: $20/month, 1000 requests/day

**Hankinta:**

1. Mene: https://newsapi.org/register
2. Luo ilmainen tili
3. Vahvista sähköposti
4. Kopioi API-avain

**Esimerkki API-avain:**
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

**HUOM:** Ilmainen versio (100 req/day) on rajallinen. Jos haluat enemmän uutisia, päivitä Developer-tiliin ($20/kk).

---

### 3. **Reddit API** ⭐ (SUOSITELTU)

**Mitä tarjoaa:**
- r/wallstreetbets posts
- r/stocks discussions
- Social sentiment
- Mention frequency

**Hinta:** Ilmainen (60 requests/min)

**Hankinta:**

1. **Luo Reddit-tili** (jos ei ole): https://www.reddit.com/register
2. **Luo Reddit App:**
   - Mene: https://www.reddit.com/prefs/apps
   - Scroll alas → "are you a developer? create an app..."
   - Klikkaa: **"create another app..."**
3. **Täytä lomake:**
   - Name: `TradeMaster Pro`
   - App type: Valitse **"script"**
   - Description: `Stock sentiment analysis`
   - About url: Jätä tyhjäksi
   - Redirect uri: `http://localhost:8000`
   - Klikkaa: **"create app"**
4. **Kopioi tiedot:**
   - **CLIENT_ID**: 14 merkkiä applin nimen alla (esim. `a1b2c3d4e5f6g7`)
   - **CLIENT_SECRET**: 27 merkkiä "secret" rivillä (esim. `ABCxyz123-_ABC123xyz456ABC`)

**Esimerkki:**
```
REDDIT_CLIENT_ID=a1b2c3d4e5f6g7
REDDIT_CLIENT_SECRET=ABCxyz123-_ABC123xyz456ABC
REDDIT_USER_AGENT=TradeMaster Pro v1.0
```

**REDDIT_USER_AGENT:** Vapaamuotoinen kuvaus (esim. "TradeMaster Pro v1.0")

---

### 4. **FRED API (Federal Reserve)** ✅ (VALINNAINEN)

**Mitä tarjoaa:**
- Interest rates
- Inflation data (CPI, PPI)
- GDP, unemployment
- Economic indicators

**Hinta:** Ilmainen, ei rajoituksia!

**Hankinta:**

1. Mene: https://fred.stlouisfed.org/
2. Klikkaa oikeassa yläkulmassa: **"My Account"** → **"API Keys"**
   - Tai suoraan: https://fredaccount.stlouisfed.org/apikeys
3. Luo ilmainen tili (email + salasana)
4. Klikkaa: **"Request API Key"**
5. Täytä lomake:
   - API Key Description: `TradeMaster Pro`
   - Agree to terms
6. Kopioi API-avain

**Esimerkki API-avain:**
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

---

### 5. **SEC Edgar** ✅ (Insider Trading - ILMAINEN)

**Mitä tarjoaa:**
- Insider trading data (Form 4 filings)
- 13F filings (institutional holdings)
- 8-K filings (major events)

**Hinta:** Ilmainen, julkinen data!

**Hankinta:**
- **EI tarvitse API-avainta!**
- Tarvitsee vain User-Agent headerin (jo koodissa)

**Esimerkki headeri (jo koodissa):**
```python
headers = {
    "User-Agent": "TradeMaster Pro trademasterpro@example.com"
}
```

**HUOM:** SEC vaatii User-Agent headerin, mutta ei API-avainta.

---

### 6. **FINRA Short Interest** ✅ (ILMAINEN)

**Mitä tarjoaa:**
- Short interest data (bi-monthly)
- Days to cover
- Short squeeze potential

**Hinta:** Ilmainen, julkinen data!

**Hankinta:**
- **EI tarvitse API-avainta!**
- Data julkaistaan 2x kuukaudessa FINRA sivuilla
- Voidaan scrapata tai käyttää Finnhub API:a

**HUOM:** FINRA data on julkista, mutta Finnhub API (premium) tarjoaa sen helpommin.

---

### 7. **yfinance** ✅ (ILMAINEN)

**Mitä tarjoaa:**
- Historical stock data
- Technical indicators (RSI, MACD, SMA)
- Options chain data
- Dividend history

**Hinta:** Ilmainen!

**Hankinta:**
- **EI tarvitse API-avainta!**
- Python library, ei API key tarvetta
- Scrapes Yahoo Finance

**Asennus:**
```bash
pip install yfinance
```

---

## 📝 .env Tiedoston Konfigurointi

### Backend .env (`/backend/.env`)

Luo tiedosto `/backend/.env` ja lisää seuraavat rivit:

```bash
# ===== REQUIRED APIs =====

# Finnhub (PAKOLLINEN - reaaliaikaiset hinnat, company data)
FINNHUB_API_KEY=your_finnhub_api_key_here

# ===== RECOMMENDED APIs =====

# NewsAPI (SUOSITELTU - uutiset)
# Free: 100 requests/day | Developer: 1000 requests/day ($20/month)
NEWS_API_KEY=your_newsapi_key_here

# Reddit API (SUOSITELTU - social sentiment)
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=TradeMaster Pro v1.0

# ===== OPTIONAL APIs =====

# FRED (VALINNAINEN - makrodata)
FRED_API_KEY=your_fred_api_key_here

# ===== NO API KEY NEEDED =====
# SEC Edgar - Insider Trading (ilmainen, ei API-avainta)
# FINRA - Short Interest (ilmainen, ei API-avainta)
# yfinance - Historical Data & Options (ilmainen, ei API-avainta)

# ===== OTHER SETTINGS =====

# Redis Cache (VALINNAINEN - production speed boost)
REDIS_URL=redis://localhost:6379/0

# Environment
ENV=development
```

---

## ✅ API Prioriteetti

### Tier 1: PAKOLLINEN (App ei toimi ilman)

1. **Finnhub** - Reaaliaikaiset hinnat, company data, earnings calendar

### Tier 2: SUOSITELTU (App toimii, mutta rajoitetusti)

2. **NewsAPI** - Uutiset (100 req/day ilmaiseksi)
3. **Reddit API** - Social sentiment

### Tier 3: VALINNAINEN (Nice to have)

4. **FRED API** - Makrodata

### Tier 4: ILMAISET (Ei API-avainta)

5. **SEC Edgar** - Insider trading
6. **FINRA** - Short interest
7. **yfinance** - Historical data & options

---

## 🧪 Testaa API-avaimia

### 1. Testaa Finnhub

```bash
curl "https://finnhub.io/api/v1/quote?symbol=AAPL&token=YOUR_FINNHUB_API_KEY"
```

**Odotettu vastaus:**
```json
{
  "c": 150.23,
  "h": 152.50,
  "l": 149.80,
  "o": 151.00,
  "pc": 149.50,
  "t": 1706212800
}
```

### 2. Testaa NewsAPI

```bash
curl "https://newsapi.org/v2/top-headlines?q=stocks&apiKey=YOUR_NEWSAPI_KEY"
```

**Odotettu vastaus:**
```json
{
  "status": "ok",
  "totalResults": 38,
  "articles": [...]
}
```

### 3. Testaa Reddit API

```python
import praw

reddit = praw.Reddit(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    user_agent="TradeMaster Pro v1.0"
)

# Test
print(reddit.read_only)  # Should print: True
subreddit = reddit.subreddit("wallstreetbets")
print(subreddit.display_name)  # Should print: wallstreetbets
```

### 4. Testaa FRED API

```bash
curl "https://api.stlouisfed.org/fred/series/observations?series_id=DFF&api_key=YOUR_FRED_API_KEY&file_type=json"
```

**Odotettu vastaus:**
```json
{
  "realtime_start": "2025-01-01",
  "realtime_end": "2025-01-01",
  "observation_start": "1954-07-01",
  "observation_end": "9999-12-31",
  "units": "lin",
  "output_type": 1,
  "file_type": "json",
  "order_by": "observation_date",
  "sort_order": "asc",
  "count": 17804,
  "offset": 0,
  "limit": 100000,
  "observations": [...]
}
```

---

## 🚀 Käynnistys oikeassa järjestyksessä

### 1. Asenna riippuvuudet

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 2. Konfiguroi .env

Luo `/backend/.env` tiedosto ja lisää API-avaimet (ks. yllä).

### 3. Käynnistä Backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Tarkista:**
- Backend pyörii: http://localhost:8000
- API docs: http://localhost:8000/docs

### 4. Käynnistä Frontend

```bash
cd frontend
npm run dev
```

**Tarkista:**
- Frontend pyörii: http://localhost:3000

### 5. Testaa App

Avaa selaimessa: http://localhost:3000

**Tarkista että:**
- AI Picks latautuu (näkyy osakkeita)
- Hidden Gems & Quick Wins näyttää dataa
- Top Movers päivittyy
- News Bombs näyttää uutisia
- Ei virheitä Consolessa (F12)

---

## 🐛 Yleisimmät Ongelmat

### Ongelma 1: "Invalid API key"

**Ratkaisu:**
1. Tarkista että API-avain on kopio-liitetty oikein (ei välilyöntejä)
2. Tarkista että .env tiedosto on oikeassa kansiossa (`/backend/.env`)
3. Käynnistä backend uudelleen (API-avaimet luetaan käynnistyksessä)

### Ongelma 2: "Rate limit exceeded"

**Ratkaisu:**
- Finnhub: 60 calls/min → Odota minuutti ja yritä uudelleen
- NewsAPI (free): 100 calls/day → Päivitä Developer-tiliin tai odota seuraavaa päivää

### Ongelma 3: "CORS error"

**Ratkaisu:**
Tarkista että backend pyörii portissa 8000:
```bash
# Backend TÄYTYY olla: http://localhost:8000
# Frontend TÄYTYY olla: http://localhost:3000
```

### Ongelma 4: "No data returned"

**Ratkaisu:**
1. Tarkista backend logi (console output)
2. Avaa http://localhost:8000/docs ja testaa API endpointteja manuaalisesti
3. Tarkista että .env tiedostossa on kaikki pakolliset API-avaimet

---

## 💰 Kustannukset yhteenveto

### Ilmainen Setup (Suositeltu aloittelijoille)

```
Finnhub Free:        $0/month  ✅
NewsAPI Free:        $0/month  ⚠️ (100 req/day)
Reddit API:          $0/month  ✅
FRED API:            $0/month  ✅
SEC Edgar:           $0/month  ✅
FINRA:               $0/month  ✅
yfinance:            $0/month  ✅
-----------------------------------
YHTEENSÄ:            $0/month
```

### Premium Setup (Tuotantokäyttöön)

```
Finnhub Free:        $0/month
NewsAPI Developer:   $20/month  (1000 req/day)
Reddit API:          $0/month
FRED API:            $0/month
SEC Edgar:           $0/month
FINRA:               $0/month
yfinance:            $0/month
-----------------------------------
YHTEENSÄ:            $20/month
```

### Enterprise Setup (Maksimaalinen data)

```
Finnhub Premium:     $25/month  (insider, 13F data)
NewsAPI Developer:   $20/month
Reddit API:          $0/month
FRED API:            $0/month
Unusual Whales:      $50/month  (options flow)
-----------------------------------
YHTEENSÄ:            $95/month
```

**Suositus:** Aloita ilmaisella setupilla. Päivitä premiumiin kun käyttäjämäärä kasvaa.

---

## 📚 API Dokumentaatio

### Finnhub
- Docs: https://finnhub.io/docs/api
- Rate limits: https://finnhub.io/pricing
- Status: https://status.finnhub.io/

### NewsAPI
- Docs: https://newsapi.org/docs
- Pricing: https://newsapi.org/pricing
- Dashboard: https://newsapi.org/account

### Reddit (PRAW)
- Docs: https://praw.readthedocs.io/
- Quickstart: https://praw.readthedocs.io/en/stable/getting_started/quick_start.html
- Reddit API: https://www.reddit.com/dev/api

### FRED
- Docs: https://fred.stlouisfed.org/docs/api/fred/
- API Keys: https://fredaccount.stlouisfed.org/apikeys

### yfinance
- Docs: https://pypi.org/project/yfinance/
- GitHub: https://github.com/ranaroussi/yfinance

---

## ✅ Yhteenveto

**Minimaalinen Setup (App toimii):**
1. Finnhub API Key (PAKOLLINEN)
2. NewsAPI Key (100 req/day)
3. Reddit API (Client ID + Secret)

**Käytä ilmaisia lähteitä:**
- SEC Edgar (insider trading) - Ei API-avainta!
- FINRA (short interest) - Ei API-avainta!
- yfinance (historical & options) - Ei API-avainta!

**Kustannukset:**
- Ilmainen: $0/month (riittää hyvin!)
- Premium: $20/month (NewsAPI Developer)

**Next Steps:**
1. Hanki API-avaimet (ks. ohjeet yllä)
2. Luo `/backend/.env` tiedosto
3. Lisää API-avaimet
4. Käynnistä backend ja frontend
5. Testaa että kaikki toimii!

---

Onko kysyttävää API-avaimista? Kerro niin autan! 🚀
