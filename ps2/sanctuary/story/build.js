// Saint Seiya: The Sanctuary (PS2, Brazilian disc) - story book (pt-BR).  node build.js story_book.json OUT_DIR
const fs = require('fs'), path = require('path');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, ImageRun, PageBreak, BorderStyle, Footer, PageNumber, AlignmentType, TableOfContents } = require('docx');
const D = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')); const OUTDIR = process.argv[3]; fs.mkdirSync(OUTDIR, { recursive: true });
const BOOK = 'Os Cavaleiros do Zodíaco: Saint Seiya - The Sanctuary';
const FONT = 'Calibri', JFONT = 'Noto Sans CJK JP', W = 9026;
const border = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' }, borders = { top: border, bottom: border, left: border, right: border };
const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, noBorders = { top: none, bottom: none, left: none, right: none };
const run = (t, o = {}) => new TextRun({ text: String(t == null ? '' : t), font: FONT, size: 21, ...o });
const jp = (t, o = {}) => new TextRun({ text: String(t == null ? '' : t), font: { name: JFONT, eastAsia: JFONT }, size: 15, color: '7F7F7F', ...o });
// «...» in the game text = words shown in colour -> bold
function marked(text, o = {}) { const out = []; String(text == null ? '' : text).split(/(«[^»]*»)/).forEach(p => { if (!p) return; if (p.startsWith('«')) out.push(run(p.slice(1, -1), { ...o, bold: true })); else out.push(run(p, o)); }); return out; }
const P = (t, o = {}) => new Paragraph({ spacing: { after: 100 }, ...o, children: (Array.isArray(t) ? t : [t]).flatMap(x => typeof x === 'string' ? marked(x, { size: o.size || 21, italics: o.italics, color: o.color }) : [x]) });
let HEADINGS = [];
const H1 = t => { HEADINGS.push([1, t]); return new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun({ text: t, font: FONT })] }); };
const H2 = t => { HEADINGS.push([2, t]); return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] }); };
const H3 = t => new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, children: [new TextRun({ text: t, font: FONT })] });
const PB = () => new Paragraph({ children: [new PageBreak()] });
const cap = t => P([run(t, { size: 17, color: '595959', italics: true })], { spacing: { after: 160 }, alignment: AlignmentType.CENTER });
function imgSize(file) { try { const b = fs.readFileSync(file); if (b.slice(1, 4).toString() === 'PNG') return [b.readUInt32BE(16), b.readUInt32BE(20)]; } catch (e) {} return [400, 300]; }
function picture(file, maxW, maxH) { const [w0, h0] = imgSize(file); const s = Math.min(maxW / w0, maxH / h0, 1.0); return new ImageRun({ type: 'png', data: fs.readFileSync(file), transformation: { width: Math.max(8, Math.round(w0 * s)), height: Math.max(8, Math.round(h0 * s)) } }); }
function IMG(file, maxW = 600, maxH = 420) { if (!file || !fs.existsSync(file)) return null; return new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 80, after: 40 }, children: [picture(file, maxW, maxH)] }); }
function imgRow(files, maxW = 150, maxH = 170) {
  const list = files.filter(f => f && (f.file || f) && fs.existsSync(f.file || f)); if (!list.length) return null;
  const cw = Math.floor(W / list.length);
  const cells = list.map(f => new TableCell({ borders: noBorders, width: { size: cw, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [picture(f.file || f, Math.min(maxW, cw / 15 - 6), maxH)] }), ...(f.label ? [P([run(f.label, { size: 15, color: '595959' })], { alignment: AlignmentType.CENTER, spacing: { after: 60 } })] : [])] }));
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: list.map(() => cw), rows: [new TableRow({ cantSplit: true, children: cells })] });
}
const chunk = (a, n) => { const r = []; for (let i = 0; i < a.length; i += n) r.push(a.slice(i, i + n)); return r; };
function grid(files, perRow, maxW, maxH) { const out = []; for (const g of chunk(files.filter(f => f && (f.file || f)), perRow)) { const r = imgRow(g, maxW, maxH); if (r) out.push(r); } return out; }
function table(cols, rows, { head = true, size = 17 } = {}) {
  const mk = (cells, isHead) => new TableRow({ tableHeader: isHead, cantSplit: true, children: cells.map((c, i) => new TableCell({ borders, width: { size: cols[i], type: WidthType.DXA }, shading: isHead ? { fill: 'DCE6F1', type: ShadingType.CLEAR, color: 'auto' } : undefined, margins: { top: 30, bottom: 30, left: 60, right: 60 }, children: String(c == null ? '' : c).split('\n').map(line => new Paragraph({ children: isHead ? [new TextRun({ text: line, font: FONT, size, bold: true })] : marked(line, { size }) })) })) });
  return new Table({ width: { size: cols.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: cols, rows: head ? [mk(rows[0], true), ...rows.slice(1).map(r => mk(r, false))] : rows.map(r => mk(r, false)) });
}
const SPEAKER_COLOURS = ['1F3864', '833C0B', '375623', '7030A0', '806000', '1F4E79', 'C00000', '3A3A3A'];
function dialogue(lines) {
  const out = []; const colour = {}; let next = 0;
  for (const l of lines) {
    const who = l.speaker || '—';
    if (!(who in colour)) colour[who] = SPEAKER_COLOURS[next++ % SPEAKER_COLOURS.length];
    const text = l.text || (l.source === 'missing' ? '(voz não transcrita)' : '(fala inaudível)');
    out.push(new Paragraph({ spacing: { after: 10 }, indent: { left: 360, hanging: 360 }, keepNext: true, children: [run(who + ': ', { bold: true, color: colour[who], size: 20 }), run(text, { size: 20, italics: !l.text })] }));
    out.push(new Paragraph({ spacing: { after: 90 }, indent: { left: 360 }, children: [run('♪ ' + l.voice + (l.source === 'fixed' ? '  · revisada' : ''), { size: 12, color: 'A6A6A6' })] }));
  }
  return out;
}
let c = []; const docs = [];
const VOLUMES = [['01', 'O jogo, os Cavaleiros e a coleção'], ['02', 'A história das Doze Casas'], ['03', 'As histórias alternativas, o Modo Mestre e o resto do disco']];
function startDoc(num) {
  const title = VOLUMES.find(v => v[0] === num)[1];
  c = []; HEADINGS = []; docs.push({ num, title, children: c, headings: HEADINGS });
  c.push(new Paragraph({ spacing: { before: 1200, after: 100 }, children: [run(BOOK, { size: 40, bold: true })] }));
  c.push(new Paragraph({ spacing: { after: 60 }, children: [jp('聖闘士星矢 聖域十二宮編 (PlayStation 2, 2005)', { size: 24, color: '595959' })] }));
  c.push(new Paragraph({ spacing: { after: 200 }, children: [run(`Volume ${num}: ${title}`, { size: 30, color: '1F3864', bold: true })] }));
  if (D.cover.logo) c.push(IMG(D.cover.logo, 420, 180));
  c.push(P([run('Tudo o que o disco brasileiro do jogo guarda, em português: as falas dubladas de cada cena, os textos do jogo, as imagens e os sons. O livro está dividido em volumes:', { size: 18, color: '595959' })]));
  for (const [n, t] of VOLUMES) c.push(P([run(`${n} - ${t}`, { size: 17, bold: n === num, color: n === num ? '1F3864' : '595959' })], { spacing: { after: 20 } }));
  c.push(PB());
  c.push(new Paragraph({ spacing: { after: 200 }, children: [run('Sumário', { size: 34, bold: true, color: '1F3864' })] }));
  c.push(new TableOfContents('Sumário', { hyperlink: true, headingStyleRange: '1-2' }));
  c.push({ __summary_placeholder: true });
}
const SUMMARIES = {};
function summaryBlock(doc) {
  const out = [PB(), P([run('Conteúdo deste volume', { bold: true, size: 24 })], { spacing: { before: 200, after: 80 } })];
  let sub = [];
  const flush = () => { if (sub.length) { out.push(P([run(sub.join(' · '), { size: 15, color: '595959' })], { spacing: { after: 60 }, indent: { left: 360 } })); sub = []; } };
  for (const [lvl, t] of doc.headings) {
    if (lvl === 1) { flush(); const s = SUMMARIES[t] || ''; out.push(P([run(t, { bold: true, size: 19 }), run(s ? ' — ' + s : '', { size: 18 })], { spacing: { before: 60, after: 20 } })); }
    else if (lvl === 2 && sub.length < 40) sub.push(t);
  }
  flush();
  return out;
}
const S = D.stats, F = D.facts;
const story = D.chapters.filter(ch => ch.kind === 'story'), ifs = D.chapters.filter(ch => ch.kind === 'if'), popes = D.chapters.filter(ch => ch.kind === 'pope'), others = D.chapters.filter(ch => ch.kind === 'other');

// =====================================================================  VOLUME 01
startDoc('01');
c.push(H1('Sobre este livro'));
SUMMARIES['Sobre este livro'] = 'o que é o jogo, de onde veio cada coisa deste livro e como ele está organizado.';
c.push(P(`Saint Seiya: The Sanctuary (聖闘士星矢 聖域十二宮編, "Saint Seiya: capítulo das Doze Casas do Santuário") é o jogo de luta de Os Cavaleiros do Zodíaco para PlayStation 2 feito pela Dimps e lançado pela Bandai em 2005. No Brasil ele saiu com dublagem em português feita pelo elenco clássico da série e com todos os textos traduzidos. Este livro foi montado a partir do disco brasileiro: as falas são a transcrição das vozes dubladas (o disco brasileiro não guarda legendas para as cenas: os arquivos de texto das cenas estão em branco), feita por reconhecimento de voz em duas passagens e revisada linha a linha; os demais textos são os do próprio jogo. Os modelos 3D dos personagens foram decodificados e renderizados a partir dos arquivos do disco.`));
c.push(P(`O livro reúne os ${S.fighters} lutadores com a ficha da enciclopédia do jogo e a lista de golpes, as ${S.encyclopedia} fichas de personagens, as coleções de bonecos Die Cast (${S.toys}) e de cards (${D.cards.length}), a história do modo História fala por fala (${S.lines} falas em ${S.scenes} cenas), as dez histórias alternativas, o Modo Mestre, os filmes e as músicas, e todos os outros textos do disco.`));
c.push(table([2600, W - 2600], [['Executável do disco', F.boot || ''], ['Versão', `${F.version || ''} (${F.vmode || ''})`], ['Arquivos no AFSDATA.AFS', String(F.afs_files)], ['Imagens extraídas', String(F.pictures)], ['Sons ADX', String(F.adx)], ['Linhas de texto em português', String(F.strings)]], { head: false }));
c.push(P(''));
c.push(P([run('Nomes. ', { bold: true }), run('Os nomes e termos são os que o próprio jogo usa em português (Shina, Máscara da Morte, Shô, Daichi e Ushô dos Cavaleiros de Aço, Mestre Ares, Armadura, Cosmo). Nas falas, o nome à frente de cada linha vem do arquivo de voz (cada arquivo traz o número do personagem que fala); o código com ♪ é o arquivo da voz, na pasta de vozes.')]));
c.push(P([run('Botões. ', { bold: true }), run('Nas listas de golpes, [□] é o ataque fraco, [△] o ataque forte, [○] o ataque especial (Cosmo) e [×] a defesa, como o tutorial do jogo os descreve.')]));
const covers = [D.cover.title ? { file: D.cover.title, label: 'Tela de título' } : null, D.cover.title_b ? { file: D.cover.title_b, label: 'Tela de título (2)' } : null, D.cover.title_c ? { file: D.cover.title_c, label: 'Tela de título (3)' } : null];
{ const r = imgRow(covers, 300, 240); if (r) c.push(r); }
c.push(H2('Menus e mensagens do jogo'));
for (const m of D.menus) { if (!m.rows.length) continue; c.push(H3(`${m.label} (${m.file})`)); c.push(table([700, W - 700], [['Nº', 'Texto'], ...m.rows.map(r => [String(r.id), r.pt])], { size: 16 })); }

c.push(H1('Os 24 lutadores'));
SUMMARIES['Os 24 lutadores'] = 'cada personagem jogável com a arte de seleção, a ficha da enciclopédia, os golpes e o boneco Die Cast.';
c.push(P('Os lutadores na ordem em que o disco os numera. A ficha é a da enciclopédia do Modo Coleção; a lista de golpes é a do menu de pausa do jogo. Os modelos 3D são os do próprio disco, na pose de repouso do esqueleto (braços abertos), vistos de frente, de lado, de costas e em três quartos, nas duas cores de cada lutador.'));
for (const k of D.fighters) {
  c.push(H2(`${k.number} · ${k.full}`));
  const head = [k.art ? { file: k.art, label: 'Arte de seleção' } : null, k.encyclopedia && k.encyclopedia.picture ? { file: k.encyclopedia.picture, label: 'Enciclopédia' } : null, k.toy && k.toy.picture ? { file: k.toy.picture, label: 'Boneco Die Cast' } : null];
  const r = imgRow(head, 220, 320); if (r) c.push(r);
  if (k.plate) { c.push(IMG(k.plate, 200, 60)); }
  for (const key of ['cor1', '_cor2']) {
    const rd = k.renders && k.renders[key]; if (!rd) continue;
    const row = imgRow([{ file: rd.views.front, label: 'Frente' }, { file: rd.views.side, label: 'Lado' }, { file: rd.views.back, label: 'Costas' }, { file: rd.views.three_quarter, label: 'Três quartos' }], 170, 330);
    if (row) { c.push(P([run(`Modelo 3D do jogo, ${rd.label.toLowerCase()}`, { bold: true, size: 18 })], { keepNext: true, spacing: { before: 100, after: 40 } })); c.push(row); }
  }
  if (k.model) c.push(P([run(`Modelo: ${k.model.triangles} triângulos, ${k.model.bones} ossos, ${k.model.parts} partes.`, { size: 16, color: '595959' })]));
  if (k.encyclopedia && k.encyclopedia.lines.length) c.push(P([run(k.encyclopedia.lines.join('  ·  '), { size: 18 })]));
  if (k.skills.length) c.push(table([3200, W - 3200], [['Golpe', 'Comando'], ...k.skills.map(s => [s.name, s.command])], { size: 16 }));
  if (k.toy && k.toy.text) c.push(P([run('Boneco Die Cast: ', { bold: true, size: 18 }), run(k.toy.text, { size: 18 })], { spacing: { before: 80 } }));
}
{ const r = imgRow(D.extra_art, 240, 330); if (r) { c.push(H2('Outros personagens com arte própria')); c.push(r); } }
if (D.extra_models && D.extra_models.length) { c.push(H2('Os outros modelos 3D do disco')); c.push(P('Modelos que só aparecem nas cenas (as pessoas do Santuário, Saori, o Mestre e os combatentes sem ficha), renderizados na pose de repouso.')); for (const g of grid(D.extra_models.filter(m => m.front).map(m => ({ file: m.front, label: `${m.file} (${m.triangles} triângulos)` })), 4, 150, 260)) c.push(g); }

if (D.stages && D.stages.length) {
  c.push(H1('Os cenários'));
  SUMMARIES['Os cenários'] = `os ${D.stages.length} cenários do disco, renderizados a partir dos modelos 3D.`;
  c.push(P('Os cenários das lutas, montados a partir das peças do disco: o chão em ladrilhos, os objetos colocados sobre ele (colunas, vasos, pedaços que quebram) e, na segunda imagem de cada um, o cenário distante ao redor. Casa por Casa, mais a Arena, as salas do Mestre e os lugares das cenas.'));
  for (const st of D.stages) {
    c.push(H2(`${st.name} (${st.id})`));
    const row = imgRow([st.aerial ? { file: st.aerial, label: 'Arena' } : null, st.completo ? { file: st.completo, label: 'Com o cenário distante' } : null], 300, 260); if (row) c.push(row);
    c.push(P([run(`${st.tiles} ladrilhos, ${st.objects} objetos, ${st.triangles} triângulos no chão.`, { size: 16, color: '595959' })]));
  }
}

c.push(H1('Enciclopédia: as fichas dos personagens'));
SUMMARIES['Enciclopédia: as fichas dos personagens'] = `as ${S.encyclopedia} fichas do Modo Coleção, com idade, altura, peso, aniversário, sangue, origem, treinamento e técnicas.`;
c.push(P('As fichas do Modo Coleção, na ordem do jogo. Os dados são os que o jogo mostra.'));
for (const g of chunk(D.encyclopedia, 2)) {
  const rows = [new TableRow({ cantSplit: true, children: g.map(e => new TableCell({ borders: noBorders, width: { size: W / 2, type: WidthType.DXA }, children: [...(e.picture ? [new Paragraph({ alignment: AlignmentType.CENTER, children: [picture(e.picture, 150, 230)] })] : []), P([run(`${e.number}. ${e.name}`, { bold: true, size: 19 })], { alignment: AlignmentType.CENTER, spacing: { after: 40 } }), ...e.lines.map(l => P([run(l, { size: 16 })], { alignment: AlignmentType.CENTER, spacing: { after: 10 } }))] })) })];
  c.push(new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: g.map(() => W / 2), rows }));
  c.push(P(''));
}

c.push(H1('Coleção de bonecos Die Cast'));
SUMMARIES['Coleção de bonecos Die Cast'] = `os ${S.toys} bonecos da linha Saint Cloth Series fotografados pelo jogo, com os textos da coleção.`;
c.push(P('As fotos e os textos do Modo Coleção sobre os bonecos originais da Bandai (anos 80 e 90), que o jogo desbloqueia aos poucos.'));
for (const t of D.toys) { c.push(H3(`${t.number}. ${t.name}`)); const r = imgRow([t.picture ? { file: t.picture } : null], 160, 240); if (r) c.push(r); if (t.text) c.push(P(t.text, { size: 18 })); }
c.push(H1('Coleção de cards'));
SUMMARIES['Coleção de cards'] = 'os cards colecionáveis dos anos 80 que o jogo reproduz.';
c.push(P('Os cards da coleção, com o texto que o jogo mostra ao lado de cada um.'));
for (const g of grid(D.cards.map(k => ({ file: k.picture, label: k.text.replace(/\n/g, ' · ') })), 4, 130, 190)) c.push(g);

c.push(H1('O tutorial'));
SUMMARIES['O tutorial'] = 'as explicações de Mu na Casa de Áries, linha por linha.';
c.push(P('As falas e instruções do tutorial, em que Mu de Áries ensina Seiya a lutar.'));
for (const t of D.tutorial) c.push(P(t, { size: 19 }));

// =====================================================================  VOLUME 02
function chapterBlock(ch, numbering) {
  c.push(H2(`${numbering}${ch.title}`));
  const pics = ch.pictures || {};
  const row = imgRow([pics.title ? { file: pics.title, label: ch.title_jp ? 'Título original: ' + ch.title_jp : 'Título original' } : null, pics.still ? { file: pics.still, label: 'Quadro da cena na seleção de capítulos' } : null], 300, 220); if (row) c.push(row);
  c.push(P([run(`Cena ${ch.id}: ${ch.pages} páginas`, { size: 15, color: '7F7F7F' }), ...(ch.bgm.length ? [run('  ·  música: ' + ch.bgm.join(', '), { size: 15, color: '7F7F7F' })] : [])], { spacing: { after: 60 } }));
  if (ch.video) { c.push(P([run(`Vídeo gravado desta cena: ${ch.video.file} (${ch.video.duration})`, { size: 16, italics: true, color: '404040' })])); for (const g of grid(ch.video.frames.map(f => ({ file: f })), 4, 150, 90)) c.push(g); }
  for (const d of dialogue(ch.lines)) c.push(d);
  if (ch.digest && ch.digest.length) { c.push(P([run('Resumo em mangá (a versão curta da cena no Modo Coleção):', { size: 16, italics: true, color: '404040' })], { spacing: { before: 120, after: 40 } })); for (const d of dialogue(ch.digest)) c.push(d); }
}
startDoc('02');
c.push(H1('A história das Doze Casas'));
SUMMARIES['A história das Doze Casas'] = 'o modo História completo: o prólogo, as doze Casas e o epílogo, fala por fala, com os quadros de cada capítulo.';
c.push(P('O modo História segue a saga das Doze Casas do Santuário: Seiya, Shiryu, Hyoga, Shun e Ikki sobem as doze Casas para salvar Saori, atingida pela flecha dourada. Cada capítulo tem uma cena antes da batalha e outra depois dela, exatamente como o Modo Coleção as lista. As falas são a dublagem brasileira; o disco não tem legendas para elas.'));
c.push(table([900, W - 900], [['Nº', 'Cena no Modo Coleção'], ...D.chapter_names.map((n, i) => [String(i), n])], { size: 16 }));
let lastChapter = '';
for (const ch of story) {
  if (ch.chapter !== lastChapter) { lastChapter = ch.chapter; }
  chapterBlock(ch, '');
  if (ch.part === 1) c.push(P([run('Batalha', { bold: true, size: 19, color: '833C0B' })], { alignment: AlignmentType.CENTER, border: { top: { style: BorderStyle.SINGLE, size: 6, color: 'C9A27A', space: 4 }, bottom: { style: BorderStyle.SINGLE, size: 6, color: 'C9A27A', space: 4 } }, spacing: { before: 160, after: 160 } }));
}

// =====================================================================  VOLUME 03
startDoc('03');
c.push(H1('As histórias alternativas'));
SUMMARIES['As histórias alternativas'] = 'as dez cenas "e se" do jogo: Mu contra Máscara da Morte, Ikki na Casa de Leão, a prova de Aiolos, Dohko e a Armadura de Libra, e a Casa que não existia, com Shina.';
c.push(P('Além da história principal, o jogo guarda cinco histórias criadas para ele, em duas cenas cada: Mu enfrentando Máscara da Morte, Ikki esperando na Casa de Leão, a Armadura de Sagitário que desce sobre Seiya e a sombra que o desafia (a "prova de Aiolos"), quem veste a Armadura de Libra, e uma décima terceira Casa que surge no caminho, onde Shina espera com uma Armadura de Ouro. Duas dessas cenas existem gravadas em vídeo na biblioteca (a prova de Aiolos, com a dublagem brasileira, e a nova Casa, da versão japonesa com legendas em inglês): seus quadros aparecem nos capítulos correspondentes.'));
for (const ch of ifs) { chapterBlock(ch, ''); if (ch.part === 1) c.push(P([run('Batalha', { bold: true, size: 19, color: '833C0B' })], { alignment: AlignmentType.CENTER, border: { top: { style: BorderStyle.SINGLE, size: 6, color: 'C9A27A', space: 4 }, bottom: { style: BorderStyle.SINGLE, size: 6, color: 'C9A27A', space: 4 } }, spacing: { before: 160, after: 160 } })); }

c.push(H1('O Modo Mestre'));
SUMMARIES['O Modo Mestre'] = 'o modo em que o jogador é o Mestre do Santuário: as três cenas dubladas e todo o texto do modo.';
c.push(P('No Modo Mestre (desbloqueado ao terminar a história) o jogador é o Mestre do Santuário, Ares, e escolhe quem defende cada Casa contra os Cavaleiros de Bronze. Abaixo, as três cenas dubladas do modo e, em seguida, os textos do modo (falas dos guardiões, Poderes Divinos e Dons de Guardião).'));
for (const g of grid(D.pope_pictures.map(f => ({ file: f })), 3, 190, 120)) c.push(g);
for (const ch of popes) chapterBlock(ch, '');
c.push(H2('Os textos do Modo Mestre'));
c.push(table([700, W - 700], [['Nº', 'Texto'], ...D.pope_text.map(t => [String(t.id), t.text])], { size: 15 }));

c.push(H1('Filmes'));
SUMMARIES['Filmes'] = 'as duas aberturas (japonesa e internacional) e o logotipo, com quadros de cada uma.';
c.push(P('Três filmes Sofdec no disco, convertidos para MP4 na pasta de vídeos: a abertura japonesa (com a música original), a abertura internacional e o logotipo da Atari. O disco brasileiro usa a abertura internacional.'));
for (const m of D.movies) { c.push(H2(`${m.title} (${m.name}.mp4, ${m.duration})`)); for (const g of grid(m.frames.filter(Boolean).map(f => ({ file: f })), 3, 190, 110)) c.push(g); }

c.push(H1('Músicas e vozes'));
SUMMARIES['Músicas e vozes'] = 'a lista das músicas com as cenas que as usam e o que há nas pastas de vozes.';
c.push(table([3400, 1100, W - 4500], [['Arquivo', 'Duração', 'Cenas que usam'], ...D.music.map(m => [m.file, m.duration, m.used])], { size: 16 }));
c.push(P(''));
c.push(P(`Efeitos sonoros: ${D.bank_samples} amostras em ${D.bank_count} bancos (pasta Música/Efeitos, um banco por cena e por lutador, com o nome original de cada amostra em japonês).`));
c.push(P(`Vozes: ${D.voices.story} vozes das cenas da história (pasta Vozes/História, uma pasta por cena, o nome de quem fala no nome do arquivo) e ${D.voices.all - D.voices.story} vozes e sons de batalha, dos menus e do Modo Mestre (Vozes/Batalha por lutador, Vozes/Modo Mestre, Vozes/Outras). A lista de vozes do Modo Coleção cobre estes personagens: ${D.voice_index.join(', ')}.`));
if (D.voices.without_scene.length) { c.push(H2('Vozes gravadas que nenhuma cena chama')); c.push(P('Arquivos de voz da história que nenhum roteiro usa:')); for (const d of dialogue(D.voices.without_scene.map(v => ({ speaker: v.speaker, text: v.text, voice: v.voice, source: 'whisper' })))) c.push(d); }

c.push(H1('Todos os outros textos do disco'));
SUMMARIES['Todos os outros textos do disco'] = 'as tabelas de texto que não apareceram antes, e a lista das tabelas de legendas que o disco brasileiro deixou em branco.';
for (const t of D.others) { c.push(H2(t.file)); c.push(table([700, W - 700], [['Nº', 'Texto'], ...t.rows.map(r => [String(r.id), r.pt])], { size: 15 })); }
c.push(H2('Tabelas de legendas em branco'));
c.push(P(`As legendas das cenas (${D.blank_tables.length} tabelas: ${D.blank_tables.join(', ')}) só têm espaços no disco brasileiro: a versão brasileira conta a história apenas pelas vozes dubladas. Por isso as falas deste livro vêm da transcrição das vozes.`));
if (others.length) { c.push(H2('Roteiros fora da história')); for (const ch of others) { c.push(H3(ch.id)); for (const d of dialogue(ch.lines)) c.push(d); } }

// =====================================================================  write
(async () => {
  for (const d of docs) {
    const kids = []; for (const x of d.children) { if (x && x.__summary_placeholder) kids.push(...summaryBlock(d)); else if (x) kids.push(x); }
    const doc = new Document({
      creator: 'games-extractor', title: `${BOOK} - ${d.num} - ${d.title}`,
      styles: { default: { document: { run: { font: FONT, size: 21 } } }, paragraphStyles: [
        { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 36, bold: true, color: '1F3864', font: FONT }, paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
        { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 28, bold: true, color: '2E74B5', font: FONT }, paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 1 } },
        { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 23, bold: true, color: '404040', font: FONT }, paragraph: { spacing: { before: 200, after: 60 }, outlineLevel: 2 } }] },
      features: { updateFields: true },
      sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } },
        footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run(`Saint Seiya - The Sanctuary · volume ${d.num} · `, { size: 15, color: '7F7F7F' }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 15, color: '7F7F7F' })] })] }) },
        children: kids }] });
    const file = path.join(OUTDIR, `Saint Seiya - The Sanctuary - ${d.num} - ${d.title}.docx`);
    fs.writeFileSync(file, await Packer.toBuffer(doc));
    console.log(file, (fs.statSync(file).size / 1048576).toFixed(1) + ' MB', d.headings.length + ' headings');
  }
})();
