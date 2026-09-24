#!/usr/bin/env python3
"""List a DeviantArt gallery folder (titles, links, dates, image URLs and the
artist's description text) through DeviantArt's RSS backend, which needs no
login or JavaScript.

    deviantart_rss.py USER FOLDER_ID OUT.json      e.g. cerberus-rack 64173492

Only the metadata is stored; the images stay on DeviantArt (they are the
artist's work) and the story book links to them.
"""
import html
import json
import re
import sys
import urllib.request


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 games-extractor/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def main(user, folder, out):
    items = []
    offset = 0
    while True:
        s = fetch("https://backend.deviantart.com/rss.xml?type=deviation&q=gallery%%3A%s%%2F%s&offset=%d" % (user, folder, offset))
        found = re.findall(r"<item>(.*?)</item>", s, re.S)
        if not found:
            break
        for it in found:
            g = lambda tag: (re.search(r"<%s>(.*?)</%s>" % (tag, tag), it, re.S) or [None, ""])[1]
            m = re.search(r'<media:content[^>]+url="([^"]+)"', it)
            d = html.unescape(re.sub(r"<br\s*/?>", "\n", html.unescape(g("description"))))
            items.append({"title": html.unescape(g("title")), "url": g("link"), "date": g("pubDate"),
                          "image": m.group(1) if m else "", "description": re.sub("<[^>]+>", "", d).strip()})
        offset += 60
    json.dump(items, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("%d deviations" % len(items))


if __name__ == "__main__":
    main(*sys.argv[1:4])
