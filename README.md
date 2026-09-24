# games-extractor

Tools to extract, dump and rebuild the assets of games, one folder per engine or platform.
Game files (ROMs, clients, archives) are never committed and never modified; every tool writes a
read-only review dump elsewhere (by default `~/Downloads/<game name>/`).

| Folder | Covers | What it does |
|---|---|---|
| `wonderswan/` | Bandai Digimon games for WonderSwan / WonderSwan Color (shared engine) | Dumps fonts, texts and graphics of the ROM, drives the JP→EN translation workflow and builds patched ROMs (+ IPS). See `wonderswan/README.md`. |
| `angelica/` | Perfect World "Angelica" engine clients (built for **Saint Seiya Online**, the Seiya Reborn client) | Unpacks the `.pck` archives, converts every texture to PNG, dumps all in-game text (LANG files, quests, NPCs), builds an HTML/CSV image index, a Word image index and the Word story book. See `angelica/README.md`. |

Both were written with Claude Code; the WonderSwan part started as the `wonderswan-romhack` repo.
