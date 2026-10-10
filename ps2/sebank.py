#!/usr/bin/env python3
"""Sound-effect banks of the game (`SE_*.BIN`): an FJF container with a `seds` chunk (the sound
sequences, not decoded) and a `swdm` chunk holding the samples. In `swdm`: at 0x40 a sub-header
(u32 0x8000, u32 0x40, u32 data size, u32 data offset...), then 32-byte sample records from 0x60:
u32 offset into the data, u32 loop/flags, u16 volume (0x0F7F), u16 pitch, 4 bytes, name[16] in
Shift-JIS (the source `.aif` name, often ending in the sample rate in kHz). The pitch is in
1/256 semitone: 0xF0D9 = 20,000 Hz, so rate = 20000 * 2 ** ((pitch - 0xF0D9) / 3072). Samples
are PlayStation ADPCM (16-byte blocks).

usage: sebank.py list FILE
       sebank.py extract SRC OUT_DIR     SRC = one bank or a folder: OUT_DIR/<bank>/<NN>_<name>.wav
"""
import os
import struct
import sys
import wave

import fjf

FILTERS = [(0, 0), (60, 0), (115, -52), (98, -55), (122, -60)]


def vag_decode(data):
    """PlayStation ADPCM -> int16 samples (stops at a block flagged as the end)."""
    out, s1, s2 = [], 0, 0
    for i in range(0, len(data) - 15, 16):
        shift, flags = data[i] & 0x0F, data[i + 1]
        f = min(data[i] >> 4, 4)
        if flags == 7:
            break
        for j in range(14):
            byte = data[i + 2 + j]
            for nib in (byte & 0x0F, byte >> 4):
                v = (nib ^ 8) - 8
                v = (v << 12) >> shift
                v += (s1 * FILTERS[f][0] + s2 * FILTERS[f][1] + 32) >> 6
                v = max(-32768, min(32767, v))
                out.append(v)
                s2, s1 = s1, v
        if flags & 1:
            break
    return out


def samples(data):
    """[(name, rate, adpcm bytes)] of a bank file."""
    data = fjf.unwrap(data)
    if not fjf.is_fjf(data):
        return []
    _flags, ents = fjf.entries(data)
    chunk = None
    for _eid, off, size in ents:
        if data[off:off + 4] == b'swdm':
            chunk = data[off:off + size]
    if chunk is None:
        return []
    if len(chunk) < 0x60:
        return []
    _a, _b, data_size, data_off = struct.unpack_from('<IIII', chunk, 0x40)
    if data_off > len(chunk):
        return []
    recs = []
    for o in range(0x60, data_off - 31, 32):
        off, loop, vol, pitch = struct.unpack_from('<IIHH', chunk, o)
        name = chunk[o + 16:o + 32].split(b'\0')[0].decode('shift_jis', 'replace')
        if not name:
            continue
        recs.append((off, loop, pitch, name))
    recs.sort()
    out = []
    for i, (off, _loop, pitch, name) in enumerate(recs):
        end = recs[i + 1][0] if i + 1 < len(recs) else data_size
        rate = int(round(20000 * 2 ** ((pitch - 0xF0D9) / 3072.0)))
        if not 4000 <= rate <= 96000:                 # a record without a pitch
            rate = 22050
        for usual in (8000, 11025, 16000, 18000, 20000, 22050, 24000, 25000, 30000, 32000, 44100, 48000):
            if abs(rate - usual) <= usual * 0.005:    # the pitch is quantised: snap to the usual rates
                rate = usual
        out.append((name, rate, chunk[data_off + off:data_off + end]))
    return out


def extract(path, out):
    with open(path, 'rb') as f:
        data = f.read()
    items = samples(data)
    bank = os.path.splitext(os.path.basename(path))[0]
    folder = os.path.join(out, bank)
    os.makedirs(folder, exist_ok=True)
    for i, (name, rate, adpcm) in enumerate(items):
        pcm = vag_decode(adpcm)
        safe = ''.join(ch if ch not in '/\\:*?"<>|' else '_' for ch in name).replace('\ufffd', '')
        with wave.open(os.path.join(folder, '%02d_%s.wav' % (i, safe)), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(struct.pack('<%dh' % len(pcm), *pcm))
    return len(items)


def main(argv):
    if len(argv) == 3 and argv[1] == 'list':
        with open(argv[2], 'rb') as f:
            for name, rate, adpcm in samples(f.read()):
                print('%6d Hz %8d bytes  %s' % (rate, len(adpcm), name))
        return 0
    if len(argv) == 4 and argv[1] == 'extract':
        src, out = argv[2], argv[3]
        files = [os.path.join(src, n) for n in sorted(os.listdir(src)) if n.lower().startswith('se_') and n.lower().endswith('.bin')] if os.path.isdir(src) else [src]
        n = sum(extract(p, out) for p in files)
        print('%d samples from %d banks -> %s' % (n, len(files), out))
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
