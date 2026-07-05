#!/usr/bin/env python3
"""Tests for save round-trip probe fixture construction."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_save import (  # noqa: E402
    SAVE_HEADER_LENGTH,
    SOURCE_BACKED_FIXED_BLOCK_LENGTHS,
    SaveBlock,
    SaveGame,
    parse_save,
)
from save_roundtrip_probe import SaveRoundTripResult  # noqa: E402
from save_roundtrip_probe import (  # noqa: E402
    SAVED_MARKER_X,
    RESTORED_MARKER_FLAG,
    UNRESTORED_MARKER_X,
    VALIDATION_CONTROL_VAR,
    VALIDATION_FRAME_VAR,
    VALIDATION_GROUP_VAR,
    VALIDATION_PRIORITY_VAR,
    VALIDATION_VIEW_VAR,
    VALIDATION_X_VAR,
    VALIDATION_Y_VAR,
    build_restore_read_error_fixture,
    build_restore_fixture,
    build_save_fixture,
    restore_fixture_logic_payload,
    save_fixture_logic_payload,
    truncated_restore_save_payload,
    write_report,
)


class SaveRoundTripProbeTests(unittest.TestCase):
    def test_save_fixture_logic_calls_save_then_draws_validation_view(self) -> None:
        payload = save_fixture_logic_payload()
        code_length = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_length]
        self.assertIn(b"\x7d", code)
        self.assertIn(b"\x8f\x01", code)
        self.assertIn(bytes([0x0C, RESTORED_MARKER_FLAG]), code)
        self.assertIn(bytes([0x03, VALIDATION_X_VAR, SAVED_MARKER_X]), code)
        self.assertIn(
            bytes(
                [
                    0x1A,
                    0x7B,
                    VALIDATION_VIEW_VAR,
                    VALIDATION_GROUP_VAR,
                    VALIDATION_FRAME_VAR,
                    VALIDATION_X_VAR,
                    VALIDATION_Y_VAR,
                    VALIDATION_PRIORITY_VAR,
                    VALIDATION_CONTROL_VAR,
                ]
            ),
            code,
        )

    def test_restore_fixture_logic_has_matching_restore_action_shape(self) -> None:
        restore_payload = restore_fixture_logic_payload()
        code_length = restore_payload[0] | (restore_payload[1] << 8)
        code = restore_payload[2 : 2 + code_length]
        self.assertIn(b"\x7e", code)
        self.assertIn(b"\x8f\x01", code)
        self.assertIn(bytes([0xFF, 0x07, RESTORED_MARKER_FLAG, 0xFF]), code)
        self.assertIn(bytes([0x03, VALIDATION_X_VAR, UNRESTORED_MARKER_X]), code)
        self.assertIn(
            bytes(
                [
                    0x1A,
                    0x7B,
                    VALIDATION_VIEW_VAR,
                    VALIDATION_GROUP_VAR,
                    VALIDATION_FRAME_VAR,
                    VALIDATION_X_VAR,
                    VALIDATION_Y_VAR,
                    VALIDATION_PRIORITY_VAR,
                    VALIDATION_CONTROL_VAR,
                ]
            ),
            code,
        )

    def test_build_save_fixture_removes_existing_sq2_save_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "SG.2").write_bytes(b"stale")
            fixture = build_save_fixture(root)
            self.assertTrue((fixture / "VOL.3").is_file())
            self.assertFalse(list(fixture.glob("SQ2SG.*")))
            self.assertFalse(list(fixture.glob("SG.*")))

    def test_build_restore_fixture_copies_selected_save_stem_and_slot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            save = root / "input.sav"
            save.write_bytes(b"save bytes")
            fixture = build_restore_fixture(root / "fixture", save, save_stem="SG", slot=3)
            self.assertEqual((fixture / "SG.3").read_bytes(), b"save bytes")

    def test_truncated_restore_save_payload_has_selector_signature_shape(self) -> None:
        payload = truncated_restore_save_payload("broken")
        self.assertEqual(len(payload), SAVE_HEADER_LENGTH + 2 + 7)
        self.assertEqual(payload[:7], b"broken\0")
        self.assertEqual(
            payload[SAVE_HEADER_LENGTH : SAVE_HEADER_LENGTH + 2],
            bytes(
                [
                    SOURCE_BACKED_FIXED_BLOCK_LENGTHS[0] & 0xFF,
                    SOURCE_BACKED_FIXED_BLOCK_LENGTHS[0] >> 8,
                ]
            ),
        )
        self.assertEqual(payload[SAVE_HEADER_LENGTH + 2 :], b"SQ2\0\0\0\0")
        with self.assertRaisesRegex(ValueError, "truncated"):
            parse_save(payload)

    def test_build_restore_read_error_fixture_writes_truncated_sq2_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = build_restore_read_error_fixture(
                Path(temp_dir),
                description="bad",
                save_stem="SQ2SG",
                slot=1,
            )
            save_path = fixture / "SQ2SG.1"
            self.assertEqual(save_path.read_bytes(), truncated_restore_save_payload("bad"))
            self.assertTrue((fixture / "VOL.3").is_file())

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
