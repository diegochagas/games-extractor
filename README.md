# games-extractor

Tools to extract, dump and rebuild the assets of games, one folder per engine or platform.
Game files (ROMs, clients, archives) are never committed and never modified; every tool writes a
read-only review dump elsewhere (by default `~/Downloads/<game name>/`).

| Folder | Covers | What it does |
|---|---|---|
| `wonderswan/` | Bandai Digimon games for WonderSwan / WonderSwan Color (shared engine) | Dumps fonts, texts and graphics of the ROM, drives the JP→EN translation workflow and builds patched ROMs (+ IPS). See `wonderswan/README.md`. |
| `psp/` | PSP games on CRI + Sony middleware (written for **Saint Seiya Omega Ultimate Cosmo**) | Unpacks the ISO, the CRI `.cpk` archives and the game's `.pac` containers, converts GIM pictures to PNG, GMO models to `.glb` (skeleton, skin, animations) and renders them with Blender, converts ADX/AHX/PMF/sound banks to `.ogg`/`.mp4`, dumps every text and the story scripts with their speakers, drives the JP→pt-BR translation and builds the gallery and the illustrated story book. See `psp/README.md`. |
| `angelica/` | Perfect World "Angelica" engine clients (built for **Saint Seiya Online**, the Seiya Reborn client) | Unpacks the `.pck` archives, converts every texture to PNG, dumps all in-game text (LANG files, quests, NPCs), builds an HTML/CSV image index, a Word image index and the Word story book, and renders every 3D character (front/side/back T pose) with Blender into a faction-organised gallery. See `angelica/README.md`. |

All were written with Claude Code; the WonderSwan part started as the `wonderswan-romhack` repo.

## Checks

`scripts/check` is the gate (syntax of every tool, shellcheck, unit tests of `psp/`); `.githooks/pre-push`
runs it before every push (`git config core.hooksPath .githooks`, once per clone).

## Builds

Every build writes to `~/Downloads` and nowhere else; the results are checked there and moved by hand. `angelica/build.sh DUMP_DIR [--story-only]` builds the Saint Seiya Online gallery and the 13 story volumes into `~/Downloads/Saint Seiya Online/` (`Imagens`, `Vídeos`, `Música`, `Documentos`; see the script header for the environment variables).
`psp/omega/extract.sh GAME.iso` followed by `psp/omega/build.sh` does the same for Saint Seiya Omega
Ultimate Cosmo, into `~/Downloads/Saint Seiya Omega Ultimate Cosmo/`, and `psp/omega/translated.sh GAME.iso`
writes its Portuguese disc image (text, font, word pictures and subtitled movies) into `patch/` there.

## Document format

The books and image indexes are delivered as LibreOffice `.odt`: the generators write `.docx`, and the `docx-odt-convert` skill of the [comic-skills](https://github.com/diegochagas/comic-skills) repo converts them (`python3 docx-odt-convert/scripts/convert.py <folder> --to odt --output <dest>`), updating the table of contents so it shows page numbers.
