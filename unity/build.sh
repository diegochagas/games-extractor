#!/usr/bin/env bash
# Saint Seiya Rebirth: refresh from the resource CDN and rebuild the gallery and the story book.
# Re-runnable: every step skips what is already done, so a new CDN config bundle (a game update)
# only costs the new bundles, the new table rows, the new characters and the new lines of text.
#
#   build.sh                 full pass: CDN sync, dumps, tables, puppets, gallery, story book
#   build.sh --cdn           only fetch what changed on the CDN (config + role bundles + icons)
#   build.sh --story-only    only the story book (translation of the missing lines + .odt)
#
# env:
#   REBIRTH_OUT   dump folder (default ~/Downloads/Saint Seiya Rebirth): client/, cdn/, dump/, Personagens/, Documentos/
#   REBIRTH_APK   the APK, only needed while dump/apk does not exist yet (default: the .apk under $REBIRTH_OUT/client)
#   REBIRTH_VENV  python with UnityPy (default ~/.cache/rebirth-venv, created with pip if missing)
#   REBIRTH_ART   where art.py files the 2D art (default $REBIRTH_OUT/Imagens; the Nextcloud Pictures folder in the scheduled task)
#   REBIRTH_WORK  work folder with node_modules (docx@8) and the picture cache (default ~/.cache/rebirth-story)
#   DOCX_ODT      comic-skills docx-odt-convert script (default: a comic-skills checkout next to this repo)
#   OLLAMA_MODEL  translation model (default qwen3-instruct-32k)
set -euo pipefail
MODE="${1:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${REBIRTH_OUT:-$HOME/Downloads/Saint Seiya Rebirth}"
VENV="${REBIRTH_VENV:-$HOME/.cache/rebirth-venv}"
W="${REBIRTH_WORK:-$HOME/.cache/rebirth-story}"
DOCX_ODT="${DOCX_ODT:-$(dirname "$(dirname "$HERE")")/comic-skills/docx-odt-convert/scripts/convert.py}"
DUMP="$OUT/dump"
step() { printf '\n== %s\n' "$1"; }

[ -x "$VENV/bin/python" ] || { step "venv with UnityPy -> $VENV"; python3 -m venv "$VENV"; "$VENV/bin/pip" install -q UnityPy; }
PY="$VENV/bin/python"

if [ "$MODE" != "--story-only" ]; then
  if [ ! -f "$DUMP/apk/GameRes.manifest" ]; then
    APK="${REBIRTH_APK:-$(find "$OUT/client" -maxdepth 1 -name '*.apk' 2>/dev/null | head -1 || true)}"
    [ -f "$APK" ] || { echo "APK not found: put it in $OUT/client/ or set REBIRTH_APK (only needed until dump/apk exists)"; exit 2; }
    step "APK bundles -> $DUMP/apk"; python3 "$HERE/abws.py" extract "$APK" "$DUMP/apk"
  fi
  step "CDN: config, characters, icons"
  python3 "$HERE/cdn.py" server
  python3 "$HERE/cdn.py" sync "$OUT/cdn" "$DUMP/apk/GameRes.manifest" --only config/ --workers 4
  python3 "$HERE/cdn.py" sync "$OUT/cdn" "$DUMP/apk/GameRes.manifest" --only role/ --workers 12
  python3 "$HERE/cdn.py" sync "$OUT/cdn" "$DUMP/apk/GameRes.manifest" --only texture/ --workers 12
  python3 "$HERE/cdn.py" sync "$OUT/cdn" "$DUMP/apk/GameRes.manifest" --only otherres/ --workers 12
  step "tables from the CDN config"
  "$PY" "$HERE/dump.py" "$OUT/cdn" "$DUMP/assets" --only config/ --workers 1
  python3 "$HERE/tables.py" "$DUMP/assets/config/config.fassets" "$DUMP/tables"
  step "characters named in RoleConfig that are not on disk yet"
  python3 "$HERE/cdn.py" roles "$OUT/cdn" "$DUMP/tables" "$DUMP/apk"
  [ "$MODE" = "--cdn" ] && { echo "done (CDN only)"; exit 0; }
  step "dump: APK bundles (once) and CDN bundles (changed ones)"
  [ -d "$DUMP/assets/effect" ] || "$PY" "$HERE/dump.py" "$DUMP/apk" "$DUMP/assets" --workers 6
  "$PY" "$HERE/dump.py" "$OUT/cdn" "$DUMP/assets" --workers 4
  step "puppets of the characters without a render yet"
  mkdir -p "$DUMP/puppets"
  for f in "$OUT"/cdn/role/*.fassets.abws; do
    n="$(basename "$f" .fassets.abws)"
    [ -f "$DUMP/puppets/$n.png" ] || "$PY" "$HERE/puppet.py" "$f" "$DUMP/puppets/$n.png" --scale 2 --json "$DUMP/puppets/$n.json" || echo "!! $n"
  done
  step "gallery -> $OUT/Personagens"
  rm -rf "$OUT/Personagens"; python3 "$HERE/roles.py" "$DUMP" "$OUT/Personagens"
  ART="${REBIRTH_ART:-$OUT/Imagens}"
  step "2D art library -> $ART (only new pictures)"
  python3 "$HERE/art.py" "$DUMP" "$ART"
fi

step "story dump"
python3 "$HERE/story/story_dump.py" "$DUMP"
step "translation of the lines not cached yet (local Ollama, $( printf '%s' "${OLLAMA_MODEL:-qwen3-instruct-32k}" ))"
python3 "$HERE/story/translate.py" run "$DUMP" --batch 40
python3 "$HERE/story/translate.py" check "$DUMP" || echo "-- some strings are still untranslated: they appear in Chinese in the book"
[ -f "$DOCX_ODT" ] || { echo "docx-odt-convert not found: set DOCX_ODT"; exit 2; }
mkdir -p "$W"; [ -d "$W/node_modules/docx" ] || (cd "$W" && npm install --silent docx@8)
step "story book"
python3 "$HERE/story/story_prep.py" "$DUMP" "$W"
rm -rf "$W/docx"; mkdir -p "$W/docx"; NODE_PATH="$W/node_modules" node "$HERE/story/build.js" "$W/story_book.json" "$W/docx"
step "odt -> $OUT/Documentos"
python3 "$DOCX_ODT" "$W/docx" --to odt --output "$OUT/Documentos" --overwrite
echo "done: $OUT"
