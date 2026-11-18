"""A translation as a delta of the game's archives: the language pack the app applies
(ReHoMM4 h4/src/language.cpp).

tools/apply.py patches a game's archives by appending the new data and
rewriting the replaced entries' 12-byte headers (offset, stored, size:
h4r.patch). This compares the original archives with patched copies and
writes what changed:

    "H4P1", u32 archive count, then per archive:
      u16 name length, name (in Data/), u64 original size, u64 appended size,
      u32 entry count, per entry: u32 file position, 12 bytes English, 12 bytes translated,
      then the appended bytes.

The app appends them to the player's own (English) archives once; the language is
then chosen by which header bytes are written, in place, without a second
copy of the game.

    make_pack.py <original Data dir> <patched Data dir> <out file>   (pack.py runs it)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h4r  # noqa: E402

ARCHIVES = ['heroes4.h4r', 'updates.h4r', 'text.h4r', 'storm.h4r', 'x2.h4r']


def main(orig_dir, new_dir, out):
    tmp = out + '.tmp'
    with open(tmp, 'wb') as f:
        f.write(b'H4P1' + struct.pack('<I', len(ARCHIVES)))
        for name in ARCHIVES:
            a, entries = h4r.read_dir(os.path.join(orig_dir, name))
            b = open(os.path.join(new_dir, name), 'rb').read()
            assert len(b) >= len(a), name
            heads = [e.at for e in entries if a[e.at:e.at + 12] != b[e.at:e.at + 12]]
            # Nothing else of the original part may differ.
            rest = bytearray(b[:len(a)])
            for p in heads:
                rest[p:p + 12] = a[p:p + 12]
            assert bytes(rest) == a, f'{name}: changes outside entry headers'
            appended = b[len(a):]
            f.write(struct.pack('<H', len(name)) + name.encode())
            f.write(struct.pack('<QQI', len(a), len(appended), len(heads)))
            for p in heads:
                f.write(struct.pack('<I', p) + a[p:p + 12] + b[p:p + 12])
            f.write(appended)
            print(f'{name}: {len(heads)} entries, +{len(appended)} bytes')
    os.replace(tmp, out)
    print(f'{out}: {os.path.getsize(out)} bytes')


if __name__ == '__main__':
    main(*sys.argv[1:4])
