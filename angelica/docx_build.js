const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, ImageRun, PageBreak, BorderStyle, LevelFormat, Footer, PageNumber, AlignmentType } = require('docx');
const D = JSON.parse(fs.readFileSync('data.json', 'utf8'));
const FONT = 'Calibri', W = 9026;
const border = { style: BorderStyle.SINGLE, size: 4, color: 'BFBFBF' }, borders = { top: border, bottom: border, left: border, right: border };
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: 21, ...o });
const p = (t, o = {}) => new Paragraph({ spacing: { after: 100 }, ...o, children: (Array.isArray(t) ? t : [t]).map(x => typeof x === 'string' ? run(x, { size: o.size || 21 }) : x) });
const mono = (t, size = 17) => new TextRun({ text: t, font: 'Consolas', size });
const bold = (t) => run(t, { bold: true });
const h1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text: t, font: FONT })] });
const h2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] });
const bullet = (c) => new Paragraph({ numbering: { reference: 'bul', level: 0 }, spacing: { after: 60 }, children: c.map(x => typeof x === 'string' ? run(x) : x) });
const pb = () => new Paragraph({ children: [new PageBreak()] });
function table(cols, rows, { head = true, size = 18 } = {}) {
  const mk = (cells, isHead) => new TableRow({ tableHeader: isHead, cantSplit: true, children: cells.map((c, i) => new TableCell({ borders, width: { size: cols[i], type: WidthType.DXA },
    shading: isHead ? { fill: 'DCE6F1', type: ShadingType.CLEAR, color: 'auto' } : undefined, margins: { top: 30, bottom: 30, left: 70, right: 70 },
    children: [new Paragraph({ children: [c instanceof TextRun ? c : new TextRun({ text: String(c), font: FONT, size, bold: isHead })] })] })) });
  return new Table({ width: { size: cols.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: cols, rows: head ? [mk(rows[0], true), ...rows.slice(1).map(r => mk(r, false))] : rows.map(r => mk(r, false)) });
}
const img = (file, cols, rws, cell) => { const w = Math.min(cols * cell, 620), h = Math.round(w * rws / cols); return new Paragraph({ spacing: { after: 60 }, children: [new ImageRun({ type: 'jpg', data: fs.readFileSync(file), transformation: { width: w, height: h } })] }); };
const n = x => x.toLocaleString('en-US');
const c = [];
c.push(new Paragraph({ spacing: { before: 2400, after: 200 }, children: [run('Saint Seiya Online', { size: 52, bold: true })] }));
c.push(new Paragraph({ spacing: { after: 600 }, children: [run('Image index: where every extracted image is, and what it is', { size: 30, color: '404040' })] }));
c.push(p(`Generated on 2026-09-24 from the Seiya Reborn client (Perfect World's Saint Seiya Online, Angelica engine) extracted read-only into ${D.out}. Every image listed here is a PNG on disk; the original .dds/.tga files stay untouched under packages/.`));
c.push(p([bold('Totals: '), `${n(D.total)} images converted from the 15 .pck archives + ${n(D.icons)} UI icons split from the icon atlases.`]));
c.push(pb());
c.push(h1('How to read this document'));
c.push(h2('Where the files are'));
c.push(bullet([bold('PNG images: '), mono(D.out + '/images/<archive>/<path inside the archive>.png')]));
c.push(bullet([bold('Original files: '), mono(D.out + '/packages/<archive>/<path>'), ' (dds/tga/bmp/jpg exactly as stored in the .pck)']));
c.push(bullet([bold('Browseable index: '), mono(D.out + '/images/index.html'), ' (thumbnails of every folder, click-through to the PNG)']));
c.push(bullet([bold('Contact sheets: '), mono(D.out + '/images/_sheets/'), ' (main folders, labelled)']));
c.push(bullet([bold('Icons: '), mono(D.out + '/images/icons/<atlas>/<name>.png'), ' with ', mono('icons/index.csv')]));
c.push(bullet([bold('Table of every image: '), mono(D.out + '/images/manifest.csv'), ' (source, format, size, mip-maps, PNG size)']));
c.push(h2('File names'));
c.push(p(['Paths are the archive paths of the game. ', mono('images/surfaces/res/portrait/穆.dds.png'), ' is the file ', mono('surfaces/res/portrait/穆.dds'), ' inside ', mono('surfaces.pck'), '. Many names are Chinese (the client was made in China): the folder table below gives an English label for each main folder, and text/lang/ holds the game\'s own translations of every in-game name.']));
c.push(h2('Image kinds'));
c.push(table([2300, W - 2300], [['Kind', 'What it is'],
  ['UI surface (surfaces, flash)', '2D interface art: loading screens, portraits, photobook cards, world maps, buttons and panels. Ready to look at.'],
  ['Icon (images/icons)', '56x56 (or smaller) item/skill/state/portrait icons cut out of the iconlist atlases, named as the game names them.'],
  ['Model texture (models, building, litmodels, grasses)', 'Skins wrapped on 3D meshes (characters, Cloths, buildings, scenery). They look like unfolded surfaces, not pictures; the 3D meshes themselves (.bmd/.ecm/.ski) are extracted but not converted.'],
  ['Effect texture (gfx)', 'Particles, trails, runes, sprite sequences used by skill effects.'],
  ['Terrain / sky (textures, maps, loddata)', 'Ground detail textures, sky boxes and aerial LOD views of each map.']], { size: 18 }));
c.push(p('DDS textures were decoded from DXT1/DXT3/DXT5 or raw RGB(A); only the top mip level is kept. PNGs keep the alpha channel.', { spacing: { before: 120 } }));
c.push(pb());
c.push(h1('Summary per archive'));
c.push(table([1700, 3900, 1100, 1200, W - 7900], [['Archive', 'What', 'Images', '≥1000x600', 'Formats'], ...D.packs.map(k => [k.pack, k.label, n(k.count), n(k.large), k.formats]), ['icons', 'split from surfaces/iconset', n(D.icons), '', 'PNG']], { size: 17 }));
c.push(p('Archives without images (maps, sfx, script, configs, interfaces, shaders' + ') hold terrain data, sounds, Lua scripts, configs and UI layouts; they are extracted under packages/ too.', { spacing: { before: 120 }, size: 18 }));
c.push(pb());
c.push(h1('Galleries'));
c.push(p('A sample of each main visual folder (first files in name order). Every folder is fully browseable in images/index.html.'));
for (const g of D.galleries) {
  c.push(h2(g.title));
  c.push(img(g.file, g.cols, g.rows, g.folder === 'icons' ? 52 : 100));
  if (g.labels.length) c.push(p([mono(g.labels.join('  ·  '), 14)], { size: 14 }));
}
c.push(pb());
c.push(h1('Map codes'));
c.push(p('Folders named by map code (litmodels/<code>, surfaces/maps/worldmaps/<code>.dds, building/textures/<n>) refer to these maps (names from script/map/instance.lua, translated with the game\'s own en-US strings; the full table is text/maps.csv):'));
c.push(table([1200, W - 1200], [['Code', 'Map (instances using it)'], ...D.map_codes.map(m => [m.code, m.names.join(' / ')])], { size: 17 }));
c.push(pb());
c.push(h1('Appendix: all image folders'));
c.push(p('Folders grouped to 2–3 levels; the count includes every sub-folder. Open images/index.html for the per-folder thumbnails.'));
c.push(table([3600, 3400, 1000, W - 8000], [['Folder', 'What', 'Images', '≥1000x600'], ...D.top.map(t => [new TextRun({ text: t.folder, font: 'Consolas', size: 15 }), t.label, n(t.count), n(t.large)])], { size: 16 }));
c.push(pb());
c.push(h1('Appendix: audio and video'));
const by = {}; for (const m of D.media) { by[m.group] = by[m.group] || { n: 0, s: 0 }; by[m.group].n++; by[m.group].s += m.seconds || 0; }
c.push(table([2000, 5000, 1000, W - 8000], [['Group', 'Where', 'Files', 'Minutes'], ['music', 'music/ (background music, ogg/mp3)', n(by.music.n), (by.music.s / 60).toFixed(0)], ['voice', 'voice/ (skill shout voice lines, 女b female / 男a male)', n(by.voice.n), (by.voice.s / 60).toFixed(1)],
  ['video', 'videos/mp4 (login, logo, class intros prof02–08, story fights)', n(by.video.n), (by.video.s / 60).toFixed(1)], ['sfx', 'packages/sfx (sound effects from sfx.pck)', n(by.sfx.n), (by.sfx.s / 60).toFixed(0)]], { size: 17 }));
c.push(p('Full list with durations: media_index.csv. Cutscenes (videos/animations/*.anm, 387 files) are in-engine scripted scenes, not video; text/animations/ lists the models, effects and sounds each one uses, and text/lang/*/animation.tsv has their dialogue.', { spacing: { before: 120 }, size: 18 }));
const doc = new Document({ creator: 'Diego Chagas', title: 'Image index - Saint Seiya Online', styles: { default: { document: { run: { font: FONT, size: 21 } } } },
  numbering: { config: [{ reference: 'bul', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] }] },
  sections: [{ properties: { page: { margin: { top: 1134, bottom: 1134, left: 1417, right: 1417 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: '808080' })] })] }) }, children: c }] });
Packer.toBuffer(doc).then(b => { fs.writeFileSync(process.argv[2], b); console.log('wrote', process.argv[2], b.length); });
