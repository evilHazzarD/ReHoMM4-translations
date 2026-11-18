# Translating Heroes IV into a new language

This guide goes from an empty folder to a language players can pick in the game. You need:

- **The game:** Heroes of Might and Magic IV Complete from GOG (version 3.0), installed or unpacked
  where the tools can read its `Data/` folder. In a ReHoMM4 checkout, that is `game/`.
- **Python 3.9 or newer.**
- **macOS**, to draw your letters into the game's fonts (`tools/glyphs` uses CoreText). The other
  steps work anywhere.
- Optionally, **ffmpeg** for a recorded voice-over, and **gh** (GitHub CLI) to make a release.

The examples use Polish (`pl`). Replace it with your language's code.

## 1. Check that the game can show your language

Heroes IV writes text one byte per character, in a single Windows code page. Find yours:

| Code page | Languages |
|---|---|
| `cp1250` | Polish, Czech, Slovak, Hungarian, Slovenian, Croatian, Romanian, Albanian |
| `cp1251` | Ukrainian, Russian, Belarusian, Bulgarian, Serbian (Cyrillic), Macedonian |
| `cp1252` | French, German, Spanish, Italian, Portuguese, Dutch, the Nordic languages |
| `cp1253` | Greek |
| `cp1254` | Turkish |
| `cp1257` | Lithuanian, Latvian, Estonian |

Languages outside these code pages cannot be done this way: Chinese, Japanese, Korean, Arabic,
Hebrew, Thai and others would need changes to the game's text drawing.

## 2. Create the language

```sh
python3 tools/new_language.py pl cp1250 "Polski" "Polish"
```

This creates `languages/pl/` with:

- `language.json`. Set `restart_note` to "Restart the game to apply the new language." in your
  language; the app shows it after a player picks the language. Every field is described at the
  top of `tools/lang.py`, including `replace` (typographic characters your code page lacks, and
  what to write instead) and `fonts` (other system fonts for the letters, by game font family).
- `text/*.json`, the same entries as the Ukrainian translation, with empty text.
- `voice/clips.json`, the narrated lines of the campaigns.
- `GLOSSARY.md`, for your names and terms.

## 3. Bring in the English and build the fonts

```sh
python3 tools/prepare.py pl /path/to/game
```

This writes `build/pl/catalog/*.json`. **These are the files you translate.** Each entry looks
like:

```json
{"id": 12, "where": "map 3", "en": "The bridge is out.", "text": ""}
```

Fill in `text`. Leave it empty to keep the English. The step also draws your code page's letters
into copies of the game's fonts (`build/pl/fonts`). Letters that look like Latin ones reuse the
game's own glyphs; the rest are rendered from a macOS system font, sized to match.

`build/` is ignored by git, because it contains the game's text. Never commit it.

## 4. Translate

| Files | What they are |
|---|---|
| `UI.Interface`, `UI.Text` | menus, buttons, messages |
| `Names.*`, `Help.*`, `Flavor.*` | creatures, spells, artifacts, skills, buildings, abilities |
| `Objects`, `Bio.heroes` | adventure map objects, hero biographies |
| `Campaign.*` | the six original campaigns |
| `wow_campaign.*`, `storm_campaign.*` | Winds of War, The Gathering Storm |
| `single.Tutorial` | the tutorial |

Rules the game itself imposes:

- **Keep `%keywords` intact, with a space or ASCII punctuation on each side.** The game swaps
  `%name`, `%value` and similar for real values. A non-ASCII letter or a guillemet right next to
  one hides it from the game. The tools refuse such text.
- **Keep line breaks** (`\n`, `\n\n`) where the English has them. Text that is much longer than
  the original may not fit its window, so check the result in the game.
- **Stay inside your code page.** No emoji, and no characters from other alphabets.
- **Do not change** `id`, `where`, `cells` or `en`, and do not add or remove entries.
- **Translate the same English the same way.** Interface tables already list each distinct
  English string once.

To merge a batch of translations (for example from a script, or from someone working in a
spreadsheet):

```sh
python3 tools/set_text.py pl build/pl/catalog/UI.Text.json batch.json   # {"<id>": "<text>"}
```

The Gathering Storm campaigns are only applied when `language.json` has
`"gathering_storm": true`.

## 5. Try it in the game

```sh
python3 tools/pack.py pl /path/to/game          # build/pl/pl.h4p
```

In a ReHoMM4 checkout, `H4_TRANSLATIONS_DIR=<this checkout> platforms/build.sh <platform>`
builds the packs into the app, so your language shows in the main menu's language list before it is
released. Run `export.py` first (step 6): the app build reads `languages/<code>/text`. Pick the
language, restart, and play.

For the Mac DMG version, `H4_TRANSLATIONS_DIR=<this checkout> platforms/macos-dmg/install_app.sh --loc pl`
applies it to the installed app.

## 6. Save your work into the repository

```sh
python3 tools/export.py pl      # build/pl/catalog -> languages/pl/text, English replaced by keys
python3 tools/check.py pl
git add languages/pl && git commit -m "Polish: the interface"
```

Run `export.py` whenever you want to commit. Open a pull request, or push to your fork. The
`check` workflow runs `check.py` on every push.

## 7. Voice-over (optional)

The original campaigns' narration can be re-recorded. `voice/clips.json` lists each clip (its
`clip` name, campaign and map) with the text it reads. Put the recordings at
`languages/pl/voice/raw/<clip>.mp3`. They are not committed; share them as a release asset or a
zip. `pack.py` converts them with ffmpeg to the game's format (44.1 kHz stereo MP3). Clips without
a recording keep the English voice.

## 8. Release

Players get translations only from a release of this repository. A maintainer makes one when the
work is ready, for all languages at once:

```sh
gh auth login                                        # once
bash tools/release.sh 2026.12 /path/to/game          # the GitHub release v2026.12
```

This builds every language's pack from `languages/*/text`, plus the button pictures for Linux
and the Switch, and uploads them with `languages.json` and a zip of the source. Commit and push
first; the script refuses a tree with uncommitted changes. The apps see the release at their next
start. A player who has picked a language gets its new pack (checked by size and SHA-256) the
time after that. Bump `version` in `language.json` when your language changes.

To try a release without uploading it, set `H4_RELEASE_BASE=http://<your Mac>:8000/`. The files
then land in `build/release-<version>/`; serve that folder (`python3 -m http.server`) and build the
app with `H4_TRANSLATIONS_URL=http://<your Mac>:8000/languages.json`.

## Tools reference

| Tool | Does |
|---|---|
| `new_language.py <code> <codepage> <name> <english name>` | creates `languages/<code>/` |
| `prepare.py <code> <game dir>` | English into `build/<code>/catalog`, fonts into `build/<code>/fonts` |
| `set_text.py <code> <catalog> <batch.json>` | merges translations, checks the code page |
| `campaign_catalog.py <code> <campaign>` | rebuilds one campaign's catalog from the game, keeping translations |
| `ui_text.py extract <code> <text.h4r>` | the same for the interface tables |
| `export.py <code>` | `build/<code>/catalog` → `languages/<code>/text` |
| `check.py [<code>...]` | validates without the game (CI) |
| `apply.py <code> <game dir>` | patches a game's archives in place (use a copy) |
| `pack.py <code> <game dir>` | `build/<code>/<code>.h4p`, the pack the app applies |
| `release.sh <version> <game dir> [owner/name]` | the GitHub release the apps read (all languages) |
| `render_ui.swift <out dir> <languages.tsv>` | the language button pictures for Linux and the Switch |
