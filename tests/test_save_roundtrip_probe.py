#!/usr/bin/env python3
"""Tests for save round-trip probe fixture construction."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_save import SAVE_HEADER_LENGTH, SaveBlock, SaveGame  # noqa: E402
from save_roundtrip_probe import SaveRoundTripResult  # noqa: E402
from save_roundtrip_probe import (  # noqa: E402
    build_save_fixture,
    save_fixture_logic_payload,
    write_report,
)


class SaveRoundTripProbeTests(unittest.TestCase):
    def test_save_fixture_logic_calls_save_then_draws_validation_view(self) -> None:
        payload = save_fixture_logic_payload()
        code_length = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_length]
        self.assertIn(b"\x7d", code)
        self.assertIn(b"\x1a\x7a\x0b\x00\x00\x32\x50\x0f\x0f", code)

    def test_build_save_fixture_removes_existing_sq2_save_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = build_save_fixture(Path(temp_dir))
            self.assertTrue((fixture / "VOL.3").is_file())
            self.assertFalse(list(fixture.glob("SQ2SG.*")))

    def test_write_report_serializes_probe_result(self) -> None:
        result = SaveRoundTripResult(
            "match",
            "SVRT",
            "capture.ppm",
            "SQ2SG.1",
            "Codex probe",
            [0x05E1, 0x0387, 0x0148, 0x00C8, 16],
            "match",
            0,
            1.25,
            None,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.json"
            report = write_report(result, path)
            saved = path.read_text(encoding="ascii")
        self.assertEqual(report["result"]["description"], "Codex probe")
        self.assertIn('"status": "match"', saved)

    def test_imported_save_types_remain_available_for_generated_saves(self) -> None:
        header = b"Codex probe\0".ljust(SAVE_HEADER_LENGTH, b"\0")
        blocks = tuple(SaveBlock(index, 0, 0, 0, b"") for index in range(5))
        save = SaveGame(None, header, blocks)
        self.assertEqual(save.description, "Codex probe")


if __name__ == "__main__":
    unittest.main()
