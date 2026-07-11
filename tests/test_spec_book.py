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

    def test_logic_catalog_mentions_every_profile_opcode(self) -> None:
        logic = (SPEC_SRC / "logic_bytecode.md").read_text(encoding="ascii")
        for opcode in range(0xB0):
            with self.subTest(profile="2.936", opcode=opcode):
                self.assertIn(f"`0x{opcode:02x}`", logic)

    def test_resource_lifecycle_specifies_ordered_discard(self) -> None:
        runtime = (SPEC_SRC / "runtime_state.md").read_text(encoding="ascii")
        logic = (SPEC_SRC / "logic_bytecode.md").read_text(encoding="ascii")

        self.assertIn("every resource loaded later in the same family", runtime)
        self.assertRegex(runtime, r"not still selected by a live\s+object")
        self.assertIn("every picture retained after it", logic)
        self.assertIn("every view retained after it", logic)
        for opcode in range(0xB0, 0xB6):
            with self.subTest(profile="3.002.149", opcode=opcode):
                self.assertIn(f"`0x{opcode:02x}`", logic)

    def test_conformance_matrix_classifies_claim_boundaries(self) -> None:
        matrix = (SPEC_SRC / "conformance_matrix.md").read_text(encoding="ascii")
        required = (
            "Common behavioral core",
            "Profile variants",
            "Game-data dimensions",
            "Partial domains",
            "Outside the current target",
            "Claim requirements",
        )
        for heading in required:
            with self.subTest(heading=heading):
                self.assertIn(f"## {heading}", matrix)
        self.assertIn("2.936 binary save interchange", matrix)
        self.assertIn("2.089 full-EGA gameplay", matrix)
        self.assertIn("2.089 SQ1 binary save interchange", matrix)
        self.assertIn("2.272 full-EGA gameplay", matrix)
        self.assertIn("2.272 XMAS binary save interchange", matrix)
        self.assertIn("2.411 full-EGA gameplay", matrix)
        self.assertIn("2.411 KQ2 binary save interchange", matrix)
        self.assertIn("2.440 full-EGA gameplay", matrix)
        self.assertIn("2.440 LSL1 binary save interchange", matrix)
        self.assertIn("2.917 full-EGA gameplay", matrix)
        self.assertIn("2.917 KQ1 binary save interchange", matrix)
        self.assertIn("2.917 PQ1 binary save interchange", matrix)
        self.assertIn("2.936 KQ3 binary save interchange", matrix)
        self.assertIn("3.002.086 full-EGA gameplay", matrix)
        self.assertIn("3.002.086 full KQ4 binary save interchange", matrix)
        self.assertIn("3.002.102 full-EGA gameplay", matrix)
        self.assertIn("3.002.102 KQ4D demo binary save interchange", matrix)
        self.assertIn("3.002.149 full-EGA gameplay", matrix)

    def test_early_profiles_are_promoted_for_full_ega_gameplay(self) -> None:
        profiles = (SPEC_SRC / "version_profiles.md").read_text(encoding="ascii")
        self.assertIn("## AGI 2.089 profile", profiles)
        self.assertIn("## AGI 2.272 profile", profiles)
        self.assertNotIn("## AGI 2.089 partial profile", profiles)
        self.assertNotIn("## AGI 2.272 partial profile", profiles)

    def test_picture_catalog_mentions_every_command(self) -> None:
        picture = (SPEC_SRC / "picture_resources.md").read_text(encoding="ascii")
        for command in range(0xF0, 0xFB):
            with self.subTest(command=command):
                self.assertIn(f"`0x{command:02x}`", picture)
        self.assertIn("`0xff`", picture)

    def test_view_chapter_covers_structural_and_drawing_contracts(self) -> None:
        view = (SPEC_SRC / "view_resources.md").read_text(encoding="ascii")
        required = (
            "Payload structure",
            "Row decoding",
            "Stateful mirroring",
            "Baseline placement",
            "Transparency and priority composition",
            "Embedded display string",
        )
        for heading in required:
            with self.subTest(heading=heading):
                self.assertIn(f"## {heading}", view)

    def test_object_chapter_covers_update_domains(self) -> None:
        objects = (SPEC_SRC / "object_behavior.md").read_text(encoding="ascii")
        required = (
            "Object lifecycle",
            "Placement search",
            "Cycle ordering and cadence",
            "Cel cycling",
            "Object-object collision",
            "Footprint control acceptance",
            "Target motion",
            "Drawing order and refresh",
        )
        for heading in required:
            with self.subTest(heading=heading):
                self.assertIn(f"## {heading}", objects)

    def test_input_chapter_covers_parser_event_and_modal_domains(self) -> None:
        input_spec = (SPEC_SRC / "input_text_and_menus.md").read_text(encoding="ascii")
        required = (
            "Dictionary file",
            "Parser normalization",
            "Parsed-word matching",
            "Event queue",
            "Raw-key condition",
            "Text geometry and surfaces",
            "Inventory selection",
            "Menu interaction",
            "Font boundary",
        )
        for heading in required:
            with self.subTest(heading=heading):
                self.assertIn(f"## {heading}", input_spec)

    def test_sound_chapter_covers_timing_and_envelope_domains(self) -> None:
        sound = (SPEC_SRC / "sound.md").read_text(encoding="ascii")
        required_headings = (
            "Payload format",
            "Logic operations",
            "Tick schedule",
            "Channel profiles",
            "PC-speaker output",
            "Four-channel command output",
            "Output boundary",
        )
        for heading in required_headings:
            with self.subTest(heading=heading):
                self.assertIn(f"## {heading}", sound)
        required_terms = (
            "Envelope index",
            "Table byte `0x80`",
            "global attenuation adjustment",
            "device value `2`",
            "channel selector byte",
        )
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, sound)

    def test_persistence_chapter_covers_room_replay_and_save_domains(self) -> None:
        persistence = (SPEC_SRC / "session_and_persistence.md").read_text(encoding="ascii")
        required = (
            "Room transition",
            "Resource replay sequence",
            "Save selector",
            "Save-file envelope",
            "Profiles 2.411 and 2.440 observed early blocks",
            "Profile 2.917 observed KQ1 blocks",
            "Profile 2.917 observed PQ1 blocks",
            "Profile 2.936 observed KQ3 blocks",
            "Profile 3.002.086 observed full KQ4 blocks",
            "Profile 3.002.102 observed KQ4D demo blocks",
            "V3 block-3 transform",
            "Restore action outcomes",
            "Restart",
            "Reserved-state rule",
        )
        for heading in required:
            with self.subTest(heading=heading):
                self.assertIn(f"## {heading}", persistence)


if __name__ == "__main__":
    unittest.main()
