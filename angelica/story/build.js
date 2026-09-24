// Saint Seiya Online - Story (pt-BR).  node build.js story.json "OUT.docx"
const fs = require('fs'), path = require('path');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, ImageRun, PageBreak, BorderStyle, LevelFormat, Footer, PageNumber, AlignmentType, TableOfContents } = require('docx');
const D = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')); const OUTDIR = process.argv[3]; fs.mkdirSync(OUTDIR, { recursive: true });
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
let c = []; const docs = [];
const VOLUMES = [['01', 'O jogo e o mundo'], ['02', 'Personagens'], ['03', 'Armaduras'], ['04', 'Galeria de modelos 3D'], ['05', 'Vídeos, músicas, arte conceitual e imprensa'],
  ...D.parts.map((p, i) => [String(6 + i).padStart(2, '0'), 'A história: ' + p.title]), ['10', 'As histórias dos personagens e as histórias secundárias'], ['11', 'Apêndices A, B e C: diálogos das dungeons, cinemáticas e títulos'],
  ['12', 'Apêndice D: outras missões, eventos e desafios'], ['13', 'Apêndices F, G, H e E: falas dos NPCs, missões de teste, duplicadas e Notas de Pesquisa']];
function startDoc(num, title) {
  c = []; docs.push({ num, title, children: c });
  c.push(new Paragraph({ spacing: { before: 1200, after: 100 }, children: [run('Saint Seiya Online - Story', { size: 44, bold: true })] }));
  c.push(new Paragraph({ spacing: { after: 200 }, children: [run(`Volume ${num}: ${title}`, { size: 30, color: '1F3864', bold: true })] }));
  c.push(P([run('A história completa do jogo, ilustrada com as imagens do cliente. O livro está dividido em volumes:', { size: 18, color: '595959' })]));
  for (const [n, t] of VOLUMES) c.push(P([run(`${n} - ${t}`, { size: 17, bold: n === num, color: n === num ? '1F3864' : '595959' })], { spacing: { after: 20 } }));
  c.push(PB());
  c.push(new Paragraph({ spacing: { after: 200 }, children: [run('Sumário', { size: 34, bold: true, color: '1F3864' })] }));
  c.push(P([run('(No Word, clique com o botão direito no sumário abaixo e escolha "Atualizar campo" para ver as páginas.)', { size: 16, italics: true, color: '7F7F7F' })]));
  c.push(new TableOfContents('Sumário', { hyperlink: true, headingStyleRange: '1-2' }));
  c.push(PB());
}
startDoc('01', 'O jogo e o mundo');
// ---------- capa ----------
c.push(H1('Sobre este livro'));
c.push(P('Saint Seiya Online (圣斗士星矢Online) é o MMORPG 3D da Perfect World, licenciado pela Shueisha e supervisionado por Masami Kurumada, lançado na China em 2013 e no Brasil e na América Latina em setembro de 2017 (Ongame / SEGA), em português e espanhol. A versão chinesa encerrou em 2018 e a brasileira em junho de 2020; hoje sobrevive no servidor de fãs Seiya Reborn, de onde vieram os arquivos usados neste livro.'));
c.push(P('Este documento reúne tudo o que o cliente do jogo guarda sobre a história: as quatro sagas da missão principal (Santuário, Poseidon, Hades: Cruzada ao Submundo e Hades: Inferno) com todas as missões e diálogos, as histórias secundárias de cada região, as trinta e oito "histórias" que o Professor Kurumada pede ao herói para investigar, a enciclopédia de personagens e Armaduras do próprio jogo (o Álbum), os mapas, as cinemáticas e os títulos. Os textos são os da localização oficial em português; quando o jogo só tinha tradução automática para um trecho (conteúdo antigo que a versão brasileira nunca revisou), isso está marcado em vermelho e um resumo em português correto precede o trecho.'));
c.push(P('Extraído em 24/09/2026 dos arquivos do cliente (element/data/lang_pt-BR.data, os pacotes .pck e o álbum surfaces/res/photobook). Os renders 3D dos personagens, NPCs e Armaduras foram feitos no Blender a partir dos modelos (.ski) do cliente, em pose T, de frente, de lado e de costas; os arquivos completos estão na pasta "Saint Seiya Online - Galeria de Imagens", organizada como o volume 04.'));
c.push(IMG(D.bg.loading18, 620, 480)); c.push(cap('Tela de carregamento: o Santuário sob o céu estrelado'));
c.push(PB());
// ---------- o mundo ----------
c.push(H1('O mundo do jogo'));
c.push(P('O jogador cria um aspirante a Cavaleiro escolhendo uma de cinco constelações de Bronze (Pégaso, Dragão, Cisne, Andrômeda e Fênix; mais tarde o jogo acrescentou Lira, Tornado e, para as facções de Poseidon e Hades, Dragão Marinho e Wyrm). O mesmo herói pode vestir dezenas de Armaduras de Bronze, Prata e Ouro, Escamas e Sapuris ao longo do jogo. A história segue os arcos do mangá clássico, mas vista pelos olhos desse novo Cavaleiro, que convive com Seiya, Shiryu, Hyoga, Shun e Ikki e carrega um segredo próprio: o sangue de Rodório, o primeiro Cavaleiro de Pégaso.'));
c.push(H2('As regiões'));
const placeCards = D.cards.filter(k => k.group === 'lugar');
for (const k of placeCards) { c.push(H3(`${k.pt} (${k.zh})`)); const t = D.pb_texts[({ 'Terra das Constelações': 'T. das Constel.', 'Santuário': 'Santuário', 'Coliseu Graad': 'Coliseu Graad', 'Rozan': 'Rozan', 'Estrada Esquecida': 'Estr. Esquecida', 'Ilha da Rainha da Morte': 'I. da R. da Morte', 'Sibéria Oriental': 'Sibéria Orie.', 'Atlântida': 'Atlântida', 'Ilha de Andrômeda': 'Ilha de Andrôm.', 'Castelo de Hades': 'Cast. de Hades', 'Submundo': 'Submundo' })[k.pt]]; if (t) c.push(P(t)); const row = imgRow([{ file: IMGROOT + k.file, label: 'Cartão do Álbum' }, ...(({ 'Terra das Constelações': 'n1', 'Santuário': 'n2', 'Coliseu Graad': 'n4', 'Rozan': 'n3', 'Estrada Esquecida': 'n5', 'Ilha da Rainha da Morte': 'n6', 'Sibéria Oriental': 'n7', 'Atlântida': 'n8', 'Ilha de Andrômeda': 'n9', 'Castelo de Hades': 'n10', 'Submundo': 'n11' })[k.pt] ? [{ file: D.worldmaps[({ 'Terra das Constelações': 'n1', 'Santuário': 'n2', 'Coliseu Graad': 'n4', 'Rozan': 'n3', 'Estrada Esquecida': 'n5', 'Ilha da Rainha da Morte': 'n6', 'Sibéria Oriental': 'n7', 'Atlântida': 'n8', 'Ilha de Andrômeda': 'n9', 'Castelo de Hades': 'n10', 'Submundo': 'n11' })[k.pt]], label: 'Mapa da região' }] : [])], 240, 260); if (row) c.push(row); }
c.push(H2('Mapas e instâncias'));
c.push(P('Todos os mapas definidos no cliente (script/map/instance.lua), com o código interno usado nos arquivos e o nome oficial em português:'));
const seen = new Set(); const maprows = [['Código', 'Nome (pt-BR)', 'Nome original']];
for (const m of D.maps) { const k = m.map_code + '|' + m.name_pt; if (!m.map_code || seen.has(k)) continue; seen.add(k); maprows.push([m.map_code, m.name_pt || m.name_en, m.name_zh]); }
c.push(table([1200, 4400, W - 5600], maprows, { size: 15 }));
c.push(H2('Telas de carregamento e a linha do tempo das sagas'));
c.push(P('A missão principal está dividida em 22 capítulos. O jogo entrega um título ao herói ao fim de cada um:'));
c.push(table([3200, 900, W - 4100], [['Saga', 'Cap.', 'Título do capítulo'], ...D.parts.flatMap(p => p.sections.map(s => [s.chapter[0], s.chapter[1], s.chapter[2]])).filter((r, i, a) => a.findIndex(x => x.join() === r.join()) === i)], { size: 17 }));
const loads = ['loading01', 'loading02', 'loading05', 'loading06', 'loading08', 'loading10', 'loading12', 'loading13', 'loading14', 'loading16'].map(n => D.bg[n]);
for (const g of chunk(loads, 2)) { const r = imgRow(g, 300, 240); if (r) c.push(r); }
c.push(cap('Telas de carregamento do jogo'));
c.push(H2('Os quadrinhos das telas de carregamento'));
c.push(P('Oito telas de carregamento reproduzem páginas de quadrinhos com os momentos clássicos da série; o Álbum do jogo também tem uma seção "Quadrinhos" (Volume I e II).'));
for (let i = 1; i <= 8; i++) { const f = D.bg['loading_comic_0' + i]; const im = IMG(f, 600, 480); if (im) { c.push(im); c.push(cap(`Quadrinhos da tela de carregamento ${i}`)); } }
startDoc('02', 'Personagens');
// ---------- personagens ----------
c.push(H1('Personagens'));
c.push(P('As fichas abaixo são as do Álbum do próprio jogo (a seção "Personagens" da enciclopédia), com a ilustração do cartão, o retrato usado nos diálogos quando existe, e os dados e o texto oficiais em português. Em seguida vêm os personagens criados para o jogo, que não existem no mangá.'));
const portraitOf = (name) => { const map = { 'Saori Kido': 'Saori Kido', 'Julian Solo': 'Julian Solo', 'Máscara da Morte': null, 'Deus · Seiya': 'Seiya', 'Deus · Shiryu': 'Shiryu', 'Deus · Hyoga': 'Hyoga', 'Deus · Shun': 'Shun', 'Deus · Ikki': 'Ikki', 'Pégasus Negro': 'Pégaso Negro', 'Mino': null, 'Sorento': 'Sorento', 'Grande Mestre': 'Grande Mestre' }; const k = map[name] === undefined ? name : map[name]; return k && D.portraits[k] ? IMGROOT + D.portraits[k] : null; };
const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const cardFor = (name) => { const alias = { 'Saori Kido': 'Athena (Saori Kido)', 'Julian Solo': 'Julian Solo (Poseidon)', 'Mu': 'Mu de Áries', 'Aldebaran': 'Aldebaran de Touro', 'Saga': 'Saga de Gêmeos', 'Máscara da Morte': 'Máscara da Morte de Câncer', 'Aioria': 'Aioria de Leão', 'Shaka': 'Shaka de Virgem', 'Dohko': 'Dohko de Libra', 'Miro': 'Miro de Escorpião', 'Aioros': 'Aioros de Sagitário', 'Shura': 'Shura de Capricórnio', 'Camus': 'Camus de Aquário', 'Afrodite': 'Afrodite de Peixes', 'Orfeu': 'Orfeu de Lira', 'Marin': 'Marin de Águia', 'Shina': 'Shina de Cobra', 'Deus · Seiya': 'Seiya de Pégaso', 'Deus · Shiryu': 'Shiryu de Dragão', 'Deus · Hyoga': 'Hyoga de Cisne', 'Deus · Shun': 'Shun de Andrômeda', 'Deus · Ikki': 'Ikki de Fênix', 'Nachi': 'Nachi de Lobo', 'Geki': 'Geki de Urso', 'Ichi': 'Ichi de Hidra', 'Jabu': 'Jabu de Unicórnio', 'Pégasus Negro': 'Pégaso Negro', 'Kanon': 'Kanon de Dragão Marinho', 'Krishna': 'Krishna de Crisaor', 'Sorento': 'Sorento de Sirene', 'Radamanthys': 'Radamanthys de Wyvern', 'Minos': 'Minos de Griffon', 'Sirene': 'Sirene (Escama)', 'Cérbero': 'Cérbero' }; const k = alias[name] || name; return D.cards.find(x => x.pt === k) || null; };
const cardOf = (name) => { const card = cardFor(name); return card ? IMGROOT + card.file : null; };
const groupTitle = { ouro: 'Cavaleiros de Ouro', bronze: 'Cavaleiros de Bronze', prata: 'Cavaleiros de Prata', marina: 'Generais Marinas', espectro: 'Espectros e o Submundo', negro: 'Cavaleiros Negros', outros: 'Outros personagens' };
const G = D.gallery || [];
const playerSets = G.filter(x => x.kind === 'render' && x.category === 'player');
const npcRendersAll = G.filter(x => x.kind === 'render' && x.category === 'npc');
const VIEW_PT = { front: 'frente', side: 'lado', back: 'costas' };
const shownChars = new Set();
const CHAR_ZH = { 'Saori Kido': ['城户纱织', '城户沙织', '婴儿沙织', '雅典娜神圣衣'], 'Julian Solo': ['朱利安'], 'Hades': ['冥王哈迪斯'], 'Mu': ['白羊座穆'], 'Aldebaran': ['阿鲁迪巴', '黄金圣斗士金牛座'], 'Saga': ['撒加'], 'Máscara da Morte': ['迪斯马斯克'], 'Aioria': ['艾欧里亚'], 'Shaka': ['沙加'], 'Dohko': ['童虎'], 'Miro': ['米罗'], 'Aioros': ['艾欧罗斯', '射手座便装'], 'Shura': ['修罗'], 'Camus': ['卡妙'], 'Afrodite': ['阿布罗狄'], 'Shion': ['史昂'], 'Orfeu': ['奥路菲', '天琴座神圣衣'], 'Marin': ['魔铃'], 'Shina': ['莎尔娜'], 'Deus · Seiya': ['星矢'], 'Deus · Shiryu': ['紫龙'], 'Deus · Hyoga': ['冰河'], 'Deus · Shun': ['瞬'], 'Deus · Ikki': ['一辉'], 'Nachi': ['那智'], 'Geki': ['檄'], 'Ban': ['幼狮座蛮'], 'Ichi': ['水蛇座市'], 'Jabu': ['邪武'], 'June': ['珍妮'], 'Pégasus Negro': ['黑暗天马'], 'Dragão Negro': ['黑暗天龙'], 'Cisne Negro': ['黑暗白鸟'], 'Andrômeda Negro': ['黑暗仙女'], 'Jango': ['强戈'], 'Mino': ['美惠'], 'Cássios': ['卡西欧士'], 'Kiki': ['贵鬼'], 'Shunrei': ['春丽'], 'Esmeralda': ['艾丝美拉达'], 'Guilty': ['基鲁提'], 'Kanon': ['加隆'], 'Krishna': ['克修拉'], 'Sorento': ['苏兰特', '海魔女鳞衣'], 'Thetis': ['美人鱼'], 'Radamanthys': ['拉达曼提斯'], 'Aiacos': ['艾亚哥斯', '天雄星'], 'Minos': ['米洛斯', '天贵星'], 'Pandora': ['潘多拉'],
  'Rodório': ['初代天马英灵'], 'Lei-Hu': ['雷虎'], 'Sher-Khan': ['希尔汗'], 'Aiya e Eide': ['艾德', '艾亚'], 'Alex': ['阿历克斯'], 'Nya e Jaffet': ['尼亚', '云峰'], 'Li-Yun': ['李云'], 'Colomba, Darius e Augusto': ['高龙巴', '奥古斯塔', '达里乌斯'], 'Sillas': ['撒里诺'], 'Lamech': ['拉蒙斯'], 'Alexer e Natássia': ['亚雷库萨', '娜塔莎'], 'Valquíria': ['瓦尔基里'], 'Acer e Taylor': ['学员枫', '泰勒'], 'Julian (Castelo de Hades)': ['尤里安'], 'Perséfone': ['冥后'], 'Zeros, Lupin e Luise': ['赛洛斯', '鲁邦', '鲁琪'], 'Kafka, Moe, Larry, Curly, Steven, Stone, Gerald, Isolde': ['地伏星', '天暗星', '天阴星', '天异星', '天杀星', '地明星', '地囚星', '地恶星'], 'Wyrm': ['天威星'],
  'Poseidon': ['波塞冬'], 'Thanatos': ['死神'], 'Hypnos': ['睡神'], 'Eurídice': ['尤丽缇丝'], 'Loki': ['洛基'], 'Apolo': ['阿波罗'], 'Eros': ['爱洛斯'], 'Afrodite (deusa)': ['阿芙洛狄忒'], 'Siegfried': ['齐格弗里德'], 'Hagen': ['哈根'], 'Alberich': ['阿鲁贝利亚'], 'Fenrir': ['菲利路'], 'Syd': ['希度'], 'Mime': ['米伊美'], 'Mitsumasa Kido': ['城户光政'], 'Seika': ['星华'], 'Isaac': ['艾尔扎克'], 'Baian': ['拜安'], 'Myu': ['地妖星缪'], 'Lune': ['路尼'], 'Rock': ['洛克'], 'Iwan': ['伊万'], 'Laimi': ['莱米'], 'Io de Skilla': ['六圣兽'], 'Kasa': ['北海巨妖'], 'Julian Solo (Poseidon)': ['海皇波塞冬'], 'Sirene (Sorento)': ['苏兰特便装'] };
const NPC_SKIP = ['翅膀', '锁链', '雕像', '雪人'];
const normN = s => norm(s || '').replace(/[^a-z0-9]+/g, '');
const jobItem = new Map(npcRendersAll.map(x => [x.job, x]));
const npcByPt = new Map(); for (const m of (D.npc_models || [])) { const k = normN(m.pt); if (!npcByPt.has(k)) npcByPt.set(k, []); npcByPt.get(k).push(m); }
const SITE_ALIAS = { 'orphee': 'Orfeu', 'rodorio': 'Rodório', 'ohko': 'Lei-Hu', 'persephone': 'Perséfone', 'valkyrie': 'Valquíria', 'lamech god of the nothing': 'Lamech', 'ares mars': 'Ares', 'aphrodite': 'Afrodite', 'alicia mii benethol': 'Mii', 'the trio of darkness 3': 'Trio das Trevas', 'noesis': 'Noesis', 'yulij': 'Yulij' };
function npcModelsFor(label) { if (!label) return []; const al = SITE_ALIAS[norm(label).replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim()]; if (al) label = al; const parts = label.replace(/\(.*?\)/g, '').split(/,| e |\/|·/).map(s => s.trim()).filter(Boolean); const out = []; for (const p of parts) for (const m of (npcByPt.get(normN(p)) || [])) if (!out.some(x => x.job === m.job)) out.push(m); return out; }
function zhFor(label) { const card = cardFor(label); if (card && card.zh) return card.zh; const zs = [...new Set(npcModelsFor(label).map(m => m.zh))].filter(z => z && z.length <= 14); return zs.slice(0, 3).join(' / '); }
const zhTag = label => { const z = zhFor(label); return z ? ` (${z})` : ''; };
function npcRenders(keys, max = 8) { if (!keys || !keys.length) return []; const out = []; for (const it of npcRendersAll) { if (NPC_SKIP.some(k => it.zh.includes(k))) continue; if (keys.some(k => it.zh.includes(k))) out.push(it); } return out.slice(0, max); }
function rendersFor(label, keys, max = 8) { const items = npcRenders(keys || [], max); for (const m of npcModelsFor(label)) { const it = jobItem.get(m.job); if (it && !items.includes(it) && !NPC_SKIP.some(k => it.zh.includes(k))) items.push(it); } return items.slice(0, max); }
function renderRows(items, maxW = 130, maxH = 190) { const files = []; items.forEach((it, i) => { const views = i === 0 ? ['front', 'side', 'back'] : ['front']; for (const v of views) if (it.files[v]) files.push({ file: it.files[v], label: it.pt + (v === 'front' ? '' : ' (' + VIEW_PT[v] + ')') }); }); return chunk(files, 6).map(g => imgRow(g, maxW, maxH)).filter(Boolean); }
function charEntry(name, stats, bio, extra) {
  c.push(H3(name + zhTag(name))); const row = imgRow([{ file: cardOf(name), label: 'Cartão do Álbum' }, { file: portraitOf(name), label: 'Retrato' }].filter(x => x.file), 170, 240); if (row) c.push(row);
  c.push(...renderRows(rendersFor(name, CHAR_ZH[name])));
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
for (const [n, t] of originals) { c.push(H3(n + zhTag(n))); const ks = origPorts[n] || []; const row = imgRow(ks.filter(k => D.portraits[k]).map(k => ({ file: IMGROOT + D.portraits[k], label: k })), 120, 120); const rr = renderRows(rendersFor(n, CHAR_ZH[n])); if (row) c.push(row); else if (!rr.length) c.push(P([run('(sem retrato nem modelo próprio: este personagem usa um modelo genérico de NPC e o jogo não desenhou um rosto para ele)', { size: 15, italics: true, color: '7F7F7F' })])); else c.push(P([run('(sem retrato próprio: o jogo não desenhou um rosto para as caixas de diálogo; abaixo, o modelo 3D)', { size: 15, italics: true, color: '7F7F7F' })])); c.push(...rr); c.push(P(t)); }
c.push(H2('Deuses, Guerreiros Deuses e outros retratos'));
const extraPorts = ['Poseidon', 'Thanatos', 'Hypnos', 'Eurídice', 'Loki', 'Apolo', 'Eros', 'Afrodite (deusa)', 'Siegfried', 'Hagen', 'Alberich', 'Fenrir', 'Syd', 'Mime', 'Sísifo', 'Mitsumasa Kido', 'Seika', 'Isaac', 'Baian', 'Myu', 'Lune', 'Rock', 'Iwan', 'Laimi', 'Io de Skilla', 'Kasa', 'Julian Solo (Poseidon)', 'Sirene (Sorento)', 'Kanon (Sapuris)', 'Seiya (Sagitário)', 'Shina (Armadura)', 'Athena (Armadura Divina)', 'Saori (vestido)', 'Shion (alma)', 'Shion ressuscitado', 'Ikki criança', 'Seiya criança', 'Pandora criança', 'Julian Solo (mendigo)', 'Máscara da Morte ressuscitado', 'Shura ressuscitado', 'Camus ressuscitado', 'Afrodite ressuscitado'].map(k => ({ file: D.portraits[k] ? IMGROOT + D.portraits[k] : null, label: k })).filter(x => x.file);
for (const g of chunk(extraPorts, 6)) { const r = imgRow(g, 120, 120); if (r) c.push(r); }
c.push(H3('Modelos 3D dos deuses, Guerreiros Deuses e outros'));
for (const k of extraPorts.map(x => x.label)) { const rs = rendersFor(k, CHAR_ZH[k], 4); if (!rs.length) continue; c.push(P([run(k + zhTag(k), { bold: true, size: 19 })], { spacing: { before: 100, after: 40 }, keepNext: true })); c.push(...renderRows(rs)); }
// ---------- personagens do site Saint Seiya Cloths ----------
c.push(H2('Personagens e Armaduras do jogo no site Saint Seiya Cloths'));
c.push(P('O site saintseiyacloths.diegochagas.com (seção History, "Saint Seiya Online") lista os personagens e as Armaduras que a enciclopédia de Diego associa ao jogo. Para cada entrada: o nome no site, o NPC correspondente nos arquivos do cliente (nome em português e em chinês) com o seu modelo 3D, e os conjuntos jogáveis da mesma constelação; a miniatura à esquerda é o esquema do próprio site. Entradas sem NPC no jogo são as que o site cataloga apenas pela Armadura.'));
const SITE_ROOT = D.site_root || '';
const siteGroups = new Map(); for (const ss of (D.site_saints || [])) { const g = ss.group_pt || ss.group; if (!siteGroups.has(g)) siteGroups.set(g, []); siteGroups.get(g).push(ss); }
for (const [g, list] of siteGroups) {
  c.push(H3(g));
  for (const ss of list) {
    const label = [ss.character, ss.cloth].filter(Boolean).join(' - ') || '(sem nome)';
    const ms = npcModelsFor(ss.character || ''); const zh = [...new Set(ms.map(m => m.zh))].slice(0, 3).join(' / ');
    c.push(P([run(label, { bold: true, size: 20 }), run(zh ? `  ·  no jogo: ${[...new Set(ms.map(m => m.pt))].slice(0, 2).join(' / ')} (${zh})` : '  ·  sem NPC com este nome nos arquivos do cliente', { size: 16, color: '595959' })], { spacing: { before: 140, after: 40 }, keepNext: true }));
    if (ss.curiosity) c.push(P([run(ss.curiosity, { size: 17, italics: true })]));
    const files = []; if (ss.image && SITE_ROOT) files.push({ file: SITE_ROOT + ss.image, label: 'esquema do site' });
    const rs = rendersFor(ss.character || '', [], 5); rs.forEach((it, i) => { for (const v of (i === 0 ? ['front', 'side', 'back'] : ['front'])) if (it.files[v]) files.push({ file: it.files[v], label: it.pt + (v === 'front' ? '' : ' (' + VIEW_PT[v] + ')') }); });
    for (const grp of chunk(files, 6)) { const r = imgRow(grp, 130, 190); if (r) c.push(r); }
    const libImgs = (D.gallery || []).filter(x => x.kind === 'concept-art' && x.site_key && [ss.character, ss.cloth, ss.group_pt].some(v => v && norm(v).includes(norm(x.site_key)))); for (const grp of chunk(libImgs, 3)) { const r = imgRow(grp.map(x => ({ file: x.files.image, label: x.pt })), 200, 200); if (r) c.push(r); }
    if (ss.cloth) { const isHades = /hades|estrela|ressuscit|espectro/i.test(ss.group + ' ' + (ss.group_pt || '')); const sets = playerSets.filter(x => norm(x.en).includes(norm(ss.cloth)) && (isHades || !x.zh.includes('冥'))); const bySetM = bySet(sets); let n = 0; for (const [zhs, its] of bySetM) { if (n++ >= 4) break; const f2 = []; for (const sex of ['male', 'female']) { const it = its.find(x => x.sex === sex); if (it && it.files.front) f2.push({ file: it.files.front, label: it.pt + ' (' + (sex === 'male' ? 'masc.' : 'fem.') + ') ' + zhs }); } const r = imgRow(f2, 130, 190); if (r) c.push(r); } }
  }
}
startDoc('03', 'Armaduras');
// ---------- armaduras ----------
c.push(H1('Armaduras'));
c.push(P('O Álbum do jogo cataloga as Armaduras de Bronze, Prata, Ouro e Divinas, as Escamas e as Sapuris. Para cada uma mostramos o cartão do Álbum e os renders 3D dos conjuntos que o jogador veste no jogo (modelos .ski do cliente renderizados no Blender em pose T: frente, lado e costas, nas versões masculina e feminina). Os nomes são a tradução do nome interno de cada conjunto; "nível 1" e "nível 2" são as versões V1 e V2 do jogo, "dourada" a variante de ouro.'));
const groupsA = [['arm_bronze', 'Armaduras de Bronze'], ['arm_prata', 'Armaduras de Prata'], ['arm_ouro', 'Armaduras de Ouro'], ['arm_divina', 'Armaduras Divinas'], ['escama', 'Escamas'], ['sapuris', 'Sapuris']];
function setsFor(card) {
  const zh = card.zh, g = card.group; let key = zh;
  if (g === 'arm_ouro') key = zh.replace('圣衣', ''); else if (g === 'arm_divina') key = zh.replace(/^神/, ''); else if (g === 'escama') key = zh.replace(/座$/, '');
  const base = key.replace(/座$/, '');
  return playerSets.filter(s => { const n = s.zh; if (!n.includes(base)) return false;
    if (g === 'arm_bronze') return !n.includes('冥') && !n.includes('黑暗') && !n.includes('神圣衣') && !n.includes('白银');
    if (g === 'arm_prata') return !n.includes('冥') && !n.includes('黑暗');
    if (g === 'arm_ouro') return n === base + '座' || n === base + '初始装';
    if (g === 'arm_divina') return n.includes('神圣衣') && !n.includes('冥');
    if (g === 'escama') return n.includes('海斗士') || n.includes('鳞衣') || n.includes('海龙');
    if (g === 'sapuris') return n.includes('冥');
    return false; });
}
function bySet(items) { const m = new Map(); for (const it of items) { if (!m.has(it.zh)) m.set(it.zh, []); m.get(it.zh).push(it); } return m; }
function setRows(items) { // one row per cloth set: male front/side/back + female front/side/back
  const out = [];
  for (const [zh, its] of bySet(items)) {
    out.push(P([run(its[0].pt, { bold: true, size: 19 }), run('  ' + zh, { size: 14, color: '7F7F7F' })], { spacing: { before: 120, after: 40 }, keepNext: true }));
    const files = [];
    for (const sex of ['male', 'female']) { const it = its.find(x => x.sex === sex); if (!it) continue; for (const v of ['front', 'side', 'back']) if (it.files[v]) files.push({ file: it.files[v], label: (sex === 'male' ? 'masc. ' : 'fem. ') + VIEW_PT[v] }); }
    const r = imgRow(files, 140, 200); if (r) out.push(r);
  }
  return out;
}
const usedSets = new Set();
for (const [g, title] of groupsA) {
  c.push(H2(title)); const items = D.cards.filter(k => k.group === g);
  for (const k of items) {
    c.push(H3(`${k.pt} (${k.zh})`)); const t = D.pb_texts[k.pt] || D.pb_texts[k.pt.replace(/ \(.*$/, '')]; if (t) c.push(P(t));
    const r1 = imgRow([{ file: IMGROOT + k.file, label: 'Cartão do Álbum' }], 150, 200); if (r1) c.push(r1);
    const sets = setsFor(k); sets.forEach(x => usedSets.add(x.zh)); c.push(...setRows(sets));
  }
}
c.push(H2('Conjuntos jogáveis sem cartão no Álbum'));
c.push(P('Os demais conjuntos de Armadura, Escama e Sapuris que existem nos arquivos do cliente (equipamentos iniciais, roupas de treino, versões de transição, Armaduras de Prata sem cartão, as Sapuris das classes jogáveis, os servos de Lamech e conjuntos de eventos).'));
c.push(...setRows(playerSets.filter(x => !usedSets.has(x.zh))));
c.push(H2('As 23 classes de Sapuris (Espectros jogáveis)'));
c.push(P('Tela de seleção de classe do jogo e a correspondência com as Estrelas Malignas, com as correções de Diego para a localização em português (do documento "Surplices - Saint Seiya Online"):'));
c.push(table([1900, 1300, 2600, W - 5800], [['Sapuris / classe', 'Estrela (chinês)', 'Português (localizado)', 'Correção / observação'],
 ['Wyrm', '天威星', 'Estrela Celeste do Prestígio', 'Imagem de referência errada: mostra a Sapuris de Wyvern.'], ['Wyrm Negro', '黑暗天威', 'Prestígio Sombrio Celeste Negro', 'Idem.'], ['Griffon', '天贵星', 'Estrela Celeste Cara', 'Correto: Estrela Celeste da Nobreza (天貴星).'], ['Wyvern', '天猛星', 'Estrela Celeste Feroz', ''], ['Garuda', '天雄星', 'Estrela Celeste do Heroísmo', ''], ['Harpia', '天哭星', 'Estrela Celeste da Lamentação', ''], ['Balron', '天英星', 'Estrela Celeste da Excelência', ''], ['Aqueronte', '天间星', 'Estrela Celeste Entrelaçada', 'Correto: Estrela Celeste do Espaço (天間星).'], ['Mandrágora (Alraune)', '天魔星', 'Estrela Celeste da Bruxaria', 'O nome deveria ser Alraune.'], ['Basilisco', '天捷星', 'Estrela Celeste da Vitória', ''], ['Esfinge', '天曾星', 'Estrela Celeste do Passado', 'Correto: Estrela Celeste da Besta (天獣星).'], ['Minotauro', '天牢星', 'Estrela Celeste da Prisão', ''], ['Lycaon', '天罪星', 'Estrela Celeste do Crime', 'Errado: é o nome da Sapuris de Phlegyas, com elmo do Espectro da Loucura e Sapuris do da Vastidão.'], ['E. Matéria', '物质星', 'Estrela da Matéria', 'Sem classificação Celeste/Terrestre.'], ['E. Ódio', '地恶星', 'Estrela Terrestre do Mal', ''], ['Deep', '地暗星', 'Estrela Terrestre da Escuridão', ''], ['Ciclope', '地暴星', 'Estrela Terrestre Violenta', ''], ['Dullahan', '地明星', 'Estrela Terrestre Brilhante', 'Correto: Estrela Terrestre da Sombra (地陰星); item trocado com o da Prisão na versão PT.'], ['Górgona', '地走星', 'Estrela Terrestre da Corrida', ''], ['E. Prisão', '地囚星', 'Estrela Terrestre da Prisão', 'Ícone trocado com o de Dullahan na versão PT.'], ['Papillon', '地妖星', 'Estrela Terrestre do Encantamento', ''], ['E. Silêncio', '地幽星', 'Estrela Terrestre do Silêncio', ''], ['E. Força', '力量星', 'Estrela da Potência', '']], { size: 15 }));
c.push(H2('Como as Armaduras são obtidas no jogo'));
c.push(P('As missões de obtenção de Armaduras (Artesão de Bronze Joseph, Artesão de Prata Altai, o Álbum de Ouro de Athena e as Sapuris entregues por Pandora):'));
c.push(P([run('Todas as missões de obtenção, com descrição e diálogos completos (as repetidas para cada constelação aparecem uma a uma, na ordem dos arquivos).', { italics: true, size: 19 })]));
for (const [k, title] of [['bronze', 'Armaduras de Bronze'], ['prata', 'Armaduras de Prata'], ['ouro', 'Armaduras de Ouro'], ['sapuris', 'Sapuris']]) { c.push(H3(title)); for (const q of D.cloth_quests[k]) c.push(...questBlock(q, true)); }
startDoc('04', 'Galeria de modelos 3D'); c.push(H1('Galeria de modelos 3D'));
c.push(P('Todos os modelos da pasta models/npcs do cliente (personagens, NPCs, monstros, pets, relíquias, efeitos de habilidades, cenários e objetos das cinemáticas), renderizados de frente em pose T. Os arquivos completos (frente, lado e costas, 1000 px) estão na pasta "Saint Seiya Online - Galeria de Imagens", com os mesmos títulos de seção deste volume; a legenda é a tradução do nome interno em chinês (nomes entre parênteses ou em pinyin quando o jogo não dá um nome).'));
for (const [folder, title] of Object.entries(D.gallery_folders || {})) { const items = npcRendersAll.filter(x => (x.folder_key || x.folder) === folder); if (!items.length) continue; c.push(H2(`${title} (${items.length} modelos)`)); for (const g of chunk(items, 6)) { const r = imgRow(g.map(x => ({ file: x.files.front_thumb || x.files.front, label: x.pt + (x.zh ? ' · ' + x.zh : '') })), 110, 150); if (r) c.push(r); } }
// ---------- mídia ----------
startDoc('05', 'Vídeos, músicas, arte conceitual e imprensa');
const G2 = D.gallery || []; const fmtDur = s => { s = Math.round(s || 0); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
c.push(H1('Vídeos do jogo'));
c.push(P('Os vinte vídeos que o cliente traz na pasta videos (formato MP4, H.264): a abertura em duas versões, o logotipo, a introdução "A última Guerra Santa", sete vídeos de apresentação de classe (a classe de cada um foi identificada pelos quadros do vídeo, por isso "provável") e oito lutas da história em estilo de quadrinhos. As cópias estão na pasta "Vídeos" da galeria, com o quadro mostrado abaixo tirado de cada um.'));
for (const v of G2.filter(x => x.kind === 'video')) { c.push(P([run(v.pt, { bold: true, size: 20 }), run(`  ${v.zh ? '(' + v.zh + ')  ' : ''}${fmtDur(v.seconds)} · ${v.width}×${v.height} · ${v.source}`, { size: 16, color: '595959' })], { spacing: { before: 140, after: 40 }, keepNext: true })); const im = IMG(v.files.frame, 420, 260, false); if (im) c.push(im); }
c.push(H1('Músicas'));
c.push(P('As 129 faixas de trilha sonora do cliente (pasta music, Ogg Vorbis), com o nome original do arquivo, a tradução quando o nome é chinês e a duração. As cópias estão na pasta "Músicas" da galeria.'));
c.push(table([3600, 2400, 900, W - 6900], [['Faixa (pt)', 'Nome original', 'Duração', 'Arquivo na galeria'], ...G2.filter(x => x.kind === 'music').map(m => [m.pt, m.zh || m.en, fmtDur(m.seconds), m.files.audio.split('/').pop()])], { size: 14 }));
c.push(H1('Vozes'));
c.push(P('Os gritos de técnica do herói (pasta voice: 女b, voz feminina; 男a, voz masculina) e as falas dubladas dos chefes (packages/sfx/boss配音), agrupadas pelo personagem indicado no nome do arquivo.'));
c.push(H2('Técnicas do herói'));
c.push(table([4200, 3000, W - 7200], [['Técnica (pt)', 'Nome original', 'Duração'], ...G2.filter(x => x.kind === 'voice').map(m => [m.pt, m.zh, fmtDur(m.seconds)])], { size: 14 }));
c.push(H2('Falas dos chefes'));
c.push(table([3200, 3200, W - 6400], [['Personagem (pt)', 'Nome no arquivo', 'Arquivos'], ...(D.boss_voices || []).map(b => [b.pt || '', b.zh, b.files.length + ' (' + b.files.slice(0, 3).join(', ') + (b.files.length > 3 ? '...' : '') + ')'])], { size: 14 }));
c.push(H1('Arte conceitual e material oficial'));
c.push(P('As três folhas de arte conceitual (圣衣设定, "xzsds") guardadas na biblioteca Saint Seiya Cloth Schemes vêm do site oficial chinês seiya.wanmei.com; a identificação abaixo foi feita comparando cada desenho com os modelos 3D do jogo. Em seguida, o que a Wayback Machine guardou das galerias do site oficial (arte original, papéis de parede e capturas de tela). Tudo está na pasta "Arte conceitual oficial" da galeria.'));
for (const a of G2.filter(x => x.kind === 'concept-art')) { const im = IMG(a.files.image, 620, 460); if (!im) continue; c.push(im); c.push(cap(a.pt + (a.note ? ' — ' + a.note : ''))); }
c.push(H1('A cobertura do CavZodiaco.com.br'));
c.push(P('O site brasileiro CavZodiaco.com.br acompanhou o jogo de 2008 (anúncio da SEGA) a 2020 (encerramento no Brasil). Abaixo, cada matéria encontrada na busca do site por "saint seiya online", em ordem cronológica, com um resumo meu e as imagens que a matéria publicou (as imagens estão na pasta "Imprensa (CavZodiaco)" da galeria, uma subpasta por matéria; o texto integral fica no site, no endereço indicado).'));
for (const a of G2.filter(x => x.kind === 'press')) { c.push(H3(`${a.date} · ${a.pt}`)); const note = (D.press_notes || {})[a.date]; if (note) c.push(P([run(note, { size: 18 })])); c.push(P([run(a.url, { size: 14, color: '7F7F7F' })])); for (const g of chunk(a.files.thumbs || a.files.images || [], 5)) { const r = imgRow(g.map(f => ({ file: f })), 150, 130); if (r) c.push(r); } }
c.push(H1('A galeria "Saint Seiya Online" de Cerberus-rack (DeviantArt)'));
c.push(P('O artista Cerberus-rack mantém no DeviantArt uma galeria com 62 desenhos dos personagens e Armaduras do jogo, feitos enquanto o jogava, com observações sobre nomes, estrelas e criaturas que o jogo revela. Como são obras do artista, as imagens ficam no DeviantArt (endereço em cada item); abaixo, o título, a data e um resumo meu de cada descrição, em ordem cronológica.'));
for (const d of [...(D.deviantart || [])].sort((a, b) => new Date(a.date) - new Date(b.date))) { const id = (d.url.match(/-(\d+)$/) || [])[1]; const note = (D.da_notes || {})[id]; c.push(P([run(d.title, { bold: true, size: 19 }), run('  ' + new Date(d.date).toISOString().slice(0, 10), { size: 15, color: '7F7F7F' })], { spacing: { before: 100, after: 20 }, keepNext: true })); if (note) c.push(P([run(note, { size: 18 })], { spacing: { after: 20 } })); c.push(P([run(d.url, { size: 14, color: '7F7F7F' })])); }
// ---------- a história ----------
let partNo = 0;
const historiaIntro = 'A partir daqui, a missão principal do jogo, saga por saga, com todas as missões na ordem dos arquivos e todas as falas: a descrição da missão (em itálico), o que o NPC diz ao entregá-la ("NPC"), as respostas que o herói pode escolher ("Herói") e o que o NPC diz ao concluí-la ("Ao concluir"). O jogo não guarda o nome de quem fala em cada janela; ele está quase sempre na própria fala ou no nome da missão. Missões cujo texto em português é a tradução automática do cliente estão marcadas em vermelho.';
for (const p of D.parts) {
  startDoc(String(6 + partNo).padStart(2, '0'), 'A história: ' + p.title); partNo++;
  c.push(H1('A história')); c.push(P(historiaIntro));
  c.push(H1(p.title)); c.push(P(p.intro));
  for (const s of p.sections) {
    c.push(H2(`${s.title}`)); c.push(P([run(`${s.chapter[0]}, capítulo ${s.chapter[1]}: "${s.chapter[2]}"`, { italics: true, color: '595959', size: 19 })]));
    const ims = imgRow(s.images.map(f => IMGROOT + f), 200, 200); if (ims) c.push(ims);
    c.push(P(s.intro));
    for (const q of s.quests) c.push(...questBlock(q));
    for (const a of s.alts) { c.push(H3(a.title)); for (const q of a.quests) c.push(...questBlock(q, true)); }
  }
}
startDoc('10', 'As histórias dos personagens e as histórias secundárias'); c.push(H1('As histórias dos personagens (Professor Kurumada)'));
c.push(P('Um personagem chamado Professor Kurumada, na Cidade Prata, pede ao herói que investigue a vida de cada Cavaleiro para "servir de inspiração". São trinta e oito histórias curtas, em capítulos numerados, cada uma passada na região do personagem.'));
for (const s of D.char_stories) { c.push(H2('A história de ' + s.character)); const pf = portraitOf(s.character); const im = IMG(pf, 120, 120, false); if (im) c.push(im); for (const q of s.quests) c.push(...questBlock(q, true)); }
c.push(PB()); c.push(H1('Histórias secundárias por região'));
c.push(P('As missões que não pertencem à linha principal: as vilas, os aldeões, os festivais e as dungeons de cada região, na ordem dos arquivos.'));
for (const s of D.side) { c.push(H2(s.title)); const ims = imgRow(s.images.map(f => IMGROOT + f), 200, 200); if (ims) c.push(ims); for (const q of s.quests) c.push(...questBlock(q, true)); }
startDoc('11', 'Apêndices A, B e C: diálogos das dungeons, cinemáticas e títulos'); c.push(H1('Apêndice A: diálogos das dungeons das Doze Casas e de outras instâncias'));
c.push(P('Falas roteirizadas dentro das instâncias, com o nome de quem fala quando o arquivo o traz (o nome aparece numa linha própria, junto das falas do personagem; $PLAYER_NAME é o herói). Reproduzidas na ordem do arquivo.'));
for (const line of D.instance_dialogue) { const isName = line.length < 40 && !/[.!?…,]/.test(line) && !/^(Sim|Não)$/.test(line); c.push(P([run(line, { size: 17, bold: isName, color: isName ? '1F3864' : '000000' })], { spacing: { after: isName ? 20 : 40 }, indent: { left: isName ? 0 : 360 } })); }
c.push(PB()); c.push(H1('Apêndice B: cinemáticas e legendas'));
c.push(P('As cinemáticas em motor do jogo (arquivos .anm), pelos títulos internos, e em seguida as legendas das cinemáticas na ordem em que o arquivo de textos as guarda.'));
for (const t of D.cut_titles) c.push(bullet([t]));
c.push(H2('Legendas'));
for (const t of D.subtitles) c.push(P([run(t, { size: 17 })], { spacing: { after: 20 } }));
c.push(PB()); c.push(H1('Apêndice C: títulos do herói'));
c.push(table([2600, 3400, W - 6000], [['Título', 'Descrição', 'Como obter'], ...D.titles.map(t => [t.name, t.desc, t.how])], { size: 15 }));
startDoc('12', 'Apêndice D: outras missões, eventos e desafios'); c.push(H1('Apêndice D: outras missões, eventos e desafios'));
c.push(P(`Missões repetíveis, eventos sazonais, desafios, tutoriais e missões de sistema que não entram na narrativa, todas com descrição e diálogos completos, agrupadas por faixa de id. As etapas sem descrição e sem falas aparecem só pelo nome ("etapa da missão"). As ${D.tests} missões de teste dos desenvolvedores estão no Apêndice G.`));
for (const b of D.others) { c.push(H2(b.block)); for (const q of b.quests) c.push(...questBlock(q, true)); }
startDoc('13', 'Apêndices F, G, H e E: falas dos NPCs, missões de teste, duplicadas e Notas de Pesquisa'); c.push(H1('Apêndice F: falas soltas dos NPCs'));
c.push(P('As frases que os NPCs dizem ao serem clicados ou que aparecem em balões durante cinemáticas e eventos (tabela text.data do cliente), sem repetição, na ordem do arquivo.'));
for (const t of D.npc_lines) c.push(P([run(t, { size: 17 })], { spacing: { after: 20 } }));
c.push(PB()); c.push(H1('Apêndice G: missões de teste dos desenvolvedores'));
c.push(P(`O cliente ainda traz ${D.tests} missões que a equipe da Perfect World usou para testar o motor de missões e nunca foram oferecidas aos jogadores: nomes como "Quest de teste", "Testar Quest", "Subquest", "Teste de arco", "Teste de QTE", "Continuação 1/2", "Opção 1/2", "Sem o item", "Liu Chunfeng" (o nome de um desenvolvedor), "Que de Armazém", ou versões alternativas de dungeons ("Doze Casas de Ouro Divinas - Versão ..."). Servem para ver como o sistema funciona: sub-missões encadeadas, ramificações por escolha do jogador (as "opções"), pré-requisitos de item, entregas ao armazém, QTE (sequências de teclas) e testes de tradução. Muitas reaproveitam falas de missões reais ou trazem texto de preenchimento; a tradução em português é a do próprio cliente (muitas vezes automática). Estão aqui na íntegra, na ordem dos arquivos, para que nenhuma linha do jogo fique de fora.`));
for (const b of D.tests_q) { c.push(H2(b.block)); for (const q of b.quests) c.push(...questBlock(q, true)); }
c.push(P([run(`Cobertura: ${D.stats.quests_in_doc} das ${D.stats.quests_total} missões do cliente estão neste documento com texto completo; as outras ${D.stats.duplicates_dropped} são cópias exatas de uma missão já incluída (mesmo nome, descrição e falas) e estão listadas no Apêndice H; ${D.stats.windows_in_doc} das ${D.stats.windows_total} janelas de diálogo têm o texto reproduzido, as restantes são as dessas cópias.`, { size: 17, italics: true })]));
c.push(PB()); c.push(H1('Apêndice H: missões duplicadas'));
c.push(P('O cliente repete muitas missões com ids diferentes e texto idêntico (por exemplo, a mesma etapa oferecida a cada facção ou a cada classe). Para não repetir páginas inteiras, cada cópia aparece aqui apenas com o id, o nome e o id da missão original cujo texto ela reproduz.'));
c.push(table([1300, W - 3900, 2600], [['Missão', 'Nome', 'Cópia exata da missão'], ...D.duplicates.map(d => [String(d.id), d.name || '(sem nome)', String(d.of)])], { size: 14 }));
c.push(PB()); c.push(H1('Apêndice E: cobertura das Notas de Pesquisa'));
c.push(P('Confronto entre o que o documento "Saint Seiya Online - Notas de Pesquisa" e o "Surplices - Saint Seiya Online" citam e o que existe nos arquivos do cliente (tabelas de NPCs, monstros, configurações e missões, em chinês e em português).'));
c.push(table([3000, 900, W - 3900], [['Item das notas', 'No jogo?', 'Onde aparece'], ...D.coverage.map(x => [x.item, x.found ? 'sim' : 'não', x.detail])], { size: 14 }));
c.push(P(`Além disso: ${D.cards.length} dos 165 cartões do Álbum foram identificados; ${new Set(playerSets.map(x => x.zh)).size} conjuntos jogáveis (Armaduras, Escamas e Sapuris) e ${npcRendersAll.length} modelos de NPC foram renderizados em 3D a partir dos arquivos do cliente.`));
const mkDoc = (children) => new Document({ creator: 'Diego Chagas', title: 'Saint Seiya Online - Story', features: { updateFields: true }, styles: { default: { document: { run: { font: FONT, size: 21 } } } },
  numbering: { config: [{ reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] }] },
  sections: [{ properties: { page: { margin: { top: 1134, bottom: 1134, left: 1417, right: 1417 } } }, footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: '808080' })] })] }) }, children: children.filter(Boolean) }] });
(async () => {
  for (const d of docs) {
    const name = `${d.num} - ${d.title.replace(/[\/:*?"<>|]/g, '-')}.docx`;
    const b = await Packer.toBuffer(mkDoc(d.children));
    fs.writeFileSync(path.join(OUTDIR, name), b);
    console.log('wrote', name, (b.length / 1e6).toFixed(1) + ' MB', 'paragraphs', d.children.length);
  }
})();
