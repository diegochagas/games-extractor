#!/usr/bin/env python3
"""Angelica PCK reader for Saint Seiya Online (Seiya Reborn client).
Usage: pck.py list FILE.pck   |   pck.py extract FILE.pck OUTDIR
"""
import os, struct, sys, zlib
KEY_1, KEY_2 = 0x62A4F9E1, 0x3520C3D5
PCK_MAX = 0x7FFFFF00  # offsets >= this continue in the .pkx file

class Pck:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        self.pkx = None
        px = path[:-4] + ".pkx"
        if os.path.exists(px):
            self.pkx = open(px, "rb")
        tail_f = self.pkx or self.f
        tail_f.seek(0, 2); n = tail_f.tell()
        
        tail_f.seek(n - 0x118)
        sig1, ver0, enc_tab = struct.unpack("<III", tail_f.read(12))
        tail_f.seek(n - 8)
        self.count, self.version = struct.unpack("<II", tail_f.read(8))
        self.table_off = enc_tab ^ KEY_1
        self.entries = []
        self.f.seek(0)
        self.size = os.path.getsize(path)
        self.pkx_size = os.path.getsize(px) if self.pkx else 0
        self._read_table()

    def _read_at(self, off, ln):
        if off >= PCK_MAX:
            self.pkx.seek(off - PCK_MAX); return self.pkx.read(ln)
        if off + ln > PCK_MAX and self.pkx:
            self.f.seek(off); a = self.f.read(PCK_MAX - off)
            self.pkx.seek(0); return a + self.pkx.read(ln - len(a))
        self.f.seek(off); return self.f.read(ln)

    def _read_table(self):
        off = self.table_off
        for i in range(self.count):
            a, b = struct.unpack("<II", self._read_at(off, 8))
            L = a ^ KEY_1
            assert L == (b ^ KEY_2), (self.path, i, hex(off))
            raw = self._read_at(off + 8, L)
            off += 8 + L
            ent = zlib.decompress(raw) if L < 272 else raw
            if len(ent) < 272 and L >= 272: ent = raw
            name = ent[:260].split(b"\0", 1)[0]
            eoff, esize, ecsize = struct.unpack_from("<III", ent, 260)
            self.entries.append((name, eoff, esize, ecsize))

    def read(self, ent):
        name, eoff, esize, ecsize = ent
        data = self._read_at(eoff, ecsize)
        if ecsize < esize:
            data = zlib.decompress(data)
        return data

def decode_name(b):
    for enc in ("gbk", "utf-8", "latin-1"):
        try: return b.decode(enc)
        except UnicodeDecodeError: pass

if __name__ == "__main__":
    cmd, path = sys.argv[1], sys.argv[2]
    p = Pck(path)
    if cmd == "list":
        for name, o, s, c in p.entries:
            print(f"{o}\t{s}\t{c}\t{decode_name(name).replace(chr(92), '/')}")
    elif cmd == "extract":
        out = sys.argv[3]
        n = 0
        for ent in p.entries:
            rel = decode_name(ent[0]).replace("\\", "/")
            dst = os.path.join(out, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fo: fo.write(p.read(ent))
            n += 1
        print(f"{path}: {n} files -> {out}")
