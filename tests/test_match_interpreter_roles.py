#!/usr/bin/env python3
"""Tests for normalized cross-build role matching."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from match_interpreter_roles import (  # noqa: E402
    RoleMatch,
    candidate_addresses,
    markdown_report,
    match_roles,
    parse_role,
)


class InterpreterRoleMatchingTests(unittest.TestCase):
    def test_parse_role_accepts_symbolic_label_and_address(self) -> None:
        self.assertEqual(parse_role("code.picture.command_scan=0x120"), ("code.picture.command_scan", 0x120))

    def test_candidate_addresses_include_call_targets_and_handlers(self) -> None:
        image = b"\xe8\x03\x00\xc3\x90\x90\xc3"
        self.assertEqual(
            candidate_addresses(image, table_handlers=(3,), additional=(4,)),
            (3, 4, 6),
        )

    def test_exact_normalized_match_ignores_relocated_call_target(self) -> None:
        reference = b"\xe8\x01\x00\xc3\xc3"
        target = b"\x90\xe8\x01\x00\xc3\xc3"
        matches = match_roles(reference, target, (("sample", 0),), (1,))
        self.assertEqual(matches, (RoleMatch("sample", 0, (1,)),))

    def test_markdown_report_classifies_unique_ambiguous_and_unmatched(self) -> None:
        report = markdown_report(
            "left",
            "right",
            (
                RoleMatch("one", 1, (4,)),
                RoleMatch("many", 2, (5, 6)),
                RoleMatch("none", 3, ()),
            ),
        )
        self.assertIn("| `one` | `0x0001` | `0x0004` | exact |", report)
        self.assertIn("ambiguous", report)
        self.assertIn("unmatched", report)


if __name__ == "__main__":
    unittest.main()
