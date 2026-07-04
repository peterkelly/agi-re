#!/usr/bin/env python3
"""Tests for one-engine picture carousel batch tooling."""

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
from picture_batch import PictureBatchCase  # noqa: E402
from picture_carousel import (  # noqa: E402
    qemu_chunk_dos_dir,
    qemu_dos_dir,
    run_carousel,
    run_chunked_carousel,
    write_report,
)
from picture_carousel import run_picture_carousel_qemu  # noqa: E402


class PictureCarouselTests(unittest.TestCase):
    def test_dos_dir_name_is_stable(self) -> None:
        self.assertEqual(qemu_dos_dir("picture sweep"), "PICTURES")
        self.assertEqual(qemu_dos_dir("!!!"), "PICSWEEP")
        self.assertEqual(qemu_chunk_dos_dir("picture sweep", 3), "PICTU003")
        self.assertEqual(qemu_chunk_dos_dir("!!!", 12), "PIC012")

    def test_report_summary_counts_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.json"
            report = write_report([], path)
            saved = json.loads(path.read_text(encoding="ascii"))
        self.assertEqual(report["summary"], {"total": 0, "matches": 0, "mismatches": 0, "errors": 0})
        self.assertEqual(saved["results"], [])

    def test_qemu_runner_rejects_empty_advance_key_list(self) -> None:
        with self.assertRaisesRegex(ValueError, "advance key"):
            run_picture_carousel_qemu(Path("disk.qcow2"), "PICSWEEP", [], 0, 0, 0, ",,,")

    def test_run_carousel_builds_once_and_compares_each_case(self) -> None:
        cases = [
            PictureBatchCase("one", 1, "one"),
            PictureBatchCase("two", 45, "two"),
        ]
        comparison = PictureCaptureComparison(1, 0, 26880, None, [])
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with mock.patch("picture_carousel.build_picture_carousel_fixture") as build_fixture, mock.patch(
                "picture_carousel.build_snapshot_boot_disk"
            ) as build_disk, mock.patch("picture_carousel.run_picture_carousel_qemu") as run_qemu, mock.patch(
                "picture_carousel.compare_picture_capture", return_value=comparison
            ) as compare:
                results = run_carousel(
                    cases,
                    root / "fixtures",
                    "PICSWEEP",
                    0,
                    0,
                    0,
                    "x",
                    "key",
                    20,
                    0,
                    False,
                    1,
                    20,
                    root / "raw.img",
                    root / "disk.qcow2",
                )
        build_fixture.assert_called_once()
        build_disk.assert_called_once()
        run_qemu.assert_called_once()
        self.assertEqual(compare.call_count, 2)
        self.assertEqual([result.status for result in results], ["match", "match"])

    def test_run_carousel_timed_mode_builds_timed_fixture_without_keys(self) -> None:
        cases = [
            PictureBatchCase("one", 1, "one"),
            PictureBatchCase("two", 45, "two"),
        ]
        comparison = PictureCaptureComparison(1, 0, 26880, None, [])
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with mock.patch("picture_carousel.build_picture_timed_carousel_fixture") as build_fixture, mock.patch(
                "picture_carousel.build_snapshot_boot_disk"
            ), mock.patch("picture_carousel.run_picture_carousel_qemu") as run_qemu, mock.patch(
                "picture_carousel.compare_picture_capture", return_value=comparison
            ):
                run_carousel(
                    cases,
                    root / "fixtures",
                    "PICSWEEP",
                    0,
                    0,
                    0,
                    "x",
                    "timed",
                    7,
                    0,
                    False,
                    1,
                    20,
                    root / "raw.img",
                    root / "disk.qcow2",
                )
        build_fixture.assert_called_once()
        self.assertEqual(build_fixture.call_args.args[2:], (7, 0))
        self.assertIsNone(run_qemu.call_args.args[6])

    def test_run_carousel_poll_mode_uses_polling_qemu_runner(self) -> None:
        cases = [
            PictureBatchCase("one", 1, "one"),
            PictureBatchCase("two", 45, "two"),
        ]
        comparison = PictureCaptureComparison(1, 0, 26880, None, [])
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with mock.patch("picture_carousel.build_picture_timed_carousel_fixture"), mock.patch(
                "picture_carousel.build_snapshot_boot_disk"
            ), mock.patch("picture_carousel.run_picture_carousel_qemu") as run_qemu, mock.patch(
                "picture_carousel.run_picture_carousel_qemu_poll"
            ) as run_poll, mock.patch("picture_carousel.compare_picture_capture", return_value=comparison):
                run_carousel(
                    cases,
                    root / "fixtures",
                    "PICSWEEP",
                    0,
                    0,
                    0,
                    "x",
                    "timed",
                    7,
                    1,
                    True,
                    0.25,
                    3,
                    root / "raw.img",
                    root / "disk.qcow2",
                )
        run_qemu.assert_not_called()
        run_poll.assert_called_once()
        self.assertEqual(run_poll.call_args.args[6:8], (0.25, 3))

    def test_run_chunked_carousel_splits_cases_and_snapshot_paths(self) -> None:
        cases = [
            PictureBatchCase(f"case_{index}", index, "case")
            for index in range(1, 6)
        ]
        expected_results = [
            [
                mock.Mock(case_id="case_1"),
                mock.Mock(case_id="case_2"),
            ],
            [
                mock.Mock(case_id="case_3"),
                mock.Mock(case_id="case_4"),
            ],
            [mock.Mock(case_id="case_5")],
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with mock.patch("picture_carousel.run_carousel", side_effect=expected_results) as run:
                results = run_chunked_carousel(
                    cases,
                    2,
                    root / "fixtures",
                    "PICALL",
                    5,
                    3,
                    1,
                    "x",
                    "timed",
                    120,
                    1,
                    True,
                    0.5,
                    15,
                    root / "disk.raw",
                    root / "disk.qcow2",
                )
        self.assertEqual(
            [result.case_id for result in results],
            [f"case_{index}" for index in range(1, 6)],
        )
        self.assertEqual(run.call_count, 3)
        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            [cases[:2], cases[2:4], cases[4:]],
        )
        self.assertEqual(
            [call.args[2] for call in run.call_args_list],
            ["PICAL000", "PICAL001", "PICAL002"],
        )
        self.assertEqual(
            [call.args[13].name for call in run.call_args_list],
            [
                "disk_chunk_000.raw",
                "disk_chunk_001.raw",
                "disk_chunk_002.raw",
            ],
        )
        self.assertEqual(
            [call.args[14].name for call in run.call_args_list],
            [
                "disk_chunk_000.qcow2",
                "disk_chunk_001.qcow2",
                "disk_chunk_002.qcow2",
            ],
        )


if __name__ == "__main__":
    unittest.main()
