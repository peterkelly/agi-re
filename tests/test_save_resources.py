#!/usr/bin/env python3
"""Tests for clean-room save-game file parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_save import (  # noqa: E402
    GR_V3_OBJECT_INVENTORY_XOR_KEY,
    SAVE_HEADER_LENGTH,
    SaveBlock,
    SaveGame,
    SavePathValidationPlan,
    SOURCE_BACKED_FIXED_BLOCK_LENGTHS,
    gr_v3_object_inventory_save_xor,
    load_save,
    parse_save,
    save_path_validation_plan,
    serialize_save,
    xor_with_repeating_key,
)
from disassemble_logic import SQ2  # noqa: E402


def sq2_save_paths() -> list[Path]:
    return sorted(
        SQ2.glob("SQ2SG.*"),
        key=lambda path: int(path.suffix[1:]) if path.suffix[1:].isdigit() else 999,
    )


class SaveResourceTests(unittest.TestCase):
    def test_sq2_save_files_match_source_backed_block_envelope(self) -> None:
        paths = sq2_save_paths()
        self.assertEqual(len(paths), 11)
        for path in paths:
            with self.subTest(save=path.name):
                save = load_save(path)
                self.assertEqual(len(save.header), SAVE_HEADER_LENGTH)
                self.assertEqual(len(save.blocks), 5)
                self.assertEqual(
                    tuple(block.length for block in save.blocks[:4]),
                    SOURCE_BACKED_FIXED_BLOCK_LENGTHS,
                )
                self.assertGreater(save.blocks[4].length, 0)
                self.assertEqual(save.blocks[0].data_offset, SAVE_HEADER_LENGTH + 2)
                expected_size = SAVE_HEADER_LENGTH + sum(2 + block.length for block in save.blocks)
                self.assertEqual(path.stat().st_size, expected_size)

    def test_sq2_save_files_serialize_byte_for_byte(self) -> None:
        paths = sq2_save_paths()
        self.assertEqual(len(paths), 11)
        for path in paths:
            with self.subTest(save=path.name):
                self.assertEqual(serialize_save(load_save(path)), path.read_bytes())

    def test_save_description_is_header_prefix(self) -> None:
        save = load_save(SQ2 / "SQ2SG.2")
        self.assertEqual(save.description, "before entering lake")
        self.assertEqual(save.description_bytes, b"before entering lake")

    def test_truncated_block_is_rejected(self) -> None:
        data = bytearray(b"description\0".ljust(SAVE_HEADER_LENGTH, b"\0"))
        data.extend((4).to_bytes(2, "little"))
        data.extend(b"xy")
        with self.assertRaisesRegex(ValueError, "block 0 is truncated"):
            parse_save(bytes(data))

    def test_trailing_bytes_are_rejected(self) -> None:
        data = bytearray(b"description\0".ljust(SAVE_HEADER_LENGTH, b"\0"))
        for _ in range(5):
            data.extend((0).to_bytes(2, "little"))
        data.extend(b"x")
        with self.assertRaisesRegex(ValueError, "trailing bytes"):
            parse_save(bytes(data))

    def test_serializer_rejects_structural_mismatches(self) -> None:
        header = b"description\0".ljust(SAVE_HEADER_LENGTH, b"\0")
        blocks = tuple(SaveBlock(i, 0, 0, 0, b"") for i in range(5))

        with self.assertRaisesRegex(ValueError, "31 bytes"):
            serialize_save(SaveGame(None, header[:-1], blocks))

        with self.assertRaisesRegex(ValueError, "exactly 5"):
            serialize_save(SaveGame(None, header, blocks[:4]))

        mismatched_length = (
            SaveBlock(0, 0, 0, 1, b""),
            *blocks[1:],
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            serialize_save(SaveGame(None, header, mismatched_length))

        mismatched_index = (
            blocks[0],
            SaveBlock(99, 0, 0, 0, b""),
            *blocks[2:],
        )
        with self.assertRaisesRegex(ValueError, "mismatched index"):
            serialize_save(SaveGame(None, header, mismatched_index))

    def test_save_path_validation_plan_models_source_string_edges(self) -> None:
        self.assertEqual(
            save_path_validation_plan("   C:\\SQ2\\", current_drive_letter="d"),
            SavePathValidationPlan("C:\\SQ2", "find_directory", "c", False, True),
        )
        self.assertEqual(
            save_path_validation_plan("", current_directory="\\SQ2", current_drive_letter="c"),
            SavePathValidationPlan("\\SQ2", "find_directory", "c", True, False),
        )
        self.assertEqual(
            save_path_validation_plan("", current_directory="\\", current_drive_letter="c"),
            SavePathValidationPlan("\\", "single_separator_accept", "c", True, False),
        )
        self.assertEqual(
            save_path_validation_plan("/", current_drive_letter="e"),
            SavePathValidationPlan("/", "single_separator_accept", "e", False, False),
        )
        self.assertEqual(
            save_path_validation_plan("A:\\", current_drive_letter="c"),
            SavePathValidationPlan("A:", "drive_available", "a", False, True),
        )

    def test_gr_v3_object_inventory_xor_round_trips(self) -> None:
        plain = bytes(range(128))
        encoded = gr_v3_object_inventory_save_xor(plain)

        self.assertNotEqual(encoded, plain)
        self.assertEqual(gr_v3_object_inventory_save_xor(encoded), plain)

    def test_gr_v3_object_inventory_xor_uses_observed_59_byte_key(self) -> None:
        self.assertEqual(len(GR_V3_OBJECT_INVENTORY_XOR_KEY), 59)
        plain = bytes(range(61))
        encoded = gr_v3_object_inventory_save_xor(plain)

        self.assertEqual(encoded[0], plain[0] ^ GR_V3_OBJECT_INVENTORY_XOR_KEY[0])
        self.assertEqual(encoded[58], plain[58] ^ GR_V3_OBJECT_INVENTORY_XOR_KEY[58])
        self.assertEqual(encoded[59], plain[59] ^ GR_V3_OBJECT_INVENTORY_XOR_KEY[0])

    def test_xor_with_repeating_key_rejects_empty_key(self) -> None:
        with self.assertRaises(ValueError):
            xor_with_repeating_key(b"data", b"")


if __name__ == "__main__":
    unittest.main()
