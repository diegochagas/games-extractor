#!/usr/bin/env python3
"""Collects everything the story book shows into one JSON for build.js.

usage: story_prep.py DUMP_DIR WORK_DIR [--videos FOLDER]   -> WORK_DIR/story_book.json, WORK_DIR/cache/*.png

DUMP_DIR is the dump made by ../extract.sh (images/, text/, audio/, video/) after transcript.py
wrote text/story.json. `--videos` is a folder with the two recorded cutscenes of the game
(file names containing "Dark" or "aiolos" = IF05, "Palace" or "nova-casa" = IF09): frames of them illustrate those chapters.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from sanctuary import names  # noqa: E402

BUTTONS = {'\r': '□', '\x0e': '△', '\x0f': '○', '\x11': '×', '\x10': 'R1', '\x05': '△', '\x06': '○', '\x07': '×',
           '\x08': '□', '\x12': 'L1', '\x0c': 'R2', '\x0b': 'L2'}
MOVIES = [('gx_jp', 'Abertura (versão japonesa)'), ('gx_us', 'Abertura (versão internacional)'),
          ('atari', 'Logotipo da Atari')]
VIDEO_OF = {'if05': ('Dark', 'aiolos'), 'if09': ('Palace', 'nova-casa')}


def render(text, keep_lines=False):
    """Game markup -> text. «...» marks the words the game shows in colour (build.js makes them bold)."""
    t = text or ''
    t = re.sub(r'\n?É\x02..', '', t, flags=re.S)              # speaker / face codes of the Pope mode
    t = re.sub(r'\n?È\x01(.)', lambda m: '[%s]' % BUTTONS.get(m.group(1), '?'), t, flags=re.S)
    t = re.sub(r'\n?\x16\x01\x01', '«', t)
    t = re.sub(r'\n?\x16\x01', '»', t)
    t = re.sub(r'\n?\x13\x01.\s*', ': ', t)
    t = t.replace('( «', '(').replace('» )', ')')
    t = t.replace('\n\x04', '').replace('\n\x06', '\n\n').replace('\n\x01', '\n').replace('\n\x0b', '')
    t = re.sub(r'[\x00-\x08\x0b-\x1f]', '', t)
    t = re.sub(r'«\s*»', '', t)
    t = re.sub(r'»\s*\n\s*«', ' ', t)
    lines = [ln.strip() for ln in t.split('\n')]
    if keep_lines:
        return [ln for ln in lines if ln]
    out = []
    for ln in lines:
        if ln == '':
            if out and out[-1] != '':
                out.append('')
        else:
            out.append(ln)
    paragraphs, cur = [], []
    for ln in out:
        if ln == '':
            if cur:
                paragraphs.append(' '.join(cur))
                cur = []
        else:
            cur.append(ln)
    if cur:
        paragraphs.append(' '.join(cur))
    return '\n'.join(paragraphs).strip()


class Cache:
    def __init__(self, dump, work):
        self.dump, self.folder = dump, os.path.join(work, 'cache')
        os.makedirs(self.folder, exist_ok=True)
        self.count = 0

    def get(self, rel, max_w=620, max_h=460, crop=False, flatten=False):
        src = rel if os.path.isabs(rel) else os.path.join(self.dump, rel)
        if not src or not os.path.exists(src):
            return None
        key = hashlib.sha1(('%s|%d|%d|%d|%d|%d' % (src, max_w, max_h, crop, flatten, os.path.getmtime(src))).encode()).hexdigest()
        dest = os.path.join(self.folder, key[:20] + '.png')
        if not os.path.exists(dest):
            try:
                im = Image.open(src).convert('RGBA')
            except Exception:
                return None
            if flatten:                                       # textures stored with half alpha
                im.putalpha(255)
            if crop:
                box = im.getbbox()
                if box:
                    im = im.crop(box)
            if im.width > max_w or im.height > max_h:
                s = min(max_w / im.width, max_h / im.height)
                im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
            im.save(dest, optimize=True)
        self.count += 1
        return dest


def pngs(folder):
    out = []
    for root, _dirs, files in os.walk(folder):
        for n in files:
            if n.lower().endswith('.png'):
                out.append(os.path.join(root, n))
    return sorted(out)


def duration(path):
    try:
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                              'default=nw=1:nk=1', path], capture_output=True, text=True).stdout
        s = float(out.strip())
        return '%d:%02d' % (s // 60, s % 60)
    except Exception:
        return ''


def frames(src, work, name, count=6):
    if not src or not os.path.exists(src):
        return []
    folder = os.path.join(work, 'frames')
    os.makedirs(folder, exist_ok=True)
    try:
        total = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                                      'default=nw=1:nk=1', src], capture_output=True, text=True).stdout.strip())
    except ValueError:
        return []
    out = []
    for i in range(count):
        dest = os.path.join(folder, '%s_%02d.png' % (name, i))
        if not os.path.exists(dest):
            t = total * (i + 0.5) / count
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', '%.2f' % t, '-i', src,
                            '-frames:v', '1', dest], check=False)
        if os.path.exists(dest):
            out.append(dest)
    return out


def entries_of(strings, starts_entry):
    """Groups the strings of a collection table into entries (a heading string + its continuations)."""
    out = []
    for s in strings:
        if starts_entry(s) or not out:
            out.append([s])
        else:
            out[-1].append(s)
    return out


def card_lines(strings):
    """['Seiya de Pégaso', 'Idade: 13', 'Altura: 1,65m', ...] out of the strings of one encyclopedia entry."""
    lines = []
    for s in strings:
        lines += [ln.replace('«', '').replace('»', '').strip() for ln in render(s, keep_lines=True)]
    merged = []
    for ln in lines:
        if not ln:
            continue
        if merged and (merged[-1].endswith(':') or merged[-1].endswith(',') or
                       (':' in merged[-1] and ':' not in ln and merged[-1].split(':')[0] in ('Treinamento', 'Técnicas'))):
            merged[-1] = (merged[-1] + ' ' + ln).replace(': ,', ':')
        elif merged and ':' not in ln and ':' not in merged[-1] and len(merged) == 1:
            merged[-1] += ' ' + ln                               # a name broken over two lines
        else:
            merged.append(ln)
    return [re.sub(r'\s+', ' ', m).strip() for m in merged]


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    dump, work = os.path.abspath(argv[1]), os.path.abspath(argv[2])
    videos = argv[argv.index('--videos') + 1] if '--videos' in argv else ''
    os.makedirs(work, exist_ok=True)
    cache = Cache(dump, work)
    text = os.path.join(dump, 'text')
    msg = json.loads(Path(os.path.join(text, 'messages.json')).read_text(encoding='utf-8'))
    story = json.loads(Path(os.path.join(text, 'story.json')).read_text(encoding='utf-8'))
    scenes = json.loads(Path(os.path.join(text, 'scenes.json')).read_text(encoding='utf-8'))
    afs_index = json.loads(Path(os.path.join(dump, 'afs', 'afs_index.json')).read_text(encoding='utf-8'))

    def pt(table):
        return msg.get(table, {}).get('pt', [])

    def img(rel, *a, **k):
        return cache.get(rel, *a, **k)

    def first(folder):
        p = pngs(os.path.join(dump, 'images', folder))
        return p[0] if p else None

    cnf = Path(os.path.join(dump, 'iso', 'SYSTEM.CNF')).read_text(errors='replace') if os.path.exists(os.path.join(dump, 'iso', 'SYSTEM.CNF')) else ''
    book = {'facts': {'boot': re.search(r'cdrom0:\\([^;]+)', cnf).group(1) if re.search(r'cdrom0:\\([^;]+)', cnf) else '',
                      'version': re.search(r'VER = (\S+)', cnf).group(1) if re.search(r'VER = (\S+)', cnf) else '',
                      'vmode': re.search(r'VMODE = (\S+)', cnf).group(1) if re.search(r'VMODE = (\S+)', cnf) else '',
                      'afs_files': len(afs_index), 'pictures': len(pngs(os.path.join(dump, 'images'))),
                      'adx': sum(1 for r in afs_index if r['name'].lower().endswith('.adx')),
                      'strings': sum(len(v.get('pt', [])) for v in msg.values())}}
    book['cover'] = {'logo': img(first('holiday_lightbelt.tpl'), 500, 200),
                     'title': img(first('title_a_us.tpl'), 480, 420),
                     'title_b': img(first('title_b_us.tpl'), 480, 420),
                     'title_c': img(first('title_c_us.tpl'), 480, 420)}

    # ---- menus and system tables
    def table_rows(name, with_en=True):
        rows = []
        en = msg.get(name, {}).get('en') or msg.get(name, {}).get('uk') or []
        for i, s in enumerate(pt(name)):
            r = render(s)
            if r.strip():
                e = render(en[i]) if with_en and i < len(en) and not re.search(r'[ぁ-ヺ一-鿿]', en[i]) else ''
                rows.append({'id': i, 'pt': r, 'en': e})
        return rows
    book['menus'] = [{'file': n, 'label': lbl, 'rows': table_rows(n)} for n, lbl in (
        ('msg_option.bin', 'Opções'), ('msg_story.bin', 'Pausa do modo História'), ('msg_vs.bin', 'Pausa do modo Versus'),
        ('msg_result.bin', 'Tela de resultado'), ('msg_holiday.bin', 'Modo Coleção'),
        ('msg_kyoukoustart.bin', 'Modo Mestre: início e instruções'), ('msg_kyoukoupause.bin', 'Modo Mestre: pausa'),
        ('msg_caution.bin', 'Aviso'))]
    book['tutorial'] = [render(s) for s in pt('msg_tutorial.bin') if render(s).strip()]

    # ---- encyclopedia (zukan): 56 entries in the order of msg_holiday_collection
    collection = pt('msg_holiday_collection.bin')
    zukan_entries = entries_of(pt('msg_zukan.bin'), lambda s: not s.startswith('\x16'))
    zukan_pics = pngs(os.path.join(dump, 'images', 'holiday_zukan.tpl'))
    encyclopedia = []
    for i, name in enumerate(collection):
        lines = card_lines(zukan_entries[i]) if i < len(zukan_entries) else []
        encyclopedia.append({'number': i + 1, 'name': name, 'lines': [ln for ln in lines if ':' in ln],
                             'picture': img(zukan_pics[i], 220, 330) if i < len(zukan_pics) else None})
    book['encyclopedia'] = encyclopedia
    by_name = {e['name']: e for e in encyclopedia}

    # ---- toys and cards
    toy_names = pt('msg_holiday_toy.bin')
    toy_entries = entries_of(pt('msg_toy.bin'), lambda s: s.startswith('\x16'))
    toy_pics = pngs(os.path.join(dump, 'images', 'holiday_toy.tpl'))
    toys = []
    for i, name in enumerate(toy_names):
        desc = ''
        if i < len(toy_entries):
            desc = render('\n\x01'.join(toy_entries[i]))
            desc = re.sub(r'^«[^»]*»\s*', '', desc).strip()
        toys.append({'number': i + 1, 'name': name, 'text': desc, 'picture': img(toy_pics[i], 200, 300) if i < len(toy_pics) else None})
    book['toys'] = toys
    card_strings = pt('msg_card.bin')
    card_pics = pngs(os.path.join(dump, 'images', 'holiday_card.tpl'))
    cards = []
    per = max(1, len(card_strings) // max(1, len(card_pics))) if card_pics else 3
    for i, p in enumerate(card_pics):
        texts = [render(s) for s in card_strings[i * per:(i + 1) * per]]
        cards.append({'number': i + 1, 'picture': img(p, 260, 380), 'text': ' · '.join(t for t in texts if t)})
    book['cards'] = cards

    # ---- the 24 fighters
    mpath = os.path.join(text, 'models.json')
    models_info = json.loads(Path(mpath).read_text(encoding='utf-8')) if os.path.exists(mpath) else []
    fighters = []
    name_plates = pngs(os.path.join(dump, 'images', 'name_us.tpl'))
    for num, short, full, slug_ in names.ROSTER:
        skills = []
        rows = pt('skilllist%s.bin' % num)
        i = 1
        while i + 1 < len(rows):
            label, cmd = render(rows[i]), render(rows[i + 1])
            if label.strip():
                skills.append({'name': label.replace('«', '').replace('»', ''), 'command': cmd})
            i += 2
        enc = by_name.get(full) or by_name.get(full.replace('Seiya com a Armadura de Sagitário', 'Seiya de Pégaso'))
        toy = next((t for t in toys if t['name'] == full), None)
        renders = {}
        for suffix, label in (('', 'Cor 1'), ('_cor2', 'Cor 2')):
            views = {v: img('renders/characters/%s%s/%s.png' % (slug_, suffix, v), 330, 420, crop=True) for v in ('front', 'side', 'back', 'three_quarter')}
            if views['front']:
                renders[suffix or 'cor1'] = {'label': label, 'views': views}
        minfo = next((m for m in models_info if m['name'] == slug_ and not m['simple'] and m['colour'] == 1), None)
        fighters.append({'number': num, 'name': short, 'full': full, 'renders': renders,
                         'model': {'bones': minfo['bones'], 'triangles': minfo['triangles'], 'parts': minfo['parts']} if minfo else None,
                         'art': img('images/charstand%sa.png' % num, 300, 420, crop=True),
                         'plate': img(name_plates[int(num)], 200, 60, crop=True) if int(num) < len(name_plates) else None,
                         'encyclopedia': enc, 'skills': skills, 'toy': toy,
                         'effects': img('images/%s.png' % num, 300, 300)})
    book['fighters'] = fighters
    book['extra_art'] = [{'file': img('images/charstande%d.png' % i, 240, 330, crop=True), 'label': lbl}
                         for i, lbl in ((0, 'Mestre Ares'), (1, 'Saori Kido'))]
    book['extra_models'] = [{'name': m['name'], 'file': m['file'], 'triangles': m['triangles'],
                             'front': img('renders/%s/front.png' % m['id'], 300, 400, crop=True),
                             'three_quarter': img('renders/%s/three_quarter.png' % m['id'], 300, 400, crop=True)}
                            for m in models_info if m['name'].startswith('outros') and not m['simple'] and m['colour'] == 1]
    spath = os.path.join(text, 'stages.json')
    stages_info = json.load(open(spath, encoding='utf-8')) if os.path.exists(spath) else []
    book['stages'] = [{'id': st['id'].split('/')[-1], 'name': st['name'], 'tiles': st['tiles'], 'objects': st['objects'],
                       'triangles': st['triangles'], 'far': st['far'],
                       'aerial': img('renders/%s/aerial.png' % st['id'], 560, 420, crop=True),
                       'top': img('renders/%s/top.png' % st['id'], 300, 300, crop=True),
                       'completo': img('renders/%s_completo/aerial.png' % st['id'], 560, 420, crop=True) if st['far'] else None}
                      for st in stages_info]
    bdir = os.path.join(dump, 'audio', 'banks')
    book['bank_count'] = len(os.listdir(bdir)) if os.path.isdir(bdir) else 0
    book['bank_samples'] = sum(len(os.listdir(os.path.join(bdir, b))) for b in os.listdir(bdir)) if os.path.isdir(bdir) else 0

    # ---- chapters
    def chapter_pictures(cid):
        out = {'title': img('images/subtitle_%s.png' % (cid[4:] if cid.startswith('demo') else cid), 400, 225)}
        n = names.TITLE_CARDS.get(cid)
        if n:
            card = pngs(os.path.join(dump, 'images', 'title%02d.bin' % n))
            out['plate'] = img(card[0], 400, 120, crop=True) if card else None
            out['still'] = img(card[1], 480, 360) if len(card) > 1 else None
        return out

    def lines_of(block):
        if not block:
            return []
        return [{'speaker': ln['speaker'], 'text': ln['text'], 'voice': (ln['voice'] or '')[:-4],
                 'source': ln['source'], 'page': ln['page']} for ln in block['lines'] if ln['voice']]

    stats = {'lines': 0, 'scenes': 0, 'whisper': 0, 'fixed': 0, 'missing': 0}
    chapters = []
    for ch in story['chapters']:
        sc = ch['scene']
        lines = lines_of(sc)
        for ln in lines:
            stats['lines'] += 1
            stats[ln['source'] if ln['source'] in stats else 'missing'] += 1
        stats['scenes'] += bool(sc)
        video = None
        if videos and ch['id'] in VIDEO_OF and os.path.isdir(videos):
            for n in sorted(os.listdir(videos)):
                if any(k in n for k in VIDEO_OF[ch['id']]) and n.lower().endswith(('.mp4', '.mkv', '.webm')):
                    src = os.path.join(videos, n)
                    video = {'file': n, 'duration': duration(src),
                             'frames': [img(f, 300, 170) for f in frames(src, work, ch['id'], 8)]}
        chapters.append({'id': ch['id'], 'kind': ch['kind'], 'title': ch['title'], 'title_jp': ch['title_jp'],
                         'chapter': ch['chapter'], 'part': ch['part'],
                         'pages': sc['pages'] if sc else 0, 'bgm': [b[:-4] for b in sc['bgm']] if sc else [],
                         'lines': lines, 'digest': lines_of(ch['digest']), 'pictures': chapter_pictures(ch['id']),
                         'video': video})
    book['chapters'] = chapters
    book['chapter_names'] = pt('msg_holiday_demo.bin')

    # ---- Pope mode text
    pope = []
    for i, s in enumerate(pt('msg_kyoukou.bin')):
        r = render(s)
        if r.strip():
            pope.append({'id': i, 'text': r})
    book['pope_text'] = pope
    book['pope_pictures'] = [img(p, 300, 200) for p in pngs(os.path.join(dump, 'images', 'popetex_us.tpl'))[:12]]

    # ---- movies, music, voices
    book['movies'] = [{'name': n, 'title': t, 'duration': duration(os.path.join(dump, 'video', n + '.mp4')),
                       'frames': [img(f, 300, 170) for f in frames(os.path.join(dump, 'video', n + '.mp4'), work, n)]}
                      for n, t in MOVIES]
    bgm_use = {}
    for s in scenes:
        for b in s['bgm']:
            bgm_use.setdefault(b[:-4].lower(), set()).add(s['script'][:-4])
    music = []
    adir = os.path.join(dump, 'audio')
    for n in sorted(os.listdir(adir)) if os.path.isdir(adir) else []:
        if re.match(r'(?i)(bgm_\d+|b\d+|j\d+|eblue|holiday_new|b14holiday|win)\.ogg$', n):
            music.append({'file': n, 'duration': duration(os.path.join(adir, n)),
                          'used': ', '.join(sorted(bgm_use.get(n[:-4].lower(), [])))})
    book['music'] = music
    voices = {'story': sum(1 for n in os.listdir(adir) if n.lower().startswith('story')) if os.path.isdir(adir) else 0,
              'all': sum(1 for n in os.listdir(adir) if n.endswith('.ogg')) if os.path.isdir(adir) else 0,
              'without_scene': [{'voice': v['voice'][:-4], 'speaker': v['speaker'], 'text': v['text']}
                                for v in story.get('voices_without_scene', [])]}
    book['voices'] = voices
    book['voice_index'] = pt('msg_holiday_voice_index.bin')

    # ---- every other text table
    shown = {'msg_option.bin', 'msg_story.bin', 'msg_vs.bin', 'msg_result.bin', 'msg_holiday.bin', 'msg_kyoukoustart.bin',
             'msg_kyoukoupause.bin', 'msg_caution.bin', 'msg_tutorial.bin', 'msg_zukan.bin', 'msg_holiday_collection.bin',
             'msg_holiday_toy.bin', 'msg_toy.bin', 'msg_card.bin', 'msg_holiday_demo.bin', 'msg_kyoukou.bin',
             'msg_holiday_voice_index.bin'} | {'skilllist%s.bin' % n for n, *_ in names.ROSTER}
    others = []
    for name in sorted(msg):
        if name in shown or re.match(r'(?i)msg(dm|if|pope)', name):
            continue
        rows = table_rows(name, with_en=False)
        if rows:
            others.append({'file': name, 'rows': rows})
    book['others'] = others
    blank = [n for n in sorted(msg) if re.match(r'(?i)msg(dm|if|pope)', n)]
    book['blank_tables'] = blank
    book['stats'] = dict(stats, fighters=len(fighters), encyclopedia=len(encyclopedia), toys=len(toys), cards=len(cards),
                         images=cache.count)
    with open(os.path.join(work, 'story_book.json'), 'w', encoding='utf-8') as f:
        json.dump(book, f, ensure_ascii=False, indent=1)
    print('STATS', json.dumps(book['stats'], ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
