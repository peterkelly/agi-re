#!/usr/bin/env python3
"""Generate clean-room QEMU fixture game directories."""

from __future__ import annotations

import argparse
import stat
import shutil
from pathlib import Path

from agi_resources import (
    ResourceDirectoryLayout,
    ResourceFormatError,
    ResourceKind,
    detect_layout,
    encode_picture_nibbles,
    read_directory_entries,
    volume_path,
)
from agi_graphics import picture_payload, view_payload
from project_paths import game_dir as configured_game_dir


ROOT = Path(__file__).resolve().parents[1]
GAMES_ROOT = ROOT / "games"
SCRATCH_VAR = 250
DEFAULT_INIT_FLAG = 199
SPEED_VAR = 0x0A
CAROUSEL_INDEX_VAR = 0xF9
CAROUSEL_DELAY_VAR = 0xF8
RAW_KEY_VAR = 0x13
CAROUSEL_STATUS_BASE = 7
EVENT_RECORDING_BLOCK_FLAG = 7
MESSAGE_XOR_KEY = b"Avis Durgan"
MINIMAL_PICTURE_FIXTURE_FILES = {
    "AGI",
    "AGIDATA.OVL",
    "CGA_GRAF.OVL",
    "EGA_GRAF.OVL",
    "HGC_FONT",
    "HGC_GRAF.OVL",
    "HGC_OBJS.OVL",
    "IBM_OBJS.OVL",
    "JR_GRAF.OVL",
    "LOGDIR",
    "OBJECT",
    "PICDIR",
    "SIERRA.COM",
    "SNDDIR",
    "VG_GRAF.OVL",
    "VIEWDIR",
    "WORDS.TOK",
    "_SQ2.BAT",
}


def u16le(value: int) -> bytes:
    return bytes([value & 0xFF, (value >> 8) & 0xFF])


def xor_message_text(text: bytes) -> bytes:
    out = bytearray()
    for idx, value in enumerate(text):
        out.append(value ^ MESSAGE_XOR_KEY[idx % len(MESSAGE_XOR_KEY)])
    return bytes(out)


def logic_resource(
    code: bytes,
    messages: list[str | bytes] | None = None,
    *,
    encrypt_messages: bool = True,
) -> bytes:
    if messages is None:
        return u16le(len(code)) + code + bytes([0x00]) + u16le(0x0002)

    encoded_messages = []
    for message in messages:
        raw = message.encode("ascii") if isinstance(message, str) else bytes(message)
        encoded_messages.append(raw.rstrip(b"\x00") + b"\x00")

    table_size = (len(encoded_messages) + 1) * 2
    offsets = []
    cursor = table_size
    text = bytearray()
    for message in encoded_messages:
        offsets.append(cursor)
        text.extend(message)
        cursor += len(message)
    table = bytearray()
    table.extend(u16le(cursor))
    for offset in offsets:
        table.extend(u16le(offset))
    message_text = xor_message_text(bytes(text)) if encrypt_messages else bytes(text)
    return u16le(len(code)) + code + bytes([len(encoded_messages)]) + bytes(table) + message_text


def self_loop() -> bytes:
    return bytes([0xFE, 0xFD, 0xFF])


def end_action() -> bytes:
    return bytes([0x00])


def assignn_action(var_no: int, value: int) -> bytes:
    values = [var_no, value]
    if any(not 0 <= item <= 0xFF for item in values):
        raise ValueError("assignn operands must fit in one byte")
    return bytes([0x03, var_no, value])


def inc_var_action(var_no: int) -> bytes:
    if not 0 <= var_no <= 0xFF:
        raise ValueError("inc_var operand must fit in one byte")
    return bytes([0x01, var_no])


def set_flag_action(flag_no: int) -> bytes:
    if not 0 <= flag_no <= 0xFF:
        raise ValueError("flag number must fit in one byte")
    return bytes([0x0C, flag_no])


def not_flag_set_condition(flag_no: int) -> bytes:
    if not 0 <= flag_no <= 0xFF:
        raise ValueError("flag number must fit in one byte")
    return bytes([0xFD, 0x07, flag_no])


def var_eq_imm_condition(var_no: int, value: int) -> bytes:
    values = [var_no, value]
    if any(not 0 <= item <= 0xFF for item in values):
        raise ValueError("variable/immediate operands must fit in one byte")
    return bytes([0x01, var_no, value])


def raw_key_event_available_condition() -> bytes:
    return bytes([0x0D])


def status_byte_condition(index: int) -> bytes:
    if not 0 <= index <= 0xFF:
        raise ValueError("status byte index must fit in one byte")
    return bytes([0x0C, index])


def all_conditions(*conditions: bytes) -> bytes:
    return b"".join(conditions)


def if_then(condition: bytes, then_actions: bytes) -> bytes:
    if len(then_actions) > 0x7FFF:
        raise ValueError("conditional body is too large for a positive relative delta")
    return bytes([0xFF]) + condition + bytes([0xFF]) + u16le(len(then_actions)) + then_actions


def run_once_logic(actions: bytes, init_flag: int = DEFAULT_INIT_FLAG) -> bytes:
    body = actions + set_flag_action(init_flag)
    return logic_resource(if_then(not_flag_set_condition(init_flag), body) + end_action())


def load_show_picture_actions(picture_no: int, scratch_var: int = SCRATCH_VAR) -> bytes:
    if not 0 <= picture_no <= 0xFF:
        raise ValueError("picture number must fit in one byte")
    if not 0 <= scratch_var <= 0xFF:
        raise ValueError("scratch variable must fit in one byte")
    return bytes([0x03, scratch_var, picture_no, 0x18, scratch_var, 0x19, scratch_var, 0x1A])


def discard_picture_actions(picture_no: int, scratch_var: int = SCRATCH_VAR) -> bytes:
    if not 0 <= picture_no <= 0xFF:
        raise ValueError("picture number must fit in one byte")
    if not 0 <= scratch_var <= 0xFF:
        raise ValueError("scratch variable must fit in one byte")
    return bytes([0x03, scratch_var, picture_no, 0x1B, scratch_var])


def map_key_event_action(key_word: int, status_index: int) -> bytes:
    if not 0 <= key_word <= 0xFFFF:
        raise ValueError("key word must fit in two bytes")
    if not 0 <= status_index <= 0xFF:
        raise ValueError("status byte index must fit in one byte")
    return bytes([0x79, key_word & 0xFF, (key_word >> 8) & 0xFF, status_index])


def picture_carousel_logic_payload(
    picture_numbers: list[int],
    advance_key_words: list[int] | None = None,
    scratch_var: int = SCRATCH_VAR,
    index_var: int = CAROUSEL_INDEX_VAR,
    status_base: int = CAROUSEL_STATUS_BASE,
    init_flag: int = DEFAULT_INIT_FLAG,
) -> bytes:
    if not picture_numbers:
        raise ValueError("picture carousel requires at least one picture")
    if len(picture_numbers) > 0x100:
        raise ValueError("picture carousel index must fit in one byte")
    if advance_key_words is None:
        advance_key_words = [ord("x")]
    if len(advance_key_words) < max(0, len(picture_numbers) - 1):
        raise ValueError("picture carousel requires one advance key per transition")
    values = [*picture_numbers, scratch_var, index_var, status_base, init_flag]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("carousel operands must fit in one byte")
    if any(not 0 <= value <= 0xFFFF for value in advance_key_words):
        raise ValueError("carousel advance keys must fit in two bytes")
    if status_base + len(picture_numbers) - 2 > 0xFF:
        raise ValueError("carousel status byte indexes must fit in one byte")

    key_mappings = b"".join(
        map_key_event_action(key_word, status_base + index)
        for index, key_word in enumerate(advance_key_words[: len(picture_numbers) - 1])
    )
    setup = (
        bytes([0x77])
        + key_mappings
        + load_show_picture_actions(picture_numbers[0], scratch_var)
        + assignn_action(index_var, 0)
        + set_flag_action(init_flag)
    )
    code = if_then(not_flag_set_condition(init_flag), setup)
    for index, picture_no in enumerate(picture_numbers[:-1]):
        next_index = index + 1
        next_picture = picture_numbers[next_index]
        condition = all_conditions(var_eq_imm_condition(index_var, index), status_byte_condition(status_base + index))
        actions = (
            load_show_picture_actions(next_picture, scratch_var)
            + assignn_action(index_var, next_index)
            + discard_picture_actions(picture_no, scratch_var)
        )
        code += if_then(condition, actions)
    code += end_action()
    return logic_resource(code)


def picture_timed_carousel_logic_payload(
    picture_numbers: list[int],
    delay_cycles: int = 20,
    speed_value: int = 0,
    scratch_var: int = SCRATCH_VAR,
    index_var: int = CAROUSEL_INDEX_VAR,
    delay_var: int = CAROUSEL_DELAY_VAR,
    init_flag: int = DEFAULT_INIT_FLAG,
    suppress_event_recording: bool = True,
) -> bytes:
    if not picture_numbers:
        raise ValueError("picture timed carousel requires at least one picture")
    if len(picture_numbers) > 0x100:
        raise ValueError("picture carousel index must fit in one byte")
    values = [*picture_numbers, delay_cycles, speed_value, scratch_var, index_var, delay_var, init_flag]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("timed carousel operands must fit in one byte")
    if delay_cycles == 0:
        raise ValueError("timed carousel delay must be nonzero")

    setup = bytes([0x77])
    if suppress_event_recording:
        setup += set_flag_action(EVENT_RECORDING_BLOCK_FLAG)
    setup += (
        assignn_action(SPEED_VAR, speed_value)
        + assignn_action(delay_var, 0)
        + load_show_picture_actions(picture_numbers[0], scratch_var)
        + assignn_action(index_var, 0)
        + set_flag_action(init_flag)
    )
    code = if_then(not_flag_set_condition(init_flag), setup)
    code += inc_var_action(delay_var)
    for index, picture_no in enumerate(picture_numbers[:-1]):
        next_index = index + 1
        next_picture = picture_numbers[next_index]
        condition = all_conditions(var_eq_imm_condition(index_var, index), var_eq_imm_condition(delay_var, delay_cycles))
        actions = (
            load_show_picture_actions(next_picture, scratch_var)
            + assignn_action(index_var, next_index)
            + assignn_action(delay_var, 0)
            + discard_picture_actions(picture_no, scratch_var)
        )
        code += if_then(condition, actions)
    code += end_action()
    return logic_resource(code)


def setup_persistent_object_actions(
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority_byte: int | None,
    object_no: int = 0,
) -> bytes:
    values = [view_no, group_no, frame_no, x, baseline_y, object_no]
    if priority_byte is not None:
        values.append(priority_byte)
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("fixture operands must fit in one byte")
    code = bytes(
        [
            0x1E,
            view_no,
            0x21,
            object_no,
            0x29,
            object_no,
            view_no,
            0x2B,
            object_no,
            group_no,
            0x2F,
            object_no,
            frame_no,
            0x25,
            object_no,
            x,
            baseline_y,
        ]
    )
    if priority_byte is not None:
        code += bytes([0x36, object_no, priority_byte])
    code += bytes([0x23, object_no])
    return code


def setup_transient_object_action(
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority: int,
    control: int | None = None,
) -> bytes:
    values = [view_no, group_no, frame_no, x, baseline_y, priority]
    if control is not None:
        values.append(control)
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("fixture operands must fit in one byte")
    if control is None:
        control = priority
    return bytes([0x7A, view_no, group_no, frame_no, x, baseline_y, priority, control])


def view_carousel_case_actions(
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority: int,
    control: int | None = None,
    scratch_var: int = SCRATCH_VAR,
) -> bytes:
    values = [picture_no, view_no, group_no, frame_no, x, baseline_y, priority, scratch_var]
    if control is not None:
        values.append(control)
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("view carousel operands must fit in one byte")
    return (
        load_show_picture_actions(picture_no, scratch_var)
        + bytes([0x1E, view_no])
        + setup_transient_object_action(view_no, group_no, frame_no, x, baseline_y, priority, control)
    )


def view_timed_carousel_logic_payload(
    cases: list[tuple[int, int, int, int, int, int, int, int | None]],
    delay_cycles: int = 20,
    speed_value: int = 0,
    scratch_var: int = SCRATCH_VAR,
    index_var: int = CAROUSEL_INDEX_VAR,
    delay_var: int = CAROUSEL_DELAY_VAR,
    init_flag: int = DEFAULT_INIT_FLAG,
    suppress_event_recording: bool = True,
) -> bytes:
    if not cases:
        raise ValueError("view timed carousel requires at least one case")
    if len(cases) > 0x100:
        raise ValueError("view carousel index must fit in one byte")
    values = [delay_cycles, speed_value, scratch_var, index_var, delay_var, init_flag]
    for picture_no, view_no, group_no, frame_no, x, baseline_y, priority, control in cases:
        values.extend([picture_no, view_no, group_no, frame_no, x, baseline_y, priority])
        if control is not None:
            values.append(control)
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("view timed carousel operands must fit in one byte")
    if delay_cycles == 0:
        raise ValueError("timed carousel delay must be nonzero")

    setup = bytes([0x77])
    if suppress_event_recording:
        setup += set_flag_action(EVENT_RECORDING_BLOCK_FLAG)
    setup += (
        assignn_action(SPEED_VAR, speed_value)
        + assignn_action(delay_var, 0)
        + view_carousel_case_actions(*cases[0], scratch_var=scratch_var)
        + assignn_action(index_var, 0)
        + set_flag_action(init_flag)
    )
    code = if_then(not_flag_set_condition(init_flag), setup)
    code += inc_var_action(delay_var)
    for index, case in enumerate(cases[:-1]):
        condition = all_conditions(var_eq_imm_condition(index_var, index), var_eq_imm_condition(delay_var, delay_cycles))
        actions = (
            view_carousel_case_actions(*cases[index + 1], scratch_var=scratch_var)
            + assignn_action(index_var, index + 1)
            + assignn_action(delay_var, 0)
        )
        code += if_then(condition, actions)
    code += end_action()
    return logic_resource(code)


def move_object_to_action(
    object_no: int,
    target_x: int,
    target_y: int,
    step_size: int,
    completion_flag: int,
) -> bytes:
    values = [object_no, target_x, target_y, step_size, completion_flag]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("fixture operands must fit in one byte")
    return bytes([0x51, object_no, target_x, target_y, step_size, completion_flag])


def approach_first_object_until_near_action(object_no: int, threshold: int, completion_flag: int) -> bytes:
    values = [object_no, threshold, completion_flag]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("approach operands must fit in one byte")
    return bytes([0x53, object_no, threshold, completion_flag])


def start_random_motion_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x54, object_no])


def stop_motion_mode_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x55, object_no])


def set_rect_bounds_action(left: int, top: int, right: int, bottom: int) -> bytes:
    values = [left, top, right, bottom]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("rectangle bounds must fit in one byte")
    return bytes([0x5A, left, top, right, bottom])


def clear_rect_bounds_action() -> bytes:
    return bytes([0x5B])


def set_object_step_from_var_action(object_no: int, var_no: int) -> bytes:
    values = [object_no, var_no]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("object/variable operands must fit in one byte")
    return bytes([0x4F, object_no, var_no])


def set_object_tick_from_var_action(object_no: int, var_no: int) -> bytes:
    values = [object_no, var_no]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("object/variable operands must fit in one byte")
    return bytes([0x50, object_no, var_no])


def set_object_field_1f_from_var_action(object_no: int, var_no: int) -> bytes:
    values = [object_no, var_no]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("object/variable operands must fit in one byte")
    return bytes([0x4C, object_no, var_no])


def set_object_field_23_mode0_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x48, object_no])


def set_object_field_23_mode1_action(object_no: int, flag_no: int) -> bytes:
    values = [object_no, flag_no]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("object/flag operands must fit in one byte")
    return bytes([0x49, object_no, flag_no])


def set_object_field_23_mode2_action(object_no: int, flag_no: int) -> bytes:
    values = [object_no, flag_no]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("object/flag operands must fit in one byte")
    return bytes([0x4B, object_no, flag_no])


def set_object_field_23_mode3_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x4A, object_no])


def get_object_field_0e_action(object_no: int, var_no: int) -> bytes:
    values = [object_no, var_no]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("object/variable operands must fit in one byte")
    return bytes([0x32, object_no, var_no])


def clear_object_bit_0020_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x46, object_no])


def set_object_bit_0020_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x47, object_no])


def set_object_bit_0200_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x43, object_no])


def clear_object_bit_0200_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x44, object_no])


def set_object_bit_0002_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x58, object_no])


def clear_object_bit_0002_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x59, object_no])


def set_object_bit_0100_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x40, object_no])


def set_object_bit_0800_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x41, object_no])


def clear_object_bits_0900_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x42, object_no])


def clear_object_field_22_and_global_action(object_no: int) -> bytes:
    if not 0 <= object_no <= 0xFF:
        raise ValueError("object number must fit in one byte")
    return bytes([0x4E, object_no])


def set_global_0139_and_clear_object0_field_22_action() -> bytes:
    return bytes([0x84])


def picture_logic_payload(picture_no: int, scratch_var: int = SCRATCH_VAR) -> bytes:
    return logic_resource(load_show_picture_actions(picture_no, scratch_var) + self_loop())


def picture_view_logic_payload(
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority: int,
    control: int | None = None,
    scratch_var: int = SCRATCH_VAR,
    pre_overlay_actions: bytes = b"",
) -> bytes:
    values = [picture_no, view_no, group_no, frame_no, x, baseline_y, priority, scratch_var]
    if control is not None:
        values.append(control)
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("fixture operands must fit in one byte")
    if control is None:
        control = priority
    code = load_show_picture_actions(picture_no, scratch_var)
    code += pre_overlay_actions
    code += bytes(
        [
            0x1E,
            view_no,
            0x7A,
            view_no,
            group_no,
            frame_no,
            x,
            baseline_y,
            priority,
            control,
        ]
    )
    return logic_resource(code + self_loop())


def persistent_object_logic_payload(
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority_byte: int | None,
    object_no: int = 0,
    scratch_var: int = SCRATCH_VAR,
    pre_overlay_actions: bytes = b"",
    post_activate_actions: bytes = b"",
) -> bytes:
    values = [picture_no, view_no, group_no, frame_no, x, baseline_y, object_no, scratch_var]
    if priority_byte is not None:
        values.append(priority_byte)
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("fixture operands must fit in one byte")
    code = load_show_picture_actions(picture_no, scratch_var)
    code += pre_overlay_actions
    code += setup_persistent_object_actions(view_no, group_no, frame_no, x, baseline_y, priority_byte, object_no)
    code += post_activate_actions
    return logic_resource(code + self_loop())


def persistent_object_once_logic_payload(
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority_byte: int | None,
    object_no: int = 0,
    scratch_var: int = SCRATCH_VAR,
    pre_overlay_actions: bytes = b"",
    post_activate_actions: bytes = b"",
    per_cycle_actions: bytes = b"",
    per_cycle_until_flag: int | None = None,
    init_flag: int = DEFAULT_INIT_FLAG,
) -> bytes:
    values = [picture_no, view_no, group_no, frame_no, x, baseline_y, object_no, scratch_var, init_flag]
    if per_cycle_until_flag is not None:
        values.append(per_cycle_until_flag)
    if priority_byte is not None:
        values.append(priority_byte)
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("fixture operands must fit in one byte")
    setup = load_show_picture_actions(picture_no, scratch_var)
    setup += pre_overlay_actions
    setup += setup_persistent_object_actions(view_no, group_no, frame_no, x, baseline_y, priority_byte, object_no)
    setup += post_activate_actions
    code = if_then(not_flag_set_condition(init_flag), setup + set_flag_action(init_flag))
    if per_cycle_actions:
        if per_cycle_until_flag is None:
            code += per_cycle_actions
        else:
            code += if_then(not_flag_set_condition(per_cycle_until_flag), per_cycle_actions)
    return logic_resource(code + end_action())


def rebuild_priority_table_action(row: int) -> bytes:
    if not 0 <= row <= 0xFF:
        raise ValueError("priority-table row must fit in one byte")
    return bytes([0xAE, row])


def volume_record(payload: bytes, volume: int) -> bytes:
    if not 0 <= volume <= 0x0F:
        raise ValueError("volume number must fit in one nibble")
    return b"\x12\x34" + bytes([volume]) + u16le(len(payload)) + payload


def v3_volume_record(payload: bytes, volume: int, *, metadata: int | None = None) -> bytes:
    """Build an observed v3 direct/uncompressed volume record."""
    if not 0 <= volume <= 0x0F:
        raise ValueError("volume number must fit in one nibble")
    if metadata is None:
        metadata = volume
    if not 0 <= metadata <= 0x7F:
        raise ValueError("direct v3 metadata must fit in 7 bits")
    if metadata & 0x0F != volume:
        raise ValueError("direct v3 metadata low nibble must match directory volume")
    length = len(payload)
    return b"\x12\x34" + bytes([metadata]) + u16le(length) + u16le(length) + payload


def v3_picture_volume_record(payload: bytes, volume: int) -> bytes:
    """Build an observed v3 picture-nibble volume record from expanded picture bytes."""
    if not 0 <= volume <= 0x0F:
        raise ValueError("volume number must fit in one nibble")
    stored = encode_picture_nibbles(payload)
    return b"\x12\x34" + bytes([0x80 | volume]) + u16le(len(payload)) + u16le(len(stored)) + stored


def patch_logdir_entry_zero(logdir: bytes, volume: int, offset: int) -> bytes:
    return patch_dir_entry(logdir, 0, volume, offset)


def patch_dir_entry(directory: bytes, resource_no: int, volume: int, offset: int) -> bytes:
    if not 0 <= volume <= 0x0F:
        raise ValueError("volume number must fit in one nibble")
    if not 0 <= offset <= 0x0FFFFF:
        raise ValueError("resource offset must fit in 20 bits")
    entry_offset = resource_no * 3
    if entry_offset + 3 > len(directory):
        raise ValueError("resource number is outside directory")
    patched = bytearray(directory)
    patched[entry_offset] = (volume << 4) | ((offset >> 16) & 0x0F)
    patched[entry_offset + 1] = (offset >> 8) & 0xFF
    patched[entry_offset + 2] = offset & 0xFF
    return bytes(patched)


def patch_combined_dir_entry(
    directory: bytes,
    layout: ResourceDirectoryLayout,
    kind: str,
    resource_no: int,
    volume: int,
    offset: int,
) -> bytes:
    if layout.version != "v3_combined":
        raise ValueError("combined directory patching requires a v3 combined layout")
    if layout.section_offsets is None or layout.section_ends is None:
        raise ResourceFormatError("combined directory layout is missing section offsets")
    if kind not in layout.section_offsets:
        raise ValueError(f"unknown resource kind: {kind}")
    if not 0 <= volume <= 0x0F:
        raise ValueError("volume number must fit in one nibble")
    if not 0 <= offset <= 0x0FFFFF:
        raise ValueError("resource offset must fit in 20 bits")

    section_start = layout.section_offsets[kind]
    section_end = layout.section_ends[kind]
    entry_offset = section_start + resource_no * 3
    if entry_offset + 3 > section_end:
        raise ValueError("resource number is outside combined directory section")

    patched = bytearray(directory)
    patched[entry_offset] = (volume << 4) | ((offset >> 16) & 0x0F)
    patched[entry_offset + 1] = (offset >> 8) & 0xFF
    patched[entry_offset + 2] = offset & 0xFF
    return bytes(patched)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def _make_writable(path: Path) -> None:
    try:
        path.chmod(path.stat().st_mode | stat.S_IWUSR)
    except FileNotFoundError:
        return


def _remove_fixture_child(path: Path) -> None:
    _make_writable(path)
    if path.is_dir() and not path.is_symlink():
        for child in path.rglob("*"):
            _make_writable(child)
        shutil.rmtree(path)
    else:
        path.unlink()


def _validate_fixture_destination(destination: Path, source_game: Path | None = None) -> None:
    resolved_destination = _resolved(destination)
    resolved_games = _resolved(GAMES_ROOT)
    if _is_relative_to(resolved_destination, resolved_games):
        raise ValueError("fixture destination must not be inside games/; use build/ for generated fixtures")
    if source_game is not None:
        resolved_game = _resolved(source_game)
        if (
            resolved_destination == resolved_game
            or _is_relative_to(resolved_destination, resolved_game)
            or _is_relative_to(resolved_game, resolved_destination)
        ):
            raise ValueError("fixture destination must not modify the selected game directory")


def _prepare_fixture_destination(destination: Path, source_game: Path | None = None, preserve_ppm: bool = True) -> None:
    _validate_fixture_destination(destination, source_game)
    destination.mkdir(parents=True, exist_ok=True)
    for path in destination.iterdir():
        if preserve_ppm and path.is_file() and path.suffix.lower() == ".ppm":
            continue
        _remove_fixture_child(path)


def _copy_game_file(source: Path, destination: Path) -> None:
    if destination.exists():
        _remove_fixture_child(destination)
    shutil.copy2(source, destination)
    destination.chmod(destination.stat().st_mode | stat.S_IRUSR | stat.S_IWUSR)


def copy_game_tree(destination: Path, *, game_dir: Path | None = None, minimal_files: set[str] | None = None) -> None:
    source_game = Path(game_dir) if game_dir is not None else None
    _validate_fixture_destination(destination, source_game)
    if source_game is None:
        source_game = configured_game_dir()
    _prepare_fixture_destination(destination, source_game)
    for source in source_game.iterdir():
        if source.is_file():
            if minimal_files is not None and source.name.upper() not in minimal_files:
                continue
            _copy_game_file(source, destination / source.name)


def copy_sq2_tree(destination: Path, *, game_dir: Path | None = None) -> None:
    copy_game_tree(destination, game_dir=game_dir)


def copy_minimal_picture_tree(destination: Path, *, game_dir: Path | None = None) -> None:
    copy_game_tree(destination, game_dir=game_dir, minimal_files=MINIMAL_PICTURE_FIXTURE_FILES)


def build_v3_logic_fixture(
    logic_payload: bytes,
    destination: Path,
    *,
    logic_no: int = 0,
    game_dir: Path | None = None,
    volume: int | None = None,
) -> Path:
    copy_game_tree(destination, game_dir=game_dir)
    patch_v3_logic_resource(destination, logic_payload, logic_no=logic_no, volume=volume)
    return destination


def patch_v3_resource(
    destination: Path,
    kind: ResourceKind,
    resource_payload: bytes,
    *,
    resource_no: int = 0,
    volume: int | None = None,
    transform: str = "direct",
) -> Path:
    layout = detect_layout(destination)
    if layout.version != "v3_combined":
        raise ValueError("v3 resource patching requires a v3 combined-directory game")
    entries = read_directory_entries(destination, kind)
    if volume is None:
        if resource_no >= len(entries) or entries[resource_no] is None:
            raise ValueError(f"{kind} resource has no existing volume; pass an explicit volume")
        volume = entries[resource_no].volume

    target_volume = volume_path(destination, layout, volume)
    offset = target_volume.stat().st_size
    if transform == "direct":
        record = v3_volume_record(resource_payload, volume=volume)
    elif transform == "picture_nibble":
        if kind != "picture":
            raise ValueError("picture_nibble transform is only valid for picture resources")
        record = v3_picture_volume_record(resource_payload, volume=volume)
    else:
        raise ValueError(f"unsupported v3 fixture transform: {transform}")
    with target_volume.open("ab") as handle:
        handle.write(record)

    if layout.directory_path is None:
        raise ResourceFormatError("combined directory layout is missing a directory path")
    directory = layout.directory_path.read_bytes()
    layout.directory_path.write_bytes(
        patch_combined_dir_entry(directory, layout, kind, resource_no, volume=volume, offset=offset)
    )
    return destination


def patch_v3_logic_resource(
    destination: Path,
    logic_payload: bytes,
    *,
    logic_no: int = 0,
    volume: int | None = None,
) -> Path:
    return patch_v3_resource(destination, "logic", logic_payload, resource_no=logic_no, volume=volume)


def patch_v3_picture_resource(
    destination: Path,
    payload: bytes,
    *,
    picture_no: int = 0,
    volume: int | None = None,
) -> Path:
    return patch_v3_resource(
        destination,
        "picture",
        payload,
        resource_no=picture_no,
        volume=volume,
        transform="picture_nibble",
    )


def patch_v3_view_resource(
    destination: Path,
    payload: bytes,
    *,
    view_no: int = 0,
    volume: int | None = None,
) -> Path:
    return patch_v3_resource(destination, "view", payload, resource_no=view_no, volume=volume)


def build_v3_synthetic_picture_fixture(
    picture_payload: bytes,
    destination: Path,
    *,
    picture_no: int = 0,
    game_dir: Path | None = None,
    volume: int | None = None,
) -> Path:
    copy_game_tree(destination, game_dir=game_dir)
    patch_v3_logic_resource(destination, picture_logic_payload(picture_no), logic_no=0, volume=volume)
    patch_v3_picture_resource(destination, picture_payload, picture_no=picture_no, volume=volume)
    return destination


def build_v3_synthetic_picture_view_fixture(
    picture_payload: bytes,
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority: int,
    destination: Path,
    *,
    view_payload_bytes: bytes | None = None,
    game_dir: Path | None = None,
    volume: int | None = None,
    control: int | None = None,
    pre_overlay_actions: bytes = b"",
) -> Path:
    copy_game_tree(destination, game_dir=game_dir)
    logic_payload = picture_view_logic_payload(
        picture_no,
        view_no,
        group_no,
        frame_no,
        x,
        baseline_y,
        priority,
        control,
        pre_overlay_actions=pre_overlay_actions,
    )
    patch_v3_logic_resource(destination, logic_payload, logic_no=0, volume=volume)
    patch_v3_picture_resource(destination, picture_payload, picture_no=picture_no, volume=volume)
    if view_payload_bytes is not None:
        patch_v3_view_resource(destination, view_payload_bytes, view_no=view_no, volume=volume)
    return destination


def build_picture_fixture(picture_no: int, destination: Path) -> Path:
    copy_sq2_tree(destination)
    logic_payload = picture_logic_payload(picture_no)
    (destination / "VOL.3").write_bytes(volume_record(logic_payload, volume=3))
    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))
    return destination


def build_packed_picture_fixture(picture_no: int, destination: Path) -> Path:
    copy_minimal_picture_tree(destination)
    logic_record = volume_record(picture_logic_payload(picture_no), volume=3)
    picture_record_offset = len(logic_record)
    picture_record = volume_record(picture_payload(picture_no), volume=3)
    (destination / "VOL.3").write_bytes(logic_record + picture_record)
    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))
    picdir = (destination / "PICDIR").read_bytes()
    (destination / "PICDIR").write_bytes(patch_dir_entry(picdir, picture_no, volume=3, offset=picture_record_offset))
    return destination


def build_picture_carousel_fixture(
    picture_numbers: list[int],
    destination: Path,
    advance_key_words: list[int] | None = None,
) -> Path:
    if not picture_numbers:
        raise ValueError("picture carousel requires at least one picture")
    copy_minimal_picture_tree(destination)
    logic_record = volume_record(picture_carousel_logic_payload(picture_numbers, advance_key_words), volume=3)
    records = bytearray(logic_record)
    picdir = (destination / "PICDIR").read_bytes()
    for picture_no in picture_numbers:
        offset = len(records)
        records.extend(volume_record(picture_payload(picture_no), volume=3))
        picdir = patch_dir_entry(picdir, picture_no, volume=3, offset=offset)
    (destination / "VOL.3").write_bytes(bytes(records))
    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))
    (destination / "PICDIR").write_bytes(picdir)
    return destination


def build_picture_timed_carousel_fixture(
    picture_numbers: list[int],
    destination: Path,
    delay_cycles: int = 20,
    speed_value: int = 0,
) -> Path:
    if not picture_numbers:
        raise ValueError("picture timed carousel requires at least one picture")
    copy_minimal_picture_tree(destination)
    logic_record = volume_record(picture_timed_carousel_logic_payload(picture_numbers, delay_cycles, speed_value), volume=3)
    records = bytearray(logic_record)
    picdir = (destination / "PICDIR").read_bytes()
    for picture_no in picture_numbers:
        offset = len(records)
        records.extend(volume_record(picture_payload(picture_no), volume=3))
        picdir = patch_dir_entry(picdir, picture_no, volume=3, offset=offset)
    (destination / "VOL.3").write_bytes(bytes(records))
    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))
    (destination / "PICDIR").write_bytes(picdir)
    return destination


def build_view_timed_carousel_fixture(
    cases: list[tuple[int, int, int, int, int, int, int, int | None]],
    destination: Path,
    delay_cycles: int = 20,
    speed_value: int = 0,
) -> Path:
    if not cases:
        raise ValueError("view timed carousel requires at least one case")
    copy_minimal_picture_tree(destination)
    logic_record = volume_record(view_timed_carousel_logic_payload(cases, delay_cycles, speed_value), volume=3)
    records = bytearray(logic_record)
    picdir = (destination / "PICDIR").read_bytes()
    viewdir = (destination / "VIEWDIR").read_bytes()

    seen_pictures: set[int] = set()
    seen_views: set[int] = set()
    for picture_no, view_no, _group_no, _frame_no, _x, _baseline_y, _priority, _control in cases:
        if picture_no not in seen_pictures:
            offset = len(records)
            records.extend(volume_record(picture_payload(picture_no), volume=3))
            picdir = patch_dir_entry(picdir, picture_no, volume=3, offset=offset)
            seen_pictures.add(picture_no)
        if view_no not in seen_views:
            offset = len(records)
            records.extend(volume_record(view_payload(view_no), volume=3))
            viewdir = patch_dir_entry(viewdir, view_no, volume=3, offset=offset)
            seen_views.add(view_no)

    (destination / "VOL.3").write_bytes(bytes(records))
    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))
    (destination / "PICDIR").write_bytes(picdir)
    (destination / "VIEWDIR").write_bytes(viewdir)
    return destination


def build_picture_view_fixture(
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority: int,
    destination: Path,
    control: int | None = None,
) -> Path:
    copy_sq2_tree(destination)
    logic_payload = picture_view_logic_payload(
        picture_no,
        view_no,
        group_no,
        frame_no,
        x,
        baseline_y,
        priority,
        control,
    )
    (destination / "VOL.3").write_bytes(volume_record(logic_payload, volume=3))
    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))
    return destination


def build_synthetic_picture_fixture(
    picture_payload: bytes,
    destination: Path,
    picture_no: int = 0,
) -> Path:
    copy_sq2_tree(destination)
    logic_payload = picture_logic_payload(picture_no)
    logic_record = volume_record(logic_payload, volume=3)
    picture_offset = len(logic_record)
    picture_record = volume_record(picture_payload, volume=3)
    (destination / "VOL.3").write_bytes(logic_record + picture_record)

    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))

    picdir = (destination / "PICDIR").read_bytes()
    (destination / "PICDIR").write_bytes(
        patch_dir_entry(picdir, picture_no, volume=3, offset=picture_offset)
    )
    return destination


def build_synthetic_picture_view_fixture(
    picture_payload: bytes,
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority: int,
    destination: Path,
    control: int | None = None,
    pre_overlay_actions: bytes = b"",
) -> Path:
    copy_sq2_tree(destination)
    logic_payload = picture_view_logic_payload(
        picture_no,
        view_no,
        group_no,
        frame_no,
        x,
        baseline_y,
        priority,
        control,
        pre_overlay_actions=pre_overlay_actions,
    )
    logic_record = volume_record(logic_payload, volume=3)
    picture_offset = len(logic_record)
    picture_record = volume_record(picture_payload, volume=3)
    (destination / "VOL.3").write_bytes(logic_record + picture_record)

    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))

    picdir = (destination / "PICDIR").read_bytes()
    (destination / "PICDIR").write_bytes(
        patch_dir_entry(picdir, picture_no, volume=3, offset=picture_offset)
    )
    return destination


def build_synthetic_picture_persistent_object_fixture(
    picture_payload: bytes,
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority_byte: int | None,
    destination: Path,
    object_no: int = 0,
    pre_overlay_actions: bytes = b"",
    post_activate_actions: bytes = b"",
    per_cycle_actions: bytes = b"",
    per_cycle_until_flag: int | None = None,
    init_flag: int | None = None,
) -> Path:
    copy_sq2_tree(destination)
    if init_flag is None:
        logic_payload = persistent_object_logic_payload(
            picture_no,
            view_no,
            group_no,
            frame_no,
            x,
            baseline_y,
            priority_byte,
            object_no,
            pre_overlay_actions=pre_overlay_actions,
            post_activate_actions=post_activate_actions,
        )
    else:
        logic_payload = persistent_object_once_logic_payload(
            picture_no,
            view_no,
            group_no,
            frame_no,
            x,
            baseline_y,
            priority_byte,
            object_no,
            pre_overlay_actions=pre_overlay_actions,
            post_activate_actions=post_activate_actions,
            per_cycle_actions=per_cycle_actions,
            per_cycle_until_flag=per_cycle_until_flag,
            init_flag=init_flag,
        )
    logic_record = volume_record(logic_payload, volume=3)
    picture_offset = len(logic_record)
    picture_record = volume_record(picture_payload, volume=3)
    (destination / "VOL.3").write_bytes(logic_record + picture_record)

    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))

    picdir = (destination / "PICDIR").read_bytes()
    (destination / "PICDIR").write_bytes(
        patch_dir_entry(picdir, picture_no, volume=3, offset=picture_offset)
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    picture = subparsers.add_parser("picture")
    picture.add_argument("picture", type=int)
    picture.add_argument("--output", type=Path)

    picture_view = subparsers.add_parser("picture-view")
    picture_view.add_argument("picture", type=int)
    picture_view.add_argument("view", type=int)
    picture_view.add_argument("group", type=int)
    picture_view.add_argument("frame", type=int)
    picture_view.add_argument("x", type=int)
    picture_view.add_argument("baseline_y", type=int)
    picture_view.add_argument("priority", type=int)
    picture_view.add_argument("--control", type=int)
    picture_view.add_argument("--output", type=Path)

    synthetic_picture = subparsers.add_parser("synthetic-picture")
    synthetic_picture.add_argument("payload", type=Path)
    synthetic_picture.add_argument("--picture", type=int, default=0)
    synthetic_picture.add_argument("--output", type=Path)

    synthetic_picture_view = subparsers.add_parser("synthetic-picture-view")
    synthetic_picture_view.add_argument("payload", type=Path)
    synthetic_picture_view.add_argument("picture", type=int)
    synthetic_picture_view.add_argument("view", type=int)
    synthetic_picture_view.add_argument("group", type=int)
    synthetic_picture_view.add_argument("frame", type=int)
    synthetic_picture_view.add_argument("x", type=int)
    synthetic_picture_view.add_argument("baseline_y", type=int)
    synthetic_picture_view.add_argument("priority", type=int)
    synthetic_picture_view.add_argument("--control", type=int)
    synthetic_picture_view.add_argument("--output", type=Path)

    v3_logic = subparsers.add_parser("v3-logic")
    v3_logic.add_argument("payload", type=Path)
    v3_logic.add_argument("--logic", type=int, default=0)
    v3_logic.add_argument("--volume", type=int)
    v3_logic.add_argument("--game-dir", type=Path)
    v3_logic.add_argument("--output", type=Path)

    v3_synthetic_picture = subparsers.add_parser("v3-synthetic-picture")
    v3_synthetic_picture.add_argument("payload", type=Path)
    v3_synthetic_picture.add_argument("--picture", type=int, default=0)
    v3_synthetic_picture.add_argument("--volume", type=int)
    v3_synthetic_picture.add_argument("--game-dir", type=Path)
    v3_synthetic_picture.add_argument("--output", type=Path)

    v3_synthetic_picture_view = subparsers.add_parser("v3-synthetic-picture-view")
    v3_synthetic_picture_view.add_argument("payload", type=Path)
    v3_synthetic_picture_view.add_argument("picture", type=int)
    v3_synthetic_picture_view.add_argument("view", type=int)
    v3_synthetic_picture_view.add_argument("group", type=int)
    v3_synthetic_picture_view.add_argument("frame", type=int)
    v3_synthetic_picture_view.add_argument("x", type=int)
    v3_synthetic_picture_view.add_argument("baseline_y", type=int)
    v3_synthetic_picture_view.add_argument("priority", type=int)
    v3_synthetic_picture_view.add_argument("--view-payload", type=Path)
    v3_synthetic_picture_view.add_argument("--control", type=int)
    v3_synthetic_picture_view.add_argument("--volume", type=int)
    v3_synthetic_picture_view.add_argument("--game-dir", type=Path)
    v3_synthetic_picture_view.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.command == "picture":
        output = args.output or Path("build/qemu-fixtures") / f"picture_{args.picture:03d}"
        build_picture_fixture(args.picture, output)
        print(output)
    elif args.command == "picture-view":
        output = args.output or (
            Path("build/qemu-fixtures")
            / f"picture_{args.picture:03d}_view_{args.view:03d}_{args.group:02d}_{args.frame:02d}"
        )
        build_picture_view_fixture(
            args.picture,
            args.view,
            args.group,
            args.frame,
            args.x,
            args.baseline_y,
            args.priority,
            output,
            args.control,
        )
        print(output)
    elif args.command == "v3-logic":
        output = args.output or Path("build/qemu-fixtures") / f"v3_logic_{args.logic:03d}"
        build_v3_logic_fixture(
            args.payload.read_bytes(),
            output,
            logic_no=args.logic,
            game_dir=args.game_dir,
            volume=args.volume,
        )
        print(output)
    elif args.command == "v3-synthetic-picture":
        output = args.output or Path("build/qemu-fixtures") / f"v3_synthetic_picture_{args.picture:03d}"
        build_v3_synthetic_picture_fixture(
            args.payload.read_bytes(),
            output,
            picture_no=args.picture,
            game_dir=args.game_dir,
            volume=args.volume,
        )
        print(output)
    elif args.command == "v3-synthetic-picture-view":
        output = args.output or (
            Path("build/qemu-fixtures")
            / f"v3_synthetic_picture_{args.picture:03d}_view_{args.view:03d}_{args.group:02d}_{args.frame:02d}"
        )
        build_v3_synthetic_picture_view_fixture(
            args.payload.read_bytes(),
            args.picture,
            args.view,
            args.group,
            args.frame,
            args.x,
            args.baseline_y,
            args.priority,
            output,
            view_payload_bytes=args.view_payload.read_bytes() if args.view_payload is not None else None,
            game_dir=args.game_dir,
            volume=args.volume,
            control=args.control,
        )
        print(output)
    elif args.command == "synthetic-picture":
        output = args.output or Path("build/qemu-fixtures") / f"synthetic_picture_{args.picture:03d}"
        build_synthetic_picture_fixture(args.payload.read_bytes(), output, args.picture)
        print(output)
    elif args.command == "synthetic-picture-view":
        output = args.output or (
            Path("build/qemu-fixtures")
            / f"synthetic_picture_{args.picture:03d}_view_{args.view:03d}_{args.group:02d}_{args.frame:02d}"
        )
        build_synthetic_picture_view_fixture(
            args.payload.read_bytes(),
            args.picture,
            args.view,
            args.group,
            args.frame,
            args.x,
            args.baseline_y,
            args.priority,
            output,
            args.control,
        )
        print(output)


if __name__ == "__main__":
    main()
