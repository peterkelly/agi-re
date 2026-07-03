#!/usr/bin/env python3
"""Tests for generated original-engine QEMU fixture resources."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from qemu_fixture import (  # noqa: E402
    DEFAULT_INIT_FLAG,
    SCRATCH_VAR,
    approach_first_object_until_near_action,
    assignn_action,
    build_synthetic_picture_persistent_object_fixture,
    build_synthetic_picture_view_fixture,
    build_synthetic_picture_fixture,
    if_then,
    logic_resource,
    clear_object_bit_0020_action,
    clear_object_field_22_and_global_action,
    clear_object_bits_0900_action,
    clear_object_bit_0002_action,
    move_object_to_action,
    not_flag_set_condition,
    patch_dir_entry,
    patch_logdir_entry_zero,
    persistent_object_logic_payload,
    persistent_object_once_logic_payload,
    picture_logic_payload,
    picture_view_logic_payload,
    rebuild_priority_table_action,
    run_once_logic,
    set_flag_action,
    set_object_bit_0020_action,
    set_object_bit_0002_action,
    set_object_bit_0100_action,
    set_object_bit_0200_action,
    set_object_bit_0800_action,
    set_object_field_1f_from_var_action,
    set_object_field_23_mode1_action,
    set_rect_bounds_action,
    clear_object_bit_0200_action,
    set_object_step_from_var_action,
    set_object_tick_from_var_action,
    setup_transient_object_action,
    start_random_motion_action,
    stop_motion_mode_action,
    volume_record,
)
from agi_graphics import PALETTE, render_picture  # noqa: E402
from compare_picture_capture import compare_picture_capture  # noqa: E402


class QemuFixtureTests(unittest.TestCase):
    def test_picture_logic_payload_shows_picture_and_loops(self) -> None:
        payload = picture_logic_payload(45)
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        self.assertEqual(
            code,
            bytes(
                [
                    0x03,
                    SCRATCH_VAR,
                    45,
                    0x18,
                    SCRATCH_VAR,
                    0x19,
                    SCRATCH_VAR,
                    0x1A,
                    0xFE,
                    0xFD,
                    0xFF,
                ]
            ),
        )
        self.assertEqual(payload[2 + code_len :], bytes([0x00, 0x02, 0x00]))

    def test_picture_view_logic_payload_draws_transient_view_and_loops(self) -> None:
        payload = picture_view_logic_payload(1, 11, 0, 0, 20, 80, 15)
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        self.assertEqual(
            code,
            bytes(
                [
                    0x03,
                    SCRATCH_VAR,
                    1,
                    0x18,
                    SCRATCH_VAR,
                    0x19,
                    SCRATCH_VAR,
                    0x1A,
                    0x1E,
                    11,
                    0x7A,
                    11,
                    0,
                    0,
                    20,
                    80,
                    15,
                    15,
                    0xFE,
                    0xFD,
                    0xFF,
                ]
            ),
        )
        self.assertEqual(payload[2 + code_len :], bytes([0x00, 0x02, 0x00]))

    def test_picture_view_logic_payload_can_insert_pre_overlay_actions(self) -> None:
        payload = picture_view_logic_payload(1, 11, 0, 0, 20, 80, 0, pre_overlay_actions=rebuild_priority_table_action(100))
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        self.assertIn(bytes([0x1A, 0xAE, 100, 0x1E, 11]), code)

    def test_persistent_object_logic_payload_uses_object_table_actions(self) -> None:
        payload = persistent_object_logic_payload(1, 11, 0, 0, 20, 80, 15)
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        self.assertIn(bytes([0x21, 0, 0x29, 0, 11, 0x2B, 0, 0, 0x2F, 0, 0]), code)
        self.assertIn(bytes([0x25, 0, 20, 80, 0x36, 0, 15, 0x23, 0]), code)

    def test_persistent_object_logic_payload_can_append_movement_action(self) -> None:
        payload = persistent_object_logic_payload(
            1,
            11,
            0,
            0,
            20,
            80,
            15,
            post_activate_actions=move_object_to_action(0, 50, 80, 5, 200),
        )
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        self.assertIn(bytes([0x23, 0, 0x51, 0, 50, 80, 5, 200, 0xFE, 0xFD, 0xFF]), code)

    def test_condition_helpers_encode_if_not_flag_then_body(self) -> None:
        body = bytes([0x03, 1, 2])
        block = if_then(not_flag_set_condition(199), body)
        self.assertEqual(block, bytes([0xFF, 0xFD, 0x07, 199, 0xFF, 0x03, 0x00, 0x03, 1, 2]))

    def test_run_once_logic_wraps_actions_with_init_guard_and_end(self) -> None:
        payload = run_once_logic(bytes([0x1A]), init_flag=199)
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        self.assertEqual(code, bytes([0xFF, 0xFD, 0x07, 199, 0xFF, 0x03, 0x00, 0x1A, 0x0C, 199, 0x00]))

    def test_flag_action_helpers_validate_byte_operands(self) -> None:
        self.assertEqual(set_flag_action(DEFAULT_INIT_FLAG), bytes([0x0C, DEFAULT_INIT_FLAG]))
        self.assertEqual(not_flag_set_condition(DEFAULT_INIT_FLAG), bytes([0xFD, 0x07, DEFAULT_INIT_FLAG]))

    def test_persistent_object_once_logic_payload_ends_each_cycle(self) -> None:
        payload = persistent_object_once_logic_payload(
            1,
            11,
            0,
            0,
            20,
            80,
            15,
            post_activate_actions=move_object_to_action(0, 50, 80, 5, 200),
            init_flag=199,
        )
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        self.assertTrue(code.startswith(bytes([0xFF, 0xFD, 0x07, 199, 0xFF])))
        self.assertIn(bytes([0x23, 0, 0x51, 0, 50, 80, 5, 200, 0x0C, 199, 0x00]), code)
        self.assertNotIn(bytes([0xFE, 0xFD, 0xFF]), code)

    def test_persistent_object_once_logic_can_run_guarded_per_cycle_actions(self) -> None:
        payload = persistent_object_once_logic_payload(
            1,
            11,
            0,
            0,
            20,
            80,
            15,
            per_cycle_actions=move_object_to_action(0, 50, 80, 5, 200),
            per_cycle_until_flag=200,
            init_flag=199,
        )
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        self.assertIn(bytes([0x0C, 199, 0xFF, 0xFD, 0x07, 200, 0xFF, 0x06, 0x00]), code)
        self.assertTrue(code.endswith(bytes([0x51, 0, 50, 80, 5, 200, 0x00])))

    def test_volume_record_wraps_payload_with_header(self) -> None:
        record = volume_record(b"abc", volume=3)
        self.assertEqual(record, b"\x12\x34\x03\x03\x00abc")

    def test_logic_resource_wraps_code_with_empty_message_table(self) -> None:
        self.assertEqual(logic_resource(b"\xff"), b"\x01\x00\xff\x00\x02\x00")

    def test_logic_resource_encodes_custom_messages(self) -> None:
        payload = logic_resource(b"\x00", ["HELLO", "look"])
        code_len = payload[0] | (payload[1] << 8)
        self.assertEqual(code_len, 1)
        count_offset = 2 + code_len
        self.assertEqual(payload[count_offset], 2)
        table = payload[count_offset + 1 : count_offset + 7]
        offsets = [table[index] | (table[index + 1] << 8) for index in range(0, len(table), 2)]
        self.assertEqual(offsets[1], 6)
        self.assertEqual(offsets[2], 12)
        self.assertEqual(offsets[0], 17)
        self.assertNotIn(b"HELLO", payload[count_offset + 7 :])

    def test_move_object_to_action_encodes_fixed_operands(self) -> None:
        self.assertEqual(move_object_to_action(0, 50, 80, 5, 200), bytes([0x51, 0, 50, 80, 5, 200]))

    def test_assignn_action_encodes_variable_and_immediate(self) -> None:
        self.assertEqual(assignn_action(249, 5), bytes([0x03, 249, 5]))

    def test_autonomous_motion_actions_encode_fixed_operands(self) -> None:
        self.assertEqual(approach_first_object_until_near_action(1, 25, 214), bytes([0x53, 1, 25, 214]))
        self.assertEqual(clear_object_field_22_and_global_action(2), bytes([0x4E, 2]))
        self.assertEqual(start_random_motion_action(2), bytes([0x54, 2]))
        self.assertEqual(stop_motion_mode_action(2), bytes([0x55, 2]))
        self.assertEqual(set_rect_bounds_action(30, 70, 60, 90), bytes([0x5A, 30, 70, 60, 90]))
        self.assertEqual(set_object_step_from_var_action(1, 249), bytes([0x4F, 1, 249]))
        self.assertEqual(set_object_tick_from_var_action(1, 248), bytes([0x50, 1, 248]))

    def test_setup_transient_object_action_encodes_fixed_operands(self) -> None:
        self.assertEqual(setup_transient_object_action(11, 1, 0, 20, 80, 15), bytes([0x7A, 11, 1, 0, 20, 80, 15, 15]))
        self.assertEqual(setup_transient_object_action(11, 1, 0, 20, 80, 15, 4), bytes([0x7A, 11, 1, 0, 20, 80, 15, 4]))

    def test_set_object_bit_0200_action_encodes_fixed_operand(self) -> None:
        self.assertEqual(set_object_bit_0200_action(3), bytes([0x43, 3]))

    def test_clear_object_bit_0200_action_encodes_fixed_operand(self) -> None:
        self.assertEqual(clear_object_bit_0200_action(3), bytes([0x44, 3]))

    def test_object_bit_0002_actions_encode_fixed_operand(self) -> None:
        self.assertEqual(set_object_bit_0002_action(3), bytes([0x58, 3]))
        self.assertEqual(clear_object_bit_0002_action(3), bytes([0x59, 3]))

    def test_object_bits_0900_actions_encode_fixed_operand(self) -> None:
        self.assertEqual(set_object_bit_0100_action(3), bytes([0x40, 3]))
        self.assertEqual(set_object_bit_0800_action(3), bytes([0x41, 3]))
        self.assertEqual(clear_object_bits_0900_action(3), bytes([0x42, 3]))

    def test_frame_timer_actions_encode_fixed_operands(self) -> None:
        self.assertEqual(set_object_field_1f_from_var_action(3, 249), bytes([0x4C, 3, 249]))
        self.assertEqual(set_object_field_23_mode1_action(3, 77), bytes([0x49, 3, 77]))
        self.assertEqual(clear_object_bit_0020_action(3), bytes([0x46, 3]))
        self.assertEqual(set_object_bit_0020_action(3), bytes([0x47, 3]))

    def test_logdir_patch_points_logic_zero_at_volume_three_offset_zero(self) -> None:
        original = bytes([0x10, 0x6D, 0x1B, 0xFF, 0xFF, 0xFF])
        patched = patch_logdir_entry_zero(original, volume=3, offset=0)
        self.assertEqual(patched[:6], bytes([0x30, 0x00, 0x00, 0xFF, 0xFF, 0xFF]))

    def test_dir_patch_updates_selected_entry(self) -> None:
        original = bytes([0xFF] * 9)
        patched = patch_dir_entry(original, resource_no=2, volume=3, offset=0x12345)
        self.assertEqual(patched[:6], bytes([0xFF] * 6))
        self.assertEqual(patched[6:9], bytes([0x31, 0x23, 0x45]))

    def test_synthetic_picture_fixture_patches_logdir_picdir_and_vol3(self) -> None:
        payload = bytes([0xF0, 0x02, 0xF6, 0, 0, 1, 1, 0xFF])
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = build_synthetic_picture_fixture(payload, Path(temp_dir) / "fixture", picture_no=0)
            vol3 = (fixture / "VOL.3").read_bytes()
            logic_record = volume_record(picture_logic_payload(0), volume=3)
            self.assertTrue(vol3.startswith(logic_record))
            self.assertEqual(vol3[len(logic_record) :], volume_record(payload, volume=3))
            self.assertEqual((fixture / "LOGDIR").read_bytes()[:3], bytes([0x30, 0x00, 0x00]))
            picture_entry = (fixture / "PICDIR").read_bytes()[:3]
            self.assertEqual(picture_entry, bytes([0x30, 0x00, len(logic_record)]))

    def test_synthetic_picture_view_fixture_patches_picture_and_logic(self) -> None:
        payload = bytes([0xFF])
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = build_synthetic_picture_view_fixture(
                payload,
                0,
                11,
                0,
                0,
                20,
                80,
                4,
                Path(temp_dir) / "fixture",
            )
            vol3 = (fixture / "VOL.3").read_bytes()
            logic_record = volume_record(picture_view_logic_payload(0, 11, 0, 0, 20, 80, 4), volume=3)
            self.assertTrue(vol3.startswith(logic_record))
            self.assertEqual(vol3[len(logic_record) :], volume_record(payload, volume=3))
            self.assertEqual((fixture / "LOGDIR").read_bytes()[:3], bytes([0x30, 0x00, 0x00]))
            self.assertEqual((fixture / "PICDIR").read_bytes()[:3], bytes([0x30, 0x00, len(logic_record)]))

    def test_synthetic_picture_persistent_object_fixture_patches_picture_and_logic(self) -> None:
        payload = bytes([0xFF])
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = build_synthetic_picture_persistent_object_fixture(
                payload,
                0,
                11,
                0,
                0,
                20,
                80,
                15,
                Path(temp_dir) / "fixture",
            )
            vol3 = (fixture / "VOL.3").read_bytes()
            logic_record = volume_record(persistent_object_logic_payload(0, 11, 0, 0, 20, 80, 15), volume=3)
            self.assertTrue(vol3.startswith(logic_record))
            self.assertEqual(vol3[len(logic_record) :], volume_record(payload, volume=3))
            self.assertEqual((fixture / "LOGDIR").read_bytes()[:3], bytes([0x30, 0x00, 0x00]))
            self.assertEqual((fixture / "PICDIR").read_bytes()[:3], bytes([0x30, 0x00, len(logic_record)]))

    def test_synthetic_qemu_scaled_picture_capture_compares_equal(self) -> None:
        rendered = render_picture(1)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "scaled.ppm"
            rgb = bytearray()
            black = bytes(PALETTE[0])
            for y in range(400):
                if y >= 168 * 2:
                    rgb.extend(black * 640)
                    continue
                logical_y = y // 2
                row = rendered.visual_nibbles[logical_y * 160 : (logical_y + 1) * 160]
                for nibble in row:
                    rgb.extend(bytes(PALETTE[nibble]) * 4)
            with path.open("wb") as f:
                f.write(b"P6\n640 400\n255\n")
                f.write(rgb)
            comparison = compare_picture_capture(1, path)
        self.assertTrue(comparison.matches)


if __name__ == "__main__":
    unittest.main()
