#!/usr/bin/env python3
"""zh -> pt-BR translation of the story dump with a local Ollama model, cached per string.

usage: translate.py run DUMP [--model NAME] [--batch N] [--limit N]    translate what is not cached yet
       translate.py check DUMP                                          report missing / suspicious entries
       translate.py status DUMP                                         how many strings are done

Cache: DUMP/text/translation/pt-BR.json = {sha1 of the Chinese text: pt-BR}. Keys are by text,
not by table id, so a new CDN config only translates the lines that are really new, and a line
repeated in several levels is translated once. `glossary.json` (names, techniques) is given to
the model and applied again at the end on any name that was left in Chinese.
Environment: OLLAMA_URL (default http://localhost:11434), OLLAMA_MODEL (default qwen3-instruct-32k).
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import story_dump  # noqa: E402

CJK = re.compile(r'[一-鿿]')
OLLAMA = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
MODEL = os.environ.get('OLLAMA_MODEL', 'qwen3-instruct-32k')
TAGS = re.compile(r'\[[0-9A-Fa-f]{6,8}\]|\[-\]|\[/?[bi]\]')

RULES = (
    'Você é tradutor profissional de Saint Seiya (Cavaleiros do Zodíaco). Traduza cada fala ou texto do chinês '
    'para o português do Brasil: diálogo natural e falado, fiel ao original, sem resumir, sem acrescentar nada, '
    'mantendo o tom de cada personagem. Use SEMPRE os nomes da dublagem brasileira indicados no glossário '
    '(Seiya, Shiryu, Hyoga, Shun, Ikki, Saori, Atena, Mu, Aldebaran, Saga, Máscara da Morte, Aiolia, Shaka, Dohko, '
    'Milo, Aiolos, Shura, Camus, Afrodite, Kanon, Radamanthys, Minos, Aiacos, Pandora, Hades, Hypnos, Thanatos, '
    'Poseidon, Sorento, Hilda, Siegfried, Alberich, Fenrir, Hagen, Thor, Syd, Bud, Mime, Éris, Orfeu...). '
    '圣衣 é "Armadura", 小宇宙 é "Cosmo", 圣斗士 é "Cavaleiro", 圣域 é "Santuário", 冥界 é "Mundo Inferior", '
    '神圣衣 é "Armadura Divina". Nomes de golpes usam o nome da dublagem brasileira quando existir. '
    'Mantenha "……" e a pontuação do original; mantenha códigos como [ffe691] e [-] exatamente onde estão. '
    'Responda SOMENTE com JSON: uma lista de objetos {"i": número, "pt": "tradução"}, um por item, na mesma ordem.'
)


def key_of(text):
    return hashlib.sha1(text.encode('utf-8')).hexdigest()[:16]


def cache_path(dump):
    return os.path.join(dump, 'text', 'translation', 'pt-BR.json')


def load_cache(dump):
    path = cache_path(dump)
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_cache(dump, cache):
    path = cache_path(dump)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, path)


def load_glossary():
    with open(os.path.join(HERE, 'glossary.json'), encoding='utf-8') as f:
        g = json.load(f)
    return {**g.get('names', {}), **g.get('techniques', {})}


def glossary_for(texts, glossary):
    """The glossary entries that occur in these texts, longest names first."""
    hits = {k: v for k, v in glossary.items() if any(k in t for t in texts)}
    return dict(sorted(hits.items(), key=lambda kv: -len(kv[0])))


def apply_glossary(text, glossary):
    """Replace any glossary term still written in Chinese (longest first)."""
    for zh, pt in sorted(glossary.items(), key=lambda kv: -len(kv[0])):
        if zh in text:
            text = text.replace(zh, pt)
    return text


def ollama(prompt, model=MODEL, timeout=900):
    req = urllib.request.Request(f'{OLLAMA}/api/generate', data=json.dumps({
        'model': model, 'prompt': prompt, 'stream': False, 'format': 'json',
        'options': {'temperature': 0.2, 'num_predict': 4000}}).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)['response']


def parse_answer(answer, n):
    """{i: pt} from the model's JSON (a list, or an object wrapping one)."""
    try:
        data = json.loads(answer)
    except json.JSONDecodeError:
        m = re.search(r'\[.*\]', answer, re.S)
        if not m:
            return {}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                data = v
                break
        else:
            data = [data]
    out = {}
    for k, item in enumerate(data if isinstance(data, list) else []):
        if isinstance(item, dict):
            i = item.get('i', k)
            pt = item.get('pt') or item.get('traducao') or item.get('tradução') or item.get('texto') or ''
        else:
            i, pt = k, item
        try:
            i = int(i)
        except (TypeError, ValueError):
            continue
        if 0 <= i < n and isinstance(pt, str) and pt.strip():
            out[i] = pt.strip()
    return out


def translate_batch(items, glossary, model=MODEL):
    """items: [(key, speaker, zh)] -> {key: pt} for the ones the model answered well."""
    texts = [zh for _, _, zh in items]
    gl = glossary_for(texts, glossary)
    payload = [{'i': i, 'falante': sp or '', 'zh': zh} for i, (_, sp, zh) in enumerate(items)]
    prompt = f"{RULES}\n\nGlossário (chinês: português): {json.dumps(gl, ensure_ascii=False)}\n\nItens:\n{json.dumps(payload, ensure_ascii=False)}"
    answer = ollama(prompt, model)
    got = parse_answer(answer, len(items))
    out = {}
    for i, pt in got.items():
        pt = apply_glossary(pt, glossary)
        if CJK.search(pt) and len(items) > 1:
            continue  # left Chinese in: retried alone later
        out[items[i][0]] = pt
    return out


def pending(dump, cache):
    with open(os.path.join(dump, 'text', 'story.json'), encoding='utf-8') as f:
        story = json.load(f)
    speakers = {}
    for ch in story['chapters']:
        for lv in ch['levels']:
            for s in lv['stories']:
                for line in s['lines']:
                    speakers[line['key']] = line['speaker']
    todo = []
    seen = set()
    for key, zh in story_dump.strings(story).items():
        if not zh or not CJK.search(zh):
            continue
        h = key_of(zh)
        if h in cache or h in seen:
            continue
        seen.add(h)
        todo.append((h, speakers.get(key, ''), zh))
    return story, todo


def run(dump, model=MODEL, batch=20, limit=None):
    glossary = load_glossary()
    cache = load_cache(dump)
    _story, todo = pending(dump, cache)
    if limit:
        todo = todo[:limit]
    print(f'{len(todo)} strings to translate with {model} (batches of {batch})', flush=True)
    done = 0
    start = time.time()
    i = 0
    while i < len(todo):
        chunk = todo[i:i + batch]
        try:
            got = translate_batch(chunk, glossary, model)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f'!! ollama: {e}; waiting 30 s', flush=True)
            time.sleep(30)
            continue
        missing = [it for it in chunk if it[0] not in got]
        for it in missing:  # one more try alone, then keep whatever comes back
            try:
                single = translate_batch([it], glossary, model)
            except (urllib.error.URLError, TimeoutError, OSError):
                single = {}
            got.update(single)
        for h, _sp, _zh in chunk:
            if h in got:
                cache[h] = got[h]
        done += len(got)
        save_cache(dump, cache)
        i += batch
        rate = done / max(1, time.time() - start) * 60
        print(f'[{min(i, len(todo))}/{len(todo)}] cached {len(cache)}  ({rate:.0f}/min)', flush=True)
    return done


def check(dump):
    cache = load_cache(dump)
    story, todo = pending(dump, cache)
    bad = [(h, pt) for h, pt in cache.items() if CJK.search(pt)]
    print(f'{len(cache)} cached, {len(todo)} missing, {len(bad)} with Chinese left')
    for h, pt in bad[:20]:
        print('  ', h, pt[:80])
    return 0 if not todo else 1


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, dump = argv[0], argv[1]
    if cmd == 'run':
        model = argv[argv.index('--model') + 1] if '--model' in argv else MODEL
        batch = int(argv[argv.index('--batch') + 1]) if '--batch' in argv else 20
        limit = int(argv[argv.index('--limit') + 1]) if '--limit' in argv else None
        run(dump, model, batch, limit)
        return 0
    if cmd == 'check':
        return check(dump)
    if cmd == 'status':
        cache = load_cache(dump)
        _s, todo = pending(dump, cache)
        print(f'{len(cache)} cached, {len(todo)} to go')
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
