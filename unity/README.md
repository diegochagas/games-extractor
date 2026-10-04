# unity — Saint Seiya Rebirth (圣斗士星矢：重生) extractor

Written for the Chinese mobile game by DeNA China / Shanghai Wapu (Unity 2022.3.62f3, IL2CPP), the one
that got the *Legend of Asgard* arc in October 2026. There is no PC client: the "PC versions" are
Android emulators, and everything here works from the Android APK plus the game's public resource
CDN, on Linux with Python 3 (`pip install UnityPy` in a venv; Pillow and numpy come with it).

## Where the files are

* **APK** (2.0 GB, the MuMu build of 2026-09-09 = game 8.4.0): `assets/GameRes/` holds 2,590 of the
  2,843 asset bundles listed in `GameRes.manifest.abws` (effects, UI, textures, scenes, audio, the
  game tables). The IL2CPP binary is `lib/<abi>/libil2cpp.so` + `assets/bin/Data/Managed/Metadata/global-metadata.dat`.
* **CDN**: the 254 `role/*` bundles (every character), the icon / card-art textures and the newest
  tables are downloaded by the game after login. The launcher asks
  `http://sdscenter.5xgames.cn/index.php/p321/server/pid/321/gid/33/o_system/android`, whose JSON has
  `android_res_url` (`https://sds-360-cdn.5xgames.cn/sds/`) and `res_version`
  (`8.3.0|base26090301_8.4.0|base26092402`: app version → resource tag). A bundle lives at
  `{android_res_url}{tag}/GameRes/{name}.abws`, its hash file next to it as `{name}.manifest.abws`.
  No login, no real-name check: `cdn.py` reads it directly.

## Formats

* `*.abws` = 256-byte header (magic `AA 55 01 00`, bundle name, zero padding) + plain `UnityFS`.
  `*.fassets.manifest.abws` is the Unity per-bundle manifest text (CRC, hashes) behind the same header.
* `config/config.fassets` holds 1,035 game tables as TextAssets: TSV with three header rows (types,
  Chinese names, English keys). `config/languagepackage.fassets` is the UI string table (key=value).
* Characters (`role/<model>.fassets`) are **2D puppets**: a prefab whose GameObjects carry the idle
  pose in their Transforms and whose SpriteRenderers (plus `SpriteDeformerBlendShape` meshes for the
  face and skirt) point at the parts of one or more atlases. Most atlases are ETC_RGB4 / ETC2_RGB
  without alpha: the mask is either the other half of the same texture (`_alphaTexUVOffset` 0.5 in U
  = right half, 0.5 in V = top half) or a second texture named by the material's `_alphaTex`
  (`Siegfried_alp`, `Thor01-alp`, `2002_1`, sometimes smaller); a few bundles mix both with plain
  RGBA textures. `sprites.py` decides per sprite from its renderer's material and rebuilds the RGBA
  parts. Animations are non-legacy muscle clips (not played back here).
* `RoleConfig` maps a character id to its Chinese name, constellation (`nameDesc`, `xzName`) and
  `modelResName` (the role bundle); `BattleRoleConfig.Types[5]` is the cloth / faction type.

## Pipeline

```bash
python3 abws.py extract GAME.apk DUMP/apk                      # plain UnityFS files, same tree
python3 cdn.py server                                           # CDN root + current tag
python3 cdn.py sync DUMP/cdn DUMP/apk/GameRes.manifest --only role/   # the character bundles (+ icons: texture/)
venv/bin/python dump.py DUMP/apk DUMP/assets --workers 6        # textures, sprites, texts, audio, meshes + objects.json
venv/bin/python dump.py DUMP/cdn DUMP/assets                    # same tree, CDN bundles
python3 tables.py DUMP/assets/config/config.fassets DUMP/tables # every table as JSON (+ _columns.json)
venv/bin/python puppet.py --all DUMP/cdn/role DUMP/puppets      # one PNG per character, idle pose
venv/bin/python roles.py DUMP "GALLERY DIR"                     # characters by faction with icons, cards, CG + index
python3 story/story_dump.py DUMP && python3 story/translate.py run DUMP   # story.json + pt-BR cache (Ollama)
python3 story/story_prep.py DUMP WORK && node story/build.js WORK/story_book.json WORK/docx   # the book
build.sh                                                        # everything above, incrementally
```

`abws.py list|extract|manifest|strip`, `cdn.py server|probe|fetch|sync`, `dump.py` (`--only PREFIX`,
`--types`), `puppet.py BUNDLE OUT.png [--parts DIR] [--json OUT.json]` (or `--all DIR OUT`) and
`tables.py` are also usable one file at a time; every tool prints its usage without arguments.

## Story book and the update loop

`story/story_dump.py DUMP` reads the tables into `text/story.json`: the 32 campaign chapters
(ChapterConfig style PT), their stages in `nextId` order (LevelConfig type 1), and the scripted
dialogues (`GameStoryConfig` → `GameStoryItemConfig` `ShowChat` items: text, speaker id, side).
Chapters 1–14 retell Sanctuary, Poseidon and Hades, 19–20 the Asgard anime, 23–24 Eris, 25–26 Abel,
27–28 Legend of Sanctuary, 31–32 a second Asgard; 15–18 and 21–22 are the game's own "nightmare
dimension" and only have stage blurbs. `story/translate.py run DUMP` translates every Chinese
string with the local Ollama model (`qwen3-instruct-32k`, 20–40 strings per request, glossary of
names and techniques in `story/glossary.json`) into `text/translation/pt-BR.json`, cached by the
text itself, so a rerun only translates new lines. `story/story_prep.py` + `story/build.js` make one
.docx per volume (speakers' puppets, chapter art, pt-BR with the Chinese in grey) and
`docx-odt-convert` turns them into .odt.

`check_update.sh` asks the CDN whether `config/config.fassets` changed since the last run (exit 0 and
"UPDATED", or "NO CHANGE"); a Claude Desktop scheduled task runs it every morning and launches
`build.sh` when it says UPDATED. `build.sh` chains all of it and is idempotent: `build.sh` (full), `build.sh --cdn` (just fetch what
the CDN changed: config, characters named in the new `RoleConfig`, icons) or
`build.sh --story-only`. When the game updates (new `res_version` tag on the server list), run
`build.sh`: it downloads the new config and role bundles, re-dumps only those, renders the new
characters, rebuilds the gallery and translates only the new lines.

## Not done

Animation clips (muscle clips) are not evaluated: the renders are the stored idle pose only.
Skill effects (`effect/`, particle systems) and UI prefabs (`modulesview/`) are dumped as their
textures and meshes, not re-assembled. The hot-updated C# patches (`initres/*gamebytes`) are not
decoded. `GameRes.manifest` is only shipped in the APK, so bundles added on the CDN after this APK
are found through the tables (`RoleConfig.modelResName`), not through a listing.
