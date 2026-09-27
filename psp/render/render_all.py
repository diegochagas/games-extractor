#!/usr/bin/env python3
"""Run several Blender processes over a job list (see blender_render.py).

usage: render_all.py JOBS.json OUT_DIR --blender /path/to/blender [--workers 2] [--size 1200]
                     [--samples 16] [--force]

Jobs that already have OUT_DIR/<id>/job.json are skipped unless --force is given.
RENDER_DEVICE=GPU in the environment makes Cycles use the graphics card.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv):
    pos, opts = [], {'workers': 2, 'size': 1200, 'samples': 16, 'blender': None, 'force': False}
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == '--force':
            opts['force'] = True
            i += 1
        elif a.startswith('--') and a[2:] in opts:
            opts[a[2:]] = argv[i + 1] if a == '--blender' else int(argv[i + 1])
            i += 2
        else:
            pos.append(a)
            i += 1
    if len(pos) != 2 or not opts['blender']:
        print(__doc__)
        return 2
    with open(pos[0], encoding='utf-8') as f:
        jobs = json.load(f)
    out = pos[1]
    todo = [j for j in jobs if opts['force'] or not os.path.exists(os.path.join(out, j['id'], 'job.json'))]
    print('%d jobs, %d to render' % (len(jobs), len(todo)))
    if not todo:
        return 0
    workers = max(1, min(opts['workers'], len(todo)))
    procs = []
    with tempfile.TemporaryDirectory() as tmp:
        for w in range(workers):
            part = os.path.join(tmp, 'jobs%d.json' % w)
            with open(part, 'w', encoding='utf-8') as f:
                json.dump(todo[w::workers], f)
            cmd = [opts['blender'], '-b', '--python', os.path.join(HERE, 'blender_render.py'), '--',
                   part, out, '--size', str(opts['size']), '--samples', str(opts['samples'])]
            if opts['force']:
                cmd.append('--force')
            procs.append(subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True))
        failed = 0
        for p in procs:
            for line in p.stdout:
                if line.startswith(('RENDERED', 'FAILED', 'done')):
                    print(line.rstrip(), flush=True)
                    failed += line.startswith('FAILED')
            p.wait()
    missing = [j['id'] for j in todo if not os.path.exists(os.path.join(out, j['id'], 'job.json'))]
    print('%d failed, %d without output' % (failed, len(missing)))
    for m in missing[:20]:
        print('  missing', m)
    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
