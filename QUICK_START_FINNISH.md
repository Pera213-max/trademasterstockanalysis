# 🚀 TradeMaster Pro - Pikaopas (Suomeksi)

## ✅ Valmista! API-avaimet lisätty!

Kaikki API-avaimet on nyt konfiguroitu ja **KAIKKI ominaisuudet ovat ilmaiseksi käytössä!** 🎉

### 📋 Mitä tehtiin:

✅ **Backend .env luotu** (`backend/.env`)
- Kaikki API-avaimesi lisätty (FRED, Reddit, Finnhub, NewsAPI, Alpha Vantage)
- Turvalliset SECRET_KEY ja JWT_SECRET generointu
- Feature flags: KAIKKI päälle (Hidden Gems, Quick Wins, AI Picks, jne.)
- Ei käyttörajoituksia (-1 = unlimited)

✅ **Frontend .env.local luotu** (`frontend/.env.local`)
- API URL konfiguroitu (localhost kehitykseen)
- Kaikki frontend-featuret päällä
- FREE_MODE=true (kaikki ilmaiseksi)

✅ **Kaikki ominaisuudet käytössä:**
- 💎 Hidden Gems (piilotetut helmet)
- ⚡ Quick Wins (päiväkauppatilaisuudet)
- 🎯 AI Stock Picks (rajoittamaton)
- 📊 Sector Analysis
- 🔥 Social Sentiment
- 📰 News Bombs
- 📈 Macro Indicators
- 📉 Backtesting
- 🌓 Dark/Light Mode

---

## 🎯 Seuraavat askeleet - YKSINKERTAISTETTU!

### Vaihe 1: Testaa paikallisesti (15 min)

#### 1.1 Käynnistä Backend

```bash
# Avaa terminaali 1
cd ~/pera/backend  # Tai missä projekti on

# Luo virtuaaliympäristö (jos ei ole vielä)
python3 -m venv venv

# Aktivoi virtuaaliympäristö
source venv/bin/activate    # Mac/Linux
# TAI
venv\Scripts\activate       # Windows

# Asenna riippuvuudet (ensimmäisellä kerralla)
pip install -r requirements.txt

# Käynnistä backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Pitäisi näkyä:
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Testaa selaimessa:**
- http://localhost:8000/health (pitäisi näyttää `{"status":"healthy"}`)
- http://localhost:8000/docs (Swagger API-dokumentaatio)

#### 1.2 Käynnistä Frontend

```bash
# Avaa terminaali 2 (pidä backend pyörimässä!)
cd ~/pera/frontend

# Asenna riippuvuudet (ensimmäisellä kerralla)
npm install

# Käynnistä frontend
npm run dev

# Pitäisi näkyä:
# ▲ Next.js 14.x.x
# - Local: http://localhost:3000
```

**Testaa selaimessa:**
- http://localhost:3000 (TradeMaster Pro dashboard)

#### 1.3 Kokeile kaikkia ominaisuuksia!

- ✅ Market Pulse näkyy
- ✅ Hidden Gems 💎 näkyy (premium feature!)
- ✅ Quick Wins ⚡ näkyy (premium feature!)
- ✅ AI Picks toimii
- ✅ Sector Picks toimii
- ✅ Dark mode toggle toimii
- ✅ Kaikki ladataan ilman virheitä

**Jos näet tyhjiä picks-kortteja:**
- Normaalia ensimmäisellä kerralla
- yfinance API voi olla hidas
- Odota 30-60 sekuntia
- Päivitä sivu (F5)

---

### Vaihe 2: Julkaise nettiin (30-60 min)

#### 2.1 Julkaise Backend Railway:hin

**A) Rekisteröidy:**
1. Mene: https://railway.app/
2. "Login" → "Continue with GitHub"
3. Anna Railway:lle pääsy repositorioon

**B) Luo projekti:**
1. "+ New Project"
2. "Deploy from GitHub repo"
3. Valitse `pera` repository
4. Root directory: `backend`
5. Railway alkaa buildaamaan automaattisesti

**C) Lisää ympäristömuuttujat:**
1. Valitse projekti → "Variables" välilehti
2. Kopioi **KAIKKI** muuttujat `backend/.env` tiedostosta
3. Paste Railway Variables -kenttään
4. Tallenna

**D) Lisää PostgreSQL:**
1. Samassa projektissa: "+ New"
2. "Database" → "Add PostgreSQL"
3. Kopioi DATABASE_URL
4. Lisää backend Variables:
   ```
   DATABASE_URL=postgresql://postgres:xxxxx@containers-us-west-xxx.railway.app:xxxx/railway
   ```

**E) Lisää Redis (Upstash - ilmainen):**
1. Mene: https://upstash.com/
2. "Sign Up" → GitHub-kirjautuminen
3. "Create Database" → Redis → Free tier
4. Kopioi:
   - REDIS_HOST
   - REDIS_PORT
   - REDIS_PASSWORD
5. Lisää Railway backend Variables

**F) Kopioi backend URL:**
1. Railway → Settings → "Generate Domain"
2. Saat URLin: `trademaster-backend-production.up.railway.app`
3. Kopioi tämä! Tarvitset seuraavassa vaiheessa.

**G) Testaa:**
```
https://SINUN-BACKEND-URL.railway.app/health
```
Pitäisi näyttää: `{"status":"healthy"}`

#### 2.2 Julkaise Frontend Verceliin

**A) Rekisteröidy:**
1. Mene: https://vercel.com/
2. "Sign Up" → "Continue with GitHub"

**B) Asenna Vercel CLI:**
```bash
npm install -g vercel
vercel login
```

**C) Julkaise:**
```bash
cd frontend
vercel

# Vastaa:
# Set up and deploy? Y
# Link to existing project? N
# Project name? trademaster-pro
# In which directory? ./
# Override settings? N

# Odota 2-5 min...
# Saat URLin: https://trademaster-pro-xxxxx.vercel.app
```

**D) Lisää ympäristömuuttujat Verceliin:**

1. Mene: https://vercel.com/dashboard
2. Valitse projektisi → Settings → Environment Variables
3. Lisää:

```bash
NEXT_PUBLIC_API_URL = https://SINUN-BACKEND-URL.railway.app
NEXT_PUBLIC_WS_URL = wss://SINUN-BACKEND-URL.railway.app/ws
NEXT_PUBLIC_ENABLE_DARK_MODE = true
NEXT_PUBLIC_ENABLE_HIDDEN_GEMS = true
NEXT_PUBLIC_ENABLE_QUICK_WINS = true
NEXT_PUBLIC_FREE_MODE = true
```

4. Tallenna → Redeploy:
```bash
vercel --prod
```

**E) Testaa tuotantoversio:**
```
https://trademaster-pro-xxxxx.vercel.app
```

Kaikki pitäisi toimia! 🎉

---

### Vaihe 3: Reddit-julkaisu (2-3 päivää myöhemmin)

#### 3.1 Testaa ensin perusteellisesti

- [ ] Backend toimii (ei virheitä logeissa)
- [ ] Frontend toimii (kaikki latautuu)
- [ ] Hidden Gems näyttää dataa
- [ ] Quick Wins näyttää dataa
- [ ] Ei kriittisiä bugeja
- [ ] Toimii mobiililla

#### 3.2 Kirjoita Reddit-postaus

**Otsikko:**
```
[Free Tool] TradeMaster Pro - AI Stock Picks with Hidden Gems Detection 💎
```

**Sisältö:**
```markdown
Hey! I built a free stock analysis tool and wanted to share it.

🚀 **What it does:**
- AI stock picks (day/swing/long-term)
- Hidden Gems: Finds mid/small-cap stocks before they blow up
- Quick Wins: Day trading opportunities with volume spikes
- Real-time heatmaps, social sentiment, news
- Clean UI with dark mode

💎 **Why it's different:**
Most platforms only show large-cap stocks. This finds opportunities
others miss - mid-caps with 30%+ growth and low analyst coverage.

🆓 **100% Free:**
No signup, no credit card, no BS. I might add paid features later
(alerts, API access), but core picks will stay free.

👉 **Try it:** https://YOUR-URL.vercel.app

Built with FastAPI + Next.js using free APIs (Yahoo Finance, FRED).

⚠️ Disclaimer: Educational tool only. Not financial advice. DYOR.

What features would you like to see added?
```

#### 3.3 Julkaise oikeaan aikaan

**Parhaat subredditit:**
- r/SideProject (250K) - tiistai 9-11 AM EST
- r/stocks (5.8M) - tiistai-torstai 9-11 AM EST
- r/investing (2.3M) - maanantai-keskiviikko 10 AM-12 PM EST
- r/Omatalous (40K) - maanantai-tiistai 18-20 (Suomen aika)

**Strategia:**
```
Päivä 1 (tiistai):
16:00 Suomen aikaa → Postaa r/SideProject
17:00 → Postaa r/stocks

Päivä 2 (keskiviikko):
18:00 Suomen aikaa → Postaa r/Omatalous

Päivä 3 (torstai):
16:00 → Postaa r/investing
```

#### 3.4 Vastaa KAIKKIIN kommentteihin

- Ensimmäiset 2 tuntia kriittisiä
- Ole ystävällinen ja kiitollinen
- Kysy palautetta aidosti
- Korjaa bugit nopeasti

---

## 📊 Mitä seurata

### Railway Backend (logs):
```
Railway → projektisi → Deployments → View Logs

Hyvät merkit:
✅ "Application startup complete"
✅ "INFO: Uvicorn running"
✅ Ei ERROR-rivejä

Huonot merkit:
❌ "ModuleNotFoundError"
❌ "Connection refused"
❌ Jatkuvat ERROR-viestit
```

### Vercel Frontend (analytics):
```
Vercel → projektisi → Analytics

Seuraa:
- Unique visitors (tavoite: 100+ ensimmäinen viikko)
- Page views (tavoite: 500+)
- Top pages (mikä on suosituin?)
```

### Tavoitteet ensimmäiselle viikolle:

- 🎯 100-500 unique visitors
- 🎯 50+ Reddit upvotes
- 🎯 10+ kommenttia
- 🎯 5-10 käyttäjää palaa toisen kerran
- 🎯 Muutama palautesähköposti/kommentti

---

## 🐛 Yleisimmät ongelmat

### Ongelma: Backend ei käynnisty paikallisesti

**Ratkaisu:**
```bash
# Varmista että olet backend-hakemistossa
cd backend

# Varmista että virtuaaliympäristö on aktiivinen
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Pitäisi näkyä (venv) komentorivin alussa

# Asenna riippuvuudet uudelleen
pip install --upgrade pip
pip install -r requirements.txt

# Yritä uudelleen
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Ongelma: Frontend ei näytä dataa

**Ratkaisu:**
```bash
# Tarkista että backend on käynnissä
curl http://localhost:8000/health

# Tarkista että API URL on oikein frontend/.env.local:
NEXT_PUBLIC_API_URL=http://localhost:8000

# Päivitä sivu (F5)
# Odota 30-60 sekuntia (yfinance voi olla hidas)
```

### Ongelma: "CORS error" selain-konsolissa

**Ratkaisu:**
```bash
# Tarkista backend/.env:
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Käynnistä backend uudelleen
# Ctrl+C (lopeta)
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Ongelma: Railway deployment epäonnistuu

**Ratkaisu:**
```bash
# Tarkista Railway Build Logs
# Yleisiä syitä:
# 1. Puuttuvia ympäristömuuttujia
# 2. requirements.txt virhe
# 3. Database URL puuttuu

# Varmista että KAIKKI backend/.env muuttujat on Railway Variablesissa
```

### Ongelma: Vercel deployment epäonnistuu

**Ratkaisu:**
```bash
# Tarkista Vercel Build Logs
# Yleisin syy: Node version

# Luo frontend/package.json viereen tiedosto: .nvmrc
# Sisältö: 18

# TAI lisää vercel.json:
{
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/next"
    }
  ]
}

# Redeploy:
vercel --prod
```

---

## 💰 Maksullinen versio myöhemmin (kuukausi 2-3)

### Milloin lisätä maksullinen?

✅ Kun sinulla on **500+ aktiivista käyttäjää**
✅ Kun ihmiset **pyytävät lisäominaisuuksia**
✅ Kun **engagement on korkea** (päivittäisiä käyttäjiä)
✅ Kun olet valmis **tukemaan** maksavia asiakkaita

### Mitä rajoittaa ilmaisessa?

**Ilmainen tier (aina ilmainen):**
- ✅ 10 AI picks/päivä
- ✅ Basic sector analysis
- ✅ Market overview
- ✅ News & events

**Pro tier ($19-49/kk):**
- ✅ Unlimited AI picks
- ✅ Hidden Gems 💎
- ✅ Quick Wins ⚡
- ✅ Email alerts
- ✅ Export data

**Premium tier ($49-99/kk):**
- ✅ Everything in Pro
- ✅ SMS alerts
- ✅ Portfolio tracking
- ✅ API access
- ✅ Priority support

### Miten rajoittaa?

**Muokkaa backend/.env:**
```bash
# Ilmaisen tierin rajoitukset
AI_PICKS_PER_DAY=10
HIDDEN_GEMS_PER_DAY=0
QUICK_WINS_PER_DAY=0
ENABLE_ALERTS=false
```

**Muokkaa frontend/.env.local:**
```bash
NEXT_PUBLIC_FREE_MODE=false
NEXT_PUBLIC_REQUIRE_AUTH=true
```

**Lisää Stripe:**
```bash
# Rekisteröidy: https://stripe.com
# Lisää avaimet:
STRIPE_SECRET_KEY=sk_live_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_...
```

---

## 🎉 Onnea!

Kaikki on nyt valmiina! Sinulla on:

✅ **Täysin toimiva TradeMaster Pro**
✅ **Kaikki API-avaimet konfiguroitu**
✅ **Kaikki premium-featuret ilmaiseksi**
✅ **Valmis julkaistavaksi Railwayhin + Verceliin**
✅ **Reddit-julkaisustrategia**

**Seuraavat askeleet:**

1. **Tänään**: Testaa paikallisesti
2. **Huomenna**: Julkaise tuotantoon
3. **Ylihuomenna**: Testaa tuotantoversio
4. **Viikon päästä**: Reddit-lanseeraus!

---

## 📞 Tarvitsetko apua?

Jos tulee ongelmia:

1. **Tarkista backend lokit** (Railway → View Logs)
2. **Tarkista frontend konsoli** (F12 → Console)
3. **Lue virheilmoitus** huolellisesti
4. **Google error message** (95% ongelmista löytyy netistä)

**Yleisimmät virheet on listattu yllä! ☝️**

---

**Tsemppiä lanseeraukseen! Tämä tulee olemaan huippu! 🚀💎⚡**

---

## 🔒 Turvallisuusmuistutus

**ÄLÄ KOSKAAN:**
- ❌ Commitoi .env tai .env.local tiedostoja Gitiin
- ❌ Jaa API-avaimia julkisesti
- ❌ Laita salaisia avaimia frontend-koodiin

**.env ja .env.local ovat jo .gitignoressa** ✅

Tiedostot on luotu paikallisesti koneellesi ja ne eivät mene Gitiin!

---

**P.S.** Muista päivittää Railway ja Vercel ympäristömuuttujat kun julkaiset! 🎯
