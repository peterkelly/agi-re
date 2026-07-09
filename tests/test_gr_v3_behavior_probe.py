#!/usr/bin/env python3
"""Tests for Gold Rush v3 targeted behavior probe fixtures."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_resources import read_volume_record  # noqa: E402
from gr_v3_behavior_probe import (  # noqa: E402
    GR_KEY_MAP_SLOT_COUNT,
    KEY_MAP_TEST_KEY_WORD,
    KEY_MAP_TEST_PICTURE,
    KEY_MAP_TEST_STATUS,
    ROOM_REMAP_ALIAS,
    ROOM_REMAP_ALIASES,
    ROOM_REMAP_DESTINATION,
    build_key_map_capacity_fixtures,
    build_room_remap_fixtures,
    key_map_capacity_payload,
    switch_room_payload,
)
from qemu_fixture import logic_resource, picture_logic_payload, v3_volume_record  # noqa: E402


def v3_entry(volume: int, offset: int) -> bytes:
    return bytes([(volume << 4) | ((offset >> 16) & 0x0F), (offset >> 8) & 0xFF, offset & 0xFF])


def make_v3_source_game(root: Path) -> Path:
    source = root / "source-gr"
    source.mkdir()
    logic0 = v3_volume_record(logic_resource(b"\x00"), volume=1)
    logic73_offset = len(logic0)
    logic73 = v3_volume_record(logic_resource(b"\x00"), volume=1)
    logic_slots = 74
    logic_start = 8
    picture_start = logic_start + logic_slots * 3
    view_start = picture_start + 3
    sound_start = view_start + 3
    directory = bytearray()
    directory.extend(bytes([logic_start, 0, picture_start & 0xFF, picture_start >> 8]))
    directory.extend(bytes([view_start & 0xFF, view_start >> 8, sound_start & 0xFF, sound_start >> 8]))
    for logic_no in range(logic_slots):
        if logic_no == 0:
            directory.extend(v3_entry(1, 0))
        elif logic_no == ROOM_REMAP_DESTINATION:
            directory.extend(v3_entry(1, logic73_offset))
        else:
            directory.extend(b"\xff\xff\xff")
    directory.extend(b"\xff\xff\xff" * 3)
    (source / "GRDIR").write_bytes(bytes(directory))
    (source / "GRVOL.1").write_bytes(logic0 + logic73)
    (source / "SIERRA.COM").write_bytes(b"launcher")
    return source


class GoldRushV3BehaviorProbeTests(unittest.TestCase):
    def test_switch_room_payload_uses_guarded_immediate_switch_opcode(self) -> None:
        payload = switch_room_payload(ROOM_REMAP_ALIAS)
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        self.assertTrue(code.startswith(bytes([0xFF, 0x01, 0xFA, 0x00, 0xFF, 0x05, 0x00])))
        self.assertIn(bytes([0x03, 0xFA, 0x01, 0x12, ROOM_REMAP_ALIAS]), code)
        self.assertTrue(code.endswith(bytes([0x17, 0x00, 0x00])))

    def test_room_remap_fixtures_patch_logic_zero_and_destination_room(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_v3_source_game(root)

            cases = build_room_remap_fixtures(source, root / "fixtures", picture_no=1)

            self.assertEqual([case.label for case in cases], ["direct_49", "alias_7e", "alias_7f", "alias_80"])
            direct = read_volume_record(cases[0].fixture, "logic", 0)
            self.assertEqual(direct.payload, switch_room_payload(ROOM_REMAP_DESTINATION))
            for case, alias in zip(cases[1:], ROOM_REMAP_ALIASES, strict=True):
                aliased = read_volume_record(case.fixture, "logic", 0)
                self.assertEqual(aliased.payload, switch_room_payload(alias))
            for case in cases:
                destination = read_volume_record(case.fixture, "logic", ROOM_REMAP_DESTINATION)
                self.assertEqual(destination.payload, picture_logic_payload(1))

    def test_key_map_capacity_payload_puts_target_mapping_in_last_gr_slot(self) -> None:
        payload = key_map_capacity_payload()
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]

        self.assertEqual(code.count(bytes([0x79])), GR_KEY_MAP_SLOT_COUNT)
        self.assertIn(bytes([0x79, KEY_MAP_TEST_KEY_WORD, 0x00, KEY_MAP_TEST_STATUS]), code)
        last_target = code.rfind(bytes([0x79, KEY_MAP_TEST_KEY_WORD, 0x00, KEY_MAP_TEST_STATUS]))
        self.assertGreater(last_target, 0)
        self.assertEqual(code[:last_target].count(bytes([0x79])), GR_KEY_MAP_SLOT_COUNT - 1)

    def test_key_map_capacity_fixtures_patch_direct_and_slot_48_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_v3_source_game(root)

            cases = build_key_map_capacity_fixtures(source, root / "fixtures", picture_no=KEY_MAP_TEST_PICTURE)

            self.assertEqual([case.label for case in cases], ["direct_picture", "slot_48_key_map", "slot_48_no_key"])
            direct = read_volume_record(cases[0].fixture, "logic", 0)
            self.assertEqual(direct.payload, picture_logic_payload(KEY_MAP_TEST_PICTURE))
            for case in cases[1:]:
                slot_48 = read_volume_record(case.fixture, "logic", 0)
                self.assertEqual(slot_48.payload, key_map_capacity_payload(picture_no=KEY_MAP_TEST_PICTURE))
            self.assertEqual(cases[1].post_launch_keys, "x")
            self.assertEqual(cases[2].post_launch_keys, "")


if __name__ == "__main__":
    unittest.main()
