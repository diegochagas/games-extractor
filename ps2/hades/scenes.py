#!/usr/bin/env python3
"""The story scripts of Saint Seiya: The Hades: `story_NNNN_<lang>.gsb` (the same SC command
language as The Sanctuary, see ../sanctuary/scenes.py) with the text in `story_NNNN_<lang>.bin`
(one text block per language file). Command 15 names the text table, 17 `[0, line, -1, '.']`
shows a text line, 62 `[voice file, slot]` plays the voice of that line (the speaker is the
number in the voice file name), 21 plays a voice at a second of the page, 63 puts a character
model in a slot, 58/24 the music, 0 loads a scene page. `story_NNNN_MM_<lang>.gsb` are the
sub-scripts of a chapter (its battle scenes).

usage: scenes.py dump AFS_DIR OUT_DIR [--lang uk]   -> OUT_DIR/scenes.json
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import msg  # noqa: E402
from sanctuary import scenes as sc  # noqa: E402

TEXT_LANGS = ['uk', 'jp', 'fr', 'it', 'sp']


def parse(name, data, texts):
    chapter = re.match(r'(?i)story_(\w+?)(?:_(\d\d))?_(\w\w)\.gsb$', name)
    scene = {'script': name, 'chapter': chapter.group(1) if chapter else name, 'part': chapter.group(2) if chapter else None,
             'pages': [], 'text_table': None, 'bgm': [], 'cast': {}, 'lines': []}
    page = None
    last_text = None            # the last text line shown (a voice command 62 that follows belongs to it)
    pending_voice = None        # a timeline voice (command 21) waiting for the text shown at the same second
    for cid, _layer, vals in sc.commands(data):
        if cid == 0 and len(vals) >= 2:
            page = {'index': vals[0], 'file': os.path.basename(vals[1].replace('\\', '/'))}
            scene['pages'].append(page)
        elif cid == 15 and vals:
            scene['text_table'] = os.path.basename(vals[0].replace('\\', '/'))
        elif cid == 63 and len(vals) >= 2:
            scene['cast'][str(vals[0])] = vals[1]
        elif cid in (24, 58) and vals and isinstance(vals[-3] if cid == 58 else vals[1], str):
            scene['bgm'].append(os.path.basename((vals[0] if cid == 58 else vals[1]).replace('\\', '/')))
        elif cid == 17 and len(vals) >= 2 and not (len(vals) >= 4 and isinstance(vals[3], str) and vals[3] != '.'):
            t = vals[0] if isinstance(vals[0], (int, float)) else 0
            last_text = {'line': int(vals[1]), 'page': page['index'] if page else None, 'voice': None, 't': t}
            if pending_voice and abs(pending_voice[0] - t) < 0.05:
                last_text['voice'] = pending_voice[1]
                pending_voice = None
            scene['lines'].append(last_text)
        elif cid == 62 and vals and isinstance(vals[0], str):
            voice = os.path.basename(vals[0].replace('\\', '/'))
            if last_text is not None and last_text['voice'] is None:
                last_text['voice'] = voice
            else:
                scene['lines'].append({'line': None, 'page': page['index'] if page else None, 'voice': voice, 't': None})
        elif cid == 21 and len(vals) >= 2 and isinstance(vals[1], str):
            voice = os.path.basename(vals[1].replace('\\', '/'))
            t = vals[0]
            if last_text is not None and last_text['voice'] is None and abs((last_text['t'] or 0) - t) < 0.05:
                last_text['voice'] = voice
            else:
                if pending_voice:
                    scene['lines'].append({'line': None, 'page': page['index'] if page else None, 'voice': pending_voice[1], 't': pending_voice[0]})
                pending_voice = (t, voice)
    if pending_voice:
        scene['lines'].append({'line': None, 'page': page['index'] if page else None, 'voice': pending_voice[1], 't': pending_voice[0]})
    table = texts.get((scene['chapter'], scene['part']))
    for ln in scene['lines']:
        if ln['line'] is not None and table:
            for lang, strings in table.items():
                if ln['line'] < len(strings):
                    ln['text_' + lang] = strings[ln['line']]
    return scene


def main(argv):
    if len(argv) < 4 or argv[1] != 'dump':
        print(__doc__)
        return 2
    src, out = argv[2], argv[3]
    lang = argv[argv.index('--lang') + 1] if '--lang' in argv else 'uk'
    os.makedirs(out, exist_ok=True)
    texts = {}
    for name in sorted(os.listdir(src)):
        m = re.match(r'(?i)story_(\w+?)(?:_(\d\d))?_(\w\w)\.bin$', name)
        if m and m.group(3) in TEXT_LANGS:
            with open(os.path.join(src, name), 'rb') as f:
                table = msg.read(f.read(), 'jp')
            strings = table.get('jp') or next(iter(table.values()), [])
            texts.setdefault((m.group(1), m.group(2)), {})[m.group(3)] = strings
    scenes = []
    for name in sorted(os.listdir(src)):
        if not re.match(r'(?i)story_\w+_%s\.gsb$' % lang, name):
            continue
        with open(os.path.join(src, name), 'rb') as f:
            data = f.read()
        try:
            scenes.append(parse(name, data, texts))
        except ValueError as e:
            print('!! %s: %s' % (name, e))
    with open(os.path.join(out, 'scenes.json'), 'w', encoding='utf-8') as f:
        json.dump(scenes, f, ensure_ascii=False, indent=1)
    n = sum(len(s['lines']) for s in scenes)
    print('%d scripts, %d lines (%d with text, %d with a voice) -> %s' % (
        len(scenes), n, sum(1 for s in scenes for ln in s['lines'] if ln['line'] is not None),
        sum(1 for s in scenes for ln in s['lines'] if ln['voice']), out))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
