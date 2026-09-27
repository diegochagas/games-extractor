#!/usr/bin/env python3
"""Subtitles out of transcribe.py segments and their translation.

usage: subtitles.py srt SEGMENTS.json TRANSLATION.json OUT.srt
       subtitles.py mux VIDEO.mp4 SUBS.srt OUT.mp4 [--language por]

TRANSLATION.json is a list with one text per segment (null or "" = no subtitle for it).
`srt` fixes the usual timing slips of the recogniser: a first word that was heard long before
the rest of its sentence, and subtitles too short to read. `mux` adds the subtitles to an MP4 as
a text track (the picture and the sound are copied as they are).
"""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

MIN_SECONDS, CHARS_PER_SECOND, LINE = 1.2, 17.0, 42


def stamp(t):
    ms = int(round(t * 1000))
    return '%02d:%02d:%02d,%03d' % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def cues(segments, texts):
    out = []
    for seg, text in zip(segments, texts):
        if not text:
            continue
        start, end = seg['start'], seg['end']
        words = seg.get('words') or []
        if len(words) > 1 and words[1]['start'] - words[0]['end'] > 1.0:
            start = max(start, words[1]['start'] - 0.4)          # the sentence starts with the rest
        end = max(end, start + max(MIN_SECONDS, len(text) / CHARS_PER_SECOND))
        out.append([start, end, text])
    for a, b in zip(out, out[1:]):                               # never over the next subtitle
        a[1] = min(a[1], b[0] - 0.05)
    return out


def srt(items):
    rows = []
    for n, (start, end, text) in enumerate(items, 1):
        body = '\n'.join(textwrap.wrap(text, LINE)[:3])
        rows.append('%d\n%s --> %s\n%s\n' % (n, stamp(start), stamp(end), body))
    return '\n'.join(rows)


def main(argv):
    if len(argv) >= 5 and argv[1] == 'srt':
        segments = json.loads(Path(argv[2]).read_text(encoding='utf-8'))
        texts = json.loads(Path(argv[3]).read_text(encoding='utf-8'))
        if len(segments) != len(texts):
            print('%d segments but %d translations' % (len(segments), len(texts)))
            return 1
        items = cues(segments, texts)
        Path(argv[4]).write_text(srt(items), encoding='utf-8')
        print('%d subtitles -> %s' % (len(items), argv[4]))
        return 0
    if len(argv) >= 5 and argv[1] == 'mux':
        lang = argv[argv.index('--language') + 1] if '--language' in argv else 'por'
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', argv[2], '-i', argv[3], '-map', '0:v',
               '-map', '0:a?', '-map', '1:0', '-c:v', 'copy', '-c:a', 'copy', '-c:s', 'mov_text',
               '-metadata:s:s:0', 'language=' + lang, '-disposition:s:0', 'default', '-movflags', '+faststart',
               argv[4]]
        return subprocess.run(cmd).returncode
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
