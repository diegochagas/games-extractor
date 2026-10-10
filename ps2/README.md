# ps2 — PlayStation 2 games on CRI middleware (Dimps)

Written for **Saint Seiya: The Sanctuary** (聖闘士星矢 聖域十二宮編, Dimps / Bandai, 2005), from the
**Brazilian disc** (`SLPS_254.76` v1.02, NTSC): the one with the Portuguese dub by the classic cast and
every text in Portuguese. Everything runs on Linux with Python 3 (Pillow), `7z`, `ffmpeg` and Node +
`docx@8` for the book; the transcription of the voices uses faster-whisper in its own virtual
environment (`psp/transcribe.py`). The ISO is only read; every result goes to
`~/Downloads/Saint Seiya - The Sanctuary (PS2)/`.

```bash
sanctuary/extract.sh "GAME.iso"     # disc -> AFS, containers, pictures, text, scripts, sound, movies, voice transcription
sanctuary/build.sh                  # gallery folders + the three volumes of the story book (.odt)
```

## Formats (generic tools, this folder)

| Tool | Format |
|---|---|
| `afs.py` | CRI **AFS** archives: `AFS\0`, u32 count, (offset, size) per file, pointer to the name table (48-byte records: name[32], date as six u16, u32 size). The game's single `DATA/AFSDATA.AFS` holds 6,277 files; a few names appear twice (`name~1`). |
| `cmps.py` | **CMPS** compressed files: `CMPS`, u32 1, u32 unpacked size, u32 0, then Okumura's LZSS (flag byte, bit set = literal, bit clear = 12-bit ring position + 4-bit length, ring of 4096 starting at 0xFEE). A few streams end a byte or two short of the announced size. `pack` writes files the game can read. |
| `fjf.py` | **FJF** containers: `FJF\0`, u16 count, u16 flags, u32 offset per entry (plus the end of the last one in most files), u16 id per entry. Everything is in them: text tables, pictures (`.tpl`), animations (`.mpl`), effect and scene packs. Entries nest and may be CMPS-compressed. The `.jnt` files are FJF *index tables* whose offsets point into the companion `.gli`: they are left as they are. |
| `tim2.py` | Sony **TIM2** pictures; the game also writes the magic `TIM3` with the same layout. 4/8-bit indexed (CSM1 CLUT: blocks of 32 colours with the two middle groups of 8 swapped), 16, 24 and 32-bit; PS2 alpha (0x80 = opaque) scaled to 8 bits. `convert` walks a tree and opens the containers on the way. |
| `msg.py` | Text tables: a block is u16 count, u16 offset per string (16-bit units from the block start), UTF-16LE text where 0x0000 is a line break and 0x00FF ends the string. Controls: `0000 0001` line, `0000 0004`/`0006` page, `C8 0001 xx` button icon, `C9 0002 ..` speaker/face (Pope mode), `0016 0001` colour, `0013 0001 xx` column. FJF files hold one block per language (seven slots: the Japanese one carries Portuguese on this disc, then US/UK English, Italian, German, French, Spanish). The Brazilian text was written over the Japanese block without fixing the FJF offsets, so the Portuguese block is read from where it starts and the other languages only where the stale offsets still point at a sane block (several are overwritten). The Brazilian text uses hiragana code points for accented letters the font had no slot for (`ぇ` = á, `げ` = ã, `く` = q...): `ACCENTS` maps them back. |
| `media.py` | **ADX** sound and **Sofdec** movies (`.sfd` = MPEG-1 video + ADX audio), both decoded by ffmpeg to `.ogg` / `.mp4`. |
| `gmi.py` | **GMI** character models (`NN.gmi`, CMPS-compressed; `NNs.gmi` the simple model): header `19 03 04 20`, a bone table (112-byte bones: 4x4 row-major matrix relative to the parent, parent index, name) and 48-byte parts: vertex count, triangle count, flags, offsets of the positions (4 floats, the 4th a strip flag: 1 = the vertex kicks a triangle with the two before it, strips restart with two flag-0 vertices), normals (4 s16 / 4096), UVs (2 floats), skin bytes (palette index, second index or 255) and, for blended parts, two float weights; a 12-byte bone palette. A vertex bound to one bone is stored in that bone's local frame (the bind pose is rebuilt by chaining the matrices); a blended vertex is in model space. `glb` writes a binary glTF with the body and face textures (unlit, PS2 half alpha made opaque), Y up, facing the front. The stage backdrops (`*_far.gmi`, `*_sky.gmi`) are bone-less models in the same format. |
| `sebank.py` | **SE banks** (`SE_*.BIN`): FJF with a `seds` chunk (sound sequences, not decoded) and a `swdm` chunk: 32-byte sample records (offset, loop, volume, pitch in 1/256 semitone with 0xF0D9 = 20 kHz, Shift-JIS source name) and PlayStation ADPCM samples, written as `.wav`. |

## The game (`sanctuary/`)

- `names.py` – the 24 fighters in the order of the disc (files `NN.tpl`, `charstandNNa.tm2`, name plate
  `NN`, voice files `story_NN_*`), the `eNN` voice codes of the people who only speak in the scenes
  (Saori, Saga's Gemini voice, Cássius, the narrator, Shunrei), the chapter lists and title cards.
- `models.py` – exports every `NN.gmi` (the 24 fighters in both colours, 30-34 the heroes in plain
  clothes, 60-67 the other people of the scenes, plus the simple models) to `models/characters/*.glb`
  with `NN.tpl` / `NNa.tpl` and the first face of `NN_face.tpl`, and writes the render job list for
  `psp/render/render_all.py` (front, side, back, three-quarter; Blender 4.2).
- `scenes.py` – the cutscene scripts (`demoNN.bin`, `ifNN.bin`, `popeNN.bin`, `*d.bin` = the manga
  digests): `SC`, then commands `E1 <u16 id> <u16 layer>` + values (`C1`/`C4` int32, `C2` fraction,
  `C3` string, all big endian) + `EF`. Command 0 loads a scene file (`comic\main\NN\NN_p_q.bin`: the
  3D scene with its cameras, models and textures), 6 its length, 24 the music, 15 the text table, and
  after the page list a timeline per page: 21 plays a voice at second t, 17 shows text line N at
  second t, 37 closes the page. A voice is matched with the text lines shown while it plays.
- `organize.py` – the gallery: `Imagens` (character art, the renders of the 3D models, encyclopedia,
  cards, Die Cast toys, chapter titles, name plates per language, model and stage textures, scene
  textures, effects, interface per language), `Vídeos`, `Música` (`Músicas`, `Vozes/História` by scene
  with the speaker in the name, `Vozes/Batalha` by fighter, `Vozes/Modo Mestre`, `Vozes/Outras`,
  `Efeitos` = the sound banks), `Modelos 3D` (the `.glb` files). Identical duplicate voices are copied once.
- `story/transcript.py`, `story/review.py`, `story/fixes.json` – the story as text: every voice of every
  scene transcribed twice with faster-whisper (Portuguese; the second pass seeded with the names of the
  game through `psp/transcribe.py --prompt`), the speaker from the file name, the recogniser's slips
  fixed by a glossary, `review.py` listing the lines where the two passes disagree, and `fixes.json`
  holding the 170-odd lines corrected by hand after reading all 859 in context (the two scenes that
  exist as recorded videos — the trial of Aiolos, IF05/06, and the new temple with Shina, IF09/10 —
  were checked against the videos; shouts and inaudible lines are marked as such).
- `story/story_prep.py`, `story/build.js` – the book, three volumes (`.docx` in the work folder,
  delivered as `.odt` by the comic-skills `docx-odt-convert` skill): the game, the 24 fighters with
  encyclopedia card, moves and Die Cast toy, the 56 encyclopedia entries, the toy and card collections
  and the tutorial; the twelve-temple story scene by scene; the ten alternative scenes (with frames
  of the recorded videos), the Pope mode and its texts, movies, music, voices and every other text.

## What the disc holds

The story is told in real-time 3D cutscenes, not pictures: the scene files carry cameras, models and
textures, so the book illustrates each chapter with the title plate and the still the game itself uses
in the scene selection, and the two scenes recorded on video with frames of the videos. The character
models are decoded and rendered in the bind pose; the Gold Cloths come out grey because the game paints
the gold as a reflection effect at run time, which is not in the texture. The cutscene
text tables (`msgDM*`, `msgIF*`, `msgPope*`) are blank in the Brazilian disc: the story is dubbed and
not subtitled, so the dialogue comes from the voices. The movies `GX_JP.SFD` / `GX_US.SFD` are the
Japanese and international openings.

## Tests

`scripts/check` (repo root) compiles everything, lints what it can and runs `ps2/tests`
(`python3 -m unittest discover -s ps2/tests -t ps2`). The tests build tiny files in every format
(AFS, CMPS, FJF, TIM2/TIM3, text tables, SC scripts) in memory (`tests/fixtures.py`); no game data is
committed.

## Not done

- The stage geometry (`dNN.bin`, `kNN.bin`, `zNN.bin` with `03 02 05 20` chunks, their `.gli` material
  lists and `.jnt` index tables) is not decoded; only the far backdrop and sky models (`*_far.gmi`,
  `*_sky.gmi`) export through `gmi.py`, without textures. Animations (`.mpl`, `.cmb`, `.glc`) are not
  played: the renders are the bind pose. The reflection maps that make the Gold Cloths gold are not reproduced.
- The sound sequences of the banks (`seds` chunk: which sample plays when) are not decoded; every
  sample is extracted. Sample names are the 16-character Shift-JIS source names, some cut short.
- The transcription was proof-read by reading, with two recognition passes, not by listening: lines
  where both passes failed are marked "(grito)" or "(inaudível)", and a few names were chosen from context.
- `EBOOT`/`SLPS_254.76` tables (which voice of the collection is which file, card names) are not read.
