#!/usr/bin/env python3
"""Translate Angelica asset names (Chinese folder / file names) into English
file names and Portuguese captions.

    names.py NAMES.json 双子座撒加神圣衣 黄金圣斗士射手座便装1 ...

NAMES.json is the zh -> {pt, en} table dumped from the game's own text
(data_npc / data_monster / data_item names, see dump in the Seiya README).
The exact game name wins; otherwise the name is split into glossary terms
(constellations, characters, factions, common words) and the rest is
romanised with pypinyin when it is installed.
"""
import json
import os
import re
import sys
import unicodedata

try:
    from pypinyin import lazy_pinyin
except ImportError:  # optional
    lazy_pinyin = None

# (chinese, english, portuguese) - longest terms are tried first.
GLOSSARY = [
    # --- constellations (Athena's cloths) ---
    ("天马座", "Pegasus", "Pégaso"), ("天龙座", "Dragon", "Dragão"), ("白鸟座", "Cygnus", "Cisne"),
    ("仙女座", "Andromeda", "Andrômeda"), ("凤凰座", "Phoenix", "Fênix"), ("天狼座", "Wolf", "Lobo"),
    ("大熊座", "Bear", "Urso"), ("幼狮座", "Lionet", "Leão Menor"), ("水蛇座", "Hydra", "Hidra"),
    ("独角兽座", "Unicorn", "Unicórnio"), ("变色龙座", "Chameleon", "Camaleão"), ("海蛇座", "Hydrus", "Hidra Macho"),
    ("盾牌座", "Scutum", "Escudo"), ("盾座", "Scutum", "Escudo"), ("六分仪座", "Sextans", "Sextante"),
    ("箭鱼座", "Volans", "Peixe-Voador"), ("飞鱼座", "Volans", "Peixe-Voador"), ("巨蛇座", "Serpens", "Serpente"),
    ("南鱼座", "Piscis Austrinus", "Peixe Austral"), ("北冕座", "Corona Borealis", "Coroa Boreal"),
    ("南冕座", "Corona Australis", "Coroa Austral"), ("南十字座", "Crux", "Cruzeiro do Sul"), ("船尾座", "Puppis", "Popa"),
    ("鹿豹座", "Camelopardalis", "Girafa"), ("天兔座", "Lepus", "Lebre"), ("波江座", "Eridanus", "Erídano"),
    ("时钟座", "Horologium", "Relógio"), ("皇女座", "Nu", "Imperatriz"), ("银莺座", "Silver Oriolus", "Oriolus de Prata"),
    ("猎豹座", "Cheetah", "Guepardo"), ("铜鱼座", "Coreius", "Coreius"), ("铜剑座", "Bronze Sword", "Espada de Bronze"),
    ("九头龙座", "Nine-Headed Dragon", "Dragão de Nove Cabeças"), ("后发座", "Coma Berenices", "Cabeleira de Berenice"),
    ("地球座", "Earth", "Terra"), ("巨鲨座", "Shark", "Tubarão"), ("曼陀铃座", "Mandolin", "Bandolim"),
    ("低走座", "Dizou", "Dizou"), ("低音座", "Bass", "Baixo"), ("夜灯座", "Night Lamp", "Lanterna Noturna"),
    ("幼蛛座", "Tarantula", "Tarântula"), ("幼蛀座", "Tarantula", "Tarântula"), ("银蝇座", "Musca", "Mosca"),
    ("天琴座", "Lyra", "Lira"), ("御夫座", "Auriga", "Auriga"), ("仙王座", "Cepheus", "Cefeu"), ("仙皇座", "Cepheus", "Cefeu"),
    ("网罟座", "Reticulum", "Rede"), ("天鹰座", "Eagle", "Águia"), ("三角座", "Triangulum", "Triângulo"),
    ("武仙座", "Heracles", "Hércules"), ("乌鸦座", "Corvus", "Corvo"), ("半人马座", "Centaurus", "Centauro"),
    ("天炉座", "Fornax", "Fornalha"), ("罗盘座", "Pyxis", "Bússola"), ("鲸鱼座", "Cetus", "Baleia"), ("巨鲸座", "Cetus", "Baleia"),
    ("白鲸座", "Beluga", "Beluga"), ("英仙座", "Perseus", "Perseu"), ("仙后座", "Cassiopeia", "Cassiopeia"),
    ("孔雀座", "Pavo", "Pavão"), ("蜥蜴座", "Lacerta", "Lagarto"), ("巨爵座", "Crater", "Taça"),
    ("地狱犬座", "Cerberus", "Cérbero"), ("巨犬座", "Canis Major", "Cão Maior"), ("天鹤座", "Grus", "Grou"),
    ("祭坛座", "Ara", "Altar"), ("大犬座", "Canis Major", "Cão Maior"), ("剑鱼座", "Dorado", "Dourado"),
    ("天幕座", "Atrium", "Atrium"), ("鬼主座", "Ghosts Master", "Mestre dos Fantasmas"), ("天坦座", "Tornado", "Tornado"),
    ("猎犬座", "Canes Venatici", "Cães de Caça"), ("天箭星座", "Sagitta", "Sagita"), ("天箭座", "Sagitta", "Sagita"),
    ("莲花座", "Lotus", "Lótus"), ("蛇夫座", "Ophiuchus", "Serpentário"), ("山案座", "Mensa", "Mensa"),
    ("白羊座", "Aries", "Áries"), ("金牛座", "Taurus", "Touro"), ("双子座", "Gemini", "Gêmeos"), ("巨蟹座", "Cancer", "Câncer"),
    ("狮子座", "Leo", "Leão"), ("处女座", "Virgo", "Virgem"), ("天秤座", "Libra", "Libra"), ("天平座", "Libra", "Libra"),
    ("天枰座", "Libra", "Libra"), ("天蝎座", "Scorpio", "Escorpião"), ("射手座", "Sagittarius", "Sagitário"),
    ("摩羯座", "Capricorn", "Capricórnio"), ("魔羯座", "Capricorn", "Capricórnio"), ("山羊座", "Capricorn", "Capricórnio"),
    ("水瓶座", "Aquarius", "Aquário"), ("双鱼座", "Pisces", "Peixes"), ("翼龙座", "Wyvern", "Wyvern"),
    ("白羊宫", "Aries Temple", "Casa de Áries"), ("双鱼宫", "Pisces Temple", "Casa de Peixes"), ("处女宫", "Virgo Temple", "Casa de Virgem"),
    ("狮子宫", "Leo Temple", "Casa de Leão"), ("射手宫", "Sagittarius Temple", "Casa de Sagitário"), ("天枰宫", "Libra Temple", "Casa de Libra"),
    ("教皇宫", "Pope's Chamber", "Salão do Grande Mestre"), ("十二宫", "Twelve Temples", "Doze Casas"),
    # gold saints named without 座
    ("白羊圣衣", "Aries Cloth", "Armadura de Áries"), ("金牛圣衣", "Taurus Cloth", "Armadura de Touro"), ("双子圣衣", "Gemini Cloth", "Armadura de Gêmeos"),
    ("巨蟹圣衣", "Cancer Cloth", "Armadura de Câncer"), ("狮子圣衣", "Leo Cloth", "Armadura de Leão"), ("处女圣衣", "Virgo Cloth", "Armadura de Virgem"),
    ("天秤圣衣", "Libra Cloth", "Armadura de Libra"), ("天蝎圣衣", "Scorpio Cloth", "Armadura de Escorpião"), ("射手圣衣", "Sagittarius Cloth", "Armadura de Sagitário"),
    ("山羊圣衣", "Capricorn Cloth", "Armadura de Capricórnio"), ("水瓶圣衣", "Aquarius Cloth", "Armadura de Aquário"), ("双鱼圣衣", "Pisces Cloth", "Armadura de Peixes"),
    # --- marinas ---
    ("海龙座", "Sea Dragon", "Dragão Marinho"), ("海龙", "Sea Dragon", "Dragão Marinho"), ("海马", "Sea Horse", "Cavalo Marinho"),
    ("六圣兽", "Scylla", "Cila"), ("六怪妖", "Scylla", "Cila"), ("海皇子", "Chrysaor", "Crisaor"), ("海魔女", "Siren", "Sirene"),
    ("魔鬼鱼", "Kraken", "Kraken"), ("北海巨妖", "Kraken", "Kraken"), ("海怪", "Lyumnades", "Limnades"), ("水魔", "Lyumnades", "Limnades"),
    ("美人鱼", "Mermaid", "Sereia"), ("鳞衣", "Scale", "Escama"), ("麟衣", "Scale", "Escama"), ("海将军", "General", "General Marina"),
    ("海斗士", "Marina", "Marina"), ("海皇", "Poseidon", "Poseidon"), ("波塞冬", "Poseidon", "Poseidon"), ("塞壬", "Siren", "Sereia"),
    ("海妖", "Sea Nymph", "Ninfa do Mar"), ("海魔兽", "Sea Monster", "Monstro Marinho"), ("三叉戟", "Trident", "Tridente"),
    # --- specters ---
    ("天猛星", "Wyvern", "Wyvern"), ("天贵星", "Griffon", "Griffon"), ("天雄星", "Garuda", "Garuda"), ("天哭星", "Harpy", "Harpia"),
    ("天英星", "Balron", "Balron"), ("天间星", "Acheron", "Aqueronte"), ("天魔星", "Alraune", "Alraune"), ("天捷星", "Basilisk", "Basilisco"),
    ("天兽星", "Sphinx", "Esfinge"), ("天牢星", "Minotaur", "Minotauro"), ("天罪星", "Lycaon", "Licaão"), ("天角星", "Golem", "Golem"),
    ("天败星", "Troll", "Troll"), ("天威星", "Wyrm", "Wyrm"), ("天暴星", "Bennu", "Bennu"), ("天杀星", "Steven's Star", "Estrela de Steven"),
    ("天暗星", "Moe's Star", "Estrela de Moe"), ("天阴星", "Larry's Star", "Estrela de Larry"), ("天异星", "Curly's Star", "Estrela de Curly"),
    ("地暗星", "Deep", "Deep"), ("地爆星", "Cyclops", "Ciclope"), ("地暴星", "Cyclops", "Ciclope"), ("地妖星", "Papillon", "Papillon"),
    ("地幽星", "Elf", "Elfo"), ("地恶星", "Isolde's Star", "Estrela de Isolde"), ("地伏星", "Worm", "Verme"), ("地奇星", "Frog", "Sapo"),
    ("地囚星", "Gerald's Star", "Estrela de Gerald"), ("地明星", "Stone's Star", "Estrela de Stone"), ("地走星", "Gorgon", "Górgona"),
    ("地阔星", "Hell Star", "Estrela Infernal"), ("冥斗士", "Specter", "Espectro"), ("冥斗星", "Specter", "Espectro"), ("冥衣", "Surplice", "Sapuris"),
    ("冥化", "Surplice", "Sapuris"), ("冥王", "Hades", "Hades"), ("冥后", "Persephone", "Perséfone"), ("冥界", "Underworld", "Submundo"),
    ("哈迪斯城", "Hades Castle", "Castelo de Hades"), ("哈迪斯", "Hades", "Hades"), ("潘多拉", "Pandora", "Pandora"),
    ("死神", "Thanatos", "Thanatos"), ("睡神", "Hypnos", "Hypnos"), ("梦神", "Dream God", "Deus do Sonho"), ("极乐", "Elysion", "Elísios"),
    ("拉达曼提斯", "Rhadamanthys", "Radamanthys"), ("拉达曼迪斯", "Rhadamanthys", "Radamanthys"), ("米洛斯", "Minos", "Minos"), ("米诺斯", "Minos", "Minos"),
    ("艾亚哥斯", "Aiacos", "Aiacos"), ("路尼", "Lune", "Lune"), ("洛克", "Rock", "Rock"), ("伊万", "Iwan", "Iwan"), ("缪", "Myu", "Myu"),
    ("赛洛斯", "Zelos", "Zeros"), ("杰拉尔德", "Gerald", "Gerald"), ("莱米", "Raimi", "Raimi"), ("巴比隆", "Papillon Myu", "Myu de Papillon"),
    ("法拉奥", "Pharaoh", "Faraó"), ("卡隆", "Charon", "Caronte"), ("奎恩", "Queen", "Queen"), ("古加多", "Gigant", "Gigante"), ("尼奥比", "Niobe", "Niobe"),
    ("西路费都", "Sylphid", "Sylphid"), ("莫菲斯", "Morpheus", "Morfeu"), ("伊克洛", "Icelus", "Icelus"), ("幻塔索", "Phantasos", "Fantaso"),
    ("奥涅依", "Oneiros", "Oneiros"), ("尤丽缇丝", "Eurydice", "Eurídice"), ("哥顿", "Gordon", "Gordon"), ("御林军", "Royal Guard", "Guarda Real"),
    # --- asgard ---
    ("天枢星", "Alpha Dubhe", "Alfa Dubhe"), ("天璇星", "Beta Merak", "Beta Merak"), ("天玑星", "Gamma Phecda", "Gama Phecda"), ("天机星", "Gamma Phecda", "Gama Phecda"),
    ("天权星", "Delta Megrez", "Delta Megrez"), ("玉衡星", "Epsilon Alioth", "Épsilon Alioth"), ("开阳星", "Zeta Mizar", "Zeta Mizar"),
    ("摇光星", "Eta Benetnasch", "Eta Benetnasch"), ("辅星", "Alcor", "Alcor"), ("双头龙", "Dubhe Twin Dragon", "Dragão de Duas Cabeças"),
    ("八脚战马", "Merak Sleipnir", "Cavalo de Oito Patas"), ("北极狼", "Alioth Fenrir", "Lobo Polar"), ("剑齿虎", "Zeta Sabertooth", "Tigre-dentes-de-sabre"),
    ("巨蛇神斗士", "Phecda Serpent God Warrior", "Guerreiro Deus da Serpente"), ("神斗士", "God Warrior", "Guerreiro Deus"),
    ("齐格弗里德", "Siegfried", "Siegfried"), ("哈根", "Hagen", "Hagen"), ("阿鲁贝利亚", "Alberich", "Alberich"), ("菲利路", "Fenrir", "Fenrir"),
    ("希度", "Syd", "Syd"), ("巴度", "Bud", "Bud"), ("米伊美", "Mime", "Mime"), ("洛基", "Loki", "Loki"), ("邪神", "Evil God", "Deus Maligno"),
    ("瓦尔基里", "Valkyrie", "Valquíria"), ("女武神", "Valkyrie", "Valquíria"), ("冰之国", "Ice Kingdom", "País do Gelo"), ("冰斗士", "Ice Warrior", "Guerreiro do Gelo"),
    ("北欧神族", "Asgardian", "Asgardiano"), ("北欧", "Nordic", "Nórdico"), ("法夫纳", "Fafnir", "Fafnir"), ("东西伯利亚", "East Siberia", "Sibéria Oriental"),
    ("雅科夫", "Jacob", "Jacob"),
    # --- gods & others ---
    ("爱神之子爱洛斯", "Eros", "Eros"), ("爱洛斯", "Eros", "Eros"), ("爱神阿芙洛狄忒", "Aphrodite (goddess)", "Afrodite (deusa)"),
    ("太阳神阿波罗", "Apollo", "Apolo"), ("阿波罗", "Apollo", "Apolo"), ("虚无之神拉蒙斯", "Lamech", "Lamech"), ("拉蒙斯", "Lamech", "Lamech"),
    ("力量之神纳乌尔", "Naur, God of Power", "Naur, deus da força"), ("物质之神帕加迪斯", "Pagadis, God of Matter", "Pagadis, deus da matéria"),
    ("真理之神默克尔斯", "Merkels, God of Truth", "Merkels, deus da verdade"), ("沙暴之奥迪加", "Odiga of the Sandstorm", "Odiga da tempestade de areia"),
    ("雷之克洛耶", "Chloe of Thunder", "Chloe do trovão"), ("火山之撒里诺", "Sillas of the Volcano", "Sillas do Vulcão"),
    ("命运三女神", "Three Fates", "Três Moiras"), ("命运女神", "Fate", "Moira"), ("四女神", "Four Goddesses", "Quatro Deusas"),
    ("普罗米修斯", "Prometheus", "Prometeu"), ("泰坦", "Titan", "Titã"), ("斯芬克斯", "Sphinx", "Esfinge"), ("迦楼罗", "Garuda", "Garuda"),
    ("美杜莎", "Medusa", "Medusa"),
    # --- athena's side: people ---
    ("雅典娜", "Athena", "Athena"), ("城户纱织", "Saori Kido", "Saori Kido"), ("城户沙织", "Saori Kido", "Saori Kido"), ("沙织", "Saori", "Saori"),
    ("城户光政", "Mitsumasa Kido", "Mitsumasa Kido"), ("辰巳德丸", "Tatsumi", "Tatsumi"), ("辰巳", "Tatsumi", "Tatsumi"),
    ("星矢", "Seiya", "Seiya"), ("紫龙", "Shiryu", "Shiryu"), ("冰河", "Hyoga", "Hyoga"), ("一辉", "Ikki", "Ikki"), ("瞬", "Shun", "Shun"),
    ("那智", "Nachi", "Nachi"), ("檄", "Geki", "Geki"), ("蛮", "Ban", "Ban"), ("市", "Ichi", "Ichi"), ("邪武", "Jabu", "Jabu"), ("珍妮", "June", "June"),
    ("穆先生", "Mu", "Mu"), ("穆", "Mu", "Mu"), ("阿鲁迪巴", "Aldebaran", "Aldebaran"), ("撒加", "Saga", "Saga"), ("迪斯马斯克", "Deathmask", "Máscara da Morte"),
    ("迪斯马克斯", "Deathmask", "Máscara da Morte"), ("艾欧里亚", "Aiolia", "Aiolia"), ("沙加", "Shaka", "Shaka"), ("童虎", "Dohko", "Dohko"),
    ("米罗", "Milo", "Miro"), ("艾欧罗斯", "Aiolos", "Aioros"), ("艾俄洛斯", "Aiolos", "Aioros"), ("修罗", "Shura", "Shura"), ("卡妙", "Camus", "Camus"),
    ("阿布罗狄", "Aphrodite", "Afrodite"), ("阿布罗秋", "Aphrodite", "Afrodite"), ("阿布罗迪", "Aphrodite", "Afrodite"), ("史昂", "Shion", "Shion"),
    ("教皇", "Pope", "Grande Mestre"), ("魔铃", "Marin", "Marin"), ("莎尔娜", "Shaina", "Shina"), ("奥路菲", "Orphee", "Orfeu"),
    ("加隆", "Kanon", "Kanon"), ("朱利安", "Julian Solo", "Julian Solo"), ("尤里安", "Julian", "Julian"), ("苏兰特", "Sorrento", "Sorento"),
    ("拜安", "Baian", "Baian"), ("克修拉", "Krishna", "Krishna"), ("艾尔扎克", "Isaak", "Isaac"), ("伊奥", "Io", "Io"), ("卡撒", "Kasa", "Kasa"),
    ("狄迪思", "Thetis", "Thetis"), ("蒂迪斯", "Thetis", "Thetis"), ("春丽", "Shunrei", "Shunrei"), ("贵鬼", "Kiki", "Kiki"), ("卡西欧士", "Cassios", "Cássios"),
    ("基鲁提", "Guilty", "Guilty"), ("艾丝美拉达", "Esmeralda", "Esmeralda"), ("星华", "Seika", "Seika"), ("美惠", "Miho", "Mino"),
    ("强戈", "Jango", "Jango"), ("娜塔莎", "Natassia", "Natássia"), ("亚雷库萨", "Alexer", "Alexer"), ("阿历克斯", "Alex", "Alex"),
    ("艾德", "Eide", "Eide"), ("艾亚", "Aiya", "Aiya"), ("雷虎", "Lei-Hu", "Lei-Hu"), ("李云", "Li-Yun", "Li-Yun"), ("枫", "Acer", "Acer"),
    ("初代天马英灵", "First Pegasus Spirit", "Espírito do primeiro Pégaso"), ("圣斗士英灵", "Saint Spirit", "Espírito de Cavaleiro"),
    ("黑暗圣斗士", "Black Saint", "Cavaleiro Negro"), ("黑暗", "Black", "Negro"), ("暗黑", "Dark", "Sombrio"),
    ("青铜圣斗士", "Bronze Saint", "Cavaleiro de Bronze"), ("白银圣斗士", "Silver Saint", "Cavaleiro de Prata"), ("黄金圣斗士", "Gold Saint", "Cavaleiro de Ouro"),
    ("圣斗士", "Saint", "Cavaleiro"), ("青铜", "Bronze", "Bronze"), ("白银", "Silver", "Prata"), ("黄金", "Gold", "Ouro"), ("真", "True", "Verdadeiro"),
    ("神圣衣", "God Cloth", "Armadura Divina"), ("圣衣", "Cloth", "Armadura"), ("神衣", "Kamui", "Kamui"), ("塑身衣", "Body Suit", "Roupa de Treino"),
    ("初始装备", "Starter Gear", "Equipamento Inicial"), ("初始装", "Starter Gear", "Equipamento Inicial"), ("候补生", "Trainee", "Aspirante"),
    ("学员", "Apprentice", "Aprendiz"), ("便装", "Casual", "Roupa Comum"), ("秋衣", "Undershirt", "Roupa de Baixo"), ("唐装", "Chinese Suit", "Traje Chinês"),
    ("裸衣", "Shirtless", "Sem Camisa"), ("晚礼服", "Evening Dress", "Vestido de Gala"), ("西服", "Suit", "Terno"), ("法袍", "Robe", "Túnica"),
    ("影衣", "Shadow Surplice", "Sapuris Sombria"), ("灰发", "Grey Hair", "Cabelo Grisalho"), ("幼年", "Child", "Criança"), ("婴儿", "Baby", "Bebê"),
    ("复生的", "Revived", "Ressuscitado"), ("异化", "Mutated", "Mutado"), ("变异", "Mutated", "Mutado"), ("灵魂状态", "Soul", "Alma"), ("灵魂", "Soul", "Alma"),
    ("空手", "Empty-handed", "Mãos Vazias"), ("翅膀", "Wings", "Asas"), ("放大版", "Large", "Grande"), ("组合版", "Assembled", "Montada"),
    ("组合形态", "Assembled Form", "Forma Montada"), ("穿着形态", "Worn Form", "Forma Vestida"), ("静立组合形态", "Standing Assembled", "Montada em Pé"),
    ("人形版", "Humanoid", "Humanoide"), ("特殊站立", "Special Stance", "Postura Especial"), ("倒吊", "Hanging", "Pendurada"), ("快速版", "Fast", "Rápido"),
    ("战斗宠", "Battle Pet", "Pet de Batalha"), ("q版", "Chibi", "Chibi"), ("Q版", "Chibi", "Chibi"), ("选人", "Character Select", "Seleção de Personagem"),
    ("选人背景", "Character Select Background", "Fundo da Seleção"), ("戴面具", "Masked", "Mascarado"), ("面具", "Mask", "Máscara"),
    ("神器", "Artifact", "Relíquia"), ("圣衣箱", "Cloth Box", "Urna da Armadura"), ("箱子", "Box", "Caixa"), ("过渡", "Interim", "Transição"),
    ("头盔", "Helmet", "Elmo"), ("头饰", "Headpiece", "Adorno de Cabeça"), ("面甲", "Face Guard", "Máscara"), ("肩甲", "Shoulder Guard", "Ombreira"),
    ("胸甲", "Chest Plate", "Peitoral"), ("背甲", "Back Plate", "Placa das Costas"), ("腕甲", "Bracer", "Braçadeira"), ("翼盔", "Winged Helmet", "Elmo Alado"),
    ("黄金神箭", "Golden Arrow", "Flecha de Ouro"), ("黄金弓", "Golden Bow", "Arco de Ouro"), ("黄金权杖", "Golden Staff", "Cetro de Ouro"),
    ("黄金盾", "Golden Shield", "Escudo de Ouro"), ("黄金匕首", "Golden Dagger", "Adaga de Ouro"), ("黄金犄角", "Golden Horns", "Chifres de Ouro"),
    ("雅典娜之盾", "Aegis", "Escudo de Athena"), ("女神", "Goddess", "Deusa"), ("双截棍", "Nunchaku", "Nunchaku"), ("佛珠", "Prayer Beads", "Rosário"),
    ("玫瑰", "Rose", "Rosa"), ("红玫瑰", "Red Rose", "Rosa Vermelha"), ("白玫瑰", "White Rose", "Rosa Branca"), ("竖琴", "Harp", "Harpa"),
    ("魔琴", "Demon Harp", "Harpa Demoníaca"), ("魔笛", "Flute", "Flauta"), ("笛子", "Flute", "Flauta"), ("船桨", "Oar", "Remo"), ("冥河", "Styx", "Estige"),
    ("审判法典", "Judgement Codex", "Código do Julgamento"), ("炎魔鞭", "Fire Whip", "Chicote de Fogo"), ("鞭尾", "Whip Tail", "Cauda-chicote"),
    ("触手", "Tentacles", "Tentáculos"), ("冥蝶", "Hell Butterfly", "Borboleta Infernal"), ("曼陀罗花", "Mandala Flower", "Flor de Mandala"),
    ("提线傀儡", "Marionette", "Marionete"), ("战斧", "Battle Axe", "Machado de Guerra"), ("铁拳", "Iron Fist", "Punho de Ferro"), ("火圈", "Fire Ring", "Anel de Fogo"),
    ("巨钳", "Giant Claw", "Garra Gigante"), ("瓶子", "Vase", "Vaso"), ("魔龙之脊", "Dragon Spine", "Espinha do Dragão"), ("善与恶", "Good and Evil", "Bem e Mal"),
    ("少女的祈祷", "Maiden's Prayer", "Oração da Donzela"), ("黑羽", "Black Feathers", "Penas Negras"), ("假面", "Mask", "Máscara"),
    ("鹰身女妖", "Harpy", "Harpia"), ("深渊", "Abyss", "Abismo"), ("狡诈", "Cunning", "Astúcia"), ("忠诚", "Loyalty", "Lealdade"), ("沉着", "Calm", "Serenidade"),
    ("猩红", "Crimson", "Carmesim"), ("深寒", "Deep Cold", "Frio Profundo"), ("创造与毁灭", "Creation and Destruction", "Criação e Destruição"),
    ("工具", "Tools", "Ferramentas"), ("手臂", "Arm", "Braço"), ("身体", "Body", "Corpo"), ("手", "Hand", "Mão"), ("角", "Horn", "Chifre"),
    # --- places ---
    ("圣域", "Sanctuary", "Santuário"), ("庐山", "Rozan", "Rozan"), ("遗忘之路", "Forgotten Road", "Estrada Esquecida"), ("遗忘之村", "Forgotten Village", "Vila Esquecida"),
    ("死亡皇后岛", "Death Queen Island", "Ilha da Rainha da Morte"), ("皇后岛", "Death Queen Island", "Ilha da Rainha da Morte"),
    ("亚特兰蒂斯", "Atlantis", "Atlântida"), ("仙女岛", "Andromeda Island", "Ilha de Andrômeda"), ("银河竞技场", "Galaxian Arena", "Coliseu Graad"),
    ("银河大赛", "Galaxian Wars", "Guerra Galáctica"), ("群星之地", "Land of Stars", "Terra das Constelações"), ("富士山", "Mount Fuji", "Monte Fuji"),
    ("铃之村", "Bell Village", "Vila do Sino"), ("星之子学园", "Children of the Stars Academy", "Orfanato Filhos das Estrelas"), ("星之学员", "Star Pupil", "Aluno das Estrelas"),
    ("星之子学员", "Star Pupil", "Aluno das Estrelas"), ("古拉杜财团", "Graad Foundation", "Fundação Graad"), ("古拉社财团", "Graad Foundation", "Fundação Graad"),
    ("希腊", "Greek", "Grego"), ("黄泉比良坂", "Yomotsu Hirasaka", "Yomotsu Hirasaka"), ("南太平洋", "South Pacific", "Pacífico Sul"), ("南冰洋", "Southern Ocean", "Oceano Antártico"),
    ("塔瓦娜", "Tavana", "Tavana"), ("坦桑诺亚", "Tanzanoa", "Tanzanoa"), ("阿提卡", "Attica", "Ática"), ("领土战", "Territory War", "Guerra de Território"),
    ("军团基地", "Legion Base", "Base da Legião"), ("浮空争霸", "Sky Battle", "Batalha Aérea"), ("钟楼", "Clock Tower", "Torre do Relógio"),
    ("墓地", "Graveyard", "Cemitério"), ("圣斗士之墓", "Saint's Grave", "Túmulo do Cavaleiro"), ("副本", "Dungeon", "Dungeon"), ("关卡", "Stage", "Fase"),
    ("万神殿", "Pantheon", "Panteão"), ("火神祭坛", "Hephaestus Altar", "Altar de Hefesto"), ("火神", "Hephaestus", "Hefesto"), ("酒神", "Dionysus", "Dionísio"),
    # --- generic people ---
    ("杂兵", "Soldier", "Soldado"), ("头目", "Leader", "Líder"), ("远程", "Ranged", "à distância"), ("近战", "Melee", "Corpo a corpo"),
    ("匀称", "Average", "Médio"), ("强壮", "Strong", "Forte"), ("壮硕", "Strong", "Forte"), ("大壮", "Big", "Grande"), ("瘦小", "Small", "Pequeno"),
    ("美型", "Handsome", "Belo"), ("娇小", "Petite", "Pequena"), ("灵活", "Agile", "Ágil"), ("队长", "Captain", "Capitão"), ("勇士", "Warrior", "Guerreiro"),
    ("长老", "Elder", "Ancião"), ("弓箭手", "Archer", "Arqueiro"), ("居民", "Resident", "Morador"), ("村民", "Villager", "Aldeão"), ("村长", "Village Chief", "Chefe da Vila"),
    ("渔民", "Fisherman", "Pescador"), ("盗贼", "Thief", "Ladrão"), ("小偷", "Thief", "Ladrão"), ("海盗", "Pirate", "Pirata"), ("水手", "Sailor", "Marinheiro"),
    ("流放者", "Exile", "Exilado"), ("亡灵", "Undead", "Morto-vivo"), ("幻象", "Illusion", "Ilusão"), ("幻像", "Illusion", "Ilusão"), ("幸存者", "Survivor", "Sobrevivente"),
    ("女仆", "Maid", "Empregada"), ("农夫", "Farmer", "Fazendeiro"), ("梦游者", "Sleepwalker", "Sonâmbulo"), ("奴隶主", "Slave Master", "Senhor de Escravos"),
    ("奴隶", "Slave", "Escravo"), ("女奴", "Slave Girl", "Escrava"), ("遗民", "Survivor", "Remanescente"), ("逃跑", "Fleeing", "Fugitiva"),
    ("商人", "Merchant", "Mercador"), ("背包客", "Backpacker", "Mochileiro"), ("杂货商", "Grocer", "Vendedor"), ("船夫", "Boatman", "Barqueiro"),
    ("厨娘", "Cook", "Cozinheira"), ("小女孩", "Little Girl", "Menina"), ("小男孩", "Little Boy", "Menino"), ("少女", "Girl", "Moça"), ("平民", "Civilian", "Civil"),
    ("使节", "Envoy", "Emissário"), ("助祭司", "Assistant Priest", "Sacerdote Auxiliar"), ("助理祭司", "Assistant Priest", "Sacerdotisa Auxiliar"), ("祭司", "Priest", "Sacerdote"),
    ("老年", "Old", "Idoso"), ("老人", "Old Man", "Ancião"), ("老妇人", "Old Woman", "Anciã"), ("隐士", "Hermit", "Eremita"), ("修行者", "Ascetic", "Asceta"),
    ("拳师", "Boxer", "Lutador"), ("观众", "Spectator", "Espectador"), ("雇员", "Employee", "Funcionário"), ("路人", "Passer-by", "Transeunte"),
    ("孤儿", "Orphan", "Órfão"), ("神父", "Priest", "Padre"), ("花童", "Flower Child", "Daminha"), ("兔女郎", "Bunny Girl", "Coelhinha"),
    ("服务员", "Waitress", "Garçonete"), ("神秘黑衣人", "Mysterious Man in Black", "Homem Misterioso de Preto"), ("神秘怪人", "Mysterious Stranger", "Estranho Misterioso"),
    ("守护者", "Guardian", "Guardião"), ("考验者", "Challenger", "Desafiante"), ("失意", "Dejected", "Desanimado"), ("中毒的", "Poisoned", "Envenenado"),
    ("死而复生的战士", "Revived Warrior", "Guerreiro Ressuscitado"), ("强盗", "Bandit", "Bandido"), ("悟空", "Wukong", "Wukong"),
    ("大天使", "Archangel", "Arcanjo"), ("神官", "Priest", "Sacerdote"), ("先锋", "Vanguard", "Vanguarda"), ("炼金术士", "Alchemist", "Alquimista"),
    ("深潜者", "Deep One", "Habitante das Profundezas"), ("女妖", "Banshee", "Banshee"), ("碟王", "Butterfly King", "Rei das Borboletas"),
    ("圣诞老人", "Santa Claus", "Papai Noel"), ("圣诞树", "Christmas Tree", "Árvore de Natal"), ("圣诞节", "Christmas", "Natal"), ("春节", "Spring Festival", "Ano Novo Chinês"),
    ("中秋节", "Mid-Autumn", "Festival do Meio-Outono"), ("岁末福娃", "New Year Doll", "Boneco de Ano Novo"), ("双旦", "Holiday", "Festas"), ("雪人", "Snowman", "Boneco de Neve"),
    ("蝙蝠侠", "Batman", "Batman"), ("小丑", "Clown", "Palhaço"), ("熊猫", "Panda", "Panda"), ("卡丁车", "Go-kart", "Kart"), ("气球人", "Balloon Man", "Homem-balão"),
    ("丘比特", "Cupid", "Cupido"), ("宠物", "Pet", "Pet"), ("玩具熊", "Teddy Bear", "Ursinho"), ("兔兔女仆", "Bunny Maid", "Coelhinha Empregada"),
    # --- monsters / animals ---
    ("石像鬼", "Gargoyle", "Gárgula"), ("圣蛇", "Holy Snake", "Serpente Sagrada"), ("冥蝮蛇", "Hell Viper", "Víbora Infernal"), ("巨鲸怪", "Giant Whale", "Baleia Gigante"),
    ("乌贼", "Squid", "Lula"), ("小蟹", "Crab", "Caranguejo"), ("黑龙", "Black Dragon", "Dragão Negro"), ("天马兽", "Pegasus Beast", "Besta Pégaso"),
    ("大青狼", "Great Wolf", "Lobo Cinzento"), ("雪原狼", "Snow Wolf", "Lobo da Neve"), ("蝙蝠", "Bat", "Morcego"), ("北极熊", "Polar Bear", "Urso Polar"),
    ("森林熊", "Forest Bear", "Urso da Floresta"), ("水母", "Jellyfish", "Água-viva"), ("狮子兽", "Lion Beast", "Besta Leão"), ("秃鹫", "Vulture", "Abutre"),
    ("毒蛙", "Poison Frog", "Sapo Venenoso"), ("猴子", "Monkey", "Macaco"), ("猕猴精", "Macaque Spirit", "Espírito Macaco"), ("妖族将领", "Demon General", "General Demônio"),
    ("妖系怪物", "Demon Monster", "Monstro Demoníaco"), ("野兽", "Beast", "Fera"), ("飞虫", "Flying Insect", "Inseto Voador"), ("海星", "Starfish", "Estrela-do-mar"),
    ("黑鹰", "Black Hawk", "Falcão Negro"), ("乌鸦", "Crow", "Corvo"), ("天鹅", "Swan", "Cisne"), ("神龙", "Divine Dragon", "Dragão Divino"), ("巨龙", "Great Dragon", "Grande Dragão"),
    ("双足飞龙", "Wyvern (beast)", "Wyvern (fera)"), ("史莱姆", "Slime", "Slime"), ("熔岩巨人", "Lava Giant", "Gigante de Lava"), ("巨人", "Giant", "Gigante"),
    ("半身", "Half-body", "Meio-corpo"), ("小恶魔", "Imp", "Diabrete"), ("游尸", "Zombie", "Zumbi"), ("南瓜怪", "Pumpkin Monster", "Monstro Abóbora"),
    ("蘑菇", "Mushroom", "Cogumelo"), ("植被", "Vegetation", "Vegetação"), ("桃子", "Peach", "Pêssego"), ("珍珠贝", "Pearl Oyster", "Ostra"),
    ("海蛇", "Sea Snake", "Serpente Marinha"), ("火凤凰", "Fire Phoenix", "Fênix de Fogo"), ("凤凰", "Phoenix", "Fênix"), ("虎头", "Tiger Head", "Cabeça de Tigre"),
    ("空壳的圣衣怪", "Empty Cloth Monster", "Armadura Vazia"), ("暴怒之衣", "Cloth of Rage", "Armadura da Fúria"), ("瘟疫之衣", "Cloth of Plague", "Armadura da Peste"),
    ("衣魂", "Cloth Spirit", "Espírito da Armadura"), ("残破", "Broken", "Quebrada"), ("机甲", "Mecha", "Mecha"), ("金牛战车", "Taurus Chariot", "Carro de Touro"),
    ("防御塔", "Defense Tower", "Torre de Defesa"), ("扭曲空间兽", "Warped Space Beast", "Besta do Espaço Distorcido"), ("灵魂娃娃", "Soul Doll", "Boneca de Alma"),
    ("变身", "Transformation", "Transformação"), ("怪物", "Monster", "Monstro"), ("怪", "Monster", "Monstro"), ("兽", "Beast", "Fera"), ("狗", "Dog", "Cachorro"),
    ("猫", "Cat", "Gato"), ("鸟", "Bird", "Pássaro"), ("兔", "Rabbit", "Coelho"), ("狼", "Wolf", "Lobo"), ("蛇", "Snake", "Serpente"), ("熊", "Bear", "Urso"),
    # --- scenery / props / effects ---
    ("柱子", "Pillar", "Coluna"), ("门柱", "Gatepost", "Pilar do Portão"), ("栏杆", "Railing", "Grade"), ("大门", "Gate", "Portão"), ("石门", "Stone Door", "Porta de Pedra"),
    ("小门", "Small Door", "Porta Pequena"), ("后门", "Back Door", "Porta dos Fundos"), ("雕像", "Statue", "Estátua"), ("雕塑", "Statue", "Estátua"), ("方尖石碑", "Obelisk", "Obelisco"),
    ("神龙碑", "Dragon Stele", "Estela do Dragão"), ("告示牌", "Notice Board", "Placa de Aviso"), ("公示牌", "Notice Board", "Placa de Aviso"), ("警告牌", "Warning Sign", "Placa de Alerta"),
    ("邮箱", "Mailbox", "Caixa de Correio"), ("邮轮", "Cruise Ship", "Navio"), ("冥船", "Hades Ship", "Barco de Hades"), ("大桥", "Bridge", "Ponte"), ("石桥", "Stone Bridge", "Ponte de Pedra"),
    ("岩石", "Rock", "Rocha"), ("石头", "Stone", "Pedra"), ("山石", "Boulder", "Rocha"), ("落石", "Falling Rock", "Pedra Caindo"), ("石笋", "Stalagmite", "Estalagmite"),
    ("石锥", "Stone Spike", "Espinho de Pedra"), ("冰锥", "Ice Spike", "Estalactite de Gelo"), ("冰壁", "Ice Wall", "Parede de Gelo"), ("冰棺", "Ice Coffin", "Caixão de Gelo"),
    ("冰山", "Iceberg", "Iceberg"), ("冰块", "Ice Block", "Bloco de Gelo"), ("冰面", "Ice Surface", "Superfície de Gelo"), ("碎冰", "Broken Ice", "Gelo Quebrado"),
    ("栅栏", "Fence", "Cerca"), ("水晶", "Crystal", "Cristal"), ("水池", "Pool", "Piscina"), ("石井", "Stone Well", "Poço"), ("石亭", "Stone Pavilion", "Pavilhão de Pedra"),
    ("废墟", "Ruins", "Ruínas"), ("房子", "House", "Casa"), ("大厅", "Hall", "Salão"), ("幕帘", "Curtain", "Cortina"), ("旗子", "Flag", "Bandeira"), ("旗座", "Flag Base", "Base da Bandeira"),
    ("攻城车", "Siege Engine", "Máquina de Cerco"), ("基地", "Base", "Base"), ("复活点", "Respawn Point", "Ponto de Ressurreição"), ("传送", "Teleport", "Teleporte"),
    ("光效门", "Light Gate", "Portal de Luz"), ("木箱", "Crate", "Caixote"), ("坛罐", "Jar", "Jarro"), ("火药桶", "Powder Keg", "Barril de Pólvora"), ("捕兽夹", "Bear Trap", "Armadilha"),
    ("地刺", "Floor Spikes", "Espinhos"), ("刺柱", "Spike Pillar", "Coluna de Espinhos"), ("铁链", "Chains", "Correntes"), ("锁链", "Chain", "Corrente"), ("枯竹", "Dry Bamboo", "Bambu Seco"),
    ("竹", "Bamboo", "Bambu"), ("树干", "Trunk", "Tronco"), ("树叶", "Leaves", "Folhas"), ("小树", "Small Tree", "Árvore Pequena"), ("阔叶树", "Broadleaf Tree", "Árvore"),
    ("柏树", "Cypress", "Cipreste"), ("沙罗树", "Sala Tree", "Árvore Sala"), ("花瓣", "Petals", "Pétalas"), ("莲花", "Lotus", "Lótus"), ("迷雾", "Mist", "Névoa"),
    ("黑风", "Black Wind", "Vento Negro"), ("阴风", "Cold Wind", "Vento Frio"), ("火焰", "Flame", "Chama"), ("硝烟", "Smoke", "Fumaça"), ("尘土", "Dust", "Poeira"),
    ("漩涡", "Whirlpool", "Redemoinho"), ("水柱", "Water Pillar", "Coluna de Água"), ("水流", "Water Flow", "Correnteza"), ("飓风", "Hurricane", "Furacão"),
    ("龙卷风", "Tornado", "Tornado"), ("闪电", "Lightning", "Relâmpago"), ("雷", "Thunder", "Trovão"), ("电", "Electric", "Elétrico"), ("风", "Wind", "Vento"),
    ("陨石", "Meteor", "Meteoro"), ("群星乱坠", "Falling Stars", "Chuva de Estrelas"), ("银河星爆", "Galaxian Explosion", "Explosão Galáctica"), ("小宇宙", "Cosmo", "Cosmo"),
    ("能量体", "Energy Body", "Corpo de Energia"), ("结界", "Barrier", "Barreira"), ("保护罩", "Shield", "Escudo"), ("法阵", "Magic Circle", "Círculo Mágico"),
    ("星盘", "Star Disc", "Disco Estelar"), ("五行", "Five Elements", "Cinco Elementos"), ("般若", "Prajna", "Prajna"), ("佛光", "Buddha Light", "Luz de Buda"),
    ("宝轮", "Treasure Wheel", "Roda do Tesouro"), ("六道轮回", "Six Paths", "Seis Caminhos"), ("积尸气", "Sekishiki", "Sekishiki"), ("圣剑", "Excalibur", "Excalibur"),
    ("寒冰", "Frost", "Gelo"), ("极寒", "Absolute Zero", "Frio Absoluto"), ("冰霜", "Frost", "Geada"), ("炸弹", "Bomb", "Bomba"), ("冰阵", "Ice Circle", "Círculo de Gelo"),
    ("冰气", "Ice Aura", "Aura de Gelo"), ("冰花", "Ice Flower", "Flor de Gelo"), ("雪球", "Snowball", "Bola de Neve"), ("糖果", "Candy", "Doce"), ("礼物盒", "Gift Box", "Caixa de Presente"),
    ("礼物堆", "Gift Pile", "Pilha de Presentes"), ("花圈", "Wreath", "Guirlanda"), ("帽子", "Hat", "Chapéu"), ("礼栅栏", "Fence", "Cerca"), ("单手斧", "Hand Axe", "Machadinha"),
    ("剑", "Sword", "Espada"), ("箭", "Arrow", "Flecha"), ("枪", "Spear", "Lança"), ("盾牌", "Shield", "Escudo"), ("长枪", "Spear", "Lança"), ("大镰刀", "Scythe", "Foice"),
    ("竖琴", "Harp", "Harpa"), ("琴", "Harp", "Harpa"), ("嘴", "Mouth", "Boca"), ("墙面", "Wall", "Parede"), ("墙", "Wall", "Parede"), ("门", "Door", "Porta"),
    ("特效", "Effect", "Efeito"), ("陷阱", "Trap", "Armadilha"), ("领域", "Domain", "Domínio"), ("区域", "Area", "Área"), ("光球", "Light Orb", "Orbe de Luz"),
    ("绿球", "Green Orb", "Orbe Verde"), ("黑球", "Black Orb", "Orbe Negro"), ("紫水晶", "Amethyst", "Ametista"), ("水晶蝎", "Crystal Scorpion", "Escorpião de Cristal"),
    ("墨池", "Ink Pool", "Poço de Tinta"), ("天降神火", "Heavenly Fire", "Fogo Celeste"), ("神圣之光", "Holy Light", "Luz Sagrada"), ("善之心", "Good Heart", "Coração Bondoso"),
    ("次元缝隙", "Dimension Rift", "Fenda Dimensional"), ("耀斑", "Flare", "Labareda"), ("扇型", "Cone", "Cone"), ("持续伤害", "Damage over Time", "Dano Contínuo"),
    ("伤害降低", "Damage Reduction", "Redução de Dano"), ("大范围伤害球", "Big Damage Orb", "Orbe de Dano"), ("减速阵", "Slow Field", "Campo de Lentidão"),
    ("麻痹效果", "Paralysis", "Paralisia"), ("群攻", "AoE", "Área"), ("天赋", "Talent", "Talento"), ("训练", "Training", "Treino"), ("石块", "Rock", "Pedra"),
    ("三连", "Triple", "Tripla"), ("二连", "Double", "Dupla"), ("一连", "Single", "Simples"), ("垫脚石", "Stepping Stone", "Pedra de Apoio"), ("尖石头", "Sharp Rock", "Pedra Pontiaguda"),
    ("小石头", "Small Rock", "Pedra Pequena"), ("小箭", "Small Arrow", "Flecha Pequena"), ("大箭", "Big Arrow", "Flecha Grande"), ("背景图", "Backdrop", "Cenário"),
    ("升龙", "Rising Dragon", "Dragão Ascendente"), ("残破的", "Broken", "Quebrada"), ("崩塌的", "Collapsed", "Desmoronado"), ("散落的", "Scattered", "Espalhado"),
    ("墓穴", "Tomb", "Túmulo"), ("守卫", "Guard", "Guarda"), ("酒", "Wine", "Vinho"), ("猎", "Hunt", "Caça"), ("商", "Trade", "Comércio"), ("战", "War", "Guerra"),
    ("座椅", "Seat", "Assento"), ("商业区", "Market", "Área Comercial"), ("高级区", "Upper Area", "Área Superior"), ("主城", "Main City", "Cidade Principal"),
    ("一线天", "Narrow Pass", "Passagem Estreita"), ("断崖", "Cliff", "Penhasco"), ("方柱", "Square Pillar", "Pilar Quadrado"), ("河床", "Riverbed", "Leito do Rio"),
    ("永久", "Permanent", "Permanente"), ("完整", "Whole", "Inteira"), ("全裂", "Fully Cracked", "Totalmente Rachada"), ("破裂", "Cracked", "Rachada"), ("断裂", "Broken", "Partida"),
    ("破损", "Damaged", "Danificada"), ("破碎的", "Shattered", "Despedaçada"), ("发射的", "Fired", "Disparada"), ("尖头", "Tip", "Ponta"), ("缠住", "Bind", "Enlaçar"),
    ("荡下来", "Swing Down", "Balançar"), ("第一道门", "First Gate", "Primeiro Portão"), ("第二道门", "Second Gate", "Segundo Portão"), ("危险区域指示箭头", "Danger Arrow", "Seta de Perigo"),
    ("机关", "Mechanism", "Mecanismo"), ("完美密林区", "Dense Forest", "Floresta Densa"), ("密林", "Forest", "Floresta"), ("高", "Tall", "Alta"), ("区", "Area", "Área"),
    ("圣域高级区", "Sanctuary Upper Area", "Área Superior do Santuário"), ("媛星", "Star", "Estrela"), ("升级", "Upgrade", "Melhoria"), ("孟", "", ""), ("兰", "", ""), ("欧", "", ""),
    ("非", "", ""), ("胤", "", ""), ("凯", "", ""), ("雨", "", ""), ("冯", "", ""), ("范", "", ""), ("云", "", ""), ("奇", "", ""),
    ("仙女", "Andromeda", "Andrômeda"), ("天马", "Pegasus", "Pégaso"), ("天龙", "Dragon", "Dragão"), ("白鸟", "Cygnus", "Cisne"),
    ("双子", "Gemini", "Gêmeos"), ("天琴", "Lyra", "Lira"), ("翼龙", "Wyvern", "Wyvern"), ("狂风", "Tornado", "Tornado"), ("装备", "Gear", "Equipamento"),
    ("爆衣", "Torn Cloth", "Roupas Rasgadas"), ("说", "", ""), ("座", "", ""),
    ("左肩", "Left Shoulder", "Ombro Esquerdo"), ("右肩", "Right Shoulder", "Ombro Direito"), ("左腿", "Left Leg", "Perna Esquerda"), ("右腿", "Right Leg", "Perna Direita"),
    ("左手", "Left Hand", "Mão Esquerda"), ("右手", "Right Hand", "Mão Direita"), ("头", "Head", "Cabeça"), ("胸", "Chest", "Peito"), ("腰", "Waist", "Cintura"),
    ("左", "Left", "Esquerdo"), ("右", "Right", "Direito"), ("射手", "Sagittarius", "Sagitário"), ("逃亡", "Escape", "Fuga"), ("巨蟹宫", "Cancer Temple", "Casa de Câncer"),
    ("巨蟹", "Cancer", "Câncer"), ("狮子", "Leo", "Leão"), ("金牛", "Taurus", "Touro"), ("水瓶", "Aquarius", "Aquário"), ("天枰", "Libra", "Libra"), ("双鱼", "Pisces", "Peixes"),
    ("天蝎", "Scorpio", "Escorpião"), ("魔羯", "Capricorn", "Capricórnio"), ("白羊", "Aries", "Áries"), ("处女", "Virgo", "Virgem"),
    ("地狱火棺材", "Hellfire Coffin", "Caixão de Fogo Infernal"), ("地狱", "Hell", "Inferno"), ("石柱", "Stone Pillar", "Coluna de Pedra"), ("雅典", "Athens", "Atenas"),
    ("主子", "Master", "Mestre"), ("宫建筑", "Temple Building", "Construção da Casa"), ("建筑", "Building", "Construção"), ("组合", "Assembled", "Montado"),
    ("掉落", "Dropped", "Caído"), ("被遗忘", "Forgotten", "Esquecido"), ("斗士", "Fighter", "Lutador"), ("婚礼", "Wedding", "Casamento"), ("花", "Flower", "Flor"),
    ("滚石", "Rolling Stone", "Pedra Rolante"), ("悬浮台动作", "Floating Platform Action", "Plataforma Flutuante"), ("喷火", "Fire-breathing", "Cuspidor de Fogo"),
    ("装饰用花瓶", "Decorative Vase", "Vaso Decorativo"), ("冰冻地面", "Frozen Ground", "Chão Congelado"), ("冰冻", "Frozen", "Congelado"), ("火盆", "Brazier", "Braseiro"),
    ("画板", "Drawing Board", "Prancheta"), ("爆炸", "Explosion", "Explosão"), ("陆", "Land", "Terra"), ("镇", "Town", "Vila"), ("残", "Broken", "Quebrado"), ("底", "Base", "Base"),
    ("保卫", "Defend", "Defesa"), ("修普诺斯", "Hypnos", "Hypnos"), ("路拿", "Lune", "Lune"), ("刺神", "Stinger God", "Deus do Ferrão"), ("穷人", "Beggar", "Mendigo"),
    ("可罗素", "Clotho", "Cloto"), ("绿", "Green", "Verde"), ("粉", "Pink", "Rosa"), ("公主", "Princess", "Princesa"), ("神", "God", "Deus"), ("缩", "Shrunk", "Reduzido"),
    ("散", "Stray", "Errante"), ("王座", "Throne", "Trono"), ("王", "King", "Rei"), ("笋", "Shoot", "Broto"), ("牙", "Fang", "Presa"), ("前", "Front", "Frente"),
    ("火堆", "Bonfire", "Fogueira"), ("星光壁垒", "Starlight Barrier", "Barreira de Luz Estelar"), ("镜像", "Mirror Image", "Imagem Espelhada"), ("喷水", "Fountain", "Fonte"),
    ("冰雕", "Ice Sculpture", "Escultura de Gelo"), ("塔尔塔罗斯", "Tartarus", "Tártaro"), ("塔尔", "Tartarus", "Tártaro"), ("岩浆", "Lava", "Lava"), ("透明", "Transparent", "Transparente"),
    ("震动", "Shake", "Tremor"), ("隔断", "Partition", "Divisória"), ("涂好色", "Coloured", "Colorido"), ("眼", "Eye", "Olho"), ("被关", "Locked", "Trancado"), ("壶中", "In the Jar", "no Jarro"),
    ("粘液", "Slime", "Gosma"), ("球", "Orb", "Orbe"), ("冰柱", "Ice Pillar", "Coluna de Gelo"), ("声波", "Sound Wave", "Onda Sonora"), ("台碎裂效果", "Platform Shatter", "Plataforma Quebrando"),
    ("幕", "Curtain", "Cortina"), ("幽冥", "Netherworld", "Submundo"), ("移动", "Moving", "Móvel"), ("群体", "Group", "Grupo"), ("属性", "Attribute", "Atributo"), ("天降", "Falling", "Caindo do Céu"),
    ("炮台", "Turret", "Torreta"), ("蚀日", "Eclipse", "Eclipse"), ("罗盘禁锢", "Compass Bind", "Prisão da Bússola"), ("爆裂音符", "Bursting Note", "Nota Explosiva"), ("神击", "Divine Strike", "Golpe Divino"),
    ("火球", "Fireball", "Bola de Fogo"), ("外寒", "Outer Cold", "Frio Exterior"), ("暴", "Storm", "Tempestade"), ("雪", "Snow", "Neve"), ("鹰爪", "Eagle Claw", "Garra de Águia"), ("血球", "Blood Orb", "Orbe de Sangue"),
    ("效果", "Effect", "Efeito"), ("地", "Ground", "Chão"), ("冥火", "Hellfire", "Fogo Infernal"), ("泡泡", "Bubbles", "Bolhas"), ("水", "Water", "Água"), ("裂隙", "Rift", "Fenda"), ("天顶", "Zenith", "Zênite"),
    ("光效片", "Light Card", "Placa de Luz"), ("防御阵", "Defense Formation", "Formação Defensiva"), ("鬼苍焰", "Ghost Flame", "Chama Fantasma"), ("恶", "Evil", "Mal"), ("心", "Heart", "Coração"), ("老", "Old", "Velho"),
    ("部族成员", "Tribe Member", "Membro da Tribo"), ("巨型", "Giant", "Gigante"), ("灵孩", "Spirit Child", "Criança Espírito"), ("剧毒", "Venomous", "Venenoso"), ("子", "Child", "Filho"), ("静力", "Static", "Estático"),
    ("人", "Person", "Pessoa"), ("破", "Broken", "Quebrado"), ("冰火", "Ice and Fire", "Gelo e Fogo"), ("巨", "Giant", "Gigante"), ("西伯利亚", "Siberia", "Sibéria"), ("竞技场", "Arena", "Arena"), ("基", "Base", "Base"),
    ("立式", "Standing", "Vertical"), ("主", "Main", "Principal"), ("断开", "Split", "Partido"), ("活动", "Event", "Evento"), ("棒子", "Staff", "Bastão"), ("便衣", "Casual", "Roupa Comum"), ("遗迹", "Ruins", "Ruínas"),
    ("将军", "General", "General"), ("美", "Beautiful", "Bela"), ("像", "Statue", "Estátua"), ("后", "Back", "Traseira"), ("三环", "Three Rings", "Três Anéis"), ("火", "Fire", "Fogo"), ("第三", "Third", "Terceiro"),
    ("第二", "Second", "Segundo"), ("完美", "Perfect", "Perfeito"), ("处", "Place", "Lugar"), ("羊", "Ram", "Carneiro"), ("前代", "Previous", "Anterior"), ("卵群", "Egg Cluster", "Ninhada"), ("部分", "Part", "Parte"),
    ("树桩状态", "Stump State", "Estado de Tronco"), ("出现", "Appear", "Aparição"), ("食人", "Man-eating", "Devorador"), ("若虫", "Nymph", "Ninfa"), ("尤利缇斯", "Eurydice", "Eurídice"), ("石化", "Petrified", "Petrificada"),
    ("土", "Earth", "Terra"), ("两半", "Halves", "Metades"), ("动画房间", "Cutscene Room", "Sala da Cinemática"), ("砖", "Brick", "Tijolo"), ("矿车", "Mine Cart", "Vagonete"),
    ("鲁邦", "Lupin", "Lupin"), ("鲁琪", "Luise", "Luise"), ("泰勒", "Taylor", "Taylor"), ("高龙巴", "Colomba", "Colomba"), ("奥古斯塔", "Augusto", "Augusto"), ("达里乌斯", "Darius", "Darius"), ("希尔汗", "Sher-Khan", "Sher-Khan"),
    ("尼亚", "Nya", "Nya"), ("云峰", "Jaffet", "Jaffet"), ("卡夫卡", "Kafka", "Kafka"), ("史东", "Stone", "Stone"), ("伊索尔", "Isolde", "Isolde"), ("贝努", "Bennu", "Bennu"),
    ("过场动画", "Cutscene", "Cinemática"), ("级别活动", "Level Event", "Evento de nível"), ("大厅", "Hall", "Salão"), ("战斗", "Battle", "Batalha"),
    ("通用", "Generic", "Genérico"), ("新", "New", "Novo"), ("旧", "Old", "Velho"), ("大", "Big", "Grande"), ("小", "Small", "Pequeno"), ("高级", "Advanced", "Avançado"),
    ("中级", "Intermediate", "Intermediário"), ("初级", "Basic", "Básico"), ("低级", "Low", "Baixo"), ("级", "Level", "Nível"), ("红色", "Red", "Vermelho"), ("蓝色", "Blue", "Azul"),
    ("黄色", "Yellow", "Amarelo"), ("绿色", "Green", "Verde"), ("紫色", "Purple", "Roxo"), ("青色", "Cyan", "Ciano"), ("粉色", "Pink", "Rosa"), ("白色", "White", "Branco"),
    ("黑色", "Black", "Preto"), ("红", "Red", "Vermelho"), ("蓝", "Blue", "Azul"), ("黄", "Yellow", "Amarelo"), ("白", "White", "Branco"), ("黑", "Black", "Preto"),
    ("白金", "Platinum", "Platina"), ("变色", "Recolored", "Recolorido"), ("裙子", "Skirt", "Saia"), ("连衣裙", "Dress", "Vestido"), ("肥", "Fat", "Gordo"), ("瘦", "Thin", "Magro"),
    ("壮", "Strong", "Forte"), ("男", "Male", "Masculino"), ("女", "Female", "Feminino"), ("版", "Version", "Versão"), ("无", "Without", "Sem"), ("没有", "Without", "Sem"),
    ("之", "of", "de"), ("的", "of", "de"), ("和", "and", "e"),
]
GLOSSARY.sort(key=lambda t: -len(t[0]))
CONSTELLATIONS_EN = {en for z, en, _pt in GLOSSARY if z.endswith("座") or z.endswith("星")}
CHARACTERS_EN = {"Seiya", "Shiryu", "Hyoga", "Shun", "Ikki", "Nachi", "Geki", "Ban", "Ichi", "Jabu", "June", "Mu", "Aldebaran", "Saga",
                 "Deathmask", "Aiolia", "Shaka", "Dohko", "Milo", "Aiolos", "Shura", "Camus", "Aphrodite", "Shion", "Marin", "Shaina",
                 "Orphee", "Kanon", "Sorrento", "Baian", "Krishna", "Isaak", "Io", "Kasa", "Thetis", "Rhadamanthys", "Minos", "Aiacos",
                 "Lune", "Rock", "Iwan", "Myu", "Zelos", "Gerald", "Raimi", "Siegfried", "Hagen", "Alberich", "Fenrir", "Syd", "Bud", "Mime"}

CJK = re.compile(r"[㐀-鿿]")


def load_game_names(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _clean(zh):
    zh = zh.replace("_", " ").replace("【", "").replace("】", "").replace("·", " ")
    zh = re.sub(r"\s*\d+\s*$", "", zh)  # variant numbers: 撒加1
    return zh.strip()


LEVEL = re.compile(r"(\d+)级")


def glossary_translate(zh):
    en_parts, pt_parts = [], []
    rest = LEVEL.sub(lambda m: " Level %s |nível %s " % (m.group(1), m.group(1)), zh)
    out = []  # (start, len, en, pt)
    i = 0
    while i < len(rest):
        hit = None
        for z, en, pt in GLOSSARY:
            if rest.startswith(z, i):
                hit = (z, en, pt)
                break
        if hit:
            out.append((hit[1], hit[2]))
            i += len(hit[0])
        else:
            ch = rest[i]
            if CJK.match(ch):
                # collect a run of unknown Chinese characters
                j = i
                while j < len(rest) and CJK.match(rest[j]) and not any(rest.startswith(z, j) for z, _e, _p in GLOSSARY):
                    j += 1
                run = rest[i:j]
                roman = "".join(w.capitalize() for w in lazy_pinyin(run)) if lazy_pinyin else run
                out.append((roman, run))
                i = j
            else:
                j = i
                while j < len(rest) and not CJK.match(rest[j]):
                    j += 1
                tok = rest[i:j]
                if "|" in tok:  # " Level N |nível N " marker from LEVEL
                    en_tok, pt_tok = tok.split("|", 1)
                    out.append((en_tok, pt_tok))
                else:
                    out.append((tok, tok))
                i = j
    out = [(en, pt) for en, pt in out if (en or pt) and (en.strip() or pt.strip() or en == " ")]
    # Portuguese order: "<constellation> <character>" -> "<character> de <constellation>"
    if len(out) >= 2 and out[0][0] in CONSTELLATIONS_EN and out[1][0] in CHARACTERS_EN:
        out = [(out[1][0] + " " + out[0][0], out[1][1] + " de " + out[0][1])] + out[2:]
    for en, pt in out:
        en_parts.append(en)
        pt_parts.append(pt)

    def join(parts):
        s = ""
        for p in parts:
            if p in " -" or not s or s.endswith(" ") or p.startswith(" "):
                s += p
            else:
                s += " " + p
        return re.sub(r"\s+", " ", s).strip()

    return join(en_parts), join(pt_parts)


def translate(zh, game_names=None):
    """Return {"zh", "en", "pt", "source"} for an asset name."""
    clean = _clean(zh)
    game_names = game_names or {}
    en, pt = glossary_translate(clean)
    source = "glossary"
    for cand in (zh, clean):
        hit = game_names.get(cand)
        if hit and hit.get("pt") and hit.get("src") != "data_item":
            pt = hit["pt"]
            source = "game"
            if CJK.search(en) or (lazy_pinyin and not en.isascii()):
                en = hit.get("en") or en
            break
    return {"zh": zh, "en": en, "pt": pt_polish(pt), "source": source}


PT_RULES = [
    (r"^Ouro (.+) Armadura Divina$", r"Armadura Divina de \1 (dourada)"),
    (r"^(.+) Armadura Divina$", r"Armadura Divina de \1"),
    (r"^Prata (.+)$", r"\1 de Prata"),
    (r"^Ouro (.+)$", r"\1 (dourada)"),
    (r"^Sapuris (.+)$", r"Sapuris de \1"),
    (r"^Espectro (.+)$", r"Espectro de \1"),
    (r"^Marina (.+) Escama(.*)$", r"Escama de \1\2"),
    (r"^Marina (.+)$", r"Marina de \1"),
    (r"^(.+) Equipamento Inicial(.*)$", r"Equipamento inicial de \1\2"),
    (r"^(.+) Roupa de Treino$", r"Roupa de treino de \1"),
    (r"^Negro (.+)$", r"\1 Negro"),
]


def pt_polish(pt):
    for pat, rep in PT_RULES:
        new = re.sub(pat, rep, pt)
        if new != pt:
            return new
    return pt


def slug(text):
    """kebab-case ASCII file name, like the Cloth Schemes library."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text or "unnamed"


if __name__ == "__main__":
    names = load_game_names(sys.argv[1]) if len(sys.argv) > 1 else {}
    for arg in sys.argv[2:]:
        t = translate(arg, names)
        print("%s -> %s | %s | %s  [%s]" % (arg, t["en"], t["pt"], slug(t["en"]), t["source"]))
