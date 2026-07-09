#!/usr/bin/env python3
"""Clean-room AGI resource directory and volume helpers.

This module is intentionally format-focused: it models only the resource
container behavior observed from local interpreter disassembly and local game
files in this repository.  It supports the SQ2-style split directory/5-byte
volume records and the Gold Rush-style combined directory/7-byte records.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal


ResourceKind = Literal["logic", "picture", "view", "sound"]

KIND_ORDER: tuple[ResourceKind, ...] = ("logic", "picture", "view", "sound")
SPLIT_DIR_NAMES: dict[ResourceKind, str] = {
    "logic": "LOGDIR",
    "picture": "PICDIR",
    "view": "VIEWDIR",
    "sound": "SNDDIR",
}


class ResourceFormatError(ValueError):
    """Raised when a local resource file does not match the observed format."""


@dataclass(frozen=True)
class ResourceEntry:
    volume: int
    offset: int
    raw: bytes


@dataclass(frozen=True)
class ResourceDirectoryLayout:
    version: Literal["v2_split", "v3_combined"]
    prefix: str
    directory_path: Path | None = None
    section_offsets: dict[ResourceKind, int] | None = None
    section_ends: dict[ResourceKind, int] | None = None


@dataclass(frozen=True)
class VolumeRecord:
    kind: ResourceKind
    number: int
    entry: ResourceEntry
    header: bytes
    expanded_length: int
    stored_length: int
    transform: Literal["direct", "lzw_like", "picture_nibble"]
    payload: bytes


def u16le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def _child_case_insensitive(directory: Path, name: str) -> Path:
    candidate = directory / name
    if candidate.exists():
        return candidate
    wanted = name.upper()
    for child in directory.iterdir():
        if child.name.upper() == wanted:
            return child
    raise FileNotFoundError(candidate)


def _combined_dir_is_plausible(data: bytes) -> bool:
    if len(data) < 8:
        return False
    offsets = [u16le(data, index * 2) for index in range(4)]
    if offsets[0] != 8:
        return False
    if any(offset < 8 or offset > len(data) for offset in offsets):
        return False
    if offsets != sorted(offsets):
        return False
    ends = offsets[1:] + [len(data)]
    return all((end - start) % 3 == 0 for start, end in zip(offsets, ends))


def detect_layout(game_dir: Path) -> ResourceDirectoryLayout:
    game_dir = Path(game_dir)
    try:
        split_dirs_present = all(
            _child_case_insensitive(game_dir, name).exists()
            for name in SPLIT_DIR_NAMES.values()
        )
    except FileNotFoundError:
        split_dirs_present = False
    if split_dirs_present:
        return ResourceDirectoryLayout("v2_split", "")

    for path in sorted(game_dir.iterdir()):
        name = path.name
        upper = name.upper()
        if not path.is_file() or not upper.endswith("DIR"):
            continue
        if upper in set(SPLIT_DIR_NAMES.values()):
            continue
        data = path.read_bytes()
        if not _combined_dir_is_plausible(data):
            continue
        offsets = {kind: u16le(data, index * 2) for index, kind in enumerate(KIND_ORDER)}
        ends = dict(zip(KIND_ORDER, [offsets["picture"], offsets["view"], offsets["sound"], len(data)]))
        return ResourceDirectoryLayout("v3_combined", name[:-3], path, offsets, ends)

    raise ResourceFormatError(f"could not detect AGI resource directory layout in {game_dir}")


def _parse_entry(raw: bytes, *, exact_absent: bool) -> ResourceEntry | None:
    if len(raw) != 3:
        raise ResourceFormatError(f"directory entry must be 3 bytes, got {len(raw)}")
    if exact_absent:
        if raw == b"\xff\xff\xff":
            return None
    elif raw[0] >> 4 == 0x0F:
        return None
    volume = raw[0] >> 4
    offset = ((raw[0] & 0x0F) << 16) | (raw[1] << 8) | raw[2]
    return ResourceEntry(volume, offset, raw)


def read_directory_entries(game_dir: Path, kind: ResourceKind) -> list[ResourceEntry | None]:
    layout = detect_layout(game_dir)
    if layout.version == "v2_split":
        data = _child_case_insensitive(Path(game_dir), SPLIT_DIR_NAMES[kind]).read_bytes()
        exact_absent = False
    else:
        if layout.directory_path is None or layout.section_offsets is None or layout.section_ends is None:
            raise ResourceFormatError("combined directory layout missing section offsets")
        all_data = layout.directory_path.read_bytes()
        data = all_data[layout.section_offsets[kind] : layout.section_ends[kind]]
        exact_absent = True

    entries: list[ResourceEntry | None] = []
    for offset in range(0, len(data), 3):
        chunk = data[offset : offset + 3]
        if len(chunk) < 3:
            break
        entries.append(_parse_entry(chunk, exact_absent=exact_absent))
    return entries


def volume_path(game_dir: Path, layout: ResourceDirectoryLayout, volume: int) -> Path:
    if layout.version == "v2_split":
        name = f"VOL.{volume}"
    else:
        name = f"{layout.prefix}VOL.{volume}"
    return _child_case_insensitive(Path(game_dir), name)


def decode_lzw_like(stored: bytes, expected_length: int | None = None) -> bytes:
    """Expand the GR v3 general resource stream observed at image offset 0x07f4."""
    source = stored + b"\x00\x00\x00"
    bitpos = 0
    width = 9
    limit = 0x200
    next_code = 0x102
    previous_code = 0
    first_byte = 0
    dictionary: dict[int, bytes] = {}
    output = bytearray()

    def read_code() -> int:
        nonlocal bitpos
        bytepos = bitpos >> 3
        if bytepos + 2 >= len(source):
            raise ResourceFormatError("compressed stream ended before end code")
        value = source[bytepos] | (source[bytepos + 1] << 8) | (source[bytepos + 2] << 16)
        value >>= bitpos & 7
        bitpos += width
        return value & ((1 << width) - 1)

    while True:
        code = read_code()
        if code == 0x101:
            break
        if code == 0x100:
            width = 9
            limit = 0x200
            next_code = 0x102
            dictionary.clear()
            code = read_code()
            if code == 0x101:
                break
            data = bytes([code & 0xFF]) if code < 0x100 else dictionary[code]
            output.extend(data)
            previous_code = code
            first_byte = data[0]
            continue

        if code < 0x100:
            data = bytes([code])
        elif code in dictionary:
            data = dictionary[code]
        elif code >= next_code:
            previous = bytes([previous_code & 0xFF]) if previous_code < 0x100 else dictionary[previous_code]
            data = previous + bytes([first_byte])
        else:
            raise ResourceFormatError(f"unknown dictionary code {code:#x}")

        output.extend(data)
        first_byte = data[0]
        previous = bytes([previous_code & 0xFF]) if previous_code < 0x100 else dictionary[previous_code]
        dictionary[next_code] = previous + bytes([first_byte])
        next_code += 1
        previous_code = code

        if next_code >= limit and width != 11:
            width += 1
            limit <<= 1
        if expected_length is not None and len(output) > expected_length:
            raise ResourceFormatError(
                f"expanded stream exceeded expected length {expected_length}"
            )

    result = bytes(output)
    if expected_length is not None and len(result) != expected_length:
        raise ResourceFormatError(
            f"expanded length {len(result)} does not match expected {expected_length}"
        )
    return result


def decode_picture_nibbles(stored: bytes, expected_length: int | None = None) -> bytes:
    """Expand the GR v3 picture nibble stream observed at image offset 0x9a5b."""
    source = stored + b"\x00\x00"
    index = 0
    phase = 0
    repeat_nibble = False
    output = bytearray()

    while True:
        if index >= len(stored):
            raise ResourceFormatError("picture nibble stream ended before 0xff")
        value = source[index]
        if repeat_nibble:
            nibble_phase = phase & 1
            if nibble_phase == 0:
                value >>= 4
            else:
                value &= 0x0F
            index += nibble_phase
            phase = nibble_phase ^ 1
            repeat_nibble = False
        else:
            index += 1
            if phase & 1:
                word = (source[index] << 8) | value
                word = ((word << 4) | (word >> 12)) & 0xFFFF
                value = word & 0xFF
            repeat_nibble = value in (0xF0, 0xF2)

        output.append(value)
        if value == 0xFF:
            break
        if expected_length is not None and len(output) > expected_length:
            raise ResourceFormatError(
                f"expanded picture stream exceeded expected length {expected_length}"
            )

    result = bytes(output)
    if expected_length is not None and len(result) != expected_length:
        raise ResourceFormatError(
            f"expanded picture length {len(result)} does not match expected {expected_length}"
        )
    return result


def read_volume_record(game_dir: Path, kind: ResourceKind, number: int) -> VolumeRecord:
    game_dir = Path(game_dir)
    layout = detect_layout(game_dir)
    entries = read_directory_entries(game_dir, kind)
    if number >= len(entries):
        raise IndexError(f"{kind} {number} is beyond directory length {len(entries)}")
    entry = entries[number]
    if entry is None:
        raise ResourceFormatError(f"{kind} {number} is absent")

    volume_data = volume_path(game_dir, layout, entry.volume).read_bytes()
    if layout.version == "v2_split":
        header = volume_data[entry.offset : entry.offset + 5]
        if len(header) != 5 or header[0:2] != b"\x12\x34" or header[2] != entry.volume:
            raise ResourceFormatError(f"bad v2 volume header for {kind} {number}")
        length = u16le(header, 3)
        start = entry.offset + 5
        payload = volume_data[start : start + length]
        if len(payload) != length:
            raise ResourceFormatError(f"short v2 payload for {kind} {number}")
        return VolumeRecord(kind, number, entry, header, length, length, "direct", payload)

    header = volume_data[entry.offset : entry.offset + 7]
    if len(header) != 7 or header[0:2] != b"\x12\x34":
        raise ResourceFormatError(f"bad v3 volume header for {kind} {number}")
    metadata = header[2]
    transform = "direct"
    volume_byte = metadata
    if metadata & 0x80:
        transform = "picture_nibble"
        volume_byte = metadata & 0x0F
    if volume_byte != entry.volume:
        raise ResourceFormatError(
            f"volume byte {volume_byte:#x} does not match entry volume {entry.volume:#x}"
        )
    expanded_length = u16le(header, 3)
    stored_length = u16le(header, 5)
    start = entry.offset + 7
    stored = volume_data[start : start + stored_length]
    if len(stored) != stored_length:
        raise ResourceFormatError(f"short v3 stored payload for {kind} {number}")
    if transform == "picture_nibble":
        payload = decode_picture_nibbles(stored, expanded_length)
    elif expanded_length == stored_length:
        payload = stored
    else:
        transform = "lzw_like"
        payload = decode_lzw_like(stored, expanded_length)
    return VolumeRecord(
        kind,
        number,
        entry,
        header,
        expanded_length,
        stored_length,
        transform,
        payload,
    )


def read_resource_payload(game_dir: Path, kind: ResourceKind, number: int) -> bytes:
    return read_volume_record(game_dir, kind, number).payload


def iter_present_entries(game_dir: Path, kind: ResourceKind) -> Iterable[tuple[int, ResourceEntry]]:
    for number, entry in enumerate(read_directory_entries(game_dir, kind)):
        if entry is not None:
            yield number, entry


def main() -> None:
    from project_paths import game_dir as configured_game_dir

    selected_game_dir = configured_game_dir()
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true", help="print directory/record summary")
    parser.add_argument("--kind", choices=KIND_ORDER, help="resource kind to inspect")
    parser.add_argument("--number", type=int, help="resource number to inspect")
    args = parser.parse_args()

    layout = detect_layout(selected_game_dir)
    print(f"layout={layout.version} prefix={layout.prefix!r}")

    if args.summary:
        for kind in KIND_ORDER:
            entries = read_directory_entries(selected_game_dir, kind)
            present = [entry for entry in entries if entry is not None]
            volumes = sorted({entry.volume for entry in present})
            print(f"{kind}: entries={len(entries)} present={len(present)} volumes={volumes}")

    if args.kind is not None and args.number is not None:
        record = read_volume_record(selected_game_dir, args.kind, args.number)
        print(
            f"{args.kind} {args.number}: volume={record.entry.volume} "
            f"offset={record.entry.offset:#x} transform={record.transform} "
            f"stored={record.stored_length} expanded={record.expanded_length}"
        )
        print("header=" + record.header.hex(" "))
        print("payload_head=" + record.payload[:32].hex(" "))


if __name__ == "__main__":
    main()
