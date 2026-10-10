#!/usr/bin/env python3
"""CMPS files: `CMPS`, u32 1, u32 size of the data once unpacked, u32 0, then an LZSS stream
(Okumura's: flag byte, bit set = one literal byte, bit clear = 2 bytes `oo ol`: 12-bit position in
a 4096-byte ring buffer that starts at 0xFEE, length = l + 3).

usage: cmps.py unpack FILE OUT_FILE
"""
import struct
import sys

MAGIC = b'CMPS'


def is_cmps(data):
    return data[:4] == MAGIC


def lzss(data, size=None):
    out = bytearray()
    ring = bytearray(4096)
    r = 0xFEE
    i = 0
    n = len(data)
    while i < n and (size is None or len(out) < size):
        flags = data[i]
        i += 1
        for bit in range(8):
            if i >= n or (size is not None and len(out) >= size):
                break
            if flags & (1 << bit):
                c = data[i]
                i += 1
                out.append(c)
                ring[r] = c
                r = (r + 1) & 0xFFF
            else:
                pos = data[i] | ((data[i + 1] & 0xF0) << 4)
                length = (data[i + 1] & 0x0F) + 3
                i += 2
                for k in range(length):
                    c = ring[(pos + k) & 0xFFF]
                    out.append(c)
                    ring[r] = c
                    r = (r + 1) & 0xFFF
    return bytes(out)


def unpack(data):
    if not is_cmps(data):
        raise ValueError('not a CMPS file')
    size = struct.unpack_from('<I', data, 8)[0]
    out = lzss(data[16:], size)
    if len(out) < size - 16 or len(out) > size:
        raise ValueError('unpacked %d bytes, header says %d' % (len(out), size))
    return out + bytes(size - len(out))          # a few files end a byte or two short of the header


def pack(data):
    """Plain LZSS stream (literals only would be enough for the game; references are used
    for runs so the files stay small)."""
    out = bytearray()
    ring = bytearray(4096)
    r = 0xFEE
    i = 0
    n = len(data)
    while i < n:
        flags = 0
        chunk = bytearray()
        for bit in range(8):
            if i >= n:
                break
            best_len, best_pos = 0, 0
            if i + 3 <= n:
                # search the ring buffer for the longest match (cheap: last 4096 bytes of the output)
                start = max(0, i - 4095)
                for j in range(start, i):
                    k = 0
                    while k < 18 and i + k < n and data[j + k] == data[i + k]:
                        k += 1
                    if k > best_len:
                        best_len, best_pos = k, (r - (i - j)) & 0xFFF
                        if k == 18:
                            break
            if best_len >= 3:
                chunk += bytes([best_pos & 0xFF, ((best_pos >> 4) & 0xF0) | (best_len - 3)])
                for k in range(best_len):
                    ring[r] = data[i + k]
                    r = (r + 1) & 0xFFF
                i += best_len
            else:
                flags |= 1 << bit
                chunk.append(data[i])
                ring[r] = data[i]
                r = (r + 1) & 0xFFF
                i += 1
        out.append(flags)
        out += chunk
    return MAGIC + struct.pack('<III', 1, n, 0) + bytes(out)


def main(argv):
    if len(argv) == 4 and argv[1] == 'unpack':
        with open(argv[2], 'rb') as f:
            data = f.read()
        with open(argv[3], 'wb') as f:
            f.write(unpack(data))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
