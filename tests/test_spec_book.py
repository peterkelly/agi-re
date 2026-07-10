#!/usr/bin/env python3
"""Structural checks for the clean-room behavioral specification."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_SRC = ROOT / "spec" / "src"


class SpecBookTests(unittest.TestCase):
    def test_summary_links_existing_chapters(self) -> None:
        summary = (SPEC_SRC / "SUMMARY.md").read_text(encoding="ascii")
        links = re.findall(r"\]\(\./([^)]+)\)", summary)
        self.assertGreater(len(links), 2)
        for link in links:
            with self.subTest(link=link):
                self.assertTrue((SPEC_SRC / link).is_file())

    def test_substantive_chapters_exclude_evidence_only_terms(self) -> None:
        excluded = {"README.md", "SUMMARY.md", "scope_and_conformance.md"}
        forbidden = (
            "/Users/",
            "AGIDATA.OVL",
            "DS:0x",
            "QEMU",
            "ndisasm",
            "radare",
            "disassembl",
            "tools/",
            "tests/",
            "build/",
            "`code.",
            "`data.",
        )
        for chapter in SPEC_SRC.glob("*.md"):
            if chapter.name in excluded:
                continue
            text = chapter.read_text(encoding="ascii")
            for term in forbidden:
                with self.subTest(chapter=chapter.name, term=term):
                    self.assertNotIn(term, text)


if __name__ == "__main__":
    unittest.main()
