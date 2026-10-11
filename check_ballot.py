import json, re
data = json.load(open('collector/raw/2026-dokumenti.json', encoding='utf-8'))
izborna = []
for x in data:
    dn = x.get('document_name', '')
    if 'ИЗБОРНА ЛИСТА' in dn:
        m = re.match(r'^\s*(\d+)\s*\.\s*ИЗБОРНА ЛИСТА\s*(.*)', dn, re.IGNORECASE)
        if m:
            bn = int(m.group(1))
            name_raw = m.group(2).strip()
            name_raw = re.sub(r'^[–—-]\s*', '', name_raw)
            izborna.append((bn, name_raw))
izborna.sort()
with open('ballot_order.txt', 'w', encoding='utf-8') as f:
    for bn, name in izborna:
        f.write(f'{bn}: {name[:120]}\n')
print("Done - check ballot_order.txt")