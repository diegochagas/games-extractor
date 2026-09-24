#!/usr/bin/env python3
"""Link every NPC / monster of the game to its 3D model.

    npc_models.py DUMP_DIR CLIENT_DATA_DIR

Reads `path.data` (id -> resource path, GBK) and `elements.data` from the
client's element/data folder, plus the language dump in DUMP_DIR/text, and
writes DUMP_DIR/text/npc_models.json:

    {"<id>": {"kind": "npc"|"monster", "zh": ..., "pt": ..., "model": "models\\npcs\\...ecm",
              "job": "<render job id or null>"}}

Record layout found empirically: the id is a u32 at the start of the record,
the model path id is the u32 at +204 (NPC records, 340 bytes) or +148
(monster records). A candidate is accepted only when that id is a
`models\\npcs\\...ecm` path.
"""
import json
import os
import re
import struct
import sys


def read_paths(path_data):
    d = open(path_data, "rb").read()
    paths = {}
    p = 8
    while p + 8 <= len(d):
        i, n = struct.unpack_from("<II", d, p)
        if n == 0 or n > 400:
            break
        paths[i] = d[p + 8:p + 8 + n].decode("gbk", "replace")
        p += 8 + n
    return paths


def main(dump, client_data):
    paths = read_paths(os.path.join(client_data, "path.data"))
    model_ids = {k for k, v in paths.items() if v.lower().endswith(".ecm") and "\\npcs\\" in v.lower()}
    E = open(os.path.join(client_data, "elements.data"), "rb").read()
    lang = json.load(open(os.path.join(dump, "text/lang/pt-BR.json"), encoding="utf-8"))
    ids = {}
    for sec, kind in (("data_npc", "npc"), ("data_monster", "monster")):
        for k, z, t in lang[sec]:
            m = re.match(r"(npc|monster)_(\d+)_name$", k)
            if m:
                ids[int(m.group(2))] = (kind, z, t)
    # index of every 4-aligned u32 value in elements.data -> positions
    offsets = {"npc": 204, "monster": 148}
    n_u32 = len(E) // 4
    vals = struct.unpack_from("<%dI" % n_u32, E, 0)
    where = {}
    for i, v in enumerate(vals):
        if v in ids:
            where.setdefault(v, []).append(i * 4)
    # jobs: ecm dir + stem -> job id
    jobs = {}
    jp = os.path.join(dump, "text/render_jobs.json")
    if os.path.exists(jp):
        for j in json.load(open(jp, encoding="utf-8")):
            if j["category"] == "npc":
                jobs[j["id"].lower()] = j["id"]
    out = {}
    for i, (kind, z, t) in ids.items():
        off = offsets[kind]
        model = None
        for p in where.get(i, []):
            if p + off + 4 > len(E):
                continue
            v = struct.unpack_from("<I", E, p + off)[0]
            if v in model_ids:
                model = paths[v]
                break
        job = None
        if model:
            rel = model.replace("\\", "/")
            rel = rel[rel.lower().index("npcs/"):]  # some path.data entries lose the "mo" of models\
            stem = os.path.splitext(rel)[0]
            job = jobs.get(stem.lower())
            if not job:  # variants like name1.ecm / name_x.ecm fall back to the folder's main smd
                folder = os.path.dirname(stem).lower()
                cands = [v for k, v in jobs.items() if k.startswith(folder + "/")]
                job = cands[0] if cands else None
        out[str(i)] = {"kind": kind, "zh": z, "pt": t, "model": model, "job": job}
    with open(os.path.join(dump, "text/npc_models.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    n_model = sum(1 for v in out.values() if v["model"])
    n_job = sum(1 for v in out.values() if v["job"])
    print("%d ids, %d with model, %d linked to a render job" % (len(out), n_model, n_job))
    return out


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
