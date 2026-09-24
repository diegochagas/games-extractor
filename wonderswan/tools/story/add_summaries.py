#!/usr/bin/env python3
"""Add a static "Conteúdo deste livro" list (chapter title + one-line summary) right
after the "Sumário" table of contents of a story .docx, so the summary page has
content even where the TOC field was never updated (LibreOffice, mobile viewers).

    add_summaries.py BOOK.docx SUMMARIES.json [--out OUT.docx]

SUMMARIES.json = {"<Heading 1 text>": "<summary>", ...}. Heading 2 titles under
each chapter are listed in a smaller line. The file is rewritten in place unless
--out is given; a copy of the original is kept next to it as BOOK.docx.bak.
"""
import json
import re
import shutil
import sys
import zipfile
from xml.sax.saxutils import escape


def para(runs, before=60, after=20, indent=0):
    xml = '<w:p><w:pPr><w:spacing w:before="%d" w:after="%d"/>%s</w:pPr>' % (before, after, '<w:ind w:left="%d"/>' % indent if indent else '')
    for text, bold, size, color in runs:
        rpr = '<w:rPr>%s<w:sz w:val="%d"/><w:szCs w:val="%d"/>%s</w:rPr>' % ('<w:b/>' if bold else '', size, size, '<w:color w:val="%s"/>' % color if color else '')
        xml += '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, escape(text))
    return xml + '</w:p>'


def main(argv):
    src = argv[0]
    summaries = json.load(open(argv[1], encoding="utf-8"))
    out = argv[argv.index("--out") + 1] if "--out" in argv else src
    zin = zipfile.ZipFile(src)
    doc = zin.read("word/document.xml").decode("utf-8")
    paras = list(re.finditer(r"<w:p[ >].*?</w:p>", doc, re.S))
    heads = []
    for i, m in enumerate(paras):
        s = re.search(r'<w:pStyle w:val="Heading(\d)"', m.group(0))
        if s:
            heads.append((i, int(s.group(1)), "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", m.group(0)))))
    # insertion point: before the first Heading 1 after "Sumário"
    sum_idx = next((i for i, lvl, t in heads if lvl == 1 and t.strip().lower().startswith("sumário")), None)
    if sum_idx is None:
        print("no Sumário heading in", src)
        return 1
    target = next(i for i, lvl, t in heads if lvl == 1 and i > sum_idx)
    block = [para([("Conteúdo deste livro", True, 24, None)], before=200, after=80)]
    chapters = [(i, lvl, t) for i, lvl, t in heads if i > sum_idx]
    matched = 0
    for k, (i, lvl, t) in enumerate(chapters):
        if lvl != 1:
            continue
        t = t.strip()
        summ = summaries.get(t) or summaries.get(re.sub(r"\s+", " ", t)) or ""
        if summ:
            matched += 1
        block.append(para([(t, True, 19, None), ((" — " + summ) if summ else "", False, 18, None)]))
        subs = [x[2].strip() for x in chapters[k + 1:] if x[1] == 2]
        subs = subs[:next((n for n, x in enumerate(chapters[k + 1:]) if x[1] == 1), len(subs))]
        subs = [s for s in subs if s][:14]
        if subs:
            block.append(para([(" · ".join(subs), False, 15, "595959")], before=0, after=60, indent=360))
    pos = paras[target].start()
    new_doc = doc[:pos] + "".join(block) + doc[pos:]
    if out == src:
        shutil.copy2(src, src + ".bak")
    zout = zipfile.ZipFile(out + ".tmp", "w", zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/document.xml":
            data = new_doc.encode("utf-8")
        zout.writestr(item, data)
    zout.close()
    shutil.move(out + ".tmp", out)
    print("%s: %d chapters, %d with summary" % (out, sum(1 for x in chapters if x[1] == 1), matched))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
