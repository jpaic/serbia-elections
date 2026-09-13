import requests, re, json
from pathlib import Path

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
base = 'https://www.rik.parlament.gov.rs/js/map/assets/rs/'
out_dir = Path(__file__).parent.parent / 'public' / 'data' / 'rik-maps'
out_dir.mkdir(parents=True, exist_ok=True)

# Kodovi: rs = cela Srbija (5 regiona), rs11-rs23 = opstine po regionima
codes = ['rs', 'rs11', 'rs12', 'rs21', 'rs22', 'rs23']
for code in codes:
    fname = f'jquery-jvectormap-data-{code}-lcc-cr.js'
    url = base + fname
    try:
        r = requests.get(url, headers=headers, timeout=30)
        print(f"{code}: {r.status_code} len={len(r.text)}")
        if r.status_code == 200 and 'addMap' in r.text:
            (out_dir / fname).write_text(r.text, encoding='utf-8')
            keys = re.findall(r'"(\d+|rs\d+)"\s*:\s*\{"name":"([^"]+)"', r.text)
            print(f"  entries={len(keys)}")
            for k, name in keys[:6]:
                print(f"    {k} = {name}")
            if len(keys) > 10:
                print(f"    ...")
                for k, name in keys[-4:]:
                    print(f"    {k} = {name}")
            m = re.search(r'"width":\s*"?(\d+)"?,\s*"height":\s*"?(\d+)"?', r.text)
            if m:
                print(f"  size {m.group(1)}x{m.group(2)}")
        else:
            print(f"  SKIP (no addMap): {r.text[:200]}")
    except Exception as e:
        print(f"{code}: ERROR {e}")
