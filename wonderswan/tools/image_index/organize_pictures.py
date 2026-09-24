#!/usr/bin/env python3
"""Copy every dumped image of the four Digimon WonderSwan games into a picture library organised like the image index:
one folder per game, one sub-folder per ROM bank named "bankNN - <Portuguese label>", original file names kept
(so "bank12/6BC8_picture_224x144.png" in the image-index document = "bank12 - Locais da história/6BC8_picture_224x144.png").
Only image files are written (no index files): the descriptions live in the folder names, the image-index .docx and the story books.

    organize_pictures.py GAMES_DIR OUT_DIR LABELS.json

GAMES_DIR = folder holding the four "<N> - <game> (WonderSwan…)" dump folders (each with images/manifest.json).
LABELS.json = {"1": {"bank00": {"label": "…"}, …}, …} (keys 1-4 = game number).
Extra image folders next to a dump (box art / official screenshots) are copied as "Material oficial - <folder name>".
"""
import json, os, re, shutil, sys

GAMES = {"1": "Digimon Anode & Cathode Tamer (Veedramon Version)", "2": "Digimon Adventure 02 - Tag Tamers",
         "3": "Digimon Adventure 02 - D-1 Tamers", "4": "Digimon Tamers - Brave Tamer"}
IMG = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")


def safe(s):
    return re.sub(r'[\\/:*?"<>|]+', "-", s).strip()


def main():
    src_root, out_root, labels = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3], encoding="utf-8"))
    n_total = 0
    for num, name in GAMES.items():
        dumps = [d for d in sorted(os.listdir(src_root)) if re.match(r"%s\s*-" % num, d) and os.path.isdir(os.path.join(src_root, d, "images"))]
        if not dumps:
            print("no dump for game", num); continue
        dump = os.path.join(src_root, dumps[0])
        out = os.path.join(out_root, "%s - %s" % (num, name))
        man = json.load(open(os.path.join(dump, "images/manifest.json")))
        n = 0
        for b, v in man.items():
            bank = "bank%02d" % int(b)
            lab = labels.get(num, {}).get(bank, {}).get("label", "")
            folder = os.path.join(out, safe("%s - %s" % (bank, lab)) if lab else bank)
            for e in v["rendered"]:
                src = os.path.join(dump, "images", bank, e["file"])
                if not os.path.exists(src): continue
                os.makedirs(folder, exist_ok=True)
                dst = os.path.join(folder, e["file"])
                if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
                    shutil.copy2(src, dst)
                n += 1
        # official material folders (box art, screenshots) next to the dump
        for d in sorted(os.listdir(dump)):
            p = os.path.join(dump, d)
            if os.path.isdir(p) and d not in ("images", "fonts") and any(f.lower().endswith(IMG) for f in os.listdir(p)):
                folder = os.path.join(out, safe("Material oficial - " + d))
                os.makedirs(folder, exist_ok=True)
                for f in sorted(os.listdir(p)):
                    if f.lower().endswith(IMG):
                        shutil.copy2(os.path.join(p, f), os.path.join(folder, f)); n += 1
        # font sheets are pictures too
        fd = os.path.join(dump, "fonts")
        if os.path.isdir(fd):
            folder = os.path.join(out, "Fontes")
            for f in sorted(os.listdir(fd)):
                if f.lower().endswith(IMG):
                    os.makedirs(folder, exist_ok=True); shutil.copy2(os.path.join(fd, f), os.path.join(folder, f)); n += 1
        print("%s: %d images" % (name, n)); n_total += n
    print("total", n_total)


if __name__ == "__main__":
    main()
