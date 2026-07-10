#!/usr/bin/env python3
"""Tests for clean-room save-game file parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_save import (  # noqa: E402
    GR_V3_OBJECT_INVENTORY_XOR_KEY,
    GR_V3_BLOCK1_LENGTH,
    GR_V3_BLOCK1_REGIONS,
    GR_V3_BLOCK2_LENGTH,
    GR_V3_BLOCK3_LENGTH,
    GR_V3_BLOCK4_LENGTH,
    GR_V3_BLOCK5_INITIAL_LENGTH,
    GR_V3_INVENTORY_ITEM_COUNT,
    GR_V3_INVENTORY_ITEM_TABLE_SIZE,
    GR_V3_OBJECT_RECORD_COUNT,
    GR_V3_REPLAY_PAIR_COUNT,
    KQ4D_V3_BLOCK1_LENGTH,
    KQ4D_V3_BLOCK1_REGIONS,
    KQ4D_V3_BLOCK2_LENGTH,
    KQ4D_V3_BLOCK3_LENGTH,
    KQ4D_V3_BLOCK4_LENGTH,
    KQ4D_V3_INVENTORY_ITEM_COUNT,
    KQ4D_V3_OBJECT_RECORD_COUNT,
    KQ1_2917_BLOCK1_LENGTH,
    KQ1_2917_BLOCK1_REGIONS,
    KQ1_2917_BLOCK2_LENGTH,
    KQ1_2917_BLOCK3_LENGTH,
    KQ1_2917_BLOCK4_LENGTH,
    KQ1_2917_INVENTORY_ITEM_COUNT,
    KQ1_2917_OBJECT_RECORD_COUNT,
    SAVE_HEADER_LENGTH,
    SQ2_BLOCK1_LENGTH,
    SQ2_BLOCK1_REGIONS,
    SQ2_BLOCK2_LENGTH,
    SQ2_BLOCK3_LENGTH,
    SQ2_BLOCK4_LENGTH,
    SQ2_INVENTORY_ITEM_COUNT,
    SQ2_INVENTORY_ITEM_TABLE_SIZE,
    SQ2_OBJECT_FILE_XOR_KEY,
    SQ2_OBJECT_RECORD_COUNT,
    SQ2_OBJECT_RECORD_FIELDS,
    SQ2_OBJECT_RECORD_SIZE,
    SQ2_REPLAY_PAIR_COUNT,
    SaveBlock,
    SaveGame,
    SavePathValidationPlan,
    SOURCE_BACKED_FIXED_BLOCK_LENGTHS,
    decode_gr_v3_object_file,
    decode_kq4d_v3_object_file,
    decode_kq1_2917_object_file,
    gr_v3_object_inventory_save_xor,
    decode_sq2_object_file,
    load_save,
    parse_save,
    save_path_validation_plan,
    serialize_save,
    split_sq2_block1,
    split_sq2_block2,
    split_sq2_block3,
    split_sq2_block4,
    split_sq2_block5,
    split_gr_v3_block2,
    split_gr_v3_block3,
    split_gr_v3_block4,
    split_gr_v3_block1,
    split_kq4d_v3_block1,
    split_kq4d_v3_block2,
    split_kq4d_v3_block3,
    split_kq4d_v3_block4,
    split_kq1_2917_block1,
    split_kq1_2917_block2,
    split_kq1_2917_block3,
    split_kq1_2917_block4,
    validate_state_regions,
    xor_with_repeating_key,
)
from disassemble_logic import SQ2  # noqa: E402

GR = ROOT / "games" / "GR"
KQ4D = ROOT / "games" / "KQ4D"
KQ1 = ROOT / "games" / "KQ1"
GR_SAVE = ROOT / "build" / "gr-v3-behavior" / "GRSG_001.1"


def sq2_save_paths() -> list[Path]:
    return sorted(
        SQ2.glob("SQ2SG.*"),
        key=lambda path: int(path.suffix[1:]) if path.suffix[1:].isdigit() else 999,
    )


class SaveResourceTests(unittest.TestCase):
    @unittest.skipUnless(KQ1.exists(), "local KQ1 game directory is not present")
    def test_kq1_2917_object_metadata_defines_save_dimensions(self) -> None:
        metadata = decode_kq1_2917_object_file((KQ1 / "OBJECT").read_bytes())

        self.assertEqual(KQ1_2917_BLOCK1_REGIONS, SQ2_BLOCK1_REGIONS)
        self.assertEqual(KQ1_2917_BLOCK1_LENGTH, SQ2_BLOCK1_LENGTH)
        self.assertEqual(len(split_kq1_2917_block1(bytes(KQ1_2917_BLOCK1_LENGTH))), len(SQ2_BLOCK1_REGIONS))
        self.assertEqual(metadata.object_record_count, KQ1_2917_OBJECT_RECORD_COUNT)
        self.assertEqual(len(split_kq1_2917_block2(bytes(KQ1_2917_BLOCK2_LENGTH))), 18)
        self.assertEqual(len(metadata.runtime_block), KQ1_2917_BLOCK3_LENGTH)
        inventory = split_kq1_2917_block3(metadata.runtime_block)
        self.assertEqual(len(inventory.items), KQ1_2917_INVENTORY_ITEM_COUNT)
        self.assertEqual(inventory.items[0].name, "?")
        self.assertEqual(inventory.items[1].name, "dagger")
        self.assertEqual(len(split_kq1_2917_block4(bytes(KQ1_2917_BLOCK4_LENGTH))), 100)

    def test_sq2_block1_map_covers_every_byte_once(self) -> None:
        validate_state_regions(SQ2_BLOCK1_REGIONS, SQ2_BLOCK1_LENGTH)
        self.assertEqual(SQ2_BLOCK1_REGIONS[0].offset, 0)
        self.assertEqual(SQ2_BLOCK1_REGIONS[-1].end, SQ2_BLOCK1_LENGTH)
        self.assertEqual(len({region.name for region in SQ2_BLOCK1_REGIONS}), len(SQ2_BLOCK1_REGIONS))

    def test_sq2_block1_map_extracts_portable_core_state(self) -> None:
        save = load_save(SQ2 / "SQ2SG.2")
        regions = split_sq2_block1(save.blocks[0].data)
        self.assertEqual(regions["signature"][:4], b"SQ2\0")
        self.assertEqual(len(regions["variables"]), 256)
        self.assertEqual(len(regions["flags"]), 32)
        self.assertEqual(len(regions["key_map"]), 39 * 4)
        self.assertEqual(len(regions["string_slots"]), 12 * 40)

    def test_sq2_block1_reserved_ranges_are_explicit(self) -> None:
        reserved = [region for region in SQ2_BLOCK1_REGIONS if region.name.startswith("reserved_")]
        self.assertEqual(
            [(region.offset, region.size) for region in reserved],
            [
                (0x012D, 2),
                (0x013D, 2),
                (0x01DF, 0x28),
                (0x0207, 4),
                (0x03EB, 0x1E0),
                (0x05D6, 1),
            ],
        )
        self.assertTrue(all(region.known for region in reserved))

    def test_sq2_block1_split_rejects_other_lengths(self) -> None:
        with self.assertRaisesRegex(ValueError, "block length"):
            split_sq2_block1(bytes(SQ2_BLOCK1_LENGTH - 1))

    def test_sq2_block1_reserved_bytes_have_canonical_observed_values(self) -> None:
        expected = {
            "reserved_012d": b"\0\0",
            "reserved_013d": b"\x0f\0",
            "reserved_key_map_tail": bytes(0x28),
            "reserved_pre_string_padding": bytes(4),
            "reserved_string_bank": bytes(0x1E0),
            "reserved_text_padding": b"\0",
        }
        for path in sq2_save_paths():
            with self.subTest(save=path.name):
                regions = split_sq2_block1(load_save(path).blocks[0].data)
                self.assertEqual(
                    {name: regions[name] for name in expected},
                    expected,
                )

    def test_sq2_block2_is_twenty_one_complete_object_records(self) -> None:
        self.assertEqual(
            SQ2_BLOCK2_LENGTH,
            SQ2_OBJECT_RECORD_COUNT * SQ2_OBJECT_RECORD_SIZE,
        )
        validate_state_regions(SQ2_OBJECT_RECORD_FIELDS, SQ2_OBJECT_RECORD_SIZE)
        records = split_sq2_block2(load_save(SQ2 / "SQ2SG.2").blocks[1].data)
        self.assertEqual(len(records), SQ2_OBJECT_RECORD_COUNT)
        self.assertEqual(records[0]["left_x"], b"N\0")
        self.assertEqual(records[0]["baseline_y"], b"\x8c\0")
        self.assertEqual(records[0]["view_number"], b"\x0a")

    def test_sq2_block2_split_rejects_other_lengths(self) -> None:
        with self.assertRaisesRegex(ValueError, "block length"):
            split_sq2_block2(bytes(SQ2_BLOCK2_LENGTH + 1))

    def test_sq2_saves_use_object_index_as_event_identifier(self) -> None:
        for path in sq2_save_paths():
            with self.subTest(save=path.name):
                records = split_sq2_block2(load_save(path).blocks[1].data)
                self.assertEqual(
                    [record["event_identifier"][0] for record in records],
                    list(range(SQ2_OBJECT_RECORD_COUNT)),
                )

    def test_sq2_block4_is_one_hundred_replay_pairs(self) -> None:
        pairs = split_sq2_block4(load_save(SQ2 / "SQ2SG.2").blocks[3].data)
        self.assertEqual(len(pairs), SQ2_REPLAY_PAIR_COUNT)
        self.assertEqual(pairs[:4], ((0, 13), (1, 0), (3, 23), (1, 17)))

    def test_sq2_block4_split_rejects_other_lengths(self) -> None:
        with self.assertRaisesRegex(ValueError, "block length"):
            split_sq2_block4(bytes(SQ2_BLOCK4_LENGTH - 1))

    def test_sq2_object_file_header_defines_blocks_two_and_three(self) -> None:
        item_table_size, maximum_object_index, runtime_block = decode_sq2_object_file(
            (SQ2 / "OBJECT").read_bytes()
        )
        self.assertEqual(SQ2_OBJECT_FILE_XOR_KEY, b"Avis Durgan")
        self.assertEqual(item_table_size, SQ2_INVENTORY_ITEM_TABLE_SIZE)
        self.assertEqual(maximum_object_index + 1, SQ2_OBJECT_RECORD_COUNT)
        self.assertEqual(len(runtime_block), SQ2_BLOCK3_LENGTH)
        self.assertEqual(
            SQ2_BLOCK2_LENGTH,
            (maximum_object_index + 1) * SQ2_OBJECT_RECORD_SIZE,
        )

    def test_sq2_block3_maps_item_entries_and_name_pool(self) -> None:
        state = split_sq2_block3(load_save(SQ2 / "SQ2SG.2").blocks[2].data)
        self.assertEqual(state.item_table_size, SQ2_INVENTORY_ITEM_TABLE_SIZE)
        self.assertEqual(len(state.items), SQ2_INVENTORY_ITEM_COUNT)
        self.assertEqual(len(state.name_pool), SQ2_BLOCK3_LENGTH - SQ2_INVENTORY_ITEM_TABLE_SIZE)
        self.assertEqual(state.items[0].name, "?")
        self.assertEqual(state.items[20].name, "Order Form")
        self.assertEqual(state.items[39].name, "Oxygen Mask")
        self.assertEqual(state.items[21].location, 0xFF)

    def test_sq2_block3_static_metadata_matches_object_file(self) -> None:
        _, _, initial = decode_sq2_object_file((SQ2 / "OBJECT").read_bytes())
        initial_state = split_sq2_block3(initial)
        for path in sq2_save_paths():
            with self.subTest(save=path.name):
                saved_state = split_sq2_block3(load_save(path).blocks[2].data)
                self.assertEqual(saved_state.name_pool, initial_state.name_pool)
                self.assertEqual(
                    [(item.name_offset, item.name_bytes) for item in saved_state.items],
                    [(item.name_offset, item.name_bytes) for item in initial_state.items],
                )

    def test_sq2_block3_rejects_invalid_name_offset(self) -> None:
        data = bytearray(load_save(SQ2 / "SQ2SG.2").blocks[2].data)
        data[0:2] = (SQ2_INVENTORY_ITEM_TABLE_SIZE - 1).to_bytes(2, "little")
        with self.assertRaisesRegex(ValueError, "invalid name offset"):
            split_sq2_block3(bytes(data))

    def test_sq2_block5_maps_logic_resume_records(self) -> None:
        expected_logic_numbers = {
            "SQ2SG.1": [0, 0, 16, 102, 106],
            "SQ2SG.2": [0, 0, 13, 102, 107, 108],
            "SQ2SG.3": [0, 0, 19, 102, 106],
            "SQ2SG.4": [0, 0, 23, 102],
            "SQ2SG.5": [0, 0, 44, 106],
            "SQ2SG.6": [0, 0, 46, 102],
            "SQ2SG.7": [0, 0, 49, 102, 124],
            "SQ2SG.8": [0, 0, 86, 102, 124],
            "SQ2SG.9": [0, 0, 53, 102, 123, 124],
            "SQ2SG.10": [0, 0, 92],
            "SQ2SG.11": [0, 0, 86, 102, 124],
        }
        for path in sq2_save_paths():
            with self.subTest(save=path.name):
                state = split_sq2_block5(load_save(path).blocks[4].data)
                self.assertEqual(
                    [entry.logic_number for entry in state.entries],
                    expected_logic_numbers[path.name],
                )
                self.assertEqual([entry.resume_offset for entry in state.entries], [0] * len(state.entries))
                self.assertEqual(state.terminator_payload, 0)

    def test_sq2_block5_lookup_uses_first_match_and_relative_offset(self) -> None:
        data = bytes.fromhex(
            "00000500"
            "00000900"
            "07003412"
            "ffffcdab"
        )
        state = split_sq2_block5(data)
        self.assertEqual(state.resume_offset_for(0), 5)
        self.assertEqual(state.resume_offset_for(7), 0x1234)
        self.assertIsNone(state.resume_offset_for(8))
        self.assertEqual(state.terminator_payload, 0xABCD)

    def test_sq2_block5_rejects_malformed_framing(self) -> None:
        with self.assertRaisesRegex(ValueError, "multiple of four"):
            split_sq2_block5(b"\xff\xff")
        with self.assertRaisesRegex(ValueError, "no terminator"):
            split_sq2_block5(bytes.fromhex("01000000"))
        with self.assertRaisesRegex(ValueError, "after its terminator"):
            split_sq2_block5(bytes.fromhex("ffff000001000000"))
        with self.assertRaisesRegex(ValueError, "byte-sized"):
            split_sq2_block5(bytes.fromhex("00010000ffff0000"))

    def test_sq2_save_files_match_source_backed_block_envelope(self) -> None:
        paths = sq2_save_paths()
        self.assertEqual(len(paths), 11)
        for path in paths:
            with self.subTest(save=path.name):
                save = load_save(path)
                self.assertEqual(len(save.header), SAVE_HEADER_LENGTH)
                self.assertEqual(len(save.blocks), 5)
                self.assertEqual(
                    tuple(block.length for block in save.blocks[:4]),
                    SOURCE_BACKED_FIXED_BLOCK_LENGTHS,
                )
                self.assertGreater(save.blocks[4].length, 0)
                self.assertEqual(save.blocks[0].data_offset, SAVE_HEADER_LENGTH + 2)
                expected_size = SAVE_HEADER_LENGTH + sum(2 + block.length for block in save.blocks)
                self.assertEqual(path.stat().st_size, expected_size)

    def test_sq2_save_files_serialize_byte_for_byte(self) -> None:
        paths = sq2_save_paths()
        self.assertEqual(len(paths), 11)
        for path in paths:
            with self.subTest(save=path.name):
                self.assertEqual(serialize_save(load_save(path)), path.read_bytes())

    def test_save_description_is_header_prefix(self) -> None:
        save = load_save(SQ2 / "SQ2SG.2")
        self.assertEqual(save.description, "before entering lake")
        self.assertEqual(save.description_bytes, b"before entering lake")

    def test_truncated_block_is_rejected(self) -> None:
        data = bytearray(b"description\0".ljust(SAVE_HEADER_LENGTH, b"\0"))
        data.extend((4).to_bytes(2, "little"))
        data.extend(b"xy")
        with self.assertRaisesRegex(ValueError, "block 0 is truncated"):
            parse_save(bytes(data))

    def test_trailing_bytes_are_rejected(self) -> None:
        data = bytearray(b"description\0".ljust(SAVE_HEADER_LENGTH, b"\0"))
        for _ in range(5):
            data.extend((0).to_bytes(2, "little"))
        data.extend(b"x")
        with self.assertRaisesRegex(ValueError, "trailing bytes"):
            parse_save(bytes(data))

    def test_serializer_rejects_structural_mismatches(self) -> None:
        header = b"description\0".ljust(SAVE_HEADER_LENGTH, b"\0")
        blocks = tuple(SaveBlock(i, 0, 0, 0, b"") for i in range(5))

        with self.assertRaisesRegex(ValueError, "31 bytes"):
            serialize_save(SaveGame(None, header[:-1], blocks))

        with self.assertRaisesRegex(ValueError, "exactly 5"):
            serialize_save(SaveGame(None, header, blocks[:4]))

        mismatched_length = (
            SaveBlock(0, 0, 0, 1, b""),
            *blocks[1:],
        )
        with self.assertRaisesRegex(ValueError, "does not match"):
            serialize_save(SaveGame(None, header, mismatched_length))

        mismatched_index = (
            blocks[0],
            SaveBlock(99, 0, 0, 0, b""),
            *blocks[2:],
        )
        with self.assertRaisesRegex(ValueError, "mismatched index"):
            serialize_save(SaveGame(None, header, mismatched_index))

    def test_save_path_validation_plan_models_source_string_edges(self) -> None:
        self.assertEqual(
            save_path_validation_plan("   C:\\SQ2\\", current_drive_letter="d"),
            SavePathValidationPlan("C:\\SQ2", "find_directory", "c", False, True),
        )
        self.assertEqual(
            save_path_validation_plan("", current_directory="\\SQ2", current_drive_letter="c"),
            SavePathValidationPlan("\\SQ2", "find_directory", "c", True, False),
        )
        self.assertEqual(
            save_path_validation_plan("", current_directory="\\", current_drive_letter="c"),
            SavePathValidationPlan("\\", "single_separator_accept", "c", True, False),
        )
        self.assertEqual(
            save_path_validation_plan("/", current_drive_letter="e"),
            SavePathValidationPlan("/", "single_separator_accept", "e", False, False),
        )
        self.assertEqual(
            save_path_validation_plan("A:\\", current_drive_letter="c"),
            SavePathValidationPlan("A:", "drive_available", "a", False, True),
        )

    def test_gr_v3_object_inventory_xor_round_trips(self) -> None:
        plain = bytes(range(128))
        encoded = gr_v3_object_inventory_save_xor(plain)

        self.assertNotEqual(encoded, plain)
        self.assertEqual(gr_v3_object_inventory_save_xor(encoded), plain)

    def test_gr_v3_object_inventory_xor_uses_data_segment_key(self) -> None:
        self.assertEqual(GR_V3_OBJECT_INVENTORY_XOR_KEY, b"Avis Durgan")
        plain = bytes(range(13))
        encoded = gr_v3_object_inventory_save_xor(plain)

        self.assertEqual(encoded[0], plain[0] ^ GR_V3_OBJECT_INVENTORY_XOR_KEY[0])
        self.assertEqual(encoded[10], plain[10] ^ GR_V3_OBJECT_INVENTORY_XOR_KEY[10])
        self.assertEqual(encoded[11], plain[11] ^ GR_V3_OBJECT_INVENTORY_XOR_KEY[0])

    def test_gr_v3_object_inventory_xor_matches_original_save_prefix(self) -> None:
        decoded = bytes.fromhex("8901008b011c")
        encoded = gr_v3_object_inventory_save_xor(decoded)
        self.assertEqual(encoded, bytes.fromhex("c87769f82158"))

    def test_gr_v3_block1_map_covers_every_byte_once(self) -> None:
        validate_state_regions(GR_V3_BLOCK1_REGIONS, GR_V3_BLOCK1_LENGTH)
        self.assertEqual(GR_V3_BLOCK1_REGIONS[0].offset, 0)
        self.assertEqual(GR_V3_BLOCK1_REGIONS[-1].end, GR_V3_BLOCK1_LENGTH)
        self.assertEqual(len({region.name for region in GR_V3_BLOCK1_REGIONS}), len(GR_V3_BLOCK1_REGIONS))

    def test_kq4d_v3_block1_extends_the_2936_shape_with_v3_gates(self) -> None:
        validate_state_regions(KQ4D_V3_BLOCK1_REGIONS, KQ4D_V3_BLOCK1_LENGTH)
        self.assertEqual(KQ4D_V3_BLOCK1_REGIONS[:-2], SQ2_BLOCK1_REGIONS)
        self.assertEqual(
            [(region.offset, region.size, region.name) for region in KQ4D_V3_BLOCK1_REGIONS[-2:]],
            [
                (0x05E1, 2, "menu_interaction_gate"),
                (0x05E3, 1, "key_release_enqueue_gate"),
            ],
        )
        regions = split_kq4d_v3_block1(bytes(KQ4D_V3_BLOCK1_LENGTH))
        self.assertEqual(regions["menu_interaction_gate"], b"\0\0")
        self.assertEqual(regions["key_release_enqueue_gate"], b"\0")

    @unittest.skipUnless(KQ4D.exists(), "local KQ4D game directory is not present")
    def test_kq4d_v3_intended_decoded_object_metadata_defines_save_dimensions(self) -> None:
        decoded_local = (KQ4D / "OBJECT").read_bytes()
        encoded_valid_input = xor_with_repeating_key(decoded_local, SQ2_OBJECT_FILE_XOR_KEY)
        metadata = decode_kq4d_v3_object_file(encoded_valid_input)

        self.assertEqual(metadata.item_table_size, 3)
        self.assertEqual(metadata.object_record_count, KQ4D_V3_OBJECT_RECORD_COUNT)
        self.assertEqual(len(metadata.runtime_block), KQ4D_V3_BLOCK3_LENGTH)
        self.assertEqual(len(split_kq4d_v3_block2(bytes(KQ4D_V3_BLOCK2_LENGTH))), 16)

        stored_block3 = gr_v3_object_inventory_save_xor(metadata.runtime_block)
        inventory = split_kq4d_v3_block3(stored_block3)
        self.assertEqual(len(inventory.items), KQ4D_V3_INVENTORY_ITEM_COUNT)
        self.assertEqual(inventory.items[0].name, "?")
        self.assertEqual(split_kq4d_v3_block4(bytes(KQ4D_V3_BLOCK4_LENGTH)), ((0, 0),))

    @unittest.skipUnless(GR_SAVE.exists(), "local Gold Rush generated save is not present")
    def test_gr_v3_block1_split_extracts_portable_core_state(self) -> None:
        regions = split_gr_v3_block1(load_save(GR_SAVE).blocks[0].data)

        self.assertEqual(regions["signature"][:3], b"GR\0")
        self.assertEqual(len(regions["variables"]), 256)
        self.assertEqual(len(regions["flags"]), 32)
        self.assertEqual(len(regions["key_map"]), 49 * 4)
        self.assertEqual(len(regions["string_slots"]), 12 * 40)
        self.assertEqual(regions["replay_capacity"], b"\x32\0")
        self.assertEqual(regions["input_row"], b"\x17\0")
        self.assertEqual(regions["status_row"], b"\x15\0")
        self.assertEqual(regions["menu_interaction_gate"], b"\x01\0")
        self.assertEqual(regions["key_release_enqueue_gate"], b"\0")

    @unittest.skipUnless(GR_SAVE.exists(), "local Gold Rush generated save is not present")
    def test_gr_v3_block1_reserved_ranges_have_canonical_values(self) -> None:
        regions = split_gr_v3_block1(load_save(GR_SAVE).blocks[0].data)

        self.assertEqual(regions["reserved_012d"], b"\0\0")
        self.assertEqual(regions["reserved_013d"], b"\x0f\0")
        self.assertEqual(regions["reserved_pre_string_padding"], b"\0\0\0\0")
        self.assertEqual(regions["reserved_text_padding"], b"\0")
        self.assertTrue(all(region.known for region in GR_V3_BLOCK1_REGIONS))

    @unittest.skipUnless(GR.exists(), "local Gold Rush game directory is not present")
    def test_gr_v3_object_file_defines_blocks_two_and_three(self) -> None:
        metadata = decode_gr_v3_object_file((GR / "OBJECT").read_bytes())

        self.assertEqual(metadata.item_table_size, GR_V3_INVENTORY_ITEM_TABLE_SIZE)
        self.assertEqual(len(metadata.runtime_block), GR_V3_BLOCK3_LENGTH)
        self.assertEqual(metadata.object_record_count, GR_V3_OBJECT_RECORD_COUNT)

        inventory = split_gr_v3_block3(gr_v3_object_inventory_save_xor(metadata.runtime_block))
        self.assertEqual(len(inventory.items), GR_V3_INVENTORY_ITEM_COUNT)
        self.assertEqual(len(inventory.name_pool), GR_V3_BLOCK3_LENGTH - GR_V3_INVENTORY_ITEM_TABLE_SIZE)

    @unittest.skipUnless(GR_SAVE.exists(), "local Gold Rush generated save is not present")
    def test_gr_v3_generated_save_blocks_have_mapped_dimensions(self) -> None:
        save = load_save(GR_SAVE)
        self.assertEqual(
            [block.length for block in save.blocks],
            [
                GR_V3_BLOCK1_LENGTH,
                GR_V3_BLOCK2_LENGTH,
                GR_V3_BLOCK3_LENGTH,
                GR_V3_BLOCK4_LENGTH,
                GR_V3_BLOCK5_INITIAL_LENGTH,
            ],
        )
        self.assertEqual(save.blocks[0].data[:8], b"GR\0\0\0\0\0\0")

        object_records = split_gr_v3_block2(save.blocks[1].data)
        self.assertEqual(len(object_records), GR_V3_OBJECT_RECORD_COUNT)
        self.assertEqual(
            [record["event_identifier"][0] for record in object_records],
            list(range(GR_V3_OBJECT_RECORD_COUNT)),
        )

        metadata = decode_gr_v3_object_file((GR / "OBJECT").read_bytes())
        decoded_block3 = gr_v3_object_inventory_save_xor(save.blocks[2].data)
        self.assertEqual(decoded_block3, metadata.runtime_block)
        inventory = split_gr_v3_block3(save.blocks[2].data)
        self.assertEqual(len(inventory.items), GR_V3_INVENTORY_ITEM_COUNT)

        pairs = split_gr_v3_block4(save.blocks[3].data)
        self.assertEqual(len(pairs), GR_V3_REPLAY_PAIR_COUNT)
        self.assertEqual(split_sq2_block5(save.blocks[4].data).terminator_payload, 0)

    def test_xor_with_repeating_key_rejects_empty_key(self) -> None:
        with self.assertRaises(ValueError):
            xor_with_repeating_key(b"data", b"")


if __name__ == "__main__":
    unittest.main()
