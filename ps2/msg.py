#!/usr/bin/env python3
"""Text tables of the game (`msg_*.bin`, `msgDM*.bin`, `msgIF*.bin`, `skilllist*.bin`...).

A table is a block: u16 count, u16 offset of every string (in 16-bit units from the block start),
then the UTF-16LE strings: 0x0000 is a line break, 0x00FF ends the string. The FJF files hold one
block per language (seven: the Japanese slot carries Portuguese in the Brazilian disc, then US
English, UK English, Italian, German, French, Spanish); the cutscene tables (`msgDM`, `msgIF`,
`msgPope`) are one bare block. In the Brazilian disc the Portuguese block was written over the
original one without fixing the FJF offsets, so the first block is read from where it really
starts and the other languages only when their offset still points at a sane block.

The Brazilian text uses hiragana code points for the accented letters the font had no slot for
(`ぇ` = á, `げ` = ã...): ACCENTS maps them back.

usage: msg.py dump SRC_DIR OUT_DIR [--slot0 pt|jp]   -> OUT_DIR/messages.json (every table, every
                                         language), OUT_DIR/messages.txt (the first language, readable)
       msg.py show FILE [LANG] [--slot0 pt|jp]
`--slot0` names the language of the first block: `pt` (the Brazilian disc, default) or `jp` (the
Japanese and European discs, whose first block is Japanese and gets no accent mapping).
"""
import json
import os
import re
import struct
import sys

import fjf

LANGUAGES = ['pt', 'en', 'uk', 'it', 'de', 'fr', 'es']
ACCENTS = {'あ': 'ç', 'ぃ': 'Q', 'い': 'í', 'ぅ': 'õ', 'う': 'ô', 'ぇ': 'á', 'え': 'Á', 'ぉ': 'é', 'か': 'í',
           'が': 'ó', 'き': 'ú', 'ぎ': 'â', 'く': 'q', 'ぐ': 'ê', 'げ': 'ã', 'ざ': ':', 'ず': 'Ó', 'せ': 'É',
           'お': 'É', 'ぁ': 'Ç', 'さ': 'Ú', 'し': 'Í', 'ご': 'Ê', 'け': 'Ã', 'こ': 'à', 'じ': 'º', 'ぜ': '+'}
KANA = re.compile(r'[぀-ヿ]')


def fix_accents(text):
    return ''.join(ACCENTS.get(ch, ch) for ch in text)


def block(data, pos):
    """(strings, end) of the block at `pos`, or (None, pos) when there is no sane block there."""
    if pos + 2 > len(data):
        return None, pos
    count = struct.unpack_from('<H', data, pos)[0]
    if count == 0 or pos + 2 + 2 * count > len(data):
        return None, pos
    offsets = struct.unpack_from('<%dH' % count, data, pos + 2)
    table_end = pos + 2 + 2 * count
    out, end = [], table_end
    for off in offsets:
        p = pos + off * 2
        if p < table_end or p >= len(data):
            return None, pos
        q = p
        while q + 1 < len(data) and data[q:q + 2] != b'\xff\x00':
            q += 2
        text = data[p:q].decode('utf-16le', 'replace').replace('\0', '\n').strip('\n')
        out.append(text)
        end = max(end, q + 2)
    return out, end


def read(data, slot0='pt'):
    """{language: [strings]} of a table file."""
    languages = [slot0] + LANGUAGES[1:]
    data = fjf.unwrap(data)
    out = {}
    if fjf.is_fjf(data):
        _flags, ents = fjf.entries(data)
        if not ents:
            return out
        strings, end = block(data, ents[0][1])
        if strings is None:
            return out
        out[languages[0]] = strings
        pos = (end + 15) & ~15
        for i, (eid, off, _size) in enumerate(ents[1:], 1):
            lang = languages[eid] if eid < len(languages) else 'lang%d' % eid
            strings = None
            if off >= end and off < len(data):            # offset still beyond the Portuguese block
                strings, nxt = block(data, off)
            if strings is None:                           # try the block that follows the previous one
                strings, nxt = block(data, pos)
            if strings is None or len(strings) == 0:
                continue
            if lang in out:                                   # two blocks with the same id: keep both
                lang = '%s_%d' % (lang, i)
            out[lang] = strings
            pos = (nxt + 15) & ~15
    else:
        strings, _end = block(data, 0)
        if strings is not None:
            out[languages[0]] = strings
    if 'pt' in out:
        out['pt'] = [fix_accents(s) for s in out['pt']]
    return out


def main(argv):
    slot0 = argv[argv.index('--slot0') + 1] if '--slot0' in argv else 'pt'
    argv = [a for i, a in enumerate(argv) if a != '--slot0' and (i == 0 or argv[i - 1] != '--slot0')]
    if len(argv) >= 3 and argv[1] == 'show':
        with open(argv[2], 'rb') as f:
            tables = read(f.read(), slot0)
        for lang, strings in tables.items():
            if len(argv) > 3 and lang != argv[3]:
                continue
            print('== %s (%d)' % (lang, len(strings)))
            for i, s in enumerate(strings):
                print('%4d  %s' % (i, s.replace('\n', '\\n')))
        return 0
    if len(argv) == 4 and argv[1] == 'dump':
        src, out = argv[2], argv[3]
        os.makedirs(out, exist_ok=True)
        result, kana, lines = {}, {}, []
        for name in sorted(os.listdir(src)):
            low = name.lower()
            if not ((low.startswith(('msg', 'skilllist', 'skill_')) and low.endswith('.bin')) or low.endswith('.msg')):
                continue
            with open(os.path.join(src, name), 'rb') as f:
                tables = read(f.read(), slot0)
            if not tables:
                continue
            result[name] = tables
            lines.append('== %s (%s)' % (name, ', '.join('%s %d' % (k, len(v)) for k, v in tables.items())))
            for i, s in enumerate(tables.get(slot0, [])):
                for ch in KANA.findall(s):
                    kana.setdefault(ch, []).append(s[:40])
                if s.strip():
                    lines.append('%4d  %s' % (i, s.replace('\n', '\\n')))
        with open(os.path.join(out, 'messages.json'), 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
        with open(os.path.join(out, 'messages.txt'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        print('%d tables -> %s' % (len(result), out))
        for ch, ex in sorted(kana.items()):
            print('!! kana left in Portuguese text: %r x%d  e.g. %s' % (ch, len(ex), ex[:3]))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
