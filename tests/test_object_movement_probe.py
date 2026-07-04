#!/usr/bin/env python3
"""Tests for persistent object movement QEMU probes."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_graphics import HEIGHT, PALETTE, WIDTH, PictureRenderer, compose_frame_on_picture, render_view_frame  # noqa: E402
from object_movement_probe import base_cases, compare_capture, load_cases, qemu_batch_dos_dir, write_report  # noqa: E402


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


class ObjectMovementProbeTests(unittest.TestCase):
    def test_base_cases_cover_horizontal_and_vertical_targets(self) -> None:
        case_ids = {case.case_id for case in base_cases()}
        self.assertIn("move_right_to_target", case_ids)
        self.assertIn("move_down_to_target", case_ids)
        self.assertIn("move_right_to_screen_edge", case_ids)
        self.assertIn("move_down_to_bottom_edge", case_ids)
        self.assertIn("move_allowed_on_control_zero", case_ids)
        self.assertIn("move_control_1_without_bit_0002_blocks", case_ids)
        self.assertIn("move_control_1_set_bit_0002_still_hidden", case_ids)
        self.assertIn("move_control_1_clear_bit_0002_still_hidden", case_ids)
        self.assertIn("move_rect_boundary_without_bit_0002_stops_at_edge", case_ids)
        self.assertIn("move_rect_boundary_set_bit_0002_reaches_target", case_ids)
        self.assertIn("move_rect_boundary_clear_bit_0002_stops_again", case_ids)
        self.assertIn("move_rect_boundary_clear_bounds_reaches_target", case_ids)
        self.assertIn("move_control_2_set_bit_0100_blocks", case_ids)
        self.assertIn("move_control_2_clear_bits_0900_reaches_target", case_ids)
        self.assertIn("move_control_3_set_bit_0800_blocks", case_ids)
        self.assertIn("move_control_3_clear_bits_0900_reaches_target", case_ids)
        self.assertIn("animation_interval_mode1_reaches_frame1", case_ids)
        self.assertIn("animation_clear_bit_0020_prevents_frame_advance", case_ids)
        self.assertIn("animation_set_bit_0020_restores_frame_advance", case_ids)
        self.assertIn("animation_mode0_forward_loop_wraps_to_frame0", case_ids)
        self.assertIn("animation_mode2_backward_completion_reaches_frame0", case_ids)
        self.assertIn("animation_mode3_backward_loop_wraps_to_frame1", case_ids)
        self.assertIn("move_left_to_target", case_ids)
        self.assertIn("move_up_to_target", case_ids)
        self.assertIn("move_diagonal_down_right", case_ids)
        self.assertIn("move_non_divisible_distance", case_ids)
        self.assertIn("move_near_target_immediate", case_ids)
        self.assertIn("move_already_at_target", case_ids)
        self.assertIn("move_zero_step_override", case_ids)
        self.assertIn("move_blocked_by_object_collision", case_ids)
        self.assertIn("move_collision_skip_bit_reaches_target", case_ids)
        self.assertIn("move_collision_clear_skip_bit_blocks_again", case_ids)
        self.assertIn("approach_first_object_until_near_band", case_ids)
        self.assertIn("move_to_once_countdown_gated_completion", case_ids)
        self.assertIn("random_motion_visible_somewhere", case_ids)
        self.assertIn("clear_field_22_after_random_motion_stops_motion", case_ids)
        self.assertIn("action_84_after_random_motion_stops_motion", case_ids)

    def test_json_case_loading(self) -> None:
        case = base_cases()[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cases.json"
            path.write_text(json.dumps([case.__dict__]) + "\n", encoding="ascii")
            loaded = load_cases(path)
        self.assertEqual(loaded, [case])

    def test_case_filtering(self) -> None:
        loaded = load_cases(None, ["move_collision_clear_skip_bit_blocks_again"])
        self.assertEqual([case.case_id for case in loaded], ["move_collision_clear_skip_bit_blocks_again"])

    def test_dos_dir_name_is_stable(self) -> None:
        self.assertEqual(qemu_batch_dos_dir("movement", 2), "MOV00002")
        self.assertEqual(qemu_batch_dos_dir("!!!", 2), "MV00002")

    def test_compare_capture_matches_expected_target_position(self) -> None:
        case = next(item for item in base_cases() if item.case_id == "move_right_to_target")
        picture = PictureRenderer(case.picture_payload).render(case.picture_no)
        frame = render_view_frame(case.view_no, case.group_no, case.frame_no)
        expected = compose_frame_on_picture(picture, frame, case.expected_x, case.expected_baseline_y, case.priority)
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = Path(temp_dir) / "capture.ppm"
            write_scaled_capture(capture, expected.visual_nibbles)
            comparison = compare_capture(case, capture)
        self.assertEqual(comparison.status, "match")
        self.assertIsNone(comparison.best_position)

    def test_compare_capture_matches_expected_obstacle_composition(self) -> None:
        case = next(item for item in base_cases() if item.case_id == "move_blocked_by_object_collision")
        picture = PictureRenderer(case.picture_payload).render(case.picture_no)
        frame = render_view_frame(case.view_no, case.group_no, case.frame_no)
        expected = compose_frame_on_picture(picture, frame, case.expected_x, case.expected_baseline_y, case.priority)
        obstacle = render_view_frame(case.obstacle_view_no, case.obstacle_group_no, case.obstacle_frame_no)
        expected = compose_frame_on_picture(expected, obstacle, case.obstacle_x, case.obstacle_baseline_y, case.obstacle_priority)
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = Path(temp_dir) / "capture.ppm"
            write_scaled_capture(capture, expected.visual_nibbles)
            comparison = compare_capture(case, capture)
        self.assertEqual(comparison.status, "match")

    def test_compare_capture_matches_picture_only_case(self) -> None:
        case = next(item for item in base_cases() if item.case_id == "move_control_1_without_bit_0002_blocks")
        picture = PictureRenderer(case.picture_payload).render(case.picture_no)
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = Path(temp_dir) / "capture.ppm"
            write_scaled_capture(capture, picture.visual_nibbles)
            comparison = compare_capture(case, capture)
        self.assertEqual(comparison.status, "match")

    def test_compare_capture_reports_best_position_on_mismatch(self) -> None:
        case = replace(base_cases()[0], expected_x=50, expected_baseline_y=80)
        picture = PictureRenderer(case.picture_payload).render(case.picture_no)
        frame = render_view_frame(case.view_no, case.group_no, case.frame_no)
        actual = compose_frame_on_picture(picture, frame, 0, 20, case.priority)
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = Path(temp_dir) / "capture.ppm"
            write_scaled_capture(capture, actual.visual_nibbles)
            comparison = compare_capture(case, capture)
        self.assertEqual(comparison.status, "mismatch")
        self.assertEqual(comparison.best_position, (0, 0, 20))

    def test_report_summary_counts_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.json"
            report = write_report([], path)
            saved = json.loads(path.read_text(encoding="ascii"))
        self.assertEqual(report["summary"], {"total": 0, "matches": 0, "mismatches": 0, "errors": 0})
        self.assertEqual(saved["results"], [])


if __name__ == "__main__":
    unittest.main()
