#!/usr/bin/env bash
# Did the Saint Seiya Rebirth CDN publish a new config bundle (new tables = new story / characters)?
# Prints the server tag and "UPDATED" (exit 0) when config/config.fassets changed on the CDN since the
# last run (its per-bundle manifest hash differs from the one in $REBIRTH_OUT/cdn), "NO CHANGE" (exit 1)
# otherwise. Downloads only the new config bundle, nothing else: run build.sh afterwards for the rest.
# usage: check_update.sh        env: REBIRTH_OUT (default ~/Downloads/Saint Seiya Rebirth)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="${REBIRTH_OUT:-$HOME/Downloads/Saint Seiya Rebirth}"
MANIFEST="$OUT/dump/apk/GameRes.manifest"
[ -f "$MANIFEST" ] || { echo "no dump in $OUT (run build.sh once first)"; exit 2; }
python3 "$HERE/cdn.py" server | grep -E "newest tag|app version"
if python3 "$HERE/cdn.py" sync "$OUT/cdn" "$MANIFEST" --only config/config --workers 1 | grep -q " ok "; then
  echo "UPDATED: a new config/config.fassets is on the CDN"
  exit 0
fi
echo "NO CHANGE"
exit 1
