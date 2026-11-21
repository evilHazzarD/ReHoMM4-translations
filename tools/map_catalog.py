"""Builds the catalogs of the single scenarios (the game's maps/*.h4c): one per map,
build/<code>/catalog/Map.<file name>.json, with the strings the player sees: the map's name, its
description and the text of its events, signs and the like (strings with a space, as for the
campaigns: campaign_catalog.visible). A string already translated, in this map's catalog or in any
other catalog of the language (the campaigns, the interface), is filled in from there.

    map_catalog.py <language code> <game dir> [<localized maps dir> <its code page>]

With a localized copy's maps (an official translation's, say), each map's strings in that
language are written beside it, build/<code>/reference/Map.<file name>.json, matched by their
order (when the map has as many strings): a reference for translating, never part of the
catalogs (export.py does not see it).
Run export.py afterwards to put the catalogs into languages/<code>/text.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import campaign_catalog as cc  # noqa: E402
import campaign_text as ct  # noqa: E402
import lang as L  # noqa: E402


def localized_maps(root):
    out = {}
    for d, _, names in os.walk(root):
        for n in names:
            if n.lower().endswith('.h4c'):
                out.setdefault(n.lower(), []).append(os.path.join(d, n))
    return out


def main(code, game, loc_dir=None, loc_codepage='cp1252'):
    lg = L.Language(code)
    os.makedirs(lg.catalog, exist_ok=True)
    known = {}  # English -> its translation, from every catalog
    for path in glob.glob(os.path.join(lg.catalog, '*.json')):
        for it in json.load(open(path, encoding='utf-8')):
            if it.get(L.FIELD):
                known.setdefault(it['en'], it[L.FIELD])
    loc = localized_maps(loc_dir) if loc_dir else {}
    total = done = 0
    for name, rel in sorted(L.game_maps(game).items()):
        out = os.path.join(lg.catalog, name + '.json')
        old = {}
        if os.path.exists(out):
            old = {it['en']: it.get(L.FIELD, '') for it in json.load(open(out, encoding='utf-8'))}
        strings = [t for _, t in ct.map_strings(os.path.join(game, rel))]
        items, seen, first = [], set(), {}
        for i, t in enumerate(strings):
            where = 'map name' if i == 0 else 'map description' if i == 1 else 'map'
            if (i == 0 and t.strip()) or cc.visible(t):
                if t in seen:
                    continue
                seen.add(t)
                first[t] = i
                items.append({'id': len(items), 'where': where, 'en': t,
                              L.FIELD: old.get(t) or known.get(t, '')})
        json.dump(items, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        total += len(items)
        done += sum(bool(it[L.FIELD]) for it in items)
        hit = loc.get(os.path.basename(rel).lower(), [])
        if len(hit) == 1:
            theirs = [t for _, t in ct.map_strings(hit[0], loc_codepage)]
            if len(theirs) == len(strings):
                ref = [{'id': it['id'], 'en': it['en'], 'ref': theirs[first[it['en']]]} for it in items]
                os.makedirs(os.path.join(lg.work, 'reference'), exist_ok=True)
                json.dump(ref, open(os.path.join(lg.work, 'reference', name + '.json'), 'w', encoding='utf-8'),
                          ensure_ascii=False, indent=1)
    print(f'{lg.english_name}: {done}/{total} map strings translated, catalogs in {lg.catalog}')


if __name__ == '__main__':
    if len(sys.argv) not in (3, 5):
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
