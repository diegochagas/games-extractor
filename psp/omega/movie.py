#!/usr/bin/env python3
"""Movies of the game with the Portuguese subtitles drawn in the picture.

usage: movie.py ORIGINAL.pmf SUBTITLES.srt OUT.pmf [--font "DejaVu Sans"] [--size 15]

Only the groups of pictures that show a subtitle are encoded again (libx264, the settings of the
original stream: Main profile, level 2.1, one reference picture, no B pictures); every other
picture, the sound and the layout of the file are the original ones. Each new group is encoded
to the size of the group it replaces, so the file keeps its size and its place on the disc.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psmf  # noqa: E402

WIDTH, HEIGHT, RATE = 480, 272, '30000/1001'
FRAME_BYTES = WIDTH * HEIGHT * 3 // 2
X264 = ('ref=1:bframes=0:aud=1:nal-hrd=vbr:vbv-maxrate=4000:vbv-bufsize=2000:keyint=infinite:min-keyint=1:'
        'scenecut=0:weightp=0:8x8dct=0:slices=1:force-cfr=1:repeat-headers=1')


def cues(srt):
    out = []
    for a, b in re.findall(r'(\d+:\d+:\d+,\d+) --> (\d+:\d+:\d+,\d+)', srt):
        def secs(t):
            h, m, s = t.replace(',', '.').split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
        out.append((secs(a), secs(b)))
    return out


def encode(frames, crf):
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'yuv420p',
           '-s', '%dx%d' % (WIDTH, HEIGHT), '-r', RATE, '-i', 'pipe:0', '-c:v', 'libx264', '-preset', 'slow',
           '-profile:v', 'main', '-level', '2.1', '-crf', '%.2f' % crf, '-x264-params', X264,
           '-pix_fmt', 'yuv420p', '-f', 'h264', 'pipe:1']
    return subprocess.run(cmd, input=frames, stdout=subprocess.PIPE, check=True).stdout


def fit(frames, room):
    """The best encoding of the frames that is not larger than `room` bytes."""
    low, high = 12.0, 45.0
    best = None
    first = encode(frames, 20.0)
    if len(first) <= room:
        best, high = first, 20.0
    else:
        low = 20.0
    for _ in range(7):
        mid = (low + high) / 2
        got = encode(frames, mid)
        if len(got) <= room:
            best, high = got, mid
        else:
            low = mid
    if best is None:
        best = encode(frames, 51)
        if len(best) > room:
            raise ValueError('a group of %d pictures does not fit %d bytes' % (len(frames) // FRAME_BYTES, room))
    return best


def main(argv):
    pos, opts = [], {'--font': 'DejaVu Sans', '--size': '15'}
    i = 1
    while i < len(argv):
        if argv[i] in opts:
            opts[argv[i]] = argv[i + 1]
            i += 2
        else:
            pos.append(argv[i])
            i += 1
    if len(pos) != 3:
        print(__doc__)
        return 2
    source, srt, out = pos
    data = Path(source).read_bytes()
    movie = psmf.Movie(data)
    shown = cues(Path(srt).read_text(encoding='utf-8'))
    es = bytes(movie.es)
    ends = movie.units[1:] + [len(es)]
    fps = 30000 / 1001
    with tempfile.TemporaryDirectory() as tmp:
        raw = os.path.join(tmp, 'frames.yuv')
        text = os.path.join(tmp, 'subs.srt')
        Path(text).write_text(Path(srt).read_text(encoding='utf-8'), encoding='utf-8')
        style = ('FontName=%s,FontSize=%s,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,'
                 'BorderStyle=1,Outline=1.6,Shadow=0.6,MarginV=14,MarginL=24,MarginR=24' % (opts['--font'], opts['--size']))
        vf = "setpts=PTS-STARTPTS,subtitles=%s:force_style='%s'" % (text.replace(':', r'\:'), style)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', source, '-an', '-vf', vf,
                        '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'yuv420p', raw], check=True)
        total = os.path.getsize(raw) // FRAME_BYTES
        if total != len(movie.units):
            raise ValueError('%d pictures decoded, the movie has %d' % (total, len(movie.units)))
        new = bytearray()
        again = 0
        with open(raw, 'rb') as f:
            for grp in movie.groups:
                first, count = grp['first'], grp['count']
                t0, t1 = first / fps, (first + count) / fps
                old = es[movie.units[first]:ends[first + count - 1]]
                if any(a < t1 and b > t0 for a, b in shown):
                    f.seek(first * FRAME_BYTES)
                    got = fit(f.read(count * FRAME_BYTES), int(min(grp['room'], len(old) + 4096) * 0.985))
                    if len(psmf.units(got)) != count:
                        raise ValueError('group at picture %d: %d pictures encoded, %d expected'
                                         % (first, len(psmf.units(got)), count))
                    new += got
                    again += 1
                else:
                    new += old
        result = psmf.replace_video(data, bytes(new))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    Path(out).write_bytes(result)
    print('%s: %d of %d groups encoded again, %d subtitles, %d bytes (the original has %d)'
          % (os.path.basename(out), again, len(movie.groups), len(shown), len(result), len(data)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
