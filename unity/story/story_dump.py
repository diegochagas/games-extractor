#!/usr/bin/env python3
"""Story dump of Saint Seiya Rebirth from the game tables (tables.py output).

usage: story_dump.py DUMP      -> DUMP/text/story.json

The campaign is ChapterConfig (style PT = the normal chapters; JY and EM are the hard and
nightmare copies of the same chapters, skipped) -> LevelConfig (chapterId, nextId chain, name,
desc, showBoss; only `type` 1 stages, the other thousands of rows per chapter are event copies) -> GameStoryConfig (LevelId, StoryTitle, TriggerCondition, StoryItemList) ->
GameStoryItemConfig items of type 6 (`ShowChat` = [text, ?, speaker id, voice, seconds, side]).
Speakers come from RoleConfig / StoryRoleConfig (Chinese name + modelResName for the picture).
Every Chinese string gets a stable key so the translation cache survives new CDN configs:
  chapter:<id>:name|desc, level:<id>:name|desc, line:<story id>:<n>, story:<id>:title
"""
import json
import os
import re
import sys
from collections import OrderedDict

CHAT = 'ShowChat'
CHAPTER_STYLE = 'PT'
LEVEL_TYPES = {1, 10}   # 1 = campaign stage (cType small / large), 10 = the tutorial fight


def load(tables, name):
    with open(os.path.join(tables, name + '.json'), encoding='utf-8') as f:
        return json.load(f)


def chapter_levels(levels, chapter_id):
    """Levels of one chapter in play order: follow nextId from the one nobody points to."""
    mine = {lv['id']: lv for lv in levels if str(lv.get('chapterId')) == str(chapter_id) and lv.get('type') in LEVEL_TYPES}
    if not mine:
        return []
    pointed = {str(lv.get('nextId')) for lv in mine.values()}
    starts = [lv for lv in mine.values() if str(lv['id']) not in pointed]
    order = []
    seen = set()
    for start in sorted(starts, key=lambda lv: int(lv['id']) if str(lv['id']).isdigit() else 0):
        cur = start
        while cur and cur['id'] not in seen:
            order.append(cur)
            seen.add(cur['id'])
            cur = mine.get(str(cur.get('nextId')))
    rest = [lv for lv in sorted(mine.values(), key=lambda lv: int(lv['id']) if str(lv['id']).isdigit() else 0) if lv['id'] not in seen]
    tutorial = [lv for lv in rest if lv.get('type') == 10]   # the tutorial fight goes first
    return tutorial + order + [lv for lv in rest if lv.get('type') != 10]


def trigger_label(cond):
    """TriggerCondition -> 'before' / 'after' / 'during' the battle."""
    first = str(cond[0]) if isinstance(cond, list) and cond else str(cond or '')
    if first in ('1', '8', '11'):
        return 'before'
    if first in ('2', '6', '9', '12'):
        return 'after'
    return 'during'


def build(dump):
    tables = os.path.join(dump, 'tables')
    chapters = [c for c in load(tables, 'ChapterConfig') if c.get('style') == CHAPTER_STYLE]
    levels = load(tables, 'LevelConfig')
    stories = load(tables, 'GameStoryConfig')
    items = {it['StoryItemId']: it for it in load(tables, 'GameStoryItemConfig')}
    roles = {r['Sid']: r for r in load(tables, 'RoleConfig')}
    story_roles = {r['id']: r for r in load(tables, 'StoryRoleConfig')}
    by_level = {}
    for s in stories:
        if s.get('StoryId') and s.get('LevelId'):
            by_level.setdefault(str(s['LevelId']), []).append(s)
    speakers = {}

    def speaker(sid):
        sid = str(sid)
        if sid not in speakers:
            r = roles.get(sid) or story_roles.get(sid) or {}
            speakers[sid] = {'sid': sid, 'name': r.get('name') or sid,
                             'model': r.get('modelResName') or r.get('modelRes') or ''}
        return speakers[sid]

    out_chapters = []
    n_lines = 0
    for ch in sorted(chapters, key=lambda c: c.get('index') or 0):
        title = re.sub(r'^第[一二三四五六七八九十百\d]+章\s*', '', ch.get('name') or '')  # "第十九章 来自北欧的斗士" -> title only
        chapter = OrderedDict(id=str(ch['id']), index=ch.get('index'), name=title,
                              desc=ch.get('desc') or '', icon=ch.get('icon') or '', show_role=str(ch.get('StoryShowRole') or ''),
                              levels=[])
        if re.fullmatch(r'第\d+章描述', chapter['desc']):
            chapter['desc'] = ''  # placeholder left by the developers
        for lv in chapter_levels(levels, ch['id']):
            level = OrderedDict(id=str(lv['id']), name=lv.get('name') or '', desc=lv.get('desc') or '',
                                boss=[str(b) for b in (lv.get('showBoss') or [])] if isinstance(lv.get('showBoss'), list) else [],
                                stories=[])
            for s in by_level.get(str(lv['id']), []):
                lines = []
                for n, item_id in enumerate(s.get('StoryItemList') or []):
                    it = items.get(item_id)
                    if not it or it.get('HandleMethod') != CHAT:
                        continue
                    p = it.get('MethodPars') or []
                    if not p or not str(p[0]).strip():
                        continue
                    sp = speaker(p[2] if len(p) > 2 else '')
                    lines.append(OrderedDict(key=f"line:{s['StoryId']}:{n}", speaker=sp['name'], sid=sp['sid'],
                                             side='right' if len(p) > 5 and str(p[5]) == '1' else 'left', zh=str(p[0])))
                if lines:
                    level['stories'].append(OrderedDict(id=str(s['StoryId']), title=s.get('StoryTitle') or '',
                                                        when=trigger_label(s.get('TriggerCondition')), lines=lines))
                    n_lines += len(lines)
            chapter['levels'].append(level)
        out_chapters.append(chapter)
    return {'chapters': out_chapters, 'speakers': speakers, 'stats': {'chapters': len(out_chapters),
            'levels': sum(len(c['levels']) for c in out_chapters), 'lines': n_lines}}


def strings(story):
    """Every Chinese string of the dump as {key: text}, the unit the translation works on."""
    out = OrderedDict()
    for ch in story['chapters']:
        out[f"chapter:{ch['id']}:name"] = ch['name']
        if ch['desc']:
            out[f"chapter:{ch['id']}:desc"] = ch['desc']
        for lv in ch['levels']:
            out[f"level:{lv['id']}:name"] = lv['name']
            if lv['desc']:
                out[f"level:{lv['id']}:desc"] = lv['desc']
            for s in lv['stories']:
                if s['title']:
                    out[f"story:{s['id']}:title"] = s['title']
                for line in s['lines']:
                    out[line['key']] = line['zh']
    for sp in story['speakers'].values():
        out[f"speaker:{sp['sid']}"] = sp['name']
    return out


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    dump = argv[0]
    story = build(dump)
    os.makedirs(os.path.join(dump, 'text'), exist_ok=True)
    with open(os.path.join(dump, 'text', 'story.json'), 'w', encoding='utf-8') as f:
        json.dump(story, f, ensure_ascii=False, indent=1)
    print(story['stats'], f"{len(strings(story))} strings")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
