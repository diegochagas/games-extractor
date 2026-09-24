"""Retry the images the first pass could not decode: patch bad DDS header size (24 -> 124),
decode 128-bit float DDS with numpy, fall back to ImageMagick. Rewrites manifest.jsonl."""
import os, sys, json, io, struct, subprocess
import numpy as np
from PIL import Image
SRC, DST = sys.argv[1], sys.argv[2]
rows = [json.loads(l) for l in open(DST + "/manifest.jsonl")]
fixed = 0
for r in rows:
    if r["status"] != "error": continue
    src, dst = os.path.join(SRC, r["src"]), os.path.join(DST, r["png"])
    d = bytearray(open(src, "rb").read())
    try:
        if d[:4] == b"DDS " and struct.unpack_from("<I", d, 4)[0] != 124:
            struct.pack_into("<I", d, 4, 124); struct.pack_into("<I", d, 76, 32)
            im = Image.open(io.BytesIO(bytes(d))); im.load(); r["note"] = "header dwSize patched 24->124"
        elif d[:4] == b"DDS " and struct.unpack_from("<I", d, 84)[0] == 116:
            h, w = struct.unpack_from("<II", d, 12)
            a = np.frombuffer(bytes(d[128:128 + w * h * 16]), dtype="<f4").reshape(h, w, 4)
            im = Image.fromarray(np.clip(a * 255, 0, 255).astype("uint8"), "RGBA"); r["note"] = "A32B32G32R32F float decoded with numpy"
        else:
            subprocess.run(["convert", src, dst], check=True, capture_output=True); im = Image.open(dst); im.load(); r["note"] = "ImageMagick"
        os.makedirs(os.path.dirname(dst), exist_ok=True); im.save(dst, "PNG", compress_level=4)
        r.update({"w": im.width, "h": im.height, "mode": im.mode, "status": "ok", "png_bytes": os.path.getsize(dst)}); r.pop("error", None); fixed += 1
    except Exception as ex:
        r["error"] = str(ex)[:200]
with open(DST + "/manifest.jsonl", "w") as f:
    for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print("fixed", fixed, "still not ok:", [(r["src"], r.get("error") or r["status"]) for r in rows if r["status"] != "ok"])
