#!/usr/bin/env python3
"""Character models of the game (`NN.gmi`, CMPS-compressed; `NNs.gmi` = the simple/shadow model).

Header: `19 03 04 20`, u32 size, u32 16, u32 0, u16 bones, u16 parts, u32 bone table offset,
u32 part table offset, u16 3, u16 2. A bone is 112 bytes: a 4x4 float matrix (row major, the
translation in the last row, relative to the parent), s16 parent, 2 u16, name[34], 8 bytes 0xDD.
A part is 48 bytes: u16 2, u16 vertices, u32 (triangles << 16 | flag), u32 flags, u32 offset of the
positions, u32 of the normals, u32 0, u32 of the UVs, u32 of the skin bytes, u32 of an optional fifth
stream, then the 16-byte bone palette (0xFF = unused). Positions are 4 floats: x, y, z and the
strip flag w (1 = this vertex kicks the triangle made with the two before it, 0 = it does not;
strips restart by repeating two vertices with w = 0).
Normals are 4 s16 (/4096). UVs are 2 floats. The stage pieces (see stage.py) have no normals and no
skin: the seventh field, 0 in the characters, is the offset of 4 colour bytes per vertex (0x80 = 1.0), and
the low 16 bits of the triangle count field pick the texture in the stage's texture pack. Skin: 4 bytes per vertex, the first a bone index into
the palette; without the fifth stream the second byte is 255 (one bone), with it the second byte is a
second palette index (255 = none) and the fifth stream holds the two weights as floats. A vertex
bound to one bone keeps its position and normal in that bone's local frame (the bind pose is
rebuilt by chaining the bone matrices); a vertex blended between two bones is in model space.
The model is Y-down (feet at +y), x = left/right.

usage: gmi.py info FILE.gmi
       gmi.py glb FILE.gmi OUT.glb [--texture PNG [--texture2 PNG]] [--env PNG] [--raw] [--parts 0,1,2]
`--env` is the reflection map (the second picture of NN.tpl): the parts flagged 8 are drawn with it
reflected by their normals (sphere mapping). glTF has no such mapping, so the map is baked into the
vertex colours as seen from the front (COLOR_0 multiplies the base texture).
"""
import json
import math
import os
import struct
import sys

import fjf

MAGIC = b'\x19\x03\x04 '


def parse(data):
    data = fjf.unwrap(data)
    if data[:4] != MAGIC:
        raise ValueError('not a GMI model')
    _m, _size, _hs, _z, nbones, nparts, boff, poff, _a, _b = struct.unpack_from('<4sIIIHHIIHH', data, 0)
    bones = []
    for i in range(nbones):
        o = boff + i * 112
        m = struct.unpack_from('<16f', data, o)
        parent = struct.unpack_from('<h', data, o + 64)[0]
        name = data[o + 70:o + 104].split(b'\0')[0].decode('latin-1')
        bones.append({'name': name, 'parent': parent, 'local': [list(m[r * 4:r * 4 + 4]) for r in range(4)]})
    parts = []
    for i in range(nparts):
        o = poff + i * 48
        (_two, nv, tri, flags, opos, onrm, ocol, ouv, oskin, o5) = struct.unpack_from('<HHIIIIIIII', data, o)
        palette = [b for b in data[o + 36:o + 48] if b != 0xFF]
        pos = [struct.unpack_from('<4f', data, opos + 16 * k) for k in range(nv)]
        nrm = [tuple(v / 4096.0 for v in struct.unpack_from('<3h', data, onrm + 8 * k)) for k in range(nv)] if onrm else None
        colours = [tuple(data[ocol + 4 * k:ocol + 4 * k + 4]) for k in range(nv)] if ocol else None
        uv = [struct.unpack_from('<2f', data, ouv + 8 * k) for k in range(nv)]
        skin = [tuple(data[oskin + 4 * k:oskin + 4 * k + 4]) for k in range(nv)]
        weights = [struct.unpack_from('<2f', data, o5 + 8 * k) for k in range(nv)] if o5 else [(1.0, 0.0)] * nv
        tris = []
        for k in range(2, nv):
            if pos[k][3] != 0.0:
                a, b, c = k - 2, k - 1, k
                tris.append((a, c, b) if k % 2 else (a, b, c))
        parts.append({'index': i, 'vertices': nv, 'triangles': tri >> 16, 'texture': tri & 0xFFFF, 'flags': flags,
                      'palette': palette, 'positions': [p[:3] for p in pos], 'normals': nrm, 'colours': colours,
                      'uvs': uv, 'skin': skin, 'faces': tris, 'weights': weights, 'extra': bool(o5)})
    return {'bones': bones, 'parts': parts}


def mat_mul(a, b):
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def world_matrices(bones):
    out = []
    for b in bones:
        m = b['local']
        out.append(mat_mul(m, out[b['parent']]) if b['parent'] >= 0 else m)
    return out


def transform(v, m):
    x, y, z = v
    return (x * m[0][0] + y * m[1][0] + z * m[2][0] + m[3][0],
            x * m[0][1] + y * m[1][1] + z * m[2][1] + m[3][1],
            x * m[0][2] + y * m[1][2] + z * m[2][2] + m[3][2])


def texture_png(path):
    """The game's textures carry PS2 half alpha (0x40-0x80): only real cut-outs stay transparent."""
    from PIL import Image
    import io
    im = Image.open(path).convert('RGBA')
    im.putalpha(im.getchannel('A').point(lambda a: 0 if a < 24 else 255))
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return buf.getvalue()


def to_glb(model, textures=(), raw=False, only=None, frame0=False, env=None):
    """Binary glTF: one node, one mesh with a primitive per part, Y up (the model is turned over)."""
    worlds = world_matrices(model['bones'])
    bufs, views, accessors, prims, images, samplers, texs, mats = bytearray(), [], [], [], [], [], [], []

    def add(blob, target=None):
        while len(bufs) % 4:
            bufs.append(0)
        views.append({'buffer': 0, 'byteOffset': len(bufs), 'byteLength': len(blob)} | ({'target': target} if target else {}))
        bufs.extend(blob)
        return len(views) - 1

    for ti, png in enumerate(textures):
        if png and os.path.exists(png):
            images.append({'bufferView': add(texture_png(png)), 'mimeType': 'image/png'})
            texs.append({'source': len(images) - 1, 'sampler': 0})
            mats.append({'name': 'tex%d' % ti, 'pbrMetallicRoughness': {'baseColorTexture': {'index': len(texs) - 1}, 'metallicFactor': 0, 'roughnessFactor': 1},
                         'alphaMode': 'MASK', 'alphaCutoff': 0.5, 'doubleSided': True, 'extensions': {'KHR_materials_unlit': {}}})
    if not mats:
        mats.append({'name': 'plain', 'pbrMetallicRoughness': {'metallicFactor': 0, 'roughnessFactor': 1}, 'doubleSided': True})
    samplers.append({'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497})
    env_image = None
    if env and os.path.exists(env):
        from PIL import Image
        env_image = Image.open(env).convert('RGB')
    for part in model['parts']:
        if not part['faces'] or (only is not None and part['index'] not in only):
            continue
        pal = part['palette']
        pos, nrm = [], []
        for p, n, sk in zip(part['positions'], part['normals'] or [(0.0, 0.0, 1.0)] * len(part['positions']), part['skin']):
            if raw or not pal:
                m = None
            elif part['extra']:
                m = worlds[pal[sk[0]]] if (sk[1] == 0xFF and sk[0] < len(pal)) else None   # two bones: already in model space
            else:
                m = worlds[pal[sk[0]] if sk[0] < len(pal) else pal[0]]
            if m:
                p = transform(p, m)
                n = transform(n, [m[0], m[1], m[2], [0, 0, 0, 1]])
            pos.append((-p[0], -p[1], p[2]))                               # Y down -> Y up, turned to face the glTF front
            nrm.append((-n[0], -n[1], n[2]))
        pb = b''.join(struct.pack('<3f', *p) for p in pos)
        nb = b''.join(struct.pack('<3f', *n) for n in nrm)
        colours = None
        if env_image is not None and part['flags'] & 8:
            w, h = env_image.size
            colours = []
            for nx, ny, nz in nrm:
                length = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
                u, v = 0.5 + nx / length * 0.5, 0.5 - ny / length * 0.5
                r, g, b = env_image.getpixel((min(w - 1, max(0, int(u * (w - 1)))), min(h - 1, max(0, int(v * (h - 1))))))
                colours.append((min(1.0, 0.35 + r / 255.0 * 1.6), min(1.0, 0.35 + g / 255.0 * 1.6), min(1.0, 0.35 + b / 255.0 * 1.6)))
        ub = b''.join(struct.pack('<2f', u, v) for u, v in part['uvs'])
        ib = b''.join(struct.pack('<3I', *f) for f in part['faces'])
        xs, ys, zs = zip(*pos)
        accessors.append({'bufferView': add(pb, 34962), 'componentType': 5126, 'count': len(pos), 'type': 'VEC3',
                          'min': [min(xs), min(ys), min(zs)], 'max': [max(xs), max(ys), max(zs)]})
        accessors.append({'bufferView': add(nb, 34962), 'componentType': 5126, 'count': len(pos), 'type': 'VEC3'})
        accessors.append({'bufferView': add(ub, 34962), 'componentType': 5126, 'count': len(pos), 'type': 'VEC2'})
        accessors.append({'bufferView': add(ib, 34963), 'componentType': 5125, 'count': len(part['faces']) * 3, 'type': 'SCALAR'})
        n = len(accessors)
        attributes = {'POSITION': n - 4, 'NORMAL': n - 3, 'TEXCOORD_0': n - 2}
        if colours:
            cb = b''.join(struct.pack('<3f', *c) for c in colours)
            accessors.append({'bufferView': add(cb, 34962), 'componentType': 5126, 'count': len(colours), 'type': 'VEC3'})
            attributes['COLOR_0'] = len(accessors) - 1
        mat = 0
        prims.append({'attributes': attributes, 'indices': n - 1, 'material': mat})
    gltf = {'asset': {'version': '2.0', 'generator': 'games-extractor ps2/gmi.py'}, 'scene': 0,
            'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0, 'name': 'model'}], 'meshes': [{'primitives': prims}],
            'materials': mats, 'samplers': samplers, 'textures': texs, 'images': images,
            'extensionsUsed': ['KHR_materials_unlit'],
            'accessors': accessors, 'bufferViews': views, 'buffers': [{'byteLength': len(bufs)}]}
    if not images:
        del gltf['textures'], gltf['images']
    js = json.dumps(gltf, separators=(',', ':')).encode()
    js += b' ' * ((-len(js)) % 4)
    while len(bufs) % 4:
        bufs.append(0)
    return (b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8 + len(bufs)) + struct.pack('<II', len(js), 0x4E4F534A) + js +
            struct.pack('<II', len(bufs), 0x004E4942) + bytes(bufs))


def main(argv):
    if len(argv) >= 3 and argv[1] == 'info':
        with open(argv[2], 'rb') as f:
            model = parse(f.read())
        print('%d bones, %d parts' % (len(model['bones']), len(model['parts'])))
        for b in model['bones']:
            print('  bone %-14s parent %d' % (b['name'], b['parent']))
        for p in model['parts']:
            print('  part %2d: %5d vertices, %5d triangles, flags %d, palette %s' % (p['index'], p['vertices'], len(p['faces']), p['flags'], p['palette']))
        return 0
    if len(argv) >= 4 and argv[1] == 'glb':
        textures = []
        for key in ('--texture', '--texture2'):
            textures.append(argv[argv.index(key) + 1] if key in argv else None)
        with open(argv[2], 'rb') as f:
            model = parse(f.read())
        only = [int(x) for x in argv[argv.index('--parts') + 1].split(',')] if '--parts' in argv else None
        env = argv[argv.index('--env') + 1] if '--env' in argv else None
        with open(argv[3], 'wb') as f:
            f.write(to_glb(model, textures, '--raw' in argv, only, '--frame0' in argv, env))
        print('%s: %d parts -> %s' % (argv[2], len(model['parts']), argv[3]))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
