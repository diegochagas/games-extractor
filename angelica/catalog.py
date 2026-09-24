#!/usr/bin/env python3
"""Image catalogue: images/manifest.csv, images/folders.json and the HTML index (images/index.html + images/_index/*.html)."""
import os, sys, json, csv, html, collections
sys.path.insert(0, os.path.dirname(__file__)); from labels import label, MAP_CODES
OUT = sys.argv[1]; IM = OUT + "/images"
for r in csv.DictReader(open(OUT + "/text/maps.csv", encoding="utf-8")):
    if r["map_code"] and r["map_code"] not in MAP_CODES: MAP_CODES[r["map_code"]] = r["name_en"] or r["name_zh"]
rows = [json.loads(l) for l in open(IM + "/manifest.jsonl")]
ok = [r for r in rows if r["status"] == "ok"]
icons = list(csv.DictReader(open(IM + "/icons/index.csv", encoding="utf-8")))
# manifest.csv
with open(IM + "/manifest.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["png", "source", "format", "width", "height", "mode", "mipmaps", "source_bytes", "png_bytes", "status", "note"])
    for r in rows: w.writerow([r["png"], r["src"], r.get("format", ""), r.get("w", ""), r.get("h", ""), r.get("mode", ""), r.get("mipmaps", ""), r["src_bytes"], r.get("png_bytes", ""), r["status"], r.get("note", r.get("error", ""))])
# folders: leaf folder = directory holding the file
by_folder = collections.defaultdict(list)
for r in ok: by_folder[os.path.dirname(r["png"])].append(r)
folders = []
for fo, items in sorted(by_folder.items()):
    dims = collections.Counter((r["w"], r["h"]) for r in items)
    folders.append({"folder": fo, "label": label(fo), "count": len(items), "large": sum(1 for r in items if r["w"] >= 1000 and r["h"] >= 600),
                    "formats": dict(collections.Counter(r.get("format", "") for r in items)), "sizes": [f"{w}x{h} ({n})" for (w, h), n in dims.most_common(3)], "bytes": sum(r.get("png_bytes", 0) for r in items)})
json.dump(folders, open(IM + "/folders.json", "w"), ensure_ascii=False, indent=0)
# HTML
IDX = IM + "/_index"; os.makedirs(IDX, exist_ok=True)
CSS = """body{font-family:system-ui,sans-serif;background:#1b1b1f;color:#ddd;margin:0;padding:16px}a{color:#8cc4ff;text-decoration:none}h1,h2{font-weight:600}
table{border-collapse:collapse;font-size:13px}td,th{padding:3px 8px;border-bottom:1px solid #333;text-align:left}th{position:sticky;top:0;background:#26262b}td.n{text-align:right;font-variant-numeric:tabular-nums}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(172px,1fr));gap:8px}.cell{background:#26262b;border-radius:6px;padding:4px;font-size:11px;overflow:hidden}
.cell img{width:160px;height:160px;object-fit:contain;display:block;margin:0 auto;background:#111}.cell .nm{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:3px}.cell .dm{color:#888}
.crumb{color:#999;font-size:13px;margin-bottom:10px}input{background:#26262b;color:#ddd;border:1px solid #444;padding:4px 8px;border-radius:4px;width:320px}.pg a{margin-right:8px}"""
def page_name(fo, n=0): return fo.replace("/", "__") + (f"_{n}" if n else "") + ".html"
PER = 1000
def folder_page(fo, items):
    items = sorted(items, key=lambda r: r["png"]); pages = [items[i:i + PER] for i in range(0, len(items), PER)] or [[]]
    for pi, chunk in enumerate(pages):
        cells = []
        for r in chunk:
            cells.append(f'<div class="cell"><a href="../{html.escape(r["png"])}" target="_blank"><img loading="lazy" src="../_thumbs/{html.escape(r["png"])}.jpg" alt=""></a>'
                         f'<div class="nm" title="{html.escape(r["src"])}">{html.escape(os.path.basename(r["src"]))}</div><div class="dm">{r["w"]}x{r["h"]} · {html.escape(r.get("format",""))}</div></div>')
        pg = "".join(f'<a href="{page_name(fo, i)}">{"["+str(i+1)+"]" if i == pi else i+1}</a>' for i in range(len(pages))) if len(pages) > 1 else ""
        parents = fo.split("/"); crumb = ' / '.join(f'<a href="../index.html">images</a>' if i < 0 else html.escape(p) for i, p in enumerate(parents))
        doc = f'<!doctype html><meta charset="utf-8"><title>{html.escape(fo)}</title><style>{CSS}</style><div class="crumb"><a href="../index.html">← index</a> · {crumb}</div>' \
              f'<h2>{html.escape(fo)} <small style="color:#999;font-weight:400">{html.escape(label(fo))}</small></h2><p>{len(items)} images · files live in <code>images/{html.escape(fo)}/</code>, originals in <code>packages/{html.escape(fo)}/</code></p>' \
              f'<div class="pg">{pg}</div><div class="grid">{"".join(cells)}</div><div class="pg">{pg}</div>'
        open(os.path.join(IDX, page_name(fo, pi)), "w", encoding="utf-8").write(doc)
for fo, items in by_folder.items(): folder_page(fo, items)
# icons page
cells = "".join(f'<div class="cell"><a href="../{html.escape(i["png"])}" target="_blank"><img loading="lazy" src="../{html.escape(i["png"])}" alt="" style="width:56px;height:56px;image-rendering:pixelated"></a><div class="nm" title="{html.escape(i["name"])}">{html.escape(i["name"])}</div><div class="dm">{html.escape(i["atlas"])} #{i["index"]}</div></div>' for i in icons)
open(os.path.join(IDX, "icons.html"), "w", encoding="utf-8").write(f'<!doctype html><meta charset="utf-8"><title>icons</title><style>{CSS}</style><div class="crumb"><a href="../index.html">← index</a></div><h2>UI icons split from the atlases</h2><p>{len(icons)} icons from surfaces/iconset (names from the iconlist_*.txt lists).</p><div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(120px,1fr))">{cells}</div>')
# master index
packs = collections.Counter(); 
for r in ok: packs[r["png"].split("/")[0]] += 1
trs = "".join(f'<tr><td><a href="_index/{page_name(f["folder"])}">{html.escape(f["folder"])}</a></td><td>{html.escape(f["label"])}</td><td class="n">{f["count"]}</td><td class="n">{f["large"]}</td><td>{html.escape(", ".join(f["sizes"]))}</td><td>{html.escape(", ".join(k.replace("DDS/","") for k in f["formats"]))}</td></tr>' for f in folders)
summary = "".join(f'<tr><td>{p}</td><td>{html.escape(label(p))}</td><td class="n">{n}</td></tr>' for p, n in sorted(packs.items()))
doc = f'''<!doctype html><meta charset="utf-8"><title>Saint Seiya Online – image index</title><style>{CSS}</style>
<h1>Saint Seiya Online (Seiya Reborn client) – image index</h1>
<p>{len(ok)} images converted to PNG under <code>images/</code> (same path as inside the .pck archives, <code>.png</code> appended), plus <a href="_index/icons.html">{len(icons)} UI icons</a> split from the atlases. Click a folder to browse thumbnails; click a thumbnail to open the full PNG. Contact sheets of the main folders are in <code>images/_sheets/</code>.</p>
<h2>Per archive</h2><table><tr><th>archive (.pck)</th><th>what</th><th class="n">images</th></tr>{summary}<tr><td>icons (split atlases)</td><td>surfaces/iconset</td><td class="n">{len(icons)}</td></tr></table>
<h2>All folders</h2><p><input id="q" placeholder="filter folders…" oninput="for(const r of document.querySelectorAll('#t tr')) r.style.display=r.textContent.toLowerCase().includes(this.value.toLowerCase())?'':'none'"></p>
<table id="t"><tr><th>folder</th><th>what</th><th class="n">images</th><th class="n">≥1000x600</th><th>common sizes</th><th>formats</th></tr>{trs}</table>'''
open(IM + "/index.html", "w", encoding="utf-8").write(doc)
print("folders", len(folders), "images", len(ok), "icons", len(icons), "pages", len(os.listdir(IDX)))
