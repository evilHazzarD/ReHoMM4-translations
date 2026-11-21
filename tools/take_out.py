"""Takes a language pack back out of a game's archives: the app (ReHoMM4 h4/src/language.cpp)
puts a translation in by appending its data to the player's archives and rewriting the replaced
entries' 12-byte headers, so a game that has been played in a translation no longer has the
English archives the tools read (prepare.py, apply.py). This writes the English headers back and
cuts the appended data off, as the app does when it switches language.

    take_out.py <Data dir> <pack> [<pack> ...]

Each archive is restored by the pack whose data it holds (make_pack.py: the format); archives
none of them is in are left as they are. Run it on a copy: pack.py does, on its copies.
"""
import os
import struct
import sys


def read_index(path):
    """[(archive name, original size, appended size, [(pos, en, tr)], data offset)]"""
    out = []
    with open(path, 'rb') as f:
        assert f.read(4) == b'H4P1', f'{path}: not a language pack'
        (n,) = struct.unpack('<I', f.read(4))
        for _ in range(n):
            (ln,) = struct.unpack('<H', f.read(2))
            name = f.read(ln).decode()
            size, appended, count = struct.unpack('<QQI', f.read(20))
            entries = []
            for _ in range(count):
                (pos,) = struct.unpack('<I', f.read(4))
                entries.append((pos, f.read(12), f.read(12)))
            out.append((name, size, appended, entries, f.tell()))
            f.seek(appended, 1)
    return out


def take_out(data_dir, packs):
    """{archive name: the pack taken out of it}"""
    done = {}
    for pack in packs:
        with open(pack, 'rb') as p:
            for name, size, appended, entries, at in read_index(pack):
                path = os.path.join(data_dir, name)
                if name in done or not os.path.exists(path) or appended == 0:
                    continue
                if os.path.getsize(path) != size + appended:
                    continue
                n = min(4096, appended)
                p.seek(at)
                head = p.read(n)
                with open(path, 'r+b') as f:
                    f.seek(size)
                    if f.read(n) != head:
                        continue  # another pack's data
                    for pos, en, tr in entries:
                        f.seek(pos)
                        if f.read(12) in (en, tr):
                            f.seek(pos)
                            f.write(en)
                    f.truncate(size)
                done[name] = pack
    return done


def english_game(game, out, packs, keep=None):
    """A copy of the game folder at `out` with the English archives (make_pack.ARCHIVES): each
    one the app has put a translation in is copied and taken out by the pack it holds, the rest
    of the folder is linked. Stops when an archive is still not the GOG one. The packs taken out
    are copied into `keep`: the game still has them in when the pack built is a new one."""
    import make_pack
    data = os.path.join(game, 'Data')
    os.makedirs(os.path.join(out, 'Data'))
    for n in os.listdir(game):
        if n != 'Data':
            os.symlink(os.path.join(game, n), os.path.join(out, n))
    for n in os.listdir(data):
        src, dst = os.path.join(data, n), os.path.join(out, 'Data', n)
        if n in make_pack.ARCHIVES and os.path.getsize(src) != make_pack.GOG_SIZES[n]:
            import shutil
            shutil.copyfile(src, dst)
        else:
            os.symlink(src, dst)
    done = take_out(os.path.join(out, 'Data'), [p for p in packs if os.path.exists(p)])
    for name, pack in sorted(done.items()):
        print(f'{name}: {os.path.basename(pack)} taken out (the game has it in)', file=sys.stderr)
    if keep:
        import hashlib
        import shutil
        os.makedirs(keep, exist_ok=True)
        for pack in set(done.values()):
            h = hashlib.sha1(open(pack, 'rb').read()).hexdigest()[:12]
            dst = os.path.join(keep, h + '.h4p')
            if not os.path.exists(dst):
                shutil.copyfile(pack, dst)
    wrong = [a for a in make_pack.ARCHIVES
             if os.path.getsize(os.path.join(out, 'Data', a)) != make_pack.GOG_SIZES[a]]
    if wrong:
        raise SystemExit(f'{data}: {", ".join(wrong)} not the English GOG archives (a translation '
                         'in them that no pack here has: give its .h4p in H4_APPLIED_PACKS, '
                         'separated by ":", or reinstall the game)')
    return out


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    for name, pack in sorted(take_out(sys.argv[1], sys.argv[2:]).items()):
        print(f'{name}: {os.path.basename(pack)} taken out')
