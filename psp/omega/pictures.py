#!/usr/bin/env python3
"""Pictures of Saint Seiya Omega Ultimate Cosmo that are nothing but words (speaker names, menu
entries, screen titles), written again in Portuguese.

Only text is drawn: each picture keeps its size and pixel format, and the new words take the
colours of the old ones (the fill from top to bottom, the dark edge and the soft shadow are
measured on the original picture). Pictures that mix artwork and words are left as they are.

usage: pictures.py preview DUMP_DIR OUT.png      the old and the new pictures side by side
`build(dump, font)` returns {path inside the archives: GIM bytes} for patch.py.
"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gim  # noqa: E402
from omega import names  # noqa: E402

SANS = '/usr/share/fonts/truetype/ubuntu/Ubuntu[wdth,wght].ttf'
SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf'
SCALE = 4                                         # drawn larger, then reduced

TRITON = '(Escama de Triton)'
PEOPLE = {c[0]: c[2] for c in names.CHARACTERS}
PEOPLE.update({'ate': 'Atena', 'sao': 'Saori', 'man': 'Homem', 'question': '???', 'random': '???',
               'lock': '???', 'r': '???', '019': 'Indefinido', 'syu': 'Shun'})

# file name (without extension) -> the words of each row of text, from the top
LABELS = {
    'MAIN_LIST_00': 'Modo História', 'MAIN_LIST_01': 'Modo Arcade', 'MAIN_LIST_02': 'Modo VS',
    'MAIN_LIST_03': 'Modo Treino', 'MAIN_LIST_04': 'Modo Galeria', 'MAIN_LIST_05': 'Configurações',
    'MAIN_LIST_06': 'Instalar dados', 'MAIN_LIST_07': 'Contra a CPU', 'MAIN_LIST_08': 'Em rede',
    'MAIN_LIST_09': 'Treino', 'MAIN_LIST_10': 'Tutorial', 'MAIN_LIST_11': 'Personagens',
    'MAIN_LIST_12': 'Ilustrações', 'MAIN_LIST_13': 'Filmes', 'MAIN_LIST_14': 'Replays',
    'MAIN_LIST_15': 'Meus dados',
    'MAIN_TITLE': 'Menu principal', 'TRAINING_TITLE': 'Modo Treino', 'VS_TITLE': 'Modo VS',
    'DIC_TITLE': 'Modo Galeria', 'STORY_TITLE': 'Escolha a história', 'ARCADE_TITLE': 'Arcade',
    'CPU_TITLE': 'Contra a CPU', 'NETWORK_TITLE': 'Em rede', 'CONF_TITLE': 'Configurações',
    'INSTALL_TITLE': 'Instalar dados', 'NW_TITLE': 'Sala de rede', 'MYDATA_TITLE': 'Meus dados',
    'DIC_CHARA_TITLE': 'Personagens', 'MOVIE_TITLE': 'Filmes', 'STILL_TITLE': 'Ilustrações',
    'DIC_SKILLLIST': 'Lista de golpes',
    'SELECT_SET00': 'Nível da CPU', 'SELECT_SET01': 'Tempo', 'SELECT_SET02': 'Rounds',
    'NW_LIST_00': 'Sala Pégaso', 'NW_LIST_01': 'Sala Águia', 'NW_LIST_02': 'Sala Leão Menor',
    'NW_LIST_03': 'Sala Dragão', 'NW_LIST_04': 'Sala Lobo', 'NW_LIST_05': 'Sala Órion',
    'MAP_STAGE_02': ['Praça do porto', 'Mansão de Julian', 'Beira-mar', 'Campina do sul', 'Campina do norte',
                     'Floresta silenciosa', 'Ruínas da arena', 'Caverna antiga', 'Templo de Poseidon',
                     'Templo subterrâneo'],
    'MENU_NAME_STORY': ' ',                      # the suffix of "story of ...": left out
}
# pictures that get another size (the words would not be readable in the old one)
SIZES = {'ADV_NAME_': (64, 16)}
for _code, _name in PEOPLE.items():
    up = _code.upper()
    two = [_name, TRITON] if _code.endswith('v2') else _name
    LABELS.setdefault('ADV_NAME_' + up, _name)
    LABELS.setdefault('BATTLE_NAME_' + up, _name + ' (Triton)' if _code.endswith('v2') else _name)
    for suffix in ('', '_00', '_01'):
        LABELS.setdefault('MENU_NAME_%s%s' % (up, suffix), two)
# strips of button hints: what follows each button, from left to right. Only the strips whose
# result was checked by eye are listed; the others keep the original picture. 'i' is a drawing of the
# original strip that is kept (a button); a text stands for the words that followed it; a pair
# (text, n) says that the old words were n separate groups of pixels.
MOVE, OK, BACK = 'Mover', 'OK', 'Voltar'
STRIPS = {
    'MENU_GUIDE_00': ['i', MOVE, 'i', OK, 'i', BACK], 'MENU_GUIDE_01': ['i', MOVE, 'i', OK, 'i', BACK],
    'SELECT_GUIDE_01': ['i', MOVE, 'i', OK, 'i', BACK], 'SELECT_GUIDE_03': ['i', MOVE, 'i', OK, 'i', BACK],
    'SELECT_GUIDE_00': ['i', MOVE, 'i', OK, 'i', BACK, 'i', 'i', 'Handicap'],
    'profiledata.pac/DIC_GUIDE_05': ['i', MOVE, 'i', OK, 'i', BACK],
    'DIC_GUIDE_06': ['i', BACK],
    'ADV_GUIDE_00': ['i', 'Anterior'],
    'ADV_GUIDE_03': ['i', 'Próxima'], 'ADV_GUIDE_04': ['i', 'Ouvir'],
    'RST_GUIDE': ['i', ('Avançar', 2)],
}
SERIF_NAMES = ('ADV_NAME_', 'MENU_NAME_', 'BATTLE_NAME_')
# pictures with the same words twice, one state of the button above the other
STACKED = ('MAIN_LIST_', 'NW_LIST_')


def bands(alpha, gap=2, floor=24):
    """Rows of text of a picture: [(x0, y0, x1, y1)] of the groups of lines that hold pixels."""
    rows = np.where((alpha > floor).any(axis=1))[0]
    out, start, last = [], None, None
    for y in rows:
        if start is None:
            start = last = y
        elif y - last > gap:
            out.append((start, last))
            start = last = y
        else:
            last = y
    if start is not None:
        out.append((start, last))
    boxes = []
    for y0, y1 in out:
        cols = np.where((alpha[y0:y1 + 1] > floor).any(axis=0))[0]
        if y1 - y0 >= 3 and len(cols):
            boxes.append((int(cols[0]), int(y0), int(cols[-1]) + 1, int(y1) + 1))
    return boxes


def style_of(rgba, box):
    """Fill colour of every line of the band, the dark edge and the shadow of the old words."""
    x0, y0, x1, y1 = box
    part = rgba[y0:y1, x0:x1].astype(np.float64)
    lum = part[:, :, :3] @ np.array([0.299, 0.587, 0.114])
    a = part[:, :, 3]
    solid = a >= 200
    fill = []
    for y in range(part.shape[0]):
        m = solid[y]
        if m.sum() >= 2:
            cut = np.percentile(lum[y][m], 60)
            fill.append(part[y][m & (lum[y] >= cut)][:, :3].mean(axis=0))
        else:
            fill.append(None)
    known = [i for i, c in enumerate(fill) if c is not None]
    if not known:
        fill = [np.array([255.0, 255.0, 255.0])] * len(fill)
    else:
        for i in range(len(fill)):
            if fill[i] is None:
                fill[i] = fill[min(known, key=lambda k: abs(k - i))]
    mid = a >= 128
    edge = None
    if mid.sum() > 8:
        cut = np.percentile(lum[mid], 20)
        dark = part[mid & (lum <= cut)][:, :3].mean(axis=0)
        bright = np.mean(fill, axis=0)
        if np.abs(bright - dark).sum() > 120:
            edge = dark
    soft = (a > 16) & (a < 128)
    shadow = part[soft][:, :3].mean(axis=0) if soft.sum() > 8 else None
    shadow_alpha = float(a[soft].mean()) if soft.sum() > 8 else 0.0
    return {'fill': np.array(fill), 'edge': edge, 'shadow': shadow, 'shadow_alpha': shadow_alpha}


def font_for(text, path, height, width, serif):
    """The largest font whose words fit `height` x `width`; the sans font gets narrower first.
    The height is the one of plain letters ("Hg"): an accent may rise above the row."""
    size = max(6, int(height * 1.3))
    while size > 5:
        for stretch in ((100, 90, 80, 75) if not serif else (100,)):
            f = ImageFont.truetype(path, size * SCALE)
            if not serif:
                try:
                    f.set_variation_by_axes([stretch, 700])
                except (OSError, AttributeError):
                    pass
            box = f.getbbox(text)
            ref = f.getbbox('Hg')
            if (box[2] - box[0]) <= width * SCALE and (ref[3] - ref[1]) <= height * SCALE:
                return f, (box[0], ref[1], box[2], ref[3])
        size -= 1
    return f, (box[0], ref[1], box[2], ref[3])


def draw_band(canvas, text, box, style, align, serif, limit, clip=None):
    x0, y0, x1, y1 = box
    height = y1 - y0
    left, right = limit
    f, tb = font_for(text, SERIF if serif else SANS, height, right - left, serif)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    W, H = canvas.size[0] * SCALE, canvas.size[1] * SCALE
    if align == 'left':
        x = x0 * SCALE
    elif align == 'right':
        x = x1 * SCALE - tw
    else:
        x = (x0 + x1) * SCALE // 2 - tw // 2
    x = min(max(x, left * SCALE), right * SCALE - tw)
    y = y0 * SCALE + (height * SCALE - th) // 2
    mask = Image.new('L', (W, H), 0)
    ImageDraw.Draw(mask).text((x - tb[0], y - tb[1]), text, font=f, fill=255)
    layers = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if style['shadow'] is not None:
        sh = mask.filter(ImageFilter.MaxFilter(2 * SCALE + 1)).filter(ImageFilter.GaussianBlur(SCALE * 1.2))
        sh = Image.eval(sh, lambda v: int(min(255, v * min(1.0, style['shadow_alpha'] / 90.0 + 0.35))))
        colour = Image.new('RGBA', (W, H), tuple(int(c) for c in style['shadow']) + (0,))
        colour.putalpha(sh)
        layers = Image.alpha_composite(layers, colour)
    if style['edge'] is not None:
        ed = mask.filter(ImageFilter.MaxFilter(2 * (SCALE // 2 + 1) + 1))
        colour = Image.new('RGBA', (W, H), tuple(int(c) for c in style['edge']) + (0,))
        colour.putalpha(ed)
        layers = Image.alpha_composite(layers, colour)
    grad = np.zeros((H, W, 4), dtype=np.uint8)
    fill = style['fill']
    for yy in range(H):
        t = (yy - y) / max(1, th)
        c = fill[int(min(len(fill) - 1, max(0, round(t * (len(fill) - 1)))))]
        grad[yy, :, :3] = np.clip(c, 0, 255)
    grad[:, :, 3] = np.asarray(mask)
    layers = Image.alpha_composite(layers, Image.fromarray(grad, 'RGBA'))
    small = layers.resize(canvas.size, Image.LANCZOS)
    if clip:
        keep = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        keep.paste(small.crop((0, clip[0], canvas.size[0], clip[1])), (0, clip[0]))
        small = keep
    canvas.alpha_composite(small)


def halves(alpha):
    """The rows of text of a picture that stacks two states: one row in each half."""
    h = alpha.shape[0] // 2
    out = []
    for top in (0, h):
        part = alpha[top:top + h]
        ys = np.where((part > 96).any(axis=1))[0]
        xs = np.where((part > 96).any(axis=0))[0]
        if len(ys) and len(xs):
            out.append((int(xs[0]), top + int(ys[0]), int(xs[-1]) + 1, top + int(ys[-1]) + 1))
    return out


def relabel(original, texts, serif=False, size=None, stacked=False):
    """New picture (PIL) with the rows of text of `original` (PIL) replaced by `texts`; with
    `size`, the new picture has another size and its words are centred."""
    rgba = np.asarray(original.convert('RGBA'))
    found = halves(rgba[:, :, 3]) if stacked else bands(rgba[:, :, 3])
    if isinstance(texts, str):
        texts = [texts] * len(found)
    if len(found) == 1 and len(texts) == 2:          # a name with a smaller line under it
        x0, y0, x1, y1 = found[0]
        cut = y0 + int((y1 - y0) * 0.6)
        found = [(x0, y0, x1, cut), (x0, cut + 1, x1, y1)]
    if len(found) != len(texts):
        raise ValueError('%d rows of text in the picture, %d texts' % (len(found), len(texts)))
    canvas = Image.new('RGBA', size or original.size, (0, 0, 0, 0))
    w = canvas.size[0]
    for box, text in zip(found, texts):
        if not text:
            canvas.alpha_composite(original.convert('RGBA').crop(box), (box[0], box[1]))
            continue
        if not text.strip():
            continue
        style = style_of(rgba, box)
        lm, rm = box[0], original.size[0] - box[2]
        align = 'centre' if abs(lm - rm) <= 4 else 'left' if lm < rm else 'right'
        if size:
            box, align = (1, box[1], w - 1, box[3]), 'centre'
        clip = None
        if stacked:
            half = original.size[1] // 2
            clip = (0, half) if box[1] < half else (half, original.size[1])
        draw_band(canvas, text, box, style, align, serif, (1, w - 1), clip)
    return canvas


def runs_of(rgba, floor=110):
    """Groups of columns that hold bright pixels (a button or some words): [(x0, x1)]."""
    a = rgba.astype(np.float64)
    lum = (a[:, :, :3] @ np.array([0.299, 0.587, 0.114])) * (a[:, :, 3] / 255.0)
    bright = lum > floor
    cols = bright.any(axis=0)
    out, start = [], None
    for x, v in enumerate(list(cols) + [False]):
        if v and start is None:
            start = x
        elif not v and start is not None:
            if out and start - out[-1][1] <= 1:
                out[-1] = (out[-1][0], x)
            else:
                out.append((start, x))
            start = None
    rows = np.where(bright.any(axis=1))[0]
    return out, (int(rows[0]), int(rows[-1]) + 1) if len(rows) else (0, rgba.shape[0])


def restrip(original, tokens):
    """New strip of button hints: the buttons of the original, each followed by its new words."""
    rgba = np.asarray(original.convert('RGBA')).copy()
    found, (top, bottom) = runs_of(rgba)
    need = sum(1 if isinstance(t, str) else t[1] for t in tokens)
    if len(found) != need:
        raise ValueError('%d groups of pixels in the strip, the list describes %d' % (len(found), need))
    parts, k, text_box = [], 0, None
    for t in tokens:
        if t == 'i':
            parts.append(('icon', found[k]))
            k += 1
        else:
            text, n = (t, 1) if isinstance(t, str) else t
            if text_box is None:
                text_box = (found[k][0], top, found[k + n - 1][1], bottom)
            parts.append(('text', text))
            k += n
    first, last = found[0][0], found[-1][1]
    style = style_of(rgba, text_box)
    # the bar without its buttons and words: every line takes the colour it has left of them
    bar = rgba.copy()
    ref = max(0, first - 3)
    bar[:, max(0, first - 2):min(bar.shape[1], last + 2)] = bar[:, ref:ref + 1]
    canvas = Image.fromarray(bar, 'RGBA')
    height = bottom - top
    room = last - 6                                # the slanted end of the bar stays clear
    size = max(6, int(height * 1.3))
    while True:
        best = None
        for stretch in (100, 88, 78, 75):
            f = ImageFont.truetype(SANS, size * SCALE)
            try:
                f.set_variation_by_axes([stretch, 700])
            except (OSError, AttributeError):
                pass
            ref_box = f.getbbox('Hg')
            widths = [(f.getbbox(p[1])[2] - f.getbbox(p[1])[0]) / SCALE if p[0] == 'text' else p[1][1] - p[1][0]
                      for p in parts]
            total = sum(widths) + sum(2 if p[0] == 'icon' else 5 for p in parts[:-1])
            if (ref_box[3] - ref_box[1]) <= height * SCALE and total <= room:
                best = (f, widths, total, ref_box)
                break
        if best or size <= 6:
            break
        size -= 1
    if not best:
        raise ValueError('the words do not fit the strip')
    f, widths, total, ref_box = best
    x = last - total
    W, H = canvas.size[0] * SCALE, canvas.size[1] * SCALE
    mask = Image.new('L', (W, H), 0)
    draw = ImageDraw.Draw(mask)
    for p, w in zip(parts, widths):
        if p[0] == 'icon':
            x0, x1 = p[1]
            icon = Image.fromarray(rgba[:, x0:x1], 'RGBA')
            canvas.paste(icon, (int(round(x)), 0))
            x += w + 2
        else:
            tb = f.getbbox(p[1])
            y = top * SCALE + (height * SCALE - (ref_box[3] - ref_box[1])) // 2
            draw.text((int(round(x * SCALE)) - tb[0], y - ref_box[1]), p[1], font=f, fill=255)
            x += w + 5
    layers = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if style['edge'] is not None or style['shadow'] is not None:
        dark = style['edge'] if style['edge'] is not None else style['shadow']
        ed = mask.filter(ImageFilter.MaxFilter(2 * (SCALE // 2) + 1))
        colour = Image.new('RGBA', (W, H), tuple(int(c) for c in dark) + (0,))
        colour.putalpha(ed)
        layers = Image.alpha_composite(layers, colour)
    fill = Image.new('RGBA', (W, H), tuple(int(c) for c in np.mean(style['fill'], axis=0)) + (0,))
    fill.putalpha(mask)
    layers = Image.alpha_composite(layers, fill)
    canvas.alpha_composite(layers.resize(canvas.size, Image.LANCZOS))
    return canvas


def strip_of(rel, stem):
    folder = rel.split('/')[-2] if '/' in rel else ''
    return STRIPS.get('%s/%s' % (folder, stem), STRIPS.get(stem))


def targets(dump):
    """[(path inside the archives, name, GIM bytes)] of the pictures that have new words."""
    files = os.path.join(dump, 'files')
    out = []
    for root, _dirs, fs in os.walk(files):
        for n in sorted(fs):
            stem = os.path.splitext(n)[0].upper()
            if n.lower().endswith('.gim') and (stem in LABELS or stem in STRIPS or any(
                    k.endswith('/' + stem) for k in STRIPS)):
                p = os.path.join(root, n)
                out.append((os.path.relpath(p, files).replace(os.sep, '/'), stem, Path(p).read_bytes()))
    return sorted(out)


def build(dump, font=None, report=None):
    out = {}
    for rel, stem, data in targets(dump):
        try:
            old = gim.decode(data)[0]
            tokens = strip_of(rel, stem)
            if tokens:
                out[rel] = gim.encode(restrip(old, tokens), data)
                continue
            if stem not in LABELS:
                continue
            size = next((v for k, v in SIZES.items() if stem.startswith(k)), None)
            new = relabel(old, LABELS[stem], stem.startswith(SERIF_NAMES), size, stem.startswith(STACKED))
            out[rel] = gim.encode(new, data)
        except ValueError as e:
            if report is not None:
                report.append('%s: %s' % (rel, e))
    return out


def main(argv):
    if len(argv) != 4 or argv[1] != 'preview':
        print(__doc__)
        return 2
    problems = []
    made = build(argv[2], report=problems)
    seen, rows = set(), []
    for rel, stem, data in targets(argv[2]):
        if stem in seen or rel not in made:
            continue
        seen.add(stem)
        rows.append((stem, gim.decode(data)[0], gim.decode(made[rel])[0]))
    cols = 5
    cw = 2 * 132 + 8
    ch = 80
    sheet = Image.new('RGB', (cols * cw, ((len(rows) + cols - 1) // cols) * ch), (70, 70, 84))
    d = ImageDraw.Draw(sheet)
    for i, (stem, old, new) in enumerate(rows):
        x, y = (i % cols) * cw, (i // cols) * ch
        d.text((x + 2, y), stem, fill=(255, 255, 140))
        for k, im in enumerate((old, new)):
            im = im.convert('RGBA')
            s = min(130 / im.width, 66 / im.height, 2.0)
            im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.NEAREST)
            sheet.paste(im, (x + k * 134, y + 12), im)
    sheet.save(argv[3])
    print('%d pictures in %d places, %d problems' % (len(seen), len(made), len(problems)))
    for p in problems[:30]:
        print('  ', p)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
