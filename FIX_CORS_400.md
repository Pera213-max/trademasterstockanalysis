# 🔧 FIX: CORS 400 Bad Request Errors

## ❌ ONGELMA:
```
OPTIONS /api/stocks/top-picks HTTP/1.1" 400 Bad Request
OPTIONS /api/news/newest HTTP/1.1" 400 Bad Request
```

Frontend-nordic (port 3001) ei saa yhteyttä backendiin (port 8000).

---

## ✅ RATKAISU:

### VAIHE 1: Pysäytä Backend

**PowerShellissä (backend-terminaalissa):**
```
Paina: Ctrl + C
```

---

### VAIHE 2: Tarkista .env-tiedosto

**Avaa:**
```
C:\Users\PerttuSipari\Documents\pera\backend\.env
```

**Etsi CORS_ORIGINS -rivi (noin rivi 6) ja varmista että se sisältää port 3001:**

✅ **Oikein:**
```env
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://localhost:3001"]
```

**Jos ei ole, lisää `"http://localhost:3001"` listaan!**

---

### VAIHE 3: Korjaa Yle API -rivit (JOS ei ole vielä korjannut)

**Etsi rivit ~60-64 ja varmista:**

✅ **Oikein (ei echo, ei lainausmerkkejä):**
```env
YLE_API_APP_ID=a08373729ce593af805b19ade1ec7402
YLE_API_APP_KEY=52a28373729ce593af805b19ade1ec7402
```

❌ **Väärin (poista jos on):**
```env
echo "YLE_API_APP_ID=...
```

**Tallenna tiedosto!**

---

### VAIHE 4: Käynnistä Backend uudestaan

```powershell
cd C:\Users\PerttuSipari\Documents\pera\backend
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Odotettu tulos (EI virheitä):**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
🚀 TradeMaster Pro API Starting...
🔒 CORS: Configured for localhost:3000, localhost:3001
```

---

### VAIHE 5: Päivitä Frontend-Nordic sivu

**Selaimessa (http://localhost:3001):**
```
Paina: F5 (Refresh)
```

---

## ✅ ODOTETTU TULOS:

**Backend-terminaalissa pitäisi nyt näkyä:**
```
INFO: 127.0.0.1:xxxxx - "GET /api/stocks/top-picks HTTP/1.1" 200 OK
INFO: 127.0.0.1:xxxxx - "GET /api/news/newest HTTP/1.1" 200 OK
```

**200 OK = Onnistui!** ✅
**400 Bad Request = CORS-virhe** ❌

---

## 🔍 MIKSI TÄMÄ TAPAHTUI?

1. Backend käynnistyi ennen kuin `.env` sisälsi `localhost:3001`
2. CORS-asetukset ladataan vain käynnistyksen yhteydessä
3. Backend pitää käynnistää uudestaan jotta uudet asetukset tulevat voimaan

---

## 📝 PIKAOHJE:

```powershell
# 1. Pysäytä backend (Ctrl+C)

# 2. Tarkista .env sisältää:
# CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://localhost:3001"]

# 3. Käynnistä backend uudestaan
cd C:\Users\PerttuSipari\Documents\pera\backend
py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 4. Päivitä frontend-nordic sivu (F5)
```

**Kerro kun backend käynnistyy uudestaan ilman virheitä!** 🚀
