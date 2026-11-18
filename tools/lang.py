"""A language of the translation: languages/<code>/language.json and where its files are.

    {
      "code": "uk",                    ISO 639-1, the folder name; what the app saves and shows
      "name": "Українська",            the language's own name (the app's language button)
      "english_name": "Ukrainian",
      "codepage": "cp1251",            the Windows code page the game's text is written in
      "replace": {"’": "'"},           characters the code page lacks -> what to write instead
      "gathering_storm": false,        The Gathering Storm campaigns translated too (default false)
      "letters": "АБВ...",             optional: only these characters drawn into the fonts
      "fonts": {"Script": "..."},      optional: other macOS fonts, by game font family
      "sample": "...",                 optional: the font preview's text
      "restart_note": "Перезапустіть гру, щоб застосувати нову мову.",
      "version": "1.0"                 bumped by its maintainers, shown in releases
    }

Generated files (the game's English text, extracted archives, fonts, the pack) go to
build/<code>/ (or $H4_LOC_WORK/<code>/), never committed.
"""
import codecs
import glob
import json
import os

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
LANGUAGES = os.path.join(ROOT, 'languages')
FIELD = 'text'  # the translated text in every catalog entry

# Code pages the game can show: one byte per character, the fonts' 224 glyphs (32..255).
CODEPAGES = ('cp1250', 'cp1251', 'cp1252', 'cp1253', 'cp1254', 'cp1257')

# Archives that hold the campaign files, by the catalog name's prefix.
CAMPAIGN_ARCHIVES = {'Campaign.': 'updates.h4r', 'storm_campaign.': 'storm.h4r',
                     'wow_campaign.': 'x2.h4r', 'single.': 'heroes4.h4r'}


def codes():
    """Every language with a language.json, sorted."""
    return sorted(os.path.basename(os.path.dirname(p))
                  for p in glob.glob(os.path.join(LANGUAGES, '*', 'language.json')))


class Language:
    def __init__(self, code):
        self.code = code
        self.dir = os.path.join(LANGUAGES, code)
        path = os.path.join(self.dir, 'language.json')
        if not os.path.exists(path):
            raise SystemExit(f'no {os.path.relpath(path, ROOT)}: make it with tools/new_language.py')
        self.meta = json.load(open(path, encoding='utf-8'))
        assert self.meta.get('code') == code, f'{path}: "code" must be "{code}"'
        self.name = self.meta['name']
        self.english_name = self.meta.get('english_name', self.name)
        self.codepage = self.meta['codepage']
        assert self.codepage in CODEPAGES, f'{path}: codepage must be one of {", ".join(CODEPAGES)}'
        codecs.lookup(self.codepage)
        self.replace = self.meta.get('replace', {})
        self.storm = bool(self.meta.get('gathering_storm', False))
        self.text_dir = os.path.join(self.dir, 'text')
        self.clips = os.path.join(self.dir, 'voice', 'clips.json')
        self.voice_raw = os.path.join(self.dir, 'voice', 'raw')
        self.work = os.path.join(os.environ.get('H4_LOC_WORK') or os.path.join(ROOT, 'build'), code)
        self.extract = os.path.join(self.work, 'extract')      # the game's campaign files
        self.catalog = os.path.join(self.work, 'catalog')      # catalogs with the English back in
        self.fonts_en = os.path.join(self.work, 'fonts_en')    # the game's fonts
        self.fonts = os.path.join(self.work, 'fonts')          # the fonts with this code page's glyphs
        self.build = os.path.join(self.work, 'build')          # rebuilt campaign files
        self.pack = os.path.join(self.work, code + '.h4p')

    def clean(self, s):
        for a, b in self.replace.items():
            s = s.replace(a, b)
        return s

    def encode(self, s):
        """The text as the game reads it (characters the code page lacks become '?')."""
        return self.clean(s).encode(self.codepage, 'replace')

    def unencodable(self, s):
        """The characters of s the code page cannot write, after the replacements."""
        out = []
        for ch in self.clean(s):
            try:
                ch.encode(self.codepage)
            except UnicodeEncodeError:
                out.append(ch)
        return out
