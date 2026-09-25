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
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "story"))
from names import translate, slug, load_game_names  # noqa: E402
from story_config import CARDS, PORTRAITS, LIB_OFFICIAL  # noqa: E402

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
    "videos": "Vídeos", "video-frames": "Quadros dos vídeos", "music": "Músicas", "voice": "Vozes", "concept-art": "Arte conceitual oficial", "press": "Imprensa (CavZodiaco)",
    "cloth-objects": "Armaduras em forma de objeto (totens e urnas)", "site-art": "Arte conceitual dos sites",
    "ui-art": "Arte 2D do jogo (interface, ícones, login)", "aerial": "Vistas aéreas dos mapas", "sky": "Céus (skyboxes)",
    "cursors": "Cursores", "notes-captures": "Capturas das Notas de Pesquisa",
}
# 2D art copied whole, keeping the game's own folder structure (Chinese names): source folder under images/ -> sub-folder
UI_ART = [("surfaces", "Interface (surfaces)"), ("icons", "Ícones"), ("flash", "Login e criação de personagem (flash)")]
# folder names used by the first version of the gallery (English); removed when found
OLD_FOLDERS = ["athena-saints", "hades-specters", "poseidon-mariners", "odin-god-warriors", "odin-blue-warriors", "lamech-servants",
               "zeus-olympians", "others", "npcs", "pets", "monsters", "artifacts", "skill-effects", "scenery-and-props", "cutscene-props",
               "world-maps", "loading-screens"]
VIEW_PT = {"front": "frente", "side": "lado", "back": "costas"}
SEX_PT = {"male": "masc", "female": "fem"}
VIDEOS = {  # file stem -> (pt title, zh)
    "login": ("Abertura (tela de login)", ""), "login_cn": ("Abertura (versão chinesa)", ""), "logo": ("Logotipo", ""),
    "last_saint_war": ("A última Guerra Santa (introdução)", ""), "last_saint_war_cn": ("A última Guerra Santa (versão chinesa)", ""),
    "prof02": ("Apresentação de classe: Pégaso (provável)", ""), "prof03": ("Apresentação de classe: Cisne (provável)", ""), "prof04": ("Apresentação de classe: Dragão (provável)", ""),
    "prof05": ("Apresentação de classe: Andrômeda (provável)", ""), "prof06": ("Apresentação de classe: Fênix (provável)", ""), "prof07": ("Apresentação de classe: Dragão Marinho (provável)", ""), "prof08": ("Apresentação de classe: Wyrm (provável)", ""),
    "一辉vs基鲁提": ("Ikki contra Guilty", "一辉vs基鲁提"), "一辉夺圣衣": ("Ikki toma a Armadura", "一辉夺圣衣"), "奥路菲vs三头犬": ("Orfeu contra Cérbero", "奥路菲vs三头犬"),
    "星矢vs卡西欧士": ("Seiya contra Cássios", "星矢vs卡西欧士"), "星矢vs莎尔娜": ("Seiya contra Shina", "星矢vs莎尔娜"), "紫龙vs英仙座": ("Shiryu contra Perseu", "紫龙vs英仙座"),
    "紫龙vs迪斯马斯克": ("Shiryu contra Máscara da Morte", "紫龙vs迪斯马斯克"), "艾欧罗斯vs修罗": ("Aioros contra Shura", "艾欧罗斯vs修罗"),
}
# concept art: file name (in the concept dir) -> (pt title, identification note)
CONCEPT = {
    "saint-seiya-online-xzsds09.jpg": ("Arte conceitual: Armadura azul com nadadeiras e elmo de chifres, versão feminina", "folha 09 da série 圣衣设定; Armadura não identificada"),
    "saint-seiya-online-xzsds15 (maybe Tornado or Cerberus).jpg": ("Arte conceitual: Armadura vermelha com totem de garras, versão feminina", "folha 15 da série 圣衣设定; Armadura não identificada"),
    "saint-seiya-online-xzsds16 (maybe Tornado or Cerberus).jpg": ("Arte conceitual: Armadura vermelha com totem de garras, versão masculina", "folha 16 da série 圣衣设定; mesma Armadura da folha anterior"),
}
WANMEI_ORIGINAL = {  # official "原画" (concept paintings) of the seiya.wanmei.com gallery, by file id
    "10151358144664371": "Cachoeira de Rozan (Cinco Picos Antigos)", "10151358144819035": "Vulcão da Ilha da Rainha da Morte",
    "10151358145450054": "Montanhas do Santuário", "10151358145823801": "Templo do Santuário", "10151358145914288": "Relógio de Fogo das Doze Casas",
    "10151358145943497": "Castelo de Hades (Heinstein)", "10151358145994204": "Coliseu Graad",
}


def has(name, words):
    return any(w in name for w in words)


def classify(job):
    name = job["name"]
    if job["category"] == "object":
        return "cloth-objects"
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
    ap.add_argument("--concept-dir", help="folder with extra concept-art files (e.g. the xzsds scans)")
    ap.add_argument("--library", help="root of the Saint Seiya Cloth Schemes library (official game images listed in story_config.LIB_OFFICIAL)")
    ap.add_argument("--sites-dir", help="folder with one sub-folder per web source (web/sites) of concept art collected from other sites")
    ap.add_argument("--videos-dir", help="write the videos to this folder instead of <out>/Vídeos (absolute paths in the index); their frames stay in the gallery, in Quadros dos vídeos")
    ap.add_argument("--music-dir", help="write the music tracks and voice lines to <music-dir>/Músicas and <music-dir>/Vozes instead of the gallery; index paths become absolute")
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
        key = classify(job)
        folder = PT_FOLDER[key]
        base = slug(t["pt"]) or slug(t["en"])
        sex = ""
        if job["category"] == "player":
            sex = job["group"]  # male / female
            base = "%s-%s" % (base, SEX_PT[sex])
        base = namer.take(folder, base, job["id"])
        files = {}
        for view in VIEWS:
            src = os.path.join(jdir, view + ".png")
            if os.path.exists(src):
                rel = "%s/%s-%s.png" % (folder, base, VIEW_PT[view])
                copy(src, os.path.join(out, rel))
                files[view] = rel
        if files:
            n_jobs += 1
            index.append({"kind": "render", "job": job["id"], "category": job["category"], "group": job["group"], "sex": sex,
                          "zh": job["name"], "en": t["en"], "pt": t["pt"], "folder": folder, "folder_key": key, "base": base, "files": files,
                          "pieces": job.get("pieces", [])})

    # 2. album cards
    pb = os.path.join(dump, "images/surfaces/res/photobook")
    for zh, (pt, group) in CARDS.items():
        src = os.path.join(pb, zh + ".dds.png")
        if not os.path.exists(src):
            continue
        key = card_folder(group)
        folder = PT_FOLDER[key]
        t = translate(zh, game_names)
        base = namer.take(folder, slug(pt), "card:" + zh)
        rel = "%s/%s-cartao-do-album.png" % (folder, base)
        copy(src, os.path.join(out, rel))
        index.append({"kind": "album-card", "zh": zh, "en": t["en"], "pt": pt, "group": group, "folder": folder, "folder_key": key, "base": base,
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
        key = portrait_folder(zh)
        folder = PT_FOLDER[key]
        base = namer.take(folder, slug(label), "portrait:" + zh)
        rel = "%s/%s-retrato.png" % (folder, base)
        copy(src, os.path.join(out, rel))
        index.append({"kind": "portrait", "zh": zh, "en": label, "pt": label, "folder": folder, "folder_key": key, "base": base, "files": {"portrait": rel}})

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
        folder = PT_FOLDER["world-maps"]
        base = namer.take(folder, slug(name) + "-" + m["map_code"], "map:" + wm)
        rel = "%s/%s-mapa.png" % (folder, base)
        copy(src, os.path.join(out, rel))
        index.append({"kind": "world-map", "zh": m.get("name_zh", ""), "en": m.get("name_en", ""), "pt": name, "map_code": m["map_code"],
                      "folder": folder, "folder_key": "world-maps", "base": base, "files": {"map": rel}})
    bg = os.path.join(dump, "images/surfaces/background")
    for f in sorted(os.listdir(bg)):
        if f.startswith("loading") and f.endswith(".png"):
            stem = f.split(".")[0]
            base = "tela-de-carregamento-" + stem.replace("loading_", "").replace("loading", "")
            folder = PT_FOLDER["loading-screens"]
            rel = "%s/%s.png" % (folder, base)
            copy(os.path.join(bg, f), os.path.join(out, rel))
            index.append({"kind": "loading-screen", "zh": "", "en": stem, "pt": "Tela de carregamento " + stem.replace("loading_", "").replace("loading", ""),
                          "folder": folder, "folder_key": "loading-screens", "base": base, "files": {"image": rel}})

    # 5. videos, music and voice lines (media_index.csv gives durations)
    media = {}
    mi = os.path.join(dump, "media_index.csv")
    if os.path.exists(mi):
        for r in csv.DictReader(open(mi, encoding="utf-8")):
            media[r["path"]] = r
    vd = os.path.join(dump, "videos/mp4")
    if os.path.isdir(vd):
        for f in sorted(os.listdir(vd)):
            stem = os.path.splitext(f)[0]
            pt, zh = VIDEOS.get(stem, (translate(stem, game_names)["pt"], stem if not stem.isascii() else ""))
            folder = PT_FOLDER["videos"]
            base = namer.take(folder, slug(pt), "video:" + f)
            if a.videos_dir:  # videos live outside the gallery (e.g. the Nextcloud Videos folder): absolute paths in the index
                vout, rel = a.videos_dir, os.path.join(a.videos_dir, base + ".mp4")
                frame = "%s/%s-quadro.jpg" % (PT_FOLDER["video-frames"], base)  # pictures stay in the (pictures-only) gallery
                os.makedirs(vout, exist_ok=True)
                os.makedirs(os.path.join(out, PT_FOLDER["video-frames"]), exist_ok=True)
                copy(os.path.join(vd, f), rel)
            else:
                rel = "%s/%s.mp4" % (folder, base)
                frame = "%s/%s-quadro.jpg" % (folder, base)
                copy(os.path.join(vd, f), os.path.join(out, rel))
            r = media.get("videos/mp4/" + f, {})
            files = {"video": rel}
            if not os.path.exists(os.path.join(out, frame)) and shutil.which("ffmpeg"):
                secs = float(r.get("seconds") or 0)
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(min(8, max(0, secs / 2))), "-i", os.path.join(vd, f), "-frames:v", "1",
                                os.path.join(out, frame)], check=False)
            if os.path.exists(os.path.join(out, frame)):
                files["frame"] = frame
            index.append({"kind": "video", "zh": zh, "en": stem, "pt": pt, "folder": folder, "folder_key": "videos", "base": base, "files": files,
                          "seconds": float(r.get("seconds") or 0), "width": r.get("width", ""), "height": r.get("height", ""), "source": f})
    md = os.path.join(dump, "music")
    if os.path.isdir(md):
        for root, _dirs, fs in os.walk(md):
            for f in sorted(fs):
                if not f.lower().endswith((".ogg", ".mp3", ".wav")):
                    continue
                relsrc = os.path.relpath(os.path.join(root, f), md)
                stem = os.path.splitext(f)[0]
                zh = stem if not stem.isascii() else ""
                pt = translate(stem, game_names)["pt"] if zh else stem
                if root != md:
                    pt = translate(os.path.basename(root), game_names)["pt"] + ": " + pt
                folder = PT_FOLDER["music"]
                base = namer.take(folder, slug(pt) or slug(stem), "music:" + relsrc)
                if a.music_dir:  # audio lives in the Nextcloud Music folder: absolute path in the index
                    rel = os.path.join(a.music_dir, folder, base + os.path.splitext(f)[1].lower())
                    copy(os.path.join(root, f), rel)
                else:
                    rel = "%s/%s%s" % (folder, base, os.path.splitext(f)[1].lower())
                    copy(os.path.join(root, f), os.path.join(out, rel))
                r = media.get("music/" + relsrc, {})
                index.append({"kind": "music", "zh": zh, "en": stem, "pt": pt, "folder": folder, "folder_key": "music", "base": base, "files": {"audio": rel},
                              "seconds": float(r.get("seconds") or 0), "source": relsrc})
    vo = os.path.join(dump, "voice")
    if os.path.isdir(vo):
        for sub in sorted(os.listdir(vo)):
            sd = os.path.join(vo, sub)
            if not os.path.isdir(sd):
                continue
            who = {"男a": "voz masculina", "女b": "voz feminina"}.get(sub, sub)
            for f in sorted(os.listdir(sd)):
                stem = os.path.splitext(f)[0]
                pt = translate(stem, game_names)["pt"] + " (" + who + ")"
                folder = PT_FOLDER["voice"]
                base = namer.take(folder, slug(pt), "voice:" + sub + "/" + f)
                if a.music_dir:
                    rel = os.path.join(a.music_dir, folder, base + os.path.splitext(f)[1].lower())
                    copy(os.path.join(sd, f), rel)
                else:
                    rel = "%s/%s%s" % (folder, base, os.path.splitext(f)[1].lower())
                    copy(os.path.join(sd, f), os.path.join(out, rel))
                r = media.get("voice/%s/%s" % (sub, f), {})
                index.append({"kind": "voice", "zh": stem, "en": "", "pt": pt, "folder": folder, "folder_key": "voice", "base": base, "files": {"audio": rel},
                              "seconds": float(r.get("seconds") or 0), "source": sub + "/" + f})

    # 6. official concept art (Diego's copies + the seiya.wanmei.com gallery fetched from the Wayback Machine)
    folder = PT_FOLDER["concept-art"]
    for src_dir in (a.concept_dir, os.path.join(dump, "web/wanmei/img")):
        if not src_dir or not os.path.isdir(src_dir):
            continue
        for f in sorted(os.listdir(src_dir)):
            if not f.lower().endswith((".jpg", ".png")):
                continue
            try:
                from PIL import Image
                Image.open(os.path.join(src_dir, f)).verify()
            except Exception:
                print("skipping unreadable image", f)
                continue
            fid = os.path.splitext(f)[0].split("_")[-1]
            if f in CONCEPT:
                pt, note = CONCEPT[f]
            elif f.startswith("original_"):
                pt, note = ("Arte conceitual oficial: " + WANMEI_ORIGINAL.get(fid, "cenário " + fid), "seiya.wanmei.com, galeria 原画 (arte original), identificação do local provável")
            elif f.startswith("wallpaper_"):
                pt, note = ("Papel de parede oficial " + fid, "seiya.wanmei.com, galeria 壁纸 (papéis de parede)")
            elif f.startswith("printscreen_"):
                pt, note = ("Captura de tela oficial " + fid, "seiya.wanmei.com, galeria 截图 (capturas de tela)")
            else:
                continue
            base = namer.take(folder, slug(pt), "concept:" + f)
            rel = "%s/%s%s" % (folder, base, os.path.splitext(f)[1].lower())
            copy(os.path.join(src_dir, f), os.path.join(out, rel))
            index.append({"kind": "concept-art", "zh": "", "en": f, "pt": pt, "note": note, "folder": folder, "folder_key": "concept-art", "base": base,
                          "files": {"image": rel}, "source": f})

    if a.library:
        for rel_src, (pt, note, key) in LIB_OFFICIAL.items():
            src = os.path.join(a.library, rel_src)
            if not os.path.exists(src):
                continue
            base = namer.take(folder, "biblioteca-" + slug(pt), "lib:" + rel_src)
            rel = "%s/%s%s" % (folder, base, os.path.splitext(rel_src)[1].lower())
            copy(src, os.path.join(out, rel))
            index.append({"kind": "concept-art", "zh": "", "en": rel_src, "pt": pt, "note": note + " (biblioteca Saint Seiya Cloth Schemes)", "site_key": key,
                          "folder": folder, "folder_key": "concept-art", "base": base, "files": {"image": rel}, "source": rel_src})

    if a.sites_dir and os.path.isdir(a.sites_dir):
        from story_config import SITE_ART_NOTES
        folder = PT_FOLDER["site-art"]
        for src_name in sorted(os.listdir(a.sites_dir)):
            sd = os.path.join(a.sites_dir, src_name)
            if not os.path.isdir(sd):
                continue
            for f in sorted(os.listdir(sd)):
                if not f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    continue
                try:
                    from PIL import Image
                    Image.open(os.path.join(sd, f)).verify()
                except Exception:
                    continue
                stem = os.path.splitext(f)[0]
                pt, note = SITE_ART_NOTES.get(stem, (stem.replace("_", " "), ""))
                base = namer.take(folder, slug(src_name + " " + pt), "site:" + src_name + "/" + f)
                rel = "%s/%s%s" % (folder, base, os.path.splitext(f)[1].lower())
                copy(os.path.join(sd, f), os.path.join(out, rel))
                index.append({"kind": "site-art", "zh": "", "en": stem, "pt": pt, "note": note, "site": src_name, "folder": folder, "folder_key": "site-art",
                              "base": base, "files": {"image": rel}, "source": src_name + "/" + f})

    # 7. press coverage (CavZodiaco articles collected by angelica/web/cavzodiaco.py)
    pj = os.path.join(dump, "web/cavzodiaco/articles.json")
    if os.path.exists(pj):
        folder = PT_FOLDER["press"]
        for art in json.load(open(pj, encoding="utf-8")):
            sub = "%s %s" % (art["date"], slug(art["title"])[:70])
            files = []
            for img in art["images"]:
                src = os.path.join(dump, "web/cavzodiaco/images", img)
                if not os.path.exists(src):
                    continue
                rel = "%s/%s/%s" % (folder, sub, img)
                copy(src, os.path.join(out, rel))
                files.append(rel)
            index.append({"kind": "press", "zh": "", "en": art["title"], "pt": art["title"], "date": art["date"], "url": art["url"],
                          "folder": folder + "/" + sub, "folder_key": "press", "base": sub, "files": {"images": files}, "n": art["n"]})

    # 8. every 2D picture of the client that is not a 3D texture: the whole interface art (surfaces, icons, flash
    #    login screens) with the game's folder structure, the aerial view of each map, the sky boxes and the cursors
    folder = PT_FOLDER["ui-art"]
    for src_sub, dst_sub in UI_ART:
        sd = os.path.join(dump, "images", src_sub)
        if not os.path.isdir(sd):
            continue
        for root, _dirs, fs in os.walk(sd):
            for f in sorted(fs):
                if not f.lower().endswith(".png"):
                    continue
                relsrc = os.path.relpath(os.path.join(root, f), sd)
                rel = "%s/%s/%s" % (folder, dst_sub, relsrc.replace(".dds.png", ".png").replace(".tga.png", ".png").replace(".bmp.png", ".png").replace(".jpg.png", ".png"))
                copy(os.path.join(root, f), os.path.join(out, rel))
                index.append({"kind": "ui-art", "folder": folder + "/" + dst_sub, "folder_key": "ui-art", "files": {"image": rel}, "source": "images/%s/%s" % (src_sub, relsrc)})
    mapnames = {}
    mc = os.path.join(dump, "text/maps.csv")
    if os.path.exists(mc):
        for r in csv.DictReader(open(mc, encoding="utf-8")):
            if r.get("map_code") and r["map_code"] not in mapnames:
                mapnames[r["map_code"]] = r.get("name_pt") or r.get("name_en") or r["map_code"]
    ld = os.path.join(dump, "images/loddata")
    folder = PT_FOLDER["aerial"]
    if os.path.isdir(ld):
        for code in sorted(os.listdir(ld)):
            for tod, tod_pt in (("day", "dia"), ("night", "noite")):
                lv = os.path.join(ld, code, "1024", tod, "level-0") if code == "birdviews" else os.path.join(ld, code, "birdviews/1024", tod, "level-0")
                if not os.path.isdir(lv):
                    continue
                tiles = sorted(f for f in os.listdir(lv) if f.endswith(".png"))
                for i, f in enumerate(tiles):
                    name = mapnames.get(code, "mapa geral" if code == "birdviews" else code)
                    base = "%s (%s) - %s%s" % (re.sub(r'[\\/:*?"<>|]', "-", name), code, tod_pt, " - parte %d" % (i + 1) if len(tiles) > 1 else "")
                    rel = "%s/%s.png" % (folder, base)
                    copy(os.path.join(lv, f), os.path.join(out, rel))
                    index.append({"kind": "aerial", "pt": "%s (%s), %s" % (name, code, tod_pt) + (", parte %d" % (i + 1) if len(tiles) > 1 else ""),
                                  "map": code, "folder": folder, "folder_key": "aerial", "files": {"image": rel}, "source": os.path.relpath(os.path.join(lv, f), dump)})
    sk = os.path.join(dump, "images/textures/sky")
    folder = PT_FOLDER["sky"]
    if os.path.isdir(sk):
        for root, _dirs, fs in os.walk(sk):
            for f in sorted(fs):
                if f.lower().endswith(".png"):
                    relsrc = os.path.relpath(os.path.join(root, f), sk)
                    rel = "%s/%s" % (folder, re.sub(r"\.(dds|tga|bmp)\.png$", ".png", relsrc))
                    copy(os.path.join(root, f), os.path.join(out, rel))
                    index.append({"kind": "sky", "folder": folder, "folder_key": "sky", "files": {"image": rel}, "source": "images/textures/sky/" + relsrc})
    cd = os.path.join(dump, "cursors")
    folder = PT_FOLDER["cursors"]
    if os.path.isdir(cd):
        from PIL import Image
        for f in sorted(os.listdir(cd)):
            try:
                im = Image.open(os.path.join(cd, f))  # .cur, and the first frame of an animated .ani
            except Exception:
                continue
            rel = "%s/%s.png" % (folder, f.replace(".", "-"))
            os.makedirs(os.path.join(out, folder), exist_ok=True)
            if not os.path.exists(os.path.join(out, rel)):
                im.convert("RGBA").save(os.path.join(out, rel))
            index.append({"kind": "cursor", "folder": folder, "folder_key": "cursors", "files": {"image": rel}, "source": "cursors/" + f})
    nd = os.path.join(dump, "web/notas")
    folder = PT_FOLDER["notes-captures"]
    if os.path.isdir(nd):
        for f in sorted(os.listdir(nd)):
            if f.lower().endswith((".png", ".jpg", ".jpeg")):
                rel = "%s/%s" % (folder, f)
                copy(os.path.join(nd, f), os.path.join(out, rel))
                index.append({"kind": "notes-capture", "pt": os.path.splitext(f)[0].replace("-", " "), "folder": folder, "folder_key": "notes-captures",
                              "files": {"image": rel}, "source": "web/notas/" + f})

    # remove files from earlier runs that are no longer in the index (renamed or reclassified)
    keep = set()
    for it in index:
        for v in it["files"].values():
            for rel in (v if isinstance(v, list) else [v]):
                keep.add(os.path.join(out, rel))
    removed = 0
    for folder in OLD_FOLDERS:
        d = os.path.join(out, folder)
        if os.path.isdir(d):
            shutil.rmtree(d)
            removed += 1
    for folder in set(PT_FOLDER.values()) | {i["folder"] for i in index}:
        d = os.path.join(out, folder)
        if not os.path.isdir(d):
            continue
        for root, _dirs, fs in os.walk(d):
            for f in fs:
                fp = os.path.join(root, f)
                if fp not in keep:
                    os.remove(fp)
                    removed += 1
        for root, dirs, fs in os.walk(d, topdown=False):
            if not os.listdir(root):
                os.rmdir(root)
    if removed:
        print("removed %d stale files/folders" % removed)
    # the gallery folder holds only pictures: index and README go to the dump's text/ folder
    for stale in ("index.json", "README.md"):
        if os.path.exists(os.path.join(out, stale)):
            os.remove(os.path.join(out, stale))
    with open(os.path.join(dump, "text/gallery_index.json"), "w", encoding="utf-8") as f:
        json.dump({"folders": PT_FOLDER, "items": index}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(dump, "text/gallery_README.md"), "w", encoding="utf-8") as f:
        f.write("# Saint Seiya Online - Galeria de Imagens\n\n"
                "Organizada como a seção \"Galeria de modelos 3D\" do livro *Saint Seiya Online - Story*: uma pasta por facção ou tipo de conteúdo, "
                "nomes em português. Renders 3D (frente, lado e costas, pose T) de todos os personagens, Armaduras, NPCs, monstros e objetos do cliente "
                "Saint Seiya Online (Seiya Reborn), feitos com Blender a partir dos arquivos .ski do jogo; cartões do Álbum, retratos, mapas e telas de "
                "carregamento do próprio jogo; os vídeos, as músicas e as vozes do cliente; a arte conceitual oficial (seiya.wanmei.com, via Wayback Machine) "
                "e as imagens da cobertura do CavZodiaco.com.br, por matéria. `index.json` traz, para cada arquivo, o nome chinês original, o nome em "
                "português e a origem.\n\n")
        for k, v in PT_FOLDER.items():
            n = sum(1 for i in index if i.get("folder_key") == k)
            if n:
                f.write("- `%s/` - %d itens\n" % (v, n))
        f.write("\nGerado por `angelica/render/organize.py` do repositório games-extractor.\n")
    counts = {}
    for i in index:
        counts[i["folder_key"]] = counts.get(i["folder_key"], 0) + 1
    print("%d rendered characters, %d index entries" % (n_jobs, len(index)))
    for k, v in sorted(counts.items()):
        print("  %-20s %d" % (k, v))


if __name__ == "__main__":
    main()
