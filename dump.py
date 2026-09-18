#!/usr/bin/env python3
"""Dump every known asset of a supported WonderSwan ROM into a folder for manual review.

Read-only: the ROM is never modified. Default output is a folder named after
the ROM, next to the ROM.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

from games import anode_tamer, brave_tamer, d1_tamers, tag_tamers
from games.common import CONTROLS, table_file
from wsrom import archive, gfx, text
from wsrom.codecs import tiles_2bpp
from wsrom.rom import Rom

GAMES = [d1_tamers, tag_tamers, anode_tamer, brave_tamer]


def dump_info(rom, game, out):
    h = rom.header()
    lines = [f"ROM file : {rom.path.name}", f"Game     : {game.NAME}"]
    lines += [f"{k:18}: {v:#x}" if isinstance(v, int) and not isinstance(v, bool) else f"{k:18}: {v}" for k, v in h.items()]
    ok = h["checksum_stored"] == h["checksum_computed"]
    lines.append("checksum           : " + ("OK" if ok else "MISMATCH (ROM was modified/patched after release, or is a bad dump)"))
    (out / "rom_info.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def dump_fonts(rom, game, out):
    d = out / "fonts"
    d.mkdir(exist_ok=True)
    for f in game.FONTS:
        per = f["tiles_w"] * f["tiles_h"]
        start = f["offset"]
        bank = rom.bank(f["bank"])
        if f["bpp"] == 2:
            tiles = tiles_2bpp(bank[start:start + f["count"] * per * 16])
        else:  # 1bpp, one block per plane
            size = f["count"] * per * 8
            planes = [np.unpackbits(np.frombuffer(bank[start + p * size:start + (p + 1) * size], dtype=np.uint8)
                                    .reshape(-1, 8, 1), axis=2) for p in range(f["planes"])]
            tiles = sum(pl << i for i, pl in enumerate(planes))
        glyphs = []
        for i in range(f["count"]):
            t = tiles[i * per:(i + 1) * per]
            rows = [np.hstack(t[r * f["tiles_w"]:(r + 1) * f["tiles_w"]]) for r in range(f["tiles_h"])]
            glyphs.append(np.vstack(rows))
        gfx.glyph_sheet(glyphs, 16).save(d / f"{f['name']}_labelled.png")
        # 1:1 sheet, 16 glyphs per row: this is the one to edit
        gh, gw = glyphs[0].shape
        rows = (len(glyphs) + 15) // 16
        idx = np.zeros((rows * gh, 16 * gw), np.uint8)
        for i, g in enumerate(glyphs):
            idx[i // 16 * gh:i // 16 * gh + gh, i % 16 * gw:i % 16 * gw + gw] = g
        gfx._image(idx, gfx.mono_palette((0, 3, 5, 7)), 4).save(d / f"{f['name']}.png")
    (d / "table.tbl").write_text(table_file(game.TABLE, game.TABLE_NOTES), encoding="utf-8")


def dump_text(rom, game, out):
    d = out / "text"
    d.mkdir(exist_ok=True)
    table = game.TABLE
    summary = {}
    for bank_no, cfg in game.TEXT_BANKS.items():
        base = cfg["base"] if cfg["base"] is not None else rom.linear_base(bank_no)
        strings = text.extract_strings(rom, bank_no, base, cfg["sources"], table, CONTROLS)
        js = []
        for kind, picked in (("", [s for s in strings if s["refs"]]),
                             ("_unreferenced", [s for s in strings if not s["refs"] and len(s["raw"]) >= 4])):
            lines = [f"# {game.NAME} - text in ROM bank {bank_no} (file offset {bank_no * 0x10000:#x})",
                     "# id | offset in bank | byte length | pointers that reference it (bank:offset)",
                     "# <XX> = byte with no glyph / unknown control. Review dump: do not edit yet.", ""]
            if kind:
                lines.insert(1, "# Found by scanning, no far pointer seen (fixed-size tables, near offsets). Expect some junk.")
            for s in picked:
                i = len(js)
                refs = " ".join("%d:%04X" % r for r in s["refs"][:6]) or "-"
                more = " (+%d more)" % (len(s["refs"]) - 6) if len(s["refs"]) > 6 else ""
                decoded = text.decode(s["raw"], table, CONTROLS)
                lines += [f"#{i:04d} @{s['offset']:04X} len={len(s['raw'])} refs={refs}{more}", decoded, "---"]
                js.append({"id": i, "bank": bank_no, "offset": s["offset"], "hex": s["raw"].hex(),
                           "text": decoded, "refs": [list(r) for r in s["refs"]],
                           "header": s["header"]})
            (d / f"bank{bank_no:02d}{kind}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        (d / f"bank{bank_no:02d}.json").write_text(json.dumps(js, ensure_ascii=False, indent=1), encoding="utf-8")
        summary[bank_no] = (len(strings), sum(1 for s in strings if not s["refs"]))
    return summary


def _resolve(p, structs, blobs):
    """Pointer -> leaf blob, looking through single-pointer wrapper structs."""
    for _ in range(3):
        if p in blobs:
            return blobs[p]
        s = [q for q in structs.get(p, []) if q is not None]
        if len(s) != 1:
            return None
        p = s[0]
    return None


def _pals_for(bank, blob, bpp):
    if blob is None:
        return gfx.gray_palette(bpp) if bpp == 4 else gfx.mono_palette()
    if blob.kind == "palette":
        return archive.palettes(bank, blob)
    return gfx.mono_palette(blob.info["shades"])


def dump_bank_graphics(rom, bank_no, out, manifest):
    bank = rom.bank(bank_no)
    structs, blobs = archive.scan(bank)
    d = out / "images" / f"bank{bank_no:02d}"
    d.mkdir(parents=True, exist_ok=True)
    used, counts = set(), {"pictures": 0, "sprites": 0, "tilesheets": 0}
    entries = []

    def tiles_of(blob):
        return gfx.decode_tiles(archive.tile_bytes(bank, blob), blob.info["bpp"])

    for saddr in sorted(structs):
        seq = [(_resolve(p, structs, blobs) if p is not None else None) for p in structs[saddr]]
        # picture = tiles + tilemap (+ palette)
        for i in range(len(seq) - 1):
            t, m = seq[i], seq[i + 1]
            if not (t and m and t.kind == "tiles" and m.kind == "tilemap") or t.offset in used:
                continue
            p = seq[i + 2] if i + 2 < len(seq) and seq[i + 2] and seq[i + 2].kind.startswith("palette") else None
            if p is not None and len(t.info.get("bpp_candidates", [])) > 1:
                t.info["bpp"] = 4 if p.kind == "palette" else 2
            w, h, cells = archive.map_cells(bank, m)
            name = f"{t.offset:04X}_picture_{w * 8}x{h * 8}.png"
            gfx.render_map(tiles_of(t), t.info["bpp"], w, h, cells, _pals_for(bank, p, t.info["bpp"])).save(d / name)
            used.update({t.offset, m.offset})
            counts["pictures"] += 1
            entries.append({"file": name, "type": "picture", "tiles": t.offset, "tilemap": m.offset,
                            "palette": p.offset if p else None})
        # sprite frames = struct of tiles followed by struct of layouts
        ptrs = [p for p in structs[saddr]]
        for i in range(len(ptrs) - 1):
            a, b = structs.get(ptrs[i]), structs.get(ptrs[i + 1])
            if not a or not b:
                continue
            ta = [blobs.get(q) for q in a if q is not None]
            lb = [blobs.get(q) for q in b if q is not None]
            if not ta or len(ta) != len(lb) or not all(x and x.kind == "tiles" for x in ta) \
                    or not all(x and x.kind == "sprite_layout" for x in lb):
                continue
            pal = next((x for x in (_resolve(q, structs, blobs) for q in ptrs[i + 2:i + 5] if q is not None)
                        if x and x.kind.startswith("palette")), None)
            for fno, (t, lay) in enumerate(zip(ta, lb)):
                if t.offset in used:
                    continue
                im = gfx.render_sprite(tiles_of(t), t.info["bpp"], archive.sprite_pieces(bank, lay),
                                       _pals_for(bank, pal, t.info["bpp"]))
                if im is None:
                    continue
                name = f"{t.offset:04X}_sprite_frame{fno}.png"
                im.save(d / name)
                used.update({t.offset, lay.offset})
                counts["sprites"] += 1
                entries.append({"file": name, "type": "sprite", "tiles": t.offset, "layout": lay.offset,
                                "palette": pal.offset if pal else None})
    for off, b in sorted(blobs.items()):
        if b.kind == "tiles" and off not in used:
            name = f"{off:04X}_tiles_{b.info['bpp']}bpp.png"
            gfx.render_sheet(tiles_of(b), b.info["bpp"], _pals_for(bank, None, b.info["bpp"])).save(d / name)
            counts["tilesheets"] += 1
            entries.append({"file": name, "type": "tilesheet", "tiles": off})
    manifest[bank_no] = {
        "rendered": entries,
        "blobs": [{"offset": b.offset, "length": b.length, "kind": b.kind,
                   **{k: v for k, v in b.info.items()}} for _, b in sorted(blobs.items())],
    }
    if not entries:
        d.rmdir()
    return counts


def write_readme(out, rom, game, tsum, totals):
    h = rom.header()
    patched = h["checksum_stored"] != h["checksum_computed"]
    lines = [
        f"# {game.NAME} - asset dump", "",
        f"Source ROM: `{rom.path.name}` (not modified; this folder is a read-only review dump).", "",
        "## What is here", "",
        "- `rom_info.txt` - header fields and checksum status." + (" **Checksum mismatch: this ROM was already patched"
            " (it contains English strings/menus next to the Japanese script).**" if patched else ""),
        "- `fonts/` - the fonts as 1:1 indexed PNGs, labelled sheets (hex code above each glyph) and `table.tbl`"
        " (byte -> character). Check the table against the labelled sheet.",
        "- `text/bankNN.txt` - strings reached through a pointer (safe to relocate later)."
        " `bankNN_unreferenced.txt` - strings found by scanning (fixed-size name tables etc., with some junk)."
        " `bankNN.json` - same data plus the raw bytes, used by the future re-inserter.",
        "- `images/bankNN/` - one PNG per graphic, named `<offset>_<type>`:",
        "  - `picture` = tiles + tilemap + palette assembled the way the game shows it;",
        "  - `sprite_frameN` = sprite animation frame assembled from its piece list;",
        "  - `tiles_*bpp` = raw tile sheet whose layout is not assembled yet (mostly battle effects), grey palette.",
        "- `images/manifest.json` - every data blob of every bank (offset, size, type, compressed or not).", "",
        "PNGs are indexed: palette slots equal the in-game colour indexes, keep them when editing.", "",
        "## Text notes", "",
        "- Control codes: `FF` end, `FE` newline (shown as a line break), `FD` space, `FA` = placeholder slot"
        " (e.g. player name). `<XX>` = unknown byte.",
        "- In dialogue lines the first character is really a speaker/portrait ID byte, not text.", "",
        "## Totals", "",
    ]
    lines += [f"- bank {b}: {n} strings, {u} of them unreferenced" for b, (n, u) in tsum.items()]
    lines += [f"- {k}: {v}" for k, v in totals.items()]
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rom")
    ap.add_argument("--out", help="output folder (default: <rom folder>/<rom name>)")
    args = ap.parse_args()
    rom = Rom(args.rom)
    game = next((g for g in GAMES if g.matches(rom.header())), None)
    if game is None:
        sys.exit("Unsupported ROM: no game definition matches its header.")
    out = Path(args.out) if args.out else rom.path.with_suffix("")
    out.mkdir(parents=True, exist_ok=True)

    dump_info(rom, game, out)
    dump_fonts(rom, game, out)
    tsum = dump_text(rom, game, out)
    manifest, totals = {}, {}
    for n in range(rom.nbanks):
        if n in game.TEXT_BANKS or not archive.is_archive(rom.bank(n)):
            continue
        c = dump_bank_graphics(rom, n, out, manifest)
        for k, v in c.items():
            totals[k] = totals.get(k, 0) + v
    (out / "images" / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    write_readme(out, rom, game, tsum, totals)
    print("text :", {b: f"{n} strings ({u} unreferenced)" for b, (n, u) in tsum.items()})
    print("gfx  :", totals)
    print("out  :", out)


if __name__ == "__main__":
    main()
