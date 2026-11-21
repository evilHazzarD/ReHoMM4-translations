"""A language pack for the Windows game from GOG (Heroes IV Complete 3.0, English) without ReHoMM4:
unzip into the game folder, and it is in. Nothing of the game is changed: the translated entries
go into Data/new.h4r, the archive heroes4.exe opens last (its entries replace the same names in
every other archive: what the Russian localizations put over the English game use), and the
translated single scenarios into maps/, over the English ones. Deleting Data/new.h4r brings the
English text back (the maps stay translated until the game's are restored).

    windows.py <pack .h4p> <English Data dir> <out .zip> [<readme>]

The pack holds, per archive, the replaced entries' headers (make_pack.py: the format); their names
and the rest of their directory records are read from the English archives. A name the pack
changes in two archives must have the same data in both (one new.h4r entry replaces it in all).
"""
import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h4r  # noqa: E402


def read_pack(path):
    """([(archive, original size, [(pos, translated header, data)])], [(path, bytes)])"""
    archives, files = [], []
    with open(path, 'rb') as f:
        assert f.read(4) == b'H4P1', f'{path}: not a language pack'
        (n,) = struct.unpack('<I', f.read(4))
        for _ in range(n):
            (ln,) = struct.unpack('<H', f.read(2))
            name = f.read(ln).decode()
            size, appended, count = struct.unpack('<QQI', f.read(20))
            heads = []
            for _ in range(count):
                (pos,) = struct.unpack('<I', f.read(4))
                f.read(12)
                heads.append((pos, f.read(12)))
            blob = f.read(appended)
            out = []
            for pos, tr in heads:
                off, stored, _ = struct.unpack('<III', tr)
                out.append((pos, tr, blob[off - size:off - size + stored]))
            archives.append((name, size, out))
        if f.read(4) == b'H4PF':
            (n,) = struct.unpack('<I', f.read(4))
            for _ in range(n):
                (ln,) = struct.unpack('<H', f.read(2))
                rel = f.read(ln).decode('cp1252')
                (size,) = struct.unpack('<Q', f.read(8))
                files.append((rel, f.read(size)))
    return archives, files


def record(d, e):
    """The entry's directory record after offset/stored/size: time, name, path and the rest."""
    p = e.at + 16
    p += 2 + struct.unpack_from('<H', d, p)[0]  # name
    p += 2 + struct.unpack_from('<H', d, p)[0]  # path
    extra = e.extra or b'\0\0' + d[p + 2:p + 6]  # the last entry: u16 0, u32 kind
    return d[e.at + 12:p] + extra


def new_h4r(pack, data_dir):
    """new.h4r bytes and the number of entries in it."""
    archives, _ = read_pack(pack)
    entries = {}  # lower-case name: (record, stored, size, data)
    for name, size, changed in archives:
        d, es = h4r.read_dir(os.path.join(data_dir, name))
        assert len(d) == size, f'{name}: not the English GOG archive'
        byat = {e.at: e for e in es}
        for pos, tr, blob in changed:
            e = byat[pos]
            _, stored, usize = struct.unpack('<III', tr)
            key = e.name.lower()
            if key in entries:
                assert entries[key][3] == blob, f'{e.name}: translated otherwise in {name}'
                continue
            entries[key] = (record(d, e), stored, usize, blob)
    items = sorted(entries.values(), key=lambda x: x[0])
    dir_size = 4 + sum(12 + len(r) for r, *_ in items)
    head = bytearray(b'H4R\x05' + struct.pack('<II', 8, len(items)))
    body = bytearray()
    at = 8 + dir_size
    for rec, stored, usize, blob in items:
        head += struct.pack('<III', at + len(body), stored, usize) + rec
        body += blob
    assert len(head) == 8 + dir_size
    return bytes(head + body), len(items)


def main(pack, data_dir, out, readme=None):
    blob, n = new_h4r(pack, data_dir)
    _, files = read_pack(pack)
    tmp = out + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('Data/new.h4r', blob)
        for rel, b in files:
            z.writestr(rel, b)
        if readme:
            z.write(readme, os.path.basename(readme))
    os.replace(tmp, out)
    print(f'{out}: Data/new.h4r ({n} entries, {len(blob)} bytes), {len(files)} maps')


if __name__ == '__main__':
    if len(sys.argv) not in (4, 5):
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
