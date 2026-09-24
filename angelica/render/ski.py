#!/usr/bin/env python3
"""Reader for Angelica skinned meshes (`.ski`, magic MOXBIKSA, version 101).

Layout (little endian):

    0x00  "MOXBIKSA"            0x08 u32 version (101)
    0x0c  u32[24]: nmesh, 0, 0, 0, ntex, nmat, nbones, 0, ?, ...   (padding to 0x6c)
    0x6c  nbones x (u32 len, bytes name)          bone names, ASCII
          ntex   x (u32 len, bytes name)          texture file names, GBK
          nmat   x "MATERIAL: " + 70 bytes        material colours
          nmesh  x mesh:
              u32 len, bytes name (GBK)
              u32 texture index, u32 material index
              u32 vertex count, u32 index count
              vertex_count x 48 bytes:
                  f32 x y z, f32 w0 w1 w2, u8 b0 b1 b2 b3, f32 nx ny nz, f32 u v
              index_count x u16
              vertex_count x 16 bytes (tangents)

The vertices are stored in model space in the skeleton's bind pose, so the
meshes of one character can be drawn together without applying the skeleton.

Usage: ski.py FILE.ski [FILE...]  -> prints a summary.
"""
import struct
import sys

MAGIC = b"MOXBIKSA"
HEADER_END = 0x6C
VERTEX_SIZE = 48
TANGENT_SIZE = 16


class SkiError(ValueError):
    pass


def _reader(data):
    pos = [0]

    def u32():
        if pos[0] + 4 > len(data):
            raise SkiError("truncated file at 0x%x" % pos[0])
        v = struct.unpack_from("<I", data, pos[0])[0]
        pos[0] += 4
        return v

    def name(encoding):
        n = u32()
        if n > 1024 or pos[0] + n > len(data):
            raise SkiError("bad string length %d at 0x%x" % (n, pos[0]))
        raw = data[pos[0]:pos[0] + n]
        pos[0] += n
        return raw.decode(encoding, "replace").rstrip("\0")

    def take(n):
        if pos[0] + n > len(data):
            raise SkiError("truncated block at 0x%x" % pos[0])
        chunk = data[pos[0]:pos[0] + n]
        pos[0] += n
        return chunk

    return pos, u32, name, take


def parse_ski(path, with_geometry=True):
    """Return a dict with bones, textures, materials and meshes.

    Each mesh is a dict: name, material, texture (index), texture_name,
    positions (list of (x, y, z)), normals, uvs, weights, bones (per vertex
    4 indices), indices (flat list of vertex indices, 3 per triangle).
    """
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != MAGIC:
        raise SkiError("not a MOXBIKSA file: %s" % path)
    version = struct.unpack_from("<I", data, 8)[0]
    nmesh, _, _, _, ntex, nmat, nbones = struct.unpack_from("<7I", data, 0x0C)
    pos, u32, name, take = _reader(data)
    pos[0] = HEADER_END

    bones = [name("ascii") for _ in range(nbones)]
    textures = [name("gbk") for _ in range(ntex)]
    materials = []
    for _ in range(nmat):
        tag = take(10)
        if tag != b"MATERIAL: ":
            raise SkiError("material tag missing at 0x%x" % (pos[0] - 10))
        blob = take(70)
        floats = struct.unpack_from("<17f", blob, 0)
        materials.append({
            "diffuse": floats[0:4],
            "ambient": floats[4:8],
            "specular": floats[8:12],
            "emissive": floats[12:16],
            "power": floats[16],
        })

    meshes = []
    for _ in range(nmesh):
        mname = name("gbk")
        tex_idx = u32()
        mat_idx = u32()
        vcount = u32()
        icount = u32()
        if vcount > 2_000_000 or icount > 6_000_000:
            raise SkiError("implausible counts in mesh %r" % mname)
        vblob = take(vcount * VERTEX_SIZE)
        iblob = take(icount * 2)
        take(vcount * TANGENT_SIZE)
        mesh = {
            "name": mname,
            "material": mat_idx,
            "texture": tex_idx,
            "texture_name": textures[tex_idx] if tex_idx < ntex else "",
            "vertex_count": vcount,
            "index_count": icount,
        }
        if with_geometry:
            positions, normals, uvs, weights, vbones = [], [], [], [], []
            for i in range(vcount):
                (x, y, z, w0, w1, w2, b0, b1, b2, b3,
                 nx, ny, nz, u, v) = struct.unpack_from("<6f4B5f", vblob, i * VERTEX_SIZE)
                positions.append((x, y, z))
                weights.append((w0, w1, w2, 1.0 - w0 - w1 - w2))
                vbones.append((b0, b1, b2, b3))
                normals.append((nx, ny, nz))
                uvs.append((u, v))
            mesh.update({
                "positions": positions,
                "normals": normals,
                "uvs": uvs,
                "weights": weights,
                "bones": vbones,
                "indices": list(struct.unpack_from("<%dH" % icount, iblob, 0)),
            })
        meshes.append(mesh)

    return {
        "path": path,
        "version": version,
        "bones": bones,
        "textures": textures,
        "materials": materials,
        "meshes": meshes,
        "trailing_bytes": len(data) - pos[0],
    }


def bounds(model):
    """Axis-aligned bounding box of all meshes: ((minx, miny, minz), (max...))."""
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for m in model["meshes"]:
        for p in m["positions"]:
            for k in range(3):
                lo[k] = min(lo[k], p[k])
                hi[k] = max(hi[k], p[k])
    return tuple(lo), tuple(hi)


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    for path in argv:
        try:
            model = parse_ski(path)
        except SkiError as exc:
            print("%s: ERROR %s" % (path, exc))
            continue
        lo, hi = bounds(model)
        print("%s: v%d, %d bones, %d textures, %d materials, %d meshes, %d trailing bytes"
              % (path, model["version"], len(model["bones"]), len(model["textures"]),
                 len(model["materials"]), len(model["meshes"]), model["trailing_bytes"]))
        print("  bbox min %s max %s" % (tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi)))
        for m in model["meshes"]:
            print("  mesh %-30s tex=%s  %d verts %d tris"
                  % (m["name"], m["texture_name"], m["vertex_count"], m["index_count"] // 3))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
