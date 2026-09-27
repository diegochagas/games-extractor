#!/usr/bin/env python3
"""Collects everything the story book shows into one JSON for build.js.

usage: story_prep.py DUMP_DIR WORK_DIR      -> WORK_DIR/story_book.json, WORK_DIR/cache/*.png

DUMP_DIR is the dump made by ../extract.sh (images/, renders/, text/, audio/, video/). Images
are copied into the cache, scaled down to what the page can show.
"""
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from omega import names  # noqa: E402

STORIES = [(50, 'kog'), (51, 'yun'), (52, 'ryo'), (53, 'som'), (54, 'ede'), (55, 'hat'), (56, 'sey')]
# names as written on the stage selection pictures
STAGES = [('st01_town', 'town', 'Praça da cidade', '街広場'),
          ('st02_villa', 'villa', 'Terreno da casa de veraneio de Julian', 'ジュリアン別荘敷地内'),
          ('st03_beach', 'beach', 'Beira-mar', '海辺'), ('st04_prairie', 'prairie', 'Campina de dia', '昼の草原'),
          ('st05_sunset', 'sunset', 'Campina ao pôr do sol', '夕日の草原'),
          ('st06_forest', 'forest', 'Floresta à meia-noite', '深夜の森'),
          ('st07_arena', 'arena', 'Ruínas da arena', '闘技場跡'),
          ('st08_cave', 'cave', 'Diante do altar da caverna', '洞窟祭壇前'),
          ('st09_shrine', 'shrine', 'Templo', '神殿'), ('st10_poseidon', 'poseidon', 'Templo subterrâneo', '地下神殿'),
          ('st00_testmap', None, 'Mapa de teste dos desenvolvedores', '')]
# scenes whose internal title was left with the name of another story
OPPONENTS = {(55, 4): 'Ryuho'}
MOVIES = [('op', 'Abertura'), ('start', 'Prólogo'), ('kog_vs_pos', 'Batalha final (Kouga)'),
          ('sey_vs_pos', 'Batalha final (Seiya)'), ('endroll', 'Créditos finais')]
ELEMENTS = {'光': 'Luz', '闇': 'Trevas', '火': 'Fogo', '水': 'Água', '風': 'Vento', '土': 'Terra', '地': 'Terra',
            '雷': 'Raio'}


class Cache:
    def __init__(self, dump, work):
        self.dump, self.folder = dump, os.path.join(work, 'cache')
        os.makedirs(self.folder, exist_ok=True)
        self.count = 0

    def get(self, rel, max_w=620, max_h=460, crop=False):
        """Path of the cached copy of DUMP/rel (None if the image does not exist)."""
        src = rel if os.path.isabs(rel) else os.path.join(self.dump, rel)
        if not os.path.exists(src):
            return None
        key = hashlib.sha1(('%s|%d|%d|%d|%d' % (src, max_w, max_h, crop, os.path.getmtime(src))).encode()).hexdigest()
        dest = os.path.join(self.folder, key[:20] + '.png')
        if not os.path.exists(dest):
            try:
                im = Image.open(src).convert('RGBA')
            except Exception:
                return None
            if crop:                                        # drop the empty border of renders
                box = im.getbbox()
                if box:
                    im = im.crop(box)
            if im.width > max_w or im.height > max_h:
                s = min(max_w / im.width, max_h / im.height)
                im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
            im.save(dest, optimize=True)
        self.count += 1
        return dest


def first_png(dump, folder):
    p = os.path.join(dump, folder)
    if os.path.isdir(p):
        for n in sorted(os.listdir(p)):
            if n.lower().endswith('.png'):
                return os.path.join(folder, n)
    return None


def sfo(path):
    d = Path(path).read_bytes()
    _magic, _ver, key_off, data_off, count = struct.unpack_from('<4sIIII', d, 0)
    out = {}
    for i in range(count):
        ko, fmt, length, _max, do = struct.unpack_from('<HHIII', d, 20 + i * 16)
        key = d[key_off + ko:d.index(b'\0', key_off + ko)].decode()
        raw = d[data_off + do:data_off + do + length]
        out[key] = struct.unpack('<I', raw[:4])[0] if fmt == 0x0404 else raw.split(b'\0')[0].decode('utf-8', 'replace')
    return out


def plain(text):
    """Game markup -> plain text (ruby keeps the base word, colour tags go away)."""
    text = re.sub(r'<c#[0-9a-fA-F]+>|<c>', '', text or '')
    text = re.sub(r'<([^<>:]+):[^<>]*>', r'\1', text)
    return text.replace('\r\n', '\n').replace('\r', '\n')


def ruby(text):
    """Japanese text with the readings in parentheses, on one line."""
    text = re.sub(r'<c#[0-9a-fA-F]+>|<c>', '', text or '')
    text = re.sub(r'<([^<>:]+):([^<>]*)>', r'\1（\2）', text)
    return re.sub(r'\s*[\r\n]+\s*', '', text).strip()


def duration(path):
    try:
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                              'default=nw=1:nk=1', path], capture_output=True, text=True).stdout
        s = float(out.strip())
        return '%d:%02d' % (s // 60, s % 60)
    except Exception:
        return ''


def movie_frames(dump, work, name, count=6):
    src = os.path.join(dump, 'video', name + '.mp4')
    if not os.path.exists(src):
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


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    dump, work = os.path.abspath(argv[1]), os.path.abspath(argv[2])
    os.makedirs(work, exist_ok=True)
    cache = Cache(dump, work)
    text = json.loads(Path(os.path.join(dump, 'text', 'all_text.json')).read_text(encoding='utf-8'))
    pt = json.loads(Path(os.path.join(dump, 'text', 'translation', 'pt-BR.json')).read_text(encoding='utf-8'))
    story = json.loads(Path(os.path.join(dump, 'text', 'story.json')).read_text(encoding='utf-8'))
    sums_path = os.path.join(dump, 'text', 'translation', 'summaries.json')
    sums = json.loads(Path(sums_path).read_text(encoding='utf-8')) if os.path.exists(sums_path) else {'game': '', 'stories': {}}
    models = {m['id']: m for m in json.loads(Path(os.path.join(dump, 'text', 'models.json')).read_text(encoding='utf-8'))}
    missing_pt = []

    def tr(key, jp=''):
        v = pt.get(key)
        if v is None and jp.strip() and re.search(r'[ぁ-ヺ一-鿿]', jp):
            missing_pt.append(key)
        return plain(v) if v is not None else plain(jp)

    book = {'facts': sfo(os.path.join(dump, 'iso', 'PSP_GAME', 'PARAM.SFO')), 'summary': sums.get('game', '')}
    book['cover'] = {'icon': cache.get('iso/PSP_GAME/ICON0.PNG', 300, 200), 'pic': cache.get('iso/PSP_GAME/PIC1.PNG'),
                     'title': cache.get(first_png(dump, 'images/scene/title/titledata.pac') or 'x')}

    # ---- menus
    menu = 'scene/mainmenu/mainmenudata.pac/MAINMENU_JP.BTX'
    book['menu'] = [{'jp': ruby(r['jp']), 'pt': tr('%s#%d' % (menu, r['id']), r['jp'])} for r in text.get(menu, [])
                    if r['jp'].strip()][:16]

    # ---- characters
    chars = []
    for code, jp, romaji, rank_jp, rank_pt in names.CHARACTERS:
        up = code.upper()
        prof = 'scene/gallery/profiledata.pac/%s_PROFILE_JP.BTX' % up
        prof_jp = text.get(prof, [{'jp': ''}])[0]['jp']
        combos = 'btx/combolist/%s_combolist_jp.btx' % code
        element = re.search(r'([光闇火水風土地雷])属性', prof_jp)
        voice = re.search(r'[（(]Voz: ([^）)]+)[）)]', pt.get(prof + '#0', ''))
        pic = 'syu' if code == 'shu' else code
        bust = []
        bdir = os.path.join(dump, 'images', 'common', 'bustup')
        for n in sorted(os.listdir(bdir)):
            m = re.match(r'adv_chara_%s_(\d+)\.pac$' % code, n)
            if m:
                f = first_png(dump, 'images/common/bustup/' + n)
                if f:
                    bust.append({'file': cache.get(f, 256, 256), 'label': 'Retrato %s' % m.group(1)})
        rnd = 'renders/characters/%s/%s_' % (code, code)
        c = {'code': code, 'name': romaji, 'jp': jp, 'rank': rank_pt, 'rank_jp': rank_jp,
             'v2': code.endswith('v2'), 'element': ELEMENTS.get(element.group(1), '') if element else '',
             'voice': voice.group(1) if voice else '',
             'profile': re.sub(r'\s*[（(]Voz: [^）)]+[）)]', '', tr(prof + '#0', prof_jp)).strip(),
             'profile_jp': ruby(prof_jp),
             'combos': [{'jp': ruby(r['jp']), 'pt': tr('%s#%d' % (combos, r['id']), r['jp'])}
                        for r in text.get(combos, []) if r['jp'].strip()],
             'select': cache.get(first_png(dump, 'images/common/image/select_pic_%s.pac' % pic) or 'x', 200, 200),
             'picture': cache.get('images/scene/gallery/profiledata.pac/CHARA_PIC_%s.png' % up, 300, 420),
             'nameplate': cache.get(first_png(dump, 'images/common/menu/menu_name_%s_01.pac' % code) or 'x', 300, 80),
             'arcade': cache.get(first_png(dump, 'images/common/image/still_arc_%s.pac' % code) or 'x', 480, 272),
             'bustups': [b for b in bust if b['file']],
             'renders': {}, 'model': {}}
        for key, label in (('00_normal', 'Armadura inteira'), ('00_half', 'Armadura danificada'),
                           ('00_broken', 'Armadura destruída'), ('01_normal', 'Cores do jogador 2'),
                           ('01_broken', 'Cores do jogador 2, Armadura destruída')):
            views = {v: cache.get('%s%s/%s.png' % (rnd, key, v), 330, 420, crop=True) for v in ('front', 'side', 'back')}
            if views['front']:
                c['renders'][key] = {'label': label, 'views': views}
        c['poses'] = [p for p in (
            {'file': cache.get(rnd + 'pose_idle/three_quarter.png', 300, 400, crop=True), 'label': 'Pose de guarda'},
            {'file': cache.get(rnd + 'pose_idle/front.png', 300, 400, crop=True), 'label': 'Pose de guarda, de frente'},
            {'file': cache.get(rnd + 'pose_win/front.png', 300, 400, crop=True), 'label': 'Pose de vitória'}) if p['file']]
        m = models.get('characters/%s/%s_00_normal' % (code, code))
        if m:
            c['model'] = {'bones': m['bones'], 'triangles': m['triangles'], 'animations': m['animations'],
                          'attachments': len(m.get('attachments', []))}
        chars.append(c)
    book['characters'] = chars
    extra = []
    for code, label in (('ate', 'Atena (Saori Kido)'), ('024', 'Atena (Saori Kido)'), ('025', 'Julian Solo'),
                        ('man', 'Homem misterioso'), ('hatv3', 'Haruto (terceiro traje)')):
        bdir = os.path.join(dump, 'images', 'common', 'bustup')
        for n in sorted(os.listdir(bdir)):
            if re.match(r'adv_chara_%s_\d+\.pac$' % code, n):
                f = cache.get(first_png(dump, 'images/common/bustup/' + n) or 'x', 256, 256)
                if f:
                    extra.append({'file': f, 'label': '%s (%s)' % (label, n[10:-4])})
    book['extra_portraits'] = extra

    # ---- stages
    stages = []
    for ident, pic, label, label_jp in STAGES:
        r = 'renders/stages/%s/map_model' % ident
        objects = []
        rdir = os.path.join(dump, 'renders', 'stages', ident)
        if os.path.isdir(rdir):
            for n in sorted(os.listdir(rdir)):
                if n.startswith('str_type'):
                    f = cache.get('renders/stages/%s/%s/three_quarter.png' % (ident, n), 200, 200, crop=True)
                    if f:
                        objects.append({'file': f, 'label': 'Objeto quebrável %s' % n[8:]})
        m = models.get('stages/%s/map_model' % ident, {})
        stages.append({'id': ident, 'name': label, 'jp': label_jp,
                       'select': cache.get(first_png(dump, 'images/common/image/select_stage_%s.pac' % pic) or 'x', 256, 200) if pic else None,
                       'view': cache.get(r + '/three_quarter.png', 620, 400, crop=True),
                       'top': cache.get(r + '/top.png', 300, 300, crop=True),
                       'sky': cache.get(r + '_sky/front.png', 300, 300, crop=True),
                       'objects': objects, 'triangles': m.get('triangles', 0)})
    book['stages'] = stages
    book['backgrounds3d'] = [{'file': cache.get('renders/backgrounds/%s/three_quarter.png' % n, 300, 300, crop=True),
                              'label': n} for n in ('bigbang_bg_galaxy', 'bigbang_bg_mars', 'bigbang_bg_sea')]

    # ---- stories
    def image_of(res):
        folder = 'images/' + res
        return first_png(dump, folder)

    by_script = {s['script']: s for s in story['scripts']}
    stories = []
    stats = {'lines': 0, 'scenes': 0, 'voiced': 0}
    for chapter, code in STORIES:
        who = names.BY_CODE[code]
        info = sums.get('stories', {}).get(str(chapter), {})
        st = {'chapter': chapter, 'code': code, 'name': who[2], 'jp': who[1], 'summary': info.get('summary', ''),
              'picture': cache.get('images/scene/gallery/profiledata.pac/CHARA_PIC_%s.png' % code.upper(), 260, 360),
              'stages': []}
        for n in range(1, 9):
            scenes = []
            for phase, num in (('Antes da batalha', n), ('Depois da batalha', n + 10)):
                s = by_script.get('%d_%02d' % (chapter, num))
                if not s or not (s['lines'] or s['unreferenced']):
                    continue
                key = s['script']
                lines = []
                for l in s['lines']:
                    who_pt = l['speaker'] + (' (%s)' % l['identity'] if l.get('identity') else '')
                    lines.append({'speaker': who_pt, 'pt': tr('%s:%d' % (key, l['id']), l['jp']), 'jp': ruby(l['jp']),
                                  'voice': os.path.splitext(l['voice'])[0] + '.ogg' if l.get('voice') else '',
                                  'id': l['id']})
                    stats['voiced'] += bool(l.get('voice'))
                cut = [{'speaker': u.get('speaker', ''), 'pt': tr('%s:%d' % (key, u['id']), u['jp']),
                        'jp': ruby(u['jp']), 'id': u['id']} for u in s['unreferenced']]
                stats['lines'] += len(lines)
                stats['scenes'] += 1
                scenes.append({
                    'script': key, 'phase': phase, 'title': tr(key + ':title', s['title_jp']), 'title_jp': s['title_jp'],
                    'backgrounds': [f for f in (cache.get(image_of(r[:-4] + '.pac') or 'x', 300, 190)
                                                for r in s['backgrounds']) if f],
                    'stills': [f for f in (cache.get(image_of(r) or 'x', 480, 272) for r in s['stills']) if f],
                    'items': [f for f in (cache.get(image_of(r) or 'x', 90, 90) for r in s['items']) if f],
                    'bgm': [os.path.basename(b)[:-4] for b in s['bgm']],
                    'movies': [os.path.basename(m)[:-4] for m in s['movies']],
                    'lines': lines, 'cut': cut})
            if scenes:
                opp = re.search(r'VS\s*(.+?)\s*\(', scenes[0]['title'])
                opp = OPPONENTS.get((chapter, n), opp.group(1) if opp else '')
                for sc in scenes:
                    sc['title_note'] = ('VS ' + opp) not in sc['title'] or st['name'] not in sc['title']
                st['stages'].append({'number': n, 'opponent': opp,
                                     'summary': info.get('stages', {}).get(str(n), ''), 'scenes': scenes})
        stories.append(st)
    book['stories'] = stories

    # ---- event pictures and movies
    titles = 'scene/gallery/eventcgdata.pac/COLLECTION_JP.BTX'
    book['cg_titles'] = [{'number': r['id'] - 99, 'jp': r['jp'], 'pt': tr('%s#%d' % (titles, r['id']), r['jp'])}
                         for r in text.get(titles, []) if 100 <= r['id'] <= 147]
    used = {}
    for st in stories:
        for stage in st['stages']:
            for sc in stage['scenes']:
                for f in sc['stills']:
                    used.setdefault(f, '%s, fase %d' % (st['name'], stage['number']))
    stills = []
    idir = os.path.join(dump, 'images', 'common', 'image')
    for n in sorted(os.listdir(idir)):
        if n.startswith(('still_st_', 'still_ed_', 'adv_thankyou')):
            f = cache.get(first_png(dump, 'images/common/image/' + n) or 'x', 480, 272)
            if f:
                stills.append({'file': f, 'label': n[:-4].upper(), 'used': used.get(f, '')})
    book['stills'] = stills
    book['movies'] = [{'name': n, 'title': t, 'duration': duration(os.path.join(dump, 'video', n + '.mp4')),
                       'frames': [cache.get(f, 300, 170) for f in movie_frames(dump, work, n)]} for n, t in MOVIES]
    book['backgrounds'] = []
    bdir = os.path.join(dump, 'images', 'common', 'background')
    for n in sorted(os.listdir(bdir)):
        f = cache.get(first_png(dump, 'images/common/background/' + n) or 'x', 300, 190)
        if f:
            book['backgrounds'].append({'file': f, 'label': n[:-4]})
    book['items'] = [{'file': cache.get(first_png(dump, 'images/common/item/adv_item_%03d.pac' % i) or 'x', 120, 120),
                      'label': 'Aqua Drop %d' % (i + 1)} for i in range(7)]

    # ---- music
    music = []
    use = {}
    for st in stories:
        for stage in st['stages']:
            for sc in stage['scenes']:
                for b in sc['bgm']:
                    use.setdefault(b, set()).add(st['name'])
    adir = os.path.join(dump, 'audio', 'bgm')
    if os.path.isdir(adir):
        for n in sorted(os.listdir(adir)):
            music.append({'file': n, 'duration': duration(os.path.join(adir, n)),
                          'used': ', '.join(sorted(use.get(n[:-4], [])))})
    book['music'] = music
    book['voices'] = {'story': sum(len(os.listdir(os.path.join(dump, 'audio', 'event', 'sound', d)))
                                   for d in os.listdir(os.path.join(dump, 'audio', 'event', 'sound'))
                                   if os.path.isdir(os.path.join(dump, 'audio', 'event', 'sound', d))),
                      'without_text': [os.path.splitext(v)[0] + '.ogg' for v in story.get('voices_without_text', [])]}

    # ---- every other text of the game
    shown = set()
    for c in chars:
        shown.add('scene/gallery/profiledata.pac/%s_PROFILE_JP.BTX' % c['code'].upper())
        shown.add('scene/gallery/profiledata.pac/%s_COMBOLIST_JP.BTX' % c['code'].upper())
        shown.add('btx/combolist/%s_combolist_jp.btx' % c['code'])
    covered = {s['script'].lower() for s in story['scripts'] if s['lines'] or s['unreferenced']}
    system, leftovers = [], []
    for rel in sorted(text):
        if rel in shown:
            continue
        m = re.match(r'event/script/([^/]+)\.pac/(.+)_JP\.BTX$', rel, re.I)
        if m and m.group(1).lower() == m.group(2).lower() and m.group(1).lower() in covered:
            continue
        rows = [{'id': r['id'], 'jp': ruby(r['jp']), 'pt': tr('%s#%d' % (rel, r['id']), r['jp'])}
                for r in text[rel] if r['jp'].strip()]
        if m:
            leftovers.append({'file': rel, 'rows': rows})
        elif rows:
            system.append({'file': rel, 'rows': rows})
    book['system'] = system
    place = []
    for s in story['scripts']:
        if s['kind'] != 'placeholder' or not (s['lines'] or s['unreferenced']):
            continue
        rows = [{'id': l['id'], 'jp': ruby(l['jp']), 'pt': tr('%s:%d' % (s['script'], l['id']), l['jp'])}
                for l in s['lines'] + s['unreferenced']]
        place.append({'file': s['script'], 'title': tr(s['script'] + ':title', s['title_jp']), 'rows': rows})
    book['placeholders'] = place
    book['leftovers'] = leftovers
    book['stats'] = dict(stats, characters=len(chars), images=cache.count, missing_translations=len(missing_pt),
                         strings=sum(len(v) for v in text.values()),
                         models=len(models), motions=sum(m.get('animations', 0) for m in models.values()))
    with open(os.path.join(work, 'story_book.json'), 'w', encoding='utf-8') as f:
        json.dump(book, f, ensure_ascii=False, indent=1)
    print('STATS', json.dumps(book['stats'], ensure_ascii=False))
    for k in missing_pt[:20]:
        print('  no translation:', k)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
