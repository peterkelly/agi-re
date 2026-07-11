#!/usr/bin/env python3
"""Audit picture pattern-command code and data across explicit local games."""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from compare_gr_sq2_static import mz_image, u16le
from decrypt_agi import transform


PATTERN_COLUMN_VALUES = (
    0x8000,
    0x2000,
    0x0800,
    0x0200,
    0x0080,
    0x0020,
    0x0008,
    0x0002,
)


@dataclass(frozen=True)
class PictureScanner:
    address: int
    last_command: int
    dispatch_offset: int


@dataclass(frozen=True)
class BrushAudit:
    game: str
    version: str
    executable: str
    scanner: PictureScanner
    mode_handler: int | None
    plot_handler: int | None
    behavior: str
    mask_offset: int | None
    pointer_offset: int | None
    radius_one: tuple[int, ...]
    max_doubled_x: int | None
    shape_digest: str | None
    code_references_tables: bool


def version_string(data: bytes) -> str:
    match = re.search(rb"Version [0-9.]+", data)
    return match.group(0).decode("ascii") if match is not None else "unknown"


def find_pattern_table_offsets(data: bytes) -> tuple[int, int] | None:
    hits = [
        offset
        for offset in range(max(0, len(data) - 31))
        if all(
            u16le(data, offset + column * 4) == value
            for column, value in enumerate(PATTERN_COLUMN_VALUES)
        )
    ]
    if not hits:
        return None
    if len(hits) != 1:
        raise ValueError(f"found {len(hits)} candidate picture-pattern tables")
    return hits[0], hits[0] + 0x20


def selected_executable(game_dir: Path) -> tuple[Path, bytes]:
    for name in ("AGI", "LL.COM", "SQ.EXE", "AGI.EXE"):
        candidate = game_dir / name
        if not candidate.is_file():
            continue
        data = candidate.read_bytes()
        if data[:2] == b"MZ":
            return candidate, data
        loader = game_dir / "SIERRA.COM"
        if name == "AGI" and loader.is_file():
            decoded = transform(loader.read_bytes(), data)
            if decoded[:2] != b"MZ":
                raise ValueError(f"{game_dir}: decoded AGI is not an MZ executable")
            return candidate, decoded
    raise FileNotFoundError(f"{game_dir}: no supported interpreter executable")


def find_picture_scanner(image: bytes) -> PictureScanner:
    hits: list[PictureScanner] = []
    for offset in range(len(image) - 23):
        chunk = image[offset : offset + 23]
        if not (
            chunk[0:3] == b"\xac\x3c\xff"
            and chunk[3] == 0x74
            and chunk[5:7] == b"\x2c\xf0"
            and chunk[7] == 0x72
            and chunk[9] == 0x3C
            and chunk[11] == 0x77
            and chunk[13:21] == b"\x8a\xd8\x32\xff\xd1\xe3\xff\x97"
        ):
            continue
        last_command = 0xF0 + chunk[10]
        if last_command not in (0xF8, 0xFA):
            continue
        hits.append(PictureScanner(offset, last_command, u16le(chunk, 21)))
    if len(hits) != 1:
        raise ValueError(f"expected one picture scanner, found {len(hits)}")
    return hits[0]


def shape_rows(data: bytes, pointer_offset: int) -> tuple[tuple[int, ...], ...]:
    result: list[tuple[int, ...]] = []
    for radius in range(8):
        rows_offset = u16le(data, pointer_offset + radius * 2)
        result.append(
            tuple(u16le(data, rows_offset + row * 2) for row in range(radius * 2 + 1))
        )
    return tuple(result)


def first_mov_cx_immediate(image: bytes, start: int, end: int) -> int | None:
    for offset in range(start, min(end, len(image) - 2)):
        if image[offset] == 0xB9:
            value = u16le(image, offset + 1)
            if value in (0x013E, 0x0140):
                return value
    return None


def audit_game(game_dir: Path) -> BrushAudit:
    game_dir = game_dir.resolve()
    agidata = (game_dir / "AGIDATA.OVL").read_bytes()
    executable_path, executable = selected_executable(game_dir)
    image = mz_image(executable)
    scanner = find_picture_scanner(image)
    command_count = scanner.last_command - 0xF0 + 1
    if scanner.dispatch_offset + command_count * 2 > len(agidata):
        raise ValueError(f"{game_dir}: picture dispatch table extends beyond AGIDATA")
    handlers = tuple(
        u16le(agidata, scanner.dispatch_offset + index * 2)
        for index in range(command_count)
    )

    if scanner.last_command == 0xF8:
        return BrushAudit(
            game_dir.name,
            version_string(agidata),
            executable_path.name,
            scanner,
            None,
            None,
            "no 0xf9/0xfa dispatch",
            None,
            None,
            (),
            None,
            None,
            False,
        )

    mode_handler = handlers[9]
    plot_handler = handlers[10]
    tables = find_pattern_table_offsets(agidata)
    if tables is None:
        mode_prefix = image[mode_handler : mode_handler + 2]
        behavior = "pixel-only" if mode_prefix == b"\xac\xc3" else "unmapped"
        return BrushAudit(
            game_dir.name,
            version_string(agidata),
            executable_path.name,
            scanner,
            mode_handler,
            plot_handler,
            behavior,
            None,
            None,
            (),
            None,
            None,
            False,
        )

    mask_offset, pointer_offset = tables
    rows = shape_rows(agidata, pointer_offset)
    encoded_mask = mask_offset.to_bytes(2, "little")
    encoded_pointer = pointer_offset.to_bytes(2, "little")
    routine = image[plot_handler : plot_handler + 0x140]
    max_doubled_x = first_mov_cx_immediate(image, plot_handler, plot_handler + 0x100)
    digest_input = b"".join(
        word.to_bytes(2, "little") for radius_rows in rows for word in radius_rows
    )
    radius_one = rows[1]
    behavior = (
        "shaped/stippled, center-row radius 1"
        if radius_one == (0x4000, 0xE000, 0x4000)
        else "shaped/stippled, filled radius 1"
    )
    return BrushAudit(
        game_dir.name,
        version_string(agidata),
        executable_path.name,
        scanner,
        mode_handler,
        plot_handler,
        behavior,
        mask_offset,
        pointer_offset,
        radius_one,
        max_doubled_x,
        hashlib.sha256(digest_input).hexdigest(),
        encoded_mask in routine and encoded_pointer in routine,
    )


def optional_hex(value: int | None) -> str:
    return "-" if value is None else f"`0x{value:04x}`"


def markdown(audits: list[BrushAudit]) -> str:
    lines = [
        "# Cross-Interpreter Picture Brush Audit",
        "",
        "This report is generated only from the explicitly selected local game files.",
        "The command scanner and handler addresses come from each loaded interpreter",
        "image; mask and radius-table offsets come from that game's `AGIDATA.OVL`.",
        "",
        "| Game | Version | Last command | Dispatch table | `0xf9` | `0xfa` | Behavior | Mask table | Radius pointers | X clamp |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for audit in audits:
        lines.append(
            "| "
            + " | ".join(
                (
                    audit.game,
                    audit.version,
                    f"`0x{audit.scanner.last_command:02x}`",
                    f"`0x{audit.scanner.dispatch_offset:04x}`",
                    optional_hex(audit.mode_handler),
                    optional_hex(audit.plot_handler),
                    audit.behavior,
                    optional_hex(audit.mask_offset),
                    optional_hex(audit.pointer_offset),
                    optional_hex(audit.max_doubled_x),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Shape Families",
            "",
        ]
    )
    groups: dict[tuple[str, str | None], list[str]] = {}
    for audit in audits:
        groups.setdefault((audit.behavior, audit.shape_digest), []).append(audit.game)
    for (behavior, digest), games in groups.items():
        suffix = "" if digest is None else f"; shape digest `{digest}`"
        lines.append(f"- {', '.join(games)}: {behavior}{suffix}.")
    lines.extend(
        [
            "",
            "## Structural Checks",
            "",
        ]
    )
    for audit in audits:
        if audit.mask_offset is None:
            continue
        result = "yes" if audit.code_references_tables else "no"
        rows = ", ".join(f"`0x{value:04x}`" for value in audit.radius_one)
        lines.append(
            f"- {audit.game}: pattern routine references selected mask and pointer "
            f"tables: {result}; radius-1 rows: {rows}."
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-dir", action="append", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    audits = [audit_game(game_dir) for game_dir in args.game_dir]
    report = markdown(audits)
    if args.output is None:
        print(report)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="ascii")
        print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
