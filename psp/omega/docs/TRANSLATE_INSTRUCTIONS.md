# Translating Saint Seiya Omega Ultimate Cosmo (JP → pt-BR)

Input: one chunk `text/translation/in/<chunk>.json`, a list of
`{"key": "...", "speaker": "...", "jp": "..."}` in the order the game shows the lines
(`scene` rows mark where a new scene starts and carry its Japanese title).
Output: `text/translation/out/<chunk>.json`, one object `{"<key>": "<pt-BR text>", ...}` with
**every** key of the input, scene rows included (translate the scene title).

Rules

1. Brazilian Portuguese, natural spoken dialogue, faithful to the Japanese: no summarising, no
   added information, no omitted sentences. Keep the tone of each character (Kouga impulsive,
   Ryuho polite, Eden formal and cold, Haruto dry, Poseidon solemn and archaic...).
2. Names and terms come from `docs/glossary.json`, always. Names that are not in the glossary
   stay in their usual romanised form.
3. Ruby markup `<漢字:よみ>` is one word: translate it once, by its meaning in the glossary
   (`<小宇宙:コスモ>` → Cosmo, `<聖衣:クロス>` → Armadura). No markup is left in the output.
4. Colour tags `<c#rrggbbaa>` … `<c>` and button names (P, K, S, L, ↑ ↓ ← →) are kept exactly.
5. Line breaks (`\r\n`, `\n`) of the text box are dropped: write flowing sentences.
6. Technique names are not translated: katakana names go back to their original language
   (`オリオン・プラズマ` → Orion Plasma), kanji names are romanised by their reading
   (`ペガサス<閃光拳:せんこうけん>` → Pegasus Senkouken, `<蘆山大瀑布:ろざんだいばくふ>` → Rozan Daibakufu).
7. Ichi ends his sentences with 「ザンス」: keep the tic as "zansu" at the end of the sentence
   ("Finalmente alcancei vocês, zansu.").
8. `（不要台詞）` is a developer's note ("line not needed"): translate it as "(fala descartada)".
9. Ellipses, exclamation and question marks follow the original; `……` alone becomes "……".
10. Empty strings stay empty. Numbers and placeholders stay as they are.

Check the result with `python3 translate.py check DUMP` before finishing: it lists missing keys,
leftover markup and leftover Japanese.
