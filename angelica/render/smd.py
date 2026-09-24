#!/usr/bin/env python3
"""Reader for Angelica skin model descriptors (`.smd`, magic MOXBDMSA).

    0x00 "MOXBDMSA"  0x08 u32 version (8/9)  0x0c u32 ski count  0x10 u32 action count
    0x58 (u32 len, GBK name) skeleton .bon
         ski_count x (u32 len, GBK name) .ski files (same folder)
         u32 ?, (u32 len, GBK name) action folder (tcks_*)
         actions: (u32 len, name) u32 u32 f32 u32 (u32 len, file .stck) ...

Only the skeleton and mesh names are needed for rendering.
"""
import struct
import sys


def parse_smd(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"MOXBDMSA":
        raise ValueError("not a MOXBDMSA file: %s" % path)
    version, nski, nact = struct.unpack_from("<III", data, 8)
    pos = 0x58

    def name():
        nonlocal pos
        n = struct.unpack_from("<I", data, pos)[0]
        if n > 1024 or pos + 4 + n > len(data):
            raise ValueError("bad string length at 0x%x" % pos)
        v = data[pos + 4:pos + 4 + n].decode("gbk", "replace")
        pos += 4 + n
        return v

    bon = name()
    skis = [name() for _ in range(nski)]
    return {"path": path, "version": version, "skeleton": bon, "skis": skis, "actions": nact}


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(parse_smd(p))
