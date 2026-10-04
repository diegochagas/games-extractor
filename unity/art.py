#!/usr/bin/env python3
"""Files the 2D art of the dump (dump.py output) into a picture library with Portuguese folders.

usage: art.py DUMP OUT_DIR

Copies the Texture2D exports of `assets/texture`, `assets/otherres`, `assets/scene` and
`assets/modulesview` (and the sprite cut-outs of `assets/atlas`) into OUT_DIR/<category>/<game folder>/,
naming cloths and items after the tables when they are known. Skipped on purpose: `effect/` and
`uieffect/` (particle sheets), `role/` (the puppet atlases; the characters are the roles.py gallery)
and the per-bundle sprite duplicates of a texture. Existing files are kept (only new ones copied),
so the run is incremental; the result is pictures only (no index inside OUT_DIR).
"""
import json
import os
import shutil
import sys

# game folder (lower case, under texture/ or otherres/) -> Portuguese category folder
CATEGORIES = {
    'Vestimentas': ['stoleicon', 'stoleicon2', 'cloth', 'stolepratice', 'closet'],
    'Artes dos personagens': ['lcherocg', 'roleicon', 'roleicon2', 'bagrolecard', 'roleequipcard', 'modelresbg', 'heroimg',
                              'heroroleequipbg', 'roleskin', 'lotteryheroname', 'handbookview'],
    'Cenários': ['bgtexture', 'level', 'loginbgicon', 'gameloading', 'exploration', 'breakthroughnewview', 'usericon',
                 'maze', 'map', 'othertex'],
    'Capítulos e história': ['levelicon', 'storyreplay', 'jibanchaptericon', 'storychatview', 'soulofgold'],
    'Golpes': ['skillicon', 'skillicon2', 'skillbanner', 'skillbanner2'],
    'Itens': ['itemicon', 'itemicon2', 'coinicon', 'microcosmicon', 'microcosmicon2', 'microcosm', 'artifactnew',
              'artifactview', 'runestone', 'relic', 'coatofarms', 'starsoul', 'soulbox', 'gradeicon', 'tittleicon',
              'souvenirtitile', 'uiicon', 'itemgetpathicon', 'taskicon'],
}
SKIP_TOP = {'effect', 'uieffect', 'role', 'config', 'allfont', 'allshader', 'initres', 'audio', 'GameRes', 'GameRes.manifest'}


def category_of(top, folder):
    first = folder.split('/')[0].lower()
    for cat, folders in CATEGORIES.items():
        if first in folders:
            return cat
    if top == 'scene':
        return 'Cenários'
    return 'Interface e eventos'


def table_names(tables_dir):
    """{'cloth': {id: name}, 'item': {id: name}} from the tables, when they exist."""
    out = {'cloth': {}, 'item': {}}

    def load(name):
        path = os.path.join(tables_dir, name + '.json')
        if os.path.exists(path):
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        return []

    # pictures are named after the icon path ('StoleIcon/1001'): the whole cloth is 1001, its pieces 10011..10016
    for r in load('StoleConfig') + load('CollectionStoleConfig'):
        icon = str(r.get('icon') or '').rsplit('/', 1)[-1]
        if icon and r.get('name'):
            out['cloth'].setdefault(icon, r['name'])
            for n in range(1, 7):
                out['cloth'].setdefault(f'{icon}{n}', f"{r['name']} - peça {n}")
    for r in load('ItemConfig'):
        icon = str(r.get('icon') or '').rsplit('/', 1)[-1]
        if icon and r.get('name'):
            out['item'].setdefault(icon, r['name'])
    return out


def safe(name):
    return ''.join(c for c in str(name) if c not in '\\/:*?"<>|').strip() or 'x'


def plan(dump):
    """[(source png, destination relative path)] for every picture to file."""
    assets = os.path.join(dump, 'assets')
    names = table_names(os.path.join(dump, 'tables'))
    out = []
    for top in sorted(os.listdir(assets)):
        if top in SKIP_TOP or not os.path.isdir(os.path.join(assets, top)):
            continue
        for root, _dirs, files in os.walk(os.path.join(assets, top)):
            if 'objects.json' not in files:
                continue
            rel = os.path.relpath(root, os.path.join(assets, top)).replace(os.sep, '/')
            folder = rel.replace('/_current_.fassets', '').replace('.fassets', '')
            if folder == '.':
                folder = top
            with open(os.path.join(root, 'objects.json'), encoding='utf-8') as f:
                objects = json.load(f)
            want_sprites = top == 'atlas'
            for o in objects:
                if not o.get('file'):
                    continue
                if o['type'] == 'Texture2D' and want_sprites:
                    continue
                if o['type'] == 'Sprite' and not want_sprites:
                    continue
                if o['type'] not in ('Texture2D', 'Sprite'):
                    continue
                if (o.get('width') or 0) < 8 or (o.get('height') or 0) < 8:
                    continue
                cat = category_of(top, folder)
                base = os.path.splitext(os.path.basename(o['file']))[0]
                first = folder.split('/')[0].lower()
                label = None
                if first in ('stoleicon', 'stoleicon2', 'cloth'):
                    label = names['cloth'].get(base)
                elif first in ('itemicon', 'itemicon2'):
                    label = names['item'].get(base)
                fname = f'{base} {safe(label)}.png' if label else f'{base}.png'
                dest = os.path.join(cat, top if top != 'texture' and top != 'otherres' else '', folder.replace('/', ' - '), fname)
                out.append((os.path.join(root, o['file']), os.path.normpath(dest)))
    return out


def copy(dump, out_dir):
    items = plan(dump)
    n = 0
    seen = set()
    for src, rel in items:
        dest = os.path.join(out_dir, rel)
        if dest in seen:
            stem, ext = os.path.splitext(dest)
            k = 2
            while f'{stem} ({k}){ext}' in seen:
                k += 1
            dest = f'{stem} ({k}){ext}'
        seen.add(dest)
        if os.path.exists(dest):
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)
        n += 1
    return n, len(items)


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    n, total = copy(argv[0], argv[1])
    print(f'{n} new pictures copied ({total} in the library) -> {argv[1]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
