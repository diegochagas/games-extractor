"""Map table from script/map/instance.lua + LANG map names -> OUT/text/maps.csv"""
import re, csv, sys
OUT = sys.argv[1]
lua = open(OUT + "/text/files/script/map/instance.lua", encoding="utf-8").read()
tr = {}
for lang in ("pt-BR", "en-US"):
    for row in csv.DictReader(open(f"{OUT}/text/lang/{lang}/map.tsv", encoding="utf-8"), delimiter="\t"):
        tr.setdefault(row["zh_source"], {})[lang] = row["translation"]
rows = []
for m in re.finditer(r'Instance\[(\d+)\] = \{(.*?)\n\}', lua, re.S):
    idx, body = int(m.group(1)), m.group(2)
    g = lambda k: (re.search(k + r'\s*=\s*_?t?\(?"([^"]*)"', body) or [None, ""])[1]
    zh = g("name"); rows.append({"instance_id": idx, "map_code": g("path"), "name_zh": zh, "name_pt": tr.get(zh, {}).get("pt-BR", ""), "name_en": tr.get(zh, {}).get("en-US", ""),
                                 "world_map": g("worldMap").replace("\\\\", "/"), "loading_image": g("loadingImage").replace("\\\\", "/"), "zone": (re.search(r"idZone\s*=\s*(\d+)", body) or [0, ""])[1]})
with open(OUT + "/text/maps.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
codes = {}
for r in rows: codes.setdefault(r["map_code"], []).append(r["name_en"] or r["name_zh"])
print(len(rows), "instances,", len(codes), "map codes"); print({k: v[:2] for k, v in list(codes.items())[:70]})
