#!/usr/bin/env python3
"""Tests for per-version logic dispatch table detection."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from disassemble_logic import (  # noqa: E402
    TableEntry,
    action_operand_count,
    decode_logic_messages,
    dispatch_table_layout_for,
)


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

    def test_kq1_2917_shorter_v2_action_table_is_detected(self) -> None:
        self.assert_layout("KQ1", "v2_split", (0x061D, 0xAE, 0x08F5, 0x13))

    def test_kq2_2411_shorter_v2_action_table_is_detected(self) -> None:
        self.assert_layout("KQ2", "v2_split", (0x061B, 0xAA, 0x08E3, 0x13))

    def test_lsl1_2440_shorter_v2_action_table_is_detected(self) -> None:
        self.assert_layout("LSL1", "v2_split", (0x061B, 0xAA, 0x08E3, 0x13))

    def test_sq1_2089_uses_early_v2_table_trailer(self) -> None:
        self.assert_layout("SQ1", "v2_split", (0x03E7, 0x9B, 0x0679, 0x13))

    def test_xmas_2272_v2_tables_are_detected(self) -> None:
        self.assert_layout("XMAS", "v2_split", (0x0417, 0xA1, 0x06BB, 0x13))

    def test_bc_2439_v2_tables_are_detected(self) -> None:
        self.assert_layout("BC", "v2_split", (0x061B, 0xAA, 0x08E3, 0x13))

    def test_mg_2915_v2_tables_are_detected(self) -> None:
        self.assert_layout("MG", "v2_split", (0x061D, 0xAE, 0x08F5, 0x13))

    def test_gr_v3_tables_are_detected(self) -> None:
        self.assert_layout("GR", "v3_combined", (0x0440, 0xB6, 0x0762, 0x13))

    def test_kq4d_v3_tables_are_detected(self) -> None:
        self.assert_layout("KQ4D", "v3_combined", (0x0620, 0xB6, 0x0942, 0x13))

    def test_kq4_3002086_shorter_v3_action_table_is_detected(self) -> None:
        self.assert_layout("KQ4", "v3_combined", (0x061D, 0xB2, 0x092F, 0x13))

    def test_mh1_3002107_v3_tables_are_detected(self) -> None:
        self.assert_layout("MH1", "v3_combined", (0x0620, 0xB6, 0x0942, 0x13))

    def test_mh2_3002149_v3_tables_are_detected(self) -> None:
        self.assert_layout("MH2", "v3_combined", (0x0440, 0xB6, 0x0762, 0x13))

    def test_early_configured_message_actions_consume_four_bytes(self) -> None:
        early_entry = TableEntry(handler=0x1C01, argc=3, meta=0)
        self.assertEqual(action_operand_count(0x97, early_entry), 4)
        self.assertEqual(action_operand_count(0x98, early_entry), 4)
        self.assertEqual(action_operand_count(0x96, early_entry), 3)

    def test_logic_message_decoder_handles_encrypted_text_and_absent_entry(self) -> None:
        code = b"\x00"
        key = b"Avis Durgan"
        plain = b"hello\x00world\x00"
        encrypted = bytes(
            value ^ key[index % len(key)] for index, value in enumerate(plain)
        )
        table = b"\x12\x00\x08\x00\x00\x00\x0e\x00"
        payload = b"\x01\x00" + code + b"\x03" + table + encrypted
        self.assertEqual(
            decode_logic_messages(payload), (None, "hello", None, "world")
        )

    def test_logic_message_decoder_can_read_plain_expanded_text(self) -> None:
        code = b"\x00"
        plain = b"hello\x00world\x00"
        table = b"\x12\x00\x08\x00\x00\x00\x0e\x00"
        payload = b"\x01\x00" + code + b"\x03" + table + plain
        self.assertEqual(
            decode_logic_messages(payload, encrypted=False),
            (None, "hello", None, "world"),
        )


if __name__ == "__main__":
    unittest.main()
