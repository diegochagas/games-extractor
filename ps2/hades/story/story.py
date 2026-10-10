#!/usr/bin/env python3
"""The story of The Hades as text: the scripts of text/scenes.json in chapter order with the
English, Japanese and translated Portuguese of every line, the speaker from the voice file and
the lines corrected by hand in fixes.json (key = voice file without extension, or "chapter:line").

usage: story.py DUMP_DIR [--report]     -> DUMP_DIR/text/story.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
from hades import names  # noqa: E402
import translate  # noqa: E402

GROUPS = [
    ('main', r'^\d{4}$', 'A Guerra Santa contra Hades'),
    ('judges', r'^0[amr]\d\d$', 'Os três Juízes'),
    ('legend', r'^1\d{3}$', 'Lenda dos Cavaleiros'),
    ('digest', r'^2\d{3}$', 'Resumos narrados'),
]
JUDGES = {'0r': 'Radamanthys', '0a': 'Aiacos', '0m': 'Minos'}


def clean(text):
    return re.sub(r'\s+', ' ', (text or '').replace('\x01', ' ')).strip()


# word order and gender slips the model makes with the English name forms ("Aries Mu", "Pegasus Seiya")
POLISH = [
    (r'\b(Áries|Touro|Gêmeos|Câncer|Leão|Virgem|Libra|Escorpião|Sagitário|Capricórnio|Aquário|Peixes|Pégaso|Dragão|Cisne|Andrômeda|Fênix|Lira|Águia|Cobra|Wyvern|Garuda|Griffon) (Mu|Aldebaran|Saga|Kanon|Máscara da Morte|Aiolia|Shaka|Dohko|Milo|Aiolos|Shura|Camus|Afrodite|Shion|Seiya|Shiryu|Hyoga|Shun|Ikki|Orfeu|Marin|Shina|Radamanthys|Aiacos|Minos)\b', r'\2 de \1'),
    (r'\bna Conflito\b', 'no Conflito'), (r'\bo Conflito das Doze Casas\b', 'a Batalha das Doze Casas'), (r'\bConflito das Doze Casas\b', 'Batalha das Doze Casas'),
    (r'\bSenhor Hades\b', 'Senhor Hades'), (r'\bMephisto\b', 'Máscara da Morte'), (r'\bRhadamanthys\b', 'Radamanthys'), (r'\bOrpheus\b', 'Orfeu'),
    (r'\bShaina\b', 'Shina'), (r'\bAphrodite\b', 'Afrodite'), (r'\bMiro\b', 'Milo'), (r'\bSpecters?\b', 'Espectros'), (r'\bSurplice\b', 'Sapuri'),
    (r'\bAthena\b', 'Atena'), (r'\bSanctuary\b', 'Santuário'), (r'\bCosmos\b', 'Cosmo'), (r'\bAgora, agora,', 'Calma, calma,'),
]


def polish(text):
    for pat, rep in POLISH:
        text = re.sub(pat, rep, text)
    return text


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    dump = os.path.abspath(argv[1])
    text = os.path.join(dump, 'text')
    with open(os.path.join(text, 'scenes.json'), encoding='utf-8') as f:
        scenes = json.load(f)
    cache = translate.load_cache(dump)
    fixes = {}
    fp = os.path.join(HERE, 'fixes.json')
    if os.path.exists(fp):
        with open(fp, encoding='utf-8') as f:
            fixes = {k.lower(): v for k, v in json.load(f).items() if not k.startswith('_')}
    by = {}
    for s in scenes:
        by.setdefault(s['chapter'], {})[s['part'] or ''] = s
    chapters = []
    stats = {'lines': 0, 'translated': 0, 'fixed': 0, 'untranslated': 0}
    for cid in sorted(by, key=lambda c: (re.sub(r'\d', '9', c) if not c.isdigit() else '0', c)):
        parts = by[cid]
        group = next((g for g, pat, _ in GROUPS if re.match(pat, cid)), 'other')
        if group == 'main':
            title = 'Capítulo %d' % int(cid)
        elif group == 'judges':
            title = '%s, cena %d' % (JUDGES.get(cid[:2], cid), int(cid[2:]) + 1)
        elif group == 'legend':
            title = 'Lenda dos Cavaleiros, cena %d' % (int(cid) - 999)
        elif group == 'digest':
            title = 'Resumo %d' % (int(cid) - 1999)
        else:
            title = cid
        blocks = []
        for part in sorted(parts, key=lambda p: (p != '', p)):
            s = parts[part]
            lines = []
            for i, ln in enumerate(s['lines']):
                en, jp = clean(ln.get('text_uk')), clean(ln.get('text_jp'))
                code, speaker = names.speaker(ln['voice'])
                key = (ln['voice'] or '')[:-4].lower()
                fix = fixes.get(key) or fixes.get('%s:%s' % (s['script'][:-4].lower(), ln['line']))
                if isinstance(fix, dict):
                    pt, source = fix.get('text', ''), 'fixed'
                    speaker = fix.get('speaker') or speaker
                elif isinstance(fix, str):
                    pt, source = fix, 'fixed'
                elif en and translate.key_of(en) in cache:
                    pt, source = polish(cache[translate.key_of(en)].replace('\n', ' ')), 'ollama'
                else:
                    pt, source = '', 'untranslated' if en else 'voice-only'
                stats['lines'] += 1
                stats[{'fixed': 'fixed', 'ollama': 'translated'}.get(source, 'untranslated' if en else 'translated')] += 1 if source != 'voice-only' else 0
                lines.append({'line': ln['line'], 'voice': ln['voice'], 'speaker_code': code, 'speaker': speaker,
                              'en': en, 'jp': jp, 'pt': pt, 'source': source, 'page': ln.get('page')})
            blocks.append({'script': s['script'], 'part': part, 'pages': len(s['pages']), 'bgm': s['bgm'],
                           'cast': s['cast'], 'lines': lines})
        chapters.append({'id': cid, 'group': group, 'title': title, 'blocks': blocks})
    story = {'chapters': chapters, 'groups': [(g, lbl) for g, _p, lbl in GROUPS], 'stats': stats}
    with open(os.path.join(text, 'story.json'), 'w', encoding='utf-8') as f:
        json.dump(story, f, ensure_ascii=False, indent=1)
    print('STATS', json.dumps(stats))
    if '--report' in argv:
        for ch in chapters:
            print('== %s (%s)' % (ch['title'], ch['id']))
            for b in ch['blocks']:
                for ln in b['lines']:
                    print('  %-24s %-18s %s  <<  %s' % ((ln['voice'] or '')[:-4], ln['speaker'], ln['pt'], ln['en']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
