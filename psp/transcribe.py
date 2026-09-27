#!/usr/bin/env python3
"""Speech of a video or audio file -> timed segments (JSON), with faster-whisper.

usage: transcribe.py OUT_DIR FILE [FILE ...] [--language ja] [--model large-v3] [--device cuda]

Writes OUT_DIR/<name>.<language>.json: [{"start", "end", "text", "no_speech", "words": [...]}].
Runs in its own environment (faster-whisper is not needed by the other tools):
    python3 -m venv VENV && VENV/bin/pip install faster-whisper nvidia-cublas-cu12 nvidia-cudnn-cu12
Songs are not meant to be subtitled: segments are kept as recognised and the choice of what
becomes a subtitle is made when the translation is written.
"""
import json
import os
import sys


def gpu_libraries():
    """The pip packages of cuBLAS / cuDNN are not on the loader path: re-run with them added."""
    if os.environ.get('TRANSCRIBE_LIBS'):
        return
    import site
    paths = []
    for base in site.getsitepackages():
        for lib in ('cublas', 'cudnn'):
            p = os.path.join(base, 'nvidia', lib, 'lib')
            if os.path.isdir(p):
                paths.append(p)
    if paths:
        env = dict(os.environ, TRANSCRIBE_LIBS='1',
                   LD_LIBRARY_PATH=':'.join(paths + [os.environ.get('LD_LIBRARY_PATH', '')]))
        os.execve(sys.executable, [sys.executable] + sys.argv, env)


def main(argv):
    opts = {'--language': 'ja', '--model': 'large-v3', '--device': 'cuda'}
    pos = []
    i = 1
    while i < len(argv):
        if argv[i] in opts:
            opts[argv[i]] = argv[i + 1]
            i += 2
        else:
            pos.append(argv[i])
            i += 1
    if len(pos) < 2:
        print(__doc__)
        return 2
    if opts['--device'] == 'cuda':
        gpu_libraries()
    from faster_whisper import WhisperModel
    out = pos[0]
    os.makedirs(out, exist_ok=True)
    kind = 'int8_float16' if opts['--device'] == 'cuda' else 'int8'
    model = WhisperModel(opts['--model'], device=opts['--device'], compute_type=kind)
    for path in pos[1:]:
        segments, info = model.transcribe(path, language=opts['--language'], beam_size=5, word_timestamps=True,
                                          vad_filter=True, vad_parameters={'min_silence_duration_ms': 400},
                                          condition_on_previous_text=False)
        rows = [{'start': round(s.start, 2), 'end': round(s.end, 2), 'text': s.text.strip(),
                 'no_speech': round(s.no_speech_prob, 3),
                 'words': [{'start': round(w.start, 2), 'end': round(w.end, 2), 'word': w.word}
                           for w in (s.words or [])]} for s in segments]
        name = os.path.splitext(os.path.basename(path))[0]
        dest = os.path.join(out, '%s.%s.json' % (name, opts['--language']))
        with open(dest, 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        print('%s: %d segments, %.0f s -> %s' % (name, len(rows), info.duration, dest))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
