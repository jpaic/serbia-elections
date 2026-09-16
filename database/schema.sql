-- Šema baze za izborni dashboard
-- PostgreSQL 14+

CREATE TABLE elections (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(50) UNIQUE,                   -- stabilan ključ dataseta: 'demo', 'parlamentarni-2023', ...
    name VARCHAR(200) NOT NULL,               -- npr. "Parlamentarni izbori 2026"
    election_type VARCHAR(50) NOT NULL,       -- 'parliamentary', 'presidential', 'local'
    election_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'upcoming', -- 'upcoming', 'live', 'closed'
    rik_type INTEGER,                          -- RIK election_type (1-4), npr. 2 = parlamentarni
    rik_round INTEGER UNIQUE,                  -- RIK election_round id (npr. 341140, 680072)
    prime_minister VARCHAR(150),                 -- predsednik Vlade formirane posle izbora
    pm_party VARCHAR(100),                       -- stranka premijera (kratka oznaka)
    prime_ministers JSONB,                       -- lanac premijera: [{name, party, period}] (npr. Vucevic -> Macut)
    registered_voters INTEGER,                  -- zvanicni nacionalni zbir kad opstinski nivo fali (2000)
    total_voted INTEGER,                         -- zvanicni nacionalni zbir kad opstinski nivo fali (2000)
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
    rik_code VARCHAR(30),                     -- stabilna fizička šifra (opciono), više nije UNIQUE po krugu
    name VARCHAR(200),
    address VARCHAR(300),
    registered_voters INTEGER,
    latitude NUMERIC(9,6),
    longitude NUMERIC(9,6),
    UNIQUE(municipality_id, name)
);

-- Mapa fizičko biračko mesto <-> RIK ID po izbornom krugu (RIK menja id svaki krug)
CREATE TABLE election_station_codes (
    election_id INTEGER NOT NULL REFERENCES elections(id) ON DELETE CASCADE,
    polling_station_id INTEGER NOT NULL REFERENCES polling_stations(id) ON DELETE CASCADE,
    rik_station_id INTEGER NOT NULL,          -- election_station id iz RIK API-ja (npr. 159757)
    PRIMARY KEY (election_id, polling_station_id),
    UNIQUE(election_id, rik_station_id)
);

CREATE TABLE parties (
    id SERIAL PRIMARY KEY,
    election_id INTEGER NOT NULL REFERENCES elections(id),
    name TEXT NOT NULL,                          -- RIK nazivi lista su dugački, VARCHAR(200) je prekratko
    short_name VARCHAR(50),
    ballot_number INTEGER,
    color_hex VARCHAR(7),                     -- za konzistentno bojenje na mapi/grafikonima
    is_minority BOOLEAN NOT NULL DEFAULT false, -- manjinske liste bez cenzusa u D'Hondtu
    official_seats INTEGER                      -- zvanična raspodela za zatvorene izbore (NULL = D'Hondt projekcija)
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

-- Mapiranje opština na RIK (region_id, municipality value) po krugu — za agregatni fetch
CREATE TABLE election_municipality_codes (
    election_id INTEGER NOT NULL REFERENCES elections(id) ON DELETE CASCADE,
    municipality_id INTEGER NOT NULL REFERENCES municipalities(id) ON DELETE CASCADE,
    rik_region_id INTEGER NOT NULL,
    rik_mun_value INTEGER NOT NULL,
    PRIMARY KEY (election_id, municipality_id),
    UNIQUE (election_id, rik_region_id, rik_mun_value)
);

-- Agregati po opštini (brzi refresh izborne noći: ~200 poziva umesto 8273)
CREATE TABLE municipality_stats (
    election_id INTEGER NOT NULL REFERENCES elections(id) ON DELETE CASCADE,
    municipality_id INTEGER NOT NULL REFERENCES municipalities(id) ON DELETE CASCADE,
    total_voted INTEGER,
    registered_voters INTEGER,
    valid_ballots INTEGER,
    invalid_ballots INTEGER,
    processed_stations INTEGER NOT NULL DEFAULT 0,
    total_stations INTEGER NOT NULL DEFAULT 0,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (election_id, municipality_id)
);

CREATE TABLE municipality_results (
    election_id INTEGER NOT NULL REFERENCES elections(id) ON DELETE CASCADE,
    municipality_id INTEGER NOT NULL REFERENCES municipalities(id) ON DELETE CASCADE,
    party_id INTEGER NOT NULL REFERENCES parties(id) ON DELETE CASCADE,
    votes INTEGER NOT NULL DEFAULT 0,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (election_id, municipality_id, party_id)
);

CREATE INDEX idx_munres_election ON municipality_results(election_id);
CREATE INDEX idx_munstats_election ON municipality_stats(election_id);

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
