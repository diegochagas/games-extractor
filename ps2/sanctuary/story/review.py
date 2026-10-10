#!/usr/bin/env python3
"""Proof-reading help: compares the two transcription passes of every voice (text/voices = plain
pass, text/voices2 = pass seeded with the names of the game) and lists the lines where they
disagree, with the scene and the speaker, so the right wording can be chosen and written into
fixes.json. Lines already in fixes.json are left out.

usage: review.py DUMP_DIR [--all]     (--all also prints the lines where both passes agree)
"""
import difflib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcript  # noqa: E402


def text_of(folder, stem, files):
    path = os.path.join(folder, files.get(stem.lower(), ''))
    if not files.get(stem.lower()) or not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return transcript.clean(' '.join(s['text'] for s in json.load(f)))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    dump = os.path.abspath(argv[1])
    text = os.path.join(dump, 'text')
    with open(os.path.join(text, 'story.json'), encoding='utf-8') as f:
        story = json.load(f)
    fixes = {}
    fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixes.json')
    if os.path.exists(fp):
        with open(fp, encoding='utf-8') as f:
            fixes = {k.lower() for k in json.load(f)}
    v1, v2 = os.path.join(text, 'voices'), os.path.join(text, 'voices2')
    f1 = {n.lower().replace('.pt.json', ''): n for n in os.listdir(v1)} if os.path.isdir(v1) else {}
    f2 = {n.lower().replace('.pt2.json', ''): n for n in os.listdir(v2)} if os.path.isdir(v2) else {}
    same = differ = 0
    for ch in story['chapters']:
        header = False
        for ln in (ch['scene'] or {'lines': []})['lines']:
            if not ln['voice']:
                continue
            stem = ln['voice'][:-4]
            if stem.lower() in fixes:
                continue
            a, b = text_of(v1, stem, f1), text_of(v2, stem, f2)
            if b is None:
                continue
            ratio = difflib.SequenceMatcher(None, (a or '').lower(), b.lower()).ratio()
            if ratio > 0.92 and '--all' not in argv:
                same += 1
                continue
            differ += ratio <= 0.92
            if not header:
                print('== %s: %s' % (ch['id'], ch['title']))
                header = True
            print('  %-24s %-14s A: %s' % (stem, ln['speaker'], a))
            print('  %-24s %-14s B: %s' % ('', '', b))
    print('agree: %d, differ: %d' % (same, differ))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
