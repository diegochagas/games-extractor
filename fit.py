"""Line-width model: English must fit the box the Japanese text was written for."""
import re
import textwrap

TOK = re.compile(r"<FC>\d|<[0-9A-F]{2}>")


def vis(line):
    """Visible width: colour switches (<FC>n) are free, other control bytes take one cell."""
    return len(TOK.sub(lambda m: "" if m.group(0).startswith("<FC>") else "x", line))


DIALOGUE_WIDTH = 20     # cells per line of the portrait dialogue box (measured in the emulator: 20x2)


def limits_for(jp_strings, window=12):
    """(width, lines, prefix) per string of one bank, in offset order.

    - Text with up to two lines is dialogue/system text: 18 cells, as many lines as the
      Japanese neighbourhood uses (1 or 2).
    - Taller text (descriptions) keeps the width and height the Japanese uses around it.
    - One-line text that is much shorter than a dialogue line (names, menu words) keeps the
      width of the widest neighbour, so fixed-width fields do not overflow.
    """
    base = box_limits(jp_strings, window)
    out = []
    for text, (w, n) in zip(jp_strings, base):
        own = [vis(l) for l in text.split("\n")]
        if len(own) <= 2 and n <= 2 and w >= 12:
            w = DIALOGUE_WIDTH
        out.append((w, max(n, len(own))))
    return out


def header_len(jp, en):
    """Length of the non-displayed header the translation copied from the Japanese.

    Records start with a speaker/portrait byte, and a string the dump began a little early
    also carries pointer-table bytes. None of that is drawn, so it must not count towards the
    box width. Translators copy it verbatim, so it is the common prefix of both texts, minus
    any ASCII letters at its end (those belong to the English sentence).
    """
    n = 0
    while n < min(len(jp), len(en)) and jp[n] == en[n]:
        n += 1
    # Only trust the run up to its last kana: a header always ends in one. Digits and letters
    # after that (a "02 " list index, a digit speaker byte) may well be drawn, and counting a
    # drawn character as hidden would let the line overflow the box.
    while n and en[n - 1].isascii():
        n -= 1
    return 0 if n >= len(en) else n


def fit_text(en, jp, width, lines):
    """English fitted to the box: (text, how) with how in ok / rewrapped / truncated."""
    k = header_len(jp, en)
    prefix, body = en[:k], en[k:]
    if all(vis(l) <= width for l in body.split("\n")) and body.count("\n") < lines:
        return en, "ok"
    wrapped = reflow(body, width, lines)
    if wrapped is not None:
        return prefix + wrapped, "rewrapped"
    # last resort: keep whole words that fit, drop the rest
    words = body.replace("\n", " ").split(" ")
    out, cur = [], ""
    for wd in words:
        wd = wd if vis(wd) <= width else wd[:width]
        if not cur:
            cur = wd
        elif vis(cur + " " + wd) <= width:
            cur += " " + wd
        else:
            out.append(cur)
            cur = wd
            if len(out) == lines:
                break
    if len(out) < lines and cur:
        out.append(cur)
    return prefix + "\n".join(out[:lines]), "truncated"


def box_limits(strings, window=12):
    """Per string (list sorted by offset): (max line width, max line count) seen in the Japanese
    text of the string itself and of its neighbours, which share the same kind of text box."""
    dims = [([vis(l) for l in s.split("\n")]) for s in strings]
    out = []
    for i in range(len(strings)):
        near = dims[max(0, i - window):i + window + 1]
        # ignore freak neighbours (data misread as text) by using the 90th percentile
        widths = sorted(max(d) for d in near)
        lines = sorted(len(d) for d in near)
        w = max(max(dims[i]), widths[int(len(widths) * 0.9) - 1] if len(widths) > 3 else widths[-1])
        n = max(len(dims[i]), lines[int(len(lines) * 0.9) - 1] if len(lines) > 3 else lines[-1])
        out.append((w, n))
    return out


def reflow(text, width, lines):
    """Re-wrap words to `width`; returns None when it cannot fit in `lines` lines."""
    if all(vis(l) <= width for l in text.split("\n")) and text.count("\n") < lines:
        return text
    words = text.replace("\n", " ").split(" ")
    out, cur = [], ""
    for w in words:
        if not cur:
            cur = w
        elif vis(cur + " " + w) <= width:
            cur += " " + w
        else:
            out.append(cur)
            cur = w
    out.append(cur)
    if len(out) > lines or any(vis(l) > width for l in out):
        return None
    return "\n".join(out)
