#!/usr/bin/env python3
"""Collects the story book data for build.js: translated text + pictures, scaled for the page.

usage: story_prep.py DUMP WORK_DIR      -> WORK_DIR/story_book.json, WORK_DIR/cache/*.png

DUMP holds text/story.json (story_dump.py), text/translation/pt-BR.json (translate.py),
puppets/<model>.png (puppet.py) and assets/ (dump.py). A string without translation is shown in
Chinese, so the book can be built while the translation is still running.
"""
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import translate  # noqa: E402

VOLUMES = [
    ('01', 'O Santuário, Poseidon e Hades (capítulos 1 a 14)', range(1, 15)),
    ('02', 'O pesadelo, Asgard, Éris, Abel e os deuses (capítulos 15 a 32)', range(15, 33)),
]


def picture(assets, ref):
    """'levelIcon/4' -> png path under assets/texture (same lookup as roles.py, simplified)."""
    if not ref or '/' not in ref:
        return None
    folder, name = ref.rsplit('/', 1)
    folder = folder.lower()
    root = os.path.join(assets, 'texture')
    for cand in (os.path.join(root, folder, '_current_.fassets'), os.path.join(root, folder + '.fassets')):
        idx = os.path.join(cand, 'objects.json')
        if os.path.exists(idx):
            with open(idx, encoding='utf-8') as f:
                for o in json.load(f):
                    if o.get('file') and str(o.get('name')).lower() == name.lower():
                        return os.path.join(cand, o['file'])
    return None


def cached(src, cache_dir, max_side):
    """Copy of a picture scaled to max_side pixels, in the cache (returns the cache path)."""
    if not src or not os.path.exists(src):
        return None
    os.makedirs(cache_dir, exist_ok=True)
    name = re.sub(r'[^A-Za-z0-9_.-]', '_', os.path.relpath(src).replace(os.sep, '_'))[-80:]
    dest = os.path.join(cache_dir, f'{max_side}_{name}')
    if not dest.endswith('.png'):
        dest += '.png'
    if not os.path.exists(dest):
        im = Image.open(src).convert('RGBA')
        im.thumbnail((max_side, max_side))
        im.save(dest)
    return dest


def prep(dump, work):
    with open(os.path.join(dump, 'text', 'story.json'), encoding='utf-8') as f:
        story = json.load(f)
    cache = translate.load_cache(dump)
    glossary = translate.load_glossary()
    missing = [0]

    def pt(zh):
        if not zh:
            return ''
        hit = cache.get(translate.key_of(zh))
        if hit is None:
            missing[0] += 1
            return translate.apply_glossary(zh, glossary)
        return hit

    assets = os.path.join(dump, 'assets')
    puppets = os.path.join(dump, 'puppets')
    cache_dir = os.path.join(work, 'cache')
    speakers = {}
    for sid, sp in story['speakers'].items():
        model = (sp.get('model') or '').lower()
        pic = os.path.join(puppets, model + '.png') if model else None
        speakers[sid] = {'sid': sid, 'zh': sp['name'], 'pt': pt(sp['name']), 'pic': cached(pic, cache_dir, 260)}
    chapters = []
    for ch in story['chapters']:
        levels = []
        for lv in ch['levels']:
            stories = []
            for s in lv['stories']:
                stories.append({'id': s['id'], 'when': s['when'], 'title_zh': s['title'], 'title': pt(s['title']),
                                'lines': [{'speaker': speakers.get(l['sid'], {}).get('pt') or l['speaker'], 'sid': l['sid'],
                                           'side': l['side'], 'zh': l['zh'], 'pt': pt(l['zh'])} for l in s['lines']]})
            levels.append({'id': lv['id'], 'name_zh': lv['name'], 'name': pt(lv['name']), 'desc_zh': lv['desc'], 'desc': pt(lv['desc']),
                           'boss': [speakers.get(b, {}).get('pt') or b for b in lv['boss']], 'stories': stories})
        chapters.append({'id': ch['id'], 'index': ch['index'], 'name_zh': ch['name'], 'name': f"Capítulo {ch['index']}: {pt(ch['name'])}",
                         'desc_zh': ch['desc'], 'desc': pt(ch['desc']),
                         'icon': cached(picture(assets, ch['icon']), cache_dir, 500),
                         'bg': cached(picture(assets, f"StoryRePlay/ChapterIcon/{ch['index']}"), cache_dir, 700),
                         'show_role': speakers.get(ch['show_role'], {}).get('pic'), 'levels': levels})
    volumes = [{'num': n, 'title': t, 'chapters': [c for c in chapters if c['index'] in r]} for n, t, r in VOLUMES]
    book = {'title': 'Saint Seiya Rebirth', 'title_zh': '圣斗士星矢：重生', 'volumes': volumes, 'speakers': speakers,
            'cover': cached(picture(assets, 'LoginBgIcon/Beioudenglu') or picture(assets, 'LoginBgIcon/denglujiemian2'), cache_dir, 900),  # the Asgard login screen
            'stats': {**story.get('stats', {}), 'untranslated': missing[0], 'cached': len(cache)}}
    os.makedirs(work, exist_ok=True)
    with open(os.path.join(work, 'story_book.json'), 'w', encoding='utf-8') as f:
        json.dump(book, f, ensure_ascii=False, indent=1)
    return book


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    book = prep(argv[0], argv[1])
    print('STATS', book['stats'])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
