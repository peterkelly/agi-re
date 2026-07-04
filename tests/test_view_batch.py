#!/usr/bin/env python3
"""Tests for picture-plus-view QEMU batch tooling."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from view_batch import (  # noqa: E402
    ViewBatchCase,
    base_cases,
    expected_view_tuple,
    load_cases,
    qemu_batch_dos_dir,
    stress_cases,
    write_report,
)


class ViewBatchTests(unittest.TestCase):
    def test_base_cases_cover_mirror_and_clipping(self) -> None:
        cases = base_cases()
        case_ids = {case.case_id for case in cases}
        self.assertTrue(any(case.group_no == 1 for case in cases))
        self.assertIn("view_011_left_clip", case_ids)
        self.assertIn("view_011_top_clip", case_ids)
        self.assertIn("view_011_right_clip", case_ids)
        self.assertIn("view_011_bottom_clip", case_ids)

    def test_stress_cases_are_optional_and_cover_transparency_range(self) -> None:
        base = load_cases(None)
        expanded = load_cases(None, include_stress=True)
        stress = stress_cases()
        self.assertEqual(expanded, base + stress)
        self.assertEqual(len(base), 8)
        self.assertGreater(len(stress), 8)
        self.assertTrue(any(case.view_no == 10 for case in stress))
        self.assertTrue(any(case.view_no == 37 for case in stress))

    def test_json_case_loading(self) -> None:
        case = ViewBatchCase("sample", 1, 11, 0, 0, 20, 80, 15)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cases.json"
            path.write_text(json.dumps([case.__dict__]) + "\n", encoding="ascii")
            loaded = load_cases(path)
        self.assertEqual(loaded, [case])

    def test_case_filtering(self) -> None:
        loaded = load_cases(None, selected_ids=["view_011_bottom_clip", "view_011_right_clip"])
        self.assertEqual(
            [case.case_id for case in loaded],
            ["view_011_right_clip", "view_011_bottom_clip"],
        )
        with self.assertRaisesRegex(ValueError, "unknown case"):
            load_cases(None, selected_ids=["missing_case"])

    def test_expected_view_tuple_uses_placement_search(self) -> None:
        cases = {case.case_id: case for case in base_cases()}
        self.assertEqual(
            expected_view_tuple(cases["view_011_right_clip"]),
            (11, 0, 0, 140, 71, 15),
        )
        self.assertEqual(
            expected_view_tuple(cases["view_011_bottom_clip"]),
            (11, 0, 0, 23, 167, 15),
        )

    def test_dos_dir_name_is_stable(self) -> None:
        self.assertEqual(qemu_batch_dos_dir("viewbatch", 3), "VIE00003")
        self.assertEqual(qemu_batch_dos_dir("!!!", 9), "VB00009")

    def test_report_summary_counts_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.json"
            report = write_report([], path)
            saved = json.loads(path.read_text(encoding="ascii"))
        self.assertEqual(report["summary"], {"total": 0, "matches": 0, "mismatches": 0, "errors": 0})
        self.assertEqual(saved["results"], [])


if __name__ == "__main__":
    unittest.main()
