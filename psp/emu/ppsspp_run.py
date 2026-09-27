#!/usr/bin/env python3
"""Drives PPSSPP through a scripted run and saves screenshots, inside a nested X server
(Xephyr), so the desktop keeps its keyboard and focus.

usage: ppsspp_run.py GAME.iso OUT_DIR --script "wait:20 shot:title key:start wait:3 shot:menu ..."
                     [--display :5] [--state FILE.ppst] [--keep]

Script words: `wait:SECONDS`, `shot:NAME` (OUT_DIR/NAME.png), `key:BUTTON` (up down left right
circle cross square triangle start select l r), `hold:BUTTON:SECONDS`, `fast:SECONDS` (runs
with fast-forward held), `save:SLOT` / `load:SLOT` (save states 1-5 of the emulator).
Needs Xephyr, xdotool, ImageMagick's `import` and the PPSSPP Flatpak (org.ppsspp.PPSSPP) with
its default keyboard mapping.
"""
import os
import subprocess
import sys
import time

KEYS = {'up': 'Up', 'down': 'Down', 'left': 'Left', 'right': 'Right', 'circle': 'x', 'cross': 'z',
        'square': 'a', 'triangle': 's', 'start': 'space', 'select': 'Return', 'l': 'q', 'r': 'w'}
SLOT = {'1': 'F1', '2': 'F2', '3': 'F3', '4': 'F4', '5': 'F5'}


def xdo(display, *args):
    subprocess.run(['xdotool'] + list(args), env=dict(os.environ, DISPLAY=display), check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main(argv):
    pos, opts = [], {'--display': ':5', '--script': '', '--state': ''}
    keep = '--keep' in argv
    i = 1
    while i < len(argv):
        if argv[i] in opts:
            opts[argv[i]] = argv[i + 1]
            i += 2
        else:
            if argv[i] != '--keep':
                pos.append(argv[i])
            i += 1
    if len(pos) != 2:
        print(__doc__)
        return 2
    iso, out = os.path.abspath(pos[0]), os.path.abspath(pos[1])
    display = opts['--display']
    os.makedirs(out, exist_ok=True)
    env = dict(os.environ, DISPLAY=display, SDL_AUDIODRIVER='dummy')
    procs = []
    if subprocess.run(['xdpyinfo'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        procs.append(subprocess.Popen(['Xephyr', display, '-screen', '960x544', '-ac', '-glamor', '-no-host-grab'],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        time.sleep(2)
    cmd = ['flatpak', 'run', '--user', 'org.ppsspp.PPSSPP', '--windowed', '--xres', '960', '--yres', '544']
    if opts['--state']:
        cmd.append('--state=' + os.path.abspath(opts['--state']))
    log = open(os.path.join(out, 'ppsspp.log'), 'w')
    emu = subprocess.Popen(cmd + [iso], env=env, stdout=log, stderr=subprocess.STDOUT)
    try:
        for word in opts['--script'].split():
            kind, _, arg = word.partition(':')
            if kind == 'wait':
                time.sleep(float(arg))
            elif kind == 'shot':
                subprocess.run(['import', '-window', 'root', os.path.join(out, arg + '.png')], env=env, check=False)
            elif kind == 'key':
                xdo(display, 'keydown', KEYS[arg])
                time.sleep(0.12)
                xdo(display, 'keyup', KEYS[arg])
                time.sleep(0.25)
            elif kind == 'hold':
                button, _, secs = arg.partition(':')
                xdo(display, 'keydown', KEYS[button])
                time.sleep(float(secs))
                xdo(display, 'keyup', KEYS[button])
            elif kind == 'fast':
                xdo(display, 'keydown', 'Tab')
                time.sleep(float(arg))
                xdo(display, 'keyup', 'Tab')
            elif kind in ('save', 'load'):
                # PPSSPP: F2 saves and F4 loads the current slot, F3 moves to the next slot
                xdo(display, 'key', 'F2' if kind == 'save' else 'F4')
                time.sleep(1.5)
            else:
                print('unknown script word', word)
            if emu.poll() is not None:
                print('emulator exited with', emu.returncode)
                return 1
    finally:
        if emu.poll() is None:
            emu.terminate()
            try:
                emu.wait(5)
            except subprocess.TimeoutExpired:
                emu.kill()
        subprocess.run(['flatpak', 'kill', 'org.ppsspp.PPSSPP'], check=False, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        log.close()
        if not keep:
            for p in procs:
                p.terminate()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
