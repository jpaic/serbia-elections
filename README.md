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

## Izborna noć 2026 — samo pokreni

Dvoklik na `izbori-2026.bat` (ili ručno odozdo). Struktura je već povučena
(185 mesta mapirano); liste i rezultati se sami dopunjuju kad RIK objavi.

```bash
pip install -r collector/requirements.txt
python collector/bootstrap.py --election-type 2 --election-round 680072
python collector/aggregates.py --election-slug parlamentarni-2026 --interval 60
```

`DATABASE_URL` se čita iz `backend/.env` automatski — ništa ne mora da se exportuje.
Prekid (Ctrl+C) je bezbedan: sledeće pokretanje nastavlja gde je stalo.
