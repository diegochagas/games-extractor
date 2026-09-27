#!/usr/bin/env bash
# Full dump of Saint Seiya Omega Ultimate Cosmo (PSP) from its ISO. The ISO is only read.
#
# usage: extract.sh GAME.iso [--no-render]
# env:
#   OMEGA_OUT   dump folder (default ~/Downloads/Saint Seiya Omega Ultimate Cosmo)
#   BLENDER     Blender 4.2 executable, for the renders of the 3D models (default: `blender` in PATH)
#   RENDER_DEVICE=GPU  renders with the graphics card
#
# Result, all under $OMEGA_OUT:
#   iso/      the files of the disc            cpk/     the two CRI archives unpacked
#   files/    every PAC container unpacked     images/  every GIM picture as PNG
#   text/     all_text.json/.txt, story.json, models.json, render_jobs.json
#   models/   every 3D model as .glb           renders/ front/side/back pictures of the models
#   audio/    music, voices and sound banks as .ogg      video/  the movies as .mp4
set -euo pipefail
ISO="${1:?usage: extract.sh GAME.iso [--no-render]}"
MODE="${2:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PSP="$(dirname "$HERE")"
OUT="${OMEGA_OUT:-$HOME/Downloads/Saint Seiya Omega Ultimate Cosmo}"
BLENDER="${BLENDER:-$(command -v blender || true)}"
for tool in 7z ffmpeg ffprobe python3; do
  command -v "$tool" >/dev/null || { echo "missing tool: $tool"; exit 2; }
done
[ -f "$ISO" ] || { echo "ISO not found: $ISO"; exit 2; }
mkdir -p "$OUT"
echo "== disc -> $OUT/iso";        7z x -y -o"$OUT/iso" "$ISO" >/dev/null
USR="$OUT/iso/PSP_GAME/USRDIR"
echo "== CPK archives";            python3 "$PSP/cpk.py" extract "$USR/install.cpk" "$OUT/cpk/install"
                                   python3 "$PSP/cpk.py" extract "$USR/archive.cpk" "$OUT/cpk/archive"
echo "== PAC containers";          rm -rf "$OUT/files"; python3 "$PSP/pac.py" extract "$OUT/cpk/install" "$OUT/files"
echo "== pictures";                python3 "$PSP/gim.py" convert "$OUT/files" "$OUT/images"
echo "== text";                    python3 "$PSP/btx.py" dump "$OUT/files" "$OUT/text"
                                   python3 "$HERE/story_dump.py" "$OUT/files" "$USR" "$OUT/text"
echo "== movies";                  python3 "$PSP/media.py" video "$USR/movie" "$OUT/video"
echo "== music and voices";        python3 "$PSP/media.py" audio "$USR" "$OUT/audio"
echo "== sound banks";             python3 "$PSP/media.py" banks "$OUT/files" "$OUT/audio/banks"
echo "== 3D models";               python3 "$HERE/models.py" "$OUT/files" "$OUT"
if [ "$MODE" != "--no-render" ]; then
  if [ -z "$BLENDER" ] || [ ! -x "$BLENDER" ]; then
    echo "Blender not found: set BLENDER or use --no-render"; exit 2
  fi
  echo "== renders"
  python3 "$PSP/render/render_all.py" "$OUT/text/render_jobs.json" "$OUT/renders" --blender "$BLENDER" --workers 3
fi
echo "== done: $OUT"
