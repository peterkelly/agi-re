#!/usr/bin/env python3
"""QEMU probes for core logic interpreter bytecode behavior."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from agi_graphics import HEIGHT, WIDTH, PictureRenderer, compose_frame_on_picture, render_view_frame
from compare_picture_capture import downsample_qemu_picture_nibbles
from ppm_tools import read_ppm
from qemu_fixture import (
    copy_sq2_tree,
    end_action,
    if_then,
    load_show_picture_actions,
    logic_resource,
    patch_dir_entry,
    patch_logdir_entry_zero,
    set_flag_action,
    self_loop,
    setup_transient_object_action,
    u16le,
    volume_record,
)
from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases


DEFAULT_FIXTURES = Path("build/logic-interpreter-probes/fixtures")
DEFAULT_RESULTS = Path("build/logic-interpreter-probes/batches")
DEFAULT_SNAPSHOT_RAW = Path("build/logic-interpreter-probes/snapshot/logic_interpreter.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/logic-interpreter-probes/snapshot/logic_interpreter.qcow2")


@dataclass(frozen=True)
class LogicInterpreterCase:
    case_id: str
    description: str
    code_hex: str
    picture_payload_hex: str
    picture_no: int
    expected_view_no: int
    expected_group_no: int
    expected_frame_no: int
    expected_x: int
    expected_baseline_y: int
    expected_priority: int
    extra_logics: list[dict[str, object]] | None = None
    messages: list[str] | None = None
    expected_extra_sprites: list[dict[str, int]] | None = None
    extra_pictures: list[dict[str, object]] | None = None
    expected_picture_payload_hex: str | None = None
    post_launch_keys: str = ""
    post_launch_wait: float = 0.0
    post_launch_key_delay: float = 0.03
    post_launch_after_text_wait: float = 0.0
    post_launch_key_names: list[str] | None = None
    agidata_patches: list[dict[str, object]] | None = None
    launch_command: str = "SIERRA"
    compare_view: bool = True
    expected_visual_rects: list[dict[str, int]] | None = None

    @property
    def code(self) -> bytes:
        return bytes.fromhex(self.code_hex)

    @property
    def picture_payload(self) -> bytes:
        return bytes.fromhex(self.picture_payload_hex)

    @property
    def expected_picture_payload(self) -> bytes:
        if self.expected_picture_payload_hex is None:
            return self.picture_payload
        return bytes.fromhex(self.expected_picture_payload_hex)


@dataclass(frozen=True)
class LogicComparison:
    case_id: str
    status: str
    mismatches: int | None
    total: int | None
    mismatch_bbox: tuple[int, int, int, int] | None
    samples: list[tuple[int, int, int, int]] | None
    error: str | None


@dataclass(frozen=True)
class LogicBatchResult:
    case_id: str
    status: str
    dos_dir: str
    capture: str
    elapsed_seconds: float
    comparison: LogicComparison | None
    error: str | None


def draw_view11_at(x: int) -> bytes:
    return setup_transient_object_action(11, 0, 0, x, 80, 15)


def byte_action(opcode: int, *operands: int) -> bytes:
    values = [opcode, *operands]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("logic action bytes must fit in one byte")
    return bytes(values)


def logic_patch(logic_no: int, code: bytes, messages: list[str] | None = None) -> dict[str, object]:
    return {"logic_no": logic_no, "code_hex": code.hex(), "messages": messages}


def base_code(body: bytes, picture_no: int = 0, preload_view_no: int | None = 11) -> bytes:
    code = load_show_picture_actions(picture_no)
    if preload_view_no is not None:
        code += bytes([0x1E, preload_view_no])
    return code + body + self_loop()


def end_code(body: bytes, picture_no: int = 0, preload_view_no: int | None = 11) -> bytes:
    code = load_show_picture_actions(picture_no)
    if preload_view_no is not None:
        code += bytes([0x1E, preload_view_no])
    return code + body + end_action()


def jump(delta_body: bytes) -> bytes:
    return bytes([0xFE]) + u16le(len(delta_body))


def var_eq_imm_condition(var_no: int, value: int) -> bytes:
    return bytes([0x01, var_no, value])


def always_false_condition() -> bytes:
    return bytes([0x00])


def var_eq_var_condition(left_var: int, right_var: int) -> bytes:
    return bytes([0x02, left_var, right_var])


def var_lt_imm_condition(var_no: int, value: int) -> bytes:
    return bytes([0x03, var_no, value])


def var_lt_var_condition(left_var: int, right_var: int) -> bytes:
    return bytes([0x04, left_var, right_var])


def var_gt_imm_condition(var_no: int, value: int) -> bytes:
    return bytes([0x05, var_no, value])


def var_gt_var_condition(left_var: int, right_var: int) -> bytes:
    return bytes([0x06, left_var, right_var])


def flag_set_condition(flag_no: int) -> bytes:
    return bytes([0x07, flag_no])


def flag_set_var_condition(var_no: int) -> bytes:
    return bytes([0x08, var_no])


def not_flag_set_condition(flag_no: int) -> bytes:
    return bytes([0xFD]) + flag_set_condition(flag_no)


def obj_table_room_ff_condition(index: int) -> bytes:
    return bytes([0x09, index])


def obj_table_room_eq_var_condition(index: int, var_no: int) -> bytes:
    return bytes([0x0A, index, var_no])


def status_byte_condition(index: int) -> bytes:
    return bytes([0x0C, index])


def raw_key_event_available_condition() -> bytes:
    return bytes([0x0D])


def object_rect_condition(opcode: int, object_no: int, left: int, top: int, right: int, bottom: int) -> bytes:
    return bytes([opcode, object_no, left, top, right, bottom])


def input_word_sequence_condition(*word_ids: int) -> bytes:
    out = bytearray([0x0E, len(word_ids)])
    for word_id in word_ids:
        out.extend(u16le(word_id))
    return bytes(out)


def string_slots_equal_condition(left_slot: int, right_slot: int) -> bytes:
    return bytes([0x0F, left_slot, right_slot])


def not_var_eq_imm_condition(var_no: int, value: int) -> bytes:
    return bytes([0xFD, 0x01, var_no, value])


def or_flags_condition(*flag_numbers: int) -> bytes:
    body = bytearray([0xFC])
    for flag_no in flag_numbers:
        body.extend([0x07, flag_no])
    body.append(0xFC)
    return bytes(body)


def all_conditions(*conditions: bytes) -> bytes:
    return b"".join(conditions)


def one_time_code(
    body: bytes,
    init_flag: int,
    picture_no: int = 0,
    preload_view_no: int | None = 11,
) -> bytes:
    setup = load_show_picture_actions(picture_no)
    if preload_view_no is not None:
        setup += bytes([0x1E, preload_view_no])
    return (
        if_then(not_flag_set_condition(init_flag), setup + body + set_flag_action(init_flag))
        + end_action()
    )


def one_time_with_per_cycle_code(
    setup_body: bytes,
    per_cycle_body: bytes,
    init_flag: int,
    picture_no: int = 0,
    preload_view_no: int | None = 11,
) -> bytes:
    setup = load_show_picture_actions(picture_no)
    if preload_view_no is not None:
        setup += bytes([0x1E, preload_view_no])
    return (
        if_then(not_flag_set_condition(init_flag), setup + setup_body + set_flag_action(init_flag))
        + per_cycle_body
        + end_action()
    )


def room_reentry_logic0_code(switch_action: bytes, init_flag: int = 120) -> bytes:
    return (
        if_then(not_flag_set_condition(init_flag), set_flag_action(init_flag) + switch_action)
        + byte_action(0x17, 0)
        + end_action()
    )


def validation_room_logic(expected_x: int, picture_no: int = 0, view_no: int = 11) -> bytes:
    return (
        if_then(
            flag_set_condition(5),
            load_show_picture_actions(picture_no)
            + bytes([0x1E, view_no])
            + draw_view11_at(expected_x),
        )
        + self_loop()
    )


def room_boundary_logic0_code(
    switch_action: bytes,
    boundary_selector: int,
    init_flag: int,
    pre_switch_setup: bytes,
) -> bytes:
    return (
        if_then(
            not_flag_set_condition(init_flag),
            pre_switch_setup
            + set_flag_action(init_flag)
            + assignn(2, boundary_selector)
            + switch_action,
        )
        + byte_action(0x17, 0)
        + end_action()
    )


def boundary_validation_room_logic(
    expected_object_x: int,
    expected_object_y: int,
    expected_draw_x: int,
    picture_no: int = 0,
    view_no: int = 11,
) -> bytes:
    return (
        if_then(
            flag_set_condition(5),
            load_show_picture_actions(picture_no)
            + bytes([0x1E, view_no])
            + byte_action(0x27, 0, 20, 21)
            + if_then(
                all_conditions(
                    var_eq_imm_condition(20, expected_object_x),
                    var_eq_imm_condition(21, expected_object_y),
                    var_eq_imm_condition(2, 0),
                ),
                draw_view11_at(expected_draw_x),
            ),
        )
        + self_loop()
    )


def previous_room_logic0_code(
    switch_action: bytes,
    previous_room: int,
    init_flag: int,
    boundary_selector: int = 7,
) -> bytes:
    return (
        if_then(
            not_flag_set_condition(init_flag),
            assignn(0, previous_room)
            + assignn(2, boundary_selector)
            + set_flag_action(init_flag)
            + switch_action,
        )
        + byte_action(0x17, 0)
        + end_action()
    )


def room_pre_switch_logic0_code(
    switch_action: bytes,
    pre_switch_setup: bytes,
    init_flag: int,
) -> bytes:
    return (
        if_then(
            not_flag_set_condition(init_flag),
            pre_switch_setup
            + set_flag_action(init_flag)
            + switch_action,
        )
        + byte_action(0x17, 0)
        + end_action()
    )


def previous_room_validation_logic(
    expected_previous_room: int,
    expected_draw_x: int,
    picture_no: int = 0,
    view_no: int = 11,
) -> bytes:
    return (
        if_then(
            flag_set_condition(5),
            load_show_picture_actions(picture_no)
            + bytes([0x1E, view_no])
            + if_then(
                all_conditions(
                    var_eq_imm_condition(0, 1),
                    var_eq_imm_condition(1, expected_previous_room),
                    var_eq_imm_condition(2, 0),
                ),
                draw_view11_at(expected_draw_x),
            ),
        )
        + self_loop()
    )


def display_mode_replay_validation_logic(
    expected_draw_x: int,
    init_flag: int,
    picture_no: int = 0,
    rollback_picture_no: int = 1,
    view_no: int = 11,
    draw_after_replay: bool = True,
) -> bytes:
    body = if_then(
        all_conditions(flag_set_condition(5), not_flag_set_condition(init_flag)),
        load_show_picture_actions(picture_no)
        + byte_action(0xAB)
        + load_show_picture_actions(rollback_picture_no)
        + byte_action(0xAC)
        + bytes([0x1E, view_no])
        + byte_action(0x8C)
        + set_flag_action(init_flag),
    )
    if draw_after_replay:
        body += draw_view11_at(expected_draw_x)
    return body + self_loop()


def display_mode_replay_flag7_validation_logic(
    expected_draw_x: int,
    init_flag: int,
    picture_no: int = 0,
    unrecorded_picture_no: int = 1,
    view_no: int = 11,
    draw_after_replay: bool = True,
) -> bytes:
    body = if_then(
        all_conditions(flag_set_condition(5), not_flag_set_condition(init_flag)),
        load_show_picture_actions(picture_no)
        + set_flag_action(7)
        + load_show_picture_actions(unrecorded_picture_no)
        + byte_action(0x0D, 7)
        + bytes([0x1E, view_no])
        + byte_action(0x8C)
        + set_flag_action(init_flag),
    )
    if draw_after_replay:
        body += draw_view11_at(expected_draw_x)
    return body + self_loop()


def alternating_row_picture_payload(even_color: int, odd_color: int) -> bytes:
    payload = bytearray()
    for y in range(HEIGHT):
        color = even_color if y % 2 == 0 else odd_color
        payload.extend([0xF0, color, 0xF6, 0x00, y, WIDTH - 1, y])
    payload.append(0xFF)
    return bytes(payload)


def room_switch_reentry_case(
    case_id: str,
    description: str,
    switch_action: bytes,
    expected_x: int,
    picture_no: int = 0,
    view_no: int = 11,
    init_flag: int = 120,
) -> LogicInterpreterCase:
    return LogicInterpreterCase(
        case_id=case_id,
        description=description,
        code_hex=room_reentry_logic0_code(switch_action, init_flag=init_flag).hex(),
        picture_payload_hex=b"\xff".hex(),
        picture_no=picture_no,
        expected_view_no=view_no,
        expected_group_no=0,
        expected_frame_no=0,
        expected_x=expected_x,
        expected_baseline_y=80,
        expected_priority=15,
        extra_logics=[
            logic_patch(
                1,
                validation_room_logic(
                    expected_x=expected_x,
                    picture_no=picture_no,
                    view_no=view_no,
                ),
            )
        ],
    )


def room_previous_state_case(
    case_id: str,
    description: str,
    switch_action: bytes,
    previous_room: int,
    expected_draw_x: int,
    init_flag: int,
) -> LogicInterpreterCase:
    return LogicInterpreterCase(
        case_id=case_id,
        description=description,
        code_hex=previous_room_logic0_code(
            switch_action,
            previous_room=previous_room,
            init_flag=init_flag,
        ).hex(),
        picture_payload_hex=b"\xff".hex(),
        picture_no=0,
        expected_view_no=11,
        expected_group_no=0,
        expected_frame_no=0,
        expected_x=expected_draw_x,
        expected_baseline_y=80,
        expected_priority=15,
        extra_logics=[
            logic_patch(
                1,
                previous_room_validation_logic(
                    expected_previous_room=previous_room,
                    expected_draw_x=expected_draw_x,
                ),
            )
        ],
    )


def room_pre_switch_object_reset_case(
    case_id: str,
    description: str,
    switch_action: bytes,
    expected_draw_x: int,
    init_flag: int,
) -> LogicInterpreterCase:
    return LogicInterpreterCase(
        case_id=case_id,
        description=description,
        code_hex=room_pre_switch_logic0_code(
            switch_action,
            pre_switch_setup=load_show_picture_actions(0)
            + bytes([0x1E, 11])
            + setup_object_for_view11(10, x=20, baseline_y=80)
            + byte_action(0x23, 10),
            init_flag=init_flag,
        ).hex(),
        picture_payload_hex=b"\xff".hex(),
        picture_no=0,
        expected_view_no=11,
        expected_group_no=0,
        expected_frame_no=0,
        expected_x=expected_draw_x,
        expected_baseline_y=80,
        expected_priority=15,
        extra_logics=[
            logic_patch(
                1,
                validation_room_logic(expected_x=expected_draw_x),
            )
        ],
    )


def room_boundary_case(
    case_id: str,
    description: str,
    boundary_selector: int,
    expected_object_x: int,
    expected_object_y: int,
    expected_draw_x: int,
    init_flag: int,
    switch_action: bytes | None = None,
) -> LogicInterpreterCase:
    if switch_action is None:
        switch_action = byte_action(0x12, 1)
    return LogicInterpreterCase(
        case_id=case_id,
        description=description,
        code_hex=room_boundary_logic0_code(
            switch_action,
            boundary_selector=boundary_selector,
            init_flag=init_flag,
            pre_switch_setup=bytes([0x1E, 11]) + setup_object_for_view11(0, x=44, baseline_y=80),
        ).hex(),
        picture_payload_hex=b"\xff".hex(),
        picture_no=0,
        expected_view_no=11,
        expected_group_no=0,
        expected_frame_no=0,
        expected_x=expected_draw_x,
        expected_baseline_y=80,
        expected_priority=15,
        extra_logics=[
            logic_patch(
                1,
                boundary_validation_room_logic(
                    expected_object_x=expected_object_x,
                    expected_object_y=expected_object_y,
                    expected_draw_x=expected_draw_x,
                ),
            )
        ],
    )


def _case(case_id: str, description: str, body: bytes, expected_x: int) -> LogicInterpreterCase:
    return _custom_case(case_id, description, body, expected_x)


def _custom_case(
    case_id: str,
    description: str,
    body: bytes,
    expected_x: int,
    *,
    expected_group_no: int = 0,
    expected_frame_no: int = 0,
    expected_baseline_y: int = 80,
    extra_logics: list[dict[str, object]] | None = None,
    messages: list[str] | None = None,
    expected_extra_sprites: list[dict[str, int]] | None = None,
    preload_view_no: int | None = 11,
    picture_payload: bytes = b"\xff",
    expected_priority: int = 15,
    expected_view_no: int = 11,
    terminate_with_end: bool = False,
    init_once_flag: int | None = None,
    per_cycle_body: bytes = b"",
    extra_pictures: list[dict[str, object]] | None = None,
    expected_picture_payload: bytes | None = None,
    post_launch_keys: str = "",
    post_launch_wait: float = 0.0,
    post_launch_key_delay: float = 0.03,
    post_launch_after_text_wait: float = 0.0,
    post_launch_key_names: list[str] | None = None,
    agidata_patches: list[dict[str, object]] | None = None,
    expected_visual_rects: list[dict[str, int]] | None = None,
) -> LogicInterpreterCase:
    if init_once_flag is not None and per_cycle_body:
        code = one_time_with_per_cycle_code(
            body,
            per_cycle_body,
            init_once_flag,
            preload_view_no=preload_view_no,
        )
    elif init_once_flag is not None:
        code = one_time_code(body, init_once_flag, preload_view_no=preload_view_no)
    else:
        code = (
            end_code(body, preload_view_no=preload_view_no)
            if terminate_with_end
            else base_code(body, preload_view_no=preload_view_no)
        )
    return LogicInterpreterCase(
        case_id,
        description,
        code.hex(),
        picture_payload.hex(),
        0,
        expected_view_no,
        expected_group_no,
        expected_frame_no,
        expected_x,
        expected_baseline_y,
        expected_priority,
        extra_logics,
        messages,
        expected_extra_sprites,
        extra_pictures,
        None if expected_picture_payload is None else expected_picture_payload.hex(),
        post_launch_keys,
        post_launch_wait,
        post_launch_key_delay,
        post_launch_after_text_wait,
        post_launch_key_names,
        agidata_patches,
        "SIERRA",
        True,
        expected_visual_rects,
    )


def _draw_if_case(
    case_id: str,
    description: str,
    setup: bytes,
    condition: bytes,
    expected_x: int = 50,
    *,
    expected_group_no: int = 0,
    expected_frame_no: int = 0,
    expected_baseline_y: int = 80,
    extra_logics: list[dict[str, object]] | None = None,
    messages: list[str] | None = None,
    post_launch_keys: str = "",
    post_launch_wait: float = 0.0,
    post_launch_key_delay: float = 0.03,
    post_launch_after_text_wait: float = 0.0,
    post_launch_key_names: list[str] | None = None,
    agidata_patches: list[dict[str, object]] | None = None,
) -> LogicInterpreterCase:
    return _custom_case(
        case_id,
        description,
        setup + if_then(condition, draw_view11_at(expected_x)),
        expected_x,
        expected_group_no=expected_group_no,
        expected_frame_no=expected_frame_no,
        expected_baseline_y=expected_baseline_y,
        extra_logics=extra_logics,
        messages=messages,
        post_launch_keys=post_launch_keys,
        post_launch_wait=post_launch_wait,
        post_launch_key_delay=post_launch_key_delay,
        post_launch_after_text_wait=post_launch_after_text_wait,
        post_launch_key_names=post_launch_key_names,
        agidata_patches=agidata_patches,
    )


def assignn(var_no: int, value: int) -> bytes:
    return byte_action(0x03, var_no, value)


def setup_object_for_view11(object_no: int, x: int = 42, baseline_y: int = 80, group_no: int = 0, frame_no: int = 0) -> bytes:
    return setup_object_for_view(11, object_no, x, baseline_y, group_no, frame_no)


def setup_object_for_view(
    view_no: int,
    object_no: int,
    x: int = 42,
    baseline_y: int = 80,
    group_no: int = 0,
    frame_no: int = 0,
) -> bytes:
    return (
        byte_action(0x21, object_no)
        + byte_action(0x29, object_no, view_no)
        + byte_action(0x2B, object_no, group_no)
        + byte_action(0x2F, object_no, frame_no)
        + byte_action(0x25, object_no, x, baseline_y)
    )


def setup_object_10_for_view11() -> bytes:
    return setup_object_for_view11(10)


def object_bitfield_smoke_actions() -> bytes:
    return (
        setup_object_10_for_view11()
        + assignn(1, 9)
        + assignn(2, 11)
        + byte_action(0x36, 10, 12)
        + byte_action(0x38, 10)
        + byte_action(0x3B, 10)
        + byte_action(0x3A, 10)
        + byte_action(0x3C, 10)
        + byte_action(0x3D, 10)
        + byte_action(0x3E, 10)
        + byte_action(0x40, 10)
        + byte_action(0x41, 10)
        + byte_action(0x42, 10)
        + byte_action(0x43, 10)
        + byte_action(0x44, 10)
        + byte_action(0x47, 10)
        + byte_action(0x46, 10)
        + byte_action(0x4C, 10, 1)
        + byte_action(0x4E, 10)
        + byte_action(0x58, 10)
        + byte_action(0x59, 10)
    )


def object_10_rect_setup() -> bytes:
    return setup_object_10_for_view11()


def base_cases() -> list[LogicInterpreterCase]:
    skipped = draw_view11_at(20)
    return [
        _case(
            "jump_skips_first_draw",
            "Structural opcode 0xfe skips over the first draw action.",
            jump(skipped) + skipped + draw_view11_at(50),
            50,
        ),
        _case(
            "if_false_skips_then_draw",
            "A false condition skips the then body using the encoded false delta.",
            if_then(var_eq_imm_condition(1, 2), draw_view11_at(20)) + draw_view11_at(50),
            50,
        ),
        _case(
            "not_condition_runs_then_draw",
            "The 0xfd marker inverts the following false condition so the body runs.",
            if_then(not_var_eq_imm_condition(1, 2), draw_view11_at(50)),
            50,
        ),
        _case(
            "or_group_true_runs_then_draw",
            "An OR group runs the body when any contained condition is true.",
            set_flag_action(56) + if_then(or_flags_condition(64, 56), draw_view11_at(50)),
            50,
        ),
        _case(
            "always_false_condition_skips_then_draw",
            "Condition opcode 0x00 is false and skips its then body.",
            if_then(always_false_condition(), draw_view11_at(20)) + draw_view11_at(50),
            50,
        ),
        _draw_if_case(
            "var_inc_reaches_expected_value",
            "Action 0x01 increments a byte variable below 0xff.",
            assignn(1, 10) + byte_action(0x01, 1),
            var_eq_imm_condition(1, 11),
        ),
        _draw_if_case(
            "var_inc_saturates_at_ff",
            "Action 0x01 leaves a byte variable unchanged at 0xff.",
            assignn(1, 0xFF) + byte_action(0x01, 1),
            var_eq_imm_condition(1, 0xFF),
        ),
        _draw_if_case(
            "var_dec_reaches_expected_value",
            "Action 0x02 decrements a byte variable above zero.",
            assignn(1, 10) + byte_action(0x02, 1),
            var_eq_imm_condition(1, 9),
        ),
        _draw_if_case(
            "var_dec_saturates_at_zero",
            "Action 0x02 leaves a byte variable unchanged at zero.",
            assignn(1, 0) + byte_action(0x02, 1),
            var_eq_imm_condition(1, 0),
        ),
        _draw_if_case(
            "assignv_copies_source_variable",
            "Action 0x04 copies one variable byte into another.",
            assignn(1, 23) + byte_action(0x04, 2, 1),
            var_eq_imm_condition(2, 23),
        ),
        _draw_if_case(
            "addn_uses_low_byte_arithmetic",
            "Action 0x05 adds an immediate byte to a variable.",
            assignn(1, 10) + byte_action(0x05, 1, 5),
            var_eq_imm_condition(1, 15),
        ),
        _draw_if_case(
            "addv_uses_source_variable",
            "Action 0x06 adds a source variable byte to a destination variable.",
            assignn(1, 10) + assignn(2, 5) + byte_action(0x06, 1, 2),
            var_eq_imm_condition(1, 15),
        ),
        _draw_if_case(
            "subn_uses_low_byte_arithmetic",
            "Action 0x07 subtracts an immediate byte from a variable.",
            assignn(1, 10) + byte_action(0x07, 1, 3),
            var_eq_imm_condition(1, 7),
        ),
        _draw_if_case(
            "subv_uses_source_variable",
            "Action 0x08 subtracts a source variable byte from a destination variable.",
            assignn(1, 10) + assignn(2, 3) + byte_action(0x08, 1, 2),
            var_eq_imm_condition(1, 7),
        ),
        _draw_if_case(
            "indirect_assignv_writes_indexed_destination",
            "Action 0x09 stores var[arg1] into var[var[arg0]].",
            assignn(1, 8) + assignn(2, 55) + assignn(8, 0) + byte_action(0x09, 1, 2),
            var_eq_imm_condition(8, 55),
        ),
        _draw_if_case(
            "assign_indirectv_reads_indexed_source",
            "Action 0x0a stores var[var[arg1]] into var[arg0].",
            assignn(1, 0) + assignn(2, 8) + assignn(8, 66) + byte_action(0x0A, 1, 2),
            var_eq_imm_condition(1, 66),
        ),
        _draw_if_case(
            "indirect_assignn_writes_immediate_to_indexed_destination",
            "Action 0x0b stores an immediate byte into var[var[arg0]].",
            assignn(1, 8) + assignn(8, 0) + byte_action(0x0B, 1, 77),
            var_eq_imm_condition(8, 77),
        ),
        _draw_if_case(
            "muln_keeps_low_product_byte",
            "Action 0xa5 multiplies a variable by an immediate and keeps the low byte.",
            assignn(1, 20) + byte_action(0xA5, 1, 13),
            var_eq_imm_condition(1, 4),
        ),
        _draw_if_case(
            "mulv_keeps_low_product_byte",
            "Action 0xa6 multiplies by a source variable and keeps the low byte.",
            assignn(1, 20) + assignn(2, 13) + byte_action(0xA6, 1, 2),
            var_eq_imm_condition(1, 4),
        ),
        _draw_if_case(
            "divn_stores_quotient_byte",
            "Action 0xa7 divides a variable by an immediate byte.",
            assignn(1, 21) + byte_action(0xA7, 1, 5),
            var_eq_imm_condition(1, 4),
        ),
        _draw_if_case(
            "divv_stores_quotient_byte",
            "Action 0xa8 divides a variable by a source variable byte.",
            assignn(1, 21) + assignn(2, 5) + byte_action(0xA8, 1, 2),
            var_eq_imm_condition(1, 4),
        ),
        _draw_if_case(
            "flag_set_clear_toggle_actions",
            "Actions 0x0c, 0x0d, and 0x0e set, clear, and toggle flag bits.",
            set_flag_action(56) + byte_action(0x0D, 56) + byte_action(0x0E, 56),
            flag_set_condition(56),
        ),
        _draw_if_case(
            "flag_var_actions_and_condition",
            "Actions 0x0f..0x11 and condition 0x08 use a variable-selected flag number.",
            assignn(1, 56)
            + byte_action(0x0F, 1)
            + byte_action(0x10, 1)
            + byte_action(0x11, 1),
            flag_set_var_condition(1),
        ),
        _draw_if_case(
            "var_comparison_conditions_all_true",
            "Condition opcodes 0x02..0x06 compare variable bytes against variables and immediates.",
            assignn(1, 7) + assignn(2, 7) + assignn(3, 9) + assignn(4, 5),
            all_conditions(
                var_eq_var_condition(1, 2),
                var_lt_imm_condition(1, 8),
                var_lt_var_condition(1, 3),
                var_gt_imm_condition(1, 6),
                var_gt_var_condition(1, 4),
            ),
        ),
        _draw_if_case(
            "object_position_getter_observes_setter",
            "Actions 0x25 and 0x27 set object position bytes and read them into variables.",
            byte_action(0x25, 10, 42, 80) + byte_action(0x27, 10, 1, 2),
            all_conditions(var_eq_imm_condition(1, 42), var_eq_imm_condition(2, 80)),
        ),
        _draw_if_case(
            "object_add_pos_from_vars_getter_observes_sum",
            "Action 0x28 adds variable-sourced positive deltas to object position bytes.",
            byte_action(0x25, 10, 30, 70)
            + assignn(1, 5)
            + assignn(2, 7)
            + byte_action(0x28, 10, 1, 2)
            + byte_action(0x27, 10, 3, 4),
            all_conditions(var_eq_imm_condition(3, 35), var_eq_imm_condition(4, 77)),
        ),
        _draw_if_case(
            "object_field_24_getter_observes_setter",
            "Actions 0x36 and 0x39 set object byte +0x24 and read it into a variable.",
            byte_action(0x36, 10, 12) + byte_action(0x39, 10, 1),
            var_eq_imm_condition(1, 12),
        ),
        _draw_if_case(
            "object_field_21_getter_observes_setter",
            "Actions 0x56 and 0x57 set object byte +0x21 from a variable and read it back.",
            assignn(1, 8) + byte_action(0x56, 10, 1) + byte_action(0x57, 10, 2),
            var_eq_imm_condition(2, 8),
        ),
        _draw_if_case(
            "random_equal_bounds_stores_bound",
            "Action 0x82 stores the only possible value when low and high bounds match.",
            byte_action(0x82, 7, 7, 1),
            var_eq_imm_condition(1, 7),
        ),
        _custom_case(
            "noop_7f_continues_to_draw",
            "Action 0x7f returns without changing state and following bytecode still executes.",
            byte_action(0x7F) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "noop_9b_consumes_two_operands_then_draws",
            "Action 0x9b consumes two operand bytes and following bytecode still executes.",
            byte_action(0x9B, 0x12, 0x34) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "noop_af_runtime_consumes_no_operand",
            "Action 0xaf uses the no-op handler at runtime, so the following opcode byte executes.",
            byte_action(0xAF) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "call_logic_draws_from_called_logic",
            "Action 0x16 switches to another logic resource and executes its bytecode.",
            byte_action(0x16, 1),
            50,
            extra_logics=[logic_patch(1, draw_view11_at(50) + self_loop())],
        ),
        _custom_case(
            "load_logic_then_call_logic_draws",
            "Action 0x14 loads a logic resource that action 0x16 can subsequently call.",
            byte_action(0x14, 1) + byte_action(0x16, 1),
            50,
            extra_logics=[logic_patch(1, draw_view11_at(50) + self_loop())],
        ),
        _custom_case(
            "load_logic_var_then_call_logic_draws",
            "Action 0x15 loads the logic resource selected by a variable before action 0x16 calls it.",
            assignn(1, 1) + byte_action(0x15, 1) + byte_action(0x16, 1),
            50,
            extra_logics=[logic_patch(1, draw_view11_at(50) + self_loop())],
        ),
        _custom_case(
            "call_logic_var_draws_selected_logic",
            "Action 0x17 reads the target logic number from a byte variable.",
            assignn(1, 2) + byte_action(0x17, 1),
            50,
            extra_logics=[logic_patch(2, draw_view11_at(50) + self_loop())],
        ),
        room_switch_reentry_case(
            "switch_room_reentry_dispatches_current_room",
            "Action 0x12 returns through the main-cycle re-entry path before logic 0 dispatches current-room logic.",
            byte_action(0x12, 1),
            expected_x=50,
        ),
        room_switch_reentry_case(
            "switch_room_v_reentry_dispatches_current_room",
            "Action 0x13 reads the destination room from a variable before the same re-entry dispatch path.",
            assignn(10, 1) + byte_action(0x13, 10),
            expected_x=58,
            init_flag=121,
        ),
        room_previous_state_case(
            "switch_room_sets_current_previous_and_clears_boundary",
            "Action 0x12 copies the old current room into v1, writes the destination to v0, and clears v2.",
            byte_action(0x12, 1),
            previous_room=37,
            expected_draw_x=98,
            init_flag=126,
        ),
        room_previous_state_case(
            "switch_room_v_sets_current_previous_and_clears_boundary",
            "Action 0x13 copies the old current room into v1, writes the variable-selected destination to v0, and clears v2.",
            assignn(10, 1) + byte_action(0x13, 10),
            previous_room=42,
            expected_draw_x=106,
            init_flag=127,
        ),
        room_pre_switch_object_reset_case(
            "switch_room_removes_preexisting_persistent_object",
            "Action 0x12 clears a persistent object activated before the room switch so it is absent in the destination room.",
            byte_action(0x12, 1),
            expected_draw_x=52,
            init_flag=132,
        ),
        room_pre_switch_object_reset_case(
            "switch_room_v_removes_preexisting_persistent_object",
            "Action 0x13 clears a persistent object activated before the room switch so it is absent in the destination room.",
            assignn(10, 1) + byte_action(0x13, 10),
            expected_draw_x=60,
            init_flag=133,
        ),
        room_boundary_case(
            "switch_room_boundary_1_sets_object0_bottom_y",
            "Boundary selector v2=1 sets object 0 Y to the bottom-entry value and clears v2.",
            boundary_selector=1,
            expected_object_x=44,
            expected_object_y=0xA7,
            expected_draw_x=66,
            init_flag=122,
        ),
        room_boundary_case(
            "switch_room_boundary_2_sets_object0_left_x",
            "Boundary selector v2=2 sets object 0 X to the left-entry value and clears v2.",
            boundary_selector=2,
            expected_object_x=0,
            expected_object_y=80,
            expected_draw_x=74,
            init_flag=123,
        ),
        room_boundary_case(
            "switch_room_boundary_3_sets_object0_top_y",
            "Boundary selector v2=3 sets object 0 Y to the top-entry value and clears v2.",
            boundary_selector=3,
            expected_object_x=44,
            expected_object_y=0x25,
            expected_draw_x=82,
            init_flag=124,
        ),
        room_boundary_case(
            "switch_room_boundary_4_sets_object0_right_x",
            "Boundary selector v2=4 sets object 0 X to 0xa0 minus object width and clears v2.",
            boundary_selector=4,
            expected_object_x=140,
            expected_object_y=80,
            expected_draw_x=90,
            init_flag=125,
        ),
        room_boundary_case(
            "switch_room_v_boundary_1_sets_object0_bottom_y",
            "Variable-selected room switch with v2=1 sets object 0 Y to the bottom-entry value and clears v2.",
            boundary_selector=1,
            expected_object_x=44,
            expected_object_y=0xA7,
            expected_draw_x=108,
            init_flag=128,
            switch_action=assignn(10, 1) + byte_action(0x13, 10),
        ),
        room_boundary_case(
            "switch_room_v_boundary_2_sets_object0_left_x",
            "Variable-selected room switch with v2=2 sets object 0 X to the left-entry value and clears v2.",
            boundary_selector=2,
            expected_object_x=0,
            expected_object_y=80,
            expected_draw_x=116,
            init_flag=129,
            switch_action=assignn(10, 1) + byte_action(0x13, 10),
        ),
        room_boundary_case(
            "switch_room_v_boundary_3_sets_object0_top_y",
            "Variable-selected room switch with v2=3 sets object 0 Y to the top-entry value and clears v2.",
            boundary_selector=3,
            expected_object_x=44,
            expected_object_y=0x25,
            expected_draw_x=124,
            init_flag=130,
            switch_action=assignn(10, 1) + byte_action(0x13, 10),
        ),
        room_boundary_case(
            "switch_room_v_boundary_4_sets_object0_right_x",
            "Variable-selected room switch with v2=4 sets object 0 X to 0xa0 minus object width and clears v2.",
            boundary_selector=4,
            expected_object_x=140,
            expected_object_y=80,
            expected_draw_x=132,
            init_flag=131,
            switch_action=assignn(10, 1) + byte_action(0x13, 10),
        ),
        _draw_if_case(
            "save_restore_resume_actions_continue_to_draw",
            "Actions 0x91 and 0x92 execute without preventing subsequent bytecode.",
            byte_action(0x91) + byte_action(0x92),
            bytes([0xFD]) + always_false_condition(),
        ),
        _draw_if_case(
            "set_object_pos_var_getter_observes_values",
            "Action 0x26 sets object position bytes from variables and 0x27 reads them back.",
            assignn(1, 42) + assignn(2, 80) + byte_action(0x26, 10, 1, 2) + byte_action(0x27, 10, 3, 4),
            all_conditions(var_eq_imm_condition(3, 42), var_eq_imm_condition(4, 80)),
        ),
        _custom_case(
            "var_resource_group_frame_setup_draws_persistent_object",
            "Actions 0x2a, 0x2c, and 0x30 select object view/group/frame from variables.",
            assignn(1, 11)
            + assignn(2, 1)
            + assignn(3, 1)
            + byte_action(0x21, 10)
            + byte_action(0x2A, 10, 1)
            + byte_action(0x2C, 10, 2)
            + byte_action(0x30, 10, 3)
            + byte_action(0x25, 10, 50, 80)
            + byte_action(0x23, 10),
            50,
            expected_group_no=1,
            expected_frame_no=1,
        ),
        _custom_case(
            "setup_transient_object_var_draws_selected_cel",
            "Action 0x7b reads all transient object operands from variables.",
            assignn(1, 11)
            + assignn(2, 1)
            + assignn(3, 1)
            + assignn(4, 50)
            + assignn(5, 80)
            + assignn(6, 15)
            + assignn(7, 15)
            + byte_action(0x7B, 1, 2, 3, 4, 5, 6, 7),
            50,
            expected_group_no=1,
            expected_frame_no=1,
        ),
        _custom_case(
            "load_view_var_allows_following_draw",
            "Action 0x1f loads the view resource selected by a variable before a following draw.",
            assignn(1, 11) + byte_action(0x1F, 1) + draw_view11_at(50),
            50,
            preload_view_no=None,
        ),
        _custom_case(
            "overlay_picture_var_composes_extra_picture",
            "Action 0x1c overlays an already loaded variable-selected picture resource; action 0x1a makes the composed picture visible.",
            assignn(1, 1) + byte_action(0x18, 1) + byte_action(0x1C, 1) + byte_action(0x1A) + draw_view11_at(50),
            50,
            picture_payload=bytes([0xF0, 0x06, 0xF8, 0x00, 0x00, 0xFF]),
            extra_pictures=[
                {
                    "picture_no": 1,
                    "payload_hex": bytes([0xF0, 0x04, 0xF6, 0x10, 0x10, 0x50, 0x10, 0xFF]).hex(),
                }
            ],
            expected_picture_payload=bytes(
                [
                    0xF0,
                    0x06,
                    0xF8,
                    0x00,
                    0x00,
                    0xF0,
                    0x04,
                    0xF6,
                    0x10,
                    0x10,
                    0x50,
                    0x10,
                    0xFF,
                ]
            ),
        ),
        _custom_case(
            "discard_picture_var_allows_reload_and_overlay",
            "Action 0x1b discards a loaded variable-selected picture resource; loading it again allows a later overlay.",
            assignn(1, 1)
            + byte_action(0x18, 1)
            + byte_action(0x1B, 1)
            + byte_action(0x18, 1)
            + byte_action(0x1C, 1)
            + byte_action(0x1A)
            + draw_view11_at(50),
            50,
            picture_payload=bytes([0xF0, 0x06, 0xF8, 0x00, 0x00, 0xFF]),
            extra_pictures=[
                {
                    "picture_no": 1,
                    "payload_hex": bytes([0xF0, 0x04, 0xF6, 0x10, 0x10, 0x50, 0x10, 0xFF]).hex(),
                }
            ],
            expected_picture_payload=bytes(
                [
                    0xF0,
                    0x06,
                    0xF8,
                    0x00,
                    0x00,
                    0xF0,
                    0x04,
                    0xF6,
                    0x10,
                    0x10,
                    0x50,
                    0x10,
                    0xFF,
                ]
            ),
        ),
        _custom_case(
            "discard_view_allows_reload_and_draw",
            "Action 0x20 discards a loaded view resource; reloading the same view allows a following draw.",
            byte_action(0x20, 11) + byte_action(0x1E, 11) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "discard_view_var_allows_reload_and_draw",
            "Action 0x99 discards the view resource selected by a variable; reloading the same view allows a following draw.",
            assignn(1, 11) + byte_action(0x99, 1) + byte_action(0x1E, 11) + draw_view11_at(50),
            50,
        ),
        _draw_if_case(
            "move_object_to_var_sets_flag_at_existing_target",
            "Action 0x52 reads target and step operands from variables and completes immediately when already at target.",
            setup_object_10_for_view11()
            + assignn(1, 42)
            + assignn(2, 80)
            + assignn(3, 5)
            + byte_action(0x52, 10, 1, 2, 3, 56),
            flag_set_condition(56),
        ),
        _draw_if_case(
            "object_left_rect_condition_true",
            "Condition 0x0b tests an object's left/baseline point against a rectangle.",
            object_10_rect_setup(),
            object_rect_condition(0x0B, 10, 0, 0, 100, 100),
        ),
        _draw_if_case(
            "object_width_rect_condition_true",
            "Condition 0x10 tests an object's width/baseline extent against a rectangle.",
            object_10_rect_setup(),
            object_rect_condition(0x10, 10, 0, 0, 100, 100),
        ),
        _draw_if_case(
            "object_center_rect_condition_true",
            "Condition 0x11 tests an object's center/baseline point against a rectangle.",
            object_10_rect_setup(),
            object_rect_condition(0x11, 10, 0, 0, 100, 100),
        ),
        _draw_if_case(
            "object_right_rect_condition_true",
            "Condition 0x12 tests an object's right/baseline point against a rectangle.",
            object_10_rect_setup(),
            object_rect_condition(0x12, 10, 0, 0, 100, 100),
        ),
        _custom_case(
            "set_string_from_message_equal_normalized",
            "Action 0x72 copies messages into string slots and condition 0x0f compares normalized text.",
            byte_action(0x72, 0, 1)
            + byte_action(0x72, 1, 2)
            + if_then(string_slots_equal_condition(0, 1), draw_view11_at(50)),
            50,
            messages=["HELLO!", "hello"],
        ),
        _custom_case(
            "parse_string_slot_sets_input_word_sequence",
            "Action 0x75 parses a message-filled string slot for condition 0x0e.",
            byte_action(0x72, 0, 1)
            + byte_action(0x75, 0)
            + if_then(input_word_sequence_condition(0x0002), draw_view11_at(50)),
            50,
            messages=["look"],
        ),
        _custom_case(
            "display_message_then_ack_continues_to_draw",
            "Action 0x65 displays a message, accepts Enter through the display helper, and returns to following bytecode.",
            byte_action(0x65, 1) + draw_view11_at(50),
            50,
            messages=["HELLO"],
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "display_message_var_then_ack_continues_to_draw",
            "Action 0x66 reads the message number from a variable, accepts Enter, and returns to following bytecode.",
            assignn(1, 1) + byte_action(0x66, 1) + draw_view11_at(50),
            50,
            messages=["HELLO"],
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "display_message_configured_then_ack_continues_to_draw",
            "Action 0x97 uses configured message-display bytes, accepts Enter, and returns to following bytecode.",
            byte_action(0x97, 1, 5, 5, 12) + draw_view11_at(50),
            50,
            messages=["HELLO"],
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "display_formatted_message_then_ack_continues_to_draw",
            "Action 0x67 displays a positioned/formatted message, accepts Enter, and returns to following bytecode.",
            byte_action(0x67, 5, 5, 1) + byte_action(0x1A) + draw_view11_at(50),
            50,
            messages=["HELLO"],
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "display_formatted_message_var_then_ack_continues_to_draw",
            "Action 0x68 reads positioned/formatted display operands from variables, accepts Enter, and returns.",
            assignn(1, 5)
            + assignn(2, 5)
            + assignn(3, 1)
            + byte_action(0x68, 1, 2, 3)
            + byte_action(0x1A)
            + draw_view11_at(50),
            50,
            messages=["HELLO"],
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "display_message_configured_var_then_ack_continues_to_draw",
            "Action 0x98 reads the message number from a variable while using immediate display configuration bytes.",
            assignn(1, 1) + byte_action(0x98, 1, 5, 5, 12) + byte_action(0x1A) + draw_view11_at(50),
            50,
            messages=["HELLO"],
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "prompt_string_to_slot_returns_after_enter",
            "Action 0x73 accepts typed text through helper 0x0da9 and returns to following bytecode after Enter.",
            byte_action(0x73, 0, 1, 10, 10, 8) + byte_action(0x1A) + draw_view11_at(50),
            50,
            messages=["WORD?"],
            post_launch_keys="look",
            post_launch_wait=1.0,
            post_launch_key_delay=0.12,
            post_launch_after_text_wait=0.5,
            post_launch_key_names=["ret"],
        ),
        _custom_case(
            "prompt_string_to_slot_stores_typed_word",
            "Action 0x73 stores typed text into a string slot; condition 0x0f observes equality with a message-filled slot.",
            byte_action(0x72, 1, 2)
            + byte_action(0x73, 0, 1, 10, 10, 8)
            + byte_action(0x1A)
            + if_then(string_slots_equal_condition(0, 1), draw_view11_at(50)),
            50,
            messages=["WORD?", "look"],
            post_launch_keys="look",
            post_launch_wait=1.0,
            post_launch_key_delay=0.12,
            post_launch_after_text_wait=0.5,
            post_launch_key_names=["ret"],
        ),
        _draw_if_case(
            "prompt_number_to_var_accepts_digits",
            "Action 0x76 accepts typed decimal digits and stores the parsed low byte in a variable.",
            byte_action(0x76, 1, 2),
            var_eq_imm_condition(2, 42),
            messages=["NUMBER?"],
            post_launch_keys="42\n\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "input_line_toggle_refresh_erase_dispatch_smoke",
            "Actions 0x77, 0x78, 0x89, and 0x8a update input-line display state and return to following bytecode.",
            byte_action(0x77) + byte_action(0x78) + byte_action(0x89) + byte_action(0x8A) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "input_line_disable_clears_configured_row",
            "Action 0x77 disables the input line and clears the row configured by action 0x6f operand 1.",
            byte_action(0x67, 5, 5, 1)
            + byte_action(0x6F, 0, 5, 22)
            + byte_action(0x77)
            + draw_view11_at(50),
            50,
            messages=["HELLO"],
            post_launch_keys="\n",
            post_launch_wait=1.0,
            expected_visual_rects=[
                {"left": 0, "top": 40, "right": WIDTH - 1, "bottom": 47, "color": 0}
            ],
        ),
        _custom_case(
            "text_rect_clear_dispatch_smoke",
            "Actions 0x69 and 0x9a clear text rectangles and return to following bytecode.",
            byte_action(0x69, 0, 0, 0)
            + byte_action(0x9A, 0, 0, 1, 10, 0)
            + byte_action(0x1A)
            + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "text_rect_clear_rows_removes_formatted_text",
            "Action 0x69 clears the rows containing formatted text without requiring a picture refresh.",
            byte_action(0x67, 5, 5, 1)
            + byte_action(0x69, 5, 6, 0)
            + draw_view11_at(50),
            50,
            messages=["HELLO"],
            post_launch_keys="\n",
            post_launch_wait=1.0,
            expected_visual_rects=[
                {"left": 0, "top": 40, "right": WIDTH - 1, "bottom": 55, "color": 0}
            ],
        ),
        _custom_case(
            "text_rect_clear_bounds_removes_formatted_text",
            "Action 0x9a clears a bounded rectangle containing formatted text without requiring a picture refresh.",
            byte_action(0x67, 8, 5, 1)
            + byte_action(0x9A, 8, 5, 8, 20, 0)
            + draw_view11_at(50),
            50,
            messages=["HELLO"],
            post_launch_keys="\n",
            post_launch_wait=1.0,
            expected_visual_rects=[
                {"left": 20, "top": 64, "right": 83, "bottom": 71, "color": 0}
            ],
        ),
        _custom_case(
            "close_text_window_state_dispatch_smoke",
            "Action 0xa9 closes any active text-window state and returns to following bytecode.",
            byte_action(0xA9) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "text_attribute_mode_dispatch_smoke",
            "Actions 0x6d, 0x6a, and 0x6b configure text attributes, enter/leave the alternate text mode, and return.",
            byte_action(0x6D, 15, 0)
            + byte_action(0x6A)
            + byte_action(0x6B)
            + byte_action(0x1A)
            + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "screen_shake_dispatch_smoke",
            "Action 0x6e performs one display-shake iteration and returns to following bytecode.",
            byte_action(0x6E, 1) + byte_action(0x1A) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "input_prompt_config_dispatch_smoke",
            "Actions 0x6c and 0x6f configure the prompt character and input-line geometry globals, then return.",
            byte_action(0x6C, 1) + byte_action(0x6F, 0, 0, 22) + byte_action(0x1A) + draw_view11_at(50),
            50,
            messages=["?"],
        ),
        _custom_case(
            "status_line_show_hide_dispatch_smoke",
            "Actions 0x70 and 0x71 show and hide the status-line-like area and return to following bytecode.",
            byte_action(0x70) + byte_action(0x71) + byte_action(0x1A) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "status_line_hide_clears_configured_row",
            "Action 0x71 hides the status line and clears the row configured by action 0x6f operand 2.",
            byte_action(0x67, 5, 5, 1)
            + byte_action(0x6F, 0, 0, 5)
            + byte_action(0x71)
            + draw_view11_at(50),
            50,
            messages=["HELLO"],
            post_launch_keys="\n",
            post_launch_wait=1.0,
            expected_visual_rects=[
                {"left": 0, "top": 40, "right": WIDTH - 1, "bottom": 47, "color": 0}
            ],
        ),
        _custom_case(
            "key_event_mapping_dispatch_smoke",
            "Action 0x79 inserts one key/event mapping table entry and returns to following bytecode.",
            byte_action(0x79, ord("x"), 0, 7) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "input_line_config_operand1_offsets_display_by_8",
            "Action 0x6f with first operand 1 offsets later visible drawing by eight logical rows.",
            byte_action(0x6F, 1, 0, 22) + byte_action(0x1A) + draw_view11_at(50),
            50,
            expected_baseline_y=88,
        ),
        _custom_case(
            "mapped_key_sets_status_byte",
            "Action 0x79 maps typed key x to status byte 7 through the event loop; condition 0x0c observes it.",
            byte_action(0x79, ord("x"), 0, 7),
            50,
            init_once_flag=85,
            per_cycle_body=if_then(status_byte_condition(7), draw_view11_at(50)),
            post_launch_keys="x",
            post_launch_wait=1.0,
            post_launch_key_delay=0.12,
        ),
        _custom_case(
            "raw_key_event_available_draws_after_typed_key",
            "Condition 0x0d observes a raw type-1 key event without using the script key-mapping table.",
            b"",
            50,
            init_once_flag=90,
            per_cycle_body=if_then(raw_key_event_available_condition(), draw_view11_at(50)),
            post_launch_keys="x",
            post_launch_wait=1.0,
            post_launch_key_delay=0.12,
        ),
        _draw_if_case(
            "set_string_from_table_copies_patched_pointer",
            "Action 0x74 copies from a DS pointer table entry into a string slot; this fixture patches a synthetic table entry.",
            byte_action(0x74, 0, 0) + byte_action(0x72, 1, 1),
            string_slots_equal_condition(0, 1),
            messages=["look"],
            agidata_patches=[
                {"offset": 0x0C8F, "data_hex": "c00c"},
                {"offset": 0x0CC0, "data_hex": "6c6f6f6b00"},
            ],
        ),
        _draw_if_case(
            "inventory_marker_ff_condition_true",
            "Action 0x5c marks an inventory/object-table entry as 0xff and condition 0x09 observes it.",
            byte_action(0x5C, 0),
            obj_table_room_ff_condition(0),
        ),
        _draw_if_case(
            "inventory_marker_eq_var_condition_true",
            "Condition 0x0a compares an inventory/object-table marker with a variable.",
            byte_action(0x5C, 0) + assignn(1, 0xFF),
            obj_table_room_eq_var_condition(0, 1),
        ),
        _draw_if_case(
            "inventory_marker_ff_var_and_getter",
            "Actions 0x5d and 0x61 use a variable-selected inventory/object-table index.",
            assignn(1, 0) + byte_action(0x5D, 1) + byte_action(0x61, 1, 2),
            var_eq_imm_condition(2, 0xFF),
        ),
        _draw_if_case(
            "inventory_marker_clear_and_getter",
            "Actions 0x5e and 0x61 clear and read an inventory/object-table marker.",
            assignn(1, 0) + byte_action(0x5C, 0) + byte_action(0x5E, 0) + byte_action(0x61, 1, 2),
            var_eq_imm_condition(2, 0),
        ),
        _draw_if_case(
            "inventory_marker_from_var",
            "Action 0x5f stores a variable value into an immediate inventory/object-table index.",
            assignn(1, 0) + assignn(2, 7) + byte_action(0x5F, 0, 2) + byte_action(0x61, 1, 3),
            var_eq_imm_condition(3, 7),
        ),
        _draw_if_case(
            "inventory_marker_from_var_var",
            "Action 0x60 stores a variable value into a variable-selected inventory/object-table index.",
            assignn(1, 0) + assignn(2, 9) + byte_action(0x60, 1, 2) + byte_action(0x61, 1, 3),
            var_eq_imm_condition(3, 9),
        ),
        _draw_if_case(
            "inventory_selection_enter_sets_var19",
            "Interactive action 0x7c writes the selected carried-entry index to absolute byte 0x0022, exposed as variable 0x19, on Enter.",
            assignn(0x19, 0x7E) + byte_action(0x5C, 0) + set_flag_action(0x0D) + byte_action(0x7C) + byte_action(0x1A),
            var_eq_imm_condition(0x19, 0),
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _draw_if_case(
            "inventory_selection_escape_sets_var19_ff",
            "Interactive action 0x7c writes 0xff to absolute byte 0x0022, exposed as variable 0x19, on Escape.",
            assignn(0x19, 0x7E) + byte_action(0x5C, 0) + set_flag_action(0x0D) + byte_action(0x7C) + byte_action(0x1A),
            var_eq_imm_condition(0x19, 0xFF),
            post_launch_key_names=["esc"],
            post_launch_wait=1.0,
        ),
        _custom_case(
            "inventory_selection_noninteractive_ack_returns",
            "Noninteractive action 0x7c waits for acknowledgement and then returns to following bytecode.",
            byte_action(0x5C, 0) + byte_action(0x7C) + byte_action(0x1A) + draw_view11_at(50),
            50,
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _draw_if_case(
            "object_view_metadata_getters",
            "Actions 0x31..0x35 read selected object/view metadata after binding view 11 group 1 frame 1.",
            setup_object_for_view11(10, group_no=1, frame_no=1)
            + byte_action(0x31, 10, 1)
            + byte_action(0x32, 10, 2)
            + byte_action(0x33, 10, 3)
            + byte_action(0x34, 10, 4)
            + byte_action(0x35, 10, 5),
            all_conditions(
                var_eq_imm_condition(1, 1),
                var_eq_imm_condition(2, 1),
                var_eq_imm_condition(3, 1),
                var_eq_imm_condition(4, 11),
                var_eq_imm_condition(5, 2),
            ),
        ),
        _draw_if_case(
            "object_field_24_var_getter_observes_value",
            "Actions 0x37 and 0x39 set object byte +0x24 from a variable and read it back.",
            assignn(1, 13) + byte_action(0x37, 10, 1) + byte_action(0x39, 10, 2),
            var_eq_imm_condition(2, 13),
        ),
        _draw_if_case(
            "object_distance_inactive_pair_sets_ff",
            "Action 0x45 stores 0xff when either object is not active.",
            byte_action(0x45, 10, 11, 1),
            var_eq_imm_condition(1, 0xFF),
        ),
        _draw_if_case(
            "clear_object_fields_21_22_clears_direction",
            "Action 0x4d clears object byte +0x21, observable through getter 0x57.",
            assignn(1, 8) + byte_action(0x56, 10, 1) + byte_action(0x4D, 10) + byte_action(0x57, 10, 2),
            var_eq_imm_condition(2, 0),
        ),
        _draw_if_case(
            "set_object_pos_dirty_getter_observes_values",
            "Action 0x93 writes object position bytes and 0x27 reads them back.",
            byte_action(0x93, 10, 44, 81) + byte_action(0x27, 10, 1, 2),
            all_conditions(var_eq_imm_condition(1, 44), var_eq_imm_condition(2, 81)),
        ),
        _draw_if_case(
            "set_object_pos_dirty_var_getter_observes_values",
            "Action 0x94 writes object position bytes from variables and 0x27 reads them back.",
            assignn(1, 45) + assignn(2, 82) + byte_action(0x94, 10, 1, 2) + byte_action(0x27, 10, 3, 4),
            all_conditions(var_eq_imm_condition(3, 45), var_eq_imm_condition(4, 82)),
        ),
        _custom_case(
            "deactivate_object_removes_persistent_draw",
            "Action 0x24 deactivates an active persistent object so only the following transient draw remains visible.",
            setup_object_for_view11(10, x=20)
            + byte_action(0x23, 10)
            + byte_action(0x24, 10)
            + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "clear_all_object_bits_keeps_current_draw_entry",
            "Action 0x22 clears active/update bits but does not immediately unlink an already activated persistent object.",
            setup_object_for_view11(10, x=20)
            + byte_action(0x23, 10)
            + byte_action(0x22)
            + draw_view11_at(50),
            50,
            expected_extra_sprites=[
                {
                    "view_no": 11,
                    "group_no": 0,
                    "frame_no": 0,
                    "x": 20,
                    "baseline_y": 80,
                    "priority": 15,
                }
            ],
        ),
        _custom_case(
            "horizon_clamps_object_when_bit_clear",
            "Action 0x3f sets the horizon-like global; with bit 0x0008 clear, placement clamps baseline to horizon + 1.",
            byte_action(0x3F, 100) + setup_object_for_view11(10, x=50, baseline_y=80) + byte_action(0x23, 10),
            50,
            expected_baseline_y=101,
        ),
        _custom_case(
            "horizon_exempt_bit_keeps_object_above_horizon",
            "Action 0x3d sets bit 0x0008, exempting placement from the horizon-like clamp.",
            byte_action(0x3F, 100)
            + byte_action(0x21, 10)
            + byte_action(0x3D, 10)
            + byte_action(0x29, 10, 11)
            + byte_action(0x2B, 10, 0)
            + byte_action(0x2F, 10, 0)
            + byte_action(0x25, 10, 50, 80)
            + byte_action(0x23, 10),
            50,
            expected_baseline_y=80,
        ),
        _custom_case(
            "horizon_clear_exempt_bit_restores_clamp",
            "Action 0x3e clears bit 0x0008 after it was set, restoring the horizon-like clamp.",
            byte_action(0x3F, 100)
            + byte_action(0x21, 10)
            + byte_action(0x3D, 10)
            + byte_action(0x3E, 10)
            + byte_action(0x29, 10, 11)
            + byte_action(0x2B, 10, 0)
            + byte_action(0x2F, 10, 0)
            + byte_action(0x25, 10, 50, 80)
            + byte_action(0x23, 10),
            50,
            expected_baseline_y=101,
        ),
        _custom_case(
            "clear_fixed_priority_bit_uses_derived_priority",
            "Action 0x38 clears bit 0x0004 so placement uses the Y-derived priority instead of fixed object byte +0x24.",
            setup_object_for_view11(10, x=50, baseline_y=80)
            + byte_action(0x36, 10, 5)
            + byte_action(0x38, 10)
            + byte_action(0x23, 10),
            50,
            picture_payload=bytes([0xF2, 0x06, 0xF8, 0x00, 0x00, 0xFF]),
            expected_priority=7,
        ),
        _custom_case(
            "clear_bit_0010_moves_object_behind_set_partition",
            "Action 0x3a clears bit 0x0010, moving the object to the root 0x1703 partition drawn before root 0x16ff.",
            setup_object_for_view11(10, x=50, baseline_y=80, frame_no=0)
            + byte_action(0x23, 10)
            + setup_object_for_view11(11, x=90, baseline_y=80, frame_no=1)
            + byte_action(0x23, 11)
            + byte_action(0x25, 11, 50, 80)
            + byte_action(0x3A, 11)
            + byte_action(0x3C, 11),
            50,
            expected_frame_no=0,
            expected_extra_sprites=[
                {
                    "view_no": 11,
                    "group_no": 0,
                    "frame_no": 1,
                    "x": 90,
                    "baseline_y": 80,
                    "priority": 15,
                },
                {
                    "view_no": 11,
                    "group_no": 0,
                    "frame_no": 1,
                    "x": 50,
                    "baseline_y": 80,
                    "priority": 15,
                }
            ],
        ),
        _custom_case(
            "set_bit_0010_moves_object_over_clear_partition",
            "Action 0x3b sets bit 0x0010, moving the object to the root 0x16ff partition drawn after root 0x1703.",
            setup_object_for_view11(10, x=50, baseline_y=80, frame_no=0)
            + byte_action(0x23, 10)
            + byte_action(0x3A, 10)
            + setup_object_for_view11(11, x=90, baseline_y=80, frame_no=1)
            + byte_action(0x23, 11)
            + byte_action(0x25, 11, 50, 80)
            + byte_action(0x3A, 11)
            + byte_action(0x3B, 11)
            + byte_action(0x3C, 11),
            50,
            expected_frame_no=1,
            expected_extra_sprites=[
                {
                    "view_no": 11,
                    "group_no": 0,
                    "frame_no": 1,
                    "x": 90,
                    "baseline_y": 80,
                    "priority": 15,
                },
                {
                    "view_no": 11,
                    "group_no": 0,
                    "frame_no": 0,
                    "x": 50,
                    "baseline_y": 80,
                    "priority": 15,
                }
            ],
        ),
        _custom_case(
            "clear_bit_2000_allows_direction_group_selection",
            "Action 0x2e leaves automatic direction-based group selection enabled; direction 6 selects view 4 group 1.",
            setup_object_for_view(4, 10, x=50, baseline_y=90, group_no=0, frame_no=0)
            + byte_action(0x23, 10)
            + assignn(1, 6)
            + byte_action(0x56, 10, 1)
            + assignn(2, 1)
            + byte_action(0x50, 10, 2)
            + byte_action(0x2E, 10),
            50,
            expected_view_no=4,
            expected_group_no=1,
            expected_frame_no=0,
            expected_baseline_y=90,
            preload_view_no=4,
            init_once_flag=79,
        ),
        _custom_case(
            "set_bit_2000_suppresses_direction_group_selection",
            "Action 0x2d suppresses automatic direction-based group selection; direction 6 leaves view 4 on group 0.",
            setup_object_for_view(4, 10, x=50, baseline_y=90, group_no=0, frame_no=0)
            + byte_action(0x23, 10)
            + assignn(1, 6)
            + byte_action(0x56, 10, 1)
            + assignn(2, 1)
            + byte_action(0x50, 10, 2)
            + byte_action(0x2D, 10),
            50,
            expected_view_no=4,
            expected_group_no=0,
            expected_frame_no=0,
            expected_baseline_y=90,
            preload_view_no=4,
            init_once_flag=80,
        ),
        _custom_case(
            "clear_bit_2000_two_or_three_group_direction6_selects_group1",
            "With a 3-group view, clear bit 0x2000 lets direction 6 select group 1 through the two/three-group table.",
            setup_object_for_view(5, 10, x=50, baseline_y=112, group_no=0, frame_no=0)
            + byte_action(0x23, 10)
            + assignn(1, 6)
            + byte_action(0x56, 10, 1)
            + assignn(2, 1)
            + byte_action(0x50, 10, 2)
            + byte_action(0x2E, 10),
            50,
            expected_view_no=5,
            expected_group_no=1,
            expected_frame_no=0,
            expected_baseline_y=112,
            preload_view_no=5,
            init_once_flag=81,
        ),
        _custom_case(
            "clear_bit_2000_two_or_three_group_direction5_is_sentinel",
            "With a 3-group view, clear bit 0x2000 and direction 5 produce sentinel group 4, so group 0 remains selected.",
            setup_object_for_view(5, 10, x=50, baseline_y=112, group_no=0, frame_no=0)
            + byte_action(0x23, 10)
            + assignn(1, 5)
            + byte_action(0x56, 10, 1)
            + assignn(2, 1)
            + byte_action(0x50, 10, 2)
            + byte_action(0x2E, 10),
            50,
            expected_view_no=5,
            expected_group_no=0,
            expected_frame_no=0,
            expected_baseline_y=112,
            preload_view_no=5,
            init_once_flag=82,
        ),
        _custom_case(
            "clear_bit_2000_field01_countdown_eventually_selects_group",
            "Clear bit 0x2000 with object byte +0x01 set to 2 skips one pass, then selects when the countdown reaches 1.",
            setup_object_for_view(4, 10, x=50, baseline_y=90, group_no=0, frame_no=0)
            + byte_action(0x23, 10)
            + assignn(1, 6)
            + byte_action(0x56, 10, 1)
            + assignn(2, 2)
            + byte_action(0x50, 10, 2)
            + byte_action(0x2E, 10),
            50,
            expected_view_no=4,
            expected_group_no=1,
            expected_frame_no=0,
            expected_baseline_y=90,
            preload_view_no=4,
            init_once_flag=83,
        ),
        _custom_case(
            "clear_bit_2000_requires_field01_equal_one_when_forced",
            "Per-cycle forcing object byte +0x01 to 2 prevents automatic direction-based group selection.",
            setup_object_for_view(4, 10, x=50, baseline_y=90, group_no=0, frame_no=0)
            + byte_action(0x23, 10)
            + assignn(1, 6)
            + byte_action(0x56, 10, 1)
            + byte_action(0x2E, 10),
            50,
            expected_view_no=4,
            expected_group_no=0,
            expected_frame_no=0,
            expected_baseline_y=90,
            preload_view_no=4,
            init_once_flag=84,
            per_cycle_body=assignn(2, 2) + byte_action(0x50, 10, 2),
        ),
        _custom_case(
            "object_field_23_mode0_dispatch_smoke",
            "Action 0x48 sets object byte +0x23 to mode 0 and returns to following bytecode.",
            setup_object_for_view11(10) + byte_action(0x48, 10) + draw_view11_at(50),
            50,
        ),
        _draw_if_case(
            "object_field_23_mode1_clears_flag",
            "Action 0x49 clears its flag operand while setting object byte +0x23 mode 1 state.",
            setup_object_for_view11(10) + set_flag_action(77) + byte_action(0x49, 10, 77),
            not_flag_set_condition(77),
        ),
        _custom_case(
            "object_field_23_mode3_dispatch_smoke",
            "Action 0x4a sets object byte +0x23 to mode 3 and returns to following bytecode.",
            setup_object_for_view11(10) + byte_action(0x4A, 10) + draw_view11_at(50),
            50,
        ),
        _draw_if_case(
            "object_field_23_mode2_clears_flag",
            "Action 0x4b clears its flag operand while setting object byte +0x23 mode 2 state.",
            setup_object_for_view11(10) + set_flag_action(78) + byte_action(0x4B, 10, 78),
            not_flag_set_condition(78),
        ),
        _custom_case(
            "object_bitfield_actions_dispatch_smoke",
            "Bitfield/helper actions 0x38, 0x3a..0x3e, 0x40..0x44, 0x46..0x47, 0x4c, 0x4e, and 0x58..0x59 execute and return to following bytecode.",
            object_bitfield_smoke_actions() + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "menu_setup_dispatch_smoke",
            "Menu/list setup actions 0x9c..0xa0 allocate/finalize/toggle entries and return to following bytecode.",
            byte_action(0x9C, 1)
            + byte_action(0x9D, 2, 7)
            + byte_action(0x9E)
            + byte_action(0xA0, 7)
            + byte_action(0x9F, 7)
            + draw_view11_at(50),
            50,
            messages=["FILE", "OPEN"],
        ),
        _custom_case(
            "menu_flag_dispatch_smoke",
            "Action 0xa1 observes flag 0x0e and returns to following bytecode.",
            set_flag_action(0x0E) + byte_action(0xA1) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "menu_interactive_enter_sets_status_byte",
            "A finalized one-item menu opened through 0xa1 enqueues a type-3 event with the enabled item id on Enter.",
            byte_action(0x9C, 1)
            + byte_action(0x9D, 2, 7)
            + byte_action(0x9E)
            + set_flag_action(0x0E)
            + byte_action(0xA1),
            50,
            messages=["FILE", "OPEN"],
            init_once_flag=86,
            per_cycle_body=if_then(status_byte_condition(7), byte_action(0x1A) + draw_view11_at(50)),
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "menu_escape_exits_without_status_byte",
            "Escape exits a menu opened through 0xa1 without setting the item status byte.",
            byte_action(0x9C, 1)
            + byte_action(0x9D, 2, 7)
            + byte_action(0x9E)
            + set_flag_action(0x0E)
            + byte_action(0xA1),
            50,
            messages=["FILE", "OPEN"],
            init_once_flag=87,
            per_cycle_body=byte_action(0x1A) + if_then(bytes([0xFD]) + status_byte_condition(7), draw_view11_at(50)),
            post_launch_key_names=["esc"],
            post_launch_wait=1.0,
        ),
        _custom_case(
            "menu_disabled_item_enter_does_not_set_status_byte",
            "Enter on a disabled menu item stays in the menu loop and does not enqueue the disabled item id before Escape exits.",
            byte_action(0x9C, 1)
            + byte_action(0x9D, 2, 7)
            + byte_action(0x9E)
            + byte_action(0xA0, 7)
            + set_flag_action(0x0E)
            + byte_action(0xA1),
            50,
            messages=["FILE", "OPEN"],
            init_once_flag=88,
            per_cycle_body=byte_action(0x1A) + if_then(bytes([0xFD]) + status_byte_condition(7), draw_view11_at(50)),
            post_launch_keys="\n",
            post_launch_wait=1.0,
            post_launch_after_text_wait=0.5,
            post_launch_key_names=["esc"],
        ),
        _custom_case(
            "menu_enable_after_disable_allows_enter_status_byte",
            "Disabling and then re-enabling a menu item lets Enter enqueue that item id.",
            byte_action(0x9C, 1)
            + byte_action(0x9D, 2, 7)
            + byte_action(0x9E)
            + byte_action(0xA0, 7)
            + byte_action(0x9F, 7)
            + set_flag_action(0x0E)
            + byte_action(0xA1),
            50,
            messages=["FILE", "OPEN"],
            init_once_flag=89,
            per_cycle_body=if_then(status_byte_condition(7), byte_action(0x1A) + draw_view11_at(50)),
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "sound_load_stop_dispatch_smoke",
            "Actions 0x62 and 0x64 load a sound resource and clear sound state before returning to following bytecode.",
            byte_action(0x62, 1) + byte_action(0x64) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "sound_start_stop_dispatch_smoke",
            "Action 0x63 starts a sound with a completion flag operand and returns; 0x64 then clears sound state.",
            byte_action(0x62, 1) + byte_action(0x63, 1, 77) + byte_action(0x64) + draw_view11_at(50),
            50,
        ),
        _draw_if_case(
            "sound_stop_sets_completion_flag",
            "After 0x63 associates a completion flag with an active sound, 0x64 sets that flag while clearing sound state.",
            byte_action(0x62, 1) + byte_action(0x63, 1, 77) + byte_action(0x64),
            flag_set_condition(77),
        ),
        _custom_case(
            "priority_screen_enter_returns",
            "Action 0x1d displays the priority/control view, accepts an input event, restores the normal screen, and returns.",
            byte_action(0x1D) + byte_action(0x1A) + draw_view11_at(50),
            50,
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "object_diagnostics_var_enter_returns",
            "Action 0x85 formats object fields selected by a variable, accepts Enter, and returns to following bytecode.",
            setup_object_for_view11(10, x=42, baseline_y=80)
            + byte_action(0x36, 10, 12)
            + assignn(1, 10)
            + byte_action(0x85, 1)
            + byte_action(0x1A)
            + draw_view11_at(50),
            50,
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "view_resource_display_immediate_returns",
            "Action 0x81 displays/previews an immediate view resource, accepts Enter, and returns to following bytecode.",
            byte_action(0x81, 11) + byte_action(0x1A) + draw_view11_at(50),
            50,
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "view_resource_display_var_returns",
            "Action 0xa2 displays/previews a variable-selected view resource, accepts Enter, and returns to following bytecode.",
            assignn(1, 11) + byte_action(0xA2, 1) + byte_action(0x1A) + draw_view11_at(50),
            50,
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "signature_check_matching_message_returns",
            "Action 0x8f accepts a current-logic message beginning with the SQ2 signature and returns.",
            byte_action(0x8F, 1) + draw_view11_at(50),
            50,
            messages=["SQ2"],
        ),
        _custom_case(
            "restart_confirm_escape_continues_to_draw",
            "Action 0x80 displays the restart confirmation, accepts Escape as cancel, and returns to following bytecode.",
            byte_action(0x80) + byte_action(0x1A) + draw_view11_at(50),
            50,
            post_launch_key_names=["esc"],
            post_launch_wait=1.0,
        ),
        _custom_case(
            "confirm_restart_like_escape_continues_to_draw",
            "Action 0x86 with operand 0 displays its confirmation prompt, accepts Escape as cancel, and returns.",
            byte_action(0x86, 0) + byte_action(0x1A) + draw_view11_at(50),
            50,
            post_launch_key_names=["esc"],
            post_launch_wait=1.0,
        ),
        _custom_case(
            "joystick_calibration_no_joystick_returns",
            "Action 0x8b returns to following bytecode on the no-joystick path observed under QEMU.",
            byte_action(0x8B) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "display_mode_toggle_guarded_noop_continues",
            "Action 0x8c returns without toggling when byte variable 0 is zero.",
            assignn(0, 0) + byte_action(0x8C) + draw_view11_at(50),
            50,
        ),
        LogicInterpreterCase(
            case_id="display_mode_replay_skips_flag7_unrecorded_picture",
            description=(
                "Action 0x8c enters display-mode replay after a picture drawn with "
                "flag 7 set; replay excludes that picture, and the recorded picture "
                "is redrawn through the alternate CGA mapping."
            ),
            code_hex=room_reentry_logic0_code(byte_action(0x12, 1), init_flag=136).hex(),
            picture_payload_hex=bytes([0xF0, 0x06, 0xF8, 0x00, 0x00, 0xFF]).hex(),
            expected_picture_payload_hex=alternating_row_picture_payload(0x06, 0x04).hex(),
            picture_no=0,
            expected_view_no=11,
            expected_group_no=0,
            expected_frame_no=0,
            expected_x=50,
            expected_baseline_y=80,
            expected_priority=15,
            extra_logics=[
                logic_patch(
                    1,
                    display_mode_replay_flag7_validation_logic(
                        expected_draw_x=50,
                        init_flag=137,
                        draw_after_replay=False,
                    ),
                )
            ],
            extra_pictures=[
                {
                    "picture_no": 1,
                    "payload_hex": bytes([0xF0, 0x04, 0xF8, 0x00, 0x00, 0xFF]).hex(),
                }
            ],
            agidata_patches=[
                {"offset": 0x112E, "data_hex": "0000"},
                {"offset": 0x1130, "data_hex": "0000"},
            ],
            launch_command="SIERRA -p -c",
            compare_view=False,
        ),
        LogicInterpreterCase(
            case_id="display_mode_replay_uses_rolled_back_event_count",
            description=(
                "Action 0x8c enters display-mode replay after 0xab/0xac roll back "
                "the resource-event count; replay excludes the rolled-back picture, "
                "and the recorded picture is redrawn through the alternate CGA mapping."
            ),
            code_hex=room_reentry_logic0_code(byte_action(0x12, 1), init_flag=134).hex(),
            picture_payload_hex=bytes([0xF0, 0x06, 0xF8, 0x00, 0x00, 0xFF]).hex(),
            expected_picture_payload_hex=alternating_row_picture_payload(0x06, 0x04).hex(),
            picture_no=0,
            expected_view_no=11,
            expected_group_no=0,
            expected_frame_no=0,
            expected_x=50,
            expected_baseline_y=80,
            expected_priority=15,
            extra_logics=[
                logic_patch(
                    1,
                    display_mode_replay_validation_logic(
                        expected_draw_x=50,
                        init_flag=135,
                        draw_after_replay=False,
                    ),
                )
            ],
            extra_pictures=[
                {
                    "picture_no": 1,
                    "payload_hex": bytes([0xF0, 0x04, 0xF8, 0x00, 0x00, 0xFF]).hex(),
                }
            ],
            agidata_patches=[
                {"offset": 0x112E, "data_hex": "0000"},
                {"offset": 0x1130, "data_hex": "0000"},
            ],
            launch_command="SIERRA -p -c",
            compare_view=False,
        ),
        _custom_case(
            "trace_window_config_enable_dispatch_smoke",
            "Actions 0x96 and gated 0x95 configure trace-window globals and return when flag 10 is clear.",
            byte_action(0x96, 0, 1, 1) + byte_action(0x95) + draw_view11_at(50),
            50,
        ),
        _custom_case(
            "log_file_append_dispatch_smoke",
            "Action 0x90 appends a formatted room/input/message record to logfile and returns.",
            byte_action(0x90, 1) + draw_view11_at(50),
            50,
            messages=["LOG"],
        ),
        _custom_case(
            "save_game_escape_continues_to_draw",
            "Action 0x7d opens the save-game selector, accepts Escape as cancel, and returns.",
            byte_action(0x7D) + byte_action(0x1A) + draw_view11_at(50),
            50,
            post_launch_key_names=["esc"],
            post_launch_wait=1.0,
        ),
        _custom_case(
            "restore_game_escape_continues_to_draw",
            "Action 0x7e opens the restore-game selector, accepts Escape as cancel, and returns.",
            byte_action(0x7E) + byte_action(0x1A) + draw_view11_at(50),
            50,
            post_launch_key_names=["esc"],
            post_launch_wait=1.0,
        ),
        _custom_case(
            "pause_message_then_ack_continues_to_draw",
            "Action 0x88 displays the pause message, accepts Enter, and returns to following bytecode.",
            byte_action(0x88) + draw_view11_at(50),
            50,
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "heap_status_then_ack_continues_to_draw",
            "Action 0x87 displays heap/status diagnostics, accepts Enter, and returns to following bytecode.",
            byte_action(0x87) + draw_view11_at(50),
            50,
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "interpreter_version_then_ack_continues_to_draw",
            "Action 0x8d displays interpreter version text, accepts Enter, and returns to following bytecode.",
            byte_action(0x8D) + draw_view11_at(50),
            50,
            post_launch_keys="\n",
            post_launch_wait=1.0,
        ),
        _custom_case(
            "diagnostic_global_actions_dispatch_smoke",
            "Actions 0x83, 0x84, 0x8e, 0xaa..0xad, 0xa3, and 0xa4 update interpreter globals and return.",
            byte_action(0x83)
            + byte_action(0x84)
            + byte_action(0x8E, 1)
            + byte_action(0xAA, 0)
            + byte_action(0xAB)
            + byte_action(0xAC)
            + byte_action(0xAD)
            + byte_action(0xA3)
            + byte_action(0xA4)
            + draw_view11_at(50),
            50,
        ),
    ]


def load_cases(path: Path | None, selected_ids: list[str] | None = None) -> list[LogicInterpreterCase]:
    if path is None:
        cases = base_cases()
    else:
        data = json.loads(path.read_text(encoding="ascii"))
        cases = [LogicInterpreterCase(**item) for item in data]
    if selected_ids:
        selected = set(selected_ids)
        cases = [case for case in cases if case.case_id in selected]
        missing = selected - {case.case_id for case in cases}
        if missing:
            raise ValueError(f"unknown case id(s): {', '.join(sorted(missing))}")
    return cases


def qemu_batch_dos_dir(prefix: str, index: int) -> str:
    clean = "".join(character for character in prefix.upper() if character.isalnum()) or "LI"
    return f"{clean[:3]}{index:05d}"[:8]


def build_logic_fixture(case: LogicInterpreterCase, destination: Path) -> Path:
    copy_sq2_tree(destination)
    if case.agidata_patches:
        agidata_path = destination / "AGIDATA.OVL"
        agidata = bytearray(agidata_path.read_bytes())
        for patch in case.agidata_patches:
            offset = int(patch["offset"])
            data = bytes.fromhex(str(patch["data_hex"]))
            agidata[offset : offset + len(data)] = data
        agidata_path.write_bytes(agidata)
    records = bytearray()
    logic_offsets: dict[int, int] = {0: 0}
    records.extend(volume_record(logic_resource(case.code, case.messages), volume=3))
    if case.extra_logics:
        for extra in case.extra_logics:
            logic_no = int(extra["logic_no"])
            logic_offsets[logic_no] = len(records)
            messages = extra.get("messages")
            if messages is not None and not isinstance(messages, list):
                raise TypeError("extra logic messages must be a list when provided")
            records.extend(
                volume_record(
                    logic_resource(bytes.fromhex(str(extra["code_hex"])), messages),
                    volume=3,
                )
            )
    picture_offsets: dict[int, int] = {case.picture_no: len(records)}
    records.extend(volume_record(case.picture_payload, volume=3))
    if case.extra_pictures:
        for extra in case.extra_pictures:
            picture_no = int(extra["picture_no"])
            payload = bytes.fromhex(str(extra["payload_hex"]))
            picture_offsets[picture_no] = len(records)
            records.extend(volume_record(payload, volume=3))
    (destination / "VOL.3").write_bytes(records)

    logdir = (destination / "LOGDIR").read_bytes()
    for logic_no, offset in logic_offsets.items():
        logdir = patch_dir_entry(logdir, logic_no, volume=3, offset=offset)
    (destination / "LOGDIR").write_bytes(logdir)

    picdir = (destination / "PICDIR").read_bytes()
    for picture_no, picture_offset in picture_offsets.items():
        picdir = patch_dir_entry(picdir, picture_no, volume=3, offset=picture_offset)
    (destination / "PICDIR").write_bytes(picdir)
    return destination


def apply_expected_visual_rects(picture, rects: list[dict[str, int]] | None):
    if not rects:
        return picture
    cells = bytearray(picture.cells)
    for rect in rects:
        left = max(0, int(rect["left"]))
        top = max(0, int(rect["top"]))
        right = min(WIDTH - 1, int(rect["right"]))
        bottom = min(HEIGHT - 1, int(rect["bottom"]))
        color = int(rect["color"]) & 0x0F
        if right < left or bottom < top:
            continue
        for y in range(top, bottom + 1):
            row = y * WIDTH
            for x in range(left, right + 1):
                idx = row + x
                cells[idx] = (cells[idx] & 0xF0) | color
    return type(picture)(picture.picture_no, bytes(cells))


def compare_capture(case: LogicInterpreterCase, capture: Path) -> LogicComparison:
    try:
        captured = downsample_qemu_picture_nibbles(read_ppm(capture))
        picture = PictureRenderer(case.expected_picture_payload).render(case.picture_no)
        picture = apply_expected_visual_rects(picture, case.expected_visual_rects)
        expected_picture = picture
        for sprite in case.expected_extra_sprites or []:
            extra_frame = render_view_frame(sprite["view_no"], sprite["group_no"], sprite["frame_no"])
            expected_picture = compose_frame_on_picture(
                expected_picture,
                extra_frame,
                sprite["x"],
                sprite["baseline_y"],
                sprite["priority"],
            )
        if case.compare_view:
            frame = render_view_frame(case.expected_view_no, case.expected_group_no, case.expected_frame_no)
            expected = compose_frame_on_picture(
                expected_picture,
                frame,
                case.expected_x,
                case.expected_baseline_y,
                case.expected_priority,
            ).visual_nibbles
        else:
            expected = expected_picture.visual_nibbles
    except Exception as exc:  # noqa: BLE001 - probe records exact local exception.
        return LogicComparison(case.case_id, "error", None, None, None, None, f"{type(exc).__name__}: {exc}")

    mismatch_samples: list[tuple[int, int, int, int]] = []
    min_x = WIDTH
    min_y = HEIGHT
    max_x = -1
    max_y = -1
    mismatches = 0
    for idx, (left, right) in enumerate(zip(captured, expected)):
        if left == right:
            continue
        mismatches += 1
        x = idx % WIDTH
        y = idx // WIDTH
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)
        if len(mismatch_samples) < 16:
            mismatch_samples.append((x, y, left, right))
    bbox = None if mismatches == 0 else (min_x, min_y, max_x, max_y)
    return LogicComparison(
        case.case_id,
        "match" if mismatches == 0 else "mismatch",
        mismatches,
        len(expected),
        bbox,
        mismatch_samples,
        None,
    )


def run_snapshot_batch(
    cases: list[LogicInterpreterCase],
    fixture_root: Path,
    boot_wait: float,
    draw_wait: float,
    dos_prefix: str,
    stop_on_failure: bool,
    snapshot_raw: Path,
    snapshot_qcow: Path,
) -> list[LogicBatchResult]:
    qemu_cases: list[SnapshotFixtureCase] = []
    started_at: dict[str, float] = {}
    for index, case in enumerate(cases):
        dos_dir = qemu_batch_dos_dir(dos_prefix, index)
        fixture = fixture_root / case.case_id
        capture = fixture / "qemu_capture.ppm"
        started_at[case.case_id] = time.monotonic()
        print(f"[{index + 1}/{len(cases)}] build {case.case_id} -> {dos_dir}", file=sys.stderr, flush=True)
        build_logic_fixture(case, fixture)
        qemu_cases.append(
            SnapshotFixtureCase(
                dos_dir,
                fixture,
                capture,
                launch_command=case.launch_command,
                post_launch_keys=case.post_launch_keys,
                post_launch_wait=case.post_launch_wait,
                post_launch_key_delay=case.post_launch_key_delay,
                post_launch_after_text_wait=case.post_launch_after_text_wait,
                post_launch_key_names=case.post_launch_key_names,
            )
        )

    print(f"building snapshot disk: {snapshot_qcow}", file=sys.stderr, flush=True)
    build_snapshot_boot_disk(qemu_cases, snapshot_raw, snapshot_qcow)
    print(f"running {len(qemu_cases)} cases from one QEMU snapshot", file=sys.stderr, flush=True)
    run_snapshot_qemu_cases(snapshot_qcow, qemu_cases, boot_wait, draw_wait)

    results: list[LogicBatchResult] = []
    for index, (case, qemu_case) in enumerate(zip(cases, qemu_cases)):
        comparison: LogicComparison | None = None
        error: str | None = None
        status = "error"
        try:
            comparison = compare_capture(case, qemu_case.capture)
            status = comparison.status
            error = comparison.error
        except Exception as exc:  # noqa: BLE001 - batch harness records exact local exception.
            error = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.monotonic() - started_at[case.case_id], 3)
        print(f"[{index + 1}/{len(cases)}] {case.case_id} {status}", file=sys.stderr, flush=True)
        results.append(
            LogicBatchResult(case.case_id, status, qemu_case.dos_dir, str(qemu_case.capture), elapsed, comparison, error)
        )
        if stop_on_failure and status != "match":
            break
    return results


def write_report(results: list[LogicBatchResult], output: Path) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "summary": {
            "total": len(results),
            "matches": sum(1 for result in results if result.status == "match"),
            "mismatches": sum(1 for result in results if result.status == "mismatch"),
            "errors": sum(1 for result in results if result.status == "error"),
        },
        "results": [asdict(result) for result in results],
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS / "logic_interpreter_base.json")
    parser.add_argument("--dos-prefix", default="LI")
    parser.add_argument("--boot-wait", type=float, default=5.0)
    parser.add_argument("--draw-wait", type=float, default=8.0)
    parser.add_argument("--stop-on-failure", action="store_true")
    parser.add_argument("--snapshot-raw", type=Path, default=DEFAULT_SNAPSHOT_RAW)
    parser.add_argument("--snapshot-qcow", type=Path, default=DEFAULT_SNAPSHOT_QCOW)
    args = parser.parse_args()

    results = run_snapshot_batch(
        load_cases(args.cases, args.case_ids),
        args.fixture_root,
        args.boot_wait,
        args.draw_wait,
        args.dos_prefix,
        args.stop_on_failure,
        args.snapshot_raw,
        args.snapshot_qcow,
    )
    report = write_report(results, args.output)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    print(f"report: {args.output}")
    if report["summary"]["mismatches"] or report["summary"]["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
