# Serbia Elections

Interaktivni dashboard izbornih rezultata Srbije — svaki parlamentarni ciklus 2000–2026 na svojoj ruti (`/parlamentarni-2023`…), sa mapom regiona i opština, dijasporom, raspodelom mandata, trendovima i istorijatom vlasti.

## Šta prikazuje

- **Mapa Srbije** — 5 RIK regiona bojenih po pobedniku i margini (≥10% / 5–10% / <5%); klik zumira na prave opštine; toggles za cifre populacije, pogled svih opština i trend strelice vs prethodni izbori
- **Dijaspora** — svetska mapa sa 81 ambasadom, boja po pobedniku svake stanice
- **Mandati** — polukružna raspodela (zvanična za završene, D'Hondt uživo), vladajuća koalicija u crvenom okviru, premijer(i) mandata
- **Stranke** — konzistentne brend boje kroz sve cikluse; liste razložene na stranke u legendi

## Tech stack

Next.js 16 · TypeScript · Tailwind · react-simple-maps — FastAPI · SQLAlchemy · psycopg — PostgreSQL (Neon) — Python collectori (RIK API, RIK XLS arhiva, RZS SDDB)
