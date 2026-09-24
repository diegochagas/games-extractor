"""Turn decoded tiles/maps/palettes into indexed PNGs."""
import numpy as np
from PIL import Image

from .codecs import tiles_2bpp, tiles_4bpp

FLIP_H, FLIP_V = 0x4000, 0x8000


def decode_tiles(data, bpp):
    return tiles_2bpp(data) if bpp == 2 else tiles_4bpp(data)


def mono_palette(shades=(0, 2, 4, 7)):
    """WonderSwan mono shades: 0 = lightest, 7 = darkest."""
    return [[(255 - s * 36,) * 3 for s in shades]]


def gray_palette(bpp):
    n = 1 << bpp
    return [[(255 - i * 255 // (n - 1),) * 3 for i in range(n)]]


def _image(idx, pals, colors_per_pal):
    flat = []
    for p in pals:
        p = list(p)[:colors_per_pal] + [(255, 0, 255)] * (colors_per_pal - len(p))
        for c in p:
            flat.extend(c)
    im = Image.fromarray(idx.astype(np.uint8), "P")
    im.putpalette(flat + [0] * (768 - len(flat)))
    return im


def _tile(tiles, cell):
    t = tiles[(cell & 0x1FF) % len(tiles)]
    if cell & FLIP_H:
        t = t[:, ::-1]
    if cell & FLIP_V:
        t = t[::-1, :]
    return t


def render_map(tiles, bpp, w, h, cells, pals):
    cpp = 1 << bpp
    idx = np.zeros((h * 8, w * 8), np.uint8)
    for i, cell in enumerate(cells):
        if cell is None:
            continue
        y, x = divmod(i, w)
        pal = (cell >> 9 & 15) % len(pals)
        idx[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = _tile(tiles, cell) + pal * cpp
    return _image(idx, pals, cpp)


def render_sheet(tiles, bpp, pals, cols=16):
    n = len(tiles)
    rows = (n + cols - 1) // cols
    idx = np.zeros((rows * 8, cols * 8), np.uint8)
    for i in range(n):
        y, x = divmod(i, cols)
        idx[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = tiles[i]
    return _image(idx, pals[:1], 1 << bpp)


def render_sprite(tiles, bpp, pieces, pals):
    """pieces: (tile word, y, x) with signed pixel offsets."""
    if not pieces:
        return None
    x0 = min(p[2] for p in pieces)
    y0 = min(p[1] for p in pieces)
    w = max(p[2] for p in pieces) - x0 + 8
    h = max(p[1] for p in pieces) - y0 + 8
    idx = np.zeros((h, w), np.uint8)
    for cell, y, x in reversed(pieces):
        t = _tile(tiles, cell)
        dst = idx[y - y0:y - y0 + 8, x - x0:x - x0 + 8]
        dst[t > 0] = t[t > 0]
    return _image(idx, pals[:1], 1 << bpp)


def glyph_sheet(glyphs, cols, scale=3):
    """Labelled contact sheet for fonts (labels are the byte codes)."""
    from PIL import ImageDraw
    gh, gw = glyphs[0].shape
    cw, ch = gw * scale + 6, gh * scale + 13
    rows = (len(glyphs) + cols - 1) // cols
    im = Image.new("L", (cols * cw, rows * ch), 200)
    dr = ImageDraw.Draw(im)
    for i, g in enumerate(glyphs):
        gi = Image.fromarray((255 - g * 85).astype(np.uint8)).resize((gw * scale, gh * scale), Image.NEAREST)
        x, y = i % cols * cw, i // cols * ch
        im.paste(gi, (x + 3, y + 11))
        dr.text((x + 3, y), "%02X" % i, fill=0)
    return im
