#!/usr/bin/env bash
# Full dump of Saint Seiya: The Hades (PS2, European disc) from its ISO. The ISO is only read.
#
# usage: extract.sh GAME.iso [--no-render]
# env:
#   HADES_OUT      dump folder (default ~/Downloads/Saint Seiya - The Hades (PS2))
#   BLENDER        Blender 4.2 executable for the renders of the 3D models (default: `blender` in PATH)
#   RENDER_DEVICE=GPU  renders with the graphics card
#
# Result, all under $HADES_OUT: iso/, afs/, files/, images/, text/ (messages, scenes, models),
# audio/ (+ banks/), video/, models/, renders/. GX_MAIN.SFD on the disc is 1.8 GB of zeros (padding).
set -euo pipefail
ISO="${1:?usage: extract.sh GAME.iso [--no-render]}"
MODE="${2:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PS2="$(dirname "$HERE")"
PSP="$(dirname "$PS2")/psp"
OUT="${HADES_OUT:-$HOME/Downloads/Saint Seiya - The Hades (PS2)}"
BLENDER="${BLENDER:-$(command -v blender || true)}"
for tool in 7z ffmpeg ffprobe python3; do
  command -v "$tool" >/dev/null || { echo "missing tool: $tool"; exit 2; }
done
[ -f "$ISO" ] || { echo "ISO not found: $ISO"; exit 2; }
mkdir -p "$OUT"
echo "== disc -> $OUT/iso";      7z x -y -o"$OUT/iso" "$ISO" -x'!GX_MAIN.SFD' >/dev/null
echo "== AFS archive";           python3 "$PS2/afs.py" extract "$OUT/iso/DATA/AFSDATA.AFS" "$OUT/afs"
echo "== containers";            rm -rf "$OUT/files"; python3 "$PS2/fjf.py" extract "$OUT/afs" "$OUT/files"
echo "== pictures";              rm -rf "$OUT/images"; python3 "$PS2/tim2.py" convert "$OUT/files" "$OUT/images"
echo "== text";                  python3 "$PS2/msg.py" dump "$OUT/afs" "$OUT/text" --slot0 jp
                                 python3 "$HERE/scenes.py" dump "$OUT/afs" "$OUT/text"
echo "== movies";                python3 "$PS2/media.py" video "$OUT/iso/DATA" "$OUT/video"
echo "== music and voices";      python3 "$PS2/media.py" audio "$OUT/afs" "$OUT/audio" --workers 6
echo "== sound banks";           python3 "$PS2/sebank.py" extract "$OUT/afs" "$OUT/audio/banks"
echo "== 3D models";             python3 "$PS2/sanctuary/models.py" "$OUT/afs" "$OUT" --names hades
echo "== stages";                python3 "$PS2/sanctuary/stages.py" "$OUT/afs" "$OUT" --names hades
if [ "$MODE" != "--no-render" ]; then
  if [ -z "$BLENDER" ] || [ ! -x "$BLENDER" ]; then
    echo "-- Blender not found: set BLENDER or use --no-render"
  else
    echo "== renders"
    python3 "$PSP/render/render_all.py" "$OUT/text/render_jobs.json" "$OUT/renders" --blender "$BLENDER" --workers 2
    python3 "$PSP/render/render_all.py" "$OUT/text/stage_render_jobs.json" "$OUT/renders" --blender "$BLENDER" --workers 2
  fi
fi
echo "== done: $OUT"
