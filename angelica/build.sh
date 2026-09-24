#!/usr/bin/env bash
# Build the Saint Seiya Online gallery and story book from a dump folder.
# Everything is written under ONE output folder in ~/Downloads, for Diego to check and then move by hand:
#
#   $SSO_OUT/Imagens      gallery (pictures only), organised like volume 04
#   $SSO_OUT/Vídeos       the client videos (their stills stay in Imagens/Quadros dos vídeos)
#   $SSO_OUT/Música       Músicas/ and Vozes/
#   $SSO_OUT/Documentos   the 13 story volumes as LibreOffice .odt
#
# usage: build.sh DUMP_DIR [--story-only]
#   --story-only   skip the gallery; read it from $SSO_GALLERY (default $SSO_OUT/Imagens)
# env:
#   SSO_OUT       output root (default ~/Downloads/Saint Seiya Online)
#   SSO_LIBRARY   Diego's "Cloth Schemes" library, for the official art kept there (optional)
#   SSO_WORK      work folder with node_modules (docx@8) and the image cache (default ~/.cache/sso-story)
#   DOCX_ODT      the comic-skills docx-odt-convert script (default: a comic-skills checkout next to this repo)
set -euo pipefail
DUMP="$(cd "${1:?usage: build.sh DUMP_DIR [--story-only]}" && pwd)"
MODE="${2:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT_ROOT="${SSO_OUT:-$HOME/Downloads/Saint Seiya Online}"
W="${SSO_WORK:-$HOME/.cache/sso-story}"
DOCX_ODT="${DOCX_ODT:-$(dirname "$(dirname "$HERE")")/comic-skills/docx-odt-convert/scripts/convert.py}"
GAL="${SSO_GALLERY:-$OUT_ROOT/Imagens}"
[ -f "$DOCX_ODT" ] || { echo "docx-odt-convert not found: set DOCX_ODT"; exit 2; }
mkdir -p "$W"
[ -d "$W/node_modules/docx" ] || (cd "$W" && npm install --silent docx@8)

if [ "$MODE" != "--story-only" ]; then
  echo "== organize -> $OUT_ROOT"
  LIB=()
  if [ -n "${SSO_LIBRARY:-}" ]; then LIB=(--library "$SSO_LIBRARY" --concept-dir "$SSO_LIBRARY/others"); fi
  (cd "$DUMP" && python3 "$HERE/render/organize.py" . "$GAL" "${LIB[@]}" --sites-dir "$DUMP/web/sites" \
      --videos-dir "$OUT_ROOT/Vídeos" --music-dir "$OUT_ROOT/Música" | head -3)
fi
[ -d "$GAL" ] || { echo "gallery not found: $GAL (run without --story-only, or set SSO_GALLERY)"; exit 2; }

cd "$HERE/story"
echo "== story_prep (gallery: $GAL)"; SSO_GALLERY="$GAL" python3 story_prep.py "$W" "$DUMP" | grep -E "STATS|gallery" || true
echo "== cache_images"; python3 cache_images.py "$W"
echo "== build"; rm -rf "$W/docx"; mkdir -p "$W/docx"; NODE_PATH="$W/node_modules" node build.js "$W/story_cached.json" "$W/docx"
echo "== odt -> $OUT_ROOT/Documentos"; python3 "$DOCX_ODT" "$W/docx" --to odt --output "$OUT_ROOT/Documentos" --overwrite
echo "== done: $OUT_ROOT"
