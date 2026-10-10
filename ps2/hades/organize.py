#!/usr/bin/env python3
"""Gallery of Saint Seiya: The Hades: the dump's pictures, movies and sounds copied into folders
with Portuguese names, ready for a media library.

usage: organize.py DUMP_DIR OUT_DIR
  OUT_DIR/Imagens   pictures only: renders of the 3D models, name tags and faces per language,
                    model and stage textures, scene textures, effects, interface per language
  OUT_DIR/Vídeos    the three Sofdec movies
  OUT_DIR/Música    Músicas/, Vozes/ (story voices by chapter with the speaker, battle voices by
                    fighter, others), Efeitos/ (the sound banks)
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
from hades import names  # noqa: E402

PICS = 'Imagens'
MOVIES = {'gx_jp': 'abertura-japonesa', 'gx_us': 'abertura-internacional', 'atari': 'logotipo-atari'}
BATTLE = re.compile(r'^(sel|win|con|start|entry|btl)_?(\d\d)_', re.I)
VIEW = {'front': 'frente', 'side': 'lado', 'back': 'costas', 'three_quarter': 'tres-quartos', 'top': 'de-cima'}


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


def who(num):
    r = names.BY_NUMBER.get(num)
    return r[3] if r else ('extra-%s' % num if num.startswith('e') else 'outros-%s' % num)


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    dump, out = os.path.abspath(argv[1]), os.path.abspath(argv[2])
    img = os.path.join(dump, 'images')
    c = Copier(out)
    for name in sorted(os.listdir(img)):
        path = os.path.join(img, name)
        low = name.lower()
        rel = lambda p: os.path.relpath(p, path).replace('/', '-')  # noqa: E731
        m = re.match(r'(nametag|facetag)_(\d\d)_(\w\w)\.fjf$', low)
        if m:
            lang = names.LANGUAGES.get(m.group(3), m.group(3))
            for p in pngs(path):
                c.copy(p, '%s/%s/%s' % (PICS, 'Nomes dos personagens' if m.group(1) == 'nametag' else 'Rostos dos personagens', lang),
                       '%s-%s-%s' % (m.group(2), who(m.group(2)), rel(p)))
            continue
        m = re.match(r'chartag_(\d\d)\.fjf$', low)
        if m:
            for p in pngs(path):
                c.copy(p, '%s/Etiquetas dos personagens' % PICS, '%s-%s-%s' % (m.group(1), who(m.group(1)), rel(p)))
            continue
        m = re.match(r'charstand(e?\d+)a?\.png$', low)
        if m:
            c.copy(path, '%s/Arte dos personagens (do jogo anterior)' % PICS, low)
            continue
        m = re.match(r'(e?\d\d)(a)?(~\d)?(_face)?\.tpl$', low)
        if m:
            label = who(m.group(1))
            sub = '-'.join(x for x in [label, 'cor-2' if m.group(2) else '', 'rosto' if m.group(4) else '',
                                       'variante' + m.group(3)[1:] if m.group(3) else ''] if x)
            for p in pngs(path):
                c.copy(p, '%s/Texturas dos modelos/%s' % (PICS, label), '%s-%s' % (sub, rel(p)), kind='texture')
            continue
        m = re.match(r'(\d\d)_(smash_[abc]|resident|rec_smash_[abc]|rec_resident)\.bin$', low)
        if m:
            for p in pngs(path):
                c.copy(p, '%s/Texturas dos modelos/%s' % (PICS, who(m.group(1))), 'pacote-%s-%s' % (m.group(2), rel(p)), kind='texture')
            continue
        m = re.match(r'(dm\d+|hk\d+)(_tex)?\.bin$', low)
        if m:
            for p in pngs(path):
                c.copy(p, '%s/Texturas dos cenários/%s' % (PICS, m.group(1)), rel(p), kind='texture')
            continue
        m = re.match(r'(\d{4}|\d[amr]\d\d)_(\d+)_(\d+).*\.bin$', low) or re.match(r'(\d\d)_(\d+)_(\d+).*\.bin$', low)
        if m:
            for p in pngs(path):
                c.copy(p, '%s/Cenas da história/%s' % (PICS, m.group(1)), '%s-%s' % (low[:-4], rel(p)), kind='texture')
            continue
        if re.match(r'(nd\d+_[abc]_\d+|\d+-\d+_\d+[ab]?|\d+a)\.png$', low):
            c.copy(path, '%s/Efeitos' % PICS, low)
            continue
        if re.match(r'eff_\d+[ab](_esb)?\.bin$', low):
            for p in pngs(path):
                c.copy(p, '%s/Efeitos/%s' % (PICS, low[:-4]), rel(p))
            continue
        m = re.match(r'([a-z_]+?)_(du|fr|it|jp|sp|uk|us)\.(tpl|fjf|bin)$', low)
        if m:
            lang = names.LANGUAGES.get(m.group(2), m.group(2))
            for p in pngs(path):
                c.copy(p, '%s/Interface/%s/%s' % (PICS, lang, m.group(1)), rel(p), kind='interface')
            continue
        if os.path.isdir(path):
            for p in pngs(path):
                c.copy(p, '%s/Interface/%s' % (PICS, low.split('.')[0]), rel(p), kind='interface')
        elif low.endswith('.png'):
            c.copy(path, '%s/Interface' % PICS, low, kind='interface')

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

    vdir = os.path.join(dump, 'video')
    for n in sorted(os.listdir(vdir)) if os.path.isdir(vdir) else []:
        if n.endswith('.mp4'):
            c.copy(os.path.join(vdir, n), 'Vídeos', '%s.mp4' % MOVIES.get(n[:-4], n[:-4]), kind='video')

    adir = os.path.join(dump, 'audio')
    spath = os.path.join(dump, 'text', 'scenes.json')
    chapter_of = {}
    if os.path.exists(spath):
        with open(spath, encoding='utf-8') as f:
            for s in json.load(f):
                for ln in s['lines']:
                    if ln['voice']:
                        chapter_of.setdefault(ln['voice'][:-4].lower(), s['chapter'])
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
        if base != stem and seen.get(base.lower()) == md5(src):
            continue
        seen.setdefault(base.lower(), md5(src))
        low = stem.lower()
        if low.startswith('story'):
            _code, speaker = names.speaker(stem)
            c.copy(src, 'Música/Vozes/História/' + chapter_of.get(low, 'sem-cena'), '%s-%s.ogg' % (stem, names.slug(speaker)), kind='voice')
        elif BATTLE.match(stem):
            c.copy(src, 'Música/Vozes/Batalha/' + who(BATTLE.match(stem).group(2)), n, kind='voice')
        elif re.match(r'(b\d+|p\d+|j\d+|n\d+|test)$', low):
            c.copy(src, 'Música/Músicas', n, kind='music')
        else:
            c.copy(src, 'Música/Vozes/Outras', n, kind='voice')

    with open(os.path.join(dump, 'text', 'gallery_index.json'), 'w', encoding='utf-8') as f:
        json.dump(c.index, f, ensure_ascii=False, indent=1)
    kinds = {}
    for e in c.index:
        kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
    print('%d files -> %s  %s' % (len(c.index), out, kinds))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
