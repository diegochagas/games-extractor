#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Monta story.json para o documento 'Saint Seiya Online - Story' a partir do dump em ~/Downloads/Seiya."""
import os, sys, re, json, csv, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from story_config import PARTS, SIDE_GROUPS, SYSTEM_PATTERNS, CHAPTERS, REGION_IMAGES, CARDS, PORTRAITS, PRESS_NOTES
OUT = os.path.expanduser("~/Downloads/Seiya"); T = OUT + "/text"
GALLERY = os.environ.get("SSO_GALLERY", os.path.expanduser("~/Downloads/Saint Seiya Online - Galeria de Imagens"))  # saída de angelica/render/organize.py
WORK = sys.argv[1] if len(sys.argv) > 1 else "."

Q = json.load(open(T + "/quests_pt-BR.json")); byid = {q["id"]: q for q in Q}
MT = set(json.load(open(T + "/quests_mt_fallback_ids.json")))
SYS = [re.compile(p) for p in SYSTEM_PATTERNS]
def is_system(q): n = q.get("name") or ""; return any(r.search(n) for r in SYS)
def clean(s): return re.sub(r"\^[0-9A-Fa-f]{6}|\^N|\$noname\$UImid|&name&", lambda m: {"&name&": "[Herói]"}.get(m.group(0), ""), s or "").replace("\\n", "\n").strip()
def qrec(q):
    return {"id": q["id"], "name": clean(q.get("name")), "descript": clean(q.get("descript")), "mt": q["id"] in MT,
            "delv": [{"talk": clean(w["talk"]), "options": [clean(o) for o in w["options"]]} for w in q["delv"].get("windows", [])],
            "award": [{"talk": clean(w["talk"]), "options": [clean(o) for o in w["options"]]} for w in q["award"].get("windows", [])],
            "unq": [{"talk": clean(w["talk"]), "options": [clean(o) for o in w["options"]]} for w in q["unq"].get("windows", [])]}
used = set(); sigs = {}; dup_ids = []; dup_of = {}
def collect(ranges, need_desc=True):
    out = []
    for lo, hi in ranges:
        for i in range(lo, hi + 1):
            q = byid.get(i)
            if not q or i in used or is_system(q): continue
            sig = (q.get("name"), q.get("descript"), json.dumps(q["delv"], ensure_ascii=False), json.dumps(q["award"], ensure_ascii=False), json.dumps(q["unq"], ensure_ascii=False))
            if sig in sigs: used.add(i); dup_ids.append(i); dup_of[i] = sigs[sig]; continue
            sigs[sig] = i; used.add(i); out.append(qrec(q))
    return out
story_re = re.compile(r"^A história d[eoa] (.+?) \((\d+)/(\d+)\)$")
# 1. partes
parts = []
for P in PARTS:
    secs = []
    for S_ in P["sections"]:
        main = collect(S_["ranges"])
        alts = [{"title": t, "quests": collect(r)} for t, r in S_.get("alt", [])]
        secs.append({"id": S_["id"], "title": S_["title"], "intro": S_["intro"], "chapter": CHAPTERS[S_["chapter"]], "images": REGION_IMAGES.get(S_["region"], []), "quests": main, "alts": [a for a in alts if a["quests"]]})
    parts.append({"id": P["id"], "title": P["title"], "intro": P["intro"], "sections": secs})
# 2. histórias dos personagens
stories = collections.OrderedDict()
for q in Q:
    m = story_re.match(q.get("name") or "")
    if m and q["id"] not in used:
        stories.setdefault(m.group(1), []).append((int(m.group(2)), q))
char_stories = []
for name, lst in stories.items():
    lst.sort(key=lambda x: (x[0], x[1]["id"])); qs = []
    for n, q in lst:
        if q["id"] in used: continue
        used.add(q["id"]); qs.append(qrec(q))
    char_stories.append({"character": name, "quests": qs})
# 3. secundárias por região
side = []
for title, region, ranges in SIDE_GROUPS:
    qs = collect(ranges)
    side.append({"title": title, "images": REGION_IMAGES.get(region, [])[:1], "quests": qs})
# 4. armaduras (missões de obtenção)
cloth_q = {"bronze": [], "prata": [], "ouro": [], "sapuris": []}
for q in Q:
    n = q.get("name") or ""
    if q["id"] in used or is_system(q): continue
    if n.startswith("Armadura de Bronze ·"): cloth_q["bronze"].append(qrec(q)); used.add(q["id"])
    elif n.startswith("Armadura de Prata ·"): cloth_q["prata"].append(qrec(q)); used.add(q["id"])
    elif re.search(r"Armadura de Ouro|Mirage|ilustrações|Atlas|Chamado de Deus|sangue · Ouro|Sangue .* [Oo]uro|Gold Sangue|de sangue · Ouro|· Ouro Sangue|Pano de Ouro", n) and 5465 <= q["id"] <= 5738: cloth_q["ouro"].append(qrec(q)); used.add(q["id"])
    elif re.search(r"Sion|冥衣", n + (q.get("name_zh") or "")): cloth_q["sapuris"].append(qrec(q)); used.add(q["id"])
# 5. restante (eventos, desafios, sistema) -> apêndice compacto
rest = collections.OrderedDict()
for q in Q:
    if q["id"] in used or is_system(q): continue
    sig = (q.get("name"), q.get("descript"), json.dumps(q["delv"], ensure_ascii=False), json.dumps(q["award"], ensure_ascii=False), json.dumps(q["unq"], ensure_ascii=False))
    if sig in sigs: dup_ids.append(q["id"]); dup_of[q["id"]] = sigs[sig]; continue
    sigs[sig] = q["id"]; used.add(q["id"])
    blk = q["id"] // 1000 * 1000
    rest.setdefault(blk, []).append(qrec(q))
others = [{"block": f"IDs {k}–{k+999}", "quests": v} for k, v in sorted(rest.items())]
# 5b. missões de teste dos desenvolvedores (padrões SYSTEM_PATTERNS): também entram, num apêndice próprio
test_rest = collections.OrderedDict()
for q in Q:
    if not is_system(q): continue
    blk = q["id"] // 1000 * 1000
    test_rest.setdefault(blk, []).append(qrec(q))
tests_q = [{"block": f"IDs {k}–{k+999}", "quests": v} for k, v in sorted(test_rest.items())]
tests = sum(len(b["quests"]) for b in tests_q)
def nwin(q): return len(q["delv"]) + len(q["award"]) + len(q["unq"])
all_recs = [q for p in parts for sct in p["sections"] for q in sct["quests"] + [x for a in sct["alts"] for x in a["quests"]]] + [q for st in char_stories for q in st["quests"]] + [q for sd in side for q in sd["quests"]] + [q for v in cloth_q.values() for q in v] + [q for b in others for q in b["quests"]] + [q for b in tests_q for q in b["quests"]]
total_win = sum(len(q["delv"].get("windows", [])) + len(q["award"].get("windows", [])) + len(q["unq"].get("windows", [])) for q in Q)
qstats = {"quests_total": len(Q), "quests_in_doc": len(all_recs), "duplicates_dropped": len(dup_ids), "windows_total": total_win, "windows_in_doc": sum(nwin(q) for q in all_recs)}
print("STATS", qstats)

# 6. fotolivro: personagens, armaduras, lugares
LANG = {}
def col(l, s):
    if l not in LANG: LANG[l] = json.load(open(f"{T}/lang/{l}.json", encoding="utf-8"))
    return [(t or "").replace("\r\n", "\n").replace("\r", "\n") for k, z, t in LANG[l][s]]
def colkv(l, s):
    if l not in LANG: LANG[l] = json.load(open(f"{T}/lang/{l}.json", encoding="utf-8"))
    return LANG[l][s]
pt = col("pt-BR", "photobook")
pb_chars = []
for i in range(1, len(pt) - 1):
    if pt[i].startswith("^cd0000") and 0 < len(pt[i - 1]) < 40 and len(pt[i + 1]) > 80:
        stats = [s.strip() for s in re.split(r"\^cd0000", pt[i]) if s.strip()]
        stats = [re.sub(r"\^ffffff", " ", s).strip() for s in stats]
        pb_chars.append({"name": pt[i - 1].strip(), "stats": stats, "bio": clean(pt[i + 1])})
cm = col("pt-BR", "common"); cz = col("DATA", "common"); bios_common = []
for i in range(1, len(cm)):
    if len(cm[i]) > 250 and cm[i].startswith("\u3000") and 0 < len(cm[i - 1]) < 40:
        bios_common.append({"name": re.sub(r"\^[0-9A-Fa-f]{6}", "", cm[i - 1]).strip(), "color": (re.match(r"\^([0-9A-Fa-f]{6})", cm[i - 1]) or [None, ""])[1], "zh": re.sub(r"\^[0-9A-Fa-f]{6}", "", cz[i - 1]).strip(), "bio": clean(cm[i])})
# textos de lugares e armaduras do fotolivro (nome curto seguido de texto longo sem stats)
pb_texts = {}
for i in range(1, len(pt)):
    if len(pt[i]) > 120 and not pt[i].startswith("^") and 0 < len(pt[i - 1]) < 30 and not pt[i - 1].startswith(("^", "script")):
        pb_texts.setdefault(pt[i - 1].strip(), clean(pt[i]))
# cartões do fotolivro: mapa manual zh -> (pt, grupo)
pb_dir = OUT + "/images/surfaces/res/photobook"; card_files = {f.split(".")[0]: "images/surfaces/res/photobook/" + f for f in os.listdir(pb_dir)}
cards = []
for zh, (ptn, grp) in CARDS.items():
    f = card_files.get(zh)
    if f: cards.append({"zh": zh, "pt": ptn, "group": grp, "file": f})
unmapped = [z for z in card_files if z not in CARDS]
# retratos principais (surfaces/res/portrait)
port_dir = OUT + "/images/surfaces/res/portrait"; port_files = {f.split(".")[0]: "images/surfaces/res/portrait/" + f for f in os.listdir(port_dir)}
head_dir = OUT + "/images/surfaces/res/head"; head_files = {f.split(".")[0]: "images/surfaces/res/head/" + f for f in os.listdir(head_dir)}
portraits = {k: (port_files.get(v) or head_files.get(v)) for k, v in PORTRAITS.items() if v in port_files or v in head_files}
# NPCs nomeados (para o índice): zh -> pt
npc = collections.OrderedDict()
for k, z, t in colkv("pt-BR", "data_npc"):
    if k.endswith("_name") and t and z: npc.setdefault(z, t)
mon = collections.OrderedDict()
for k, z, t in colkv("pt-BR", "data_monster"):
    if k.endswith("_name") and t and z: mon.setdefault(z, t)
# 7. galeria de renders 3D (angelica/render/organize.py -> text/gallery_index.json)
gallery, gallery_folders = [], {}
if os.path.exists(T + "/gallery_index.json"):
    gi = json.load(open(T + "/gallery_index.json", encoding="utf-8")); gallery_folders = gi["folders"]
    for it in gi["items"]:
        it = dict(it); it["files"] = {k: ([GALLERY + "/" + x for x in v] if isinstance(v, list) else GALLERY + "/" + v) for k, v in it["files"].items()}
        if "front" in it["files"]: it["files"]["front_thumb"] = it["files"]["front"] + "#thumb"
        if "images" in it["files"]: it["files"]["thumbs"] = [x + "#thumb" for x in it["files"]["images"]]
        gallery.append(it)
# 7b. NPC/monstro -> modelo (angelica/npc_models.py -> text/npc_models.json): lista única (nome pt, zh, job)
npc_models = []
if os.path.exists(T + "/npc_models.json"):
    seen_nm = set()
    for i, v in json.load(open(T + "/npc_models.json", encoding="utf-8")).items():
        if not v.get("job"): continue
        key = (v["pt"], v["job"])
        if key in seen_nm: continue
        seen_nm.add(key); npc_models.append({"id": int(i), "kind": v["kind"], "zh": v["zh"], "pt": v["pt"], "job": v["job"], "model": v["model"]})
# 7c. personagens do histórico do site Saint Seiya Cloths (text/site_history_saints.json)
site_saints = json.load(open(T + "/site_history_saints.json", encoding="utf-8")) if os.path.exists(T + "/site_history_saints.json") else []
# 7d. vozes dos chefes (packages/sfx/boss配音): nome zh do arquivo -> personagem
boss_voices = collections.OrderedDict()
bv = OUT + "/packages/sfx/boss配音"
if os.path.isdir(bv):
    for f in sorted(os.listdir(bv)):
        stem = re.sub(r"^[a-z]-", "", os.path.splitext(f)[0]); who = re.sub(r"\d+$", "", stem)
        boss_voices.setdefault(who, []).append(f)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "render"))
from names import translate as _tr, load_game_names as _lg  # noqa: E402
_GN = _lg(T + "/names_zh_en_pt.json")
boss_voices = [{"zh": k, "pt": _tr(k, _GN)["pt"], "files": v} for k, v in boss_voices.items()]
# 8. mapas, cinemáticas, legendas, diálogos das dungeons, títulos
maps = list(csv.DictReader(open(T + "/maps.csv", encoding="utf-8")))
anim = col("pt-BR", "animation")
is_title = lambda a: bool(re.search(r" ?- |--|_", a)) and len(a) < 90 and not re.search(r"[.!?…]$", a.strip())
cut_titles = [a.strip() for a in anim if is_title(a)]
subtitles = [clean(a) for a in anim if a.strip() and not is_title(a) and not a.startswith("script")]
inst = [clean(x) for x in col("pt-BR", "quest") if x.strip() and not x.startswith("script")]
npc_lines = []
for k, z, t in colkv("pt-BR", "data_text"):
    t = clean(t)
    if t and len(t) > 2 and not re.match(r"^(Dano|text_|Reunindo o|Esta atividade)", t) and not re.search(r"\+\d", t): npc_lines.append(t)
npc_lines = list(dict.fromkeys(npc_lines))
titles = col("pt-BR", "title")
title_rows = []
for i in range(0, len(titles) - 1):
    if titles[i].startswith("^009933") and titles[i + 1] and not titles[i + 1].startswith("^"):
        how = next((titles[j] for j in range(i + 2, min(i + 9, len(titles))) if re.match(r"(Conclua|Complete|Atinja|Alcance|Obtenha|Derrote|Participe|Vença|Ganhe|Colete|Ao )", titles[j])), "")
        title_rows.append({"name": clean(titles[i]), "desc": clean(titles[i + 1]), "how": clean(how)})
# 9. cobertura das notas de pesquisa
KEYS = [("Rodório", ["罗德里奥"]), ("Lei-Hu", ["雷虎"]), ("Sher-Khan", ["希尔汗", "Sher Khan"]), ("June renegada (Sapuris)", ["变色龙座珍妮", "冥化"]), ("Asceta (Dorado)", ["剑鱼座"]), ("Perséfone", ["冥后", "珀耳塞福涅"]), ("Lamech", ["拉蒙斯", "虚无之神"]), ("Sillas", ["撒里诺", "西拉斯", "火山"]), ("Valquíria", ["瓦尔基里"]), ("Loki", ["洛基"]), ("Wyrm", ["天威星"]), ("Jubokko (soldado)", ["树妖", "冥界杂兵"]), ("Kafka (Arlequim)", ["卡夫卡", "Kafka", "地伏星"]), ("Moe / Larry / Curly", ["Moe", "Larry", "Curly", "天暗星", "天阴星", "天异星"]), ("Steven", ["Steven", "天杀星"]), ("Stone", ["史东", "地明星"]), ("Gerald", ["杰拉尔德", "Gerald"]), ("Isolde", ["伊索尔", "地恶星"]), ("Tornado / Ellan", ["狂风", "天坦座"]), ("Aiya e Eide", ["艾娅", "艾德"]), ("Alex", ["阿历克斯"]), ("Nya", ["尼亚"]), ("Jaffet", ["云峰"]), ("Li-Yun", ["李云"]), ("Colomba / Augusto", ["高龙巴", "奥古斯塔"]), ("Alexer", ["亚雷库萨"]), ("Natássia", ["娜塔莎"]), ("Acer", ["枫"]), ("Taylor", ["泰勒"]), ("Zeros", ["赛洛斯"]), ("Lupin / Luise", ["鲁邦", "鲁琪"]), ("Cássios", ["卡西欧士"]), ("Kanon", ["加隆"]), ("Thetis", ["狄蒂斯"]), ("Julian / Füssen", ["尤里安", "菲森"]), ("Hermes", ["赫尔墨斯"]), ("Odin", ["奥丁"]), ("Fenrir", ["芬里尔", "菲利路"]), ("Siegfried/Hagen/Alberich/Mime/Syd (Guerreiros Deuses)", ["齐格弗里德", "哈根", "阿鲁贝利亚", "米伊美", "希度"]), ("Ares", ["阿瑞斯", "战神"]), ("Afrodite (deusa)", ["阿芙洛狄忒"]), ("Eros", ["爱洛斯"]), ("Apolo", ["阿波罗"]), ("Bennu", ["贝努", "Bennu", "贝奴"]), ("Górgona", ["地走星", "戈尔贡"]), ("Icelus / Morfeu / Fantaso (deuses do sonho)", ["梦神", "伊刻罗斯", "摩耳甫斯", "幻想神"]), ("Cão Menor / Cérbero", ["地狱犬座"]), ("Atrium / Mensa / Oriolus", ["天幕座", "山案座", "银莺座"])]
allzh = set(npc) | set(mon)
cfg = set()
for k, z, t in colkv("pt-BR", "data_config"): cfg.add(z)
qtext = " ".join((q.get("name_zh") or "") for q in Q)
coverage = []
for label, keys in KEYS:
    hits = []
    for k in keys:
        n1 = [npc[z] for z in npc if k in z or k.lower() in npc[z].lower()][:3]; m1 = [mon[z] for z in mon if k in z or k.lower() in mon[z].lower()][:3]; c1 = sum(1 for z in cfg if k in z); q1 = qtext.count(k)
        if n1 or m1 or c1 or q1: hits.append(f"{k}: NPC {n1} | monstros {m1} | {c1} entradas de config | {q1} quests")
    coverage.append({"item": label, "found": bool(hits), "detail": "; ".join(hits)[:500]})
data = {"parts": parts, "char_stories": char_stories, "side": side, "cloth_quests": cloth_q, "others": others, "tests": tests, "tests_q": tests_q, "stats": qstats, "duplicates": [{"id": i, "name": clean(byid[i].get("name")), "of": o} for i, o in sorted(dup_of.items())],
        "pb_chars": pb_chars, "bios_common": bios_common, "pb_texts": pb_texts, "cards": cards, "unmapped_cards": unmapped, "portraits": portraits,
        "gallery": gallery, "gallery_folders": gallery_folders, "npc_models": npc_models, "site_saints": site_saints, "boss_voices": boss_voices, "press_notes": PRESS_NOTES, "bg": {f.split(".")[0]: "images/surfaces/background/" + f for f in os.listdir(OUT + "/images/surfaces/background") if f.startswith("loading")},
        "worldmaps": {f.split(".")[0]: "images/surfaces/maps/worldmaps/" + f for f in os.listdir(OUT + "/images/surfaces/maps/worldmaps")},
        "site_root": os.environ.get("SSC_SITE", os.path.expanduser("~/Projects/saintseiyacloths/public")), "maps": maps, "cut_titles": cut_titles, "subtitles": subtitles, "instance_dialogue": inst, "titles": title_rows, "coverage": coverage, "npc_lines": npc_lines,
        "npc_count": len(npc), "mon_count": len(mon), "out": OUT}
json.dump(data, open(os.path.join(WORK, "story.json"), "w"), ensure_ascii=False)
def cnt(qs): return len(qs), sum(len(q["delv"]) + len(q["award"]) for q in qs)
print("PARTS:"); tot = 0
for p in parts:
    for s in p["sections"]:
        n, w = cnt(s["quests"]); a = sum(len(x["quests"]) for x in s["alts"]); tot += n + a; print(f"  {s['id']:4s} {n:4d} quests {w:5d} janelas  +{a} alt   {s['title'][:60]}")
print("char stories:", len(char_stories), sum(len(c["quests"]) for c in char_stories))
print("side:", [(s["title"][:20], len(s["quests"])) for s in side]); print("cloth quests:", {k: len(v) for k, v in cloth_q.items()})
print("others:", sum(len(o["quests"]) for o in others), "blocks", len(others), "| tests skipped", tests)
print("pb_chars", len(pb_chars), [c["name"] for c in pb_chars][:50]); print("bios_common", len(bios_common)); print("pb_texts", len(pb_texts)); print("cards", len(cards), "unmapped", unmapped)
print("portraits", len(portraits), "missing:", [k for k in PORTRAITS if k not in portraits]); print("gallery items", len(gallery)); print("cut titles", len(cut_titles), "subtitles", len(subtitles), "inst lines", len(inst), "titles", len(title_rows))
print("coverage:", [(c["item"], c["found"]) for c in coverage])
