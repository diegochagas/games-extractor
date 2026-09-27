import contextlib
import io
import json
import os
import struct
import sys
import tempfile
import unittest

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

import numpy as np  # noqa: E402

import btx  # noqa: E402
import cpk  # noqa: E402
import fixtures  # noqa: E402
import gim  # noqa: E402
import gmo  # noqa: E402
import gmo2glb  # noqa: E402
import media  # noqa: E402
import pac  # noqa: E402


class CpkTest(unittest.TestCase):
    def test_utf_table(self):
        name, rows = cpk.utf_table(fixtures.utf_table('T', [('A', 4), ('B', 0xA), ('C', 6)],
                                                      [(1, 'x', 2 ** 40), (7, 'longer', 3)]))
        self.assertEqual(name, 'T')
        self.assertEqual(rows, [{'A': 1, 'B': 'x', 'C': 2 ** 40}, {'A': 7, 'B': 'longer', 'C': 3}])

    def test_encrypted_table_is_refused(self):
        with self.assertRaises(ValueError):
            cpk.utf_table(b'\x1f\x9e\xf3\xf5' + bytes(40))

    def test_crilayla_literals(self):
        data = bytes(range(256)) + bytes((i * 7 + 3) & 255 for i in range(300))
        self.assertEqual(cpk.crilayla(fixtures.crilayla(data)), data)

    def test_crilayla_back_reference(self):
        data = bytes(range(256)) + b'abcdefgh' * 4 + b'tail'
        packed = fixtures.crilayla(data, reference=(8, 20))
        self.assertLess(len(packed), len(fixtures.crilayla(data)))
        self.assertEqual(cpk.crilayla(packed), data)

    def test_extract(self):
        files = {'a/one.bin': b'hello', 'a/b/two.bin': bytes(range(256)) * 3, 'root.txt': b''}
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'test.cpk')
            write(src, fixtures.cpk(files, compress=('a/b/two.bin',)))
            self.assertEqual(sorted(e['name'] for e in cpk.Cpk(src).files), sorted(files))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cpk.main(['cpk.py', 'extract', src, os.path.join(tmp, 'out'), '--workers', '1']), 0)
            for name, data in files.items():
                self.assertEqual(read(os.path.join(tmp, 'out', name)), data)
            self.assertEqual(os.listdir(tmp).count('test.cpk'), 1)            # the archive is only read


    def test_patch_compresses_what_was_compressed(self):
        files = {'packed.bin': bytes(range(256)) * 8, 'raw.bin': bytes(range(256)) * 8}
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'test.cpk')
            write(src, fixtures.cpk(files, compress=('packed.bin',)))
            same = bytes(range(256)) * 6
            cpk.patch(src, {'packed.bin': same, 'raw.bin': same})
            by = {e['name']: e for e in cpk.Cpk(src).files}
            self.assertLess(by['packed.bin']['csize'], len(same))
            self.assertEqual(by['raw.bin']['csize'], len(same))

    def test_patch_keeps_the_storage_of_each_file(self):
        files = {'a/raw.bin': bytes(range(256)) * 8, 'a/packed.bin': bytes(range(256)) * 8, 'b.txt': b'old'}
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'test.cpk')
            write(src, fixtures.cpk(files, compress=('a/packed.bin',)))
            # data that does not compress and is larger than the sector the old file had
            noise = bytes((i * 197 + (i >> 3) * 31 + (i * i >> 5)) & 255 for i in range(6000))
            new = {'a/raw.bin': b'\x07' * 2000, 'a/packed.bin': noise}
            done = cpk.patch(src, new)
            self.assertEqual(sorted(d[0] for d in done), ['a/packed.bin', 'a/raw.bin'])
            self.assertEqual([d[1] for d in done if d[0] == 'a/raw.bin'], ['slot'])       # fits where it was
            c = cpk.Cpk(src)
            by = {e['name']: e for e in c.files}
            self.assertEqual(by['a/raw.bin']['csize'], by['a/raw.bin']['size'])          # still stored as it is
            self.assertLessEqual(by['a/packed.bin']['csize'], by['a/packed.bin']['size'])
            self.assertEqual(c.read(by['a/raw.bin']), new['a/raw.bin'])
            self.assertEqual(c.read(by['a/packed.bin']), new['a/packed.bin'])
            self.assertEqual(c.read(by['b.txt']), b'old')
            self.assertEqual([d[1] for d in done if d[0] == 'a/packed.bin'], ['end'])     # did not fit its slot


class PacTest(unittest.TestCase):
    def test_nested(self):
        inner = fixtures.pac([('A.GIM', b'aaaa'), ('B.GIM', b'bb')], total_without_header=True)
        outer = fixtures.pac([('NORMAL.PAC', inner), ('X.TXT', b'text'), ('X.TXT', b'again')])
        self.assertTrue(pac.is_pac(inner))
        self.assertEqual(dict(pac.walk(outer)), {'NORMAL.PAC/A.GIM': b'aaaa', 'NORMAL.PAC/B.GIM': b'bb',
                                                 'X.TXT': b'text', 'X~1.TXT': b'again'})

    def test_other_data_is_not_a_pac(self):
        self.assertFalse(pac.is_pac(b'MIG.00.1PSP\0' + bytes(100)))
        self.assertFalse(pac.is_pac(struct.pack('<HHI', 1, 0x78, 60) + bytes(52)))
        self.assertFalse(pac.is_pac(b''))

    def test_extract_writes_outside_the_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = os.path.join(tmp, 'src'), os.path.join(tmp, 'out')
            os.makedirs(os.path.join(src, 'dir'))
            write(os.path.join(src, 'dir', 'pack.pac'), fixtures.pac([('F.BIN', b'123')]))
            write(os.path.join(src, 'plain.bin'), b'zz')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pac.main(['pac.py', 'extract', src, out]), 0)
            self.assertEqual(read(os.path.join(out, 'dir', 'pack.pac', 'F.BIN')), b'123')
            self.assertEqual(read(os.path.join(out, 'plain.bin')), b'zz')
            self.assertEqual(sorted(os.listdir(src)), ['dir', 'plain.bin'])


class GimTest(unittest.TestCase):
    def test_rgba8888(self):
        pixels = b''.join(bytes([x * 10, y * 20, 5, 255]) for y in range(8) for x in range(16))
        im = gim.decode(fixtures.gim(fixtures.gim_block(3, 0, 16, 8, 32, pixels, 1, 1)))[0]
        self.assertEqual(im.size, (16, 8))
        self.assertEqual(im.getpixel((3, 2)), (30, 40, 5, 255))

    def test_index8_swizzled(self):
        rows = np.arange(32 * 8, dtype=np.uint8).reshape(8, 32) % 4
        swizzled = rows.reshape(1, 8, 2, 16).transpose(0, 2, 1, 3).tobytes()      # two 16x8 blocks
        palette = b''.join(bytes(c) for c in ((0, 0, 0, 255), (255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 0)))
        im = gim.decode(fixtures.gim(fixtures.gim_block(5, 1, 32, 8, 8, swizzled),
                                     fixtures.gim_block(3, 0, 4, 1, 32, palette, 1, 1)))[0]
        self.assertEqual(im.size, (32, 8))
        for x, y in ((0, 0), (17, 0), (31, 7), (5, 3)):
            self.assertEqual(im.getpixel((x, y)), tuple(palette[rows[y, x] * 4:rows[y, x] * 4 + 4]))

    def test_narrow_index4_swizzled(self):
        # 8 pixels of 4 bits are 4 bytes, but a swizzled row is always 16 bytes wide
        raw = bytes([0x10] * 16 * 8)
        palette = bytes([9, 9, 9, 255, 200, 100, 50, 255]) + bytes(4 * 14)
        im = gim.decode(fixtures.gim(fixtures.gim_block(4, 1, 8, 8, 4, raw),
                                     fixtures.gim_block(3, 0, 16, 1, 32, palette, 1, 1)))[0]
        self.assertEqual((im.size, im.getpixel((0, 0)), im.getpixel((1, 0))), ((8, 8), (9, 9, 9, 255), (200, 100, 50, 255)))

    def test_colour_formats(self):
        self.assertEqual(gim.colours(struct.pack('<H', 0xFFFF), gim.RGBA5650).tolist(), [[255, 255, 255, 255]])
        self.assertEqual(gim.colours(struct.pack('<H', 0x001F), gim.RGBA5551).tolist(), [[255, 0, 0, 0]])
        self.assertEqual(gim.colours(struct.pack('<H', 0xF00F), gim.RGBA4444).tolist(), [[255, 0, 0, 255]])

    def test_not_a_gim(self):
        with self.assertRaises(ValueError):
            gim.decode(b'.GIM1.00' + bytes(64))


class BtxTest(unittest.TestCase):
    def test_read(self):
        rows = [(100000, '光牙'), (100010, 'line one\r\nline two'), (5, '')]
        self.assertEqual(btx.read(fixtures.btx(rows)), rows)


class GmoTest(unittest.TestCase):
    def test_model(self):
        m = gmo.models(fixtures.gmo_triangle())[0]
        self.assertEqual([b.name for b in m.bones], ['root', 'child', 'body'])
        self.assertEqual(m.bones[1].parent, 0)
        self.assertEqual(m.bones[2].blend_bones, [0, 1])
        arr = m.parts[0]['arrays'][0]
        np.testing.assert_allclose(arr.pos, [[0, 0, 0], [100, 0, 0], [0, 100, 0]], atol=0.01)
        np.testing.assert_allclose(arr.uv, [[0, 0], [1, 0], [0, 1]], atol=1e-6)
        np.testing.assert_allclose(arr.weights, [[1], [1], [1]])
        self.assertEqual(gmo.triangles(m.parts[0]['meshes'][0]['draws'][0]).tolist(), [[0, 1, 2]])
        self.assertEqual(m.textures[0]['file'], 'D:/work/tex.tga')
        track = m.motions[0].tracks[0]
        self.assertEqual((track[0], track[1], track[3].tolist(), track[4].tolist()),
                         (1, 'translate', [0, 30], [[0, 0, 0], [0, 5, 0]]))

    def test_primitive_modes(self):
        idx = np.array([[0, 1, 2, 3]])
        self.assertEqual(gmo.triangles({'mode': 4, 'indices': idx}).tolist(), [[0, 1, 2], [2, 1, 3]])
        self.assertEqual(gmo.triangles({'mode': 5, 'indices': idx}).tolist(), [[0, 1, 2], [0, 2, 3]])

    def test_vertex_layout(self):
        self.assertEqual(gmo.vertex_layout(0x1322)['size'], 16)
        self.assertEqual(gmo.vertex_layout(0x5322)['weights'], 2)
        self.assertEqual(gmo.vertex_layout(0x113E)['size'], 20)       # uv16, colour 8888, normal8, pos16

    def test_pivot_without_rotation_moves_nothing(self):
        data = fixtures.chunk(4, 'b', fixtures.command(0x8046, struct.pack('<fff', 5, 6, 7)))
        b = gmo.Bone(0, gmo.parse_chunks(data, 0, len(data))[0])
        np.testing.assert_allclose(b.local(), np.eye(4))

    def read_glb(self, path):
        d = read(path)
        self.assertEqual(d[:4], b'glTF')
        self.assertEqual(struct.unpack_from('<I', d, 8)[0], len(d))
        n = struct.unpack_from('<I', d, 12)[0]
        return json.loads(d[20:20 + n])

    def test_glb(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = os.path.join(tmp, 'model.gmo'), os.path.join(tmp, 'out', 'model.glb')
            write(src, fixtures.gmo_triangle())
            rep = gmo2glb.convert(src, out)
            self.assertEqual((rep['triangles'], rep['vertices'], rep['animations'], rep['missing_textures']), (1, 3, 1, []))
            j = self.read_glb(out)
            pos = j['accessors'][j['meshes'][0]['primitives'][0]['attributes']['POSITION']]
            np.testing.assert_allclose(pos['min'] + pos['max'], [0, 0, 0, 100, 100, 0], atol=0.01)
            self.assertEqual(len(j['skins']), 1)
            self.assertEqual(len(j['skins'][0]['joints']), 3)
            self.assertEqual(j['images'][0]['mimeType'], 'image/png')
            self.assertEqual(j['animations'][0]['channels'][0]['target']['path'], 'translation')
            self.assertEqual(j['nodes'][0]['scale'], [0.01, 0.01, 0.01])

    def test_glb_attachment_is_written_in_scene_space(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, extra, out = (os.path.join(tmp, n) for n in ('model.gmo', 'loc_210.gmo', 'model.glb'))
            write(src, fixtures.gmo_triangle())
            write(extra, fixtures.gmo_triangle())
            rep = gmo2glb.convert(src, out, attachments=[{'file': extra, 'bone': 1, 'translation': (1, 2, 3)}])
            self.assertEqual(rep['triangles'], 2)
            j = self.read_glb(out)
            self.assertEqual(len(j['skins']), 1)                  # one skin for the whole file
            pos = j['accessors'][j['meshes'][1]['primitives'][0]['attributes']['POSITION']]
            self.assertEqual(pos['min'], [1, 12, 3])              # bone "child" is at y = 10


class MediaTest(unittest.TestCase):
    def test_ahx_frames_are_padded(self):
        sync = b'\xff\xf5\xe0\xc0'
        head = b'\x80\x00\x00\x20\x11\x00\x00\x01' + struct.pack('>II', 44100, 2304) + bytes(20)
        data = head + sync + b'\x01' * 100 + sync + b'\x02' * 200 + b'\x80\x01\x00\x0cAHXE' + bytes(8)
        mp2, rate, samples = media.ahx_to_mp2(data)
        self.assertEqual((rate, samples, len(mp2)), (44100, 2304, 2 * 1044))
        self.assertEqual(mp2[:4], sync)
        self.assertEqual(mp2[1044:1048], sync)
        self.assertEqual(mp2[104:1044], bytes(940))

    def test_ahx_with_reserved_header_is_refused(self):
        head = b'\x80\x00\x00\x20\x11\x00\x00\x01' + struct.pack('>II', 44100, 1152) + bytes(20)
        for sync in (b'\xff\xf5\xfc\xc0', b'\xff\xf5\x00\xc0', b'\xff\xf5\xec\xc0'):
            with self.assertRaises(ValueError):
                media.ahx_to_mp2(head + sync + bytes(100))

    def test_vag(self):
        block = bytes([0x0C, 0x00]) + bytes([0x21] + [0] * 13)      # shift 12, filter 0: nibbles 1, 2
        self.assertEqual(list(media.vag_decode(block))[:3], [1, 2, 0])
        self.assertEqual(len(media.vag_decode(block + bytes([0, 7]) + bytes(14) + block)), 28)

    def test_bank_table(self):
        va = 0x40
        phd = bytearray(b'PPHD' + bytes(va - 4))
        struct.pack_into('<I', phd, 0x18, va)
        phd += b'PPVA' + struct.pack('<IIIII', 0, 16, 0xFFFFFFFF, 0, 2) + bytes(8)
        phd += struct.pack('<IIII', 0, 22050, 560, 0xFFFFFFFF) + b'\xff' * 16 + struct.pack('<IIII', 560, 11025, 32, 0)
        self.assertEqual(media.bank_samples(bytes(phd)), [(0, 0, 22050, 560), (2, 560, 11025, 32)])

    def test_psmf_audio(self):
        frame = b'\x0f\xd0\x28\x00' + bytes(4) + b'\xAA' * 8                   # frame size (0 + 1) * 8
        pes = b'\x00\x00\x01\xbd' + struct.pack('>H', 3 + 4 + len(frame)) + b'\x81\x00\x00' + bytes(4) + frame
        pack = b'\x00\x00\x01\xba' + bytes(9) + b'\xf8'
        oma = media.psmf_audio(bytes(0x800) + pack + pes + b'\x00\x00\x01\xb9')
        self.assertEqual((oma[:3], oma[32], oma[34:36], oma[96:]), (b'EA3', 1, b'\x28\x00', b'\xAA' * 8))
        self.assertIsNone(media.psmf_audio(bytes(0x800) + pack + b'\x00\x00\x01\xb9'))


if __name__ == '__main__':
    unittest.main()
