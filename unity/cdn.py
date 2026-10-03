#!/usr/bin/env python3
"""Saint Seiya Rebirth resource CDN: the bundles the APK does not ship (`role/*` characters, icons,
card art, newer configs) are fetched by the game after login from a public CDN. No login is needed
to read it.

How the client finds it (from the launcher SDK in classes.dex + the IL2CPP metadata):
  GET {center}/index.php/p{PID}/server/pid/{PID}/gid/{GID}/o_system/android
  -> JSON with `android_res_url` (CDN root) and `res_version` = "APP|TAG_APP|TAG..." pairs
  bundle URL = {android_res_url}{TAG}/GameRes/{bundle name}.abws   (plus `.manifest.abws` next to it)

usage: cdn.py server                                   prints the CDN root, the tags and the server count
       cdn.py fetch OUTDIR NAME [NAME...]              e.g. role/hilda.fassets
       cdn.py sync OUTDIR MANIFEST [--only PREFIX] [--all] [--workers N]
             every bundle of a GameRes.manifest(.abws) that is not yet in OUTDIR (same relative
             path as the APK: OUTDIR/role/hilda.fassets.abws); --only role/ limits to a prefix;
             a bundle already present with the same per-bundle manifest hash is skipped
       cdn.py probe NAME [NAME...]                     HEAD only: which of these exist on the CDN
Environment: SSR_CENTER, SSR_PID, SSR_GID override the center host and ids; SSR_TAG forces a tag.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import abws  # noqa: E402

CENTER = os.environ.get('SSR_CENTER', 'http://sdscenter.5xgames.cn')
PID = os.environ.get('SSR_PID', '321')
GID = os.environ.get('SSR_GID', '33')
UA = 'Mozilla/5.0 (Linux; Android 10) UnityPlayer/2022.3.62f3'
TIMEOUT = 120


def server_url(center=CENTER, pid=PID, gid=GID):
    return f'{center}/index.php/p{pid}/server/pid/{pid}/gid/{gid}/o_system/android'


def http(url, method='GET', retries=3):
    last = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, method=method, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.status, (b'' if method == 'HEAD' else r.read()), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, b'', dict(e.headers)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last = e
    raise RuntimeError(f'{url}: {last}')


def parse_res_version(text):
    """"8.3.0|base26090301_8.4.0|base26092402" -> [("8.3.0", "base26090301"), ("8.4.0", "base26092402")]."""
    pairs = []
    for part in text.split('_'):
        if '|' in part:
            app, tag = part.split('|', 1)
            pairs.append((app, tag))
    return pairs


def version_key(v):
    return tuple(int(x) if x.isdigit() else 0 for x in v.split('.'))


def server_info(raw=None):
    """{"root": CDN root, "tags": [(app, tag)...], "tag": newest tag, "servers": N, "json": ...}"""
    if raw is None:
        status, raw, _ = http(server_url())
        if status != 200:
            raise RuntimeError(f'server list: HTTP {status}')
    data = json.loads(raw)
    tags = parse_res_version(data.get('res_version', ''))
    tag = os.environ.get('SSR_TAG') or (max(tags, key=lambda t: version_key(t[0]))[1] if tags else None)
    return {'root': data.get('android_res_url', ''), 'tags': tags, 'tag': tag,
            'servers': len(data.get('data', [])), 'app_version': data.get('version'), 'json': data}


def bundle_url(root, tag, name):
    """name = "role/hilda.fassets" (or already ending in .abws)."""
    if not name.endswith('.abws'):
        name += '.abws'
    return f'{root}{tag}/GameRes/{name}'


def manifest_hash(data):
    m = re.search(rb'AssetFileHash:\s*serializedVersion: \d+\s*Hash: ([0-9a-f]{32})', data)
    return m.group(1).decode() if m else None


def fetch_one(root, tag, name, outdir, force=False):
    """Downloads NAME.abws and NAME.manifest.abws into OUTDIR. Returns 'ok', 'skip' or 'missing'."""
    dest = os.path.join(outdir, name + '.abws')
    mdest = os.path.join(outdir, name + '.manifest.abws')
    status, mdata, _ = http(bundle_url(root, tag, name + '.manifest'))
    if status != 200:
        mdata = None  # a few bundles (the code patches) have no manifest on the CDN
    if mdata is not None and not force and os.path.exists(dest) and os.path.exists(mdest):
        with open(mdest, 'rb') as f:
            if manifest_hash(f.read()) == manifest_hash(mdata):
                return 'skip'
    if mdata is None and not force and os.path.exists(dest):
        return 'skip'
    status, data, _ = http(bundle_url(root, tag, name))
    if status != 200 or (data[:4] != abws.MAGIC and data[:7] != b'UnityFS'):
        return 'missing'  # the code patches come as raw UnityFS
    os.makedirs(os.path.dirname(dest) or '.', exist_ok=True)
    with open(dest + '.part', 'wb') as f:
        f.write(data)
    os.replace(dest + '.part', dest)
    if mdata is not None:
        with open(mdest, 'wb') as f:
            f.write(mdata)
    return 'ok'


def manifest_names(path):
    with open(path, 'rb') as f:
        data = f.read()
    if data[:4] == abws.MAGIC:
        data = data[abws.HEADER:]
    return list(abws.parse_manifest(data.decode('utf-8', 'replace')))


def sync(outdir, names, root, tag, workers=4, force=False):
    counts = {'ok': 0, 'skip': 0, 'missing': 0}
    missing = []

    def job(name):
        try:
            return name, fetch_one(root, tag, name, outdir, force)
        except RuntimeError as e:
            print(f'!! {name}: {e}', file=sys.stderr)
            return name, 'missing'

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (name, result) in enumerate(pool.map(job, names), 1):
            counts[result] += 1
            if result == 'missing':
                missing.append(name)
            if result == 'ok' or i % 50 == 0:
                print(f'[{i}/{len(names)}] {result:7s} {name}', flush=True)
    return counts, missing


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == 'server':
        info = server_info()
        print(f"root        {info['root']}")
        print(f"app version {info['app_version']}")
        for app, tag in info['tags']:
            print(f"tag         {app} -> {tag}")
        print(f"newest tag  {info['tag']}")
        print(f"servers     {info['servers']}")
        return 0
    if cmd == 'probe':
        info = server_info()
        for name in argv[1:]:
            status, _, h = http(bundle_url(info['root'], info['tag'], name), method='HEAD')
            print(f"{status} {h.get('Content-Length', '?'):>10}  {name}")
        return 0
    if cmd == 'fetch':
        info = server_info()
        counts, missing = sync(argv[1], argv[2:], info['root'], info['tag'])
        print(counts)
        return 1 if missing else 0
    if cmd == 'sync':
        outdir, manifest = argv[1], argv[2]
        only = None
        force = '--all' in argv
        workers = 4
        if '--only' in argv:
            only = argv[argv.index('--only') + 1]
        if '--workers' in argv:
            workers = int(argv[argv.index('--workers') + 1])
        names = manifest_names(manifest)
        if only:
            names = [n for n in names if n.startswith(only)]
        info = server_info()
        print(f"{len(names)} bundles from {info['root']}{info['tag']}/GameRes/ -> {outdir}")
        counts, missing = sync(outdir, names, info['root'], info['tag'], workers=workers, force=force)
        print(counts)
        if missing:
            with open(os.path.join(outdir, 'missing.txt'), 'w') as f:
                f.write('\n'.join(missing) + '\n')
            print(f"{len(missing)} not on the CDN, listed in {outdir}/missing.txt")
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
