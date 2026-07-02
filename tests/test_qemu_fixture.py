#!/usr/bin/env python3
"""Tests for generated original-engine QEMU fixture resources."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from qemu_fixture import (  # noqa: E402
    SCRATCH_VAR,
    build_synthetic_picture_fixture,
    patch_dir_entry,
    patch_logdir_entry_zero,
    picture_logic_payload,
    picture_view_logic_payload,
    volume_record,
)
from agi_graphics import PALETTE, render_picture  # noqa: E402
from compare_picture_capture import compare_picture_capture  # noqa: E402


class QemuFixtureTests(unittest.TestCase):
    def test_picture_logic_payload_shows_picture_and_loops(self) -> None:
        payload = picture_logic_payload(45)
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        self.assertEqual(
            code,
            bytes(
                [
                    0x03,
                    SCRATCH_VAR,
                    45,
                    0x18,
                    SCRATCH_VAR,
                    0x19,
                    SCRATCH_VAR,
                    0x1A,
                    0xFE,
                    0xFD,
                    0xFF,
                ]
            ),
        )
        self.assertEqual(payload[2 + code_len :], bytes([0x00, 0x02, 0x00]))

    def test_picture_view_logic_payload_draws_transient_view_and_loops(self) -> None:
        payload = picture_view_logic_payload(1, 11, 0, 0, 20, 80, 15)
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        self.assertEqual(
            code,
            bytes(
                [
                    0x03,
                    SCRATCH_VAR,
                    1,
                    0x18,
                    SCRATCH_VAR,
                    0x19,
                    SCRATCH_VAR,
                    0x1A,
                    0x1E,
                    11,
                    0x7A,
                    11,
                    0,
                    0,
                    20,
                    80,
                    15,
                    15,
                    0xFE,
                    0xFD,
                    0xFF,
                ]
            ),
        )
        self.assertEqual(payload[2 + code_len :], bytes([0x00, 0x02, 0x00]))

    def test_volume_record_wraps_payload_with_header(self) -> None:
        record = volume_record(b"abc", volume=3)
        self.assertEqual(record, b"\x12\x34\x03\x03\x00abc")

    def test_logdir_patch_points_logic_zero_at_volume_three_offset_zero(self) -> None:
        original = bytes([0x10, 0x6D, 0x1B, 0xFF, 0xFF, 0xFF])
        patched = patch_logdir_entry_zero(original, volume=3, offset=0)
        self.assertEqual(patched[:6], bytes([0x30, 0x00, 0x00, 0xFF, 0xFF, 0xFF]))

    def test_dir_patch_updates_selected_entry(self) -> None:
        original = bytes([0xFF] * 9)
        patched = patch_dir_entry(original, resource_no=2, volume=3, offset=0x12345)
        self.assertEqual(patched[:6], bytes([0xFF] * 6))
        self.assertEqual(patched[6:9], bytes([0x31, 0x23, 0x45]))

    def test_synthetic_picture_fixture_patches_logdir_picdir_and_vol3(self) -> None:
        payload = bytes([0xF0, 0x02, 0xF6, 0, 0, 1, 1, 0xFF])
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = build_synthetic_picture_fixture(payload, Path(temp_dir) / "fixture", picture_no=0)
            vol3 = (fixture / "VOL.3").read_bytes()
            logic_record = volume_record(picture_logic_payload(0), volume=3)
            self.assertTrue(vol3.startswith(logic_record))
            self.assertEqual(vol3[len(logic_record) :], volume_record(payload, volume=3))
            self.assertEqual((fixture / "LOGDIR").read_bytes()[:3], bytes([0x30, 0x00, 0x00]))
            picture_entry = (fixture / "PICDIR").read_bytes()[:3]
            self.assertEqual(picture_entry, bytes([0x30, 0x00, len(logic_record)]))

    def test_synthetic_qemu_scaled_picture_capture_compares_equal(self) -> None:
        rendered = render_picture(1)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "scaled.ppm"
            rgb = bytearray()
            black = bytes(PALETTE[0])
            for y in range(400):
                if y >= 168 * 2:
                    rgb.extend(black * 640)
                    continue
                logical_y = y // 2
                row = rendered.visual_nibbles[logical_y * 160 : (logical_y + 1) * 160]
                for nibble in row:
                    rgb.extend(bytes(PALETTE[nibble]) * 4)
            with path.open("wb") as f:
                f.write(b"P6\n640 400\n255\n")
                f.write(rgb)
            comparison = compare_picture_capture(1, path)
        self.assertTrue(comparison.matches)


if __name__ == "__main__":
    unittest.main()
