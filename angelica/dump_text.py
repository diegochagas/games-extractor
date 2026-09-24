#!/usr/bin/env python3
"""Text dump for the Saint Seiya Online client.
 - text/files/<pack>/...   : every txt/ini/cfg/xml/lua/dcf/h/hlsl file from the packs and loose folders, re-encoded to UTF-8
 - text/binary_strings/*.txt: Chinese strings scraped from binary tables (elements.data, text.data, tasks.data*, gshop.data)
 - text/animations/*.txt   : asset references (models, effects, sounds) inside each cutscene .anm
Usage: dump_text.py CLIENT_ELEMENT_DIR PACKAGES_DIR OUT_TEXT_DIR"""
import os, re, sys, json
ELEM, PKG, OUT = [a.rstrip("/") for a in sys.argv[1:4]]
TEXT_EXT = {"txt", "ini", "cfg", "xml", "lua", "dcf", "h", "hlsl", "sw", "project", "prefs", "manifest", "json"}

def decode(b):
    if b[:2] == b"\xff\xfe": return b[2:].decode("utf-16le", "replace"), "utf-16le"
    if b[:2] == b"\xfe\xff": return b[2:].decode("utf-16be", "replace"), "utf-16be"
    if b[:3] == b"\xef\xbb\xbf": return b[3:].decode("utf-8", "replace"), "utf-8-bom"
    if len(b) > 1 and b.count(b"\0") > len(b) // 4: return b.decode("utf-16le", "replace"), "utf-16le?"
    try: return b.decode("utf-8"), "utf-8"
    except UnicodeDecodeError: pass
    try: return b.decode("gbk"), "gbk"
    except UnicodeDecodeError: return b.decode("latin-1"), "latin-1"

stats = {}
def dump_tree(root, prefix):
    for dp, _, fs in os.walk(root):
        for f in fs:
            ext = f.lower().rsplit(".", 1)[-1] if "." in f else ""
            if ext not in TEXT_EXT: continue
            p = os.path.join(dp, f); rel = os.path.relpath(p, root)
            b = open(p, "rb").read()
            if len(b) > 20_000_000: continue
            t, enc = decode(b)
            dst = os.path.join(OUT, "files", prefix, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, "w", encoding="utf-8").write(t.replace("\r\n", "\n"))
            stats[enc] = stats.get(enc, 0) + 1
for pack in ("configs", "interfaces", "script", "shaders"):
    dump_tree(os.path.join(PKG, pack), pack)
for loose in ("resources", "bin", "roleSettings", "audio", "newstips", "Logs", "reportbugs", "pp"):
    dump_tree(os.path.join(ELEM, loose), loose)
for f in ("launcher.ini", "start.bat"):
    b = open(os.path.join(ELEM, f), "rb").read(); t, enc = decode(b)
    os.makedirs(os.path.join(OUT, "files"), exist_ok=True); open(os.path.join(OUT, "files", f), "w").write(t)
print("text files re-encoded:", stats)

# binary string scrape (UTF-16LE Chinese runs)
cjk = re.compile(r"[一-鿿　-〿！-～][一-鿿　-〿！-～A-Za-z0-9 ,.!?:;()+%/\-_…、《》]{1,}")
os.makedirs(os.path.join(OUT, "binary_strings"), exist_ok=True)
for name in sorted(os.listdir(os.path.join(ELEM, "data"))):
    if name.startswith("lang_") or name.startswith("n") and name.endswith(".dat") or name == "path.data": continue
    d = open(os.path.join(ELEM, "data", name), "rb").read()
    found = []
    seen = set()
    for off in (0, 1):
        t = d[off:].decode("utf-16le", "ignore")
        for m in cjk.finditer(t):
            s = m.group(0)
            if len(s) >= 2 and s not in seen: seen.add(s); found.append((off + m.start() * 2, s))
    if not found: continue
    found.sort()
    with open(os.path.join(OUT, "binary_strings", name + ".txt"), "w") as f:
        f.write(f"# UTF-16LE Chinese strings scraped from data/{name} ({len(d)} bytes). Column 1 = byte offset. Not parsed structurally.\n")
        for o, s in found: f.write(f"{o:08X}\t{s}\n")
    print(name, len(found), "strings")

# cutscene asset references
anm_dir = os.path.join(ELEM, "videos", "animations"); os.makedirs(os.path.join(OUT, "animations"), exist_ok=True)
ref = re.compile(r"[A-Za-z0-9_一-鿿\\/\-\. ]+\.(?:ecm|gfx|ogg|mp4|smd|bmd|ski|mox|dds|tga|png|wav|anm)", re.I)
index = []
for f in sorted(os.listdir(anm_dir)):
    if not f.endswith(".anm"): continue
    d = open(os.path.join(anm_dir, f), "rb").read()
    refs = set()
    for off in (0, 1):
        for m in ref.finditer(d[off:].decode("utf-16le", "ignore")): refs.add(m.group(0).strip())
    refs = sorted(refs)
    with open(os.path.join(OUT, "animations", f[:-4] + ".txt"), "w") as o:
        o.write(f"# {f} ({len(d)} bytes): assets referenced by this cutscene\n" + "\n".join(refs) + "\n")
    index.append({"file": f, "bytes": len(d), "refs": len(refs)})
json.dump(index, open(os.path.join(OUT, "animations", "index.json"), "w"), ensure_ascii=False, indent=0)
print("cutscenes:", len(index))
