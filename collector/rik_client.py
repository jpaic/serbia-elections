"""
RIK API klijent — centralizovana logika za cascading RIK endpoint-e.

Otkriveno discover.py:
  - get-elections:  POST election_type -> {"rounds": {"341140": "Парламентарни 2023"}}
  - get-regions:    POST election_type,election_round -> {"regions": {"1":"Београдски"...}, "data_id": ...}
  - get-municipalities: POST ... election_region -> HTML <option value="5" data-id="70157">...
  - get-election-stations: POST ... election_region,election_municipality -> {"election_stations": {"159757":"1 - OŠ..."}}
  - get_results:    POST ... [election_region][election_municipality][election_station] -> chart.js JSON

Važno:
  - RIK menja rik_station_id svaki izborni krug (isto fizičko mesto ima različit id 2023 vs 2026)
  - get_results filtrira samo na nivou biračkog mesta; region/opština vraćaju nacionalni zbir
  - rate limiting: sleep između poziva da ne preopteretimo RIK
"""
import time
import logging
import requests
from bs4 import BeautifulSoup

BASE = "https://www.rik.parlament.gov.rs"

HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en,sr;q=0.9",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": BASE,
    "referer": BASE + "/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}

log = logging.getLogger("rik_client")
DEFAULT_DELAY = 0.35  # sekundi između RIK poziva


def create_session() -> requests.Session:
    s = requests.Session()
    # početni GET da izvuče PHPSESSID
    try:
        s.get(f"{BASE}/", headers={"user-agent": HEADERS["user-agent"]}, timeout=15)
    except Exception as e:
        log.warning("Početni GET / nije uspeo: %s", e)
    return s


def _post(session: requests.Session, path: str, payload: dict, delay: float = DEFAULT_DELAY):
    if delay:
        time.sleep(delay)
    resp = session.post(f"{BASE}/{path}/", headers=HEADERS, data=payload, timeout=20)
    resp.raise_for_status()
    return resp


def get_elections(session: requests.Session, election_type: int) -> dict:
    resp = _post(session, "get-elections", {"election_type": election_type})
    try:
        return resp.json()
    except ValueError:
        return {}


def get_regions(session: requests.Session, election_type: int, election_round: int) -> dict:
    resp = _post(session, "get-regions", {"election_type": election_type, "election_round": election_round})
    return resp.json()


def get_municipalities(session: requests.Session, election_type: int, election_round: int, region_id: int) -> list[dict]:
    resp = _post(session, "get-municipalities", {
        "election_type": election_type,
        "election_round": election_round,
        "election_region": region_id,
    })
    # odgovor je HTML, ne JSON
    soup = BeautifulSoup(resp.text, "html.parser")
    out = []
    for opt in soup.find_all("option"):
        val = opt.get("value")
        data_id = opt.get("data-id")
        name = opt.get_text(strip=True)
        if not val:
            continue
        try:
            out.append({"value": int(val), "data_id": data_id, "name": name})
        except ValueError:
            continue
    return out


def get_election_stations(session: requests.Session, election_type: int, election_round: int, region_id: int, municipality_value: int) -> dict:
    resp = _post(session, "get-election-stations", {
        "election_type": election_type,
        "election_round": election_round,
        "election_region": region_id,
        "election_municipality": municipality_value,
    })
    data = resp.json()
    # {"election_stations": {"159757": "1 - OŠ ..."}}
    return data.get("election_stations") or {}


def get_results_raw(session: requests.Session, election_type: int, election_round: int, region_id=None, municipality_value=None, station_id=None) -> dict:
    payload = {"election_type": election_type, "election_round": election_round}
    if region_id is not None:
        payload["election_region"] = region_id
    if municipality_value is not None:
        payload["election_municipality"] = municipality_value
    if station_id is not None:
        payload["election_station"] = station_id
    resp = _post(session, "get_results", payload)
    # prazan 500 za 2026 bez rezultata
    if resp.status_code == 500 or not resp.text.strip():
        return {}
    try:
        return resp.json()
    except ValueError:
        return {}


# ---------- robustni parseri za get_results ----------

def _parse_int(s) -> int | None:
    if s is None:
        return None
    if isinstance(s, int):
        return s
    # "1.783.701" -> 1783701, "1,234" -> 1234
    cleaned = str(s).replace(".", "").replace(",", "").replace("\xa0", "").strip()
    if not cleaned or cleaned == "-":
        return 0
    try:
        return int(cleaned)
    except ValueError:
        try:
            return int(float(cleaned))
        except ValueError:
            return None


def parse_table_data(raw: dict) -> list[dict]:
    """Vraća listu {ballot_number, name, votes, pct, image} iz table_data. Radi i za chart.js ugnježdene forme."""
    if not raw:
        return []
    # direktan slučaj - table_data je glavni izvor
    rows = raw.get("table_data")
    if isinstance(rows, list) and rows:
        out = []
        for r in rows:
            out.append({
                "ballot_number": int(r.get("count_number") or 0),
                "name": (r.get("list_name") or "").strip(),
                "votes": _parse_int(r.get("won_number")),
                "pct": r.get("won_percent"),
                "image": r.get("list_image") or "",
            })
        return out
    # fallback: pokušaj iz pie chart data (retko, ali pokriva drugi oblik)
    for key in ("sum_config", "processed_config"):
        cfg = raw.get(key)
        if isinstance(cfg, dict):
            data = cfg.get("data", {}).get("datasets", [{}])[0].get("data") if isinstance(cfg.get("data"), dict) else None
            if data:
                return []  # chart data nema imena lista, ne koristi se za votes
    return []


def parse_stat_sum(raw: dict) -> dict:
    """Izvlači stat_sum_numbers + sum_config/processed_config u normalizovan oblik. Podržava oba oblika."""
    stat = raw.get("stat_sum_numbers") or {}
    # chart.js sums: sum_config.data.datasets[0].data = [valid, invalid]
    def extract_pie(cfg):
        if not isinstance(cfg, dict):
            return None
        # pokriva i {data:{datasets:[{data:[...]}]}} i {data:[...]} pojednostavljeno
        d = cfg.get("data")
        if isinstance(d, dict):
            ds = d.get("datasets")
            if isinstance(ds, list) and ds and isinstance(ds[0], dict):
                return ds[0].get("data")
        elif isinstance(d, list):
            return d
        return None

    valid_invalid = extract_pie(raw.get("sum_config"))
    turnout = extract_pie(raw.get("processed_config"))

    return {
        "total_voters": _parse_int(stat.get("total_voters")),
        "available": _parse_int(stat.get("available")),  # glasalo
        "processed_stations": _parse_int(stat.get("processed_stations")) or _parse_int(stat.get("number_of_stations")),
        "total_stations": _parse_int(stat.get("number_of_stations")),
        "valid": valid_invalid[0] if isinstance(valid_invalid, list) and len(valid_invalid) > 0 else None,
        "invalid": valid_invalid[1] if isinstance(valid_invalid, list) and len(valid_invalid) > 1 else None,
        "turnout_voted": turnout[1] if isinstance(turnout, list) and len(turnout) > 1 else None,
        "turnout_abstained": turnout[0] if isinstance(turnout, list) and len(turnout) > 0 else None,
        "datetime": stat.get("datetime"),
        "title": stat.get("election_title"),
    }
