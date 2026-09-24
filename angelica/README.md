# angelica — Saint Seiya Online (Perfect World Angelica engine) extractor

Used on the Seiya Reborn client (`C:\Seiya\element`, build 290). Everything runs on Linux with
Python 3 (Pillow, numpy), ffprobe for the media index and Node + `npm install docx@8` for the Word
documents. The full dump these tools produced lives in `~/Downloads/Seiya/` (see its README.md).

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
cd story && python3 story_prep.py WORK && python3 cache_images.py WORK && node build.js WORK/story_cached.json OUT/"Story.docx"
```

`story/story_config.py` holds the narrative structure (quest-id ranges per chapter, hand-written
pt-BR intros, region images); `labels.py` translates the Chinese folder names.

## Not done

3D meshes (`.ski` skin meshes, `.bon` skeletons, `.smd`, `.ecm` model descriptions, `.stck`
animations) are extracted but not parsed or rendered; `tasks.data*` (quest tree with NPC ids and
prerequisites) and `elements.data` are only string-scraped; `.anm` cutscenes are not played back.
