#!/usr/bin/env python3
"""Dump the Unity asset bundles of Saint Seiya Rebirth (needs `pip install UnityPy`).

usage: dump.py BUNDLE_DIR OUT_DIR [--only PREFIX] [--list FILE] [--types Texture2D,Sprite,...] [--workers N]

BUNDLE_DIR holds the bundles as `abws.py extract` wrote them (`role/hilda.fassets`) or still
wrapped (`role/hilda.fassets.abws`); every bundle goes to OUT_DIR/<bundle path>/:
  Texture2D  -> NAME.png            Sprite -> sprites/NAME.png (cut out of its atlas)
  TextAsset  -> NAME.txt (or .bytes) AudioClip -> NAME.wav (as decoded by fmod)
  Mesh       -> NAME.obj             Font -> NAME.ttf/.otf
plus `objects.json`: every object of the bundle (type, name, path id, size and the file written).
`--list FILE` limits the run to the bundle paths listed in FILE (one per line, relative to BUNDLE_DIR).
Sprites whose name equals a texture's name are still written (they are the atlas cuts).
"""
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import abws  # noqa: E402
import sprites  # noqa: E402

DEFAULT_TYPES = {'Texture2D', 'Sprite', 'TextAsset', 'AudioClip', 'Mesh', 'Font'}


def safe_name(name, fallback):
    name = (name or '').strip().replace('/', '_').replace('\\', '_').replace('\0', '')
    return name or fallback


def load_env(path):
    import UnityPy
    with open(path, 'rb') as f:
        data = f.read()
    if data[:4] == abws.MAGIC:
        data = data[abws.HEADER:]
    return UnityPy.load(data)


def unique(path, used):
    base, ext = os.path.splitext(path)
    out = path
    k = 1
    while out in used:
        out = f'{base}_{k}{ext}'
        k += 1
    used.add(out)
    return out


def dump_bundle(args):
    path, out, types = args
    try:
        env = load_env(path)
    except Exception as e:  # noqa: BLE001 - one bad bundle must not stop the run
        return path, 0, f'load failed: {e}'
    os.makedirs(out, exist_ok=True)
    index = []
    used = set()
    written = 0
    errors = []
    plan = sprites.alpha_plan(env)
    cache = sprites.TextureCache()
    for obj in env.objects:
        entry = {'type': obj.type.name, 'path_id': obj.path_id, 'size': obj.byte_size}
        name = None
        try:
            if obj.type.name in types or obj.type.name in ('GameObject', 'MonoBehaviour', 'AnimationClip', 'Material', 'Shader', 'MonoScript'):
                data = obj.read()
                name = getattr(data, 'm_Name', None) or getattr(data, 'm_ClassName', None)
                entry['name'] = name
            if obj.type.name not in types:
                index.append(entry)
                continue
            fname = safe_name(name, f'{obj.type.name}_{obj.path_id}')
            if obj.type.name == 'Texture2D':
                if data.m_Width == 0 or data.m_Height == 0:
                    index.append(entry)
                    continue
                dest = unique(os.path.join(out, fname + '.png'), used)
                img = sprites.texture_image(obj, plan, cache)
                img.save(dest)
                entry.update(file=os.path.relpath(dest, out), width=data.m_Width, height=data.m_Height,
                             format=str(data.m_TextureFormat).split('.')[-1], merged=img.size != (data.m_Width, data.m_Height))
            elif obj.type.name == 'Sprite':
                dest = unique(os.path.join(out, 'sprites', fname + '.png'), used)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                sprites.sprite_image(data, plan, cache, env).save(dest)
                entry.update(file=os.path.relpath(dest, out), width=int(data.m_Rect.width), height=int(data.m_Rect.height),
                             pivot=[data.m_Pivot.x, data.m_Pivot.y], ppu=data.m_PixelsToUnits)
            elif obj.type.name == 'TextAsset':
                script = data.m_Script
                raw = script.encode('utf-8', 'surrogateescape') if isinstance(script, str) else bytes(script)
                try:
                    raw.decode('utf-8')
                    ext = '.txt'
                except UnicodeDecodeError:
                    ext = '.bytes'
                dest = unique(os.path.join(out, fname + ext), used)
                with open(dest, 'wb') as f:
                    f.write(raw)
                entry.update(file=os.path.relpath(dest, out))
            elif obj.type.name == 'AudioClip':
                samples = data.samples
                for sname, sdata in samples.items():
                    ext = os.path.splitext(sname)[1] or '.wav'
                    dest = unique(os.path.join(out, fname + ext), used)
                    with open(dest, 'wb') as f:
                        f.write(sdata)
                    entry.update(file=os.path.relpath(dest, out), seconds=round(float(data.m_Length), 2))
            elif obj.type.name == 'Mesh':
                dest = unique(os.path.join(out, fname + '.obj'), used)
                with open(dest, 'w', encoding='utf-8') as f:
                    f.write(data.export())
                entry.update(file=os.path.relpath(dest, out), vertices=data.m_VertexData.m_VertexCount)
            elif obj.type.name == 'Font':
                fdata = data.m_FontData
                if fdata:
                    raw = bytes(fdata)
                    ext = '.otf' if raw[:4] == b'OTTO' else '.ttf'
                    dest = unique(os.path.join(out, fname + ext), used)
                    with open(dest, 'wb') as f:
                        f.write(raw)
                    entry.update(file=os.path.relpath(dest, out))
            if 'file' in entry:
                written += 1
        except Exception as e:  # noqa: BLE001
            entry['error'] = str(e)[:200]
            errors.append(f'{obj.type.name} {name}: {e}')
        index.append(entry)
    with open(os.path.join(out, 'objects.json'), 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=0)
    return path, written, '; '.join(errors[:3])


def find_bundles(root, only=None, wanted=None):
    """[(full path, relative path)] of the bundles under root; `wanted` = set of relative paths (with or
    without the .abws suffix) to keep."""
    out = []
    for r, _dirs, files in os.walk(root):
        for f in sorted(files):
            if f.endswith('.fassets') or f.endswith('.fassets.abws'):
                full = os.path.join(r, f)
                rel = os.path.relpath(full, root)
                if only and not rel.startswith(only):
                    continue
                if wanted is not None and rel not in wanted and rel.replace('.abws', '') not in wanted:
                    continue
                out.append((full, rel))
    out.sort(key=lambda t: t[1])
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    src, dest = argv[0], argv[1]
    only = argv[argv.index('--only') + 1] if '--only' in argv else None
    types = set(argv[argv.index('--types') + 1].split(',')) if '--types' in argv else DEFAULT_TYPES
    workers = int(argv[argv.index('--workers') + 1]) if '--workers' in argv else max(1, (os.cpu_count() or 2) // 2)
    wanted = None
    if '--list' in argv:
        with open(argv[argv.index('--list') + 1], encoding='utf-8') as f:
            wanted = {line.strip().replace('.abws', '') for line in f if line.strip()}
    bundles = find_bundles(src, only, wanted)
    jobs = []
    for full, rel in bundles:
        out = os.path.join(dest, rel[:-len('.abws')] if rel.endswith('.abws') else rel)
        jobs.append((full, out, types))
    print(f'{len(jobs)} bundles -> {dest} ({workers} workers)')
    total = 0
    failed = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for i, (path, n, err) in enumerate(pool.map(dump_bundle, jobs, chunksize=4), 1):
            total += n
            if err:
                failed.append(f'{os.path.relpath(path, src)}: {err}')
            if i % 100 == 0 or i == len(jobs):
                print(f'[{i}/{len(jobs)}] {total} files', flush=True)
    if failed:
        with open(os.path.join(dest, 'errors.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(failed) + '\n')
        print(f'{len(failed)} bundles with errors, see {dest}/errors.txt')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
