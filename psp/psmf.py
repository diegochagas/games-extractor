#!/usr/bin/env python3
"""Sony PSMF movies (.pmf): read them and put a new video stream in the place of the old one.

A PSMF file is a 2048-byte header ("PSMF", version, header size, stream size, first and last
time stamp, the streams) followed by an MPEG programme stream cut in packs of 2048 bytes. Each
pack holds a pack header and one packet: video (stream 0xE0, H.264 with access unit delimiters),
audio (private stream 1 = ATRAC3plus) or padding. The video is made of groups of pictures that
start with an IDR picture; the pack where a group starts also carries the system header and a
private stream 2 packet that describes the group: the packs (counted from that one) in which its
first four pictures end, then the number of pictures and the size of each one.
Time stamps are written for the first picture of a group and for every 16th picture after it.

`replace_video` keeps the layout of the original file: every pack stays where it is, with its
clock reference; the audio packs are not touched; the packs that held the pictures of a group
hold the pictures of the same group of the new stream, and what is left over is padding. The new
stream must have the same pictures per group and no group may be larger than the old one's room.

usage: psmf.py info FILE.pmf
       psmf.py video FILE.pmf OUT.h264                 the video stream as it is
       psmf.py replace FILE.pmf NEW.h264 OUT.pmf
"""
import bisect
import re
import struct
import sys
from pathlib import Path

PACK = 2048
HEADER = 0x800
FRAME = 3003                      # 90 kHz ticks of one picture at 29.97 per second
STAMP_EVERY = 16
AUD = re.compile(b'\x00\x00\x01\x09')


def read_stamp(b):
    return ((b[0] >> 1) & 7) << 30 | b[1] << 22 | (b[2] >> 1) << 15 | b[3] << 7 | b[4] >> 1


def write_stamp(prefix, t):
    return bytes([prefix << 4 | ((t >> 30) & 7) << 1 | 1, (t >> 22) & 0xFF, ((t >> 15) & 0x7F) << 1 | 1,
                  (t >> 7) & 0xFF, (t & 0x7F) << 1 | 1])


def units(es):
    """Offsets of the access units of an H.264 stream (each starts with a delimiter)."""
    out = []
    for m in AUD.finditer(es):
        start = m.start() - 1 if m.start() and es[m.start() - 1] == 0 else m.start()
        out.append(start)
    return out


def is_idr(es, start, end):
    return re.search(b'\x00\x00\x01[\x25\x45\x65]', es[start:end]) is not None


class Movie:
    def __init__(self, data):
        if data[:4] != b'PSMF':
            raise ValueError('not a PSMF file')
        self.data = data
        self.packs = []                       # per pack: {'kind', 'items': [(code, offset, length)]}
        self.es = bytearray()
        starts = []                           # (offset in the stream, pack) of every video payload
        p = HEADER
        while p + PACK <= len(data):
            if data[p:p + 4] != b'\x00\x00\x01\xba':
                raise ValueError('pack %d does not start with a pack header' % len(self.packs))
            q = p + 14 + (data[p + 13] & 7)
            items = []
            while q + 6 <= p + PACK and data[q:q + 3] == b'\x00\x00\x01':
                code, length = data[q + 3], struct.unpack_from('>H', data, q + 4)[0]
                items.append((code, q, length))
                if code == 0xE0:
                    hl = data[q + 8]
                    starts.append((len(self.es), len(self.packs)))
                    self.es += data[q + 9 + hl:q + 6 + length]
                q += 6 + length
            codes = [c for c, _o, _l in items]
            kind = 'audio' if 0xBD in codes else 'group' if 0xBF in codes else 'video' if 0xE0 in codes else 'padding'
            self.packs.append({'kind': kind, 'items': items, 'offset': p})
            p += PACK
        self.units = units(self.es)
        ends = self.units[1:] + [len(self.es)]
        offsets = [s for s, _n in starts]
        self.groups = []                      # {'pack', 'first', 'count', 'room'}
        group_packs = [i for i, k in enumerate(self.packs) if k['kind'] == 'group']
        for g, pack in enumerate(group_packs):
            es_at = [s for s, n in starts if n == pack][0]
            first = bisect.bisect_left(self.units, es_at)
            self.groups.append({'pack': pack, 'first': first})
        for g, grp in enumerate(self.groups):
            nxt = self.groups[g + 1] if g + 1 < len(self.groups) else None
            grp['count'] = (nxt['first'] if nxt else len(self.units)) - grp['first']
            last = nxt['pack'] if nxt else len(self.packs)
            grp['slots'] = [i for i in range(grp['pack'], last) if self.packs[i]['kind'] != 'audio']
            grp['room'] = room(len(grp['slots']), grp['count'])
            nav = [length for code, _q, length in self.packs[grp['pack']]['items'] if code == 0xBF][0]
            grp['room'] += 254 - nav
            grp['size'] = (ends[grp['first'] + grp['count'] - 1]) - self.units[grp['first']]
        first_stamp = None
        for code, q, _l in self.packs[0]['items']:
            if code == 0xE0 and data[q + 7] & 0x80:
                first_stamp = read_stamp(data[q + 9:q + 14])
        self.first_stamp = first_stamp if first_stamp is not None else 90000


def room(slots, pictures):
    """Bytes of video that fit in `slots` packs of a group (worst case of time stamps)."""
    stamped = (pictures + STAMP_EVERY - 1) // STAMP_EVERY
    return slots * 2025 - 291 - 10 * stamped - 16          # group pack: 1734 instead of 2025


def video_packet(payload, stamp=None, extension=False, fill=0):
    """PES packet of the video stream; `fill` bytes of stuffing go into its header."""
    head = b''
    flags = 0
    if stamp is not None:
        flags = 0xC0 | (1 if extension else 0)
        head = write_stamp(3, stamp) + write_stamp(1, stamp - FRAME)
        if extension:
            head += b'\x1e\x60\xeb'                       # buffer size of the decoder, as the originals
    head += b'\xff' * fill
    body = bytes([0x81, flags, len(head)]) + head + payload
    return b'\x00\x00\x01\xe0' + struct.pack('>H', len(body)) + body


def padding(size):
    """Padding packet of `size` bytes in all (at least 6)."""
    return b'\x00\x00\x01\xbe' + struct.pack('>H', size - 6) + b'\xff' * (size - 6)


def replace_video(data, new_es):
    movie = Movie(data)
    new_units = units(new_es)
    if len(new_units) != len(movie.units):
        raise ValueError('%d pictures in the new video, %d in the movie' % (len(new_units), len(movie.units)))
    ends = new_units[1:] + [len(new_es)]
    out = bytearray(data)
    for g, grp in enumerate(movie.groups):
        first, count = grp['first'], grp['count']
        if not is_idr(new_es, new_units[first], ends[first]):
            raise ValueError('picture %d of the new video does not start a group' % first)
        start, stop = new_units[first], ends[first + count - 1]
        chunk = new_es[start:stop]
        begins = [new_units[first + i] - start for i in range(count)]
        finish = [ends[first + i] - start for i in range(count)]
        slots = grp['slots']
        pos = 0
        ended = {}                                          # picture -> pack (from the group's) where it ends
        written = []
        for s, pack in enumerate(slots):
            base = movie.packs[pack]['offset']
            head = bytes(data[base:base + 14 + (data[base + 13] & 7)])
            free = PACK - len(head)
            pieces = b''
            if s == 0:
                for code, q, length in movie.packs[pack]['items']:
                    if code == 0xBB:
                        pieces += bytes(data[q:q + 6 + length])
                nav_size = [6 + length for code, _q, length in movie.packs[pack]['items'] if code == 0xBF][0]
                nav_at = base + len(head) + len(pieces)
                pieces += b'\0' * nav_size                   # the group description, written below
                free -= len(pieces)
            if pos >= len(chunk):
                body = padding(free)
            else:
                i = bisect.bisect_left(begins, pos)
                starting = i < count and begins[i] < pos + (free - 9)
                stamp = None
                if s == 0:
                    stamp = movie.first_stamp + first * FRAME
                elif starting:
                    # the first picture that starts in this packet, if a stamped one starts here
                    limit = pos + free - 9 - 10
                    inside = [k for k in range(i, count) if begins[k] < limit]
                    if any(k % STAMP_EVERY == 0 for k in inside):
                        stamp = movie.first_stamp + (first + inside[0]) * FRAME
                hlen = 9 + (13 if s == 0 else 10 if stamp is not None else 0)
                take = min(free - hlen, len(chunk) - pos)
                left = free - hlen - take
                fill = 0
                if 0 < left < 7:                            # too small for a padding packet
                    fill, left = left, 0
                body = video_packet(chunk[pos:pos + take], stamp, s == 0, fill)
                if left:
                    body += padding(left)
                for k in range(bisect.bisect_right(finish, pos), count):
                    if finish[k] <= pos + take:
                        ended[k] = pack - grp['pack']
                    else:
                        break
                pos += take
            block = head + pieces + body
            if len(block) != PACK:
                raise ValueError('pack %d of group %d has %d bytes' % (pack, g, len(block)))
            out[base:base + PACK] = block
            written.append(pack)
        if pos < len(chunk):
            raise ValueError('group %d (pictures %d-%d) has %d bytes, its packs hold %d'
                             % (g, first, first + count - 1, len(chunk), pos))
        # the description of the group
        base = movie.packs[grp['pack']]['offset']
        old = [(q, length) for code, q, length in movie.packs[grp['pack']]['items'] if code == 0xBF][0]
        nav = bytearray(data[old[0]:old[0] + 6 + old[1]])
        table = bytearray(len(nav))
        refs = [ended.get(k, ended.get(count - 1, 0)) for k in range(4)]
        struct.pack_into('>4H', nav, 8, *refs)
        listed = struct.unpack_from('>H', nav, 22)[0]
        if 24 + listed * 4 > len(nav):
            raise ValueError('group %d: its description lists %d pictures but has room for %d'
                             % (g, listed, (len(nav) - 24) // 4))
        for k in range(min(listed, count)):
            struct.pack_into('>I', table, k * 4, 0x00800000 | (finish[k] - begins[k]))
        nav[24:24 + listed * 4] = table[:listed * 4]
        out[nav_at:nav_at + len(nav)] = nav
    return bytes(out)


def main(argv):
    if len(argv) == 3 and argv[1] == 'info':
        m = Movie(Path(argv[2]).read_bytes())
        kinds = {}
        for p in m.packs:
            kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
        print('%d packs %s, %d pictures in %d groups, video stream of %d bytes'
              % (len(m.packs), kinds, len(m.units), len(m.groups), len(m.es)))
        tight = min(m.groups, key=lambda g: g['room'] - g['size'])
        print('room left in the tightest group: %d bytes (group at pack %d)'
              % (tight['room'] - tight['size'], tight['pack']))
        return 0
    if len(argv) == 4 and argv[1] == 'video':
        Path(argv[3]).write_bytes(bytes(Movie(Path(argv[2]).read_bytes()).es))
        return 0
    if len(argv) == 5 and argv[1] == 'replace':
        Path(argv[4]).write_bytes(replace_video(Path(argv[2]).read_bytes(), Path(argv[3]).read_bytes()))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
