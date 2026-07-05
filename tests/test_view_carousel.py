#!/usr/bin/env python3
"""Tests for timed view/object carousel tooling."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from compare_picture_capture import PictureCaptureComparison  # noqa: E402
from view_batch import ViewBatchCase  # noqa: E402
from view_carousel import (  # noqa: E402
    carousel_case_tuple,
    qemu_chunk_dos_dir,
    qemu_dos_dir,
    run_carousel,
    write_report,
)


class ViewCarouselTests(unittest.TestCase):
    def test_case_tuple_preserves_optional_control(self) -> None:
        case = ViewBatchCase("sample", 1, 11, 0, 0, 20, 80, 15, control=4)
        self.assertEqual(carousel_case_tuple(case), (1, 11, 0, 0, 20, 80, 15, 4))

    def test_dos_dir_names_are_stable(self) -> None:
        self.assertEqual(qemu_dos_dir("view sweep"), "VIEWSWEE")
        self.assertEqual(qemu_chunk_dos_dir("view sweep", 7), "VIEWS007")
        with self.assertRaisesRegex(ValueError, "non-negative"):
            qemu_chunk_dos_dir("view", -1)

    def test_report_summary_counts_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.json"
            report = write_report([], path)
            saved = json.loads(path.read_text(encoding="ascii"))
        self.assertEqual(report["summary"], {"total": 0, "matches": 0, "mismatches": 0, "errors": 0})
        self.assertEqual(saved["results"], [])

    def test_run_carousel_uses_builder_runner_and_comparison(self) -> None:
        case = ViewBatchCase("sample", 1, 11, 0, 0, 20, 80, 15)
        comparison = PictureCaptureComparison(
            picture_no=1,
            mismatches=0,
            total=160 * 168,
            mismatch_bbox=None,
            samples=[],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            with mock.patch("view_carousel.build_view_timed_carousel_fixture") as build_fixture, mock.patch(
                "view_carousel.build_snapshot_boot_disk"
            ) as build_disk, mock.patch("view_carousel.run_view_carousel_qemu_poll") as run_qemu, mock.patch(
                "view_carousel.compare_picture_capture",
                return_value=comparison,
            ):
                results = run_carousel(
                    [case],
                    temp / "fixtures",
                    "VC",
                    0,
                    0,
                    3,
                    1,
                    0,
                    0,
                    temp / "snapshot.raw",
                    temp / "snapshot.qcow2",
                )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "match")
        build_fixture.assert_called_once()
        build_disk.assert_called_once()
        run_qemu.assert_called_once()


if __name__ == "__main__":
    unittest.main()
