# wonderswan-romhack

Tools to reverse-engineer the Bandai Digimon games for WonderSwan / WonderSwan Color:
dump texts, fonts and graphics into editable files (and, later, put them back).

ROMs are never committed and never modified by the dumper.

## Usage

```bash
python3 dump.py path/to/game.wsc            # writes <rom folder>/<rom name>/
python3 dump.py path/to/game.wsc --out DIR
```

Requires Python 3 with `numpy` and `pillow`.

## Supported games

| Game | Graphics | Fonts + text |
|---|---|---|
| Digimon Adventure 02 - D-1 Tamers | yes | yes (JP, partly EN-patched dump) |
| Digimon Adventure 02 - Tag Tamers | yes | yes (fan-translated dump, some JP leftovers) |
| Digimon Anode Tamer - Veedramon Version | yes | yes (official English, shifted ASCII) |
| Digimon Tamers - Brave Tamer | yes | yes (JP) |

## Building a patched ROM

```bash
python3 build.py path/to/game.wsc      # -> <dump>/patched/<name> [EN].wsc + .ips + build_report.txt
```

The original ROM is only read. English text is written in place when it fits; otherwise the
string moves to unused ROM space (tails of the always-mapped linear banks, plus the space freed
by other moved strings) and every far pointer to it is updated, then read back as a check.
Strings referenced from code (no relocatable pointer) use `docs/short_forms.json`; if nothing
fits, the original bytes stay. Graphics banks are never touched. The header checksum is fixed.

Text record facts the builder relies on: records are even aligned; names/descriptions start
with an `FF` header byte and pointers aim at that header; dialogue records start with a speaker
byte; some dialogue records start with one far pointer (linked entries) which is not text.

## Translation workflow (draft files only, the ROM is not touched)

```bash
python3 translate.py export DUMP      # unique Japanese strings -> DUMP/translation/chunks/chunk_NN.json
# translate each chunk into chunk_NN.en.json following docs/TRANSLATE_INSTRUCTIONS.md
python3 translate.py normalize DUMP   # apply docs/glossary.json: original Japanese names + shared terms
python3 translate.py rename DUMP      # English text already in the ROM: DUMP/text_en/bankNN_renamed.txt (ROM vs NEW)
python3 translate.py merge DUMP       # DUMP/text_en/bankNN.txt (JP/EN side by side) + translation/en.json
```

Add a game by creating `games/<name>.py` with the character table overrides and the font/text bank
locations (see `games/d1_tamers.py`), then list it in `dump.py`.

## Engine notes (found by disassembling D-1 Tamers, NEC V30MZ / 80186 code)

- Code lives in the last 12 banks (fixed linear window, segment `0x4000`+). Data banks are
  paged in at segment `0x3000`, so every pointer inside them is a normalized `offset:segment`
  far pointer with segment `0x3xxx`.
- A data bank starts with two far pointers (table start/end). The table lists 8-byte
  `{far ptr, 0}` records in triples: tiles, tilemap, palette. Object banks keep the table
  empty and list groups of `{tile frames}, {piece lists}, animation data` after it.
- Tiles: `u16 LE count` + raw 2bpp (16 B) or 4bpp planar (32 B) tiles, or
  `u16 BE count` + LZSS (flags LSB first, 1 = literal, match = 12-bit distance, 4-bit len-3).
- Tilemap: `u16 w, u16 h` + cells, or `u8 w, u8 h` + 2-bit codes
  (00 skip, 01 same tile, 10 tile+1, 11 literal BE u16). Cell bits: 0-8 tile, 14 h-flip, 15 v-flip.
- Palette: `u16 count` + 16 x `0x0RGB` per palette; mono: `00 00` + four 4-bit shade indexes.
- Sprite piece list: `u16 count` + `{u16 tile, s8 y, s8 x}`.
- Text: one byte per character, `FF` end, `FE` newline, `FD` space, `FA` placeholder.
  Glyphs are drawn into tile RAM from a 8x16 font (`857F:000E`) or a 16x16 DigiCode font
  (`8773:000E`); renderer at `AB0F:02F6`.
