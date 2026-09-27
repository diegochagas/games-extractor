#!/usr/bin/env python3
"""PAC containers of Saint Seiya Omega Ultimate Cosmo.

Header: u16 file count, u16 flags, u32 total size (with or without these 8 bytes); then one
40-byte entry per file
(name[32], u32 offset from the start of the PAC, u32 size). PACs nest: an entry named *.PAC is
another container.

usage: pac.py list FILE.pac
       pac.py extract SRC_DIR_OR_FILE OUTDIR     (recursive; every *.pac becomes a folder)

`build(data, {path: bytes})` makes a copy of a container with some of its files replaced.
"""
import os
import struct
import sys
from pathlib import Path


def is_pac(data):
    if len(data) < 48:
        return False
    count, _flags, total = struct.unpack_from('<HHI', data, 0)
    if not count or not len(data) - 16 <= total <= len(data) or 8 + count * 40 > len(data):
        return False                              # the total leaves out the header in some files
    if struct.unpack_from('<I', data, 8 + 32)[0] != 8 + count * 40:
        return False
    for i in range(count):
        p = 8 + i * 40
        name = data[p:p + 32].split(b'\0')[0]
        off, size = struct.unpack_from('<II', data, p + 32)
        if not name or any(c < 0x20 for c in name) or off + size > len(data):
            return False
    return True


def entries(data):
    count = struct.unpack_from('<H', data, 0)[0]
    out = []
    for i in range(count):
        p = 8 + i * 40
        name = data[p:p + 32].split(b'\0')[0].decode('shift_jis', 'replace')
        off, size = struct.unpack_from('<II', data, p + 32)
        out.append((name, off, size))
    return out


def build(data, replace):
    """Copy of the PAC `data` with some files replaced. replace: {path: bytes}, the paths as
    `walk` gives them (nested containers are rebuilt too). Order, names and flags are kept."""
    count, flags, total = struct.unpack_from('<HHI', data, 0)
    short = len(data) - total                    # 0, or 8 when the total leaves the header out
    items = entries(data)
    seen = {}
    blobs = []
    for name, off, size in items:
        blob = data[off:off + size]
        n = seen.get(name.lower(), 0)
        seen[name.lower()] = n + 1
        shown = name
        if n:
            stem, ext = os.path.splitext(name)
            shown = '%s~%d%s' % (stem, n, ext)
        if shown in replace:
            blob = replace[shown]
        else:
            inner = {k[len(shown) + 1:]: v for k, v in replace.items() if k.startswith(shown + '/')}
            if inner:
                blob = build(blob, inner)
        blobs.append(blob)
    # the space between two files (alignment) is kept as it was in the original
    gaps = [b[1] - (a[1] + a[2]) for a, b in zip(items, items[1:])] + [len(data) - (items[-1][1] + items[-1][2])]
    align = 16 if all((off % 16) == 0 for _n, off, _s in items) else 4 if all((off % 4) == 0 for _n, off, _s in items) else 1
    out = bytearray(data[:8 + count * 40])
    for i, blob in enumerate(blobs):
        struct.pack_into('<II', out, 8 + i * 40 + 32, len(out), len(blob))
        out += blob
        pad = -len(out) % align
        if len(blob) == items[i][2]:
            pad = max(0, gaps[i])
        out += bytes(pad)
    struct.pack_into('<HHI', out, 0, count, flags, len(out) - short)
    return bytes(out)


def walk(data, prefix=''):
    """Yield (path, bytes) for every leaf file, descending into nested PACs."""
    seen = {}
    for name, off, size in entries(data):
        blob = data[off:off + size]
        n = seen.get(name.lower(), 0)
        seen[name.lower()] = n + 1
        if n:                                   # same name twice in one PAC
            stem, ext = os.path.splitext(name)
            name = '%s~%d%s' % (stem, n, ext)
        path = prefix + name
        if is_pac(blob):
            yield from walk(blob, path + '/')
        else:
            yield path, blob


def main(argv):
    if len(argv) < 3 or argv[1] not in ('list', 'extract'):
        print(__doc__)
        return 2
    if argv[1] == 'list':
        for path, blob in walk(Path(argv[2]).read_bytes()):
            print('%10d  %s' % (len(blob), path))
        return 0
    src, out = argv[2], argv[3]
    files = []
    if os.path.isdir(src):
        for root, _dirs, names in os.walk(src):
            files += [os.path.join(root, n) for n in names]
    else:
        files, src = [src], os.path.dirname(src)
    count = 0
    for f in sorted(files):
        data = Path(f).read_bytes()
        rel = os.path.relpath(f, src)
        if is_pac(data):
            for path, blob in walk(data, rel + '/'):
                dest = os.path.join(out, path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                Path(dest).write_bytes(blob)
                count += 1
        else:
            dest = os.path.join(out, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            Path(dest).write_bytes(data)
            count += 1
    print('%d files -> %s' % (count, out))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
