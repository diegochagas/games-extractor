#!/usr/bin/env python3
"""Collect metadata + thumbnails of every dumped image for the image-index document.

    python3 collect.py DOWNLOADS_DIR      # writes data.json and thumbs/ in the current folder
    node build.js "OUT.docx"              # needs: npm install docx
"""
import json
import os
import sys

from PIL import Image

D = sys.argv[1].rstrip("/") + "/"
GAMES = [("D-1 Tamers", "Digimon Adventure 02 - D-1 Tamers", "Digimon Adventure 02- D-1 Tamers.wsc", "WonderSwan Color"),
         ("Tag Tamers", "Digimon Adventure 02 - Tag Tamers (2000)(Bandai)[tr en][SWJ-BAN032]",
          "Digimon Adventure 02 - Tag Tamers (2000)(Bandai)[tr en][SWJ-BAN032].ws", "WonderSwan (mono)"),
         ("Anode Tamer", "Digimon Anode Tamer - Veedramon Version", "Digimon Anode Tamer - Veedramon Version.wsc", "WonderSwan Color"),
         ("Brave Tamer", "Digimon Tamers - Brave Tamer (2001-12-29)(Bandai)[SWJ-BANC1D]",
          "Digimon Tamers - Brave Tamer (2001-12-29)(Bandai)[SWJ-BANC1D].wsc", "WonderSwan Color")]
os.makedirs("thumbs", exist_ok=True)
out = []
for short, folder, rom, system in GAMES:
    base = D + folder + "/images/"
    man = json.load(open(base + "manifest.json"))
    blobs = {(int(b), x["offset"]): x for b, v in man.items() for x in v["blobs"]}
    items = []
    for bank, v in sorted(man.items(), key=lambda kv: int(kv[0])):
        bank = int(bank)
        for e in v["rendered"]:
            p = base + "bank%02d/" % bank + e["file"]
            if not os.path.exists(p):
                continue
            w, h = Image.open(p).size
            t = blobs.get((bank, e["tiles"]), {})
            hexo = lambda k: "%04X" % e[k] if e.get(k) is not None else ""
            it = {"bank": bank, "file": e["file"], "rel": "images/bank%02d/%s" % (bank, e["file"]), "type": e["type"],
                  "w": w, "h": h, "tiles": "%04X" % e["tiles"], "bpp": t.get("bpp"), "ntiles": t.get("count"),
                  "compressed": t.get("compressed"), "tilemap": hexo("tilemap"), "layout": hexo("layout"),
                  "palette": hexo("palette"), "rom_offset": "0x%06X" % (bank * 0x10000 + e["tiles"])}
            it["full"] = it["type"] == "picture" and w >= 208 and h >= 128
            if it["full"]:
                tn = "thumbs/%s_%02d_%s" % (short.replace(" ", "_"), bank, e["file"])
                im = Image.open(p).convert("RGB")
                im.thumbnail((168, 120), Image.NEAREST)
                im.save(tn)
                it["thumb"] = tn
            items.append(it)
    out.append({"short": short, "folder": D + folder, "rom": D + rom, "system": system, "items": items})
json.dump(out, open("data.json", "w"))
print({g["short"]: len(g["items"]) for g in out})
