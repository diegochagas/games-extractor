#!/usr/bin/env python3
"""Story dump of Saint Seiya Omega Ultimate Cosmo: every event script with its title, resources
and dialogue lines (speaker, voice file, Japanese text).

The event scripts (`event/script/NN_MM.pac` = `NN_MM.E` bytecode + `NN_MM_JP.BTX` text) are a
stack machine; a dialogue line is `push line id, push character number, call`, which is all that
is read here (characters 0-23 are the playable ones, 24 Athena, 25 "???", 26 "man"). The string table after "ACT1" holds the title and the files the scene loads.
Chapters 50-56 are the seven story modes (scenes 01-08 before each battle, 11-18 after it);
00-23 are one placeholder set per playable character.

usage: story_dump.py FILES_DIR ISO_USRDIR OUT_DIR      -> OUT_DIR/story.json
"""
import json
import os
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import btx  # noqa: E402
from omega import names  # noqa: E402

LINE = re.compile(rb'\x03(.{4})\x87\x01(.)\x87\x83\x00\x00\x00\x00\x8e', re.S)
STORY_OF = {50: 'kog', 51: 'yun', 52: 'ryo', 53: 'som', 54: 'ede', 55: 'hat', 56: 'sey'}


def script_strings(data):
    i = data.find(b'ACT1\0')
    out = []
    if i < 0:
        return out
    for s in data[i + 5:].split(b'\0'):
        if not s:
            continue
        try:
            t = s.decode('shift_jis')
        except UnicodeDecodeError:
            break
        out.append(t.strip())
        if t.startswith('■'):                     # closing title
            break
    return out


def voices(usrdir):
    out = {}
    root = os.path.join(usrdir, 'event', 'sound')
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d)
        if not os.path.isdir(p):
            continue
        for n in os.listdir(p):
            m = re.match(r'(\d+)_(\d+)_(\w+)\.ahx$', n)
            if m:
                out[(int(d), int(m.group(1)) * 100000 + int(m.group(2)))] = (m.group(3), 'event/sound/%s/%s' % (d, n))
    return out


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    files, usrdir, out = argv[1:4]
    voice = voices(usrdir)
    root = os.path.join(files, 'event', 'script')
    scripts = []
    used = set()
    for pac in sorted(os.listdir(root)):
        m = re.match(r'(\d+)_(\d+)\.pac$', pac)
        if not m:
            continue
        chapter, scene = int(m.group(1)), int(m.group(2))
        folder = os.path.join(root, pac)
        stem = pac[:-4]
        by_name = {n.lower(): n for n in os.listdir(folder)}
        e = by_name.get(stem + '.e')
        b = by_name.get(stem + '_jp.btx')
        if not e:
            continue
        data = Path(os.path.join(folder, e)).read_bytes()
        strings = script_strings(data)
        title = strings[0].lstrip('□').strip() if strings else ''
        resources = [s for s in strings[1:] if not s.startswith(('□', '■'))]
        code_end = data.find(b'ACT1\0')
        order = [(struct.unpack('<I', a)[0], b2[0]) for a, b2 in LINE.findall(data[:code_end])]
        text = dict(btx.read(Path(os.path.join(folder, b)).read_bytes())) if b else {}
        lines = []
        seen = set()
        for lid, who in order:
            if lid in seen or lid not in text:
                continue
            seen.add(lid)
            v = voice.get((chapter, lid))
            if v:
                used.add((chapter, lid))
            # the script's character is the name the text box shows ("???" and "man" hide who
            # speaks; the voice file tells); a few voice files carry another character's code
            code = names.SCRIPT_CODES[who] if who < len(names.SCRIPT_CODES) else (v[0] if v else '')
            jp, romaji = names.speaker(code) if code else ('', '')
            row = {'id': lid, 'speaker_code': code, 'speaker_jp': jp, 'speaker': romaji,
                   'character_number': who, 'voice': v[1] if v else None, 'jp': text[lid]}
            if v and code in ('who', 'man') and v[0] not in ('who', 'man'):
                row['identity_code'] = v[0]
                row['identity'] = names.speaker(v[0])[1]
            lines.append(row)
        unreferenced = [{'id': k, 'jp': t} for k, t in text.items() if k not in seen and t.strip()]
        for u in unreferenced:
            v = voice.get((chapter, u['id']))
            if v:
                u['speaker_code'], u['voice'] = v
                u['speaker_jp'], u['speaker'] = names.speaker(v[0])
                used.add((chapter, u['id']))
        kind = 'story' if chapter >= 50 else 'placeholder'
        phase = 'branch' if scene == 0 else 'before' if scene < 10 else 'after'
        opponent = re.search(r'VS(.+?)\(', title)
        scripts.append({
            'script': stem, 'chapter': chapter, 'scene': scene, 'kind': kind, 'phase': phase,
            'story_of': STORY_OF.get(chapter), 'title_jp': title,
            'opponent_jp': opponent.group(1) if opponent else None,
            'backgrounds': [r for r in resources if r.startswith('common/background/') and 'map_bg' not in r],
            'stills': [r for r in resources if r.startswith('common/image/still')],
            'items': [r for r in resources if r.startswith('common/item/')],
            'bustups': [r for r in resources if r.startswith('common/bustup/')],
            'bgm': [r for r in resources if r.startswith('bgm/')],
            'movies': [r for r in resources if r.startswith('movie/')],
            'lines': lines, 'unreferenced': unreferenced})
    unused_voices = sorted('%s' % v[1] for k, v in voice.items() if k not in used)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, 'story.json'), 'w', encoding='utf-8') as f:
        json.dump({'scripts': scripts, 'voices_without_text': unused_voices}, f, ensure_ascii=False, indent=1)
    story = [s for s in scripts if s['kind'] == 'story']
    print('%d scripts (%d story scenes), %d lines (%d story), %d unreferenced strings, %d voices without text'
          % (len(scripts), len(story), sum(len(s['lines']) for s in scripts),
             sum(len(s['lines']) for s in story), sum(len(s['unreferenced']) for s in scripts),
             len(unused_voices)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
