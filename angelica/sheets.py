"""Contact sheets for chosen folders -> OUT/images/_sheets/<folder>.jpg (cells labelled with file name)."""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont
OUT = sys.argv[1]; IM = OUT + "/images"; SH = IM + "/_sheets"; os.makedirs(SH, exist_ok=True)
rows = [json.loads(l) for l in open(IM + "/manifest.jsonl") if '"status": "ok"' in l]
FOLDERS = sys.argv[2:] or ["surfaces/background", "surfaces/maps/worldmaps", "surfaces/res/photobook", "surfaces/res/portrait", "surfaces/res/head",
           "flash", "gfx/title", "surfaces/res/login", "surfaces/special/charcreat", "surfaces/res/quest", "surfaces/iconset", "surfaces/res/daily",
           "surfaces/special/godship", "surfaces/special/territory", "textures/sky", "models/players/圣衣", "models/npcs/黄金圣斗士", "models/npcs/青铜圣斗士",
           "loddata/f8/birdviews", "surfaces/special/athena", "surfaces/special/gift", "surfaces/special/explore"]
try: font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10); cjk = ImageFont.truetype(OUT + "/fonts/fzlbjw.ttf", 11)
except Exception: font = cjk = ImageFont.load_default()
for folder in FOLDERS:
    items = sorted([r for r in rows if r["png"].startswith(folder + "/")], key=lambda r: r["png"])
    if not items: print("empty", folder); continue
    cap = int(os.environ.get("CAP", "400")); items = items[:cap]
    cell, cols = 160, 8; th = 24
    rws = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rws * (cell + th)), (30, 30, 30)); d = ImageDraw.Draw(sheet)
    for i, r in enumerate(items):
        x, y = (i % cols) * cell, (i // cols) * (cell + th)
        try:
            t = Image.open(IM + "/_thumbs/" + r["png"] + ".jpg"); sheet.paste(t, (x + (cell - t.width) // 2, y + (cell - t.height) // 2))
        except Exception: pass
        name = os.path.basename(r["src"]); label = name if len(name) <= 24 else name[:22] + "…"
        f = cjk if any(ord(c) > 127 for c in label) else font
        d.text((x + 3, y + cell + 2), label, fill=(230, 230, 230), font=f); d.text((x + 3, y + cell + 12), f'{r["w"]}x{r["h"]}', fill=(150, 150, 150), font=font)
    out = SH + "/" + folder.replace("/", "__") + ".jpg"; sheet.save(out, "JPEG", quality=82)
    print(folder, len(items), sheet.size)
