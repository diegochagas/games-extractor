"""Resource archives of the Digimon WSC engine.

A data bank is mapped at segment 0x3000 and starts with two far pointers
(table start, table end). Everything in it is reached through normalized
offset:segment pointers, so the whole bank can be walked generically:
pointer lists are "structs", anything else is a leaf blob whose type is
recognised by exact-size checks.
"""
import struct
from dataclasses import dataclass, field

from .codecs import cmap_decode, lzss_decode
from .rom import far_ptr

BASE = 0x30000


@dataclass
class Blob:
    offset: int
    length: int
    kind: str = "unknown"
    info: dict = field(default_factory=dict)


def is_archive(bank):
    return far_ptr(bank, 0, BASE) == 8 and (far_ptr(bank, 4, BASE) or -1) > 8


def _ptr_run(bank, addr):
    """Far pointers stored back to back at addr (nulls allowed in between)."""
    out = []
    o = addr
    while o + 4 <= len(bank):
        p = far_ptr(bank, o, BASE)
        if p == -1:
            break
        out.append(p)
        o += 4
    while out and out[-1] is None:
        out.pop()
    return out


def walk(bank):
    """Return (structs {addr: [ptr|None,...]}, leaf start offsets)."""
    structs, leaves, todo = {}, set(), [0]
    while todo:
        a = todo.pop()
        if a in structs or a in leaves:
            continue
        # a mono palette (00 00 xx 3y) reads like a far pointer; it always sits right
        # before the {tiles, map, palette} struct triple whose last member points back at it
        mono = bank[a:a + 2] == b"\0\0" and a + 24 <= len(bank) and far_ptr(bank, a + 20, BASE) == a
        run = [] if mono else _ptr_run(bank, a)
        if not run:
            leaves.add(a)
            continue
        structs[a] = run
        todo.extend(p for p in run if p is not None)
    # a struct's pointer run may spill over the next struct; cut it there
    starts = sorted(structs)
    for a, nxt in zip(starts, starts[1:]):
        structs[a] = structs[a][:(nxt - a) // 4]
    return structs, leaves


def _used_end(bank):
    end = len(bank)
    while end and bank[end - 1] == 0xFF:
        end -= 1
    return end


def classify(bank, off, length):
    d = bank[off:off + length]
    if length < 2:
        return Blob(off, length)
    le = struct.unpack_from("<H", d)[0]
    be = d[0] << 8 | d[1]
    if length in (4, 5) and le == 0:
        return Blob(off, length, "palette_mono", {"shades": [d[2] & 15, d[2] >> 4, d[3] & 15, d[3] >> 4]})
    if 1 <= le <= 16 and 0 <= length - (2 + 32 * le) <= 1:
        cols = struct.unpack_from("<%dH" % (16 * le), d, 2)
        if all(c < 0x1000 for c in cols):
            return Blob(off, length, "palette", {"count": le})
    if le >= 1:
        for bpp, size in ((2, 16), (4, 32)):
            if 0 <= length - (2 + size * le) <= 1:
                return Blob(off, length, "tiles", {"bpp": bpp, "count": le, "compressed": False})
    if length >= 4:
        w, h = struct.unpack_from("<HH", d)
        if 1 <= w <= 256 and 1 <= h <= 256 and 0 <= length - (4 + 2 * w * h) <= 1:
            return Blob(off, length, "tilemap", {"w": w, "h": h, "compressed": False})
    if le >= 1 and 0 <= length - (2 + 4 * le) <= 1:
        return Blob(off, length, "sprite_layout", {"count": le})
    cm = cmap_decode(d)
    if cm and 0 <= length - cm[3] <= 3:
        return Blob(off, length, "tilemap", {"w": cm[0], "h": cm[1], "compressed": True})
    if be >= 1:
        fits = []
        for bpp, size in ((4, 32), (2, 16)):
            if be * size > 0x10000:
                continue
            out, used = lzss_decode(d[2:], be * size)
            if out is not None and 0 <= length - 2 - used <= 3:
                fits.append(bpp)
        if fits:
            return Blob(off, length, "tiles", {"bpp": fits[0], "bpp_candidates": fits, "count": be, "compressed": True})
    return Blob(off, length)


def scan(bank):
    """Walk a bank. Returns (structs, blobs {offset: Blob})."""
    structs, leaves = walk(bank)
    marks = sorted(set(structs) | leaves | {_used_end(bank)})
    blobs = {}
    for a in sorted(leaves):
        nxt = next(m for m in marks if m > a) if a < marks[-1] else a
        blobs[a] = classify(bank, a, nxt - a)
    return structs, blobs


def tile_bytes(bank, blob):
    d = bank[blob.offset:blob.offset + blob.length]
    size = 16 if blob.info["bpp"] == 2 else 32
    n = blob.info["count"]
    if blob.info["compressed"]:
        return lzss_decode(d[2:], n * size)[0]
    return d[2:2 + n * size]


def map_cells(bank, blob):
    d = bank[blob.offset:blob.offset + blob.length]
    if blob.info["compressed"]:
        w, h, cells, _ = cmap_decode(d)
        return w, h, cells
    w, h = blob.info["w"], blob.info["h"]
    return w, h, list(struct.unpack_from("<%dH" % (w * h), d, 4))


def palettes(bank, blob):
    d = bank[blob.offset:blob.offset + blob.length]
    n = blob.info["count"]
    cols = struct.unpack_from("<%dH" % (16 * n), d, 2)
    return [[((c >> 8 & 15) * 17, (c >> 4 & 15) * 17, (c & 15) * 17) for c in cols[i * 16:i * 16 + 16]] for i in range(n)]


def sprite_pieces(bank, blob):
    d = bank[blob.offset:blob.offset + blob.length]
    return [struct.unpack_from("<Hbb", d, 2 + 4 * i) for i in range(blob.info["count"])]
