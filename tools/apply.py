"""Applies a translation to a Heroes IV game directory.

Rebuilds every campaign that has translated strings (build/<code>/catalog/*.json, entries with
a non-empty "text"), the interface tables, the voice-over (when the language has recordings)
and the fonts (build/<code>/fonts), patching the archives of <game dir>/Data in place: the
campaigns live in updates.h4r (expansions in storm.h4r and x2.h4r, the tutorial in heroes4.h4r),
the fonts in heroes4.h4r, the interface text in text.h4r. Patch a fresh copy of the archives
each time (the new data is appended). The single scenarios (catalogs Map.*: <game dir>/maps) are
written to build/<code>/maps. Run prepare.py first.

    apply.py <language code> <game dir>
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import campaign_text as ct  # noqa: E402
import h4r  # noqa: E402
import lang as L  # noqa: E402
import ui_text  # noqa: E402
import voice  # noqa: E402


def keyword_glue(catalog_dir):
    """The game cuts a %keyword out of the text as a run of isalnum/_/% bytes, with the byte
    sign-extended, so a non-ASCII letter or a guillemet next to it joins the run and the
    keyword is left unreplaced."""
    bad = []
    for path in sorted(glob.glob(os.path.join(catalog_dir, '*.json'))):
        for it in json.load(open(path, encoding='utf-8')):
            text = it.get(L.FIELD) or ''
            for m in re.finditer(r'%[A-Za-z_][A-Za-z0-9_]*', text):
                for c in text[m.start() - 1:m.start()] + text[m.end():m.end() + 1]:
                    if ord(c) > 127 or c.isalnum() or c == '_':
                        bad.append(f'{os.path.basename(path)} #{it["id"]}: {m.group()} next to {c!r}')
    return bad


def main(code, game):
    lg = L.Language(code)
    assert os.path.isdir(lg.catalog), f'no {lg.catalog}: run tools/prepare.py {code} <game dir> first'
    bad = keyword_glue(lg.catalog)
    assert not bad, 'keywords glued to text:\n' + '\n'.join(bad)
    os.makedirs(lg.build, exist_ok=True)
    data = os.path.join(game, 'Data')
    storm = lg.storm or os.environ.get('H4_LOC_STORM') == '1'
    patches = {a: {} for a in L.CAMPAIGN_ARCHIVES.values()}
    for path in sorted(glob.glob(os.path.join(lg.catalog, '*.json'))):
        base = os.path.basename(path)[:-5]
        archive = next((a for p, a in L.CAMPAIGN_ARCHIVES.items() if base.startswith(p)), None)
        if archive is None:
            continue
        if base.startswith('storm_campaign.') and not storm:
            continue  # The Gathering Storm only when language.json says so
        items = json.load(open(path, encoding='utf-8'))
        table = {it['en'].encode('cp1252'): lg.encode(it[L.FIELD]) for it in items if it.get(L.FIELD)}
        if not table:
            continue
        name = 'game_maps.' + base + '.h4d'
        src = os.path.join(lg.extract, name)
        patches[archive][name] = ct.rebuild(src, table, os.path.join(lg.build, name))
        # Every map must still parse into as many strings as the original;
        # a misread string boundary would leave stale bytes and crash the map.
        old = [len(ct.strings(p[2])) for p in ct.split_parts(open(src, 'rb').read())]
        new = [len(ct.strings(p[2])) for p in ct.split_parts(patches[archive][name])]
        assert old == new, f'{name}: string layout changed {old} -> {new}'
        print(f'{name}: {len(table)} strings')
    for archive, campaigns in patches.items():
        if campaigns and archive != 'heroes4.h4r':
            h4r.patch(os.path.join(data, archive), campaigns)
    tables = ui_text.build(os.path.join(data, 'text.h4r'), lg.encode, lg.catalog)
    if tables:
        h4r.patch(os.path.join(data, 'text.h4r'), tables)
        print(f'{len(tables)} interface tables')
    names = {a: {e.name for e in h4r.read_dir(os.path.join(data, a))[1]}
             for a in ('heroes4.h4r', 'storm.h4r', 'x2.h4r')}
    clips = voice.build(lg, names)
    for archive in ('storm.h4r', 'x2.h4r'):
        if clips.get(archive):
            h4r.patch(os.path.join(data, archive), clips[archive])
    print(f'{sum(map(len, clips.values()))} voice-over entries')
    fonts = {}
    if os.path.isdir(lg.fonts):
        fonts = {n: open(os.path.join(lg.fonts, n), 'rb').read() for n in os.listdir(lg.fonts)}  # (in the directory's order, as the packs were first made)
    heroes4 = {**fonts, **patches['heroes4.h4r'], **clips.get('heroes4.h4r', {})}
    if heroes4:
        h4r.patch(os.path.join(data, 'heroes4.h4r'), heroes4)
    print(f'{len(fonts)} fonts')
    # The single scenarios: rebuilt into build/<code>/maps/<their path below the game folder>
    # (pack.py puts them in the pack as files; the game reads them in place of its own).
    out_maps = os.path.join(lg.work, 'maps')
    if os.path.isdir(out_maps):
        import shutil
        shutil.rmtree(out_maps)
    n = 0
    for name, rel in sorted(L.game_maps(game).items()):
        path = os.path.join(lg.catalog, name + '.json')
        if not os.path.exists(path):
            continue
        items = json.load(open(path, encoding='utf-8'))
        table = {it['en'].encode('cp1252'): lg.encode(it[L.FIELD]) for it in items if it.get(L.FIELD)}
        if not table:
            continue
        out = os.path.join(out_maps, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, 'wb').write(ct.rebuild_map(os.path.join(game, rel), table))
        n += 1
    print(f'{n} single scenarios')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
