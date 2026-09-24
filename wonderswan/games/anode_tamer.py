"""Digimon Anode Tamer - Veedramon Version (English release for Asia, Bandai)."""
from .common import CONTROLS

NAME = "Digimon Anode Tamer - Veedramon Version"
# Text is ASCII minus 0x20 for space..Z, then a-z packed right after three unused codes.
TABLE = {i: chr(0x20 + i) for i in range(0x3B)}
TABLE.update({0x3E + i: chr(97 + i) for i in range(26)})
TABLE_NOTES = ["Shifted ASCII: 00-3A = ' '..'Z', 3E-57 = a-z. The renderer remaps these onto the kana-era font below."]
CODE_BANKS = range(52, 64)

# 1bpp glyphs stored as two consecutive plane blocks (250 glyphs each).
FONTS = [
    {"name": "font_small_8x16", "bank": 60, "offset": 0x5892, "count": 250, "bpp": 1, "planes": 2, "tiles_w": 1, "tiles_h": 2},
]

TEXT_BANKS = {n: {"base": None, "sources": list(CODE_BANKS)} for n in (54, 55, 59, 60)}


def matches(header):
    return header["developer_id"] == 0x01 and header["game_id"] == 0x01
