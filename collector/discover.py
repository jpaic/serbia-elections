"""
Discovery skripta — jednokratno "hoda" kroz RIK-ov cascading API
(get-elections -> get-regions -> get-municipalities -> get-election-stations
-> get_results) i ispisuje SIROVE JSON odgovore, da bismo videli tačna imena
polja pre nego što napišemo pravi parser u collector.py.

Pokretanje:
    pip install requests --break-system-packages
    python discover.py --election-type 2

Opciono, kad imaš id-jeve iz prethodnog izlaza skripte:
    python discover.py --election-type 2 --election-round 680072 \
        --region 1 --municipality 5 --station <id>

Rezultat: nalepi CEO output ovde u chat (sve JSON blokove), pa pišem finalni
fetch_raw_results() u collector.py sa tačnim imenima polja.
"""
import argparse
import json
import sys

import requests

BASE = "https://www.rik.parlament.gov.rs"

HEADERS = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "en,sr;q=0.9",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": BASE,
    "referer": BASE + "/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "x-requested-with": "XMLHttpRequest",
}


def dump(label: str, resp: requests.Response):
    print(f"\n{'=' * 70}\n{label}  [HTTP {resp.status_code}]\n{'=' * 70}")
    try:
        data = resp.json()
        print(json.dumps(data, ensure_ascii=False, indent=2)[:6000])
    except ValueError:
        print("(nije JSON, sirov tekst ispod)")
        print(resp.text[:2000])
    return resp


def post(session: requests.Session, path: str, payload: dict) -> requests.Response:
    return session.post(f"{BASE}/{path}/", headers=HEADERS, data=payload)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--election-type", type=int, required=True, help="1/2/3/4 iz menija (probaj sve)")
    ap.add_argument("--election-round", type=int, default=None, help="id konkretnih izbora iz get-elections odgovora")
    ap.add_argument("--region", type=int, default=None)
    ap.add_argument("--municipality", type=int, default=None)
    ap.add_argument("--station", type=int, default=None)
    args = ap.parse_args()

    session = requests.Session()
    # prvo posetimo početnu stranu da PHP izda validan PHPSESSID
    home = session.get(f"{BASE}/")
    print(f"GET / -> {home.status_code}, cookies: {dict(session.cookies)}")

    dump(
        "get-elections",
        post(session, "get-elections", {"election_type": args.election_type}),
    )

    if not args.election_round:
        print(
            "\n>>> Nema --election-round. Pogledaj 'id' (ili slično polje) gore u "
            "get-elections odgovoru za izbore koje želiš, pa pokreni skriptu ponovo "
            "sa --election-round <id>."
        )
        sys.exit(0)

    payload = {"election_type": args.election_type, "election_round": args.election_round}
    dump("get-regions", post(session, "get-regions", payload))
    # i odmah probamo get_results na nivou celih izbora (bez regiona/opštine)
    dump("get_results (nacionalni nivo)", post(session, "get_results", payload))

    if args.region:
        payload["election_region"] = args.region
        dump("get-municipalities", post(session, "get-municipalities", payload))
        dump("get_results (nivo regiona)", post(session, "get_results", payload))

    if args.municipality:
        payload["election_municipality"] = args.municipality
        dump("get-election-stations", post(session, "get-election-stations", payload))
        dump("get_results (nivo opstine)", post(session, "get_results", payload))

    if args.station:
        payload["election_station"] = args.station
        dump("get_results (nivo birackog mesta)", post(session, "get_results", payload))


if __name__ == "__main__":
    main()
