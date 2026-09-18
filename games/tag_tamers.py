"""Digimon Adventure 02 - Tag Tamers (WonderSwan mono, Bandai 2000). Known dump carries a fan English patch."""
from .common import CONTROLS, base_table

NAME = "Digimon Adventure 02 - Tag Tamers"
TABLE = base_table({0xB0: "'", 0xB1: "。", 0xB3: "&"})
TABLE_NOTES = ["B0 is an apostrophe in the English-patched ROM (original: 、); B1 is drawn as a small full stop."]
CODE_BANKS = range(20, 32)

FONTS = [
    {"name": "font_small_8x16", "bank": 28, "offset": 0x55CA, "count": 250, "bpp": 2, "tiles_w": 1, "tiles_h": 2},
    {"name": "font_digicode_16x16", "bank": 28, "offset": 0x750A, "count": 0x56, "bpp": 2, "tiles_w": 2, "tiles_h": 2},
]

TEXT_BANKS = {n: {"base": None, "sources": list(CODE_BANKS)} for n in (22, 23, 24, 25, 28)}


def matches(header):
    return header["developer_id"] == 0x01 and header["game_id"] == 0x32
