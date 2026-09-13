-- Šema baze za izborni dashboard
-- PostgreSQL 14+

CREATE TABLE elections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,               -- npr. "Parlamentarni izbori 2026"
    election_type VARCHAR(50) NOT NULL,       -- 'parliamentary', 'presidential', 'local'
    election_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'upcoming', -- 'upcoming', 'live', 'closed'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE municipalities (
    id SERIAL PRIMARY KEY,
    rzs_code VARCHAR(20) UNIQUE,              -- šifra opštine iz RZS
    name VARCHAR(150) NOT NULL,
    region VARCHAR(150),                      -- upravni okrug
    population INTEGER,
    registered_voters INTEGER,
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6),
    geo_boundary JSONB                        -- GeoJSON geometrija (za mapu)
);

CREATE TABLE polling_stations (
    id SERIAL PRIMARY KEY,
    municipality_id INTEGER NOT NULL REFERENCES municipalities(id),
    rik_code VARCHAR(30) UNIQUE,              -- šifra biračkog mesta iz RIK-a
    name VARCHAR(200),
    address VARCHAR(300),
    registered_voters INTEGER,
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6)
);

CREATE TABLE parties (
    id SERIAL PRIMARY KEY,
    election_id INTEGER NOT NULL REFERENCES elections(id),
    name VARCHAR(200) NOT NULL,
    short_name VARCHAR(50),
    ballot_number INTEGER,
    color_hex VARCHAR(7)                      -- za konzistentno bojenje na mapi/grafikonima
);

-- Rezultati na nivou biračkog mesta (najgranularniji sloj, iz njega se agregira sve ostalo)
CREATE TABLE results (
    id BIGSERIAL PRIMARY KEY,
    election_id INTEGER NOT NULL REFERENCES elections(id),
    polling_station_id INTEGER NOT NULL REFERENCES polling_stations(id),
    party_id INTEGER NOT NULL REFERENCES parties(id),
    votes INTEGER NOT NULL DEFAULT 0,
    is_processed BOOLEAN NOT NULL DEFAULT false,   -- da li je RIK objavio rezultat za ovo mesto
    valid_ballots INTEGER,
    invalid_ballots INTEGER,
    total_voted INTEGER,                            -- za izračun izlaznosti tog mesta
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(election_id, polling_station_id, party_id)
);

CREATE INDEX idx_results_election ON results(election_id);
CREATE INDEX idx_results_station ON results(polling_station_id);
CREATE INDEX idx_stations_municipality ON polling_stations(municipality_id);

-- Log svakog povlačenja podataka sa RIK-a (za auditing i debug pipeline-a)
CREATE TABLE ingestion_log (
    id SERIAL PRIMARY KEY,
    election_id INTEGER REFERENCES elections(id),
    source VARCHAR(50) NOT NULL,             -- 'rik_api', 'rik_scrape', 'manual'
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    stations_updated INTEGER,
    success BOOLEAN,
    error_message TEXT
);
