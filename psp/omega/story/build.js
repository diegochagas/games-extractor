// Saint Seiya Omega Ultimate Cosmo - story book (pt-BR).  node build.js story_book.json OUT_DIR
const fs = require('fs'), path = require('path');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, ImageRun, PageBreak, BorderStyle, LevelFormat, Footer, PageNumber, AlignmentType, TableOfContents } = require('docx');
const D = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')); const OUTDIR = process.argv[3]; fs.mkdirSync(OUTDIR, { recursive: true });
const BOOK = 'Saint Seiya Omega Ultimate Cosmo';
const FONT = 'Calibri', JFONT = 'Noto Sans CJK JP', W = 9026;
const border = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' }, borders = { top: border, bottom: border, left: border, right: border };
const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, noBorders = { top: none, bottom: none, left: none, right: none };
const run = (t, o = {}) => new TextRun({ text: String(t == null ? '' : t), font: FONT, size: 21, ...o });
const jp = (t, o = {}) => new TextRun({ text: String(t == null ? '' : t), font: { name: JFONT, eastAsia: JFONT }, size: 15, color: '7F7F7F', ...o });
const P = (t, o = {}) => new Paragraph({ spacing: { after: 100 }, ...o, children: (Array.isArray(t) ? t : [t]).map(x => typeof x === 'string' ? run(x, { size: o.size || 21, italics: o.italics, color: o.color }) : x) });
let HEADINGS = [];
const H1 = t => { HEADINGS.push([1, t]); return new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun({ text: t, font: FONT })] }); };
const H2 = t => { HEADINGS.push([2, t]); return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] }); };
const H3 = t => new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, children: [new TextRun({ text: t, font: FONT })] });
const PB = () => new Paragraph({ children: [new PageBreak()] });
const cap = t => P([run(t, { size: 17, color: '595959', italics: true })], { spacing: { after: 160 }, alignment: AlignmentType.CENTER });
function imgSize(file) { try { const b = fs.readFileSync(file); if (b.slice(1, 4).toString() === 'PNG') return [b.readUInt32BE(16), b.readUInt32BE(20)]; } catch (e) {} return [400, 300]; }
function picture(file, maxW, maxH) { const [w0, h0] = imgSize(file); const s = Math.min(maxW / w0, maxH / h0, 1.0); return new ImageRun({ type: 'png', data: fs.readFileSync(file), transformation: { width: Math.max(8, Math.round(w0 * s)), height: Math.max(8, Math.round(h0 * s)) } }); }
function IMG(file, maxW = 600, maxH = 420) { if (!file || !fs.existsSync(file)) return null; return new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 80, after: 40 }, children: [picture(file, maxW, maxH)] }); }
function imgRow(files, maxW = 150, maxH = 170) { // several images side by side in a borderless table
  const list = files.filter(f => f && (f.file || f) && fs.existsSync(f.file || f)); if (!list.length) return null;
  const cw = Math.floor(W / list.length);
  const cells = list.map(f => new TableCell({ borders: noBorders, width: { size: cw, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [picture(f.file || f, Math.min(maxW, cw / 15 - 6), maxH)] }), ...(f.label ? [P([run(f.label, { size: 15, color: '595959' })], { alignment: AlignmentType.CENTER, spacing: { after: 60 } })] : [])] }));
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: list.map(() => cw), rows: [new TableRow({ cantSplit: true, children: cells })] });
}
const chunk = (a, n) => { const r = []; for (let i = 0; i < a.length; i += n) r.push(a.slice(i, i + n)); return r; };
function grid(files, perRow, maxW, maxH) { const out = []; for (const g of chunk(files.filter(f => f && (f.file || f)), perRow)) { const r = imgRow(g, maxW, maxH); if (r) { out.push(r); } } return out; }
function table(cols, rows, { head = true, size = 17, jcol = [] } = {}) {
  const mk = (cells, isHead) => new TableRow({ tableHeader: isHead, cantSplit: true, children: cells.map((c, i) => new TableCell({ borders, width: { size: cols[i], type: WidthType.DXA }, shading: isHead ? { fill: 'DCE6F1', type: ShadingType.CLEAR, color: 'auto' } : undefined, margins: { top: 30, bottom: 30, left: 60, right: 60 }, children: [new Paragraph({ children: [jcol.includes(i) && !isHead ? jp(c, { size: size - 2 }) : new TextRun({ text: String(c == null ? '' : c), font: FONT, size, bold: isHead })] })] })) });
  return new Table({ width: { size: cols.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: cols, rows: head ? [mk(rows[0], true), ...rows.slice(1).map(r => mk(r, false))] : rows.map(r => mk(r, false)) });
}
const SPEAKER_COLOURS = ['1F3864', '833C0B', '375623', '7030A0', '806000', '1F4E79', 'C00000', '3A3A3A'];
function dialogue(lines, hero) {
  const out = []; const colour = {}; let next = 1;
  for (const l of lines) {
    const who = l.speaker || '—';
    if (!(who in colour)) colour[who] = who.startsWith(hero) ? SPEAKER_COLOURS[0] : SPEAKER_COLOURS[(next++ - 1) % (SPEAKER_COLOURS.length - 1) + 1];
    out.push(new Paragraph({ spacing: { after: 10 }, indent: { left: 360, hanging: 360 }, keepNext: true, children: [run(who + ': ', { bold: true, color: colour[who], size: 20 }), run(l.pt, { size: 20 })] }));
    out.push(new Paragraph({ spacing: { after: 90 }, indent: { left: 360 }, children: [jp(l.jp), ...(l.voice ? [run('   ♪ ' + l.voice.replace('event/sound/', ''), { size: 12, color: 'A6A6A6' })] : [])] }));
  }
  return out;
}
let c = []; const docs = [];
const VOLUMES = [['01', 'O jogo, os personagens e os cenários'], ['02', 'A história: Kouga, Yuna, Ryuho e Souma'], ['03', 'A história: Eden, Haruto e Seiya'], ['04', 'Galeria, músicas e todos os textos do jogo']];
function startDoc(num) {
  const title = VOLUMES.find(v => v[0] === num)[1];
  c = []; HEADINGS = []; docs.push({ num, title, children: c, headings: HEADINGS });
  c.push(new Paragraph({ spacing: { before: 1200, after: 100 }, children: [run(BOOK, { size: 44, bold: true })] }));
  c.push(new Paragraph({ spacing: { after: 60 }, children: [jp('聖闘士星矢Ω アルティメットコスモ', { size: 26, color: '595959' })] }));
  c.push(new Paragraph({ spacing: { after: 200 }, children: [run(`Volume ${num}: ${title}`, { size: 30, color: '1F3864', bold: true })] }));
  if (D.cover.pic) c.push(IMG(D.cover.pic, 480, 272));
  c.push(P([run('A história completa do jogo em português, ilustrada com as imagens e os modelos 3D do próprio disco. O livro está dividido em volumes:', { size: 18, color: '595959' })]));
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
    else if (lvl === 2 && sub.length < 30) sub.push(t);
  }
  flush();
  return out;
}
const S = D.stats, F = D.facts;
const playable = D.characters.filter(k => !k.v2), scaled = D.characters.filter(k => k.v2);

// =====================================================================  VOLUME 01
startDoc('01');
c.push(H1('Sobre este livro'));
SUMMARIES['Sobre este livro'] = 'o que é o jogo, de onde veio cada coisa deste livro e como ele está organizado.';
c.push(P(`${BOOK} (聖闘士星矢Ω アルティメットコスモ) é o jogo de luta de Saint Seiya Omega para PSP, lançado pela Namco Bandai Games apenas no Japão, em novembro de 2012. Nunca foi traduzido: todo o texto em português deste livro foi traduzido do japonês a partir dos arquivos do disco, e o original aparece em cinza logo abaixo de cada fala, com a leitura dos termos entre parênteses.`));
if (D.summary) c.push(P(D.summary));
c.push(P(`O livro reúne tudo o que o disco guarda: os ${playable.length} lutadores e as ${scaled.length} versões com a Escama de Triton, com perfil, golpes, retratos e os modelos 3D renderizados de frente, de lado e de costas; os cenários de batalha; as sete histórias do modo História, fala por fala (${S.lines} falas em ${S.scenes} cenas, ${S.voiced} delas com voz gravada); as ilustrações de evento, os filmes e as músicas; e, no último volume, todos os outros textos do jogo (menus, mensagens do sistema, tutorial) e o que os desenvolvedores deixaram sem uso no disco.`));
c.push(table([2600, W - 2600], [['Título no disco', F.TITLE || ''], ['Código do disco', F.DISC_ID || ''], ['Versão', `${F.DISC_VERSION || ''} (aplicativo ${F.APP_VER || ''})`], ['Sistema exigido', 'PSP, firmware ' + (F.PSP_SYSTEM_VER || '')], ['Classificação etária (nível do sistema)', String(F.PARENTAL_LEVEL || '')], ['Nome interno do programa', 'AppNewGalaxy (pastas de trabalho "newGALA")'], ['Textos', `${S.strings} linhas em ${'193'} tabelas (BTX, UTF-16)`], ['Modelos 3D', `${S.models} modelos e ${S.motions} animações (formato GMO da Sony)`]], { head: false }));
c.push(P(''));
c.push(P([run('Nomes. ', { bold: true }), run('Os nomes seguem a grafia do site saintseiyacloths (Kouga, Ryuho, Souma, Sorento...). Os termos seguem a tradição brasileira da série: Cavaleiro e Amazona (聖闘士, Saint), Armadura (聖衣, Cloth), Escama (鱗衣, Scale), Cosmo (小宇宙). Os nomes dos golpes ficam no original, como no jogo.')]));
c.push(P([run('Quem fala. ', { bold: true }), run('O nome à frente de cada fala é o que a caixa de texto do jogo mostra. Quando o jogo esconde quem fala ("???" ou "Homem"), o arquivo de voz entrega o personagem, que aparece entre parênteses. O código com ♪ é o arquivo da voz gravada, na pasta de vozes.')]));
c.push(H2('O menu principal'));
c.push(table([3400, W - 3400], [['Original', 'Descrição no jogo'], ...D.menu.map(m => [m.jp, m.pt])], { jcol: [0], size: 17 }));
if (D.cover.title) { c.push(IMG(D.cover.title, 480, 272)); c.push(cap('Tela de título')); }

c.push(H1('Os personagens'));
SUMMARIES['Os personagens'] = 'os dezoito lutadores, com o perfil do jogo, os golpes, os retratos das cenas e os modelos 3D.';
c.push(P(`Dezoito lutadores, na ordem em que o jogo os numera. Cada um tem duas paletas (jogador 1 e jogador 2) e três estados de Armadura: inteira, danificada (a mesma malha com a textura rachada) e destruída (outra malha). Os renders mostram o modelo do jogo na pose de repouso do esqueleto, sem perspectiva.`));
function characterBlock(k) {
  c.push(H2(`${k.name} (${k.jp})`));
  const head = [k.picture ? { file: k.picture } : null, k.select ? { file: k.select, label: 'Seleção de personagem' } : null, k.nameplate ? { file: k.nameplate, label: 'Nome no menu' } : null];
  const r = imgRow(head, 260, 330); if (r) c.push(r);
  c.push(P([run(k.rank, { bold: true, color: '1F3864' }), run(k.element ? `  ·  Elemento: ${k.element}` : ''), run(k.voice ? `  ·  Voz: ${k.voice}` : '')]));
  c.push(P(k.profile));
  c.push(new Paragraph({ spacing: { after: 120 }, children: [jp(k.profile_jp)] }));
  for (const key of ['00_normal', '00_half', '00_broken', '01_normal', '01_broken']) {
    const rd = k.renders[key]; if (!rd) continue;
    const full = key === '00_normal' || key === '00_broken';
    const row = imgRow(full ? [{ file: rd.views.front, label: 'Frente' }, { file: rd.views.side, label: 'Lado' }, { file: rd.views.back, label: 'Costas' }] : [{ file: rd.views.front, label: 'Frente' }, { file: rd.views.back, label: 'Costas' }], full ? 190 : 150, full ? 330 : 240);
    if (row) { c.push(P([run(rd.label, { bold: true, size: 18 })], { keepNext: true, spacing: { before: 100, after: 40 } })); c.push(row); }
  }
  if (k.poses.length) { const row = imgRow(k.poses, 190, 300); if (row) { c.push(P([run('Poses das animações', { bold: true, size: 18 })], { keepNext: true, spacing: { before: 100, after: 40 } })); c.push(row); } }
  if (k.model && k.model.triangles) c.push(P([run(`Modelo: ${k.model.triangles} triângulos, ${k.model.bones} ossos, ${k.model.animations} animações${k.model.attachments ? `, ${k.model.attachments} peça(s) presa(s) ao esqueleto (cabelo, capa, asas ou arma)` : ''}.`, { size: 16, color: '595959' })]));
  if (k.bustups.length) { c.push(P([run('Retratos das cenas de diálogo', { bold: true, size: 18 })], { keepNext: true, spacing: { before: 100, after: 40 } })); for (const g of grid(k.bustups, 5, 110, 130)) c.push(g); }
  if (k.arcade) { c.push(IMG(k.arcade, 400, 230)); c.push(cap('Ilustração de encerramento do modo Arcade')); }
  if (k.combos.length) { c.push(P([run('Golpes e combos', { bold: true, size: 18 })], { keepNext: true, spacing: { before: 100, after: 40 } })); c.push(table([W - 4300, 4300], [['Lista de comandos (P = soco, K = chute, S = especial)', 'Original'], ...k.combos.map(m => [m.pt, m.jp])], { jcol: [1], size: 16 })); }
}
for (const k of playable) characterBlock(k);
c.push(H1('Os Cavaleiros com a Escama de Triton'));
SUMMARIES['Os Cavaleiros com a Escama de Triton'] = 'as seis versões dos protagonistas vestindo a Escama de Triton, criada para o jogo.';
c.push(P('Os seis jovens Cavaleiros de Bronze têm uma segunda versão jogável, vestindo a Escama de Triton que o final de cada história entrega. São personagens separados no jogo, com perfil e atributos próprios.'));
for (const k of scaled) characterBlock(k);
if (D.extra_portraits.length) { c.push(H1('Outros personagens das cenas')); SUMMARIES['Outros personagens das cenas'] = 'quem aparece só nos diálogos: Atena, Julian Solo e o homem misterioso.'; c.push(P('Personagens que só existem como retrato nas cenas de diálogo, sem modelo 3D de luta.')); for (const g of grid(D.extra_portraits, 4, 140, 170)) c.push(g); }

c.push(H1('Os cenários de batalha'));
SUMMARIES['Os cenários de batalha'] = 'as dez arenas em 3D, vistas de fora e de cima, com os objetos quebráveis.';
c.push(P('Dez arenas e um mapa de teste esquecido no disco. Cada cenário é um modelo 3D com o céu em cúpula; nas vistas abaixo o céu, as nuvens e as montanhas do fundo foram retirados, e as faces vistas por trás ficam transparentes, para que as paredes não escondam a arena.'));
for (const s of D.stages) {
  c.push(H2(s.jp ? `${s.name} (${s.jp})` : s.name));
  c.push(P([run(`Arquivo ${s.id}`, { size: 15, color: '7F7F7F' })], { spacing: { after: 40 } }));
  const r1 = imgRow([s.select ? { file: s.select, label: 'Tela de seleção' } : null, s.sky ? { file: s.sky, label: 'Com o céu, de frente' } : null, s.top ? { file: s.top, label: 'De cima' } : null], 190, 200); if (r1) c.push(r1);
  if (s.view) { c.push(IMG(s.view, 600, 360)); c.push(cap(`Vista geral (${s.triangles} triângulos)`)); }
  if (s.objects.length) for (const g of grid(s.objects, 4, 130, 130)) c.push(g);
}
const b3 = D.backgrounds3d.filter(b => b.file);
if (b3.length) { c.push(H2('Fundos dos golpes especiais')); c.push(P('Três cúpulas usadas como fundo durante os golpes finais (galáxia, Marte e mar).')); const r = imgRow(b3, 190, 200); if (r) c.push(r); }

// =====================================================================  VOLUMES 02 / 03
function storyBlock(st) {
  const title = `A história de ${st.name}`;
  c.push(H1(title));
  SUMMARIES[title] = (st.summary || '').split(/(?<=\.)\s/)[0] || '';
  if (st.picture) c.push(IMG(st.picture, 260, 340));
  if (st.summary) c.push(P(st.summary, { italics: true }));
  c.push(table([900, 2600, W - 3500], [['Fase', 'Adversário', 'O que acontece'], ...st.stages.map(g => [String(g.number), g.opponent, g.summary])], { size: 16 }));
  for (const g of st.stages) {
    c.push(H2(`${st.name}, fase ${g.number}: VS ${g.opponent}`));
    if (g.summary) c.push(P(g.summary, { italics: true, color: '404040' }));
    for (const sc of g.scenes) {
      c.push(H3(`${sc.phase}`));
      c.push(P([run(`Cena ${sc.script}`, { size: 15, color: '7F7F7F' }), run('  ·  ', { size: 15, color: '7F7F7F' }), jp(sc.title_jp, { size: 14 }), ...(sc.bgm.length ? [run('  ·  música: ' + sc.bgm.join(', '), { size: 15, color: '7F7F7F' })] : []), ...(sc.movies.length ? [run('  ·  filme: ' + sc.movies.join(', '), { size: 15, color: '7F7F7F' })] : []), ...(sc.title_note ? [run('  ·  o título interno ficou com o nome de outra cena', { size: 15, color: 'C00000', italics: true })] : [])], { spacing: { after: 60 } }));
      const bg = imgRow(sc.backgrounds.map(f => ({ file: f })), 280, 170); if (bg) c.push(bg);
      for (const d of dialogue(sc.lines, st.name)) c.push(d);
      for (const f of sc.stills) c.push(IMG(f, 440, 250));
      if (sc.stills.length) c.push(cap(sc.stills.length > 1 ? 'Ilustrações de evento desta cena' : 'Ilustração de evento desta cena'));
      const it = imgRow(sc.items.map(f => ({ file: f })), 70, 70); if (it) { c.push(it); c.push(cap('Aqua Drops mostradas na cena')); }
      if (sc.cut.length) { c.push(P([run('Falas gravadas no arquivo da cena que o roteiro não chama:', { size: 16, italics: true, color: 'C00000' })], { spacing: { before: 80, after: 40 } })); for (const d of dialogue(sc.cut, st.name)) c.push(d); }
      if (sc.phase.startsWith('Antes')) c.push(P([run(`Batalha: ${st.name} contra ${g.opponent}`, { bold: true, size: 19, color: '833C0B' })], { alignment: AlignmentType.CENTER, border: { top: { style: BorderStyle.SINGLE, size: 6, color: 'C9A27A', space: 4 }, bottom: { style: BorderStyle.SINGLE, size: 6, color: 'C9A27A', space: 4 } }, spacing: { before: 160, after: 160 } }));
    }
  }
}
startDoc('02');
for (const st of D.stories.slice(0, 4)) storyBlock(st);
startDoc('03');
for (const st of D.stories.slice(4)) storyBlock(st);

// =====================================================================  VOLUME 04
startDoc('04');
c.push(H1('Ilustrações de evento'));
SUMMARIES['Ilustrações de evento'] = 'todas as ilustrações das cenas e os 48 títulos da coleção do jogo.';
c.push(P('As ilustrações em tela cheia que o modo História mostra. No jogo elas ficam guardadas na Coleção de CG, que tem 48 lugares: as ilustrações da história, os três finais e o encerramento do modo Arcade de cada um dos dezoito lutadores (estes estão no volume 01, na ficha de cada personagem).'));
for (const g of chunk(D.stills, 2)) { const r = imgRow(g.map(s => ({ file: s.file, label: s.label + (s.used ? ' · ' + s.used : '') })), 290, 170); if (r) c.push(r); }
c.push(H2('Títulos da Coleção de CG'));
c.push(P('Os títulos na ordem do jogo. O disco não guarda, nos arquivos lidos, qual título pertence a qual imagem; a ordem acompanha a das histórias (Kouga, Souma, Yuna...), por isso a lista fica aqui separada das imagens.'));
c.push(table([900, W - 900 - 3600, 3600], [['Nº', 'Título', 'Original'], ...D.cg_titles.map(t => [String(t.number), t.pt, t.jp])], { jcol: [2], size: 16 }));
c.push(H2('Fundos das cenas de diálogo'));
for (const g of grid(D.backgrounds, 3, 190, 120)) c.push(g);
c.push(H2('As sete Aqua Drops'));
{ const r = imgRow(D.items.filter(i => i.file), 80, 80); if (r) c.push(r); }

c.push(H1('Filmes'));
SUMMARIES['Filmes'] = 'os cinco filmes do disco, com quadros de cada um.';
c.push(P('Cinco filmes em 480 × 272, convertidos para MP4 (vídeo original, sem recompressão) na pasta de vídeos.'));
for (const m of D.movies) { c.push(H2(`${m.title} (${m.name}.mp4, ${m.duration})`)); for (const g of grid(m.frames.filter(Boolean).map(f => ({ file: f })), 3, 190, 110)) c.push(g); }

c.push(H1('Músicas e vozes'));
SUMMARIES['Músicas e vozes'] = 'a lista das músicas com as histórias que as usam e o que há nas pastas de vozes.';
c.push(table([3800, 1100, W - 4900], [['Arquivo', 'Duração', 'Histórias que usam'], ...D.music.map(m => [m.file, m.duration, m.used])], { size: 16 }));
c.push(P(''));
c.push(P(`Vozes: ${D.voices.story} vozes gravadas das cenas (pasta event/sound: uma pasta por história e uma frase de cada lutador), as chamadas de golpe especial (scene/battle/sound/voice) e os bancos de som de luta, menus e galeria (pasta banks, numerados como no jogo).`));
if (D.voices.without_text.length) { c.push(H2('Vozes gravadas sem fala correspondente')); c.push(P('Arquivos de voz que existem no disco mas não têm texto em nenhuma cena:')); c.push(P([run(D.voices.without_text.join('   '), { size: 15, color: '595959' })])); }

c.push(H1('Todos os outros textos do jogo'));
SUMMARIES['Todos os outros textos do jogo'] = 'menus, mensagens do sistema, tutorial, configurações e galeria, tabela por tabela.';
c.push(P('Cada tabela de texto do disco que não é fala de cena nem ficha de personagem, na ordem dos arquivos. Linhas que são só números ou símbolos ficam como no original.'));
for (const t of D.system) { c.push(H2(t.file.replace(/^.*\/([^/]+\/[^/]+)$/, '$1'))); c.push(table([800, W - 800 - 3700, 3700], [['Nº', 'Português', 'Original'], ...t.rows.map(r => [String(r.id), r.pt, r.jp])], { jcol: [2], size: 15 })); }

c.push(H1('O que ficou sem uso no disco'));
SUMMARIES['O que ficou sem uso no disco'] = 'roteiros de teste dos desenvolvedores e outras sobras.';
c.push(P('Além das sete histórias, o disco tem 240 roteiros numerados de 00 a 23 (dez por lutador) que são moldes vazios do modo História; alguns guardam falas de teste. Há também uma cópia em ZIP das vozes (três vezes o mesmo arquivo, "ext", "ext2" e "ext3", com 1.818 vozes de uma versão anterior), um mapa de teste e retratos com etiquetas provisórias.'));
for (const t of D.placeholders) { c.push(H2(`Roteiro ${t.file}: ${t.title}`)); c.push(table([800, W - 800 - 3700, 3700], [['Nº', 'Português', 'Original'], ...t.rows.map(r => [String(r.id), r.pt, r.jp])], { jcol: [2], size: 15 })); }
for (const t of D.leftovers) { c.push(H2(`Tabela fora do lugar: ${path.basename(t.file)}`)); c.push(P(`Arquivo ${t.file}`, { size: 16, color: '595959' })); c.push(table([800, W - 800 - 3700, 3700], [['Nº', 'Português', 'Original'], ...t.rows.map(r => [String(r.id), r.pt, r.jp])], { jcol: [2], size: 15 })); }

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
        footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run(`${BOOK} · volume ${d.num} · `, { size: 15, color: '7F7F7F' }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 15, color: '7F7F7F' })] })] }) },
        children: kids }] });
    const file = path.join(OUTDIR, `${BOOK} - ${d.num} - ${d.title}.docx`);
    fs.writeFileSync(file, await Packer.toBuffer(doc));
    console.log(file, (fs.statSync(file).size / 1048576).toFixed(1) + ' MB', d.headings.length + ' headings');
  }
})();
