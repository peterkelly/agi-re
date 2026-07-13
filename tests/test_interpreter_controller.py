#!/usr/bin/env python3
"""Tests for the persistent interpreter-controller state and image helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from interpreter_controller import (  # noqa: E402
    ControllerError,
    SQ122_PROFILE,
    classify_blocking_stack,
    colorize_logical_buffer,
    detect_modal_borders,
    evaluate_predicate,
    find_runtime_image_base,
    parse_object_records,
    parse_ppm,
    qcode_for_character,
    unpack_flags,
)


class FakeMemoryGdb:
    def __init__(self, memory: bytes):
        self.memory = memory

    def read_memory(self, address: int, size: int, chunk_size: int = 0x1000) -> bytes:
        return self.memory[address : address + size]


class InterpreterControllerTests(unittest.TestCase):
    def test_unpack_flags_uses_high_bit_first(self) -> None:
        flags = unpack_flags(bytes([0xA1]))
        self.assertEqual(flags, [True, False, True, False, False, False, False, True])

    def test_parse_object_records_exposes_semantic_fields(self) -> None:
        record = bytearray(43)
        record[3:5] = (126).to_bytes(2, "little")
        record[5:7] = (108).to_bytes(2, "little")
        record[7] = 9
        record[0x0A] = 2
        record[0x0E] = 6
        record[0x1A:0x1C] = (14).to_bytes(2, "little")
        record[0x1C:0x1E] = (20).to_bytes(2, "little")
        record[0x21] = 7
        record[0x22] = 3
        record[0x25:0x27] = (0x1234).to_bytes(2, "little")
        parsed = parse_object_records(bytes(record), 0x42F3)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["x"], 126)
        self.assertEqual(parsed[0]["y"], 108)
        self.assertEqual(parsed[0]["view"], 9)
        self.assertEqual(parsed[0]["direction"], 7)
        self.assertEqual(parsed[0]["motion_mode"], 3)
        self.assertEqual(parsed[0]["flags"], 0x1234)

    def test_parse_object_records_rejects_partial_record(self) -> None:
        with self.assertRaises(ControllerError):
            parse_object_records(bytes(42), 0)

    def test_parse_object_records_rejects_unimplemented_layout(self) -> None:
        with self.assertRaisesRegex(ControllerError, "no object-record decoder"):
            parse_object_records(bytes(44), 0, record_size=44)

    def test_colorize_priority_uses_high_nibble(self) -> None:
        ppm = colorize_logical_buffer(bytes([0x4E]), "priority", width=1, height=1)
        width, height, pixels = parse_ppm(ppm)
        self.assertEqual((width, height), (1, 1))
        self.assertEqual(pixels, bytes((0xAA, 0x00, 0x00)))

    def test_colorize_visual_uses_low_nibble(self) -> None:
        ppm = colorize_logical_buffer(bytes([0x4E]), "visual", width=1, height=1)
        _, _, pixels = parse_ppm(ppm)
        self.assertEqual(pixels, bytes((0xFF, 0xFF, 0x55)))

    def test_modal_detector_finds_red_box_with_white_interior(self) -> None:
        width, height = 120, 80
        pixels = bytearray((0, 0, 0) * width * height)

        def set_pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
            offset = (y * width + x) * 3
            pixels[offset : offset + 3] = bytes(color)

        for y in range(20, 61):
            for x in range(15, 106):
                set_pixel(x, y, (255, 255, 255))
        for x in range(15, 106):
            set_pixel(x, 20, (168, 0, 0))
            set_pixel(x, 60, (168, 0, 0))
        for y in range(20, 61):
            set_pixel(15, y, (168, 0, 0))
            set_pixel(105, y, (168, 0, 0))
        ppm = f"P6\n{width} {height}\n255\n".encode() + bytes(pixels)
        self.assertEqual(
            detect_modal_borders(ppm),
            [{"left": 15, "top": 20, "right": 105, "bottom": 60}],
        )

    def test_modal_detector_rejects_plain_screen(self) -> None:
        ppm = b"P6\n40 30\n255\n" + bytes((0, 0, 0) * 40 * 30)
        self.assertEqual(detect_modal_borders(ppm), [])

    def test_nested_predicate(self) -> None:
        state = {"room": 1, "objects": [{"x": 126, "y": 108}], "flags": [False, True]}
        predicate = {
            "all": [
                {"path": "room", "op": "eq", "value": 1},
                {"path": "objects.0.x", "op": "between", "value": [98, 130]},
                {"path": "flags.1", "op": "truthy"},
            ]
        }
        self.assertTrue(evaluate_predicate(state, predicate))

    def test_keyboard_character_mapping(self) -> None:
        self.assertEqual(qcode_for_character("a"), ("a", False))
        self.assertEqual(qcode_for_character("A"), ("a", True))
        self.assertEqual(qcode_for_character(":"), ("semicolon", True))
        self.assertEqual(qcode_for_character("\n"), ("ret", False))

    def test_blocking_stack_classifies_shared_string_editor(self) -> None:
        stack = b"\x00\x00" * 4 + (0x0DF8).to_bytes(2, "little") + b"\x00\x00"
        self.assertEqual(classify_blocking_stack(stack, SQ122_PROFILE), "string_prompt_wait")

    def test_blocking_stack_classifies_modal_message_wait(self) -> None:
        stack = b"\x00\x00" * 3 + (0x1D25).to_bytes(2, "little")
        self.assertEqual(classify_blocking_stack(stack, SQ122_PROFILE), "modal_wait")

    def test_sq122_profile_uses_verified_cycle_and_ui_hooks(self) -> None:
        self.assertEqual(SQ122_PROFILE.cycle_boundary, 0x015B)
        self.assertEqual(SQ122_PROFILE.string_prompt_wait, 0x0DF2)
        self.assertEqual(SQ122_PROFILE.string_prompt_wait_return, 0x0DF8)
        self.assertEqual(SQ122_PROFILE.modal_wait, 0x1D1B)
        self.assertEqual(SQ122_PROFILE.modal_wait_return, 0x1D25)

    def test_runtime_image_discovery_uses_cycle_signature(self) -> None:
        image = bytearray(0x4000)
        image[0x150 : 0x170] = bytes(range(32))
        memory = bytearray(0xA0000)
        base = 0x23000
        memory[base : base + len(image)] = image
        discovered = find_runtime_image_base(FakeMemoryGdb(bytes(memory)), bytes(image), SQ122_PROFILE)
        self.assertEqual(discovered, base)


if __name__ == "__main__":
    unittest.main()
