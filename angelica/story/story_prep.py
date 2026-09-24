#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Monta story.json para o documento 'Saint Seiya Online - Story' a partir do dump em ~/Downloads/Seiya."""
import os, sys, re, json, csv, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from story_config import PARTS, SIDE_GROUPS, SYSTEM_PATTERNS, CHAPTERS, REGION_IMAGES
OUT = os.path.expanduser("~/Downloads/Seiya"); T = OUT + "/text"
NOTES = "/home/diego/Nextcloud/Documents/Reading/Mangás que vou fazer/Saint Seiya Online"
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
used = set(); sigs = set()
def collect(ranges, need_desc=True):
    out = []
    for lo, hi in ranges:
        for i in range(lo, hi + 1):
            q = byid.get(i)
            if not q or i in used or is_system(q): continue
            if not q.get("descript") and not (q["delv"].get("windows") or q["award"].get("windows") or q["unq"].get("windows")): continue
            sig = (q.get("name"), q.get("descript"), json.dumps(q["delv"], ensure_ascii=False), json.dumps(q["award"], ensure_ascii=False))
            if sig in sigs: used.add(i); continue
            sigs.add(sig); used.add(i); out.append(qrec(q))
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
    if not q.get("descript") and not (q["delv"].get("windows") or q["award"].get("windows") or q["unq"].get("windows")): continue
    sig = (q.get("name"), q.get("descript"), json.dumps(q["delv"], ensure_ascii=False), json.dumps(q["award"], ensure_ascii=False))
    if sig in sigs: continue
    sigs.add(sig); used.add(q["id"])
    blk = q["id"] // 1000 * 1000
    rest.setdefault(blk, []).append(qrec(q))
others = [{"block": f"IDs {k}–{k+999}", "quests": v} for k, v in sorted(rest.items())]
tests = sum(1 for q in Q if is_system(q))

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
CARDS = {
 "天马座星矢": ("Seiya de Pégaso", "bronze"), "天龙座紫龙": ("Shiryu de Dragão", "bronze"), "白鸟座冰河": ("Hyoga de Cisne", "bronze"), "仙女座瞬": ("Shun de Andrômeda", "bronze"), "凤凰座一辉": ("Ikki de Fênix", "bronze"),
 "天狼座那智": ("Nachi de Lobo", "bronze"), "大熊座檄": ("Geki de Urso", "bronze"), "幼狮座蛮": ("Ban de Leão Menor", "bronze"), "水蛇座市": ("Ichi de Hidra", "bronze"), "独角兽座邪武": ("Jabu de Unicórnio", "bronze"), "变色龙座珍妮": ("June de Camaleão", "bronze"),
 "白羊座穆": ("Mu de Áries", "ouro"), "金牛座阿鲁迪巴": ("Aldebaran de Touro", "ouro"), "双子座撒加": ("Saga de Gêmeos", "ouro"), "巨蟹座迪斯马克斯": ("Máscara da Morte de Câncer", "ouro"), "狮子座艾欧里亚": ("Aioria de Leão", "ouro"), "处女座沙加": ("Shaka de Virgem", "ouro"),
 "天秤座童虎": ("Dohko de Libra", "ouro"), "天蝎座米罗": ("Miro de Escorpião", "ouro"), "射手座艾欧罗斯": ("Aioros de Sagitário", "ouro"), "摩羯座修罗": ("Shura de Capricórnio", "ouro"), "水瓶座卡妙": ("Camus de Aquário", "ouro"), "双鱼座阿布罗迪": ("Afrodite de Peixes", "ouro"), "教皇史昂": ("Shion, o Grande Mestre", "ouro"),
 "天鹰座魔铃": ("Marin de Águia", "prata"), "蛇夫座莎尔娜": ("Shina de Cobra", "prata"), "天琴座奥路菲": ("Orfeu de Lira", "prata"),
 "海皇朱利安·索罗": ("Julian Solo (Poseidon)", "marina"), "海皇海龙加隆": ("Kanon de Dragão Marinho", "marina"), "海皇海马拜安": ("Baian de Cavalo Marinho", "marina"), "海皇六圣兽伊奥": ("Io de Skilla", "marina"), "海皇海皇子克修拉": ("Krishna de Crisaor", "marina"), "海皇海魔女苏兰特": ("Sorento de Sirene", "marina"), "海皇魔鬼鱼艾尔扎克": ("Isaac de Kraken", "marina"), "海皇海怪卡撒": ("Kasa de Lymnades", "marina"), "海皇美人鱼狄迪思": ("Thetis de Sereia", "marina"),
 "冥天猛星拉达曼迪斯": ("Radamanthys de Wyvern", "espectro"), "冥天贵星米诺斯": ("Minos de Griffon", "espectro"), "冥天雄星艾亚哥斯": ("Aiacos de Garuda", "espectro"), "冥潘多拉": ("Pandora", "espectro"), "冥死神达拿都斯": ("Thanatos", "espectro"), "冥睡神修普诺斯": ("Hypnos", "espectro"),
 "黑暗天马": ("Pégaso Negro", "negro"), "黑暗天龙": ("Dragão Negro", "negro"), "黑暗白鸟": ("Cisne Negro", "negro"), "黑暗仙女": ("Andrômeda Negro", "negro"), "黑暗强戈": ("Jango", "negro"),
 "普城户光政": ("Mitsumasa Kido", "outros"), "普辰巳德丸": ("Tatsumi", "outros"), "普美穗": ("Mino", "outros"), "普春丽": ("Shunrei", "outros"), "普贵鬼": ("Kiki", "outros"), "普卡西欧士": ("Cássios", "outros"), "普基鲁提": ("Guilty", "outros"), "普艾丝美拉达": ("Esmeralda", "outros"), "普星华": ("Seika", "outros"), "雅典娜": ("Athena (Saori Kido)", "outros"), "普冰之国公主瓦尔基里": ("Valquíria, princesa do País do Gelo", "outros"), "普圣域美人鱼": ("Sereia do Santuário", "outros"), "普东西伯利亚居民女": ("Moradora da Sibéria Oriental", "outros"),
 "天马座": ("Pégaso", "arm_bronze"), "天龙座": ("Dragão", "arm_bronze"), "白鸟座": ("Cisne", "arm_bronze"), "仙女座": ("Andrômeda", "arm_bronze"), "凤凰座": ("Fênix", "arm_bronze"),
 "盾牌座": ("Escudo", "arm_bronze"), "六分仪座": ("Sextante", "arm_bronze"), "箭鱼座": ("Volans (Peixe-Voador)", "arm_bronze"), "巨蛇座": ("Serpente", "arm_bronze"), "南鱼座": ("Peixe Austral", "arm_bronze"), "变色龙座": ("Camaleão", "arm_bronze"), "海蛇座": ("Hidra (macho)", "arm_bronze"), "北冕座": ("Coroa Boreal", "arm_bronze"), "南十字座": ("Cruzeiro do Sul", "arm_bronze"), "船尾座": ("Popa", "arm_bronze"), "鹿豹座": ("Rena / Girafa (Camelopardalis)", "arm_bronze"), "南冕座": ("Coroa Austral", "arm_bronze"), "天兔座": ("Lebre", "arm_bronze"), "波江座": ("Erídano", "arm_bronze"), "时钟座": ("Relógio (Horologium)", "arm_bronze"), "皇女座": ("Imperatriz (Nu)", "arm_bronze"), "银莺座": ("Oriolus de Prata", "arm_bronze"), "猎豹座": ("Guepardo", "arm_bronze"), "铜鱼座": ("Coreius", "arm_bronze"),
 "天琴座": ("Lira", "arm_prata"), "御夫座": ("Auriga", "arm_prata"), "仙王座": ("Cefeu", "arm_prata"), "网罟座": ("Rede (Reticulum)", "arm_prata"), "天鹰座": ("Águia", "arm_prata"), "三角座": ("Triângulo", "arm_prata"), "武仙座": ("Hércules", "arm_prata"), "乌鸦座": ("Corvo", "arm_prata"), "半人马座": ("Centauro", "arm_prata"), "天炉座": ("Fornalha", "arm_prata"), "罗盘座": ("Bússola", "arm_prata"), "鲸鱼座": ("Baleia", "arm_prata"), "英仙座": ("Perseu", "arm_prata"), "仙后座": ("Cassiopeia", "arm_prata"), "孔雀座": ("Pavão", "arm_prata"), "蜥蜴座": ("Lagarto", "arm_prata"), "巨爵座": ("Taça", "arm_prata"), "地狱犬座": ("Cérbero", "arm_prata"), "天鹤座": ("Grou", "arm_prata"), "祭坛座": ("Altar", "arm_prata"), "大犬座": ("Cão Maior ('Duquesa' na localização)", "arm_prata"), "剑鱼座": ("Dourado (Dorado)", "arm_prata"), "天幕座": ("Atrium", "arm_prata"), "鬼主座": ("Mestre dos Fantasmas", "arm_prata"), "天坦座": ("Titã (Tornado)", "arm_prata"), "猎犬座": ("Cães de Caça", "arm_prata"), "天箭座": ("Sagita", "arm_prata"), "海魔女座": ("Sirene (Escama)", "escama"), "海龙座": ("Dragão Marinho (Escama)", "escama"), "莲花座": ("Lótus", "arm_prata"),
 "白羊圣衣": ("Áries", "arm_ouro"), "金牛圣衣": ("Touro", "arm_ouro"), "双子圣衣": ("Gêmeos", "arm_ouro"), "巨蟹圣衣": ("Câncer", "arm_ouro"), "狮子圣衣": ("Leão", "arm_ouro"), "处女圣衣": ("Virgem", "arm_ouro"), "天秤圣衣": ("Libra", "arm_ouro"), "天蝎圣衣": ("Escorpião", "arm_ouro"), "射手圣衣": ("Sagitário", "arm_ouro"), "山羊圣衣": ("Capricórnio", "arm_ouro"), "水瓶圣衣": ("Aquário", "arm_ouro"), "双鱼圣衣": ("Peixes", "arm_ouro"),
 "神白羊座": ("Áries", "arm_divina"), "神金牛座": ("Touro", "arm_divina"), "神双子座": ("Gêmeos", "arm_divina"), "神巨蟹座": ("Câncer", "arm_divina"), "神狮子座": ("Leão", "arm_divina"), "神处女座": ("Virgem", "arm_divina"), "神天秤座": ("Libra", "arm_divina"), "神天平座": ("Libra (variante)", "arm_divina"), "神天蝎座": ("Escorpião", "arm_divina"), "神射手座": ("Sagitário", "arm_divina"), "神摩羯座": ("Capricórnio", "arm_divina"), "神水瓶座": ("Aquário", "arm_divina"), "神双鱼座": ("Peixes", "arm_divina"),
 "天猛星": ("Wyvern (Estrela Celeste da Fúria)", "sapuris"), "天贵星": ("Griffon (Estrela Celeste da Nobreza)", "sapuris"), "天雄星": ("Garuda (Estrela Celeste do Heroísmo)", "sapuris"), "天哭星": ("Harpia (Estrela Celeste da Lamentação)", "sapuris"), "天英星": ("Balron (Estrela Celeste da Excelência)", "sapuris"), "天间星": ("Aqueronte (Estrela Celeste do Espaço)", "sapuris"), "天魔星": ("Alraune (Estrela Celeste da Bruxaria)", "sapuris"), "天捷星": ("Basilisco (Estrela Celeste da Vitória)", "sapuris"), "天兽星": ("Esfinge (Estrela Celeste da Besta)", "sapuris"),
 "群星之地": ("Terra das Constelações", "lugar"), "圣域": ("Santuário", "lugar"), "银河竞技场": ("Coliseu Graad", "lugar"), "庐山": ("Rozan", "lugar"), "遗忘之路": ("Estrada Esquecida", "lugar"), "死亡皇后岛": ("Ilha da Rainha da Morte", "lugar"), "东西伯利亚": ("Sibéria Oriental", "lugar"), "亚特兰蒂斯": ("Atlântida", "lugar"), "仙女岛": ("Ilha de Andrômeda", "lugar"), "哈迪斯城": ("Castelo de Hades", "lugar"), "冥界地狱": ("Submundo", "lugar"), "阿提卡战场": ("Ruínas de Ática", "lugar"),
}
pb_dir = OUT + "/images/surfaces/res/photobook"; card_files = {f.split(".")[0]: "images/surfaces/res/photobook/" + f for f in os.listdir(pb_dir)}
cards = []
for zh, (ptn, grp) in CARDS.items():
    f = card_files.get(zh)
    if f: cards.append({"zh": zh, "pt": ptn, "group": grp, "file": f})
unmapped = [z for z in card_files if z not in CARDS]
# retratos principais (surfaces/res/portrait)
PORTRAITS = {"Seiya": "星矢", "Shiryu": "紫龙便装", "Hyoga": "冰河水瓶版", "Shun": "瞬", "Ikki": "一辉", "Saori Kido": "城户纱织", "Athena": "雅典娜", "Kiki": "贵鬼", "Shunrei": "春丽", "Cássios": "卡西欧士", "Marin": "魔铃", "Shina": "莎尔娜", "Dohko": "童虎",
 "Kanon": "加隆", "Julian Solo": "朱利安", "Pandora": "潘多拉", "Hades": "冥王哈迪斯", "Poseidon": "海皇波塞冬", "Guilty": "基鲁提", "Esmeralda": "艾丝美拉达", "Jango": "强戈", "Orfeu": "奥路菲", "Grande Mestre": "教皇", "Shion": "白羊座史昂", "Miro": "天蝎座米罗", "Aioros": "射手座艾俄洛斯",
 "Lei-Hu": "庐山雷虎", "Rodório": "初代天马英灵", "Alex": "圣斗士学员阿历克斯", "Eide": "圣斗士男学员少年艾德", "Aiya": "圣域圣斗士女学员艾亚", "Alexer": "亚雷库萨", "Natássia": "娜塔莎", "Valquíria": "冰之国公主瓦尔基里", "Isaac": "北海巨妖艾尔扎克便衣", "Sorento": "海将军海魔女苏兰特", "Baian": "海将军海马拜安", "Krishna": "海将军海皇子克修拉",
 "Radamanthys": "冥斗士天猛星拉达曼提斯", "Minos": "冥斗士天贵星米洛斯", "Thanatos": "死神", "Hypnos": "睡神", "Perséfone": "冥后", "Eurídice": "尤丽缇丝", "Pégaso Negro": "黑暗天马座", "Dragão Negro": "黑暗天龙座", "Cisne Negro": "黑暗白鸟座", "Andrômeda Negro": "黑暗仙女", "Fênix Negro": "黑暗凤凰座",
 "Nachi": "白银天琴座", "Mitsumasa Kido": "城户光政", "Seika": "星华", "Zeros": "冥斗士地奇星赛洛斯", "Myu": "冥斗士地妖星缪", "Gerald": "冥斗士地囚星杰拉尔德", "Loki": "洛基", "Apolo": "太阳神阿波罗", "Eros": "爱神之子爱洛斯", "Afrodite (deusa)": "爱神阿芙洛狄忒", "Siegfried": "天枢星双头龙座齐格弗里德", "Hagen": "天璇星八脚战马哈根", "Alberich": "天权星阿鲁贝利亚", "Fenrir": "玉衡星北极狼菲利路", "Syd": "开阳星剑齿虎希度", "Mime": "摇光星米伊美", "Sísifo": "掷铁饼者", "Lamech": "虚无之神拉蒙斯", "Li-Yun": "庐山李云异化", "Julian (Castelo de Hades)": "哈迪斯城幸存者男尤里安版", "Lei-Hu (mutado)": "庐山雷虎变异", "Alex (Sapuris)": "圣斗士学员阿历克斯冥衣版", "Acer (máscara)": "死亡皇后岛学员枫戴面具", "Acer": "皇后岛学员枫", "Valquíria (guerreira)": "冰之国公主瓦尔基里女武神版", "Eide (mutado)": "圣斗士男学员少年艾德异化", "Loki": "邪神洛基", "Kanon (Sapuris)": "加隆灰发", "Seiya (Sagitário)": "星矢射手版", "Shina (Armadura)": "莎尔娜圣衣版", "Athena (Armadura Divina)": "雅典娜神圣衣", "Saori (vestido)": "城户纱织晚礼服", "Shion (alma)": "白羊座史昂灵魂状态", "Shion ressuscitado": "复生的白羊座史昂", "Ikki criança": "一辉幼年抱着瞬", "Seiya criança": "幼年星矢", "Pandora criança": "潘多拉幼年抱哈迪斯", "Julian Solo (mendigo)": "朱利安穷人", "Máscara da Morte ressuscitado": "复生的黄金圣斗士巨蟹座迪斯马斯克", "Shura ressuscitado": "复生的黄金圣斗士摩羯座修罗", "Camus ressuscitado": "复生的黄金圣斗士水瓶座卡妙", "Afrodite ressuscitado": "复生的黄金圣斗士双鱼座阿布罗狄", "Lune": "天英星路尼法袍", "Rock": "冥斗士天角星洛克", "Iwan": "冥斗士天败星伊万", "Laimi": "冥斗士地伏星莱米触手", "Sirene (Sorento)": "海魔女苏兰特便装", "Io de Skilla": "海将军六圣兽", "Kasa": "海斗士北海巨妖", "Julian Solo (Poseidon)": "【海皇】朱利安·梭罗", }
port_dir = OUT + "/images/surfaces/res/portrait"; port_files = {f.split(".")[0]: "images/surfaces/res/portrait/" + f for f in os.listdir(port_dir)}
head_dir = OUT + "/images/surfaces/res/head"; head_files = {f.split(".")[0]: "images/surfaces/res/head/" + f for f in os.listdir(head_dir)}
PORTRAITS["Sillas"] = "火山之撒里诺"
portraits = {k: (port_files.get(v) or head_files.get(v)) for k, v in PORTRAITS.items() if v in port_files or v in head_files}
# NPCs nomeados (para o índice): zh -> pt
npc = collections.OrderedDict()
for k, z, t in colkv("pt-BR", "data_npc"):
    if k.endswith("_name") and t and z: npc.setdefault(z, t)
mon = collections.OrderedDict()
for k, z, t in colkv("pt-BR", "data_monster"):
    if k.endswith("_name") and t and z: mon.setdefault(z, t)
# 7. armaduras: renders (pasta Cloths do Diego) e screenshots (pasta Saints)
CONST_EN = {"andromeda": "Andrômeda", "aquarius": "Aquário", "aquila": "Águia", "aries": "Áries", "atrium": "Atrium", "auriga": "Auriga", "cancer": "Câncer", "canes-venatici": "Cães de Caça", "capricornus": "Capricórnio", "cassiopeia": "Cassiopeia", "centaurus": "Centauro", "cepheus": "Cefeu", "cerberus": "Cérbero", "cetus": "Baleia", "chamaeleon": "Camaleão", "corona-australis": "Coroa Austral", "corona-borealis": "Coroa Boreal", "corvus": "Corvo", "crux": "Cruzeiro do Sul", "cygnus": "Cisne", "delphinus": "Delfim", "dorado": "Dourado", "draco": "Dragão", "eridanus": "Erídano", "fornax": "Fornalha", "gemini": "Gêmeos", "ghosts-master": "Mestre dos Fantasmas", "heracles": "Hércules", "hydrus": "Hidra (macho)", "lacerta": "Lagarto", "leo": "Leão", "lepus": "Lebre", "libra": "Libra", "lyra": "Lira", "mensa": "Mensa", "nu": "Nu (Imperatriz)", "pavo": "Pavão", "pegasus": "Pégaso", "perseus": "Perseu", "phoenix": "Fênix", "pisces": "Peixes", "puppis": "Popa", "pyxis": "Bússola", "rangifer": "Rena", "reticulum": "Rede", "sagittarius": "Sagitário", "scorpio": "Escorpião", "scutum": "Escudo", "serpens": "Serpente", "sextans": "Sextante", "silver-oriolus": "Oriolus de Prata", "taurus": "Touro", "tornado": "Tornado", "triangulum": "Triângulo", "virgo": "Virgem", "volans": "Volans"}
renders = collections.OrderedDict()
for f in sorted(os.listdir(NOTES + "/Cloths")):
    m = re.match(r"(.+?)(?:-v(\d))?(?:-(male|female))?\.png$", f)
    base, ver, sex = m.group(1), m.group(2), m.group(3)
    key = CONST_EN.get(base, base) + (f" V{ver}" if ver else "")
    renders.setdefault(key, []).append({"file": NOTES + "/Cloths/" + f, "sex": {"male": "masc.", "female": "fem."}.get(sex, "")})
shots = list(csv.DictReader(open(T + "/saints_screenshots.csv", encoding="utf-8")))
shots_by = collections.OrderedDict()
for s in shots: shots_by.setdefault(s["identificacao"], []).append({"file": NOTES + "/Saints/" + s["file"], "sex": {"M": "masc.", "F": "fem."}[s["genero"]]})
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
data = {"parts": parts, "char_stories": char_stories, "side": side, "cloth_quests": cloth_q, "others": others, "tests": tests,
        "pb_chars": pb_chars, "bios_common": bios_common, "pb_texts": pb_texts, "cards": cards, "unmapped_cards": unmapped, "portraits": portraits,
        "renders": renders, "shots_by": shots_by, "maps": maps, "cut_titles": cut_titles, "subtitles": subtitles, "instance_dialogue": inst, "titles": title_rows, "coverage": coverage, "npc_lines": npc_lines,
        "npc_count": len(npc), "mon_count": len(mon), "out": OUT, "notes": NOTES}
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
print("portraits", len(portraits), "missing:", [k for k in PORTRAITS if k not in portraits]); print("renders", len(renders), "shot groups", len(shots_by)); print("cut titles", len(cut_titles), "subtitles", len(subtitles), "inst lines", len(inst), "titles", len(title_rows))
print("coverage:", [(c["item"], c["found"]) for c in coverage])
