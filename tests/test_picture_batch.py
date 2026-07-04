#!/usr/bin/env python3
"""Tests for real-picture QEMU batch tooling."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from picture_batch import (  # noqa: E402
    PictureBatchCase,
    all_present_cases,
    base_cases,
    broad_cases,
    load_cases,
    preset_cases,
    qemu_batch_dos_dir,
    write_report,
)


class PictureBatchTests(unittest.TestCase):
    def test_base_cases_cover_first_and_largest_pictures(self) -> None:
        cases = base_cases()
        self.assertEqual(
            [case.case_id for case in cases],
            ["picture_001_first_present", "picture_045_largest_payload"],
        )
        self.assertEqual([case.picture_no for case in cases], [1, 45])

    def test_broad_cases_cover_representative_pictures(self) -> None:
        cases = broad_cases()
        self.assertEqual([case.picture_no for case in cases], [1, 6, 17, 43, 44, 45, 46, 76])
        self.assertEqual(len({case.case_id for case in cases}), len(cases))

    def test_all_present_cases_are_discovered_from_picdir(self) -> None:
        cases = all_present_cases()
        self.assertEqual(len(cases), 74)
        self.assertEqual(cases[0].case_id, "picture_001_present")
        self.assertTrue(all(case.description for case in cases))

    def test_preset_selection(self) -> None:
        self.assertEqual(preset_cases("base"), base_cases())
        self.assertEqual(preset_cases("broad"), broad_cases())
        self.assertEqual(len(preset_cases("all")), 74)
        with self.assertRaisesRegex(ValueError, "unknown preset"):
            preset_cases("missing")

    def test_json_case_loading(self) -> None:
        case = PictureBatchCase("sample", 1, "sample picture")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cases.json"
            path.write_text(json.dumps([case.__dict__]) + "\n", encoding="ascii")
            loaded = load_cases(path)
        self.assertEqual(loaded, [case])

    def test_case_filtering(self) -> None:
        loaded = load_cases(None, ["picture_045_largest_payload"])
        self.assertEqual([case.case_id for case in loaded], ["picture_045_largest_payload"])
        loaded = load_cases(None, ["picture_046_pattern_heavy"], preset="broad")
        self.assertEqual([case.case_id for case in loaded], ["picture_046_pattern_heavy"])
        with self.assertRaisesRegex(ValueError, "unknown case"):
            load_cases(None, ["missing_case"])

    def test_dos_dir_name_is_stable(self) -> None:
        self.assertEqual(qemu_batch_dos_dir("picturebatch", 4), "PIC00004")
        self.assertEqual(qemu_batch_dos_dir("!!!", 4), "PB00004")

    def test_report_summary_counts_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.json"
            report = write_report([], path)
            saved = json.loads(path.read_text(encoding="ascii"))
        self.assertEqual(report["summary"], {"total": 0, "matches": 0, "mismatches": 0, "errors": 0})
        self.assertEqual(saved["results"], [])


if __name__ == "__main__":
    unittest.main()
