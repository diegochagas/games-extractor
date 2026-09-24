#!/usr/bin/env python3
"""Fetch the official seiya.wanmei.com picture galleries (concept art,
wallpapers, screenshots) from the Wayback Machine.

    wanmei_wayback.py OUT_DIR

The site is offline; the 2015 snapshots of /picture/{original,wallpaper,
printscreen}/index*.htm list the full-size JPGs under /resources/. Images are
fetched one every few seconds (the archive rate-limits) into OUT_DIR/img with
the gallery name as prefix; OUT_DIR/gallery_urls.txt keeps the source URLs.
"""
import os
import re
import sys
import time
import urllib.request

SITE = "http://seiya.wanmei.com/picture/"
PAGES = ["original/index"] + ["wallpaper/index%s" % i for i in ["", 1, 2, 3, 4, 5, 6]] + ["printscreen/index%s" % i for i in ["", 1, 2, 3, 4]]
WB = "http://web.archive.org/web/2015id_/"


def fetch(url, tries=3):
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "games-extractor/1.0"}), timeout=120) as r:
                return r.read()
        except Exception as exc:
            if t == tries - 1:
                print("failed", url, exc)
                return None
            time.sleep(20)


def main(out):
    os.makedirs(os.path.join(out, "img"), exist_ok=True)
    urls = {}
    for p in PAGES:
        data = fetch(WB + SITE + p + ".htm")
        time.sleep(4)
        if not data:
            continue
        s = data.decode("gbk", "replace")
        for u in re.findall(r'href="(http://seiya\.wanmei\.com/resources/[^"#]+\.jpg)', s):
            urls.setdefault(u, p.split("/")[0])
    with open(os.path.join(out, "gallery_urls.txt"), "w") as f:
        f.write("\n".join("%s\t%s" % (k, u) for u, k in urls.items()))
    for u, kind in urls.items():
        path = os.path.join(out, "img", "%s_%s" % (kind, os.path.basename(u)))
        if os.path.exists(path):
            continue
        data = fetch(WB + u)
        if data and len(data) > 2000:
            open(path, "wb").write(data)
        time.sleep(6)
    print("%d gallery urls, %d files" % (len(urls), len(os.listdir(os.path.join(out, "img")))))


if __name__ == "__main__":
    main(sys.argv[1])
