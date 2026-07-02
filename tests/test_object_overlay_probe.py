#!/usr/bin/env python3
"""Tests for targeted object overlay QEMU probes."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_graphics import HEIGHT, PALETTE, WIDTH, PictureRenderer, compose_frame_on_picture, render_view_frame  # noqa: E402
from object_overlay_probe import base_cases, compare_capture, load_cases, qemu_batch_dos_dir, write_report  # noqa: E402


def write_scaled_capture(path: Path, nibbles: bytes) -> None:
    rgb = bytearray()
    black = bytes(PALETTE[0])
    for y in range(400):
        if y >= HEIGHT * 2:
            rgb.extend(black * 640)
            continue
        logical_y = y // 2
        row = nibbles[logical_y * WIDTH : (logical_y + 1) * WIDTH]
        for nibble in row:
            rgb.extend(bytes(PALETTE[nibble]) * 4)
    with path.open("wb") as f:
        f.write(b"P6\n640 400\n255\n")
        f.write(rgb)


class ObjectOverlayProbeTests(unittest.TestCase):
    def test_base_cases_cover_priority_threshold_pairs(self) -> None:
        case_ids = {case.case_id for case in base_cases()}
        self.assertIn("default_control4_priority3_hidden", case_ids)
        self.assertIn("default_control4_priority4_draws", case_ids)
        self.assertIn("filled_control6_priority5_hidden", case_ids)
        self.assertIn("filled_control6_priority6_draws", case_ids)
        self.assertIn("priority3_control6_uses_low_hidden", case_ids)
        self.assertIn("priority6_control3_uses_low_draws", case_ids)
        self.assertIn("scan_down_control6_priority5_hidden", case_ids)
        self.assertIn("scan_down_control6_priority6_draws", case_ids)

    def test_json_case_loading(self) -> None:
        case = base_cases()[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cases.json"
            path.write_text(json.dumps([case.__dict__]) + "\n", encoding="ascii")
            loaded = load_cases(path)
        self.assertEqual(loaded, [case])

    def test_dos_dir_name_is_stable(self) -> None:
        self.assertEqual(qemu_batch_dos_dir("overlay", 2), "OVE00002")
        self.assertEqual(qemu_batch_dos_dir("!!!", 2), "OP00002")

    def test_compare_capture_matches_synthetic_expected_image(self) -> None:
        case = next(item for item in base_cases() if item.case_id == "default_control4_priority4_draws")
        picture = PictureRenderer(case.picture_payload).render(case.picture_no)
        frame = render_view_frame(case.view_no, case.group_no, case.frame_no)
        expected = compose_frame_on_picture(picture, frame, case.x, case.baseline_y, case.priority)
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = Path(temp_dir) / "capture.ppm"
            write_scaled_capture(capture, expected.visual_nibbles)
            comparison = compare_capture(case, capture)
        self.assertTrue(comparison.matches)
        self.assertEqual(comparison.mismatches, 0)

    def test_report_summary_counts_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.json"
            report = write_report([], path)
            saved = json.loads(path.read_text(encoding="ascii"))
        self.assertEqual(report["summary"], {"total": 0, "matches": 0, "mismatches": 0, "errors": 0})
        self.assertEqual(saved["results"], [])


if __name__ == "__main__":
    unittest.main()
