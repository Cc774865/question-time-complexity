"""Turn W9-zkcc-18正课.docx into the calibration skill's markdown pair."""

from __future__ import annotations

import re
import struct
import zipfile
from pathlib import Path

from lxml import etree

DOCX = Path(r"c:\Users\PC\Downloads\W9-zkcc-18正课.docx")
OUT = Path(__file__).resolve().parent


class Reader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def remaining(self) -> int:
        return len(self.data) - self.pos

    def u8(self) -> int:
        value = self.data[self.pos]
        self.pos += 1
        return value

    def u16(self) -> int:
        value = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return value

    def unsigned(self) -> int:
        value = self.u8()
        return self.u16() if value == 255 else value

    def signed(self) -> int:
        value = self.u8()
        return self.u16() - 32768 if value == 255 else value - 128

    def cstring(self) -> str:
        end = self.data.index(b"\x00", self.pos)
        text = self.data[self.pos : end].decode("latin1", "replace")
        self.pos = end + 1
        return text

    def nudge(self) -> None:
        if self.u8() == 128 and self.u8() == 128:
            self.pos += 4

    def skip_dim_array(self) -> None:
        count = self.u8()
        pending: list[int] = []

        def take() -> int:
            if not pending:
                byte = self.u8()
                pending.extend((byte >> 4, byte & 0x0F))
            return pending.pop(0)

        for _ in range(count):
            take()
            while take() != 0xF:
                pass


def equation_native(data: bytes) -> bytes:
    if data[:8] != bytes.fromhex("d0cf11e0a1b11ae1"):
        return data
    sector = 1 << struct.unpack_from("<H", data, 0x1E)[0]
    mini = 1 << struct.unpack_from("<H", data, 0x20)[0]
    dir_start = struct.unpack_from("<I", data, 0x30)[0]
    cutoff = struct.unpack_from("<I", data, 0x38)[0]
    minifat_start = struct.unpack_from("<I", data, 0x3C)[0]
    minifat_count = struct.unpack_from("<I", data, 0x40)[0]
    difat = list(struct.unpack_from("<109I", data, 0x4C))
    fat: list[int] = []
    for sec in difat:
        if sec >= 0xFFFFFFFE:
            break
        off = (sec + 1) * sector
        fat.extend(struct.unpack_from("<" + "I" * (sector // 4), data, off))

    def chain(start: int) -> list[int]:
        out: list[int] = []
        seen: set[int] = set()
        while start < 0xFFFFFFF8 and start not in seen:
            seen.add(start)
            out.append(start)
            start = fat[start]
        return out

    def read_sectors(start: int, size: int) -> bytes:
        buf = b"".join(data[(i + 1) * sector : (i + 2) * sector] for i in chain(start))
        return buf[:size]

    directory = b"".join(data[(i + 1) * sector : (i + 2) * sector] for i in chain(dir_start))
    entries: list[tuple[str, int, int]] = []
    for index in range(0, len(directory), 128):
        entry = directory[index : index + 128]
        name_len = struct.unpack_from("<H", entry, 64)[0]
        if name_len == 0:
            continue
        name = entry[: name_len - 2].decode("utf-16le", "replace")
        start = struct.unpack_from("<I", entry, 116)[0]
        size = struct.unpack_from("<I", entry, 120)[0]
        entries.append((name, start, size))
    ministream = read_sectors(entries[0][1], entries[0][2])
    minifat_blob = read_sectors(minifat_start, minifat_count * sector)
    minifat = list(struct.unpack_from("<" + "I" * (len(minifat_blob) // 4), minifat_blob))

    def read_mini(start: int, size: int) -> bytes:
        buf = b""
        seen: set[int] = set()
        while start < 0xFFFFFFF8 and start not in seen and len(buf) < size:
            seen.add(start)
            buf += ministream[start * mini : (start + 1) * mini]
            start = minifat[start]
        return buf[:size]

    for name, start, size in entries:
        if name == "Equation Native":
            return read_mini(start, size) if size < cutoff else read_sectors(start, size)
    return b""


FENCE = {0: ("〈", "〉"), 1: ("(", ")"), 2: ("{", "}"), 3: ("[", "]"), 4: ("|", "|")}
MT = {0x2212: "-", 0x00D7: "×", 0x2264: "≤", 0x2265: "≥", 0x2220: "∠", 0x25B3: "△", 0x2225: "∥", 0x2245: "≅", 0x2250: "≌", 0x00B0: "°"}


def mt_char(code: int) -> str:
    if code in MT:
        return MT[code]
    if 32 <= code < 0xE000:
        return chr(code)
    return ""


def parse_list(reader: Reader, parts: list[str]) -> None:
    while reader.remaining() > 0:
        record = reader.u8()
        if record == 0:
            return
        if record >= 100:
            reader.pos += reader.unsigned()
            continue
        if not parse_record(reader, record, parts):
            return


def parse_record(reader: Reader, record: int, parts: list[str]) -> bool:
    if record == 1:
        options = reader.u8()
        if options & 0x08:
            reader.nudge()
        if options & 0x04:
            reader.u16()
        if options & 0x02:
            if reader.u8() != 7:
                return False
            reader.pos += reader.u8() * 3
        if not options & 0x01:
            parse_list(reader, parts)
        return True
    if record == 2:
        options = reader.u8()
        if options & 0x08:
            reader.nudge()
        reader.signed()
        code = None if options & 0x20 else reader.u16()
        if options & 0x04:
            reader.u8()
        if options & 0x10:
            reader.u16()
        if options & 0x01:
            parse_list(reader, parts)
        if code is not None:
            parts.append(mt_char(code))
        return True
    if record == 3:
        options = reader.u8()
        if options & 0x08:
            reader.nudge()
        selector = reader.u8()
        variation = reader.u8()
        if variation & 0x80:
            variation = (variation & 0x7F) | (reader.u8() << 8)
        if selector <= 9 or selector == 15:
            reader.u8()
        slot: list[str] = []
        parse_list(reader, slot)
        body = "".join(slot)
        if selector in FENCE:
            left, right = FENCE[selector]
            parts.append((left if variation & 1 else "") + body + (right if variation & 2 else ""))
        elif selector == 11:
            parts.append("(" + body + ")")
        else:
            parts.append(body)
        return True
    if record == 4:
        options = reader.u8()
        if options & 0x08:
            reader.nudge()
        reader.u8()
        reader.u8()
        if options & 0x02:
            if reader.u8() != 7:
                return False
            reader.pos += reader.u8() * 3
        parse_list(reader, parts)
        return True
    if record in (6, 8, 9, 15, 16, 17, 18, 19) or 10 <= record <= 14:
        if record == 6:
            options = reader.u8()
            if options & 0x08:
                reader.nudge()
            reader.u8()
        elif record == 8:
            reader.unsigned()
            reader.u8()
        elif record == 9:
            kind = reader.u8()
            if kind == 101:
                reader.u16()
            elif kind == 100:
                reader.u8()
                reader.u16()
        elif 10 <= record <= 14:
            pass
        elif record == 15:
            reader.unsigned()
        elif record == 16:
            options = reader.u8()
            reader.pos += 8 if options & 1 else 6
            if options & 4:
                reader.cstring()
        elif record == 17:
            reader.unsigned()
            reader.cstring()
        elif record == 18:
            reader.u8()
            reader.skip_dim_array()
            reader.skip_dim_array()
            for _ in range(reader.u8()):
                if reader.unsigned():
                    reader.u8()
        elif record == 19:
            reader.cstring()
        return True
    if record == 5:
        options = reader.u8()
        if options & 0x08:
            reader.nudge()
        reader.pos += 3
        rows, cols = reader.u8(), reader.u8()
        reader.pos += (rows + 1 + 3) // 4 + (cols + 1 + 3) // 4
        parse_list(reader, parts)
        return True
    if record == 7:
        reader.pos += reader.u8() * 3
        return True
    return False


def equation_text(blob: bytes) -> str:
    start = blob.find(b"\x05\x01\x00\x07\x04DSMT")
    if start < 0:
        return ""
    reader = Reader(blob)
    reader.pos = start + 5
    reader.cstring()
    reader.u8()
    parts: list[str] = []
    try:
        parse_list(reader, parts)
    except Exception:
        return "".join(parts)
    return "".join(parts)


def paragraphs(path: Path) -> list[str]:
    archive = zipfile.ZipFile(path)
    rels = etree.fromstring(archive.read("word/_rels/document.xml.rels"))
    targets = {rel.get("Id"): rel.get("Target") for rel in rels}
    root = etree.fromstring(archive.read("word/document.xml"))
    r_id = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    lines: list[str] = []
    for para in root.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body/{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        parts: list[str] = []
        for node in para.iter():
            tag = node.tag.split("}")[-1]
            if tag == "t" and node.text:
                parts.append(node.text)
            elif tag == "OLEObject":
                target = targets.get(node.get(r_id), "")
                if target.endswith(".bin"):
                    try:
                        parts.append(equation_text(equation_native(archive.read("word/" + target))))
                    except Exception:
                        parts.append("")
        text = "".join(parts).strip()
        if text:
            lines.append(text)
    return lines


def tier_of(label: str) -> str:
    match = re.search(r"(\d+)\s*星", label) or re.search(r"(\d+)\s*star", label, re.I)
    if not match:
        return "中等"
    star = int(match.group(1))
    if star <= 3:
        return "简单"
    if star <= 5:
        return "中等"
    return "困难"


def qtype_of(stem: str) -> str:
    if re.search(r"A[.．、].{0,12}B[.．、]", stem):
        return "选择"
    if "求证" in stem or "证明" in stem:
        return "证明"
    if "____" in stem or "＿" in stem or "______" in stem:
        return "填空"
    return "解答"


def questions_from(lines: list[str]) -> list[dict]:
    items: list[dict] = []
    current: dict | None = None
    mode = ""
    pending = ""

    def open_item(label: str) -> None:
        nonlocal current, mode
        current = {"label": label, "stem": [], "answer": [], "sol": [], "dist": []}
        items.append(current)
        mode = ""

    for line in lines:
        if line.startswith(("周次", "使用年级", "课次", "题目类型", "课件 ID")):
            continue
        if re.fullmatch(r"\d+星-[例练]", line) or line.endswith("作业题"):
            open_item(line.removesuffix("题") if line.endswith("作业题") else line)
            pending = ""
            continue
        if line == "晋级题":
            pending = "晋级"
            continue
        star = re.fullmatch(r"星级\s*(\d+)star", line, re.I)
        if star and pending == "晋级":
            pending = f"晋级{star.group(1)}星"
            continue
        if line == "题目":
            if pending:
                open_item(pending)
                pending = ""
            mode = "stem"
            continue
        if line == "答案":
            mode = "answer"
            continue
        if line == "解析":
            mode = "sol"
            continue
        if line == "解题方法":
            mode = "dist"
            continue
        if current and mode:
            current[mode].append(line)
    return [item for item in items if any(item["stem"])]


def main() -> None:
    items = questions_from(paragraphs(DOCX))
    stu: list[str] = ["# W9-zkcc-18 学生卷", ""]
    ans: list[str] = ["# W9-zkcc-18 解析卷", ""]
    for number, item in enumerate(items, 1):
        stem = "\n".join(item["stem"]).replace("##", "")
        stu.append(f"> 📌 来源：`W9-zkcc-18正课.docx` · {item['label']}")
        stu.append(f"> 难度：{tier_of(item['label'])}　题型：{qtype_of(stem)}")
        stu.append(f"{number}.（0分）{stem}")
        stu.append("")
        stu.append("---")
        stu.append("")
        sol = "\n".join(item["answer"] + item["sol"]) or "（课件解析为空）"
        dist = "\n".join(item["dist"]) or "课件未单列区分点"
        ans.append(f"**{number}. {item['label']}**")
        ans.append(f"【解析】{sol}")
        ans.append(f"【区分点】{dist}")
        ans.append("")
    (OUT / "stu.md").write_text("\n".join(stu), encoding="utf-8")
    (OUT / "ans.md").write_text("\n".join(ans), encoding="utf-8")
    print(f"questions {len(items)}")
    for number, item in enumerate(items, 1):
        print(f"{number:02d} {item['label']} {tier_of(item['label'])} {qtype_of(chr(10).join(item['stem']))}")


if __name__ == "__main__":
    main()
