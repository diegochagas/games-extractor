import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import roles  # noqa: E402


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


class RolesTest(unittest.TestCase):
    def make_dump(self, tmp):
        tables = os.path.join(tmp, 'tables')
        write_json(os.path.join(tables, 'RoleConfig.json'), [
            {'Sid': '26250', 'name': '希露达', 'nameDesc': '', 'xzName': '', 'modelResName': 'Hilda', 'originalStar': 4,
             'icon': 'RoleIcon/t6001', 'iconShow': 'RoleIcon/t6001_Show', 'descEx': 'x'},
            {'Sid': '1050', 'name': '希露达', 'nameDesc': '北极星希露达', 'xzName': '北极星', 'modelResName': 'Hilda',
             'originalStar': 4, 'icon': 'RoleIcon/t6001', 'iconShow': 'RoleIcon/t6001_Show', 'descEx': 'desc'},
            {'Sid': '23002', 'name': '烈焰斗士', 'nameDesc': '', 'xzName': '', 'modelResName': '2002', 'originalStar': 1,
             'icon': '', 'iconShow': '', 'descEx': ''},
            {'Sid': '9', 'name': 'x', 'nameDesc': '', 'xzName': '', 'modelResName': '', 'originalStar': 1},
        ])
        write_json(os.path.join(tables, 'BattleRoleConfig.json'), [
            {'id': '1050', 'Types': [2, 1, 1, 3, 2, 7, 1]}, {'id': '23002', 'Types': [1, 1, 1, 1, 1, 1, 1]}])
        write_json(os.path.join(tables, 'RoleSkinConfig.json'), [{'roleSid': '1050', 'bagShow': 'BagRoleCard/Big/1050'}])
        assets = os.path.join(tmp, 'assets', 'texture')
        icon_dir = os.path.join(assets, 'roleicon', '_current_.fassets')
        os.makedirs(os.path.join(icon_dir, 'sprites'))
        write_json(os.path.join(icon_dir, 'objects.json'), [
            {'type': 'Sprite', 'name': 't6001', 'file': 'sprites/t6001.png'},
            {'type': 'Texture2D', 'name': 'atlas', 'file': 'atlas.png'}])
        with open(os.path.join(icon_dir, 'sprites', 't6001.png'), 'wb') as f:
            f.write(b'png')
        card_dir = os.path.join(assets, 'bagrolecard', 'newbig', '_current_.fassets')
        os.makedirs(card_dir)
        write_json(os.path.join(card_dir, 'objects.json'), [{'type': 'Texture2D', 'name': '1050', 'file': '1050.png'}])
        with open(os.path.join(card_dir, '1050.png'), 'wb') as f:
            f.write(b'card')
        puppets = os.path.join(tmp, 'puppets')
        os.makedirs(puppets)
        with open(os.path.join(puppets, 'hilda.png'), 'wb') as f:
            f.write(b'pose')
        return tmp

    def test_characters_and_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_dump(tmp)
            chars = roles.characters(os.path.join(tmp, 'tables'))
            self.assertEqual(sorted(chars), ['2002', 'hilda'])
            h = chars['hilda']
            self.assertEqual((h['sid'], h['nameDesc'], h['cloth'], h['card'], sorted(h['ids'])),
                             ('1050', '北极星希露达', 7, 'BagRoleCard/Big/1050', ['1050', '26250']))
            self.assertEqual(roles.faction(7), 'Guerreiros Deuses')
            self.assertEqual(roles.faction(None, 'en'), 'Unknown')
            index = roles.picture_index(os.path.join(tmp, 'assets'))
            self.assertTrue(roles.resolve(index, 'RoleIcon/t6001').endswith('sprites/t6001.png'))
            self.assertTrue(roles.resolve(index, 'BagRoleCard/Big/1050').endswith('newbig/_current_.fassets/1050.png'))
            self.assertIsNone(roles.resolve(index, 'RoleIcon/nope'))
            self.assertIsNone(roles.resolve(index, ''))
            self.assertTrue(roles.resolve(index, ['RoleIcon/t6001', 'x']).endswith('t6001.png'))
            self.assertIsNone(roles.resolve(index, 5))

    def test_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_dump(tmp)
            gallery = os.path.join(tmp, 'gallery')
            self.assertEqual(roles.build(tmp, gallery), 1)
            with open(os.path.join(gallery, 'index.json'), encoding='utf-8') as f:
                rows = json.load(f)
            self.assertEqual(rows[0]['folder'], 'Guerreiros Deuses/Hilda - 北极星希露达')
            self.assertEqual(sorted(rows[0]['files']), ['card', 'icon', 'pose'])
            self.assertTrue(os.path.exists(os.path.join(gallery, rows[0]['files']['pose'])))
            with open(os.path.join(gallery, 'index.html'), encoding='utf-8') as f:
                page = f.read()
            self.assertIn('北极星希露达', page)
            self.assertIn('Guerreiros Deuses', page)


if __name__ == '__main__':
    unittest.main()
