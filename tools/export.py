"""Writes the shareable form of a translation: build/<code>/catalog/*.json -> languages/<code>/text
with the game's English text replaced by a key (the first 12 hex digits of its SHA-1), so the
repository carries no game text. prepare.py puts the English back from the player's own copy of
the game. Run it after translating, before committing.

    export.py <language code>
"""
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lang as L  # noqa: E402


def key(en):
    return hashlib.sha1(en.encode('utf-8')).hexdigest()[:12]


def main(code):
    lg = L.Language(code)
    paths = sorted(glob.glob(os.path.join(lg.catalog, '*.json')))
    assert paths, f'no catalogs in {lg.catalog}: run tools/prepare.py {code} <game dir> first'
    os.makedirs(lg.text_dir, exist_ok=True)
    done = total = 0
    for path in paths:
        out, seen = [], {}
        for it in json.load(open(path, encoding='utf-8')):
            en = it['en']
            k = key(en)
            assert seen.setdefault(k, en) == en, f'{path}: key collision'
            bad = lg.unencodable(it.get(L.FIELD, ''))
            assert not bad, f'{os.path.basename(path)} #{it["id"]}: {lg.codepage} has no {"".join(bad)!r}'
            out.append({k2: v for k2, v in it.items() if k2 not in ('en', L.FIELD)}
                       | {L.FIELD: it.get(L.FIELD, ''), 'key': k})
            total += 1
            done += bool(it.get(L.FIELD))
        json.dump(out, open(os.path.join(lg.text_dir, os.path.basename(path)), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    print(f'{lg.english_name}: {done}/{total} strings translated, written to {lg.text_dir}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
