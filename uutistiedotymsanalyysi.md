1) Perusarkkitehtuuri: “ingest → analysoi → cache → näytä”

Tavoite: et kutsu LLM:ää joka klikkauksella, vaan vain uusille tiedotteille/uutisille ja tallennat tulokset.

Ingest

Hae uudet tiedotteet / manager transactions / uutiset RSS:stä ja yhtiöiden IR-sivuilta.

Normalize

Muunna yhtenäiseen muotoon: ticker, company, timestamp, type, title, body, source_url.

Analyze (LLM)

Pyydä mallilta strukturoitu JSON: yhteenveto, vaikutus (pos/neu/neg/mixed), avainluvut, riskit, “what changed”.

Cache

Tallenna Supabase/Postgresiin. Sama tiedote analysoidaan vain kerran.

Serve

Frontend näyttää analyysin heti ja linkittää alkuperäiseen lähteeseen.

2) OpenAI API (ChatGPT) – toteutusperiaatteet
Avaimet ja turvallisuus

API-avain backendille ympäristömuuttujaksi (OPENAI_API_KEY) ja käytä Bearer-authia. 
platform.openai.com

Käytä OpenAI:n Responses APIa. 
platform.openai.com

 


Suositus käytännössä: käytä OpenAI:ta “tiivistykseen + numeropoimintaan + luokitteluun”, koska JSON-ulostulo on helppo UI:ssa.

3) Claude API – toteutusperiaatteet

Claudeen saat yhteyden Anthropic SDK:lla; se hoitaa headerit (x-api-key jne.). 
Claude Docs

 

Käyttöstrategia: Claude on usein erittäin hyvä pitkän tekstin tiivistämisessä. Voit käyttää:

Claude = “summary & reasoning”

OpenAI = “structured extraction & scoring”
tai päinvastoin. Tärkeintä on cache.

4) Mistä saat suomalaisista osakkeista datan ilmaiseksi
A) Pörssitiedotteet ja “insider”-tyyppinen data (Manager’s transactions)

Nasdaq Europe / Nordic tiedotteet (RSS + disclosure-sivut)

Nasdaq tarjoaa RSS-syötteitä “Main Markets Notices” ja “First North Notices”. 
subscribe.news.eu.nasdaq.com
+1

Huomio: RSS-pollauksen max-taajuus on 30 sekuntia (liian tiheä → voi blokata). 
subscribe.news.eu.nasdaq.com

“Managers’ transactions” -tiedotteet löytyvät Nasdaqin disclosure-sivuilta (newsclient.omxgroup.com), eli saat käytännössä sisäpiiriläisten kauppoja tiedotteina. 
newsclient.omxgroup.com
+1

Mitä rakennat:

RSS ingest → hae link → lataa disclosure HTML → parsitaan body text → LLM-analyysi.

B) Lyhyet positiot (short interest -tyyppinen)

Finanssivalvonta julkaisee voimassa olevat lyhyet positiot ja historiatiedot, tietyin kynnysarvoin. 
www.finanssivalvonta.fi
+1

Tämä on hyvä lisä Suomen osioon (“short pressure”, “bearish signal”).

C) Makrodata (Suomi)

BoF/FIN-FSA Open Data (boffsaopendata.fi)

Suomen Pankilla ja Finanssivalvonnalla on yhteinen avoin rajapintapalvelu; käyttö ei vaadi rekisteröitymistä. 
Suomen Pankki
+1

Täältä saat mm. korkoja, valuuttakursseja ja finanssiaikasarjoja.

Tilastokeskus PxWeb API

Tilastokeskuksen avoin PxWeb API (inflaatio, työllisyys, BKT jne.). 
pxdata.stat.fi
+1

D) Osakelista / ticker-mappaus (Helsinki)

Tarvitset luotettavan mappingin (yhtiö ↔ ticker ↔ ISIN).

Nasdaq OMX index -sivuilla (esim. OMXHPI weighting) on yhtiöitä ja symboleita listattuna. 
indexes.nasdaqomx.com

Lisäksi voit täydentää yhtiön omilta IR-sivuilta ISINin.

E) Hintadata ja perusfundamentit (ilmaiseksi)

Yahoo Finance / yfinance toimii usein Helsingin tickereille muodossa XXX.HE (viiveellinen data).

Tätä kannattaa käyttää fallbackina, mutta “virallisemmat” eventit (tiedotteet, manager transactions) tulee Nasdaqista/yhtiöiltä.

5) Konkreettiset käyttötapaukset: uutiset, tiedotteet, sisäpiiri
5.1 Tiedote-analyysi (Nasdaq + yhtiön IR)

LLM:n tuottama JSON:

impact: positive/neutral/negative/mixed

bullets: 3–6 syytä

key_metrics: poimitut numerot (Revenue, EBIT, guidance, dividend…)

risks: 1–6 riskiä

watch_items: mitä seurata seuraavaksi

UI: näytä “Impact”, bulletit, avainluvut, linkki tiedotteeseen.

5.2 Manager’s transactions (sisäpiiri)

Ingestoit “Managers’ transactions” tiedotteet Nasdaq disclosureista. 
newsclient.omxgroup.com
+1

LLM poimii: ostiko/myikö, määrä, hinta, euromäärä, rooli.

Tee signaali: “Net buying last 30d”, “Insider buy cluster”, “Sell after rally”.

5.3 Lyhyet positiot (FIVA)

Scrape/parse FIVA-taulukot (voimassa olevat + historia). 
www.finanssivalvonta.fi
+1

Näytä yhtiösivulla “Short positions ≥0.5%” ja trendi.

5.4 Uutiset

Ilmaisilla lähteillä:

Nasdaq company news feed (otsikot) + yhtiöiden IR

lisää myöhemmin yleisuutiset (rajalliset ilmaiset uutis-API:t ovat usein heikkoja)
LLM tekee “uutisvaikutus”-kortit samalla JSON-skeemalla.

6) Kustannusten hallinta (tärkeää)

Analysoi vain uudet eventit (tiedote/uutinen/transaktio), ei käyttäjän jokainen sivulataus.

Cache: event_hash (esim. sha256 tekstistä) → jos sama, älä analysoi uudestaan.

Rajoita pituus: lähetä max 10k–20k merkkiä (tai tee 2-vaiheinen: tiivistä → analysoi tiivistelmä).

Tee “priority queue”: isoille yhtiöille ja “price move” -päivinä analysoi ensin.