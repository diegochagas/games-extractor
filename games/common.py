"""Pieces shared by the four Bandai Digimon WonderSwan games (same engine, same code page)."""

HIRA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽぁぃぅぇぉゃゅょっ"
KATA = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポァィゥェォャュョッ"

# FF = end of string in every game
CONTROLS = {0xFE: "\n", 0xFD: " ", 0xFA: "<FA>"}


def base_table(overrides=None):
    """8x16 font code page: digits, hiragana, katakana, punctuation, latin."""
    t = {i: str(i) for i in range(10)}
    t.update({0x0A + i: c for i, c in enumerate(HIRA)})
    t.update({0x5A + i: c for i, c in enumerate(KATA)})
    t.update({0xAA + i: c for i, c in enumerate("ヴー！？…～、'%#")})
    t.update({0xB4 + i: chr(65 + i) for i in range(26)})
    t.update({0xCE + i: chr(97 + i) for i in range(26)})
    t.update({0xE8 + i: c for i, c in enumerate("*+,-./:;<=>@()「」『』")})
    t.update(overrides or {})
    return t


def table_file(table, notes=()):
    lines = ["# byte=character. Control codes (not glyphs): FF=end FE=newline FD=space FA=placeholder"]
    lines += ["# " + n for n in notes]
    lines += ["%02X=%s" % (k, table[k]) for k in sorted(table)]
    return "\n".join(lines) + "\n"
