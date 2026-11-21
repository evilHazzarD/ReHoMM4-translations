# ReHoMM4 translations

Translations of Heroes of Might and Magic IV for ReHoMM4, the native port for Mac, Linux,
iPhone, iPad, Android and the Switch. Players pick a language from the list in the game's main
menu. The app then downloads that language's pack from this repository's latest release and applies
it to their own GOG copy of the game.

The translations are managed here, apart from the game's code, and reach players **only through a
release**. Commits change nothing for them. At every start the apps read the latest release's
`languages.json`, and they take a new pack when a release changes it.

| Language | Code | Code page | State |
|---|---|---|---|
| Українська (Ukrainian) | `uk` | Windows-1251 | interface, campaigns (with The Gathering Storm), single scenarios, voice-over of the original campaigns |

The Ukrainian translation was taken from [HoMM4Deadware](https://github.com/LeoDeadware/HoMM4Deadware).

Want to add your language? [TRANSLATING.md](TRANSLATING.md) walks through the whole path, from
creating the files to the release. A language GOG sells the game in (an official translation) needs
no translating at all: see [Official translations](TRANSLATING.md#official-translations).

## What is here, and what is not

```
languages/<code>/
  language.json       name, code page, options (tools/lang.py documents every field);
                      an official translation has only this file
  text/*.json         the translation: one file per campaign or interface table
  voice/clips.json    the campaign narration, line by line (for a recorded voice-over)
  GLOSSARY.md         how names and terms are translated
tools/                building, checking and releasing (Python 3; the fonts need macOS)
```

The repository carries **no game text**. Every entry names its English original by a key, the first
12 hex digits of the SHA-1 of the English text. `tools/prepare.py` puts the English back from your
own copy of the game, in `build/` (ignored by git). Voice recordings (`languages/<code>/voice/raw/`)
are not committed either.

## Releases

`tools/release.sh <version> <game dir> [<code>...]` makes the GitHub release `<version>` (tagged as given, e.g. `0.1`), for every
language or only those named (the others keep their packs from earlier releases). A pack is made from
the game, so a release is built on a maintainer's Mac, from their own GOG copy. The release
carries:

| File | What |
|---|---|
| `languages.json` | the list the apps read: each language's name, restart note, pack address, size and SHA-256 |
| `<code>.h4p` | the language pack: a delta of the game's archives that the app applies in place |
| `ReHoMM4-translations-<version>.zip` | the source: `languages/` and `tools/`, no game data |

Every push is checked by `tools/check.py` (the `check` workflow). It validates `language.json`,
checks that the entries match the reference translation, that every text fits the code page, and
that no `%keyword` is glued to letters.

## In ReHoMM4

ReHoMM4 does not include this repository: its apps get the translations only from the releases
here. Their builds start with the latest release's list and check for a newer one at every start;
the Mac DMG installer downloads the packs while it installs the game.
`H4_TRANSLATIONS_DIR=<this checkout> platforms/build.sh <platform>` in ReHoMM4 builds the packs
from a checkout into the app, for testing a translation before it is released.

## License

MIT ([LICENSE](LICENSE)). The Ukrainian translation and the tools started in
[HoMM4Deadware](https://github.com/LeoDeadware/HoMM4Deadware) (MIT, LeoDeadware).
