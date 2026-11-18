"""Merges translations into a catalog and checks they fit the language's code page.

    set_text.py <language code> <catalog.json> <batch.json>

batch.json is {"<id>": "<translation>"}; the catalog is one of build/<code>/catalog/*.json.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lang as L  # noqa: E402

if len(sys.argv) != 4:
    raise SystemExit(__doc__)
lg = L.Language(sys.argv[1])
cat, batch = sys.argv[2], json.load(open(sys.argv[3], encoding='utf-8'))
items = json.load(open(cat, encoding='utf-8'))
byid = {str(it['id']): it for it in items}
for k, v in batch.items():
    bad = lg.unencodable(v)
    assert not bad, f'#{k}: {lg.codepage} has no {"".join(bad)!r}'
    byid[k][L.FIELD] = v
json.dump(items, open(cat, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'{len(batch)} set, {sum(1 for i in items if i.get(L.FIELD))}/{len(items)} translated')
