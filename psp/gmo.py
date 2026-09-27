#!/usr/bin/env python3
"""Sony GMO models ("OMG.00.1PSP"), the PSP's standard model format.

A file is a tree of chunks. Full chunks (type < 0x8000) have a 16-byte header
`u16 type, u16 args offset, u32 size, u32 children offset, u32 data offset`, a name, arguments,
raw data and children; command chunks (type >= 0x8000) have `u16 type, u16 8, u32 size` + arguments.
References to other chunks are `type << 16 | level << 12 | index`.

usage: gmo.py FILE.gmo            print the chunk tree
       gmo.py stats DIR           chunk types / vertex formats / primitive modes used under DIR
"""
import os
import struct
import sys
from pathlib import Path

import numpy as np

FILE, MODEL, BONE, PART, MESH, ARRAYS, MATERIAL, LAYER, TEXTURE, MOTION, FCURVE = range(2, 13)
NAMES = {2: 'File', 3: 'Model', 4: 'Bone', 5: 'Part', 6: 'Mesh', 7: 'Arrays', 8: 'Material', 9: 'Layer',
         10: 'Texture', 11: 'Motion', 12: 'FCurve', 13: 'BlindBlock',
         0x8011: 'FileName?', 0x8012: 'FileName', 0x8013: 'FileImage', 0x8014: 'BoundingBox',
         0x8015: 'VertexOffset',
         0x8041: 'ParentBone', 0x8042: 'Visibility', 0x8043: 'Morph', 0x8044: 'BlendBones',
         0x8045: 'BlendOffsets', 0x8046: 'Pivot', 0x8047: 'MultMatrix', 0x8048: 'Translate',
         0x8049: 'RotateZYX', 0x804A: 'RotateYXZ', 0x804B: 'RotateQ', 0x804C: 'Scale', 0x804D: 'Scale2',
         0x804E: 'DrawPart',
         0x8061: 'SetMaterial', 0x8062: 'BlendSubset', 0x8063: 'Subdivision', 0x8064: 'KnotVectorU',
         0x8065: 'KnotVectorV', 0x8066: 'DrawArrays', 0x8067: 'DrawParticle', 0x8068: 'DrawBSpline',
         0x8069: 'DrawRectMesh', 0x806A: 'DrawRectPatch',
         0x8081: 'RenderState', 0x8082: 'Diffuse', 0x8083: 'Specular', 0x8084: 'Emission',
         0x8085: 'Ambient', 0x8086: 'Reflection', 0x8087: 'Refraction', 0x8088: 'Bump',
         0x8091: 'SetTexture', 0x8092: 'MapType', 0x8093: 'MapFactor', 0x8094: 'BlendFunc',
         0x8095: 'TexFunc', 0x8096: 'TexFilter', 0x8097: 'TexWrap', 0x8098: 'TexCrop', 0x8099: 'TexGen',
         0x809A: 'TexMatrix',
         0x80B1: 'FrameLoop', 0x80B2: 'FrameRate', 0x80B3: 'Animate', 0x80B4: 'FrameRepeat'}


class Chunk:
    __slots__ = ('type', 'name', 'args', 'data', 'children', 'offset')

    def __init__(self, typ, name, args, data, children, offset):
        self.type, self.name, self.args, self.data, self.children, self.offset = typ, name, args, data, children, offset

    def find(self, typ):
        return [c for c in self.children if c.type == typ]

    def first(self, typ):
        for c in self.children:
            if c.type == typ:
                return c
        return None

    def ints(self):
        return struct.unpack('<%di' % (len(self.args) // 4), self.args[:len(self.args) // 4 * 4])

    def floats(self):
        return struct.unpack('<%df' % (len(self.args) // 4), self.args[:len(self.args) // 4 * 4])


def parse_chunks(d, p, end):
    out = []
    while p + 8 <= end:
        typ, hs, size = struct.unpack_from('<HHI', d, p)
        if size < 8 or p + size > end:
            break
        if typ & 0x8000:
            out.append(Chunk(typ, '', d[p + 8:p + size], b'', [], p))
        else:
            child, data = struct.unpack_from('<II', d, p + 8)
            name = d[p + 16:p + hs].split(b'\0')[0].decode('shift_jis', 'replace')
            first = min(x for x in (child, data, size) if x >= hs)
            args = d[p + hs:p + first]
            raw = d[p + data:p + child] if child > data else b''
            out.append(Chunk(typ, name, args, raw, parse_chunks(d, p + child, p + size), p))
        p += size
    return out


def load(path_or_bytes):
    d = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else Path(path_or_bytes).read_bytes()
    if d[:11] != b'OMG.00.1PSP':
        raise ValueError('not a GMO file')
    root = parse_chunks(d, 16, len(d))
    if not root or root[0].type != FILE:
        raise ValueError('GMO without a File chunk')
    return root[0]


def ref(value):
    """(chunk type, index) of a reference, or None for a null reference."""
    if value in (0, -1, 0xFFFFFFFF):
        return None
    return (value >> 16) & 0xFFFF, value & 0xFFF


# ---------------------------------------------------------------- vertex arrays

def vertex_layout(fmt):
    """Offsets of the components of one vertex (GE vertex type bits, the GE's alignment rules)."""
    tex, col, nrm, pos = fmt & 3, (fmt >> 2) & 7, (fmt >> 5) & 3, (fmt >> 7) & 3
    wgt, nweights = (fmt >> 9) & 3, ((fmt >> 14) & 7) + 1
    size = {0: 0, 1: 1, 2: 2, 3: 4}
    lay = {'weights': nweights if wgt else 0}
    off = 0
    align = 1

    def put(key, esize, count):
        nonlocal off, align
        if not esize:
            lay[key] = None
            return
        off = (off + esize - 1) // esize * esize
        lay[key] = (off, esize, count)
        off += esize * count
        align = max(align, esize)

    put('w', size[wgt], nweights)
    put('t', size[tex], 2)
    put('c', {0: 0, 4: 2, 5: 2, 6: 2, 7: 4}.get(col, 0), 1)
    put('n', size[nrm], 3)
    put('p', size[pos], 3)
    lay['colour'] = col
    lay['size'] = (off + align - 1) // align * align
    return lay


def read_field(raw, stride, count, spec, signed):
    off, esize, n = spec
    dt = {1: 'i1' if signed else 'u1', 2: '<i2' if signed else '<u2', 4: '<f4'}[esize]
    a = np.frombuffer(raw, dtype=np.uint8)[:stride * count].reshape(count, stride)
    return np.ascontiguousarray(a[:, off:off + esize * n]).view(dt).reshape(count, n).astype(np.float64), esize


class Arrays:
    """Decoded vertex array: positions, normals, uvs, colours (0..1), weights (n, k)."""

    def __init__(self, chunk, offsets):
        fmt, count, morphs = struct.unpack_from('<III', chunk.args, 0)
        self.format, self.count, self.name = fmt, count, chunk.name
        lay = vertex_layout(fmt)
        self.stride = lay['size']
        raw = chunk.data
        self.morphs = max(1, morphs)
        if len(raw) < self.stride * count:
            raise ValueError('%s: %d vertices of %d bytes do not fit in %d bytes'
                             % (chunk.name, count, self.stride, len(raw)))
        self.pos = self.nrm = self.uv = self.col = self.weights = None
        if lay['p']:
            v, esize = read_field(raw, self.stride, count, lay['p'], True)
            if esize < 4:
                v /= (128.0 if esize == 1 else 32768.0)
                o = offsets.get('p')
                if o:
                    v = v * np.array(o[3:6]) + np.array(o[0:3])
            self.pos = v
        if lay['n']:
            v, esize = read_field(raw, self.stride, count, lay['n'], True)
            if esize < 4:
                v /= (127.0 if esize == 1 else 32767.0)
            self.nrm = v
        if lay['t']:
            v, esize = read_field(raw, self.stride, count, lay['t'], False)
            if esize < 4:
                v /= (128.0 if esize == 1 else 32768.0)
                o = offsets.get('t')
                if o:
                    v = v * np.array(o[2:4]) + np.array(o[0:2])
            self.uv = v
        if lay['c']:
            off, esize, _n = lay['c']
            a = np.frombuffer(raw, dtype=np.uint8)[:self.stride * count].reshape(count, self.stride)
            w = np.ascontiguousarray(a[:, off:off + esize]).view('<u2' if esize == 2 else '<u4').reshape(count)
            w = w.astype(np.uint32)
            c = lay['colour']
            if c == 7:
                rgba = [(w >> s) & 255 for s in (0, 8, 16, 24)]
                rgba = [x / 255.0 for x in rgba]
            elif c == 4:
                rgba = [(w & 31) / 31.0, ((w >> 5) & 63) / 63.0, ((w >> 11) & 31) / 31.0, np.ones(count)]
            elif c == 5:
                rgba = [(w & 31) / 31.0, ((w >> 5) & 31) / 31.0, ((w >> 10) & 31) / 31.0, ((w >> 15) & 1) * 1.0]
            else:
                rgba = [((w >> s) & 15) / 15.0 for s in (0, 4, 8, 12)]
            self.col = np.stack(rgba, axis=1)
        if lay['w']:
            v, esize = read_field(raw, self.stride, count, lay['w'], False)
            if esize < 4:
                v /= (128.0 if esize == 1 else 32768.0)
            self.weights = v


# ---------------------------------------------------------------- model

def quat_matrix(q):
    x, y, z, w = q
    n = (x * x + y * y + z * z + w * w) ** 0.5 or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0],
                     [0, 0, 0, 1]], dtype=np.float64)


def euler_quat(rx, ry, rz, order):
    """Quaternion (x, y, z, w) of rotations applied in `order` (first letter = outermost)."""
    def axis(a, i):
        q = [0.0, 0.0, 0.0, np.cos(a / 2)]
        q[i] = np.sin(a / 2)
        return q

    def mul(a, b):
        ax, ay, az, aw = a
        bx, by, bz, bw = b
        return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]
    qs = {'x': axis(rx, 0), 'y': axis(ry, 1), 'z': axis(rz, 2)}
    q = [0.0, 0.0, 0.0, 1.0]
    for c in order:
        q = mul(q, qs[c])
    return q


class Bone:
    def __init__(self, index, chunk):
        self.index, self.name = index, chunk.name
        self.parent = None
        self.translate = (0.0, 0.0, 0.0)
        self.rotate = (0.0, 0.0, 0.0, 1.0)
        self.scale = (1.0, 1.0, 1.0)
        self.pivot = None
        self.matrix = None                     # MultMatrix, if any
        self.blend_bones = []
        self.blend_offsets = []
        self.parts = []
        self.visible = True
        for c in chunk.children:
            t = c.type
            if t == 0x8041:
                r = ref(c.ints()[0])
                self.parent = r[1] if r else None
            elif t == 0x8048:
                self.translate = c.floats()[:3]
            elif t == 0x804B:
                self.rotate = c.floats()[:4]
            elif t == 0x8049:
                self.rotate = tuple(euler_quat(*c.floats()[:3], 'zyx'))
            elif t == 0x804A:
                self.rotate = tuple(euler_quat(*c.floats()[:3], 'yxz'))
            elif t in (0x804C, 0x804D):
                self.scale = c.floats()[:3]
            elif t == 0x8046:
                self.pivot = c.floats()[:3]
            elif t == 0x8047:
                self.matrix = np.array(c.floats()[:16], dtype=np.float64).reshape(4, 4).T
            elif t == 0x8042:
                self.visible = bool(c.ints()[0] & 1)
            elif t == 0x8044:
                n = c.ints()[0]
                self.blend_bones = [ref(v)[1] for v in c.ints()[1:1 + n]]
            elif t == 0x8045:
                n = c.ints()[0]
                f = c.floats()[1:1 + 16 * n]
                self.blend_offsets = [np.array(f[i * 16:i * 16 + 16], dtype=np.float64).reshape(4, 4).T
                                      for i in range(n)]
            elif t == 0x804E:
                r = ref(c.ints()[0])
                if r:
                    self.parts.append(r[1])

    def simple(self):
        """True when the bone is a plain translate/rotate/scale (what a glTF node can animate)."""
        rs = tuple(self.rotate) != (0.0, 0.0, 0.0, 1.0) or tuple(self.scale) != (1.0, 1.0, 1.0)
        return self.matrix is None and not (self.pivot and rs)

    def local(self, translate=None, rotate=None, scale=None):
        """T * P * R * S * P^-1 (* MultMatrix); the arguments replace the bone's own values."""
        m = np.eye(4)
        m[:3, 3] = self.translate if translate is None else translate
        rs = quat_matrix(self.rotate if rotate is None else rotate)
        s = np.eye(4)
        s[0, 0], s[1, 1], s[2, 2] = self.scale if scale is None else scale
        rs = rs @ s
        if self.pivot:
            p = np.eye(4)
            p[:3, 3] = self.pivot
            q = np.eye(4)
            q[:3, 3] = [-v for v in self.pivot]
            rs = p @ rs @ q
        m = m @ rs
        if self.matrix is not None:
            m = m @ self.matrix
        return m


class Model:
    def __init__(self, chunk):
        self.name = chunk.name
        self.offsets = {}
        self.bbox = None
        for c in chunk.children:
            if c.type == 0x8015:
                fmt = c.ints()[0]
                f = c.floats()[1:]
                if fmt & 0x180:
                    self.offsets['p'] = f
                elif fmt & 3:
                    self.offsets['t'] = f
            elif c.type == 0x8014:
                self.bbox = c.floats()[:6]
        self.bones = [Bone(i, c) for i, c in enumerate(chunk.find(BONE))]
        self.parts = []
        for pc in chunk.find(PART):
            part = {'name': pc.name, 'meshes': [], 'arrays': []}
            for ac in pc.find(ARRAYS):
                try:
                    part['arrays'].append(Arrays(ac, self.offsets))
                except ValueError as e:
                    part['arrays'].append(None)
                    part.setdefault('errors', []).append(str(e))
            for mc in pc.find(MESH):
                mesh = {'name': mc.name, 'material': None, 'subset': None, 'draws': []}
                for c in mc.children:
                    if c.type == 0x8061:
                        r = ref(c.ints()[0])
                        mesh['material'] = r[1] if r else None
                    elif c.type == 0x8062:
                        v = c.ints()
                        mesh['subset'] = list(v[1:1 + v[0]])
                    elif c.type == 0x8066:
                        arr, mode, nverts, nprims = struct.unpack_from('<IIII', c.args, 0)
                        idx = np.frombuffer(c.args, dtype='<u2', offset=16, count=nverts * nprims)
                        mesh['draws'].append({'arrays': ref(arr)[1], 'mode': mode,
                                              'indices': idx.reshape(nprims, nverts)})
                part['meshes'].append(mesh)
            self.parts.append(part)
        self.textures = []
        for tc in chunk.find(TEXTURE):
            fn = tc.first(0x8012)
            im = tc.first(0x8013)
            self.textures.append({'name': tc.name,
                                  'file': fn.args.split(b'\0')[0].decode('shift_jis', 'replace') if fn else '',
                                  'image': im.args[4:4 + struct.unpack_from('<I', im.args, 0)[0]] if im else None})
        self.materials = []
        for mc in chunk.find(MATERIAL):
            mat = {'name': mc.name, 'texture': None, 'diffuse': (1.0, 1.0, 1.0, 1.0), 'state': [], 'layers': []}
            for c in mc.children:
                if c.type == 0x8082:
                    mat['diffuse'] = c.floats()[:4]
                elif c.type == 0x8081:
                    mat['state'].append(c.ints())
                elif c.type == LAYER:
                    layer = {'texture': None, 'blend': None, 'wrap': None}
                    for l in c.children:
                        if l.type == 0x8091:
                            r = ref(l.ints()[0])
                            layer['texture'] = r[1] if r else None
                        elif l.type == 0x8094:
                            layer['blend'] = l.ints()
                        elif l.type == 0x8097:
                            layer['wrap'] = l.ints()
                    mat['layers'].append(layer)
                    if mat['texture'] is None:
                        mat['texture'] = layer['texture']
            self.materials.append(mat)
        self.motions = [Motion(c) for c in chunk.find(MOTION)]

    def world_matrices(self, locals_=None):
        out = [None] * len(self.bones)
        for b in self.bones:                       # parents always come first
            m = locals_[b.index] if locals_ else b.local()
            out[b.index] = m if b.parent is None or out[b.parent] is None else out[b.parent] @ m
        return out


def half_floats(raw):
    return np.frombuffer(raw[:len(raw) // 2 * 2], dtype='<f2').astype(np.float64)


class Motion:
    """One animation: `tracks` = list of (bone index, 'translate'|'rotate'|'scale', interpolation,
    frames, values); frame numbers are in `rate` frames per second."""

    TARGETS = {0x48: 'translate', 0x4B: 'rotate', 0x4C: 'scale', 0x4D: 'scale'}

    def __init__(self, chunk):
        self.name = chunk.name
        self.start, self.end, self.rate = 0.0, 0.0, 30.0
        curves = chunk.find(FCURVE)
        self.tracks = []
        self.skipped = 0
        for c in chunk.children:
            if c.type == 0x80B1:
                self.start, self.end = c.floats()[:2]
            elif c.type == 0x80B2:
                self.rate = c.floats()[0] or 30.0
            elif c.type == 0x80B3:
                target, cmd, _index, curve = c.ints()[:4]
                t, cr = ref(target), ref(curve)
                if not t or not cr or t[0] != BONE or cmd not in self.TARGETS or cr[1] >= len(curves):
                    self.skipped += 1
                    continue
                fc = curves[cr[1]]
                fmt, dims, nkeys = struct.unpack_from('<III', fc.args, 0)
                interp = fmt & 0xF
                per_key = 1 + dims * (3 if interp == 2 else 1 if interp != 3 else 3)
                if fmt & 0x80:
                    v = half_floats(fc.data)
                else:
                    v = np.frombuffer(fc.data[:len(fc.data) // 4 * 4], dtype='<f4').astype(np.float64)
                if len(v) < per_key * nkeys:
                    self.skipped += 1
                    continue
                v = v[:per_key * nkeys].reshape(nkeys, per_key)
                self.tracks.append((t[1], self.TARGETS[cmd], interp, v[:, 0].copy(), v[:, 1:1 + dims].copy()))


def triangles(draw):
    """(n, 3) index array of a DrawArrays command (3 triangles, 4 strip, 5 fan)."""
    out = []
    for prim in draw['indices']:
        p = [int(i) for i in prim]
        if draw['mode'] == 3:
            out += [p[i:i + 3] for i in range(0, len(p) - 2, 3)]
        elif draw['mode'] == 4:
            for i in range(len(p) - 2):
                tri = [p[i], p[i + 1], p[i + 2]] if i % 2 == 0 else [p[i + 1], p[i], p[i + 2]]
                if len(set(tri)) == 3:
                    out.append(tri)
        elif draw['mode'] == 5:
            out += [[p[0], p[i], p[i + 1]] for i in range(1, len(p) - 1)]
    return np.array(out, dtype=np.int64).reshape(-1, 3)


def models(path_or_bytes):
    return [Model(c) for c in load(path_or_bytes).find(MODEL)]


# ---------------------------------------------------------------- command line

def show(chunk, depth=0):
    label = NAMES.get(chunk.type, '%04x' % chunk.type)
    if chunk.type & 0x8000:
        n = len(chunk.args) // 4
        if chunk.type == 0x8012:
            body = chunk.args.split(b'\0')[0].decode('shift_jis', 'replace')
        elif n <= 8:
            body = ' '.join('%d' % i if abs(i) < 0x100000 or (i >> 16) in range(2, 14) and False else
                            ('%.4g' % f if 1e-6 < abs(f) < 1e7 else '0x%x' % (i & 0xFFFFFFFF))
                            for i, f in zip(chunk.ints(), chunk.floats()))
        else:
            body = '%d bytes' % len(chunk.args)
        print('%s%s  %s' % ('  ' * depth, label, body))
    else:
        extra = ''
        if chunk.args:
            extra += ' args=%s' % chunk.args[:16].hex()
        if chunk.data:
            extra += ' data=%d bytes' % len(chunk.data)
        print('%s%s "%s"%s' % ('  ' * depth, label, chunk.name, extra))
        for c in chunk.children:
            show(c, depth + 1)


def stats(root_dir):
    import collections
    types, formats, modes, files = collections.Counter(), collections.Counter(), collections.Counter(), 0
    kinds = collections.Counter()

    def walk(c):
        types[NAMES.get(c.type, '%04x' % c.type)] += 1
        if c.type == ARRAYS:
            formats['%08x' % struct.unpack_from('<I', c.args, 0)[0]] += 1
        if c.type == 0x8066:
            modes[struct.unpack_from('<I', c.args, 4)[0]] += 1
        for k in c.children:
            walk(k)
    for root, _dirs, names in os.walk(root_dir):
        for n in names:
            if n.lower().endswith('.gmo'):
                f = load(os.path.join(root, n))
                files += 1
                walk(f)
                m = f.first(MODEL)
                kinds[('mesh' if m and m.find(PART) else '') + ('+motion' if m and m.find(MOTION) else '')] += 1
    print(files, 'files', dict(kinds))
    print('chunks', sorted(types.items(), key=lambda x: -x[1]))
    print('vertex formats', formats.most_common())
    print('primitive modes', dict(modes))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'stats':
        stats(sys.argv[2])
    elif len(sys.argv) == 2:
        show(load(sys.argv[1]))
    else:
        print(__doc__)
