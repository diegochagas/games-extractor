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

## Testing a build locally

`testrom.py` drives the same libretro core the RomM web player uses (Beetle/Mednafen WonderSwan),
headless, and saves screenshots, so a build can be verified without an emulator GUI:

```bash
python3 testrom.py ROM --core /path/to/mednafen_wswan_libretro.so \
    --script "240,300:start,150:a,120:a" --out shots
```

Get the core with `apt-get download libretro-beetle-wswan` and unpack it with `dpkg-deb -x`.

**Text box size (measured with a ruler string in the emulator): the portrait dialogue box holds
exactly 20 characters x 2 lines.** Writing past that overwrites tile RAM: the background turns into
rows of garbage and the game hangs. `fit.py` derives each string's box from the Japanese text and
`build.py` never writes anything wider or taller; strings that cannot be re-wrapped are condensed by
hand (see `docs/FIT_INSTRUCTIONS.md`, `translation/fit/`) and checked by `check_fit.py`.

## Story books and picture library (tools/)

The books are delivered as LibreOffice `.odt` (converted by the `docx-odt-convert` skill of comic-skills, which also fills in the table of contents with page numbers). The patch tools below work on `.docx`: convert with `soffice --headless --convert-to docx BOOK.odt`, patch, then convert back with that skill (`convert.py BOOK.docx --to odt`). Like every build here, they write their result to `~/Downloads/<book file name>` (`STORY_OUTPUT_DIR` replaces `~/Downloads`) so it can be checked before it replaces the book; `--in-place` patches the file itself.


- `tools/story/add_summaries.py BOOK.docx SUMMARIES.json` - adds a "Conteúdo deste livro" page (one line per chapter) after the table of contents of an existing .docx.
- `tools/story/add_content.py BOOK.docx SPEC.json [--before "Heading"]` - appends or inserts headings, paragraphs, dialogue lines, tables and image grids into an existing .docx without any library; SPEC may be a list of anchored insertions (`before` a heading, `after_para` a paragraph, `replace_para` to rewrite one). Used to add the text the first build had missed (per-string review reports live next to each dump as `text/story_review_<date>.json`).
- `tools/story/image_appendix.py BOOK.docx DUMP_DIR bank_labels_pt.json GAME_KEY OUT.json --before "Heading" --pictures "..."` - builds the "Apêndice: galeria de imagens do cartucho" spec (every dumped image the book does not show yet, bank by bank) for add_content.py.
- `tools/image_index/collect.py` + `build.js` - the "Image index" document (what every extracted image is); `tools/image_index/organize_pictures.py GAMES_DIR OUT_DIR bank_labels_pt.json` - copies every dumped image into a picture library organised like that index (one folder per game, `bankNN - <label>` sub-folders, original file names); `bank_labels_pt.json` holds the Portuguese label/description of each ROM bank of the four games.
