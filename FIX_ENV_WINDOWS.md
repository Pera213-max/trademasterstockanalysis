# ❌ FIX: .env Parse Error (Windowsissa)

## Ongelma:
```
Python-dotenv could not parse statement starting at line 60
Python-dotenv could not parse statement starting at line 62
Python-dotenv could not parse statement starting at line 63
Python-dotenv could not parse statement starting at line 64
```

## ✅ Ratkaisu:

### Vaihtoehto 1: Avaa ja korjaa .env (Suositus)

**Avaa Visual Studio Codella tai Notepadilla:**
```
C:\Users\PerttuSipari\Documents\pera\backend\.env
```

**Etsi rivit 60-64 ja tarkista:**

❌ **Väärin (ei saa olla lainausmerkkejä lopussa):**
```bash
echo "YLE_API_APP_ID=a08373729ce593af805b19ade1ec7402 >> .env
echo "YLE_API_APP_KEY=52a28373s >> .env
```

✅ **Oikein:**
```bash
YLE_API_APP_ID=a08373729ce593af805b19ade1ec7402
YLE_API_APP_KEY=52a28373729ce593af805b19ade1ec7402
```

**Poista kaikki ylimääräiset echo-komennot ja lainausmerkit!**

---

### Vaihtoehto 2: Korvaa koko tiedosto (Nopea)

**PowerShellissä:**

```powershell
cd C:\Users\PerttuSipari\Documents\pera\backend

# Lataa oikea .env GitHubista
git checkout origin/claude/trademaster-pro-continuation-01ULiZfC2QchyKuGGqReZAwt -- .env

# TAI kopioi tämä sisältö .env-tiedostoon:
```

**Kopioi ja liitä tämä `.env`-tiedostoon:**

```env
# Application
APP_NAME=TradeMaster Pro
DEBUG=True

# CORS - JSON array format
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://localhost:3001"]

# Database (optional)
DATABASE_URL=postgresql://user:pass@localhost:5432/trademaster

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_URL=redis://localhost:6379

# ===== REQUIRED API KEYS =====

# Finnhub (REQUIRED)
FINNHUB_API_KEY=d3ojvjpr01quo6o4mmn0d3ojvjpr01quo6o4mmng

# Reddit (REQUIRED)
REDDIT_CLIENT_ID=vZMJtKhK6rrAniSj9VUZRQ
REDDIT_CLIENT_SECRET=VeSdRxFSaY3setTSov532lal466Zrg
REDDIT_USER_AGENT=TradeMaster Pro 1.0

# NewsAPI (REQUIRED)
NEWS_API_KEY=b45cfa208bed43a9a2b510b290f8b5c5

# Polygon API
POLYGON_API_KEY=FSE13ZMl4yudBNi15WpFRMpQNeLVMC6y

# ===== OPTIONAL API KEYS =====

# FRED (Recommended)
FRED_API_KEY=bf4c30451ce80dad9a62d133e46be555

# Alpha Vantage (Optional)
ALPHA_VANTAGE_API_KEY=WX0MVARBJ7P9TH6G

# Binance (Optional)
BINANCE_API_KEY=
BINANCE_API_SECRET=

# Twitter (Optional)
TWITTER_API_KEY=E7jyWltCMOPwTqLKDIfwsNSo5
TWITTER_API_SECRET=rsxCRfg81JdJg8bIZeFo7G0bt8Xaa5BVySZHddlzp47rt5jkASs
TWITTER_BEARER_TOKEN=AAAAAAAAAAAAAAAAAAAAAM6u5QEAAAAAMhcmmx%2FWW%2B22CYQkvg%2Bpsqw61pc%3D2rLdmakXX5mF2Y1CocN7kAoL0CToDB2fgLM13gvLVtgqpnAOWw

# ===== NORDIC API KEYS =====

# Yle API (Nordic news)
YLE_API_APP_ID=a08373729ce593af805b19ade1ec7402
YLE_API_APP_KEY=52a28373729ce593af805b19ade1ec7402

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO

# Cache settings
CACHE_TTL_PRICES=60
CACHE_TTL_PREDICTIONS=3600
CACHE_TTL_SOCIAL=300
CACHE_TTL_NEWS=600
CACHE_TTL_MACRO=3600
```

**Tallenna ja käynnistä backend uudestaan.**

---

## ✅ Tarkista Korjaus:

**PowerShellissä:**
```powershell
# Pysäytä backend (Ctrl+C)

# Käynnistä uudestaan
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Ei pitäisi tulla virheitä!** ✅

---

## 🎯 Odotettu Tulos:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Started server process
INFO:     Application startup complete.
============================================================
🚀 TradeMaster Pro API Starting...
============================================================
📊 Version: 1.0.0
🌐 Docs: http://localhost:8000/docs
============================================================
```

**EI virheilmoituksia "Python-dotenv could not parse"!**

---

## ℹ️ Mikä Meni Vikaan?

Todennäköisesti lisäsit echo-komennot väärin:

❌ **Väärin:**
```powershell
echo "YLE_API_APP_ID=abc123 >> .env
```

Tämä jättää lainausmerkin alkuun ja ei sulje sitä!

✅ **Oikein:**
```powershell
echo YLE_API_APP_ID=abc123 >> .env
```

**TAI avaa .env editorissa ja kirjoita suoraan!**

---

Korjaa ja käynnistä uudestaan! 🚀
