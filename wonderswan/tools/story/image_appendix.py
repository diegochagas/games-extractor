#!/usr/bin/env python3
"""Build the "Apêndice: galeria de imagens do cartucho" insertion spec for add_content.py: every dumped image that the
story book does not already show, bank by bank, as image grids with the file name in the caption.

    image_appendix.py BOOK.docx DUMP_DIR LABELS.json GAME_KEY OUT_SPEC.json --before "Heading" --pictures "Pictures/… folder name" [--summary-after "start of the last summary line"]

DUMP_DIR has images/manifest.json (dump.py output); LABELS.json = bank_labels_pt.json ({GAME_KEY: {bankNN: {label, desc}}}).
Images already in the book are detected by pixel comparison (any integer scale, with or without cropping to content).
"""
import hashlib, io, json, os, sys, zipfile
from PIL import Image


def sig(im):
    return (im.size, hashlib.md5(im.convert("RGBA").tobytes()).hexdigest())


def crop(im):
    bb = im.convert("RGBA").getchannel("A").getbbox()
    return im.crop(bb) if bb else im


def variants(im):
    w, h = im.size
    for f in range(1, 11):
        if w % f == 0 and h % f == 0:
            yield sig(im if f == 1 else im.resize((w // f, h // f), Image.NEAREST))


def used_images(book, base, man):
    dump = {}
    for b, v in man.items():
        for e in v["rendered"]:
            rel = "bank%02d/%s" % (int(b), e["file"]); p = base + rel
            if not os.path.exists(p): continue
            im = Image.open(p).convert("RGBA")
            dump.setdefault(sig(im), rel)
            c = crop(im)
            if c.size != im.size: dump.setdefault(sig(c), rel)
    z = zipfile.ZipFile(book); found = set()
    for n in z.namelist():
        if not n.startswith("word/media/") or n.endswith("/"): continue
        try: im = Image.open(io.BytesIO(z.read(n))).convert("RGBA")
        except Exception: continue
        for c in (im, crop(im)):
            hit = next((dump[k] for k in variants(c) if k in dump), None)
            if hit: found.add(hit); break
    return found


def main():
    a = sys.argv[1:]
    book, dump_dir, labels_path, key, out = a[:5]
    before = a[a.index("--before") + 1]
    pictures = a[a.index("--pictures") + 1]
    summary_after = a[a.index("--summary-after") + 1] if "--summary-after" in a else None
    base = os.path.join(dump_dir, "images") + "/"
    man = json.load(open(base + "manifest.json"))
    labels = json.load(open(labels_path, encoding="utf-8")).get(key, {})
    found = used_images(book, base, man)
    n_all = sum(1 for v in man.values() for e in v["rendered"])
    blocks = [{"pagebreak": True}, {"h1": "Apêndice: galeria de imagens do cartucho"},
              {"p": "O cartucho guarda %d imagens (telas e retratos montados, quadros de sprites e folhas de tiles de efeitos). %d delas ilustram os capítulos deste livro; as demais estão aqui, banco por banco, na ordem em que aparecem na ROM, com o nome do arquivo em cada legenda. A cópia de todas as imagens, organizada da mesma forma, está na pasta \"%s\" do Nextcloud (uma pasta por banco), e o documento \"Image index\" da pasta do jogo traz os detalhes técnicos (offset na ROM, tiles, paleta) de cada uma." % (n_all, len(found), pictures)},
              {"note": "Telas e janelas em fundo verde, ciano ou magenta usam essa cor como transparência no jogo. Os sprites mostram cada quadro de animação; as folhas de tiles são a matéria-prima dos efeitos de batalha, ainda não montada."}]
    total = 0
    for b, v in sorted(man.items(), key=lambda kv: int(kv[0])):
        bank = "bank%02d" % int(b)
        ents = [e for e in v["rendered"] if os.path.exists(base + bank + "/" + e["file"]) and bank + "/" + e["file"] not in found]
        if not ents: continue
        lab = labels.get(bank, {})
        blocks.append({"h2": "Banco %02d%s (%d imagens)" % (int(b), " - " + lab["label"] if lab.get("label") else "", len(ents))})
        if lab.get("desc"): blocks.append({"note": lab["desc"]})
        big, small, spr, ts = [], [], [], []
        for e in ents:
            p = base + bank + "/" + e["file"]; w, h = Image.open(p).size; off = e["file"].split("_")[0]
            if e["type"] == "picture":
                (big if w >= 208 and h >= 128 else small).append({"img": p, "caption": "%s (%dx%d)" % (off, w, h)})
            elif e["type"].startswith("sprite"):
                spr.append({"img": p, "caption": off + " q" + e["file"].split("frame")[-1].replace(".png", "")})
            else:
                ts.append({"img": p, "caption": off + " tiles"})
        if big: blocks.append({"grid": big, "cols": 2, "width": 300})
        if small: blocks.append({"grid": small, "cols": 5, "width": 110})
        if spr: blocks.append({"grid": spr, "cols": 8, "width": 64})
        if ts: blocks.append({"grid": ts, "cols": 3, "width": 200})
        total += len(ents)
    spec = []
    if summary_after:
        spec.append({"after_para": summary_after, "blocks": [{"summary": "Apêndice: galeria de imagens do cartucho", "text": "Todas as imagens do cartucho que não ilustram os capítulos: telas, retratos, sprites e efeitos, banco por banco, com o nome de cada arquivo."}]})
    spec.append({"before": before, "blocks": blocks})
    json.dump(spec, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("%s: %d images already in the book, %d in the appendix" % (os.path.basename(book), len(found), total))


if __name__ == "__main__":
    main()
