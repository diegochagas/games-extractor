const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType,
  ShadingType, AlignmentType, ImageRun, PageBreak, TableOfContents, Footer, PageNumber,
  BorderStyle, LevelFormat, PageOrientation, Header,
} = require('docx');

// usage: node build.js OUT.docx [game short name]  (no name = all games in one document)
const only = process.argv[3];
const data = JSON.parse(fs.readFileSync('data.json', 'utf8')).filter(g => !only || g.short === only);
if (!data.length) { console.error('unknown game: ' + only); process.exit(1); }
const single = data.length === 1;
const notes = JSON.parse(fs.readFileSync('notes.json', 'utf8'));
const FONT = 'Calibri';
const W = 9026;                       // A4 content width with 1" margins
const border = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' };
const borders = { top: border, bottom: border, left: border, right: border };
const noBorders = { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE },
  left: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE } };

const p = (text, o = {}) => new Paragraph({ spacing: { after: 100 }, ...o,
  children: (Array.isArray(text) ? text : [text]).map(t => typeof t === 'string' ? new TextRun({ text: t, font: FONT, size: o.size || 21 }) : t) });
const mono = (t, size = 18) => new TextRun({ text: t, font: 'Consolas', size });
const bold = (t, size = 21) => new TextRun({ text: t, font: FONT, bold: true, size });
const h1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT })] });
const h2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] });
const bullet = (children) => new Paragraph({ numbering: { reference: 'bul', level: 0 }, spacing: { after: 60 },
  children: children.map(t => typeof t === 'string' ? new TextRun({ text: t, font: FONT, size: 21 }) : t) });

function table(cols, rows, { head = true, size = 18, fill = 'DCE6F1' } = {}) {
  const mk = (cells, isHead) => new TableRow({ tableHeader: isHead, cantSplit: true, children: cells.map((c, i) =>
    new TableCell({ borders, width: { size: cols[i], type: WidthType.DXA },
      shading: isHead ? { fill, type: ShadingType.CLEAR, color: 'auto' } : undefined,
      margins: { top: 40, bottom: 40, left: 80, right: 80 },
      children: [new Paragraph({ children: [c instanceof TextRun ? c :
        new TextRun({ text: String(c), font: FONT, size, bold: isHead })] })] })) });
  const all = head ? [mk(rows[0], true), ...rows.slice(1).map(r => mk(r, false))] : rows.map(r => mk(r, false));
  return new Table({ width: { size: cols.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: cols, rows: all });
}

const TYPE = { picture: 'Picture', sprite: 'Sprite frame', tilesheet: 'Tile sheet' };
const count = (items, f) => items.filter(f).length;

const children = [];
// ---------- cover ----------
children.push(new Paragraph({ spacing: { before: 2400, after: 200 }, children: [new TextRun({ text: single ? `Digimon ${data[0].short}` : 'Digimon WonderSwan games', font: FONT, size: 52, bold: true })] }));
children.push(new Paragraph({ spacing: { after: 600 }, children: [new TextRun({ text: 'Image index: where every extracted image is, and what it is', font: FONT, size: 30, color: '404040' })] }));
children.push(p('Generated on 2026-09-19 from the asset dumps made by wonderswan-romhack (dump.py). Every image listed here is a PNG on disk, extracted read-only from the original ROMs.'));
children.push(p((single ? 'Game: ' : 'Games covered: ') + data.map(g => g.folder.split('/').pop()).join(', ') + '.'));
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: 'Contents', font: FONT, size: 34, bold: true, color: '1F3864' })] }));
for (const line of ['How to read this document: folders, file names, image types', 'Summary: image counts per game',
  ...data.map(g => `${g.short}: folders, cutscenes and story art, images per bank, gallery of every full-screen picture`),
  ...data.map(g => `Appendix: every image of ${g.short} (path, size, ROM offset, tiles, palette)`)])
  children.push(bullet([line]));
children.push(new Paragraph({ children: [new PageBreak()] }));

// ---------- how to read ----------
children.push(h1('How to read this document'));
children.push(h2('Where the files are'));
children.push(p(single ? 'All images are under the images folder of this game\'s dump folder, one sub-folder per ROM bank:' : 'Each game has its own dump folder in Downloads. All images are under its images folder, one sub-folder per ROM bank:'));
for (const g of data) children.push(bullet([bold(g.short + ': '), mono(g.folder + '/images/', 17)]));
children.push(p('Every image folder also has a _fullscreen_overview.png contact sheet (all full-screen pictures with their labels) and a manifest.json with the raw data of every block in every bank.', { spacing: { before: 120, after: 100 } }));
children.push(h2('File names'));
children.push(p([ 'Files are named ', mono('<offset>_<type>...png'), '. The offset is where the image data starts inside its bank (hexadecimal), so ', mono('bank12/0B18_picture_224x144.png'), ' is a 224x144 picture whose tile data starts at offset 0x0B18 of ROM bank 12, which is file offset 0x0C0B18 in the ROM (bank x 0x10000 + offset).' ]));
children.push(h2('Image types'));
children.push(table([2200, W - 2200], [
  ['Type', 'What it is'],
  ['Picture', 'A complete screen or window: tiles + tilemap + palette assembled exactly as the game shows it. Full-screen ones (at least 208x128) are backgrounds, title screens and cutscene art.'],
  ['Sprite frame', 'One animation frame of a character or Digimon, assembled from its list of 8x8 pieces.'],
  ['Tile sheet', 'Raw tiles whose layout is not assembled (mostly battle effects). All pixels are there, arranged 16 tiles per row in a grey palette.'],
], { size: 19 }));
children.push(p('The PNGs are indexed-colour images whose palette slots equal the in-game colour indexes. Keep the palette when editing, so an edited image can later be put back into the ROM.', { spacing: { before: 120 } }));

// ---------- summary ----------
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1('Summary'));
const sumRows = [['Game', 'System', 'Pictures', 'Full-screen', 'Sprite frames', 'Tile sheets', 'Total']];
for (const g of data) {
  const it = g.items;
  sumRows.push([g.short, g.system, count(it, i => i.type === 'picture'), count(it, i => i.full), count(it, i => i.type === 'sprite'), count(it, i => i.type === 'tilesheet'), it.length]);
}
const tot = k => data.reduce((a, g) => a + count(g.items, k), 0);
if (!single) sumRows.push(['All four', '', tot(i => i.type === 'picture'), tot(i => i.full), tot(i => i.type === 'sprite'), tot(i => i.type === 'tilesheet'), tot(() => true)]);
children.push(p('Full-screen pictures are a subset of pictures.', { size: 18 }));
children.push(table([1900, 1900, 1000, 1150, 1150, 1000, 926], sumRows, { size: 19 }));

// ---------- per game ----------
for (const g of data) {
  const it = g.items;
  children.push(new Paragraph({ children: [new PageBreak()] }));
  children.push(h1(g.short));
  children.push(table([2000, W - 2000], [
    ['Dump folder', mono(g.folder, 16)],
    ['Images', mono(g.folder + '/images/', 16)],
    ['Contact sheet', mono(g.folder + '/images/_fullscreen_overview.png', 16)],
    ['Patched ROM', mono(g.rom, 16)],
    ['System', g.system],
    ['Images', `${it.length} (${count(it, i => i.type === 'picture')} pictures, ${count(it, i => i.type === 'sprite')} sprite frames, ${count(it, i => i.type === 'tilesheet')} tile sheets)`],
  ], { head: false, size: 18 }));

  children.push(h2('Cutscenes and story art'));
  for (const [where, what] of notes[g.short].cutscenes) children.push(bullet([bold(where + ': '), what]));

  // bank table
  children.push(h2('Images per bank'));
  const banks = [...new Set(it.map(i => i.bank))].sort((a, b) => a - b);
  const rows = [['Folder', 'Pictures', 'Full-screen', 'Sprites', 'Tile sheets', 'Picture sizes']];
  for (const b of banks) {
    const bi = it.filter(i => i.bank === b);
    const sizes = {};
    bi.filter(i => i.type === 'picture').forEach(i => { const k = `${i.w}x${i.h}`; sizes[k] = (sizes[k] || 0) + 1; });
    const top = Object.entries(sizes).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, n]) => `${k} (${n})`).join(', ');
    rows.push([`images/bank${String(b).padStart(2, '0')}`, count(bi, i => i.type === 'picture'), count(bi, i => i.full), count(bi, i => i.type === 'sprite'), count(bi, i => i.type === 'tilesheet'), top || '-']);
  }
  children.push(table([1700, 1000, 1150, 950, 1100, W - 5900], rows, { size: 17 }));

  // gallery of full-screen pictures
  const full = it.filter(i => i.full);
  children.push(new Paragraph({ children: [new PageBreak()] }));
  children.push(h2(`Full-screen pictures (${full.length})`));
  children.push(p('Every full-screen picture, in bank order. The label is the path inside the images folder.', { size: 19 }));
  const COLS = 4, cw = Math.floor(W / COLS);
  const grows = [];
  for (let r = 0; r < full.length; r += COLS) {
    const cells = [];
    for (let c = 0; c < COLS; c++) {
      const i = full[r + c];
      if (!i) { cells.push(new TableCell({ borders: noBorders, width: { size: cw, type: WidthType.DXA }, children: [new Paragraph('')] })); continue; }
      const img = fs.readFileSync(i.thumb);
      const tw = 132, th = Math.round(132 * i.h / i.w);
      cells.push(new TableCell({ borders: noBorders, width: { size: cw, type: WidthType.DXA }, margins: { top: 60, bottom: 60, left: 40, right: 40 },
        children: [
          new Paragraph({ alignment: AlignmentType.CENTER, children: [new ImageRun({ type: 'png', data: img, transformation: { width: tw, height: th } })] }),
          new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: `bank${String(i.bank).padStart(2, '0')}/${i.file}`, font: 'Consolas', size: 13 })] }),
        ] }));
    }
    grows.push(new TableRow({ cantSplit: true, children: cells }));
  }
  children.push(new Table({ width: { size: cw * COLS, type: WidthType.DXA }, columnWidths: Array(COLS).fill(cw), rows: grows }));
}

// ---------- appendix: full index ----------
for (const g of data) {
  children.push(new Paragraph({ children: [new PageBreak()] }));
  children.push(h1(`Appendix: every image - ${g.short}`));
  children.push(p([ 'Paths are relative to ', mono(g.folder + '/', 15), '. ROM offset is where the tile data starts in the ROM file. Tiles: bits per pixel, tile count, and whether the data is LZSS-compressed in the ROM.' ], { size: 18 }));
  const rows = [['Path', 'Type', 'Size', 'ROM offset', 'Tiles', 'Map / layout', 'Palette']];
  for (const i of g.items) {
    const tiles = i.bpp ? `${i.bpp}bpp x${i.ntiles}${i.compressed ? ' LZ' : ''}` : '';
    rows.push([i.rel, TYPE[i.type], `${i.w}x${i.h}`, i.rom_offset, tiles, i.tilemap || i.layout || '-', i.palette || '-']);
  }
  children.push(table([3400, 1050, 850, 1000, 1000, 900, 826], rows, { size: 14 }));
}

const doc = new Document({
  creator: 'wonderswan-romhack', title: single ? `Digimon ${data[0].short} - image index` : 'Digimon WonderSwan games - image index',
  styles: {
    default: { document: { run: { font: FONT, size: 21 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 34, bold: true, font: FONT, color: '1F3864' }, paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, font: FONT, color: '2E74B5' }, paragraph: { spacing: { before: 220, after: 120 }, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [{ reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [
      new TextRun({ text: (single ? `Digimon ${data[0].short}` : 'Digimon WonderSwan') + ' image index  -  page ', font: FONT, size: 16, color: '808080' }),
      new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: '808080' })] })] }) },
    children,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(process.argv[2], b); console.log('wrote', process.argv[2], b.length); });
