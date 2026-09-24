"""WonderSwan ROM container: header, banks and far-pointer helpers."""
import struct
from pathlib import Path

BANK = 0x10000


class Rom:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        if len(self.data) % BANK:
            raise ValueError(f"{path}: size is not a multiple of 64 KiB")
        self.nbanks = len(self.data) // BANK

    def bank(self, n):
        return self.data[n * BANK:(n + 1) * BANK]

    def header(self):
        h = self.data[-10:]
        stored = h[8] | h[9] << 8
        return {
            "developer_id": h[0],
            "color": bool(h[1]),
            "game_id": h[2],
            "version": h[3],
            "rom_size_code": h[4],
            "save_type": h[5],
            "flags": h[6],
            "rtc": h[7],
            "checksum_stored": stored,
            "checksum_computed": sum(self.data[:-2]) & 0xFFFF,
            "size": len(self.data),
            "banks": self.nbanks,
        }

    def linear_base(self, bank):
        """Linear address where `bank` shows up in the fixed 0x40000+ window, or None."""
        first_linear = self.nbanks - 12
        if bank < first_linear:
            return None
        return (bank - self.nbanks + 16) << 16


def far_ptr(buf, off, base):
    """Decode a normalized offset:segment pointer into an offset relative to `base`."""
    o, s = struct.unpack_from("<HH", buf, off)
    if o == 0 and s == 0:
        return None
    if o >= 16:
        return -1
    lin = s * 16 + o - base
    return lin if 0 <= lin < BANK else -1


def default_dump_dir(rom_path):
    """<rom folder>/<rom name>, or the same folder name one level up when the ROMs were
    moved into a sub-folder next to their dumps."""
    rom_path = Path(rom_path)
    here = rom_path.with_suffix("")
    up = rom_path.parent.parent / rom_path.stem
    return up if up.is_dir() and not here.is_dir() else here
