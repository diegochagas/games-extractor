#!/usr/bin/env python3
"""Dump Saint Seiya Online lang_*.data (LANG v1) files.
Layout: 'LANG' u32 ver u32 ? u16 nsections, then per section: u32 tag, u32 nameLen, name, u32 count,
count x ( u32 len key, u32 len zh_source, u32 len translation ) all UTF-8.
Usage: lang.py OUTDIR FILE...   -> OUTDIR/<lang>/<section>.tsv  +  OUTDIR/<lang>.json
"""
import struct, sys, json, os
def parse(path):
    d = open(path, "rb").read()
    assert d[:4] == b"LANG"
    nsec = struct.unpack_from("<H", d, 0x0c)[0]
    p = 0x0e; sections = []
    for _ in range(nsec):
        tag, nl = struct.unpack_from("<II", d, p); name = d[p+8:p+8+nl].decode(); p += 8 + nl
        cnt = struct.unpack_from("<I", d, p)[0]; p += 4
        rows = []
        for _ in range(cnt):
            r = []
            for _ in range(3):
                L = struct.unpack_from("<I", d, p)[0]; p += 4; r.append(d[p:p+L].decode("utf-8", "replace")); p += L
            rows.append(r)
        sections.append((name, rows))
    assert len(d) - p <= 4, (path, hex(p), hex(len(d)))  # files end with 2 trailing bytes
    return sections
out = sys.argv[1]
for path in sys.argv[2:]:
    lang = os.path.basename(path)[5:-5]
    secs = parse(path)
    os.makedirs(f"{out}/{lang}", exist_ok=True)
    total = 0
    for name, rows in secs:
        with open(f"{out}/{lang}/{name or 'noname'}.tsv", "w") as f:
            f.write("key\tzh_source\ttranslation\n")
            for r in rows: f.write("\t".join(x.replace("\t", "\\t").replace("\r\n", "\\n").replace("\n", "\\n") for x in r) + "\n")
        total += len(rows)
    json.dump({name: rows for name, rows in secs}, open(f"{out}/{lang}.json", "w"), ensure_ascii=False)
    print(lang, len(secs), "sections", total, "strings:", ", ".join(f"{n or 'noname'}={len(r)}" for n, r in secs))
