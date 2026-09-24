// Saint Seiya Online - Story (pt-BR).  node build.js story.json "OUT.docx"
const fs = require('fs'), path = require('path');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, ImageRun, PageBreak, BorderStyle, LevelFormat, Footer, PageNumber, AlignmentType, TableOfContents } = require('docx');
const D = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')); const OUTF = process.argv[3];
const FONT = 'Calibri', W = 9026;
const border = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' }, borders = { top: border, bottom: border, left: border, right: border };
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: 21, ...o });
const P = (t, o = {}) => new Paragraph({ spacing: { after: 100 }, ...o, children: (Array.isArray(t) ? t : [t]).map(x => typeof x === 'string' ? run(x, { size: o.size || 21, italics: o.italics, color: o.color }) : x) });
const H1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT })] });
const H2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] });
const H3 = t => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: t, font: FONT })] });
const H4 = t => new Paragraph({ heading: HeadingLevel.HEADING_4, children: [new TextRun({ text: t, font: FONT })] });
const PB = () => new Paragraph({ children: [new PageBreak()] });
const bullet = c => new Paragraph({ numbering: { reference: 'bul', level: 0 }, spacing: { after: 40 }, children: c.map(x => typeof x === 'string' ? run(x) : x) });
const cap = t => P([run(t, { size: 17, color: '595959', italics: true })], { spacing: { after: 160 }, alignment: AlignmentType.CENTER });
const sizes = {};
function imgSize(file) { // read PNG/JPEG dimensions
  try { const b = fs.readFileSync(file); if (b.slice(1, 4).toString() === 'PNG') return [b.readUInt32BE(16), b.readUInt32BE(20)];
    if (b[0] === 0xFF && b[1] === 0xD8) { let i = 2; while (i < b.length) { if (b[i] !== 0xFF) { i++; continue; } const m = b[i + 1]; if (m >= 0xC0 && m <= 0xCF && m !== 0xC4 && m !== 0xC8 && m !== 0xCC) return [b.readUInt16BE(i + 7), b.readUInt16BE(i + 5)]; i += 2 + b.readUInt16BE(i + 2); } } } catch (e) {} return [400, 300]; }
function IMG(file, maxW = 600, maxH = 420, center = true) {
  if (!file || !fs.existsSync(file)) return null;
  const [w0, h0] = imgSize(file); const s = Math.min(maxW / w0, maxH / h0, 1.0); const w = Math.max(40, Math.round(w0 * s)), h = Math.max(40, Math.round(h0 * s));
  return new Paragraph({ alignment: center ? AlignmentType.CENTER : AlignmentType.LEFT, spacing: { before: 80, after: 40 }, children: [new ImageRun({ type: file.endsWith('.png') ? 'png' : 'jpg', data: fs.readFileSync(file), transformation: { width: w, height: h } })] });
}
function imgRow(files, maxW = 150, maxH = 170) { // several small images side by side in a borderless table
  const cells = files.filter(f => f && fs.existsSync(f.file || f)).map(f => { const file = f.file || f; const [w0, h0] = imgSize(file); const s = Math.min(maxW / w0, maxH / h0, 1); return new TableCell({ borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } }, width: { size: Math.floor(W / Math.max(1, files.length)), type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: file.endsWith('.png') ? 'png' : 'jpg', data: fs.readFileSync(file), transformation: { width: Math.round(w0 * s), height: Math.round(h0 * s) } })] }), ...(f.label ? [P([run(f.label, { size: 15, color: '595959' })], { alignment: AlignmentType.CENTER })] : [])] }); });
  if (!cells.length) return null; return new Table({ width: { size: W, type: WidthType.DXA }, rows: [new TableRow({ children: cells })] });
}
function table(cols, rows, { head = true, size = 17 } = {}) {
  const mk = (cells, isHead) => new TableRow({ tableHeader: isHead, cantSplit: true, children: cells.map((c, i) => new TableCell({ borders, width: { size: cols[i], type: WidthType.DXA }, shading: isHead ? { fill: 'DCE6F1', type: ShadingType.CLEAR, color: 'auto' } : undefined, margins: { top: 30, bottom: 30, left: 60, right: 60 }, children: [new Paragraph({ children: [c instanceof TextRun ? c : new TextRun({ text: String(c == null ? '' : c), font: FONT, size, bold: isHead })] })] })) });
  return new Table({ width: { size: cols.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: cols, rows: head ? [mk(rows[0], true), ...rows.slice(1).map(r => mk(r, false))] : rows.map(r => mk(r, false)) });
}
const IMGROOT = D.out ? D.out + '/' : '';
const chunk = (a, n) => { const r = []; for (let i = 0; i < a.length; i += n) r.push(a.slice(i, i + n)); return r; };
// ---------- quest rendering ----------
function questBlock(q, small = false) {
  const out = []; const sz = small ? 19 : 21;
  out.push(new Paragraph({ spacing: { before: 200, after: 60 }, keepNext: true, children: [run(q.name && q.name !== 'None' ? q.name : 'Etapa', { bold: true, size: sz + 1 }), run(`  [missão ${q.id}]`, { size: 14, color: '7F7F7F' }), ...(q.mt ? [run('  · texto em tradução automática do jogo', { size: 14, color: 'C00000', italics: true })] : [])] }));
  if (q.descript) out.push(P([run(q.descript, { size: sz, italics: true })], { spacing: { after: 80 } })); else out.push(P([run('(etapa da missão)', { size: 15, italics: true, color: '7F7F7F' })], { spacing: { after: 40 } }));
  const dlg = (label, wins) => { if (!wins || !wins.length) return; wins.forEach((w, i) => { if (w.talk) out.push(P([run(`${label}: `, { bold: true, size: sz - 1, color: '1F3864' }), run(w.talk, { size: sz - 1 })], { spacing: { after: 30 }, indent: { left: 360 } })); const opts = (w.options || []).filter(o => !/^(Aceitar|Recusar|Concluído|Cancelar|Confirmar|OK|Fechar|Sim|Não|\.\.\.)$/.test(o)); if (opts.length) out.push(P([run('Herói: ', { bold: true, size: sz - 1, color: '833C0B' }), run(opts.join('  /  '), { size: sz - 1 })], { spacing: { after: 30 }, indent: { left: 720 } })); }); };
  dlg('NPC', q.delv); dlg('Ao concluir', q.award); dlg('Se não estiver pronto', q.unq);
  return out;
}
const c = [];
// ---------- capa ----------
c.push(new Paragraph({ spacing: { before: 2000, after: 200 }, children: [run('Saint Seiya Online', { size: 56, bold: true })] }));
c.push(new Paragraph({ spacing: { after: 300 }, children: [run('A história completa, ilustrada com as imagens do jogo', { size: 30, color: '404040' })] }));
c.push(P('Saint Seiya Online (圣斗士星矢Online) é o MMORPG 3D da Perfect World, licenciado pela Shueisha e supervisionado por Masami Kurumada, lançado na China em 2013 e no Brasil e na América Latina em setembro de 2017 (Ongame / SEGA), em português e espanhol. A versão chinesa encerrou em 2018 e a brasileira em junho de 2020; hoje sobrevive no servidor de fãs Seiya Reborn, de onde vieram os arquivos usados neste livro.'));
c.push(P('Este documento reúne tudo o que o cliente do jogo guarda sobre a história: as quatro sagas da missão principal (Santuário, Poseidon, Hades: Cruzada ao Submundo e Hades: Inferno) com todas as missões e diálogos, as histórias secundárias de cada região, as trinta e oito "histórias" que o Professor Kurumada pede ao herói para investigar, a enciclopédia de personagens e Armaduras do próprio jogo (o Álbum), os mapas, as cinemáticas e os títulos. Os textos são os da localização oficial em português; quando o jogo só tinha tradução automática para um trecho (conteúdo antigo que a versão brasileira nunca revisou), isso está marcado em vermelho e um resumo em português correto precede o trecho.'));
c.push(P('Extraído em 24/09/2026 dos arquivos do cliente (element/data/lang_pt-BR.data, os pacotes .pck e o álbum surfaces/res/photobook). As capturas de tela do personagem vestindo cada Armadura e os renders das Armaduras vêm das pastas Saints e Cloths de Diego Chagas.'));
c.push(IMG(IMGROOT + 'images/surfaces/background/loading18.jpg.png', 620, 480)); c.push(cap('Tela de carregamento: o Santuário sob o céu estrelado'));
c.push(PB());
c.push(new Paragraph({ spacing: { after: 200 }, children: [run('Sumário', { size: 34, bold: true, color: '1F3864' })] }));
c.push(P([run('(No Word, clique com o botão direito no sumário abaixo e escolha "Atualizar campo" para ver as páginas.)', { size: 16, italics: true, color: '7F7F7F' })]));
c.push(new TableOfContents('Sumário', { hyperlink: true, headingStyleRange: '1-2' }));
c.push(P([run('Conteúdo', { bold: true, size: 24 })], { spacing: { before: 200 } }));
for (const line of ['O mundo do jogo: as regiões, os mapas, os capítulos e as telas de carregamento', 'Personagens: o Álbum do jogo e os personagens criados para o jogo', 'Armaduras: Bronze, Prata, Ouro, Divinas, Escamas e Sapuris, com renders e capturas', ...D.parts.map(p => p.title + ': ' + p.sections.map(s => s.title.split(':')[0]).join(', ')), 'As histórias dos personagens (Professor Kurumada): ' + D.char_stories.map(s => s.character).join(', '), 'Histórias secundárias por região', 'Apêndices: diálogos das dungeons, cinemáticas e legendas, títulos, outras missões e eventos (com diálogos), falas soltas dos NPCs, cobertura das Notas de Pesquisa']) c.push(bullet([line]));
c.push(PB());
// ---------- o mundo ----------
c.push(H1('O mundo do jogo'));
c.push(P('O jogador cria um aspirante a Cavaleiro escolhendo uma de cinco constelações de Bronze (Pégaso, Dragão, Cisne, Andrômeda e Fênix; mais tarde o jogo acrescentou Lira, Tornado e, para as facções de Poseidon e Hades, Dragão Marinho e Wyrm). O mesmo herói pode vestir dezenas de Armaduras de Bronze, Prata e Ouro, Escamas e Sapuris ao longo do jogo. A história segue os arcos do mangá clássico, mas vista pelos olhos desse novo Cavaleiro, que convive com Seiya, Shiryu, Hyoga, Shun e Ikki e carrega um segredo próprio: o sangue de Rodório, o primeiro Cavaleiro de Pégaso.'));
c.push(H2('As regiões'));
const placeCards = D.cards.filter(k => k.group === 'lugar');
for (const k of placeCards) { c.push(H3(k.pt)); const t = D.pb_texts[({ 'Terra das Constelações': 'T. das Constel.', 'Santuário': 'Santuário', 'Coliseu Graad': 'Coliseu Graad', 'Rozan': 'Rozan', 'Estrada Esquecida': 'Estr. Esquecida', 'Ilha da Rainha da Morte': 'I. da R. da Morte', 'Sibéria Oriental': 'Sibéria Orie.', 'Atlântida': 'Atlântida', 'Ilha de Andrômeda': 'Ilha de Andrôm.', 'Castelo de Hades': 'Cast. de Hades', 'Submundo': 'Submundo' })[k.pt]]; if (t) c.push(P(t)); const row = imgRow([{ file: IMGROOT + k.file, label: 'Cartão do Álbum' }, ...(({ 'Terra das Constelações': 'n1', 'Santuário': 'n2', 'Coliseu Graad': 'n4', 'Rozan': 'n3', 'Estrada Esquecida': 'n5', 'Ilha da Rainha da Morte': 'n6', 'Sibéria Oriental': 'n7', 'Atlântida': 'n8', 'Ilha de Andrômeda': 'n9', 'Castelo de Hades': 'n10', 'Submundo': 'n11' })[k.pt] ? [{ file: IMGROOT + `images/surfaces/maps/worldmaps/${({ 'Terra das Constelações': 'n1', 'Santuário': 'n2', 'Coliseu Graad': 'n4', 'Rozan': 'n3', 'Estrada Esquecida': 'n5', 'Ilha da Rainha da Morte': 'n6', 'Sibéria Oriental': 'n7', 'Atlântida': 'n8', 'Ilha de Andrômeda': 'n9', 'Castelo de Hades': 'n10', 'Submundo': 'n11' })[k.pt]}.dds.png`, label: 'Mapa da região' }] : [])], 240, 260); if (row) c.push(row); }
c.push(H2('Mapas e instâncias'));
c.push(P('Todos os mapas definidos no cliente (script/map/instance.lua), com o código interno usado nos arquivos e o nome oficial em português:'));
const seen = new Set(); const maprows = [['Código', 'Nome (pt-BR)', 'Nome original']];
for (const m of D.maps) { const k = m.map_code + '|' + m.name_pt; if (!m.map_code || seen.has(k)) continue; seen.add(k); maprows.push([m.map_code, m.name_pt || m.name_en, m.name_zh]); }
c.push(table([1200, 4400, W - 5600], maprows, { size: 15 }));
c.push(H2('Telas de carregamento e a linha do tempo das sagas'));
c.push(P('A missão principal está dividida em 22 capítulos. O jogo entrega um título ao herói ao fim de cada um:'));
c.push(table([3200, 900, W - 4100], [['Saga', 'Cap.', 'Título do capítulo'], ...D.parts.flatMap(p => p.sections.map(s => [s.chapter[0], s.chapter[1], s.chapter[2]])).filter((r, i, a) => a.findIndex(x => x.join() === r.join()) === i)], { size: 17 }));
const loads = ['loading01', 'loading02', 'loading05', 'loading06', 'loading08', 'loading10', 'loading12', 'loading13', 'loading14', 'loading16'].map(n => IMGROOT + `images/surfaces/background/${n}.jpg.png`);
for (const g of chunk(loads, 2)) { const r = imgRow(g, 300, 240); if (r) c.push(r); }
c.push(cap('Telas de carregamento do jogo'));
c.push(H2('Os quadrinhos das telas de carregamento'));
c.push(P('Oito telas de carregamento reproduzem páginas de quadrinhos com os momentos clássicos da série; o Álbum do jogo também tem uma seção "Quadrinhos" (Volume I e II).'));
for (let i = 1; i <= 8; i++) { const f = IMGROOT + `images/surfaces/background/loading_comic_0${i}.jpg.png`; const im = IMG(f, 600, 480); if (im) { c.push(im); c.push(cap(`Quadrinhos da tela de carregamento ${i}`)); } }
c.push(PB());
// ---------- personagens ----------
c.push(H1('Personagens'));
c.push(P('As fichas abaixo são as do Álbum do próprio jogo (a seção "Personagens" da enciclopédia), com a ilustração do cartão, o retrato usado nos diálogos quando existe, e os dados e o texto oficiais em português. Em seguida vêm os personagens criados para o jogo, que não existem no mangá.'));
const portraitOf = (name) => { const map = { 'Saori Kido': 'Saori Kido', 'Julian Solo': 'Julian Solo', 'Máscara da Morte': null, 'Deus · Seiya': 'Seiya', 'Deus · Shiryu': 'Shiryu', 'Deus · Hyoga': 'Hyoga', 'Deus · Shun': 'Shun', 'Deus · Ikki': 'Ikki', 'Pégasus Negro': 'Pégaso Negro', 'Mino': null, 'Sorento': 'Sorento', 'Grande Mestre': 'Grande Mestre' }; const k = map[name] === undefined ? name : map[name]; return k && D.portraits[k] ? IMGROOT + D.portraits[k] : null; };
const cardOf = (name) => { const alias = { 'Saori Kido': 'Athena (Saori Kido)', 'Julian Solo': 'Julian Solo (Poseidon)', 'Mu': 'Mu de Áries', 'Aldebaran': 'Aldebaran de Touro', 'Saga': 'Saga de Gêmeos', 'Máscara da Morte': 'Máscara da Morte de Câncer', 'Aioria': 'Aioria de Leão', 'Shaka': 'Shaka de Virgem', 'Dohko': 'Dohko de Libra', 'Miro': 'Miro de Escorpião', 'Aioros': 'Aioros de Sagitário', 'Shura': 'Shura de Capricórnio', 'Camus': 'Camus de Aquário', 'Afrodite': 'Afrodite de Peixes', 'Orfeu': 'Orfeu de Lira', 'Marin': 'Marin de Águia', 'Shina': 'Shina de Cobra', 'Deus · Seiya': 'Seiya de Pégaso', 'Deus · Shiryu': 'Shiryu de Dragão', 'Deus · Hyoga': 'Hyoga de Cisne', 'Deus · Shun': 'Shun de Andrômeda', 'Deus · Ikki': 'Ikki de Fênix', 'Nachi': 'Nachi de Lobo', 'Geki': 'Geki de Urso', 'Ichi': 'Ichi de Hidra', 'Jabu': 'Jabu de Unicórnio', 'Pégasus Negro': 'Pégaso Negro', 'Kanon': 'Kanon de Dragão Marinho', 'Krishna': 'Krishna de Crisaor', 'Sorento': 'Sorento de Sirene', 'Radamanthys': 'Radamanthys de Wyvern', 'Minos': 'Minos de Griffon', 'Sirene': 'Sirene (Escama)', 'Cérbero': 'Cérbero' }; const k = alias[name] || name; const card = D.cards.find(x => x.pt === k); return card ? IMGROOT + card.file : null; };
const groupTitle = { ouro: 'Cavaleiros de Ouro', bronze: 'Cavaleiros de Bronze', prata: 'Cavaleiros de Prata', marina: 'Generais Marinas', espectro: 'Espectros e o Submundo', negro: 'Cavaleiros Negros', outros: 'Outros personagens' };
const shownChars = new Set();
function charEntry(name, stats, bio, extra) {
  c.push(H3(name)); const row = imgRow([{ file: cardOf(name), label: 'Cartão do Álbum' }, { file: portraitOf(name), label: 'Retrato' }].filter(x => x.file), 170, 240); if (row) c.push(row);
  if (stats && stats.length) c.push(P([run(stats.join('  ·  '), { size: 17, color: '595959' })]));
  if (bio) c.push(P(bio)); if (extra) c.push(P([run(extra, { italics: true, size: 19 })]));
}
const order = ['Saori Kido', 'Julian Solo', 'Hades', 'Mu', 'Aldebaran', 'Saga', 'Máscara da Morte', 'Aioria', 'Shaka', 'Dohko', 'Miro', 'Aioros', 'Shura', 'Camus', 'Afrodite', 'Shion', 'Orfeu', 'Marin', 'Shina', 'Deus · Seiya', 'Deus · Shiryu', 'Deus · Hyoga', 'Deus · Shun', 'Deus · Ikki', 'Nachi', 'Geki', 'Ban', 'Ichi', 'Jabu', 'June', 'Pégasus Negro', 'Dragão Negro', 'Cisne Negro', 'Andrômeda Negro', 'Jango', 'Mino', 'Cássios', 'Kiki', 'Shunrei', 'Esmeralda', 'Guilty', 'Kanon', 'Krishna', 'Sorento', 'Thetis', 'Radamanthys', 'Aiacos', 'Minos', 'Pandora'];
c.push(H2('O Álbum do jogo: personagens'));
for (const n of order) { const e = D.pb_chars.find(x => x.name === n); const b = D.bios_common.find(x => x.name === n); if (e || b || cardOf(n)) { charEntry(n, e ? e.stats : [], e ? e.bio : (b ? b.bio : ''), null); shownChars.add(n); } }
c.push(H2('Personagens criados para o jogo'));
c.push(P('Nomes e descrições vêm das missões e das tabelas de NPCs do cliente; os retratos são os que o jogo mostra nas caixas de diálogo.'));
const originals = [
 ['Rodório', 'O primeiro Cavaleiro de Pégaso. Lutou ao lado de Athena numa Guerra Santa anterior, morreu nela e voltou como alma para proteger o selo de Athena quando a fronteira entre os vivos e o Submundo se rompeu. Usa uma réplica da Armadura de Pégaso, tem o corpo feito de chamas e só se lembra em parte da vida passada. Sacrifica-se contra Thanatos para que o herói escape com o sangue de Hades; reaparece no Inferno, no Abismo dos Deuses, para dar ao herói a bênção dos Titãs. O herói carrega o seu sangue.'],
 ['Lei-Hu', 'Discípulo de Dohko expulso de Rozan por ambição, rival e amigo de Shiryu (sua Armadura ocupa o lugar da constelação de Draco no catálogo do jogo). Volta à Vila do Dragão Oculto para o duelo prometido dois anos antes, luta ao lado de Shiryu contra Máscara da Morte, é possuído pelo cosmo maligno de Câncer e sacrifica-se. No Inferno reaparece transformado em morcego pela maldição do Lago de Sangue e ajuda o herói a atravessá-lo.'],
 ['Sher-Khan', 'Exilado do Caminho Esquecido disfarçado de espião, com uma máscara de Amazona para poupar Athena da vergonha. Investiga a conspiração em torno do Grande Mestre, guia o herói ao Penhasco da Pedra Vermelha e à dungeon "Treze anos atrás", e acaba morto por Saga depois de descobrir que Shion foi assassinado.'],
 ['Aiya e Eide', 'Irmãos aspirantes da Terra das Constelações. Eide, o gênio orgulhoso, é assassinado por Cássios na disputa pela Armadura; Aiya leva o corpo ao Cemitério dos Cavaleiros e desaparece em Star Hill. O diário de Eide guia a investigação do herói sobre a fissura do Muro da Guerra Santa e o gás do Submundo.'],
 ['Alex', 'Aspirante do Campo de Treinamento, amigo do herói no Santuário, que se revela um guerreiro do Submundo: rouba o sangue de Hades e é derrotado no Cume da Loucura.'],
 ['Nya e Jaffet', 'Nya é o falso Cavaleiro do Orfanato Filhos das Estrelas que manipula Ichi; o Mestre Jaffet, o "ancião que busca o enigma" de Rozan, ensina o herói a controlar a força negra que corre em suas veias.'],
 ['Li-Yun', 'Curandeiro da Vila do Dragão Oculto, em Rozan. Desenvolve o remédio para os olhos de Shiryu e morre corroído pelo Sekishiki de Máscara da Morte enquanto purifica os aldeões.'],
 ['Colomba, Darius e Augusto', 'Na Estrada Esquecida: Colomba, a menina que acompanha o herói pelos testes das Moiras; Darius, o servo exilado; Augusto, o rei exilado que comanda os Guerreiros das Sombras.'],
 ['Sillas', 'Servo mais leal de Lamech, com uma Armadura Sagrada estilizada; caça os Cavaleiros de Athena em combate honrado. Chefe de campo em vários mapas e no Incidente da Névoa Vermelha ("Silas de Vulcão").'],
 ['Lamech', 'O Deus do Nada, cujo objetivo é consumir toda a existência; preso numa guerra perpétua com Athena, aparece como chefe voador no evento semanal da Névoa Vermelha e na Lacuna do Vazio.'],
 ['Alexer e Natássia', 'Príncipe e princesa do País do Gelo (o clã do Gelo Azul) na Sibéria Oriental. Alexer (a releitura do Alexei dos Guerreiros Azuis) mata o próprio pai, alia-se a Isaac de Kraken para obter o Oricalco e usa a irmã Natássia para quebrar o selo; Natássia é a menina que o herói e Hyoga salvam do gelo.'],
 ['Valquíria', 'Representante de Odin na Terra, contraparte de Hilda de Polaris: uma guerreira que recupera o anel dos Nibelungos em Yggdrasil, reúne os clãs do Norte e do Gelo Azul e toma o Castelo do Graad Azul; ao final é corrompida pelo poder do anel e enfrentada no Santuário de Gelo.'],
 ['Acer e Taylor', 'Na Ilha da Rainha da Morte: Acer, o aspirante que lidera a resistência e veste a máscara de Guilty para selar a ilha; Taylor, o escravo covarde que aprende coragem.'],
 ['Julian (Castelo de Hades)', 'Jovem habitante do Castelo Heinstein cuja irmã foi levada pelos Espectros; guia o herói pela Vila dos Mortos e pela Cidade Füssen até o núcleo do encantamento de Hypnos.'],
 ['Perséfone', 'A Imperatriz do Submundo, esposa de Hades: uma jovem numa Sapuris que lembra a vestimenta do próprio Hades. Guarda a árvore Mokurenji e barra o caminho diante do Templo de Hades nos Campos Elísios.'],
 ['Zeros, Lupin e Luise', 'Zeros de Sapo, o covarde responsável pela Floresta do Crepúsculo; Lupin e sua irmã Luise, as almas de ladrões do Inferno das Serpentes.'],
 ['Kafka, Moe, Larry, Curly, Steven, Stone, Gerald, Isolde', 'Espectros criados pelo jogo (ou nomeados pela localização brasileira) para completar o exército de Hades: as Estrelas Terrestre da Submissão, da Escuridão, da Sombra, da Diferença, do Assassinato, do Brilho, da Prisão e do Mal.'],
 ['Wyrm', 'A classe de Espectro jogável: Estrela Celeste do Prestígio, com uma Sapuris própria (V1 azul-prata, V2 e Divina dourada) distinta da Wyvern de Radamanthys.'],
];
const origPorts = { 'Rodório': ['Rodório'], 'Lei-Hu': ['Lei-Hu', 'Lei-Hu (mutado)'], 'Aiya e Eide': ['Eide', 'Eide (mutado)', 'Aiya'], 'Alex': ['Alex', 'Alex (Sapuris)'], 'Li-Yun': ['Li-Yun'], 'Sillas': ['Sillas'], 'Lamech': ['Lamech'], 'Alexer e Natássia': ['Alexer', 'Natássia'], 'Valquíria': ['Valquíria', 'Valquíria (guerreira)'], 'Acer e Taylor': ['Acer', 'Acer (máscara)'], 'Julian (Castelo de Hades)': ['Julian (Castelo de Hades)'], 'Perséfone': ['Perséfone'], 'Zeros, Lupin e Luise': ['Zeros'], 'Kafka, Moe, Larry, Curly, Steven, Stone, Gerald, Isolde': ['Gerald'], 'Wyrm': [] };
for (const [n, t] of originals) { c.push(H3(n)); const ks = origPorts[n] || []; const row = imgRow(ks.filter(k => D.portraits[k]).map(k => ({ file: IMGROOT + D.portraits[k], label: k })), 120, 120); if (row) c.push(row); else c.push(P([run('(sem retrato próprio: este personagem usa um modelo genérico de NPC e o jogo não desenhou um rosto para ele)', { size: 15, italics: true, color: '7F7F7F' })])); c.push(P(t)); }
c.push(H2('Deuses, Guerreiros Deuses e outros retratos'));
const extraPorts = ['Poseidon', 'Thanatos', 'Hypnos', 'Eurídice', 'Loki', 'Apolo', 'Eros', 'Afrodite (deusa)', 'Siegfried', 'Hagen', 'Alberich', 'Fenrir', 'Syd', 'Mime', 'Sísifo', 'Mitsumasa Kido', 'Seika', 'Isaac', 'Baian', 'Myu', 'Lune', 'Rock', 'Iwan', 'Laimi', 'Io de Skilla', 'Kasa', 'Julian Solo (Poseidon)', 'Sirene (Sorento)', 'Kanon (Sapuris)', 'Seiya (Sagitário)', 'Shina (Armadura)', 'Athena (Armadura Divina)', 'Saori (vestido)', 'Shion (alma)', 'Shion ressuscitado', 'Ikki criança', 'Seiya criança', 'Pandora criança', 'Julian Solo (mendigo)', 'Máscara da Morte ressuscitado', 'Shura ressuscitado', 'Camus ressuscitado', 'Afrodite ressuscitado'].map(k => ({ file: D.portraits[k] ? IMGROOT + D.portraits[k] : null, label: k })).filter(x => x.file);
for (const g of chunk(extraPorts, 6)) { const r = imgRow(g, 120, 120); if (r) c.push(r); }
c.push(PB());
// ---------- armaduras ----------
c.push(H1('Armaduras'));
c.push(P('O Álbum do jogo cataloga as Armaduras de Bronze, Prata, Ouro e Divinas, as Escamas e as Sapuris. Para cada uma mostramos o cartão do Álbum, o render da Armadura da biblioteca de Diego (pasta Cloths, masculino e feminino) e as capturas de tela do personagem de Diego vestindo essa Armadura (pasta Saints). A identificação das capturas foi feita visualmente e pode conter enganos, sobretudo entre as Armaduras de Prata originais do jogo e as versões Sapuris (roxas) das Armaduras de Bronze.'));
const groupsA = [['arm_bronze', 'Armaduras de Bronze'], ['arm_prata', 'Armaduras de Prata'], ['arm_ouro', 'Armaduras de Ouro'], ['arm_divina', 'Armaduras Divinas'], ['escama', 'Escamas'], ['sapuris', 'Sapuris']];
const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
function shotsFor(pt, group) {
  const base = norm(pt.replace(/\s*\(.*\)$/, '')); const out = [];
  for (const [lab, files] of Object.entries(D.shots_by)) { const l = norm(lab); const isSap = l.startsWith('sapuris'), isOuro = l.startsWith('ouro'), isDiv = /divina/.test(l), isNegro = /negro|cavaleiro negro/.test(l);
    const mention = l.includes(base) || (base === 'pegaso' && l.includes('pegasus'));
    if (!mention) continue;
    if (group === 'sapuris' && !isSap) continue; if (group === 'arm_ouro' && !isOuro) continue; if (group === 'arm_divina' && !isDiv) continue;
    if ((group === 'arm_bronze' || group === 'arm_prata') && (isSap || isOuro || isDiv || isNegro)) continue;
    out.push(...files.map(f => ({ ...f, label: lab }))); }
  return out;
}
function rendersFor(pt) { const base = norm(pt.replace(/\s*\(.*\)$/, '')); const out = []; for (const [k, files] of Object.entries(D.renders)) { if (norm(k).startsWith(base)) out.push(...files.map(f => ({ ...f, label: k + ' ' + f.sex }))); } return out; }
for (const [g, title] of groupsA) {
  c.push(H2(title)); const items = D.cards.filter(k => k.group === g);
  for (const k of items) {
    c.push(H3(k.pt)); const t = D.pb_texts[k.pt] || D.pb_texts[k.pt.replace(/ \(.*$/, '')]; if (t) c.push(P(t));
    const r1 = imgRow([{ file: IMGROOT + k.file, label: 'Cartão do Álbum' }, ...rendersFor(k.pt).slice(0, 4).map(x => ({ file: x.file, label: x.label }))], 150, 200); if (r1) c.push(r1);
    const sh = shotsFor(k.pt, g); for (const grp of chunk(sh.slice(0, 12), 6)) { const r = imgRow(grp.map(x => ({ file: x.file, label: x.label + ' (' + x.sex + ')' })), 140, 200); if (r) c.push(r); }
  }
}
c.push(H2('Renders e capturas sem cartão no Álbum'));
const cardPts = new Set(D.cards.map(k => norm(k.pt.replace(/\s*\(.*\)$/, ''))));
const extraR = Object.entries(D.renders).filter(([k]) => ![...cardPts].some(p => norm(k).startsWith(p)));
for (const [k, files] of extraR) { c.push(H3(k)); const r = imgRow(files.map(f => ({ file: f.file, label: f.sex })), 150, 200); if (r) c.push(r); }
c.push(H3('Capturas de tela classificadas como Cavaleiros Negros, Divinas ou não identificadas'));
const leftovers = Object.entries(D.shots_by).filter(([lab]) => /negro|nao identificada|não identificada|divina|variante|prata \(|^prata$|^ouro \(|holog/i.test(lab));
for (const [lab, files] of leftovers) { c.push(P([run(lab, { bold: true })])); for (const grp of chunk(files, 6)) { const r = imgRow(grp.map(x => ({ file: x.file, label: x.sex })), 140, 200); if (r) c.push(r); } }
c.push(H2('As 23 classes de Sapuris (Espectros jogáveis)'));
c.push(P('Tela de seleção de classe do jogo e a correspondência com as Estrelas Malignas, com as correções de Diego para a localização em português (do documento "Surplices - Saint Seiya Online"):'));
c.push(table([1900, 1300, 2600, W - 5800], [['Sapuris / classe', 'Estrela (chinês)', 'Português (localizado)', 'Correção / observação'],
 ['Wyrm', '天威星', 'Estrela Celeste do Prestígio', 'Imagem de referência errada: mostra a Sapuris de Wyvern.'], ['Wyrm Negro', '黑暗天威', 'Prestígio Sombrio Celeste Negro', 'Idem.'], ['Griffon', '天贵星', 'Estrela Celeste Cara', 'Correto: Estrela Celeste da Nobreza (天貴星).'], ['Wyvern', '天猛星', 'Estrela Celeste Feroz', ''], ['Garuda', '天雄星', 'Estrela Celeste do Heroísmo', ''], ['Harpia', '天哭星', 'Estrela Celeste da Lamentação', ''], ['Balron', '天英星', 'Estrela Celeste da Excelência', ''], ['Aqueronte', '天间星', 'Estrela Celeste Entrelaçada', 'Correto: Estrela Celeste do Espaço (天間星).'], ['Mandrágora (Alraune)', '天魔星', 'Estrela Celeste da Bruxaria', 'O nome deveria ser Alraune.'], ['Basilisco', '天捷星', 'Estrela Celeste da Vitória', ''], ['Esfinge', '天曾星', 'Estrela Celeste do Passado', 'Correto: Estrela Celeste da Besta (天獣星).'], ['Minotauro', '天牢星', 'Estrela Celeste da Prisão', ''], ['Lycaon', '天罪星', 'Estrela Celeste do Crime', 'Errado: é o nome da Sapuris de Phlegyas, com elmo do Espectro da Loucura e Sapuris do da Vastidão.'], ['E. Matéria', '物质星', 'Estrela da Matéria', 'Sem classificação Celeste/Terrestre.'], ['E. Ódio', '地恶星', 'Estrela Terrestre do Mal', ''], ['Deep', '地暗星', 'Estrela Terrestre da Escuridão', ''], ['Ciclope', '地暴星', 'Estrela Terrestre Violenta', ''], ['Dullahan', '地明星', 'Estrela Terrestre Brilhante', 'Correto: Estrela Terrestre da Sombra (地陰星); item trocado com o da Prisão na versão PT.'], ['Górgona', '地走星', 'Estrela Terrestre da Corrida', ''], ['E. Prisão', '地囚星', 'Estrela Terrestre da Prisão', 'Ícone trocado com o de Dullahan na versão PT.'], ['Papillon', '地妖星', 'Estrela Terrestre do Encantamento', ''], ['E. Silêncio', '地幽星', 'Estrela Terrestre do Silêncio', ''], ['E. Força', '力量星', 'Estrela da Potência', '']], { size: 15 }));
c.push(H2('Como as Armaduras são obtidas no jogo'));
c.push(P('As missões de obtenção de Armaduras (Artesão de Bronze Joseph, Artesão de Prata Altai, o Álbum de Ouro de Athena e as Sapuris entregues por Pandora), sem repetição:'));
for (const [k, title] of [['bronze', 'Armaduras de Bronze'], ['prata', 'Armaduras de Prata'], ['ouro', 'Armaduras de Ouro'], ['sapuris', 'Sapuris']]) { c.push(H3(title)); const seenN = new Set(); for (const q of D.cloth_quests[k]) { if (seenN.has(q.name)) continue; seenN.add(q.name); c.push(bullet([run(q.name, { bold: true }), run(q.descript ? ' — ' + q.descript.slice(0, 220) : '', { size: 18 })])); } }
c.push(PB());
// ---------- a história ----------
c.push(H1('A história'));
c.push(P('A partir daqui, a missão principal do jogo, saga por saga, com todas as missões na ordem dos arquivos e todas as falas: a descrição da missão (em itálico), o que o NPC diz ao entregá-la ("NPC"), as respostas que o herói pode escolher ("Herói") e o que o NPC diz ao concluí-la ("Ao concluir"). O jogo não guarda o nome de quem fala em cada janela; ele está quase sempre na própria descrição.'));
for (const p of D.parts) {
  c.push(PB()); c.push(H1(p.title)); c.push(P(p.intro));
  for (const s of p.sections) {
    c.push(H2(`${s.title}`)); c.push(P([run(`${s.chapter[0]}, capítulo ${s.chapter[1]}: "${s.chapter[2]}"`, { italics: true, color: '595959', size: 19 })]));
    const ims = imgRow(s.images.map(f => IMGROOT + f), 200, 200); if (ims) c.push(ims);
    c.push(P(s.intro));
    for (const q of s.quests) c.push(...questBlock(q));
    for (const a of s.alts) { c.push(H3(a.title)); for (const q of a.quests) c.push(...questBlock(q, true)); }
  }
}
c.push(PB()); c.push(H1('As histórias dos personagens (Professor Kurumada)'));
c.push(P('Um personagem chamado Professor Kurumada, na Cidade Prata, pede ao herói que investigue a vida de cada Cavaleiro para "servir de inspiração". São trinta e oito histórias curtas, em capítulos numerados, cada uma passada na região do personagem.'));
for (const s of D.char_stories) { c.push(H2('A história de ' + s.character)); const pf = portraitOf(s.character); const im = IMG(pf, 120, 120, false); if (im) c.push(im); for (const q of s.quests) c.push(...questBlock(q, true)); }
c.push(PB()); c.push(H1('Histórias secundárias por região'));
c.push(P('As missões que não pertencem à linha principal: as vilas, os aldeões, os festivais e as dungeons de cada região, na ordem dos arquivos.'));
for (const s of D.side) { c.push(H2(s.title)); const ims = imgRow(s.images.map(f => IMGROOT + f), 200, 200); if (ims) c.push(ims); for (const q of s.quests) c.push(...questBlock(q, true)); }
c.push(PB()); c.push(H1('Apêndice A: diálogos das dungeons das Doze Casas e de outras instâncias'));
c.push(P('Falas roteirizadas dentro das instâncias, com o nome de quem fala quando o arquivo o traz (o nome aparece numa linha própria, junto das falas do personagem; $PLAYER_NAME é o herói). Reproduzidas na ordem do arquivo.'));
for (const line of D.instance_dialogue) { const isName = line.length < 40 && !/[.!?…,]/.test(line) && !/^(Sim|Não)$/.test(line); c.push(P([run(line, { size: 17, bold: isName, color: isName ? '1F3864' : '000000' })], { spacing: { after: isName ? 20 : 40 }, indent: { left: isName ? 0 : 360 } })); }
c.push(PB()); c.push(H1('Apêndice B: cinemáticas e legendas'));
c.push(P('As cinemáticas em motor do jogo (arquivos .anm), pelos títulos internos, e em seguida as legendas das cinemáticas na ordem em que o arquivo de textos as guarda.'));
for (const t of D.cut_titles) c.push(bullet([t]));
c.push(H2('Legendas'));
for (const t of D.subtitles) c.push(P([run(t, { size: 17 })], { spacing: { after: 20 } }));
c.push(PB()); c.push(H1('Apêndice C: títulos do herói'));
c.push(table([2600, 3400, W - 6000], [['Título', 'Descrição', 'Como obter'], ...D.titles.map(t => [t.name, t.desc, t.how])], { size: 15 }));
c.push(PB()); c.push(H1('Apêndice D: outras missões, eventos e desafios'));
c.push(P(`Missões repetíveis, eventos sazonais, desafios, tutoriais e missões de sistema que não entram na narrativa, com seus diálogos. (${D.tests} missões de teste dos desenvolvedores foram deixadas de fora.)`));
for (const b of D.others) { c.push(H2(b.block)); for (const q of b.quests) c.push(...questBlock(q, true)); }
c.push(PB()); c.push(H1('Apêndice F: falas soltas dos NPCs'));
c.push(P('As frases que os NPCs dizem ao serem clicados ou que aparecem em balões durante cinemáticas e eventos (tabela text.data do cliente), sem repetição, na ordem do arquivo.'));
for (const t of D.npc_lines) c.push(P([run(t, { size: 17 })], { spacing: { after: 20 } }));
c.push(PB()); c.push(H1('Apêndice E: cobertura das Notas de Pesquisa'));
c.push(P('Confronto entre o que o documento "Saint Seiya Online - Notas de Pesquisa" e o "Surplices - Saint Seiya Online" citam e o que existe nos arquivos do cliente (tabelas de NPCs, monstros, configurações e missões, em chinês e em português).'));
c.push(table([3000, 900, W - 3900], [['Item das notas', 'No jogo?', 'Onde aparece'], ...D.coverage.map(x => [x.item, x.found ? 'sim' : 'não', x.detail])], { size: 14 }));
c.push(P(`Além disso: ${D.cards.length} dos 165 cartões do Álbum foram identificados; ${Object.keys(D.renders).length} Armaduras da pasta Cloths e ${Object.values(D.shots_by).reduce((a, b) => a + b.length, 0)} capturas da pasta Saints foram associadas a ${Object.keys(D.shots_by).length} rótulos.`));
const doc = new Document({ creator: 'Diego Chagas', title: 'Saint Seiya Online - Story', features: { updateFields: true }, styles: { default: { document: { run: { font: FONT, size: 21 } } } },
  numbering: { config: [{ reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] }] },
  sections: [{ properties: { page: { margin: { top: 1134, bottom: 1134, left: 1417, right: 1417 } } }, footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: '808080' })] })] }) }, children: c.filter(Boolean) }] });
Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUTF, b); console.log('wrote', OUTF, (b.length / 1e6).toFixed(1) + ' MB', 'paragraphs', c.length); });
