# Translating Digimon WonderSwan game text (Japanese -> English)

You get one chunk file: a JSON list of `{"k": "<key>", "jp": "<text>"}` extracted from the ROM of a
Bandai Digimon game for WonderSwan (D-1 Tamers, Tag Tamers or Brave Tamer; Ryo Akiyama saga).
Write the translations to a new file next to it, same name with `.en.json` instead of `.json`
(e.g. `chunk_03.json` -> `chunk_03.en.json`), as ONE JSON object `{"<key>": "<english>", ...}`
containing EVERY key of the chunk. Translate everything yourself; do not call web tools and do not
write scripts that "translate" - the translation must be your own reading of each string.

## About the source text
- Written almost entirely in kana with spaces between words; katakana is used for nouns/emphasis.
  Read it phonetically and work out the words (e.g. `シンカ` = evolve/Digivolve, `ワザ` = move/technique,
  `テキ` = enemy, `ミカタ` = ally, `コウゲキ` = attack, `かいふく` = recovery/heal).
- A literal `\n` in the JSON string is a line break inside the text box.
- `<FA><FA><FA><FA><FA>` is the player-name placeholder. `<FC>1 ... <FC>0` switches text colour
  (highlight on/off). Any `<XX>` token is a control byte: copy every token unchanged into the matching
  place of the English text.
- **Speaker-ID prefix:** many dialogue strings begin with ONE stray character (a kana, digit or letter)
  that is really a speaker/portrait ID byte, not text: `けこれは ディーアーク！`, `5ふーん そんなに…`,
  `9オモイダシタカ…`, `ぬここで デジモンを…`, `だむ！ …`. When the first character clearly does not belong
  to the sentence, keep it UNCHANGED as the first character of your translation (`けThis is a D-Ark!`).
  When the string is ordinary text (menu entry, name, description), add nothing.
- Some strings are tails of longer sentences (several pointers share an ending), e.g. `っぱいした。`.
  Translate them as the matching tail fragment as best you can.
- Strings that are clearly not language (random kana/digit soup from data tables): translate as `[junk]`.

## Style
- Natural, concise game English. Same number of lines as the source whenever possible, never more
  lines than the source has, and try to keep each line within about 24 characters for dialogue and
  the source line length +30% for menus/descriptions. Shorten wording rather than overflow.
- **Names policy: ORIGINAL JAPANESE NAMES** for every character - humans (family name first: Yagami Taichi,
  Ichijouji Ken, Akiyama Ryo; Taichi, Yamato, Koushiro, Jou, Takeru, Hikari, Daisuke, Miyako, Iori, Wallace,
  Ruki, Lee, Digimon Kaiser) and Digimon in Bandai's Japanese romanisation (V-mon, Tailmon, Vamdemon, Piemon,
  Mugendramon, Omegamon, Dukemon, Millenniumon ...). `docs/glossary.json` converts any dub name afterwards.
  Group terms also stay Japanese: シセイジュウ = Holy Beasts (not Sovereigns), ジョグレス = Jogress, デジメンタル = Digimental,
  十二神将 = Devas.
- Other terms: (the dub-style examples below are superseded by the names policy) (ブイモン Veemon,
  ワームモン Wormmon, アグモン Agumon, エクスブイモン ExVeemon, ミレニアモン Millenniummon,
  モノドラモン Monodramon, サイバードラモン Cyberdramon ...), リョウ Ryo, ケン / いちじょうじ ケン Ken Ichijouji,
  テイマー Tamer, デジタマ Digi-Egg, シンカ Digivolve, ワザ move, ディーアーク D-Ark, D-3, デジメンタル Digi-Egg
  (armor item) -> "Digimental", BIT (currency), ワクチン/データ/ウイルス Vaccine/Data/Virus,
  デジタルワールド Digital World.
- Speech written fully in katakana (robotic / monstrous voice) -> ALL CAPS English.
- The in-game font only has ASCII: use only `A-Z a-z 0-9` space and `! ? . , ' - : ; / ( ) % & + * = < > ~`.
  `…` becomes `...`, `「」『』` become `"` -> use `'` instead (no double quote glyph), `ー` long vowels are dropped.

## Finish
After writing the file, read it back (or load it with `python3 -c "import json;json.load(open(...))"`)
to make sure it is valid JSON and has the same number of keys as the chunk. Reply with one line:
number of strings translated and how many you marked `[junk]`.
