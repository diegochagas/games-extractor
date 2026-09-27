"""Tiny synthetic files in the formats of psp/ (no game data is ever committed)."""
import struct


def utf_table(name, columns, rows):
    """@UTF table. columns: [(name, type)], types 4 = u32, 6 = u64, 0xA = string; per-row storage."""
    strings = bytearray(b'<NULL>\0')
    offsets = {}

    def s(text):
        if text not in offsets:
            offsets[text] = len(strings)
            strings.extend(text.encode() + b'\0')
        return offsets[text]

    name_off = s(name)
    schema = b''.join(struct.pack('>BI', 0x50 | t, s(n)) for n, t in columns)
    body = bytearray()
    for row in rows:
        for (n, t), v in zip(columns, row):
            body += {4: lambda x: struct.pack('>I', x), 6: lambda x: struct.pack('>Q', x),
                     0xA: lambda x: struct.pack('>I', s(x))}[t](v)
    rows_off = 24 + len(schema)
    str_off = rows_off + len(body)
    data_off = str_off + len(strings)
    head = struct.pack('>IIIIHHI', rows_off, str_off, data_off, name_off, len(columns),
                       len(body) // max(1, len(rows)), len(rows))
    payload = head + schema + bytes(body) + bytes(strings)
    return b'@UTF' + struct.pack('>I', len(payload)) + payload


def crilayla(data, reference=None):
    """CRILAYLA stream of `data` (at least 0x100 bytes): literals only, or with one
    back-reference (distance, length) = `reference` placed at the end of the file."""
    assert len(data) >= 0x100
    prefix, body = data[:0x100], data[0x100:]
    bits = []

    def put(value, n):
        bits.extend((value >> (n - 1 - i)) & 1 for i in range(n))

    todo = list(body)
    if reference:
        dist, length = reference                # the last `length` bytes repeat what follows them
        for b in reversed(todo[-dist:] if False else []):
            pass
    pos = len(todo) - 1
    out_tail = []                               # bytes already written, from the end backwards
    while pos >= 0:
        if reference and len(out_tail) >= reference[0] and pos + 1 >= reference[1] \
                and all(todo[pos - i] == out_tail[-reference[0] + i] if False else
                        todo[pos - i] == todo[pos - i + reference[0]] for i in range(reference[1])) \
                and reference[0] >= 3:
            put(1, 1)
            put(reference[0] - 3, 13)
            length = reference[1] - 3
            for n in (2, 3, 5, 8):
                top = (1 << n) - 1
                if length >= top:
                    put(top, n)
                    length -= top
                else:
                    put(length, n)
                    length = None
                    break
            assert length is None, 'reference too long for this helper'
            for i in range(reference[1]):
                out_tail.append(todo[pos - i])
            pos -= reference[1]
            reference = None
            continue
        put(0, 1)
        put(todo[pos], 8)
        out_tail.append(todo[pos])
        pos -= 1
    while len(bits) % 8:
        bits.append(0)
    stream = bytes(int(''.join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8))[::-1]
    return b'CRILAYLA' + struct.pack('<II', len(body), len(stream)) + stream + prefix


def cpk(files, compress=()):
    """CPK archive with a TOC. files: {name: bytes}; names in `compress` are stored as CRILAYLA."""
    toc_off, content_off = 0x800, 0x1000
    blobs, rows, p = [], [], content_off
    for i, (name, data) in enumerate(files.items()):
        stored = crilayla(data) if name in compress else data
        d, f = name.rsplit('/', 1) if '/' in name else ('', name)
        rows.append((d, f, len(stored), len(data), p - toc_off, i))
        blobs.append((p, stored))
        p += (len(stored) + 0x7FF) // 0x800 * 0x800
    toc = utf_table('CpkTocInfo', [('DirName', 0xA), ('FileName', 0xA), ('FileSize', 4), ('ExtractSize', 4),
                                   ('FileOffset', 6), ('ID', 4)], rows)
    header = utf_table('CpkHeader', [('ContentOffset', 6), ('TocOffset', 6), ('TocSize', 6), ('Files', 4)],
                       [(content_off, toc_off, len(toc) + 16, len(files))])
    out = bytearray(p)
    out[0:16 + len(header)] = b'CPK ' + b'\xff\0\0\0' + struct.pack('<Q', len(header)) + header
    out[toc_off:toc_off + 16 + len(toc)] = b'TOC ' + b'\xff\0\0\0' + struct.pack('<Q', len(toc)) + toc
    for off, blob in blobs:
        out[off:off + len(blob)] = blob
    return bytes(out)


def pac(files, total_without_header=False):
    """PAC container. files: [(name, bytes)]"""
    table = 8 + 40 * len(files)
    body, entries, p = b'', b'', table
    for name, data in files:
        entries += name.encode().ljust(32, b'\0') + struct.pack('<II', p, len(data))
        body += data
        p += len(data)
    total = p - (8 if total_without_header else 0)
    return struct.pack('<HHI', len(files), 0x78, total) + entries + body


def gim_chunk(kind, data):
    return struct.pack('<HHIII', kind, 0, 16 + len(data), 16 + len(data), 16) + data


def gim_block(fmt, order, width, height, bpp, pixels, palign=16, halign=8):
    head = struct.pack('<HHHHHHHHHHHHIIIIHHHH', 0x30, 0, fmt, order, width, height, bpp, palign, halign, 2, 0, 0,
                       0x30, 0x40, 0x40 + len(pixels), 0, 1, 1, 3, 1)
    return head + struct.pack('<IIII', 0x40, 0, 0, 0) + pixels


def gim(image, palette=None):
    """GIM file from an image block and an optional palette block (made with gim_block)."""
    inner = gim_chunk(4, image) + (gim_chunk(5, palette) if palette else b'')
    picture = struct.pack('<HHIII', 3, 0, 16 + len(inner), 16, 16) + inner
    root = struct.pack('<HHIII', 2, 0, 16 + len(picture), 16, 16) + picture
    return b'MIG.00.1PSP\0\0\0\0\0' + root


def btx(rows):
    """BTX table. rows: [(id, text)]"""
    head = b'BTX ' + struct.pack('<III', 1, 16, 0) + struct.pack('<II', 1, len(rows))
    table_end = len(head) + 8 * len(rows)
    text, entries = b'', b''
    for i, (sid, s) in enumerate(rows):
        at = len(head) + 8 * i
        entries += struct.pack('<II', sid, table_end + len(text) - at)
        text += s.encode('utf-16-le') + b'\0\0'
    return head + entries + text


def command(kind, args):
    return struct.pack('<HHI', kind, 8, 8 + len(args)) + args


def chunk(kind, name, children=b'', args=b'', data=b''):
    label = name.encode() + b'\0'
    label += b'\0' * (-len(label) % 4)
    hs = 16 + len(label)
    d = hs + len(args)
    c = d + len(data)
    size = c + len(children)
    return struct.pack('<HHIII', kind, hs, size, c, d) + label + args + data + children


def gmo_triangle(skinned=True):
    """GMO with two bones, one part, one triangle (16-bit positions and uvs, 8-bit normals and
    weights), one material and texture, and a one-bone motion."""
    fmt = 0x1322 if skinned else 0x1122                # uv16, normal8, position16, (weight8), index16
    verts = b''
    for x, y, z, u, v in ((0, 0, 0, 0, 0), (32767, 0, 0, 32768, 0), (0, 32767, 0, 0, 32768)):
        if skinned:
            verts += struct.pack('<Bx', 128)
        verts += struct.pack('<HH', u, v) + struct.pack('<bbbx', 0, 0, 127) + struct.pack('<hhh', x, y, z)
    arrays = chunk(7, 'arrays-0', args=struct.pack('<IIII', fmt, 3, 1, 0), data=verts)
    mesh = chunk(6, 'mesh-0', command(0x8061, struct.pack('<I', 0x00082000)) +
                 (command(0x8062, struct.pack('<II', 1, 1)) if skinned else b'') +
                 command(0x8066, struct.pack('<IIII', 0x00071000, 3, 3, 1) + struct.pack('<HHHxx', 0, 1, 2)))
    part = chunk(5, 'part-0', mesh + arrays)
    ident = struct.pack('<16f', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)
    back = struct.pack('<16f', 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, -10, 0, 1)
    root = chunk(4, 'root', command(0x8048, struct.pack('<fff', 0, 0, 0)))
    child = chunk(4, 'child', command(0x8041, struct.pack('<I', 0x00041000)) +
                  command(0x8048, struct.pack('<fff', 0, 10, 0)))
    drawer = chunk(4, 'body', (command(0x8044, struct.pack('<III', 2, 0x00041000, 0x00041001)) +
                                command(0x8045, struct.pack('<I', 2) + ident + back) if skinned else b'') +
                   command(0x804E, struct.pack('<I', 0x00051000)))
    material = chunk(8, 'mat', chunk(9, 'layer-0', command(0x8091, struct.pack('<I', 0x000A2000))))
    pixels = bytes([255, 0, 0, 255] * 16 * 8)
    image = gim(gim_block(3, 0, 16, 8, 32, pixels, palign=1, halign=1))
    texture = chunk(10, 'tex', command(0x8012, b'D:/work/tex.tga\0') +
                    command(0x8013, struct.pack('<I', len(image)) + image + b'\0' * (-len(image) % 4)))
    import numpy as np
    keys = np.array([0, 0, 0, 0, 30, 0, 5, 0], dtype='<f2').tobytes()
    curve = chunk(12, 'fcurve-0', args=struct.pack('<IIII', 0x81, 3, 2, 0), data=keys)
    motion = chunk(11, 'Take 001', command(0x80B1, struct.pack('<ff', 0, 30)) + command(0x80B2, struct.pack('<f', 30)) +
                   command(0x80B3, struct.pack('<IIII', 0x00041001, 0x48, 0, 0x000C0000)) + curve)
    model = chunk(3, 'model-0', command(0x8015, struct.pack('<Iffffff', 0x180, 0, 0, 0, 100, 100, 100)) +
                  command(0x8015, struct.pack('<Iffff', 3, 0, 0, 1, 1)) + root + child + drawer + part +
                  material + texture + motion)
    return b'OMG.00.1PSP\0\0\0\0\0' + chunk(2, '', model)
