"""Tiny files in every format the ps2 tools read, built in memory (no game data)."""
import struct

from PIL import Image


def afs(files):
    """CRI AFS with a name table. files = [(name, bytes)]."""
    count = len(files)
    header = 8 + 8 * count + 8
    offset = (header + 2047) & ~2047
    entries, blobs = [], []
    for name, data in files:
        entries.append((offset, len(data)))
        blobs.append((offset, data))
        offset = (offset + len(data) + 2047) & ~2047
    names_off = offset
    names = b''.join(name.encode('latin-1').ljust(32, b'\0') + struct.pack('<6HI', 2005, 3, 2, 0, 0, 0, len(data))
                     for name, data in files)
    out = bytearray(names_off + len(names))
    out[:4] = b'AFS\0'
    struct.pack_into('<I', out, 4, count)
    for i, (off, size) in enumerate(entries):
        struct.pack_into('<II', out, 8 + 8 * i, off, size)
    struct.pack_into('<II', out, 8 + 8 * count, names_off, len(names))
    for off, data in blobs:
        out[off:off + len(data)] = data
    out[names_off:] = names
    return bytes(out)


def fjf(entries, flags=0x4000, with_end=True):
    """FJF container. entries = [(id, bytes)]."""
    count = len(entries)
    pos = 8 + 4 * (count + (1 if with_end else 0)) + 2 * count
    start = (pos + 15) & ~15
    offsets, data, off = [], b'', start
    for _eid, blob in entries:
        offsets.append(off)
        padded = blob + b'\0' * ((-len(blob)) % 16)
        data += padded
        off += len(padded)
    head = b'FJF\0' + struct.pack('<HH', count, flags) + struct.pack('<%dI' % count, *offsets)
    if with_end:
        head += struct.pack('<I', off)
    head += struct.pack('<%dH' % count, *[e[0] for e in entries])
    return head.ljust(start, b'\0') + data


def tim2(image, magic=b'TIM2', indexed=True):
    """A TIM2 file of a PIL RGBA image: 8-bit indexed with a 32-bit CSM1 CLUT, or 32-bit RGBA."""
    w, h = image.size
    if indexed:
        pal = image.convert('RGBA').getcolors(256)
        colours = [c for _n, c in pal]
        while len(colours) < 256:
            colours.append((0, 0, 0, 0))
        index = {c: i for i, c in enumerate(colours)}
        pixels = bytes(index[p] for p in image.getdata())
        swizzled = []
        for b in range(0, 256, 32):
            blk = colours[b:b + 32]
            swizzled += blk[0:8] + blk[16:24] + blk[8:16] + blk[24:32]
        clut = b''.join(struct.pack("4B", r, g, b, (a + 1) // 2) for r, g, b, a in swizzled)
        img_type, clut_type, clut_colours = 5, 3, 256
    else:
        pixels = b''.join(struct.pack("4B", r, g, b, (a + 1) // 2) for r, g, b, a in image.getdata())
        clut, img_type, clut_type, clut_colours = b'', 3, 0, 0
    pic = struct.pack('<IIIHHBBBBHH', 48 + len(pixels) + len(clut), len(clut), len(pixels), 48, clut_colours, 0, 1,
                      clut_type, img_type, w, h) + b'\0' * 24
    return magic + struct.pack('<BBH', 4, 0, 1) + b'\0' * 8 + pic + pixels + clut


def sample_image():
    im = Image.new('RGBA', (8, 4))
    px = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 128), (0, 0, 0, 0)]
    im.putdata([px[(x + y) % 4] for y in range(4) for x in range(8)])
    return im


def msg_block(strings):
    """A text block: u16 count, u16 offsets, UTF-16LE strings (0x0000 = line break, 0x00FF = end)."""
    count = len(strings)
    body, offsets = b'', []
    pos = 2 + 2 * count
    for s in strings:
        offsets.append((pos + len(body)) // 2)
        body += s.replace('\n', '\0').encode('utf-16le') + b'\xff\x00'
    return struct.pack('<H', count) + struct.pack('<%dH' % count, *offsets) + body


def msg_file(languages):
    """FJF text table: one block per language, ids 0.."""
    return fjf([(i, msg_block(strings)) for i, strings in enumerate(languages)])


def script(commands):
    """SC cutscene script. commands = [(id, layer, [values])]; ints, floats and strings."""
    out = b'SC\x01\x00\x01\x00'
    for cid, layer, values in commands:
        out += b'\xe1' + struct.pack('>HH', cid, layer)
        for v in values:
            if isinstance(v, str):
                out += b'\xc3' + v.encode('latin-1') + b'\0'
            elif isinstance(v, float):
                out += b'\xc2' + struct.pack('>ii', int(round(v * 1000)), 1000)
            else:
                out += b'\xc1' + struct.pack('>i', v)
        out += b'\xef'
    return out + b'\xff'


def gmi(bone_local=True):
    """A GMI model: two bones (root, child moved +1 on x) and one part with one quad (two triangles)."""
    def bone(name, parent, tx):
        m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, tx, 0, 0, 1]
        return struct.pack('<16f', *m) + struct.pack('<hHH', parent, 0x88, 0x88) + name.encode().ljust(34, b'\0') + b'\xdd' * 8
    bones = bone('root', -1, 0) + bone('child', 0, 1.0)
    # four vertices: strip restart pair (w=0) then two kicks (w=1)
    quad = [(0, 0, 0, 0.0), (0, 1, 0, 0.0), (1, 0, 0, 1.0), (1, 1, 0, 1.0)]
    pos = b''.join(struct.pack('<4f', *v) for v in quad)
    nrm = b''.join(struct.pack('<4h', 0, 0, 4096, 4096) for _ in quad)
    uv = b''.join(struct.pack('<2f', v[0], v[1]) for v in quad)
    skin = b''.join(bytes([1, 255, 0xDD, 0xDD]) for _ in quad)            # every vertex on palette slot 1 = child
    boff = 32
    poff = boff + len(bones)
    opos = poff + 48
    onrm = opos + len(pos)
    ouv = onrm + len(nrm)
    oskin = ouv + len(uv)
    part = struct.pack('<HHIIIIIIII', 2, 4, 2 << 16, 0, opos, onrm, 0, ouv, oskin, 0) + bytes([0, 1] + [0xFF] * 10)
    body = bones + part + pos + nrm + uv + skin
    head = b'\x19\x03\x04 ' + struct.pack('<IIIHHIIHH', 32 + len(body), 16, 0, 2, 1, boff, poff, 3, 2)
    return head + body


def sebank(samples):
    """An SE bank: FJF with a `seds` chunk and a `swdm` chunk. samples = [(name, pitch, adpcm bytes)]."""
    recs, data, off = b'', b'', 0
    for name, pitch, adpcm in samples:
        recs += struct.pack('<IIHH', off, 0x10, 0x0F7F, pitch) + b'\0' * 4 + name.encode('shift_jis').ljust(16, b'\0')
        data += adpcm
        off += len(adpcm)
    data_off = 0x60 + len(recs)
    swdm = b'swdm' + b'\0' * 60 + struct.pack('<IIII', 0x8000, 0x40, len(data), data_off) + b'\0' * 16 + recs + data
    return fjf([(0, b'seds' + b'\0' * 28), (0, swdm)], flags=0xC000)
