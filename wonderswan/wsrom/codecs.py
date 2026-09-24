"""Graphics codecs shared by the Bandai/Digimon WonderSwan engine."""
import numpy as np


def lzss_decode(data, out_len):
    """LZSS: flag byte LSB first, 1 = literal; match = 12-bit distance + 4-bit (len-3).

    Returns (bytes, consumed) or (None, consumed) when the stream is invalid.
    """
    out = bytearray()
    i = 0
    n = len(data)
    while len(out) < out_len:
        if i >= n:
            return None, i
        flags = data[i]
        i += 1
        for k in range(8):
            if len(out) >= out_len:
                break
            if flags >> k & 1:
                if i >= n:
                    return None, i
                out.append(data[i])
                i += 1
            else:
                if i + 1 >= n:
                    return None, i
                dist = data[i] << 4 | data[i + 1] >> 4
                length = (data[i + 1] & 0xF) + 3
                i += 2
                src = len(out) - dist
                if dist == 0 or src < 0:
                    return None, i
                for _ in range(min(length, out_len - len(out))):
                    out.append(out[src])
                    src += 1
    return bytes(out), i


def cmap_decode(data):
    """Compressed tilemap: bytes w,h then 2-bit codes (MSB first).

    00 = leave cell empty, 01 = repeat current tile, 10 = current tile + 1,
    11 = literal big-endian u16 follows inline. Returns (w, h, cells, consumed);
    empty cells are None.
    """
    if len(data) < 3:
        return None
    w, h = data[0], data[1]
    if not (1 <= w <= 64 and 1 <= h <= 64):
        return None
    cells = []
    cur = 0
    i = 2
    total = w * h
    while len(cells) < total:
        if i >= len(data):
            return None
        codes = data[i]
        i += 1
        for k in range(4):
            if len(cells) >= total:
                break
            c = codes >> (6 - 2 * k) & 3
            if c == 0:
                cells.append(None)
            elif c == 1:
                cells.append(cur)
            elif c == 2:
                cur = (cur + 1) & 0xFFFF
                cells.append(cur)
            else:
                if i + 1 >= len(data):
                    return None
                cur = data[i] << 8 | data[i + 1]
                i += 2
                cells.append(cur)
    return w, h, cells, i


def tiles_2bpp(data):
    n = len(data) // 16
    a = np.frombuffer(data[:n * 16], dtype=np.uint8).reshape(n, 8, 2)
    bits = np.unpackbits(a, axis=2).reshape(n, 8, 2, 8)
    return bits[:, :, 0, :] | bits[:, :, 1, :] << 1


def tiles_4bpp(data):
    """WonderSwan Color 4bpp planar: 4 bytes per row, one bitplane each."""
    n = len(data) // 32
    a = np.frombuffer(data[:n * 32], dtype=np.uint8).reshape(n, 8, 4)
    bits = np.unpackbits(a, axis=2).reshape(n, 8, 4, 8)
    return bits[:, :, 0, :] | bits[:, :, 1, :] << 1 | bits[:, :, 2, :] << 2 | bits[:, :, 3, :] << 3
