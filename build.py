#!/usr/bin/env python3
"""Build a patched copy of a ROM from its dump folder (English text, Japanese names).

The original ROM is only read. Output: <dump>/patched/<rom name> [EN].<ext>, an IPS patch
and build_report.txt.

Insertion rules
- A string is rewritten in place whenever the English fits the original byte length. The
  length (and therefore every terminator position) is preserved by padding line ends with
  spaces, so tables that are walked string by string keep working.
- A string that does not fit is moved into unused ROM space of the always-mapped (linear)
  banks, but only if far pointers to its exact start are known; every such pointer is
  updated. A far pointer into the linear window works no matter which bank is paged in, so
  text of paged data banks can live there too. The old location keeps a shortened English
  copy for any reference this tool does not know about.
- A string that does not fit and has no known pointer gets a hand-made short form from
  docs/short_forms.json; without one its original bytes are left untouched (see the report).
"""
import argparse
import re
import struct
import sys
from pathlib import Path

from dump import GAMES
from games.common import CONTROLS
from translate import Lookup, apply_rules, japanese, load_rules, load_strings
from wsrom.rom import Rom

import json

END = 0xFF
TOKEN = re.compile(r"<([0-9A-F]{2})>")
# ASCII written by the translators -> glyph that exists in the kana-era fonts
FALLBACK = {"!": "！", "?": "？", "~": "～", '"': "'", "-": "ー", "&": "+", ";": ":", "*": "+"}


class Encoder:
    def __init__(self, game):
        self.rev = {}
        for code, ch in sorted(game.TABLE.items(), reverse=True):
            self.rev[ch] = code          # lowest code wins for duplicated glyphs
        self.space = self.rev.get(" ", 0xFD)
        self.rev.update(getattr(game, "ENCODE_EXTRA", {}))
        self.missing = {}

    def encode(self, text):
        out = bytearray()
        text = text.replace("...", "…") if "…" in self.rev else text.replace("…", "...")
        pos = 0
        while pos < len(text):
            m = TOKEN.match(text, pos)
            if m:
                out.append(int(m.group(1), 16))
                pos = m.end()
                continue
            ch = text[pos]
            pos += 1
            if ch == "\n":
                out.append(0xFE)
            elif ch == " ":
                out.append(self.space)
            elif ch in self.rev:
                out.append(self.rev[ch])
            elif FALLBACK.get(ch) in self.rev:
                out.append(self.rev[FALLBACK[ch]])
            else:
                self.missing[ch] = self.missing.get(ch, 0) + 1
                out.append(self.space)
        return bytes(out)


def decode(raw, game):
    out = []
    for b in raw:
        out.append(CONTROLS[b] if b in CONTROLS else game.TABLE.get(b, "<%02X>" % b))
    return "".join(out)


def visible(line):
    return len(TOKEN.sub("x", line))


def fit_in_place(text, enc, size):
    """Encode `text` to exactly `size` bytes by padding line ends with spaces, or None."""
    raw = enc.encode(text)
    if len(raw) > size:
        return None
    pad = size - len(raw)
    if pad == 0:
        return raw, 0
    lines = text.split("\n")
    width = max(visible(l) for l in lines)
    room = [width - visible(l) for l in lines]
    for i in range(len(lines)):
        take = min(pad, room[i])
        lines[i] += " " * take
        pad -= take
    lines[-1] += " " * pad              # whatever is left goes after the last line
    return enc.encode("\n".join(lines)), pad


def shorten(text, enc, size):
    """Last resort for strings that cannot move: trim the end of the longest line until it fits."""
    lines = text.split("\n")
    while len(enc.encode("\n".join(lines))) > size:
        cut = [k for k in range(len(lines)) if visible(lines[k]) > 1 and not lines[k].endswith(">")]
        if not cut:
            return None
        i = max(cut, key=lambda k: visible(lines[k]))
        lines[i] = lines[i][:-1].rstrip()
    return "\n".join(lines)


def free_space(bank, protect_tail):
    """(start, end) of the FF run that closes the bank."""
    end = len(bank) - (16 if protect_tail else 0)
    start = end
    while start > 0 and bank[start - 1] == END:
        start -= 1
    start += 32                          # the first FFs may be terminators/padding of real data
    start += start & 1
    return (start, end) if end - start >= 64 else (end, end)


class Space:
    """Free ROM space: unused tails of the linear banks plus the old spans of moved strings.

    A region inside a paged data bank can only hold strings of that same bank (the pointer
    keeps the paged segment); regions in linear banks can hold any string.
    """

    def __init__(self, rom):
        self.rom = rom
        self.first_linear = rom.nbanks - 12
        self.regions = []                       # [bank, start, end]
        for bn in range(self.first_linear, rom.nbanks):
            fs, fe = free_space(rom.bank(bn), bn == rom.nbanks - 1)
            if fe > fs:
                self.regions.append([bn, fs, fe])

    def release(self, bank, start, end):
        for r in self.regions:
            if r[0] == bank and 0 <= start - r[2] <= 1:     # glue spans separated by a pad byte
                r[2] = end
                return
        self.regions.append([bank, start, end])

    def alloc(self, size, bank):
        size += size & 1
        fits = [r for r in self.regions if r[2] - (r[1] + (r[1] & 1)) >= size
                and (r[0] >= self.first_linear or r[0] == bank)]
        if not fits:
            return None
        # paged strings use up their own bank first; otherwise best fit
        r = min(fits, key=lambda r: (r[0] >= self.first_linear and bank < self.first_linear, r[0] != bank, r[2] - r[1]))
        start = r[1] + (r[1] & 1)
        r[1] = start + size
        return r[0], start

    def left(self):
        return sum(r[2] - r[1] for r in self.regions)


def ips(original, patched):
    out = bytearray(b"PATCH")
    i, n = 0, len(original)
    while i < n:
        if original[i] == patched[i]:
            i += 1
            continue
        j = i
        while j < n and j - i < 0xFFFF and (original[j] != patched[j] or original[j:j + 8] != patched[j:j + 8]):
            j += 1
        if i == 0x454F46:                # offset that spells "EOF"
            i -= 1
        out += i.to_bytes(3, "big") + (j - i).to_bytes(2, "big") + patched[i:j]
        i = j
    return bytes(out + b"EOF")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("--dump", help="dump folder (default: <rom folder>/<rom name>)")
    args = ap.parse_args()
    rom = Rom(args.rom)
    game = next((g for g in GAMES if g.matches(rom.header())), None)
    if game is None:
        sys.exit("Unsupported ROM.")
    dump = Path(args.dump) if args.dump else rom.path.with_suffix("")
    data = bytearray(rom.data)
    enc = Encoder(game)
    rules = load_rules()
    shorts = json.loads((Path(__file__).parent / "docs" / "short_forms.json").read_text(encoding="utf-8"))

    chunks = dump / "translation" / "chunks"
    jp, en = {}, {}
    for f in sorted(chunks.glob("chunk_*.json")) if chunks.exists() else []:
        if f.name.endswith(".en.json"):
            en.update(json.loads(f.read_text(encoding="utf-8")))
        else:
            jp.update({it["k"]: it["jp"] for it in json.loads(f.read_text(encoding="utf-8"))})
    look = Lookup({jp[k]: v for k, v in en.items() if k in jp})

    space = Space(rom)
    stats = {"in place": 0, "relocated": 0, "short form": 0, "left original": 0, "kept short copy (no space)": 0, "unchanged": 0, "skipped junk": 0,
             "skipped untranslated": 0, "skipped overlap": 0, "skipped round-trip": 0, "failed": 0}
    notes = []
    by_bank = {}
    for s in load_strings(dump):
        by_bank.setdefault(s["bank"], []).append(s)

    moving, placed = [], []
    for bank_no, strings in sorted(by_bank.items()):
        cfg = game.TEXT_BANKS[bank_no]
        bstart = bank_no * 0x10000
        last_end = -1
        for s in sorted(strings, key=lambda x: x["offset"]):
            raw = bytes.fromhex(s["hex"])
            off = s["offset"]
            if off < last_end:
                stats["skipped overlap"] += 1
                continue
            if japanese(s["text"]):
                new = look.get(s["text"])
                if new is None:
                    stats["skipped untranslated"] += 1
                    continue
                if new.strip() == "[junk]":
                    stats["skipped junk"] += 1
                    continue
                new = apply_rules(new, rules)
            else:
                new = apply_rules(s["text"], rules)
                if new == s["text"]:
                    stats["unchanged"] += 1
                    continue
            if enc.encode(decode(raw, game)) != raw:
                stats["skipped round-trip"] += 1
                notes.append(f"bank {bank_no} @{off:04X}: original bytes do not round-trip, left untouched")
                continue
            last_end = off + len(raw) + 1
            payload = enc.encode(new)
            if len(payload) <= len(raw):
                if s["refs"]:
                    # reached through pointers only: end the string early, the rest is never read
                    body = payload + bytes([END]) * (len(raw) - len(payload))
                else:
                    body, overflow = fit_in_place(new, enc, len(raw))
                    if overflow:
                        notes.append(f"bank {bank_no} @{off:04X}: {overflow} padding spaces after the last line")
                data[bstart + off:bstart + off + len(raw)] = body
                stats["in place"] += 1
                continue
            # does not fit. With pointers: move it (a shortened copy stays behind for unknown references).
            if s["refs"]:
                short = next((c for c in shorts.get(new, []) if len(enc.encode(c)) <= len(raw)), None) \
                    or shorten(new, enc, len(raw))
                if short is not None:
                    data[bstart + off:bstart + off + len(raw)] = fit_in_place(short, enc, len(raw))[0]
                moving.append((bank_no, s, new, payload))
                continue
            # no pointer (referenced from code, fixed-size record, or dead data): only a hand-made short form
            short = next((c for c in shorts.get(new, []) if len(enc.encode(c)) <= len(raw)), None)
            if short is None:
                stats["left original"] += 1
                notes.append(f"bank {bank_no} @{off:04X}: does not fit and cannot move, original kept: {new!r}")
            else:
                data[bstart + off:bstart + off + len(raw)] = fit_in_place(short, enc, len(raw))[0]
                stats["short form"] += 1
                notes.append(f"bank {bank_no} @{off:04X}: short form {short!r} for {new!r}")

    # the old spans of everything that moves become free space (own bank only for paged banks)
    for bank_no, s, new, payload in moving:
        hdr = s.get("header", 0)
        space.release(bank_no, s["offset"] - hdr, s["offset"] + len(s["hex"]) // 2 + 1)
    for bank_no, s, new, payload in sorted(moving, key=lambda m: -len(m[3])):
        hdr = s.get("header", 0)
        record = bytes([END]) * hdr + payload + bytes([END])
        spot = space.alloc(len(record), bank_no)
        if spot is None:
            stats["kept short copy (no space)"] += 1
            notes.append(f"bank {bank_no} @{s['offset']:04X}: no free space, kept shortened text for {new!r}")
            continue
        nb, no = spot
        data[nb * 0x10000 + no:nb * 0x10000 + no + len(record)] = record
        cfg = game.TEXT_BANKS[bank_no]
        if nb >= rom.nbanks - 12:
            lin = rom.linear_base(nb) + no
        else:
            lin = cfg["base"] + no
        ptr = struct.pack("<HH", lin & 0xF, lin >> 4)
        for rb, ro in s["refs"]:
            data[rb * 0x10000 + ro:rb * 0x10000 + ro + 4] = ptr
        stats["relocated"] += 1
        placed.append((bank_no, s, payload))

    # read every moved string back through each of its pointers, the way the game will
    bad = 0
    for bank_no, s, payload in placed:
        hdr = s.get("header", 0)
        for rb, ro in s["refs"]:
            o, sg = struct.unpack_from("<HH", data, rb * 0x10000 + ro)
            lin = sg * 16 + o
            at = (lin >> 16) - 16 + rom.nbanks if lin >= 0x40000 else bank_no
            pos = at * 0x10000 + (lin & 0xFFFF)
            got = bytes(data[pos:pos + hdr + len(payload) + 1])
            if got != bytes([END]) * hdr + payload + bytes([END]):
                bad += 1
    stats["pointer check failures"] = bad

    for patch in getattr(game, "BINARY_PATCHES", []):
        o = patch["bank"] * 0x10000 + patch["offset"]
        data[o:o + len(patch["data"])] = patch["data"]
        notes.append(f"binary patch: {patch['why']}")

    data[-2:] = struct.pack("<H", sum(data[:-2]) & 0xFFFF)

    out = dump / "patched"
    out.mkdir(exist_ok=True)
    target = out / f"{rom.path.stem} [EN]{rom.path.suffix}"
    target.write_bytes(data)
    (out / f"{rom.path.stem} [EN].ips").write_bytes(ips(rom.data, bytes(data)))
    report = [f"{game.NAME}: patched ROM built from {rom.path.name}", ""]
    report += [f"{k:22}: {v}" for k, v in stats.items()]
    report += [f"{'free ROM space left':22}: {space.left()} bytes"]
    if enc.missing:
        report += ["", "characters with no glyph (written as a space): " + " ".join(f"{c!r}x{n}" for c, n in enc.missing.items())]
    report += ["", *notes]
    (out / "build_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(target.name, stats, "missing glyphs:", enc.missing)


if __name__ == "__main__":
    main()
