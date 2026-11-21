"""Draws a language's letters into the Heroes IV fonts, in its code page's slots.

The fonts cover codes 32..255 as Windows-1252; a translation's text is written in its own
Windows code page (languages/<code>/language.json). For every code where that page has a
character Windows-1252 shows differently:
  - the same character elsewhere in Windows-1252 (ó, « », „ “ ”) gets that glyph;
  - a letter that looks like a Latin one (Cyrillic А В Е К М Н О Р С Т Х І Ї Ё а е о р с у х
    і ї ё, Greek Α Β Ε Ζ Η Ι Κ Μ Ν Ο Ρ Τ Υ Χ ο) gets a copy of the game's own Latin glyph, so most
    of a line is drawn in the original face;
  - the rest are rendered by CoreText (tools/glyphs, macOS) from a system font that has them:
    capitals sized so H is as tall as the game's H, small letters so x is as tall as the game's
    x, with the game's 1-pixel right bearing. language.json "fonts" can name other faces, and
    "letters" limits the characters drawn to the ones the language uses (default: all of them).

    build_fonts.py <language code> <in dir with font.*.h4d> <out dir> [preview dir]
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import h4font  # noqa: E402
import lang as L  # noqa: E402

GLYPHS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'glyphs')

# Letters drawn as a Latin one: the character -> the Windows-1252 character whose glyph it gets.
LOOKALIKE = dict(zip('АВЕКМНОРСТХІЇЁЅЈаеорсухіїёѕј' 'ΑΒΕΖΗΙΚΜΝΟΡΤΥΧο',
                     'ABEKMHOPCTXIÏËSJaeopcyxiïësj' 'ABEZHIKMNOPTYXo'))


def plan(codepage, letters=None):
    """({code: Windows-1252 code whose glyph it copies}, [codes to render]) for a code page
    (only the characters in `letters` when it is given)."""
    copy, render = {}, []
    for code in range(0x80, 0x100):
        try:
            ch = bytes([code]).decode(codepage)
        except UnicodeDecodeError:
            continue  # unused in that code page
        if letters is not None and ch not in letters:
            continue
        try:
            if bytes([code]).decode('cp1252') == ch:
                continue  # already right
        except UnicodeDecodeError:
            pass
        latin = LOOKALIKE.get(ch, ch)
        try:
            copy[code] = latin.encode('cp1252')[0]
        except UnicodeEncodeError:
            if ch.isprintable() and not ch.isspace():
                render.append(code)
    return copy, render


# Game font family -> (system font, antialiased).
FACES = {
    'Prose_Antique': ('GillSans-SemiBold', True),
    'Script': ('SnellRoundhand-Bold', True),
    'Small Fonts': ('Geneva', False),
}


def family(name):
    for k in FACES:
        if k in name:
            return k
    raise KeyError(name)


def render(face, pt, cell, base, aa, text):
    out = subprocess.run([GLYPHS, 'render', face, '%.2f' % pt, str(cell), str(base), '1' if aa else '0', text],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    glyphs = []
    for line in out:
        w, _, hexpx = line.partition(' ')
        glyphs.append((int(w), bytes.fromhex(hexpx)))
    return glyphs


def ink_rows(w, h, px, threshold=60):
    rows = [y for y in range(h) if any(px[y * w + x] > threshold for x in range(w))]
    return (rows[0], rows[-1]) if rows else (0, -1)


def fit(font, face, aa, ch='H'):
    """(point size, baseline row) at which ch is as tall as the game's."""
    w, h, _, _, px = font.glyph(ord(ch))
    top, bottom = ink_rows(w, h, px)
    want = bottom - top + 1
    best = None
    pt = want * (1.0 if ch == 'H' else 1.4)
    for _ in range(40):
        (rw, rpx), = render(face, pt, h, bottom, aa, ch)
        t, b = ink_rows(rw, h, rpx)
        got = b - t + 1
        err = abs(got - want)
        if best is None or err < best[0]:
            best = (err, pt)
        if got == want:
            break
        pt *= want / max(got, 1)
        pt += 0.25 if got < want else -0.25
    return best[1], bottom


def convert(px, aa):
    if aa:
        return bytearray(min(240, v * 240 // 255) for v in px)
    return bytearray(240 if v > 127 else 0 for v in px)


def pad(w, h, px, left, right):
    out = bytearray()
    for y in range(h):
        out += bytes(left) + px[y * w:(y + 1) * w] + bytes(right)
    return w + left + right, out


def build(lg, path_in, path_out):
    name = os.path.basename(path_in)
    font = h4font.Font(open(path_in, 'rb').read())
    fam = family(name)
    face, aa = FACES[fam]
    face = lg.meta.get('fonts', {}).get(fam, face)
    left = 1 if fam == 'Small Fonts' else 0
    copy, rendered = plan(lg.codepage, lg.meta.get('letters'))
    for code, latin in copy.items():
        if code >= font.first and latin >= font.first:
            w, h, c, d, px = font.glyph(latin)
            g = font.glyph(code)
            g[0], g[2], g[3], g[4] = w, c, d, bytearray(px)
    sizes = {'H': fit(font, face, aa, 'H'), 'x': fit(font, face, aa, 'x')}
    if not rendered:
        open(path_out, 'wb').write(font.encode())
        return font, face, sizes
    text = bytes(rendered).decode(lg.codepage)
    for case, (pt, base) in sizes.items():
        for code, ch, (w, px) in zip(rendered, text, render(face, pt, font.size, sizes['H'][1], aa, text)):
            small = ch.islower() or ch == '№'
            if (case == 'x') != small or code < font.first or w == 0:
                continue
            w2, px2 = pad(w, font.size, convert(px, aa), left, 1)
            g = font.glyph(code)
            g[0], g[2], g[3], g[4] = w2, 0, 0, px2
    open(path_out, 'wb').write(font.encode())
    return font, face, sizes


def line(font, data):
    """A PGM image of a line of text set with the font."""
    h = font.size
    glyphs = [font.glyph(c) for c in data if c >= font.first]
    W = sum(g[0] for g in glyphs) + 4
    img = bytearray(W * h)
    x0 = 2
    for w, _, _, _, px in glyphs:
        for y in range(h):
            for x in range(w):
                img[y * W + x0 + x] = px[y * w + x]
        x0 += w
    return b'P5 %d %d 255\n' % (W, h) + bytes(img)


if __name__ == '__main__':
    code, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    prev = sys.argv[4] if len(sys.argv) > 4 else None
    lg = L.Language(code)
    sample = lg.meta.get('sample') or ''.join(bytes([c]).decode(lg.codepage) for c in plan(lg.codepage, lg.meta.get('letters'))[1])
    os.makedirs(dst, exist_ok=True)
    for name in sorted(os.listdir(src)):
        if not name.startswith('font.'):
            continue
        font, face, sizes = build(lg, os.path.join(src, name), os.path.join(dst, name))
        print(f"{name}: {face} H {sizes['H'][0]:.2f}pt x {sizes['x'][0]:.2f}pt")
        if prev:
            os.makedirs(prev, exist_ok=True)
            open(os.path.join(prev, name + '.pgm'), 'wb').write(line(font, lg.encode(sample)))
