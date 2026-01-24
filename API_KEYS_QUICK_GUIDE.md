# API-AVAINTEN HAKEMINEN - Pikaohjeet
## Tarvitset nämä Nordic-versiota varten

---

## 1️⃣ YLE API (Suomi) - PAKOLLINEN ⭐

**Aika:** 10 minuuttia
**Hinta:** Ilmainen
**URL:** https://developer.yle.fi/

### Vaiheet:

1. **Mene:** https://developer.yle.fi/
2. **Klikkaa:** "Rekisteröidy" (oikeassa yläkulmassa)
3. **Täytä lomake:**
   - Nimi
   - Sähköposti
   - Salasana
   - Organisaatio: Laita "Personal" tai oma nimesi
4. **Hyväksy** käyttöehdot
5. **Vahvista** sähköpostistasi
6. **Kirjaudu sisään:** https://developer.yle.fi/
7. **Luo uusi App:**
   - Klikkaa "My Apps" tai "Omat sovellukset"
   - Klikkaa "Luo uusi sovellus"
   - **App Name:** "TradeMaster Nordic"
   - **Description:** "Stock market news aggregation for Nordic markets"
8. **Kopioi ja tallenna:**
   - ✅ **App ID** (esim: `abcd1234`)
   - ✅ **App Key** (esim: `1234567890abcdef1234567890abcdef`)

**Tallenna nämä turvallisesti!**

---

## 2️⃣ NewsAPI - JO KÄYTÖSSÄ ✅

Sinulla on jo NewsAPI-avain US-versiota varten.

**Sama avain toimii Nordic-uutisille!**

Ei tarvitse tehdä mitään, käytämme samaa avainta.

---

## 3️⃣ Alpha Vantage - VALINNAINEN

**Aika:** 5 minuuttia
**Hinta:** Ilmainen (25 pyyntöä/päivä) tai $49.99/kk
**URL:** https://www.alphavantage.co/support/#api-key

### Jos haluat:

1. **Mene:** https://www.alphavantage.co/support/#api-key
2. **Täytä lomake** (pelkkä sähköposti riittää)
3. **Kopioi API Key** sähköpostista

**Huom:** Free tier (25 req/päivä) riittää testaamiseen.

---

## 4️⃣ EOD Historical Data - VALINNAINEN (Paras osakelistoille)

**Aika:** 10 minuuttia
**Hinta:** $19.99/kk (14 päivän trial)
**URL:** https://eodhistoricaldata.com/

### Jos haluat kaikki 540 osaketta helposti:

1. **Mene:** https://eodhistoricaldata.com/register
2. **Rekisteröidy**
3. **Valitse:** "All World" plan ($19.99/kk)
4. **14 päivän trial** ilmainen
5. **Kopioi API Key**

**Etu:** Saat kaikki Helsinki + Stockholm osakkeet yhdellä API-kutsulla.

---

## ✅ YHTEENVETO - Mitä Tarvitset NYT

### MVP (Ilmainen):
- ✅ **Yle API** - Hae tämä NYT (10 min)
- ✅ **NewsAPI** - Sinulla jo (käytä samaa)
- ✅ **yfinance** - Ei vaadi avainta

### Tuotanto (Maksullinen):
- ⚠️ **EOD Historical** - Hae myöhemmin ($19.99/kk)
- ⚠️ **Alpha Vantage** - Hae myöhemmin ($49.99/kk)

---

## 🎯 SEURAAVAT ASKELEET

1. **Hae Yle API -avaimet nyt** (10 min)
2. **Tallenna avaimet:**
   - App ID: ________________
   - App Key: ________________
3. **Palaa tänne ja kerro kun valmista!**

Sitten jatkamme koodin kanssa! 🚀
