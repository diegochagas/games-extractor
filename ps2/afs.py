#!/usr/bin/env python3
"""CRI AFS archives (PS2 / Dreamcast era): `AFS\\0`, u32 count, (u32 offset, u32 size) per file,
then the pointer to the name table (right after the entries, or at 0x7FFF8 in older archives);
the name table has 48-byte records: name[32], six u16 of a date (y, m, d, h, min, s), u32 size.

usage: afs.py list ARCHIVE.afs
       afs.py extract ARCHIVE.afs OUT_DIR [--index OUT.json]

Files without a name table are written as NNNN.bin. A listing with the order, offsets, dates
and sizes goes to OUT_DIR/afs_index.json (or --index).
"""
import json
import os
import struct
import sys


def read_table(f):
    f.seek(0)
    if f.read(4) != b'AFS\0':
        raise ValueError('not an AFS archive')
    count = struct.unpack('<I', f.read(4))[0]
    entries = [struct.unpack('<II', f.read(8)) for _ in range(count)]
    name_off, name_size = struct.unpack('<II', f.read(8))
    if name_off == 0:
        f.seek(0x7FFF8)
        name_off, name_size = struct.unpack('<II', f.read(8))
    names = []
    if name_off and name_size >= 48 * count:
        f.seek(name_off)
        for _ in range(count):
            rec = f.read(48)
            name = rec[:32].split(b'\0')[0].decode('latin-1')
            y, mo, d, h, mi, s, size = struct.unpack('<6HI', rec[32:48])
            names.append({'name': name, 'date': '%04d-%02d-%02d %02d:%02d:%02d' % (y, mo, d, h, mi, s), 'size': size})
    rows = []
    for i, (off, size) in enumerate(entries):
        row = {'index': i, 'offset': off, 'size': size}
        if names:
            row.update(names[i])
        else:
            row['name'] = '%04d.bin' % i
        rows.append(row)
    return rows


def extract(archive, out, index_path=None):
    with open(archive, 'rb') as f:
        rows = read_table(f)
        os.makedirs(out, exist_ok=True)
        seen = {}
        for row in rows:
            name = row['name']
            if name in seen:                       # the same name twice: keep the order in the name
                seen[name] += 1
                stem, ext = os.path.splitext(name)
                name = '%s~%d%s' % (stem, seen[name], ext)
            else:
                seen[name] = 0
            row['file'] = name
            f.seek(row['offset'])
            with open(os.path.join(out, name), 'wb') as g:
                g.write(f.read(row['size']))
    with open(index_path or os.path.join(out, 'afs_index.json'), 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    return rows


def main(argv):
    if len(argv) >= 3 and argv[1] == 'list':
        with open(argv[2], 'rb') as f:
            for row in read_table(f):
                print('%5d %10d %10d %s %s' % (row['index'], row['offset'], row['size'], row.get('date', ''), row['name']))
        return 0
    if len(argv) >= 4 and argv[1] == 'extract':
        index = argv[argv.index('--index') + 1] if '--index' in argv else None
        rows = extract(argv[2], argv[3], index)
        print('%d files -> %s' % (len(rows), argv[3]))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
