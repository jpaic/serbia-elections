"""Minimalni RIK live-fetch za backend (station on-demand).

Ne uvozi collector modul da Vercel deploy sa root=backend ostane samostalan.
Koristi KRATKE parametre (type/region/municipality/election_station) koji zaista filtriraju.
"""
import requests

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


def _parse_int(s):
    if s is None:
        return 0
    if isinstance(s, int):
        return s
    cleaned = str(s).replace(".", "").replace(",", "").replace("\xa0", "").strip()
    if not cleaned or cleaned == "-":
        return 0
    try:
        return int(cleaned)
    except ValueError:
        return 0


def fetch_station(election_type: int, election_round: int, region_id: int, mun_value: int, station_id: int, timeout: int = 15) -> dict:
    """Vraća {rows: [{ballot_number, name, votes}], stat: {...}} za jedno biračko mesto."""
    s = requests.Session()
    try:
        s.get(f"{BASE}/", headers={"user-agent": HEADERS["user-agent"]}, timeout=10)
    except Exception:
        pass
    resp = s.post(f"{BASE}/get_results/", headers=HEADERS, data={
        "type": election_type,
        "election_round": election_round,
        "region": region_id,
        "municipality": mun_value,
        "election_station": station_id,
    }, timeout=timeout)
    resp.raise_for_status()
    if resp.status_code == 500 or not resp.text.strip():
        return {"rows": [], "stat": {}}
    try:
        data = resp.json()
    except ValueError:
        return {"rows": [], "stat": {}}
    rows = []
    for r in data.get("table_data") or []:
        try:
            bn = int(r.get("count_number") or 0)
        except (ValueError, TypeError):
            continue
        rows.append({
            "ballot_number": bn,
            "name": (r.get("list_name") or "").strip(),
            "votes": _parse_int(r.get("won_number")),
        })
    st = data.get("stat_sum_numbers") or {}
    return {"rows": rows, "stat": {
        "available": _parse_int(st.get("available")),
        "total_voters": _parse_int(st.get("total_voters")),
        "processed": 1 if str(st.get("processed_stations") or "0") not in ("0", "") else 0,
    }}
