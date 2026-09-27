#!/usr/bin/env python3
"""Sony GIM images ("MIG.00.1PSP") -> PNG.

Supports the pixel formats the PSP uses: RGBA5650/5551/4444/8888, 4/8/16/32-bit indexed and
DXT1/3/5, plain or swizzled ("fast") pixel order, every frame/level of a picture.

`encode(image, like)` writes a picture back in the format of an existing file (indexed 4 or 8
bits with its palette size, swizzled or not), optionally with another size.

usage: gim.py FILE.gim [OUT.png]
       gim.py convert SRC_DIR OUT_DIR [--workers N]     every *.gim -> OUT_DIR/<same path>.png
"""
import os
import struct
import sys
from pathlib import Path
from multiprocessing import Pool

import numpy as np
from PIL import Image

RGBA5650, RGBA5551, RGBA4444, RGBA8888, INDEX4, INDEX8, INDEX16, INDEX32, DXT1, DXT3, DXT5 = range(11)
BPP = {RGBA5650: 16, RGBA5551: 16, RGBA4444: 16, RGBA8888: 32, INDEX4: 4, INDEX8: 8, INDEX16: 16, INDEX32: 32}


def chunks(data, start, end):
    """Flat list of (type, data offset, data size); `next` already walks into the children."""
    out = []
    p = start
    while p + 16 <= end:
        typ, _unk, size, nxt, doff = struct.unpack_from('<HHIII', data, p)
        if size < 16:
            break
        out.append((typ, p + doff, size - doff))
        p += nxt if nxt else size
    return out


def unswizzle(buf, pitch, height):
    """buf: bytes in 16x8-byte blocks -> rows of `pitch` bytes."""
    bw, bh = pitch // 16, height // 8
    a = np.frombuffer(buf[:bw * bh * 128], dtype=np.uint8).reshape(bh, bw, 8, 16)
    return a.transpose(0, 2, 1, 3).reshape(bh * 8, bw * 16)


def colours(raw, fmt):
    """raw little-endian pixel words -> (n, 4) uint8 RGBA."""
    if fmt == RGBA8888:
        return np.frombuffer(raw, dtype=np.uint8).reshape(-1, 4).copy()
    v = np.frombuffer(raw, dtype='<u2').astype(np.uint32)
    if fmt == RGBA5650:
        r, g, b = v & 31, (v >> 5) & 63, (v >> 11) & 31
        out = [(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2), np.full_like(v, 255)]
    elif fmt == RGBA5551:
        r, g, b, a = v & 31, (v >> 5) & 31, (v >> 10) & 31, (v >> 15) & 1
        out = [(r << 3) | (r >> 2), (g << 3) | (g >> 2), (b << 3) | (b >> 2), a * 255]
    elif fmt == RGBA4444:
        out = [((v >> s) & 15) * 17 for s in (0, 4, 8, 12)]
    else:
        raise ValueError('colour format %d' % fmt)
    return np.stack(out, axis=1).astype(np.uint8)


def dxt(buf, fmt, width, height):
    """PSP DXT blocks (colour words first, then the 2-bit indices; alpha block after the colour)."""
    bw, bh = (width + 3) // 4, (height + 3) // 4
    out = np.zeros((bh * 4, bw * 4, 4), dtype=np.uint8)
    size = 8 if fmt == DXT1 else 16
    for i in range(bw * bh):
        blk = buf[i * size:(i + 1) * size]
        if len(blk) < size:
            break
        idx, c0, c1 = struct.unpack_from('<IHH', blk, 0)
        pal = np.zeros((4, 4), dtype=np.int32)
        for k, c in enumerate((c0, c1)):
            r, g, b = (c >> 11) & 31, (c >> 5) & 63, c & 31
            pal[k] = ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2), 255)
        if fmt != DXT1 or c0 > c1:
            pal[2] = (2 * pal[0] + pal[1]) // 3
            pal[3] = (pal[0] + 2 * pal[1]) // 3
        else:
            pal[2] = (pal[0] + pal[1]) // 2
            pal[3] = (0, 0, 0, 0)
        pal[:, 3] = np.where(pal[:, 3] > 0, 255, 0) if fmt == DXT1 else 255
        px = np.array([(idx >> (2 * k)) & 3 for k in range(16)])
        cell = pal[px].reshape(4, 4, 4)
        if fmt == DXT3:
            bits = struct.unpack_from('<Q', blk, 8)[0]
            cell[:, :, 3] = np.array([((bits >> (4 * k)) & 15) * 17 for k in range(16)]).reshape(4, 4)
        elif fmt == DXT5:
            bits = int.from_bytes(blk[8:14], 'little')
            a0, a1 = blk[14], blk[15]
            if a0 > a1:
                al = [a0, a1] + [((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)]
            else:
                al = [a0, a1] + [((5 - k) * a0 + k * a1) // 5 for k in range(1, 5)] + [0, 255]
            cell[:, :, 3] = np.array([al[(bits >> (3 * k)) & 7] for k in range(16)]).reshape(4, 4)
        y, x = divmod(i, bw)
        out[y * 4:y * 4 + 4, x * 4:x * 4 + 4] = cell
    return out[:height, :width]


def block(data, off):
    """Parse an image/palette block: list of frames as raw arrays plus its description."""
    (hsize, _r, fmt, order, width, height, bpp, palign, halign, _dim, _r2, _r3, _idx, pix, _end, _mask,
     _ltype, levels, _ftype, frames) = struct.unpack_from('<HHHHHHHHHHHHIIIIHHHH', data, off)
    offsets = struct.unpack_from('<%dI' % max(1, frames * levels), data, off + 0x30)
    out = []
    for fo in offsets[:max(1, frames)]:
        start = off + (fo if fo else pix)
        if fmt in (DXT1, DXT3, DXT5):
            bw, bh = (width + 3) // 4, (height + 3) // 4
            n = bw * bh * (8 if fmt == DXT1 else 16)
            out.append(dxt(data[start:start + n], fmt, width, height))
            continue
        palign = palign or 1
        halign = halign or 1
        pw = (width + palign - 1) // palign * palign
        ph = (height + halign - 1) // halign * halign
        pitch = pw * bpp // 8
        if order == 1:                                       # swizzled blocks are 16 bytes wide
            pitch = (pitch + 15) // 16 * 16
            ph = (ph + 7) // 8 * 8
        raw = data[start:start + pitch * ph]
        if len(raw) < pitch * ph:
            raw = raw + bytes(pitch * ph - len(raw))
        if order == 1:
            rows = unswizzle(raw, pitch, ph)
        else:
            rows = np.frombuffer(raw, dtype=np.uint8).reshape(ph, pitch)
        rows = np.ascontiguousarray(rows)
        if fmt == INDEX4:
            idx = np.stack([rows & 15, rows >> 4], axis=2).reshape(ph, pitch * 2)
        elif fmt == INDEX8:
            idx = rows
        elif fmt == INDEX16:
            idx = rows.view('<u2')
        elif fmt == INDEX32:
            idx = rows.view('<u4')
        else:
            out.append(colours(rows.tobytes(), fmt).reshape(ph, -1, 4)[:height, :width])
            continue
        out.append(idx[:height, :width])
    return {'format': fmt, 'width': width, 'height': height, 'frames': out}


def decode(data):
    """Return a list of PIL images (one per picture/frame) of a GIM file."""
    start = data.find(b'MIG.00.1PSP')
    if start < 0:
        raise ValueError('not a GIM file (big-endian ".GIM1.00" files are not handled)')
    images, palettes = [], []
    for typ, off, _size in chunks(data, start + 16, len(data)):
        if typ == 4:
            images.append(block(data, off))
        elif typ == 5:
            palettes.append(block(data, off))
    out = []
    for n, img in enumerate(images):
        pal = palettes[n] if n < len(palettes) else (palettes[-1] if palettes else None)
        for f, frame in enumerate(img['frames']):
            if frame.ndim == 3:
                rgba = frame
            else:
                if pal is None:
                    raise ValueError('indexed image without a palette')
                lut = pal['frames'][min(f, len(pal['frames']) - 1)].reshape(-1, 4)
                if lut.shape[0] < 256:
                    lut = np.vstack([lut, np.zeros((256 - lut.shape[0], 4), dtype=np.uint8)])
                rgba = lut[np.minimum(frame.astype(np.int64), lut.shape[0] - 1)]
            out.append(Image.fromarray(np.ascontiguousarray(rgba).astype(np.uint8), 'RGBA'))
    return out


def swizzle(rows):
    """rows: (height, pitch) bytes, height a multiple of 8 and pitch of 16 -> swizzled bytes."""
    h, pitch = rows.shape
    return rows.reshape(h // 8, 8, pitch // 16, 16).transpose(0, 2, 1, 3).tobytes()


def quantise(image, colours):
    """(indices (h, w), palette (colours, 4)) of an RGBA image; colour 0 is fully transparent
    when the picture has transparent pixels."""
    rgba = np.asarray(image.convert('RGBA')).copy()
    rgba[rgba[:, :, 3] == 0] = 0
    clear = bool((rgba[:, :, 3] == 0).any())
    q = Image.fromarray(rgba, 'RGBA').quantize(colors=colours - (1 if clear else 0),
                                                 method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette('RGBA'), dtype=np.uint8).reshape(-1, 4)
    idx = np.asarray(q, dtype=np.uint8).copy()
    used = int(idx.max()) + 1
    pal = pal[:used]
    if clear:
        idx = idx + 1
        idx[rgba[:, :, 3] == 0] = 0
        pal = np.vstack([np.zeros((1, 4), dtype=np.uint8), pal])
    out = np.zeros((colours, 4), dtype=np.uint8)
    out[:len(pal)] = pal[:colours]
    return idx, out


def _block(fmt, order, width, height, bpp, palign, halign, level_type, pixels):
    head = struct.pack('<HHHHHHHHHHHHIIIIHHHH', 0x30, 0, fmt, order, width, height, bpp, palign, halign, 2, 0, 0,
                       0x30, 0x40, 0x40 + len(pixels), 0, level_type, 1, 3, 1)
    return head + struct.pack('<IIII', 0x40, 0, 0, 0) + pixels


def _chunk(kind, body, children=False):
    size = 16 + len(body)
    return struct.pack('<HHIII', kind, 0, size, 16 if children else size, 16) + body


def encode(image, like):
    """GIM file of `image` (PIL) in the format of the GIM file `like` (bytes): same pixel format,
    order and palette size, the size of `image`. Only indexed pictures with one frame."""
    start = like.find(b'MIG.00.1PSP')
    parts = chunks(like, start + 16, len(like))
    img = [off for typ, off, _s in parts if typ == 4]
    pal = [off for typ, off, _s in parts if typ == 5]
    if len(img) != 1 or len(pal) != 1:
        raise ValueError('only pictures with one image and one palette are written')
    ih = struct.unpack_from('<HHHHHHHHH', like, img[0])
    ph = struct.unpack_from('<HHHHHHHHH', like, pal[0])
    fmt, order, bpp, palign, halign = ih[2], ih[3], ih[6], ih[7], ih[8]
    if fmt not in (INDEX4, INDEX8) or ph[2] != RGBA8888:
        raise ValueError('pixel format %d with palette format %d is not written' % (fmt, ph[2]))
    colours = ph[4]
    width, height = image.size
    idx, table = quantise(image, min(colours, 16 if fmt == INDEX4 else 256))
    pw = (width + palign - 1) // palign * palign
    ph_ = (height + halign - 1) // halign * halign
    pitch = pw * bpp // 8
    if order == 1:
        pitch = (pitch + 15) // 16 * 16
        ph_ = (ph_ + 7) // 8 * 8
    full = np.zeros((ph_, pitch * 8 // bpp), dtype=np.uint8)
    full[:height, :width] = idx
    if fmt == INDEX4:
        rows = (full[:, 0::2] & 15) | (full[:, 1::2] << 4)
    else:
        rows = full
    rows = np.ascontiguousarray(rows, dtype=np.uint8)
    pixels = swizzle(rows) if order == 1 else rows.tobytes()
    colours_bytes = np.zeros((colours, 4), dtype=np.uint8)
    colours_bytes[:len(table)] = table
    picture = _chunk(4, _block(fmt, order, width, height, bpp, palign, halign, 1, pixels)) + \
        _chunk(5, _block(RGBA8888, 0, colours, 1, 32, ph[7], ph[8], 2, colours_bytes.tobytes()))
    tail = b''
    end = [off for typ, off, _s in parts if typ == 5][0]
    last = max(parts, key=lambda c: c[1])
    if last[0] not in (4, 5):                                  # file information chunk, kept as it is
        tail = like[last[1] - 16:]
    body = _chunk(3, picture, children=True)
    return like[start:start + 16] + _chunk(2, body + tail, children=True)


def save(src, dest):
    imgs = decode(Path(src).read_bytes())
    os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
    for i, im in enumerate(imgs):
        im.save(dest if i == 0 else '%s~%d.png' % (dest[:-4], i))
    return len(imgs)


def _job(job):
    try:
        return job[0], save(*job), None
    except Exception as e:                                  # keep going, report at the end
        return job[0], 0, '%s: %s' % (type(e).__name__, e)


def main(argv):
    if len(argv) >= 4 and argv[1] == 'convert':
        src, out = argv[2], argv[3]
        workers = int(argv[argv.index('--workers') + 1]) if '--workers' in argv else os.cpu_count()
        jobs = []
        for root, _dirs, names in os.walk(src):
            for n in sorted(names):
                if n.lower().endswith('.gim'):
                    p = os.path.join(root, n)
                    jobs.append((p, os.path.join(out, os.path.relpath(p, src))[:-4] + '.png'))
        done, failed = 0, []
        with Pool(workers) as pool:
            for path, n, err in pool.imap_unordered(_job, jobs, chunksize=8):
                done += n
                if err:
                    failed.append((path, err))
        for path, err in failed:
            print('FAILED', path, err)
        print('%d GIM files, %d images written, %d failed -> %s' % (len(jobs), done, len(failed), out))
        return 1 if failed else 0
    if len(argv) < 2:
        print(__doc__)
        return 2
    dest = argv[2] if len(argv) > 2 else os.path.splitext(argv[1])[0] + '.png'
    print(save(argv[1], dest), 'image(s) ->', dest)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
