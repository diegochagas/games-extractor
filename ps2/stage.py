#!/usr/bin/env python3
"""Stages (arenas) of the PS2 Saint Seiya games: `NN.gli` + `NN.jnt` + `NN.bin` + `NN_tex.bin`, with the
optional `NN_obj.bin`, `NN_spe.bin`, `NN_far.gmi` and `NN_sky.gmi`.

`NN.gli` (`03 02 05 20`) is the stage list: u32 size, 16, 0, then 3 floats (tile size, x and z of the
grid corner), u16 columns, rows, textures, objects, effects, specials, 2 u16, u32 offsets of the object,
effect and special tables, u32, u32 end, u32 offset of the grid. The grid is columns x rows entries of
u16 present + u8 column + u8 row; every present cell is one tile. The three tables hold 112-byte records
like the bones of gmi.py (4x4 matrix with the placement in the last row, name[32] at 64, s16 link, u16
kind): the objects place the models of `NN_obj.bin` (FJF of GMI models, same order), the effects are
particle emitters (no model), the specials place the billboards of `NN_spe.bin` (fire, lens flares).

`NN.bin` holds one `03 02 05 20` chunk per tile (offsets in `NN.jnt`, an FJF index table) wrapping a GMI
model at +0x60; its vertices are centred on the tile. `NN_far.gmi` is the far scenery and `NN_sky.gmi`
the sky dome (CMPS-compressed GMI). All pieces pick their textures in `NN_tex.bin` (FJF of TIM2) by
index; vertices carry colours (0x80 = 1.0) that multiply the texture. Y is down, like the characters.

usage: stage.py info AFS_DIR ID
       stage.py glb AFS_DIR ID OUT.glb [--images DIR]   DIR = the converted pictures of `ID_tex.bin`
The glTF has one node per piece: tile_C_R, obj_<name>, spe_<name>, far, sky (Y up, unlit materials).
"""
import json
import os
import re
import struct
import sys

import cmps
import fjf
import gmi

MAGIC = b'\x03\x02\x05 '


def records(data, offset, count):
    out = []
    for i in range(count):
        o = offset + 112 * i
        m = struct.unpack_from('<16f', data, o)
        name = data[o + 64:o + 96].split(b'\0')[0].decode('latin-1')
        link, kind = struct.unpack_from('<hH', data, o + 96)
        out.append({'name': name, 'matrix': [list(m[r * 4:r * 4 + 4]) for r in range(4)], 'link': link, 'kind': kind})
    return out


def parse_list(data):
    if data[:4] != MAGIC:
        raise ValueError('not a stage list')
    tile, ox, oz = struct.unpack_from('<3f', data, 16)
    cols, rows, ntex, nobj, nfx, nspe = struct.unpack_from('<6H', data, 28)
    o_obj, o_fx, o_spe = struct.unpack_from('<3I', data, 44)
    o_grid = struct.unpack_from('<I', data, 64)[0]
    cells = []
    for i in range(cols * rows):
        present, x, y = struct.unpack_from('<HBB', data, o_grid + 4 * i)
        if present:
            cells.append((x, y))
    return {'tile': tile, 'origin': (ox, oz), 'columns': cols, 'rows': rows, 'textures': ntex, 'cells': cells,
            'objects': records(data, o_obj, nobj), 'effects': records(data, o_fx, nfx),
            'specials': records(data, o_spe, nspe)}


def tiles(data):
    """The GMI models wrapped in a tile file, in file order."""
    out = []
    for m in re.finditer(re.escape(MAGIC), data):
        o = m.start() + 0x60
        if data[o:o + 4] == gmi.MAGIC:
            size = struct.unpack_from('<I', data, o + 4)[0]
            out.append(gmi.parse(data[o:o + size]))
    return out


def model_file(path):
    with open(path, 'rb') as f:
        data = f.read()
    return gmi.parse(cmps.unpack(data) if cmps.is_cmps(data) else data)


def pack_models(path):
    with open(path, 'rb') as f:
        data = f.read()
    out = []
    for _id, off, size in fjf.entries(data)[1]:
        blob = data[off:off + size]
        blob = cmps.unpack(blob) if cmps.is_cmps(blob) else blob
        out.append(gmi.parse(blob) if blob[:4] == gmi.MAGIC else None)
    return out


def load(afs_dir, ident):
    """Every piece of a stage: {'list', 'tiles': [(cell, model)], 'objects': [(record, model)], 'specials', 'far', 'sky'}."""
    def path(suffix):
        p = os.path.join(afs_dir, ident + suffix)
        return p if os.path.exists(p) else None

    with open(path('.gli'), 'rb') as f:
        info = parse_list(f.read())
    with open(path('.bin'), 'rb') as f:
        chunks = tiles(f.read())
    stage = {'id': ident, 'list': info, 'tiles': list(zip(info['cells'], chunks)), 'objects': [], 'specials': [],
             'far': model_file(path('_far.gmi')) if path('_far.gmi') else None,
             'sky': model_file(path('_sky.gmi')) if path('_sky.gmi') else None}
    for key, suffix in (('objects', '_obj.bin'), ('specials', '_spe.bin')):
        if path(suffix):
            models = pack_models(path(suffix))
            stage[key] = [(rec, models[i]) for i, rec in enumerate(info[key]) if i < len(models) and models[i]]
    return stage


def texture_pngs(images_dir):
    """index -> PNG of the converted texture pack (tim2.py names them NN_id.png)."""
    out = {}
    if images_dir and os.path.isdir(images_dir):
        for n in os.listdir(images_dir):
            m = re.match(r'(\d+)_\d+\.png$', n)
            if m:
                out[int(m.group(1))] = os.path.join(images_dir, n)
    return out


def blend_png(path):
    """Texture of an alpha-blended piece: PS2 alpha 0x80 = opaque."""
    from PIL import Image
    import io
    im = Image.open(path).convert('RGBA')
    im.putalpha(im.getchannel('A').point(lambda a: min(255, a * 2)))
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return buf.getvalue()


class Glb:
    """Minimal binary glTF writer: unlit materials by texture, one node per named mesh."""

    def __init__(self, pngs):
        self.pngs = pngs
        self.bufs, self.views, self.accessors, self.meshes, self.nodes = bytearray(), [], [], [], []
        self.images, self.textures, self.materials, self.material_of = [], [], [], {}

    def view(self, blob, target=None):
        while len(self.bufs) % 4:
            self.bufs.append(0)
        self.views.append({'buffer': 0, 'byteOffset': len(self.bufs), 'byteLength': len(blob)} | ({'target': target} if target else {}))
        self.bufs.extend(blob)
        return len(self.views) - 1

    def material(self, texture, blend):
        key = (texture, blend)
        if key not in self.material_of:
            mat = {'name': 'tex%d%s' % (texture, '_blend' if blend else ''), 'doubleSided': True,
                   'pbrMetallicRoughness': {'metallicFactor': 0, 'roughnessFactor': 1},
                   'alphaMode': 'BLEND' if blend else 'MASK', 'extensions': {'KHR_materials_unlit': {}}}
            if not blend:
                mat['alphaCutoff'] = 0.5
            png = self.pngs.get(texture)
            if png:
                self.images.append({'bufferView': self.view(blend_png(png) if blend else gmi.texture_png(png)), 'mimeType': 'image/png'})
                self.textures.append({'source': len(self.images) - 1, 'sampler': 0})
                mat['pbrMetallicRoughness']['baseColorTexture'] = {'index': len(self.textures) - 1}
            self.materials.append(mat)
            self.material_of[key] = len(self.materials) - 1
        return self.material_of[key]

    def mesh(self, name, model, matrix=None):
        prims = []
        for part in model['parts']:
            if not part['faces']:
                continue
            pos = []
            for p in part['positions']:
                if matrix:
                    p = gmi.transform(p, matrix)
                pos.append((-p[0], -p[1], p[2]))                       # Y down -> Y up, facing the glTF front
            xs, ys, zs = zip(*pos)
            self.accessors.append({'bufferView': self.view(b''.join(struct.pack('<3f', *p) for p in pos), 34962),
                                   'componentType': 5126, 'count': len(pos), 'type': 'VEC3',
                                   'min': [min(xs), min(ys), min(zs)], 'max': [max(xs), max(ys), max(zs)]})
            attributes = {'POSITION': len(self.accessors) - 1}
            self.accessors.append({'bufferView': self.view(b''.join(struct.pack('<2f', u, v) for u, v in part['uvs']), 34962),
                                   'componentType': 5126, 'count': len(pos), 'type': 'VEC2'})
            attributes['TEXCOORD_0'] = len(self.accessors) - 1
            if part['colours']:
                cb = b''.join(struct.pack('<4f', *[min(1.0, c / 128.0) for c in rgba]) for rgba in part['colours'])
                self.accessors.append({'bufferView': self.view(cb, 34962), 'componentType': 5126, 'count': len(pos), 'type': 'VEC4'})
                attributes['COLOR_0'] = len(self.accessors) - 1
            self.accessors.append({'bufferView': self.view(b''.join(struct.pack('<3I', *f) for f in part['faces']), 34963),
                                   'componentType': 5125, 'count': len(part['faces']) * 3, 'type': 'SCALAR'})
            prims.append({'attributes': attributes, 'indices': len(self.accessors) - 1,
                          'material': self.material(part['texture'], bool(part['flags'] & 4))})
        if prims:
            self.meshes.append({'name': name, 'primitives': prims})
            self.nodes.append({'name': name, 'mesh': len(self.meshes) - 1})

    def bytes(self):
        gltf = {'asset': {'version': '2.0', 'generator': 'games-extractor ps2/stage.py'}, 'scene': 0,
                'scenes': [{'nodes': list(range(len(self.nodes)))}], 'nodes': self.nodes, 'meshes': self.meshes,
                'materials': self.materials, 'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}],
                'textures': self.textures, 'images': self.images, 'extensionsUsed': ['KHR_materials_unlit'],
                'accessors': self.accessors, 'bufferViews': self.views, 'buffers': [{'byteLength': len(self.bufs)}]}
        if not self.images:
            del gltf['textures'], gltf['images']
        js = json.dumps(gltf, separators=(',', ':')).encode()
        js += b' ' * ((-len(js)) % 4)
        while len(self.bufs) % 4:
            self.bufs.append(0)
        return (b'glTF' + struct.pack('<II', 2, 12 + 8 + len(js) + 8 + len(self.bufs)) + struct.pack('<II', len(js), 0x4E4F534A) + js +
                struct.pack('<II', len(self.bufs), 0x004E4942) + bytes(self.bufs))


def to_glb(stage, pngs):
    info = stage['list']
    g = Glb(pngs)
    for (x, y), model in stage['tiles']:
        cx = info['origin'][0] + (x + 0.5) * info['tile']
        cz = info['origin'][1] + (y + 0.5) * info['tile']
        g.mesh('tile_%d_%d' % (x, y), model, [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [cx, 0, cz, 1]])
    for key, prefix in (('objects', 'obj_'), ('specials', 'spe_')):
        for rec, model in stage[key]:
            g.mesh(prefix + rec['name'], model, rec['matrix'])
    for key in ('far', 'sky'):
        if stage[key]:
            g.mesh(key, stage[key])
    return g.bytes()


def main(argv):
    if len(argv) >= 4 and argv[1] == 'info':
        stage = load(argv[2], argv[3])
        info = stage['list']
        print('grid %dx%d of %.0f, corner (%.0f, %.0f), %d tiles, %d textures' % (
            info['columns'], info['rows'], info['tile'], *info['origin'], len(info['cells']), info['textures']))
        for (x, y), model in stage['tiles']:
            print('  tile %d,%d: %d parts, %d vertices' % (x, y, len(model['parts']), sum(p['vertices'] for p in model['parts'])))
        for key in ('objects', 'specials'):
            for rec, model in stage[key]:
                print('  %s %s at (%.0f, %.0f, %.0f): %d vertices' % (key[:-1], rec['name'], *rec['matrix'][3][:3],
                                                                   sum(p['vertices'] for p in model['parts'])))
        print('  effects: ' + ', '.join(r['name'] for r in info['effects']))
        for key in ('far', 'sky'):
            if stage[key]:
                print('  %s: %d parts' % (key, len(stage[key]['parts'])))
        return 0
    if len(argv) >= 5 and argv[1] == 'glb':
        images = argv[argv.index('--images') + 1] if '--images' in argv else None
        stage = load(argv[2], argv[3])
        with open(argv[4], 'wb') as f:
            f.write(to_glb(stage, texture_pngs(images)))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
