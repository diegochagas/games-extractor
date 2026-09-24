# angelica — Saint Seiya Online (Perfect World Angelica engine) extractor

Used on the Seiya Reborn client (`C:\Seiya\element`, build 290). Everything runs on Linux with
Python 3 (Pillow, numpy), ffprobe for the media index and Node + `npm install docx@8` for the Word
documents, and Blender 4.2 LTS for the 3D renders. The full dump these tools produced lives in `~/Downloads/Seiya/` (see its README.md).

## Archive format

`.pck` = Angelica File Package v2.0.2. Footer (last 0x118 bytes): `sig(4) ver(4) table_offset^KEY_1(4)
description(256) sig2(4) entry_count(4) ver(4)`. Entry table: `u32 len^KEY_1, u32 len^KEY_2,
zlib(name[260] offset size csize)`. Saint Seiya Online uses its own keys, `KEY_1 = 0x62A4F9E1`,
`KEY_2 = 0x3520C3D5` (found by matching zlib stream lengths in `configs.pck`); other Angelica games
(Perfect World, Jade Dynasty…) use different keys — `pck.py` is where to change them. `models.pck`
stops at 0x7FFFFF00 bytes and continues in `models.pkx`.

Text: `element/data/lang_<lang>.data` ("LANG" v1) holds every string of the game with its Chinese
source: `lang.py` dumps them to TSV + JSON. Read the JSON, not the TSV (strings contain line breaks).

## Pipeline (order used for the dump)

```bash
python3 pck.py list package/configs.pck                  # or extract FILE.pck OUTDIR
python3 lang.py OUT/text/lang data/lang_*.data
python3 convert_images.py OUT/packages OUT/images 11     # dds/tga/bmp/jpg -> png + manifest.jsonl
python3 fix_images.py OUT/packages OUT/images            # retries broken DDS headers / float textures
python3 thumbs.py OUT/images; python3 sheets.py OUT; python3 split_icons.py OUT
python3 catalog.py OUT                                   # manifest.csv, folders.json, images/index.html
python3 dump_text.py CLIENT/element OUT/packages OUT/text; python3 maps_table.py OUT; python3 media_index.py OUT
python3 docx_data.py OUT WORK && node docx_build.js OUT/"Image index.docx"   # Word image index
python3 quests_dump.py OUT pt-BR                         # text/quests_pt-BR.json (dialogue windows)
cd story && python3 story_prep.py WORK && python3 cache_images.py WORK && node build.js WORK/story_cached.json OUT/"Story"   # one .docx per volume
```

`story/story_config.py` holds the narrative structure (quest-id ranges per chapter, hand-written
pt-BR intros, region images); `labels.py` translates the Chinese folder names.

## 3D renders (`render/`)

The characters are Angelica skinned meshes; `render/` parses them and renders every character in
its bind pose (T pose) with Blender, front / side / back, transparent background:

- `ski.py` – `.ski` reader (MOXBIKSA v101: header counts, bone names, GBK texture names,
  `MATERIAL:` blocks, then per mesh 48-byte vertices `pos3f weights3f bones4B normal3f uv2f`,
  u16 indices, 16-byte tangents). Vertices are already in model space (bind pose), so the meshes of
  one character can be drawn together without the skeleton. `smd.py` reads the `.smd` descriptors
  (skeleton + list of `.ski` files).
- `inventory.py DUMP OUT.json` – builds the job list: one job per NPC `.smd` (deduplicated) and one
  per player cloth set (`players/圣衣/<sex>/<set><sex>.ski` + the eight `<set>圣衣<piece>_动画.ski`
  pieces + base head, pupils and class hair from `players/形象/<sex>`), with every texture resolved
  to the converted PNG next to the model.
- `blender_render.py` – runs inside Blender (`blender -b --python blender_render.py -- JOBS OUT`):
  builds the meshes (engine is left-handed Y-up, characters face +Z; Blender vertex = (-x, -z, y)),
  fixes the winding against the stored normals, one Principled material per texture with alpha
  cut-out, orthographic cameras, Cycles. `RENDER_DEVICE=GPU` uses OptiX/CUDA; denoising is off by
  default because OIDN reloads its kernels every frame in background mode (12 s per view).
- `render_all.py JOBS OUT --workers N` – runs several Blender processes over the job list, players
  first, skipping jobs that already have `job.json`.
- `names.py` – Chinese asset name → English file name / Portuguese caption (game text first, then a
  glossary of constellations, characters and common words, pinyin as last resort).
- `organize.py DUMP GALLERY [--concept-dir DIR]` – copies the renders plus the album cards,
  portraits, world maps, loading screens, videos (with a frame each), music, voice lines, official
  concept art and press images into a gallery with one Portuguese-named folder per faction or
  content type (the same sections as the story book's gallery volume) and writes `index.json` /
  `text/gallery_index.json`, which `story/story_prep.py` picks up.
- `../npc_models.py DUMP CLIENT/element/data` – links every NPC/monster id of the language files
  to its `.ecm` model (`path.data` id table + `elements.data` records) and to the render job, so the
  story book can show the real model of characters that use a generic NPC body.
- `../web/cavzodiaco.py OUT`, `../web/wanmei_wayback.py OUT` and `../web/deviantart_rss.py USER FOLDER OUT`
  – collect the CavZodiaco.com.br coverage (articles + images), the official site's galleries from the
  Wayback Machine and a DeviantArt gallery's metadata (Cerberus-rack's Saint Seiya Online drawings).
- `inventory.py` also picks up `.ski` meshes that no `.smd` references (variant models such as
  June's Surplice version, Dohko's god cloth) and the later "新职业_<name>_<sex>_<version>" class
  sets (Ellan of Tornado).

```bash
python3 render/inventory.py OUT OUT/text/render_jobs.json
RENDER_DEVICE=GPU python3 render/render_all.py OUT/text/render_jobs.json OUT/renders --blender /opt/blender/blender --workers 2
python3 render/organize.py OUT "GALLERY DIR"
```

## Not done

`.bon` skeletons and `.stck` animations are not applied (renders are the bind pose only);
`tasks.data*` (quest tree with NPC ids and prerequisites) and `elements.data` are only
string-scraped; `.anm` cutscenes are not played back.
