# Keep-Alive Guide - Pitää sivuston hereillä 24/7

Railway/Vercel free tier sammuttaa sovelluksen jos ei käyttöä. Tämä pitää backendin hereillä.

---

## Ratkaisu 1: Cron-Job.org (SUOSITUS) ✅

**100% ILMAINEN, helppokäyttöinen**

### Setup (2 minuuttia):

1. **Mene:** https://cron-job.org/en/
2. **Luo tili** (ilmainen)
3. **Lisää uusi cronjob:**
   - **Title:** TradeMaster Pro Keep-Alive
   - **URL:** `https://your-backend.railway.app/health`
   - **Interval:** Every 5 minutes
   - **Status:** Enabled
4. **Tallenna**

✅ **Valmis!** Backend pysyy hereillä 24/7

---

## Ratkaisu 2: UptimeRobot (SUOSITUS) ✅

**100% ILMAINEN + Bonus: Saat alertit jos backend menee alas**

### Setup (2 minuuttia):

1. **Mene:** https://uptimerobot.com/
2. **Luo tili** (ilmainen)
3. **Add New Monitor:**
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** TradeMaster Pro Backend
   - **URL:** `https://your-backend.railway.app/health`
   - **Monitoring Interval:** 5 minutes
4. **Create Monitor**

**BONUS:**
- Saat email jos backend menee offline
- Näet uptime statistiikat
- 50 monitoria ilmaiseksi

---

## Ratkaisu 3: Cloudflare Workers (Advanced)

**Ilmainen, mutta vaatii enemmän setuppia**

### Luo worker:

```javascript
// TradeMaster Pro Keep-Alive Worker
addEventListener('scheduled', event => {
  event.waitUntil(handleScheduled(event.scheduledTime))
})

async function handleScheduled(scheduledTime) {
  // Ping backend health endpoint
  const backendUrl = 'https://your-backend.railway.app/health'
  
  try {
    const response = await fetch(backendUrl)
    const data = await response.json()
    
    console.log('Backend health check:', data.status)
    console.log('Timestamp:', scheduledTime)
    
    return new Response('OK', { status: 200 })
  } catch (error) {
    console.error('Backend health check failed:', error)
    return new Response('Error', { status: 500 })
  }
}
```

### Cron Trigger:
```
*/5 * * * *
```
(Every 5 minutes)

---

## Ratkaisu 4: GitHub Actions (Advanced)

**Ilmainen, jos käytät GitHubia**

Luo `.github/workflows/keep-alive.yml`:

```yaml
name: Keep-Alive

on:
  schedule:
    # Run every 5 minutes
    - cron: '*/5 * * * *'
  workflow_dispatch: # Allow manual trigger

jobs:
  keep-alive:
    runs-on: ubuntu-latest
    
    steps:
      - name: Ping Backend
        run: |
          echo "Pinging TradeMaster Pro backend..."
          response=$(curl -s -o /dev/null -w "%{http_code}" https://your-backend.railway.app/health)
          echo "Response code: $response"
          if [ $response -eq 200 ]; then
            echo "✅ Backend is alive"
          else
            echo "❌ Backend returned $response"
            exit 1
          fi
```

---

## Mikä ratkaisu valita?

| Ratkaisu | Helppous | Ilmainen | Ominaisuudet | Suositus |
|----------|----------|----------|--------------|----------|
| **Cron-Job.org** | ⭐⭐⭐⭐⭐ | ✅ | Perus ping | Paras aloittelijoille |
| **UptimeRobot** | ⭐⭐⭐⭐⭐ | ✅ | Ping + alertit | Paras tuotantoon |
| **Cloudflare Workers** | ⭐⭐⭐ | ✅ | Customizable | Jos osaat koodata |
| **GitHub Actions** | ⭐⭐ | ✅ | CI/CD integraatio | Jos käytät GitHubia |

---

## Testaa että toimii

1. **Odota 5 minuuttia**
2. **Tarkista Railway logeista:**
   ```
   GET /health 200 OK
   ```
3. **Tarkista Cron-Job.org / UptimeRobot:**
   - Status: Success
   - Response time: <500ms

---

## Miksi tämä on tärkeää?

### Railway Free Tier:
- **Sammuttaa backend** jos ei pyyntöjä 5-10 minuutissa
- **Cold start** vie 10-30 sekuntia
- **Ensimmäinen käyttäjä** saa hitaan kokemuksen

### Keep-Alive ratkaisu:
- ✅ Backend pysyy lämpimänä 24/7
- ✅ Nopea vastaus kaikille käyttäjille
- ✅ Background tasks (scheduler) toimii jatkuvasti
- ✅ AI picks päivittyy säännöllisesti

---

## Kustannukset

**100% ILMAINEN** kaikilla ratkaisuilla!

- Cron-Job.org: Ilmainen (10 cronjobsia)
- UptimeRobot: Ilmainen (50 monitoria)
- Cloudflare Workers: Ilmainen (100k requests/day)
- GitHub Actions: Ilmainen (2000 min/month)

---

## Advanced: Monitoring Dashboard

Jos haluat nähdä backendin tilan reaaliajassa:

### UptimeRobot Status Page:
1. Luo Public Status Page
2. Jaa URL: `https://status.yourdomain.com`
3. Käyttäjät näkevät onko backend ylhäällä

### Esimerkki:
```
TradeMaster Pro Status

Backend API: ✅ Operational (99.9% uptime)
Last check: 2 minutes ago
Response time: 150ms
```

---

**Suositus:** Aloita UptimeRobotilla → helppo setup + bonusina alertit!

---

**Lisäohje:** Jos Railway sammuttaa backendin usein (>10 kertaa/päivä), harkitse päivitystä Pro-tilaukseen ($5/kk) joka poistaa cold startin kokonaan.
