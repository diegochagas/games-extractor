#!/usr/bin/env python3
"""How the non-standard Angelica .pck keys of Saint Seiya Online were found (KEY_1=0x62A4F9E1, KEY_2=0x3520C3D5, see pck.py).

    find_pck_keys.py PATH/TO/configs.pck

Every file stored in a .pck starts with a zlib stream. The encrypted file table holds, per entry, the compressed
length XOR-ed with the two keys, so for each zlib stream found by scanning the archive the two little-endian
words right before it XOR the stream's real length back to KEY_1 and KEY_2. The value that repeats across many
streams is the key. Useful again for another Angelica-engine game with its own keys.
"""
import struct
import sys
import zlib
from collections import Counter


def main(path):
    d = open(path, "rb").read()
    n = len(d)
    print("tail fields:", [hex(x) for x in struct.unpack_from("<IIII", d, n - 0x118 - 4)], "count/ver:", [hex(x) for x in struct.unpack_from("<II", d, n - 8)])
    k1, k2 = Counter(), Counter()
    for p in range(8, n - 16):
        if d[p + 8] == 0x78 and d[p + 9] in (0x01, 0x9C, 0xDA, 0x5E):
            do = zlib.decompressobj()
            chunk = d[p + 8:p + 8 + 4096]
            try:
                out = do.decompress(chunk)
            except zlib.error:
                continue
            if do.eof:
                length = len(chunk) - len(do.unused_data)
                a, b = struct.unpack_from("<II", d, p)
                k1[a ^ length] += 1
                k2[b ^ length] += 1
                print(f"p=0x{p:x} len={length} out={len(out)} K1?=0x{a ^ length:08x} K2?=0x{b ^ length:08x} {out[:40]!r}")
    print("most common KEY_1 candidates:", [(hex(k), c) for k, c in k1.most_common(3)])
    print("most common KEY_2 candidates:", [(hex(k), c) for k, c in k2.most_common(3)])


if __name__ == "__main__":
    main(sys.argv[1])
