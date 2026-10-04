import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import art  # noqa: E402


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


def png(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'png')


class ArtTest(unittest.TestCase):
    def test_plan_and_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, 'assets')
            write_json(os.path.join(tmp, 'tables', 'StoleConfig.json'), [{'icon': 'StoleIcon/1001', 'name': '天马座圣衣'}])
            write_json(os.path.join(tmp, 'tables', 'ItemConfig.json'), [{'id': '2000', 'icon': 'ItemIcon/2003', 'name': '候补者外衣'}])
            stole = os.path.join(a, 'texture', 'stoleicon', '_current_.fassets')
            write_json(os.path.join(stole, 'objects.json'), [
                {'type': 'Texture2D', 'name': '1001', 'file': '1001.png', 'width': 500, 'height': 500},
                {'type': 'Texture2D', 'name': '10013', 'file': '10013.png', 'width': 100, 'height': 100},
                {'type': 'Sprite', 'name': '1001', 'file': 'sprites/1001.png', 'width': 500, 'height': 500},
                {'type': 'Texture2D', 'name': 'tiny', 'file': 'tiny.png', 'width': 4, 'height': 4}])
            for f in ('1001.png', '10013.png', 'sprites/1001.png', 'tiny.png'):
                png(os.path.join(stole, f))
            item = os.path.join(a, 'texture', 'itemicon', '_current_.fassets')
            write_json(os.path.join(item, 'objects.json'), [{'type': 'Texture2D', 'name': '2003', 'file': '2003.png', 'width': 100, 'height': 100}])
            png(os.path.join(item, '2003.png'))
            atlas = os.path.join(a, 'atlas', 'common', '_current_.fassets')
            write_json(os.path.join(atlas, 'objects.json'), [
                {'type': 'Texture2D', 'name': 'CommonTex', 'file': 'CommonTex.png', 'width': 1024, 'height': 2048},
                {'type': 'Sprite', 'name': 'btn', 'file': 'sprites/btn.png', 'width': 50, 'height': 20}])
            png(os.path.join(atlas, 'CommonTex.png'))
            png(os.path.join(atlas, 'sprites', 'btn.png'))
            fx = os.path.join(a, 'effect', 'x', '_current_.fassets')
            write_json(os.path.join(fx, 'objects.json'), [{'type': 'Texture2D', 'name': 'ring', 'file': 'ring.png', 'width': 256, 'height': 256}])
            png(os.path.join(fx, 'ring.png'))
            rels = sorted(rel for _src, rel in art.plan(tmp))
            self.assertEqual(rels, ['Interface e eventos/atlas/common/btn.png', 'Itens/itemicon/2003 候补者外衣.png',
                                    'Vestimentas/stoleicon/1001 天马座圣衣.png', 'Vestimentas/stoleicon/10013 天马座圣衣 - peça 3.png'])
            out = os.path.join(tmp, 'out')
            self.assertEqual(art.copy(tmp, out), (4, 4))
            self.assertEqual(art.copy(tmp, out), (0, 4))   # incremental
            self.assertEqual(art.category_of('texture', 'anniversary'), 'Interface e eventos')
            self.assertEqual(art.category_of('scene', '1001'), 'Cenários')


if __name__ == '__main__':
    unittest.main()
