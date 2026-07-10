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
    GR_ACTION_51_MODE_STORE_CONTEXT_OFFSET,
    GR_ACTION_51_MODE_STORE_OFFSET,
    GR_KEY_MAP_SLOT_COUNT,
    GR_RESTORE_MARKER_FLAG,
    GR_RESTORE_SAVED_X,
    GR_RESTORE_UNRESTORED_X,
    GR_RESTORE_X_VAR,
    GR_RESTART_PROMPT_MESSAGE,
    GR_RESTART_PROMPT_ROW,
    GR_RESTART_TEST_PICTURE,
    GR_SAVE_SIGNATURE_MESSAGE,
    GR_SAVE_TEST_PICTURE,
    FRAME_GATE_EXACT4_VIEW,
    FRAME_GATE_FLAG,
    FRAME_GATE_MORE4_VIEW,
    FRAME_GATE_OBJECT,
    FRAME_GATE_TEST_PICTURE,
    KEY_MAP_TEST_KEY_WORD,
    KEY_MAP_TEST_PICTURE,
    KEY_MAP_TEST_STATUS,
    MOTION_MODE_TEST_BASELINE_Y,
    MOTION_MODE_TEST_PICTURE,
    MOTION_MODE_TEST_TARGET_X,
    MOTION_MODE_TEST_VIEW,
    ROOM_REMAP_ALIAS,
    ROOM_REMAP_ALIASES,
    ROOM_REMAP_DESTINATION,
    build_frame_selection_gate_fixtures,
    build_gr_save_extract_fixture,
    build_gr_signed_restore_comparison_fixtures,
    build_gr_signed_restore_fixture,
    build_gr_signed_restore_save_fixture,
    build_gr_restart_prompt_marker_fixtures,
    build_key_map_capacity_fixtures,
    build_motion_mode_4_fixtures,
    frame_selection_control_payload,
    frame_selection_gate_payload,
    gr_signed_restore_direct_payload,
    gr_signed_restore_restore_payload,
    gr_signed_restore_save_payload,
    gr_restart_prompt_marker_payload,
    gr_save_extract_payload,
    build_room_remap_fixtures,
    key_map_capacity_payload,
    motion_mode_dispatch_payload,
    patch_gr_action_51_to_seed_mode4,
    switch_room_payload,
)
from qemu_fixture import logic_resource, picture_logic_payload, v3_volume_record, xor_message_text  # noqa: E402


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
    agi = bytearray(b"\x90" * (GR_ACTION_51_MODE_STORE_OFFSET + 1))
    agi[
        GR_ACTION_51_MODE_STORE_CONTEXT_OFFSET : GR_ACTION_51_MODE_STORE_CONTEXT_OFFSET + 4
    ] = b"\xc6\x45\x22\x03"
    (source / "AGI").write_bytes(bytes(agi))
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

    def test_motion_mode_payload_builds_stationary_and_moving_logic(self) -> None:
        stationary = motion_mode_dispatch_payload(moving=False)
        moving = motion_mode_dispatch_payload(moving=True)
        stationary_code_len = stationary[0] | (stationary[1] << 8)
        moving_code_len = moving[0] | (moving[1] << 8)
        stationary_code = stationary[2 : 2 + stationary_code_len]
        moving_code = moving[2 : 2 + moving_code_len]

        self.assertIn(bytes([0x18, 0xFA, 0x19, 0xFA, 0x1A]), stationary_code)
        self.assertIn(bytes([0x1E, MOTION_MODE_TEST_VIEW]), moving_code)
        self.assertNotIn(bytes([0x51, 0, MOTION_MODE_TEST_TARGET_X]), stationary_code)
        self.assertIn(
            bytes([0x51, 0, MOTION_MODE_TEST_TARGET_X, MOTION_MODE_TEST_BASELINE_Y]),
            moving_code,
        )

    def test_motion_mode_4_patch_changes_only_copied_action_51_mode_byte(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir)
            agi = bytearray(b"\x90" * (GR_ACTION_51_MODE_STORE_OFFSET + 1))
            agi[
                GR_ACTION_51_MODE_STORE_CONTEXT_OFFSET : GR_ACTION_51_MODE_STORE_CONTEXT_OFFSET + 4
            ] = b"\xc6\x45\x22\x03"
            (fixture / "AGI").write_bytes(bytes(agi))

            patch_gr_action_51_to_seed_mode4(fixture)

            patched = (fixture / "AGI").read_bytes()
            self.assertEqual(patched[GR_ACTION_51_MODE_STORE_OFFSET], 0x04)
            self.assertEqual(
                patched[GR_ACTION_51_MODE_STORE_CONTEXT_OFFSET : GR_ACTION_51_MODE_STORE_CONTEXT_OFFSET + 3],
                b"\xc6\x45\x22",
            )

    def test_motion_mode_4_patch_rejects_unexpected_interpreter_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir)
            (fixture / "AGI").write_bytes(b"\x90" * (GR_ACTION_51_MODE_STORE_OFFSET + 1))

            with self.assertRaisesRegex(ValueError, "unexpected GR action 0x51"):
                patch_gr_action_51_to_seed_mode4(fixture)

    def test_motion_mode_4_fixtures_patch_only_instrumented_case(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_v3_source_game(root)

            cases = build_motion_mode_4_fixtures(source, root / "fixtures", picture_no=MOTION_MODE_TEST_PICTURE)

            self.assertEqual(
                [case.label for case in cases],
                ["stationary_control", "mode3_move_object_to", "mode4_instrumented_move_object_to"],
            )
            self.assertEqual((cases[1].fixture / "AGI").read_bytes()[GR_ACTION_51_MODE_STORE_OFFSET], 0x03)
            self.assertEqual((cases[2].fixture / "AGI").read_bytes()[GR_ACTION_51_MODE_STORE_OFFSET], 0x04)
            stationary = read_volume_record(cases[0].fixture, "logic", 0)
            moving = read_volume_record(cases[1].fixture, "logic", 0)
            self.assertEqual(stationary.payload, motion_mode_dispatch_payload(picture_no=MOTION_MODE_TEST_PICTURE, moving=False))
            self.assertEqual(moving.payload, motion_mode_dispatch_payload(picture_no=MOTION_MODE_TEST_PICTURE, moving=True))

    def test_frame_selection_gate_payload_sets_direction_tick_and_optional_flag(self) -> None:
        clear_payload = frame_selection_gate_payload(
            view_no=FRAME_GATE_MORE4_VIEW,
            initial_group=0,
            set_gate_flag=False,
        )
        set_payload = frame_selection_gate_payload(
            view_no=FRAME_GATE_MORE4_VIEW,
            initial_group=0,
            set_gate_flag=True,
        )
        clear_code_len = clear_payload[0] | (clear_payload[1] << 8)
        set_code_len = set_payload[0] | (set_payload[1] << 8)
        clear_code = clear_payload[2 : 2 + clear_code_len]
        set_code = set_payload[2 : 2 + set_code_len]

        self.assertIn(bytes([0x1E, FRAME_GATE_MORE4_VIEW]), clear_code)
        self.assertIn(bytes([0x56, FRAME_GATE_OBJECT]), clear_code)
        self.assertIn(bytes([0x50, FRAME_GATE_OBJECT]), clear_code)
        self.assertIn(bytes([0x2E, FRAME_GATE_OBJECT]), clear_code)
        self.assertNotIn(bytes([0x0C, FRAME_GATE_FLAG]), clear_code)
        self.assertIn(bytes([0x0C, FRAME_GATE_FLAG]), set_code)

    def test_frame_selection_controls_have_no_direction_setup(self) -> None:
        payload = frame_selection_control_payload(
            view_no=FRAME_GATE_EXACT4_VIEW,
            group_no=1,
        )
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]

        self.assertIn(bytes([0x1E, FRAME_GATE_EXACT4_VIEW]), code)
        self.assertIn(bytes([0x2B, FRAME_GATE_OBJECT, 1]), code)
        self.assertNotIn(bytes([0x56, FRAME_GATE_OBJECT]), code)
        self.assertNotIn(bytes([0x2E, FRAME_GATE_OBJECT]), code)

    def test_frame_selection_gate_fixtures_build_expected_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_v3_source_game(root)

            cases = build_frame_selection_gate_fixtures(
                source,
                root / "fixtures",
                picture_no=FRAME_GATE_TEST_PICTURE,
            )

            self.assertEqual(
                [case.label for case in cases],
                [
                    "exact4_group0_control",
                    "exact4_group1_control",
                    "exact4_flag_clear",
                    "exact4_flag_set",
                    "more4_group0_control",
                    "more4_group1_control",
                    "more4_flag_clear",
                    "more4_flag_set",
                ],
            )
            self.assertEqual(
                read_volume_record(cases[1].fixture, "logic", 0).payload,
                frame_selection_control_payload(
                    picture_no=FRAME_GATE_TEST_PICTURE,
                    view_no=FRAME_GATE_EXACT4_VIEW,
                    group_no=1,
                ),
            )
            self.assertEqual(
                read_volume_record(cases[7].fixture, "logic", 0).payload,
                frame_selection_gate_payload(
                    picture_no=FRAME_GATE_TEST_PICTURE,
                    view_no=FRAME_GATE_MORE4_VIEW,
                    initial_group=0,
                    set_gate_flag=True,
                ),
            )

    def test_gr_save_extract_payload_uses_encrypted_signature_message(self) -> None:
        payload = gr_save_extract_payload(verify_signature=True)
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        message_data = payload[2 + code_len :]
        text_start = 1 + 4
        encrypted_text = message_data[text_start:]

        self.assertIn(bytes([0x8F, 0x01, 0x7D]), code)
        self.assertNotIn(GR_SAVE_SIGNATURE_MESSAGE.encode("ascii") + b"\x00", message_data)
        self.assertEqual(
            xor_message_text(encrypted_text),
            GR_SAVE_SIGNATURE_MESSAGE.encode("ascii") + b"\x00",
        )

    def test_gr_save_extract_payload_defaults_to_blank_prefix_save(self) -> None:
        payload = gr_save_extract_payload()
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        message_data = payload[2 + code_len :]

        self.assertIn(bytes([0x7D]), code)
        self.assertNotIn(bytes([0x8F, 0x01]), code)
        self.assertEqual(message_data, bytes([0x00, 0x02, 0x00]))

    def test_gr_save_extract_fixture_patches_logic_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_v3_source_game(root)
            (source / "GRSG.1").write_bytes(b"stale")

            case = build_gr_save_extract_fixture(
                source,
                root / "fixtures",
                picture_no=GR_SAVE_TEST_PICTURE,
            )

            self.assertEqual(case.label, "save_xor_extract")
            self.assertFalse((case.fixture / "GRSG.1").exists())
            self.assertEqual(
                read_volume_record(case.fixture, "logic", 0).payload,
                gr_save_extract_payload(picture_no=GR_SAVE_TEST_PICTURE),
            )

    def test_gr_signed_save_extract_fixture_patches_logic_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_v3_source_game(root)

            case = build_gr_save_extract_fixture(
                source,
                root / "fixtures",
                picture_no=GR_SAVE_TEST_PICTURE,
                verify_signature=True,
            )

            self.assertEqual(case.label, "save_xor_extract_signed")
            self.assertEqual(
                read_volume_record(case.fixture, "logic", 0).payload,
                gr_save_extract_payload(picture_no=GR_SAVE_TEST_PICTURE, verify_signature=True),
            )

    def test_gr_signed_restore_save_payload_sets_marker_state_before_save(self) -> None:
        payload = gr_signed_restore_save_payload()
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        message_data = payload[2 + code_len :]
        text_start = 1 + 4

        self.assertIn(bytes([0x8F, 0x01]), code)
        self.assertIn(bytes([0x0C, GR_RESTORE_MARKER_FLAG]), code)
        self.assertIn(bytes([0x03, GR_RESTORE_X_VAR, GR_RESTORE_SAVED_X]), code)
        self.assertIn(bytes([0x7D]), code)
        self.assertNotIn(GR_SAVE_SIGNATURE_MESSAGE.encode("ascii") + b"\x00", message_data)
        self.assertEqual(
            xor_message_text(message_data[text_start:]),
            GR_SAVE_SIGNATURE_MESSAGE.encode("ascii") + b"\x00",
        )

    def test_gr_signed_restore_restore_payload_branches_on_restored_flag(self) -> None:
        payload = gr_signed_restore_restore_payload()
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        message_data = payload[2 + code_len :]

        self.assertTrue(code.startswith(bytes([0xFF, 0x07, GR_RESTORE_MARKER_FLAG, 0xFF])))
        self.assertIn(bytes([0x8F, 0x01]), code)
        self.assertIn(bytes([0x03, GR_RESTORE_X_VAR, GR_RESTORE_UNRESTORED_X]), code)
        self.assertIn(bytes([0x7E]), code)
        self.assertNotIn(GR_SAVE_SIGNATURE_MESSAGE.encode("ascii") + b"\x00", message_data)

    def test_gr_signed_restore_fixtures_patch_logic_and_copy_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_v3_source_game(root)
            save_input = root / "GRSG.1"
            save_input.write_bytes(b"synthetic save bytes")

            save_case = build_gr_signed_restore_save_fixture(source, root / "fixtures")
            restore_case = build_gr_signed_restore_fixture(source, root / "fixtures", save_input)
            comparison_cases = build_gr_signed_restore_comparison_fixtures(source, root / "fixtures")

            self.assertEqual(save_case.label, "signed_restore_save")
            self.assertEqual(restore_case.label, "signed_restore_from_save")
            self.assertEqual(
                read_volume_record(save_case.fixture, "logic", 0).payload,
                gr_signed_restore_save_payload(),
            )
            self.assertEqual(
                read_volume_record(restore_case.fixture, "logic", 0).payload,
                gr_signed_restore_restore_payload(),
            )
            self.assertEqual((restore_case.fixture / "GRSG.1").read_bytes(), b"synthetic save bytes")
            self.assertEqual(
                read_volume_record(comparison_cases[0].fixture, "logic", 0).payload,
                gr_signed_restore_direct_payload(marker_x=GR_RESTORE_SAVED_X),
            )
            self.assertEqual(
                read_volume_record(comparison_cases[1].fixture, "logic", 0).payload,
                gr_signed_restore_direct_payload(marker_x=GR_RESTORE_UNRESTORED_X),
            )

    def test_gr_restart_prompt_marker_payload_visible_cancel_path(self) -> None:
        payload = gr_restart_prompt_marker_payload(
            marker_visible_before_restart=True,
            include_restart=True,
        )
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]
        message_data = payload[2 + code_len :]
        text_start = 1 + 4

        self.assertIn(bytes([0x6C, 0x01]), code)
        self.assertIn(bytes([0x6F, 0x00, GR_RESTART_PROMPT_ROW, 0x16]), code)
        self.assertIn(bytes([0x78, 0x80]), code)
        self.assertNotIn(bytes([0x77, 0x80]), code)
        self.assertEqual(
            xor_message_text(message_data[text_start:]),
            GR_RESTART_PROMPT_MESSAGE.encode("ascii") + b"\x00",
        )

    def test_gr_restart_prompt_marker_payload_hidden_control_path(self) -> None:
        payload = gr_restart_prompt_marker_payload(
            marker_visible_before_restart=False,
            include_restart=False,
        )
        code_len = payload[0] | (payload[1] << 8)
        code = payload[2 : 2 + code_len]

        self.assertIn(bytes([0x6F, 0x00, GR_RESTART_PROMPT_ROW, 0x16, 0x77]), code)
        self.assertNotIn(bytes([0x80]), code)

    def test_gr_restart_prompt_marker_fixtures_patch_controls_and_cancel_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_v3_source_game(root)

            cases = build_gr_restart_prompt_marker_fixtures(
                source,
                root / "fixtures",
                picture_no=GR_RESTART_TEST_PICTURE,
            )

            self.assertEqual(
                [case.label for case in cases],
                [
                    "restart_hidden_control",
                    "restart_visible_control",
                    "restart_cancel_hidden",
                    "restart_cancel_visible",
                ],
            )
            self.assertEqual(cases[0].post_launch_key_names, None)
            self.assertEqual(cases[2].post_launch_key_names, ["esc"])
            self.assertEqual(
                read_volume_record(cases[0].fixture, "logic", 0).payload,
                gr_restart_prompt_marker_payload(
                    marker_visible_before_restart=False,
                    include_restart=False,
                    picture_no=GR_RESTART_TEST_PICTURE,
                ),
            )
            self.assertEqual(
                read_volume_record(cases[3].fixture, "logic", 0).payload,
                gr_restart_prompt_marker_payload(
                    marker_visible_before_restart=True,
                    include_restart=True,
                    picture_no=GR_RESTART_TEST_PICTURE,
                ),
            )


if __name__ == "__main__":
    unittest.main()
