#!/usr/bin/env python3
"""Translation helper for a dump folder produced by dump.py.

export DUMP   -> DUMP/translation/chunks/chunk_NN.json   (unique Japanese strings, to be translated)
normalize DUMP -> apply docs/glossary.json to the translated chunks
rename DUMP  -> DUMP/text_en/bankNN_renamed.txt: English text already in the ROM with names switched
merge  DUMP   -> DUMP/text_en/bankNN.txt + DUMP/translation/en.json (JP/EN side by side for review)

Translations are files named chunk_NN.en.json next to each chunk: {"key": "english", ...}.
Nothing here touches the ROM.
"""
import json
import re
import sys
from pathlib import Path

KANA = re.compile(r"[぀-ヿ]")
CHUNK = 260


def japanese(s):
    return len(KANA.findall(s)) >= 2


def load_strings(dump):
    out = []
    for f in sorted((dump / "text").glob("bank*.json")):
        out += json.loads(f.read_text(encoding="utf-8"))
    return out


class Lookup:
    """Translation by Japanese text. A string whose extraction later lost a junk prefix
    (pointer-table bytes the translators copied unchanged) is matched by its tail."""

    def __init__(self, pairs):
        self.pairs = pairs

    def get(self, text):
        if text in self.pairs:
            return self.pairs[text]
        if len(text) < 4:
            return None
        for jp, en in self.pairs.items():
            if len(jp) > len(text) and jp.endswith(text):
                prefix = jp[:-len(text)]
                if en.startswith(prefix):
                    return en[len(prefix):]
        return None


def export(dump):
    uniq = {}
    for s in load_strings(dump):
        if japanese(s["text"]):
            uniq.setdefault(s["text"], []).append((s["bank"], s["id"]))
    items = [{"k": "%05d" % i, "jp": t} for i, t in enumerate(uniq)]
    d = dump / "translation" / "chunks"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("chunk_*.json"):
        if not old.name.endswith(".en.json"):
            old.unlink()
    for n in range(0, len(items), CHUNK):
        (d / ("chunk_%02d.json" % (n // CHUNK))).write_text(
            json.dumps(items[n:n + CHUNK], ensure_ascii=False, indent=0), encoding="utf-8")
    lines = [len(l) for it in items for l in it["jp"].split("\n")]
    lines.sort()
    print(f"{len(items)} unique Japanese strings in {(len(items) + CHUNK - 1) // CHUNK} chunks;"
          f" 95% of lines are <= {lines[int(len(lines) * .95)] if lines else 0} chars")


def export_missing(dump):
    """Strings that appeared after an extractor improvement: write them as one extra chunk."""
    d = dump / "translation" / "chunks"
    jp, en = {}, {}
    for f in sorted(d.glob("chunk_*.json")):
        if f.name.endswith(".en.json"):
            en.update(json.loads(f.read_text(encoding="utf-8")))
        else:
            jp.update({it["k"]: it["jp"] for it in json.loads(f.read_text(encoding="utf-8"))})
    look = Lookup({jp[k]: v for k, v in en.items() if k in jp})
    known = set(jp.values())
    todo = []
    for s in load_strings(dump):
        t = s["text"]
        if japanese(t) and t not in known and look.get(t) is None and t not in todo:
            todo.append(t)
    if not todo:
        print("nothing missing")
        return
    n = 1 + max(int(f.name[6:8]) for f in d.glob("chunk_*.json") if not f.name.endswith(".en.json"))
    first = 1 + max(int(k) for k in jp)
    items = [{"k": "%05d" % (first + i), "jp": t} for i, t in enumerate(todo)]
    (d / ("chunk_%02d.json" % n)).write_text(json.dumps(items, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(items)} new strings -> chunk_{n:02d}.json")


def fit_export(dump):
    """Translations that overflow their text box even after re-wrapping -> translation/fit/fit_NN.json."""
    import fit
    d = dump / "translation" / "chunks"
    jp, en = {}, {}
    for f in sorted(d.glob("chunk_*.json")):
        if f.name.endswith(".en.json"):
            en.update(json.loads(f.read_text(encoding="utf-8")))
        else:
            jp.update({it["k"]: it["jp"] for it in json.loads(f.read_text(encoding="utf-8"))})
    look = Lookup({jp[k]: v for k, v in en.items() if k in jp})
    rules = load_rules()
    banks = {}
    for s in load_strings(dump):
        banks.setdefault(s["bank"], []).append(s)
    todo = {}
    for bank, strings in banks.items():
        strings.sort(key=lambda x: x["offset"])
        for s, (w, n) in zip(strings, fit.limits_for([x["text"] for x in strings])):
            if not japanese(s["text"]):
                continue
            tr = look.get(s["text"])
            if tr is None or tr.strip() == "[junk]":
                continue
            tr = apply_rules(tr, rules)
            if fit.fit_text(tr, s["text"], w, n)[1] != "truncated":
                continue
            prefix = tr[0] if tr[0] == s["text"][0] and not tr[0].isascii() else ""
            key = (s["text"], w, n)
            todo.setdefault(key, {"jp": s["text"], "en": tr, "width": w, "lines": n, "prefix": prefix})
    out = dump / "translation" / "fit"
    out.mkdir(exist_ok=True)
    done = load_fitted(dump)
    items = [dict(v, k="%05d" % i) for i, ((jp, w, n), v) in enumerate(todo.items())
             if not any(fit.fit_text(apply_rules(c, rules), jp, w, n)[1] == "ok" for c in done.get(jp, ()))]
    start = 1 + max([int(f.name[4:6]) for f in out.glob("fit_*.json") if not f.name.endswith(".en.json")] + [-1])
    for n in range(0, len(items), 240):
        part = items[n:n + 240]
        for j, it in enumerate(part):
            it["k"] = "%02d-%03d" % (start + n // 240, j)
        (out / ("fit_%02d.json" % (start + n // 240))).write_text(json.dumps(part, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(items)} strings need condensing -> {(len(items) + 239) // 240} chunk(s) in {out}")


def load_fitted(dump):
    """Japanese text -> already condensed English variants (a narrower one still fits a wider box)."""
    out = dump / "translation" / "fit"
    done = {}
    if not out.exists():
        return done
    for f in sorted(out.glob("fit_*.en.json")):
        src_file = out / f.name.replace(".en.json", ".json")
        if not src_file.exists():
            continue
        src = {it["k"]: it for it in json.loads(src_file.read_text(encoding="utf-8"))}
        for k, v in json.loads(f.read_text(encoding="utf-8")).items():
            if k in src:
                done.setdefault(src[k]["jp"], []).append(v)
    return done


def merge(dump):
    d = dump / "translation" / "chunks"
    jp, en = {}, {}
    for f in sorted(d.glob("chunk_*.json")):
        if f.name.endswith(".en.json"):
            en.update(json.loads(f.read_text(encoding="utf-8")))
        else:
            jp.update({it["k"]: it["jp"] for it in json.loads(f.read_text(encoding="utf-8"))})
    by_text = Lookup({jp[k]: v for k, v in en.items() if k in jp})
    out = dump / "text_en"
    out.mkdir(exist_ok=True)
    total = done = 0
    result = []
    banks = {}
    for s in load_strings(dump):
        banks.setdefault(s["bank"], []).append(s)
    for bank, strings in banks.items():
        lines = [f"# bank {bank}: Japanese -> English draft. Review file, nothing is inserted into the ROM.",
                 "# EN lines keep control codes (<FA> etc.) and the leading speaker-ID character when there is one.", ""]
        for s in strings:
            if not japanese(s["text"]):
                continue
            total += 1
            tr = by_text.get(s["text"])
            done += tr is not None
            refs = "referenced" if s["refs"] else "unreferenced"
            lines += [f"#{s['id']:04d} @{s['offset']:04X} {refs}", "JP: " + s["text"].replace("\n", "\n    "),
                      "EN: " + (tr if tr is not None else "(missing)").replace("\n", "\n    "), "---"]
            result.append({"bank": bank, "id": s["id"], "offset": s["offset"], "jp": s["text"], "en": tr})
        (out / f"bank{bank:02d}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (dump / "translation" / "en.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{done}/{total} Japanese strings have a translation -> {out}")


def load_rules():
    g = json.loads((Path(__file__).parent / "docs" / "glossary.json").read_text(encoding="utf-8"))
    rules = [(re.compile("^" + re.escape(k) + "$"), v) for k, v in g.get("exact", {}).items() if not k.startswith("_")]
    rules += [(re.compile(k), v) for k, v in g["terms"].items()]
    rules += _split_name_rules(g["digimon"])
    for table, whole_word in ((g["digimon"], False), (g["humans"], True)):
        for src in sorted(table, key=len, reverse=True):
            for a, b in ((src, table[src]), (src.upper(), table[src].upper())):
                pat = re.escape(a)
                if whole_word:
                    # a one-character speaker-ID prefix may be glued in front of the name
                    pat = r"(?:(?<![A-Za-z])|(?<=^[A-Za-z0-9]))" + pat + r"(?![A-Za-z])"
                rules.append((re.compile(pat), b))
    return rules


def _split_name_rules(table):
    """Names broken over two lines ('Flamedra-\\nmon'): keep the break at the same letter position."""
    rules = []
    for src in sorted(table, key=len, reverse=True):
        pat = "".join(re.escape(c) + (r"(-?\n)?" if i < len(src) - 1 else "") for i, c in enumerate(src))
        dst = table[src]

        def rep(m, src=src, dst=dst):
            # keep every break the same number of letters away from the END of the name ("...-\nmon")
            out = dst
            for i, g in reversed(list(enumerate(m.groups()))):
                if g:
                    pos = max(1, min(len(out) - 1, len(dst) - (len(src) - 1 - i)))
                    out = out[:pos] + g + out[pos:]
            return out
        rules.append((re.compile(pat), rep))
    return rules


def apply_rules(text, rules):
    for rx, rep in rules:
        text = rx.sub(rep, text)
    return text


def normalize(dump):
    """Apply docs/glossary.json to every chunk_NN.en.json so all chunks use the same names/terms."""
    rules = load_rules()
    changed = 0
    for f in sorted((dump / "translation" / "chunks").glob("chunk_*.en.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for k, v in data.items():
            new = apply_rules(v, rules)
            changed += new != v
            data[k] = new
        f.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{changed} translated strings normalised")


def rename(dump):
    """English text that is already in the ROM: list every string whose names change."""
    rules = load_rules()
    out = dump / "text_en"
    out.mkdir(exist_ok=True)
    result, total = [], 0
    banks = {}
    for s in load_strings(dump):
        if japanese(s["text"]):
            continue
        new = apply_rules(s["text"], rules)
        if new != s["text"]:
            banks.setdefault(s["bank"], []).append((s, new))
    for old in out.glob("bank*_renamed.txt"):
        old.unlink()
    for bank, items in banks.items():
        lines = [f"# bank {bank}: English text already in the ROM whose character names change to the Japanese originals.",
                 "# '+N' = N bytes longer than the ROM text (matters for unreferenced fixed-size tables);\n# 'WIDER+N' = its longest line is N characters wider than the longest line of the ROM text.", ""]
        for s, new in items:
            grow = len(new) - len(s["text"])
            wider = max(map(len, new.split("\n"))) - max(map(len, s["text"].split("\n")))
            refs = "referenced" if s["refs"] else "unreferenced"
            lines += [f"#{s['id']:04d} @{s['offset']:04X} {refs}" + (f" +{grow}" if grow > 0 else "")
                      + (f" WIDER+{wider}" if wider > 0 else ""),
                      "ROM: " + s["text"].replace("\n", "\n     "), "NEW: " + new.replace("\n", "\n     "), "---"]
            result.append({"bank": bank, "id": s["id"], "offset": s["offset"], "rom": s["text"], "new": new, "grow": grow, "wider": max(wider, 0),
                           "fixed_table": not s["refs"]})
        total += len(items)
        (out / f"bank{bank:02d}_renamed.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (dump / "translation").mkdir(exist_ok=True)
    (dump / "translation" / "renames.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{total} existing English strings renamed ({sum(1 for r in result if r['grow'] > 0)} get longer) -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("export", "export-missing", "fit-export", "merge", "normalize", "rename"):
        sys.exit(__doc__)
    {"export": export, "export-missing": export_missing, "fit-export": fit_export, "merge": merge, "normalize": normalize, "rename": rename}[sys.argv[1]](Path(sys.argv[2]))
