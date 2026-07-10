#!/usr/bin/env python3
"""Tests for generic interpreter dispatch-table comparison."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from compare_gr_sq2_static import TableEntry  # noqa: E402
from compare_interpreter_tables import compare_entries, load_build, parse_role_pair  # noqa: E402


class InterpreterTableComparisonTests(unittest.TestCase):
    def test_parse_role_pair_accepts_symbolic_label_and_hex_addresses(self) -> None:
        self.assertEqual(
            parse_role_pair("code.picture.command_scan=0x68c6,0x67ed"),
            ("code.picture.command_scan", 0x68C6, 0x67ED),
        )

    def test_compare_entries_separates_contract_and_handler_shape(self) -> None:
        return_image = b"\xc3" * 32
        changed_image = b"\x90\xc3" + b"\xc3" * 30
        left = (TableEntry(0, 1, 0x80), TableEntry(1, 2, 0xC0))
        right = (TableEntry(0, 1, 0x80), TableEntry(0, 3, 0xC0))

        compared = compare_entries(left, right, return_image, changed_image)

        self.assertFalse(compared[0].same_normalized_snippet)
        self.assertTrue(compared[0].same_contract)
        self.assertFalse(compared[1].same_contract)

    def test_local_v3_builds_have_detected_table_shapes(self) -> None:
        previous_game_dir = os.environ.get("AGI_GAME_DIR")
        for label in ("KQ4D", "GR"):
            game_dir = ROOT / "games" / label
            if not game_dir.exists():
                self.skipTest(f"local {label} game directory is not present")
            build = load_build(label, game_dir, game_dir / "AGI")
            self.assertEqual(build.layout, "v3_combined")
            self.assertEqual(len(build.actions), 0xB6)
            self.assertEqual(len(build.conditions), 0x13)
        self.assertEqual(os.environ.get("AGI_GAME_DIR"), previous_game_dir)


if __name__ == "__main__":
    unittest.main()
