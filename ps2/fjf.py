#!/usr/bin/env python3
"""FJF containers of the game (every `.tpl`, `.mpl`, `.jnt`, `msg_*.bin`, `skilllist*.bin`...):
`FJF\\0`, u16 count, u16 flags, u32 offset of every entry (+ the end of the last one in some files),
u16 id of every entry, data. Entries may themselves be FJF containers or CMPS-compressed files.

usage: fjf.py list FILE
       fjf.py extract SRC OUT_DIR       SRC = one file or a folder: every CMPS file is unpacked and
                                        every FJF container is unpacked into a folder of the same
                                        name, recursively; other files are copied as they are
"""
import os
import shutil
import struct
import sys

import cmps

MAGIC = b'FJF\0'


def is_fjf(data):
    return data[:4] == MAGIC and len(data) >= 8


def entries(data):
    """[(id, offset, size)] of a container."""
    count, flags = struct.unpack_from('<HH', data, 4)
    offsets = list(struct.unpack_from('<%dI' % count, data, 8))
    pos = 8 + 4 * count
    end = len(data)
    if count and pos + 4 <= offsets[0]:
        nxt = struct.unpack_from('<I', data, pos)[0]
        if offsets[-1] < nxt <= len(data):
            end = nxt
            pos += 4
    ids = list(struct.unpack_from('<%dH' % count, data, pos)) if pos + 2 * count <= (offsets[0] if count else len(data)) else list(range(count))
    out = []
    for i, off in enumerate(offsets):
        nxt = offsets[i + 1] if i + 1 < count else end
        out.append((ids[i], off, max(0, min(nxt, len(data)) - off)))
    return flags, out


def inside(data):
    """False for the index tables (`.jnt`) whose offsets point into another file."""
    _flags, ents = entries(data)
    return bool(ents) and ents[0][1] > 0 and all(off + size <= len(data) for _eid, off, size in ents)


def unwrap(data):
    """CMPS -> plain data, as many times as needed."""
    while cmps.is_cmps(data):
        data = cmps.unpack(data)
    return data


def extract_data(data, out, name):
    """Writes `data` as OUT/name, or as a folder when it is a container; returns the entries written."""
    data = unwrap(data)
    if is_fjf(data) and inside(data):
        folder = os.path.join(out, name)
        os.makedirs(folder, exist_ok=True)
        _flags, ents = entries(data)
        n = 0
        for i, (eid, off, size) in enumerate(ents):
            n += extract_data(data[off:off + size], folder, '%02d_%d' % (i, eid))
        return n
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, name), 'wb') as f:
        f.write(data)
    return 1


def extract_file(path, out):
    with open(path, 'rb') as f:
        data = f.read()
    if not cmps.is_cmps(data) and not is_fjf(data):
        os.makedirs(out, exist_ok=True)
        shutil.copyfile(path, os.path.join(out, os.path.basename(path)))
        return 1
    return extract_data(data, out, os.path.basename(path))


def main(argv):
    if len(argv) == 3 and argv[1] == 'list':
        with open(argv[2], 'rb') as f:
            data = unwrap(f.read())
        if not is_fjf(data):
            print('not a FJF container')
            return 1
        flags, ents = entries(data)
        print('flags 0x%04x, %d entries' % (flags, len(ents)))
        for i, (eid, off, size) in enumerate(ents):
            head = data[off:off + 4]
            if cmps.is_cmps(head):
                head = cmps.lzss(data[off + 16:off + 64])[:4]
            print('%3d id %3d  0x%08x %9d  %s' % (i, eid, off, size, head))
        return 0
    if len(argv) == 4 and argv[1] == 'extract':
        src, out = argv[2], argv[3]
        n = 0
        if os.path.isdir(src):
            for name in sorted(os.listdir(src)):
                p = os.path.join(src, name)
                if os.path.isfile(p):
                    n += extract_file(p, out)
        else:
            n += extract_file(src, out)
        print('%d files -> %s' % (n, out))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
