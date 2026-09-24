#!/usr/bin/env python3
"""check_fit.py FIT_CHUNK.json FIT_CHUNK.en.json - verify condensed translations fit their boxes."""
import json
import re
import sys

import fit

ALLOWED = re.compile(r"^[A-Za-z0-9 !?.,'\-:;/()%&+*=<>~\n]*$")
chunk = json.load(open(sys.argv[1], encoding="utf-8"))
out = json.load(open(sys.argv[2], encoding="utf-8"))
bad = 0
for it in chunk:
    k, en = it["k"], out.get(it["k"])
    if en is None:
        print(k, "MISSING")
        bad += 1
        continue
    prefix = it["prefix"]
    if not en.startswith(prefix):
        print(k, f"must start with the prefix {prefix!r}")
        bad += 1
        continue
    # the hidden header can be longer than the prefix the chunk names (pointer-table bytes)
    body = en[max(len(prefix), fit.header_len(it["jp"], en)):]
    lines = body.split("\n")
    probs = []
    if len(lines) > it["lines"]:
        probs.append(f"{len(lines)} lines > {it['lines']}")
    wide = [l for l in lines if fit.vis(l) > it["width"]]
    if wide:
        probs.append(f"line too wide ({fit.vis(wide[0])} > {it['width']}): {wide[0]!r}")
    if sorted(re.findall(r"<[0-9A-F]{2}>\d?", body)) != sorted(re.findall(r"<[0-9A-F]{2}>\d?", it["jp"][len(prefix):])):
        probs.append("control tokens differ from the Japanese")
    if not ALLOWED.match(re.sub(r"<[0-9A-F]{2}>", "", body)):
        probs.append("characters outside the font")
    if probs:
        bad += 1
        print(k, "; ".join(probs))
print(f"{len(chunk) - bad}/{len(chunk)} OK")
sys.exit(1 if bad else 0)
