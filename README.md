# Serbia Elections

Interaktivni dashboard za izborne rezultate — Srbija (5 RIK regiona), opštine unutar regiona i dijaspora (81 ambasada). Klik na region zumira i prikazuje opštine sa granicama, boje po margini pobednika.

## Tech Stack

**Frontend:** Next.js 16, TypeScript, Tailwind CSS, react-simple-maps, d3-geo, SWR  
**Backend:** FastAPI, SQLAlchemy, psycopg  
**Baza:** PostgreSQL (Neon) — regioni, opštine, biračka mesta, rezultati  
**Collector:** Python (requests, BeautifulSoup) — RIK cascading API

## Struktura

```
database/  — schema.sql (elections, municipalities, polling_stations, election_station_codes, results)
backend/   — FastAPI: /elections, /summary, /regions, /municipalities (+ leader/margin)
collector/ — rik_client.py, bootstrap.py, collector.py (po biračkom mestu, rate-limited)
frontend/  — Next.js:
             Serbiamap (5 regiona + 161 opština, Beograd 17), WorldMap (UN, dijaspora 81)
             tiered boje: sigurno ≥10% / umereno 5–10% / neizvesno <5% (šrafirano)
```
