# Condensing translations to their text boxes

The game's text boxes have a FIXED size (the Japanese script never exceeds it). English that is
wider or taller than the box overwrites video memory and freezes the game, so the limits below are
HARD limits, not style advice.

You get one file `fit_NN.json`: a list of
`{"k", "jp", "en", "width", "lines", "prefix"}` where `en` is the current English translation that
does NOT fit. Write `fit_NN.en.json` next to it: ONE JSON object `{"<k>": "<new english>", ...}`
with every key.

Rules for each new string
- Start with `prefix` exactly (a speaker-ID character that is not displayed; often empty). The
  prefix does not count towards the width.
- After the prefix: at most `lines` lines (separated by `\n`), each line at most `width` visible
  characters. `<FC>1` / `<FC>0` (colour on/off) count as 0 characters; any other `<XX>` token
  counts as 1. `<FA><FA><FA><FA><FA>` is the player name (5 cells).
- Keep exactly the control tokens that the Japanese has (same tokens, same count).
- Keep the meaning of the Japanese (`jp`), but be terse: drop filler, use short words, contractions,
  digits, "&"-less abbreviations common in games (HP, ATK, DEF, Lv, max, foe, ally, dmg). For
  dialogue keep the voice of the speaker. Sentences that continue in the next box may simply stop
  mid-sentence the way the Japanese does. Never pad, never add lines beyond `lines`.
- Names policy: original Japanese names (Taichi, Daisuke, Tailmon, Vamdemon, V-mon, Millenniumon,
  Digimon Kaiser, Holy Beasts, Jogress, Digimental ...). A long Digimon name may be shortened the way
  the game's own menus do (drop vowels near the end: `BWarGreymn`, `Mugendramn`) only when it
  cannot fit otherwise.
- ASCII only: `A-Z a-z 0-9` space and `! ? . , ' - : / ( ) % + = ~`. `...` is fine.
- ALL-CAPS speech (katakana robot/monster voice) stays ALL CAPS.

Mandatory check: run
`cd /home/diego/Projects/wonderswan-romhack && python3 check_fit.py "<fit_NN.json>" "<fit_NN.en.json>"`
and fix every line it reports until it prints `N/N OK`. Do not finish before it passes. Write the
translations yourself (you may use a small script only to assemble/validate the JSON). Do not
modify any other file. Reply with one line: how many strings, and the final check result.
