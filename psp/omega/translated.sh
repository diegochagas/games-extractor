#!/usr/bin/env bash
# Portuguese disc image of Saint Seiya Omega Ultimate Cosmo. The original image is only read.
#
# usage: translated.sh ORIGINAL.iso [OUT.iso]
# env:
#   OMEGA_OUT   dump folder made by extract.sh (default ~/Downloads/Saint Seiya Omega Ultimate Cosmo)
#
# Needs in the dump: text/translation/pt-BR.json (translate.py merge) and, for the movies,
# text/subtitles/NAME.pt-BR.srt (transcribe.py + the translation + subtitles.py srt).
# Result: $OMEGA_OUT/patch/ (movies, report.json and the image).
set -euo pipefail
ISO="${1:?usage: translated.sh ORIGINAL.iso [OUT.iso]}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${OMEGA_OUT:-$HOME/Downloads/Saint Seiya Omega Ultimate Cosmo}"
NEW="${2:-$OUT/patch/Saint Seiya Omega - Ultimate Cosmo (Japan) [pt-BR].iso}"
[ -f "$ISO" ] || { echo "image not found: $ISO"; exit 2; }
[ -f "$OUT/text/translation/pt-BR.json" ] || { echo "translation not found in $OUT/text/translation"; exit 2; }
python3 "$HERE/translate.py" check "$OUT" >/dev/null || { echo "translation incomplete (translate.py check)"; exit 2; }
mkdir -p "$OUT/patch/movie"
for srt in "$OUT"/text/subtitles/*.pt-BR.srt; do
  [ -s "$srt" ] || continue
  name="$(basename "$srt" .pt-BR.srt)"
  src="$OUT/iso/PSP_GAME/USRDIR/movie/$name.pmf"
  if [ -f "$src" ] && [ ! -f "$OUT/patch/movie/$name.pmf" ]; then
    echo "== movie $name"; python3 "$HERE/movie.py" "$src" "$srt" "$OUT/patch/movie/$name.pmf"
  fi
done
echo "== image"
python3 "$HERE/patch.py" "$OUT" "$ISO" "$NEW" --movies "$OUT/patch/movie" --report "$OUT/patch/report.json"
echo "== done: $NEW"
