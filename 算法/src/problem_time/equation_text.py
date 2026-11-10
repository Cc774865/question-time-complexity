"""Turn a MathType object into the characters used for scoring.

The output document keeps the original equation. This text is not written back.
"""

from __future__ import annotations

import struct

_OLE = bytes.fromhex("d0cf11e0a1b11ae1")
_SYMBOL = {
    0x2212: "-",
    0x00D7: "×",
    0x00F7: "÷",
    0x2264: "≤",
    0x2265: "≥",
    0x2260: "≠",
    0x2220: "∠",
    0x25B3: "△",
    0x25B2: "▲",
    0x2225: "∥",
    0x2245: "≅",
    0x2250: "≌",
    0x00B0: "°",
    0x00B1: "±",
    0x22A5: "⊥",
    0x221E: "∞",
}


def equation_text(blob: bytes) -> str:
    """Readable characters from one Equation Native stream or OLE file."""
    native = _equation_native(blob)
    source = native or blob
    chars: list[str] = []
    index = 0
    while index + 4 < len(source):
        if source[index] == 2 and source[index + 1] in (0, 1, 4, 8):
            code = source[index + 3] | (source[index + 4] << 8)
            char = _symbol(code)
            if char:
                chars.append(char)
                index += 5
                continue
        index += 1
    return "".join(chars)


def _symbol(code: int) -> str:
    if code in _SYMBOL:
        return _SYMBOL[code]
    if 32 <= code <= 126:
        return chr(code)
    return ""


def _equation_native(data: bytes) -> bytes:
    if not data.startswith(_OLE):
        return b""
    sector = 1 << struct.unpack_from("<H", data, 0x1E)[0]
    mini = 1 << struct.unpack_from("<H", data, 0x20)[0]
    dir_start = struct.unpack_from("<I", data, 0x30)[0]
    cutoff = struct.unpack_from("<I", data, 0x38)[0]
    minifat_start = struct.unpack_from("<I", data, 0x3C)[0]
    minifat_count = struct.unpack_from("<I", data, 0x40)[0]
    difat = list(struct.unpack_from("<109I", data, 0x4C))
    fat: list[int] = []
    for start in difat:
        if start >= 0xFFFFFFFE:
            break
        offset = (start + 1) * sector
        fat.extend(struct.unpack_from("<" + "I" * (sector // 4), data, offset))

    def chain(start: int) -> list[int]:
        found: list[int] = []
        seen: set[int] = set()
        while start < 0xFFFFFFF8 and start not in seen and start < len(fat):
            seen.add(start)
            found.append(start)
            start = fat[start]
        return found

    def read_sectors(start: int, size: int) -> bytes:
        buf = b"".join(data[(item + 1) * sector : (item + 2) * sector] for item in chain(start))
        return buf[:size]

    directory = read_sectors(dir_start, sector * 8)
    entries: list[tuple[str, int, int]] = []
    for index in range(0, len(directory), 128):
        entry = directory[index : index + 128]
        if len(entry) < 128:
            break
        name_len = struct.unpack_from("<H", entry, 64)[0]
        if name_len < 2:
            continue
        name = entry[: name_len - 2].decode("utf-16le", "replace")
        start = struct.unpack_from("<I", entry, 116)[0]
        size = struct.unpack_from("<I", entry, 120)[0]
        entries.append((name, start, size))
    if not entries:
        return b""
    ministream = read_sectors(entries[0][1], entries[0][2])
    minifat_blob = read_sectors(minifat_start, minifat_count * sector)
    minifat = list(struct.unpack_from("<" + "I" * (len(minifat_blob) // 4), minifat_blob))

    def read_mini(start: int, size: int) -> bytes:
        buf = b""
        seen: set[int] = set()
        while start < 0xFFFFFFF8 and start not in seen and len(buf) < size and start < len(minifat):
            seen.add(start)
            buf += ministream[start * mini : (start + 1) * mini]
            start = minifat[start]
        return buf[:size]

    for name, start, size in entries:
        if name == "Equation Native":
            return read_mini(start, size) if size < cutoff else read_sectors(start, size)
    return b""
