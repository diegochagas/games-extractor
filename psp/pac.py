#!/usr/bin/env python3
"""PAC containers of Saint Seiya Omega Ultimate Cosmo.

Header: u16 file count, u16 flags, u32 total size (with or without these 8 bytes); then one
40-byte entry per file
(name[32], u32 offset from the start of the PAC, u32 size). PACs nest: an entry named *.PAC is
another container.

usage: pac.py list FILE.pac
       pac.py extract SRC_DIR_OR_FILE OUTDIR     (recursive; every *.pac becomes a folder)
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
