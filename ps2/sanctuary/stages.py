#!/usr/bin/env python3
"""Exports every stage (arena) of the game to .glb and writes the Blender render job list.

usage: stages.py AFS_DIR DUMP_DIR [--names hades]  -> DUMP_DIR/models/stages/<id>.glb,
                                          DUMP_DIR/text/stages.json, DUMP_DIR/text/stage_render_jobs.json
A stage is every `<id>.gli` of the disc (see ps2/stage.py). Two render jobs per stage: `stages/<id>`
is the arena alone (sky, far scenery and fire billboards hidden) and `stages/<id>_completo` adds the far
scenery. The Portuguese names come from STAGES in the game's names.py.
"""
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import stage  # noqa: E402


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    if '--names' in argv:
        import importlib
        names = importlib.import_module(argv[argv.index('--names') + 1] + '.names')
    else:
        from sanctuary import names
    afs, dump = os.path.abspath(argv[1]), os.path.abspath(argv[2])
    out = os.path.join(dump, 'models', 'stages')
    os.makedirs(out, exist_ok=True)
    stages, jobs = [], []
    for name in sorted(os.listdir(afs)):
        if not name.endswith('.gli'):
            continue
        ident = name[:-4]
        try:
            st = stage.load(afs, ident)
        except (ValueError, struct.error, OSError) as e:
            print('!! %s: %s' % (name, e))
            continue
        pngs = stage.texture_pngs(os.path.join(dump, 'images', ident + '_tex.bin'))
        path = os.path.join(out, ident + '.glb')
        with open(path, 'wb') as f:
            f.write(stage.to_glb(st, pngs))
        info = st['list']
        label = getattr(names, 'STAGES', {}).get(ident, 'Cenário %s' % ident)
        stages.append({'id': 'stages/' + ident, 'file': name, 'name': label, 'slug': names.slug(label),
                       'grid': [info['columns'], info['rows']], 'tiles': len(st['tiles']), 'objects': len(st['objects']),
                       'specials': len(st['specials']), 'effects': [r['name'] for r in info['effects']],
                       'far': bool(st['far']), 'sky': bool(st['sky']), 'textures': len(pngs),
                       'triangles': sum(len(p['faces']) for _c, m in st['tiles'] for p in m['parts']),
                       'glb': os.path.relpath(path, dump)})
        jobs.append({'id': 'stages/' + ident, 'glb': path, 'views': ['aerial', 'top', 'front'], 'hide': ['sky', 'spe', 'far']})
        if st['far']:
            jobs.append({'id': 'stages/%s_completo' % ident, 'glb': path, 'views': ['aerial', 'top'], 'hide': ['sky', 'spe']})
    os.makedirs(os.path.join(dump, 'text'), exist_ok=True)
    with open(os.path.join(dump, 'text', 'stages.json'), 'w', encoding='utf-8') as f:
        json.dump(stages, f, ensure_ascii=False, indent=1)
    with open(os.path.join(dump, 'text', 'stage_render_jobs.json'), 'w', encoding='utf-8') as f:
        json.dump(jobs, f, ensure_ascii=False, indent=1)
    print('%d stages -> %s, %d render jobs' % (len(stages), out, len(jobs)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
