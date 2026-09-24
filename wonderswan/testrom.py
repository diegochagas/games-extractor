#!/usr/bin/env python3
"""Boot a WonderSwan ROM in the libretro core and save screenshots.

Drives the same emulator core the RomM web player uses (mednafen_wswan), headless,
through ctypes. Used to verify a patched ROM actually runs.

    python3 testrom.py ROM --core PATH --script "600:start,60:a,120:a" --out DIR

`--script` is a comma separated list of `frames:button` steps: run that many frames,
then tap that button (a, b, start, x1..x4 for the top d-pad, y1..y4 for the left one).
A step with no button just runs frames. A screenshot is saved after every step.
"""
import argparse
import ctypes
import os
from pathlib import Path

from PIL import Image

RETRO_DEVICE_JOYPAD = 1
BUTTONS = {"b": 0, "y": 1, "select": 2, "start": 3, "up": 4, "down": 5, "left": 6, "right": 7,
           "a": 8, "x": 9, "l": 10, "r": 11}
# WonderSwan maps its two d-pads onto the joypad: X1-X4 = up/right/down/left (top pad),
# Y1-Y4 = the left pad. Beetle exposes them as the joypad d-pad + L/R/L2/R2.
ALIASES = {"x1": "up", "x2": "right", "x3": "down", "x4": "left"}

PIX_FMT = {0: "0RGB1555", 1: "XRGB8888", 2: "RGB565"}


class Emulator:
    def __init__(self, core, rom):
        self.lib = ctypes.CDLL(core)
        self.frame = None
        self.fmt = 0
        self.keys = set()
        self._keep = []
        self._dir = ctypes.create_string_buffer(str(Path(rom).parent).encode())
        LOG = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p)

        class LogIface(ctypes.Structure):
            _fields_ = [("log", LOG)]

        self.log_lines = []
        self._log_cb = LOG(lambda lvl, msg: self.log_lines.append(msg.decode("utf8", "replace").strip()))
        self._log_iface = LogIface(self._log_cb)
        self._keep += [self._log_cb, self._log_iface, self._dir]
        self.lib.retro_set_environment(self._cb(ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_uint, ctypes.c_void_p), self._env))
        self.lib.retro_set_video_refresh(self._cb(
            ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_size_t), self._video))
        self.lib.retro_set_audio_sample(self._cb(ctypes.CFUNCTYPE(None, ctypes.c_int16, ctypes.c_int16), lambda l, r: None))
        self.lib.retro_set_audio_sample_batch(self._cb(
            ctypes.CFUNCTYPE(ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t), lambda d, f: f))
        self.lib.retro_set_input_poll(self._cb(ctypes.CFUNCTYPE(None), lambda: None))
        self.lib.retro_set_input_state(self._cb(
            ctypes.CFUNCTYPE(ctypes.c_int16, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint), self._input))
        self.lib.retro_init()
        class GameInfo(ctypes.Structure):
            _fields_ = [("path", ctypes.c_char_p), ("data", ctypes.c_void_p),
                        ("size", ctypes.c_size_t), ("meta", ctypes.c_char_p)]

        # the core has need_fullpath=1: it opens the file itself, data/size are ignored
        gi = GameInfo(str(rom).encode(), None, 0, None)
        if not self.lib.retro_load_game(ctypes.byref(gi)):
            raise RuntimeError("core refused the ROM: " + "; ".join(self.log_lines))

    def _cb(self, proto, fn):
        cb = proto(fn)
        self._keep.append(cb)
        return cb

    def _env(self, cmd, data):
        if cmd == 10:                                  # SET_PIXEL_FORMAT
            self.fmt = ctypes.cast(data, ctypes.POINTER(ctypes.c_int)).contents.value
            return True
        if cmd in (9, 31) and data:                    # GET_SYSTEM_DIRECTORY / GET_SAVE_DIRECTORY
            # note: ptr.contents = x only rebinds the Python pointer; ptr[0] = x writes through it
            ctypes.cast(data, ctypes.POINTER(ctypes.c_void_p))[0] = ctypes.cast(self._dir, ctypes.c_void_p)
            return True
        if cmd == 27 and data:                         # GET_LOG_INTERFACE
            ctypes.memmove(data, ctypes.byref(self._log_iface), ctypes.sizeof(self._log_iface))
            return True
        if cmd == 3 and data:                          # GET_CAN_DUPE
            ctypes.cast(data, ctypes.POINTER(ctypes.c_bool))[0] = True
            return True
        return False

    def _video(self, data, w, h, pitch):
        if not data:
            return
        if self.fmt == 1:
            raw = ctypes.string_at(data, pitch * h)
            im = Image.frombytes("RGBA", (w, h), raw, "raw", "BGRA", pitch)
            self.frame = im.convert("RGB")
        else:
            raw = ctypes.string_at(data, pitch * h)
            mode = "BGR;16" if self.fmt == 2 else "BGR;15"
            self.frame = Image.frombytes("RGB", (w, h), raw, "raw", mode, pitch)

    def _input(self, port, device, index, ident):
        return 1 if (port == 0 and device == RETRO_DEVICE_JOYPAD and ident in self.keys) else 0

    def run(self, frames):
        for _ in range(frames):
            self.lib.retro_run()

    def tap(self, button, hold=6, gap=6):
        name = ALIASES.get(button, button)
        self.keys.add(BUTTONS[name])
        self.run(hold)
        self.keys.discard(BUTTONS[name])
        self.run(gap)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rom")
    ap.add_argument("--core", default=os.environ.get("WS_CORE", ""))
    ap.add_argument("--script", default="900")
    ap.add_argument("--out", default="shots")
    ap.add_argument("--scale", type=int, default=3)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    emu = Emulator(args.core, args.rom)
    for i, step in enumerate(args.script.split(",")):
        frames, _, button = step.partition(":")
        emu.run(int(frames))
        if button:
            emu.tap(button)
        if emu.frame:
            im = emu.frame
            im.resize((im.width * args.scale, im.height * args.scale), Image.NEAREST).save(out / f"{i:02d}_{step.replace(':', '_')}.png")
    print(f"{len(list(out.glob('*.png')))} screenshots -> {out}")


if __name__ == "__main__":
    main()
