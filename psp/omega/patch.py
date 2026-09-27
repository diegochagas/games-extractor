#!/usr/bin/env python3
"""Portuguese version of Saint Seiya Omega Ultimate Cosmo: writes the translated text, the font
and the pictures with text back into a COPY of the disc image.

usage: patch.py DUMP_DIR ORIGINAL.iso OUT.iso [--font FILE.ttf] [--size 13] [--report FILE.json]
                [--movies DIR] [--without NAME,NAME]      (pictures left as they are, by name)

DUMP_DIR is the dump of extract.sh with the translation merged (text/translation/pt-BR.json).
What is replaced:
  - every BTX text table (story, menus, messages, profiles, move lists), the Portuguese text
    wrapped to the width and the number of lines the Japanese text of the same table uses
  - FONT.FNT: the glyphs of the characters the new text needs, drawn with a free TrueType font,
    in the place of Japanese glyphs the new text no longer uses (same number of glyphs and pages)
  - pictures listed in pictures.py (speaker names of the dialogue window)
  - the movies found in --movies (NAME.pmf, made by movie.py), with the subtitles in the picture
The original image is only read. Files keep their place in the image when they fit.
"""
import json
import os
import re
import shutil
import struct
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import btx  # noqa: E402
import cpk  # noqa: E402
import fnt  # noqa: E402
import iso  # noqa: E402
import pac  # noqa: E402

TAG = re.compile(r'<c#[0-9a-fA-F]+>|<c>')
RUBY = re.compile(r'<([^<>:]+):[^<>]*>')
# tables drawn in windows that break the lines by themselves: the text goes in unbroken
SELF_WRAPPING = ('btx/system/systemmessage_jp.btx',)
# one-line help at the foot of the screen: the bar is as wide as the screen
FOOTERS = ('MAINMENU_JP.BTX', 'STORYSELECT_JP.BTX', 'SELECT_JP.BTX', 'KEY_JP.BTX')
FOOTER_ROOM = (440.0, 1)
KEEP_ORIGINAL_GLYPH = set('←↑→↓○△□×※Ω∞∨～・')       # symbols of the button hints: the game's own drawing
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def visible(text):
    return RUBY.sub(r'\1', TAG.sub('', text))


class Layout:
    """Pixel widths with the advances of a font ({code: advance})."""

    def __init__(self, advances, default):
        self.adv, self.default = advances, default

    def width(self, text):
        return sum(self.adv.get(ord(c), self.default) for c in visible(text))

    def lines(self, text):
        rows = re.split(r'\r?\n', text)
        while rows and not rows[-1].strip():
            rows.pop()
        return rows

    def wrap(self, text, width):
        """Greedy word wrap; colour tags stay glued to their word."""
        out, row = [], ''
        for word in text.split(' '):
            trial = word if not row else row + ' ' + word
            if row and self.width(trial) > width:
                out.append(row)
                row = word
            else:
                row = trial
        if row:
            out.append(row)
        return out

    def fit(self, text, width, rows):
        """Wrapped text, and how many pixels / lines it goes over the room it has."""
        got = self.wrap(text, width)
        if len(got) > rows:                       # a little wider may save a line
            for extra in (1.04, 1.08):
                wider = self.wrap(text, width * extra)
                if len(wider) <= rows:
                    got = wider
                    break
        over = max(0.0, max(self.width(r) for r in got) - width) if got else 0.0
        return '\r\n'.join(got), over, max(0, len(got) - rows)       # the game's line break


def translation_key(rel, sid, covered):
    m = re.match(r'event/script/([^/]+)\.pac/(.+)_JP\.BTX$', rel, re.I)
    if m and m.group(1).lower() == m.group(2).lower() and m.group(1) in covered:
        return '%s:%d' % (m.group(1), sid)
    return '%s#%d' % (rel, sid)


def group_of(rel):
    """Tables that are drawn in the same window share their room."""
    if rel.startswith('event/script/'):
        return 'dialogue'
    if 'combolist' in rel.lower():
        return 'combolist'
    if 'profile' in rel.lower():
        return 'profile'
    return rel


def main(argv):
    pos, opts = [], {'--font': FONT, '--size': '13', '--report': '', '--movies': '', '--without': ''}
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
    dump, original, out = (os.path.abspath(p) for p in pos)
    if os.path.abspath(original) == os.path.abspath(out):
        print('the original image is never written: choose another output')
        return 2
    files = os.path.join(dump, 'files')
    text = json.loads(Path(dump, 'text', 'all_text.json').read_text(encoding='utf-8'))
    pt = json.loads(Path(dump, 'text', 'translation', 'pt-BR.json').read_text(encoding='utf-8'))
    story = json.loads(Path(dump, 'text', 'story.json').read_text(encoding='utf-8'))
    covered = {s['script'] for s in story['scripts'] if s['lines'] or s['unreferenced']}
    short_path = Path(dump, 'text', 'translation', 'short.json')
    short = json.loads(short_path.read_text(encoding='utf-8')) if short_path.exists() else {}

    # ---- the text that goes into the game, before wrapping
    final = {}
    for rel, rows in text.items():
        for r in rows:
            key = translation_key(rel, r['id'], covered)
            new = short.get(key, pt.get(key))
            if new is not None and r['jp'].strip():
                final[(rel, r['id'])] = new.replace('\r', '')

    # ---- font
    old_font = fnt.read(Path(files, 'common', 'globalobject.pac', 'FONT.FNT').read_bytes())
    old_by = {g['code']: g for g in old_font}
    needed = set()
    for rel, rows in text.items():
        for r in rows:
            needed |= set(visible(final.get((rel, r['id']), r['jp'])))
    needed -= set('\n\r')
    needed |= set(' 0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?')
    draw = sorted(c for c in needed if ord(c) < 0x3000 and not (c in KEEP_ORIGINAL_GLYPH and ord(c) in old_by))
    new_glyphs = {g['code']: g for g in fnt.render(opts['--font'], int(opts['--size']), ''.join(draw))}
    keep = {ord(c) for c in needed if ord(c) not in new_glyphs}
    missing = sorted(chr(c) for c in keep if c not in old_by)
    glyphs = dict(new_glyphs)
    for c in keep:
        if c in old_by:
            glyphs[c] = old_by[c]
    # fill up to the original number of glyphs: kana and symbols first, then kanji
    rest = [g for g in old_font if g['code'] not in glyphs]
    rest.sort(key=lambda g: (0x4E00 <= g['code'] <= 0x9FFF, g['code']))
    for g in rest:
        if len(glyphs) >= len(old_font):
            break
        glyphs[g['code']] = g
    if len(glyphs) > len(old_font):
        print('the new text needs %d glyphs, the font holds %d' % (len(glyphs), len(old_font)))
        return 1
    new_font = fnt.build(list(glyphs.values()))
    lay_new = Layout({c: fnt.advance(g) for c, g in glyphs.items()}, 8.0)
    lay_old = Layout({g['code']: fnt.advance(g) for g in old_font}, 15.0)

    # ---- room of every group of tables, from the Japanese text
    room = {}
    for rel, rows in text.items():
        w, n = room.get(group_of(rel), (0.0, 0))
        for r in rows:
            ls = lay_old.lines(r['jp'])
            if ls:
                w = max(w, max(lay_old.width(x) for x in ls))
                n = max(n, len(ls))
        room[group_of(rel)] = FOOTER_ROOM if rel.upper().endswith(FOOTERS) else (w, n)

    # ---- new tables
    report = {'overflow': [], 'missing_glyphs': missing, 'room': room, 'strings': 0}
    tables = {}
    for rel, rows in text.items():
        w, n = room[group_of(rel)]
        new = {}
        for r in rows:
            t = final.get((rel, r['id']))
            if t is None:
                continue
            if rel in SELF_WRAPPING:
                new[r['id']] = t
                report['strings'] += 1
                continue
            own = lay_old.lines(r['jp'])
            # a string never gets less room than the Japanese one had, nor more than the window
            wrapped, over, extra = lay_new.fit(t, w, max(n, len(own)))
            new[r['id']] = wrapped
            report['strings'] += 1
            if over > 0.5 or extra:
                report['overflow'].append({'key': translation_key(rel, r['id'], covered), 'lines_over': extra,
                                           'pixels_over': round(over, 1), 'room': [round(w), n],
                                           'characters': len(visible(t)), 'text': t})
        path = os.path.join(files, rel)
        tables[rel] = btx.write(Path(path).read_bytes(), new)

    # ---- everything that changes, by archive entry
    changed = dict(tables)
    changed['common/globalobject.pac/FONT.FNT'] = new_font
    try:
        from omega import pictures
        left_out = [w.upper() for w in opts['--without'].split(',') if w]
        for rel, blob in pictures.build(dump, opts['--font']).items():
            stem = os.path.splitext(os.path.basename(rel))[0].upper()
            if not any(stem.startswith(w) for w in left_out):
                changed[rel] = blob
    except ImportError:
        pass

    work = tempfile.mkdtemp(prefix='omega-patch-')
    try:
        shutil.copyfile(original, out)
        listing = {p.upper(): p for p, _o, _l, _s, d in iso.listing(out) if not d}
        replaced = {}
        for archive in ('install.cpk', 'archive.cpk'):
            inner = 'PSP_GAME/USRDIR/' + archive
            src = os.path.join(dump, 'iso', 'PSP_GAME', 'USRDIR', archive)
            copy = os.path.join(work, archive)
            shutil.copyfile(src, copy)
            entries = {e['name']: e for e in cpk.Cpk(copy).files}
            new_files = {}
            for name, entry in entries.items():
                if name in changed:
                    new_files[name] = changed[name]
                    continue
                parts = {k[len(name) + 1:]: v for k, v in changed.items() if k.startswith(name + '/')}
                if parts:
                    base = cpk.Cpk(copy).read(entry)
                    names = {p.lower(): p for p, _b in pac.walk(base)}
                    fixed = {}
                    for k, v in parts.items():
                        if k.lower() not in names:
                            raise ValueError('%s is not inside %s' % (k, name))
                        fixed[names[k.lower()]] = v
                    new_files[name] = pac.build(base, fixed)
            done = cpk.patch(copy, new_files)
            # read back what was written
            check = cpk.Cpk(copy)
            for e in check.files:
                if e['name'] in new_files and check.read(e) != new_files[e['name']]:
                    raise ValueError('%s: %s does not read back' % (archive, e['name']))
            replaced[inner] = copy
            report[archive] = {'files': len(done), 'at_the_end': sum(1 for d in done if d[1] == 'end'),
                               'size': os.path.getsize(copy), 'original_size': os.path.getsize(src)}
        if opts['--movies']:
            for n in sorted(os.listdir(opts['--movies'])):
                inner = 'PSP_GAME/USRDIR/MOVIE/' + n.upper()
                if n.lower().endswith('.pmf') and inner.upper() in listing:
                    replaced[listing[inner.upper()]] = os.path.join(opts['--movies'], n)
        report['image'] = [list(x) for x in iso.replace(out, replaced)]
        report['image_size'] = os.path.getsize(out)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    if opts['--report']:
        Path(opts['--report']).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print('%d strings written, %d do not fit their window, %d characters without a glyph'
          % (report['strings'], len(report['overflow']), len(missing)))
    for k in ('install.cpk', 'archive.cpk'):
        print('  %s: %d files replaced (%d moved to the end), %d -> %d bytes'
              % (k, report[k]['files'], report[k]['at_the_end'], report[k]['original_size'], report[k]['size']))
    for name, place, size in report['image']:
        print('  image: %s %s (%d bytes)' % (name, 'in place' if place == 'place' else 'moved to the end', size))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
