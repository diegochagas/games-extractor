"""Make 160px thumbnails (JPEG on white/checker-free flatten, PNG kept for alpha) of every converted image -> DST/_thumbs/<png path>.jpg"""
import os, sys, json
from multiprocessing import Pool
from PIL import Image
DST = sys.argv[1]; T = DST + "/_thumbs"
def work(png):
    src = os.path.join(DST, png); out = os.path.join(T, png + ".jpg")
    try:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        im = Image.open(src); im.thumbnail((160, 160))
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA"); bg = Image.new("RGBA", im.size, (40, 40, 40, 255)); bg.alpha_composite(im); im = bg.convert("RGB")
        elif im.mode != "RGB": im = im.convert("RGB")
        im.save(out, "JPEG", quality=80); return None
    except Exception as ex: return (png, str(ex)[:80])
if __name__ == "__main__":
    pngs = [json.loads(l)["png"] for l in open(DST + "/manifest.jsonl") if '"status": "ok"' in l]
    with Pool(11) as p: errs = [e for e in p.imap_unordered(work, pngs, chunksize=64) if e]
    print("thumbs", len(pngs), "errors", errs[:5])
