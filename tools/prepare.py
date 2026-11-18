"""Gets a translation ready for apply.py from the player's own copy of the game: extracts the
campaign files and fonts it rebuilds, puts the English text back into the catalogs (matched by
key, see export.py) and draws the language's letters into the game's fonts.

    prepare.py <language code> <game dir> [--keep-catalog | --discard]

Writes build/<code>/: extract/ (campaign files), catalog/*.json (each entry with "en" and
"text": the files you translate in), fonts_en/ and fonts/.

The catalogs are made again from languages/<code>/text (after a git pull, say). It stops if
they hold translations export.py has not written back yet: --discard drops them,
--keep-catalog leaves the catalogs as they are (pack.py: the pack of the work in progress).
"""
import glob
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import campaign_text as ct  # noqa: E402
import h4r  # noqa: E402
import lang as L  # noqa: E402
import ui_text  # noqa: E402


def key(en):
    return hashlib.sha1(en.encode('utf-8')).hexdigest()[:12]


def entries(path):
    d, es = h4r.read_dir(path)
    return {e.name: (d, e) for e in es}


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'wb').write(data)


def english(lg, archives):
    """{key: English} of every campaign string and table cell of the game."""
    found = {}
    for path in sorted(glob.glob(os.path.join(lg.text_dir, '*.json'))):
        base = os.path.basename(path)[:-5]
        archive = next((a for p, a in L.CAMPAIGN_ARCHIVES.items() if base.startswith(p)), None)
        if archive is None:
            continue
        name = 'game_maps.' + base + '.h4d'
        out = os.path.join(lg.extract, name)
        write(out, h4r.data(*archives[archive][name]))
        for r in ct.extract(out):
            found[key(r['en'])] = r['en']
    for name in ui_text.TABLES:
        rows, _ = ui_text.parse(h4r.data(*archives['text.h4r'][name]))
        for row in rows:
            for cell in row:
                en = cell.decode('cp1252')
                found[key(en)] = en
    return found


def unexported(lg):
    """Catalog files in build/<code>/catalog whose texts differ from languages/<code>/text."""
    out = []
    for path in sorted(glob.glob(os.path.join(lg.catalog, '*.json'))):
        repo = os.path.join(lg.text_dir, os.path.basename(path))
        if not os.path.exists(repo):
            continue
        have = {key(it['en']): it.get(L.FIELD, '') for it in json.load(open(path, encoding='utf-8'))}
        want = {it['key']: it.get(L.FIELD, '') for it in json.load(open(repo, encoding='utf-8'))}
        if any(have.get(k, t) != t for k, t in want.items()):
            out.append(os.path.basename(path))
    return out


def main(code, game, mode=''):
    lg = L.Language(code)
    if mode == '':
        changed = unexported(lg)
        if changed:
            raise SystemExit(f'build/{code}/catalog has translations not in languages/{code}/text yet '
                             f'({", ".join(changed[:5])}{"..." if len(changed) > 5 else ""}):\n'
                             f'  python3 tools/export.py {code}    to keep them, then run this again\n'
                             f'  prepare.py {code} <game dir> --discard    to drop them')
    data = os.path.join(game, 'Data')
    archives = {a: entries(os.path.join(data, a))
                for a in set(L.CAMPAIGN_ARCHIVES.values()) | {'text.h4r'}}
    found = english(lg, archives)

    os.makedirs(lg.catalog, exist_ok=True)
    missing = 0
    for path in sorted(glob.glob(os.path.join(lg.text_dir, '*.json'))):
        if mode == '--keep-catalog' and os.path.exists(os.path.join(lg.catalog, os.path.basename(path))):
            continue
        items = []
        for it in json.load(open(path, encoding='utf-8')):
            en = found.get(it['key'])
            if en is None:
                missing += 1
                print(f'{os.path.basename(path)} #{it["id"]}: not in this copy of the game')
                continue
            items.append({k: v for k, v in it.items() if k not in ('key', L.FIELD)}
                         | {'en': en, L.FIELD: it.get(L.FIELD, '')})
        json.dump(items, open(os.path.join(lg.catalog, os.path.basename(path)), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    assert not missing, f'{missing} strings missing: is it GOG Complete 3.0?'

    # Fonts: the game's own, with the letters of the language's code page drawn in.
    d, es = h4r.read_dir(os.path.join(data, 'heroes4.h4r'))
    for e in es:
        if e.name.startswith('font.'):
            write(os.path.join(lg.fonts_en, e.name), h4r.data(d, e))
    glyphs = os.path.join(HERE, 'glyphs')
    if not os.path.exists(glyphs):
        subprocess.run(['swiftc', '-O', '-o', glyphs, glyphs + '.swift'], check=True)
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'build_fonts.py'), code,
                    lg.fonts_en, lg.fonts], check=True)
    print(f'{lg.english_name}: {len(found)} game strings; catalogs in {lg.catalog}; fonts ready')


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4) or sys.argv[3:] not in ([], ['--keep-catalog'], ['--discard']):
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2], (sys.argv[3:] or [''])[0])
