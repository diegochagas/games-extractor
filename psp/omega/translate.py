#!/usr/bin/env python3
"""JP -> pt-BR translation workflow for the story dump.

usage: translate.py export DUMP     text/story.json + text/all_text.json -> text/translation/in/*.json
       translate.py check DUMP      verify text/translation/out/*.json against the chunks
       translate.py merge DUMP      -> text/translation/pt-BR.json (key -> text)

Keys: `<script>:<line id>` for dialogue, `<script>:title` for a scene, `<btx path>#<id>` for
every other string. The translation itself is done by hand or by agents following
docs/TRANSLATE_INSTRUCTIONS.md.
"""
import json
import os
import re
import sys
from pathlib import Path

JAPANESE = re.compile(r'[ぁ-ゖァ-ヺ一-鿿]')
CHAPTERS = {50: 'kouga', 51: 'yuna', 52: 'ryuho', 53: 'souma', 54: 'eden', 55: 'haruto', 56: 'seiya'}


def chunks(dump):
    story = json.loads(Path(os.path.join(dump, 'text', 'story.json')).read_text(encoding='utf-8'))
    everything = json.loads(Path(os.path.join(dump, 'text', 'all_text.json')).read_text(encoding='utf-8'))
    out = {}
    covered = set()
    for s in story['scripts']:
        name = 'story_%d_%s' % (s['chapter'], CHAPTERS[s['chapter']]) if s['kind'] == 'story' else 'placeholders'
        rows = out.setdefault(name, [])
        if not s['lines'] and not s['unreferenced']:
            continue
        rows.append({'key': '%s:title' % s['script'], 'speaker': 'scene', 'jp': s['title_jp']})
        for l in s['lines']:
            rows.append({'key': '%s:%d' % (s['script'], l['id']), 'speaker': l['speaker'], 'jp': l['jp']})
        for l in s['unreferenced']:
            rows.append({'key': '%s:%d' % (s['script'], l['id']), 'speaker': l.get('speaker', ''),
                         'jp': l['jp'], 'note': 'not called by the script'})
        covered.add(s['script'].lower())
    seen = {}
    rows = out.setdefault('system', [])
    for rel in sorted(everything):
        m = re.match(r'event/script/([^/]+)\.pac/', rel)
        if m and m.group(1).lower() in covered and rel.lower().endswith('%s_jp.btx' % m.group(1).lower()):
            continue
        for r in everything[rel]:
            jp = r['jp']
            if not jp.strip() or not JAPANESE.search(jp):
                continue
            if jp in seen:                                   # combo lists exist twice, menus repeat
                seen[jp].append('%s#%d' % (rel, r['id']))
                continue
            key = '%s#%d' % (rel, r['id'])
            seen[jp] = []
            target = out.setdefault('placeholders', []) if m else rows
            target.append({'key': key, 'speaker': '', 'jp': jp})
    return out, seen


def load_out(dump):
    folder = os.path.join(dump, 'text', 'translation', 'out')
    done = {}
    if os.path.isdir(folder):
        for n in sorted(os.listdir(folder)):
            if n.endswith('.json'):
                done[n[:-5]] = json.loads(Path(os.path.join(folder, n)).read_text(encoding='utf-8'))
    return done


def check(dump):
    parts, _dupes = chunks(dump)
    done = load_out(dump)
    problems = 0
    for name, rows in parts.items():
        got = done.get(name)
        if got is None:
            print('%-20s MISSING (%d strings)' % (name, len(rows)))
            problems += len(rows)
            continue
        missing = [r['key'] for r in rows if r['key'] not in got]
        empty = [r['key'] for r in rows if r['key'] in got and not str(got[r['key']]).strip()]
        markup = [k for k, v in got.items() if re.search(r'<[^c/][^>]*:[^>]*>', str(v))]
        japanese = [k for k, v in got.items() if JAPANESE.search(str(v))]
        tags = [r['key'] for r in rows if r['key'] in got
                and len(re.findall(r'<c', r['jp'])) != len(re.findall(r'<c', str(got[r['key']])))]
        extra = [k for k in got if k not in {r['key'] for r in rows}]
        print('%-20s %4d strings, %d missing, %d empty, %d with ruby markup, %d with Japanese, '
              '%d colour tag mismatches, %d unknown keys'
              % (name, len(rows), len(missing), len(empty), len(markup), len(japanese), len(tags), len(extra)))
        for label, keys in (('missing', missing), ('empty', empty), ('markup', markup),
                            ('japanese', japanese), ('tags', tags), ('unknown', extra)):
            if keys:
                print('    %s: %s' % (label, ', '.join(keys[:12]) + (' ...' if len(keys) > 12 else '')))
        problems += len(missing) + len(empty) + len(markup) + len(japanese) + len(tags)
    return problems


def main(argv):
    if len(argv) != 3 or argv[1] not in ('export', 'check', 'merge'):
        print(__doc__)
        return 2
    dump = argv[2]
    if argv[1] == 'export':
        parts, _dupes = chunks(dump)
        folder = os.path.join(dump, 'text', 'translation', 'in')
        os.makedirs(folder, exist_ok=True)
        os.makedirs(os.path.join(dump, 'text', 'translation', 'out'), exist_ok=True)
        for name, rows in parts.items():
            with open(os.path.join(folder, name + '.json'), 'w', encoding='utf-8') as f:
                json.dump(rows, f, ensure_ascii=False, indent=1)
            print('%-20s %4d strings, %6d characters' % (name, len(rows), sum(len(r['jp']) for r in rows)))
        return 0
    if argv[1] == 'check':
        return 1 if check(dump) else 0
    parts, dupes = chunks(dump)
    done = load_out(dump)
    merged = {}
    for name, rows in parts.items():
        for r in rows:
            pt = done.get(name, {}).get(r['key'])
            if pt is None:
                continue
            merged[r['key']] = pt
            for other in dupes.get(r['jp'], []):
                merged[other] = pt
    path = os.path.join(dump, 'text', 'translation', 'pt-BR.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    print('%d strings -> %s' % (len(merged), path))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
