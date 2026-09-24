#!/usr/bin/env python3
"""Convert .docx documents to LibreOffice .odt, updating the table of contents (page numbers) on the way.

    docx_to_odt.py [--out-dir DIR] [--drop-paragraph PREFIX]... [--trash] FILE.docx...

- Runs a private headless LibreOffice (own user profile, so an open LibreOffice window is not disturbed).
- Every index of the document (table of contents etc.) is updated after layout, so the TOC shows page numbers
  (a .docx written by a generator only has an empty TOC field until someone updates it by hand).
- Heading N styles without an outline level get level N (otherwise the TOC stays empty).
- --drop-paragraph removes paragraphs starting with PREFIX (e.g. an "update this field in Word" hint).
- The .odt is written next to the .docx (or into --out-dir) with the same name; --trash moves the .docx to the
  desktop trash (gio trash) after a successful conversion.
To go back (e.g. to patch a book with wonderswan/tools/story/add_content.py): soffice --headless --convert-to docx FILE.odt
"""
import os, shutil, subprocess, sys, tempfile, time

import uno
from com.sun.star.beans import PropertyValue


def prop(name, value):
    p = PropertyValue(); p.Name = name; p.Value = value
    return p


def start_office():
    profile = tempfile.mkdtemp(prefix="lo-profile-")
    pipe = "docx2odt_%d" % os.getpid()
    proc = subprocess.Popen(["soffice", "--headless", "--invisible", "--nologo", "--norestore", "--nodefault",
                             "-env:UserInstallation=file://" + profile,
                             "--accept=pipe,name=%s;urp;StarOffice.ComponentContext" % pipe],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
    for _ in range(120):
        try:
            ctx = resolver.resolve("uno:pipe,name=%s;urp;StarOffice.ComponentContext" % pipe)
            break
        except Exception:
            time.sleep(0.5)
    else:
        proc.kill(); raise SystemExit("LibreOffice did not start")
    desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    return proc, desktop, profile


def drop_paragraphs(doc, prefixes):
    n = 0
    enum = doc.Text.createEnumeration()
    victims = []
    while enum.hasMoreElements():
        par = enum.nextElement()
        if par.supportsService("com.sun.star.text.Paragraph") and any(par.getString().startswith(p) for p in prefixes):
            victims.append(par)
    for par in victims:
        par.dispose(); n += 1
    return n


def convert(desktop, src, dst, prefixes):
    url = uno.systemPathToFileUrl(os.path.abspath(src))
    doc = desktop.loadComponentFromURL(url, "_blank", 0, (prop("Hidden", True), prop("ReadOnly", False)))
    try:
        dropped = drop_paragraphs(doc, prefixes) if prefixes else 0
        # headings whose style carries no outline level are invisible to the table of contents: give Heading N level N
        styles = doc.getStyleFamilies().getByName("ParagraphStyles")
        for n in range(1, 7):
            name = "Heading %d" % n
            if styles.hasByName(name) and styles.getByName(name).OutlineLevel == 0:
                styles.getByName(name).OutlineLevel = n
        idx = doc.getDocumentIndexes()
        for i in range(idx.getCount()):
            idx.getByIndex(i).update()
        doc.refresh()
        for i in range(idx.getCount()):  # second pass: page numbers settle after the TOC itself took its pages
            idx.getByIndex(i).update()
        pages = doc.getCurrentController().getPropertyValue("PageCount") if doc.getCurrentController() else None
        tmp = dst + ".tmp.odt"
        doc.storeToURL(uno.systemPathToFileUrl(os.path.abspath(tmp)), (prop("FilterName", "writer8"),))
        os.replace(tmp, dst)
        return idx.getCount(), dropped, pages
    finally:
        doc.close(True)


def main():
    a = sys.argv[1:]
    out_dir, prefixes, trash, files = None, [], False, []
    while a:
        x = a.pop(0)
        if x == "--out-dir": out_dir = a.pop(0)
        elif x == "--drop-paragraph": prefixes.append(a.pop(0))
        elif x == "--trash": trash = True
        else: files.append(x)
    if not files:
        raise SystemExit(__doc__)
    proc, desktop, profile = start_office()
    try:
        for f in files:
            dst = os.path.join(out_dir or os.path.dirname(os.path.abspath(f)), os.path.splitext(os.path.basename(f))[0] + ".odt")
            t = time.time()
            n_idx, dropped, pages = convert(desktop, f, dst, prefixes)
            print("%s -> %s (%d index(es) updated, %d paragraph(s) dropped, %s pages, %.0fs)" % (
                os.path.basename(f), os.path.basename(dst), n_idx, dropped, pages, time.time() - t), flush=True)
            if trash and os.path.getsize(dst) > 0:
                subprocess.run(["gio", "trash", f], check=True)
    finally:
        try: desktop.terminate()
        except Exception: pass
        try: proc.wait(timeout=30)
        except Exception: proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
