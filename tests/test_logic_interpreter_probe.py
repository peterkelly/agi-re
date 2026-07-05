#!/usr/bin/env python3
"""Tests for core logic interpreter QEMU probes."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_graphics import HEIGHT, PALETTE, WIDTH, PictureRenderer, compose_frame_on_picture, render_view_frame  # noqa: E402
from logic_interpreter_probe import (  # noqa: E402
    alternating_row_picture_payload,
    base_cases,
    compare_capture,
    load_cases,
    qemu_batch_dos_dir,
    write_report,
)


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


class LogicInterpreterProbeTests(unittest.TestCase):
    def test_base_cases_cover_core_control_flow(self) -> None:
        case_ids = {case.case_id for case in base_cases()}
        self.assertIn("jump_skips_first_draw", case_ids)
        self.assertIn("if_false_skips_then_draw", case_ids)
        self.assertIn("not_condition_runs_then_draw", case_ids)
        self.assertIn("or_group_true_runs_then_draw", case_ids)
        self.assertIn("always_false_condition_skips_then_draw", case_ids)
        self.assertIn("var_inc_reaches_expected_value", case_ids)
        self.assertIn("indirect_assignv_writes_indexed_destination", case_ids)
        self.assertIn("muln_keeps_low_product_byte", case_ids)
        self.assertIn("flag_var_actions_and_condition", case_ids)
        self.assertIn("var_comparison_conditions_all_true", case_ids)
        self.assertIn("object_position_getter_observes_setter", case_ids)
        self.assertIn("call_logic_draws_from_called_logic", case_ids)
        self.assertIn("load_logic_var_then_call_logic_draws", case_ids)
        self.assertIn("switch_room_reentry_dispatches_current_room", case_ids)
        self.assertIn("switch_room_v_reentry_dispatches_current_room", case_ids)
        self.assertIn("switch_room_sets_current_previous_and_clears_boundary", case_ids)
        self.assertIn("switch_room_v_sets_current_previous_and_clears_boundary", case_ids)
        self.assertIn("switch_room_removes_preexisting_persistent_object", case_ids)
        self.assertIn("switch_room_v_removes_preexisting_persistent_object", case_ids)
        self.assertIn("switch_room_boundary_1_sets_object0_bottom_y", case_ids)
        self.assertIn("switch_room_boundary_2_sets_object0_left_x", case_ids)
        self.assertIn("switch_room_boundary_3_sets_object0_top_y", case_ids)
        self.assertIn("switch_room_boundary_4_sets_object0_right_x", case_ids)
        self.assertIn("switch_room_v_boundary_1_sets_object0_bottom_y", case_ids)
        self.assertIn("switch_room_v_boundary_2_sets_object0_left_x", case_ids)
        self.assertIn("switch_room_v_boundary_3_sets_object0_top_y", case_ids)
        self.assertIn("switch_room_v_boundary_4_sets_object0_right_x", case_ids)
        self.assertIn("overlay_picture_var_composes_extra_picture", case_ids)
        self.assertIn("discard_picture_var_allows_reload_and_overlay", case_ids)
        self.assertIn("discard_view_allows_reload_and_draw", case_ids)
        self.assertIn("discard_view_var_allows_reload_and_draw", case_ids)
        self.assertIn("display_message_then_ack_continues_to_draw", case_ids)
        self.assertIn("display_message_var_then_ack_continues_to_draw", case_ids)
        self.assertIn("display_message_configured_then_ack_continues_to_draw", case_ids)
        self.assertIn("display_formatted_message_then_ack_continues_to_draw", case_ids)
        self.assertIn("display_formatted_message_var_then_ack_continues_to_draw", case_ids)
        self.assertIn("display_message_configured_var_then_ack_continues_to_draw", case_ids)
        self.assertIn("prompt_string_to_slot_returns_after_enter", case_ids)
        self.assertIn("prompt_string_to_slot_stores_typed_word", case_ids)
        self.assertIn("prompt_number_to_var_accepts_digits", case_ids)
        self.assertIn("input_line_toggle_refresh_erase_dispatch_smoke", case_ids)
        self.assertIn("input_line_disable_clears_configured_row", case_ids)
        self.assertIn("input_line_enable_clears_configured_row", case_ids)
        self.assertIn("input_line_typed_text_visible_baseline", case_ids)
        self.assertIn("input_line_erase_clears_typed_buffer", case_ids)
        self.assertIn("input_line_refresh_repaints_entered_buffer", case_ids)
        self.assertIn("text_rect_clear_dispatch_smoke", case_ids)
        self.assertIn("text_rect_clear_rows_removes_formatted_text", case_ids)
        self.assertIn("text_rect_clear_bounds_removes_formatted_text", case_ids)
        self.assertIn("close_text_window_state_dispatch_smoke", case_ids)
        self.assertIn("input_width_flag_a3_allows_long_live_input", case_ids)
        self.assertIn("input_width_flag_a4_restores_long_slot_limit", case_ids)
        self.assertIn("close_text_window_state_clears_input_width_flag", case_ids)
        self.assertIn("text_attribute_mode_dispatch_smoke", case_ids)
        self.assertIn("text_attribute_enable_clears_visible_surface", case_ids)
        self.assertIn("text_attribute_pair_changes_attr_mode_clear_color", case_ids)
        self.assertIn("text_attribute_disable_restores_picture_draw", case_ids)
        self.assertIn("screen_shake_dispatch_smoke", case_ids)
        self.assertIn("input_prompt_config_dispatch_smoke", case_ids)
        self.assertIn("input_prompt_empty_message_suppresses_marker", case_ids)
        self.assertIn("status_line_show_hide_dispatch_smoke", case_ids)
        self.assertIn("status_line_hide_clears_configured_row", case_ids)
        self.assertIn("status_line_show_draws_configured_row", case_ids)
        self.assertIn("key_event_mapping_dispatch_smoke", case_ids)
        self.assertIn("input_line_config_operand1_offsets_display_by_8", case_ids)
        self.assertIn("mapped_key_sets_status_byte", case_ids)
        self.assertIn("raw_key_event_available_draws_after_typed_key", case_ids)
        self.assertIn("set_string_from_table_copies_patched_pointer", case_ids)
        self.assertIn("menu_setup_dispatch_smoke", case_ids)
        self.assertIn("menu_flag_dispatch_smoke", case_ids)
        self.assertIn("menu_interactive_enter_sets_status_byte", case_ids)
        self.assertIn("menu_escape_exits_without_status_byte", case_ids)
        self.assertIn("menu_disabled_item_enter_does_not_set_status_byte", case_ids)
        self.assertIn("menu_enable_after_disable_allows_enter_status_byte", case_ids)
        self.assertIn("sound_load_stop_dispatch_smoke", case_ids)
        self.assertIn("sound_start_stop_dispatch_smoke", case_ids)
        self.assertIn("sound_stop_sets_completion_flag", case_ids)
        self.assertIn("priority_screen_enter_returns", case_ids)
        self.assertIn("object_diagnostics_var_enter_returns", case_ids)
        self.assertIn("view_resource_display_immediate_returns", case_ids)
        self.assertIn("view_resource_display_var_returns", case_ids)
        self.assertIn("signature_check_matching_message_returns", case_ids)
        self.assertIn("restart_confirm_escape_continues_to_draw", case_ids)
        self.assertIn("confirm_restart_like_escape_continues_to_draw", case_ids)
        self.assertIn("joystick_calibration_no_joystick_returns", case_ids)
        self.assertIn("display_mode_toggle_guarded_noop_continues", case_ids)
        self.assertIn("display_mode_replay_skips_flag7_unrecorded_picture", case_ids)
        self.assertIn("display_mode_replay_uses_rolled_back_event_count", case_ids)
        self.assertIn("trace_window_config_enable_dispatch_smoke", case_ids)
        self.assertIn("trace_window_enable_draws_box_when_flag10_set", case_ids)
        self.assertIn("log_file_append_dispatch_smoke", case_ids)
        self.assertIn("save_game_escape_continues_to_draw", case_ids)
        self.assertIn("restore_game_escape_continues_to_draw", case_ids)
        self.assertIn("pause_message_then_ack_continues_to_draw", case_ids)
        self.assertIn("heap_status_then_ack_continues_to_draw", case_ids)
        self.assertIn("interpreter_version_then_ack_continues_to_draw", case_ids)
        self.assertIn("diagnostic_global_actions_dispatch_smoke", case_ids)
        self.assertIn("setup_transient_object_var_draws_selected_cel", case_ids)
        self.assertIn("object_right_rect_condition_true", case_ids)
        self.assertIn("set_string_from_message_equal_normalized", case_ids)
        self.assertIn("input_word_sequence_matches_two_words", case_ids)
        self.assertIn("input_word_sequence_wildcard_matches_word", case_ids)
        self.assertIn("input_word_sequence_terminator_accepts_prefix", case_ids)
        self.assertIn("input_word_sequence_terminator_matches_unknown_word", case_ids)
        self.assertIn("inventory_marker_from_var_var", case_ids)
        self.assertIn("inventory_selection_enter_sets_var19", case_ids)
        self.assertIn("inventory_selection_escape_sets_var19_ff", case_ids)
        self.assertIn("inventory_selection_noninteractive_ack_returns", case_ids)
        self.assertIn("object_view_metadata_getters", case_ids)
        self.assertIn("object_field_24_var_getter_observes_value", case_ids)
        self.assertIn("object_distance_inactive_pair_sets_ff", case_ids)
        self.assertIn("clear_object_fields_21_22_clears_direction", case_ids)
        self.assertIn("object_bitfield_actions_dispatch_smoke", case_ids)
        self.assertIn("object_add_pos_from_vars_getter_observes_sum", case_ids)
        self.assertIn("random_equal_bounds_stores_bound", case_ids)
        self.assertIn("noop_7f_continues_to_draw", case_ids)
        self.assertIn("noop_9b_consumes_two_operands_then_draws", case_ids)
        self.assertIn("noop_af_runtime_consumes_no_operand", case_ids)
        self.assertIn("set_object_pos_dirty_getter_observes_values", case_ids)
        self.assertIn("set_object_pos_dirty_var_getter_observes_values", case_ids)
        self.assertIn("deactivate_object_removes_persistent_draw", case_ids)
        self.assertIn("clear_all_object_bits_keeps_current_draw_entry", case_ids)
        self.assertIn("load_view_var_allows_following_draw", case_ids)
        self.assertIn("object_field_23_mode0_dispatch_smoke", case_ids)
        self.assertIn("object_field_23_mode1_clears_flag", case_ids)
        self.assertIn("object_field_23_mode3_dispatch_smoke", case_ids)
        self.assertIn("object_field_23_mode2_clears_flag", case_ids)
        self.assertIn("horizon_clamps_object_when_bit_clear", case_ids)
        self.assertIn("horizon_exempt_bit_keeps_object_above_horizon", case_ids)
        self.assertIn("horizon_clear_exempt_bit_restores_clamp", case_ids)
        self.assertIn("clear_fixed_priority_bit_uses_derived_priority", case_ids)
        self.assertIn("clear_bit_0010_moves_object_behind_set_partition", case_ids)
        self.assertIn("set_bit_0010_moves_object_over_clear_partition", case_ids)
        self.assertIn("clear_bit_2000_allows_direction_group_selection", case_ids)
        self.assertIn("set_bit_2000_suppresses_direction_group_selection", case_ids)
        self.assertIn("clear_bit_2000_two_or_three_group_direction6_selects_group1", case_ids)
        self.assertIn("clear_bit_2000_two_or_three_group_direction5_is_sentinel", case_ids)
        self.assertIn("clear_bit_2000_field01_countdown_eventually_selects_group", case_ids)
        self.assertIn("clear_bit_2000_requires_field01_equal_one_when_forced", case_ids)
        self.assertEqual(len(case_ids), len(base_cases()))
        self.assertGreaterEqual(len(case_ids), 70)

    def test_json_case_loading(self) -> None:
        case = base_cases()[0]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cases.json"
            path.write_text(json.dumps([case.__dict__]) + "\n", encoding="ascii")
            loaded = load_cases(path)
        self.assertEqual(loaded, [case])

    def test_case_filtering(self) -> None:
        loaded = load_cases(None, ["call_logic_draws_from_called_logic"])
        self.assertEqual([case.case_id for case in loaded], ["call_logic_draws_from_called_logic"])

    def test_dos_dir_name_is_stable(self) -> None:
        self.assertEqual(qemu_batch_dos_dir("logic", 2), "LOG00002")
        self.assertEqual(qemu_batch_dos_dir("!!!", 2), "LI00002")

    def test_compare_capture_matches_expected_draw(self) -> None:
        case = next(item for item in base_cases() if item.case_id == "jump_skips_first_draw")
        picture = PictureRenderer(case.picture_payload).render(case.picture_no)
        frame = render_view_frame(case.expected_view_no, case.expected_group_no, case.expected_frame_no)
        expected = compose_frame_on_picture(
            picture,
            frame,
            case.expected_x,
            case.expected_baseline_y,
            case.expected_priority,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = Path(temp_dir) / "capture.ppm"
            write_scaled_capture(capture, expected.visual_nibbles)
            comparison = compare_capture(case, capture)
        self.assertEqual(comparison.status, "match")

    def test_compare_capture_uses_expected_picture_payload(self) -> None:
        case = next(item for item in base_cases() if item.case_id == "overlay_picture_var_composes_extra_picture")
        picture = PictureRenderer(case.expected_picture_payload).render(case.picture_no)
        frame = render_view_frame(case.expected_view_no, case.expected_group_no, case.expected_frame_no)
        expected = compose_frame_on_picture(
            picture,
            frame,
            case.expected_x,
            case.expected_baseline_y,
            case.expected_priority,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = Path(temp_dir) / "capture.ppm"
            write_scaled_capture(capture, expected.visual_nibbles)
            comparison = compare_capture(case, capture)
        self.assertEqual(comparison.status, "match")

    def test_display_mode_replay_cases_expect_row_interleaving(self) -> None:
        expected_payload = alternating_row_picture_payload(0x06, 0x04).hex()
        for case_id in (
            "display_mode_replay_skips_flag7_unrecorded_picture",
            "display_mode_replay_uses_rolled_back_event_count",
        ):
            case = next(item for item in base_cases() if item.case_id == case_id)
            self.assertFalse(case.compare_view)
            self.assertEqual(case.expected_picture_payload_hex, expected_payload)
            picture = PictureRenderer(case.expected_picture_payload).render(case.picture_no)
            self.assertEqual(set(picture.visual_nibbles[0:WIDTH]), {0x06})
            self.assertEqual(set(picture.visual_nibbles[WIDTH : WIDTH * 2]), {0x04})

    def test_text_rect_clear_cases_expect_display_surface_rectangles(self) -> None:
        cases = {case.case_id: case for case in base_cases()}
        self.assertEqual(
            cases["text_rect_clear_rows_removes_formatted_text"].expected_visual_rects,
            [{"left": 0, "top": 40, "right": WIDTH - 1, "bottom": 55, "color": 0}],
        )
        self.assertEqual(
            cases["text_rect_clear_bounds_removes_formatted_text"].expected_visual_rects,
            [{"left": 20, "top": 64, "right": 83, "bottom": 71, "color": 0}],
        )
        self.assertEqual(
            cases["input_line_disable_clears_configured_row"].expected_visual_rects,
            [{"left": 0, "top": 40, "right": WIDTH - 1, "bottom": 47, "color": 0}],
        )
        self.assertEqual(
            cases["input_line_enable_clears_configured_row"].expected_visual_rects,
            [{"left": 0, "top": 40, "right": WIDTH - 1, "bottom": 47, "color": 0}],
        )
        self.assertEqual(
            cases["input_line_erase_clears_typed_buffer"].expected_visual_rects,
            [{"left": 0, "top": 40, "right": WIDTH - 1, "bottom": 47, "color": 0}],
        )
        self.assertEqual(
            cases["status_line_hide_clears_configured_row"].expected_visual_rects,
            [{"left": 0, "top": 40, "right": WIDTH - 1, "bottom": 47, "color": 0}],
        )
        self.assertEqual(
            cases["text_attribute_enable_clears_visible_surface"].expected_visual_rects,
            [{"left": 0, "top": 0, "right": WIDTH - 1, "bottom": HEIGHT - 1, "color": 0}],
        )
        self.assertFalse(cases["text_attribute_enable_clears_visible_surface"].compare_view)
        self.assertEqual(
            cases["text_attribute_pair_changes_attr_mode_clear_color"].expected_visual_rects,
            [{"left": 0, "top": 0, "right": WIDTH - 1, "bottom": HEIGHT - 1, "color": 15}],
        )
        self.assertFalse(cases["text_attribute_pair_changes_attr_mode_clear_color"].compare_view)
        self.assertEqual(
            cases["input_prompt_empty_message_suppresses_marker"].expected_visual_rects,
            [{"left": 0, "top": 40, "right": WIDTH - 1, "bottom": 47, "color": 0}],
        )

    def test_rect_checks_can_match_without_glyph_model(self) -> None:
        case = next(item for item in base_cases() if item.case_id == "status_line_show_draws_configured_row")
        nibbles = bytearray([0] * (WIDTH * HEIGHT))
        nibbles[40 * WIDTH] = 15
        nibbles[40 * WIDTH + 1] = 15
        nibbles[40 * WIDTH + 2] = 15
        nibbles[40 * WIDTH + 3] = 15
        nibbles[40 * WIDTH + 4] = 15
        nibbles[40 * WIDTH + 5] = 15
        nibbles[40 * WIDTH + 6] = 15
        nibbles[40 * WIDTH + 7] = 15
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = Path(temp_dir) / "capture.ppm"
            write_scaled_capture(capture, bytes(nibbles))
            comparison = compare_capture(case, capture)
        self.assertEqual(comparison.status, "match")

    def test_rect_checks_report_mismatch(self) -> None:
        case = next(item for item in base_cases() if item.case_id == "status_line_show_draws_configured_row")
        with tempfile.TemporaryDirectory() as temp_dir:
            capture = Path(temp_dir) / "capture.ppm"
            write_scaled_capture(capture, bytes([0] * (WIDTH * HEIGHT)))
            comparison = compare_capture(case, capture)
        self.assertEqual(comparison.status, "mismatch")
        self.assertIn("below", comparison.error or "")

    def test_trace_window_rect_check_tracks_source_bounds(self) -> None:
        case = next(item for item in base_cases() if item.case_id == "trace_window_enable_draws_box_when_flag10_set")
        self.assertFalse(case.compare_view)
        self.assertEqual(
            case.expected_rect_checks,
            [
                {
                    "mode": "contains_color",
                    "left": 0,
                    "top": 5,
                    "right": WIDTH - 1,
                    "bottom": 28,
                    "color": 4,
                    "min_count": 180,
                },
                {
                    "mode": "contains_color",
                    "left": 0,
                    "top": 6,
                    "right": WIDTH - 1,
                    "bottom": 31,
                    "color": 15,
                    "min_count": 3000,
                },
                {
                    "mode": "contains_color",
                    "left": 8,
                    "top": 18,
                    "right": 110,
                    "bottom": 30,
                    "color": 0,
                    "min_count": 80,
                },
            ],
        )

    def test_input_width_flag_cases_have_distinct_row_checks(self) -> None:
        cases = {item.case_id: item for item in base_cases()}
        self.assertEqual(
            cases["input_width_flag_a3_allows_long_live_input"].expected_rect_checks,
            [
                {
                    "mode": "contains_color",
                    "left": 0,
                    "top": 48,
                    "right": WIDTH - 1,
                    "bottom": 55,
                    "color": 0,
                    "min_count": 100,
                }
            ],
        )
        self.assertEqual(
            cases["input_width_flag_a4_restores_long_slot_limit"].expected_rect_checks,
            [
                {
                    "mode": "no_color",
                    "left": 0,
                    "top": 48,
                    "right": WIDTH - 1,
                    "bottom": 55,
                    "color": 0,
                    "max_count": 20,
                }
            ],
        )
        self.assertEqual(
            cases["close_text_window_state_clears_input_width_flag"].expected_rect_checks,
            cases["input_width_flag_a4_restores_long_slot_limit"].expected_rect_checks,
        )

    def test_report_summary_counts_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.json"
            report = write_report([], path)
            saved = json.loads(path.read_text(encoding="ascii"))
        self.assertEqual(report["summary"], {"total": 0, "matches": 0, "mismatches": 0, "errors": 0})
        self.assertEqual(saved["results"], [])


if __name__ == "__main__":
    unittest.main()
