#!/usr/bin/env python3
"""Gallery of Saint Seiya: The Sanctuary: the dump's pictures, movies and sounds copied into
folders with Portuguese names, ready for a media library.

usage: organize.py DUMP_DIR OUT_DIR
  OUT_DIR/Imagens   pictures only, one folder per subject (character art, encyclopedia, cards,
                    toys, chapter titles, name plates, textures, scenes, effects, interface)
                    and the renders of the 3D models (Modelos 3D dos personagens)
  OUT_DIR/Vídeos    the three Sofdec movies
  OUT_DIR/Música    Músicas/, Vozes/ (story voices by chapter, battle voices by fighter), Efeitos/ (the sound banks)
  OUT_DIR/Modelos 3D  the .glb models
The index of what was copied goes to DUMP_DIR/text/gallery_index.json.
"""
import hashlib
import json
import os
import re
import shutil
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sanctuary import names  # noqa: E402

PICS = 'Imagens'
TEXTURE_FOLDERS = {'k': 'cenarios-k', 'd': 'cenarios-d', 'z': 'cenarios-z'}
MOVIES = {'gx_jp': 'abertura-japonesa', 'gx_us': 'abertura-internacional', 'atari': 'logotipo-atari'}
BATTLE = re.compile(r'^(sel|win|con|cone|start|strat|rese|rase|bo|boe)(\d\d)_', re.I)


class Copier:
    def __init__(self, out):
        self.out, self.index, self.written = out, [], set()

    def copy(self, src, folder, name, kind='image'):
        if not os.path.exists(src):
            return
        dest = os.path.join(self.out, folder, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        n = 2
        while dest in self.written:
            stem, ext = os.path.splitext(name)
            dest = os.path.join(self.out, folder, '%s-%d%s' % (stem, n, ext))
            n += 1
        self.written.add(dest)
        shutil.copyfile(src, dest)
        self.index.append({'file': dest, 'source': src, 'kind': kind})


def pngs(folder):
    out = []
    for root, _dirs, files in os.walk(folder):
        for n in files:
            if n.lower().endswith('.png'):
                out.append(os.path.join(root, n))
    return sorted(out)


def md5(path):
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    dump, out = os.path.abspath(argv[1]), os.path.abspath(argv[2])
    img = os.path.join(dump, 'images')
    c = Copier(out)
    msg = {}
    mpath = os.path.join(dump, 'text', 'messages.json')
    if os.path.exists(mpath):
        with open(mpath, encoding='utf-8') as f:
            msg = json.load(f)
    collection = msg.get('msg_holiday_collection.bin', {}).get('pt', [])
    toys = msg.get('msg_holiday_toy.bin', {}).get('pt', [])

    def who(num):
        r = names.BY_NUMBER.get(num)
        return r[3] if r else names.PICTURE_EXTRA.get(num, num)

    handled = set()

    def take(name):
        handled.add(name)
        return os.path.join(img, name)

    entries = sorted(os.listdir(img))
    for name in entries:
        path = os.path.join(img, name)
        low = name.lower()
        m = re.match(r'charstand(e?\d+)a?\.png$', low)
        if m:
            c.copy(take(name), '%s/Arte dos personagens' % PICS, '%s-arte.png' % who(m.group(1)))
            continue
        if low == 'holiday_zukan.tpl':
            for i, p in enumerate(pngs(take(name))):
                label = names.slug(collection[i]) if i < len(collection) else 'personagem-%02d' % i
                c.copy(p, '%s/Enciclopédia' % PICS, '%02d-%s.png' % (i + 1, label))
            continue
        if low == 'holiday_card.tpl':
            for i, p in enumerate(pngs(take(name))):
                c.copy(p, '%s/Coleção de cards' % PICS, 'card-%02d.png' % (i + 1))
            continue
        if low == 'holiday_toy.tpl':
            for i, p in enumerate(pngs(take(name))):
                label = names.slug(toys[i]) if i < len(toys) else 'boneco-%02d' % i
                c.copy(p, '%s/Bonecos Die Cast' % PICS, '%02d-%s.png' % (i + 1, label))
            continue
        m = re.match(r'subtitle_(if\d+|\d+)\.png$', low)
        if m:
            key = m.group(1) if m.group(1).startswith('if') else 'demo' + m.group(1)
            c.copy(take(name), '%s/Títulos dos capítulos' % PICS, '%s-titulo.png' % key)
            continue
        m = re.match(r'title(\d+)\.bin$', low)
        if m:
            script = {v: k for k, v in names.TITLE_CARDS.items()}.get(int(m.group(1)), 'title%s' % m.group(1))
            for i, p in enumerate(pngs(take(name))):
                c.copy(p, '%s/Títulos dos capítulos' % PICS, '%s-%s.png' % (script, 'placa' if i == 0 else 'quadro'))
            continue
        m = re.match(r'(name|nametpl)_(\w\w)\.tpl$', low)
        if m:
            lang = names.LANGUAGES.get(m.group(2), m.group(2))
            for p in pngs(take(name)):
                c.copy(p, '%s/Nomes dos personagens/%s' % (PICS, lang),
                       '%s-%s.png' % (m.group(1), os.path.basename(p)[:-4].split('_')[0]))
            continue
        m = re.match(r'(e?\d+)(a|b)?(~\d)?(_face)?\.tpl$', low)
        if m:
            num = m.group(1)
            label = who(num) if (num in names.BY_NUMBER or num in names.PICTURE_EXTRA) else ('extra-%s' % num if num.startswith('e') else 'outros-%s' % num)
            sub = '-'.join(x for x in [label, {'a': 'cor-2', 'b': 'cor-3'}.get(m.group(2) or '', ''),
                                       'rosto' if m.group(4) else '', 'variante' + m.group(3)[1:] if m.group(3) else ''] if x)
            for p in pngs(take(name)):
                c.copy(p, '%s/Texturas dos modelos/%s' % (PICS, label), '%s-%s.png' % (sub, os.path.basename(p)[:-4]), kind='texture')
            continue
        m = re.match(r'([kdz])(\d+)_tex\.bin$', low)
        if m:
            for p in pngs(take(name)):
                c.copy(p, '%s/Texturas dos cenários/%s%s' % (PICS, m.group(1), m.group(2)), os.path.basename(p), kind='texture')
            continue
        if low in ('stage_b.bin', 'stage_p.bin', 'stage_t.bin', 'select_st_tex.bin', 'sele_st_colosseum_tex.bin',
                   'sele_st_hell_tex.bin', 'bgdata.bin', 'op_hashira_tex.bin', 'test_tex.bin', 'menu_map_tex.bin',
                   'map.bin', 'model.bin', 'lcg.bin') or re.match(r'([dr]\d+a?)\.bin$', low):
            for p in pngs(take(name)):
                c.copy(p, '%s/Texturas dos cenários/%s' % (PICS, low.replace('.bin', '').replace('_tex', '')),
                       os.path.relpath(p, path).replace('/', '-'), kind='texture')
            continue
        m = re.match(r'(\d\d)a?(~\d)?\.bin$', low)
        if m:                                             # the fighters' model packs
            for p in pngs(take(name)):
                c.copy(p, '%s/Texturas dos modelos/%s' % (PICS, who(m.group(1))),
                       'pacote-%s-%s' % (low[:-4].replace('~', '-'), os.path.relpath(p, path).replace('/', '-')), kind='texture')
            continue
        m = re.match(r'(d?if\d+|d?\d+|kyoukou_\d+)_(\d+)_(\d+)(_[ab]\d?)?\.bin$', low)
        if m:
            script = m.group(1).replace('kyoukou_', 'pope')
            if script.isdigit():
                script = 'demo' + script
            elif script.startswith('d'):
                script = ('demo' + script[1:] if script[1:].isdigit() else script[1:]) + '-resumo'
            for p in pngs(take(name)):
                c.copy(p, '%s/Cenas da história/%s/%s' % (PICS, script, low[:-4]),
                       os.path.relpath(p, path).replace('/', '-'), kind='texture')
            continue
        m = re.match(r'(\d\d)\.png$', low)
        if m:
            c.copy(take(name), '%s/Efeitos/golpes-dos-personagens' % PICS, '%s-efeitos.png' % who(m.group(1)))
            continue
        if re.match(r'(kouka\d+|gefe_\d+|kkmj\d+(_\d)?|fkword\d+|fkbase\d+|2dbg\d+|2dobj\d+|\d+dbg\d+|\d+dobj\d+|kage|common|mangabg\d)\.png$', low):
            group = re.match(r'[a-z]*', low).group() or 'fundos-2d'
            c.copy(take(name), '%s/Efeitos/%s' % (PICS, group), low)
            continue
        if low in ('eff_01.bin', 'spriteblur.bin', 'gauge.bin', 'bbctr.tpl', 'parts.bin', 'reborn.bin'):
            for p in pngs(take(name)):
                c.copy(p, '%s/Efeitos/%s' % (PICS, low.split('.')[0]), os.path.relpath(p, path).replace('/', '-'))
            continue
        m = re.match(r'(menu2d|title_[abc]|logo|charselparts|popetex|resident|result|holiday|vs\d+[ab]|result_c\d+)_(du|fr|it|jp|sp|uk|us)\.tpl$', low)
        if m:
            lang = names.LANGUAGES.get(m.group(2), m.group(2))
            for p in pngs(take(name)):
                c.copy(p, '%s/Interface/%s/%s' % (PICS, lang, m.group(1)), os.path.relpath(p, path).replace('/', '-'), kind='interface')
            continue
        # everything else that is a picture: interface
        if os.path.isdir(path):
            for p in pngs(take(name)):
                c.copy(p, '%s/Interface/%s' % (PICS, low.split('.')[0]), os.path.relpath(p, path).replace('/', '-'), kind='interface')
        elif low.endswith('.png'):
            c.copy(take(name), '%s/Interface' % PICS, low, kind='interface')

    # renders of the 3D models
    VIEW = {'front': 'frente', 'side': 'lado', 'back': 'costas', 'three_quarter': 'tres-quartos', 'top': 'de-cima'}
    rdir = os.path.join(dump, 'renders', 'characters')
    for ident in sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []:
        for view, label in VIEW.items():
            src = os.path.join(rdir, ident, view + '.png')
            if os.path.exists(src):
                im = Image.open(src).convert('RGBA')
                box = im.getbbox()
                dest = os.path.join(out, '%s/Modelos 3D dos personagens/%s' % (PICS, ident.split('_')[0]), '%s-%s.png' % (ident.replace('_', '-'), label))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                (im.crop(box) if box else im).save(dest)
                c.index.append({'file': dest, 'source': src, 'kind': 'render'})
    mdir = os.path.join(dump, 'models')
    for root, _dirs, files in os.walk(mdir):
        for n in sorted(files):
            c.copy(os.path.join(root, n), os.path.join('Modelos 3D', os.path.relpath(root, mdir)), n, kind='model')

    # movies
    vdir = os.path.join(dump, 'video')
    for n in sorted(os.listdir(vdir)) if os.path.isdir(vdir) else []:
        if n.endswith('.mp4'):
            c.copy(os.path.join(vdir, n), 'Vídeos', '%s.mp4' % MOVIES.get(n[:-4], n[:-4]), kind='video')

    # music and voices
    adir = os.path.join(dump, 'audio')
    scenes = []
    spath = os.path.join(dump, 'text', 'scenes.json')
    if os.path.exists(spath):
        with open(spath, encoding='utf-8') as f:
            scenes = json.load(f)
    chapter_of = {}
    for s in scenes:
        for ln in s['lines']:
            if ln['voice']:
                chapter_of.setdefault(ln['voice'][:-4].lower(), re.sub(r'd$', '', s['script'][:-4]))
    bdir = os.path.join(adir, 'banks')
    for bank in sorted(os.listdir(bdir)) if os.path.isdir(bdir) else []:
        for n in sorted(os.listdir(os.path.join(bdir, bank))):
            c.copy(os.path.join(bdir, bank, n), 'Música/Efeitos/' + bank, n, kind='effect')
    seen = {}
    for n in sorted(os.listdir(adir)) if os.path.isdir(adir) else []:
        if not n.endswith('.ogg'):
            continue
        src = os.path.join(adir, n)
        stem = n[:-4]
        base = re.sub(r'~\d+$', '', stem)
        if base != stem:                                  # the disc stores some voices twice
            h = md5(src)
            if seen.get(base.lower()) == h:
                continue
        else:
            seen[base.lower()] = md5(src)
        low = stem.lower()
        if low.startswith('story'):
            code, speaker = names.speaker(stem)
            folder = 'Música/Vozes/História/' + chapter_of.get(low, 'sem-cena')
            c.copy(src, folder, '%s-%s.ogg' % (stem, names.slug(speaker)), kind='voice')
        elif BATTLE.match(stem):
            m = BATTLE.match(stem)
            c.copy(src, 'Música/Vozes/Batalha/' + who(m.group(2)), n, kind='voice')
        elif low.startswith('pope'):
            c.copy(src, 'Música/Vozes/Modo Mestre', n, kind='voice')
        elif re.match(r'(bgm_\d+|b\d+|j\d+|eblue|win|holiday_new|b14holiday|demo35)', low):
            c.copy(src, 'Música/Músicas', n, kind='music')
        else:
            c.copy(src, 'Música/Vozes/Outras', n, kind='voice')

    os.makedirs(os.path.join(dump, 'text'), exist_ok=True)
    with open(os.path.join(dump, 'text', 'gallery_index.json'), 'w', encoding='utf-8') as f:
        json.dump(c.index, f, ensure_ascii=False, indent=1)
    kinds = {}
    for e in c.index:
        kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
    print('%d files -> %s  %s' % (len(c.index), out, kinds))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
