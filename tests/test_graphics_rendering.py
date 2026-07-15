#!/usr/bin/env python3
"""Compatibility-oriented tests for clean-room picture/view rendering."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_graphics import (  # noqa: E402
    ControlAcceptance,
    DEFAULT_CELL,
    HEIGHT,
    DirtyRect,
    ObjectDrawCandidate,
    PictureRenderer,
    RenderedFrame,
    decode_view_loop_header,
    WIDTH,
    automatic_direction_loop,
    control_acceptance_scan,
    approach_motion_update,
    dirty_rect_union,
    draw_frame_on_buffer,
    iter_view_frames,
    iter_valid_resources,
    _mirror_view_row_runs,
    object_update_draw_order,
    object_update_sort_key,
    object_distance_value,
    find_pattern_table_offsets,
    pattern_column_mask,
    pattern_max_doubled_x,
    pattern_max_doubled_x_for_radius_one,
    pattern_row_words,
    pattern_table_offsets,
    picture_command_is_supported,
    picture_payload,
    picture_to_ppm,
    priority_value_to_sort_y,
    render_picture,
    render_view_frame,
    search_object_placement,
    random_motion_update,
    target_axis_relation,
    target_direction,
    update_packed_view_loop_orientation,
)
from agi_resources import read_resource_payload  # noqa: E402
from disassemble_logic import SQ2, read_dir_entries, read_volume_payload  # noqa: E402
from ppm_tools import non_background_bbox, read_ppm, unique_colors  # noqa: E402


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def changed_visual_pixels(rendered) -> set[tuple[int, int]]:
    return {
        (idx % WIDTH, idx // WIDTH)
        for idx, cell in enumerate(rendered.cells)
        if (cell & 0x0F) != (DEFAULT_CELL & 0x0F)
    }


def changed_control_pixels(rendered) -> set[tuple[int, int]]:
    return {
        (idx % WIDTH, idx // WIDTH)
        for idx, cell in enumerate(rendered.cells)
        if (cell & 0xF0) != (DEFAULT_CELL & 0xF0)
    }


class ObjectMotionModelTests(unittest.TestCase):
    def test_early_object_distance_wraps_instead_of_saturating(self) -> None:
        self.assertEqual(object_distance_value(0, 0, 160, 167), 0xFE)
        self.assertEqual(
            object_distance_value(0, 0, 160, 167, saturate=False),
            71,
        )

    def test_early_automatic_loop_selection_is_not_cadence_gated(self) -> None:
        self.assertEqual(
            automatic_direction_loop(
                3, 4, 5, cadence_countdown=7, require_countdown_one=False
            ),
            2,
        )
        self.assertEqual(
            automatic_direction_loop(3, 4, 5, cadence_countdown=7),
            3,
        )

    def test_automatic_loop_tables_cover_two_and_four_loop_views(self) -> None:
        self.assertEqual(automatic_direction_loop(1, 2, 3), 0)
        self.assertEqual(automatic_direction_loop(0, 3, 7), 1)
        self.assertEqual(automatic_direction_loop(0, 4, 1), 3)
        self.assertEqual(automatic_direction_loop(2, 5, 1), 2)
        self.assertEqual(automatic_direction_loop(2, 5, 1, four_or_more=True), 3)

    def test_target_axis_relation_uses_strict_band(self) -> None:
        self.assertEqual(target_axis_relation(-5, 5), 0)
        self.assertEqual(target_axis_relation(-4, 5), 1)
        self.assertEqual(target_axis_relation(4, 5), 1)
        self.assertEqual(target_axis_relation(5, 5), 2)

    def test_target_direction_uses_nine_cell_grid(self) -> None:
        self.assertEqual(target_direction(20, 20, 30, 10, 5), 2)
        self.assertEqual(target_direction(20, 20, 22, 18, 5), 0)
        self.assertEqual(target_direction(20, 20, 10, 30, 5), 6)

    def test_random_motion_decrements_without_reselection(self) -> None:
        self.assertEqual(random_motion_update(3, 10, False, ()), (3, 9))

    def test_random_motion_rejects_short_countdowns(self) -> None:
        self.assertEqual(random_motion_update(3, 0, False, (20, 1, 57)), (2, 6))

    def test_approach_initial_sentinel_uses_direct_direction(self) -> None:
        self.assertEqual(
            approach_motion_update(0, 0, 100, 0, 10, 5, 0, 0xFF, False),
            (3, 0, False),
        )

    def test_approach_exact_threshold_is_not_complete(self) -> None:
        self.assertEqual(
            approach_motion_update(0, 0, 35, 0, 35, 5, 0, 0, False),
            (3, 0, False),
        )
        self.assertEqual(
            approach_motion_update(0, 0, 30, 0, 35, 5, 0, 0, False),
            (0, 0, True),
        )

    def test_approach_stationary_recovery_samples_nonzero_direction_and_delay(self) -> None:
        self.assertEqual(
            approach_motion_update(
                0, 0, 100, 0, 10, 5, 3, 0, True, (9, 7, 3, 55, 60)
            ),
            (7, 9, False),
        )

    def test_approach_retry_delay_counts_down_before_direct_mode_resumes(self) -> None:
        self.assertEqual(
            approach_motion_update(0, 0, 100, 0, 10, 5, 7, 9, False),
            (7, 4, False),
        )
        self.assertEqual(
            approach_motion_update(0, 0, 100, 0, 10, 5, 7, 4, False),
            (7, 0, False),
        )
        self.assertEqual(
            approach_motion_update(0, 0, 100, 0, 10, 5, 7, 0, False),
            (3, 0, False),
        )


class PictureRenderingTests(unittest.TestCase):
    def test_picture_command_profile_boundary(self) -> None:
        self.assertTrue(picture_command_is_supported(0xF8, pattern_commands=False))
        self.assertFalse(picture_command_is_supported(0xF9, pattern_commands=False))
        self.assertTrue(picture_command_is_supported(0xFA, pattern_commands=True))
        self.assertFalse(picture_command_is_supported(0xFF, pattern_commands=True))

    def test_picture_directory_has_renderable_entries(self) -> None:
        present = [picture_no for picture_no, _payload in iter_valid_resources("PICDIR")]
        self.assertEqual(len(present), 74)
        self.assertIn(1, present)

    def test_picdir_has_one_invalid_sentinel_like_entry(self) -> None:
        invalid = []
        for picture_no, entry in enumerate(read_dir_entries(SQ2 / "PICDIR")):
            if entry is None:
                continue
            try:
                read_volume_payload(*entry)
            except ValueError:
                invalid.append((picture_no, entry))
        self.assertEqual(invalid, [(147, (0, 0x2FFFF))])

    def test_all_valid_pictures_render(self) -> None:
        for picture_no, _payload in iter_valid_resources("PICDIR"):
            with self.subTest(picture=picture_no):
                rendered = render_picture(picture_no)
                self.assertEqual(len(rendered.cells), WIDTH * HEIGHT)

    def test_picture_one_renders_deterministically(self) -> None:
        rendered = render_picture(1)
        self.assertEqual(len(rendered.cells), WIDTH * HEIGHT)
        self.assertNotEqual(rendered.cells, bytes([DEFAULT_CELL]) * (WIDTH * HEIGHT))
        self.assertEqual(
            digest(rendered.cells),
            "6b411907c5146fdb561c0b4dcf9632e83137af03afa12fcead8323b74c47a535",
        )

    def test_longest_picture_sample_renders_deterministically(self) -> None:
        rendered = render_picture(45)
        self.assertEqual(len(rendered.cells), WIDTH * HEIGHT)
        self.assertNotEqual(rendered.cells, bytes([DEFAULT_CELL]) * (WIDTH * HEIGHT))
        self.assertEqual(
            digest(rendered.cells),
            "7e8132ddf0658ada246440e409f0801a416d88f003495b7a9f55fbee23fb3974",
        )

    def test_picture_payload_terminates_with_ff(self) -> None:
        for picture_no, payload in iter_valid_resources("PICDIR"):
            with self.subTest(picture=picture_no):
                self.assertIn(0xFF, payload)
                self.assertEqual(payload[-1], 0xFF)

    def test_picture_command_byte_census(self) -> None:
        counts: dict[int, int] = {}
        for _picture_no, payload in iter_valid_resources("PICDIR"):
            for value in payload:
                if value >= 0xF0:
                    counts[value] = counts.get(value, 0) + 1
        self.assertEqual(
            counts,
            {
                0xF0: 4746,
                0xF1: 309,
                0xF2: 1018,
                0xF3: 425,
                0xF6: 7736,
                0xF7: 9282,
                0xF8: 1447,
                0xF9: 22,
                0xFA: 701,
                0xFF: 74,
            },
        )

    def test_pattern_tables_decode_from_agidata(self) -> None:
        self.assertEqual(pattern_table_offsets(), (0x15F9, 0x1619))
        self.assertEqual(
            [pattern_column_mask(column) for column in range(8)],
            [0x8000, 0x2000, 0x0800, 0x0200, 0x0080, 0x0020, 0x0008, 0x0002],
        )
        self.assertEqual(pattern_row_words(0), [0x8000])
        self.assertEqual(pattern_row_words(2), [0x7000, 0xF800, 0xF800, 0xF800, 0x7000])
        self.assertEqual(len(pattern_row_words(7)), 15)
        self.assertEqual(pattern_max_doubled_x(), 0x140)

    def test_pattern_tables_are_found_structurally(self) -> None:
        data = bytearray(0x200)
        mask_offset = 0x20
        pointer_offset = 0x40
        values = [0x8000, 0x2000, 0x0800, 0x0200, 0x0080, 0x0020, 0x0008, 0x0002]
        for column, value in enumerate(values):
            data[mask_offset + column * 4 : mask_offset + column * 4 + 2] = value.to_bytes(2, "little")
        rows_offset = 0x80
        for radius in range(8):
            data[pointer_offset + radius * 2 : pointer_offset + radius * 2 + 2] = rows_offset.to_bytes(2, "little")
        self.assertEqual(find_pattern_table_offsets(bytes(data)), (mask_offset, pointer_offset))

    def test_pattern_family_selects_horizontal_clamp(self) -> None:
        self.assertEqual(
            pattern_max_doubled_x_for_radius_one([0xE000, 0xE000, 0xE000]),
            0x140,
        )
        self.assertEqual(
            pattern_max_doubled_x_for_radius_one([0x4000, 0xE000, 0x4000]),
            0x13E,
        )

    def test_visual_operand_consumes_command_like_raw_byte(self) -> None:
        payload = bytes([0xF0, 0xF2, 0xF6, 1, 1, 1, 1, 0xFF])
        rendered = PictureRenderer(payload).render()
        self.assertEqual(changed_visual_pixels(rendered), {(1, 1)})
        self.assertEqual(rendered.cells[1 * WIDTH + 1] & 0x0F, 2)
        self.assertEqual(rendered.cells[1 * WIDTH + 1] >> 4, 4)

    def test_control_operand_consumes_command_like_raw_byte(self) -> None:
        payload = bytes([0xF2, 0xF1, 0xF6, 1, 1, 1, 1, 0xFF])
        rendered = PictureRenderer(payload).render()
        self.assertEqual(changed_control_pixels(rendered), {(1, 1)})
        self.assertEqual(rendered.cells[1 * WIDTH + 1] >> 4, 1)
        self.assertEqual(rendered.cells[1 * WIDTH + 1] & 0x0F, 0x0F)

    def test_pattern_mode_operand_consumes_command_like_raw_byte(self) -> None:
        payload = bytes([0xF9, 0xFA, 0xF0, 4, 0xF6, 1, 1, 1, 1, 0xFF])
        rendered = PictureRenderer(payload).render()
        self.assertEqual(changed_visual_pixels(rendered), {(1, 1)})
        self.assertEqual(rendered.cells[1 * WIDTH + 1] & 0x0F, 4)

    def test_2411_pattern_commands_plot_single_coordinate_pixels(self) -> None:
        payload = bytes(
            [0xF0, 4, 0xF9, 0x27, 0xFA, 40, 40, 42, 42, 0xFF]
        )

        rendered = PictureRenderer(payload, pattern_brushes=False).render()

        self.assertEqual(changed_visual_pixels(rendered), {(40, 40), (42, 42)})

    def test_corner_path_y_first_draws_alternating_segments(self) -> None:
        payload = bytes([0xF0, 4, 0xF4, 5, 5, 8, 12, 6, 0xFF])
        rendered = PictureRenderer(payload).render()
        expected = (
            {(5, y) for y in range(5, 9)}
            | {(x, 8) for x in range(5, 13)}
            | {(12, y) for y in range(6, 9)}
        )
        self.assertEqual(changed_visual_pixels(rendered), expected)

    def test_corner_path_x_first_draws_alternating_segments(self) -> None:
        payload = bytes([0xF0, 5, 0xF5, 5, 5, 12, 8, 6, 0xFF])
        rendered = PictureRenderer(payload).render()
        expected = (
            {(x, 5) for x in range(5, 13)}
            | {(12, y) for y in range(5, 9)}
            | {(x, 8) for x in range(6, 13)}
        )
        self.assertEqual(changed_visual_pixels(rendered), expected)

    def test_seed_fill_prefers_visual_test_channel_but_writes_all_active_channels(self) -> None:
        payload = bytes(
            [
                0xF2,
                0x02,
                0xF0,
                0x01,
                0xF8,
                0x00,
                0x00,
                0xFF,
            ]
        )
        rendered = PictureRenderer(payload).render()
        self.assertEqual(set(rendered.cells), {0x21})

    def test_seed_fill_uses_control_test_channel_when_visual_is_disabled(self) -> None:
        payload = bytes(
            [
                0xF2,
                0x02,
                0xF8,
                0x00,
                0x00,
                0xFF,
            ]
        )
        rendered = PictureRenderer(payload).render()
        self.assertEqual(set(rendered.cells), {0x2F})

    def test_seed_fill_stops_at_full_height_visual_barrier(self) -> None:
        payload = bytes(
            [
                0xF0,
                0x02,
                0xF6,
                80,
                0,
                80,
                167,
                0xF0,
                0x03,
                0xF8,
                10,
                10,
                0xFF,
            ]
        )
        rendered = PictureRenderer(payload).render()
        for y in range(HEIGHT):
            self.assertEqual(rendered.cells[y * WIDTH + 79] & 0x0F, 3)
            self.assertEqual(rendered.cells[y * WIDTH + 80] & 0x0F, 2)
            self.assertEqual(rendered.cells[y * WIDTH + 81] & 0x0F, 0x0F)

    def test_seed_fill_accepts_multiple_seed_pairs_in_one_command(self) -> None:
        payload = bytes(
            [
                0xF0,
                0x02,
                0xF4,
                10,
                10,
                20,
                20,
                10,
                10,
                0xF4,
                30,
                10,
                20,
                40,
                10,
                30,
                0xF0,
                0x03,
                0xF8,
                15,
                15,
                35,
                15,
                0xFF,
            ]
        )
        rendered = PictureRenderer(payload).render()
        self.assertEqual(rendered.cells[15 * WIDTH + 15] & 0x0F, 3)
        self.assertEqual(rendered.cells[15 * WIDTH + 35] & 0x0F, 3)
        self.assertEqual(rendered.cells[15 * WIDTH + 25] & 0x0F, 0x0F)
        self.assertEqual(rendered.cells[10 * WIDTH + 10] & 0x0F, 2)
        self.assertEqual(rendered.cells[10 * WIDTH + 30] & 0x0F, 2)

    def test_control_seed_fill_ignores_visual_only_barrier(self) -> None:
        payload = bytes(
            [
                0xF0,
                0x02,
                0xF6,
                80,
                0,
                80,
                167,
                0xF1,
                0xF2,
                0x06,
                0xF8,
                10,
                10,
                0xFF,
            ]
        )
        rendered = PictureRenderer(payload).render()
        self.assertEqual(rendered.cells[10 * WIDTH + 10] >> 4, 6)
        self.assertEqual(rendered.cells[10 * WIDTH + 81] >> 4, 6)
        self.assertEqual(rendered.cells[10 * WIDTH + 80] & 0x0F, 2)
        self.assertEqual(rendered.cells[10 * WIDTH + 81] & 0x0F, 0x0F)

    def test_absolute_line_uses_interpreter_step_pattern(self) -> None:
        payload = bytes([0xF0, 0x00, 0xF6, 0x00, 0x00, 0x03, 0x01, 0xFF])
        rendered = PictureRenderer(payload).render()
        self.assertEqual(changed_visual_pixels(rendered), {(0, 0), (1, 0), (2, 1), (3, 1)})

    def test_relative_line_decodes_packed_delta_and_uses_same_step_pattern(self) -> None:
        payload = bytes([0xF0, 0x00, 0xF7, 0x00, 0x00, 0x31, 0xFF])
        rendered = PictureRenderer(payload).render()
        self.assertEqual(changed_visual_pixels(rendered), {(0, 0), (1, 0), (2, 1), (3, 1)})

    def test_relative_line_x_underflow_wraps_then_clamps_to_right_edge(self) -> None:
        payload = bytes([0xF0, 0x02, 0xF7, 0x00, 0x0A, 0x90, 0xFF])
        rendered = PictureRenderer(payload).render()
        changed = changed_visual_pixels(rendered)
        self.assertEqual(len(changed), WIDTH)
        self.assertIn((0, 10), changed)
        self.assertIn((159, 10), changed)

    def test_relative_line_y_underflow_wraps_then_clamps_to_bottom_edge(self) -> None:
        payload = bytes([0xF0, 0x02, 0xF7, 0x0A, 0x00, 0x09, 0xFF])
        rendered = PictureRenderer(payload).render()
        changed = changed_visual_pixels(rendered)
        self.assertEqual(len(changed), HEIGHT)
        self.assertIn((10, 0), changed)
        self.assertIn((10, 167), changed)

    def test_long_diagonal_uses_byte_width_line_accumulators(self) -> None:
        payload = bytes([0xF0, 0x02, 0xF6, 0x9F, 0xA7, 0x00, 0x00, 0xFF])
        rendered = PictureRenderer(payload).render()
        changed = changed_visual_pixels(rendered)
        self.assertEqual(len(changed), 168)
        self.assertIn((159, 167), changed)
        self.assertIn((25, 0), changed)
        self.assertIn((25, 1), changed)
        self.assertNotIn((0, 0), changed)

    def test_pattern_edge_column_wraps_to_next_scanline(self) -> None:
        payload = bytes([0xF0, 0x09, 0xF9, 0x17, 0xFA, 0x9F, 0xA7, 0xFF])
        rendered = PictureRenderer(payload).render()
        visual = rendered.visual_nibbles
        self.assertEqual(visual[154 * WIDTH + 0], 9)
        self.assertEqual(visual[167 * WIDTH + 0], 9)
        self.assertNotEqual(visual[153 * WIDTH + 0], 9)

    def test_pattern_mode_bit_10_bypasses_shape_mask(self) -> None:
        payload = bytes([0xF0, 0x0B, 0xF9, 0x13, 0xFA, 80, 80, 0xFF])
        rendered = PictureRenderer(payload).render()
        changed = changed_visual_pixels(rendered)
        self.assertEqual(len(changed), 28)
        for y in range(77, 84):
            for x in range(78, 82):
                self.assertIn((x, y), changed)

    def test_interleaved_line_fill_pattern_order_is_sequential(self) -> None:
        payload = bytes(
            [
                0xF0,
                0x02,
                0xF4,
                20,
                20,
                40,
                40,
                20,
                20,
                0xF0,
                0x03,
                0xF8,
                30,
                30,
                0xF0,
                0x04,
                0xF6,
                20,
                30,
                40,
                30,
                0xF0,
                0x05,
                0xF9,
                0x14,
                0xFA,
                30,
                30,
                0xFF,
            ]
        )
        rendered = PictureRenderer(payload).render()
        visual = rendered.visual_nibbles
        self.assertEqual(visual[20 * WIDTH + 20], 2)
        self.assertEqual(visual[25 * WIDTH + 25], 3)
        self.assertEqual(visual[30 * WIDTH + 22], 4)
        self.assertEqual(visual[30 * WIDTH + 30], 5)

    def test_pattern_plot_writes_all_active_channels(self) -> None:
        payload = bytes([0xF2, 5, 0xF0, 3, 0xF9, 0x12, 0xFA, 40, 40, 0xFF])
        rendered = PictureRenderer(payload).render()
        visual = changed_visual_pixels(rendered)
        control = changed_control_pixels(rendered)
        self.assertEqual(visual, control)
        self.assertIn((40, 40), visual)
        self.assertEqual(rendered.cells[40 * WIDTH + 40], 0x53)

    def test_pattern_plot_respects_visual_disable(self) -> None:
        payload = bytes([0xF0, 6, 0xF1, 0xF2, 5, 0xF9, 0x12, 0xFA, 40, 40, 0xFF])
        rendered = PictureRenderer(payload).render()
        self.assertEqual(changed_visual_pixels(rendered), set())
        self.assertIn((40, 40), changed_control_pixels(rendered))
        self.assertEqual(rendered.cells[40 * WIDTH + 40], 0x5F)

    def test_pattern_plot_respects_control_disable(self) -> None:
        payload = bytes([0xF2, 5, 0xF3, 0xF0, 6, 0xF9, 0x12, 0xFA, 40, 40, 0xFF])
        rendered = PictureRenderer(payload).render()
        self.assertIn((40, 40), changed_visual_pixels(rendered))
        self.assertEqual(changed_control_pixels(rendered), set())
        self.assertEqual(rendered.cells[40 * WIDTH + 40], 0x46)

    def test_command_byte_terminates_incomplete_absolute_line_pair_and_resumes_scanner(self) -> None:
        payload = bytes([0xF0, 2, 0xF6, 10, 0xF0, 3, 0xF6, 20, 20, 20, 20, 0xFF])
        rendered = PictureRenderer(payload).render()
        self.assertEqual(changed_visual_pixels(rendered), {(20, 20)})
        self.assertEqual(rendered.visual_nibbles[20 * WIDTH + 20], 3)

    def test_command_byte_terminates_corner_path_and_resumes_scanner(self) -> None:
        payload = bytes([0xF0, 2, 0xF4, 10, 10, 20, 0xF0, 4, 0xF6, 30, 30, 30, 30, 0xFF])
        rendered = PictureRenderer(payload).render()
        changed = changed_visual_pixels(rendered)
        self.assertEqual({(10, y) for y in range(10, 21)} | {(30, 30)}, changed)
        self.assertEqual(rendered.visual_nibbles[30 * WIDTH + 30], 4)

    def test_command_byte_terminates_seed_fill_list_and_resumes_scanner(self) -> None:
        payload = bytes([0xF0, 3, 0xF8, 0, 0, 0xF0, 4, 0xF6, 0, 0, 0, 0, 0xFF])
        rendered = PictureRenderer(payload).render()
        self.assertEqual(rendered.visual_nibbles[0], 4)
        self.assertEqual(rendered.visual_nibbles[1], 3)
        self.assertEqual(rendered.visual_nibbles[-1], 3)


class ViewRenderingTests(unittest.TestCase):
    def test_packed_loop_header_exposes_count_and_mutable_orientation(self) -> None:
        state = decode_view_loop_header(0xC4, packed_orientation=True)
        self.assertEqual(state.cel_count, 4)
        self.assertTrue(state.orientation_is_mutable)
        self.assertTrue(state.mirror_rows_on_orientation_change)
        self.assertEqual(state.orientation, 0)

        rewritten, mirror = update_packed_view_loop_orientation(0xC4, 1)
        self.assertEqual(rewritten, 0xD4)
        self.assertTrue(mirror)
        self.assertEqual(
            update_packed_view_loop_orientation(rewritten, 1),
            (0xD4, False),
        )
        self.assertEqual(
            update_packed_view_loop_orientation(rewritten, 0),
            (0xC4, True),
        )

    def test_packed_loop_header_limits_frame_iteration_to_low_nibble(self) -> None:
        payload = bytes(
            [
                1, 1, 1, 0, 0, 7, 0,
                0xC2, 5, 0, 9, 0,
                1, 1, 0, 0,
                1, 1, 0, 0,
            ]
        )
        self.assertEqual(
            list(iter_view_frames(payload, packed_loop_orientation=True)),
            [(0, 0, 12), (0, 1, 16)],
        )

    @unittest.skipUnless(
        (ROOT / "games" / "XMAS.230").exists()
        and (ROOT / "games" / "XMAS").exists(),
        "local XMAS 2.230 and 2.272 game directories are not present",
    )
    def test_xmas_2230_moves_mirroring_state_from_cels_to_loop_header(self) -> None:
        early = read_resource_payload(ROOT / "games" / "XMAS.230", "view", 10)
        later = read_resource_payload(ROOT / "games" / "XMAS", "view", 10)
        early_loop = int.from_bytes(early[5:7], "little")
        later_loop = int.from_bytes(later[5:7], "little")

        self.assertEqual(early_loop, later_loop)
        self.assertEqual(
            decode_view_loop_header(
                early[early_loop],
                packed_orientation=True,
            ).cel_count,
            later[later_loop],
        )
        self.assertEqual(early[early_loop], 0xC4)
        self.assertEqual(later[later_loop], 0x04)
        for cel_no in range(4):
            early_cel = early_loop + int.from_bytes(
                early[early_loop + 1 + cel_no * 2 : early_loop + 3 + cel_no * 2],
                "little",
            )
            later_cel = later_loop + int.from_bytes(
                later[later_loop + 1 + cel_no * 2 : later_loop + 3 + cel_no * 2],
                "little",
            )
            self.assertEqual(early[early_cel + 2], 0x01)
            self.assertEqual(later[later_cel + 2], 0x81)

    def test_view_header_reserved_bytes_are_stable_in_local_resources(self) -> None:
        headers = {payload[:2] for _view_no, payload in iter_valid_resources("VIEWDIR")}
        self.assertEqual(headers, {b"\x01\x01"})

    def test_all_view_payloads_parse_frame_offsets(self) -> None:
        parsed = 0
        for _view_no, payload in iter_valid_resources("VIEWDIR"):
            for _group_no, _frame_no, frame_offset in iter_view_frames(payload):
                self.assertLess(frame_offset + 3, len(payload))
                parsed += 1
        self.assertEqual(parsed, 2066)

    def test_all_view_rows_stay_within_declared_width(self) -> None:
        row_count = 0
        for view_no, payload in iter_valid_resources("VIEWDIR"):
            for group_no, frame_no, frame_offset in iter_view_frames(payload):
                width = payload[frame_offset]
                height = payload[frame_offset + 1]
                pos = frame_offset + 3
                for y in range(height):
                    x = 0
                    while pos < len(payload):
                        value = payload[pos]
                        pos += 1
                        if value == 0:
                            break
                        x += value & 0x0F
                    self.assertLessEqual(
                        x,
                        width,
                        (view_no, group_no, frame_no, y, x, width),
                    )
                    row_count += 1
        self.assertEqual(row_count, 50640)

    def test_view_frame_dimension_bounds(self) -> None:
        max_width = 0
        max_height = 0
        for _view_no, payload in iter_valid_resources("VIEWDIR"):
            for _group_no, _frame_no, frame_offset in iter_view_frames(payload):
                max_width = max(max_width, payload[frame_offset])
                max_height = max(max_height, payload[frame_offset + 1])
        self.assertEqual((max_width, max_height), (88, 129))

    def test_view_11_sample_frame_renders_deterministically(self) -> None:
        rendered = render_view_frame(11, 0, 0)
        self.assertEqual((rendered.width, rendered.height, rendered.control), (20, 5, 0x01))
        self.assertEqual(len(rendered.pixels), 100)
        self.assertEqual(
            digest(rendered.pixels),
            "62921ee301cb11e11966ae9f8664607c9a861ab0f81b83800f2f0a0ef1224154",
        )

    def test_bit_80_frame_sample_renders_deterministically(self) -> None:
        rendered = render_view_frame(0, 0, 0)
        self.assertEqual((rendered.width, rendered.height, rendered.control), (7, 33, 0x81))
        self.assertEqual(len(rendered.pixels), 231)
        self.assertEqual(
            digest(rendered.pixels),
            "486ad21d27047cbd5135fff07c782577f5aeda5ee5f9c8703353fe90c10ad6ad",
        )

    def test_bit_80_frame_rewrites_to_selected_group_orientation(self) -> None:
        group_0 = render_view_frame(0, 0, 0)
        group_1 = render_view_frame(0, 1, 0)
        self.assertEqual((group_1.width, group_1.height, group_1.control), (7, 33, 0x91))
        for y in range(group_0.height):
            for x in range(group_0.width):
                self.assertEqual(
                    group_1.pixels[y * group_1.width + x],
                    group_0.pixels[y * group_0.width + (group_0.width - 1 - x)],
                )

    def test_mirror_view_row_collapses_all_transparent_row(self) -> None:
        self.assertEqual(_mirror_view_row_runs([0x13, 0x12], width=20, transparent=1), [])

    def test_mirror_view_row_emits_implicit_trailing_transparency(self) -> None:
        row = [0x13, 0x62]
        self.assertEqual(_mirror_view_row_runs(row, width=20, transparent=1), [0x1F, 0x62])

    def test_mirror_view_row_chunks_long_implicit_transparency(self) -> None:
        row = [0x13, 0x62]
        self.assertEqual(
            _mirror_view_row_runs(row, width=40, transparent=1),
            [0x1F, 0x1F, 0x15, 0x62],
        )

    def test_mirror_view_row_reverses_from_first_visible_run(self) -> None:
        row = [0x13, 0x62, 0x14, 0x71]
        self.assertEqual(
            _mirror_view_row_runs(row, width=20, transparent=1),
            [0x1A, 0x71, 0x14, 0x62],
        )

    def test_draw_frame_on_buffer_uses_baseline_and_transparency(self) -> None:
        cells = bytearray([DEFAULT_CELL] * (WIDTH * HEIGHT))
        frame = RenderedFrame(-1, 0, 0, 3, 2, 0x00, bytes([1, 0, 2, 0, 3, 3]))
        draw_frame_on_buffer(cells, frame, left=2, baseline_y=4, priority=5)
        self.assertEqual(cells[3 * WIDTH + 2], 0x51)
        self.assertEqual(cells[3 * WIDTH + 3], DEFAULT_CELL)
        self.assertEqual(cells[3 * WIDTH + 4], 0x52)
        self.assertEqual(cells[4 * WIDTH + 2], DEFAULT_CELL)
        self.assertEqual(cells[4 * WIDTH + 3], 0x53)
        self.assertEqual(cells[4 * WIDTH + 4], 0x53)

    def test_draw_frame_on_buffer_adjusts_negative_top_edge(self) -> None:
        cells = bytearray([DEFAULT_CELL] * (WIDTH * HEIGHT))
        equivalent = bytearray([DEFAULT_CELL] * (WIDTH * HEIGHT))
        frame = RenderedFrame(-1, 0, 0, 3, 3, 0x00, bytes([1, 1, 1] * 3))
        draw_frame_on_buffer(cells, frame, left=4, baseline_y=1, priority=5)
        draw_frame_on_buffer(equivalent, frame, left=3, baseline_y=2, priority=5)
        self.assertEqual(cells, equivalent)

    def test_draw_frame_on_buffer_clamps_right_edge_placement(self) -> None:
        cells = bytearray([DEFAULT_CELL] * (WIDTH * HEIGHT))
        equivalent = bytearray([DEFAULT_CELL] * (WIDTH * HEIGHT))
        frame = RenderedFrame(-1, 0, 0, 3, 1, 0x00, bytes([1, 1, 1]))
        draw_frame_on_buffer(cells, frame, left=159, baseline_y=4, priority=5)
        draw_frame_on_buffer(equivalent, frame, left=WIDTH - 3, baseline_y=4, priority=5)
        self.assertEqual(cells, equivalent)

    def test_search_object_placement_matches_source_spiral_edges(self) -> None:
        frame = render_view_frame(11, 0, 0)
        self.assertEqual(
            search_object_placement(20, 2, frame.width, frame.height),
            (18, 4),
        )
        self.assertEqual(
            search_object_placement(154, 80, frame.width, frame.height),
            (140, 67),
        )

    def test_search_object_placement_applies_horizon_when_not_exempt(self) -> None:
        frame = render_view_frame(11, 0, 0)
        self.assertEqual(
            search_object_placement(20, 80, frame.width, frame.height, horizon=100, horizon_exempt=False),
            (20, 101),
        )

    def test_search_object_placement_accept_hook_extends_spiral(self) -> None:
        rejected = {(20, 80), (19, 80), (19, 81), (20, 81)}
        self.assertEqual(
            search_object_placement(20, 80, 2, 2, accept=lambda left, y: (left, y) not in rejected),
            (21, 81),
        )

    def test_priority_value_to_sort_y_models_source_scan(self) -> None:
        self.assertEqual(priority_value_to_sort_y(0), -1)
        self.assertEqual(priority_value_to_sort_y(5), HEIGHT)
        self.assertEqual(priority_value_to_sort_y(5, after_table_value=0x0F), 47)
        self.assertEqual(priority_value_to_sort_y(15, after_table_value=0x0F), 167)

    def test_object_update_draw_order_uses_roots_and_stable_sort(self) -> None:
        candidates = [
            ObjectDrawCandidate(0, 100, 0x0051),
            ObjectDrawCandidate(1, 80, 0x0051),
            ObjectDrawCandidate(2, 90, 0x0041),
            ObjectDrawCandidate(3, 70, 0x0041),
            ObjectDrawCandidate(4, 70, 0x0041),
        ]
        self.assertEqual(
            [candidate.object_no for candidate in object_update_draw_order(candidates)],
            [3, 4, 2, 1, 0],
        )

    def test_2089_earlier_partition_retains_object_number_order(self) -> None:
        candidates = [
            ObjectDrawCandidate(0, 100, 0x0051),
            ObjectDrawCandidate(1, 80, 0x0051),
            ObjectDrawCandidate(2, 90, 0x0041),
            ObjectDrawCandidate(3, 70, 0x0041),
            ObjectDrawCandidate(4, 70, 0x0041),
        ]
        self.assertEqual(
            [
                candidate.object_no
                for candidate in object_update_draw_order(
                    candidates,
                    sort_earlier_partition=False,
                )
            ],
            [2, 3, 4, 1, 0],
        )

    def test_object_update_sort_key_uses_fixed_priority_mapping(self) -> None:
        fixed_zero = ObjectDrawCandidate(0, 100, 0x0055, 0)
        fixed_nonzero = ObjectDrawCandidate(1, 10, 0x0055, 5)
        ordinary = ObjectDrawCandidate(2, 90, 0x0051, 0)
        self.assertEqual(object_update_sort_key(fixed_zero), -1)
        self.assertEqual(object_update_sort_key(fixed_nonzero), HEIGHT)
        self.assertEqual(
            [candidate.object_no for candidate in object_update_draw_order([fixed_nonzero, ordinary, fixed_zero])],
            [0, 2, 1],
        )

    def test_dirty_rect_union_preserves_identical_footprints(self) -> None:
        self.assertEqual(
            dirty_rect_union(20, 80, 10, 5, 20, 80, 10, 5),
            DirtyRect(20, 80, 10, 5),
        )

    def test_dirty_rect_union_covers_old_and_current_footprints(self) -> None:
        self.assertEqual(
            dirty_rect_union(30, 90, 8, 6, 20, 80, 12, 4),
            DirtyRect(20, 90, 18, 14),
        )
        self.assertEqual(
            dirty_rect_union(20, 80, 12, 4, 30, 90, 8, 6),
            DirtyRect(20, 90, 18, 14),
        )

    def test_control_acceptance_scan_models_source_classes(self) -> None:
        self.assertEqual(
            control_acceptance_scan([0x00], object_flags=0, priority_byte=14),
            ControlAcceptance(False),
        )
        self.assertEqual(
            control_acceptance_scan([0x10], object_flags=0, priority_byte=14),
            ControlAcceptance(False),
        )
        self.assertEqual(
            control_acceptance_scan([0x10], object_flags=0x0002, priority_byte=14),
            ControlAcceptance(True),
        )
        self.assertEqual(
            control_acceptance_scan([0x20], object_flags=0x0100, priority_byte=14),
            ControlAcceptance(False),
        )
        self.assertEqual(
            control_acceptance_scan([0x30], object_flags=0x0800, priority_byte=14),
            ControlAcceptance(False),
        )
        self.assertEqual(
            control_acceptance_scan([0x00], object_flags=0, priority_byte=15),
            ControlAcceptance(True),
        )

    def test_control_acceptance_scan_uses_final_scanned_class_state(self) -> None:
        self.assertEqual(
            control_acceptance_scan([0x20, 0x30], object_flags=0x0100, priority_byte=14),
            ControlAcceptance(True),
        )
        self.assertEqual(
            control_acceptance_scan([0x30, 0x20], object_flags=0x0100, priority_byte=14),
            ControlAcceptance(False),
        )
        self.assertEqual(
            control_acceptance_scan([0x20, 0x30], object_flags=0, priority_byte=14, object_event_byte=0),
            ControlAcceptance(True, flag0_value=True, flag3_value=False),
        )
        self.assertEqual(
            control_acceptance_scan([0x30, 0x20], object_flags=0, priority_byte=14, object_event_byte=0),
            ControlAcceptance(True, flag0_value=False, flag3_value=True),
        )

    def test_control_acceptance_scan_other_nonzero_classes_use_false_false_state(self) -> None:
        self.assertEqual(
            control_acceptance_scan([0x40], object_flags=0, priority_byte=14, object_event_byte=0),
            ControlAcceptance(True, flag0_value=False, flag3_value=False),
        )
        self.assertEqual(
            control_acceptance_scan([0x40], object_flags=0x0100, priority_byte=14),
            ControlAcceptance(False),
        )
        self.assertEqual(
            control_acceptance_scan([0x40], object_flags=0x0800, priority_byte=14),
            ControlAcceptance(True),
        )

    def test_control_acceptance_priority_15_bypass_clears_event_flags(self) -> None:
        self.assertEqual(
            control_acceptance_scan([0x00], object_flags=0x0902, priority_byte=15, object_event_byte=0),
            ControlAcceptance(True, flag0_value=False, flag3_value=False),
        )

    def test_draw_frame_on_buffer_respects_existing_higher_priority(self) -> None:
        cells = bytearray([DEFAULT_CELL] * (WIDTH * HEIGHT))
        cells[2 * WIDTH + 2] = 0x6F
        frame = RenderedFrame(-1, 0, 0, 1, 1, 0x00, bytes([1]))
        draw_frame_on_buffer(cells, frame, left=2, baseline_y=2, priority=5)
        self.assertEqual(cells[2 * WIDTH + 2], 0x6F)

    def test_draw_frame_on_buffer_scans_down_from_low_control_cell(self) -> None:
        cells = bytearray([DEFAULT_CELL] * (WIDTH * HEIGHT))
        cells[2 * WIDTH + 2] = 0x2F
        cells[3 * WIDTH + 2] = 0x6F
        frame = RenderedFrame(-1, 0, 0, 1, 1, 0x00, bytes([1]))
        draw_frame_on_buffer(cells, frame, left=2, baseline_y=2, priority=5)
        self.assertEqual(cells[2 * WIDTH + 2], 0x2F)

    def test_draw_frame_on_buffer_accepts_equal_scanned_priority(self) -> None:
        cells = bytearray([DEFAULT_CELL] * (WIDTH * HEIGHT))
        cells[2 * WIDTH + 2] = 0x2F
        cells[3 * WIDTH + 2] = 0x5F
        frame = RenderedFrame(-1, 0, 0, 1, 1, 0x00, bytes([1]))
        draw_frame_on_buffer(cells, frame, left=2, baseline_y=2, priority=5)
        self.assertEqual(cells[2 * WIDTH + 2], 0x51)

    def test_draw_frame_on_buffer_low_control_without_scan_hit_allows_zero_priority(self) -> None:
        cells = bytearray([0x2F] * (WIDTH * HEIGHT))
        frame = RenderedFrame(-1, 0, 0, 1, 1, 0x00, bytes([1]))
        draw_frame_on_buffer(cells, frame, left=2, baseline_y=2, priority=0)
        self.assertEqual(cells[2 * WIDTH + 2], 0x01)

    def test_draw_frame_on_buffer_rejection_does_not_abort_run(self) -> None:
        cells = bytearray([DEFAULT_CELL] * (WIDTH * HEIGHT))
        cells[2 * WIDTH + 3] = 0x6F
        frame = RenderedFrame(-1, 0, 0, 3, 1, 0x00, bytes([1, 1, 1]))
        draw_frame_on_buffer(cells, frame, left=2, baseline_y=2, priority=5)
        self.assertEqual(cells[2 * WIDTH + 2], 0x51)
        self.assertEqual(cells[2 * WIDTH + 3], 0x6F)
        self.assertEqual(cells[2 * WIDTH + 4], 0x51)


class PpmHelperTests(unittest.TestCase):
    def test_picture_ppm_output_is_parseable(self) -> None:
        rendered = render_picture(1)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "picture_001_visual.ppm"
            picture_to_ppm(path, rendered)
            image = read_ppm(path)
        self.assertEqual((image.width, image.height, image.max_value), (WIDTH, HEIGHT, 255))
        self.assertEqual(len(image.rgb), WIDTH * HEIGHT * 3)
        self.assertGreater(len(unique_colors(image)), 1)
        self.assertIsNotNone(non_background_bbox(image))


if __name__ == "__main__":
    unittest.main()
