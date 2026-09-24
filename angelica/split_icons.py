"""Split the UI icon atlases (surfaces/iconset/iconlist_*.dds + .txt) into single icons.
.txt (GBK): cell width, cell height, rows, columns, then one icon name per cell (row-major).
-> OUT/images/icons/<atlas>/<name>.png and OUT/images/icons/index.csv"""
import os, sys, csv
from PIL import Image
OUT = sys.argv[1]; SRC = OUT + "/packages/surfaces/iconset"; DST = OUT + "/images/icons"; os.makedirs(DST, exist_ok=True)
rows = []
for f in sorted(os.listdir(SRC)):
    if not f.endswith(".txt"): continue
    atlas = f[:-4]; b = open(os.path.join(SRC, f), "rb").read()
    t = b[2:].decode("utf-16le") if b[:2] == b"\xff\xfe" else b.decode("gbk", "replace")
    lines = [l for l in t.splitlines()]
    cw, ch, nr, nc = (int(x) for x in lines[:4]); names = lines[4:]
    im = Image.open(os.path.join(SRC, atlas + ".dds")).convert("RGBA")
    os.makedirs(os.path.join(DST, atlas), exist_ok=True); n = 0
    for i, name in enumerate(names):
        if not name.strip(): continue
        r, c = divmod(i, nc); x, y = c * cw, r * ch
        if x + cw > im.width or y + ch > im.height: continue
        icon = im.crop((x, y, x + cw, y + ch)); stem = os.path.splitext(name)[0].replace("/", "_")
        p = os.path.join(DST, atlas, stem + ".png"); icon.save(p); n += 1
        rows.append({"atlas": atlas, "index": i, "name": name, "png": f"icons/{atlas}/{stem}.png", "w": cw, "h": ch})
    print(f"{atlas}: {n} icons ({cw}x{ch}, {nr}x{nc} grid, atlas {im.width}x{im.height})")
with open(DST + "/index.csv", "w", newline="") as fo:
    w = csv.DictWriter(fo, fieldnames=["atlas", "index", "name", "png", "w", "h"]); w.writeheader(); w.writerows(rows)
print("total icons", len(rows))
