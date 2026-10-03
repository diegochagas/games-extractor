#!/usr/bin/env python3
"""Character index and gallery of Saint Seiya Rebirth.

usage: roles.py DUMP GALLERY_DIR [--lang pt-BR]

DUMP is the folder with `tables/` (tables.py), `assets/` (dump.py of the APK and CDN bundles) and
`puppets/` (puppet.py --all). For every role bundle the script finds its characters in RoleConfig
(`modelResName`), takes the hero entry (id below 2000, with a constellation) as the main one and the
faction from BattleRoleConfig.Types[5], then copies into GALLERY_DIR/<faction>/<NN model - name>/:
  pose.png (puppet render), icon.png / show.png (RoleConfig icon, iconShow), card.png (bag card),
  bg.png (modelresbg) and the sprite parts of the puppet when `puppets/<model>_parts` exists.
It writes GALLERY_DIR/index.json (every character with its ids, names, faction and files) and
GALLERY_DIR/index.html (a grid by faction).
"""
import html
import json
import os
import shutil
import sys

# BattleRoleConfig.Types[5] (from the table's own header comment)
CLOTH_TYPES = {
    1: ('青铜', 'Bronze Saints', 'Cavaleiros de Bronze'),
    2: ('白银', 'Silver Saints', 'Cavaleiros de Prata'),
    3: ('黄金', 'Gold Saints', 'Cavaleiros de Ouro'),
    4: ('冥界', 'Specters', 'Espectros'),
    5: ('斗士', 'Fighters', 'Guerreiros'),
    6: ('亡灵圣斗士', 'Undead Saints', 'Cavaleiros mortos'),
    7: ('神斗士', 'God Warriors', 'Guerreiros Deuses'),
    8: ('日冕斗士', 'Corona Fighters', 'Guerreiros da Coroa Solar'),
    9: ('神', 'Gods', 'Deuses'),
    10: ('圣魔天使', 'Angels', 'Anjos'),
    11: ('神圣衣', 'God Cloth Saints', 'Cavaleiros de Armadura Divina'),
    12: ('刻斗士', 'Pallasites', 'Pallasites'),
    13: ('其他', 'Others', 'Outros'),
}
UNKNOWN = ('未知', 'Unknown', 'Desconhecido')


def faction(cloth_type, lang='pt-BR'):
    names = CLOTH_TYPES.get(cloth_type, UNKNOWN)
    return names[2] if lang == 'pt-BR' else names[1]


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def characters(tables_dir):
    """{model name (lower): {'model', 'name', 'nameDesc', 'constellation', 'sid', 'cloth', 'star', 'icon',
    'iconShow', 'card', 'desc', 'ids': [all sids]}} from RoleConfig + BattleRoleConfig + RoleSkinConfig."""
    role = load_json(os.path.join(tables_dir, 'RoleConfig.json'))
    battle = {b['id']: b for b in load_json(os.path.join(tables_dir, 'BattleRoleConfig.json'))}
    skins = {}
    skin_path = os.path.join(tables_dir, 'RoleSkinConfig.json')
    if os.path.exists(skin_path):
        for s in load_json(skin_path):
            skins.setdefault(str(s.get('roleSid')), s)
    out = {}
    for r in role:
        model = (r.get('modelResName') or '').strip()
        if not model:
            continue
        key = model.lower()
        sid = str(r.get('Sid'))
        b = battle.get(sid)
        cloth = b['Types'][5] if b and isinstance(b.get('Types'), list) and len(b['Types']) > 5 else None
        is_hero = sid.isdigit() and int(sid) < 2000 and bool(r.get('nameDesc'))
        entry = out.setdefault(key, {'model': model, 'ids': [], 'name': '', 'nameDesc': '', 'constellation': '',
                                     'sid': None, 'cloth': None, 'star': None, 'icon': '', 'iconShow': '',
                                     'card': '', 'desc': '', 'hero': False})
        entry['ids'].append(sid)
        better = is_hero and (not entry['hero'] or int(sid) < int(entry['sid']))
        if entry['sid'] is None or better:
            skin = skins.get(sid, {})
            entry.update(name=r.get('name') or '', nameDesc=r.get('nameDesc') or '', constellation=r.get('xzName') or '',
                         sid=sid, cloth=cloth if cloth is not None else entry['cloth'], star=r.get('originalStar'),
                         icon=r.get('icon') or '', iconShow=r.get('iconShow') or '', card=skin.get('bagShow') or '',
                         desc=r.get('descEx') or r.get('desc') or '', hero=is_hero)
        elif entry['cloth'] is None and cloth is not None:
            entry['cloth'] = cloth
    return out


def picture_index(assets_dir):
    """{(bundle dir lower, picture name lower): png path} for every texture / sprite dumped under assets/texture."""
    index = {}
    root = os.path.join(assets_dir, 'texture')
    if not os.path.isdir(root):
        return index
    for r, _dirs, files in os.walk(root):
        if 'objects.json' not in files:
            continue
        rel = os.path.relpath(r, root).replace('\\', '/')
        bundle_dir = rel.replace('/_current_.fassets', '').replace('.fassets', '').lower()
        for obj in load_json(os.path.join(r, 'objects.json')):
            if obj.get('file') and obj['type'] in ('Texture2D', 'Sprite'):
                index.setdefault((bundle_dir, (obj.get('name') or '').lower()), os.path.join(r, obj['file']))
    return index


def resolve(index, ref):
    """'RoleIcon/t6001' -> the dumped png (exact bundle dir first, then any bundle under the first folder)."""
    if isinstance(ref, list):
        ref = next((r for r in ref if r), '')
    if not ref or not isinstance(ref, str):
        return None
    parts = ref.replace('\\', '/').strip('/').split('/')
    if len(parts) < 2:
        return None
    name = parts[-1].lower()
    folder = '/'.join(parts[:-1]).lower()
    if (folder, name) in index:
        return index[(folder, name)]
    first = parts[0].lower()
    for (d, n), path in index.items():
        if n == name and (d == first or d.startswith(first + '/') or d.startswith(first)):
            return path
    return None


def safe(name):
    return ''.join(c for c in name if c not in '\\/:*?"<>|').strip() or 'x'


def build(dump, gallery, lang='pt-BR'):
    chars = characters(os.path.join(dump, 'tables'))
    index = picture_index(os.path.join(dump, 'assets'))
    puppets = os.path.join(dump, 'puppets')
    rows = []
    n = 0
    for key in sorted(chars):
        c = chars[key]
        pose = os.path.join(puppets, c['model'] + '.png')
        if not os.path.exists(pose):
            # the bundle names are lower case, the table name keeps its case
            cands = [f for f in os.listdir(puppets)] if os.path.isdir(puppets) else []
            match = next((f for f in cands if f.lower() == key + '.png'), None)
            pose = os.path.join(puppets, match) if match else None
        fac = faction(c['cloth'], lang)
        label = f"{c['model']} - {c['nameDesc'] or c['name']}" if (c['nameDesc'] or c['name']) else c['model']
        dest = os.path.join(gallery, safe(fac), safe(label))
        files = {}
        copies = [('pose.png', pose), ('icon.png', resolve(index, c['icon'])), ('show.png', resolve(index, c['iconShow'])),
                  ('card.png', resolve(index, c['card'])), ('bg.png', resolve(index, f"ModelResBg/{c['sid']}"))]
        if not any(p for _, p in copies):
            continue
        os.makedirs(dest, exist_ok=True)
        for fname, src in copies:
            if src and os.path.exists(src):
                shutil.copyfile(src, os.path.join(dest, fname))
                files[fname[:-4]] = os.path.relpath(os.path.join(dest, fname), gallery)
        parts = os.path.join(puppets, c['model'] + '_parts')
        if os.path.isdir(parts):
            shutil.copytree(parts, os.path.join(dest, 'parts'), dirs_exist_ok=True)
            files['parts'] = os.path.relpath(os.path.join(dest, 'parts'), gallery)
        rows.append({**{k: v for k, v in c.items() if k != 'hero'}, 'faction': fac,
                     'faction_cn': CLOTH_TYPES.get(c['cloth'], UNKNOWN)[0], 'folder': os.path.relpath(dest, gallery),
                     'files': files})
        n += 1
    rows.sort(key=lambda r: (r['cloth'] if r['cloth'] is not None else 99, int(r['sid']) if str(r['sid']).isdigit() else 0))
    with open(os.path.join(gallery, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    write_html(rows, os.path.join(gallery, 'index.html'), lang)
    return n


def write_html(rows, path, lang):
    title = 'Saint Seiya Rebirth - personagens' if lang == 'pt-BR' else 'Saint Seiya Rebirth - characters'
    out = [f'<!doctype html><meta charset="utf-8"><title>{title}</title>',
           '<style>body{font-family:sans-serif;background:#111;color:#eee;margin:16px}h2{margin-top:32px}'
           '.grid{display:flex;flex-wrap:wrap;gap:12px}.card{width:200px;background:#222;padding:8px;border-radius:8px;text-align:center}'
           '.card img{max-width:184px;max-height:220px}.card small{color:#aaa}</style>',
           f'<h1>{title}</h1>']
    current = None
    for r in rows:
        if r['faction'] != current:
            if current is not None:
                out.append('</div>')
            current = r['faction']
            out.append(f'<h2>{html.escape(current)} <small>{html.escape(r["faction_cn"])}</small></h2><div class="grid">')
        pic = r['files'].get('pose') or r['files'].get('show') or r['files'].get('icon') or ''
        out.append(f'<div class="card"><a href="{html.escape(r["folder"])}/">'
                   f'<img src="{html.escape(pic)}" alt="{html.escape(r["model"])}" loading="lazy"></a><br>'
                   f'<b>{html.escape(r["nameDesc"] or r["name"])}</b><br><small>{html.escape(r["model"])} · {html.escape(str(r["sid"]))}</small></div>')
    if current is not None:
        out.append('</div>')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    lang = argv[argv.index('--lang') + 1] if '--lang' in argv else 'pt-BR'
    n = build(argv[0], argv[1], lang)
    print(f'{n} characters -> {argv[1]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
