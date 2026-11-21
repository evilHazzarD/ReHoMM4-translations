# Translating Heroes IV into a new language

This guide goes from an empty folder to a language players can pick in the game. (A language GOG
already sells the game in needs none of it: see [Official translations](#official-translations).)
You need:

- **The game:** Heroes of Might and Magic IV Complete from GOG (version 3.0), installed or unpacked
  where the tools can read its `Data/` folder. In a ReHoMM4 checkout, that is `game/`.
- **Python 3.9 or newer.**
- **macOS**, to draw your letters into the game's fonts (`tools/glyphs` uses CoreText). The other
  steps work anywhere.
- Optionally, **ffmpeg** for a recorded voice-over, and **gh** (GitHub CLI) to make a release.

The examples use Czech (`cs`). Replace it with your language's code.

## 1. Check that the game can show your language

Heroes IV writes text one byte per character, in a single Windows code page. Find yours:

| Code page | Languages |
|---|---|
| `cp1250` | Czech, Polish, Slovak, Hungarian, Slovenian, Croatian, Romanian, Albanian |
| `cp1251` | Ukrainian, Russian, Belarusian, Bulgarian, Serbian (Cyrillic), Macedonian |
| `cp1252` | French, German, Spanish, Italian, Portuguese, Dutch, the Nordic languages |
| `cp1253` | Greek |
| `cp1254` | Turkish |
| `cp1257` | Lithuanian, Latvian, Estonian |

Languages outside these code pages cannot be done this way: Chinese, Japanese, Korean, Arabic,
Hebrew, Thai and others would need changes to the game's text drawing.

## 2. Create the language

```sh
python3 tools/new_language.py cs cp1250 "Čeština" "Czech"
```

This creates `languages/cs/` with:

- `language.json`. Set `restart_note` to "Restart the game to apply the new language." in your
  language; the app shows it after a player picks the language. Every field is described at the
  top of `tools/lang.py`, including `replace` (typographic characters your code page lacks, and
  what to write instead) and `fonts` (other system fonts for the letters, by game font family).
- `text/*.json`, the same entries as the Ukrainian translation, with empty text.
- `voice/clips.json`, the narrated lines of the campaigns.
- `GLOSSARY.md`, for your names and terms.

## 3. Bring in the English and build the fonts

```sh
python3 tools/prepare.py cs /path/to/game
```

This writes `build/cs/catalog/*.json`. **These are the files you translate.** Each entry looks
like:

```json
{"id": 12, "where": "map 3", "en": "The bridge is out.", "text": ""}
```

Fill in `text`. Leave it empty to keep the English. The step also draws your code page's letters
into copies of the game's fonts (`build/cs/fonts`). Letters that look like Latin ones reuse the
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
| `Map.*` | the single scenarios (`maps/*.h4c`), one catalog per map |

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
python3 tools/set_text.py cs build/cs/catalog/UI.Text.json batch.json   # {"<id>": "<text>"}
```

The Gathering Storm campaigns are only applied when `language.json` has
`"gathering_storm": true`.

In the maps, leave the map editor's own labels empty ("Timed Event", "Computer Bonus",
"Starting event"): the player never sees them. A map's text is only found again if it still reads
as text in the scenario file, so a short string needs at least half of its characters to be
letters of Windows-1252; letters outside it (Cyrillic і, ї, є) do not count. `pack.py` stops with
"string layout changed" and the map's name when one does not. Make that string a little longer
(for example "Вежі: 2" → "Вежі магів: 2").

## 5. Try it in the game

```sh
python3 tools/pack.py cs /path/to/game          # build/cs/cs.h4p
```

In a ReHoMM4 checkout, `H4_TRANSLATIONS_DIR=<this checkout> platforms/build.sh <platform>`
builds the packs into the app, so your language shows in the main menu's language list before it is
released. Run `export.py` first (step 6): the app build reads `languages/<code>/text`. Pick the
language, restart, and play.

`pack.py` needs the English archives. If the game folder has been played in a translation, the
app has put that pack into its archives. `pack.py` takes the pack out of copies of the archives,
using `build/<code>/<code>.h4p`, `build/<code>/applied/` (where it keeps the packs it took out) and
any `.h4p` listed in `H4_APPLIED_PACKS` (paths separated by `:`). The game folder itself is not
changed. If no pack matches, it stops and names the archives. `tools/take_out.py <Data dir> <pack>...`
does the same in place.

For the Mac DMG version, `H4_TRANSLATIONS_DIR=<this checkout> platforms/macos-dmg/install_app.sh --loc cs`
applies it to the installed app.

## 6. Save your work into the repository

```sh
python3 tools/export.py cs      # build/cs/catalog -> languages/cs/text, English replaced by keys
python3 tools/check.py cs
git add languages/cs && git commit -m "Czech: the interface"
```

Run `export.py` whenever you want to commit. Open a pull request, or push to your fork. The
`check` workflow runs `check.py` on every push.

## 7. Voice-over (optional)

The original campaigns' narration can be re-recorded. `voice/clips.json` lists each clip (its
`clip` name, campaign and map) with the text it reads. Put the recordings at
`languages/cs/voice/raw/<clip>.mp3`. They are not committed; share them as a release asset or a
zip. `pack.py` converts them with ffmpeg to the game's format (44.1 kHz stereo MP3). Clips without
a recording keep the English voice.

## 8. Release

Players get translations only from a release of this repository. A maintainer makes one when the
work is ready, for all languages or only the ones that changed:

```sh
gh auth login                                        # once
bash tools/release.sh 2026.12 /path/to/game          # every language: the GitHub release 2026.12
bash tools/release.sh 2026.12.1 /path/to/game cs     # only Czech
```

This builds the packs from `languages/<code>/text` and uploads them with `languages.json` and a zip
of the source. When only some languages are named, the others keep their entries from the previous
release's `languages.json`, with their packs where they were uploaded then: players of those
languages download nothing. So never delete an old release while its pack is still in use (the
latest `languages.json` shows each pack's address). Commit and push first; the script refuses a tree with uncommitted changes. The apps see the release at their next
start. A player who has picked a language gets its new pack (checked by size and SHA-256) the
time after that. Bump `version` in `language.json` when your language changes.

To try a release without uploading it, set `H4_RELEASE_BASE=http://<your Mac>:8000/`. The files
then land in `build/release-<version>/`; serve that folder (`python3 -m http.server`) and build the
app with `H4_TRANSLATIONS_URL=http://<your Mac>:8000/languages.json`.

## Official translations

GOG sells Heroes IV Complete in other languages too (the **Language** switch on the game's page in
your library). Such a version can become a language here as it is, without translating anything:
its text, fonts, pictures with words, voice-over and the expansions' movies are taken from its
`Data/` archives into a pack. ReHoMM4 keeps running the English `heroes4.exe` (the localized one
is another build of the game), which reads the localized archives as well as its own.

1. Download the localized **offline installer** from GOG (both parts: `setup_….exe` and
   `setup_…-1.bin`) into `~/Downloads`.
2. Create `languages/<code>/language.json` by hand, with `official` instead of a `text/` folder,
   for example (with your language's code, name and code page; the installer's name as GOG gives it):

   ```json
   {
    "code": "xx",
    "name": "<the language's own name>",
    "english_name": "<its English name>",
    "codepage": "cp1252",
    "restart_note": "<Restart the game to apply the new language, in that language>",
    "version": "1.0",
    "official": {
     "installer": "setup_heroes_of_might_and_magic_4_complete_*_(<language>)_*.exe",
     "from": "GOG, Heroes of Might and Magic IV Complete 3.0, <language> (the official translation)"
    }
   }
   ```

   `installer` is the installer's file name, with `*` where the version may change. `codepage` is
   the one of step 1 above for that language.
3. Build the pack: `python3 tools/pack.py xx /path/to/english/game`. It unpacks the installer once
   (innoextract) into `build/xx/official/` and compares every archive entry with the English game
   (`tools/official.py` explains the rules). `H4_OFFICIAL_XX=<an unpacked localized game folder>`
   uses that folder instead of the installer.
4. Try it and release it as in steps 5 and 8 (`H4_TRANSLATIONS_DIR=…`, `release.sh`). Nothing of
   the localized game is committed: the repository holds only `language.json`.

A localization made to be put over the English GOG game (a folder with `Data/new.h4r`, the
archive the game opens last, and maybe its own maps) works the same way: `"folder"` instead of
`"installer"`, the folder's name in `~/Downloads`, and `"maps"` for where its maps are in it, for
example Russian:

```json
"official": {
 "folder": "Heroes4_Russification",
 "maps": "Maps/RUS",
 "from": "Buka's Russian localization, as put over the English GOG game (Data/new.h4r, Maps/RUS)"
}
```

Each entry of `new.h4r` replaces the entry of that name the English game reads. Voice-over stored
as raw PCM is re-encoded as MP3, as the English voice-over is (with ffmpeg; ten times smaller).

The single scenarios (`maps/*.h4c`, outside the archives) go into the pack as files: the app
unpacks them beside the game and reads them in place of the English ones (the game folder is not
changed). A map the localized version does not have stays English.

## Tools reference

| Tool | Does |
|---|---|
| `new_language.py <code> <codepage> <name> <english name>` | creates `languages/<code>/` |
| `prepare.py <code> <game dir>` | English into `build/<code>/catalog`, fonts into `build/<code>/fonts` |
| `set_text.py <code> <catalog> <batch.json>` | merges translations, checks the code page |
| `map_catalog.py <code> <game dir>` | rebuilds the single scenarios' catalogs from the game, keeping translations |
| `take_out.py <Data dir> <pack>...` | takes a pack the app applied back out of the archives, in place |
| `campaign_catalog.py <code> <campaign>` | rebuilds one campaign's catalog from the game, keeping translations |
| `ui_text.py extract <code> <text.h4r>` | the same for the interface tables |
| `export.py <code>` | `build/<code>/catalog` → `languages/<code>/text` |
| `check.py [<code>...]` | validates without the game (CI) |
| `apply.py <code> <game dir>` | patches a game's archives in place (use a copy) |
| `pack.py <code> <game dir>` | `build/<code>/<code>.h4p`, the pack the app applies |
| `official.py <code> <game dir> [<localized copy>]` | the pack of an official translation, from a localized GOG copy (pack.py runs it) |
| `release.sh <version> <game dir> [<code>...]` | the GitHub release the apps read (all languages, or only those named) |
