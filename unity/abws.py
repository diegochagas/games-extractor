#!/usr/bin/env python3
"""Saint Seiya Rebirth (圣斗士星矢：重生, DeNA / Wapu, Unity 2022.3 IL2CPP) asset bundles.

The game ships its Unity AssetBundles as `*.fassets.abws` files: a 256-byte header (magic
`AA 55 01 00`, then the bundle name, zero padded) followed by a normal `UnityFS` stream.
`GameRes.manifest.abws` is the Unity AssetBundleManifest text (bundle names + dependencies);
every `X.fassets.manifest.abws` is the per-bundle manifest (hashes). The APK holds most
bundles under `assets/GameRes/`; the `role/*` ones (character models) come from the CDN
after login (see `cdn.py`).

usage: abws.py list APK_OR_DIR                 every bundle with its size
       abws.py extract APK_OR_DIR OUTDIR       plain UnityFS files, same relative paths, `.abws` dropped
       abws.py manifest GameRes.manifest.abws  JSON of {bundle: [dependencies]} on stdout
       abws.py strip FILE.abws OUT             one file
"""
import json
import os
import re
import sys
import zipfile

MAGIC = b'\xaa\x55\x01\x00'
HEADER = 256
PREFIX = 'assets/GameRes/'


def strip_header(data, name='?'):
    """The UnityFS payload of an .abws blob (or the raw bytes when there is no wrapper)."""
    if data[:4] == MAGIC:
        return data[HEADER:]
    if data[:7] == b'UnityFS':
        return data
    raise ValueError(f'{name}: not an .abws bundle (magic {data[:4].hex()})')


def wrapped_name(data):
    """The bundle name stored in the 256-byte header."""
    return data[4:HEADER].split(b'\0', 1)[0].decode('utf-8', 'replace')


def parse_manifest(text):
    """AssetBundleManifest text -> {bundle name: [dependency names]}, in file order."""
    out = {}
    current = None
    for line in text.splitlines():
        m = re.match(r'\s*Name: (\S+)', line)
        if m:
            current = m.group(1)
            out[current] = []
            continue
        m = re.match(r'\s*Dependencies: \{\}', line)
        if m:
            continue
        m = re.match(r'\s*Dependency_\d+: (\S+)', line)
        if m and current:
            out[current].append(m.group(1))
    return out


def read_file(path):
    with open(path, 'rb') as f:
        return f.read()


def iter_source(path):
    """Yields (relative path without the APK prefix, bytes reader) for every .abws of an APK or a folder."""
    if os.path.isdir(path):
        for root, _dirs, files in os.walk(path):
            for f in sorted(files):
                if f.endswith('.abws'):
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, path)
                    yield rel, (lambda p=full: read_file(p))
        return
    z = zipfile.ZipFile(path)
    for info in z.infolist():
        if info.filename.startswith(PREFIX) and info.filename.endswith('.abws'):
            rel = info.filename[len(PREFIX):]
            yield rel, (lambda i=info: z.read(i))


def list_bundles(path):
    rows = []
    if os.path.isdir(path):
        for rel, read in iter_source(path):
            rows.append((rel, len(read())))
    else:
        z = zipfile.ZipFile(path)
        for info in z.infolist():
            if info.filename.startswith(PREFIX) and info.filename.endswith('.abws'):
                rows.append((info.filename[len(PREFIX):], info.file_size))
    return rows


def extract(path, outdir, manifests=True):
    """Writes every bundle as a plain UnityFS file (`.abws` dropped). Returns the count."""
    n = 0
    for rel, read in iter_source(path):
        if not manifests and '.manifest.' in rel:
            continue
        data = read()
        dest = os.path.join(outdir, rel[:-len('.abws')])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(strip_header(data, rel) if '.manifest.' not in rel else data[HEADER:] if data[:4] == MAGIC else data)
        n += 1
    return n


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == 'list':
        for rel, size in list_bundles(argv[1]):
            print(f'{size:12d}  {rel}')
    elif cmd == 'extract':
        n = extract(argv[1], argv[2])
        print(f'{n} files written to {argv[2]}')
    elif cmd == 'manifest':
        with open(argv[1], 'rb') as f:
            data = f.read()
        text = (data[HEADER:] if data[:4] == MAGIC else data).decode('utf-8', 'replace')
        json.dump(parse_manifest(text), sys.stdout, indent=1, ensure_ascii=False)
        print()
    elif cmd == 'strip':
        with open(argv[1], 'rb') as f:
            data = f.read()
        with open(argv[2], 'wb') as f:
            f.write(strip_header(data, argv[1]))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
