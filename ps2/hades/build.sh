#!/usr/bin/env bash
# Gallery and story book of Saint Seiya: The Hades from the dump made by extract.sh. The story text
# of the disc is English (with Japanese, French, Italian, Spanish): the book is in Portuguese, translated
# by the local Ollama model (story/translate.py, cached per line) and reviewed by hand (story/fixes.json).
#
# usage: build.sh [--story-only]
# env:
#   HADES_OUT    dump folder (default ~/Downloads/Saint Seiya - The Hades (PS2))
#   HADES_WORK   work folder with node_modules (docx@8) and the image cache (default ~/.cache/hades-story)
#   DOCX_ODT     the comic-skills docx-odt-convert script (default: a comic-skills checkout next to this repo)
#   OLLAMA_MODEL translation model (default qwen3-instruct-32k)
set -euo pipefail
MODE="${1:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${HADES_OUT:-$HOME/Downloads/Saint Seiya - The Hades (PS2)}"
W="${HADES_WORK:-$HOME/.cache/hades-story}"
DOCX_ODT="${DOCX_ODT:-$(dirname "$(dirname "$(dirname "$HERE")")")/comic-skills/docx-odt-convert/scripts/convert.py}"
[ -f "$OUT/text/scenes.json" ] || { echo "dump not found in $OUT: run extract.sh first"; exit 2; }
[ -f "$DOCX_ODT" ] || { echo "docx-odt-convert not found: set DOCX_ODT"; exit 2; }
mkdir -p "$W"
[ -d "$W/node_modules/docx" ] || (cd "$W" && npm install --silent docx@8)
if [ "$MODE" != "--story-only" ]; then
  echo "== gallery"; python3 "$HERE/organize.py" "$OUT" "$OUT"
fi
echo "== translation of the lines not cached yet"; python3 "$HERE/story/translate.py" run "$OUT" --batch 20
python3 "$HERE/story/translate.py" check "$OUT" || echo "-- some lines are still untranslated: they appear in English in the book"
echo "== story"; python3 "$HERE/story/story.py" "$OUT"
echo "== story_prep"; python3 "$HERE/story/story_prep.py" "$OUT" "$W"
echo "== build"; rm -rf "$W/docx"; mkdir -p "$W/docx"; NODE_PATH="$W/node_modules" node "$HERE/story/build.js" "$W/story_book.json" "$W/docx"
echo "== odt -> $OUT/Documentos"; python3 "$DOCX_ODT" "$W/docx" --to odt --output "$OUT/Documentos" --overwrite
echo "== done: $OUT"
