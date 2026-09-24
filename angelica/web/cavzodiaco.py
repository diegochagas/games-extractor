#!/usr/bin/env python3
"""Collect CavZodiaco.com.br's coverage of Saint Seiya Online.

    cavzodiaco.py OUT_DIR [--query saint-seiya-online]

Walks the site search (informacoes/pesquisar/<query>/pagina-N), keeps the
articles whose title or URL mention the game, downloads each article and every
content image it embeds (images from /imagesNN/ folders, skipping site chrome)
into OUT_DIR/html, OUT_DIR/images and writes OUT_DIR/articles.json with title,
date, URL, paragraphs (for reading only, the story book quotes nothing from
them) and image file names.
"""
import html
import json
import os
import re
import sys
import time
import urllib.request

BASE = "https://www.cavzodiaco.com.br"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) games-extractor/1.0"}


def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        data = r.read()
    return data if binary else data.decode("latin-1")


def main(out, query="saint-seiya-online"):
    os.makedirs(os.path.join(out, "html"), exist_ok=True)
    os.makedirs(os.path.join(out, "images"), exist_ok=True)
    links = []
    for page in range(1, 40):
        url = "%s/informacoes/pesquisar/%s" % (BASE, query) + ("" if page == 1 else "/pagina-%d" % page)
        try:
            s = get(url)
        except Exception:
            break
        found = 0
        for m in re.finditer(r'<a href="(/noticia/[^"]+)"[^>]*>(.*?)</a>', s, re.S):
            href, t = m.group(1), html.unescape(re.sub("<[^>]+>", "", m.group(2)).strip())
            if "online" in (t + href).lower() and href not in [l[0] for l in links]:
                links.append((href, t))
                found += 1
        if not found:
            break
        time.sleep(1)
    articles = []
    for n, (href, title) in enumerate(links, 1):
        fn = os.path.join(out, "html", "%02d.html" % n)
        if not os.path.exists(fn):
            try:
                open(fn, "w", encoding="latin-1").write(get(BASE + href))
            except Exception as exc:
                print("skip", href, exc)
                continue
            time.sleep(1)
        s = open(fn, encoding="latin-1").read()
        paras = [html.unescape(re.sub("<[^>]+>", "", p)).strip() for p in re.findall(r"<p[^>]*>(.*?)</p>", s, re.S)]
        paras = [p for p in paras if len(p) > 40 and "cavzodiaco" not in p.lower() and "Anônimo" not in p]
        imgs = [i for i in re.findall(r'<img[^>]+src="([^"]+)"', s)
                if re.search(r"/images\d\d/", i) and not re.search(r"logo|banner|qrcode|icone|estrela|mail|googleplay|appstore|pix", i)]
        files = []
        for u in dict.fromkeys(imgs):
            full = ("https:" + u) if u.startswith("//") else (BASE + u if u.startswith("/") else u)
            name = full.replace(BASE + "/", "").replace("/", "_")
            path = os.path.join(out, "images", name)
            if not os.path.exists(path):
                try:
                    open(path, "wb").write(get(full, binary=True))
                    time.sleep(0.3)
                except Exception as exc:
                    print("image failed", full, exc)
                    continue
            files.append(name)
        m = re.match(r"/noticia/(\d\d)/(\d\d)/(\d{4})/", href)
        date = "%s-%s-%s" % (m.group(3), m.group(2), m.group(1)) if m else ""
        articles.append({"n": n, "url": BASE + href, "title": title, "date": date, "paragraphs": paras, "images": files})
    # images repeated in several articles are site chrome (colouring-page promo, social banners): drop them
    counts = {}
    for a in articles:
        for i in a["images"]:
            counts[i] = counts.get(i, 0) + 1
    for a in articles:
        a["images"] = [i for i in a["images"] if counts[i] < 4]
    articles.sort(key=lambda a: a["date"])
    json.dump(articles, open(os.path.join(out, "articles.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("%d articles, %d images" % (len(articles), sum(len(a["images"]) for a in articles)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "saint-seiya-online")
