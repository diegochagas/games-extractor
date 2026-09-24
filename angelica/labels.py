# English labels for the Chinese / cryptic folder names used by the client
LABELS = {
 "building": "Buildings (static architecture per map)", "building/textures": "Building textures, one sub-folder per map number", "building/chf": "Building height fields",
 "flash": "Login / character-creation screens (Scaleform flash UI)", "gfx": "Particle & skill effects", "gfx/textures": "Effect textures", "gfx/models": "Effect meshes' textures",
 "gfx/title": "Skill-name title strips", "gfx/skillattack": "Skill attack sheet", "grasses": "Grass & plant billboards", "loddata": "Map LOD data (aerial bird views)",
 "litmodels": "Light-mapped static scenery, one folder per map code", "models": "3D model textures", "models/npcs": "NPC & monster textures", "models/players": "Player character textures",
 "models/matters": "Loot / world objects", "shaders": "Shader lookup textures", "surfaces": "2D UI surfaces", "textures": "Terrain, sky & misc textures", "textures/maps": "Terrain detail textures per map",
 "textures/sky": "Sky boxes", "textures/colormaping": "Colour mapping LUTs",
 "surfaces/background": "Loading screens & login backgrounds (1280x1024)", "surfaces/common": "Common widgets (buttons, edits, scrollbars)", "surfaces/iconset": "Icon atlases (split into images/icons/)",
 "surfaces/ingame": "In-game HUD pieces", "surfaces/maps": "World maps, minimaps & map marks", "surfaces/maps/worldmaps": "World map & minimap images per map code", "surfaces/maps/minimapmark": "Minimap marks",
 "surfaces/maps/precinct": "District/precinct map pieces", "surfaces/res": "UI resources", "surfaces/res/head": "Character heads (128x128)", "surfaces/res/portrait": "Character portraits (128x128)",
 "surfaces/res/photobook": "Photobook / collection cards (356x520 illustrations)", "surfaces/res/daily": "Daily activities banners & icons", "surfaces/res/login": "Login class icons",
 "surfaces/res/quest": "Quest illustrations", "surfaces/res/target": "Target bars", "surfaces/res/countbirds": "Bird-counting minigame", "surfaces/res/qte": "QTE prompts", "surfaces/res/enhance": "Enhance icons",
 "surfaces/special": "UI panels, one folder per window", "surfaces/temp": "Temporary UI pieces", "surfaces/button": "Buttons", "surfaces/frame": "Frames", "surfaces/logo.png": "Logo",
 "东西伯利亚": "East Siberia", "其他": "Others", "其他原著角色": "Other original-series characters", "冥王势力": "Hades' forces (Specters)", "动画": "Cutscene models", "哈迪斯城": "Hades City",
 "圣域势力": "Sanctuary forces", "圣域地区": "Sanctuary area", "场景": "Scenes", "场景物品": "Scene props", "宠物": "Pets", "庐山地区": "Mount Lu (Rozan) area", "技能用怪": "Skill dummy monsters",
 "机关npc": "Mechanism NPCs", "机关怪物": "Mechanism monsters", "极乐净土": "Elysium", "死亡皇后岛地区": "Death Queen Island", "海皇势力": "Poseidon's forces (Marinas)", "滚雪球": "Snowball event",
 "白银圣斗士": "Silver Saints", "神器": "Artifacts", "结婚场景": "Wedding scene", "遗忘之路地区": "Forgotten Road area", "野兽": "Beasts", "银河竞技场地区": "Galaxian Wars arena", "雅典娜": "Athena",
 "青铜圣斗士": "Bronze Saints", "黄金圣斗士": "Gold Saints", "黑暗圣斗士": "Black Saints", "圣衣": "Cloths (armour sets)", "形象": "Appearance (faces, hair, bodies)", "时装": "Fashion costumes",
 "道具": "Props, weapons, wings & mounts", "掉落简化模型": "Simplified drop models", "场景动画模型": "Scene animation models", "领土战漂浮物": "Territory-war floating objects", "特效用ecm": "FX-only models",
 "矿物": "Minerals / furniture", "光晕": "Glow halos", "图案": "Patterns", "圆环光": "Ring light", "多个粒子": "Multi-particle", "序列": "Sprite sequences", "放射光": "Radial light", "模型贴图": "Model textures",
 "法阵": "Magic circles", "溶解": "Dissolve", "烟火": "Fire & smoke", "物体": "Objects", "界面用": "UI use", "符文": "Runes", "粒子": "Particles", "纹理": "Textures", "轨迹": "Trails", "闪光": "Flashes", "闪电": "Lightning",
 "normalmap": "Normal maps", "birdviews": "Aerial views", "water": "Water", "detail": "Detail textures", "npcs": "NPCs", "players": "Players", "matters": "Objects",
}
MAP_CODES = {}
def label(path):
    if path in LABELS: return LABELS[path]
    last = path.rsplit("/", 1)[-1]
    if last in LABELS: return LABELS[last]
    if last in MAP_CODES: return "map " + last + ": " + MAP_CODES[last]
    return ""
