#!/usr/bin/env python3
"""Clean-room helpers for SQ2 save-game files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SAVE_HEADER_LENGTH = 0x1F
SAVE_BLOCK_COUNT = 5
SOURCE_BACKED_FIXED_BLOCK_LENGTHS = (0x05E1, 0x0387, 0x0148, 0x00C8)
SAVE_PATH_SEPARATORS = "\\/"
GR_V3_OBJECT_INVENTORY_XOR_KEY = b"Avis Durgan"
SQ2_OBJECT_FILE_XOR_KEY = b"Avis Durgan"


@dataclass(frozen=True)
class SavePathValidationPlan:
    effective_path: str
    check_kind: str
    drive_letter: str
    used_default_directory: bool
    stripped_trailing_separator: bool


@dataclass(frozen=True)
class SaveBlock:
    index: int
    length_prefix_offset: int
    data_offset: int
    length: int
    data: bytes


@dataclass(frozen=True)
class SaveGame:
    path: Path | None
    header: bytes
    blocks: tuple[SaveBlock, ...]

    @property
    def description_bytes(self) -> bytes:
        return self.header.split(b"\0", 1)[0]

    @property
    def description(self) -> str:
        return self.description_bytes.decode("ascii", errors="replace")


@dataclass(frozen=True)
class SaveStateRegion:
    offset: int
    size: int
    name: str
    known: bool
    description: str

    @property
    def end(self) -> int:
        return self.offset + self.size


@dataclass(frozen=True)
class SaveInventoryItem:
    index: int
    name_offset: int
    location: int
    name_bytes: bytes

    @property
    def name(self) -> str:
        return self.name_bytes.decode("ascii", errors="replace")


@dataclass(frozen=True)
class SaveInventoryState:
    item_table_size: int
    items: tuple[SaveInventoryItem, ...]
    name_pool: bytes


@dataclass(frozen=True)
class ObjectMetadata:
    item_table_size: int
    maximum_object_index: int
    runtime_block: bytes

    @property
    def object_record_count(self) -> int:
        return self.maximum_object_index + 1


@dataclass(frozen=True)
class SaveLogicResumeEntry:
    logic_number: int
    resume_offset: int


@dataclass(frozen=True)
class SaveLogicResumeState:
    entries: tuple[SaveLogicResumeEntry, ...]
    terminator_payload: int

    def resume_offset_for(self, logic_number: int) -> int | None:
        for entry in self.entries:
            if entry.logic_number == logic_number:
                return entry.resume_offset
        return None


SQ2_BLOCK1_LENGTH = 0x05E1
SQ2_BLOCK1_REGIONS = (
    SaveStateRegion(0x0000, 0x0007, "signature", True, "Seven-byte game/save signature area."),
    SaveStateRegion(0x0007, 0x0100, "variables", True, "Variables v0 through v255."),
    SaveStateRegion(0x0107, 0x0020, "flags", True, "Packed flags f0 through f255."),
    SaveStateRegion(0x0127, 0x0004, "timer_ticks", True, "Little-endian 32-bit timer tick counter."),
    SaveStateRegion(0x012B, 0x0002, "horizon", True, "Object horizon baseline."),
    SaveStateRegion(0x012D, 0x0002, "reserved_012d", True, "Reserved word; canonically zero and preserved on interchange."),
    SaveStateRegion(0x012F, 0x0002, "motion_rect_left", True, "Configured movement rectangle left bound."),
    SaveStateRegion(0x0131, 0x0002, "motion_rect_top", True, "Configured movement rectangle top bound."),
    SaveStateRegion(0x0133, 0x0002, "motion_rect_right", True, "Configured movement rectangle right bound."),
    SaveStateRegion(0x0135, 0x0002, "motion_rect_bottom", True, "Configured movement rectangle bottom bound."),
    SaveStateRegion(0x0137, 0x0002, "direction_coupling", True, "Object-0/v6 direction coupling selector."),
    SaveStateRegion(0x0139, 0x0002, "prepared_picture", True, "Most recently prepared picture number."),
    SaveStateRegion(0x013B, 0x0002, "motion_rect_enabled", True, "Configured movement rectangle enable word."),
    SaveStateRegion(0x013D, 0x0002, "reserved_013d", True, "Reserved word; canonical value 0x000f and preserved on interchange."),
    SaveStateRegion(0x013F, 0x0002, "replay_capacity", True, "Resource replay capacity in pairs."),
    SaveStateRegion(0x0141, 0x0002, "replay_count", True, "Active resource replay pair count."),
    SaveStateRegion(0x0143, 0x009C, "key_map", True, "Thirty-nine four-byte raw-key/status mappings."),
    SaveStateRegion(0x01DF, 0x0028, "reserved_key_map_tail", True, "Ten inactive four-byte key-map records outside the profile capacity."),
    SaveStateRegion(0x0207, 0x0004, "reserved_pre_string_padding", True, "Reserved bytes before the string slots."),
    SaveStateRegion(0x020B, 0x01E0, "string_slots", True, "Twelve 40-byte script string slots."),
    SaveStateRegion(0x03EB, 0x01E0, "reserved_string_bank", True, "Twelve reserved 40-byte records outside the valid string-slot range."),
    SaveStateRegion(0x05CB, 0x0002, "text_foreground", True, "Derived foreground text attribute."),
    SaveStateRegion(0x05CD, 0x0002, "text_background", True, "Derived background text attribute."),
    SaveStateRegion(0x05CF, 0x0002, "text_attribute", True, "Packed current text/window attribute."),
    SaveStateRegion(0x05D1, 0x0002, "input_line_enabled", True, "Input-line enabled word."),
    SaveStateRegion(0x05D3, 0x0002, "input_row", True, "Configured input text row."),
    SaveStateRegion(0x05D5, 0x0001, "prompt_marker", True, "Input prompt marker byte."),
    SaveStateRegion(0x05D6, 0x0001, "reserved_text_padding", True, "Reserved byte aligning the following word state."),
    SaveStateRegion(0x05D7, 0x0002, "status_line_enabled", True, "Status-line enabled word."),
    SaveStateRegion(0x05D9, 0x0002, "status_row", True, "Configured status text row."),
    SaveStateRegion(0x05DB, 0x0002, "display_base_row", True, "Configured display base row."),
    SaveStateRegion(0x05DD, 0x0002, "display_bottom_row", True, "Display base row plus 21."),
    SaveStateRegion(0x05DF, 0x0002, "saved_replay_count", True, "Replay rollback checkpoint count."),
)

SQ2_BLOCK2_LENGTH = 0x0387
SQ2_OBJECT_RECORD_SIZE = 0x2B
SQ2_OBJECT_RECORD_COUNT = 21
SQ2_OBJECT_RECORD_FIELDS = (
    SaveStateRegion(0x00, 0x01, "cadence_interval", True, "Movement cadence reload value."),
    SaveStateRegion(0x01, 0x01, "cadence_countdown", True, "Movement cadence countdown."),
    SaveStateRegion(0x02, 0x01, "event_identifier", True, "Boundary and collision event identifier."),
    SaveStateRegion(0x03, 0x02, "left_x", True, "Current left X coordinate."),
    SaveStateRegion(0x05, 0x02, "baseline_y", True, "Current baseline Y coordinate."),
    SaveStateRegion(0x07, 0x01, "view_number", True, "Selected view resource number."),
    SaveStateRegion(0x08, 0x02, "view_reference", True, "Serialized view payload reference."),
    SaveStateRegion(0x0A, 0x01, "loop_number", True, "Selected loop number."),
    SaveStateRegion(0x0B, 0x01, "loop_count", True, "Selected view loop count."),
    SaveStateRegion(0x0C, 0x02, "loop_reference", True, "Serialized selected-loop reference."),
    SaveStateRegion(0x0E, 0x01, "cel_number", True, "Selected cel number."),
    SaveStateRegion(0x0F, 0x01, "cel_count", True, "Selected loop cel count."),
    SaveStateRegion(0x10, 0x02, "cel_reference", True, "Serialized selected-cel reference."),
    SaveStateRegion(0x12, 0x02, "saved_cel_reference", True, "Serialized previous-cel reference."),
    SaveStateRegion(0x14, 0x02, "render_node_reference", True, "Serialized render-list node reference."),
    SaveStateRegion(0x16, 0x02, "previous_left_x", True, "Previous or saved left X coordinate."),
    SaveStateRegion(0x18, 0x02, "previous_baseline_y", True, "Previous or saved baseline Y coordinate."),
    SaveStateRegion(0x1A, 0x02, "width", True, "Selected cel width."),
    SaveStateRegion(0x1C, 0x02, "height", True, "Selected cel height."),
    SaveStateRegion(0x1E, 0x01, "step_size", True, "Movement step size."),
    SaveStateRegion(0x1F, 0x01, "cel_interval", True, "Cel-cycling interval reload value."),
    SaveStateRegion(0x20, 0x01, "cel_countdown", True, "Cel-cycling countdown."),
    SaveStateRegion(0x21, 0x01, "direction", True, "Current movement direction."),
    SaveStateRegion(0x22, 0x01, "motion_mode", True, "Autonomous motion mode."),
    SaveStateRegion(0x23, 0x01, "cycling_mode", True, "Cel-cycling mode."),
    SaveStateRegion(0x24, 0x01, "priority_control", True, "Priority/control byte."),
    SaveStateRegion(0x25, 0x02, "flags", True, "Object state flags."),
    SaveStateRegion(0x27, 0x04, "motion_parameters", True, "Mode-dependent motion parameters."),
)

SQ2_BLOCK4_LENGTH = 0x00C8
SQ2_REPLAY_PAIR_COUNT = 100
SQ2_REPLAY_PAIR_SIZE = 2
SQ2_BLOCK3_LENGTH = 0x0148
SQ2_INVENTORY_ITEM_COUNT = 40
SQ2_INVENTORY_ITEM_SIZE = 3
SQ2_INVENTORY_ITEM_TABLE_SIZE = 0x78
EARLY_24XX_BLOCK1_LENGTH = 0x05DF
EARLY_24XX_BLOCK1_REGIONS = SQ2_BLOCK1_REGIONS[:-1]
KQ2_2411_OBJECT_RECORD_COUNT = 17
KQ2_2411_BLOCK2_LENGTH = KQ2_2411_OBJECT_RECORD_COUNT * SQ2_OBJECT_RECORD_SIZE
KQ2_2411_INVENTORY_ITEM_COUNT = 85
KQ2_2411_INVENTORY_ITEM_TABLE_SIZE = 0x00FF
KQ2_2411_BLOCK3_LENGTH = 0x0256
KQ2_2411_REPLAY_PAIR_COUNT = 60
KQ2_2411_BLOCK4_LENGTH = KQ2_2411_REPLAY_PAIR_COUNT * SQ2_REPLAY_PAIR_SIZE
LSL1_2440_OBJECT_RECORD_COUNT = 17
LSL1_2440_BLOCK2_LENGTH = LSL1_2440_OBJECT_RECORD_COUNT * SQ2_OBJECT_RECORD_SIZE
LSL1_2440_INVENTORY_ITEM_COUNT = 21
LSL1_2440_INVENTORY_ITEM_TABLE_SIZE = 0x003F
LSL1_2440_BLOCK3_LENGTH = 0x0134
LSL1_2440_REPLAY_PAIR_COUNT = 144
LSL1_2440_BLOCK4_LENGTH = LSL1_2440_REPLAY_PAIR_COUNT * SQ2_REPLAY_PAIR_SIZE
KQ1_2917_BLOCK1_LENGTH = SQ2_BLOCK1_LENGTH
KQ1_2917_BLOCK1_REGIONS = SQ2_BLOCK1_REGIONS
KQ1_2917_OBJECT_RECORD_COUNT = 18
KQ1_2917_BLOCK2_LENGTH = KQ1_2917_OBJECT_RECORD_COUNT * SQ2_OBJECT_RECORD_SIZE
KQ1_2917_INVENTORY_ITEM_COUNT = 27
KQ1_2917_INVENTORY_ITEM_TABLE_SIZE = 0x51
KQ1_2917_BLOCK3_LENGTH = SQ2_BLOCK3_LENGTH
KQ1_2917_REPLAY_PAIR_COUNT = 100
KQ1_2917_BLOCK4_LENGTH = KQ1_2917_REPLAY_PAIR_COUNT * SQ2_REPLAY_PAIR_SIZE
PQ1_2917_OBJECT_RECORD_COUNT = 20
PQ1_2917_BLOCK2_LENGTH = PQ1_2917_OBJECT_RECORD_COUNT * SQ2_OBJECT_RECORD_SIZE
PQ1_2917_INVENTORY_ITEM_COUNT = 25
PQ1_2917_INVENTORY_ITEM_TABLE_SIZE = 0x4B
PQ1_2917_BLOCK3_LENGTH = 0x016E
PQ1_2917_REPLAY_PAIR_COUNT = 250
PQ1_2917_BLOCK4_LENGTH = PQ1_2917_REPLAY_PAIR_COUNT * SQ2_REPLAY_PAIR_SIZE
KQ3_2936_OBJECT_RECORD_COUNT = 17
KQ3_2936_BLOCK2_LENGTH = KQ3_2936_OBJECT_RECORD_COUNT * SQ2_OBJECT_RECORD_SIZE
KQ3_2936_INVENTORY_ITEM_COUNT = 55
KQ3_2936_INVENTORY_ITEM_TABLE_SIZE = 0xA5
KQ3_2936_BLOCK3_LENGTH = 0x0307
KQ3_2936_REPLAY_PAIR_COUNT = 127
KQ3_2936_BLOCK4_LENGTH = KQ3_2936_REPLAY_PAIR_COUNT * SQ2_REPLAY_PAIR_SIZE
KQ4_3002086_BLOCK1_LENGTH = SQ2_BLOCK1_LENGTH
KQ4_3002086_BLOCK1_REGIONS = SQ2_BLOCK1_REGIONS
KQ4_3002086_OBJECT_RECORD_COUNT = 26
KQ4_3002086_BLOCK2_LENGTH = KQ4_3002086_OBJECT_RECORD_COUNT * SQ2_OBJECT_RECORD_SIZE
KQ4_3002086_INVENTORY_ITEM_COUNT = 45
KQ4_3002086_INVENTORY_ITEM_TABLE_SIZE = 0x87
KQ4_3002086_BLOCK3_LENGTH = 0x02C6
KQ4_3002086_REPLAY_PAIR_COUNT = 250
KQ4_3002086_BLOCK4_LENGTH = KQ4_3002086_REPLAY_PAIR_COUNT * SQ2_REPLAY_PAIR_SIZE
GR_V3_BLOCK1_LENGTH = 0x0404
GR_V3_BLOCK2_LENGTH = 0x03DD
GR_V3_BLOCK3_LENGTH = 0x0713
GR_V3_BLOCK4_LENGTH = 0x0064
GR_V3_BLOCK5_INITIAL_LENGTH = 0x000C
GR_V3_OBJECT_RECORD_COUNT = 23
GR_V3_INVENTORY_ITEM_COUNT = 131
GR_V3_INVENTORY_ITEM_TABLE_SIZE = 0x0189
GR_V3_REPLAY_PAIR_COUNT = 50
KQ4D_V3_BLOCK1_LENGTH = SQ2_BLOCK1_LENGTH + 3
KQ4D_V3_OBJECT_RECORD_COUNT = 16
KQ4D_V3_BLOCK2_LENGTH = KQ4D_V3_OBJECT_RECORD_COUNT * SQ2_OBJECT_RECORD_SIZE
KQ4D_V3_INVENTORY_ITEM_COUNT = 1
KQ4D_V3_INVENTORY_ITEM_TABLE_SIZE = 3
KQ4D_V3_BLOCK3_LENGTH = 5
KQ4D_V3_REPLAY_PAIR_COUNT = 1
KQ4D_V3_BLOCK4_LENGTH = KQ4D_V3_REPLAY_PAIR_COUNT * SQ2_REPLAY_PAIR_SIZE
KQ4D_V3_BLOCK1_REGIONS = SQ2_BLOCK1_REGIONS + (
    SaveStateRegion(0x05E1, 0x0002, "menu_interaction_gate", True, "V3 menu interaction gate word."),
    SaveStateRegion(0x05E3, 0x0001, "key_release_enqueue_gate", True, "V3 key-release enqueue gate byte."),
)
GR_V3_BLOCK1_REGIONS = (
    SaveStateRegion(0x0000, 0x0007, "signature", True, "Seven-byte game/save signature area."),
    SaveStateRegion(0x0007, 0x0100, "variables", True, "Variables v0 through v255."),
    SaveStateRegion(0x0107, 0x0020, "flags", True, "Packed flags f0 through f255."),
    SaveStateRegion(0x0127, 0x0004, "timer_ticks", True, "Little-endian 32-bit timer tick counter."),
    SaveStateRegion(0x012B, 0x0002, "horizon", True, "Object horizon baseline."),
    SaveStateRegion(0x012D, 0x0002, "reserved_012d", True, "Reserved word; canonically zero and preserved on interchange."),
    SaveStateRegion(0x012F, 0x0002, "motion_rect_left", True, "Configured movement rectangle left bound."),
    SaveStateRegion(0x0131, 0x0002, "motion_rect_top", True, "Configured movement rectangle top bound."),
    SaveStateRegion(0x0133, 0x0002, "motion_rect_right", True, "Configured movement rectangle right bound."),
    SaveStateRegion(0x0135, 0x0002, "motion_rect_bottom", True, "Configured movement rectangle bottom bound."),
    SaveStateRegion(0x0137, 0x0002, "direction_coupling", True, "Object-0/v6 direction coupling selector."),
    SaveStateRegion(0x0139, 0x0002, "prepared_picture", True, "Most recently prepared picture number."),
    SaveStateRegion(0x013B, 0x0002, "motion_rect_enabled", True, "Configured movement rectangle enable word."),
    SaveStateRegion(0x013D, 0x0002, "reserved_013d", True, "Reserved word; canonical value 0x000f and preserved on interchange."),
    SaveStateRegion(0x013F, 0x0002, "replay_capacity", True, "Replay-pair capacity."),
    SaveStateRegion(0x0141, 0x0002, "replay_count", True, "Active resource replay pair count."),
    SaveStateRegion(0x0143, 0x00C4, "key_map", True, "Forty-nine four-byte raw-key/status mappings."),
    SaveStateRegion(0x0207, 0x0004, "reserved_pre_string_padding", True, "Reserved bytes before the string slots."),
    SaveStateRegion(0x020B, 0x01E0, "string_slots", True, "Twelve 40-byte script string slots."),
    SaveStateRegion(0x03EB, 0x0002, "text_foreground", True, "Derived foreground text attribute."),
    SaveStateRegion(0x03ED, 0x0002, "text_background", True, "Derived background text attribute."),
    SaveStateRegion(0x03EF, 0x0002, "text_attribute", True, "Packed current text/window attribute."),
    SaveStateRegion(0x03F1, 0x0002, "input_line_enabled", True, "Input-line enabled word."),
    SaveStateRegion(0x03F3, 0x0002, "input_row", True, "Configured input text row."),
    SaveStateRegion(0x03F5, 0x0001, "prompt_marker", True, "Input prompt marker byte."),
    SaveStateRegion(0x03F6, 0x0001, "reserved_text_padding", True, "Reserved byte aligning the following word state."),
    SaveStateRegion(0x03F7, 0x0002, "status_line_enabled", True, "Status-line enabled word."),
    SaveStateRegion(0x03F9, 0x0002, "status_row", True, "Configured status text row."),
    SaveStateRegion(0x03FB, 0x0002, "display_base_row", True, "Configured display base row."),
    SaveStateRegion(0x03FD, 0x0002, "display_bottom_row", True, "Display base row plus 21."),
    SaveStateRegion(0x03FF, 0x0002, "saved_replay_count", True, "Replay rollback checkpoint count."),
    SaveStateRegion(0x0401, 0x0002, "menu_interaction_gate", True, "GR menu interaction gate word."),
    SaveStateRegion(0x0403, 0x0001, "key_release_enqueue_gate", True, "GR key-release enqueue gate byte."),
)


def validate_state_regions(regions: tuple[SaveStateRegion, ...], length: int) -> None:
    expected = 0
    names: set[str] = set()
    for region in regions:
        if region.name in names:
            raise ValueError(f"duplicate save-state region name: {region.name}")
        names.add(region.name)
        if region.offset != expected:
            raise ValueError(
                f"save-state map gap or overlap at {expected:#x}: "
                f"next region {region.name} starts at {region.offset:#x}"
            )
        if region.size <= 0:
            raise ValueError(f"save-state region {region.name} has nonpositive size")
        expected = region.end
    if expected != length:
        raise ValueError(f"save-state map ends at {expected:#x}, expected {length:#x}")


def split_state_regions(
    data: bytes,
    regions: tuple[SaveStateRegion, ...],
    length: int,
) -> dict[str, bytes]:
    validate_state_regions(regions, length)
    if len(data) != length:
        raise ValueError(f"save-state block length {len(data):#x}, expected {length:#x}")
    return {region.name: data[region.offset : region.end] for region in regions}


def split_sq2_block1(data: bytes) -> dict[str, bytes]:
    return split_state_regions(data, SQ2_BLOCK1_REGIONS, SQ2_BLOCK1_LENGTH)


def split_early_24xx_block1(data: bytes) -> dict[str, bytes]:
    return split_state_regions(
        data,
        EARLY_24XX_BLOCK1_REGIONS,
        EARLY_24XX_BLOCK1_LENGTH,
    )


def split_kq1_2917_block1(data: bytes) -> dict[str, bytes]:
    return split_state_regions(data, KQ1_2917_BLOCK1_REGIONS, KQ1_2917_BLOCK1_LENGTH)


def split_kq4_3002086_block1(data: bytes) -> dict[str, bytes]:
    return split_state_regions(
        data,
        KQ4_3002086_BLOCK1_REGIONS,
        KQ4_3002086_BLOCK1_LENGTH,
    )


def split_gr_v3_block1(data: bytes) -> dict[str, bytes]:
    return split_state_regions(data, GR_V3_BLOCK1_REGIONS, GR_V3_BLOCK1_LENGTH)


def split_kq4d_v3_block1(data: bytes) -> dict[str, bytes]:
    return split_state_regions(data, KQ4D_V3_BLOCK1_REGIONS, KQ4D_V3_BLOCK1_LENGTH)


def split_object_records(
    data: bytes,
    *,
    record_count: int,
    block_name: str = "save-state block",
) -> tuple[dict[str, bytes], ...]:
    expected_length = record_count * SQ2_OBJECT_RECORD_SIZE
    if len(data) != expected_length:
        raise ValueError(
            f"{block_name} length {len(data):#x}, expected {expected_length:#x}"
        )
    validate_state_regions(SQ2_OBJECT_RECORD_FIELDS, SQ2_OBJECT_RECORD_SIZE)
    return tuple(
        split_state_regions(
            data[offset : offset + SQ2_OBJECT_RECORD_SIZE],
            SQ2_OBJECT_RECORD_FIELDS,
            SQ2_OBJECT_RECORD_SIZE,
        )
        for offset in range(0, expected_length, SQ2_OBJECT_RECORD_SIZE)
    )


def split_sq2_block2(data: bytes) -> tuple[dict[str, bytes], ...]:
    return split_object_records(data, record_count=SQ2_OBJECT_RECORD_COUNT)


def split_kq1_2917_block2(data: bytes) -> tuple[dict[str, bytes], ...]:
    return split_object_records(
        data,
        record_count=KQ1_2917_OBJECT_RECORD_COUNT,
        block_name="KQ1 2.917 save-state block 2",
    )


def split_kq2_2411_block2(data: bytes) -> tuple[dict[str, bytes], ...]:
    return split_object_records(
        data,
        record_count=KQ2_2411_OBJECT_RECORD_COUNT,
        block_name="KQ2 2.411 save-state block 2",
    )


def split_pq1_2917_block2(data: bytes) -> tuple[dict[str, bytes], ...]:
    return split_object_records(
        data,
        record_count=PQ1_2917_OBJECT_RECORD_COUNT,
        block_name="PQ1 2.917 save-state block 2",
    )


def split_kq3_2936_block2(data: bytes) -> tuple[dict[str, bytes], ...]:
    return split_object_records(
        data,
        record_count=KQ3_2936_OBJECT_RECORD_COUNT,
        block_name="KQ3 2.936 save-state block 2",
    )


def split_lsl1_2440_block2(data: bytes) -> tuple[dict[str, bytes], ...]:
    return split_object_records(
        data,
        record_count=LSL1_2440_OBJECT_RECORD_COUNT,
        block_name="LSL1 2.440 save-state block 2",
    )


def split_kq4_3002086_block2(data: bytes) -> tuple[dict[str, bytes], ...]:
    return split_object_records(
        data,
        record_count=KQ4_3002086_OBJECT_RECORD_COUNT,
        block_name="KQ4 3.002.086 save-state block 2",
    )


def split_replay_pairs(data: bytes, *, pair_count: int) -> tuple[tuple[int, int], ...]:
    expected_length = pair_count * SQ2_REPLAY_PAIR_SIZE
    if len(data) != expected_length:
        raise ValueError(
            f"save-state block length {len(data):#x}, expected {expected_length:#x}"
        )
    return tuple(
        (data[offset], data[offset + 1])
        for offset in range(0, expected_length, SQ2_REPLAY_PAIR_SIZE)
    )


def split_sq2_block4(data: bytes) -> tuple[tuple[int, int], ...]:
    return split_replay_pairs(data, pair_count=SQ2_REPLAY_PAIR_COUNT)


def split_kq1_2917_block4(data: bytes) -> tuple[tuple[int, int], ...]:
    return split_replay_pairs(data, pair_count=KQ1_2917_REPLAY_PAIR_COUNT)


def split_kq2_2411_block4(data: bytes) -> tuple[tuple[int, int], ...]:
    return split_replay_pairs(data, pair_count=KQ2_2411_REPLAY_PAIR_COUNT)


def split_pq1_2917_block4(data: bytes) -> tuple[tuple[int, int], ...]:
    return split_replay_pairs(data, pair_count=PQ1_2917_REPLAY_PAIR_COUNT)


def split_kq3_2936_block4(data: bytes) -> tuple[tuple[int, int], ...]:
    return split_replay_pairs(data, pair_count=KQ3_2936_REPLAY_PAIR_COUNT)


def split_lsl1_2440_block4(data: bytes) -> tuple[tuple[int, int], ...]:
    return split_replay_pairs(data, pair_count=LSL1_2440_REPLAY_PAIR_COUNT)


def split_kq4_3002086_block4(data: bytes) -> tuple[tuple[int, int], ...]:
    return split_replay_pairs(data, pair_count=KQ4_3002086_REPLAY_PAIR_COUNT)


def u16le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def u16le_bytes(value: int) -> bytes:
    if value < 0 or value > 0xFFFF:
        raise ValueError(f"value does not fit in a save-file length prefix: {value}")
    return bytes((value & 0xFF, value >> 8))


def split_inventory_block(data: bytes, *, item_table_size: int) -> SaveInventoryState:
    if item_table_size % SQ2_INVENTORY_ITEM_SIZE:
        raise ValueError("inventory item table size must be a multiple of three")
    if item_table_size <= 0 or item_table_size > len(data):
        raise ValueError("inventory item table size is outside the save-state block")

    items: list[SaveInventoryItem] = []
    item_count = item_table_size // SQ2_INVENTORY_ITEM_SIZE
    for index in range(item_count):
        offset = index * SQ2_INVENTORY_ITEM_SIZE
        name_offset = u16le(data, offset)
        if name_offset < item_table_size or name_offset >= len(data):
            raise ValueError(f"inventory item {index} has invalid name offset {name_offset:#x}")
        name_end = data.find(b"\0", name_offset)
        if name_end < 0:
            raise ValueError(f"inventory item {index} name is not terminated")
        items.append(
            SaveInventoryItem(
                index,
                name_offset,
                data[offset + 2],
                data[name_offset:name_end],
            )
        )
    return SaveInventoryState(
        item_table_size,
        tuple(items),
        data[item_table_size:],
    )


def split_sq2_block3(data: bytes) -> SaveInventoryState:
    if len(data) != SQ2_BLOCK3_LENGTH:
        raise ValueError(
            f"save-state block length {len(data):#x}, expected {SQ2_BLOCK3_LENGTH:#x}"
        )
    if SQ2_INVENTORY_ITEM_TABLE_SIZE != SQ2_INVENTORY_ITEM_COUNT * SQ2_INVENTORY_ITEM_SIZE:
        raise ValueError("inventory item table constants do not agree")
    return split_inventory_block(data, item_table_size=SQ2_INVENTORY_ITEM_TABLE_SIZE)


def split_kq1_2917_block3(data: bytes) -> SaveInventoryState:
    if len(data) != KQ1_2917_BLOCK3_LENGTH:
        raise ValueError(
            f"KQ1 2.917 save-state block 3 length {len(data):#x}, "
            f"expected {KQ1_2917_BLOCK3_LENGTH:#x}"
        )
    return split_inventory_block(data, item_table_size=KQ1_2917_INVENTORY_ITEM_TABLE_SIZE)


def split_kq2_2411_block3(data: bytes) -> SaveInventoryState:
    if len(data) != KQ2_2411_BLOCK3_LENGTH:
        raise ValueError(
            f"KQ2 2.411 save-state block 3 length {len(data):#x}, "
            f"expected {KQ2_2411_BLOCK3_LENGTH:#x}"
        )
    return split_inventory_block(data, item_table_size=KQ2_2411_INVENTORY_ITEM_TABLE_SIZE)


def split_pq1_2917_block3(data: bytes) -> SaveInventoryState:
    if len(data) != PQ1_2917_BLOCK3_LENGTH:
        raise ValueError(
            f"PQ1 2.917 save-state block 3 length {len(data):#x}, "
            f"expected {PQ1_2917_BLOCK3_LENGTH:#x}"
        )
    return split_inventory_block(data, item_table_size=PQ1_2917_INVENTORY_ITEM_TABLE_SIZE)


def split_kq3_2936_block3(data: bytes) -> SaveInventoryState:
    if len(data) != KQ3_2936_BLOCK3_LENGTH:
        raise ValueError(
            f"KQ3 2.936 save-state block 3 length {len(data):#x}, "
            f"expected {KQ3_2936_BLOCK3_LENGTH:#x}"
        )
    return split_inventory_block(data, item_table_size=KQ3_2936_INVENTORY_ITEM_TABLE_SIZE)


def split_lsl1_2440_block3(data: bytes) -> SaveInventoryState:
    if len(data) != LSL1_2440_BLOCK3_LENGTH:
        raise ValueError(
            f"LSL1 2.440 save-state block 3 length {len(data):#x}, "
            f"expected {LSL1_2440_BLOCK3_LENGTH:#x}"
        )
    return split_inventory_block(data, item_table_size=LSL1_2440_INVENTORY_ITEM_TABLE_SIZE)


def split_kq4_3002086_block3(data: bytes) -> SaveInventoryState:
    decoded = gr_v3_object_inventory_save_xor(data)
    if len(decoded) != KQ4_3002086_BLOCK3_LENGTH:
        raise ValueError(
            f"KQ4 3.002.086 save-state block 3 length {len(decoded):#x}, "
            f"expected {KQ4_3002086_BLOCK3_LENGTH:#x}"
        )
    return split_inventory_block(
        decoded,
        item_table_size=KQ4_3002086_INVENTORY_ITEM_TABLE_SIZE,
    )


def split_sq2_block5(data: bytes) -> SaveLogicResumeState:
    if len(data) < 4 or len(data) % 4 != 0:
        raise ValueError("save-state block 5 length must be a nonzero multiple of four")

    entries: list[SaveLogicResumeEntry] = []
    for offset in range(0, len(data), 4):
        logic_number = u16le(data, offset)
        resume_offset = u16le(data, offset + 2)
        if logic_number == 0xFFFF:
            if offset + 4 != len(data):
                raise ValueError("save-state block 5 has data after its terminator")
            return SaveLogicResumeState(tuple(entries), resume_offset)
        if logic_number > 0xFF:
            raise ValueError(
                f"save-state block 5 logic number {logic_number:#x} is not byte-sized"
            )
        entries.append(SaveLogicResumeEntry(logic_number, resume_offset))
    raise ValueError("save-state block 5 has no terminator")


def xor_with_repeating_key(data: bytes, key: bytes) -> bytes:
    if not key:
        raise ValueError("xor key must not be empty")
    return bytes(value ^ key[index % len(key)] for index, value in enumerate(data))


def decode_object_metadata_file(data: bytes, *, key: bytes) -> ObjectMetadata:
    decoded = xor_with_repeating_key(data, key)
    if len(decoded) < 3:
        raise ValueError("object metadata file is too short")
    item_table_size = u16le(decoded, 0)
    maximum_object_index = decoded[2]
    runtime_block = decoded[3:]
    split_inventory_block(runtime_block, item_table_size=item_table_size)
    return ObjectMetadata(item_table_size, maximum_object_index, runtime_block)


def decode_sq2_object_file(data: bytes) -> tuple[int, int, bytes]:
    metadata = decode_object_metadata_file(data, key=SQ2_OBJECT_FILE_XOR_KEY)
    item_table_size = metadata.item_table_size
    maximum_object_index = metadata.maximum_object_index
    runtime_block = metadata.runtime_block
    if item_table_size != SQ2_INVENTORY_ITEM_TABLE_SIZE:
        raise ValueError(
            f"object metadata item table size {item_table_size:#x}, "
            f"expected {SQ2_INVENTORY_ITEM_TABLE_SIZE:#x}"
        )
    if maximum_object_index + 1 != SQ2_OBJECT_RECORD_COUNT:
        raise ValueError(
            f"object metadata record count {maximum_object_index + 1}, "
            f"expected {SQ2_OBJECT_RECORD_COUNT}"
        )
    split_sq2_block3(runtime_block)
    return item_table_size, maximum_object_index, runtime_block


def decode_kq1_2917_object_file(data: bytes) -> ObjectMetadata:
    metadata = decode_object_metadata_file(data, key=SQ2_OBJECT_FILE_XOR_KEY)
    if metadata.item_table_size != KQ1_2917_INVENTORY_ITEM_TABLE_SIZE:
        raise ValueError(
            f"KQ1 2.917 object metadata item table size "
            f"{metadata.item_table_size:#x}, "
            f"expected {KQ1_2917_INVENTORY_ITEM_TABLE_SIZE:#x}"
        )
    if metadata.object_record_count != KQ1_2917_OBJECT_RECORD_COUNT:
        raise ValueError(
            f"KQ1 2.917 object metadata record count "
            f"{metadata.object_record_count}, "
            f"expected {KQ1_2917_OBJECT_RECORD_COUNT}"
        )
    if len(metadata.runtime_block) != KQ1_2917_BLOCK3_LENGTH:
        raise ValueError(
            f"KQ1 2.917 object runtime block length "
            f"{len(metadata.runtime_block):#x}, "
            f"expected {KQ1_2917_BLOCK3_LENGTH:#x}"
        )
    return metadata


def decode_kq2_2411_object_file(data: bytes) -> ObjectMetadata:
    metadata = decode_object_metadata_file(data, key=SQ2_OBJECT_FILE_XOR_KEY)
    if metadata.item_table_size != KQ2_2411_INVENTORY_ITEM_TABLE_SIZE:
        raise ValueError(
            f"KQ2 2.411 object metadata item table size "
            f"{metadata.item_table_size:#x}, "
            f"expected {KQ2_2411_INVENTORY_ITEM_TABLE_SIZE:#x}"
        )
    if metadata.object_record_count != KQ2_2411_OBJECT_RECORD_COUNT:
        raise ValueError(
            f"KQ2 2.411 object metadata record count "
            f"{metadata.object_record_count}, "
            f"expected {KQ2_2411_OBJECT_RECORD_COUNT}"
        )
    if len(metadata.runtime_block) != KQ2_2411_BLOCK3_LENGTH:
        raise ValueError(
            f"KQ2 2.411 object runtime block length "
            f"{len(metadata.runtime_block):#x}, "
            f"expected {KQ2_2411_BLOCK3_LENGTH:#x}"
        )
    return metadata


def decode_pq1_2917_object_file(data: bytes) -> ObjectMetadata:
    metadata = decode_object_metadata_file(data, key=SQ2_OBJECT_FILE_XOR_KEY)
    if metadata.item_table_size != PQ1_2917_INVENTORY_ITEM_TABLE_SIZE:
        raise ValueError(
            f"PQ1 2.917 object metadata item table size "
            f"{metadata.item_table_size:#x}, "
            f"expected {PQ1_2917_INVENTORY_ITEM_TABLE_SIZE:#x}"
        )
    if metadata.object_record_count != PQ1_2917_OBJECT_RECORD_COUNT:
        raise ValueError(
            f"PQ1 2.917 object metadata record count "
            f"{metadata.object_record_count}, expected {PQ1_2917_OBJECT_RECORD_COUNT}"
        )
    if len(metadata.runtime_block) != PQ1_2917_BLOCK3_LENGTH:
        raise ValueError(
            f"PQ1 2.917 object runtime block length "
            f"{len(metadata.runtime_block):#x}, expected {PQ1_2917_BLOCK3_LENGTH:#x}"
        )
    return metadata


def decode_kq3_2936_object_file(data: bytes) -> ObjectMetadata:
    metadata = decode_object_metadata_file(data, key=SQ2_OBJECT_FILE_XOR_KEY)
    if metadata.item_table_size != KQ3_2936_INVENTORY_ITEM_TABLE_SIZE:
        raise ValueError(
            f"KQ3 2.936 object metadata item table size "
            f"{metadata.item_table_size:#x}, "
            f"expected {KQ3_2936_INVENTORY_ITEM_TABLE_SIZE:#x}"
        )
    if metadata.object_record_count != KQ3_2936_OBJECT_RECORD_COUNT:
        raise ValueError(
            f"KQ3 2.936 object metadata record count "
            f"{metadata.object_record_count}, expected {KQ3_2936_OBJECT_RECORD_COUNT}"
        )
    if len(metadata.runtime_block) != KQ3_2936_BLOCK3_LENGTH:
        raise ValueError(
            f"KQ3 2.936 object runtime block length "
            f"{len(metadata.runtime_block):#x}, expected {KQ3_2936_BLOCK3_LENGTH:#x}"
        )
    return metadata


def decode_lsl1_2440_object_file(data: bytes) -> ObjectMetadata:
    metadata = decode_object_metadata_file(data, key=SQ2_OBJECT_FILE_XOR_KEY)
    if metadata.item_table_size != LSL1_2440_INVENTORY_ITEM_TABLE_SIZE:
        raise ValueError(
            f"LSL1 2.440 object metadata item table size "
            f"{metadata.item_table_size:#x}, "
            f"expected {LSL1_2440_INVENTORY_ITEM_TABLE_SIZE:#x}"
        )
    if metadata.object_record_count != LSL1_2440_OBJECT_RECORD_COUNT:
        raise ValueError(
            f"LSL1 2.440 object metadata record count "
            f"{metadata.object_record_count}, "
            f"expected {LSL1_2440_OBJECT_RECORD_COUNT}"
        )
    if len(metadata.runtime_block) != LSL1_2440_BLOCK3_LENGTH:
        raise ValueError(
            f"LSL1 2.440 object runtime block length "
            f"{len(metadata.runtime_block):#x}, "
            f"expected {LSL1_2440_BLOCK3_LENGTH:#x}"
        )
    return metadata


def decode_kq4_3002086_object_file(data: bytes) -> ObjectMetadata:
    metadata = decode_object_metadata_file(data, key=SQ2_OBJECT_FILE_XOR_KEY)
    if metadata.item_table_size != KQ4_3002086_INVENTORY_ITEM_TABLE_SIZE:
        raise ValueError(
            f"KQ4 3.002.086 object metadata item table size "
            f"{metadata.item_table_size:#x}, "
            f"expected {KQ4_3002086_INVENTORY_ITEM_TABLE_SIZE:#x}"
        )
    if metadata.object_record_count != KQ4_3002086_OBJECT_RECORD_COUNT:
        raise ValueError(
            f"KQ4 3.002.086 object metadata record count "
            f"{metadata.object_record_count}, "
            f"expected {KQ4_3002086_OBJECT_RECORD_COUNT}"
        )
    if len(metadata.runtime_block) != KQ4_3002086_BLOCK3_LENGTH:
        raise ValueError(
            f"KQ4 3.002.086 object runtime block length "
            f"{len(metadata.runtime_block):#x}, "
            f"expected {KQ4_3002086_BLOCK3_LENGTH:#x}"
        )
    return metadata


def decode_gr_v3_object_file(data: bytes) -> ObjectMetadata:
    metadata = decode_object_metadata_file(data, key=SQ2_OBJECT_FILE_XOR_KEY)
    if metadata.item_table_size != GR_V3_INVENTORY_ITEM_TABLE_SIZE:
        raise ValueError(
            f"object metadata item table size {metadata.item_table_size:#x}, "
            f"expected {GR_V3_INVENTORY_ITEM_TABLE_SIZE:#x}"
        )
    if metadata.object_record_count != GR_V3_OBJECT_RECORD_COUNT:
        raise ValueError(
            f"object metadata record count {metadata.object_record_count}, "
            f"expected {GR_V3_OBJECT_RECORD_COUNT}"
        )
    if len(metadata.runtime_block) != GR_V3_BLOCK3_LENGTH:
        raise ValueError(
            f"object runtime block length {len(metadata.runtime_block):#x}, "
            f"expected {GR_V3_BLOCK3_LENGTH:#x}"
        )
    return metadata


def decode_kq4d_v3_object_file(data: bytes) -> ObjectMetadata:
    metadata = decode_object_metadata_file(data, key=SQ2_OBJECT_FILE_XOR_KEY)
    if metadata.item_table_size != KQ4D_V3_INVENTORY_ITEM_TABLE_SIZE:
        raise ValueError(
            f"KQ4D v3 object metadata item table size {metadata.item_table_size:#x}, "
            f"expected {KQ4D_V3_INVENTORY_ITEM_TABLE_SIZE:#x}"
        )
    if metadata.object_record_count != KQ4D_V3_OBJECT_RECORD_COUNT:
        raise ValueError(
            f"KQ4D v3 object metadata record count {metadata.object_record_count}, "
            f"expected {KQ4D_V3_OBJECT_RECORD_COUNT}"
        )
    if len(metadata.runtime_block) != KQ4D_V3_BLOCK3_LENGTH:
        raise ValueError(
            f"KQ4D v3 object runtime block length {len(metadata.runtime_block):#x}, "
            f"expected {KQ4D_V3_BLOCK3_LENGTH:#x}"
        )
    return metadata


def split_gr_v3_block2(data: bytes) -> tuple[dict[str, bytes], ...]:
    return split_object_records(
        data,
        record_count=GR_V3_OBJECT_RECORD_COUNT,
        block_name="GR v3 save-state block 2",
    )


def split_kq4d_v3_block2(data: bytes) -> tuple[dict[str, bytes], ...]:
    return split_object_records(
        data,
        record_count=KQ4D_V3_OBJECT_RECORD_COUNT,
        block_name="KQ4D v3 save-state block 2",
    )


def split_kq4d_v3_block3(data: bytes) -> SaveInventoryState:
    decoded = gr_v3_object_inventory_save_xor(data)
    if len(decoded) != KQ4D_V3_BLOCK3_LENGTH:
        raise ValueError(
            f"KQ4D v3 save-state block 3 length {len(decoded):#x}, "
            f"expected {KQ4D_V3_BLOCK3_LENGTH:#x}"
        )
    return split_inventory_block(decoded, item_table_size=KQ4D_V3_INVENTORY_ITEM_TABLE_SIZE)


def split_kq4d_v3_block4(data: bytes) -> tuple[tuple[int, int], ...]:
    return split_replay_pairs(data, pair_count=KQ4D_V3_REPLAY_PAIR_COUNT)


def split_gr_v3_block3(data: bytes) -> SaveInventoryState:
    decoded = gr_v3_object_inventory_save_xor(data)
    if len(decoded) != GR_V3_BLOCK3_LENGTH:
        raise ValueError(
            f"GR v3 save-state block 3 length {len(decoded):#x}, "
            f"expected {GR_V3_BLOCK3_LENGTH:#x}"
        )
    return split_inventory_block(decoded, item_table_size=GR_V3_INVENTORY_ITEM_TABLE_SIZE)


def split_gr_v3_block4(data: bytes) -> tuple[tuple[int, int], ...]:
    return split_replay_pairs(data, pair_count=GR_V3_REPLAY_PAIR_COUNT)


def gr_v3_object_inventory_save_xor(data: bytes) -> bytes:
    """Apply the observed Gold Rush v3 object/inventory save-block transform."""
    return xor_with_repeating_key(data, GR_V3_OBJECT_INVENTORY_XOR_KEY)


def _source_lower_drive(char: str) -> str:
    if "A" <= char <= "Z":
        return chr(ord(char) + 0x20)
    return char


def save_path_validation_plan(
    text: str,
    *,
    current_directory: str = "\\",
    current_drive_letter: str = "c",
) -> SavePathValidationPlan:
    """Model the source-level path normalization before DOS availability checks."""
    pos = 0
    while pos < len(text) and text[pos] == " ":
        pos += 1
    effective = text[pos:]
    used_default = False
    if effective == "":
        effective = current_directory
        used_default = True

    stripped = False
    if len(effective) > 1 and effective[-1] in SAVE_PATH_SEPARATORS:
        effective = effective[:-1]
        stripped = True

    if len(effective) >= 2 and effective[1] == ":":
        drive_letter = _source_lower_drive(effective[0])
    else:
        drive_letter = current_drive_letter

    if len(effective) == 1 and effective in SAVE_PATH_SEPARATORS:
        check_kind = "single_separator_accept"
    elif len(effective) == 2 and effective[1] == ":":
        check_kind = "drive_available"
    else:
        check_kind = "find_directory"

    return SavePathValidationPlan(effective, check_kind, drive_letter, used_default, stripped)


def parse_save(data: bytes, *, path: Path | None = None) -> SaveGame:
    if len(data) < SAVE_HEADER_LENGTH:
        raise ValueError("save file is too short for the 31-byte header")
    header = data[:SAVE_HEADER_LENGTH]
    pos = SAVE_HEADER_LENGTH
    blocks: list[SaveBlock] = []
    for block_index in range(SAVE_BLOCK_COUNT):
        length_prefix_offset = pos
        if pos + 2 > len(data):
            raise ValueError(f"save block {block_index} has no length prefix")
        length = u16le(data, pos)
        pos += 2
        data_offset = pos
        end = pos + length
        if end > len(data):
            raise ValueError(f"save block {block_index} is truncated")
        blocks.append(
            SaveBlock(
                block_index,
                length_prefix_offset,
                data_offset,
                length,
                data[pos:end],
            )
        )
        pos = end
    if pos != len(data):
        raise ValueError("save file has trailing bytes after the fifth block")
    return SaveGame(path, header, tuple(blocks))


def load_save(path: Path) -> SaveGame:
    return parse_save(path.read_bytes(), path=path)


def serialize_save(save: SaveGame) -> bytes:
    if len(save.header) != SAVE_HEADER_LENGTH:
        raise ValueError("save header must be exactly 31 bytes")
    if len(save.blocks) != SAVE_BLOCK_COUNT:
        raise ValueError("save file envelope must contain exactly 5 save blocks")

    data = bytearray(save.header)
    for expected_index, block in enumerate(save.blocks):
        if block.index != expected_index:
            raise ValueError(
                f"save block {expected_index} has mismatched index {block.index}"
            )
        if block.length != len(block.data):
            raise ValueError(
                f"save block {block.index} length prefix {block.length} "
                f"does not match {len(block.data)} data bytes"
            )
        data.extend(u16le_bytes(block.length))
        data.extend(block.data)
    return bytes(data)


def write_save(save: SaveGame, path: Path) -> None:
    path.write_bytes(serialize_save(save))
