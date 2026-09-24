"""Data + gallery images for the Image index document -> scratch/docxbuild/data.json, galleries/*.jpg"""
import os, sys, json, csv, collections
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__)); from labels import label, MAP_CODES
OUT, WORK = sys.argv[1], sys.argv[2]; IM = OUT + "/images"; G = WORK + "/galleries"; os.makedirs(G, exist_ok=True)
for r in csv.DictReader(open(OUT + "/text/maps.csv", encoding="utf-8")):
    if r["map_code"] and r["map_code"] not in MAP_CODES: MAP_CODES[r["map_code"]] = r["name_en"] or r["name_zh"]
rows = [json.loads(l) for l in open(IM + "/manifest.jsonl") if '"status": "ok"' in l]
folders = json.load(open(IM + "/folders.json"))
def gallery(name, items, cols=6, cell=200, cap=24, label_fn=lambda r: os.path.basename(r["src"])):
    items = items[:cap]; rws = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rws * cell), (245, 245, 245))
    for i, r in enumerate(items):
        try: t = Image.open(IM + "/_thumbs/" + r["png"] + ".jpg")
        except Exception: continue
        t.thumbnail((cell - 8, cell - 8)); sheet.paste(t, ((i % cols) * cell + (cell - t.width) // 2, (i // cols) * cell + (cell - t.height) // 2))
    p = f"{G}/{name}.jpg"; sheet.save(p, "JPEG", quality=80); return {"file": p, "labels": [label_fn(r) for r in items], "cols": cols, "rows": rws}
def under(prefix): return sorted([r for r in rows if r["png"].startswith(prefix + "/")], key=lambda r: r["png"])
GAL = [("Loading screens (surfaces/background)", "surfaces/background", 4, 24), ("Photobook cards (surfaces/res/photobook)", "surfaces/res/photobook", 6, 36),
       ("World maps (surfaces/maps/worldmaps)", "surfaces/maps/worldmaps", 6, 24), ("Character portraits (surfaces/res/portrait)", "surfaces/res/portrait", 8, 40),
       ("Quest illustrations (surfaces/res/quest)", "surfaces/res/quest", 6, 18), ("Login / character creation (flash)", "flash", 6, 18),
       ("Gold Saint model textures (models/npcs/黄金圣斗士)", "models/npcs/黄金圣斗士", 6, 24), ("Player Cloth textures (models/players/圣衣)", "models/players/圣衣", 6, 24),
       ("Sky boxes (textures/sky)", "textures/sky", 6, 12), ("Effect textures (gfx/textures)", "gfx/textures", 8, 32), ("Aerial map views (loddata)", "loddata", 6, 18)]
gals = [{"title": t, "folder": f, **gallery(f.replace("/", "__"), under(f), cols=c, cap=n)} for t, f, c, n in GAL]
icons = list(csv.DictReader(open(IM + "/icons/index.csv", encoding="utf-8")))
ic = [{"png": i["png"], "src": i["name"]} for i in icons if i["atlas"] in ("iconlist_ivtr1", "iconlist_skill", "iconlist_portrait")][::40][:48]
def icon_gallery():
    cell, cols = 64, 12; rws = (len(ic) + cols - 1) // cols; sheet = Image.new("RGB", (cols * cell, rws * cell), (245, 245, 245))
    for i, r in enumerate(ic):
        t = Image.open(IM + "/" + r["png"]).convert("RGBA"); bg = Image.new("RGBA", t.size, (245, 245, 245, 255)); bg.alpha_composite(t)
        sheet.paste(bg.convert("RGB"), ((i % cols) * cell + 4, (i // cols) * cell + 4))
    p = G + "/icons.jpg"; sheet.save(p, "JPEG", quality=85); return {"title": "UI icons split from the atlases (images/icons)", "folder": "icons", "file": p, "labels": [], "cols": cols, "rows": rws}
gals.append(icon_gallery())
packs = collections.OrderedDict()
for r in rows: p = r["png"].split("/")[0]; packs.setdefault(p, {"count": 0, "large": 0, "formats": collections.Counter()}); packs[p]["count"] += 1; packs[p]["large"] += (r["w"] >= 1000 and r["h"] >= 600); packs[p]["formats"][r.get("format", "").replace("DDS/", "")] += 1
top = collections.OrderedDict()
for f in folders:
    parts = f["folder"].split("/"); key = "/".join(parts[:3 if (parts[0] == "surfaces" or parts[:2] in (["models", "npcs"], ["models", "players"])) else (1 if parts[0] in ("grasses", "loddata", "shaders", "flash") else 2)]) if parts[0] != "building" else "building/textures"
    t = top.setdefault(key, {"count": 0, "large": 0, "folders": 0}); t["count"] += f["count"]; t["large"] += f["large"]; t["folders"] += 1
maps = list(csv.DictReader(open(OUT + "/text/maps.csv", encoding="utf-8")))
codes = collections.OrderedDict()
for m in maps:
    if m["map_code"]: codes.setdefault(m["map_code"], []).append(m["name_en"] or m["name_zh"])
data = {"out": OUT, "total": len(rows), "icons": len(icons), "packs": [{"pack": k, **v, "formats": ", ".join(f"{a} {b}" for a, b in v["formats"].most_common(4)), "label": label(k)} for k, v in packs.items()],
        "top": [{"folder": k, **v, "label": label(k)} for k, v in top.items()], "galleries": gals, "map_codes": [{"code": k, "names": sorted(set(v))[:4]} for k, v in codes.items()],
        "media": json.load(open(OUT + "/media_index.json"))}
json.dump(data, open(WORK + "/data.json", "w"), ensure_ascii=False); print("galleries", len(gals), "top folders", len(top), "packs", len(packs))
