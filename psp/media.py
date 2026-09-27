#!/usr/bin/env python3
"""Audio and video of a PSP game that uses CRI ADX/AHX and Sony PSMF movies (needs ffmpeg).

  .adx  CRI ADX ADPCM          -> decoded by ffmpeg
  .ahx  CRI AHX (MPEG-2 Layer II with short frames; the header is an ADX header with type 0x11)
        -> every frame is padded to the size its MPEG header announces, which makes a regular MP2
           stream; it is decoded and tagged with the sample rate of the AHX header
  .pmf  PSMF (MPEG-PS, H.264 video + ATRAC3plus audio in private stream 1) -> .mp4; the video is
        copied as it is, the audio is pulled out of the PES packets, wrapped in an OMA header so
        that ffmpeg can decode it, and encoded to AAC

  .phd + .pbd  Sony sound bank ("PPHD8": programs, tones and the PPVA table of samples; the .pbd
        holds the samples as PlayStation ADPCM) -> one file per sample, numbered as in the bank

usage: media.py audio SRC_DIR OUT_DIR [--workers N]     every .adx/.ahx -> OUT_DIR/<same path>.ogg
       media.py video SRC_DIR OUT_DIR                   every .pmf -> OUT_DIR/<name>.mp4
       media.py banks SRC_DIR OUT_DIR [--workers N]     every .phd/.pbd pair -> OUT_DIR/<path>/NNN.ogg
"""
import array
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from multiprocessing import Pool

FFMPEG = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y']
OGG = ['-c:a', 'libvorbis', '-q:a', '6']
BITRATES_V2_L2 = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]
RATES_V2 = [22050, 24000, 16000]


def ahx_to_mp2(data):
    """Return (mp2 bytes, sample rate, sample count) of an AHX file."""
    if data[0] != 0x80 or data[4] not in (0x10, 0x11):
        raise ValueError('not an AHX file')
    start = struct.unpack_from('>H', data, 2)[0] + 4
    rate, samples = struct.unpack_from('>II', data, 8)
    sync = data[start:start + 4]
    b2 = sync[2]
    if sync[:2] != b'\xff\xf5' or (b2 >> 4) in (0, 15) or (b2 >> 2) & 3 == 3:
        raise ValueError('AHX data does not start with an MPEG-2 Layer II frame header')
    size = 144000 * BITRATES_V2_L2[b2 >> 4] // RATES_V2[(b2 >> 2) & 3]
    end = data.rfind(b'\x80\x01\x00\x0cAHXE')
    if end < 0:
        end = len(data)
    pos = [m.start() for m in re.finditer(re.escape(sync), data[:end]) if m.start() >= start]
    # a sync word inside the audio data would make a frame far shorter than its neighbours
    frames = []
    for a, b in zip(pos, pos[1:] + [end]):
        if frames and b - a < 64 or (frames and len(frames[-1]) < 64):
            frames[-1] += data[a:b]
        else:
            frames.append(data[a:b])
    out = bytearray()
    for fr in frames:
        out += fr[:size] + bytes(max(0, size - len(fr)))
    return bytes(out), rate, samples


def convert_audio(job):
    src, dest = job
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        data = Path(src).read_bytes()
        if data[4] in (0x10, 0x11):
            mp2, rate, samples = ahx_to_mp2(data)
            cmd = FFMPEG + ['-f', 'mp3', '-i', 'pipe:0', '-af',
                            'asetrate=%d,atrim=end_sample=%d' % (rate, samples), '-ar', str(rate)] + OGG + [dest]
            subprocess.run(cmd, input=mp2, check=True, capture_output=True)
        else:
            subprocess.run(FFMPEG + ['-i', src] + OGG + [dest], check=True, capture_output=True)
        return src, None
    except subprocess.CalledProcessError as e:
        return src, e.stderr.decode('utf-8', 'replace')[-300:]
    except Exception as e:
        return src, repr(e)


VAG_FILTERS = ((0, 0), (60, 0), (115, -52), (98, -55), (122, -60))


def vag_decode(data):
    """PlayStation ADPCM (16-byte blocks: shift/filter, flags, 28 nibbles) -> int16 samples."""
    out = array.array('h')
    h1 = h2 = 0
    for p in range(0, len(data) - 15, 16):
        head, flags = data[p], data[p + 1]
        if flags == 7:                                   # end marker block
            break
        shift, filt = head & 15, min(head >> 4, 4)
        f0, f1 = VAG_FILTERS[filt]
        for b in data[p + 2:p + 16]:
            for nib in (b & 15, b >> 4):
                s = nib << 12
                if s & 0x8000:
                    s -= 0x10000
                s = (s >> shift) + ((h1 * f0 + h2 * f1 + 32) >> 6)
                s = -32768 if s < -32768 else 32767 if s > 32767 else s
                out.append(s)
                h2, h1 = h1, s
        if flags & 1:                                    # last block of the sample
            break
    return out


def bank_samples(phd):
    """[(number, offset, sample rate, size)] of the PPVA table of a .phd file."""
    if phd[:4] != b'PPHD':
        raise ValueError('not a PHD sound bank')
    va = struct.unpack_from('<I', phd, 0x18)[0]
    if phd[va:va + 4] != b'PPVA':
        raise ValueError('PPVA table not found')
    esize, _r, first, last = struct.unpack_from('<IIII', phd, va + 8)
    out = []
    for i in range(last - first + 1):
        q = va + 0x20 + i * esize
        if q + 12 > len(phd):
            break
        off, rate, size = struct.unpack_from('<III', phd, q)
        if off != 0xFFFFFFFF and size and size != 0xFFFFFFFF:
            out.append((first + i, off, rate, size))
    return out


def convert_bank(job):
    phd, pbd, dest = job
    try:
        head = Path(phd).read_bytes()
        body = Path(pbd).read_bytes()
        os.makedirs(dest, exist_ok=True)
        n = 0
        for number, off, rate, size in bank_samples(head):
            pcm = vag_decode(body[off:off + size])
            if not len(pcm):
                continue
            cmd = FFMPEG + ['-f', 's16le', '-ar', str(rate), '-ac', '1', '-i', 'pipe:0'] + OGG + \
                [os.path.join(dest, '%03d.ogg' % number)]
            subprocess.run(cmd, input=pcm.tobytes(), check=True, capture_output=True)
            n += 1
        return phd, n, None
    except subprocess.CalledProcessError as e:
        return phd, 0, e.stderr.decode('utf-8', 'replace')[-300:]
    except Exception as e:
        return phd, 0, repr(e)


def psmf_audio(data):
    """ATRAC3plus frames of private stream 1 as an OMA file (None if the movie has no audio)."""
    out = bytearray()
    params = None
    p = data.find(b'\x00\x00\x01\xba')
    n = len(data)
    while 0 <= p < n - 6:
        if data[p:p + 3] != b'\x00\x00\x01':
            p = data.find(b'\x00\x00\x01', p + 1)
            continue
        code = data[p + 3]
        if code == 0xBA:                               # pack header
            p += 14 + (data[p + 13] & 7)
            continue
        if code == 0xB9:
            break
        length = struct.unpack_from('>H', data, p + 4)[0]
        if code == 0xBD:
            hlen = data[p + 8]
            body = data[p + 9 + hlen + 4:p + 6 + length]      # 4 bytes: sub-stream id + 3 reserved
            out += body
        p += 6 + length
    if not out:
        return None
    # split into frames: 0x0FD0, 2 bytes of parameters, 4 reserved bytes, then the frame
    frames = bytearray()
    q = 0
    while q + 8 <= len(out) and out[q:q + 2] == b'\x0f\xd0':
        params = bytes(out[q + 2:q + 4])
        size = ((struct.unpack('>H', params)[0] & 0x3FF) + 1) * 8
        frames += out[q + 8:q + 8 + size]
        q += 8 + size
    head = bytearray(96)
    head[0:8] = b'EA3\x01\x00\x60\xff\xff'
    head[32] = 1                                       # ATRAC3plus
    head[34:36] = params
    return bytes(head) + bytes(frames)


def convert_video(src, dest):
    data = Path(src).read_bytes()
    oma = psmf_audio(data)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cmd = FFMPEG + ['-i', src]
        if oma:
            path = os.path.join(tmp, 'audio.oma')
            Path(path).write_bytes(oma)
            cmd += ['-i', path, '-map', '0:v:0', '-map', '1:a:0', '-c:a', 'aac', '-b:a', '192k']
        cmd += ['-c:v', 'copy', '-movflags', '+faststart', dest]
        subprocess.run(cmd, check=True)
    return bool(oma)


def main(argv):
    if len(argv) < 4 or argv[1] not in ('audio', 'video', 'banks'):
        print(__doc__)
        return 2
    src, out = argv[2], argv[3]
    found = []
    for root, _dirs, names in os.walk(src):
        for n in sorted(names):
            found.append(os.path.join(root, n))
    if argv[1] == 'video':
        for f in sorted(found):
            if f.lower().endswith('.pmf'):
                dest = os.path.join(out, os.path.splitext(os.path.basename(f))[0] + '.mp4')
                print(dest, 'with audio' if convert_video(f, dest) else 'no audio track')
        return 0
    workers = int(argv[argv.index('--workers') + 1]) if '--workers' in argv else os.cpu_count()
    if argv[1] == 'banks':
        lower = {f.lower(): f for f in found}
        jobs = [(f, lower[f.lower()[:-4] + '.pbd'], os.path.splitext(os.path.join(out, os.path.relpath(f, src)))[0])
                for f in found if f.lower().endswith('.phd') and f.lower()[:-4] + '.pbd' in lower]
        total, failed = 0, []
        with Pool(workers) as pool:
            for path, n, err in pool.imap_unordered(convert_bank, jobs):
                total += n
                if err:
                    failed.append((path, err))
        for path, err in failed:
            print('FAILED', path, err)
        print('%d sound banks, %d samples, %d failed -> %s' % (len(jobs), total, len(failed), out))
        return 1 if failed else 0
    jobs = [(f, os.path.splitext(os.path.join(out, os.path.relpath(f, src)))[0] + '.ogg')
            for f in found if f.lower().endswith(('.adx', '.ahx'))]
    failed = []
    with Pool(workers) as pool:
        for path, err in pool.imap_unordered(convert_audio, jobs, chunksize=4):
            if err:
                failed.append((path, err))
    for path, err in failed:
        print('FAILED', path, err)
    print('%d audio files, %d failed -> %s' % (len(jobs), len(failed), out))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
