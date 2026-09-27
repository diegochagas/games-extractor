#!/usr/bin/env bash
# Gallery and story book of Saint Seiya Omega Ultimate Cosmo from the dump made by extract.sh.
# Everything is written inside the dump folder in ~/Downloads, to be checked and moved by hand:
#
#   $OMEGA_OUT/Imagens      pictures only, one folder per subject
#   $OMEGA_OUT/Vídeos       the movies
#   $OMEGA_OUT/Música       Músicas/, Vozes/ and Efeitos/
#   $OMEGA_OUT/Modelos 3D   the .glb models
#   $OMEGA_OUT/Documentos   the four volumes of the story book as LibreOffice .odt
#
# usage: build.sh [--story-only]
# env:
#   OMEGA_OUT    dump folder (default ~/Downloads/Saint Seiya Omega Ultimate Cosmo)
#   OMEGA_WORK   work folder with node_modules (docx@8) and the image cache (default ~/.cache/omega-story)
#   DOCX_ODT     the comic-skills docx-odt-convert script (default: a comic-skills checkout next to this repo)
#
# The pt-BR text comes from $OMEGA_OUT/text/translation (translate.py export, the translation
# itself following docs/TRANSLATE_INSTRUCTIONS.md, translate.py merge).
set -euo pipefail
MODE="${1:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${OMEGA_OUT:-$HOME/Downloads/Saint Seiya Omega Ultimate Cosmo}"
W="${OMEGA_WORK:-$HOME/.cache/omega-story}"
DOCX_ODT="${DOCX_ODT:-$(dirname "$(dirname "$(dirname "$HERE")")")/comic-skills/docx-odt-convert/scripts/convert.py}"
[ -f "$OUT/text/story.json" ] || { echo "dump not found in $OUT: run extract.sh first"; exit 2; }
[ -f "$DOCX_ODT" ] || { echo "docx-odt-convert not found: set DOCX_ODT"; exit 2; }
mkdir -p "$W"
[ -d "$W/node_modules/docx" ] || (cd "$W" && npm install --silent docx@8)
python3 "$HERE/translate.py" check "$OUT" >/dev/null || { python3 "$HERE/translate.py" check "$OUT" || true; echo "translation incomplete"; exit 2; }
python3 "$HERE/translate.py" merge "$OUT"
if [ "$MODE" != "--story-only" ]; then
  echo "== gallery"; python3 "$HERE/organize.py" "$OUT" "$OUT"
fi
echo "== story_prep"; python3 "$HERE/story/story_prep.py" "$OUT" "$W" | grep -E "STATS|no translation" || true
echo "== build"; rm -rf "$W/docx"; mkdir -p "$W/docx"; NODE_PATH="$W/node_modules" node "$HERE/story/build.js" "$W/story_book.json" "$W/docx"
echo "== odt -> $OUT/Documentos"; python3 "$DOCX_ODT" "$W/docx" --to odt --output "$OUT/Documentos" --overwrite
echo "== done: $OUT"
