"""Builds a language pack from your own GOG copy of the game: prepare.py, apply.py on a copy of
the five archives it changes, then make_pack.py keeps only the difference.

    pack.py <language code> <game dir> [--from-repo]      prints build/<code>/<code>.h4p

The pack is made from build/<code>/catalog (your work, exported or not) when it exists, else
from languages/<code>/text; --from-repo always from languages/<code>/text (ReHoMM4's build).

Made again only when the translation, the tools, the recordings or the game's archives change.
The translated single scenarios (catalogs Map.*) go in as files (make_pack.py: the H4PF section).
An official translation (language.json "official") is taken from a localized copy of the game
instead: tools/official.py.
The pack holds data rebuilt from the game, so it is made on your machine, never committed.
Without ffmpeg the voice-over is left out (text only) with a warning.
"""
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lang as L  # noqa: E402
import make_pack  # noqa: E402
import take_out  # noqa: E402


def stamp(lg, data, catalog):
    h = hashlib.sha1()
    files = sorted(glob.glob(os.path.join(lg.dir, '**', '*.json'), recursive=True))
    if catalog:
        files += sorted(glob.glob(os.path.join(lg.catalog, '*.json')))
    files += sorted(glob.glob(os.path.join(HERE, '*.py'))) + [os.path.join(HERE, 'glyphs.swift')]
    for p in files:
        h.update(p.encode() + open(p, 'rb').read())
    for p in sorted(glob.glob(os.path.join(lg.voice_raw, '*.mp3'))):
        st = os.stat(p)
        h.update(f'{os.path.basename(p)} {st.st_size} {int(st.st_mtime)}'.encode())
    for a in make_pack.ARCHIVES:
        st = os.stat(os.path.join(data, a))
        h.update(f'{a} {st.st_size} {int(st.st_mtime)}'.encode())
    for rel in sorted(L.game_maps(os.path.dirname(data)).values()):
        st = os.stat(os.path.join(os.path.dirname(data), rel))
        h.update(f'{rel} {st.st_size} {int(st.st_mtime)}'.encode())
    h.update(str(bool(shutil.which('ffmpeg'))).encode())
    return h.hexdigest()[:16]


def run(tool, *args, log):
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, 'w') as f:
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, tool), *args],
                           stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        sys.stderr.write(''.join(open(log).readlines()[-8:]))
        raise SystemExit(f'{tool} failed (log: {log})')


def official_stamp(lg, data):
    h = hashlib.sha1()
    for p in [os.path.join(lg.dir, 'language.json'), os.path.join(HERE, 'official.py'),
              os.path.join(HERE, 'make_pack.py'), os.path.join(HERE, 'h4r.py')]:
        h.update(open(p, 'rb').read())
    for p in sorted(glob.glob(os.path.join(lg.work, 'official', '.from'))):
        h.update(open(p, 'rb').read())
    h.update(os.environ.get('H4_OFFICIAL_' + lg.code.upper().replace('-', '_'), '').encode())
    for a in sorted(glob.glob(os.path.join(data, '*.h4r'))):
        st = os.stat(a)
        h.update(f'{os.path.basename(a)} {st.st_size} {int(st.st_mtime)}'.encode())
    return h.hexdigest()[:16]


def applied_packs(lg):
    """The packs the player's game may have in it (take_out.py): the ones built here and any
    given in H4_APPLIED_PACKS (separated by ":")."""
    given = [p for p in os.environ.get('H4_APPLIED_PACKS', '').split(':') if p]
    built = os.path.join(os.path.dirname(lg.work), '*')
    return given + sorted(glob.glob(os.path.join(built, '*.h4p')) + glob.glob(os.path.join(built, 'applied', '*.h4p')))


def main(code, game, from_repo=False):
    lg = L.Language(code)
    data = os.path.join(game, 'Data')
    if lg.official:  # taken whole from a localized copy of the game (official.py)
        import official
        stamp_file = lg.pack + '.stamp'
        official.localized_dir(lg)  # unpacked first: its stamp is part of the pack's
        if not (os.path.exists(lg.pack) and os.path.exists(stamp_file)
                and open(stamp_file).read() == official_stamp(lg, data)):
            with tempfile.TemporaryDirectory(prefix='h4_en_') as en:
                official.main(code, take_out.english_game(game, os.path.join(en, 'game'), applied_packs(lg),
                                           os.path.join(lg.work, 'applied')))
            open(stamp_file, 'w').write(official_stamp(lg, data))
        return
    stamp_file = lg.pack + '.stamp'
    if (os.path.exists(lg.pack) and os.path.exists(stamp_file)
            and open(stamp_file).read() == stamp(lg, data, not from_repo)):
        return
    # A game played in a translation has it in its archives (the app puts it there); the tools
    # read and compare with the English ones.
    with tempfile.TemporaryDirectory(prefix='h4_en_') as en:
        build(lg, take_out.english_game(game, os.path.join(en, 'game'), applied_packs(lg),
                                           os.path.join(lg.work, 'applied')), from_repo)
    open(stamp_file, 'w').write(stamp(lg, data, not from_repo))


def build(lg, game, from_repo):
    code, data = lg.code, os.path.join(game, 'Data')
    os.makedirs(lg.work, exist_ok=True)
    if glob.glob(os.path.join(lg.voice_raw, '*.mp3')) and not shutil.which('ffmpeg'):
        print('warning: no ffmpeg: the pack is text only (no voice-over)', file=sys.stderr)
        os.environ['H4_LOC_NO_VOICE'] = '1'
    run('prepare.py', code, game, '--discard' if from_repo else '--keep-catalog',
        log=os.path.join(lg.work, 'prepare.log'))
    with tempfile.TemporaryDirectory(prefix='h4_pack_') as tmp:
        os.makedirs(os.path.join(tmp, 'Data'))
        for a in make_pack.ARCHIVES:
            shutil.copyfile(os.path.join(data, a), os.path.join(tmp, 'Data', a))  # real copies
        maps = L.game_maps(game)
        for rel in maps.values():  # read, never changed: the rebuilt ones go to build/<code>/maps
            os.makedirs(os.path.dirname(os.path.join(tmp, rel)), exist_ok=True)
            os.symlink(os.path.join(game, rel), os.path.join(tmp, rel))
        run('apply.py', code, tmp, log=os.path.join(lg.work, 'apply.log'))
        make_pack.main(data, os.path.join(tmp, 'Data'), lg.pack + '.new')
    # The translated single scenarios, as files at their place below the game folder.
    files = []
    for rel in sorted(maps.values()):
        p = os.path.join(lg.work, 'maps', rel)
        if os.path.exists(p):
            files.append((rel, open(p, 'rb').read()))
    if files:
        import official
        official.append_files(lg.pack + '.new', files)
    os.replace(lg.pack + '.new', lg.pack)


if __name__ == '__main__':
    if len(sys.argv) not in (3, 4) or sys.argv[3:] not in ([], ['--from-repo']):
        raise SystemExit(__doc__)
    # make_pack prints its summary; keep stdout for the pack's path only
    out = sys.stdout
    sys.stdout = sys.stderr
    try:
        main(sys.argv[1], sys.argv[2], sys.argv[3:] == ['--from-repo'])
    finally:
        sys.stdout = out
    print(L.Language(sys.argv[1]).pack)
