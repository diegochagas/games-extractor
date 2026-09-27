#!/usr/bin/env python3
"""FNT glyph caches of Saint Seiya Omega Ultimate Cosmo (`common/globalobject.pac/FONT.FNT`).

The game does not draw text with the console's fonts: it carries the glyphs of the characters its
own text uses. File: `u32 count`, 12 zero bytes, `count` entries of 64 bytes sorted by character
code, then pages of 128 x 128 pixels, 4 bits each (low nibble first), 64 cells of 16 x 16 per page;
glyph `i` sits in page `i // 64`, cell `i % 64`, drawn from the top left corner of its cell.
Entry: `u16 code, u8 page, u8 cell`, then the fields of a sceFont glyph description:
bitmap width, height, left, top (rows above the baseline), and in 26.6 fixed point width, height,
bearing x, bearing y, vertical bearing x, y, ascender, advance, vertical advance, 2 unused.

usage: fnt.py show FONT.FNT OUT.png        every page side by side
       fnt.py list FONT.FNT                the characters of the font
"""
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PAGE, CELL, PER_PAGE = 128, 16, 64


def read(data):
    count = struct.unpack_from('<I', data, 0)[0]
    base = 16 + count * 64
    glyphs = []
    for i in range(count):
        e = struct.unpack_from('<HBB15i', data, 16 + i * 64)
        code, page, cell, w, h, left, top = e[:7]
        raw = np.frombuffer(data, dtype=np.uint8, count=PAGE * PAGE // 2, offset=base + page * PAGE * PAGE // 2)
        pix = np.stack([raw & 15, raw >> 4], axis=1).reshape(PAGE, PAGE)
        y, x = (cell // 8) * CELL, (cell % 8) * CELL
        glyphs.append({'code': code, 'w': w, 'h': h, 'left': left, 'top': top, 'metrics': list(e[7:]),
                       'bitmap': pix[y:y + CELL, x:x + CELL].copy()})
    return glyphs


def build(glyphs):
    glyphs = sorted(glyphs, key=lambda g: g['code'])
    codes = [g['code'] for g in glyphs]
    if len(set(codes)) != len(codes):
        raise ValueError('a character appears twice in the font')
    pages = (len(glyphs) + PER_PAGE - 1) // PER_PAGE
    pix = np.zeros((pages, PAGE, PAGE), dtype=np.uint8)
    head = bytearray(struct.pack('<I', len(glyphs)) + bytes(12))
    for i, g in enumerate(glyphs):
        page, cell = divmod(i, PER_PAGE)
        bm = np.zeros((CELL, CELL), dtype=np.uint8)
        src = np.asarray(g['bitmap'], dtype=np.uint8)[:CELL, :CELL]
        bm[:src.shape[0], :src.shape[1]] = src
        y, x = (cell // 8) * CELL, (cell % 8) * CELL
        pix[page, y:y + CELL, x:x + CELL] = bm
        head += struct.pack('<HBB15i', g['code'], page, cell, g['w'], g['h'], g['left'], g['top'], *g['metrics'])
    flat = pix.reshape(-1, 2)
    return bytes(head) + ((flat[:, 0] & 15) | (flat[:, 1] << 4)).astype(np.uint8).tobytes()


def render(font_path, size, chars, weight=1.0, advance_extra=0.0):
    """Glyphs of `chars` drawn with a TrueType font, `size` pixels high (4-bit coverage)."""
    font = ImageFont.truetype(font_path, size)
    ascent, _descent = font.getmetrics()
    out = []
    for ch in chars:
        adv = font.getlength(ch) + advance_extra
        box = font.getbbox(ch)
        w, h = (box[2] - box[0], box[3] - box[1]) if box else (0, 0)
        if w <= 0 or h <= 0 or not ch.strip():
            bitmap, w, h, left, top = np.zeros((CELL, CELL), dtype=np.uint8), 0, 0, 0, 0
        else:
            if w > CELL or h > CELL:
                raise ValueError('%r is %dx%d at size %d: it does not fit a cell' % (ch, w, h, size))
            im = Image.new('L', (CELL, CELL), 0)
            ImageDraw.Draw(im).text((-box[0], -box[1]), ch, font=font, fill=255)
            a = np.asarray(im, dtype=np.float64) / 255.0
            bitmap = np.clip(np.round(np.clip(a * weight, 0, 1) * 15), 0, 15).astype(np.uint8)
            left, top = box[0], ascent - box[1]
        out.append({'code': ord(ch), 'w': w, 'h': h, 'left': left, 'top': top, 'bitmap': bitmap,
                    'metrics': [w * 64, h * 64, left * 64, top * 64, 0, 0, top * 64, int(round(adv * 64)), 0, 0, 0]})
    return out


def advance(glyph):
    return glyph['metrics'][7] / 64.0


def sheet(glyphs):
    pages = (len(glyphs) + PER_PAGE - 1) // PER_PAGE
    im = Image.new('L', (PAGE * min(pages, 8), PAGE * ((pages + 7) // 8)), 0)
    for i, g in enumerate(glyphs):
        page, cell = divmod(i, PER_PAGE)
        x = (page % 8) * PAGE + (cell % 8) * CELL
        y = (page // 8) * PAGE + (cell // 8) * CELL
        im.paste(Image.fromarray((np.asarray(g['bitmap'], dtype=np.uint8) * 17)), (x, y))
    return im


def main(argv):
    if len(argv) == 4 and argv[1] == 'show':
        sheet(read(Path(argv[2]).read_bytes())).save(argv[3])
        return 0
    if len(argv) == 3 and argv[1] == 'list':
        g = read(Path(argv[2]).read_bytes())
        print(len(g), 'glyphs')
        print(''.join(chr(x['code']) for x in g))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
