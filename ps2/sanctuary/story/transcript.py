#!/usr/bin/env python3
"""The story of the game as text: the scene scripts (text/scenes.json) in the order of the game's
own scene list, with the Portuguese transcription of every voice (text/voices/*.pt.json, written by
psp/transcribe.py with faster-whisper), the speaker taken from the voice file name, the
recogniser's usual slips fixed (GLOSSARY) and the lines corrected by hand in fixes.json.

usage: transcript.py DUMP_DIR [--report]     -> DUMP_DIR/text/story.json
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sanctuary import names  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
# (pattern, replacement): names and terms faster-whisper gets wrong in the Brazilian dub
GLOSSARY = [
    (r'\b[Aa]rias\b', 'Áries'), (r'\bChina\b', 'Shina'), (r'\bSheena\b', 'Shina'), (r'\bXina\b', 'Shina'),
    (r'\b[Cc]êia\b', 'Seiya'), (r'\b[Cc]eia\b', 'Seiya'), (r'\bXeia\b', 'Seiya'), (r'\bAiorus\b', 'Aiolos'),
    (r'\bA Iurus\b', 'Aiolos'), (r'\bIurus\b', 'Aiolos'), (r'\bo yoga\b', 'o Hyoga'), (r'\bIoria\b', 'Aiolia'),
    (r'\b[Ss]anto [Ii]mperial\b', 'Satã Imperial'), (r'\b(Ioga|Yogg|Yoga|Hioga)\b', 'Hyoga'), (r'\bMiro\b', 'Milo'),
    (r'\bCássio\b', 'Cássius'), (r'\b(Chaca|Chaka|Xaca)\b', 'Shaka'), (r'\bCamos\b', 'Camus'), (r'\b(Ioros|Iorus)\b', 'Aiolos'),
    (r'\b(Cheia|Céia|Zeia|Seia)\b', 'Seiya'), (r'\b(Nick|Rick|Rikki)\b', 'Ikki'), (r'\bXungri\b', 'Shunrei'),
    (r'\b(Ayoria|Aeoria)\b', 'Aiolia'), (r'\bTchiriu\b', 'Shiryu'), (r'\bMitsuma\b', 'Mitsumasa'), (r'\bSakido\b', 'Saori Kido'),
    (r'\b[Ii]olos\b', 'Aiolos'), (r'\bAiolos\b', 'Aiolos'), (r'\bAioros\b', 'Aiolos'), (r'\b[Ii]olia\b', 'Aiolia'),
    (r'\bAiória\b', 'Aiolia'), (r'\bShiriu\b', 'Shiryu'), (r'\bShirou\b', 'Shiryu'), (r'\bShiryú\b', 'Shiryu'),
    (r'\bHioga\b', 'Hyoga'), (r'\bYoga\b', 'Hyoga'), (r'\bIki\b', 'Ikki'), (r'\bIkky\b', 'Ikki'),
    (r'\bSeia\b', 'Seiya'), (r'\bSeya\b', 'Seiya'), (r'\bSeiá\b', 'Seiya'), (r'\bXun\b', 'Shun'),
    (r'\bChun\b', 'Shun'), (r'\bShaca\b', 'Shaka'), (r'\bXaca\b', 'Shaka'), (r'\bDeathmask\b', 'Máscara da Morte'),
    (r'\bAfrodith\b', 'Afrodite'), (r'\bCamo\b', 'Camus'), (r'\bXura\b', 'Shura'), (r'\bMilô\b', 'Milo'),
    (r'\bSága\b', 'Saga'), (r'\bDokko\b', 'Dohko'), (r'\bDoko\b', 'Dohko'), (r'\bMarim\b', 'Marin'),
    (r'\bJamiel\b', 'Jamiel'), (r'\bJamir\b', 'Jamiel'), (r'\bCassios\b', 'Cássius'), (r'\bCasios\b', 'Cássius'),
    (r'\bSaori\b', 'Saori'), (r'\bSaôri\b', 'Saori'), (r'\bAtenas\b', 'Atena'), (r'\bAthena\b', 'Atena'),
    (r'\b[Cc]osmos\b', 'Cosmo'), (r'\b[Cc]avaleiro do [Zz]odíaco\b', 'Cavaleiro do Zodíaco'),
    (r'\bSaint\b', 'Cavaleiro'), (r'\bCloth\b', 'Armadura'), (r'\bPégasus\b', 'Pégaso'), (r'\bPegasus\b', 'Pégaso'),
    (r'\bAries\b', 'Áries'), (r'\bGêmios\b', 'Gêmeos'), (r'\bCancer\b', 'Câncer'), (r'\bEscorpiao\b', 'Escorpião'),
    (r'\bSagittarius\b', 'Sagitário'), (r'\bSagitarius\b', 'Sagitário'), (r'\bAquarius\b', 'Aquário'),
    (r'\bCapricorn\b', 'Capricórnio'), (r'\bPisces\b', 'Peixes'), (r'\bVirgo\b', 'Virgem'), (r'\bLeo\b', 'Leão'),
    (r'\bArmadura de Ouro\b', 'Armadura de Ouro'), (r'\bMestre do Santuário\b', 'Mestre do Santuário'),
    (r'\bGrande Mestre\b', 'Grande Mestre'), (r'\bSantuario\b', 'Santuário'),
]


def clean(text):
    text = text.strip()
    for pat, rep in GLOSSARY:
        text = re.sub(pat, rep, text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\s+([,.!?…])', r'\1', text)
    return text


def chapters_of(scenes, titles):
    """Chapters = the game's own scene list: one entry per script, paired before/after a battle."""
    by = {s['script'][:-4].lower(): s for s in scenes}
    out = []
    for kind, scripts, offset in (('story', names.STORY_SCRIPTS, 1), ('if', names.IF_SCRIPTS, 30)):
        for i, key in enumerate(scripts):
            title = titles[offset + i] if offset + i < len(titles) else key
            base = re.sub(r'\s*-\s*\d+$', '', title)
            out.append({'id': key, 'kind': kind, 'title': title, 'title_jp': names.TITLES_JP.get(key, ''),
                        'chapter': base, 'part': int(m.group(1)) if (m := re.search(r'-\s*(\d+)$', title)) else 0,
                        'scene': by.get(key), 'digest': by.get(key + 'd')})
    for i, key in enumerate(names.POPE_SCRIPTS):
        out.append({'id': key, 'kind': 'pope', 'title': 'Modo Mestre, cena %d' % (i + 1), 'title_jp': '',
                    'chapter': 'Modo Mestre', 'part': i + 1, 'scene': by.get(key), 'digest': None})
    known = {c['id'] for c in out} | {c['id'] + 'd' for c in out}
    for s in scenes:
        key = s['script'][:-4].lower()
        if key not in known:
            out.append({'id': key, 'kind': 'other', 'title': key, 'title_jp': '', 'chapter': key, 'part': 0,
                        'scene': s, 'digest': None})
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    dump = os.path.abspath(argv[1])
    text = os.path.join(dump, 'text')
    with open(os.path.join(text, 'scenes.json'), encoding='utf-8') as f:
        scenes = json.load(f)
    with open(os.path.join(text, 'messages.json'), encoding='utf-8') as f:
        messages = json.load(f)
    fixes_path = os.path.join(HERE, 'fixes.json')
    fixes = {}
    if os.path.exists(fixes_path):
        with open(fixes_path, encoding='utf-8') as f:
            fixes = json.load(f)
    titles = messages.get('msg_holiday_demo.bin', {}).get('pt', [])
    vdir = os.path.join(text, 'voices')
    files = {n.lower(): n for n in os.listdir(vdir)} if os.path.isdir(vdir) else {}
    missing, used = [], set()

    def line_of(ln):
        voice = ln['voice']
        entry = {'voice': voice, 'page': ln['page'], 't': ln['t'], 'text_lines': ln.get('text_lines', [])}
        if not voice:
            entry.update(speaker_code='', speaker='', text='', source='text-only')
            return entry
        code, speaker = names.speaker(voice)
        entry.update(speaker_code=code, speaker=speaker)
        stem = voice[:-4]
        used.add(stem.lower())
        fix = fixes.get(stem) or fixes.get(stem.lower())
        if isinstance(fix, dict):
            entry['text'] = fix.get('text', '')
            entry['source'] = 'fixed'
            if fix.get('speaker'):
                entry['speaker'] = fix['speaker']
            return entry
        if isinstance(fix, str):
            entry['text'], entry['source'] = fix, 'fixed'
            return entry
        path = os.path.join(vdir, files.get(stem.lower() + '.pt.json', stem + '.pt.json'))
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                segs = json.load(f)
            entry['text'] = clean(' '.join(s['text'] for s in segs))
            entry['source'] = 'whisper'
        else:
            entry['text'], entry['source'] = '', 'missing'
            missing.append(stem)
        return entry

    def scene_block(s):
        if not s:
            return None
        return {'script': s['script'], 'pages': len(s['pages']), 'bgm': s['bgm'], 'text_table': s['text_table'],
                'lines': [line_of(ln) for ln in s['lines']]}

    chapters = []
    for ch in chapters_of(scenes, titles):
        chapters.append({'id': ch['id'], 'kind': ch['kind'], 'title': ch['title'], 'title_jp': ch['title_jp'],
                         'chapter': ch['chapter'], 'part': ch['part'],
                         'scene': scene_block(ch['scene']), 'digest': scene_block(ch['digest'])})
    extra = []
    for n in sorted(os.listdir(vdir)) if os.path.isdir(vdir) else []:
        if n.endswith('.pt.json') and n[:-8].lower() not in used:
            with open(os.path.join(vdir, n), encoding='utf-8') as f:
                segs = json.load(f)
            code, speaker = names.speaker(n[:-8])
            extra.append({'voice': n[:-8] + '.adx', 'speaker_code': code, 'speaker': speaker,
                          'text': clean(' '.join(s['text'] for s in segs))})
    story = {'chapters': chapters, 'voices_without_scene': extra,
             'stats': {'voices': len(used), 'missing_transcriptions': len(missing),
                       'fixed': sum(1 for c in chapters for b in (c['scene'], c['digest']) if b
                                    for ln in b['lines'] if ln.get('source') == 'fixed')}}
    with open(os.path.join(text, 'story.json'), 'w', encoding='utf-8') as f:
        json.dump(story, f, ensure_ascii=False, indent=1)
    print('STATS', json.dumps(story['stats']))
    if '--report' in argv:
        for c in chapters:
            print('== %s: %s' % (c['id'], c['title']))
            for ln in (c['scene'] or {'lines': []})['lines']:
                print('  %-26s %-18s %s' % ((ln['voice'] or '')[:-4], ln['speaker'], ln['text']))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
