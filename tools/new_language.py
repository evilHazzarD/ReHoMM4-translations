"""Starts a new language: languages/<code>/ with language.json and every catalog of the
reference translation (languages/uk) with its text emptied, so the new one lists exactly the
strings the game shows (by key: no game text is in the repository).

    new_language.py <code> <codepage> "<name in the language>" "<name in English>"

    e.g. new_language.py cs cp1250 "Čeština" "Czech"

Then: tools/prepare.py <code> <game dir> puts the English in (build/<code>/catalog), you
translate there, tools/export.py <code> writes it back. TRANSLATING.md has the whole path.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lang as L  # noqa: E402

REFERENCE = 'uk'


def main(code, codepage, name, english_name):
    assert re.fullmatch(r'[a-z]{2,3}(-[A-Za-z0-9]{2,8})?', code), 'code: ISO 639 (e.g. pl, pt-BR)'
    assert code != 'en', 'English is the game as it is'
    assert codepage in L.CODEPAGES, f'codepage: one of {", ".join(L.CODEPAGES)}'
    dst = os.path.join(L.LANGUAGES, code)
    assert not os.path.exists(dst), f'{dst} exists'
    ref = L.Language(REFERENCE)
    os.makedirs(os.path.join(dst, 'text'))
    for path in sorted(glob.glob(os.path.join(ref.text_dir, '*.json'))):
        items = [it | {L.FIELD: ''} for it in json.load(open(path, encoding='utf-8'))]
        json.dump(items, open(os.path.join(dst, 'text', os.path.basename(path)), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    if os.path.exists(ref.clips):
        os.makedirs(os.path.join(dst, 'voice'))
        clips = [it | {L.FIELD: ''} for it in json.load(open(ref.clips, encoding='utf-8'))]
        json.dump(clips, open(os.path.join(dst, 'voice', 'clips.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
    meta = {'code': code, 'name': name, 'english_name': english_name, 'codepage': codepage,
            'replace': {'’': "'"}, 'gathering_storm': False,
            'restart_note': 'Restart the game to apply the new language.', 'version': '0.1'}
    json.dump(meta, open(os.path.join(dst, 'language.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    open(os.path.join(dst, 'GLOSSARY.md'), 'w', encoding='utf-8').write(
        f'# {english_name} glossary\n\nNames, places and game terms as this translation writes them, '
        'so every file says them the same way. Add rows; do not rewrite other people\'s.\n\n'
        '| English | ' + name + ' | Note |\n|---|---|---|\n')
    print(f'{dst}: {len(glob.glob(os.path.join(dst, "text", "*.json")))} catalogs. '
          f'Edit language.json ("restart_note" in {english_name}), then tools/prepare.py {code} <game dir>')


if __name__ == '__main__':
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    main(*sys.argv[1:5])
