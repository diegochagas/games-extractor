#!/usr/bin/env python3
"""Copy the rendered characters and the game images used in the story book
into a gallery organised like Diego's "Saint Seiya Cloth Schemes" library:
one flat folder per faction, kebab-case English file names.

    organize.py DUMP_DIR OUT_DIR [--jobs text/render_jobs.json] [--renders renders]
                [--names text/names_zh_en_pt.json]

Output:
    OUT_DIR/<faction>/<name>[-male|-female]-{front,side,back}.png   3D renders
    OUT_DIR/<faction>/<name>-album-card.png / -portrait.png          game images
    OUT_DIR/world-maps/, OUT_DIR/loading-screens/                    game images
    OUT_DIR/index.json (+ copy in DUMP_DIR/text/gallery_index.json)  what went where
"""
import argparse
import csv
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "story"))
from names import translate, slug, load_game_names  # noqa: E402
from story_config import CARDS, PORTRAITS  # noqa: E402

VIEWS = ["front", "side", "back"]

LAMECH = ("力量之神", "物质之神", "真理之神", "沙暴之", "雷之", "虚无之神", "拉蒙斯")
OLYMPIANS = ("爱神", "爱洛斯", "阿波罗", "阿芙洛狄忒")
ASGARD = ("天枢星", "天璇星", "天玑星", "天机星", "天权星", "玉衡星", "开阳星", "摇光星", "辅星", "神斗士", "洛基", "瓦尔基里",
          "北欧神族", "北欧弓箭手")
BLUE_WARRIORS = ("冰斗士", "冰之国", "冰大陆", "亚雷库萨", "娜塔莎")
SAINT_PROPS = ("锁链", "雕像", "红玫瑰", "掉落的", "_特效", "面具", "竖琴", "美杜莎之盾", "死亡特效")
STORY_PEOPLE = ("雷虎", "李云", "枫", "朱利安", "尤里安", "命运", "美惠", "艾丝美拉达", "娜塔莎", "雅科夫", "亚雷库萨", "星华", "基鲁提",
                "春丽", "贵鬼", "尤丽缇丝", "城户光政", "辰巳", "卡西欧士", "撒里诺", "艾德", "艾亚", "阿历克斯", "黑衣人", "怪人")
GENERIC_PEOPLE = ("杂兵", "居民", "村民", "学员", "候补生", "观众", "商人", "雇员", "路人", "亡灵", "奴隶", "女奴", "渔民", "盗贼", "水手",
                  "流放者", "幸存者", "女仆", "农夫", "梦游者", "遗民", "船夫", "厨娘", "小女孩", "小男孩", "少女", "平民", "使节", "祭司",
                  "老人", "隐士", "修行者", "拳师", "孤儿", "神父", "花童", "兔女郎", "守护者", "考验者", "勇士", "长老", "弓箭手", "队长",
                  "强盗", "战士", "中毒的", "先锋", "御林军", "炼金术士", "服务员", "村长", "海盗", "英灵", "神父", "花童", "圣诞老人")
MONSTERS = ("怪", "兽", "妖", "史莱姆", "巨人", "石像鬼", "蛇", "狼", "熊", "蝙蝠", "鲸", "蟹", "乌贼", "水母", "秃鹫", "蛙", "猴", "虫",
            "鹰", "乌鸦", "天鹅", "游尸", "小恶魔", "深潜者", "碟王", "黑龙", "神龙", "巨龙", "飞龙", "斯芬克斯", "迦楼罗", "蘑菇", "海星",
            "海蛇", "衣魂", "之衣", "圣衣怪", "机甲", "组合", "防御塔", "娃娃", "南瓜")
PROPS = ("锁链", "特效", "雕像", "柱子", "石头", "植被", "桃子", "门", "琴", "面具", "玫瑰", "箱", "笛", "佛珠", "盾", "剑", "船", "墓",
         "礼物", "花圈", "帽子", "栅栏", "邮箱", "卡丁车", "气球", "圣诞树", "背景", "大厅", "房子", "栏杆", "冰", "球", "旗", "水池")

PT_FOLDER = {
    "athena-saints": "Cavaleiros de Athena", "hades-specters": "Espectros de Hades", "poseidon-mariners": "Marinas de Poseidon",
    "odin-god-warriors": "Guerreiros Deuses de Odin", "odin-blue-warriors": "Guerreiros Azuis (País do Gelo)", "lamech-servants": "Servos de Lamech", "zeus-olympians": "Olimpianos",
    "others": "Outros personagens", "npcs": "NPCs genéricos", "pets": "Pets", "monsters": "Monstros e feras",
    "artifacts": "Relíquias e armas", "skill-effects": "Efeitos de habilidades", "scenery-and-props": "Cenários e objetos",
    "cutscene-props": "Objetos das cinemáticas", "world-maps": "Mapas do mundo", "loading-screens": "Telas de carregamento",
}


def has(name, words):
    return any(w in name for w in words)


def classify(job):
    name = job["name"]
    if job["category"] == "player":
        if has(name, LAMECH):
            return "lamech-servants"
        if has(name, ("冥", "翼龙")):
            return "hades-specters"
        if has(name, ("海斗士", "鳞衣", "海龙", "北海巨妖")):
            return "poseidon-mariners"
        return "athena-saints"
    g = job["group"]
    if g == "宠物":
        return "pets"
    if g in ("野兽", "怪物", "洪荒模型"):
        return "monsters"
    if g == "技能用怪":
        return "skill-effects"
    if g in ("机关npc", "机关怪物", "场景", "场景物品", "矿物", "滚雪球"):
        return "scenery-and-props"
    if g == "神器":
        return "artifacts"
    if g == "动画":
        return "cutscene-props"
    if has(name, OLYMPIANS):
        return "zeus-olympians"
    if has(name, LAMECH):
        return "lamech-servants"
    if has(name, ASGARD):
        return "odin-god-warriors"
    if has(name, BLUE_WARRIORS):
        return "odin-blue-warriors"
    if g == "极乐净土":
        return "hades-specters"
    if g == "冥王势力":
        if has(name, ("雕像", "特效", "树桩", "花")):
            return "scenery-and-props"
        if has(name, ("卵群", "若虫", "史莱姆", "深潜者", "女妖", "碟王", "冥蝶", "飞龙")):
            return "monsters"
        return "npcs" if has(name, ("杂兵", "御林军", "先锋", "炼金术士")) else "hades-specters"
    if g in ("青铜圣斗士", "白银圣斗士", "黄金圣斗士", "黑暗圣斗士", "雅典娜"):
        return "scenery-and-props" if has(name, SAINT_PROPS) else "athena-saints"
    if g in ("其他原著角色", "boss") or has(name, STORY_PEOPLE):
        return "others"
    if has(name, GENERIC_PEOPLE):
        return "npcs"
    if g in ("圣域势力", "选人背景npc"):
        return "scenery-and-props" if has(name, SAINT_PROPS) else "athena-saints"
    if g == "哈迪斯城":
        return "hades-specters"
    if g in ("海皇势力", "亚特兰蒂斯"):
        if has(name, ("雕像", "石头")):
            return "scenery-and-props"
        return "monsters" if has(name, ("乌贼", "巨鲸")) else "poseidon-mariners"
    if g == "东西伯利亚":
        return "monsters" if has(name, MONSTERS) else "npcs"
    if g == "其他":
        if has(name, ("冰河",)):
            return "athena-saints"
        if has(name, ("辰巳",)):
            return "others"
        if has(name, MONSTERS):
            return "monsters"
        return "scenery-and-props"
    # region groups
    if has(name, MONSTERS) and not has(name, ("植被", "桃子")):
        return "monsters"
    if has(name, PROPS):
        return "scenery-and-props"
    return "npcs"


def card_folder(group):
    return {"bronze": "athena-saints", "prata": "athena-saints", "ouro": "athena-saints", "negro": "athena-saints",
            "arm_bronze": "athena-saints", "arm_prata": "athena-saints", "arm_ouro": "athena-saints", "arm_divina": "athena-saints",
            "marina": "poseidon-mariners", "escama": "poseidon-mariners", "espectro": "hades-specters", "sapuris": "hades-specters",
            "outros": "others", "lugar": "world-maps"}.get(group, "others")


def portrait_folder(zh):
    for words, folder in ((OLYMPIANS, "zeus-olympians"), (LAMECH, "lamech-servants"), (ASGARD, "odin-god-warriors"), (BLUE_WARRIORS, "odin-blue-warriors"),
                          (("冥", "潘多拉", "死神", "睡神", "哈迪斯", "尤丽缇丝"), "hades-specters"),
                          (("海", "朱利安", "加隆", "波塞冬"), "poseidon-mariners")):
        if has(zh, words):
            return folder
    if has(zh, ("星矢", "紫龙", "冰河", "瞬", "一辉", "雅典娜", "纱织", "沙织", "魔铃", "莎尔娜", "童虎", "教皇", "史昂", "米罗", "艾俄洛斯",
                "黄金圣斗士", "黑暗", "白银", "奥路菲", "英灵", "学员")):
        return "athena-saints"
    return "others"


class Namer:
    """Unique kebab-case base names per folder."""

    def __init__(self):
        self.used = {}

    def take(self, folder, base, key):
        used = self.used.setdefault(folder, {})
        if used.get(base) in (None, key):
            used[base] = key
            return base
        n = 2
        while used.get("%s-%d" % (base, n)) not in (None, key):
            n += 1
        used["%s-%d" % (base, n)] = key
        return "%s-%d" % (base, n)


def copy(src, dst):
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump")
    ap.add_argument("out")
    ap.add_argument("--jobs", default="text/render_jobs.json")
    ap.add_argument("--renders", default="renders")
    ap.add_argument("--names", default="text/names_zh_en_pt.json")
    a = ap.parse_args()
    dump = os.path.abspath(a.dump)
    out = os.path.abspath(a.out)
    jobs = json.load(open(os.path.join(dump, a.jobs), encoding="utf-8"))
    game_names = load_game_names(os.path.join(dump, a.names))
    renders = os.path.join(dump, a.renders)
    namer = Namer()
    index = []

    # 1. 3D renders
    n_jobs = 0
    for job in jobs:
        jdir = os.path.join(renders, job["id"])
        if not os.path.exists(os.path.join(jdir, "job.json")):
            continue
        t = translate(job["name"], game_names)
        folder = classify(job)
        base = slug(t["en"])
        sex = ""
        if job["category"] == "player":
            sex = job["group"]  # male / female
            base = "%s-%s" % (base, sex)
        base = namer.take(folder, base, job["id"])
        files = {}
        for view in VIEWS:
            src = os.path.join(jdir, view + ".png")
            if os.path.exists(src):
                rel = "%s/%s-%s.png" % (folder, base, view)
                copy(src, os.path.join(out, rel))
                files[view] = rel
        if files:
            n_jobs += 1
            index.append({"kind": "render", "job": job["id"], "category": job["category"], "group": job["group"], "sex": sex,
                          "zh": job["name"], "en": t["en"], "pt": t["pt"], "folder": folder, "base": base, "files": files,
                          "pieces": job.get("pieces", [])})

    # 2. album cards
    pb = os.path.join(dump, "images/surfaces/res/photobook")
    for zh, (pt, group) in CARDS.items():
        src = os.path.join(pb, zh + ".dds.png")
        if not os.path.exists(src):
            continue
        folder = card_folder(group)
        t = translate(zh, game_names)
        base = namer.take(folder, slug(pt if group == "lugar" else t["en"]), "card:" + zh)
        rel = "%s/%s-album-card.png" % (folder, base)
        copy(src, os.path.join(out, rel))
        index.append({"kind": "album-card", "zh": zh, "en": t["en"], "pt": pt, "group": group, "folder": folder, "base": base,
                      "files": {"card": rel}})

    # 3. portraits
    for label, zh in PORTRAITS.items():
        src = None
        for sub in ("portrait", "head"):
            cand = os.path.join(dump, "images/surfaces/res", sub, zh + ".dds.png")
            if os.path.exists(cand):
                src = cand
                break
        if not src:
            continue
        folder = portrait_folder(zh)
        base = namer.take(folder, slug(label), "portrait:" + zh)
        rel = "%s/%s-portrait.png" % (folder, base)
        copy(src, os.path.join(out, rel))
        index.append({"kind": "portrait", "zh": zh, "en": label, "pt": label, "folder": folder, "base": base, "files": {"portrait": rel}})

    # 4. world maps and loading screens
    maps = list(csv.DictReader(open(os.path.join(dump, "text/maps.csv"), encoding="utf-8")))
    seen = set()
    for m in maps:
        wm = m.get("world_map")
        if not wm or wm in seen:
            continue
        src = os.path.join(dump, "images", wm) if not wm.startswith("images/") else os.path.join(dump, wm)
        if not os.path.exists(src):
            src = os.path.join(dump, "images/surfaces/maps/worldmaps", os.path.basename(wm))
        if not os.path.exists(src):
            continue
        seen.add(wm)
        name = m.get("name_pt") or m.get("name_en") or m["map_code"]
        base = namer.take("world-maps", slug(m.get("name_en") or name) + "-" + m["map_code"], "map:" + wm)
        rel = "world-maps/%s.png" % base
        copy(src, os.path.join(out, rel))
        index.append({"kind": "world-map", "zh": m.get("name_zh", ""), "en": m.get("name_en", ""), "pt": name, "map_code": m["map_code"],
                      "folder": "world-maps", "base": base, "files": {"map": rel}})
    bg = os.path.join(dump, "images/surfaces/background")
    for f in sorted(os.listdir(bg)):
        if f.startswith("loading") and f.endswith(".png"):
            base = f.split(".")[0].replace("_", "-")
            rel = "loading-screens/%s.png" % base
            copy(os.path.join(bg, f), os.path.join(out, rel))
            index.append({"kind": "loading-screen", "zh": "", "en": base, "pt": base, "folder": "loading-screens", "base": base,
                          "files": {"image": rel}})

    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"folders": PT_FOLDER, "items": index}, f, ensure_ascii=False, indent=1)
    shutil.copy2(os.path.join(out, "index.json"), os.path.join(dump, "text/gallery_index.json"))
    with open(os.path.join(out, "README.md"), "w", encoding="utf-8") as f:
        f.write("# Saint Seiya Online - galeria de modelos e imagens\n\n"
                "Renders 3D (frente, lado e costas, pose T) de todos os personagens, Armaduras, NPCs, monstros e objetos do cliente "
                "Saint Seiya Online (Seiya Reborn), feitos com Blender a partir dos arquivos .ski do jogo, mais os cartões do Álbum, "
                "retratos, mapas e telas de carregamento do próprio jogo. Uma pasta por facção, nomes em inglês (kebab-case) como na "
                "biblioteca Saint Seiya Cloth Schemes; `index.json` traz o nome chinês original, o nome em português e a origem de cada arquivo.\n\n")
        for k, v in PT_FOLDER.items():
            n = sum(1 for i in index if i["folder"] == k)
            if n:
                f.write("- `%s/` - %s (%d itens)\n" % (k, v, n))
        f.write("\nGerado por `angelica/render/organize.py` do repositório games-extractor.\n")
    counts = {}
    for i in index:
        counts[i["folder"]] = counts.get(i["folder"], 0) + 1
    print("%d rendered characters, %d index entries" % (n_jobs, len(index)))
    for k, v in sorted(counts.items()):
        print("  %-20s %d" % (k, v))


if __name__ == "__main__":
    main()
