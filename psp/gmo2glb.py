#!/usr/bin/env python3
"""GMO model (+ textures, + motions) -> binary glTF 2.0 (.glb).

The skeleton becomes glTF nodes, skinned parts share one skin (joints = every bone, inverse bind
matrices = the BlendOffsets of the bone that draws the part), every motion becomes a glTF animation. Vertex data is
de-quantised with the model's VertexOffset commands; one model unit = 1 cm, the root node scales
it to metres. Materials are unlit (the game draws the painted textures as they are).

Attachments (`--attach FILE.gmo=bone`) are other models hung from a bone of the main one
(capes, hair, weapons: the APPENDAGE packs of the game).

usage: gmo2glb.py MODEL.gmo OUT.glb [--textures DIR ...] [--motions DIR_OR_FILE ...]
                  [--attach FILE.gmo=BONE ...]
"""
import io
import json
import os
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gim  # noqa: E402
import gmo  # noqa: E402

FLOAT, USHORT, UINT, UBYTE = 5126, 5123, 5125, 5121


class Glb:
    def __init__(self):
        self.bin = bytearray()
        self.j = {'asset': {'version': '2.0', 'generator': 'games-extractor psp/gmo2glb.py'},
                  'scene': 0, 'scenes': [{'nodes': []}], 'nodes': [], 'meshes': [], 'materials': [],
                  'accessors': [], 'bufferViews': [], 'buffers': []}

    def view(self, data, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        v = {'buffer': 0, 'byteOffset': len(self.bin), 'byteLength': len(data)}
        if target:
            v['target'] = target
        self.bin += data
        self.j['bufferViews'].append(v)
        return len(self.j['bufferViews']) - 1

    def accessor(self, array, ctype, kind, target=None, minmax=False, normalized=False):
        dt = {FLOAT: '<f4', USHORT: '<u2', UINT: '<u4', UBYTE: 'u1'}[ctype]
        a = np.ascontiguousarray(array, dtype=dt)
        acc = {'bufferView': self.view(a.tobytes(), target), 'componentType': ctype,
               'count': int(a.shape[0]), 'type': kind}
        if normalized:
            acc['normalized'] = True
        if minmax:
            flat = a.reshape(a.shape[0], -1)
            acc['min'] = [float(x) for x in flat.min(0)]
            acc['max'] = [float(x) for x in flat.max(0)]
        self.j['accessors'].append(acc)
        return len(self.j['accessors']) - 1

    def save(self, path):
        while len(self.bin) % 4:
            self.bin.append(0)
        self.j['buffers'] = [{'byteLength': len(self.bin)}]
        j = {k: v for k, v in self.j.items() if v or k in ('asset', 'scene')}
        text = json.dumps(j, separators=(',', ':')).encode('utf-8')
        text += b' ' * (-len(text) % 4)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(text) + 8 + len(self.bin)))
            f.write(struct.pack('<I4s', len(text), b'JSON') + text)
            f.write(struct.pack('<I4s', len(self.bin), b'BIN\0') + bytes(self.bin))


class Textures:
    """Finds the image of a GMO texture: embedded GIM first, then <stem>.gim/.png in the folders."""

    def __init__(self, dirs):
        self.index = {}
        for d in dirs:
            for root, _dirs, names in os.walk(d):
                for n in names:
                    stem, ext = os.path.splitext(n.lower())
                    if ext in ('.gim', '.png'):
                        self.index.setdefault(stem, os.path.join(root, n))

    def image(self, tex):
        from PIL import Image
        embedded = tex.get('image')
        if embedded and b'MIG.00.1PSP' in embedded[:64]:
            return gim.decode(embedded)[0]
        stem = os.path.splitext(os.path.basename(tex['file'].replace('\\', '/')))[0].lower()
        path = self.index.get(stem)
        if not path:
            if embedded:                               # the artist's source image (TGA) left in the file
                try:
                    return Image.open(io.BytesIO(embedded)).convert('RGBA')
                except Exception:
                    return None
            return None
        if path.lower().endswith('.png'):
            return Image.open(path).convert('RGBA')
        return gim.decode(Path(path).read_bytes())[0]


def alpha_mode(img, hint):
    a = np.asarray(img)[:, :, 3]
    if hint.upper().startswith('TR_'):
        return 'BLEND'
    if a.min() >= 250:
        return 'OPAQUE'
    soft = ((a > 16) & (a < 240)).mean()
    return 'BLEND' if soft > 0.25 else 'MASK'


def convert(model_path, out_path, texture_dirs=(), motion_files=(), attachments=(), model_index=0):
    """attachments: [{'file': gmo path, 'bone': bone name or index of the main model,
    'translation', 'rotation' (quaternion), 'scale': optional placement under that bone}, ...]"""
    model = gmo.models(model_path)[model_index]
    g = Glb()
    j = g.j
    report = {'model': os.path.basename(model_path), 'bones': len(model.bones), 'missing_textures': [],
              'vertices': 0, 'triangles': 0, 'animations': 0, 'attachments': []}
    root = {'name': os.path.splitext(os.path.basename(out_path))[0], 'scale': [0.01, 0.01, 0.01], 'children': []}
    j['nodes'].append(root)                       # node 0 = root (cm -> m)
    j['scenes'][0]['nodes'] = [0]
    textures = Textures(texture_dirs)
    # one skin for the whole file (importers cope badly with a skin hanging inside another one)
    skin_joints = []                  # node index of every bone, parents first
    joint_world = {}                  # node index -> bind-pose matrix in the scene
    joint_ibm = {}                    # node index -> inverse bind matrix given by the file
    pending = []                      # (attributes dict, per-vertex node indices) of skinned primitives

    def add(model, parent_index, prefix, world=None):
        """Nodes, meshes, skins and materials of one model; returns bone index -> node index.
        `world` is the bind-pose matrix of the parent node: skinned vertices are written in the
        space of the whole scene, so that every skin of the file is in its bind pose as it stands."""
        parent_node = j['nodes'][parent_index]
        node_of = {}
        for b in model.bones:
            n = {'name': prefix + b.name}
            if b.simple():
                if any(b.translate):
                    n['translation'] = [float(x) for x in b.translate]
                if tuple(b.rotate) != (0.0, 0.0, 0.0, 1.0):
                    q = np.array(b.rotate, dtype=np.float64)
                    n['rotation'] = [float(x) for x in q / (np.linalg.norm(q) or 1.0)]
                if tuple(b.scale) != (1.0, 1.0, 1.0):
                    n['scale'] = [float(x) for x in b.scale]
            else:
                n['matrix'] = [float(x) for x in b.local().T.reshape(-1)]
            node_of[b.index] = len(j['nodes'])
            j['nodes'].append(n)
        for b in model.bones:
            parent = j['nodes'][node_of[b.parent]] if b.parent is not None else parent_node
            parent.setdefault('children', []).append(node_of[b.index])
        base = world if world is not None else np.eye(4)
        for b, m in zip(model.bones, model.world_matrices()):
            skin_joints.append(node_of[b.index])
            joint_world[node_of[b.index]] = base @ m
        images = {}
        mat_index = {}

        def material(mi, hint):
            key = (mi, hint.upper().startswith('TR_'))
            if key in mat_index:
                return mat_index[key]
            mat = model.materials[mi] if mi is not None and mi < len(model.materials) else None
            out = {'name': mat['name'] if mat else 'default', 'doubleSided': True,
                   'extensions': {'KHR_materials_unlit': {}},
                   'pbrMetallicRoughness': {'metallicFactor': 0.0, 'roughnessFactor': 1.0}}
            if mat:
                out['pbrMetallicRoughness']['baseColorFactor'] = [float(min(1.0, max(0.0, x)))
                                                                  for x in mat['diffuse']]
                ti = mat['texture']
                if ti is not None and ti < len(model.textures):
                    tex = model.textures[ti]
                    if ti not in images:
                        img = textures.image(tex)
                        if img is None:
                            report['missing_textures'].append(tex['file'] or tex['name'])
                            images[ti] = None
                        else:
                            buf = io.BytesIO()
                            img.save(buf, 'PNG')
                            j.setdefault('images', []).append({'name': tex['name'], 'mimeType': 'image/png',
                                                               'bufferView': g.view(buf.getvalue())})
                            j.setdefault('samplers', [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497,
                                                       'wrapT': 10497}])
                            j.setdefault('textures', []).append({'sampler': 0, 'source': len(j['images']) - 1})
                            images[ti] = (len(j['textures']) - 1, alpha_mode(img, hint))
                    if images[ti]:
                        out['pbrMetallicRoughness']['baseColorTexture'] = {'index': images[ti][0]}
                        mode = images[ti][1]
                        if mode != 'OPAQUE':
                            out['alphaMode'] = mode
                            if mode == 'MASK':
                                out['alphaCutoff'] = 0.5
            j['materials'].append(out)
            j.setdefault('extensionsUsed', ['KHR_materials_unlit'])
            mat_index[key] = len(j['materials']) - 1
            return mat_index[key]

        for b in model.bones:
            for pi in b.parts:
                if pi >= len(model.parts):
                    continue
                part = model.parts[pi]
                skinned = bool(b.blend_bones)
                groups = {}
                for mesh in part['meshes']:
                    for draw in mesh['draws']:
                        arr = part['arrays'][draw['arrays']] if draw['arrays'] < len(part['arrays']) else None
                        if arr is None or arr.pos is None:
                            continue
                        tris = gmo.triangles(draw)
                        if not len(tris) or tris.max() >= arr.count:
                            continue
                        n = arr.count
                        joints = np.zeros((n, 4), dtype=np.int64)
                        weights = np.zeros((n, 4), dtype=np.float64)
                        if skinned:
                            subset = mesh['subset'] or [0]
                            if arr.weights is None:
                                joints[:, 0] = subset[0]
                                weights[:, 0] = 1.0
                            else:
                                w = arr.weights[:, :len(subset)]
                                order = np.argsort(-w, axis=1)[:, :4]
                                top = np.take_along_axis(w, order, axis=1)
                                ids = np.array(subset, dtype=np.int64)[order]
                                total = top.sum(1, keepdims=True)
                                total[total == 0] = 1.0
                                top = top / total
                                ids[top == 0] = 0
                                weights[:, :top.shape[1]] = top
                                joints[:, :ids.shape[1]] = ids
                                empty = weights.sum(1) == 0
                                weights[empty, 0] = 1.0
                                joints[empty, 0] = subset[0]
                        key = (mesh['material'], arr.col is not None)
                        grp = groups.setdefault(key, {'pos': [], 'nrm': [], 'uv': [], 'col': [], 'j': [],
                                                      'w': [], 'idx': [], 'count': 0})
                        grp['pos'].append(arr.pos)
                        grp['nrm'].append(arr.nrm if arr.nrm is not None else np.zeros((n, 3)))
                        grp['uv'].append(arr.uv if arr.uv is not None else np.zeros((n, 2)))
                        if arr.col is not None:
                            grp['col'].append(arr.col)
                        grp['j'].append(joints)
                        grp['w'].append(weights)
                        grp['idx'].append(tris + grp['count'])
                        grp['count'] += n
                prims = []
                for (mi, has_col), grp in groups.items():
                    pos = np.vstack(grp['pos'])
                    if skinned and world is not None:
                        pos = pos @ world[:3, :3].T + world[:3, 3]
                        grp['nrm'] = [np.vstack(grp['nrm']) @ world[:3, :3].T]
                    idx = np.vstack(grp['idx'])
                    used = np.unique(idx)                         # drop vertices no triangle uses
                    remap = np.full(pos.shape[0], -1, dtype=np.int64)
                    remap[used] = np.arange(len(used))
                    idx = remap[idx]
                    nrm = np.vstack(grp['nrm'])[used]
                    # glTF front faces are counter-clockwise: follow the stored normals
                    p3 = pos[used][idx]
                    face = np.cross(p3[:, 1] - p3[:, 0], p3[:, 2] - p3[:, 0])
                    agree = np.einsum('ij,ij->i', face, nrm[idx].sum(1))
                    if (agree < 0).sum() > (agree > 0).sum():
                        idx = idx[:, ::-1]
                    length = np.linalg.norm(nrm, axis=1, keepdims=True)
                    nrm = np.where(length > 1e-6, nrm / np.where(length > 1e-6, length, 1.0), [0.0, 1.0, 0.0])
                    attrs = {'POSITION': g.accessor(pos[used], FLOAT, 'VEC3', 34962, minmax=True),
                             'NORMAL': g.accessor(nrm, FLOAT, 'VEC3', 34962),
                             'TEXCOORD_0': g.accessor(np.vstack(grp['uv'])[used], FLOAT, 'VEC2', 34962)}
                    if has_col:
                        attrs['COLOR_0'] = g.accessor(np.vstack(grp['col'])[used], FLOAT, 'VEC4', 34962)
                    if skinned:
                        blend = np.array([node_of[i] for i in b.blend_bones], dtype=np.int64)
                        pending.append((attrs, blend[np.vstack(grp['j'])[used]]))
                        attrs['WEIGHTS_0'] = g.accessor(np.vstack(grp['w'])[used], FLOAT, 'VEC4', 34962)
                    big = len(used) > 65535
                    prims.append({'attributes': attrs, 'mode': 4, 'material': material(mi, b.name),
                                  'indices': g.accessor(idx.reshape(-1), UINT if big else USHORT, 'SCALAR',
                                                        34963)})
                    report['vertices'] += len(used)
                    report['triangles'] += len(idx)
                if not prims:
                    continue
                j['meshes'].append({'name': prefix + part['name'], 'primitives': prims})
                node = {'name': prefix + part['name'] + '_mesh', 'mesh': len(j['meshes']) - 1}
                if skinned:
                    back = np.linalg.inv(world) if world is not None else np.eye(4)
                    for i, m in zip(b.blend_bones, b.blend_offsets):
                        joint_ibm.setdefault(node_of[i], m @ back)
                    node['skin'] = 0
                    root['children'].append(len(j['nodes']))      # a skinned mesh follows its joints only
                else:
                    j['nodes'][node_of[b.index]].setdefault('children', []).append(len(j['nodes']))
                j['nodes'].append(node)
        return node_of

    node_of = add(model, 0, '')
    by_name = {b.name.lower(): node_of[b.index] for b in model.bones}
    bone_of = {v: k for k, v in node_of.items()}
    bind = model.world_matrices()
    for att in attachments:
        if isinstance(att, (tuple, list)):
            att = {'file': att[0], 'bone': att[1]}
        path, bone = att['file'], att['bone']
        target = node_of.get(bone) if isinstance(bone, int) else by_name.get(str(bone).lower())
        if target is None:
            report['attachments'].append('%s: no bone %s' % (os.path.basename(path), bone))
            continue
        stem = os.path.splitext(os.path.basename(path))[0].lower()
        world = bind[bone_of[target]]
        if any(k in att for k in ('translation', 'rotation', 'scale')):
            local = np.eye(4)
            local[:3, 3] = att.get('translation') or (0, 0, 0)
            local = local @ gmo.quat_matrix(att.get('rotation') or (0, 0, 0, 1))
            local[:3, :3] = local[:3, :3] * np.array(att.get('scale') or (1, 1, 1))
            world = world @ local
            holder = {'name': stem + '/attach'}
            for k in ('translation', 'rotation', 'scale'):
                if att.get(k) is not None:
                    holder[k] = [float(x) for x in att[k]]
            j['nodes'][target].setdefault('children', []).append(len(j['nodes']))
            target = len(j['nodes'])
            j['nodes'].append(holder)
            skin_joints.append(target)
            joint_world[target] = world
        for extra in gmo.models(path):
            add(extra, target, stem + '/', world)
        report['attachments'].append('%s -> %s' % (os.path.basename(path), j['nodes'][target]['name']
                                                     if isinstance(bone, int) else bone))

    if pending:
        slot = {n: i for i, n in enumerate(skin_joints)}
        lookup = np.zeros(max(skin_joints) + 1, dtype=np.int64)
        for n, i in slot.items():
            lookup[n] = i
        for attrs, nodes in pending:
            attrs['JOINTS_0'] = g.accessor(lookup[nodes], USHORT, 'VEC4', 34962)
        ibm = np.array([joint_ibm.get(n, np.linalg.inv(joint_world[n])).T.reshape(-1) for n in skin_joints],
                       dtype=np.float64)
        j['skins'] = [{'name': root['name'], 'joints': skin_joints,
                       'inverseBindMatrices': g.accessor(ibm, FLOAT, 'MAT4')}]

    # ---- animations
    motions = [(m.name, m) for m in model.motions]
    for path in motion_files:
        for m in gmo.models(path):
            for mo in m.motions:
                motions.append((os.path.splitext(os.path.basename(path))[0].lower(), mo))
    paths = {'translate': ('translation', 'VEC3'), 'rotate': ('rotation', 'VEC4'), 'scale': ('scale', 'VEC3')}
    for name, mo in motions:
        anim = {'name': name, 'samplers': [], 'channels': []}
        for bone, target, interp, frames, values in mo.tracks:
            if bone not in node_of or not model.bones[bone].simple():
                continue
            if target == 'rotate':
                if values.shape[1] != 4:
                    continue
                norm = np.linalg.norm(values, axis=1, keepdims=True)
                values = values / np.where(norm > 1e-9, norm, 1.0)
            elif values.shape[1] != 3:
                continue
            order = np.argsort(frames, kind='stable')
            t, v = frames[order] / mo.rate, values[order]
            keep = np.concatenate([[True], np.diff(t) > 1e-9])     # glTF wants strictly increasing times
            t, v = t[keep], v[keep]
            anim['samplers'].append({'input': g.accessor(t, FLOAT, 'SCALAR', minmax=True),
                                     'output': g.accessor(v, FLOAT, paths[target][1]),
                                     'interpolation': 'STEP' if interp == 0 else 'LINEAR'})
            anim['channels'].append({'sampler': len(anim['samplers']) - 1,
                                     'target': {'node': node_of[bone], 'path': paths[target][0]}})
        if anim['channels']:
            j.setdefault('animations', []).append(anim)
            report['animations'] += 1
    g.save(out_path)
    return report


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    tex, mot, att, mode = [], [], [], None
    for a in argv[3:]:
        if a in ('--textures', '--motions', '--attach'):
            mode = a
        elif mode == '--attach':
            att.append(tuple(a.rsplit('=', 1)))
        elif mode == '--textures':
            tex.append(a)
        elif mode == '--motions':
            if os.path.isdir(a):
                mot += [os.path.join(a, n) for n in sorted(os.listdir(a)) if n.lower().endswith('.gmo')]
            else:
                mot.append(a)
    mot = [m for m in mot if os.path.abspath(m) != os.path.abspath(argv[1])]
    print(convert(argv[1], argv[2], tex, mot, att))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
