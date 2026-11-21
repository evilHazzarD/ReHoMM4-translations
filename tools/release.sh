#!/bin/bash
# release.sh <version> <game dir> [<code>...]: a release of the translations, the only way they
# reach players. It builds the pack of each language named (all of languages/ when none is) from
# languages/<code>/text (tools/pack.py --from-repo, from your own GOG copy), then makes the GitHub
# release <version> (its tag) with:
#
#   languages.json      the list the app reads (releases/latest/download/languages.json): every
#                       language, {"version", "languages": [{"code", "name", "english", "note",
#                       "version", "url", "sha256", "size"}]}
#   <code>.h4p          the pack of each language built now
#   ReHoMM4-translations-<version>.zip     the source (languages/ and tools/, no game data)
#
# Updating one language: `release.sh 1.1.0 <game dir> uk` builds only uk; every other language
# keeps its entry from the previous release's languages.json (its pack where it was uploaded
# then: never delete an old release while a language's pack is still in it). Its name and note
# are taken from languages/ as they are now. A language not in the previous release must be built.
#
# The apps check languages.json at every start and take a language's new pack (its SHA-256
# changed) at the next start; the other languages are not downloaded again. Commits alone change
# nothing for players. Needs a clean, pushed tree, `gh` signed in (gh auth login), macOS (the
# fonts) and ffmpeg (voice-over). The repository: H4_RELEASE_REPO (owner/name), else the origin
# remote. H4_RELEASE_PREVIOUS: the previous languages.json (a file or an address) instead of the
# latest release's.
# H4_RELEASE_BASE=<url>/ makes the files in build/release-<version> for a test server instead
# (URLs under that address, uncommitted changes allowed, nothing uploaded).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:?usage: release.sh <version> <game dir> [<code>...]}"; GAME="${2:?game dir}"; shift 2
TAG="$VERSION"  # the tag is the version as given: 0.1 (as the first release)
REPO="${H4_RELEASE_REPO:-$( (git -C "$ROOT" remote get-url origin 2>/dev/null || true) | sed -E 's#(\.git)?$##; s#^.*github\.com[:/]##')}"
DRY="${H4_RELEASE_BASE:-}"
if [[ -z "$DRY" ]]; then
  [[ "$REPO" == */* ]] || { echo "no GitHub remote: set H4_RELEASE_REPO=owner/name"; exit 1; }
  [[ -z "$(git -C "$ROOT" status --porcelain)" ]] || { echo "uncommitted changes: commit and push first"; exit 1; }
fi
python3 -I "$ROOT/tools/check.py"
OUT="$ROOT/build/release-$VERSION"; rm -rf "$OUT"; mkdir -p "$OUT"
export H4_LOC_WORK="$ROOT/build/release-work"  # not build/<code>: your unexported work stays
ALL=(); for j in "$ROOT"/languages/*/language.json; do ALL+=("$(basename "$(dirname "$j")")"); done
CODES=("$@"); [[ ${#CODES[@]} -gt 0 ]] || CODES=("${ALL[@]}")
for c in "${CODES[@]}"; do
  [[ -f "$ROOT/languages/$c/language.json" ]] || { echo "no language $c in languages/"; exit 1; }
done
# The previous release's list: the entries of the languages not built now.
PREV="${H4_RELEASE_PREVIOUS:-}"
[[ -z "$PREV" && "$REPO" == */* ]] && PREV="https://github.com/$REPO/releases/latest/download/languages.json"
: > "$OUT/previous.json"
if [[ ${#CODES[@]} -lt ${#ALL[@]} && -n "$PREV" ]]; then
  if [[ -f "$PREV" ]]; then cp "$PREV" "$OUT/previous.json"
  else curl -fsSL -o "$OUT/previous.json" "$PREV" || { echo "no previous release list at $PREV"; exit 1; }; fi
fi
for c in "${CODES[@]}"; do
  echo "== $c"
  cp "$(python3 -I "$ROOT/tools/pack.py" "$c" "$GAME" --from-repo)" "$OUT/$c.h4p"
done
python3 -I - "$ROOT" "$OUT" "${DRY:-https://github.com/$REPO/releases/download/$TAG/}" "$VERSION" "${ALL[@]}" <<'PY'
import hashlib, json, os, sys
root, out, base, version, *codes = sys.argv[1:]
prev_path = os.path.join(out, 'previous.json')
prev = {}
if os.path.getsize(prev_path):
    prev = {l['code']: l for l in json.load(open(prev_path, encoding='utf-8')).get('languages', [])}
os.remove(prev_path)
langs = []
for c in codes:
    m = json.load(open(os.path.join(root, 'languages', c, 'language.json'), encoding='utf-8'))
    pack = os.path.join(out, c + '.h4p')
    entry = {'code': c, 'name': m['name'], 'english': m.get('english_name', m['name']), 'note': m['restart_note']}
    if os.path.exists(pack):  # built now
        entry.update({'version': m.get('version', ''), 'url': base + c + '.h4p',
                      'sha256': hashlib.sha256(open(pack, 'rb').read()).hexdigest(), 'size': os.path.getsize(pack)})
        print(f'{c}: new pack')
    elif c in prev:  # its pack as in the previous release
        entry.update({k: prev[c][k] for k in ('version', 'url', 'sha256', 'size')})
        print(f'{c}: kept ({prev[c]["url"]})')
    else:
        sys.exit(f'{c}: not in the previous release: build it too (release.sh <version> <game dir> {c} ...)')
    langs.append(entry)
json.dump({'version': version, 'languages': langs}, open(os.path.join(out, 'languages.json'), 'w'),
          ensure_ascii=False, indent=1)
PY
if [[ -n "$DRY" ]]; then echo "test release in $OUT (serve it at $DRY)"; exit 0; fi
git -C "$ROOT" archive --format=zip --prefix="ReHoMM4-translations-$TAG/" -o "$OUT/ReHoMM4-translations-$TAG.zip" HEAD
NOTES="$(python3 -I "$ROOT/tools/check.py" 2>&1 || true)"
gh release create "$TAG" -R "$REPO" --target "$(git -C "$ROOT" rev-parse HEAD)" --title "Translations $TAG" \
  --notes "$(printf 'The ReHoMM4 apps take these at their next start (languages.json).\n\n```\n%s\n```' "$NOTES")" \
  "$OUT/languages.json" "$OUT"/*.h4p "$OUT/ReHoMM4-translations-$TAG.zip"
echo "released $TAG: https://github.com/$REPO/releases/tag/$TAG"
