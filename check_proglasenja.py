import json, re
data = json.load(open('collector/raw/2026-dokumenti.json', encoding='utf-8'))
lists = []
for x in data:
    dn = x.get('document_name', '')
    if 'ПРОГЛАШЕЊУ' in dn:
        name = dn.replace('РЕШЕЊЕ О ПРОГЛАШЕЊУ ИЗБОРНЕ ЛИСТЕ', '').strip()
        num = int(re.sub(r'\D', '', x.get('number', '0')) or 0)
        try:
            dt = int(str(x.get('datetime', '0')).strip())
        except ValueError:
            dt = 0
        lists.append((dt, num, name))
lists.sort()
with open('proglasenja.txt', 'w', encoding='utf-8') as f:
    for dt, num, name in lists:
        f.write(f'[{num}] dt={dt} {name[:150]}\n')
print(f"proglasenih lista: {len(lists)}")
print("Done - check proglasenja.txt")