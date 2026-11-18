"""Checks every language (or the ones named) without the game: language.json is valid, the
catalogs match the reference translation's keys, every text fits the code page, and %keywords
are not glued to letters. CI runs it on every push.

    check.py [<code> ...]
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import apply  # noqa: E402
import lang as L  # noqa: E402


def check(code, ref_keys):
    lg = L.Language(code)
    errors, done, total = [], 0, 0
    for k in ('name', 'english_name', 'codepage', 'restart_note', 'version'):
        if not lg.meta.get(k):
            errors.append(f'language.json: no "{k}"')
    if lg.unencodable(lg.name):
        errors.append('language.json: "name" does not fit the code page')
    for path in sorted(glob.glob(os.path.join(lg.text_dir, '*.json'))):
        base = os.path.basename(path)
        items = json.load(open(path, encoding='utf-8'))
        keys = [it['key'] for it in items]
        if base in ref_keys and keys != ref_keys[base]:
            errors.append(f'{base}: entries differ from languages/uk (added, removed or reordered)')
        for it in items:
            text = it.get(L.FIELD, '')
            total += 1
            done += bool(text)
            if 'en' in it:
                errors.append(f'{base} #{it["id"]}: has the English text (run tools/export.py)')
            bad = lg.unencodable(text)
            if bad:
                errors.append(f'{base} #{it["id"]}: {lg.codepage} has no {"".join(sorted(set(bad)))!r}')
    errors += apply.keyword_glue(lg.text_dir)
    return errors, done, total


def main(codes):
    ref = L.Language('uk')
    ref_keys = {os.path.basename(p): [it['key'] for it in json.load(open(p, encoding='utf-8'))]
                for p in glob.glob(os.path.join(ref.text_dir, '*.json'))}
    failed = False
    for code in codes or L.codes():
        errors, done, total = check(code, ref_keys)
        print(f'{code}: {done}/{total} translated' + (f', {len(errors)} problems' if errors else ''))
        for e in errors[:50]:
            print('  ' + e)
        failed |= bool(errors)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main(sys.argv[1:])
