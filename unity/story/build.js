// Saint Seiya Rebirth - story book (pt-BR).  node build.js story_book.json OUT_DIR
// One .docx per volume; docx-odt-convert turns them into .odt with a page-numbered table of contents.
const fs = require('fs'), path = require('path');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ImageRun, PageBreak, BorderStyle, Footer, PageNumber, AlignmentType, TableOfContents } = require('docx');
const D = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')); const OUTDIR = process.argv[3]; fs.mkdirSync(OUTDIR, { recursive: true });
const BOOK = D.title, FONT = 'Calibri', CFONT = 'Noto Sans CJK SC', W = 9026;
const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, noBorders = { top: none, bottom: none, left: none, right: none };
const run = (t, o = {}) => new TextRun({ text: String(t == null ? '' : t), font: FONT, size: 21, ...o });
const zh = (t, o = {}) => new TextRun({ text: String(t == null ? '' : t), font: { name: CFONT, eastAsia: CFONT }, size: 15, color: '7F7F7F', ...o });
const P = (t, o = {}) => new Paragraph({ spacing: { after: 100 }, ...o, children: (Array.isArray(t) ? t : [t]).map(x => typeof x === 'string' ? run(x, { size: o.size || 21, italics: o.italics, color: o.color }) : x) });
const H1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun({ text: t, font: FONT })] });
const H2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [new TextRun({ text: t, font: FONT })] });
const H3 = t => new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, children: [new TextRun({ text: t, font: FONT })] });
const PB = () => new Paragraph({ children: [new PageBreak()] });
function imgSize(file) { try { const b = fs.readFileSync(file); if (b.slice(1, 4).toString() === 'PNG') return [b.readUInt32BE(16), b.readUInt32BE(20)]; } catch (e) {} return [400, 300]; }
function picture(file, maxW, maxH) { const [w0, h0] = imgSize(file); const s = Math.min(maxW / w0, maxH / h0, 1.0); return new ImageRun({ type: 'png', data: fs.readFileSync(file), transformation: { width: Math.max(8, Math.round(w0 * s)), height: Math.max(8, Math.round(h0 * s)) } }); }
function IMG(file, maxW = 600, maxH = 420, o = {}) { if (!file || !fs.existsSync(file)) return null; return new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 80, after: 40 }, ...o, children: [picture(file, maxW, maxH)] }); }
function imgRow(files, maxW = 150, maxH = 170) {
  const list = files.filter(f => f && f.file && fs.existsSync(f.file)); if (!list.length) return null;
  const cw = Math.floor(W / list.length);
  const cells = list.map(f => new TableCell({ borders: noBorders, width: { size: cw, type: WidthType.DXA }, children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [picture(f.file, Math.min(maxW, cw / 15 - 6), maxH)] }), ...(f.label ? [P([run(f.label, { size: 15, color: '595959' })], { alignment: AlignmentType.CENTER, spacing: { after: 60 } })] : [])] }));
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: list.map(() => cw), rows: [new TableRow({ cantSplit: true, children: cells })] });
}
const SPEAKER_COLOURS = ['1F3864', '833C0B', '375623', '7030A0', '806000', '1F4E79', 'C00000', '3A3A3A'];
function dialogue(lines) {
  const out = []; const colour = {}; let next = 0;
  for (const l of lines) {
    const who = l.speaker || '—';
    if (!(who in colour)) colour[who] = SPEAKER_COLOURS[next++ % SPEAKER_COLOURS.length];
    out.push(new Paragraph({ spacing: { after: 10 }, indent: { left: 360, hanging: 360 }, keepNext: true, children: [run(who + ': ', { bold: true, color: colour[who], size: 20 }), run(l.pt, { size: 20 })] }));
    out.push(new Paragraph({ spacing: { after: 90 }, indent: { left: 360 }, children: [zh(l.zh)] }));
  }
  return out;
}
const WHEN = { before: 'Antes da batalha', after: 'Depois da batalha', during: 'Durante a batalha' };

function volumeDoc(vol) {
  const c = [];
  c.push(new Paragraph({ spacing: { before: 1200, after: 100 }, children: [run(BOOK, { size: 44, bold: true })] }));
  c.push(new Paragraph({ spacing: { after: 60 }, children: [zh(D.title_zh, { size: 26, color: '595959' })] }));
  c.push(new Paragraph({ spacing: { after: 200 }, children: [run(`Volume ${vol.num}: ${vol.title}`, { size: 30, color: '1F3864', bold: true })] }));
  if (D.cover) c.push(IMG(D.cover, 520, 300));
  c.push(P([run('A campanha do jogo chinês Saint Seiya Rebirth em português, com todas as falas dos personagens, as descrições das fases e os personagens tal como aparecem no jogo. O texto original em chinês aparece em cinza abaixo de cada fala.', { size: 18, color: '595959' })]));
  for (const v of D.volumes) c.push(P([run(`${v.num} - ${v.title}`, { size: 17, bold: v.num === vol.num, color: v.num === vol.num ? '1F3864' : '595959' })], { spacing: { after: 20 } }));
  c.push(PB());
  c.push(new Paragraph({ spacing: { after: 200 }, children: [run('Sumário', { size: 34, bold: true, color: '1F3864' })] }));
  c.push(new TableOfContents('Sumário', { hyperlink: true, headingStyleRange: '1-2' }));
  for (const ch of vol.chapters) {
    c.push(H1(ch.name));
    c.push(P([zh(ch.name_zh, { size: 18 })], { spacing: { after: 120 } }));
    const pics = imgRow([{ file: ch.icon, label: '' }, { file: ch.show_role, label: '' }].filter(p => p.file), 300, 220);
    if (pics) c.push(pics);
    if (ch.desc) { c.push(P(ch.desc, { italics: true })); c.push(P([zh(ch.desc_zh)])); }
    const seen = new Set();
    for (const lv of ch.levels) {
      c.push(H2(lv.name));
      if (lv.desc) { c.push(P(lv.desc)); c.push(P([zh(lv.desc_zh)], { spacing: { after: 140 } })); }
      if (lv.boss && lv.boss.length) c.push(P([run('Chefe: ' + lv.boss.join(', '), { size: 17, color: '595959' })]));
      for (const s of lv.stories) {
        // the puppets of the speakers that first appear in this chapter, once each
        const fresh = [];
        for (const l of s.lines) { const sp = D.speakers[l.sid]; if (sp && sp.pic && !seen.has(l.sid)) { seen.add(l.sid); fresh.push({ file: sp.pic, label: sp.pt || sp.zh }); } }
        for (let i = 0; i < fresh.length; i += 5) { const r = imgRow(fresh.slice(i, i + 5), 150, 170); if (r) c.push(r); }
        c.push(H3((s.title && s.title !== lv.name ? s.title + ' — ' : '') + WHEN[s.when]));
        c.push(...dialogue(s.lines));
      }
    }
  }
  return new Document({
    styles: { default: { document: { run: { font: FONT, size: 21 } } },
      paragraphStyles: [
        { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 32, bold: true, color: '1F3864', font: FONT }, paragraph: { spacing: { before: 240, after: 120 } } },
        { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 26, bold: true, color: '2E75B6', font: FONT }, paragraph: { spacing: { before: 240, after: 100 } } },
        { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 21, bold: true, color: '595959', font: FONT }, paragraph: { spacing: { before: 160, after: 60 } } }] },
    features: { updateFields: true },
    sections: [{ properties: { page: { margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [run(`${BOOK} - Volume ${vol.num}   `, { size: 15, color: '7F7F7F' }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 15, color: '7F7F7F' })] })] }) },
      children: c }] });
}

(async () => {
  for (const vol of D.volumes) {
    const doc = volumeDoc(vol);
    const file = path.join(OUTDIR, `${BOOK} - Volume ${vol.num} - ${vol.title.replace(/[\\/:*?"<>|]/g, '').replace(/ \(.*\)$/, '')}.docx`);
    fs.writeFileSync(file, await Packer.toBuffer(doc));
    console.log('wrote', file);
  }
})();
