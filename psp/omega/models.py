#!/usr/bin/env python3
"""Every 3D model of Saint Seiya Omega Ultimate Cosmo -> .glb, plus the render job list.

Characters (`scene/battle/character/<code>.pac`): NORMAL.GMO (whole cloth) and BROKEN.GMO
(destroyed cloth), drawn with the textures of `<code>_<colour>.pac` (00 = player 1 colours,
01 = player 2 colours; NORMAL.PAC, HALF.PAC = damaged cloth on the normal model, BROKEN.PAC).
The APPENDAGE_NORMAL/BROKEN packs (capes, hair, wings, weapons: LOC_<n>.GMO) hang from locator
<n>, which NORMAL.ATP / BROKEN.ATP place on a bone. All the motions of the character go into `<code>_00_normal.glb`.
Stages (`scene/battle/map/<stage>.pac`): MAP_MODEL.GMO and the breakable STR_TYPEn.GMO objects,
textures inside the GMO. `common/globalobject.pac`: the three "big bang" backgrounds.

usage: models.py FILES_DIR OUT_DIR [--workers N]    -> OUT_DIR/models/**.glb, OUT_DIR/text/models.json,
                                                       OUT_DIR/text/render_jobs.json
"""
import json
import os
import sys
from pathlib import Path
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gmo  # noqa: E402
import gmo2glb  # noqa: E402
from omega import names  # noqa: E402

VARIANTS = [('normal', 'NORMAL.GMO', 'NORMAL.PAC', 'APPENDAGE_NORMAL.PAC'),
            ('half', 'NORMAL.GMO', 'HALF.PAC', 'APPENDAGE_NORMAL.PAC'),
            ('broken', 'BROKEN.GMO', 'BROKEN.PAC', 'APPENDAGE_BROKEN.PAC')]
SKY = ['sky', 'TR_sky', 'TR_cloud', 'TR_mountain', 'TR_fog', 'TR_far', 'TR_ray', 'TR_light', 'TR_glow',
       'TR_moon', 'TR_treefar', 'TR_drop_light', 'light2']


def attach_points(path):
    """ATP file ("PADH" > "CLKC" > "CLDH"): locator number -> bone index and placement."""
    import struct
    d = Path(path).read_bytes()
    p = d.find(b'CLDH')
    out = {}
    if d[:4] != b'PADH' or p < 0:
        return out
    count = struct.unpack_from('<I', d, p + 8)[0]
    for i in range(count):
        q = p + 12 + i * 44
        if q + 44 > len(d):
            break
        f = struct.unpack_from('<9f', d, q)
        bone, loc = struct.unpack_from('<II', d, q + 36)
        out[loc] = {'bone': bone, 'translation': f[0:3], 'rotation': gmo.euler_quat(f[3], f[4], f[5], 'zyx'),
                    'scale': f[6:9]}
    return out


def find(folder, name):
    for n in os.listdir(folder):
        if n.lower() == name.lower():
            return os.path.join(folder, n)
    return None


def plan(files, out):
    jobs = []
    chars = os.path.join(files, 'scene', 'battle', 'character')
    for code in names.CODES:
        base = os.path.join(chars, code + '.pac')
        if not os.path.isdir(base):
            continue
        motions = sorted(os.path.join(base, n) for n in os.listdir(base)
                         if n.lower().endswith('.gmo') and n.upper() not in ('NORMAL.GMO', 'BROKEN.GMO'))
        for colour in ('00', '01'):
            for variant, model, tex, extra in VARIANTS:
                src = find(base, model)
                attach = []
                extra = find(base, extra)
                atp = find(base, model[:-4] + '.ATP')
                points = attach_points(atp) if atp else {}
                if extra and os.path.isdir(extra):
                    for n in sorted(os.listdir(extra)):        # LOC_210_2.GMO hangs from locator 210
                        parts = n[:-4].split('_')
                        if n.lower().endswith('.gmo') and parts[0].upper() == 'LOC' and parts[1].isdigit():
                            point = points.get(int(parts[1]))
                            if point:
                                attach.append(dict(point, file=os.path.join(extra, n)))
                            else:
                                attach.append({'file': os.path.join(extra, n), 'bone': 'loc_' + parts[1]})
                texdir = os.path.join(chars, '%s_%s.pac' % (code, colour))
                texdir = find(texdir, tex) if os.path.isdir(texdir) else None
                if not src or not texdir:
                    continue
                ident = 'characters/%s/%s_%s_%s' % (code, code, colour, variant)
                first = colour == '00' and variant == 'normal'
                jobs.append({'id': ident, 'kind': 'character', 'code': code, 'colour': colour, 'variant': variant,
                             'source': src, 'textures': [texdir], 'motions': motions if first else [],
                             'attachments': attach,
                             'glb': os.path.join(out, 'models', ident + '.glb')})
    maps = os.path.join(files, 'scene', 'battle', 'map')
    for stage in sorted(os.listdir(maps)):
        folder = os.path.join(maps, stage)
        for n in sorted(os.listdir(folder)):
            if n.lower().endswith('.gmo'):
                ident = 'stages/%s/%s' % (stage[:-4], n[:-4].lower())
                jobs.append({'id': ident, 'kind': 'stage' if n.upper().startswith('MAP') else 'stage_object',
                             'stage': stage[:-4], 'source': os.path.join(folder, n), 'textures': [folder],
                             'motions': [], 'glb': os.path.join(out, 'models', ident + '.glb')})
    glob = os.path.join(files, 'common', 'globalobject.pac')
    for n in sorted(os.listdir(glob)):
        if n.lower().endswith('.gmo'):
            ident = 'backgrounds/%s' % n[:-4].lower()
            jobs.append({'id': ident, 'kind': 'background', 'source': os.path.join(glob, n), 'textures': [glob],
                         'motions': [], 'glb': os.path.join(out, 'models', ident + '.glb')})
    return jobs


def run(job):
    try:
        rep = gmo2glb.convert(job['source'], job['glb'], job['textures'], job['motions'],
                              job.get('attachments', ()))
        return job['id'], rep, None
    except Exception as e:                                       # reported at the end
        return job['id'], None, '%s: %s' % (type(e).__name__, e)


def render_jobs(jobs):
    out = []
    for j in jobs:
        if j['kind'] == 'character':
            out.append({'id': j['id'], 'glb': j['glb'], 'views': ['front', 'side', 'back']})
            if j['motions']:
                out.append({'id': j['id'].replace('_00_normal', '_pose_idle'), 'glb': j['glb'],
                            'views': ['front', 'three_quarter'], 'pose': {'animation': 'idle_001', 'frame': 0}})
                out.append({'id': j['id'].replace('_00_normal', '_pose_win'), 'glb': j['glb'],
                            'views': ['front'], 'pose': {'animation': 'win_001', 'frame': 9999}})
        elif j['kind'] == 'stage':
            out.append({'id': j['id'], 'glb': j['glb'], 'views': ['three_quarter', 'top'], 'hide': SKY,
                        'cull': True})
            out.append({'id': j['id'] + '_sky', 'glb': j['glb'], 'views': ['front'], 'cull': True})
        else:
            out.append({'id': j['id'], 'glb': j['glb'], 'views': ['front', 'three_quarter'],
                        'cull': j['kind'] == 'background'})
    return out


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    files, out = argv[1], os.path.abspath(argv[2])
    workers = int(argv[argv.index('--workers') + 1]) if '--workers' in argv else os.cpu_count()
    jobs = plan(files, out)
    failed = []
    reports = {}
    with Pool(workers) as pool:
        for ident, rep, err in pool.imap_unordered(run, jobs):
            if err:
                failed.append((ident, err))
            else:
                reports[ident] = rep
    good = [j for j in jobs if j['id'] in reports]
    for j in good:
        j.update({k: reports[j['id']][k] for k in ('bones', 'vertices', 'triangles', 'animations',
                                                   'missing_textures')})
        j['attachments'] = reports[j['id']]['attachments']
        j['motions'] = [os.path.basename(m) for m in j['motions']]
    os.makedirs(os.path.join(out, 'text'), exist_ok=True)
    Path(os.path.join(out, 'text', 'models.json')).write_text(json.dumps(good, ensure_ascii=False, indent=1), encoding='utf-8')
    Path(os.path.join(out, 'text', 'render_jobs.json')).write_text(json.dumps(render_jobs(good), ensure_ascii=False, indent=1), encoding='utf-8')
    for ident, err in failed:
        print('FAILED', ident, err)
    missing = sum(len(j['missing_textures']) for j in good)
    print('%d models, %d failed, %d triangles, %d animations, %d missing textures'
          % (len(good), len(failed), sum(j['triangles'] for j in good),
             sum(j['animations'] for j in good), missing))
    for j in good:
        if j['missing_textures']:
            print('  missing textures in', j['id'], j['missing_textures'][:5])
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
