"""An official translation: the language pack made from a localized GOG copy of the game (its
Data/ archives) instead of from catalogs. Nothing of it is in the repository: the localized copy
is the player's or maintainer's own, like the English one.

language.json of such a language has, instead of text/:

    "official": {
      "installer": "setup_heroes_of_might_and_magic_4_complete_*_(<language>)_*.exe",
      "from": "GOG, Heroes of Might and Magic IV Complete 3.0, <language>"
    }

or, for a localization made to be put over the English GOG game (a folder with Data/new.h4r,
the archive heroes4.exe opens last, and maybe maps), "folder" instead of "installer": its name in
~/Downloads (with * allowed), and "maps": where its single scenarios are in it (default "maps").

    official.py <language code> <English game dir> [<localized game dir or installer>]

The localized copy: the argument, else $H4_OFFICIAL_<CODE> (e.g. H4_OFFICIAL_CS), else the newest
installer matching "installer" in ~/Downloads (both parts, .exe and -1.bin), its Data/ and maps/
unpacked once with innoextract into build/<code>/official/. Writes build/<code>/<code>.h4p
(pack.py runs this).

The pack holds every entry of the localized archives that differs from the English one, as the
English heroes4.exe finds them: heroes4.h4r, movies.h4r, music.h4r, text.h4r and updates.h4r are
one set of names (a
later archive's entry wins, the order heroes4.exe opens them in), storm.h4r, x2.h4r and the
*_override.h4r archives each stand alone (the expansions' own data, chosen by campaign). Of the
override archives only strings.* is taken: the rest there are not translation. Names compare
ignoring case (table.Interface / table.interface). The localized data is kept as it is stored
(gzip), with its own sizes. The localized heroes4.exe is not used (another build of the game:
ReHoMM4 runs the English one).

The single scenarios (maps/, outside the archives) go after the archives as files (make_pack.py:
"H4PF"): every English map whose localized one differs, found by its path or else by its file
name anywhere in the localized maps/ (the localized folders may be named otherwise), under the
English path. The app unpacks them beside the game and reads them in its place.
"""
import glob
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h4r  # noqa: E402
import lang as L  # noqa: E402
import make_pack  # noqa: E402

# One namespace, the later wins (the order heroes4.exe opens them in: a localized text.h4r may
# hold the intro movie of movies.h4r).
GENERAL = ['heroes4.h4r', 'movies.h4r', 'music.h4r', 'text.h4r', 'updates.h4r']
ALONE = ['storm.h4r', 'x2.h4r']
OVERRIDES = ['storm_override.h4r', 'x2_override.h4r']  # strings.* only
NEW = 'new.h4r'  # opened last: its entries replace the same names in every archive


def localized_dir(lg, given=None):
    """The localized game folder (with Data/), unpacking the installer when needed."""
    src = given or os.environ.get('H4_OFFICIAL_' + lg.code.upper().replace('-', '_'), '')
    if src and os.path.isdir(src):
        return src
    folder = (lg.official or {}).get('folder', '')
    if not src and folder:
        found = sorted((p for p in glob.glob(os.path.join(os.path.expanduser('~/Downloads'), folder))
                        if os.path.isdir(p)), key=os.path.getmtime)
        if not found:
            raise SystemExit(f'{lg.english_name}: no {folder} folder in ~/Downloads (or set '
                             f'H4_OFFICIAL_{lg.code.upper()}=<its folder>)')
        return found[-1]
    if not src:
        pattern = (lg.official or {}).get('installer', '')
        found = sorted(glob.glob(os.path.join(os.path.expanduser('~/Downloads'), pattern)),
                       key=os.path.getmtime) if pattern else []
        kept = os.path.join(lg.work, 'official')
        if not found and os.path.exists(os.path.join(kept, '.from')):
            print(f'{lg.english_name}: no installer in ~/Downloads: the copy unpacked before '
                  f'({kept})', file=sys.stderr)
            return kept
        if not found:
            raise SystemExit(f'{lg.english_name}: no localized copy: put the GOG installer '
                             f'({pattern}, with its .bin) into ~/Downloads, or set '
                             f'H4_OFFICIAL_{lg.code.upper()}=<its game folder>')
        src = found[-1]
    out = os.path.join(lg.work, 'official')
    stamp = os.path.join(out, '.from')
    want = f'2 {os.path.abspath(src)} {os.path.getsize(src)} {int(os.path.getmtime(src))}'
    if os.path.exists(stamp) and open(stamp).read() == want:
        return out
    if not shutil.which('innoextract'):
        raise SystemExit('no innoextract (brew install innoextract)')
    shutil.rmtree(out, ignore_errors=True)
    tmp = out + '.tmp'
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    print(f'{lg.english_name}: unpacking {os.path.basename(src)}', file=sys.stderr)
    subprocess.run(['innoextract', '-s', '-I', 'Data', '-I', 'maps', '-d', tmp, src], check=True)
    if not os.path.exists(os.path.join(tmp, 'Data', 'text.h4r')):
        shutil.rmtree(tmp)
        raise SystemExit(f'{src}: no Data/text.h4r in it (both parts, the .exe and the -1.bin?)')
    os.rename(tmp, out)
    open(stamp, 'w').write(want)
    return out


def archives(data, names):
    """{archive: (bytes, {lower name: entry})} of the ones present."""
    out = {}
    for a in names:
        p = os.path.join(data, a)
        if os.path.exists(p):
            d, es = h4r.read_dir(p)
            out[a] = (d, {e.name.lower(): e for e in es})
    return out


def raw(d, e):
    return d[e.offset:e.offset + e.stored]


def effective(arcs, name, within):
    """(archive, entry) the game reads name from among `within` (the later wins), or None."""
    hit = None
    for a in within:
        if a in arcs and name in arcs[a][1]:
            hit = a, arcs[a][1][name]
    return hit


def plan(en, loc):
    """{English archive: {entry name: (localized bytes as stored, size)}}: the entries to replace."""
    out = {}
    names = set()
    for a in GENERAL:
        if a in en:
            names |= set(en[a][1])
    for n in sorted(names):
        e = effective(en, n, GENERAL)
        t = effective(loc, n, GENERAL)
        if not e or not t:
            continue
        b = raw(loc[t[0]][0], t[1])
        if b != raw(en[e[0]][0], e[1]):
            out.setdefault(e[0], {})[e[1].name] = (b, t[1].size)
    for a in ALONE + OVERRIDES:
        if a not in en or a not in loc:
            continue
        for n, e in en[a][1].items():
            if a in OVERRIDES and not n.startswith('strings.'):
                continue
            t = loc[a][1].get(n)
            if t is None:
                continue
            b = raw(loc[a][0], t)
            if b != raw(en[a][0], e):
                out.setdefault(a, {})[e.name] = (b, t.size)
    if NEW in loc:
        d, entries = loc[NEW]
        unused = []
        for n, t in entries.items():
            b = raw(d, t)
            hit = False
            general = effective(en, n, GENERAL)  # of these, only the one the game reads
            for a in GENERAL + ALONE + OVERRIDES:
                e = en.get(a, (None, {}))[1].get(n)
                if e is None or (a in GENERAL and a != general[0]):
                    continue
                hit = True
                if b != raw(en[a][0], e):
                    out.setdefault(a, {})[e.name] = (b, t.size)
            if not hit:
                unused.append(t.name)
        if unused:
            print(f'{NEW}: not in the English game (left out): {", ".join(sorted(unused))}', file=sys.stderr)
    return out


def find_dir(root, rel):
    """root/rel, each part matched ignoring case (Maps/RUS: maps/rus), or None."""
    cur = root
    for part in rel.replace('\\', '/').split('/'):
        if not os.path.isdir(cur):
            return None
        hit = [n for n in os.listdir(cur) if n.lower() == part.lower()]
        if not hit:
            return None
        cur = os.path.join(cur, hit[0])
    return cur if os.path.isdir(cur) else None


def map_files(game, loc_game, maps='maps'):
    """[(path below the game folder, localized bytes)]: the maps whose localized ones differ
    (`maps`: where the localized copy has them)."""
    def walk(root):
        out = {}
        if root:
            for d, _, names in os.walk(root):
                for n in names:
                    p = os.path.join(d, n)
                    out['maps/' + os.path.relpath(p, root).replace(os.sep, '/')] = p
        return out
    en, loc = walk(find_dir(game, 'maps')), walk(find_dir(loc_game, maps))
    by_path = {k.lower(): v for k, v in loc.items()}
    by_name = {}
    for k, v in loc.items():
        by_name.setdefault(k.rsplit('/', 1)[-1].lower(), []).append(v)
    out = []
    for rel, p in sorted(en.items()):
        q = by_path.get(rel.lower())
        if q is None:
            same = by_name.get(rel.rsplit('/', 1)[-1].lower(), [])
            q = same[0] if len(same) == 1 else None
        if q is None:
            continue
        b = open(q, 'rb').read()
        if b != open(p, 'rb').read():
            out.append((rel, b))
    return out


def append_files(path, files):
    with open(path, 'ab') as f:
        f.write(b'H4PF' + struct.pack('<I', len(files)))
        for rel, b in files:
            name = rel.encode('cp1252')
            f.write(struct.pack('<H', len(name)) + name + struct.pack('<Q', len(b)) + b)


def mp3_voice(blob, size):
    """A voice-over entry stored as PCM (u8 0, u16 0, u8 bits, u8 channels, u32 rate, u32 PCM
    bytes, u16 1, the samples) re-encoded as the English ones are (voice.py: MP3), which is
    some ten times smaller; as it is without ffmpeg or when it is not PCM."""
    data = blob
    if blob[:2] == b'\x1f\x8b':
        import gzip
        data = gzip.decompress(blob)
    if len(data) < 15 or data[0] != 0 or not shutil.which('ffmpeg'):
        return blob, size
    bits, channels, rate, n = struct.unpack_from('<BBII', data, 3)
    if bits != 16 or channels not in (1, 2) or n != len(data) - 15:
        return blob, size
    import voice
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, 'v.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(rate), '-ac',
                        str(channels), '-i', '-', wav], input=data[15:], check=True)
        e = voice.entry(wav)
    return e, len(e)


def patch(path, replacements):
    """Like h4r.patch, but each new entry keeps its own stored and full size (gzip as stored)."""
    _, es = h4r.read_dir(path)
    byname = {e.name: e for e in es}
    with open(path, 'r+b') as f:
        f.seek(0, 2)
        for name, (blob, size) in replacements.items():
            e = byname[name]
            off = f.tell()
            f.write(blob)
            end = f.tell()
            f.seek(e.at)
            f.write(struct.pack('<III', off, len(blob), size))
            f.seek(end)


def main(code, game, given=None):
    lg = L.Language(code)
    if not lg.official:
        raise SystemExit(f'{code}: not an official translation (no "official" in language.json)')
    data = os.path.join(game, 'Data')
    loc_game = localized_dir(lg, given)
    loc_data = os.path.join(loc_game, 'Data')
    en = archives(data, GENERAL + ALONE + OVERRIDES)
    loc_data = find_dir(loc_game, 'Data') or loc_data
    loc = archives(loc_data, GENERAL + ALONE + OVERRIDES + [NEW])
    todo = plan(en, loc)
    del loc
    pcm = 0
    for r in todo.values():
        for name, (b, size) in list(r.items()):
            if name.lower().startswith('sound.voice_over.'):
                nb, ns = mp3_voice(b, size)
                if nb is not b:
                    pcm += 1
                    r[name] = (nb, ns)
    if pcm:
        print(f'voice-over: {pcm} PCM entries re-encoded as MP3', file=sys.stderr)
    if not todo:
        raise SystemExit(f'{loc_data}: nothing differs from the English game')
    for a, r in todo.items():
        print(f'{a}: {len(r)} entries, {sum(len(b) for b, _ in r.values()) >> 10} KB', file=sys.stderr)
    os.makedirs(lg.work, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='h4_official_', dir=lg.work) as tmp:
        os.makedirs(os.path.join(tmp, 'Data'))
        for a in todo:
            shutil.copyfile(os.path.join(data, a), os.path.join(tmp, 'Data', a))  # real copies
            patch(os.path.join(tmp, 'Data', a), todo[a])
        make_pack.ARCHIVES = [a for a in GENERAL + ALONE + OVERRIDES if a in todo]
        make_pack.main(data, os.path.join(tmp, 'Data'), lg.pack + '.new')
    files = map_files(game, loc_game, lg.official.get('maps', 'maps'))
    if files:
        append_files(lg.pack + '.new', files)
        print(f'maps: {len(files)} files, {sum(len(b) for _, b in files) >> 10} KB', file=sys.stderr)
    os.replace(lg.pack + '.new', lg.pack)
    return lg.pack


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4):
        raise SystemExit(__doc__)
    out = sys.stdout
    sys.stdout = sys.stderr
    try:
        pack = main(*sys.argv[1:])
    finally:
        sys.stdout = out
    print(pack)
