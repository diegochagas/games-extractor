import contextlib
import io
import os
import struct
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import btx  # noqa: E402
import fixtures  # noqa: E402
import fnt  # noqa: E402
import gim  # noqa: E402
import iso  # noqa: E402
import pac  # noqa: E402
import psmf  # noqa: E402
import subtitles  # noqa: E402
from omega import patch, pictures  # noqa: E402

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def write(path, data):
    with open(path, 'wb') as f:
        f.write(data)


def read(path):
    with open(path, 'rb') as f:
        return f.read()


class WritersTest(unittest.TestCase):
    def test_btx_write(self):
        old = fixtures.btx([(100000, 'はぁ'), (100010, 'x'), (7, '')])
        new = btx.write(old, {100010: 'Nossa, que calor.\r\nSegunda linha', 999: 'ignored'})
        self.assertEqual(btx.read(new), [(100000, 'はぁ'), (100010, 'Nossa, que calor.\r\nSegunda linha'), (7, '')])

    def test_pac_build(self):
        inner = fixtures.pac([('A.GIM', b'aaaa'), ('B.GIM', b'bb')], total_without_header=True)
        outer = fixtures.pac([('NORMAL.PAC', inner), ('X.TXT', b'text'), ('X.TXT', b'again')])
        self.assertEqual(pac.build(outer, {}), outer)
        new = pac.build(outer, {'NORMAL.PAC/B.GIM': b'a much longer file', 'X~1.TXT': b'!'})
        self.assertTrue(pac.is_pac(new))
        self.assertEqual(dict(pac.walk(new)), {'NORMAL.PAC/A.GIM': b'aaaa', 'NORMAL.PAC/B.GIM': b'a much longer file',
                                               'X.TXT': b'text', 'X~1.TXT': b'!'})

    def test_gim_encode(self):
        rows = np.zeros((8, 32), dtype=np.uint8)
        like = fixtures.gim(fixtures.gim_block(5, 1, 32, 8, 8, rows.tobytes()),
                            fixtures.gim_block(3, 0, 16, 1, 32, bytes(64), 1, 1))
        im = Image.new('RGBA', (32, 8), (0, 0, 0, 0))
        im.paste((255, 0, 0, 255), (4, 2, 20, 6))
        out = gim.encode(im, like)
        self.assertEqual(len(out), len(like))
        back = gim.decode(out)[0]
        self.assertEqual((back.size, back.getpixel((0, 0))[3], back.getpixel((10, 3))), ((32, 8), 0, (255, 0, 0, 255)))
        wide = gim.decode(gim.encode(Image.new('RGBA', (64, 16), (0, 0, 255, 255)), like))[0]
        self.assertEqual((wide.size, wide.getpixel((63, 15))), ((64, 16), (0, 0, 255, 255)))


class FontTest(unittest.TestCase):
    def test_build_and_read(self):
        glyphs = fnt.render(FONT, 13, 'Aç ')
        data = fnt.build(glyphs + fnt.render(FONT, 13, ''.join(chr(0x100 + i) for i in range(70))))
        back = fnt.read(data)
        self.assertEqual(len(back), 73)
        self.assertEqual([g['code'] for g in back], sorted(g['code'] for g in back))
        self.assertEqual(len(data), 16 + 73 * 64 + 2 * 8192)               # two pages of 64 glyphs
        a = [g for g in back if g['code'] == ord('A')][0]
        self.assertGreater(a['w'], 5)
        self.assertGreater(int(a['bitmap'].max()), 10)
        self.assertEqual(fnt.build(back), data)
        space = [g for g in back if g['code'] == 32][0]
        self.assertEqual((space['w'], int(space['bitmap'].max())), (0, 0))
        self.assertGreater(fnt.advance(space), 2)

    def test_same_character_twice(self):
        with self.assertRaises(ValueError):
            fnt.build(fnt.render(FONT, 13, 'AA'))


class IsoTest(unittest.TestCase):
    def test_replace(self):
        files = {'A.BIN': b'a' * 3000, 'DIR/B.BIN': b'b' * 100, 'DIR/C.BIN': b'c' * 5000}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'test.iso')
            write(path, fixtures.iso(files))
            found = {p: (lba, size) for p, _o, lba, size, d in iso.listing(path) if not d}
            self.assertEqual(sorted(found), ['A.BIN', 'DIR/B.BIN', 'DIR/C.BIN'])
            done = iso.replace(path, {'dir/b.bin': b'B' * 9000, 'A.BIN': b'A' * 2500})
            self.assertEqual(sorted(done), [('A.BIN', 'place', 2500), ('DIR/B.BIN', 'end', 9000)])
            after = {p: (lba, size) for p, _o, lba, size, d in iso.listing(path) if not d}
            self.assertEqual(after['DIR/C.BIN'], found['DIR/C.BIN'])             # untouched files stay
            self.assertEqual(after['A.BIN'], (found['A.BIN'][0], 2500))
            data = read(path)
            self.assertEqual(len(data) % 2048, 0)
            self.assertEqual(struct.unpack_from('<I', data, 16 * 2048 + 80)[0], len(data) // 2048)
            for name, want in (('A.BIN', b'A' * 2500), ('DIR/B.BIN', b'B' * 9000), ('DIR/C.BIN', b'c' * 5000)):
                lba, size = after[name]
                self.assertEqual(data[lba * 2048:lba * 2048 + size], want)
            with self.assertRaises(ValueError):
                iso.replace(path, {'NOPE.BIN': b''})


class MovieTest(unittest.TestCase):
    def test_read(self):
        m = psmf.Movie(fixtures.psmf([6, 6, 4]))
        self.assertEqual((len(m.units), [g['first'] for g in m.groups], [g['count'] for g in m.groups]),
                         (16, [0, 6, 12], [6, 6, 4]))
        self.assertEqual(bytes(m.es), fixtures.h264([6, 6, 4]))
        # six pictures of 910 bytes fill the group's pack and two more; the rest is padding
        self.assertEqual([p['kind'] for p in m.packs[:6]], ['group', 'video', 'video', 'padding', 'padding', 'audio'])

    def test_replace_video(self):
        old = fixtures.psmf([6, 6, 4])
        new_es = fixtures.h264([6, 6, 4], size=700, salt=9)
        out = psmf.replace_video(old, new_es)
        self.assertEqual(len(out), len(old))
        m = psmf.Movie(out)
        self.assertEqual(bytes(m.es), new_es)
        before = psmf.Movie(old)
        for a, b in zip(before.packs, m.packs):                                # the sound is not touched
            if a['kind'] == 'audio':
                self.assertEqual(old[a['offset']:a['offset'] + 2048], out[b['offset']:b['offset'] + 2048])
        # the description of a group lists the size of its pictures
        nav = [(q, n) for code, q, n in m.packs[0]['items'] if code == 0xBF][0]
        sizes = [struct.unpack_from('>I', out, nav[0] + 24 + k * 4)[0] & 0x7FFFFF for k in range(6)]
        self.assertEqual(sizes, [6 + 4 + 700] * 6)
        # the system header of the group's pack is the original one, untouched
        bb = [(q, n) for code, q, n in before.packs[0]['items'] if code == 0xBB][0]
        self.assertEqual(out[bb[0]:bb[0] + 6 + bb[1]], old[bb[0]:bb[0] + 6 + bb[1]])

    def test_a_description_that_lies_about_its_size_is_refused(self):
        old = bytearray(fixtures.psmf([6, 6, 4]))
        m = psmf.Movie(bytes(old))
        nav = [q for code, q, _n in m.packs[0]['items'] if code == 0xBF][0]
        struct.pack_into('>H', old, nav + 22, 200)                              # 200 pictures in 50 bytes
        with self.assertRaises(ValueError):
            psmf.replace_video(bytes(old), fixtures.h264([6, 6, 4], size=700))

    def test_what_does_not_fit_is_refused(self):
        old = fixtures.psmf([6, 6, 4])
        with self.assertRaises(ValueError):
            psmf.replace_video(old, fixtures.h264([6, 6, 4], size=4000))        # a group larger than its packs
        with self.assertRaises(ValueError):
            psmf.replace_video(old, fixtures.h264([6, 6, 3]))                   # a picture is missing
        with self.assertRaises(ValueError):
            psmf.replace_video(old, fixtures.h264([7, 5, 4]))                   # groups start elsewhere


class SubtitlesTest(unittest.TestCase):
    def test_timing(self):
        segments = [{'start': 1.0, 'end': 2.0, 'text': 'a', 'words': []},
                    {'start': 3.0, 'end': 19.0, 'text': 'b',
                     'words': [{'start': 3.0, 'end': 3.5, 'word': 'x'}, {'start': 17.0, 'end': 17.5, 'word': 'y'}]},
                    {'start': 19.5, 'end': 19.6, 'text': 'c', 'words': []},
                    {'start': 30.0, 'end': 31.0, 'text': 'song', 'words': []}]
        got = subtitles.cues(segments, ['Um', 'Dois', 'Três', None])
        self.assertEqual(len(got), 3)
        self.assertAlmostEqual(got[1][0], 16.6)                  # starts with the rest of the sentence
        self.assertLessEqual(got[1][1], got[2][0])               # never over the next one
        self.assertGreaterEqual(got[2][1] - got[2][0], 1.2 - 1e-9)      # long enough to read
        text = subtitles.srt(got)
        self.assertIn('00:00:01,000 --> 00:00:02,200\nUm\n', text)       # a one-second cue gets the minimum
        self.assertEqual(subtitles.stamp(3661.5), '01:01:01,500')


class LayoutTest(unittest.TestCase):
    def setUp(self):
        self.lay = patch.Layout({ord(c): 10.0 for c in 'abcdefghijklmnopqrstuvwxyz '}, 10.0)

    def test_wrap(self):
        self.assertEqual(self.lay.wrap('aaaa bbbb cccc', 100), ['aaaa bbbb', 'cccc'])
        self.assertEqual(self.lay.width('<c#ff1f75ff>ab<c> <x:y>'), 40.0)        # tags take no room
        text, over, extra = self.lay.fit('aaaa bbbb cccc', 100, 3)
        self.assertEqual((text, over, extra), ('aaaa bbbb\r\ncccc', 0.0, 0))

    def test_what_does_not_fit_is_reported(self):
        _text, over, extra = self.lay.fit('aaaa bbbb cccc dddd', 50, 2)
        self.assertEqual(extra, 2)
        _text, over, _extra = self.lay.fit('aaaaaaaaaaaa', 50, 2)
        self.assertEqual(over, 70.0)

    def test_keys(self):
        self.assertEqual(patch.translation_key('event/script/50_01.pac/50_01_JP.BTX', 100000, {'50_01'}), '50_01:100000')
        self.assertEqual(patch.translation_key('event/script/51_15.pac/50_15_JP.BTX', 1, {'51_15'}),
                         'event/script/51_15.pac/50_15_JP.BTX#1')
        self.assertEqual(patch.group_of('event/script/50_01.pac/50_01_JP.BTX'), 'dialogue')


class PicturesTest(unittest.TestCase):
    def label(self, rows):
        im = Image.new('RGBA', (128, 32), (0, 0, 0, 0))
        for y0, colour in rows:
            im.paste(colour, (20, y0, 100, y0 + 10))
        return im

    def test_rows_of_text(self):
        im = self.label([(3, (255, 255, 255, 255)), (19, (40, 80, 255, 255))])
        a = np.asarray(im)[:, :, 3]
        self.assertEqual(pictures.bands(a), [(20, 3, 100, 13), (20, 19, 100, 29)])
        self.assertEqual(pictures.halves(a), [(20, 3, 100, 13), (20, 19, 100, 29)])

    def test_relabel_keeps_each_state_in_its_half(self):
        im = self.label([(3, (255, 255, 255, 255)), (19, (40, 80, 255, 255))])
        new = np.asarray(pictures.relabel(im, 'Modo', stacked=True))
        self.assertEqual(new.shape, (32, 128, 4))
        top, bottom = new[:16], new[16:]
        self.assertGreater(int(top[:, :, 3].max()), 200)
        self.assertGreater(int(bottom[:, :, 3].max()), 200)
        solid = bottom[bottom[:, :, 3] > 200]
        self.assertGreater(int(solid[:, 2].mean()), int(solid[:, 0].mean()))        # the blue state stays blue
        with self.assertRaises(ValueError):
            pictures.relabel(im, ['one', 'two', 'three'])

    def test_every_label_is_short_text(self):
        for name, value in pictures.LABELS.items():
            for text in ([value] if isinstance(value, str) else value):
                self.assertLessEqual(len(text), 24, name)


if __name__ == '__main__':
    with contextlib.redirect_stdout(io.StringIO()):
        pass
    unittest.main()
