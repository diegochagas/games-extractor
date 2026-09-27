#!/usr/bin/env python3
"""BTX string tables ("BTX ", UTF-16LE text).

Header: "BTX " u32 version u32 header size u32 0; then u32 group count(?), u32 string count and one
(u32 id, u32 offset) pair per string, the offset being relative to the start of its own pair.

usage: btx.py FILE.btx            print the strings
       btx.py dump SRC_DIR OUT    every *.btx under SRC_DIR -> OUT/<path>.json + OUT/all_text.json/.txt
"""
import json
import os
import struct
import sys
from pathlib import Path


def read(data):
    if data[:4] != b'BTX ':
        raise ValueError('not a BTX file')
    hsize = struct.unpack_from('<I', data, 8)[0]
    _groups, count = struct.unpack_from('<II', data, hsize)
    out = []
    for i in range(count):
        p = hsize + 8 + i * 8
        sid, off = struct.unpack_from('<II', data, p)
        q = p + off
        e = q
        while e + 1 < len(data) and data[e:e + 2] != b'\0\0':
            e += 2
        out.append((sid, data[q:e].decode('utf-16-le', 'replace')))
    return out


def write(data, texts):
    """Copy of the BTX `data` with new strings. texts: {id: text}; the other strings, the ids and
    their order stay as they are."""
    hsize = struct.unpack_from('<I', data, 8)[0]
    groups, count = struct.unpack_from('<II', data, hsize)
    old = read(data)
    head = bytearray(data[:hsize + 8 + count * 8])
    body = bytearray()
    for i, (sid, text) in enumerate(old):
        p = hsize + 8 + i * 8
        struct.pack_into('<II', head, p, sid, len(head) + len(body) - p)
        body += texts.get(sid, text).encode('utf-16-le') + b'\0\0\0\0'     # as the original files do
    body += bytes(-(len(head) + len(body)) % 16)
    return bytes(head) + bytes(body)


def main(argv):
    if len(argv) == 2:
        for sid, text in read(Path(argv[1]).read_bytes()):
            print('%4d  %s' % (sid, text.replace('\n', '\\n')))
        return 0
    if len(argv) != 4 or argv[1] != 'dump':
        print(__doc__)
        return 2
    src, out = argv[2], argv[3]
    everything = {}
    for root, _dirs, names in os.walk(src):
        for n in sorted(names):
            if not n.lower().endswith('.btx'):
                continue
            path = os.path.join(root, n)
            rel = os.path.relpath(path, src)
            rows = read(Path(path).read_bytes())
            everything[rel] = [{'id': sid, 'jp': text} for sid, text in rows]
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'all_text.json'), 'w', encoding='utf-8') as f:
        json.dump(everything, f, ensure_ascii=False, indent=1)
    with open(os.path.join(out, 'all_text.txt'), 'w', encoding='utf-8') as f:
        for rel in sorted(everything):
            f.write('### %s\n' % rel)
            for r in everything[rel]:
                f.write('%4d\t%s\n' % (r['id'], r['jp'].replace('\n', '\\n')))
            f.write('\n')
    n = sum(len(v) for v in everything.values())
    print('%d files, %d strings, %d characters -> %s' % (len(everything), n,
          sum(len(r['jp']) for v in everything.values() for r in v), out))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
