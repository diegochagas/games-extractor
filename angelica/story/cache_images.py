"""Rewrite every image path in story.json to a resized JPEG in WORK/imgcache (keeps the docx small)."""
import json, os, sys, hashlib
from PIL import Image
WORK = sys.argv[1]; SRC = json.load(open(WORK + "/story.json")); OUT = SRC["out"] + "/"; CACHE = WORK + "/imgcache"; os.makedirs(CACHE, exist_ok=True)
def size_for(p):
    if "/Saints/" in p: return 420
    if "/portrait/" in p or "/head/" in p: return 128
    if "/photobook/" in p or "/Cloths/" in p: return 320
    if "/worldmaps/" in p: return 420
    return 720
def cached(p):
    full = p if p.startswith("/") else OUT + p
    if not os.path.exists(full): return p
    h = hashlib.md5(full.encode()).hexdigest()[:12]; dst = f"{CACHE}/{h}.jpg"
    if not os.path.exists(dst):
        im = Image.open(full); im.thumbnail((size_for(full), size_for(full)))
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA"); bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im); im = bg.convert("RGB")
        elif im.mode != "RGB": im = im.convert("RGB")
        im.save(dst, "JPEG", quality=82)
    return dst
n = 0
def walk(o):
    global n
    if isinstance(o, dict): return {k: walk(v) for k, v in o.items()}
    if isinstance(o, list): return [walk(v) for v in o]
    if isinstance(o, str) and o.lower().endswith((".png", ".jpg", ".jpeg")) and ("/" in o):
        r = cached(o); n += (r != o); return r
    return o
D = walk(SRC); D["out"] = ""; json.dump(D, open(WORK + "/story_cached.json", "w"), ensure_ascii=False)
tot = sum(os.path.getsize(CACHE + "/" + f) for f in os.listdir(CACHE)); print("cached", n, "images,", round(tot / 1e6, 1), "MB")
