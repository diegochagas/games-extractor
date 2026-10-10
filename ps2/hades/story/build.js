// Saint Seiya: The Hades (PS2, European disc) - story book (pt-BR).  node build.js story_book.json OUT_DIR
const fs = require('fs'), path = require('path');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, ImageRun, PageBreak, BorderStyle, Footer, PageNumber, AlignmentType, TableOfContents } = require('docx');
const D = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')); const OUTDIR = process.argv[3]; fs.mkdirSync(OUTDIR, { recursive: true });
const BOOK = 'Saint Seiya: The Hades';
const FONT = 'Calibri', JFONT = 'Noto Sans CJK JP', W = 9026;
const border = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' }, borders = { top: border, bottom: border, left: border, right: border };
const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, noBorders = { top: none, bottom: none, left: none, right: none };
const run = (t, o = {}) => new TextRun({ text: String(t == null ? '' : t), font: FONT, size: 21, ...o });
const jp = (t, o = {}) => new TextRun({ text: String(t == null ? '' : t), font: { name: JFONT, eastAsia: JFONT }, size: 15, color: '7F7F7F', ...o });
function marked(text, o = {}) { const out = []; String(text == null ? '' : text).split(/(«[^»]*»)/).forEach(p => { if (!p) return; if (p.startsWith('«')) out.push(run(p.slice(1, -1), { ...o, bold: true })); else out.push(run(p, o)); }); return out; }
const P = (t, o = {}) => new Paragraph({ spacing: { after: 100 }, ...o, children: (Array.isArray(t) ? t : [t]).flatMap(x => typeof x === 'string' ? marked(x, { size: o.size || 21, italics: o.italics, color: o.color }) : [x]) });
let HEADINGS = [];
const H1 = t => { HEADINGS.push([1, t]); return new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun({ text: t, font: FONT })] }); };
const H2 = t => { HEADINGS.push([2, t]); return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] }); };
const H3 = t => new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, children: [new TextRun({ text: t, font: FONT })] });
const PB = () => new Paragraph({ children: [new PageBreak()] });
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
    const text = l.pt || (l.voice ? '(só voz, sem legenda no disco)' : '');
    out.push(new Paragraph({ spacing: { after: 10 }, indent: { left: 360, hanging: 360 }, keepNext: true, children: [run(who + ': ', { bold: true, color: colour[who], size: 20 }), run(text, { size: 20, italics: !l.pt })] }));
    out.push(new Paragraph({ spacing: { after: 90 }, indent: { left: 360 }, children: [run(l.en ? l.en + '   ' : '', { size: 14, color: '7F7F7F', italics: true }), jp(l.jp, { size: 14 }), ...(l.voice ? [run('   ♪ ' + l.voice + (l.source === 'fixed' ? '  · revisada' : ''), { size: 12, color: 'A6A6A6' })] : [])] }));
  }
  return out;
}
let c = []; const docs = [];
const VOLUMES = [['01', 'O jogo e os 49 lutadores'], ['02', 'A história: a Guerra Santa contra Hades'], ['03', 'Os Juízes, a Lenda dos Cavaleiros, os resumos e o resto do disco']];
function startDoc(num) {
  const title = VOLUMES.find(v => v[0] === num)[1];
  c = []; HEADINGS = []; docs.push({ num, title, children: c, headings: HEADINGS });
  c.push(new Paragraph({ spacing: { before: 1200, after: 100 }, children: [run(BOOK, { size: 40, bold: true })] }));
  c.push(new Paragraph({ spacing: { after: 60 }, children: [jp('聖闘士星矢 冥王ハーデス十二宮編 (PlayStation 2, 2006)', { size: 24, color: '595959' })] }));
  c.push(new Paragraph({ spacing: { after: 200 }, children: [run(`Volume ${num}: ${title}`, { size: 30, color: '1F3864', bold: true })] }));
  if (D.cover.title) c.push(IMG(D.cover.title, 420, 300));
  c.push(P([run('Tudo o que o disco europeu do jogo guarda: a história fala por fala, traduzida para o português a partir do texto inglês do próprio disco (com o inglês e o japonês ao lado), os lutadores com os modelos 3D do disco, as imagens e os sons. O livro está dividido em volumes:', { size: 18, color: '595959' })]));
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
  for (const [lvl, t] of doc.headings) { if (lvl === 1) { flush(); const s = SUMMARIES[t] || ''; out.push(P([run(t, { bold: true, size: 19 }), run(s ? ' — ' + s : '', { size: 18 })], { spacing: { before: 60, after: 20 } })); } else if (lvl === 2 && sub.length < 50) sub.push(t); }
  flush(); return out;
}
const S = D.stats, F = D.facts;
const byGroup = g => D.chapters.filter(ch => ch.group === g);

// ===== VOLUME 01
startDoc('01');
c.push(H1('Sobre este livro'));
SUMMARIES['Sobre este livro'] = 'o que é o jogo, de onde veio cada coisa deste livro e como ele está organizado.';
c.push(P(`Saint Seiya: The Hades (聖闘士星矢 冥王ハーデス十二宮編, "capítulo do Santuário da saga de Hades") é o segundo jogo de luta de Os Cavaleiros do Zodíaco para PlayStation 2, feito pela Dimps e lançado pela Bandai em 2006 no Japão e em 2007 na Europa, sem versão brasileira. Este livro foi montado a partir do disco europeu: as vozes são as japonesas originais e as legendas vêm em inglês, francês, italiano, espanhol, alemão e japonês. As falas aqui estão em português, traduzidas do inglês do disco por um modelo de linguagem local e revisadas onde indicado; abaixo de cada fala ficam o inglês e o japonês originais.`));
c.push(P(`O livro reúne os ${S.fighters} lutadores com os modelos 3D do disco e as listas de golpes, a história completa do modo História (${S.chapters} capítulos e cenas, ${S.lines} falas), as cenas dos três Juízes, o modo Lenda dos Cavaleiros, os resumos narrados, os filmes, as músicas e os textos dos menus.`));
c.push(table([2600, W - 2600], [['Executável do disco', F.boot || ''], ['Versão', `${F.version || ''} (${F.vmode || ''})`], ['Arquivos no AFSDATA.AFS', String(F.afs_files)], ['Imagens extraídas', String(F.pictures)], ['Sons ADX', String(F.adx)], ['Linhas de texto em inglês', String(F.strings)]], { head: false }));
c.push(P([run('Nomes. ', { bold: true }), run('Os nomes seguem a dublagem brasileira da série (Máscara da Morte, Afrodite, Milo, Radamanthys, Orfeu, Shina, Mestre Ancião, Espectro, Sapuri). O nome à frente de cada fala vem do arquivo de voz, que traz o número do personagem que fala.')]));
c.push(H2('O Zodiac Holiday e os textos dos menus'));
for (const m of D.menus) { c.push(H3(`${m.label} (${m.file})`)); c.push(table([700, W - 700], [['Nº', 'Texto (inglês)'], ...m.rows.map(r => [String(r.id), r.en])], { size: 15 })); }
c.push(H1('Os 49 lutadores'));
SUMMARIES['Os 49 lutadores'] = 'cada personagem jogável com a etiqueta de nome, o rosto, os modelos 3D do disco e a lista de golpes.';
c.push(P('Os lutadores na ordem em que o disco os numera: os cinco Cavaleiros de Bronze com três Armaduras cada (a atual, a Armadura Final e a primeira), Seiya, Shiryu e Hyoga com Armaduras de Ouro, os Cavaleiros de Ouro, Kanon, Orfeu, Marin, Shina, Shion, os cinco Cavaleiros de Ouro ressuscitados com os Sapuris de Espectro, os três Juízes do Inferno e os cinco Bronze com as Armaduras douradas. Não há um Seiya com Sapuri de Sagitário: as versões de Espectro são só as de Máscara da Morte, Afrodite, Shura, Camus e Saga.'));
for (const k of D.fighters) {
  c.push(H2(`${k.number} · ${k.full}${k.english ? ' (' + k.english + ')' : ''}`));
  const r = imgRow([k.face ? { file: k.face, label: 'Rosto' } : null, k.nametag ? { file: k.nametag, label: 'Etiqueta' } : null], 200, 120); if (r) c.push(r);
  for (const key of ['cor1', '_cor2', '_h', '_h_cor2']) {
    const rd = k.renders && k.renders[key]; if (!rd) continue;
    const row = imgRow([{ file: rd.views.front, label: 'Frente' }, { file: rd.views.side, label: 'Lado' }, { file: rd.views.back, label: 'Costas' }, { file: rd.views.three_quarter, label: 'Três quartos' }], 170, 330);
    if (row) { c.push(P([run(`Modelo 3D do jogo, ${rd.label.toLowerCase()}`, { bold: true, size: 18 })], { keepNext: true, spacing: { before: 100, after: 40 } })); c.push(row); }
  }
  if (k.model) c.push(P([run(`Modelo: ${k.model.triangles} triângulos, ${k.model.bones} ossos, ${k.model.parts} partes.`, { size: 16, color: '595959' })]));
  if (k.skills.length) c.push(P([run('Golpes: ', { bold: true, size: 18 }), run(k.skills.join(' · '), { size: 18 })]));
}
if (D.extra_models.length) { c.push(H2('Os outros modelos 3D do disco')); for (const g of grid(D.extra_models.filter(m => m.front).map(m => ({ file: m.front, label: `${m.file} (${m.triangles} triângulos)` })), 4, 150, 260)) c.push(g); }

if (D.stages && D.stages.length) {
  c.push(H1('Os cenários'));
  SUMMARIES['Os cenários'] = `os ${D.stages.length} cenários do disco, renderizados a partir dos modelos 3D.`;
  c.push(P('Os cenários das lutas, montados a partir das peças do disco: o chão em ladrilhos, os objetos colocados sobre ele (colunas, tochas, pedaços que quebram) e, na segunda imagem de cada um, o cenário distante ao redor.'));
  for (const st of D.stages) {
    c.push(H2(`${st.name} (${st.id})`));
    const row = imgRow([st.aerial ? { file: st.aerial, label: 'Arena' } : null, st.completo ? { file: st.completo, label: 'Com o cenário distante' } : null], 300, 260); if (row) c.push(row);
    c.push(P([run(`${st.tiles} ladrilhos, ${st.objects} objetos, ${st.triangles} triângulos no chão.`, { size: 16, color: '595959' })]));
  }
}

// ===== VOLUME 02
function chapterBlock(ch) {
  c.push(H2(`${ch.title}${ch.speakers.length ? ' — ' + ch.speakers.slice(0, 4).join(', ') : ''}`));
  for (const b of ch.blocks) {
    if (b.part) c.push(H3(`Cena de batalha ${b.part}`));
    c.push(P([run(`Roteiro ${b.script}: ${b.pages} páginas`, { size: 15, color: '7F7F7F' }), ...(b.bgm.length ? [run('  ·  música: ' + b.bgm.join(', '), { size: 15, color: '7F7F7F' })] : [])], { spacing: { after: 60 } }));
    for (const d of dialogue(b.lines)) c.push(d);
  }
}
startDoc('02');
c.push(H1('A Guerra Santa contra Hades'));
SUMMARIES['A Guerra Santa contra Hades'] = 'o modo História completo, capítulo por capítulo e fala por fala.';
c.push(P('O modo História segue a saga de Hades desde a invasão do Santuário pelos Cavaleiros de Ouro ressuscitados até o Muro das Lamentações: cada capítulo é um roteiro do disco, com suas cenas de batalha logo abaixo. As falas são a tradução do texto inglês do disco; o inglês e o japonês originais ficam em cinza.'));
for (const ch of byGroup('main')) chapterBlock(ch);

// ===== VOLUME 03
startDoc('03');
c.push(H1('Os três Juízes'));
SUMMARIES['Os três Juízes'] = 'as cenas de Radamanthys, Aiacos e Minos.';
for (const ch of byGroup('judges')) chapterBlock(ch);
c.push(H1('Lenda dos Cavaleiros'));
SUMMARIES['Lenda dos Cavaleiros'] = 'o modo que conta o lado dos Cavaleiros de Ouro.';
for (const ch of byGroup('legend')) chapterBlock(ch);
c.push(H1('Resumos narrados'));
SUMMARIES['Resumos narrados'] = 'as narrações que resumem a história entre as fases.';
for (const ch of byGroup('digest')) chapterBlock(ch);
c.push(H1('As oito cenas do Zodiac Holiday'));
c.push(table([3600, W - 3600], [['Inglês', 'Português'], ...D.demos.map(d => [d[0], d[1]])], { size: 16 }));
c.push(H1('Filmes, músicas e sons'));
SUMMARIES['Filmes, músicas e sons'] = 'as duas aberturas e o logotipo, a lista das músicas, as vozes e os bancos de efeitos.';
for (const m of D.movies) { c.push(H2(`${m.title} (${m.name}.mp4, ${m.duration})`)); for (const g of grid(m.frames.filter(Boolean).map(f => ({ file: f })), 3, 190, 110)) c.push(g); }
c.push(H2('Músicas'));
c.push(table([3400, W - 3400], [['Arquivo', 'Duração'], ...D.music.map(m => [m.file, m.duration])], { size: 16 }));
c.push(P(`Vozes: ${D.voices} vozes japonesas das cenas (pasta Vozes/História, uma pasta por capítulo, quem fala no nome do arquivo) e as vozes de batalha por lutador. Efeitos sonoros: ${D.bank_samples} amostras em ${D.bank_count} bancos (pasta Música/Efeitos).`));
c.push(H1('O arquivo GX_MAIN.SFD'));
c.push(P('O disco traz um arquivo de filme de 1,8 GB que só contém zeros: é enchimento para ocupar o DVD, não um filme. As cenas da história são feitas em tempo real com os modelos 3D.'));

(async () => {
  for (const d of docs) {
    const kids = []; for (const x of d.children) { if (x && x.__summary_placeholder) kids.push(...summaryBlock(d)); else if (x) kids.push(x); }
    const doc = new Document({ creator: 'games-extractor', title: `${BOOK} - ${d.num} - ${d.title}`,
      styles: { default: { document: { run: { font: FONT, size: 21 } } }, paragraphStyles: [
        { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 36, bold: true, color: '1F3864', font: FONT }, paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
        { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 28, bold: true, color: '2E74B5', font: FONT }, paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 1 } },
        { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 23, bold: true, color: '404040', font: FONT }, paragraph: { spacing: { before: 200, after: 60 }, outlineLevel: 2 } }] },
      features: { updateFields: true },
      sections: [{ properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } },
        footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run(`Saint Seiya: The Hades · volume ${d.num} · `, { size: 15, color: '7F7F7F' }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 15, color: '7F7F7F' })] })] }) },
        children: kids }] });
    const file = path.join(OUTDIR, `Saint Seiya - The Hades - ${d.num} - ${d.title}.docx`);
    fs.writeFileSync(file, await Packer.toBuffer(doc));
    console.log(file, (fs.statSync(file).size / 1048576).toFixed(1) + ' MB', d.headings.length + ' headings');
  }
})();
