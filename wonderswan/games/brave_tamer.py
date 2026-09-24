"""Digimon Tamers - Brave Tamer (WonderSwan Color, Bandai 2001)."""
from .common import CONTROLS, base_table

NAME = "Digimon Tamers - Brave Tamer"
TABLE = base_table({0xB1: "。", 0xB3: "@", 0xEB: ".", 0xEC: "/", 0xED: "=", 0xEE: ":", 0xEF: "#",
                    0xF0: "Ⅰ", 0xF1: "Ⅱ", 0xF2: "Ⅲ", 0xF3: "Ⅳ"})
TABLE_NOTES = ["FC introduces an inline control sequence (argument bytes follow)."]
CODE_BANKS = range(52, 64)

FONTS = [
    {"name": "font_small_8x16", "bank": 57, "offset": 0x5E10, "count": 250, "bpp": 2, "tiles_w": 1, "tiles_h": 2},
    {"name": "font_digicode_16x16", "bank": 57, "offset": 0x7D50, "count": 0x56, "bpp": 2, "tiles_w": 2, "tiles_h": 2},
]

TEXT_BANKS = {
    31: {"base": 0x30000, "sources": [31, *CODE_BANKS]},
    39: {"base": 0x30000, "sources": [39, *CODE_BANKS]},
    55: {"base": None, "sources": list(CODE_BANKS)},
    58: {"base": None, "sources": list(CODE_BANKS)},
}


# The font has no apostrophe. English needs one and no longer needs the Japanese comma,
# so glyph B0 is redrawn (same 8x16 2bpp glyph the D-1 Tamers patch uses).
ENCODE_EXTRA = {"'": 0xB0}
BINARY_PATCHES = [{
    "bank": 57, "offset": 0x5E10 + 0xB0 * 32, "why": "font glyph B0 redrawn as an apostrophe",
    "data": bytes.fromhex("0000000000000000300030001020001000000000000000000000000000000000"),
}]


def matches(header):
    return header["developer_id"] == 0x01 and header["game_id"] == 0x1D
