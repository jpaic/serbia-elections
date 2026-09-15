"""
Skidanje RZS SDDB tabela u raw/ JSON, chunkovano po listama (server spor za velike selekcije).
  python sddb_fetch.py --sub 07021001 --out raw/2022-glasovi.json
  python sddb_fetch.py --sub 07021002 --out raw/2022-mandati.json
"""
import argparse
import json
import logging
import re
import sys
import time

from sddb_client import create_session, fetch_table, get_selection_trees

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    s = create_session()
    ind, trees = get_selection_trees(s, args.sub)
    aggs = {agg: [n["id"] for n in nodes if n.get("id")] for agg, nodes in trees.items()}
    for agg, ids in aggs.items():
        print(f"  {agg}: {len(ids)}")
    # chunkuj po najvecoj dimenziji; teritoriju suzi na opstine ako postoje 5-cifreni kodovi
    chunk_agg = max(aggs, key=lambda a: len(aggs[a]))
    base = {}
    for agg, ids in aggs.items():
        if agg == chunk_agg:
            continue
        if any(re.fullmatch(r"\d{5}", i) for i in ids):
            base[agg] = [i for i in ids if re.fullmatch(r"\d{5}", i)]
        else:
            base[agg] = ids
    print(f"chunk dimenzija: {chunk_agg} ({len(aggs[chunk_agg])}), fiksno: { {k: len(v) for k, v in base.items()} }")

    all_rows = []
    t0 = time.time()
    for i, cid in enumerate(aggs[chunk_agg]):
        sel = dict(base)
        sel[chunk_agg] = [cid]
        rows = fetch_table(s, args.sub, ind, sel, delay=1.0)
        all_rows.extend(rows)
        print(f"  [{i+1}/{len(aggs[chunk_agg])}] {cid}: {len(rows)} slogova ({time.time()-t0:.0f}s)")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"sub": args.sub, "indicator": ind, "aggs": aggs,
                   "rows": all_rows}, f, ensure_ascii=False)
    print(f"UKUPNO {len(all_rows)} slogova za {time.time()-t0:.0f}s -> {args.out}")


if __name__ == "__main__":
    sys.exit(main())
