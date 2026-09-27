import contextlib
import io
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))


def write(path, data):
    with open(path, 'wb' if isinstance(data, bytes) else 'w', **({} if isinstance(data, bytes) else {'encoding': 'utf-8'})) as f:
        f.write(data)


def read(path):
    with open(path, 'rb') as f:
        return f.read()


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import fixtures  # noqa: E402
from omega import models, names, story_dump, translate  # noqa: E402
from omega.story import story_prep  # noqa: E402


def script(title, lines, resources=()):
    code = b''.join(b'\x01\x01\x87\x03' + struct.pack('<I', i) + b'\x87\x01' + bytes([who]) +
                    b'\x87\x83\0\0\0\0\x8e\x0c' for i, who in lines)
    table = ('\u25a1%s\n' % title).encode('shift_jis') + b'\0' + b''.join(r.encode() + b'\0' for r in resources)
    return bytes(32) + code + b'\x82ACT1\0' + table + ('\u25a0%s' % title).encode('shift_jis') + b'\0' + bytes(16)


class Dump:
    """A two-scene dump in a temporary folder."""

    def __init__(self, tmp):
        self.files, self.usr, self.out = (os.path.join(tmp, n) for n in ('files', 'usr', 'dump'))
        scenes = {'50_01': ('光牙編.VS龍峰(50_01)', [(100000, 0), (100010, 25), (100020, 2)],
                            ['common/background/adv_bg_003.pac', 'bgm/bgm_adv_daily.adx', 'common/image/still_st_01.pac']),
                  '50_11': ('光牙編.VS龍峰(50_11)', [(100300, 2)], [])}
        text = {'50_01': [(100000, 'はぁ'), (100010, '<小宇宙:コスモ>'), (100020, '光牙君！'), (100030, '不要')],
                '50_11': [(100300, '負けたよ')]}
        for name, (title, lines, res) in scenes.items():
            folder = os.path.join(self.files, 'event', 'script', name + '.pac')
            os.makedirs(folder)
            Path(os.path.join(folder, name.upper() + '.E')).write_bytes(script(title, lines, res))
            Path(os.path.join(folder, name.upper() + '_JP.BTX')).write_bytes(fixtures.btx(text[name]))
        sound = os.path.join(self.usr, 'event', 'sound', '50')
        os.makedirs(sound)
        for n in ('01_00000_kog', '01_00010_sot', '01_00020_ryo', '01_00300_ryo', '01_02610_ate'):
            write(os.path.join(sound, n + '.ahx'), b'')
        os.makedirs(os.path.join(self.files, 'btx'))
        write(os.path.join(self.files, 'btx', 'menu_jp.btx'), fixtures.btx([(0, 'はい'), (1, 'はい'), (2, '12')]))


class StoryTest(unittest.TestCase):
    def test_names(self):
        self.assertEqual(len(names.CHARACTERS), 24)
        self.assertEqual(names.SCRIPT_CODES[15], 'sot')
        self.assertEqual(names.SCRIPT_CODES[24:], ['ate', 'who', 'man'])
        self.assertEqual(names.speaker('KOGV2'), ('光牙', 'Kouga'))

    def test_dump_and_translation(self):
        import btx
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            d = Dump(tmp)
            self.assertEqual(btx.main(['btx.py', 'dump', d.files, os.path.join(d.out, 'text')]), 0)
            self.assertEqual(story_dump.main(['x', d.files, d.usr, os.path.join(d.out, 'text')]), 0)
            story = load(os.path.join(d.out, 'text', 'story.json'))
            first = story['scripts'][0]
            self.assertEqual((first['script'], first['opponent_jp'], first['phase']), ('50_01', '龍峰', 'before'))
            self.assertEqual(first['backgrounds'], ['common/background/adv_bg_003.pac'])
            self.assertEqual([(l['id'], l['speaker'], l.get('identity')) for l in first['lines']],
                             [(100000, 'Kouga', None), (100010, '???', 'Sorento'), (100020, 'Ryuho', None)])
            self.assertEqual(first['lines'][0]['voice'], 'event/sound/50/01_00000_kog.ahx')
            self.assertEqual([u['id'] for u in first['unreferenced']], [100030])
            self.assertEqual(story['voices_without_text'], ['event/sound/50/01_02610_ate.ahx'])

            self.assertEqual(translate.main(['x', 'export', d.out]), 0)
            folder = os.path.join(d.out, 'text', 'translation')
            rows = load(os.path.join(folder, 'in', 'story_50_kouga.json'))
            self.assertEqual([r['key'] for r in rows], ['50_01:title', '50_01:100000', '50_01:100010', '50_01:100020',
                                                        '50_01:100030', '50_11:title', '50_11:100300'])
            system = load(os.path.join(folder, 'in', 'system.json'))
            self.assertEqual([r['key'] for r in system], ['btx/menu_jp.btx#0'])   # repeated and numeric rows left out
            self.assertEqual(translate.check(d.out), 8)                            # nothing translated yet
            done = {r['key']: 'texto' for r in rows}
            done['50_01:100010'] = '<小宇宙:コスモ>'
            write(os.path.join(folder, 'out', 'story_50_kouga.json'), json.dumps(done))
            write(os.path.join(folder, 'out', 'system.json'), json.dumps({'btx/menu_jp.btx#0': 'Sim'}))
            self.assertEqual(translate.check(d.out), 2)                            # ruby markup + Japanese left
            done['50_01:100010'] = 'Cosmo'
            write(os.path.join(folder, 'out', 'story_50_kouga.json'), json.dumps(done))
            self.assertEqual(translate.check(d.out), 0)
            self.assertEqual(translate.main(['x', 'merge', d.out]), 0)
            merged = load(os.path.join(folder, 'pt-BR.json'))
            self.assertEqual((merged['btx/menu_jp.btx#0'], merged['btx/menu_jp.btx#1'], merged['50_01:100010']),
                             ('Sim', 'Sim', 'Cosmo'))

    def test_markup(self):
        self.assertEqual(story_prep.plain('<c#ff1f75ff>P<c>・<聖衣:クロス>\r\nx'), 'P・聖衣\nx')
        self.assertEqual(story_prep.ruby('<小宇宙:コスモ>を\r\n燃やせ'), '小宇宙（コスモ）を燃やせ')

    def test_attach_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'NORMAL.ATP')
            entry = struct.pack('<9f', 1, 2, 3, 0, 0, 0, 1, 1, 1) + struct.pack('<II', 14, 210)
            write(path, b'PADH' + struct.pack('<I', 0) + b'CLKC' + struct.pack('<II', 0, 1) + b'CLDH' +
                                   struct.pack('<II', 0, 1) + entry)
            p = models.attach_points(path)[210]
            self.assertEqual((p['bone'], p['translation'], list(p['rotation'])), (14, (1, 2, 3), [0, 0, 0, 1]))


if __name__ == '__main__':
    unittest.main()
