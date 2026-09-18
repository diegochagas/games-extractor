"""Table-based text decoding and pointer-anchored string discovery."""
import struct
from pathlib import Path


def load_table(path):
    table = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        code, char = line.split("=", 1)
        table[int(code, 16)] = char
    return table


def decode(raw, table, controls):
    out = []
    for b in raw:
        if b in controls:
            out.append(controls[b])
        elif b in table:
            out.append(table[b])
        else:
            out.append("<%02X>" % b)
    return "".join(out)


def find_pointers(rom, target_bank, base, source_banks):
    """All normalized far pointers in source_banks that land inside target_bank."""
    hits = {}
    for sb in source_banks:
        buf = rom.bank(sb)
        for o in range(len(buf) - 3):
            off, seg = struct.unpack_from("<HH", buf, o)
            if off < 16 and seg:
                lin = seg * 16 + off - base
                if 0 <= lin < 0x10000:
                    hits.setdefault(lin, []).append((sb, o))
    return hits


def looks_like_text(raw, table, controls, min_ratio=0.9):
    if not raw:
        return False
    known = sum(1 for b in raw if b in table or b in controls)
    return known / len(raw) >= min_ratio


def extract_strings(rom, bank_no, base, source_banks, table, controls, end=0xFF, max_len=400):
    """Strings reached by a pointer, plus unreferenced FF-terminated runs between them."""
    bank = rom.bank(bank_no)
    refs = find_pointers(rom, bank_no, base, source_banks)
    found = {}
    # records without a speaker byte start with an FF header and the pointer aims at that header
    for t, who in list(refs.items()):
        if bank[t] == end and t + 1 < len(bank) and bank[t + 1] != end:
            refs.setdefault(("hdr", t + 1), []).extend(who)
    for t, who in refs.items():
        hdr = 0
        if isinstance(t, tuple):
            hdr, t = 1, t[1]
        e = bank.find(bytes([end]), t)
        if e <= t or e - t > max_len:
            continue
        if t and end not in bank[max(0, t - 2):t] and not _is_ptr(bank, t - 4, base):
            continue
        t2 = _true_start(bank, t, e, base)
        if t2 != t:
            # the pointer hit a table entry; the text behind the table keeps only its own references
            t, who, hdr = t2, refs.get(t2, []), 0
        raw = bank[t:e]
        if raw and looks_like_text(raw, table, controls) and _texty(raw, table):
            if t not in found or len(who) > len(found[t]["refs"]):
                found[t] = {"offset": t, "raw": raw, "refs": who, "header": hdr}
    # unreferenced leftovers
    covered = sorted((s["offset"], s["offset"] + len(s["raw"])) for s in found.values())
    pos = 0
    for m in _runs(bank, end):
        t, e = m
        if any(a <= t < b or a < e <= b for a, b in covered):
            continue
        t = _true_start(bank, t, e, base)
        if any(a <= t < b for a, b in covered):
            continue
        raw = bank[t:e]
        if len(raw) >= 3 and looks_like_text(raw, table, controls, 1.0) and _texty(raw, table) and len(set(raw)) > 2:
            # a run that starts right behind a pointer table is often the target of a pointer after all
            hdr = 1 if refs.get(("hdr", t)) else 0
            found[t] = {"offset": t, "raw": raw, "refs": refs.get(("hdr", t)) or refs.get(t, []), "header": hdr}
    # a record may begin with one far pointer (linked dialogue entries): those 4 bytes are a
    # known pointer slot, not text
    slots = {o for who in refs.values() for sb, o in who if sb == bank_no}
    for t in sorted(found):
        s = found[t]
        n = t
        while n in slots and n + 4 < t + len(s["raw"]):
            n += 4
        if n != t:
            del found[t]
            raw = s["raw"][n - t:]
            if looks_like_text(raw, table, controls) and _texty(raw, table) and n not in found:
                found[n] = {"offset": n, "raw": raw, "refs": refs.get(n, []), "header": 0}
    return [found[k] for k in sorted(found)]


def _true_start(bank, t, e, base):
    """Skip pointer-table bytes glued in front of a string (no FF between table and text).

    Two or more back-to-back far pointers inside [t, e) cannot be text; the string
    really starts after the last of them.
    """
    def group(o):
        return _is_ptr(bank, o, base) or bank[o:o + 4] == b"\0\0\0\0"

    start = t
    p = t
    while p + 8 <= e:
        # tables are lists of far pointers, often as {pointer, 00000000} records
        if _is_ptr(bank, p, base) and group(p + 4):
            p += 8
            while p + 4 <= e and group(p):
                p += 4
            start = p
        else:
            p += 1
    return start


def _is_ptr(bank, o, base):
    if o < 0:
        return False
    off, seg = struct.unpack_from("<HH", bank, o)
    return off < 16 and 0 <= seg * 16 + off - base < 0x10000


def _char_class(ch):
    if ch.isdigit():
        return "d"
    if "\u3040" <= ch <= "\u309f":
        return "h"
    if "\u30a0" <= ch <= "\u30ff":
        return "k"
    if ch.isascii() and ch.isalpha():
        return "l"
    return None  # punctuation/space: neutral


def _texty(raw, table):
    """Reject data tables that happen to decode as characters.

    Real text is mostly letters/kana, does not flip between scripts on every
    character, and is not a run of consecutive byte values.
    """
    chars = [table[b] for b in raw if b in table]
    letters = [c for c in chars if _char_class(c) in ("h", "k", "l")]
    if len(letters) < max(2, len(raw) // 2):
        return False
    if len(raw) >= 3 and all(b - a == 1 for a, b in zip(raw, raw[1:])):
        return False
    classes = [c for c in map(_char_class, chars) if c]
    switches = sum(1 for a, b in zip(classes, classes[1:]) if a != b)
    return switches <= max(1, (len(classes) - 1) * 0.45)


def _runs(bank, end):
    start = 0
    for i, b in enumerate(bank):
        if b == end:
            if i > start:
                yield start, i
            start = i + 1
