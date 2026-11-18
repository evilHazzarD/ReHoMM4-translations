"""Builds a language pack from your own GOG copy of the game: prepare.py, apply.py on a copy of
the five archives it changes, then make_pack.py keeps only the difference.

    pack.py <language code> <game dir> [--from-repo]      prints build/<code>/<code>.h4p

The pack is made from build/<code>/catalog (your work, exported or not) when it exists, else
from languages/<code>/text; --from-repo always from languages/<code>/text (ReHoMM4's build).

Made again only when the translation, the tools, the recordings or the game's archives change.
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


def main(code, game, from_repo=False):
    lg = L.Language(code)
    data = os.path.join(game, 'Data')
    stamp_file = lg.pack + '.stamp'
    if (os.path.exists(lg.pack) and os.path.exists(stamp_file)
            and open(stamp_file).read() == stamp(lg, data, not from_repo)):
        return
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
        run('apply.py', code, tmp, log=os.path.join(lg.work, 'apply.log'))
        make_pack.main(data, os.path.join(tmp, 'Data'), lg.pack + '.new')
    os.replace(lg.pack + '.new', lg.pack)
    open(stamp_file, 'w').write(stamp(lg, data, not from_repo))


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
