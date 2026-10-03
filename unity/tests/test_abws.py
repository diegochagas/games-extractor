import os
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import abws  # noqa: E402

MANIFEST = b"""ManifestFileVersion: 0
CRC: 1
AssetBundleManifest:
  AssetBundleInfos:
    Info_0:
      Name: config/config.fassets
      Dependencies: {}
    Info_1:
      Name: role/hilda.fassets
      Dependencies:
        Dependency_0: allshader/uscript.fassets
        Dependency_1: config/config.fassets
"""


def wrap(name, payload):
    return abws.MAGIC + name.encode().ljust(abws.HEADER - 4, b'\0') + payload


class AbwsTest(unittest.TestCase):
    def test_strip_and_name(self):
        blob = wrap('atlas/common/_current_.fassets', b'UnityFS\0payload')
        self.assertEqual(abws.strip_header(blob), b'UnityFS\0payload')
        self.assertEqual(abws.wrapped_name(blob), 'atlas/common/_current_.fassets')
        self.assertEqual(abws.strip_header(b'UnityFS\0raw'), b'UnityFS\0raw')
        with self.assertRaises(ValueError):
            abws.strip_header(b'nope')

    def test_manifest(self):
        deps = abws.parse_manifest(MANIFEST.decode())
        self.assertEqual(deps, {'config/config.fassets': [],
                                'role/hilda.fassets': ['allshader/uscript.fassets', 'config/config.fassets']})

    def test_apk_list_and_extract(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk = os.path.join(tmp, 'game.apk')
            with zipfile.ZipFile(apk, 'w') as z:
                z.writestr('assets/GameRes/GameRes.manifest.abws', wrap('GameRes.manifest', MANIFEST))
                z.writestr('assets/GameRes/config/config.fassets.abws', wrap('config/config.fassets', b'UnityFS\0cfg'))
                z.writestr('assets/GameRes/config/config.fassets.manifest.abws', wrap('config/config.fassets.manifest', b'CRC: 2\n'))
                z.writestr('lib/arm64-v8a/libunity.so', b'ELF')
            self.assertEqual([r for r, _ in abws.list_bundles(apk)],
                             ['GameRes.manifest.abws', 'config/config.fassets.abws', 'config/config.fassets.manifest.abws'])
            out = os.path.join(tmp, 'out')
            self.assertEqual(abws.extract(apk, out), 3)
            with open(os.path.join(out, 'config/config.fassets'), 'rb') as f:
                self.assertEqual(f.read(), b'UnityFS\0cfg')
            with open(os.path.join(out, 'config/config.fassets.manifest'), 'rb') as f:
                self.assertEqual(f.read(), b'CRC: 2\n')
            # a folder of .abws files is accepted too
            folder = os.path.join(tmp, 'folder', 'config')
            os.makedirs(folder)
            with open(os.path.join(folder, 'x.fassets.abws'), 'wb') as f:
                f.write(wrap('config/x.fassets', b'UnityFS\0x'))
            self.assertEqual(abws.extract(os.path.join(tmp, 'folder'), os.path.join(tmp, 'out2')), 1)
            with open(os.path.join(tmp, 'out2', 'config', 'x.fassets'), 'rb') as f:
                self.assertEqual(f.read(), b'UnityFS\0x')


if __name__ == '__main__':
    unittest.main()
