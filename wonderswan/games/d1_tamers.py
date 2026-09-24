"""Digimon Adventure 02 - D-1 Tamers (WonderSwan Color, Bandai 2000)."""
from .common import CONTROLS, base_table

NAME = "Digimon Adventure 02 - D-1 Tamers"
TABLE = base_table()
TABLE_NOTES = ["In the 16x16 DigiCode font mode the engine folds katakana/small kana onto glyphs 00-52."]
CODE_BANKS = range(52, 64)

# Raw 2bpp tiles in bank 56 (far pointers 857F:000E / 8773:000E in the text renderer).
FONTS = [
    {"name": "font_small_8x16", "bank": 56, "offset": 0x57FE, "count": 250, "bpp": 2, "tiles_w": 1, "tiles_h": 2},
    {"name": "font_digicode_16x16", "bank": 56, "offset": 0x773E, "count": 0x56, "bpp": 2, "tiles_w": 2, "tiles_h": 2},
]

# bank -> base address of the bank when the text is read (None = fixed linear window)
# and the banks searched for pointers into it.
TEXT_BANKS = {
    23: {"base": 0x30000, "sources": [23, *CODE_BANKS]},
    55: {"base": None, "sources": list(CODE_BANKS)},
    56: {"base": None, "sources": list(CODE_BANKS)},
    57: {"base": None, "sources": list(CODE_BANKS)},
}


def matches(header):
    return header["developer_id"] == 0x01 and header["game_id"] == 0x03 and header["size"] == 0x400000
