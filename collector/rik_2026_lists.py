# -*- coding: utf-8 -*-
"""RIK proglašene liste 2026: sve strane /get-additional-documents type=1 round=680072."""
import json
import re
import requests

s = requests.Session()
s.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
s.get("https://www.rik.parlament.gov.rs/", timeout=20)

all_recs = []
page = 1
while True:
    r = s.get("https://www.rik.parlament.gov.rs/get-additional-documents",
              params={"page": page, "filters[document-type]": 1,
                      "filters[election-round]": 680072, "election_type": 2},
              timeout=30)
    j = r.json()
    recs = j.get("records", [])
    if not recs:
        break
    all_recs.extend(recs)
    print(f"strana {page}: {len(recs)} dokumenata")
    if "data-page" not in j.get("pagination", "") or len(recs) < 10:
        # ima li sledece strane? proveri data-page > page
        pages = sorted({int(x) for x in re.findall(r'data-page="(\d+)"', j.get("pagination", ""))})
        if not pages or max(pages) <= page:
            break
    page += 1
    if page > 10:
        break

print(f"UKUPNO: {len(all_recs)}")
proclaimed = [x for x in all_recs if "ПРОГЛАШЕЊУ" in x.get("document_name", "")]
print(f"proglasenih lista: {len(proclaimed)}")
for x in proclaimed:
    name = x["document_name"].replace("РЕШЕЊЕ О ПРОГЛАШЕЊУ ИЗБОРНЕ ЛИСТЕ", "").strip()
    print(f"  [{x['number']}] {name}")
import os
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw", "2026-dokumenti.json")
json.dump(all_recs, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print("snimljeno", out)
