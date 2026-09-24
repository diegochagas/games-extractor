#!/usr/bin/env python3
"""Append sections (headings, paragraphs, images, image grids, tables) to an existing .docx without any library.

    add_content.py BOOK.docx SPEC.json [--out OUT.docx | --in-place] [--before "Heading 1 text"]

The result goes to ~/Downloads/<book file name> ($STORY_OUTPUT_DIR replaces ~/Downloads, --out names
the file), so it can be checked before it replaces anything; --in-place rewrites the book itself.

SPEC.json = list of blocks, in order:
  {"h1": "title"}                      Heading 1
  {"h2": "title"}                      Heading 2
  {"p": "text"}                        paragraph ("**bold**" at the start of the text is kept bold)
  {"speech": "Name", "text": "..."}    dialogue line: bold speaker + text
  {"note": "text"}                     small grey paragraph
  {"summary": "Chapter title", "text": "one-line summary"}   a line of the "Conteúdo deste livro" page (bold title — text)
  {"img": "path.png", "caption": "…", "width": 320}      one image (width in px at 96 dpi), centred, with a caption
  {"grid": [{"img": "path", "caption": "…"}, ...], "cols": 4, "width": 150}   table of images with captions
  {"table": [["h1","h2"], ["a","b"], ...]}   simple table, first row = header
  {"pagebreak": true}
  {"replace_para": "start of an existing paragraph", "speech": "Name" (optional), "text": "new text"}
                                       rewrites the first paragraph starting with that text (keeps its style; "" deletes it)
  {"replace_text": "old", "with": "new", "all": false, "raw": false}
                                       replaces text inside the XML (a line inside a multi-line paragraph, a table cell...);
                                       raw=true matches the XML itself (e.g. to drop a whole run)
The blocks are inserted before the heading (any level) whose text equals --before (default: at the end of the body).
SPEC.json may also be a list of insertions: [{"before": "heading text" | null, "after_para": "start of a paragraph" | null, "blocks": [...]}, ...]
("after_para" inserts right after the first paragraph whose text starts with that string; the anchors are searched in the
document as it is at that moment, so later insertions can anchor on earlier ones).
Images are resized (nearest neighbour, keeping the pixel look) to at most 2x their width and stored as PNG.
With --in-place a BOOK.docx.bak copy of the original is kept next to it.
"""
import io, json, os, re, shutil, sys, zipfile
from xml.sax.saxutils import escape
from PIL import Image

NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
EMU = 9525  # EMU per pixel at 96 dpi


def run(text, bold=False, italic=False, size=None, color=None):
    rpr = ""
    if bold: rpr += "<w:b/><w:bCs/>"
    if italic: rpr += "<w:i/><w:iCs/>"
    if color: rpr += '<w:color w:val="%s"/>' % color
    if size: rpr += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size, size)
    out = []
    for i, part in enumerate(str(text).split("\n")):
        if i: out.append("<w:r>%s<w:br/></w:r>" % ("<w:rPr>%s</w:rPr>" % rpr if rpr else ""))
        out.append('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % ("<w:rPr>%s</w:rPr>" % rpr if rpr else "", escape(part)))
    return "".join(out)


def para(runs, style=None, jc=None, after=120, keep_next=False):
    ppr = ""
    if style: ppr += '<w:pStyle w:val="%s"/>' % style
    if keep_next: ppr += "<w:keepNext/>"
    ppr += '<w:spacing w:after="%d"/>' % after
    if jc: ppr += '<w:jc w:val="%s"/>' % jc
    return "<w:p><w:pPr>%s</w:pPr>%s</w:p>" % (ppr, runs)


class Doc:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.files = {n: self.z.read(n) for n in self.z.namelist()}
        self.xml = self.files["word/document.xml"].decode("utf-8")
        self.rels = self.files["word/_rels/document.xml.rels"].decode("utf-8")
        self.next_rid = max([int(x) for x in re.findall(r'Id="rId(\d+)"', self.rels)] + [0]) + 1
        self.next_doc_pr = max([int(x) for x in re.findall(r'<wp:docPr id="(\d+)"', self.xml)] + [0]) + 1
        self.next_media = len([n for n in self.files if n.startswith("word/media/")]) + 1
        self.new_media = {}

    def add_image(self, path, width_px, max_scale=2):
        im = Image.open(path).convert("RGBA")
        w, h = im.size
        scale = min(max_scale, width_px / w) if w < width_px else width_px / w
        tw = max(1, int(round(w * scale))); th = max(1, int(round(h * scale)))
        if abs(scale - round(scale)) < 1e-6 and scale >= 1:  # integer upscale: keep pixels crisp
            im = im.resize((tw, th), Image.NEAREST)
        else:
            im = im.resize((tw, th), Image.LANCZOS if scale < 1 else Image.NEAREST)
        buf = io.BytesIO(); im.save(buf, "PNG", optimize=True)
        name = "word/media/add_%04d.png" % self.next_media; self.next_media += 1
        self.new_media[name] = buf.getvalue()
        rid = "rId%d" % self.next_rid; self.next_rid += 1
        self.rels = self.rels.replace("</Relationships>", '<Relationship Id="%s" Type="%s/image" Target="media/%s"/></Relationships>' % (rid, NS_R, os.path.basename(name)))
        did = self.next_doc_pr; self.next_doc_pr += 1
        cx, cy = tw * EMU, th * EMU
        return ('<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="%d" cy="%d"/><wp:effectExtent t="0" r="0" b="0" l="0"/>'
                '<wp:docPr id="%d" name="img%d" descr=""/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
                '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
                '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="0" name="" descr=""/><pic:cNvPicPr><a:picLocks noChangeAspect="1" noChangeArrowheads="1"/></pic:cNvPicPr></pic:nvPicPr>'
                '<pic:blipFill><a:blip r:embed="%s" cstate="none"/><a:srcRect/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                '<pic:spPr bwMode="auto"><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>'
                % (cx, cy, did, did, rid, cx, cy))

    def block(self, b):
        if "replace_text" in b:
            old = b["replace_text"] if b.get("raw") else escape(b["replace_text"]); new = b.get("with", "") if b.get("raw") else escape(b.get("with", ""))
            if old not in self.xml: print("warning: text %r not found for replace_text" % b["replace_text"])
            self.xml = self.xml.replace(old, new) if b.get("all") else self.xml.replace(old, new, 1)
            return ""
        if "replace_para" in b:
            self.replace_para(b["replace_para"], b.get("speech"), b["text"]); return ""
        if "h1" in b: return para(run(b["h1"]), "Heading1")
        if "h2" in b: return para(run(b["h2"]), "Heading2")
        if "p" in b:
            t = b["p"]
            m = re.match(r"\*\*(.+?)\*\*(.*)", t, re.S)
            return para((run(m.group(1), bold=True) + run(m.group(2))) if m else run(t))
        if "speech" in b: return para(run(b["speech"] + ": ", bold=True) + run(b["text"]), after=60)
        if "note" in b: return para(run(b["note"], size=18, color="595959"))
        if "summary" in b:
            return '<w:p><w:pPr><w:spacing w:before="60" w:after="20"/></w:pPr>%s%s</w:p>' % (run(b["summary"], bold=True, size=19), run(" — " + b["text"], size=18))
        if "pagebreak" in b: return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
        if "img" in b:
            out = para(self.add_image(b["img"], b.get("width", 320)), jc="center", after=40, keep_next=bool(b.get("caption")))
            if b.get("caption"): out += para(run(b["caption"], size=18, color="595959"), jc="center", after=160)
            return out
        if "grid" in b:
            cols = b.get("cols", 4); width = b.get("width", 150); items = b["grid"]
            cw = int(9300 / cols)
            rows = []
            for i in range(0, len(items), cols):
                cells = []
                for j in range(cols):
                    it = items[i + j] if i + j < len(items) else None
                    inner = ""
                    if it:
                        inner = para(self.add_image(it["img"], width), jc="center", after=20)
                        if it.get("caption"): inner += para(run(it["caption"], size=15, color="595959"), jc="center", after=20)
                    else:
                        inner = "<w:p/>"
                    cells.append('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/></w:tcPr>%s</w:tc>' % (cw, inner))
                rows.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>%s</w:tr>' % "".join(cells))
            tbl = ('<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/><w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/><w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders></w:tblPr>'
                   '<w:tblGrid>%s</w:tblGrid>%s</w:tbl>' % (cw * cols, "".join('<w:gridCol w:w="%d"/>' % cw for _ in range(cols)), "".join(rows)))
            return tbl + "<w:p/>"
        if "table" in b:
            data = b["table"]; ncol = max(len(r) for r in data); cw = int(9300 / ncol)
            rows = []
            for ri, r in enumerate(data):
                cells = []
                for ci in range(ncol):
                    t = r[ci] if ci < len(r) else ""
                    shade = '<w:shd w:val="clear" w:color="auto" w:fill="DCE6F1"/>' if ri == 0 else ""
                    cells.append('<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>%s</w:tcPr>%s</w:tc>' % (cw, shade, para(run(t, bold=(ri == 0), size=18), after=20)))
                rows.append('<w:tr>%s%s</w:tr>' % ('<w:trPr><w:tblHeader/></w:trPr>' if ri == 0 else '', "".join(cells)))
            bd = "".join('<w:%s w:val="single" w:sz="4" w:color="BFBFBF"/>' % s for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
            return ('<w:tbl><w:tblPr><w:tblW w:w="%d" w:type="dxa"/><w:tblBorders>%s</w:tblBorders></w:tblPr><w:tblGrid>%s</w:tblGrid>%s</w:tbl><w:p/>'
                    % (cw * ncol, bd, "".join('<w:gridCol w:w="%d"/>' % cw for _ in range(ncol)), "".join(rows)))
        raise ValueError("unknown block: %s" % list(b))

    def replace_para(self, start, speech, text):
        from xml.sax.saxutils import unescape
        norm = lambda t: re.sub(r"\s+", " ", unescape(t, {"&quot;": '"', "&apos;": "'"})).strip()
        for m in re.finditer(r"<w:p[ >](?:(?!</w:p>).)*?</w:p>", self.xml, re.S):
            p = m.group(0); t = norm(re.sub(r"<[^>]+>", "", p))
            if t.startswith(norm(start)):
                ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, re.S)
                runs = (run(speech + ": ", bold=True) if speech else "") + run(text)
                newp = ("<w:p>" + (ppr.group(0) if ppr else "") + runs + "</w:p>") if (text or speech) else ""  # empty text = delete the paragraph
                self.xml = self.xml[:m.start()] + newp + self.xml[m.end():]
                return True
        print("warning: paragraph %r not found for replace_para" % start)
        return False

    def insert(self, blocks, before=None, after_para=None):
        from xml.sax.saxutils import unescape
        body = "".join(self.block(b) for b in blocks)
        pos = None
        norm = lambda t: re.sub(r"\s+", " ", unescape(t, {"&quot;": '"', "&apos;": "'"})).strip()
        if before or after_para:
            for m in re.finditer(r"<w:p[ >](?:(?!</w:p>).)*?</w:p>", self.xml, re.S):
                p = m.group(0); t = norm(re.sub(r"<[^>]+>", "", p))
                if before and re.search(r'w:val="Heading\d"', p) and t == norm(before):
                    pos = m.start(); break
                if after_para and t.startswith(norm(after_para)):
                    pos = m.end()
                    if self.xml.rfind("<w:tbl>", 0, pos) > self.xml.rfind("</w:tbl>", 0, pos):  # inside a table cell: go after the table
                        pos = self.xml.find("</w:tbl>", pos) + len("</w:tbl>")
                    break
            if pos is None:
                print("warning: anchor %r not found, appending at the end" % (before or after_para))
        if pos is None:
            pos = self.xml.rfind("<w:sectPr")
        self.xml = self.xml[:pos] + body + self.xml[pos:]

    def save(self, out):
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zo:
            for n, data in self.files.items():
                if n == "word/document.xml": data = self.xml.encode("utf-8")
                elif n == "word/_rels/document.xml.rels": data = self.rels.encode("utf-8")
                zo.writestr(n, data)
            for n, data in self.new_media.items():
                zo.writestr(n, data)


def main():
    a = sys.argv[1:]
    book, spec = a[0], a[1]
    if "--out" in a:
        out = a[a.index("--out") + 1]
    elif "--in-place" in a:
        out = book
    else:
        root = os.path.expanduser(os.environ.get("STORY_OUTPUT_DIR", "~/Downloads"))
        os.makedirs(root, exist_ok=True)
        out = os.path.join(root, os.path.basename(book))
        if os.path.abspath(out) == os.path.abspath(book):
            raise SystemExit("the book already sits in the output folder; use --out or --in-place")
    before = a[a.index("--before") + 1] if "--before" in a else None
    spec_data = json.load(open(spec, encoding="utf-8"))
    d = Doc(book)
    if spec_data and isinstance(spec_data[0], dict) and "blocks" in spec_data[0]:
        blocks = []
        for ins in spec_data:
            d.insert(ins["blocks"], ins.get("before"), ins.get("after_para")); blocks += ins["blocks"]
    else:
        blocks = spec_data
        d.insert(blocks, before)
    if out == book: shutil.copy2(book, book + ".bak")
    d.save(out + ".tmp"); os.replace(out + ".tmp", out)
    print("%s: +%d blocks, +%d images -> %s" % (os.path.basename(book), len(blocks), len(d.new_media), out))


if __name__ == "__main__":
    main()
