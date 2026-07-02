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

from view_batch import ViewBatchCase, base_cases, load_cases, qemu_batch_dos_dir, write_report  # noqa: E402


class ViewBatchTests(unittest.TestCase):
    def test_base_cases_cover_mirror_and_clipping(self) -> None:
        cases = base_cases()
        self.assertTrue(any(case.group_no == 1 for case in cases))
        self.assertTrue(any(case.x == 0 for case in cases))
        self.assertTrue(any(case.baseline_y < 5 for case in cases))

    def test_json_case_loading(self) -> None:
        case = ViewBatchCase("sample", 1, 11, 0, 0, 20, 80, 15)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cases.json"
            path.write_text(json.dumps([case.__dict__]) + "\n", encoding="ascii")
            loaded = load_cases(path)
        self.assertEqual(loaded, [case])

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
