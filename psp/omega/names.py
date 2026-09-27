"""Saint Seiya Omega Ultimate Cosmo: character codes used in file names and scripts.

The index is the character number of the event scripts (= the folder number of
event/sound/NN for the arcade lines); `jp` follows the game text, `romaji` keeps the original
Japanese names in the spelling of the saintseiyacloths site.
"""

CHARACTERS = [
    # code, jp, romaji, constellation / rank (jp), (pt)
    ('kog', '光牙', 'Kouga', '天馬座（ペガサス）の青銅聖闘士', 'Cavaleiro de Bronze de Pégaso'),
    ('yun', 'ユナ', 'Yuna', '鷲座（アクィラ）の青銅聖闘士', 'Amazona de Bronze de Águia'),
    ('ryo', '龍峰', 'Ryuho', '龍座（ドラゴン）の青銅聖闘士', 'Cavaleiro de Bronze de Dragão'),
    ('som', '蒼摩', 'Souma', '仔獅子座（ライオネット）の青銅聖闘士', 'Cavaleiro de Bronze de Leão Menor'),
    ('ede', 'エデン', 'Eden', 'オリオン星座の青銅聖闘士', 'Cavaleiro de Bronze de Órion'),
    ('hat', '栄斗', 'Haruto', '狼座（ウルフ）の青銅聖闘士', 'Cavaleiro de Bronze de Lobo'),
    ('sey', '星矢', 'Seiya', '射手座（サジタリアス）の黄金聖闘士', 'Cavaleiro de Ouro de Sagitário'),
    ('shn', 'シャイナ', 'Shaina', '蛇遣い座（オピュクス）の白銀聖闘士', 'Amazona de Prata de Ofiúco'),
    ('ion', 'イオニア', 'Ionia', '山羊座（カプリコーン）の黄金聖闘士', 'Cavaleiro de Ouro de Capricórnio'),
    ('soi', 'ソニア', 'Sonia', '雀蜂（ホーネット）のハイマーシアン', 'Alta Marciana de Vespa'),
    ('mik', 'ミケーネ', 'Mycenae', '獅子座（レオ）の黄金聖闘士', 'Cavaleiro de Ouro de Leão'),
    ('gen', '玄武', 'Genbu', '天秤座（ライブラ）の黄金聖闘士', 'Cavaleiro de Ouro de Libra'),
    ('kik', '貴鬼', 'Kiki', '牡羊座（アリエス）の黄金聖闘士', 'Cavaleiro de Ouro de Áries'),
    ('iti', '市', 'Ichi', '水蛇座（ヒドラス）の白銀聖闘士', 'Cavaleiro de Prata de Hidra'),
    ('jyu', 'ポセイドン', 'Poseidon', '海皇（ジュリアン・ソロ）', 'Imperador dos Mares (Julian Solo)'),
    ('sot', 'ソレント', 'Sorento', '海魔女（セイレーン）の海将軍', 'General Marina de Sirene'),
    ('shu', '瞬', 'Shun', 'アンドロメダ座の青銅聖闘士', 'Cavaleiro de Bronze de Andrômeda'),
    ('pab', 'パブリーン', 'Pavlin', '孔雀座（ピーコック）の白銀聖闘士', 'Amazona de Prata de Pavão'),
    ('kogv2', '光牙', 'Kouga', 'トリトンの鱗衣', 'com a Escama de Tritão'),
    ('yunv2', 'ユナ', 'Yuna', 'トリトンの鱗衣', 'com a Escama de Tritão'),
    ('ryov2', '龍峰', 'Ryuho', 'トリトンの鱗衣', 'com a Escama de Tritão'),
    ('somv2', '蒼摩', 'Souma', 'トリトンの鱗衣', 'com a Escama de Tritão'),
    ('edev2', 'エデン', 'Eden', 'トリトンの鱗衣', 'com a Escama de Tritão'),
    ('hatv2', '栄斗', 'Haruto', 'トリトンの鱗衣', 'com a Escama de Tritão'),
]
CODES = [c[0] for c in CHARACTERS]
BY_CODE = {c[0]: c for c in CHARACTERS}

# voices that are not playable characters; in the scripts they are characters 24, 25 and 26
EXTRA_VOICES = {
    'ate': ('アテナ', 'Atena'),
    'who': ('？？？', '???'),
    'man': ('男', 'Homem'),
}
SCRIPT_CODES = CODES + ['ate', 'who', 'man']


def speaker(code):
    """(jp, romaji) of a voice/character code."""
    code = code.lower()
    if code in BY_CODE:
        return BY_CODE[code][1], BY_CODE[code][2]
    if code in EXTRA_VOICES:
        return EXTRA_VOICES[code]
    return code, code
