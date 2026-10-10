#!/usr/bin/env python3
"""Sony TIM2 pictures (`TIM2`; the game also writes `TIM3`, same layout) -> PNG.

File header: magic, u8 version, u8 alignment, u16 pictures, 8 reserved. Picture header (48 bytes):
u32 total size, u32 CLUT size, u32 image size, u16 header size, u16 CLUT colours, u8 format,
u8 mipmaps, u8 CLUT type, u8 image type, u16 width, u16 height, GS registers. Image types: 1 =
16-bit A1B5G5R5, 2 = 24-bit RGB, 3 = 32-bit RGBA, 4 = 4-bit indexed, 5 = 8-bit indexed. CLUT types:
1 = 16-bit, 2 = 24-bit, 3 = 32-bit; without bit 0x80 (CSM1) a 256-colour CLUT is stored in blocks
of 32 with the two middle groups of 8 swapped. Alpha 0x80 is opaque on the PS2 (scaled x2 here).

usage: tim2.py convert SRC_DIR OUT_DIR     every TIM2/TIM3 (also inside FJF containers and CMPS
                                            files) under SRC_DIR -> OUT_DIR/<same path>[_N].png
       tim2.py png FILE OUT.png [--picture N]
"""
import os
import struct
import sys

from PIL import Image

import fjf

MAGICS = (b'TIM2', b'TIM3')


def is_tim2(data):
    return data[:4] in MAGICS


def a8(a):
    return min(255, a * 2)


def clut_colours(raw, clut_type, count):
    fmt = clut_type & 0x3F
    colours = []
    if fmt == 1:
        for i in range(count):
            v = struct.unpack_from('<H', raw, i * 2)[0]
            colours.append(((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31, 255 if v & 0x8000 else 0))
    elif fmt == 2:
        for i in range(count):
            r, g, b = raw[i * 3:i * 3 + 3]
            colours.append((r, g, b, 255))
    else:
        for i in range(count):
            r, g, b, a = raw[i * 4:i * 4 + 4]
            colours.append((r, g, b, a8(a)))
    if not clut_type & 0x80 and count == 256:        # CSM1: swap the middle 8-colour groups of each 32
        fixed = []
        for b in range(0, 256, 32):
            blk = colours[b:b + 32]
            fixed += blk[0:8] + blk[16:24] + blk[8:16] + blk[24:32]
        colours = fixed
    return colours


def pictures(data):
    """Every picture of a TIM2 file as a PIL image."""
    version, align, count = struct.unpack_from('<BBH', data, 4)
    pos = 16 if align == 0 else 128
    out = []
    for _ in range(count):
        (total, clut_size, image_size, header_size, clut_colours_n, _fmt, _mips, clut_type,
         image_type, width, height) = struct.unpack_from('<IIIHHBBBBHH', data, pos)
        image = data[pos + header_size:pos + header_size + image_size]
        clut = data[pos + header_size + image_size:pos + header_size + image_size + clut_size]
        if image_type == 3:
            im = Image.frombytes('RGBA', (width, height), image[:width * height * 4])
            im.putdata([(r, g, b, a8(a)) for r, g, b, a in im.getdata()])
        elif image_type == 2:
            im = Image.frombytes('RGB', (width, height), image[:width * height * 3]).convert('RGBA')
        elif image_type == 1:
            px = []
            for i in range(width * height):
                v = struct.unpack_from('<H', image, i * 2)[0]
                px.append(((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31, 255 if v & 0x8000 else 0))
            im = Image.new('RGBA', (width, height))
            im.putdata(px)
        elif image_type in (4, 5):
            colours = clut_colours(clut, clut_type, clut_colours_n or (16 if image_type == 4 else 256))
            if image_type == 4:
                idx = []
                for b in image[:(width * height + 1) // 2]:
                    idx.append(b & 15)
                    idx.append(b >> 4)
                idx = idx[:width * height]
            else:
                idx = image[:width * height]
            im = Image.new('RGBA', (width, height))
            im.putdata([colours[i] if i < len(colours) else (0, 0, 0, 0) for i in idx])
        else:
            raise ValueError('image type %d' % image_type)
        out.append(im)
        pos += total if total else header_size + image_size + clut_size
        if align == 1:
            pos = (pos + 127) & ~127
    return out


def convert_file(data, dest_stem):
    """Pictures of `data` (TIM2, or a container holding some) -> dest_stem[_N].png; returns count."""
    data = fjf.unwrap(data)
    n = 0
    if is_tim2(data):
        pics = pictures(data)
        for i, im in enumerate(pics):
            path = dest_stem + ('' if len(pics) == 1 else '_%d' % i) + '.png'
            os.makedirs(os.path.dirname(path), exist_ok=True)
            im.save(path)
            n += 1
    elif fjf.is_fjf(data):
        _flags, ents = fjf.entries(data)
        for i, (eid, off, size) in enumerate(ents):
            n += convert_file(data[off:off + size], os.path.join(dest_stem, '%02d_%d' % (i, eid)))
    return n


def main(argv):
    if len(argv) >= 4 and argv[1] == 'convert':
        src, out = argv[2], argv[3]
        n, bad = 0, []
        for root, _dirs, files in os.walk(src):
            for name in sorted(files):
                path = os.path.join(root, name)
                with open(path, 'rb') as f:
                    data = f.read()
                rel = os.path.relpath(path, src)
                try:
                    n += convert_file(data, os.path.join(out, os.path.splitext(rel)[0] if is_tim2(fjf.unwrap(data[:64]) if not fjf.is_fjf(data) else data) else rel))
                except Exception as e:  # noqa: BLE001
                    bad.append('%s: %s' % (rel, e))
        print('%d pictures -> %s' % (n, out))
        for b in bad:
            print('!! ' + b)
        return 0
    if len(argv) >= 4 and argv[1] == 'png':
        with open(argv[2], 'rb') as f:
            data = fjf.unwrap(f.read())
        pics = pictures(data)
        which = int(argv[argv.index('--picture') + 1]) if '--picture' in argv else 0
        pics[which].save(argv[3])
        print('%d picture(s), wrote %s' % (len(pics), argv[3]))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
