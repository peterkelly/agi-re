#!/usr/bin/env python3
"""Tests for per-version logic dispatch table detection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from disassemble_logic import dispatch_table_layout_for  # noqa: E402


class DispatchTableDetectionTests(unittest.TestCase):
    def assert_layout(self, game: str, version: str, expected: tuple[int, int, int, int]) -> None:
        game_dir = ROOT / "games" / game
        if not game_dir.exists():
            self.skipTest(f"local {game} game directory is not present")
        self.assertEqual(
            dispatch_table_layout_for((game_dir / "AGIDATA.OVL").read_bytes(), version),
            expected,
        )

    def test_sq2_v2_tables_are_detected(self) -> None:
        self.assert_layout("SQ2", "v2_split", (0x061D, 0xB0, 0x08FD, 0x13))

    def test_gr_v3_tables_are_detected(self) -> None:
        self.assert_layout("GR", "v3_combined", (0x0440, 0xB6, 0x0762, 0x13))

    def test_kq4d_v3_tables_are_detected(self) -> None:
        self.assert_layout("KQ4D", "v3_combined", (0x0620, 0xB6, 0x0942, 0x13))


if __name__ == "__main__":
    unittest.main()
