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
    DEFAULT_CELL,
    HEIGHT,
    PictureRenderer,
    RenderedFrame,
    WIDTH,
    draw_frame_on_buffer,
    iter_view_frames,
    iter_valid_resources,
    pattern_column_mask,
    pattern_row_words,
    picture_payload,
    picture_to_ppm,
    render_picture,
    render_view_frame,
)
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


class PictureRenderingTests(unittest.TestCase):
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
        self.assertEqual(
            [pattern_column_mask(column) for column in range(8)],
            [0x8000, 0x2000, 0x0800, 0x0200, 0x0080, 0x0020, 0x0008, 0x0002],
        )
        self.assertEqual(pattern_row_words(0), [0x8000])
        self.assertEqual(pattern_row_words(2), [0x7000, 0xF800, 0xF800, 0xF800, 0x7000])
        self.assertEqual(len(pattern_row_words(7)), 15)

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

    def test_absolute_line_uses_interpreter_step_pattern(self) -> None:
        payload = bytes([0xF0, 0x00, 0xF6, 0x00, 0x00, 0x03, 0x01, 0xFF])
        rendered = PictureRenderer(payload).render()
        self.assertEqual(changed_visual_pixels(rendered), {(0, 0), (1, 0), (2, 1), (3, 1)})

    def test_relative_line_decodes_packed_delta_and_uses_same_step_pattern(self) -> None:
        payload = bytes([0xF0, 0x00, 0xF7, 0x00, 0x00, 0x31, 0xFF])
        rendered = PictureRenderer(payload).render()
        self.assertEqual(changed_visual_pixels(rendered), {(0, 0), (1, 0), (2, 1), (3, 1)})

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


class ViewRenderingTests(unittest.TestCase):
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
