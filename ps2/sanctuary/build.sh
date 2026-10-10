#!/usr/bin/env bash
# Gallery and story book of Saint Seiya: The Sanctuary from the dump made by extract.sh.
# Everything is written inside the dump folder in ~/Downloads, to be checked and moved by hand:
#
#   $SANCTUARY_OUT/Imagens      pictures only, one folder per subject
#   $SANCTUARY_OUT/Vídeos       the three movies
#   $SANCTUARY_OUT/Música       Músicas/ and Vozes/
#   $SANCTUARY_OUT/Documentos   the volumes of the story book as LibreOffice .odt
#
# usage: build.sh [--story-only]
# env:
#   SANCTUARY_OUT    dump folder (default ~/Downloads/Saint Seiya - The Sanctuary (PS2))
#   SANCTUARY_WORK   work folder with node_modules (docx@8) and the image cache (default ~/.cache/sanctuary-story)
#   SANCTUARY_VIDEOS folder with the two recorded cutscene videos (IF05 and IF09), whose frames
#                    illustrate those chapters (default: the Nextcloud Videos folder of the game)
#   DOCX_ODT         the comic-skills docx-odt-convert script (default: a comic-skills checkout next to this repo)
set -euo pipefail
MODE="${1:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${SANCTUARY_OUT:-$HOME/Downloads/Saint Seiya - The Sanctuary (PS2)}"
W="${SANCTUARY_WORK:-$HOME/.cache/sanctuary-story}"
DOCX_ODT="${DOCX_ODT:-$(dirname "$(dirname "$(dirname "$HERE")")")/comic-skills/docx-odt-convert/scripts/convert.py}"
[ -f "$OUT/text/scenes.json" ] || { echo "dump not found in $OUT: run extract.sh first"; exit 2; }
[ -f "$DOCX_ODT" ] || { echo "docx-odt-convert not found: set DOCX_ODT"; exit 2; }
mkdir -p "$W"
[ -d "$W/node_modules/docx" ] || (cd "$W" && npm install --silent docx@8)
if [ "$MODE" != "--story-only" ]; then
  echo "== gallery"; python3 "$HERE/organize.py" "$OUT" "$OUT"
fi
echo "== transcript"; python3 "$HERE/story/transcript.py" "$OUT"
echo "== story_prep"; python3 "$HERE/story/story_prep.py" "$OUT" "$W" ${SANCTUARY_VIDEOS:+--videos "$SANCTUARY_VIDEOS"}
echo "== build"; rm -rf "$W/docx"; mkdir -p "$W/docx"; NODE_PATH="$W/node_modules" node "$HERE/story/build.js" "$W/story_book.json" "$W/docx"
echo "== odt -> $OUT/Documentos"; python3 "$DOCX_ODT" "$W/docx" --to odt --output "$OUT/Documentos" --overwrite
echo "== done: $OUT"
