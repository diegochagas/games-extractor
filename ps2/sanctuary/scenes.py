#!/usr/bin/env python3
"""The cutscene scripts of Saint Seiya: The Sanctuary (`demoNN.bin`, `ifNN.bin`, `PopeNN.bin`,
`*d.bin` = the manga digest versions): `SC`, u16 1, u16 count, then commands. A command is
`E1 <u16 id> <u16 layer>`, its values (`C1`/`C4` + int32, `C2` + two int32 = a fraction,
`C3` + a C string) and `EF`. All numbers are big endian. Ids used here: 0 loads a scene file
(`comic\\main\\NN\\NN_p_q.bin`), 6 ends it after N seconds, 15 names the text table (`msgDMNN`),
17 shows text line N at second t, 21 plays a voice file at second t, 24 a music, 19 the sound
effect bank, 7/8 draw a picture (sound-effect lettering, backgrounds).

usage: scenes.py dump AFS_DIR OUT_DIR    -> OUT_DIR/scenes.json
       scenes.py show FILE
"""
import json
import os
import re
import struct
import sys


def tokens(data):
    i, out = 6, []
    while i < len(data):
        b = data[i]
        if b in (0xC1, 0xC4):
            out.append(struct.unpack_from('>i', data, i + 1)[0])
            i += 5
        elif b == 0xC2:
            num, den = struct.unpack_from('>ii', data, i + 1)
            out.append(num / den if den else num)
            i += 9
        elif b == 0xC3:
            end = data.index(b'\0', i + 1)
            out.append(data[i + 1:end].decode('latin-1'))
            i = end + 1
        elif b == 0xE1:
            out.append(('CMD',) + struct.unpack_from('>HH', data, i + 1))
            i += 5
        elif b == 0xEF:
            out.append('END')
            i += 1
        elif b == 0xFF and i == len(data) - 1:
            break
        else:
            raise ValueError('unknown byte 0x%02x at 0x%x' % (b, i))
    return out


def commands(data):
    """[(id, layer, [values])]"""
    out, cur = [], None
    for t in tokens(data):
        if isinstance(t, tuple):
            cur = [t[1], t[2], []]
        elif t == 'END':
            if cur:
                out.append(tuple(cur))
            cur = None
        elif cur is not None:
            cur[2].append(t)
    return out


def parse(name, data):
    scene = {'script': name, 'kind': kind_of(name), 'pages': [], 'text_table': None, 'bgm': [], 'sfx_bank': None,
             'pictures': [], 'lines': []}
    group = 0                                   # the timeline after the page list: one group per page, closed by command 37
    for cid, _layer, vals in commands(data):
        pages = scene['pages']
        if cid == 0 and len(vals) >= 2:
            pages.append({'index': vals[0], 'file': os.path.basename(vals[1].replace('\\', '/')), 'seconds': None,
                          'lines': [], 'voices': []})
        elif cid == 6 and pages and len(vals) >= 2:
            pages[-1]['seconds'] = vals[1]
        elif cid == 15 and vals:
            scene['text_table'] = os.path.basename(vals[0].replace('\\', '/'))
        elif cid == 17 and len(vals) >= 2 and group < len(pages):
            pages[group]['lines'].append({'t': vals[0], 'line': int(vals[1])})
        elif cid == 21 and len(vals) >= 2 and group < len(pages):
            pages[group]['voices'].append({'t': vals[0], 'file': os.path.basename(vals[1].replace('\\', '/'))})
        elif cid == 37:
            group += 1
        elif cid == 24 and len(vals) >= 2:
            scene['bgm'].append(os.path.basename(vals[1].replace('\\', '/')))
        elif cid == 19 and vals:
            scene['sfx_bank'] = os.path.basename(vals[0].replace('\\', '/'))
        elif cid in (7, 29) and len(vals) >= 2 and isinstance(vals[1], str):
            scene['pictures'].append(os.path.basename(vals[1].replace('\\', '/')))
    # the dialogue: one entry per voice, with the text lines shown while it plays (the next voice ends it)
    lines = []
    for p in scene['pages']:
        events = sorted([(v['t'], 0, v['file']) for v in p['voices']] + [(ln['t'], 1, ln['line']) for ln in p['lines']])
        cur = None
        for t, kind, val in events:
            if kind == 0:
                cur = {'page': p['index'], 'page_file': p['file'], 't': t, 'voice': val, 'text_lines': []}
                lines.append(cur)
            elif cur is not None and cur['page'] == p['index']:
                cur['text_lines'].append(val)
            else:
                lines.append({'page': p['index'], 'page_file': p['file'], 't': t, 'voice': None, 'text_lines': [val]})
    scene['lines'] = lines
    return scene


def kind_of(name):
    low = name.lower()
    if low.startswith('demo'):
        return 'digest' if low.endswith('d.bin') else 'story'
    if low.startswith('if'):
        return 'if-digest' if low.endswith('d.bin') else 'if'
    if low.startswith('pope'):
        return 'pope'
    return 'other'


def main(argv):
    if len(argv) == 3 and argv[1] == 'show':
        with open(argv[2], 'rb') as f:
            data = f.read()
        for cid, layer, vals in commands(data):
            print('%3d %3d  %s' % (cid, layer, vals))
        return 0
    if len(argv) == 4 and argv[1] == 'dump':
        src, out = argv[2], argv[3]
        os.makedirs(out, exist_ok=True)
        scenes = []
        for name in sorted(os.listdir(src)):
            path = os.path.join(src, name)
            if not os.path.isfile(path) or not name.lower().endswith('.bin'):
                continue
            with open(path, 'rb') as f:
                head = f.read(4)
                if head[:2] != b'SC':
                    continue
                data = head + f.read()
            try:
                scenes.append(parse(name, data))
            except ValueError as e:
                print('!! %s: %s' % (name, e))
        with open(os.path.join(out, 'scenes.json'), 'w', encoding='utf-8') as f:
            json.dump(scenes, f, ensure_ascii=False, indent=1)
        print('%d scripts, %d pages, %d voices, %d text-only entries -> %s' % (
            len(scenes), sum(len(s['pages']) for s in scenes),
            sum(1 for s in scenes for ln in s['lines'] if ln['voice']),
            sum(1 for s in scenes for ln in s['lines'] if not ln['voice']), out))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
