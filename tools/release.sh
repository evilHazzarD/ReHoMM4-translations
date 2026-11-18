#!/bin/bash
# release.sh <version> <game dir> [owner/name]: a release of the translations, the only way they
# reach players. For every language in languages/ it builds the pack from languages/<code>/text
# (tools/pack.py --from-repo, from your own GOG copy) and the Linux/Switch button pictures
# (tools/render_ui.swift), then makes the GitHub release v<version> with:
#
#   languages.json      the list the app reads (releases/latest/download/languages.json):
#                       {"version", "languages": [{"code", "name", "english", "note", "version",
#                        "url", "sha256", "size", "button", "note_picture"}]}
#   <code>.h4p          each language's pack
#   <code>.button.argb, <code>.note.argb   its pictures for the Linux and Switch apps
#   ReHoMM4-translations-v<version>.zip    the source (languages/ and tools/, no game data)
#
# The apps check languages.json at every start and take a language's new pack (its SHA-256
# changed) at the next start: commits alone change nothing for players. Needs a clean, pushed
# tree, `gh` signed in (gh auth login), macOS (the fonts and pictures) and ffmpeg (voice-over).
# H4_RELEASE_BASE=<url>/ makes the files in build/release-<version> for a test server instead
# (URLs under that address, uncommitted changes allowed, nothing uploaded).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:?usage: release.sh <version> <game dir> [owner/name]}"; GAME="${2:?game dir}"
VERSION="${VERSION#v}"; TAG="v$VERSION"
REPO="${3:-$( (git -C "$ROOT" remote get-url origin 2>/dev/null || true) | sed -E 's#(\.git)?$##; s#^.*github\.com[:/]##')}"
DRY="${H4_RELEASE_BASE:-}"
if [[ -z "$DRY" ]]; then
  [[ "$REPO" == */* ]] || { echo "no GitHub remote: pass owner/name"; exit 1; }
  [[ -z "$(git -C "$ROOT" status --porcelain)" ]] || { echo "uncommitted changes: commit and push first"; exit 1; }
fi
python3 -I "$ROOT/tools/check.py"
OUT="$ROOT/build/release-$VERSION"; rm -rf "$OUT"; mkdir -p "$OUT"
export H4_LOC_WORK="$ROOT/build/release-work"  # not build/<code>: your unexported work stays
CODES=(); for j in "$ROOT"/languages/*/language.json; do CODES+=("$(basename "$(dirname "$j")")"); done
: > "$OUT/languages.tsv"
for c in "${CODES[@]}"; do
  echo "== $c"
  cp "$(python3 -I "$ROOT/tools/pack.py" "$c" "$GAME" --from-repo)" "$OUT/$c.h4p"
  python3 -I -c 'import json,sys; m=json.load(open(sys.argv[1], encoding="utf-8")); print(m["code"], m["name"], m["restart_note"], sep="\t")' \
    "$ROOT/languages/$c/language.json" >> "$OUT/languages.tsv"
done
swift "$ROOT/tools/render_ui.swift" "$OUT/ui" "$OUT/languages.tsv"
for c in "${CODES[@]}"; do mv "$OUT/ui/lang_$c.argb" "$OUT/$c.button.argb"; mv "$OUT/ui/note_$c.argb" "$OUT/$c.note.argb"; done
python3 -I - "$ROOT" "$OUT" "${DRY:-https://github.com/$REPO/releases/download/$TAG/}" "$VERSION" "${CODES[@]}" <<'PY'
import hashlib, json, os, sys
root, out, base, version, *codes = sys.argv[1:]
langs = []
for c in codes:
    m = json.load(open(os.path.join(root, 'languages', c, 'language.json'), encoding='utf-8'))
    pack = os.path.join(out, c + '.h4p')
    langs.append({'code': c, 'name': m['name'], 'english': m.get('english_name', m['name']),
                  'note': m['restart_note'], 'version': m.get('version', ''),
                  'url': base + c + '.h4p', 'sha256': hashlib.sha256(open(pack, 'rb').read()).hexdigest(),
                  'size': os.path.getsize(pack),
                  'button': base + c + '.button.argb', 'note_picture': base + c + '.note.argb'})
json.dump({'version': version, 'languages': langs}, open(os.path.join(out, 'languages.json'), 'w'),
          ensure_ascii=False, indent=1)
PY
if [[ -n "$DRY" ]]; then echo "test release in $OUT (serve it at $DRY)"; exit 0; fi
git -C "$ROOT" archive --format=zip --prefix="ReHoMM4-translations-$TAG/" -o "$OUT/ReHoMM4-translations-$TAG.zip" HEAD
NOTES="$(python3 -I "$ROOT/tools/check.py" 2>&1 || true)"
gh release create "$TAG" -R "$REPO" --target "$(git -C "$ROOT" rev-parse HEAD)" --title "Translations $TAG" \
  --notes "$(printf 'The ReHoMM4 apps take these at their next start (languages.json).\n\n```\n%s\n```' "$NOTES")" \
  "$OUT/languages.json" "$OUT"/*.h4p "$OUT"/*.argb "$OUT/ReHoMM4-translations-$TAG.zip"
echo "released $TAG: https://github.com/$REPO/releases/tag/$TAG"
