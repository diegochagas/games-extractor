import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import abws  # noqa: E402
import cdn  # noqa: E402

SERVER = {
    'version': '8.0.0',
    'res_version': '8.3.0|base26090301_8.4.0|base26092402',
    'android_res_url': 'https://cdn.example.test/sds/',
    'data': [{'sid': '1'}, {'sid': '2'}],
}


def wrap(name, payload):
    return abws.MAGIC + name.encode().ljust(abws.HEADER - 4, b'\0') + payload


def manifest(h):
    return wrap('x.manifest', f'ManifestFileVersion: 0\nCRC: 1\nHashes:\n  AssetFileHash:\n    serializedVersion: 2\n    Hash: {h}\n'.encode())


class CdnTest(unittest.TestCase):
    def test_res_version_and_urls(self):
        self.assertEqual(cdn.parse_res_version(SERVER['res_version']),
                         [('8.3.0', 'base26090301'), ('8.4.0', 'base26092402')])
        info = cdn.server_info(json.dumps(SERVER).encode())
        self.assertEqual(info['tag'], 'base26092402')
        self.assertEqual(info['root'], 'https://cdn.example.test/sds/')
        self.assertEqual(info['servers'], 2)
        self.assertEqual(cdn.bundle_url(info['root'], info['tag'], 'role/hilda.fassets'),
                         'https://cdn.example.test/sds/base26092402/GameRes/role/hilda.fassets.abws')
        self.assertEqual(cdn.bundle_url(info['root'], info['tag'], 'role/hilda.fassets.manifest.abws'),
                         'https://cdn.example.test/sds/base26092402/GameRes/role/hilda.fassets.manifest.abws')
        self.assertEqual(cdn.server_url('http://c', '9', '8'), 'http://c/index.php/p9/server/pid/9/gid/8/o_system/android')
        self.assertEqual(cdn.manifest_hash(manifest('a' * 32)), 'a' * 32)
        self.assertIsNone(cdn.manifest_hash(b'nothing'))

    def test_fetch_skip_and_missing(self):
        files = {
            'https://cdn.example.test/sds/t/GameRes/role/hilda.fassets.manifest.abws': manifest('b' * 32),
            'https://cdn.example.test/sds/t/GameRes/role/hilda.fassets.abws': wrap('role/hilda.fassets', b'UnityFS\0data'),
        }
        calls = []

        def fake_http(url, method='GET', retries=3):
            calls.append(url)
            if url in files:
                return 200, files[url], {}
            return 404, b'', {}

        real = cdn.http
        cdn.http = fake_http
        try:
            with tempfile.TemporaryDirectory() as tmp:
                self.assertEqual(cdn.fetch_one('https://cdn.example.test/sds/', 't', 'role/hilda.fassets', tmp), 'ok')
                with open(os.path.join(tmp, 'role/hilda.fassets.abws'), 'rb') as f:
                    self.assertEqual(abws.strip_header(f.read()), b'UnityFS\0data')
                # same hash on the CDN: nothing downloaded again
                n = len(calls)
                self.assertEqual(cdn.fetch_one('https://cdn.example.test/sds/', 't', 'role/hilda.fassets', tmp), 'skip')
                self.assertEqual(len(calls), n + 1)
                # changed hash: fetched again
                files['https://cdn.example.test/sds/t/GameRes/role/hilda.fassets.manifest.abws'] = manifest('c' * 32)
                self.assertEqual(cdn.fetch_one('https://cdn.example.test/sds/', 't', 'role/hilda.fassets', tmp), 'ok')
                self.assertEqual(cdn.fetch_one('https://cdn.example.test/sds/', 't', 'role/freya.fassets', tmp), 'missing')
                # a bundle without a manifest on the CDN is still fetched, once
                files['https://cdn.example.test/sds/t/GameRes/initres/igamebytes.fassets.abws'] = wrap('initres/igamebytes.fassets', b'UnityFS\0code')
                self.assertEqual(cdn.fetch_one('https://cdn.example.test/sds/', 't', 'initres/igamebytes.fassets', tmp), 'ok')
                self.assertEqual(cdn.fetch_one('https://cdn.example.test/sds/', 't', 'initres/igamebytes.fassets', tmp), 'skip')
                counts, missing = cdn.sync(tmp, ['role/hilda.fassets', 'role/freya.fassets'], 'https://cdn.example.test/sds/', 't', workers=2)
                self.assertEqual(counts, {'ok': 0, 'skip': 1, 'missing': 1})
                self.assertEqual(missing, ['role/freya.fassets'])
        finally:
            cdn.http = real


if __name__ == '__main__':
    unittest.main()
