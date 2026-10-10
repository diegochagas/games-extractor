import io
import json
import os
import sys
import struct
import tempfile
import unittest

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

import afs  # noqa: E402
import cmps  # noqa: E402
import fjf  # noqa: E402
import msg  # noqa: E402
import tim2  # noqa: E402
import gmi  # noqa: E402
import sebank  # noqa: E402
from sanctuary import names  # noqa: E402
from sanctuary import scenes  # noqa: E402
from tests import fixtures  # noqa: E402


class AfsTest(unittest.TestCase):
    def test_list_and_extract(self):
        data = fixtures.afs([('a.bin', b'hello'), ('b.adx', b'x' * 3000)])
        rows = afs.read_table(io.BytesIO(data))
        self.assertEqual([r['name'] for r in rows], ['a.bin', 'b.adx'])
        self.assertEqual(rows[1]['size'], 3000)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'x.afs')
            with open(path, 'wb') as f:
                f.write(data)
            out = os.path.join(tmp, 'out')
            afs.extract(path, out)
            with open(os.path.join(out, 'a.bin'), 'rb') as f:
                self.assertEqual(f.read(), b'hello')
            self.assertTrue(os.path.exists(os.path.join(out, 'afs_index.json')))

    def test_duplicate_names(self):
        data = fixtures.afs([('v.adx', b'1'), ('v.adx', b'2')])
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'x.afs')
            with open(path, 'wb') as f:
                f.write(data)
            rows = afs.extract(path, os.path.join(tmp, 'out'))
            self.assertEqual([r['file'] for r in rows], ['v.adx', 'v~1.adx'])


class CmpsTest(unittest.TestCase):
    def test_round_trip(self):
        plain = b'FJF\0' + bytes(range(256)) * 3 + b'\0' * 100 + b'abcabcabcabc' * 10
        packed = cmps.pack(plain)
        self.assertTrue(cmps.is_cmps(packed))
        self.assertLess(len(packed), len(plain))
        self.assertEqual(cmps.unpack(packed), plain)

    def test_short_stream_is_padded(self):
        packed = cmps.pack(b'abc' * 10)
        self.assertEqual(cmps.unpack(packed[:-1] if packed[-1:] == b'c' else packed)[:10], b'abcabcabca')


class FjfTest(unittest.TestCase):
    def test_entries(self):
        data = fixtures.fjf([(1, b'one'), (7, b'seven' * 5)])
        flags, ents = fjf.entries(data)
        self.assertEqual(flags, 0x4000)
        self.assertEqual([e[0] for e in ents], [1, 7])
        self.assertEqual(data[ents[1][1]:ents[1][1] + 5], b'seven')
        self.assertTrue(fjf.inside(data))

    def test_index_table_is_not_opened(self):
        data = b'FJF\0' + (4).to_bytes(2, 'little') + (0x4000).to_bytes(2, 'little') + \
            b''.join(x.to_bytes(4, 'little') for x in (0, 0x18800, 0x31000, 0x95000, 0xea000)) + b'\0' * 40
        self.assertFalse(fjf.inside(data))

    def test_extract_recursive(self):
        inner = fixtures.fjf([(0, b'deep')])
        outer = fixtures.fjf([(2, cmps.pack(inner)), (3, b'flat')])
        with tempfile.TemporaryDirectory() as tmp:
            n = fjf.extract_data(outer, tmp, 'x.bin')
            self.assertEqual(n, 2)
            with open(os.path.join(tmp, 'x.bin', '00_2', '00_0'), 'rb') as f:
                self.assertEqual(f.read().rstrip(b'\0'), b'deep')


class Tim2Test(unittest.TestCase):
    def check(self, data):
        pics = tim2.pictures(data)
        self.assertEqual(len(pics), 1)
        self.assertEqual(pics[0].size, (8, 4))
        self.assertEqual(pics[0].getpixel((0, 0)), (255, 0, 0, 255))
        self.assertEqual(pics[0].getpixel((2, 0)), (0, 0, 255, 128))
        self.assertEqual(pics[0].getpixel((3, 0))[3], 0)

    def test_indexed_and_rgba(self):
        im = fixtures.sample_image()
        self.check(fixtures.tim2(im))
        self.check(fixtures.tim2(im, magic=b'TIM3', indexed=False))

    def test_index_table_does_not_recurse(self):
        data = b'FJF\0' + (4).to_bytes(2, 'little') + (0x4000).to_bytes(2, 'little') + \
            b''.join(x.to_bytes(4, 'little') for x in (0, 0x18800, 0x31000, 0x95000, 0xea000)) + b'\0' * 40
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(tim2.convert_file(data, os.path.join(tmp, 'x.jnt')), 0)

    def test_convert_inside_container(self):
        im = fixtures.sample_image()
        data = fixtures.fjf([(1, fixtures.tim2(im)), (2, b'not a picture')])
        with tempfile.TemporaryDirectory() as tmp:
            n = tim2.convert_file(data, os.path.join(tmp, 'x.tpl'))
            self.assertEqual(n, 1)
            self.assertTrue(os.path.exists(os.path.join(tmp, 'x.tpl', '00_1.png')))
            self.assertEqual(Image.open(os.path.join(tmp, 'x.tpl', '00_1.png')).size, (8, 4))


class MsgTest(unittest.TestCase):
    def test_languages_and_accents(self):
        data = fixtures.msg_file([['Continuar jogo', 'Vocぐ nげo\n\x01pode'], ['Resume game', 'You cannot']])
        tables = msg.read(data)
        self.assertEqual(tables['pt'], ['Continuar jogo', 'Você não\n\x01pode'])
        self.assertEqual(tables['en'], ['Resume game', 'You cannot'])

    def test_bare_block(self):
        data = fixtures.msg_block(['   ', 'x'])
        self.assertEqual(msg.read(data), {'pt': ['   ', 'x']})

    def test_long_strings(self):
        data = fixtures.msg_file([['a' * 600, 'b' * 600, 'c']])
        self.assertEqual(len(msg.read(data)['pt']), 3)


class ScenesTest(unittest.TestCase):
    def test_parse(self):
        data = fixtures.script([
            (19, 12, ['comic\\main\\00\\se_demo_00.bin']),
            (0, 0, [1, 'comic\\main\\00\\00_1_1.bin', 'FILENAME_NULL', 1, 1, 1]),
            (6, 2, [1, 10.0]),
            (0, 0, [5, 'comic\\main\\00\\00_1_2.bin', 'FILENAME_NULL', 1, 1, 1]),
            (6, 2, [5, 4.0]),
            (24, 13, [0.04, 'bgm\\bgm_25.adx', 0, 0.0]),
            (15, 8, ['comic\\main\\00\\msgDM00']),
            (21, 16, [2.0, 'comic\\main\\00\\story_e06_00_00000.adx', -1, 0, -1]),
            (17, 10, [2.0, 0]), (17, 10, [5.0, 1]), (18, 10, [10.0]), (37, 10, [10.0]),
            (21, 16, [0.5, 'comic\\main\\00\\story_00_00_00100.adx', -1, 0, -1]),
            (17, 10, [0.5, 2]), (18, 10, [4.0]), (37, 10, [4.0])])
        cmds = scenes.commands(data)
        self.assertEqual(cmds[0][0], 19)
        self.assertEqual(cmds[2][2], [1, 10.0])
        scene = scenes.parse('demo00.bin', data)
        self.assertEqual(scene['kind'], 'story')
        self.assertEqual(scene['text_table'], 'msgDM00')
        self.assertEqual(scene['bgm'], ['bgm_25.adx'])
        self.assertEqual([p['seconds'] for p in scene['pages']], [10.0, 4.0])
        self.assertEqual([(ln['page'], ln['voice'], ln['text_lines']) for ln in scene['lines']],
                         [(1, 'story_e06_00_00000.adx', [0, 1]), (5, 'story_00_00_00100.adx', [2])])

    def test_speaker(self):
        self.assertEqual(names.speaker('story_17_if09_00000.adx'), ('17', 'Shina'))
        self.assertEqual(names.speaker('STORY_09_18_00000.adx'), ('09', 'Shaka'))
        self.assertEqual(names.speaker('story_e06_00_00000.adx'), ('e06', 'Narrador'))
        self.assertEqual(names.speaker('bgm_01.adx'), ('', ''))


class TranscriptTest(unittest.TestCase):
    def test_glossary(self):
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'sanctuary', 'story'))
        import transcript
        self.assertEqual(transcript.clean(' A casa de Arias , disse China ao Iolos.'), 'A casa de Áries, disse Shina ao Aiolos.')
        with open(os.path.join(os.path.dirname(HERE), 'sanctuary', 'story', 'fixes.json'), encoding='utf-8') as f:
            self.assertEqual(json.load(f)['story_00_if09_00500'], 'Shiryu, deixe esta comigo.')


if __name__ == '__main__':
    unittest.main()


class GmiTest(unittest.TestCase):
    def test_parse_and_bind_pose(self):
        model = gmi.parse(fixtures.gmi())
        self.assertEqual([b['name'] for b in model['bones']], ['root', 'child'])
        part = model['parts'][0]
        self.assertEqual(part['palette'], [0, 1])
        self.assertEqual(part['faces'], [(0, 1, 2), (1, 3, 2)])
        glb = gmi.to_glb(model)
        self.assertEqual(glb[:4], b'glTF')
        n = struct.unpack_from('<I', glb, 12)[0]
        doc = json.loads(glb[20:20 + n])
        pos_acc = doc['accessors'][doc['meshes'][0]['primitives'][0]['attributes']['POSITION']]
        self.assertAlmostEqual(pos_acc['min'][0], -2.0, places=5)      # child bone at +1 on x, then mirrored to face the front
        self.assertAlmostEqual(pos_acc['max'][0], -1.0, places=5)

    def test_raw_keeps_coordinates(self):
        model = gmi.parse(fixtures.gmi())
        glb = gmi.to_glb(model, raw=True)
        n = struct.unpack_from('<I', glb, 12)[0]
        doc = json.loads(glb[20:20 + n])
        pos_acc = doc['accessors'][0]
        self.assertAlmostEqual(pos_acc['max'][0], 0.0, places=5)


class SebankTest(unittest.TestCase):
    def test_samples_and_rate(self):
        silence = bytes([0x00, 0x00] + [0] * 14) * 4 + bytes([0x00, 0x01] + [0] * 14)
        bank = fixtures.sebank([('星矢_20.aif', 0xF0D9, silence), ('b_22.aif', 0xF289, silence)])
        items = sebank.samples(bank)
        self.assertEqual([(n, r) for n, r, _ in items], [('星矢_20.aif', 20000), ('b_22.aif', 22050)])
        self.assertEqual(len(items[0][2]), len(silence))
        pcm = sebank.vag_decode(items[0][2])
        self.assertEqual(len(pcm), 28 * 5)
        self.assertTrue(all(v == 0 for v in pcm))

    def test_decode_tone(self):
        block = bytes([0x00, 0x00]) + bytes([0x11] * 14)                  # nibbles of +1 at shift 0
        pcm = sebank.vag_decode(block * 2)
        self.assertEqual(pcm[0], 4096)
