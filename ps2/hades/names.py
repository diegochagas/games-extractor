"""Names used by the Saint Seiya: The Hades tools (European disc: Japanese voices, text in
English, French, Italian, Spanish, German and Japanese). Portuguese names follow the Brazilian
dub of the series (Máscara da Morte, Radamanthys...).

ROSTER: the 49 fighters in the order of the disc (files NN.gmi/NN.tpl, voice files story_NN_*,
the unlock list of msg_submenu_uk.bin). EXTRA: the `eNN` voice codes of the scenes.
"""
import re

ROSTER = [
    ('00', 'Seiya', 'Seiya de Pégaso', 'seiya'), ('01', 'Shiryu', 'Shiryu de Dragão', 'shiryu'),
    ('02', 'Hyoga', 'Hyoga de Cisne', 'hyoga'), ('03', 'Shun', 'Shun de Andrômeda', 'shun'),
    ('04', 'Ikki', 'Ikki de Fênix', 'ikki'),
    ('05', 'Seiya (Armadura Final)', 'Seiya com a Armadura Final de Pégaso', 'seiya-armadura-final'),
    ('06', 'Shiryu (Armadura Final)', 'Shiryu com a Armadura Final de Dragão', 'shiryu-armadura-final'),
    ('07', 'Hyoga (Armadura Final)', 'Hyoga com a Armadura Final de Cisne', 'hyoga-armadura-final'),
    ('08', 'Shun (Armadura Final)', 'Shun com a Armadura Final de Andrômeda', 'shun-armadura-final'),
    ('09', 'Ikki (Armadura Final)', 'Ikki com a Armadura Final de Fênix', 'ikki-armadura-final'),
    ('10', 'Seiya (primeira Armadura)', 'Seiya com a primeira Armadura de Pégaso', 'seiya-primeira-armadura'),
    ('11', 'Shiryu (primeira Armadura)', 'Shiryu com a primeira Armadura de Dragão', 'shiryu-primeira-armadura'),
    ('12', 'Hyoga (primeira Armadura)', 'Hyoga com a primeira Armadura de Cisne', 'hyoga-primeira-armadura'),
    ('13', 'Shun (primeira Armadura)', 'Shun com a primeira Armadura de Andrômeda', 'shun-primeira-armadura'),
    ('14', 'Ikki (primeira Armadura)', 'Ikki com a primeira Armadura de Fênix', 'ikki-primeira-armadura'),
    ('15', 'Seiya (Sagitário)', 'Seiya com a Armadura de Sagitário', 'seiya-sagitario'),
    ('16', 'Shiryu (Libra)', 'Shiryu com a Armadura de Libra', 'shiryu-libra'),
    ('17', 'Hyoga (Aquário)', 'Hyoga com a Armadura de Aquário', 'hyoga-aquario'),
    ('18', 'Mu', 'Mu de Áries', 'mu'), ('19', 'Aldebaran', 'Aldebaran de Touro', 'aldebaran'),
    ('20', 'Cavaleiro de Gêmeos', 'Cavaleiro de Gêmeos (a Armadura vazia)', 'cavaleiro-de-gemeos'),
    ('21', 'Máscara da Morte', 'Máscara da Morte de Câncer', 'mascara-da-morte'),
    ('22', 'Aiolia', 'Aiolia de Leão', 'aiolia'), ('23', 'Shaka', 'Shaka de Virgem', 'shaka'),
    ('24', 'Dohko', 'Dohko de Libra', 'dohko'), ('25', 'Milo', 'Milo de Escorpião', 'milo'),
    ('26', 'Aiolos', 'Aiolos de Sagitário', 'aiolos'), ('27', 'Shura', 'Shura de Capricórnio', 'shura'),
    ('28', 'Camus', 'Camus de Aquário', 'camus'), ('29', 'Afrodite', 'Afrodite de Peixes', 'afrodite'),
    ('30', 'Saga', 'Saga de Gêmeos', 'saga'), ('31', 'Kanon', 'Kanon de Gêmeos', 'kanon'),
    ('32', 'Orfeu', 'Orfeu de Lira', 'orfeu'), ('33', 'Marin', 'Marin de Águia', 'marin'),
    ('34', 'Shina', 'Shina de Cobra', 'shina'), ('35', 'Shion', 'Shion de Áries, o Grande Mestre', 'shion'),
    ('36', 'Máscara da Morte (Sapuri)', 'Máscara da Morte com o Sapuri (Espectro)', 'mascara-da-morte-sapuri'),
    ('37', 'Afrodite (Sapuri)', 'Afrodite com o Sapuri (Espectro)', 'afrodite-sapuri'),
    ('38', 'Shura (Sapuri)', 'Shura com o Sapuri (Espectro)', 'shura-sapuri'),
    ('39', 'Camus (Sapuri)', 'Camus com o Sapuri (Espectro)', 'camus-sapuri'),
    ('40', 'Saga (Sapuri)', 'Saga com o Sapuri (Espectro)', 'saga-sapuri'),
    ('41', 'Radamanthys', 'Radamanthys de Wyvern', 'radamanthys'), ('42', 'Aiacos', 'Aiacos de Garuda', 'aiacos'),
    ('43', 'Minos', 'Minos de Griffon', 'minos'),
    ('44', 'Seiya (Bronze Dourado)', 'Seiya com a Armadura de Bronze Dourada', 'seiya-bronze-dourado'),
    ('45', 'Shiryu (Bronze Dourado)', 'Shiryu com a Armadura de Bronze Dourada', 'shiryu-bronze-dourado'),
    ('46', 'Hyoga (Bronze Dourado)', 'Hyoga com a Armadura de Bronze Dourada', 'hyoga-bronze-dourado'),
    ('47', 'Shun (Bronze Dourado)', 'Shun com a Armadura de Bronze Dourada', 'shun-bronze-dourado'),
    ('48', 'Ikki (Bronze Dourado)', 'Ikki com a Armadura de Bronze Dourada', 'ikki-bronze-dourado'),
]
BY_NUMBER = {r[0]: r for r in ROSTER}
# voice codes eNN of the scenes (identified by what the lines say) — filled in as they are checked
EXTRA = {'e00': 'Saori Kido', 'e01': 'Pandora', 'e02': 'Mestre Ancião (Dohko)', 'e03': 'Hades'}
PICTURE_EXTRA = {'e00': 'Saori Kido', 'e01': 'Pandora', 'e02': 'Mestre Ancião (Dohko)', 'e03': 'Hades'}
LANGUAGES = {'us': 'ingles-eua', 'uk': 'ingles', 'jp': 'japones', 'it': 'italiano', 'du': 'alemao',
             'fr': 'frances', 'sp': 'espanhol'}
# the collection's eight "story demos"
DEMOS = ['A New Holy War', 'The Ancient Warrior', 'Moment of Vacillation', 'Shaking Sanctuary', 'The Cloth of Athena',
         'Morning of Resolution', "Orpheus' Sad Requiem", 'Road to Judecca']
DEMOS_PT = ['Uma nova Guerra Santa', 'O antigo guerreiro', 'Momento de hesitação', 'O Santuário abalado',
            'A Armadura de Atena', 'A manhã da decisão', 'O triste réquiem de Orfeu', 'O caminho para Judeca']


def speaker(voice_file):
    """(code, name) of the character who speaks a story voice file (story_NN_... / story_eNN_...)."""
    m = re.match(r'(?i)story_([ev]?\d+)_', voice_file or '')
    if not m:
        return '', ''
    code = m.group(1).lower()
    if code in BY_NUMBER:
        return code, BY_NUMBER[code][1]
    if code.startswith('v'):
        return code, 'Vários'
    return code, EXTRA.get(code) or ('Personagem %s' % code)


def slug(text):
    t = text.lower()
    for a, b in (('á', 'a'), ('â', 'a'), ('ã', 'a'), ('à', 'a'), ('é', 'e'), ('ê', 'e'), ('í', 'i'), ('ó', 'o'),
                 ('ô', 'o'), ('õ', 'o'), ('ú', 'u'), ('ç', 'c')):
        t = t.replace(a, b)
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    return t or 'x'
