#!/usr/bin/env python3
"""Build the list of render jobs (characters) from an Angelica model dump.

    inventory.py DUMP_DIR OUT.json

DUMP_DIR is the dump folder (with `packages/models/...` and the converted
`images/models/.../*.dds.png`). Each job lists the `.ski` parts that make one
character and the PNG texture for every texture name the parts use.

Jobs:
  * NPCs: every `.smd` under `packages/models/npcs` that references at least
    one `.ski` (duplicates with the same mesh set are merged).
  * Players: every cloth set in `packages/models/players/圣衣/<gender>`:
    the base head, pupils and class hair from `形象/<gender>`, the inner suit
    `<set><gender>.ski` and the cloth pieces `<set>圣衣<piece>_动画.ski`.
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ski import parse_ski, SkiError  # noqa: E402
from smd import parse_smd  # noqa: E402

PIECES = ["头盔", "胸甲", "左肩甲", "右肩甲", "左臂", "右臂", "腰", "左右腿"]
CLASSES = ["天马", "天龙", "白鸟", "仙女", "凤凰"]
GENDERS = {"男": "male", "女": "female"}


class TextureIndex:
    def __init__(self, images_root):
        self.by_name = defaultdict(list)
        self.by_stem_nogender = defaultdict(list)
        for root, _dirs, files in os.walk(images_root):
            for f in files:
                if f.lower().endswith(".png"):
                    key = f[:-4].lower()
                    self.by_name[key].append(os.path.join(root, f))
                    self.by_stem_nogender[os.path.splitext(key)[0].replace("男", "").replace("女", "")].append(os.path.join(root, f))

    def find(self, name, near):
        """PNG for texture `name`, preferring the candidate closest to `near`."""
        cands = self.by_name.get(name.lower())
        if not cands:
            stem = os.path.splitext(name)[0].lower()
            cands = [p for k, v in self.by_name.items() if os.path.splitext(k)[0] == stem for p in v]
        if not cands:
            # NPC meshes sometimes name the player textures without the gender character (白银天琴座神圣衣圣衣DF1 -> ...神圣衣男圣衣df1)
            key = os.path.splitext(name)[0].lower().replace("男", "").replace("女", "")
            cands = self.by_stem_nogender.get(key, [])
        if not cands:
            return None
        near_parts = near.lower().split(os.sep)

        def score(p):
            parts = p.lower().split(os.sep)
            n = 0
            for a, b in zip(near_parts, parts):
                if a != b:
                    break
                n += 1
            return n

        return max(cands, key=score)


def texture_map(ski_path, tex_index, rel_for_images):
    try:
        model = parse_ski(ski_path, with_geometry=False)
    except SkiError as exc:
        return None, str(exc)
    used = {m["texture_name"] for m in model["meshes"] if m["texture_name"]}
    textures = {}
    missing = []
    for t in used:
        png = tex_index.find(t, rel_for_images)
        if png:
            textures[t] = png
        else:
            missing.append(t)
    return {"ski": ski_path, "textures": textures, "missing": missing,
            "meshes": len(model["meshes"]),
            "vertices": sum(m["vertex_count"] for m in model["meshes"])}, None


def npc_jobs(models, images_models, tex_index):
    jobs = []
    npcs = os.path.join(models, "npcs")
    seen = set()
    for root, _dirs, files in os.walk(npcs):
        for f in sorted(files):
            if not f.lower().endswith(".smd"):
                continue
            smd_path = os.path.join(root, f)
            try:
                info = parse_smd(smd_path)
            except ValueError as exc:
                print("skip %s: %s" % (smd_path, exc), file=sys.stderr)
                continue
            skis = [os.path.join(root, s) for s in info["skis"]]
            skis = [s for s in skis if os.path.exists(s)]
            if not skis:
                continue
            key = tuple(sorted(skis))
            if key in seen:
                continue
            seen.add(key)
            rel = os.path.relpath(root, npcs)
            group = rel.split(os.sep)[0]
            parts = []
            for s in skis:
                part, err = texture_map(s, tex_index, os.path.join(images_models, os.path.relpath(s, models)))
                if err:
                    print("skip %s: %s" % (s, err), file=sys.stderr)
                    continue
                parts.append(part)
            if parts:
                jobs.append({
                    "id": "npcs/" + os.path.join(rel, os.path.splitext(f)[0]).replace(os.sep, "/"),
                    "category": "npc",
                    "group": group,
                    "folder": rel.replace(os.sep, "/"),
                    "name": os.path.splitext(f)[0],
                    "parts": parts,
                })
    # .ski files that no .smd of their folder references (variant meshes such as 珍妮冥衣版.ski)
    referenced = {p["ski"] for j in jobs for p in j["parts"]}
    for root, _dirs, files in os.walk(npcs):
        for f in sorted(files):
            if not f.lower().endswith(".ski"):
                continue
            s = os.path.join(root, f)
            if s in referenced:
                continue
            rel = os.path.relpath(root, npcs)
            part, err = texture_map(s, tex_index, os.path.join(images_models, os.path.relpath(s, models)))
            if err or not part["meshes"]:
                continue
            jobs.append({
                "id": "npcs/" + os.path.join(rel, os.path.splitext(f)[0]).replace(os.sep, "/"),
                "category": "npc", "group": rel.split(os.sep)[0], "folder": rel.replace(os.sep, "/"),
                "name": os.path.splitext(f)[0], "parts": [part], "orphan": True,
            })
    return jobs


def player_jobs(models, images_models, tex_index):
    jobs = []
    players = os.path.join(models, "players")
    for zh, gender in GENDERS.items():
        cloth_dir = os.path.join(players, "圣衣", zh)
        look = os.path.join(players, "形象", zh)
        base = []
        for sub, first in (("头", zh + "头01"), ("瞳孔", zh + "瞳孔01")):
            p = os.path.join(look, sub, first, first + ".ski")
            if os.path.exists(p):
                base.append(p)
        default_hair = os.path.join(look, "头发", zh + "头发01", zh + "头发01.ski")
        if not os.path.isdir(cloth_dir):
            continue
        files = set(os.listdir(cloth_dir))
        sets = sorted(f[:-len(zh + ".ski")] for f in files if f.endswith(zh + ".ski"))
        # sets of the later "new class" naming: 新职业_<name>_<sex>_<version>.ski + 新职业_<name>_<sex>_<version>_头盔.ski
        import re as _re
        for f in sorted(files):
            m = _re.match(r"^(新职业_.+?)_%s_([^_]+)\.ski$" % zh, f)
            if not m:
                continue
            name = "%s_%s" % (m.group(1), m.group(2))
            skis = list(base) + [default_hair, os.path.join(cloth_dir, f)]
            helmet = os.path.join(cloth_dir, f[:-4] + "_头盔.ski")
            if os.path.exists(helmet):
                skis.append(helmet)
            parts = []
            for s in skis:
                if not os.path.exists(s):
                    continue
                part, err = texture_map(s, tex_index, os.path.join(images_models, os.path.relpath(s, models)))
                if not err:
                    parts.append(part)
            jobs.append({"id": "players/%s/%s" % (gender, name), "category": "player", "group": gender,
                         "folder": "players/圣衣/" + zh, "name": name, "pieces": ["头盔"] if os.path.exists(helmet) else [], "parts": parts})
        for name in sets:
            skis = list(base)
            hair = None
            for cls in CLASSES:
                cand = "%s%s职业%s头发.ski" % (name, cls, zh)
                if cand in files:
                    hair = os.path.join(cloth_dir, cand)
                    break
            skis.append(hair or default_hair)
            skis.append(os.path.join(cloth_dir, name + zh + ".ski"))
            pieces = []
            for piece in PIECES:
                cand = "%s圣衣%s_动画.ski" % (name, piece)
                if cand in files:
                    pieces.append(cand)
                    skis.append(os.path.join(cloth_dir, cand))
            parts = []
            for s in skis:
                if not os.path.exists(s):
                    continue
                part, err = texture_map(s, tex_index, os.path.join(images_models, os.path.relpath(s, models)))
                if err:
                    print("skip %s: %s" % (s, err), file=sys.stderr)
                    continue
                parts.append(part)
            jobs.append({
                "id": "players/%s/%s" % (gender, name),
                "category": "player",
                "group": gender,
                "folder": "players/圣衣/" + zh,
                "name": name,
                "pieces": pieces,
                "parts": parts,
            })
    return jobs


def object_jobs(models, images_models, tex_index):
    """Cloth object forms (players/道具/圣衣组合版), cloth boxes (players/道具/圣衣箱) and the
    other assembled-cloth models: one job per .smd, category "object"."""
    jobs = []
    seen = set()
    roots = [("players/道具/圣衣组合版", "cloth-object"), ("players/道具/圣衣箱", "cloth-box"),
             ("特效用ecm/狮子座圣衣组合版", "cloth-object"), ("矿物/海龙座鳞衣组合版", "cloth-object")]
    for rel_root, group in roots:
        root_dir = os.path.join(models, rel_root)
        if not os.path.isdir(root_dir):
            continue
        for root, _dirs, files in os.walk(root_dir):
            for f in sorted(files):
                if not f.lower().endswith(".smd"):
                    continue
                try:
                    info = parse_smd(os.path.join(root, f))
                except ValueError:
                    continue
                skis = [os.path.join(root, s) for s in info["skis"] if os.path.exists(os.path.join(root, s))]
                if not skis or tuple(sorted(skis)) in seen:
                    continue
                seen.add(tuple(sorted(skis)))
                parts = []
                for s in skis:
                    part, err = texture_map(s, tex_index, os.path.join(images_models, os.path.relpath(s, models)))
                    if not err:
                        parts.append(part)
                if parts:
                    rel = os.path.relpath(root, models)
                    jobs.append({"id": "objects/" + os.path.join(rel, os.path.splitext(f)[0]).replace(os.sep, "/"),
                                 "category": "object", "group": group, "folder": rel.replace(os.sep, "/"),
                                 "name": os.path.splitext(f)[0], "parts": parts})
    return jobs


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 1
    dump, out = argv
    models = os.path.join(dump, "packages", "models")
    images_models = os.path.join(dump, "images", "models")
    tex_index = TextureIndex(images_models)
    jobs = npc_jobs(models, images_models, tex_index) + player_jobs(models, images_models, tex_index) + object_jobs(models, images_models, tex_index)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=1)
    missing = sum(len(p["missing"]) for j in jobs for p in j["parts"])
    print("%d jobs (%d npc, %d player, %d object), %d missing textures"
          % (len(jobs), sum(j["category"] == "npc" for j in jobs),
             sum(j["category"] == "player" for j in jobs), sum(j["category"] == "object" for j in jobs), missing))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
