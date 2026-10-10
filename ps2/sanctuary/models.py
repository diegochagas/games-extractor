#!/usr/bin/env python3
"""Exports every character model of the game to .glb and writes the Blender render job list.

usage: models.py AFS_DIR DUMP_DIR     -> DUMP_DIR/models/characters/<code>[_cor2].glb,
                                         DUMP_DIR/text/models.json, DUMP_DIR/text/render_jobs.json

`NN.gmi` (00-23 the fighters, 30-34 and 60-67 the people of the scenes) with the body texture
`NN.tpl` (first picture; `NNa.tpl` = the second colour) and the first face of `NN_face.tpl`.
`NNs.gmi` is the simplified model (shadows / far away) and is exported next to it.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import gmi  # noqa: E402
from sanctuary import names  # noqa: E402


def first_png(folder):
    if not os.path.isdir(folder):
        return None
    for root, _dirs, files in os.walk(folder):
        for n in sorted(files):
            if n.lower().endswith('.png'):
                return os.path.join(root, n)
    return None


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    afs, dump = os.path.abspath(argv[1]), os.path.abspath(argv[2])
    out = os.path.join(dump, 'models', 'characters')
    os.makedirs(out, exist_ok=True)
    images = os.path.join(dump, 'images')
    models, jobs = [], []
    for name in sorted(os.listdir(afs)):
        m = re.match(r'(\d\d)(s?)\.gmi$', name, re.I)
        if not m:
            continue
        num, simple = m.group(1), bool(m.group(2))
        with open(os.path.join(afs, name), 'rb') as f:
            model = gmi.parse(f.read())
        label = names.BY_NUMBER[num][3] if num in names.BY_NUMBER else 'outros-%s' % num
        face = first_png(os.path.join(images, '%s_face.tpl' % num))
        variants = [('', first_png(os.path.join(images, '%s.tpl' % num)))]
        if not simple and os.path.isdir(os.path.join(images, '%sa.tpl' % num)):
            variants.append(('_cor2', first_png(os.path.join(images, '%sa.tpl' % num))))
        for suffix, body in variants:
            ident = '%s%s%s' % (label, '_simples' if simple else '', suffix)
            path = os.path.join(out, ident + '.glb')
            with open(path, 'wb') as f:
                f.write(gmi.to_glb(model, (body, face)))
            info = {'id': 'characters/' + ident, 'file': name, 'number': num, 'name': label, 'simple': simple,
                    'colour': 2 if suffix else 1, 'bones': len(model['bones']),
                    'triangles': sum(len(p['faces']) for p in model['parts']), 'parts': len(model['parts']),
                    'texture': os.path.relpath(body, dump) if body else None, 'glb': os.path.relpath(path, dump)}
            models.append(info)
            if not simple:
                jobs.append({'id': info['id'], 'glb': path, 'views': ['front', 'side', 'back', 'three_quarter']})
    os.makedirs(os.path.join(dump, 'text'), exist_ok=True)
    with open(os.path.join(dump, 'text', 'models.json'), 'w', encoding='utf-8') as f:
        json.dump(models, f, ensure_ascii=False, indent=1)
    with open(os.path.join(dump, 'text', 'render_jobs.json'), 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=1)
    print('%d models -> %s, %d render jobs' % (len(models), out, len(jobs)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
