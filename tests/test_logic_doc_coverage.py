#!/usr/bin/env python3
"""Documentation coverage checks for logic bytecode opcode labels."""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from disassemble_logic import ACTION_NAMES, COND_NAMES  # noqa: E402


LOGIC_BYTECODE = ROOT / "docs" / "src" / "logic_bytecode.md"
LOGIC_OPCODE_EVIDENCE = ROOT / "docs" / "src" / "logic_opcode_evidence.md"


def has_opcode_entry(text: str, opcode: int, name: str) -> bool:
    return re.search(rf"\*\*`0x{opcode:02x}` \(`{re.escape(name)}`\)\*\*", text, re.IGNORECASE) is not None


class LogicDocCoverageTests(unittest.TestCase):
    def test_every_action_label_is_documented(self) -> None:
        text = LOGIC_BYTECODE.read_text(encoding="utf-8")
        missing = [
            f"0x{opcode:02x} {name}"
            for opcode, name in sorted(ACTION_NAMES.items())
            if not has_opcode_entry(text, opcode, name)
        ]
        self.assertEqual(missing, [])

    def test_every_known_condition_label_is_documented(self) -> None:
        text = LOGIC_BYTECODE.read_text(encoding="utf-8")
        missing = [
            f"0x{opcode:02x} {name}"
            for opcode, name in sorted(COND_NAMES.items())
            if not has_opcode_entry(text, opcode, name)
        ]
        self.assertEqual(missing, [])

    def test_action_name_map_covers_contiguous_sq2_dispatch_range(self) -> None:
        self.assertEqual(sorted(ACTION_NAMES), list(range(0xB0)))

    def test_condition_name_map_covers_sq2_valid_table_range(self) -> None:
        self.assertEqual(sorted(COND_NAMES), list(range(0x13)))

    def test_opcode_evidence_matrix_is_current(self) -> None:
        from logic_opcode_evidence import markdown

        self.assertEqual(LOGIC_OPCODE_EVIDENCE.read_text(encoding="utf-8"), markdown())


if __name__ == "__main__":
    unittest.main()
