"""Sprite and texture decoding shared by dump.py and puppet.py.

Most character atlases have no alpha channel (ETC_RGB4 / ETC2_RGB). The mask lives either
  * in the other half of the same texture (material colour `_alphaTexUVOffset`: 0.5 in U = right
    half, 0.5 in V = the top half of the picture, shaders "alphaOnePic"), or
  * in a second texture given by the material's `_alphaTex` (usually named `<atlas>_alp`,
    `<atlas>-alp`, `<atlas>_1`..., sometimes smaller than the atlas; shaders "alphaTwoPic").
A bundle can mix layouts (Dohko_35: a split atlas plus two RGBA textures on Sprites-Default).
`alpha_plan(env)` collects the materials, name pairs and texture formats; `sprite_image` decides
per sprite (its renderer's material first, then the texture's own alpha, then the atlas layout).
"""

ALPHA_SUFFIXES = ('_alp', '-alp', '_alpha', '_1alp', '_2alpha')


def _typetree(obj):
    try:
        return obj.read_typetree()
    except Exception:  # noqa: BLE001
        return None


def material_info(env):
    """{material path id: {'alpha_tex': path id or 0, 'offset': (du, dv) or None}}."""
    out = {}
    for obj in env.objects:
        if obj.type.name != 'Material':
            continue
        tree = _typetree(obj)
        if not tree:
            continue
        props = tree.get('m_SavedProperties', {})
        alpha_tex = 0
        for name, env_ in props.get('m_TexEnvs', []):
            if name.lower() == '_alphatex':
                alpha_tex = env_.get('m_Texture', {}).get('m_PathID', 0) or 0
        offset = None
        for name, color in props.get('m_Colors', []):
            if name == '_alphaTexUVOffset':
                du, dv = float(color.get('r', 0)), float(color.get('g', 0))
                if du or dv:
                    offset = (du, dv)
        out[obj.path_id] = {'alpha_tex': alpha_tex, 'offset': offset}
    return out


def alpha_offset(env):
    """The `_alphaTexUVOffset` of the bundle's materials, or None."""
    for info in material_info(env).values():
        if info['offset']:
            return info['offset']
    return None


def pair_alpha_textures(names):
    """{colour texture name: alpha texture name} for names like ['Siegfried', 'Siegfried_alp']."""
    lookup = {n.lower(): n for n in names}
    pairs = {}
    for n in names:
        for suffix in ALPHA_SUFFIXES:
            if n.lower().endswith(suffix):
                base = n[:-len(suffix)]
                if base.lower() in lookup:
                    pairs[lookup[base.lower()]] = n
    return pairs


def alpha_plan(env):
    """Everything sprite_image needs: {'offset', 'alpha_of' {colour pid: alpha obj}, 'materials',
    'textures' {pid: obj}, 'has_alpha' {pid: bool} (filled lazily)}."""
    objs = {o.path_id: o for o in env.objects}
    textures = {pid: o for pid, o in objs.items() if o.type.name == 'Texture2D'}
    names = {}
    for pid, o in textures.items():
        try:
            names[pid] = o.read().m_Name
        except Exception:  # noqa: BLE001
            continue
    pairs = pair_alpha_textures(list(names.values()))
    by_name = {}
    for pid, name in names.items():
        by_name.setdefault(name, pid)
    alpha_of = {by_name[c]: objs[by_name[a]] for c, a in pairs.items() if c in by_name and a in by_name}
    materials = material_info(env)
    # materials with an _alphaTex and a single colour texture left: pair by elimination
    alpha_ids = {m['alpha_tex'] for m in materials.values() if m['alpha_tex'] in textures}
    colours = [pid for pid in textures if pid not in alpha_ids and pid not in alpha_of]
    if len(colours) == 1 and len(alpha_ids) == 1:
        alpha_of[colours[0]] = objs[next(iter(alpha_ids))]
    offset = next((m['offset'] for m in materials.values() if m['offset']), None)
    return {'offset': offset, 'alpha_of': alpha_of, 'materials': materials, 'textures': textures, 'has_alpha': {}}


class TextureCache:
    """Decoded textures by path id, so the 2048x2048 atlas is decoded once per bundle."""

    def __init__(self):
        self.images = {}

    def get(self, texture_obj):
        key = texture_obj.path_id
        if key not in self.images:
            self.images[key] = texture_obj.read().image.convert('RGBA')
        return self.images[key]


def texture_has_alpha(image):
    """False when the decoded picture is fully opaque (RGB-only formats decode to alpha 255)."""
    return image.getchannel('A').getextrema() != (255, 255)


def guess_offset(image):
    """(du, dv) when one half of a fully opaque atlas is a grey mask (R = G = B), else None."""
    from PIL import ImageChops
    w, h = image.size

    def is_grey(region):
        r, g, b = region.convert('RGB').split()
        diff = ImageChops.add(ImageChops.difference(r, g), ImageChops.difference(g, b))
        hist = diff.histogram()
        total = sum(hist)
        return bool(total) and sum(hist[:12]) / total > 0.98

    right = image.crop((w // 2, 0, w, h))
    if is_grey(right) and not is_grey(image.crop((0, 0, w // 2, h))):
        return (0.5, 0.0)
    top = image.crop((0, 0, w, h // 2))
    if is_grey(top) and not is_grey(image.crop((0, h // 2, w, h))):
        return (0.0, 0.5)
    return None


def merge_alpha(image, offset):
    """RGBA picture of a split atlas: colour half + alpha half -> one half-size RGBA image."""
    du, dv = offset
    w, h = image.size
    if du:
        half = int(w * du)
        colour = image.crop((0, 0, half, h))
        alpha = image.crop((half, 0, half * 2, h)).convert('L')
    else:  # Unity's V axis points up: the colour half is the bottom of the picture, the mask the top
        half = int(h * dv)
        colour = image.crop((0, h - half, w, h))
        alpha = image.crop((0, h - half * 2, w, h - half)).convert('L')
    colour.putalpha(alpha)
    return colour


def with_alpha_texture(colour, alpha):
    """RGBA picture from a colour picture and an alpha picture (resized when the sizes differ)."""
    colour = colour.convert('RGBA')
    mask = alpha.convert('L')
    if mask.size != colour.size:
        mask = mask.resize(colour.size)
    colour.putalpha(mask)
    return colour


def layout_for(plan, tex_obj, atlas, material_id=None):
    """('texture', alpha object) | ('offset', (du, dv)) | ('plain', None) for one atlas."""
    mat = plan['materials'].get(material_id) if material_id else None
    if mat and mat['alpha_tex'] in plan['textures']:
        return 'texture', plan['textures'][mat['alpha_tex']]
    if mat and mat['offset']:
        return 'offset', mat['offset']
    if tex_obj.path_id in plan['alpha_of']:
        return 'texture', plan['alpha_of'][tex_obj.path_id]
    has_alpha = plan['has_alpha'].get(tex_obj.path_id)
    if has_alpha is None:
        has_alpha = plan['has_alpha'][tex_obj.path_id] = texture_has_alpha(atlas)
    if has_alpha:
        return 'plain', None
    if plan['offset']:
        return 'offset', plan['offset']
    guessed = guess_offset(atlas)
    if guessed:
        return 'offset', guessed
    return 'plain', None


def texture_image(tex_obj, plan, cache):
    """The whole Texture2D as RGBA, with its mask merged in when the bundle keeps it apart."""
    atlas = cache.get(tex_obj)
    kind, extra = layout_for(plan, tex_obj, atlas)
    if kind == 'texture':
        return with_alpha_texture(atlas, cache.get(extra))
    if kind == 'offset':
        return merge_alpha(atlas, extra)
    return atlas


def sprite_image(sprite, plan=None, cache=None, env=None, material_id=None):
    """The picture of a Sprite with its alpha rebuilt (UnityPy's own crop when there is no plan)."""
    if not plan or env is None:
        return sprite.image.convert('RGBA')
    rd = sprite.m_RD
    tex_obj = plan['textures'].get(rd.texture.path_id)
    if tex_obj is None:
        return sprite.image.convert('RGBA')
    cache = cache or TextureCache()
    atlas = cache.get(tex_obj)
    w, h = atlas.size
    rect = rd.textureRect
    x, y, rw, rh = int(round(rect.x)), int(round(rect.y)), int(round(rect.width)), int(round(rect.height))
    top = h - (y + rh)  # Unity rects have their origin at the bottom-left of the texture
    colour = atlas.crop((x, top, x + rw, top + rh))
    kind, extra = layout_for(plan, tex_obj, atlas, material_id)
    if kind == 'texture':
        alpha_atlas = cache.get(extra)
        if alpha_atlas.size != atlas.size:
            alpha_atlas = alpha_atlas.resize(atlas.size)
        alpha = alpha_atlas.crop((x, top, x + rw, top + rh)).convert('L')
    elif kind == 'offset':
        dx, dy = int(w * extra[0]), int(h * extra[1])
        atop = top - dy if dy else top
        alpha = atlas.crop((x + dx, atop, x + dx + rw, atop + rh)).convert('L')
    else:
        return colour
    colour.putalpha(alpha)
    # packed sprites may be stored rotated (settingsRaw bits 2..4); the game never rotates its
    # character parts (checked on the role atlases), so no rotation is applied here
    return colour
