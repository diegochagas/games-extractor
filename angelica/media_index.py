#!/usr/bin/env python3
"""Index every audio/video file (duration via ffprobe) -> OUT/media_index.csv + media_index.json"""
import os, sys, csv, json, subprocess
from concurrent.futures import ThreadPoolExecutor
OUT = sys.argv[1].rstrip("/"); PKG = OUT + "/packages"
groups = [("music", OUT + "/music"), ("voice", OUT + "/voice"), ("video", OUT + "/videos/mp4"), ("sfx", PKG + "/sfx"), ("ui-sound", OUT + "/audio_projects")]
files = []
for g, root in groups:
    for dp, _, fs in os.walk(root):
        for f in fs:
            if f.lower().rsplit(".", 1)[-1] in ("ogg", "mp3", "wav", "mp4"):
                files.append((g, os.path.join(dp, f)))
def probe(item):
    g, p = item
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,sample_rate,channels,width,height", "-of", "json", p], capture_output=True, text=True, timeout=60)
        j = json.loads(r.stdout or "{}"); st = (j.get("streams") or [{}])[0]
        return {"group": g, "path": os.path.relpath(p, OUT), "bytes": os.path.getsize(p), "seconds": round(float(j.get("format", {}).get("duration", 0) or 0), 2),
                "codec": st.get("codec_name"), "sample_rate": st.get("sample_rate"), "channels": st.get("channels"), "width": st.get("width"), "height": st.get("height")}
    except Exception as ex:
        return {"group": g, "path": os.path.relpath(p, OUT), "bytes": os.path.getsize(p), "error": str(ex)[:100]}
with ThreadPoolExecutor(12) as ex: rows = list(ex.map(probe, files))
rows.sort(key=lambda r: (r["group"], r["path"]))
with open(OUT + "/media_index.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["group", "path", "bytes", "seconds", "codec", "sample_rate", "channels", "width", "height", "error"]); w.writeheader(); w.writerows(rows)
json.dump(rows, open(OUT + "/media_index.json", "w"), ensure_ascii=False)
from collections import Counter
c = Counter(r["group"] for r in rows); s = Counter()
for r in rows: s[r["group"]] += r.get("seconds", 0)
print({g: (c[g], round(s[g] / 60, 1)) for g in c})
