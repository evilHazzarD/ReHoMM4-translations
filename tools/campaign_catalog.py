"""Builds a catalog of the player-visible strings of a campaign file.

    campaign_catalog.py <language code> <X>     (X: e.g. Campaign.Chaos_Campaign)

reads build/<code>/extract/game_maps.X.h4d, writes build/<code>/catalog/X.json.

Keeps prose and titles (strings with a space), drops object-type keys
such as "mountains.Grass rough.17" (a dot followed by a non-space with no
sentence break). The campaign name and description in the header are
always kept. Existing translations in the catalog are preserved."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import campaign_text as ct  # noqa: E402
import lang as L  # noqa: E402


def visible(t):
    if ' ' not in t:
        return False
    if re.search(r'\.\S', t) and not re.search(r'[.!?]["\')]*\s', t):
        return False
    return True


def build(src, out):
    old = {}
    if os.path.exists(out):
        old = {e['en']: e.get(L.FIELD, '') for e in json.load(open(out, encoding='utf-8'))}
    items, seen = [], set()
    for k, r in enumerate(ct.extract(src)):
        t = r['en']
        part = r['part']
        if part == 'header':
            where = 'campaign name' if not items else 'campaign description'
            ok = len(t) > 1
        else:
            where = 'map %d' % (int(part[3:]) + 1)
            ok = visible(t)
        if ok and t not in seen:
            seen.add(t)
            items.append({'id': len(items), 'where': where, 'en': t, L.FIELD: old.get(t, '')})
    json.dump(items, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return items


if __name__ == '__main__':
    lg = L.Language(sys.argv[1])
    os.makedirs(lg.catalog, exist_ok=True)
    out = os.path.join(lg.catalog, sys.argv[2] + '.json')
    items = build(os.path.join(lg.extract, 'game_maps.' + sys.argv[2] + '.h4d'), out)
    print(f'{out}: {len(items)} strings, {sum(len(i["en"].split()) for i in items)} words')
