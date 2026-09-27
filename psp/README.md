# psp — PSP games built on CRI and Sony middleware

Written for **Saint Seiya Omega Ultimate Cosmo** (聖闘士星矢Ω アルティメットコスモ, Namco Bandai, 2012,
program name "AppNewGalaxy"). Everything runs on Linux with Python 3 (Pillow, numpy), `7z`, `ffmpeg`,
Blender 4.2 LTS for the renders and Node + `docx@8` for the book. The ISO is only read; every result
goes to `~/Downloads/Saint Seiya Omega Ultimate Cosmo/`.

```bash
omega/extract.sh "GAME.iso"        # disc -> files, pictures, text, models, renders, audio, video
omega/build.sh                     # gallery folders + the story book (.odt) out of the dump
omega/translated.sh "GAME.iso"     # the Portuguese disc image (needs the dump and its translation)
```

## Formats (generic tools, this folder)

| Tool | Format |
|---|---|
| `cpk.py` | CRI **CPK** archives (CPKMC2): `CPK ` header and `TOC ` as `@UTF` tables (big endian, typed columns with zero / constant / per-row storage), file offsets relative to the TOC, **CRILAYLA** compression (LZ stream read backwards from the end, 13-bit distance, lengths in 2/3/5/8-bit steps, first 0x100 bytes stored raw after the stream). Encrypted `@UTF` tables are not handled. |
| `pac.py` | **PAC** containers of the game: `u16 count, u16 flags, u32 total`, then 40-byte entries `name[32], u32 offset, u32 size`. They nest (a character pack holds NORMAL.PAC, APPENDAGE_NORMAL.PAC...). The total counts the 8 header bytes in some files and not in others. |
| `gim.py` | Sony **GIM** pictures (`MIG.00.1PSP`): chunks walked by their `next` offset (root 2, picture 3, image 4, palette 5), formats RGBA5650/5551/4444/8888, 4/8/16/32-bit indexed, DXT1/3/5, plain or swizzled (16×8-byte blocks; a swizzled row is always a multiple of 16 bytes, whatever the width). |
| `btx.py` | **BTX** string tables: `BTX `, version, header size; `u32 1, u32 count`, then `(u32 id, u32 offset)` pairs, the offset counted from the pair itself; UTF-16LE strings. Ruby is written `<漢字:よみ>`, colour `<c#rrggbbaa>…<c>`. |
| `gmo.py` | Sony **GMO** models (`OMG.00.1PSP`): chunk tree (File 2, Model 3, Bone 4, Part 5, Mesh 6, Arrays 7, Material 8, Layer 9, Texture 10, Motion 11, FCurve 12 and the 0x80xx commands). Vertex arrays follow the GE vertex type bits (weights, uv, colour, normal, position, each aligned to its size); 8/16-bit positions and uvs are de-quantised with the model's two `VertexOffset` (0x8015) commands: `position = raw / 32768 * scale + offset`, `uv = unsigned raw / 32768 * scale + offset`. `DrawArrays` (0x8066) = arrays, primitive (3 triangles, 4 strip, 5 fan), vertices per primitive, primitive count, 16-bit indices. Skinning: the bone that draws a part lists `BlendBones` + `BlendOffsets` (inverse bind matrices), each mesh picks up to 8 of them with `BlendSubset`. FCurves are keyed in 16-bit floats (`format & 0x80`), `frame, value × dims`; interpolation in the low bits (0 step, 1 linear, 4 spherical). |
| `gmo2glb.py` | GMO (+ textures, + motions, + attachments) → binary **glTF 2.0**: nodes for the bones, one skin per file, unlit materials with the PNG textures inside, one animation per motion, 1 unit = 1 cm scaled to metres at the root. |
| `media.py` | **ADX** (ffmpeg); **AHX** = MPEG-2 Layer II with short frames: each frame is padded to the size its MPEG header announces and decoded as MP2 at the sample rate of the AHX header; **PMF/PSMF** movies: H.264 copied, ATRAC3plus audio pulled out of private stream 1 (4-byte sub-header, then `0x0FD0` frames with an 8-byte header), wrapped in an OMA (`EA3`) header and encoded to AAC; **PHD/PBD** sound banks (`PPHD8`, sample table in `PPVA`, samples in PlayStation ADPCM). |
| `render/blender_render.py`, `render/render_all.py` | Orthographic renders of `.glb` models (front, side, back, three-quarter, top) with a transparent background, in the bind pose or in a frame of an animation; `cull` makes faces seen from behind transparent so that sky domes do not hide a stage. |

| `fnt.py` | **FNT** glyph caches of the game: the font only holds the characters the game's own text uses (1,215 glyphs, 64-byte entries with the fields of a sceFont glyph description, pages of 128 × 128 pixels at 4 bits, 64 cells of 16 × 16). `render` draws glyphs with a TrueType font, `build` writes the file. |
| `psmf.py` | **PSMF** movies: packs of 2048 bytes, groups of pictures that start in a pack with the system header and a private stream 2 packet describing the group (packs where its first four pictures end, number and size of its pictures), time stamps on the first picture of a group and on every 16th after it. `replace_video` puts a new H.264 stream in the packs of the old one: same size, same clock references, sound untouched. |
| `iso.py` | ISO 9660: lists the files and replaces one in place, or at the end of the image when it grew (directory record and volume size updated, every other file keeps its sector). |
| `transcribe.py`, `subtitles.py` | Speech of a movie to timed segments with faster-whisper (in its own virtual environment), and segments + translation to `.srt` or to a text track of an MP4. |
| `emu/ppsspp_run.py` | Scripted runs of PPSSPP (Flatpak) inside a nested X server (Xephyr): waits, key presses, screenshots. The desktop keeps its keyboard and focus. |

Writers: `btx.write` (new strings in a table), `pac.build` (a container with some files replaced,
nested ones too), `gim.encode` (a picture in the format of an existing file), `cpk.crilayla_pack`
and `cpk.patch` (files replaced inside the archive: in their slot when they fit, at the end when
they do not; **a file the archive stores without compression must stay uncompressed**, the game
reads some of them in place: compressing `scene/adv/adv.pac` leaves the story on an empty screen).

## The game (`omega/`)

- `names.py` – character codes (`kog`, `yun`, `ryo`… ; `v2` = with Triton's Scale) and the character
  numbers of the scripts (0-23 playable, 24 Athena, 25 "???", 26 "man").
- `story_dump.py` – `event/script/NN_MM.pac` = `NN_MM.E` (stack-machine bytecode) + `NN_MM_JP.BTX`.
  A dialogue line is `03 <line id> 87 01 <character> 87 83 00000000 8E`; the string table after `ACT1`
  holds the title and the files the scene loads. The voice of line `N` of chapter `CC` is
  `event/sound/CC/<N / 100000>_<N % 100000>_<code>.ahx`. Chapters 50-56 are the seven stories (scenes
  01-08 before each battle, 11-18 after it); 00-23 are empty templates, one set per character.
- `models.py` – exports every model: characters (NORMAL/BROKEN model × NORMAL/HALF/BROKEN textures ×
  two colours, with the capes, hair, wings and weapons of the APPENDAGE packs hung from the locators
  of `NORMAL.ATP`/`BROKEN.ATP`: 44-byte entries `9 floats (position, rotation, scale), u32 bone,
  u32 locator`), stages, breakable objects, backgrounds; writes the render job list.
- `translate.py`, `docs/TRANSLATE_INSTRUCTIONS.md`, `docs/glossary.json` – JP → pt-BR workflow:
  `export` splits the text into chunks, agents (or a person) translate each chunk following the
  instructions, `check` finds missing keys / leftover markup / leftover Japanese, `merge` joins them.
- `organize.py` – the gallery: `Imagens` (pictures only), `Vídeos`, `Música`, `Modelos 3D`.
- `story/story_prep.py`, `story/build.js` – the story book, four volumes (`.docx` in the work
  folder, delivered as `.odt` by the comic-skills `docx-odt-convert` skill).

## The Portuguese image (`omega/patch.py`, `pictures.py`, `movie.py`, `translated.sh`)

- Text: every BTX table is written again with the translation. Line breaks are `\r\n`. The
  dialogue window holds 3 lines of 420 pixels; the windows of the system messages break the lines
  by themselves (their text goes in unbroken); the help at the foot of the menus is one line. The
  room of the other tables is measured on their Japanese text, and `text/translation/short.json`
  (in the dump) holds shorter wordings for what does not fit. `--report` lists what is left over.
- Font: the glyphs of the characters the new text uses are drawn with DejaVu Sans (13 pixels) and
  take the place of Japanese glyphs that are no longer used; the font keeps its 1,215 glyphs.
- Pictures that are only words (speaker names, menu entries, screen titles, stage names, some
  strips of button hints) are drawn again with the colours measured on the original. The speaker
  names get 64 × 16 pixels (the game draws them at the size of the picture). Pictures that mix
  artwork and words are left alone.
- Movies: only the groups of pictures that show a subtitle are encoded again (libx264, Main
  profile, level 2.1, one reference, no B pictures), each one to the size of the group it replaces.
  Songs are not subtitled.
- The image: `install.cpk` and `archive.cpk` grow and go to the end of the image; the movies keep
  their size and their place.

Checked in PPSSPP 1.20.4: boot, system windows, main menu, story selection, the prologue with
subtitles, dialogue with speaker names, a whole battle and its result screen, the character
profile. Not checked: stages 2 to 8, the other six stories, the two final movies inside the game
(their files decode and are consistent), network play, a real PSP.

## Tests

`scripts/check` (repo root) compiles everything, lints what it can and runs `psp/tests`
(`python3 -m unittest discover -s psp/tests -t psp`). The tests build tiny files in every format
in memory (`tests/fixtures.py`); no game data is committed.

## Not done

- Still in Japanese in the Portuguese image: the small buttons of the story selection, the stage
  names of the stage selection, the hint strips of the gallery, configuration and key screens,
  the install screen, the name entry keyboard (the console's own), the title logo.
- `EBOOT.BIN` is the encrypted executable (`~PSP`): not decrypted, so tables that live in the code
  (which title of the CG collection belongs to which picture, battle order of the Arcade mode) are
  not read. `INSTALL.DNS` is the PGD-protected copy of `install.cpk`, which the disc also has in clear.
- `.CSB` (2D effect and interface animations, `SCDH`/`PSPH18.1`), `.DAT` (hit boxes, movement and
  camera data), `.LIP` (lip movement), `.CMD`/`.CIN` (move commands) stay as raw files in `files/`.
- Texture animation (`TexCrop` curves: blinking eyes, mouths) and material render states are ignored
  by the exporter; the 64 `TexCrop` tracks of the game are skipped.
- The sound banks are exported sample by sample; the programs and tones (`PPPG`, `PPTN`) and the
  `.MID` sequences that play them are not interpreted.
