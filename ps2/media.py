#!/usr/bin/env python3
"""Sound and movies of the game: CRI ADX (`.adx`) and Sofdec (`.sfd`, MPEG-1 video + ADX audio),
both decoded by ffmpeg.

usage: media.py audio SRC_DIR OUT_DIR [--workers N]    every .adx -> OUT_DIR/<name>.ogg (Vorbis q5)
       media.py video SRC_DIR OUT_DIR                  every .sfd -> OUT_DIR/<name>.mp4 (H.264 + AAC)
Files already converted are skipped.
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor


def run(args):
    return subprocess.run(['ffmpeg', '-v', 'error', '-y', '-nostdin'] + args, check=False).returncode


def audio(src, out, workers=4):
    os.makedirs(out, exist_ok=True)
    jobs = []
    for name in sorted(os.listdir(src)):
        if name.lower().endswith('.adx'):
            dest = os.path.join(out, name[:-4] + '.ogg')
            if not os.path.exists(dest):
                jobs.append((os.path.join(src, name), dest))
    with ThreadPoolExecutor(workers) as pool:
        codes = list(pool.map(lambda j: run(['-i', j[0], '-c:a', 'libvorbis', '-q:a', '5', j[1]]), jobs))
    bad = [j[0] for j, c in zip(jobs, codes) if c]
    print('%d files converted, %d failed -> %s' % (len(jobs) - len(bad), len(bad), out))
    for b in bad:
        print('!! ' + b)
    return 0


def video(src, out):
    os.makedirs(out, exist_ok=True)
    n = 0
    for name in sorted(os.listdir(src)):
        if name.lower().endswith('.sfd'):
            dest = os.path.join(out, name[:-4].lower() + '.mp4')
            if os.path.exists(dest):
                continue
            if run(['-i', os.path.join(src, name), '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
                    '-vf', 'setsar=1', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', dest]):
                print('!! ' + name)
            else:
                n += 1
    print('%d movies -> %s' % (n, out))
    return 0


def main(argv):
    if len(argv) >= 4 and argv[1] == 'audio':
        workers = int(argv[argv.index('--workers') + 1]) if '--workers' in argv else 4
        return audio(argv[2], argv[3], workers)
    if len(argv) == 4 and argv[1] == 'video':
        return video(argv[2], argv[3])
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
