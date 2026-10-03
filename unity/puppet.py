#!/usr/bin/env python3
"""Render the 2D puppet characters of Saint Seiya Rebirth (`role/*.fassets`) in their stored pose.

A role bundle is a prefab: a hierarchy of GameObjects whose Transforms hold the idle pose and
whose SpriteRenderers point to the body-part sprites of one atlas (`Hilda&idle&H1` = head...).
This composes those parts with Pillow: world transform of every part (2D affine from the local
position / Z rotation / scale chain), drawn back to front (sorting order, then larger Z first),
pivot aligned to the transform origin, 100 pixels per unit times --scale.

usage: puppet.py BUNDLE OUT.png [--scale 2] [--parts DIR] [--json OUT.json]
       puppet.py --all BUNDLE_DIR OUT_DIR [--scale 2]     every role/*.fassets(.abws) -> OUT_DIR/NAME.png
--parts also writes every used sprite as DIR/NAME.png; --json writes the part list with their
world transforms (for other renderers).
Needs `pip install UnityPy` (and Pillow, numpy).
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import abws  # noqa: E402
import sprites  # noqa: E402


def quat_to_z_angle(x, y, z, w):
    """Rotation about Z in degrees (counter-clockwise) of a Unity quaternion."""
    return math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))


def compose(parent, local):
    """2D affine matrices [a, b, c, d, tx, ty] (x' = a x + c y + tx, y' = b x + d y + ty)."""
    pa, pb, pc, pd, ptx, pty = parent
    a, b, c, d, tx, ty = local
    return [pa * a + pc * b, pb * a + pd * b, pa * c + pc * d, pb * c + pd * d,
            pa * tx + pc * ty + ptx, pb * tx + pd * ty + pty]


def local_matrix(pos, rot_deg, scale):
    r = math.radians(rot_deg)
    cos, sin = math.cos(r), math.sin(r)
    return [cos * scale[0], sin * scale[0], -sin * scale[1], cos * scale[1], pos[0], pos[1]]


def apply(m, x, y):
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def collect_parts(env):
    """[{name, sprite (UnityPy Sprite), matrix, z, order, color, flip_x, flip_y, enabled}] of a role bundle."""
    objs = {o.path_id: o for o in env.objects}
    transforms = {}
    for o in env.objects:
        if o.type.name == 'Transform':
            transforms[o.path_id] = o.read()

    def go_of(t):
        return objs[t.m_GameObject.path_id].read() if t.m_GameObject.path_id in objs else None

    def ptr_id(c):
        return (c.component if hasattr(c, 'component') else c).path_id

    parts = []

    def walk(pid, parent_m, parent_z, depth):
        t = transforms[pid]
        go = go_of(t)
        if go is None or not go.m_IsActive:
            return
        p, q, s = t.m_LocalPosition, t.m_LocalRotation, t.m_LocalScale
        m = compose(parent_m, local_matrix((p.x, p.y), quat_to_z_angle(q.x, q.y, q.z, q.w), (s.x, s.y)))
        z = parent_z + p.z
        for c in go.m_Component:
            o = objs.get(ptr_id(c))
            if o is None:
                continue
            if o.type.name == 'SpriteRenderer':
                sr = o.read()
                sp = objs.get(sr.m_Sprite.path_id)
                if sp is None or not sr.m_Enabled:
                    continue
                mats = getattr(sr, 'm_Materials', None) or []
                parts.append({'name': go.m_Name, 'sprite': sp.read(), 'matrix': m, 'z': z,
                              'order': sr.m_SortingOrder, 'depth': depth, 'material': mats[0].path_id if mats else None,
                              'color': (sr.m_Color.r, sr.m_Color.g, sr.m_Color.b, sr.m_Color.a),
                              'flip_x': bool(getattr(sr, 'm_FlipX', False)), 'flip_y': bool(getattr(sr, 'm_FlipY', False))})
            elif o.type.name == 'MonoBehaviour':
                # SpriteDeformerBlendShape: a mesh built from a sprite (face, skirt...), drawn as that sprite
                try:
                    tree = o.read_typetree()
                except Exception:  # noqa: BLE001
                    continue
                ptr = tree.get('_sprite') or {}
                sp = objs.get(ptr.get('m_PathID', 0))
                if sp is None or sp.type.name != 'Sprite' or not tree.get('m_Enabled', 1):
                    continue
                ref = tree.get('_referenceMaterial') or {}
                parts.append({'name': go.m_Name, 'sprite': sp.read(), 'matrix': m, 'z': z, 'order': 0, 'depth': depth,
                              'material': ref.get('m_PathID') or None, 'color': (1, 1, 1, 1), 'flip_x': False,
                              'flip_y': False, 'deformer': True})
        for c in t.m_Children:
            if c.path_id in transforms:
                walk(c.path_id, m, z, depth + 1)

    for pid, t in transforms.items():
        if t.m_Father.path_id == 0:
            walk(pid, [1, 0, 0, 1, 0, 0], 0.0, 0)
    # Unity draws by sorting order, then by distance: a larger Z is farther from the camera
    parts.sort(key=lambda d: (d['order'], -d['z']))
    return parts


def render(parts, scale=2.0, margin=16, plan=None, env=None):
    from PIL import Image
    ppu = 100.0 * scale
    placed = []
    cache = sprites.TextureCache()
    for d in parts:
        sp = d['sprite']
        try:
            img = sprites.sprite_image(sp, plan, cache, env, d.get('material'))
        except Exception:  # noqa: BLE001 - a sprite that cannot be decoded is skipped
            continue
        if d['flip_x']:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if d['flip_y']:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
        w, h = img.size
        px, py = sp.m_Pivot.x * w, sp.m_Pivot.y * h   # pivot in sprite pixels, origin bottom-left
        units = sp.m_PixelsToUnits or 100.0
        # corners of the sprite in local units, then to world, then to pixels (y up)
        corners = [((cx - px) / units, (cy - py) / units) for cx, cy in ((0, 0), (w, 0), (w, h), (0, h))]
        world = [apply(d['matrix'], x, y) for x, y in corners]
        placed.append((d, img, [(x * ppu, y * ppu) for x, y in world]))
    if not placed:
        return Image.new('RGBA', (1, 1)), []
    xs = [x for _, _, pts in placed for x, _ in pts]
    ys = [y for _, _, pts in placed for _, y in pts]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    W, H = int(math.ceil(maxx - minx)) + 2 * margin, int(math.ceil(maxy - miny)) + 2 * margin
    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    info = []
    for d, img, pts in placed:
        # affine from the sprite image (x right, y down) to the canvas: use three corners
        (x0, y0), (x1, y1), _, (x3, y3) = pts
        w, h = img.size
        # canvas coordinates (y down)
        cx0, cy0 = x0 - minx + margin, H - (y0 - miny + margin)
        cx1, cy1 = x1 - minx + margin, H - (y1 - miny + margin)
        cx3, cy3 = x3 - minx + margin, H - (y3 - miny + margin)
        # image (0,h) -> c0 (bottom-left), (w,h) -> c1, (0,0) -> c3 (top-left)
        a = (cx1 - cx0) / w
        b = (cy1 - cy0) / w
        c = (cx0 - cx3) / h
        dd = (cy0 - cy3) / h
        tx, ty = cx3, cy3
        # PIL wants the inverse mapping (output -> input)
        det = a * dd - b * c
        if abs(det) < 1e-9:
            continue
        ia, ib, ic, id_ = dd / det, -b / det, -c / det, a / det
        itx, ity = -(ia * tx + ic * ty), -(ib * tx + id_ * ty)
        layer = img.transform((W, H), Image.AFFINE, (ia, ic, itx, ib, id_, ity), resample=Image.BICUBIC)
        r, g, bl, al = d['color']
        if (r, g, bl, al) != (1, 1, 1, 1):
            from PIL import ImageMath  # noqa: F401 - keeps the dependency explicit
            px = layer.split()
            layer = Image.merge('RGBA', (px[0].point(lambda v, r=r: int(v * r)), px[1].point(lambda v, g=g: int(v * g)),
                                         px[2].point(lambda v, bl=bl: int(v * bl)), px[3].point(lambda v, al=al: int(v * al))))
        canvas.alpha_composite(layer)
        info.append({'name': d['name'], 'sprite': d['sprite'].m_Name, 'order': d['order'], 'z': round(d['z'], 4),
                     'matrix': [round(v, 5) for v in d['matrix']], 'size': [w, h]})
    return canvas, info


def load_env(path):
    import UnityPy
    with open(path, 'rb') as f:
        data = f.read()
    return UnityPy.load(abws.strip_header(data, path))


def render_bundle(path, out_png, scale=2.0, parts_dir=None, json_path=None):
    env = load_env(path)
    parts = collect_parts(env)
    plan = sprites.alpha_plan(env)
    canvas, info = render(parts, scale, plan=plan, env=env)
    os.makedirs(os.path.dirname(out_png) or '.', exist_ok=True)
    canvas.save(out_png)
    if parts_dir:
        os.makedirs(parts_dir, exist_ok=True)
        seen = set()
        cache = sprites.TextureCache()
        for d in parts:
            name = d['sprite'].m_Name
            if name in seen:
                continue
            seen.add(name)
            sprites.sprite_image(d['sprite'], plan, cache, env, d.get('material')).save(os.path.join(parts_dir, name.replace('/', '_') + '.png'))
    if json_path:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=1)
    return len(info), canvas.size


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    scale = float(argv[argv.index('--scale') + 1]) if '--scale' in argv else 2.0
    if argv[0] == '--all':
        src, dest = argv[1], argv[2]
        os.makedirs(dest, exist_ok=True)
        n = 0
        for r, _d, files in os.walk(src):
            for f in sorted(files):
                if not (f.endswith('.fassets') or f.endswith('.fassets.abws')):
                    continue
                name = f.split('.fassets')[0]
                try:
                    count, size = render_bundle(os.path.join(r, f), os.path.join(dest, name + '.png'), scale,
                                                json_path=os.path.join(dest, name + '.json'))
                    print(f'{name}: {count} parts {size[0]}x{size[1]}')
                    n += 1
                except Exception as e:  # noqa: BLE001
                    print(f'{name}: FAILED {e}', file=sys.stderr)
        print(f'{n} characters -> {dest}')
        return 0
    parts_dir = argv[argv.index('--parts') + 1] if '--parts' in argv else None
    json_path = argv[argv.index('--json') + 1] if '--json' in argv else None
    count, size = render_bundle(argv[0], argv[1], scale, parts_dir, json_path)
    print(f'{count} parts -> {argv[1]} ({size[0]}x{size[1]})')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
