import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'story'))

import story_dump  # noqa: E402
import translate  # noqa: E402


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)


class StoryDumpTest(unittest.TestCase):
    def make_dump(self, tmp):
        t = os.path.join(tmp, 'tables')
        write_json(os.path.join(t, 'ChapterConfig.json'), [
            {'id': '1', 'index': 1, 'style': 'PT', 'name': '第一章', 'desc': '第1章描述', 'icon': 'levelIcon/1', 'StoryShowRole': '1008'},
            {'id': '10001', 'index': 1, 'style': 'JY', 'name': '第一章', 'desc': ''}])
        write_json(os.path.join(t, 'LevelConfig.json'), [
            {'id': '30001', 'chapterId': '1', 'type': 1, 'name': '1-1 开始', 'desc': '描述', 'nextId': '30002', 'showBoss': ['1027']},
            {'id': '30002', 'chapterId': '1', 'type': 1, 'name': '1-2', 'desc': '', 'nextId': ''},
            {'id': '30000', 'chapterId': '1', 'type': 1, 'name': '刺客', 'desc': '', 'nextId': '30001'},
            {'id': '50000', 'chapterId': '1', 'type': 60, 'name': 'event copy', 'desc': ''}])
        write_json(os.path.join(t, 'GameStoryConfig.json'), [
            {'StoryId': '3', 'LevelId': '30001', 'StoryTitle': '开始', 'TriggerCondition': ['1'], 'StoryItemList': ['a', 'b', 'c']},
            {'StoryId': '', 'LevelId': '', 'StoryItemList': []}])
        write_json(os.path.join(t, 'GameStoryItemConfig.json'), [
            {'StoryItemId': 'a', 'StoryItemType': 6, 'HandleMethod': 'ShowChat', 'MethodPars': ['你好', '2', '1000', '""', '2', '0']},
            {'StoryItemId': 'b', 'StoryItemType': 7, 'HandleMethod': 'PlayAnimation', 'MethodPars': ['1000', '9']},
            {'StoryItemId': 'c', 'StoryItemType': 6, 'HandleMethod': 'ShowChat', 'MethodPars': ['哼', '2', '1027', '""', '2', '1']}])
        write_json(os.path.join(t, 'RoleConfig.json'), [{'Sid': '1000', 'name': '星矢', 'modelResName': 'Seiya'}])
        write_json(os.path.join(t, 'StoryRoleConfig.json'), [{'id': '1027', 'name': '哈迪斯', 'modelRes': 'Hades'}])

    def test_build_and_strings(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.make_dump(tmp)
            story = story_dump.build(tmp)
            self.assertEqual(story['stats'], {'chapters': 1, 'levels': 3, 'lines': 2})
            ch = story['chapters'][0]
            self.assertEqual(ch['desc'], '')   # placeholder dropped
            self.assertEqual([lv['name'] for lv in ch['levels']], ['刺客', '1-1 开始', '1-2'])   # nextId chain order
            s = ch['levels'][1]['stories'][0]
            self.assertEqual((s['when'], s['title']), ('before', '开始'))
            self.assertEqual([(l['speaker'], l['side'], l['zh']) for l in s['lines']], [('星矢', 'left', '你好'), ('哈迪斯', 'right', '哼')])
            self.assertEqual(story['speakers']['1027']['model'], 'Hades')
            keys = story_dump.strings(story)
            self.assertIn('line:3:0', keys)
            self.assertEqual(keys['chapter:1:name'], '第一章')
            self.assertEqual(keys['speaker:1000'], '星矢')
            self.assertEqual(story_dump.trigger_label(['2']), 'after')
            self.assertEqual(story_dump.trigger_label(['3', '1']), 'during')


class TranslateTest(unittest.TestCase):
    def test_parse_and_glossary(self):
        self.assertEqual(translate.parse_answer('[{"i": 0, "pt": "Olá"}, {"i": 1, "pt": "Hum"}]', 2), {0: 'Olá', 1: 'Hum'})
        self.assertEqual(translate.parse_answer('{"itens": [{"i": 1, "pt": "x"}]}', 2), {1: 'x'})
        self.assertEqual(translate.parse_answer('["a", "b"]', 2), {0: 'a', 1: 'b'})
        self.assertEqual(translate.parse_answer('garbage', 2), {})
        self.assertEqual(translate.parse_answer('[{"i": 5, "pt": "x"}]', 2), {})
        g = {'星矢': 'Seiya', '圣衣': 'Armadura', '黄金圣衣': 'Armadura de Ouro'}
        self.assertEqual(translate.apply_glossary('A 黄金圣衣 de 星矢', g), 'A Armadura de Ouro de Seiya')
        self.assertEqual(list(translate.glossary_for(['黄金圣衣!'], g)), ['黄金圣衣', '圣衣'])
        self.assertEqual(translate.key_of('你好'), translate.key_of('你好'))
        self.assertNotEqual(translate.key_of('你好'), translate.key_of('你好 '))

    def test_pending_uses_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            story = {'chapters': [{'id': '1', 'name': '第一章', 'desc': '', 'levels': [
                {'id': '30001', 'name': '1-1', 'desc': '', 'stories': [{'id': '3', 'title': '', 'lines': [
                    {'key': 'line:3:0', 'speaker': '星矢', 'zh': '你好'}, {'key': 'line:3:1', 'speaker': '星矢', 'zh': '你好'}]}]}]}],
                     'speakers': {'1000': {'sid': '1000', 'name': '星矢'}}}
            write_json(os.path.join(tmp, 'text', 'story.json'), story)
            _s, todo = translate.pending(tmp, {})
            self.assertEqual([(sp, zh) for _h, sp, zh in todo], [('', '第一章'), ('星矢', '你好'), ('', '星矢')])   # repeated line once
            cache = {translate.key_of('你好'): 'Olá'}
            _s, todo = translate.pending(tmp, cache)
            self.assertEqual([zh for _h, _sp, zh in todo], ['第一章', '星矢'])


if __name__ == '__main__':
    unittest.main()
