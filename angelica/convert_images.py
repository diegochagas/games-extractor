#!/usr/bin/env python3
"""Convert every dds/tga/bmp/jpg under SRC to PNG under DST (same relative path, .png suffix appended
when the source is not already .png). PNG sources are copied. Writes DST/manifest.jsonl.
Usage: convert_images.py SRC DST [workers]"""
import os, sys, json, struct, shutil, time
from multiprocessing import Pool
from PIL import Image
SRC, DST = sys.argv[1].rstrip("/"), sys.argv[2].rstrip("/")
W = int(sys.argv[3]) if len(sys.argv) > 3 else 10
IMG = {"dds", "tga", "bmp", "jpg", "jpeg", "png"}

def info_dds(p):
    h = open(p, "rb").read(128)
    if h[:4] != b"DDS ": return {"format": "dds?"}
    hgt, wid, _, depth, mips = struct.unpack_from("<IIIII", h, 12)
    fl = struct.unpack_from("<I", h, 80)[0]
    fmt = h[84:88].decode("latin1").strip("\0") if fl & 4 else "rgb%d%s" % (struct.unpack_from("<I", h, 88)[0], "a" if fl & 1 else "")
    caps2 = struct.unpack_from("<I", h, 112)[0]
    return {"format": "DDS/" + fmt, "mipmaps": mips, "cubemap": bool(caps2 & 0x200), "volume": bool(caps2 & 0x200000)}

def work(rel):
    src = os.path.join(SRC, rel); ext = rel.lower().rsplit(".", 1)[-1]
    out_rel = rel if ext == "png" else rel + ".png"
    dst = os.path.join(DST, out_rel)
    row = {"src": rel, "png": out_rel, "src_bytes": os.path.getsize(src)}
    try:
        if row["src_bytes"] == 0: row["status"] = "empty"; return row
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if ext == "dds": row.update(info_dds(src))
        else: row["format"] = ext.upper()
        im = Image.open(src); im.load()
        row.update({"w": im.width, "h": im.height, "mode": im.mode})
        if ext == "png":
            shutil.copyfile(src, dst)
        else:
            if im.mode not in ("RGB", "RGBA", "L", "LA", "P", "I;16", "I"): im = im.convert("RGBA")
            im.save(dst, "PNG", compress_level=4)
        row["status"] = "ok"; row["png_bytes"] = os.path.getsize(dst)
    except Exception as ex:
        row["status"] = "error"; row["error"] = str(ex)[:200]
    return row

if __name__ == "__main__":
    rels = []
    for dp, _, fs in os.walk(SRC):
        for f in fs:
            if f.lower().rsplit(".", 1)[-1] in IMG: rels.append(os.path.relpath(os.path.join(dp, f), SRC))
    rels.sort(); os.makedirs(DST, exist_ok=True)
    t0 = time.time(); n = 0; bad = 0
    with open(os.path.join(DST, "manifest.jsonl"), "w") as mf, Pool(W) as pool:
        for row in pool.imap_unordered(work, rels, chunksize=32):
            mf.write(json.dumps(row, ensure_ascii=False) + "\n"); n += 1
            if row["status"] != "ok": bad += 1
            if n % 5000 == 0: print(f"{n}/{len(rels)} ({bad} not ok) {time.time()-t0:.0f}s", flush=True)
    print(f"done {n} files, {bad} not ok, {time.time()-t0:.0f}s")
