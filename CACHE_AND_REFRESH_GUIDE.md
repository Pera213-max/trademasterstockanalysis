# TradeMaster Pro - Cache & Auto-Refresh Guide

## 📋 Yleiskatsaus

TradeMaster Pro käyttää älykästä cache-järjestelmää ja automaattista datanpäivitystä suorituskyvyn optimoimiseksi ja API-kutsujen vähentämiseksi.

---

## 🗄️ Caching System

### **Frontend Cache (React Query)**

TradeMaster Pro käyttää **TanStack React Query** (formerly React Query) kaikessa data fetchingissä.

**Mitä se tekee:**
- Cachettaa API-vastauksia muistiin
- Päivittää dataa automaattisesti taustalla
- Estää tuplakutsut samalle datalle
- Näyttää cached datan välittömästi (nopea UX!)

### **Backend Cache (In-Memory tai Redis)**

Backend voi käyttää kahta cache-metodia:

1. **In-Memory Cache** (Default, ilmainen)
   - Tallennetaan RAM-muistiin
   - Nollautuu palvelimen restarteissa
   - Riittää useimmille

2. **Redis Cache** (Valinnainen, production)
   - Ulkoinen cache-palvelin
   - Persistent (säilyy restarteissa)
   - Jaettu (toimii multi-server setupeissa)

---

## ⏱️ Cache TTL (Time-To-Live) - Kuinka kauan data säilyy?

### Frontend Cache Times

| Data Type | Stale Time | Refetch Interval | Perustelu |
|-----------|------------|------------------|-----------|
| **AI Picks** | 30 min | 5 min (inactive) | Ei muutu usein |
| **Hidden Gems** | 30 min | 5 min (inactive) | Analysointi kestää kauan |
| **Quick Wins** | 5 min | 1 min (inactive) | Day trading, muuttuu nopeasti |
| **Top Movers** | 5 min | 1 min (active) | Reaaliaikaiset muutokset |
| **News Bombs** | 10 min | 5 min (inactive) | Uutiset päivittyvät usein |
| **Stock Details** | 15 min | 5 min (inactive) | Yksittäinen osake-analyysi |
| **Stock Quote** | 1 min | 30 sec (active) | Hinnat muuttuvat jatkuvasti |
| **Social Trending** | 5 min | 2 min (inactive) | Reddit/Twitter sentimentti |

### Backend Cache Times

```python
# Backend cache TTL asetukset (.env)
CACHE_TTL_PRICES=60          # 1 min - Reaaliaikaiset hinnat
CACHE_TTL_PREDICTIONS=3600   # 1 tunti - AI-ennusteet
CACHE_TTL_SOCIAL=300         # 5 min - Sosiaalinen sentimentti
CACHE_TTL_NEWS=600           # 10 min - Uutiset
CACHE_TTL_MACRO=3600         # 1 tunti - Makrodata
```

---

## 🔄 Automaattinen Päivitys (Auto-Refresh)

### **React Query Refetch Strategies**

#### 1. **refetchOnWindowFocus** (Default: `true`)

**Mitä:** Päivittää datan automaattisesti kun palaat välilehteen

**Esimerkki:**
1. Avaa TradeMaster Pro
2. Vaihda toiseen välilehteen (esim. lukemaan uutisia)
3. Palaa TradeMaster Pro välilehteen
4. → **DATA PÄIVITTYY AUTOMAATTISESTI!**

```typescript
useQuery({
  queryKey: ['stock-picks'],
  queryFn: fetchStockPicks,
  refetchOnWindowFocus: true,  // ✅ Päivittyy kun tulet takaisin!
});
```

#### 2. **refetchInterval** (Aktiivinen toistoväli)

**Mitä:** Päivittää datan säännöllisesti kun sivu on aktiivinen

**Esimerkki: Top Movers (1 min interval)**

```typescript
useQuery({
  queryKey: ['top-movers'],
  queryFn: fetchTopMovers,
  refetchInterval: 60000,  // 60 sekuntia = 1 min
  refetchIntervalInBackground: false,  // Ei päivityksiä taustalla
});
```

**Milloin käytössä:**
- Top Movers: 1 min interval
- Market Pulse: 2 min interval
- News Bombs (jos aktiivinen): 5 min interval

#### 3. **Stale Time** (Vanhentumisaika)

**Mitä:** Kuinka kauan data katsotaan "tuoreeksi"

**Esimerkki:**

```typescript
useQuery({
  queryKey: ['ai-picks'],
  queryFn: fetchAIPicks,
  staleTime: 1000 * 60 * 30,  // 30 min = data on "fresh"
});
```

**Käytännössä:**
- Jos stale time = 30 min
- Avaat AI Picks → Fetch 12:00
- Avaat uudelleen 12:10 → **Ei fetchaa** (käyttää cachea)
- Avaat uudelleen 12:35 → **Fetchaa** (data vanhentunut)

---

## 🚀 Cache toiminta käytännössä

### **Skenaario 1: Dashboard Lataus**

1. **Ensimmäinen lataus:**
   - Frontend: Fetchaa kaikki komponentit
   - Backend: Laskee AI-scoret, hakee Finnhub, yfinance, news
   - Tallennetaan cache
   - **Latausaika: ~3-5 sekuntia**

2. **Toinen lataus (5 min sisällä):**
   - Frontend: Käyttää React Query cachea
   - Backend: Palauttaa cached data
   - **Latausaika: <1 sekunti** ⚡

3. **Lataus 35 min jälkeen:**
   - Frontend: Cache stale → fetchaa uudelleen
   - Backend: Cache vanhentunut → laskee uudelleen
   - **Latausaika: ~3-5 sekuntia**

### **Skenaario 2: View Analysis Klikkaus**

**Ennen (hidas):**
```typescript
// Fetched KAIKKI AI picks, sitten etsi yksi ticker
const allPicks = await fetchAllPicks();  // 5-10 sec
const stock = allPicks.find(pick => pick.ticker === 'NVDA');
```

**Nyt (nopea):**
```typescript
// Fetchaa SUORAAN yksi ticker
const stock = await fetchStockAnalysis('NVDA');  // <1 sec ⚡
```

**Cache:**
- Stale time: 15 min
- Jos klikkaat samaa osaketta 15 min sisällä → **instant load!**

---

## 📊 Muistinkäyttö

### **Frontend (Selain)**

**React Query Cache:**
- **Arvio**: 10-20 MB RAM (n. 500+ cached queries)
- **Maksimi**: 50 MB (garbage collection kicks in)
- **Vanhentuneet poistetaan**: Automaattisesti 5 min inaktiivisuuden jälkeen

**Kokonaismuisti (koko app):**
- **Idle (ei aktiivista dataa)**: ~150 MB
- **Active (paljon data latautuu)**: ~250-300 MB
- **Normaali käyttö**: ~200 MB

### **Backend (Server)**

#### In-Memory Cache:

```python
# Esimerkki cache koko
{
  "ai_picks:swing:10": 45 KB,
  "hidden_gems:10": 38 KB,
  "stock:NVDA": 12 KB,
  "news:market": 85 KB,
  # ... jne
}
```

**Arvio muistinkäytöstä:**
- **500 käyttäjää**: ~50-100 MB RAM
- **5000 käyttäjää**: ~500 MB - 1 GB RAM
- **Cleanup**: Vanhat entries poistetaan automaattisesti TTL:n mukaan

#### Redis Cache (Jos käytössä):

- **Koko**: Sama kuin in-memory
- **Hyödyt**: Jaettu, persistent
- **Kustannus**: +$5/kk (Upstash/Railway)

---

## 🔧 Cache Konfigurointi

### **Frontend - React Query Config**

Muokkaa `/frontend/lib/queryClient.ts`:

```typescript
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,        // 5 min default
      cacheTime: 1000 * 60 * 30,       // 30 min cache
      refetchOnWindowFocus: true,      // Päivitä kun tulet takaisin
      refetchOnReconnect: true,        // Päivitä kun netti palaa
      retry: 1,                        // Yritä 1 kertaa jos failaa
    },
  },
});
```

### **Backend - Cache TTL**

Muokkaa `/backend/.env`:

```bash
# Cache TTL (sekunteina)
CACHE_TTL_PRICES=60          # 1 min
CACHE_TTL_PREDICTIONS=1800   # 30 min (muutettu 3600 -> 1800)
CACHE_TTL_SOCIAL=300         # 5 min
CACHE_TTL_NEWS=600           # 10 min
CACHE_TTL_MACRO=3600         # 1 tunti
```

**Mitä muuttaa:**

- **Nopeampi data** (kustannuksella API calls):
  - Laske TTL arvoja (esim. 1800 → 900)

- **Vähemmän API calls** (hitaampi data):
  - Nosta TTL arvoja (esim. 1800 → 3600)

---

## 🎯 Auto-Refresh Toiminta Dashboardilla

### **Aktiivisena välilehdellä:**

| Komponentti | Refresh Interval | Huomio |
|-------------|------------------|--------|
| Market Pulse | 2 min | Live market status |
| Top Movers | 1 min | Reaaliaikaiset muutokset |
| News Bombs | 5 min | Uudet uutiset |
| Social Trending | 2 min | Reddit/Twitter |
| AI Picks | Ei automaattista | Päivittyy vain manuaalisesti / focus |
| Hidden Gems | Ei automaattista | Päivittyy vain manuaalisesti / focus |

### **Taustalla (inactive):**

- **EI PÄIVITÄ AUTOMAATTISESTI**
- Säästää resursseja
- Päivittyy kun tulet takaisin välilehteen

---

## 🔍 Miten tarkistaa että cache toimii?

### **Browser Developer Tools:**

1. Avaa DevTools (F12)
2. Siirry **Network** välilehteen
3. Päivitä sivu
4. Etsi API kutsut (esim. `/api/stocks/picks`)
5. Päivitä sivu uudelleen
6. Jos cached:
   - **Ei uutta API kutsua!** ✅
   - React Query palauttaa cached data
   - Network tab tyhjä (tai vain yksi kutsu taustalla)

### **React Query DevTools:**

**Asenna (Dev only):**

```bash
npm install @tanstack/react-query-devtools
```

**Lisää `/frontend/app/layout.tsx`:**

```typescript
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

<QueryClientProvider client={queryClient}>
  <ReactQueryDevtools initialIsOpen={false} />  {/* Bottom-right corner */}
  {children}
</QueryClientProvider>
```

**Käytä:**
- Näet kaikki cached queries
- Näet stale/fresh status
- Voit manuaalisesti invalidate cachea
- Näet refetch statuksen reaaliajassa

---

## ⚡ Optimointitippit

### **1. Pidennä stale time jos data ei muutu usein**

**Huono:**
```typescript
useQuery({
  queryKey: ['ai-picks'],
  staleTime: 1000 * 60,  // 1 min - liian lyhyt!
});
```

**Hyvä:**
```typescript
useQuery({
  queryKey: ['ai-picks'],
  staleTime: 1000 * 60 * 30,  // 30 min - sopiva!
});
```

### **2. Käytä prefetch kriittisille sivuille**

**Esimerkki: Stock Analysis**

```typescript
// Dashboard - prefetch AI picks scores
const { data: picks } = useQuery({
  queryKey: ['ai-picks'],
  queryFn: fetchAIPicks,
});

// Pre-fetch top 5 stock details
picks?.slice(0, 5).forEach((pick) => {
  queryClient.prefetchQuery({
    queryKey: ['stock-details', pick.ticker],
    queryFn: () => fetchStockDetails(pick.ticker),
  });
});
```

**Tulos**: Kun käyttäjä klikkaa View Analysis → **Instant load!**

### **3. Batch API calls kun mahdollista**

**Huono:**
```typescript
// 10 erillistä API kutsua
for (const ticker of tickers) {
  await fetch(`/api/stocks/${ticker}`);
}
```

**Hyvä:**
```typescript
// Yksi batch request
await fetch('/api/stocks/batch', {
  method: 'POST',
  body: JSON.stringify({ tickers }),
});
```

---

## 🐛 Yleisimmät Ongelmat

### **Ongelma 1: "Data ei päivity!"**

**Syy:** Cache stale time liian pitkä

**Ratkaisu:**
1. Lyhennä stale time
2. TAI käytä `refetchInterval`
3. TAI lisää manual refresh button

**Esimerkki:**
```typescript
const { refetch } = useQuery({...});

<button onClick={() => refetch()}>Refresh</button>
```

### **Ongelma 2: "Liian monta API kutsua!"**

**Syy:** Stale time liian lyhyt tai ei cachea ollenkaan

**Ratkaisu:**
- Nosta stale time
- Varmista että queryKey on sama (ei dynaaminen)

**Huono:**
```typescript
useQuery({
  queryKey: ['picks', new Date()],  // EI CACHEA!
});
```

**Hyvä:**
```typescript
useQuery({
  queryKey: ['picks'],  // Sama key = cache toimii
});
```

### **Ongelma 3: "Cache täyttyy (memory leak)"**

**Syy:** cacheTime liian pitkä

**Ratkaisu:**
- Laske cacheTime (default 30 min)
- React Query garbage collector poistaa automaattisesti

---

## 📊 Yhteenveto: Nykyinen Cache Setup

| Data | Frontend Stale | Frontend Cache | Backend TTL | Auto-Refresh |
|------|----------------|----------------|-------------|--------------|
| AI Picks | 30 min | 60 min | 30 min | Window focus |
| Hidden Gems | 30 min | 60 min | 30 min | Window focus |
| Quick Wins | 5 min | 15 min | 5 min | Window focus |
| Top Movers | 5 min | 10 min | 5 min | 1 min interval |
| News Bombs | 10 min | 20 min | 10 min | Window focus |
| Stock Details | 15 min | 30 min | 15 min | Window focus |
| Stock Quote | 1 min | 5 min | 1 min | 30 sec (if active) |
| Social | 5 min | 15 min | 5 min | 2 min interval |
| Macro | 60 min | 120 min | 60 min | Window focus |

**Muisti käyttö:**
- Frontend: ~200 MB (normal)
- Backend (500 users): ~100 MB
- Total: ~300 MB

**API Calls (500 käyttäjää / tunti):**
- Ilman cachea: ~50,000 calls
- Cachen kanssa: ~5,000 calls
- **Säästö: 90%!** 🎉

---

Onko kysyttävää cache-toiminnasta? Kerro niin autan! 🚀
