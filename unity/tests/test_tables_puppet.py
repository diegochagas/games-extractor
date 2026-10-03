import json
import math
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import dump  # noqa: E402
import puppet  # noqa: E402
import sprites  # noqa: E402
import tables  # noqa: E402

TABLE = (
    'STR\tINT\tFLOAT\tSTRARR\tINTARR2\tVECTOR\n'
    '编号\t名字\t倍率\t技能\t消耗\t坐标\n'
    'id\tname\trate\tskills\tcost\tpos\n'
    '1050\t5\t1.5\ta+b\t1+2|3+4\t3.08,1.25\n'
    '\n'
    '1051\t\t\t\t\t\n'
)


class TablesTest(unittest.TestCase):
    def test_parse(self):
        columns, records = tables.parse_table(TABLE)
        self.assertEqual(columns, [['id', '编号', 'STR'], ['name', '名字', 'INT'], ['rate', '倍率', 'FLOAT'],
                                   ['skills', '技能', 'STRARR'], ['cost', '消耗', 'INTARR2'], ['pos', '坐标', 'VECTOR']])
        self.assertEqual(records[0], {'id': '1050', 'name': 5, 'rate': 1.5, 'skills': ['a', 'b'],
                                      'cost': [[1, 2], [3, 4]], 'pos': '3.08,1.25'})
        self.assertEqual(records[1], {'id': '1051', 'name': None, 'rate': None, 'skills': [], 'cost': [], 'pos': ''})
        self.assertEqual(tables.convert_value('x', 'INT'), 'x')  # malformed cells stay as text

    def test_convert_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'txt')
            os.makedirs(src)
            with open(os.path.join(src, 'RoleConfig.txt'), 'w', encoding='utf-8') as f:
                f.write(TABLE)
            with open(os.path.join(src, 'LanguagePackage.txt'), 'w', encoding='utf-8') as f:
                f.write('//comment\nsure=确定\n')
            out = os.path.join(tmp, 'json')
            self.assertEqual(tables.convert_dir(src, out), 1)
            with open(os.path.join(out, 'RoleConfig.json'), encoding='utf-8') as f:
                self.assertEqual(json.load(f)[0]['skills'], ['a', 'b'])
            with open(os.path.join(out, '_columns.json'), encoding='utf-8') as f:
                self.assertEqual(list(json.load(f)), ['RoleConfig'])


class PuppetMathTest(unittest.TestCase):
    def test_quaternion_and_affine(self):
        s = math.sin(math.radians(45)), math.cos(math.radians(45))
        self.assertAlmostEqual(puppet.quat_to_z_angle(0, 0, s[0], s[1]), 90.0, places=5)
        self.assertAlmostEqual(puppet.quat_to_z_angle(0, 0, 0, 1), 0.0)
        m = puppet.local_matrix((1, 2), 90, (1, 1))
        x, y = puppet.apply(m, 1, 0)
        self.assertAlmostEqual(x, 1.0)
        self.assertAlmostEqual(y, 3.0)
        parent = puppet.local_matrix((10, 0), 0, (2, 2))
        world = puppet.compose(parent, puppet.local_matrix((1, 0), 0, (1, 1)))
        self.assertEqual([round(v, 6) for v in puppet.apply(world, 0, 0)], [12.0, 0.0])
        self.assertEqual([round(v, 6) for v in puppet.apply(world, 1, 1)], [14.0, 2.0])

    def test_render_order_and_canvas(self):
        from PIL import Image

        class Vec:
            def __init__(self, x, y):
                self.x, self.y = x, y

        class Sprite:
            def __init__(self, name, color):
                self.m_Name = name
                self.image = Image.new('RGBA', (10, 10), color)
                self.m_Pivot = Vec(0.5, 0.5)
                self.m_PixelsToUnits = 100.0

        parts = [
            {'name': 'back', 'sprite': Sprite('b', (255, 0, 0, 255)), 'matrix': [1, 0, 0, 1, 0, 0], 'z': 1.0, 'order': 0,
             'depth': 0, 'color': (1, 1, 1, 1), 'flip_x': False, 'flip_y': False},
            {'name': 'front', 'sprite': Sprite('f', (0, 0, 255, 255)), 'matrix': [1, 0, 0, 1, 0.05, 0], 'z': -1.0, 'order': 0,
             'depth': 0, 'color': (1, 1, 1, 1), 'flip_x': False, 'flip_y': False},
        ]
        parts.sort(key=lambda d: (d['order'], -d['z']))
        canvas, info = puppet.render(parts, scale=1.0, margin=0)
        self.assertEqual([i['name'] for i in info], ['back', 'front'])
        self.assertEqual(canvas.size, (15, 10))
        self.assertEqual(canvas.getpixel((1, 5))[:3], (255, 0, 0))    # only the back part here
        self.assertEqual(canvas.getpixel((7, 5))[:3], (0, 0, 255))    # the front part covers the overlap


class SpritesTest(unittest.TestCase):
    def test_alpha_pairs_and_merge(self):
        from PIL import Image
        self.assertEqual(sprites.pair_alpha_textures(['Siegfried', 'Siegfried_alp', 'ring', 'Thor01', 'Thor01-alp', '2005', '2005_alpha']),
                         {'Siegfried': 'Siegfried_alp', 'Thor01': 'Thor01-alp', '2005': '2005_alpha'})
        opaque = Image.new('RGBA', (8, 8), (200, 30, 30, 255))
        self.assertFalse(sprites.texture_has_alpha(opaque))
        self.assertTrue(sprites.texture_has_alpha(Image.new('RGBA', (2, 2), (0, 0, 0, 0))))
        split = opaque.copy()
        split.paste((90, 90, 90, 255), (4, 0, 8, 8))     # grey right half = mask
        self.assertEqual(sprites.guess_offset(split), (0.5, 0.0))
        vsplit = opaque.copy()
        vsplit.paste((90, 90, 90, 255), (0, 0, 8, 4))    # grey top half = mask
        self.assertEqual(sprites.guess_offset(vsplit), (0.0, 0.5))
        self.assertIsNone(sprites.guess_offset(opaque))
        self.assertEqual(sprites.pair_alpha_textures(['Hilda']), {})
        atlas = Image.new('RGBA', (4, 2), (255, 0, 0, 255))
        atlas.putpixel((2, 0), (0, 0, 0, 255))   # alpha half: black = transparent
        atlas.putpixel((3, 0), (255, 255, 255, 255))
        merged = sprites.merge_alpha(atlas, (0.5, 0))
        self.assertEqual(merged.size, (2, 2))
        self.assertEqual(merged.getpixel((0, 0)), (255, 0, 0, 0))
        self.assertEqual(merged.getpixel((1, 0)), (255, 0, 0, 255))
        tall = Image.new('RGBA', (2, 4), (0, 0, 255, 255))
        tall.putpixel((0, 0), (255, 255, 255, 255))   # mask (top half): opaque at (0,0), transparent at (1,0)
        tall.putpixel((1, 0), (0, 0, 0, 255))
        vert = sprites.merge_alpha(tall, (0, 0.5))
        self.assertEqual(vert.size, (2, 2))
        self.assertEqual(vert.getpixel((0, 0)), (0, 0, 255, 255))
        self.assertEqual(vert.getpixel((1, 0)), (0, 0, 255, 0))
        colour = Image.new('RGB', (2, 2), (0, 255, 0))
        alpha = Image.new('L', (4, 4), 128)
        self.assertEqual(sprites.with_alpha_texture(colour, alpha).getpixel((0, 0)), (0, 255, 0, 128))


class DumpHelpersTest(unittest.TestCase):
    def test_names_and_bundles(self):
        self.assertEqual(dump.safe_name(' a/b\\c ', 'x'), 'a_b_c')
        self.assertEqual(dump.safe_name('', 'Texture2D_5'), 'Texture2D_5')
        used = set()
        self.assertEqual(dump.unique('/o/a.png', used), '/o/a.png')
        self.assertEqual(dump.unique('/o/a.png', used), '/o/a_1.png')
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, 'role'))
            for name in ('role/hilda.fassets', 'role/hilda.fassets.manifest', 'config/config.fassets.abws', 'readme.txt'):
                os.makedirs(os.path.dirname(os.path.join(tmp, name)), exist_ok=True)
                with open(os.path.join(tmp, name), 'wb') as f:
                    f.write(b'')
            self.assertEqual([rel for _, rel in dump.find_bundles(tmp)], ['config/config.fassets.abws', 'role/hilda.fassets'])
            self.assertEqual([rel for _, rel in dump.find_bundles(tmp, 'role/')], ['role/hilda.fassets'])
            self.assertEqual([rel for _, rel in dump.find_bundles(tmp, wanted={'config/config.fassets'})], ['config/config.fassets.abws'])


if __name__ == '__main__':
    unittest.main()
