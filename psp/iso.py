#!/usr/bin/env python3
"""ISO 9660 images: list the files and replace one without rebuilding the image.

usage: iso.py list IMAGE.iso
       iso.py replace IMAGE.iso PATH/IN/IMAGE NEW_FILE [PATH NEW_FILE ...]

`replace` changes the image itself (work on a copy). The new file is written over the old one
when it fits in its sectors, and at the end of the image when it does not; the directory record
(position and size, in both byte orders) and the size of the volume are updated. Every other
file stays at its sector, which matters to games that remember sector numbers.
"""
import os
import struct
import sys

SECTOR = 2048


def records(f, lba, size, prefix=''):
    """Yield (path, record offset in the image, lba, size, is_dir) of a directory, recursively."""
    f.seek(lba * SECTOR)
    data = f.read(size)
    p = 0
    while p < len(data):
        n = data[p]
        if n == 0:                                   # records do not cross sectors
            p = (p // SECTOR + 1) * SECTOR
            continue
        ext, length = struct.unpack_from('<I', data, p + 2)[0], struct.unpack_from('<I', data, p + 10)[0]
        flags, nlen = data[p + 25], data[p + 32]
        name = data[p + 33:p + 33 + nlen]
        if name not in (b'\0', b'\1'):
            text = name.decode('ascii', 'replace').split(';')[0]
            path = prefix + text
            yield path, lba * SECTOR + p, ext, length, bool(flags & 2)
            if flags & 2:
                yield from records(f, ext, length, path + '/')
        p += n


def listing(path):
    with open(path, 'rb') as f:
        f.seek(16 * SECTOR)
        pvd = f.read(SECTOR)
        if pvd[1:6] != b'CD001':
            raise ValueError('%s: not an ISO 9660 image' % path)
        root_lba, root_size = struct.unpack_from('<I', pvd, 156 + 2)[0], struct.unpack_from('<I', pvd, 156 + 10)[0]
        return list(records(f, root_lba, root_size))


def replace(path, changes):
    """changes: {path in the image: bytes or a file name}. Returns [(path, 'place' | 'end', size)]."""
    table = {p.upper(): (p, off, lba, size) for p, off, lba, size, is_dir in listing(path) if not is_dir}
    done = []
    with open(path, 'r+b') as f:
        for inner, new in changes.items():
            if inner.upper() not in table:
                raise ValueError('not in the image: %s' % inner)
            name, rec, lba, size = table[inner.upper()]
            if not isinstance(new, (bytes, bytearray)):
                with open(new, 'rb') as g:
                    new = g.read()
            room = (size + SECTOR - 1) // SECTOR * SECTOR
            if len(new) <= room:
                where, place = lba, 'place'
            else:
                f.seek(0, 2)
                where, place = (f.tell() + SECTOR - 1) // SECTOR, 'end'
            f.seek(where * SECTOR)
            f.write(new)
            f.write(bytes(-len(new) % SECTOR if place == 'end' else room - len(new)))
            f.seek(rec + 2)
            f.write(struct.pack('<I', where) + struct.pack('>I', where) +
                    struct.pack('<I', len(new)) + struct.pack('>I', len(new)))
            done.append((name, place, len(new)))
        f.seek(0, 2)
        sectors = f.tell() // SECTOR
        f.seek(16 * SECTOR + 80)
        f.write(struct.pack('<I', sectors) + struct.pack('>I', sectors))
    return done


def main(argv):
    if len(argv) == 3 and argv[1] == 'list':
        for p, _off, lba, size, is_dir in listing(argv[2]):
            print('%8d %10d  %s%s' % (lba, size, p, '/' if is_dir else ''))
        return 0
    if len(argv) >= 5 and argv[1] == 'replace' and len(argv) % 2 == 1:
        changes = dict(zip(argv[3::2], argv[4::2]))
        for name, place, size in replace(argv[2], changes):
            print('%-5s %10d  %s' % (place, size, name))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
