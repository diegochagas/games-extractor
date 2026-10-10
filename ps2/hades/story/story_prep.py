#!/usr/bin/env python3
"""Collects everything the story book of The Hades shows into one JSON for build.js.

usage: story_prep.py DUMP_DIR WORK_DIR   -> WORK_DIR/story_book.json, WORK_DIR/cache/*.png
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from hades import names  # noqa: E402
from sanctuary.story.story_prep import Cache, duration, frames, pngs, render  # noqa: E402

MOVIES = [('gx_jp', 'Abertura (versão japonesa)'), ('gx_us', 'Abertura (versão internacional)'), ('atari', 'Logotipo da Atari')]


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    dump, work = os.path.abspath(argv[1]), os.path.abspath(argv[2])
    os.makedirs(work, exist_ok=True)
    cache = Cache(dump, work)
    text = os.path.join(dump, 'text')
    msg = json.loads(Path(os.path.join(text, 'messages.json')).read_text(encoding='utf-8'))
    story = json.loads(Path(os.path.join(text, 'story.json')).read_text(encoding='utf-8'))
    mpath = os.path.join(text, 'models.json')
    models_info = json.loads(Path(mpath).read_text(encoding='utf-8')) if os.path.exists(mpath) else []
    afs_index = json.loads(Path(os.path.join(dump, 'afs', 'afs_index.json')).read_text(encoding='utf-8'))

    def uk(table):
        t = msg.get(table, {})
        return t.get('uk') or t.get('jp') or []

    def img(rel, *a, **k):
        return cache.get(rel, *a, **k)

    def first(folder):
        p = pngs(os.path.join(dump, 'images', folder))
        return p[0] if p else None

    cnf = Path(os.path.join(dump, 'iso', 'SYSTEM.CNF')).read_text(errors='replace')
    book = {'facts': {'boot': re.search(r'cdrom0:\\([^;]+)', cnf).group(1), 'version': re.search(r'VER = (\S+)', cnf).group(1),
                      'vmode': re.search(r'VMODE = (\S+)', cnf).group(1), 'afs_files': len(afs_index),
                      'pictures': len(pngs(os.path.join(dump, 'images'))),
                      'adx': sum(1 for r in afs_index if r['name'].lower().endswith('.adx')),
                      'strings': sum(len(v.get('uk', [])) for v in msg.values())},
            'cover': {'title': img(first('title_00_uk.fjf'), 480, 420), 'logo': img(first('holi_title_uk.fjf'), 480, 200)}}
    # menus (English, with the Japanese): the unlock list, main menu, options...
    book['menus'] = []
    for name, label in (('msg_submenu_uk.bin', 'Menu de jogo (desbloqueios)'), ('msg_mainmenu_uk.bin', 'Menu principal'),
                        ('msg_option.bin', 'Opções'), ('msg_result.bin', 'Resultado'), ('msg_continue.bin', 'Tela de continuar'),
                        ('msg_charsel_uk.bin', 'Frases de entrada dos lutadores'), ('msg_holiday_uk.bin', 'Zodiac Holiday (coleção)')):
        rows = [{'id': i, 'en': render(s)} for i, s in enumerate(uk(name)) if render(s).strip()]
        if rows:
            book['menus'].append({'file': name, 'label': label, 'rows': rows})
    # fighters
    unlock = uk('msg_holiday_uk.bin')
    fighters = []
    for num, short, full, slug_ in names.ROSTER:
        renders = {}
        for suffix, label in (('', 'Cor 1'), ('_cor2', 'Cor 2'), ('_h', 'Variante h'), ('_h_cor2', 'Variante h, cor 2')):
            views = {v: img('renders/characters/%s%s/%s.png' % (slug_, suffix, v), 330, 420, crop=True) for v in ('front', 'side', 'back', 'three_quarter')}
            if views['front']:
                renders[suffix or 'cor1'] = {'label': label, 'views': views}
        minfo = next((m for m in models_info if m['name'] == slug_ and not m['simple'] and m['colour'] == 1 and not m.get('variant')), None)
        skills = []
        rows = msg.get('skill_%s_uk.msg' % num, {})
        rows = rows.get('jp') or []
        for s in rows:
            r = render(s)
            if r.strip():
                skills.append(r)
        fighters.append({'number': num, 'name': short, 'full': full, 'english': unlock[67 + int(num)] if 67 + int(num) < len(unlock) else '',
                         'renders': renders, 'skills': skills,
                         'model': {'bones': minfo['bones'], 'triangles': minfo['triangles'], 'parts': minfo['parts']} if minfo else None,
                         'nametag': img(first('nametag_%s_uk.fjf' % num) or 'x', 200, 60, crop=True),
                         'face': img(first('facetag_%s_uk.fjf' % num) or 'x', 120, 120)})
    book['fighters'] = fighters
    book['extra_models'] = [{'name': m['name'], 'file': m['file'], 'triangles': m['triangles'],
                             'front': img('renders/%s/front.png' % m['id'], 300, 400, crop=True)}
                            for m in models_info if m['name'].startswith('extra') and not m['simple'] and m['colour'] == 1 and not m.get('variant')]
    # chapters
    stats = {'lines': 0, 'translated': 0, 'fixed': 0, 'untranslated': 0}
    chapters = []
    for ch in story['chapters']:
        blocks = []
        for b in ch['blocks']:
            lines = []
            for ln in b['lines']:
                if not ln['en'] and not ln['voice']:
                    continue
                stats['lines'] += 1
                stats[{'ollama': 'translated', 'fixed': 'fixed'}.get(ln['source'], 'untranslated')] += 1 if ln['en'] else 0
                lines.append({'speaker': ln['speaker'], 'pt': ln['pt'] or ln['en'], 'en': ln['en'], 'jp': ln['jp'],
                              'voice': (ln['voice'] or '')[:-4], 'source': ln['source']})
            speakers = []
            for ln in lines:
                if ln['speaker'] and ln['speaker'] not in speakers:
                    speakers.append(ln['speaker'])
            blocks.append({'script': b['script'], 'part': b['part'], 'pages': b['pages'], 'bgm': [x[:-4] for x in b['bgm']],
                           'lines': lines, 'speakers': speakers})
        chapters.append({'id': ch['id'], 'group': ch['group'], 'title': ch['title'], 'blocks': blocks,
                         'speakers': [s for b in blocks for s in b['speakers']]})
    book['chapters'] = chapters
    book['groups'] = story['groups']
    book['demos'] = list(zip(names.DEMOS, names.DEMOS_PT))
    book['movies'] = [{'name': n, 'title': t, 'duration': duration(os.path.join(dump, 'video', n + '.mp4')),
                       'frames': [img(f, 300, 170) for f in frames(os.path.join(dump, 'video', n + '.mp4'), work, n)]} for n, t in MOVIES]
    adir = os.path.join(dump, 'audio')
    book['music'] = [{'file': n, 'duration': duration(os.path.join(adir, n))} for n in sorted(os.listdir(adir))
                     if re.match(r'(?i)(b\d+|p\d+|j\d+|n\d+)\.ogg$', n)] if os.path.isdir(adir) else []
    bdir = os.path.join(adir, 'banks')
    book['bank_count'] = len(os.listdir(bdir)) if os.path.isdir(bdir) else 0
    book['bank_samples'] = sum(len(os.listdir(os.path.join(bdir, b))) for b in os.listdir(bdir)) if os.path.isdir(bdir) else 0
    book['voices'] = sum(1 for n in os.listdir(adir) if n.lower().startswith('story')) if os.path.isdir(adir) else 0
    book['stats'] = dict(stats, fighters=len(fighters), images=cache.count, chapters=len(chapters))
    with open(os.path.join(work, 'story_book.json'), 'w', encoding='utf-8') as f:
        json.dump(book, f, ensure_ascii=False, indent=1)
    print('STATS', json.dumps(book['stats'], ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
