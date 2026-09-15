"""
RZS SDDB klijent — masinsko izvlacenje tabela diseminacione baze
(data.stat.gov.rs) bez browsera.

Otkriveno:
  - GET  /Home/Result/<subAreaId>?languageCode=sr-Latn  (mora HTTPS + session)
  - stabla selekcije su ugradjena u HTML: $('#agg-XXX').jstree({'core':{'data':[...]}})
  - query format (iz site.js ValidateAndBuildQuery):
        indicators=<IND>ID + &agg-<N>=<id1,id2,...>
  - POST https://data.stat.gov.rs/Home/DisplayResult
        {languageCode, displayMode:'table', subAreaId, uriQuery, resultDisplayType:'Identificator'}
    vraca HTML sa ugradjenim JSON slogovima:
        {"Teritorija - NSTJ": "70092", "Izborna lista": "...", "Vrsta podatka": "1", "Vrednost": "5977", ...}

Poznate tabele (parlamentarni izbori, glasovi/mandati):
  07020601/02 - 2012, 07020701/02 - 2014, 07020801/02 - 2016,
  07020901/02 - 2020, 07021001/02 - 2022, 07021101/02 - 2023
"""
import json
import logging
import re
import time

import requests

BASE = "https://data.stat.gov.rs"

log = logging.getLogger("sddb_client")
DEFAULT_DELAY = 1.0


def create_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "sr-RS,sr;q=0.9,en;q=0.8",
    })
    return s


def _extract_trees(html: str) -> dict[str, list[dict]]:
    """Vadi jstree JSON nizove {agg-id: [cvorovi]} iz HTML strane."""
    trees: dict[str, list[dict]] = {}
    for m in re.finditer(r"\$\('#(agg-\d+)'\)\.jstree\(\{\s*'core':\s*\{\s*'data'\s*:\s*(\[)", html):
        agg = m.group(1)
        start = m.start(2)
        depth, instr, esc = 0, False, False
        for i in range(start, len(html)):
            ch = html[i]
            if instr:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    instr = False
            elif ch == '"':
                instr = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    trees[agg] = json.loads(html[start:i + 1])
                    break
    return trees


def _extract_indicator(html: str) -> str | None:
    m = re.search(r'<input type="checkbox" id="(\w+IND\d+)"', html)
    return m.group(1) if m else None


def get_selection_trees(session: requests.Session, sub_area_id: str) -> tuple[str, dict]:
    """GET Result strana -> (indicator_id, {agg: cvorovi}). Baca na gresku ako nema stabala."""
    r = session.get(f"{BASE}/Home/Result/{sub_area_id}?languageCode=sr-Latn", timeout=60)
    r.raise_for_status()
    trees = _extract_trees(r.text)
    ind = _extract_indicator(r.text)
    if not trees or not ind:
        raise RuntimeError(f"SDDB {sub_area_id}: nema stabala/indikatora u odgovoru")
    try:
        from bs4 import BeautifulSoup  # noqa
        soup = BeautifulSoup(r.text, "html.parser")
        dims = [re.sub(r"\s+", " ", (lbl.get_text() or "")).strip()
                for lbl in soup.select("label[for^='cbAggT-']")]
    except Exception:
        dims = []
    log.info("SDDB %s: indikator=%s dimenzije=%s stabla=%s",
             sub_area_id, ind, dims, {k: len(v) for k, v in trees.items()})
    return ind, trees


def fetch_table(session: requests.Session, sub_area_id: str, indicator: str,
                selections: dict[str, list[str]],
                display: str = "Identificator", delay: float = DEFAULT_DELAY) -> list[dict]:
    """POST DisplayResult sa punom selekcijom -> lista JSON slogova."""
    if delay:
        time.sleep(delay)
    parts = [f"indicators={indicator}"]
    for agg, ids in selections.items():
        parts.append(f"{agg}={','.join(ids)}")
    r = session.post(
        f"{BASE}/Home/DisplayResult",
        data={"languageCode": "sr-Latn", "displayMode": "table",
              "subAreaId": sub_area_id, "uriQuery": "&".join(parts),
              "resultDisplayType": display},
        headers={"X-Requested-With": "XMLHttpRequest",
                 "Referer": f"{BASE}/Home/Result/{sub_area_id}?languageCode=sr-Latn"},
        timeout=180,
    )
    r.raise_for_status()
    m = re.search(r"\$\(\"#pivotTableOutput\"\)\.pivotUI\(\s*(\[)", r.text)
    if not m:
        raise RuntimeError(f"SDDB {sub_area_id}: nema pivotUI JSON u odgovoru")
    start = m.start(1)
    depth, instr, esc = 0, False, False
    for i in range(start, len(r.text)):
        ch = r.text[i]
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
        elif ch == '"':
            instr = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return json.loads(r.text[start:i + 1])
    raise RuntimeError(f"SDDB {sub_area_id}: nezatvoren JSON")
