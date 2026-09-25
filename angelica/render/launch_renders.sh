#!/usr/bin/env bash
# Render every job of text/render_jobs.json on the GPU with the settings that worked on an RTX 3050:
# Cycles + OptiX, 64 samples, denoising off (OIDN reloads its kernels per frame in -b mode), 2 Blender workers.
#   launch_renders.sh DUMP_DIR BLENDER_EXECUTABLE [extra render_all.py flags, e.g. --force]
set -euo pipefail
DUMP="${1:?usage: launch_renders.sh DUMP_DIR BLENDER_EXECUTABLE}"; BLENDER="${2:?blender executable}"; shift 2
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$DUMP"
export RENDER_DEVICE=GPU RENDER_THREADS=6 RENDER_BACKEND=OPTIX
exec python3 "$HERE/render_all.py" text/render_jobs.json renders --blender "$BLENDER" --workers 2 --size 1000 --samples 64 "$@"
