#!/usr/bin/env python3
"""Exports every character model of the game to .glb and writes the Blender render job list.

usage: models.py AFS_DIR DUMP_DIR [--names hades]   -> DUMP_DIR/models/characters/<code>[_cor2].glb,
                                         DUMP_DIR/text/models.json, DUMP_DIR/text/render_jobs.json
`--names hades` uses the roster of The Hades (ps2/hades/names.py), whose `NNh.gmi` hold the hair of
each fighter as a separate model on the same skeleton: it is merged into the body model (and also
exported alone as `_h`).

`NN.gmi` (00-23 the fighters, 30-34 and 60-67 the people of the scenes) with the body texture
`NN.tpl` (first picture; `NNa.tpl` = the second colour), the reflection map of the Cloth (second
picture of `NN.tpl`, baked into the vertex colours of the armour parts) and the first face of `NN_face.tpl`.
`NNs.gmi` is the simplified model (shadows / far away) and is exported next to it.
On The Sanctuary disc the face is not in `NN.gmi` (its head is only the neck): `NN_face.bin` (CMPS, FJF)
holds the face meshes, bone-less models in model space offset from the head bone's position (no rotation),
entry 0 the neutral face and the others the expressions (the matching `NN_face.tpl` pictures replace the face corner of the body texture).
The neutral face is placed on the head bone and merged into the body. `NNadd.bin` holds extra rigged
models of some characters (Saori's head and hair, the Pope's hair and sleeves) that are merged too.
The Hades disc models carry the face in the body itself.
"""
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import cmps  # noqa: E402
import fjf  # noqa: E402
import gmi  # noqa: E402


def extra_models(path):
    """The GMI models of a CMPS/FJF file (`NN_face.bin`, `NNadd.bin`)."""
    with open(path, 'rb') as f:
        data = f.read()
    data = cmps.unpack(data) if cmps.is_cmps(data) else data
    blobs = [data[o:o + n] for _i, o, n in fjf.entries(data)[1]] if data[:4] == b'FJF\0' else [data]
    out = []
    for blob in blobs:
        blob = cmps.unpack(blob) if cmps.is_cmps(blob) else blob
        if blob[:4] == gmi.MAGIC:
            out.append(gmi.parse(blob))
    return out


def head_position(model, bone='h_jnt_head'):
    """Model-space position of the head bone, or None."""
    heads = [i for i, b in enumerate(model['bones']) if b['name'] == bone] or [i for i, b in enumerate(model['bones']) if 'head' in b['name']]
    return tuple(gmi.world_matrices(model['bones'])[heads[0]][3][:3]) if heads else None


def placed(part, index, positions):
    return dict(part, index=index, palette=[], extra=False, positions=positions,
                skin=[(0, 255, 0, 0)] * part['vertices'], weights=[(1.0, 0.0)] * part['vertices'])


def face_parts(path, head):
    """The neutral face of `NN_face.bin` (entry 0) as parts in model space, offset to the head position."""
    models = extra_models(path)
    if not models or not head:
        return []
    tx, ty, tz = head
    return [placed(part, i, [(x + tx, y + ty, z + tz) for x, y, z in part['positions']])
            for i, part in enumerate(models[0]['parts'])]


def add_parts(path):
    """The rigged models of `NNadd.bin` (hair, heads, sleeves of the scene characters) in model space.
    Bone-less entries (small accessories attached at run time) are left out. Returns (parts, head)."""
    parts, head = [], None
    for model in extra_models(path):
        if not model['bones']:
            continue
        head = head or head_position(model)
        worlds = gmi.world_matrices(model['bones'])
        for part in model['parts']:
            pal = part['palette']
            if part['extra'] or not pal:
                positions = part['positions']
            else:
                positions = [gmi.transform(p, worlds[pal[sk[0]] if sk[0] < len(pal) else pal[0]]) for p, sk in zip(part['positions'], part['skin'])]
            parts.append(placed(part, len(parts), positions))
    return parts, head


def nth_png(folder, index=0):
    if not os.path.isdir(folder):
        return None
    found = []
    for root, _dirs, files in os.walk(folder):
        for n in sorted(files):
            if n.lower().endswith('.png'):
                found.append(os.path.join(root, n))
    return found[index] if index < len(found) else None


first_png = nth_png


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    if '--names' in argv:
        import importlib
        names = importlib.import_module(argv[argv.index('--names') + 1] + '.names')
    else:
        from sanctuary import names
    afs, dump = os.path.abspath(argv[1]), os.path.abspath(argv[2])
    out = os.path.join(dump, 'models', 'characters')
    os.makedirs(out, exist_ok=True)
    images = os.path.join(dump, 'images')
    models, jobs = [], []
    for name in sorted(os.listdir(afs)):
        m = re.match(r'(e?\d\d)(s|h)?\.gmi$', name, re.I)
        if not m:
            continue
        num, simple = m.group(1).lower(), m.group(2) == 's'
        variant = '_h' if m.group(2) == 'h' else ''
        with open(os.path.join(afs, name), 'rb') as f:
            data = f.read()
        try:
            model = gmi.parse(data)
        except (ValueError, struct.error) as e:
            print('!! %s: %s' % (name, e))
            continue
        hair = os.path.join(afs, '%sh.gmi' % num)
        if not simple and not variant and os.path.exists(hair):
            try:
                with open(hair, 'rb') as f:
                    hair_model = gmi.parse(f.read())
                if len(hair_model['bones']) == len(model['bones']):
                    model['parts'] = model['parts'] + hair_model['parts']
            except (ValueError, struct.error):
                pass
        if not simple and not variant:
            head = head_position(model)
            try:
                add_file = os.path.join(afs, '%sadd.bin' % num)
                if os.path.exists(add_file):
                    extra, add_head = add_parts(add_file)
                    head = head or add_head
                    model['parts'] = model['parts'] + [dict(p, index=len(model['parts']) + i) for i, p in enumerate(extra)]
                face_file = os.path.join(afs, '%s_face.bin' % num)
                if os.path.exists(face_file):
                    model['parts'] = model['parts'] + [dict(p, index=len(model['parts']) + i) for i, p in enumerate(face_parts(face_file, head))]
            except (ValueError, struct.error):
                pass
        label = names.BY_NUMBER[num][3] if num in names.BY_NUMBER else ('extra-%s' % num if num.startswith('e') else 'outros-%s' % num)
        face = first_png(os.path.join(images, '%s_face.tpl' % num))
        env = nth_png(os.path.join(images, '%s.tpl' % num), 1)
        variants = [('', first_png(os.path.join(images, '%s.tpl' % num)))]
        if not simple and os.path.isdir(os.path.join(images, '%sa.tpl' % num)):
            variants.append(('_cor2', first_png(os.path.join(images, '%sa.tpl' % num))))
        for suffix, body in variants:
            ident = '%s%s%s%s' % (label, variant, '_simples' if simple else '', suffix)
            path = os.path.join(out, ident + '.glb')
            with open(path, 'wb') as f:
                f.write(gmi.to_glb(model, (body, face), env=env))
            info = {'id': 'characters/' + ident, 'file': name, 'number': num, 'name': label, 'simple': simple,
                    'colour': 2 if suffix else 1, 'variant': variant.strip('_'), 'bones': len(model['bones']),
                    'triangles': sum(len(p['faces']) for p in model['parts']), 'parts': len(model['parts']),
                    'texture': os.path.relpath(body, dump) if body else None,
                    'reflection': os.path.relpath(env, dump) if env else None, 'glb': os.path.relpath(path, dump)}
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
