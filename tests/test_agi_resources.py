#!/usr/bin/env python3
"""Tests for clean-room AGI resource container parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_resources import (  # noqa: E402
    KIND_ORDER,
    RetainedResourceFamily,
    ResourceNotRetained,
    decode_lzw_like,
    decode_picture_nibbles,
    discard_resource,
    detect_layout,
    encode_picture_nibbles,
    iter_present_entries,
    read_directory_entries,
    read_volume_record,
    retain_resource,
    ResourceFormatError,
)


SQ2_DIR = ROOT / "games" / "SQ2"
GR_DIR = ROOT / "games" / "GR"
KQ4D_DIR = ROOT / "games" / "KQ4D"


def pack_codes(codes: list[int], width: int = 9) -> bytes:
    value = 0
    bitpos = 0
    for code in codes:
        value |= code << bitpos
        bitpos += width
    return value.to_bytes((bitpos + 7) // 8, "little")


class ResourceContainerTests(unittest.TestCase):
    def test_repeated_load_preserves_retention_order(self) -> None:
        state = RetainedResourceFamily((4, 9))

        self.assertIs(retain_resource(state, 4), state)
        self.assertEqual(retain_resource(state, 12).numbers, (4, 9, 12))

    def test_discard_truncates_selected_and_later_resources(self) -> None:
        state = RetainedResourceFamily((4, 9, 12, 15))

        self.assertEqual(discard_resource(state, 9).numbers, (4,))
        self.assertEqual(discard_resource(state, 15).numbers, (4, 9, 12))

    def test_discard_requires_a_retained_resource(self) -> None:
        with self.assertRaisesRegex(ResourceNotRetained, "resource 7"):
            discard_resource(RetainedResourceFamily((4, 9)), 7)

    def test_resource_numbers_are_bytes(self) -> None:
        with self.assertRaisesRegex(ValueError, "one byte"):
            retain_resource(RetainedResourceFamily(), 256)

    @unittest.skipUnless(KQ4D_DIR.exists(), "local KQ4D game directory is not present")
    def test_kq4d_sound_directory_ignores_unaddressable_file_tail(self) -> None:
        entries = read_directory_entries(KQ4D_DIR, "sound")

        self.assertEqual(len(entries), 256)
        self.assertIsNotNone(entries[198])
        self.assertIsNotNone(entries[221])

    def test_lzw_like_reset_literal_end_stream(self) -> None:
        self.assertEqual(decode_lzw_like(pack_codes([0x100, ord("A"), 0x101]), 1), b"A")

    def test_picture_nibble_expands_f0_and_f2_operands(self) -> None:
        compressed = bytes([0xF0, 0xAF, 0x2B, 0xFF])
        self.assertEqual(
            decode_picture_nibbles(compressed, 5),
            bytes([0xF0, 0x0A, 0xF2, 0x0B, 0xFF]),
        )

    def test_picture_nibble_encoder_round_trips_expanded_stream(self) -> None:
        expanded = bytes([0xF0, 0x0A, 0xF2, 0x0B, 0xF6, 0, 0, 1, 1, 0xFF])
        stored = encode_picture_nibbles(expanded)

        self.assertEqual(decode_picture_nibbles(stored, len(expanded)), expanded)

    def test_picture_nibble_encoder_rejects_invalid_expanded_streams(self) -> None:
        with self.assertRaisesRegex(ResourceFormatError, "one nibble"):
            encode_picture_nibbles(bytes([0xF0, 0x10, 0xFF]))
        with self.assertRaisesRegex(ResourceFormatError, "after a color/control command"):
            encode_picture_nibbles(bytes([0xF0]))
        with self.assertRaisesRegex(ResourceFormatError, "must end"):
            encode_picture_nibbles(bytes([0xF6]))
        with self.assertRaisesRegex(ResourceFormatError, "after 0xff"):
            encode_picture_nibbles(bytes([0xFF, 0xF6, 0xFF]))

    @unittest.skipUnless(SQ2_DIR.exists(), "local SQ2 game directory is not present")
    def test_sq2_uses_split_directories_and_direct_records(self) -> None:
        layout = detect_layout(SQ2_DIR)
        self.assertEqual(layout.version, "v2_split")
        self.assertEqual(len(read_directory_entries(SQ2_DIR, "logic")), 142)
        record = read_volume_record(SQ2_DIR, "logic", 0)
        self.assertEqual(record.transform, "direct")
        self.assertEqual(record.header, bytes.fromhex("12 34 01 b2 1c"))
        self.assertEqual(record.payload[:4], bytes.fromhex("03 0e ff 05"))

    @unittest.skipUnless(GR_DIR.exists(), "local Gold Rush game directory is not present")
    def test_gr_uses_combined_directory_sections(self) -> None:
        layout = detect_layout(GR_DIR)
        self.assertEqual(layout.version, "v3_combined")
        self.assertEqual(layout.prefix, "GR")
        self.assertEqual(
            layout.section_offsets,
            {"logic": 0x0008, "picture": 0x02E7, "view": 0x05C6, "sound": 0x08C6},
        )
        self.assertEqual(
            [len(read_directory_entries(GR_DIR, kind)) for kind in KIND_ORDER],
            [245, 245, 256, 51],
        )

    @unittest.skipUnless(GR_DIR.exists(), "local Gold Rush game directory is not present")
    def test_gr_known_records_expand_to_payloads(self) -> None:
        logic = read_volume_record(GR_DIR, "logic", 0)
        self.assertEqual(logic.transform, "lzw_like")
        self.assertEqual(logic.header, bytes.fromhex("12 34 01 66 1a d0 10"))
        self.assertEqual(len(logic.payload), 0x1A66)
        self.assertEqual(logic.payload[:4], bytes.fromhex("36 0e ff 05"))

        picture = read_volume_record(GR_DIR, "picture", 1)
        self.assertEqual(picture.transform, "picture_nibble")
        self.assertEqual(picture.header, bytes.fromhex("12 34 81 1b 11 f6 10"))
        self.assertEqual(picture.payload[:4], bytes.fromhex("f0 00 f2 0e"))
        self.assertEqual(picture.payload[-1], 0xFF)

        view = read_volume_record(GR_DIR, "view", 0)
        self.assertEqual(view.transform, "lzw_like")
        self.assertEqual(view.header, bytes.fromhex("12 34 00 7e 0b 1b 04"))
        self.assertEqual(view.payload[:4], bytes.fromhex("01 01 04 00"))

    @unittest.skipUnless(GR_DIR.exists(), "local Gold Rush game directory is not present")
    def test_all_gr_records_expand_with_expected_transforms(self) -> None:
        counts: dict[str, int] = {}
        for kind in KIND_ORDER:
            for number, _entry in iter_present_entries(GR_DIR, kind):
                record = read_volume_record(GR_DIR, kind, number)
                counts[record.transform] = counts.get(record.transform, 0) + 1
                self.assertEqual(len(record.payload), record.expanded_length)
        self.assertEqual(counts, {"direct": 5, "lzw_like": 468, "picture_nibble": 186})


if __name__ == "__main__":
    unittest.main()
