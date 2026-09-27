#!/usr/bin/env python3
"""Gallery of Saint Seiya Omega Ultimate Cosmo: the dump's pictures, videos and sounds copied
into folders with Portuguese names, ready to be moved into a media library.

usage: organize.py DUMP_DIR OUT_DIR
  OUT_DIR/Imagens   pictures only (renders of the 3D models, portraits, event pictures, stages,
                    interface), one folder per subject
  OUT_DIR/Vídeos    the five movies
  OUT_DIR/Música    Músicas/ (BGM), Vozes/ (story voices by story, special attack calls),
                    Efeitos/ (sound banks)
  OUT_DIR/Modelos 3D  the .glb models
The index of what was copied is written to DUMP_DIR/text/gallery_index.json.
"""
import json
import os
import re
import shutil
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from omega import names  # noqa: E402

STORY = {'50': 'Kouga', '51': 'Yuna', '52': 'Ryuho', '53': 'Souma', '54': 'Eden', '55': 'Haruto', '56': 'Seiya'}
VARIANT = {'00_normal': 'armadura-inteira', '00_half': 'armadura-danificada', '00_broken': 'armadura-destruida',
           '01_normal': 'jogador-2-armadura-inteira', '01_half': 'jogador-2-armadura-danificada',
           '01_broken': 'jogador-2-armadura-destruida', 'pose_idle': 'pose-de-guarda', 'pose_win': 'pose-de-vitoria'}
VIEW = {'front': 'frente', 'side': 'lado', 'back': 'costas', 'three_quarter': 'tres-quartos', 'top': 'de-cima'}
STAGE = {'st00_testmap': 'mapa-de-teste', 'st01_town': 'praca-da-cidade', 'st02_villa': 'casa-de-julian',
         'st03_beach': 'beira-mar', 'st04_prairie': 'campina-de-dia', 'st05_sunset': 'campina-ao-por-do-sol',
         'st06_forest': 'floresta-a-meia-noite', 'st07_arena': 'ruinas-da-arena',
         'st08_cave': 'altar-da-caverna', 'st09_shrine': 'templo', 'st10_poseidon': 'templo-subterraneo'}
INTERFACE = [('scene', 'Interface'), ('common/menu', 'Interface/nomes-do-menu'),
             ('common/systemwindow.pac', 'Interface/janelas'), ('common/globalobject.pac', 'Interface/objetos-globais'),
             ('font', 'Interface/fonte')]


def who(code):
    c = names.BY_CODE.get(code)
    if not c:
        return code
    return (c[2] + ('-escama-de-triton' if code.endswith('v2') else '')).lower()


class Copier:
    def __init__(self, out):
        self.out, self.index, self.written = out, [], set()

    def copy(self, src, folder, name, kind='image', crop=False):
        if not os.path.exists(src):
            return
        dest = os.path.join(self.out, folder, name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        n = 2
        while dest in self.written:                     # two sources with the same name
            stem, ext = os.path.splitext(name)
            dest = os.path.join(self.out, folder, '%s-%d%s' % (stem, n, ext))
            n += 1
        self.written.add(dest)
        if crop:                                        # renders: drop the empty border
            im = Image.open(src).convert('RGBA')
            box = im.getbbox()
            (im.crop(box) if box else im).save(dest)
        else:
            shutil.copyfile(src, dest)
        self.index.append({'file': dest, 'source': src, 'kind': kind})


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    dump, out = os.path.abspath(argv[1]), os.path.abspath(argv[2])
    c = Copier(out)
    img = os.path.join(dump, 'images')
    pics = 'Imagens'

    # renders
    rdir = os.path.join(dump, 'renders', 'characters')
    for code in sorted(os.listdir(rdir)) if os.path.isdir(rdir) else []:
        for job in sorted(os.listdir(os.path.join(rdir, code))):
            key = job[len(code) + 1:]
            for view, label in VIEW.items():
                c.copy(os.path.join(rdir, code, job, view + '.png'),
                       '%s/Modelos 3D dos personagens/%s' % (pics, who(code)),
                       '%s-%s-%s.png' % (who(code), VARIANT.get(key, key), label), crop=True)
    sdir = os.path.join(dump, 'renders', 'stages')
    for stage in sorted(os.listdir(sdir)) if os.path.isdir(sdir) else []:
        for job in sorted(os.listdir(os.path.join(sdir, stage))):
            part = {'map_model': 'cenario', 'map_model_sky': 'cenario-com-ceu'}.get(job, job.replace('str_type', 'objeto-quebravel-'))
            for view, label in VIEW.items():
                c.copy(os.path.join(sdir, stage, job, view + '.png'), '%s/Cenários/%s' % (pics, STAGE.get(stage, stage)),
                       '%s-%s-%s.png' % (STAGE.get(stage, stage), part, label), crop=True)
    bdir = os.path.join(dump, 'renders', 'backgrounds')
    for job in sorted(os.listdir(bdir)) if os.path.isdir(bdir) else []:
        for view, label in VIEW.items():
            c.copy(os.path.join(bdir, job, view + '.png'), '%s/Cenários/fundos-dos-golpes' % pics,
                   '%s-%s.png' % (job.replace('bigbang_bg_', 'fundo-').replace('_', '-'), label), crop=True)

    # pictures of the game, by subject
    def each(folder):
        p = os.path.join(img, folder)
        for root, _dirs, files in os.walk(p):
            for n in sorted(files):
                if n.lower().endswith('.png'):
                    yield os.path.join(root, n), os.path.relpath(os.path.join(root, n), p)

    for src, rel in each('common/bustup'):
        m = re.match(r'adv_chara_([a-z0-9]+)_(\d+)\.pac', rel.lower())
        code = m.group(1) if m else 'outros'
        label = {'024': 'atena', '025': 'julian-solo', 'ate': 'atena', 'man': 'homem-misterioso',
                 'hatv3': 'haruto-terceiro-traje'}.get(code, who(code))
        c.copy(src, '%s/Retratos das cenas/%s' % (pics, label), '%s-retrato-%s.png' % (label, m.group(2) if m else '00'))
    for src, rel in each('common/image'):
        low = rel.lower()
        name = os.path.basename(low)
        if low.startswith('select_pic_'):
            code = low[11:].split('.')[0].replace('syu', 'shu')
            c.copy(src, '%s/Seleção de personagem' % pics, '%s-selecao.png' % who(code))
        elif low.startswith('select_stage_'):
            c.copy(src, '%s/Cenários/telas-de-selecao' % pics, 'selecao-%s.png' % low[13:].split('.')[0])
        elif low.startswith('still_arc_'):
            c.copy(src, '%s/Ilustrações de evento/encerramentos-do-arcade' % pics,
                   'encerramento-arcade-%s.png' % who(low[10:].split('.')[0]))
        elif low.startswith('still_ed_'):
            c.copy(src, '%s/Ilustrações de evento/finais' % pics, 'final-%s.png' % low[9:11])
        elif low.startswith('still_st_'):
            c.copy(src, '%s/Ilustrações de evento/historia' % pics, 'ilustracao-%s.png' % low[9:11])
        else:
            c.copy(src, '%s/Ilustrações de evento/outras' % pics, name)
    for src, rel in each('common/background'):
        c.copy(src, '%s/Fundos das cenas' % pics, os.path.basename(rel).lower())
    for src, rel in each('common/item'):
        m = re.search(r'(\d+)', os.path.basename(rel))
        c.copy(src, '%s/Aqua Drops' % pics, 'aqua-drop-%d.png' % (int(m.group(1)) + 1 if m else 0))
    for src, rel in each('scene/gallery/profiledata.pac'):
        m = re.match(r'CHARA_PIC_(\w+)\.png', os.path.basename(rel))
        if m:
            c.copy(src, '%s/Arte dos personagens' % pics, '%s-arte.png' % who(m.group(1).lower()))
    for src, rel in each('scene/battle/character'):
        code = rel.split('/')[0].split('.')[0]
        code, colour = (code.rsplit('_', 1) + [''])[:2]
        parts = [p.split('.')[0].lower() for p in rel.split('/')[1:-1]]
        c.copy(src, '%s/Texturas dos modelos/%s' % (pics, who(code)),
               '-'.join([x for x in [who(code), 'jogador-2' if colour == '01' else '', *parts,
                                     os.path.basename(rel)[:-4].lower()] if x]) + '.png', kind='texture')
    for src, rel in each('scene/battle/map'):
        c.copy(src, '%s/Texturas dos modelos/cenarios' % pics, rel.lower().replace('/', '-').replace('.pac', ''),
               kind='texture')
    for folder, dest in INTERFACE:
        for src, rel in each(folder):
            if folder == 'scene' and rel.startswith(('battle/character', 'battle/map')):
                continue
            sub = os.path.dirname(rel).lower().replace('.pac', '')
            c.copy(src, '%s/%s/%s' % (pics, dest, sub), os.path.basename(rel).lower(), kind='interface')
    for n in ('ICON0.PNG', 'PIC1.PNG'):
        c.copy(os.path.join(dump, 'iso', 'PSP_GAME', n), '%s/Interface/disco' % pics, n.lower())
    xmb = os.path.join(dump, 'files', 'xmb')
    for n in sorted(os.listdir(xmb)) if os.path.isdir(xmb) else []:
        c.copy(os.path.join(xmb, n), '%s/Interface/disco' % pics, n.lower())

    # videos, music, voices
    vdir = os.path.join(dump, 'video')
    titles = {'op': 'abertura', 'start': 'prologo', 'kog_vs_pos': 'batalha-final-kouga',
              'sey_vs_pos': 'batalha-final-seiya', 'endroll': 'creditos-finais'}
    for n in sorted(os.listdir(vdir)) if os.path.isdir(vdir) else []:
        c.copy(os.path.join(vdir, n), 'Vídeos', '%s.mp4' % titles.get(n[:-4], n[:-4]), kind='video')
    adir = os.path.join(dump, 'audio')
    for root, _dirs, files in os.walk(adir):
        rel = os.path.relpath(root, adir)
        for n in sorted(files):
            src = os.path.join(root, n)
            if rel == 'bgm':
                c.copy(src, 'Música/Músicas', n, kind='music')
            elif rel.startswith('event/sound'):
                num = rel.split('/')[-1]
                if num in STORY:
                    m = re.match(r'(\d+)_(\d+)_(\w+)\.ogg', n)
                    c.copy(src, 'Música/Vozes/História de %s' % STORY[num],
                           '%s_%s_%s.ogg' % (m.group(1), m.group(2), names.speaker(m.group(3))[1].lower().replace('???', 'desconhecido'))
                           if m else n, kind='voice')
                else:
                    c.copy(src, 'Música/Vozes/Frases dos personagens', '%s_%s' % (num, n), kind='voice')
            elif rel.startswith('scene/battle/sound/voice'):
                c.copy(src, 'Música/Vozes/Golpes especiais', n, kind='voice')
            elif rel.startswith('banks'):
                c.copy(src, 'Música/Efeitos/' + rel[6:].replace('.pac', ''), n, kind='effect')
    mdir = os.path.join(dump, 'models')
    for root, _dirs, files in os.walk(mdir):
        for n in sorted(files):
            c.copy(os.path.join(root, n), os.path.join('Modelos 3D', os.path.relpath(root, mdir)), n, kind='model')

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
