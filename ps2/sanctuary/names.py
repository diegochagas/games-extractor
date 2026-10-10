"""Names used by the Saint Seiya: The Sanctuary tools (Brazilian disc, so the Portuguese names
of the game itself: msg_holiday_collection.bin, msg_holiday_voice_index.bin, nametpl_*.tpl).

ROSTER: the 24 fighters in the order of the disc (files NN.tpl, charstandNNa.tm2, nametpl entry
NN, voice files story_NN_*). EXTRA: the `eNN` voice codes (people who only speak in the scenes)
and the e0/e1 picture codes.
"""
import re

ROSTER = [
    ('00', 'Seiya', 'Seiya de Pégaso', 'seiya'), ('01', 'Shiryu', 'Shiryu de Dragão', 'shiryu'),
    ('02', 'Hyoga', 'Hyoga de Cisne', 'hyoga'), ('03', 'Shun', 'Shun de Andrômeda', 'shun'),
    ('04', 'Ikki', 'Ikki de Fênix', 'ikki'), ('05', 'Aldebaran', 'Aldebaran de Touro', 'aldebaran'),
    ('06', '???', 'Cavaleiro de Gêmeos (ilusão de Saga)', 'gemeos-ilusao'),
    ('07', 'Máscara da Morte', 'Máscara da Morte de Câncer', 'mascara-da-morte'),
    ('08', 'Aiolia', 'Aiolia de Leão', 'aiolia'), ('09', 'Shaka', 'Shaka de Virgem', 'shaka'),
    ('10', 'Milo', 'Milo de Escorpião', 'milo'), ('11', 'Shura', 'Shura de Capricórnio', 'shura'),
    ('12', 'Camus', 'Camus de Aquário', 'camus'), ('13', 'Afrodite', 'Afrodite de Peixes', 'afrodite'),
    ('14', 'Saga', 'Saga de Gêmeos', 'saga'), ('15', 'Mu', 'Mu de Áries', 'mu'),
    ('16', 'Marin', 'Marin de Águia', 'marin'), ('17', 'Shina', 'Shina de Cobra', 'shina'),
    ('18', 'Dohko', 'Dohko de Libra', 'dohko'),
    ('19', 'Seiya (Sagitário)', 'Seiya com a Armadura de Sagitário', 'seiya-sagitario'),
    ('20', 'Misty', 'Misty de Lagarto', 'misty'), ('21', 'Shô', 'Shô da Armadura do Céu', 'sho'),
    ('22', 'Daichi', 'Daichi da Armadura da Terra', 'daichi'), ('23', 'Ushô', 'Ushô da Armadura do Mar', 'usho'),
]
BY_NUMBER = {r[0]: r for r in ROSTER}
# voice codes eNN of the scenes, identified by what the lines say
EXTRA = {'e00': 'Saori Kido', 'e01': 'Saga (voz de Gêmeos)', 'e04': 'Cássius', 'e06': 'Narrador', 'e11': 'Shunrei'}
PICTURE_EXTRA = {'e0': 'Mestre Ares', 'e1': 'Saori Kido'}
LANGUAGES = {'us': 'portugues', 'uk': 'ingles', 'jp': 'japones', 'it': 'italiano', 'du': 'alemao',
             'fr': 'frances', 'sp': 'espanhol'}
# story scenes in the order of the game's own list (msg_holiday_demo.bin): script -> list entry
STORY_SCRIPTS = ['demo00', 'demo01', 'demo06', 'demo07', 'demo08', 'demo09', 'demo10', 'demo11', 'demo12', 'demo13',
                 'demo14', 'demo15', 'demo16', 'demo17', 'demo18', 'demo19', 'demo20', 'demo21', 'demo22', 'demo23',
                 'demo24', 'demo25', 'demo26', 'demo27', 'demo28', 'demo29', 'demo30', 'demo31', 'demo33', 'demo35']
IF_SCRIPTS = ['if%02d' % n for n in range(1, 11)]
POPE_SCRIPTS = ['pope01', 'pope02', 'pope03']
# title cards: titleNN.bin (plate + a still of the scene) and subtitle_NN pictures
TITLE_CARDS = {'demo08': 1, 'demo10': 2, 'demo12': 3, 'demo14': 4, 'demo16': 5, 'demo18': 6, 'demo20': 7, 'demo21': 8,
               'demo23': 9, 'demo24': 10, 'demo26': 11, 'demo28': 12, 'demo30': 13, 'if01': 14, 'if03': 15,
               'if05': 16, 'if07': 17, 'if09': 18}
TITLES_JP = {'demo06': '決戦！黄金十二宮', 'demo08': '黄金の野牛！アルデバラン！', 'demo10': '双子座！幻影の迷宮！！',
             'demo12': '師弟対決！', 'demo14': '生と死の狭間で', 'demo16': '目覚めよアイオリア！',
             'demo18': '不死鳥はよみがえる！', 'demo20': '天秤座の剣', 'demo21': 'スカーレットニードル！最後のアンタレス',
             'demo23': 'アイオロスの遺志', 'demo24': '禁断の廬山亢龍覇！', 'demo26': '絶対零度の闘い',
             'demo28': '爆発！ネビュラストリーム！', 'demo30': '我こそは神！サガ二つの顔！！',
             'if01': '非情の刺客！ムウ対デスマスク', 'if03': '獅子宮に待つ不死鳥', 'if05': 'アイオロスからの試練',
             'if07': '天秤座を身につける者', 'if09': '出現！新たなる宮！'}
# the twelve temples, in the order of the titleNN name plates (title01..) is not needed: scene order is
TEMPLES = ['Áries', 'Touro', 'Gêmeos', 'Câncer', 'Leão', 'Virgem', 'Libra', 'Escorpião', 'Sagitário',
           'Capricórnio', 'Aquário', 'Peixes']


def speaker(voice_file):
    """(code, name) of the character who speaks a story voice file (story_NN_... / story_eNN_...)."""
    m = re.match(r'(?i)(?:story|pope)_?(e?\d+)_', voice_file or '')
    if not m:
        return '', ''
    code = m.group(1).lower()
    if code in BY_NUMBER:
        return code, BY_NUMBER[code][1]
    return code, EXTRA.get(code) or ('Personagem %s' % code)


def slug(text):
    t = text.lower()
    for a, b in (('á', 'a'), ('â', 'a'), ('ã', 'a'), ('à', 'a'), ('é', 'e'), ('ê', 'e'), ('í', 'i'), ('ó', 'o'),
                 ('ô', 'o'), ('õ', 'o'), ('ú', 'u'), ('ç', 'c')):
        t = t.replace(a, b)
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    return t or 'x'
