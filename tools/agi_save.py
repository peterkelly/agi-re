#!/usr/bin/env python3
"""Clean-room helpers for SQ2 save-game files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SAVE_HEADER_LENGTH = 0x1F
SAVE_BLOCK_COUNT = 5
SOURCE_BACKED_FIXED_BLOCK_LENGTHS = (0x05E1, 0x0387, 0x0148, 0x00C8)
SAVE_PATH_SEPARATORS = "\\/"


@dataclass(frozen=True)
class SavePathValidationPlan:
    effective_path: str
    check_kind: str
    drive_letter: str
    used_default_directory: bool
    stripped_trailing_separator: bool


@dataclass(frozen=True)
class SaveBlock:
    index: int
    length_prefix_offset: int
    data_offset: int
    length: int
    data: bytes


@dataclass(frozen=True)
class SaveGame:
    path: Path | None
    header: bytes
    blocks: tuple[SaveBlock, ...]

    @property
    def description_bytes(self) -> bytes:
        return self.header.split(b"\0", 1)[0]

    @property
    def description(self) -> str:
        return self.description_bytes.decode("ascii", errors="replace")


def u16le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def u16le_bytes(value: int) -> bytes:
    if value < 0 or value > 0xFFFF:
        raise ValueError(f"value does not fit in a save-file length prefix: {value}")
    return bytes((value & 0xFF, value >> 8))


def _source_lower_drive(char: str) -> str:
    if "A" <= char <= "Z":
        return chr(ord(char) + 0x20)
    return char


def save_path_validation_plan(
    text: str,
    *,
    current_directory: str = "\\",
    current_drive_letter: str = "c",
) -> SavePathValidationPlan:
    """Model the source-level path normalization before DOS availability checks."""
    pos = 0
    while pos < len(text) and text[pos] == " ":
        pos += 1
    effective = text[pos:]
    used_default = False
    if effective == "":
        effective = current_directory
        used_default = True

    stripped = False
    if len(effective) > 1 and effective[-1] in SAVE_PATH_SEPARATORS:
        effective = effective[:-1]
        stripped = True

    if len(effective) >= 2 and effective[1] == ":":
        drive_letter = _source_lower_drive(effective[0])
    else:
        drive_letter = current_drive_letter

    if len(effective) == 1 and effective in SAVE_PATH_SEPARATORS:
        check_kind = "single_separator_accept"
    elif len(effective) == 2 and effective[1] == ":":
        check_kind = "drive_available"
    else:
        check_kind = "find_directory"

    return SavePathValidationPlan(effective, check_kind, drive_letter, used_default, stripped)


def parse_save(data: bytes, *, path: Path | None = None) -> SaveGame:
    if len(data) < SAVE_HEADER_LENGTH:
        raise ValueError("save file is too short for the 31-byte header")
    header = data[:SAVE_HEADER_LENGTH]
    pos = SAVE_HEADER_LENGTH
    blocks: list[SaveBlock] = []
    for block_index in range(SAVE_BLOCK_COUNT):
        length_prefix_offset = pos
        if pos + 2 > len(data):
            raise ValueError(f"save block {block_index} has no length prefix")
        length = u16le(data, pos)
        pos += 2
        data_offset = pos
        end = pos + length
        if end > len(data):
            raise ValueError(f"save block {block_index} is truncated")
        blocks.append(
            SaveBlock(
                block_index,
                length_prefix_offset,
                data_offset,
                length,
                data[pos:end],
            )
        )
        pos = end
    if pos != len(data):
        raise ValueError("save file has trailing bytes after the fifth block")
    return SaveGame(path, header, tuple(blocks))


def load_save(path: Path) -> SaveGame:
    return parse_save(path.read_bytes(), path=path)


def serialize_save(save: SaveGame) -> bytes:
    if len(save.header) != SAVE_HEADER_LENGTH:
        raise ValueError("save header must be exactly 31 bytes")
    if len(save.blocks) != SAVE_BLOCK_COUNT:
        raise ValueError("save file envelope must contain exactly 5 save blocks")

    data = bytearray(save.header)
    for expected_index, block in enumerate(save.blocks):
        if block.index != expected_index:
            raise ValueError(
                f"save block {expected_index} has mismatched index {block.index}"
            )
        if block.length != len(block.data):
            raise ValueError(
                f"save block {block.index} length prefix {block.length} "
                f"does not match {len(block.data)} data bytes"
            )
        data.extend(u16le_bytes(block.length))
        data.extend(block.data)
    return bytes(data)


def write_save(save: SaveGame, path: Path) -> None:
    path.write_bytes(serialize_save(save))
