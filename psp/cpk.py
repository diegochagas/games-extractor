#!/usr/bin/env python3
"""CRI Middleware CPK archives (CPKMC2, "CPK " + @UTF tables, CRILAYLA compression).

usage: cpk.py list FILE.cpk
       cpk.py extract FILE.cpk OUTDIR [--workers N]
       cpk.py patch FILE.cpk NEW_FILES_DIR      replaces the files found under NEW_FILES_DIR

`patch` changes the archive itself (work on a copy): a new file goes into the slot of the old one
when it fits and to the end of the archive when it does not; only its row of the TOC changes.
A file that was stored without compression is stored without compression again.
"""
import os
import struct
import sys
from multiprocessing import Pool

FMT = {0: '>B', 1: '>b', 2: '>H', 3: '>h', 4: '>I', 5: '>i', 6: '>Q', 7: '>q', 8: '>f', 9: '>d'}


def utf_table(buf, where=None):
    """Parse an @UTF table: returns (table name, list of row dicts). With `where` (a list), the
    offset inside `buf` and the struct format of every per-row value is appended to it as
    {column: (offset, format)} per row."""
    if buf[:4] != b'@UTF':
        raise ValueError('not an @UTF table (encrypted tables are not supported)')
    _size, rows_off, str_off, data_off, name, ncol, rowlen, nrows = struct.unpack('>IIIIIHHI', buf[4:32])
    base = 8
    strings = buf[base + str_off:base + data_off]

    def text(o):
        return strings[o:strings.index(b'\0', o)].decode('utf-8', 'replace')

    def read(t, p):
        if t in FMT:
            n = struct.calcsize(FMT[t])
            return struct.unpack(FMT[t], buf[p:p + n])[0], p + n
        if t == 0xA:
            return text(struct.unpack('>I', buf[p:p + 4])[0]), p + 4
        if t == 0xB:
            o, n = struct.unpack('>II', buf[p:p + 8])
            return buf[base + data_off + o:base + data_off + o + n], p + 8
        raise ValueError('unknown @UTF column type %x' % t)

    p = 32
    cols = []
    for _ in range(ncol):
        flags = buf[p]
        col = text(struct.unpack('>I', buf[p + 1:p + 5])[0])
        p += 5
        storage, typ = flags & 0xF0, flags & 0x0F
        const = None
        if storage == 0x30:
            const, p = read(typ, p)
        cols.append((col, storage, typ, const))
    rows = []
    for r in range(nrows):
        q = base + rows_off + r * rowlen
        row, at = {}, {}
        for col, storage, typ, const in cols:
            if storage == 0x50:
                at[col] = (q, FMT.get(typ))
                row[col], q = read(typ, q)
            else:
                row[col] = const
        rows.append(row)
        if where is not None:
            where.append(at)
    return text(name), rows


def crilayla(data):
    """Decompress a CRILAYLA stream (LZ77 variant read backwards, first 0x100 bytes stored raw)."""
    size, csize = struct.unpack('<II', data[8:16])
    out = bytearray(size + 0x100)
    out[:0x100] = data[16 + csize:16 + csize + 0x100]
    pos = 16 + csize - 1          # next input byte (read backwards)
    acc = 0                       # bit accumulator
    nacc = 0
    end = 0x100 + size - 1
    done = 0
    while done < size:
        if nacc < 1:
            acc = data[pos]; pos -= 1; nacc = 8
        nacc -= 1
        if (acc >> nacc) & 1:
            while nacc < 13:
                acc = ((acc & 0xFFFFFF) << 8) | data[pos]; pos -= 1; nacc += 8
            nacc -= 13
            ref = end - done + ((acc >> nacc) & 0x1FFF) + 3
            length = 3
            for bits in (2, 3, 5, 8):
                while nacc < bits:
                    acc = ((acc & 0xFFFFFF) << 8) | data[pos]; pos -= 1; nacc += 8
                nacc -= bits
                v = (acc >> nacc) & ((1 << bits) - 1)
                length += v
                if v != (1 << bits) - 1:
                    break
            else:
                while True:
                    while nacc < 8:
                        acc = ((acc & 0xFFFFFF) << 8) | data[pos]; pos -= 1; nacc += 8
                    nacc -= 8
                    v = (acc >> nacc) & 0xFF
                    length += v
                    if v != 0xFF:
                        break
            length = min(length, size - done)
            dst = end - done
            for i in range(length):
                out[dst - i] = out[ref - i]
            done += length
        else:
            while nacc < 8:
                acc = ((acc & 0xFFFFFF) << 8) | data[pos]; pos -= 1; nacc += 8
            nacc -= 8
            out[end - done] = (acc >> nacc) & 0xFF
            done += 1
    return bytes(out)


def crilayla_pack(data, chain=48):
    """CRILAYLA stream of `data`, or None when the file is too small or does not shrink."""
    if len(data) <= 0x100 + 8:
        return None
    body = data[0x100:][::-1]                     # the stream describes the file from its end
    n = len(body)
    bits = []
    put = bits.append
    heads, links = {}, [0] * n
    i = 0

    def index(k):
        if k + 3 <= n:
            key = body[k:k + 3]
            links[k] = heads.get(key, -1)
            heads[key] = k

    while i < n:
        best, where = 0, 0
        if i + 3 <= n:
            j = heads.get(body[i:i + 3], -1)
            tries = chain
            limit = n - i
            while j >= 0 and tries and i - j <= 8194:
                if i - j >= 3 and body[j + best:j + best + 1] == body[i + best:i + best + 1]:
                    k = 0
                    while k < limit and body[j + k] == body[i + k]:
                        k += 1
                    if k > best:
                        best, where = k, j
                        if k >= 512:
                            break
                j = links[j]
                tries -= 1
        if best >= 3:
            put((1, 1))
            put((i - where - 3, 13))
            rest = best - 3
            for size in (2, 3, 5, 8):
                top = (1 << size) - 1
                if rest >= top:
                    put((top, size))
                    rest -= top
                    if size == 8:
                        while rest >= 255:
                            put((255, 8))
                            rest -= 255
                        put((rest, 8))
                else:
                    put((rest, size))
                    break
            for k in range(i, i + best):
                index(k)
            i += best
        else:
            put((0, 1))
            put((body[i], 8))
            index(i)
            i += 1
    acc = nacc = 0
    out = bytearray()
    for value, size in bits:
        acc = (acc << size) | value
        nacc += size
        while nacc >= 8:
            nacc -= 8
            out.append((acc >> nacc) & 0xFF)
        acc &= (1 << nacc) - 1
    if nacc:
        out.append((acc << (8 - nacc)) & 0xFF)
    out += bytes(-len(out) % 4)                    # never read: the decoder stops at the file size
    packed = b'CRILAYLA' + struct.pack('<II', n, len(out)) + bytes(out[::-1]) + data[:0x100]
    return packed if len(packed) < len(data) else None


def patch(path, new_files):
    """Replace files of the archive at `path` (in place). new_files: {name in the archive: bytes}.
    Returns a list of (name, 'slot' | 'end', stored size)."""
    cpk = Cpk(path)
    with open(path, 'rb') as f:
        f.seek(cpk.header['TocOffset'])
        toc = f.read(cpk.header['TocSize'])
    where = []
    _name, rows = utf_table(toc[16:], where)
    base = min(cpk.header['TocOffset'], cpk.header['ContentOffset'] or cpk.header['TocOffset'])
    align = cpk.header.get('Align') or 0x800
    names = [(r['DirName'] + '/' if r['DirName'] else '') + r['FileName'] for r in rows]
    unknown = sorted(set(new_files) - set(names))
    if unknown:
        raise ValueError('not in the archive: %s' % ', '.join(unknown[:5]))
    starts = sorted(base + r['FileOffset'] for r in rows)
    limit = cpk.header.get('EtocOffset') or cpk.header.get('ItocOffset') or os.path.getsize(path)
    toc = bytearray(toc)
    done = []
    with open(path, 'r+b') as f:
        for i, name in enumerate(names):
            if name not in new_files:
                continue
            data = new_files[name]
            # a file the archive keeps as it is stays so: the game reads some of them in place
            raw = rows[i]['FileSize'] == rows[i]['ExtractSize']
            stored = data if raw else (crilayla_pack(data) or data)
            start = base + rows[i]['FileOffset']
            later = [s for s in starts if s > start]
            room = (later[0] if later else limit) - start
            if len(stored) <= room:
                f.seek(start)
                f.write(stored + bytes(room - len(stored)))
                done.append((name, 'slot', len(stored)))
            else:
                f.seek(0, 2)
                start = (f.tell() + align - 1) // align * align
                f.seek(start)
                f.write(stored + bytes(-len(stored) % align))
                done.append((name, 'end', len(stored)))
            for col, value in (('FileOffset', start - base), ('FileSize', len(stored)), ('ExtractSize', len(data))):
                off, fmt = where[i][col]
                struct.pack_into(fmt, toc, 16 + off, value)
        f.seek(cpk.header['TocOffset'])
        f.write(toc)
    return done


class Cpk:
    def __init__(self, path):
        self.path = path
        with open(path, 'rb') as f:
            head = f.read(0x800)
            if head[:4] != b'CPK ':
                raise ValueError('%s: not a CPK archive' % path)
            self.header = utf_table(head[16:])[1][0]
            f.seek(self.header['TocOffset'])
            toc = f.read(self.header['TocSize'])
        if toc[:4] != b'TOC ':
            raise ValueError('%s: TOC not found' % path)
        base = min(self.header['TocOffset'], self.header['ContentOffset'] or self.header['TocOffset'])
        self.files = []
        for r in utf_table(toc[16:])[1]:
            name = (r['DirName'] + '/' if r['DirName'] else '') + r['FileName']
            self.files.append({'name': name, 'offset': base + r['FileOffset'], 'csize': r['FileSize'],
                               'size': r['ExtractSize'], 'id': r['ID']})

    def read(self, entry):
        with open(self.path, 'rb') as f:
            f.seek(entry['offset'])
            data = f.read(entry['csize'])
        if data[:8] == b'CRILAYLA':
            data = crilayla(data)
        if len(data) != entry['size']:
            raise ValueError('%s: size %d != %d' % (entry['name'], len(data), entry['size']))
        return data


def _extract(job):
    path, entry, out = job
    dest = os.path.join(out, entry['name'])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    data = _read(path, entry)
    with open(dest, 'wb') as f:
        f.write(data)
    return entry['name'], len(data)


def _read(path, entry):
    c = Cpk.__new__(Cpk)
    c.path = path
    return c.read(entry)


def main(argv):
    if len(argv) < 3 or argv[1] not in ('list', 'extract', 'patch'):
        print(__doc__)
        return 2
    if argv[1] == 'patch':
        root = argv[3]
        new = {}
        for folder, _dirs, files in os.walk(root):
            for n in files:
                p = os.path.join(folder, n)
                with open(p, 'rb') as f:
                    new[os.path.relpath(p, root).replace(os.sep, '/')] = f.read()
        for name, place, size in patch(argv[2], new):
            print('%-5s %9d  %s' % (place, size, name))
        return 0
    cpk = Cpk(argv[2])
    if argv[1] == 'list':
        for e in cpk.files:
            print('%10d %10d  %s' % (e['csize'], e['size'], e['name']))
        print('%d files, %d bytes' % (len(cpk.files), sum(e['size'] for e in cpk.files)))
        return 0
    out = argv[3]
    workers = int(argv[argv.index('--workers') + 1]) if '--workers' in argv else os.cpu_count()
    jobs = [(cpk.path, e, out) for e in sorted(cpk.files, key=lambda e: -e['size'])]
    total = 0
    with Pool(workers) as pool:
        for _name, n in pool.imap_unordered(_extract, jobs, chunksize=4):
            total += n
    print('%d files, %d bytes -> %s' % (len(jobs), total, out))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
