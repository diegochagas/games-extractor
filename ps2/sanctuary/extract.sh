#!/usr/bin/env bash
# Full dump of Saint Seiya: The Sanctuary (PS2, Brazilian disc) from its ISO. The ISO is only read.
#
# usage: extract.sh GAME.iso [--no-transcribe] [--no-render]
# env:
#   SANCTUARY_OUT  dump folder (default ~/Downloads/Saint Seiya - The Sanctuary (PS2))
#   BLENDER        Blender 4.2 executable for the renders of the 3D models (default: `blender` in PATH)
#   RENDER_DEVICE=GPU  renders with the graphics card
#   WHISPER_PY     python of a virtual environment with faster-whisper, for the transcription of the
#                  Portuguese voices (default /mnt/data/venvs/whisper/bin/python; skipped when absent)
#
# Result, all under $SANCTUARY_OUT:
#   iso/      the files of the disc            afs/     DATA/AFSDATA.AFS unpacked (+ afs_index.json)
#   files/    every CMPS file unpacked and every FJF container opened, recursively
#   images/   every TIM2 picture as PNG         text/    messages.json/.txt, scenes.json, voices/*.pt.json
#   audio/    every ADX as .ogg, banks/ the sound banks as .wav     video/   the three Sofdec movies as .mp4
#   models/   the character and stage models as .glb   renders/ pictures of them (characters: front/side/back/
#             three-quarter; stages: aerial/top/front, with and without the far scenery)
set -euo pipefail
ISO="${1:?usage: extract.sh GAME.iso [--no-transcribe] [--no-render]}"
shift
MODES="$*"
HERE="$(cd "$(dirname "$0")" && pwd)"
PS2="$(dirname "$HERE")"
PSP="$(dirname "$PS2")/psp"
OUT="${SANCTUARY_OUT:-$HOME/Downloads/Saint Seiya - The Sanctuary (PS2)}"
WHISPER_PY="${WHISPER_PY:-/mnt/data/venvs/whisper/bin/python}"
BLENDER="${BLENDER:-$(command -v blender || true)}"
for tool in 7z ffmpeg ffprobe python3; do
  command -v "$tool" >/dev/null || { echo "missing tool: $tool"; exit 2; }
done
[ -f "$ISO" ] || { echo "ISO not found: $ISO"; exit 2; }
mkdir -p "$OUT"
echo "== disc -> $OUT/iso";      7z x -y -o"$OUT/iso" "$ISO" >/dev/null
echo "== AFS archive";           python3 "$PS2/afs.py" extract "$OUT/iso/DATA/AFSDATA.AFS" "$OUT/afs"
echo "== containers";            rm -rf "$OUT/files"; python3 "$PS2/fjf.py" extract "$OUT/afs" "$OUT/files"
echo "== pictures";              rm -rf "$OUT/images"; python3 "$PS2/tim2.py" convert "$OUT/files" "$OUT/images"
echo "== text";                  python3 "$PS2/msg.py" dump "$OUT/afs" "$OUT/text"
                                 python3 "$HERE/scenes.py" dump "$OUT/afs" "$OUT/text"
echo "== movies";                python3 "$PS2/media.py" video "$OUT/iso/DATA" "$OUT/video"
echo "== music and voices";      python3 "$PS2/media.py" audio "$OUT/afs" "$OUT/audio" --workers 6
echo "== sound banks";           python3 "$PS2/sebank.py" extract "$OUT/afs" "$OUT/audio/banks"
echo "== 3D models";             python3 "$HERE/models.py" "$OUT/afs" "$OUT"
echo "== stages";                python3 "$HERE/stages.py" "$OUT/afs" "$OUT"
case " $MODES " in *" --no-render "*) ;; *)
  if [ -z "$BLENDER" ] || [ ! -x "$BLENDER" ]; then
    echo "-- Blender not found: set BLENDER or use --no-render"
  else
    echo "== renders"
    python3 "$PSP/render/render_all.py" "$OUT/text/render_jobs.json" "$OUT/renders" --blender "$BLENDER" --workers 2
    python3 "$PSP/render/render_all.py" "$OUT/text/stage_render_jobs.json" "$OUT/renders" --blender "$BLENDER" --workers 2
  fi;;
esac
case " $MODES " in *" --no-transcribe "*) ;; *)
  if [ -x "$WHISPER_PY" ]; then
    echo "== transcription of the story voices (faster-whisper, pt)"
    mapfile -t VOICES < <(python3 -c "import json,sys; s=json.load(open(sys.argv[1])); print('\\n'.join(sorted({l['voice'] for x in s for l in x['lines'] if l['voice']})))" "$OUT/text/scenes.json")
    TODO=()
    for v in "${VOICES[@]}"; do
      f="$(find "$OUT/afs" -maxdepth 1 -iname "$v" | head -1)"; n="$(basename "$f" .adx)"
      [ -z "$f" ] || [ -f "$OUT/text/voices/$n.pt.json" ] || TODO+=("$f")
    done
    [ "${#TODO[@]}" -eq 0 ] || "$WHISPER_PY" "$PSP/transcribe.py" "$OUT/text/voices" "${TODO[@]}" --language pt
  else
    echo "-- faster-whisper not found ($WHISPER_PY): voices not transcribed"
  fi;;
esac
echo "== done: $OUT"
