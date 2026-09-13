# Serbia Elections

Interaktivni dashboard za praćenje izbornih rezultata u Srbiji. Klik na okrug prikazuje rezultate po opštinama, izlaznost i raspodelu glasova — podaci se osvežavaju automatski.

## Tech Stack

**Frontend:** Next.js 16, TypeScript, Tailwind CSS, react-simple-maps, SWR  
**Backend:** FastAPI, SQLAlchemy, psycopg  
**Baza:** PostgreSQL (Neon)  
**Collector:** Python — periodični job za RIK izvor

## Struktura

```
database/  — schema.sql, seed_demo_data.py
backend/   — FastAPI (GET /elections, /summary, /municipalities...)
collector/ — fetch_raw_results() + upsert u bazu
frontend/  — Next.js mapa Srbije (30 okruga) + live rezultati
```
