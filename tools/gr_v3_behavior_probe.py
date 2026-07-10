#!/usr/bin/env python3
"""Targeted behavior probes for the local Gold Rush AGI v3 interpreter."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


ROOM_REMAP_DESTINATION = 0x49
ROOM_REMAP_ALIAS = 0x7E
ROOM_REMAP_ALIASES = (0x7E, 0x7F, 0x80)
GR_KEY_MAP_SLOT_COUNT = 0x31
SQ2_KEY_MAP_SLOT_COUNT = 0x27
KEY_MAP_TEST_PICTURE = 1
KEY_MAP_TEST_STATUS = 7
KEY_MAP_TEST_KEY_WORD = ord("x")
MOTION_MODE_TEST_PICTURE = 1
MOTION_MODE_TEST_VIEW = 0
MOTION_MODE_TEST_GROUP = 0
MOTION_MODE_TEST_FRAME = 0
MOTION_MODE_TEST_START_X = 20
MOTION_MODE_TEST_TARGET_X = 50
MOTION_MODE_TEST_BASELINE_Y = 80
MOTION_MODE_TEST_STEP = 5
MOTION_MODE_TEST_COMPLETION_FLAG = 200
MOTION_MODE_TEST_PRIORITY = 15
MOTION_TICK_VAR = 0xF8
FRAME_GATE_TEST_PICTURE = 1
FRAME_GATE_EXACT4_VIEW = 177
FRAME_GATE_MORE4_VIEW = 39
FRAME_GATE_OBJECT = 10
FRAME_GATE_DIRECTION = 6
FRAME_GATE_FLAG = 0x14
FRAME_GATE_X = 50
FRAME_GATE_BASELINE_Y = 90
FRAME_GATE_PRIORITY = 15
FRAME_GATE_DIR_VAR = 0xF7
FRAME_GATE_TICK_VAR = 0xF6
GR_SAVE_TEST_PICTURE = 1
GR_SAVE_SIGNATURE_MESSAGE = "GR"
GR_SAVE_STEM = "SG"
GR_SAVE_DESCRIPTION = "codex gr probe"
GR_SAVE_SLOT = 1
GR_RESTORE_TEST_PICTURE = 1
GR_RESTORE_TEST_VIEW = 0
GR_RESTORE_TEST_GROUP = 0
GR_RESTORE_TEST_FRAME = 0
GR_RESTORE_SAVED_X = 50
GR_RESTORE_UNRESTORED_X = 90
GR_RESTORE_BASELINE_Y = 80
GR_RESTORE_PRIORITY = 15
GR_RESTORE_CONTROL = 15
GR_RESTORE_MARKER_FLAG = 0xC6
GR_RESTORE_VIEW_VAR = 0xE0
GR_RESTORE_GROUP_VAR = 0xE1
GR_RESTORE_FRAME_VAR = 0xE2
GR_RESTORE_X_VAR = 0xE3
GR_RESTORE_Y_VAR = 0xE4
GR_RESTORE_PRIORITY_VAR = 0xE5
GR_RESTORE_CONTROL_VAR = 0xE6
GR_RESTART_TEST_PICTURE = 1
GR_RESTART_PROMPT_MESSAGE = "?"
GR_RESTART_PROMPT_ROW = 5
GR_RESTART_PROMPT_LEFT = 0
GR_RESTART_PROMPT_RIGHT = 39
GR_RESTART_PROMPT_TOP = GR_RESTART_PROMPT_ROW * 8
GR_RESTART_PROMPT_BOTTOM = GR_RESTART_PROMPT_TOP + 7
GR_MENU_GATE_TEST_PICTURE = 1
GR_MENU_GATE_TEST_VIEW = 0
GR_MENU_GATE_TEST_GROUP = 0
GR_MENU_GATE_TEST_FRAME = 0
GR_MENU_GATE_ACCEPTED_X = 50
GR_MENU_GATE_BLOCKED_X = 90
GR_MENU_GATE_BASELINE_Y = 80
GR_MENU_GATE_PRIORITY = 15
GR_MENU_GATE_CONTROL = 15
GR_MENU_GATE_STATUS = 7
GR_MENU_GATE_INIT_FLAG = 0xC7
GR_MENU_GATE_VIEW_VAR = 0xD8
GR_MENU_GATE_GROUP_VAR = 0xD9
GR_MENU_GATE_FRAME_VAR = 0xDA
GR_MENU_GATE_X_VAR = 0xDB
GR_MENU_GATE_Y_VAR = 0xDC
GR_MENU_GATE_PRIORITY_VAR = 0xDD
GR_MENU_GATE_CONTROL_VAR = 0xDE
GR_SYNTHETIC_PICTURE_NO = 0
GR_SYNTHETIC_VIEW_NO = 0
GR_SYNTHETIC_GROUP_NO = 0
GR_SYNTHETIC_FRAME_NO = 0
GR_SYNTHETIC_VIEW_X = 20
GR_SYNTHETIC_VIEW_BASELINE_Y = 80
GR_SYNTHETIC_VIEW_PRIORITY = 15
GR_SYNTHETIC_VOLUME = 1
GR_SYNTHETIC_PICTURE_PAYLOAD = bytes([0xF0, 0x01, 0xF8, 0x50, 0x50, 0xFF])
GR_SYNTHETIC_VIEW_PAYLOAD = bytes(
    [
        0x00,
        0x00,
        0x01,
        0x00,
        0x00,
        0x07,
        0x00,
        0x01,
        0x03,
        0x00,
        0x04,
        0x04,
        0x00,
        0x44,
        0x00,
        0x44,
        0x00,
        0x44,
        0x00,
        0x44,
        0x00,
    ]
)
GR_ACTION_51_MODE_STORE_OFFSET = 0x707F
GR_ACTION_51_MODE_STORE_CONTEXT_OFFSET = GR_ACTION_51_MODE_STORE_OFFSET - 3
GR_ACTION_51_MODE_STORE_CONTEXT = b"\xc6\x45\x22\x03"
DEFAULT_FIXTURE_ROOT = Path("build/gr-v3-behavior/room-remap-fixtures")
DEFAULT_OUTPUT = Path("build/gr-v3-behavior/room_remap_001.json")
DEFAULT_SNAPSHOT_RAW = Path("build/gr-v3-behavior/snapshot/room_remap.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/gr-v3-behavior/snapshot/room_remap.qcow2")


@dataclass(frozen=True)
class RoomRemapCase:
    label: str
    target_room: int
    fixture: Path
    dos_dir: str
    capture: Path


@dataclass(frozen=True)
class ProbeCase:
    label: str
    fixture: Path
    dos_dir: str
    capture: Path
    post_launch_keys: str = ""
    post_launch_wait: float = 0.0
    post_launch_key_delay: float = 0.03
    post_launch_after_text_wait: float = 0.0
    post_launch_key_names: list[str] | None = None


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def suffixed_path(path: Path, suffix: str) -> Path:
    return path.with_name(f"{path.stem}_{suffix}{path.suffix}")


def byte_action(opcode: int, *operands: int) -> bytes:
    values = [opcode, *operands]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("logic action bytes must fit in one byte")
    return bytes(values)


def flag_set_condition(flag_no: int) -> bytes:
    if not 0 <= flag_no <= 0xFF:
        raise ValueError("flag number must fit in one byte")
    return bytes([0x07, flag_no])


def switch_room_payload(room_no: int, guard_var: int = 0xFA) -> bytes:
    from qemu_fixture import assignn_action, if_then, logic_resource, var_eq_imm_condition

    if not 0 <= room_no <= 0xFF:
        raise ValueError("room number must fit in one byte")
    if not 0 <= guard_var <= 0xFF:
        raise ValueError("guard variable must fit in one byte")
    switch_once = assignn_action(guard_var, 1) + bytes([0x12, room_no])
    return logic_resource(if_then(var_eq_imm_condition(guard_var, 0), switch_once) + bytes([0x17, 0x00, 0x00]))


def key_map_capacity_payload(
    *,
    picture_no: int = KEY_MAP_TEST_PICTURE,
    target_key_word: int = KEY_MAP_TEST_KEY_WORD,
    status_index: int = KEY_MAP_TEST_STATUS,
    dummy_count: int = GR_KEY_MAP_SLOT_COUNT - 1,
    init_flag: int = 0xF9,
) -> bytes:
    from qemu_fixture import (
        end_action,
        if_then,
        load_show_picture_actions,
        logic_resource,
        map_key_event_action,
        not_flag_set_condition,
        set_flag_action,
        status_byte_condition,
    )

    if not 0 <= dummy_count < GR_KEY_MAP_SLOT_COUNT:
        raise ValueError("dummy mapping count must leave room for the target mapping")
    if not 0 <= init_flag <= 0xFF:
        raise ValueError("init flag must fit in one byte")

    setup = bytearray()
    for index in range(dummy_count):
        setup.extend(map_key_event_action(0x0101 + index, status_index + 1))
    setup.extend(map_key_event_action(target_key_word, status_index))
    setup.extend(set_flag_action(init_flag))

    per_cycle = if_then(status_byte_condition(status_index), load_show_picture_actions(picture_no))
    return logic_resource(if_then(not_flag_set_condition(init_flag), bytes(setup)) + per_cycle + end_action())


def motion_mode_dispatch_payload(
    *,
    picture_no: int = MOTION_MODE_TEST_PICTURE,
    view_no: int = MOTION_MODE_TEST_VIEW,
    group_no: int = MOTION_MODE_TEST_GROUP,
    frame_no: int = MOTION_MODE_TEST_FRAME,
    start_x: int = MOTION_MODE_TEST_START_X,
    target_x: int = MOTION_MODE_TEST_TARGET_X,
    baseline_y: int = MOTION_MODE_TEST_BASELINE_Y,
    step_size: int = MOTION_MODE_TEST_STEP,
    completion_flag: int = MOTION_MODE_TEST_COMPLETION_FLAG,
    priority: int = MOTION_MODE_TEST_PRIORITY,
    moving: bool = True,
) -> bytes:
    from qemu_fixture import (
        assignn_action,
        move_object_to_action,
        persistent_object_once_logic_payload,
        set_object_tick_from_var_action,
    )

    post_activate = b""
    if moving:
        post_activate = (
            assignn_action(MOTION_TICK_VAR, 1)
            + set_object_tick_from_var_action(0, MOTION_TICK_VAR)
            + move_object_to_action(0, target_x, baseline_y, step_size, completion_flag)
        )
    return persistent_object_once_logic_payload(
        picture_no,
        view_no,
        group_no,
        frame_no,
        start_x,
        baseline_y,
        priority,
        object_no=0,
        post_activate_actions=post_activate,
    )


def gr_save_extract_payload(
    *,
    picture_no: int = GR_SAVE_TEST_PICTURE,
    signature_message: str = GR_SAVE_SIGNATURE_MESSAGE,
    verify_signature: bool = False,
) -> bytes:
    from qemu_fixture import load_show_picture_actions, logic_resource, self_loop

    if not 0 <= picture_no <= 0xFF:
        raise ValueError("picture number must fit in one byte")
    verify = bytes([0x8F, 0x01]) if verify_signature else b""
    code = load_show_picture_actions(picture_no) + verify + bytes([0x7D]) + self_loop()
    messages = [signature_message] if verify_signature else None
    return logic_resource(code, messages=messages)


def gr_restore_validation_var_setup(
    marker_x: int,
    *,
    view_no: int = GR_RESTORE_TEST_VIEW,
    group_no: int = GR_RESTORE_TEST_GROUP,
    frame_no: int = GR_RESTORE_TEST_FRAME,
    baseline_y: int = GR_RESTORE_BASELINE_Y,
    priority: int = GR_RESTORE_PRIORITY,
    control: int = GR_RESTORE_CONTROL,
) -> bytes:
    return (
        byte_action(0x03, GR_RESTORE_VIEW_VAR, view_no)
        + byte_action(0x03, GR_RESTORE_GROUP_VAR, group_no)
        + byte_action(0x03, GR_RESTORE_FRAME_VAR, frame_no)
        + byte_action(0x03, GR_RESTORE_X_VAR, marker_x)
        + byte_action(0x03, GR_RESTORE_Y_VAR, baseline_y)
        + byte_action(0x03, GR_RESTORE_PRIORITY_VAR, priority)
        + byte_action(0x03, GR_RESTORE_CONTROL_VAR, control)
    )


def gr_restore_validation_draw_from_vars() -> bytes:
    return byte_action(
        0x7B,
        GR_RESTORE_VIEW_VAR,
        GR_RESTORE_GROUP_VAR,
        GR_RESTORE_FRAME_VAR,
        GR_RESTORE_X_VAR,
        GR_RESTORE_Y_VAR,
        GR_RESTORE_PRIORITY_VAR,
        GR_RESTORE_CONTROL_VAR,
    )


def gr_signed_restore_success_branch(
    *,
    picture_no: int = GR_RESTORE_TEST_PICTURE,
    view_no: int = GR_RESTORE_TEST_VIEW,
) -> bytes:
    from qemu_fixture import load_show_picture_actions, self_loop

    return (
        load_show_picture_actions(picture_no)
        + byte_action(0x1E, view_no)
        + gr_restore_validation_draw_from_vars()
        + self_loop()
    )


def gr_signed_restore_save_payload(
    *,
    picture_no: int = GR_RESTORE_TEST_PICTURE,
    view_no: int = GR_RESTORE_TEST_VIEW,
    signature_message: str = GR_SAVE_SIGNATURE_MESSAGE,
) -> bytes:
    from qemu_fixture import load_show_picture_actions, logic_resource, self_loop, set_flag_action

    code = (
        load_show_picture_actions(picture_no)
        + byte_action(0x1E, view_no)
        + byte_action(0x8F, 0x01)
        + set_flag_action(GR_RESTORE_MARKER_FLAG)
        + gr_restore_validation_var_setup(GR_RESTORE_SAVED_X, view_no=view_no)
        + byte_action(0x7D)
        + byte_action(0x1A)
        + gr_restore_validation_draw_from_vars()
        + self_loop()
    )
    return logic_resource(code, messages=[signature_message])


def gr_signed_restore_restore_payload(
    *,
    picture_no: int = GR_RESTORE_TEST_PICTURE,
    view_no: int = GR_RESTORE_TEST_VIEW,
    signature_message: str = GR_SAVE_SIGNATURE_MESSAGE,
) -> bytes:
    from qemu_fixture import if_then, load_show_picture_actions, logic_resource, self_loop

    code = (
        if_then(
            flag_set_condition(GR_RESTORE_MARKER_FLAG),
            gr_signed_restore_success_branch(picture_no=picture_no, view_no=view_no),
        )
        + load_show_picture_actions(picture_no)
        + byte_action(0x1E, view_no)
        + byte_action(0x8F, 0x01)
        + gr_restore_validation_var_setup(GR_RESTORE_UNRESTORED_X, view_no=view_no)
        + byte_action(0x7E)
        + byte_action(0x1A)
        + gr_restore_validation_draw_from_vars()
        + self_loop()
    )
    return logic_resource(code, messages=[signature_message])


def gr_signed_restore_direct_payload(
    *,
    marker_x: int,
    picture_no: int = GR_RESTORE_TEST_PICTURE,
    view_no: int = GR_RESTORE_TEST_VIEW,
) -> bytes:
    from qemu_fixture import load_show_picture_actions, logic_resource, self_loop

    code = (
        load_show_picture_actions(picture_no)
        + byte_action(0x1E, view_no)
        + gr_restore_validation_var_setup(marker_x, view_no=view_no)
        + gr_restore_validation_draw_from_vars()
        + self_loop()
    )
    return logic_resource(code)


def gr_restart_prompt_marker_payload(
    *,
    marker_visible_before_restart: bool,
    include_restart: bool,
    picture_no: int = GR_RESTART_TEST_PICTURE,
    prompt_message: str = GR_RESTART_PROMPT_MESSAGE,
) -> bytes:
    from qemu_fixture import load_show_picture_actions, logic_resource, self_loop

    code = (
        load_show_picture_actions(picture_no)
        + byte_action(0x6C, 0x01)
        + byte_action(0x6F, 0x00, GR_RESTART_PROMPT_ROW, 0x16)
        + byte_action(0x78 if marker_visible_before_restart else 0x77)
    )
    if include_restart:
        code += byte_action(0x80)
    return logic_resource(code + self_loop(), messages=[prompt_message])


def gr_menu_gate_marker_var_setup(
    marker_x: int,
    *,
    view_no: int = GR_MENU_GATE_TEST_VIEW,
    group_no: int = GR_MENU_GATE_TEST_GROUP,
    frame_no: int = GR_MENU_GATE_TEST_FRAME,
    baseline_y: int = GR_MENU_GATE_BASELINE_Y,
    priority: int = GR_MENU_GATE_PRIORITY,
    control: int = GR_MENU_GATE_CONTROL,
) -> bytes:
    return (
        byte_action(0x03, GR_MENU_GATE_VIEW_VAR, view_no)
        + byte_action(0x03, GR_MENU_GATE_GROUP_VAR, group_no)
        + byte_action(0x03, GR_MENU_GATE_FRAME_VAR, frame_no)
        + byte_action(0x03, GR_MENU_GATE_X_VAR, marker_x)
        + byte_action(0x03, GR_MENU_GATE_Y_VAR, baseline_y)
        + byte_action(0x03, GR_MENU_GATE_PRIORITY_VAR, priority)
        + byte_action(0x03, GR_MENU_GATE_CONTROL_VAR, control)
    )


def gr_menu_gate_draw_marker_from_vars() -> bytes:
    return byte_action(
        0x7B,
        GR_MENU_GATE_VIEW_VAR,
        GR_MENU_GATE_GROUP_VAR,
        GR_MENU_GATE_FRAME_VAR,
        GR_MENU_GATE_X_VAR,
        GR_MENU_GATE_Y_VAR,
        GR_MENU_GATE_PRIORITY_VAR,
        GR_MENU_GATE_CONTROL_VAR,
    )


def gr_menu_gate_marker_draw_actions(
    marker_x: int,
    *,
    picture_no: int = GR_MENU_GATE_TEST_PICTURE,
    view_no: int = GR_MENU_GATE_TEST_VIEW,
) -> bytes:
    from qemu_fixture import load_show_picture_actions

    return (
        load_show_picture_actions(picture_no)
        + byte_action(0x1E, view_no)
        + gr_menu_gate_marker_var_setup(marker_x, view_no=view_no)
        + gr_menu_gate_draw_marker_from_vars()
    )


def gr_menu_gate_direct_payload(
    *,
    marker_x: int,
    picture_no: int = GR_MENU_GATE_TEST_PICTURE,
    view_no: int = GR_MENU_GATE_TEST_VIEW,
) -> bytes:
    from qemu_fixture import logic_resource, self_loop

    return logic_resource(
        gr_menu_gate_marker_draw_actions(marker_x, picture_no=picture_no, view_no=view_no)
        + self_loop()
    )


def gr_menu_gate_payload(
    *,
    gate_value: int,
    picture_no: int = GR_MENU_GATE_TEST_PICTURE,
    view_no: int = GR_MENU_GATE_TEST_VIEW,
    status_index: int = GR_MENU_GATE_STATUS,
    init_flag: int = GR_MENU_GATE_INIT_FLAG,
) -> bytes:
    from qemu_fixture import (
        end_action,
        if_then,
        logic_resource,
        not_flag_set_condition,
        set_flag_action,
        status_byte_condition,
    )

    if not 0 <= gate_value <= 0xFF:
        raise ValueError("GR menu gate value must fit in one byte")
    setup = (
        byte_action(0x9C, 0x01)
        + byte_action(0x9D, 0x02, status_index)
        + byte_action(0x9E)
        + byte_action(0xB1, gate_value)
        + set_flag_action(0x0E)
        + byte_action(0xA1)
        + set_flag_action(init_flag)
    )
    accepted = gr_menu_gate_marker_draw_actions(
        GR_MENU_GATE_ACCEPTED_X,
        picture_no=picture_no,
        view_no=view_no,
    )
    blocked = gr_menu_gate_marker_draw_actions(
        GR_MENU_GATE_BLOCKED_X,
        picture_no=picture_no,
        view_no=view_no,
    )
    code = (
        if_then(not_flag_set_condition(init_flag), setup)
        + if_then(status_byte_condition(status_index), accepted)
        + if_then(bytes([0xFD]) + status_byte_condition(status_index), blocked)
        + end_action()
    )
    return logic_resource(code, messages=["FILE", "OPEN"])


def frame_selection_gate_payload(
    *,
    picture_no: int = FRAME_GATE_TEST_PICTURE,
    view_no: int,
    initial_group: int,
    set_gate_flag: bool,
    object_no: int = FRAME_GATE_OBJECT,
    direction: int = FRAME_GATE_DIRECTION,
    x: int = FRAME_GATE_X,
    baseline_y: int = FRAME_GATE_BASELINE_Y,
    priority: int = FRAME_GATE_PRIORITY,
) -> bytes:
    from qemu_fixture import (
        assignn_action,
        persistent_object_once_logic_payload,
        set_flag_action,
        set_object_tick_from_var_action,
    )

    values = [view_no, initial_group, object_no, direction, x, baseline_y, priority]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("frame-selection gate operands must fit in one byte")

    post_activate = b""
    if set_gate_flag:
        post_activate += set_flag_action(FRAME_GATE_FLAG)
    post_activate += (
        assignn_action(FRAME_GATE_DIR_VAR, direction)
        + bytes([0x56, object_no, FRAME_GATE_DIR_VAR])
        + assignn_action(FRAME_GATE_TICK_VAR, 1)
        + set_object_tick_from_var_action(object_no, FRAME_GATE_TICK_VAR)
        + bytes([0x2E, object_no])
    )
    return persistent_object_once_logic_payload(
        picture_no,
        view_no,
        initial_group,
        0,
        x,
        baseline_y,
        priority,
        object_no=object_no,
        post_activate_actions=post_activate,
    )


def frame_selection_control_payload(
    *,
    picture_no: int = FRAME_GATE_TEST_PICTURE,
    view_no: int,
    group_no: int,
    object_no: int = FRAME_GATE_OBJECT,
    x: int = FRAME_GATE_X,
    baseline_y: int = FRAME_GATE_BASELINE_Y,
    priority: int = FRAME_GATE_PRIORITY,
) -> bytes:
    from qemu_fixture import persistent_object_once_logic_payload

    values = [view_no, group_no, object_no, x, baseline_y, priority]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("frame-selection control operands must fit in one byte")
    return persistent_object_once_logic_payload(
        picture_no,
        view_no,
        group_no,
        0,
        x,
        baseline_y,
        priority,
        object_no=object_no,
    )


def patch_gr_action_51_to_seed_mode4(fixture: Path) -> None:
    """Instrument a copied GR interpreter so action 0x51 writes mode 4.

    This intentionally patches only generated fixture copies. The byte at
    image/file offset 0x707f is the immediate in ``mov byte [di+0x22],0x03``
    inside GR action 0x51, as observed in the local flat executable.
    """

    def u16le(data: bytes, offset: int) -> int:
        return data[offset] | (data[offset + 1] << 8)

    agi_path = fixture / "AGI"
    data = bytearray(agi_path.read_bytes())
    image_base = u16le(data, 0x08) * 16 if len(data) >= 0x20 and data[:2] == b"MZ" else 0
    start = image_base + GR_ACTION_51_MODE_STORE_CONTEXT_OFFSET
    end = start + len(GR_ACTION_51_MODE_STORE_CONTEXT)
    if bytes(data[start:end]) != GR_ACTION_51_MODE_STORE_CONTEXT:
        actual = bytes(data[start:end]).hex()
        expected = GR_ACTION_51_MODE_STORE_CONTEXT.hex()
        raise ValueError(
            f"unexpected GR action 0x51 mode-store bytes at file offset {start:#x}: "
            f"{actual} != {expected}"
        )
    data[image_base + GR_ACTION_51_MODE_STORE_OFFSET] = 0x04
    agi_path.write_bytes(bytes(data))


def build_direct_draw_fixture(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int,
    dos_prefix: str = "GRD",
) -> ProbeCase:
    from qemu_fixture import build_v3_logic_fixture, picture_logic_payload

    fixture_root.mkdir(parents=True, exist_ok=True)
    fixture = fixture_root / "direct_draw"
    build_v3_logic_fixture(picture_logic_payload(picture_no), fixture, game_dir=game_dir, logic_no=0)
    return ProbeCase("direct_draw", fixture, f"{dos_prefix}0", fixture / "qemu_capture.ppm")


def build_motion_mode_4_fixtures(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int = MOTION_MODE_TEST_PICTURE,
    dos_prefix: str = "GRM",
) -> list[ProbeCase]:
    from qemu_fixture import build_v3_logic_fixture

    fixture_root.mkdir(parents=True, exist_ok=True)

    stationary_fixture = fixture_root / "stationary_control"
    build_v3_logic_fixture(
        motion_mode_dispatch_payload(picture_no=picture_no, moving=False),
        stationary_fixture,
        game_dir=game_dir,
        logic_no=0,
    )

    mode3_fixture = fixture_root / "mode3_move_object_to"
    build_v3_logic_fixture(
        motion_mode_dispatch_payload(picture_no=picture_no, moving=True),
        mode3_fixture,
        game_dir=game_dir,
        logic_no=0,
    )

    mode4_fixture = fixture_root / "mode4_instrumented_move_object_to"
    build_v3_logic_fixture(
        motion_mode_dispatch_payload(picture_no=picture_no, moving=True),
        mode4_fixture,
        game_dir=game_dir,
        logic_no=0,
    )
    patch_gr_action_51_to_seed_mode4(mode4_fixture)

    return [
        ProbeCase("stationary_control", stationary_fixture, f"{dos_prefix}0", stationary_fixture / "qemu_capture.ppm"),
        ProbeCase("mode3_move_object_to", mode3_fixture, f"{dos_prefix}1", mode3_fixture / "qemu_capture.ppm"),
        ProbeCase(
            "mode4_instrumented_move_object_to",
            mode4_fixture,
            f"{dos_prefix}2",
            mode4_fixture / "qemu_capture.ppm",
        ),
    ]


def build_frame_selection_gate_fixtures(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int = FRAME_GATE_TEST_PICTURE,
    dos_prefix: str = "GRF",
) -> list[ProbeCase]:
    from qemu_fixture import build_v3_logic_fixture

    fixture_root.mkdir(parents=True, exist_ok=True)
    specs = [
        (
            "exact4_group0_control",
            frame_selection_control_payload(
                picture_no=picture_no,
                view_no=FRAME_GATE_EXACT4_VIEW,
                group_no=0,
            ),
        ),
        (
            "exact4_group1_control",
            frame_selection_control_payload(
                picture_no=picture_no,
                view_no=FRAME_GATE_EXACT4_VIEW,
                group_no=1,
            ),
        ),
        (
            "exact4_flag_clear",
            frame_selection_gate_payload(
                picture_no=picture_no,
                view_no=FRAME_GATE_EXACT4_VIEW,
                initial_group=0,
                set_gate_flag=False,
            ),
        ),
        (
            "exact4_flag_set",
            frame_selection_gate_payload(
                picture_no=picture_no,
                view_no=FRAME_GATE_EXACT4_VIEW,
                initial_group=0,
                set_gate_flag=True,
            ),
        ),
        (
            "more4_group0_control",
            frame_selection_control_payload(
                picture_no=picture_no,
                view_no=FRAME_GATE_MORE4_VIEW,
                group_no=0,
            ),
        ),
        (
            "more4_group1_control",
            frame_selection_control_payload(
                picture_no=picture_no,
                view_no=FRAME_GATE_MORE4_VIEW,
                group_no=1,
            ),
        ),
        (
            "more4_flag_clear",
            frame_selection_gate_payload(
                picture_no=picture_no,
                view_no=FRAME_GATE_MORE4_VIEW,
                initial_group=0,
                set_gate_flag=False,
            ),
        ),
        (
            "more4_flag_set",
            frame_selection_gate_payload(
                picture_no=picture_no,
                view_no=FRAME_GATE_MORE4_VIEW,
                initial_group=0,
                set_gate_flag=True,
            ),
        ),
    ]

    cases: list[ProbeCase] = []
    for index, (label, payload) in enumerate(specs):
        fixture = fixture_root / label
        build_v3_logic_fixture(payload, fixture, game_dir=game_dir, logic_no=0)
        cases.append(ProbeCase(label, fixture, f"{dos_prefix}{index}", fixture / "qemu_capture.ppm"))
    return cases


def remove_existing_gr_save_files(fixture: Path, *, save_stem: str = GR_SAVE_STEM) -> None:
    for pattern in (f"{save_stem}.*", "GRSG.*", "SG.*"):
        for path in fixture.glob(pattern):
            if path.is_file():
                path.unlink()


def build_gr_save_extract_fixture(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int = GR_SAVE_TEST_PICTURE,
    dos_prefix: str = "GRS",
    verify_signature: bool = False,
) -> ProbeCase:
    from qemu_fixture import build_v3_logic_fixture

    label = "save_xor_extract_signed" if verify_signature else "save_xor_extract"
    fixture = fixture_root / label
    build_v3_logic_fixture(
        gr_save_extract_payload(picture_no=picture_no, verify_signature=verify_signature),
        fixture,
        game_dir=game_dir,
        logic_no=0,
    )
    remove_existing_gr_save_files(fixture)
    return ProbeCase(label, fixture, f"{dos_prefix}0", fixture / "qemu_capture.ppm")


def build_gr_signed_restore_save_fixture(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int = GR_RESTORE_TEST_PICTURE,
    dos_prefix: str = "GRSR",
) -> ProbeCase:
    from qemu_fixture import build_v3_logic_fixture

    fixture = fixture_root / "signed_restore_save"
    build_v3_logic_fixture(
        gr_signed_restore_save_payload(picture_no=picture_no),
        fixture,
        game_dir=game_dir,
        logic_no=0,
    )
    remove_existing_gr_save_files(fixture, save_stem=f"{GR_SAVE_SIGNATURE_MESSAGE}{GR_SAVE_STEM}")
    return ProbeCase("signed_restore_save", fixture, f"{dos_prefix}0", fixture / "qemu_capture.ppm")


def build_gr_signed_restore_fixture(
    game_dir: Path,
    fixture_root: Path,
    save_input: Path,
    *,
    picture_no: int = GR_RESTORE_TEST_PICTURE,
    dos_prefix: str = "GRSR",
    slot: int = GR_SAVE_SLOT,
) -> ProbeCase:
    from qemu_fixture import build_v3_logic_fixture

    fixture = fixture_root / "signed_restore_from_save"
    build_v3_logic_fixture(
        gr_signed_restore_restore_payload(picture_no=picture_no),
        fixture,
        game_dir=game_dir,
        logic_no=0,
    )
    save_stem = f"{GR_SAVE_SIGNATURE_MESSAGE}{GR_SAVE_STEM}"
    remove_existing_gr_save_files(fixture, save_stem=save_stem)
    (fixture / f"{save_stem}.{slot}").write_bytes(save_input.read_bytes())
    return ProbeCase("signed_restore_from_save", fixture, f"{dos_prefix}1", fixture / "qemu_capture.ppm")


def build_gr_signed_restore_comparison_fixtures(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int = GR_RESTORE_TEST_PICTURE,
    dos_prefix: str = "GRSR",
) -> list[ProbeCase]:
    from qemu_fixture import build_v3_logic_fixture

    direct_fixture = fixture_root / "signed_restore_expected_direct"
    build_v3_logic_fixture(
        gr_signed_restore_direct_payload(marker_x=GR_RESTORE_SAVED_X, picture_no=picture_no),
        direct_fixture,
        game_dir=game_dir,
        logic_no=0,
    )

    unrestored_fixture = fixture_root / "signed_restore_unrestored_control"
    build_v3_logic_fixture(
        gr_signed_restore_direct_payload(marker_x=GR_RESTORE_UNRESTORED_X, picture_no=picture_no),
        unrestored_fixture,
        game_dir=game_dir,
        logic_no=0,
    )

    return [
        ProbeCase("signed_restore_expected_direct", direct_fixture, f"{dos_prefix}2", direct_fixture / "qemu_capture.ppm"),
        ProbeCase("signed_restore_unrestored_control", unrestored_fixture, f"{dos_prefix}3", unrestored_fixture / "qemu_capture.ppm"),
    ]


def build_gr_restart_prompt_marker_fixtures(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int = GR_RESTART_TEST_PICTURE,
    dos_prefix: str = "GRP",
) -> list[ProbeCase]:
    from qemu_fixture import build_v3_logic_fixture

    fixture_root.mkdir(parents=True, exist_ok=True)
    specs = [
        ("restart_hidden_control", False, False, None),
        ("restart_visible_control", True, False, None),
        ("restart_cancel_hidden", False, True, ["esc"]),
        ("restart_cancel_visible", True, True, ["esc"]),
    ]
    cases: list[ProbeCase] = []
    for index, (label, marker_visible, include_restart, key_names) in enumerate(specs):
        fixture = fixture_root / label
        build_v3_logic_fixture(
            gr_restart_prompt_marker_payload(
                marker_visible_before_restart=marker_visible,
                include_restart=include_restart,
                picture_no=picture_no,
            ),
            fixture,
            game_dir=game_dir,
            logic_no=0,
        )
        cases.append(
            ProbeCase(
                label,
                fixture,
                f"{dos_prefix}{index}",
                fixture / "qemu_capture.ppm",
                post_launch_wait=1.0 if key_names else 0.0,
                post_launch_key_delay=0.12,
                post_launch_key_names=key_names,
            )
        )
    return cases


def build_gr_menu_gate_fixtures(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int = GR_MENU_GATE_TEST_PICTURE,
    dos_prefix: str = "GRG",
) -> list[ProbeCase]:
    from qemu_fixture import build_v3_logic_fixture

    fixture_root.mkdir(parents=True, exist_ok=True)
    specs = [
        (
            "menu_gate_blocked_control",
            gr_menu_gate_direct_payload(
                marker_x=GR_MENU_GATE_BLOCKED_X,
                picture_no=picture_no,
            ),
            None,
        ),
        (
            "menu_gate_enabled_request",
            gr_menu_gate_payload(gate_value=1, picture_no=picture_no),
            None,
        ),
        (
            "menu_gate_disabled_request",
            gr_menu_gate_payload(gate_value=0, picture_no=picture_no),
            None,
        ),
    ]
    cases: list[ProbeCase] = []
    for index, (label, payload, keys) in enumerate(specs):
        fixture = fixture_root / label
        build_v3_logic_fixture(payload, fixture, game_dir=game_dir, logic_no=0)
        cases.append(
            ProbeCase(
                label,
                fixture,
                f"{dos_prefix}{index}",
                fixture / "qemu_capture.ppm",
                post_launch_keys=keys or "",
                post_launch_wait=1.0 if keys else 0.0,
                post_launch_key_delay=0.12,
                post_launch_after_text_wait=0.5 if keys else 0.0,
            )
        )
    return cases


def build_gr_synthetic_picture_view_fixtures(
    game_dir: Path,
    fixture_root: Path,
    *,
    dos_prefix: str = "GSP",
) -> list[ProbeCase]:
    from qemu_fixture import (
        build_v3_logic_fixture,
        build_v3_synthetic_picture_fixture,
        build_v3_synthetic_picture_view_fixture,
        logic_resource,
        self_loop,
    )

    fixture_root.mkdir(parents=True, exist_ok=True)

    blank_fixture = fixture_root / "synthetic_blank_control"
    build_v3_logic_fixture(
        logic_resource(self_loop()),
        blank_fixture,
        game_dir=game_dir,
        logic_no=0,
        volume=GR_SYNTHETIC_VOLUME,
    )

    picture_fixture = fixture_root / "synthetic_picture_only"
    build_v3_synthetic_picture_fixture(
        GR_SYNTHETIC_PICTURE_PAYLOAD,
        picture_fixture,
        picture_no=GR_SYNTHETIC_PICTURE_NO,
        game_dir=game_dir,
        volume=GR_SYNTHETIC_VOLUME,
    )

    view_fixture = fixture_root / "synthetic_picture_view"
    build_v3_synthetic_picture_view_fixture(
        GR_SYNTHETIC_PICTURE_PAYLOAD,
        GR_SYNTHETIC_PICTURE_NO,
        GR_SYNTHETIC_VIEW_NO,
        GR_SYNTHETIC_GROUP_NO,
        GR_SYNTHETIC_FRAME_NO,
        GR_SYNTHETIC_VIEW_X,
        GR_SYNTHETIC_VIEW_BASELINE_Y,
        GR_SYNTHETIC_VIEW_PRIORITY,
        view_fixture,
        view_payload_bytes=GR_SYNTHETIC_VIEW_PAYLOAD,
        game_dir=game_dir,
        volume=GR_SYNTHETIC_VOLUME,
    )

    return [
        ProbeCase("synthetic_blank_control", blank_fixture, f"{dos_prefix}0", blank_fixture / "qemu_capture.ppm"),
        ProbeCase("synthetic_picture_only", picture_fixture, f"{dos_prefix}1", picture_fixture / "qemu_capture.ppm"),
        ProbeCase("synthetic_picture_view", view_fixture, f"{dos_prefix}2", view_fixture / "qemu_capture.ppm"),
    ]


def build_room_remap_fixtures(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int = ROOM_REMAP_DESTINATION,
    dos_prefix: str = "GRR",
) -> list[RoomRemapCase]:
    from qemu_fixture import build_v3_logic_fixture, patch_v3_logic_resource, picture_logic_payload

    fixture_root.mkdir(parents=True, exist_ok=True)
    cases = [("direct_49", ROOM_REMAP_DESTINATION)]
    cases.extend((f"alias_{alias:02x}", alias) for alias in ROOM_REMAP_ALIASES)
    built: list[RoomRemapCase] = []
    for index, (label, target_room) in enumerate(cases):
        fixture = fixture_root / label
        build_v3_logic_fixture(switch_room_payload(target_room), fixture, game_dir=game_dir, logic_no=0)
        patch_v3_logic_resource(fixture, picture_logic_payload(picture_no), logic_no=ROOM_REMAP_DESTINATION)
        built.append(
            RoomRemapCase(
                label=label,
                target_room=target_room,
                fixture=fixture,
                dos_dir=f"{dos_prefix}{index}",
                capture=fixture / "qemu_capture.ppm",
            )
        )
    return built


def build_key_map_capacity_fixtures(
    game_dir: Path,
    fixture_root: Path,
    *,
    picture_no: int = KEY_MAP_TEST_PICTURE,
    dos_prefix: str = "GRK",
) -> list[ProbeCase]:
    from qemu_fixture import build_v3_logic_fixture, picture_logic_payload

    fixture_root.mkdir(parents=True, exist_ok=True)
    direct_fixture = fixture_root / "direct_picture"
    build_v3_logic_fixture(picture_logic_payload(picture_no), direct_fixture, game_dir=game_dir, logic_no=0)

    key_fixture = fixture_root / "slot_48_key_map"
    build_v3_logic_fixture(key_map_capacity_payload(picture_no=picture_no), key_fixture, game_dir=game_dir, logic_no=0)

    no_key_fixture = fixture_root / "slot_48_no_key"
    build_v3_logic_fixture(key_map_capacity_payload(picture_no=picture_no), no_key_fixture, game_dir=game_dir, logic_no=0)

    return [
        ProbeCase("direct_picture", direct_fixture, f"{dos_prefix}0", direct_fixture / "qemu_capture.ppm"),
        ProbeCase(
            "slot_48_key_map",
            key_fixture,
            f"{dos_prefix}1",
            key_fixture / "qemu_capture.ppm",
            post_launch_keys="x",
            post_launch_wait=1.0,
            post_launch_key_delay=0.12,
            post_launch_after_text_wait=0.5,
        ),
        ProbeCase("slot_48_no_key", no_key_fixture, f"{dos_prefix}2", no_key_fixture / "qemu_capture.ppm"),
    ]


def run_room_remap_qemu(
    cases: list[RoomRemapCase],
    *,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    boot_wait: float,
    draw_wait: float,
) -> dict[str, bool]:
    from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases

    qemu_cases = [
        SnapshotFixtureCase(case.dos_dir, case.fixture, case.capture)
        for case in cases
    ]
    build_snapshot_boot_disk(qemu_cases, snapshot_raw, snapshot_qcow)
    run_snapshot_qemu_cases(snapshot_qcow, qemu_cases, boot_wait, draw_wait)
    direct_capture = cases[0].capture.read_bytes()
    return {
        case.label: case.capture.read_bytes() == direct_capture
        for case in cases[1:]
    }


def run_qemu_cases(
    cases: list[ProbeCase],
    *,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    boot_wait: float,
    draw_wait: float,
) -> None:
    from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases

    qemu_cases = [
        SnapshotFixtureCase(
            case.dos_dir,
            case.fixture,
            case.capture,
            post_launch_keys=case.post_launch_keys,
            post_launch_wait=case.post_launch_wait,
            post_launch_key_delay=case.post_launch_key_delay,
            post_launch_after_text_wait=case.post_launch_after_text_wait,
            post_launch_key_names=case.post_launch_key_names,
        )
        for case in cases
    ]
    build_snapshot_boot_disk(qemu_cases, snapshot_raw, snapshot_qcow)
    run_snapshot_qemu_cases(snapshot_qcow, qemu_cases, boot_wait, draw_wait)


def prompt_marker_foreground_count(capture: Path) -> int:
    from compare_picture_capture import downsample_qemu_picture_nibbles
    from ppm_tools import read_ppm

    nibbles = downsample_qemu_picture_nibbles(read_ppm(capture))
    count = 0
    for y in range(GR_RESTART_PROMPT_TOP, GR_RESTART_PROMPT_BOTTOM + 1):
        row = y * 0xA0
        for x in range(GR_RESTART_PROMPT_LEFT, GR_RESTART_PROMPT_RIGHT + 1):
            if nibbles[row + x] != 0:
                count += 1
    return count


def run_gr_restart_prompt_marker_qemu(
    cases: list[ProbeCase],
    *,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    boot_wait: float,
    draw_wait: float,
) -> dict:
    run_qemu_cases(
        cases,
        snapshot_raw=snapshot_raw,
        snapshot_qcow=snapshot_qcow,
        boot_wait=boot_wait,
        draw_wait=draw_wait,
    )
    captures = {case.label: case.capture.read_bytes() for case in cases}
    foreground_counts = {
        case.label: prompt_marker_foreground_count(case.capture)
        for case in cases
    }
    capture_matches = {
        "hidden_cancel_matches_hidden_control": captures["restart_cancel_hidden"] == captures["restart_hidden_control"],
        "visible_cancel_matches_visible_control": captures["restart_cancel_visible"] == captures["restart_visible_control"],
        "visible_control_differs_hidden_control": captures["restart_visible_control"] != captures["restart_hidden_control"],
        "visible_cancel_differs_hidden_cancel": captures["restart_cancel_visible"] != captures["restart_cancel_hidden"],
    }
    checks = {
        "visible_control_has_prompt_pixels": (
            foreground_counts["restart_visible_control"] > foreground_counts["restart_hidden_control"]
        ),
        "hidden_cancel_matches_hidden_control_count": (
            foreground_counts["restart_cancel_hidden"] == foreground_counts["restart_hidden_control"]
        ),
        "visible_cancel_matches_visible_control_count": (
            foreground_counts["restart_cancel_visible"] == foreground_counts["restart_visible_control"]
        ),
        "visible_cancel_has_prompt_pixels": (
            foreground_counts["restart_cancel_visible"] > foreground_counts["restart_cancel_hidden"]
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "capture_matches": capture_matches,
        "prompt_foreground_counts": foreground_counts,
        "capture_sha256": {
            label: sha256_hex(data)
            for label, data in captures.items()
        },
        "snapshot_raw": str(snapshot_raw),
        "snapshot_qcow": str(snapshot_qcow),
    }


def run_gr_menu_gate_qemu(
    cases: list[ProbeCase],
    *,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    boot_wait: float,
    draw_wait: float,
) -> dict:
    run_qemu_cases(
        cases,
        snapshot_raw=snapshot_raw,
        snapshot_qcow=snapshot_qcow,
        boot_wait=boot_wait,
        draw_wait=draw_wait,
    )
    captures = {case.label: case.capture.read_bytes() for case in cases}
    comparisons = {
        "disabled_request_matches_blocked_control": (
            captures["menu_gate_disabled_request"] == captures["menu_gate_blocked_control"]
        ),
        "enabled_request_differs_blocked_control": (
            captures["menu_gate_enabled_request"] != captures["menu_gate_blocked_control"]
        ),
        "enabled_request_differs_disabled_request": (
            captures["menu_gate_enabled_request"] != captures["menu_gate_disabled_request"]
        ),
    }
    return {
        "passed": all(comparisons.values()),
        "comparisons": comparisons,
        "capture_sha256": {
            label: sha256_hex(data)
            for label, data in captures.items()
        },
        "snapshot_raw": str(snapshot_raw),
        "snapshot_qcow": str(snapshot_qcow),
    }


def differing_pixel_count(left: Path, right: Path) -> int:
    from ppm_tools import read_ppm

    left_image = read_ppm(left)
    right_image = read_ppm(right)
    if (
        left_image.width != right_image.width
        or left_image.height != right_image.height
        or len(left_image.rgb) != len(right_image.rgb)
    ):
        raise ValueError("captures have different dimensions")
    count = 0
    for index in range(0, len(left_image.rgb), 3):
        if left_image.rgb[index : index + 3] != right_image.rgb[index : index + 3]:
            count += 1
    return count


def capture_unique_color_count(path: Path) -> int:
    from ppm_tools import read_ppm, unique_colors

    return len(unique_colors(read_ppm(path)))


def run_gr_synthetic_picture_view_qemu(
    cases: list[ProbeCase],
    *,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    boot_wait: float,
    draw_wait: float,
) -> dict:
    run_qemu_cases(
        cases,
        snapshot_raw=snapshot_raw,
        snapshot_qcow=snapshot_qcow,
        boot_wait=boot_wait,
        draw_wait=draw_wait,
    )
    captures = {case.label: case.capture.read_bytes() for case in cases}
    diff_pixels = {
        "picture_vs_blank": differing_pixel_count(cases[1].capture, cases[0].capture),
        "picture_view_vs_picture": differing_pixel_count(cases[2].capture, cases[1].capture),
    }
    unique_color_counts = {
        case.label: capture_unique_color_count(case.capture)
        for case in cases
    }
    checks = {
        "picture_differs_blank_control": diff_pixels["picture_vs_blank"] > 0,
        "picture_view_differs_picture_only": diff_pixels["picture_view_vs_picture"] > 0,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "diff_pixels": diff_pixels,
        "unique_color_counts": unique_color_counts,
        "capture_sha256": {
            label: sha256_hex(data)
            for label, data in captures.items()
        },
        "snapshot_raw": str(snapshot_raw),
        "snapshot_qcow": str(snapshot_qcow),
    }


def run_gr_save_extract_qemu(
    case: ProbeCase,
    *,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    post_run_raw: Path,
    save_output: Path,
    boot_wait: float,
    draw_wait: float,
    path_prompt_wait: float,
    path_keys: str,
    slot_wait: float,
    slot_keys: str,
    description_wait: float,
    description: str,
    confirmation_wait: float,
    confirmation_keys: str,
    key_delay: float,
    save_stem: str,
    slot: int,
    expected_signature_prefix: str,
) -> dict:
    from agi_save import gr_v3_object_inventory_save_xor, load_save
    from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk
    from save_roundtrip_probe import convert_qcow_to_raw, extract_save, run_save_qemu_case

    qemu_case = SnapshotFixtureCase(case.dos_dir, case.fixture, case.capture)
    build_snapshot_boot_disk([qemu_case], snapshot_raw, snapshot_qcow)
    run_save_qemu_case(
        snapshot_qcow,
        case.dos_dir,
        case.capture,
        boot_wait,
        path_prompt_wait,
        path_keys,
        slot_wait,
        slot_keys,
        description_wait,
        description,
        True,
        confirmation_wait,
        confirmation_keys,
        key_delay,
        draw_wait,
    )
    convert_qcow_to_raw(snapshot_qcow, post_run_raw)
    extracted = extract_save(post_run_raw, case.dos_dir, save_stem, slot, save_output)
    parsed = load_save(extracted)
    encoded_block = parsed.blocks[2].data
    decoded_block = gr_v3_object_inventory_save_xor(encoded_block)

    expected_prefix = expected_signature_prefix.encode("ascii") + b"\0" if expected_signature_prefix else b"\0"
    signature_check_name = (
        "first_block_has_expected_signature_prefix"
        if expected_signature_prefix
        else "first_block_has_blank_signature_prefix"
    )
    checks = {
        "description_matches": parsed.description == description,
        signature_check_name: parsed.blocks[0].data.startswith(expected_prefix),
        "third_block_changes_when_decoded": decoded_block != encoded_block,
        "third_block_xor_round_trips": gr_v3_object_inventory_save_xor(decoded_block) == encoded_block,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "save_file": str(extracted),
        "description": parsed.description,
        "block_lengths": [block.length for block in parsed.blocks],
        "first_block_prefix_hex": parsed.blocks[0].data[:8].hex(),
        "third_block_encoded_prefix_hex": encoded_block[:24].hex(),
        "third_block_decoded_prefix_hex": decoded_block[:24].hex(),
        "third_block_encoded_sha256": sha256_hex(encoded_block),
        "third_block_decoded_sha256": sha256_hex(decoded_block),
        "snapshot_raw": str(snapshot_raw),
        "snapshot_qcow": str(snapshot_qcow),
        "post_run_raw": str(post_run_raw),
    }


def run_gr_signed_restore_qemu(
    *,
    game_dir: Path,
    fixture_root: Path,
    picture_no: int,
    dos_prefix: str,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    post_run_raw: Path,
    save_output: Path,
    boot_wait: float,
    draw_wait: float,
    path_prompt_wait: float,
    path_keys: str,
    slot_wait: float,
    slot_keys: str,
    description_wait: float,
    description: str,
    confirmation_wait: float,
    confirmation_keys: str,
    key_delay: float,
    slot: int,
) -> dict:
    from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk
    from save_roundtrip_probe import run_restore_qemu_case

    save_stem = f"{GR_SAVE_SIGNATURE_MESSAGE}{GR_SAVE_STEM}"
    save_case = build_gr_signed_restore_save_fixture(
        game_dir,
        fixture_root,
        picture_no=picture_no,
        dos_prefix=dos_prefix,
    )
    save_result = run_gr_save_extract_qemu(
        save_case,
        snapshot_raw=snapshot_raw,
        snapshot_qcow=snapshot_qcow,
        post_run_raw=post_run_raw,
        save_output=save_output,
        boot_wait=boot_wait,
        draw_wait=draw_wait,
        path_prompt_wait=path_prompt_wait,
        path_keys=path_keys,
        slot_wait=slot_wait,
        slot_keys=slot_keys,
        description_wait=description_wait,
        description=description,
        confirmation_wait=confirmation_wait,
        confirmation_keys=confirmation_keys,
        key_delay=key_delay,
        save_stem=save_stem,
        slot=slot,
        expected_signature_prefix=GR_SAVE_SIGNATURE_MESSAGE,
    )

    restore_case = build_gr_signed_restore_fixture(
        game_dir,
        fixture_root,
        Path(save_result["save_file"]),
        picture_no=picture_no,
        dos_prefix=dos_prefix,
        slot=slot,
    )
    comparison_cases = build_gr_signed_restore_comparison_fixtures(
        game_dir,
        fixture_root,
        picture_no=picture_no,
        dos_prefix=dos_prefix,
    )

    comparison_snapshot_raw = suffixed_path(snapshot_raw, "comparison")
    comparison_snapshot_qcow = suffixed_path(snapshot_qcow, "comparison")
    run_qemu_cases(
        comparison_cases,
        snapshot_raw=comparison_snapshot_raw,
        snapshot_qcow=comparison_snapshot_qcow,
        boot_wait=boot_wait,
        draw_wait=draw_wait,
    )

    restore_snapshot_raw = suffixed_path(snapshot_raw, "restore")
    restore_snapshot_qcow = suffixed_path(snapshot_qcow, "restore")
    qemu_case = SnapshotFixtureCase(restore_case.dos_dir, restore_case.fixture, restore_case.capture)
    build_snapshot_boot_disk([qemu_case], restore_snapshot_raw, restore_snapshot_qcow)
    run_restore_qemu_case(
        restore_snapshot_qcow,
        restore_case.dos_dir,
        restore_case.capture,
        boot_wait,
        path_prompt_wait,
        path_keys,
        slot_wait,
        slot_keys,
        confirmation_wait,
        confirmation_keys,
        key_delay,
        draw_wait,
    )

    direct_capture = comparison_cases[0].capture.read_bytes()
    unrestored_capture = comparison_cases[1].capture.read_bytes()
    restored_capture = restore_case.capture.read_bytes()
    comparisons = {
        "restored_matches_expected_direct": restored_capture == direct_capture,
        "restored_differs_unrestored_control": restored_capture != unrestored_capture,
        "expected_direct_differs_unrestored_control": direct_capture != unrestored_capture,
    }
    checks = {
        "save_generation_passed": bool(save_result["passed"]),
        **comparisons,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "comparisons": comparisons,
        "save_generation": save_result,
        "cases": [
            probe_case_report(save_case),
            probe_case_report(restore_case),
            *(probe_case_report(case) for case in comparison_cases),
        ],
        "capture_sha256": {
            restore_case.label: sha256_hex(restored_capture),
            comparison_cases[0].label: sha256_hex(direct_capture),
            comparison_cases[1].label: sha256_hex(unrestored_capture),
        },
        "snapshot_raw": str(snapshot_raw),
        "snapshot_qcow": str(snapshot_qcow),
        "comparison_snapshot_raw": str(comparison_snapshot_raw),
        "comparison_snapshot_qcow": str(comparison_snapshot_qcow),
        "restore_snapshot_raw": str(restore_snapshot_raw),
        "restore_snapshot_qcow": str(restore_snapshot_qcow),
    }


def write_report(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def case_report(case: RoomRemapCase) -> dict:
    return {
        "label": case.label,
        "target_room": case.target_room,
        "fixture": str(case.fixture),
        "dos_dir": case.dos_dir,
        "capture": str(case.capture),
    }


def probe_case_report(case: ProbeCase) -> dict:
    return {
        "label": case.label,
        "fixture": str(case.fixture),
        "dos_dir": case.dos_dir,
        "capture": str(case.capture),
        "post_launch_keys": case.post_launch_keys,
        "post_launch_key_names": case.post_launch_key_names,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--probe",
        choices=(
            "room-remap",
            "direct-draw",
            "key-map-capacity",
            "motion-mode-4",
            "frame-selection-gate",
            "save-xor-extract",
            "signed-restore-roundtrip",
            "restart-prompt-marker",
            "menu-gate",
            "synthetic-picture-view",
        ),
        default="room-remap",
    )
    parser.add_argument("--game-dir", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--picture", type=int)
    parser.add_argument("--dos-prefix", default="GRR")
    parser.add_argument("--run-qemu", action="store_true")
    parser.add_argument("--snapshot-raw", type=Path, default=DEFAULT_SNAPSHOT_RAW)
    parser.add_argument("--snapshot-qcow", type=Path, default=DEFAULT_SNAPSHOT_QCOW)
    parser.add_argument("--post-run-raw", type=Path, default=Path("build/gr-v3-behavior/snapshot/gr_save_after.raw"))
    parser.add_argument("--save-output", type=Path)
    parser.add_argument("--description", default=GR_SAVE_DESCRIPTION)
    parser.add_argument("--path-keys", default="\n")
    parser.add_argument("--slot-keys", default="\n")
    parser.add_argument("--confirmation-keys", default="\n")
    parser.add_argument("--path-prompt-wait", type=float, default=2.0)
    parser.add_argument("--slot-wait", type=float, default=1.0)
    parser.add_argument("--description-wait", type=float, default=1.0)
    parser.add_argument("--confirmation-wait", type=float, default=1.0)
    parser.add_argument("--key-delay", type=float, default=0.08)
    parser.add_argument("--save-stem")
    parser.add_argument("--verify-signature", action="store_true")
    parser.add_argument("--slot", type=int, default=GR_SAVE_SLOT)
    parser.add_argument("--boot-wait", type=float, default=5.0)
    parser.add_argument("--draw-wait", type=float, default=8.0)
    args = parser.parse_args()

    if args.probe == "synthetic-picture-view":
        cases = build_gr_synthetic_picture_view_fixtures(
            args.game_dir,
            args.fixture_root,
            dos_prefix=args.dos_prefix,
        )
        result: dict = {
            "probe": "gr_v3_synthetic_picture_view_fixture",
            "game_dir": str(args.game_dir),
            "picture": GR_SYNTHETIC_PICTURE_NO,
            "view": GR_SYNTHETIC_VIEW_NO,
            "group": GR_SYNTHETIC_GROUP_NO,
            "frame": GR_SYNTHETIC_FRAME_NO,
            "view_x": GR_SYNTHETIC_VIEW_X,
            "view_baseline_y": GR_SYNTHETIC_VIEW_BASELINE_Y,
            "view_priority": GR_SYNTHETIC_VIEW_PRIORITY,
            "volume": GR_SYNTHETIC_VOLUME,
            "picture_payload_hex": GR_SYNTHETIC_PICTURE_PAYLOAD.hex(),
            "view_payload_hex": GR_SYNTHETIC_VIEW_PAYLOAD.hex(),
            "expected_checks": {
                "picture_differs_blank_control": True,
                "picture_view_differs_picture_only": True,
            },
            "cases": [probe_case_report(case) for case in cases],
            "qemu": {"ran": False},
        }
        if args.run_qemu:
            qemu_result = run_gr_synthetic_picture_view_qemu(
                cases,
                snapshot_raw=args.snapshot_raw,
                snapshot_qcow=args.snapshot_qcow,
                boot_wait=args.boot_wait,
                draw_wait=args.draw_wait,
            )
            result["qemu"] = {
                "ran": True,
                **qemu_result,
            }
        write_report(args.output, result)
        print(args.output)
        if args.run_qemu and not result["qemu"]["passed"]:
            return 1
        return 0

    if args.probe == "menu-gate":
        picture_no = args.picture if args.picture is not None else GR_MENU_GATE_TEST_PICTURE
        cases = build_gr_menu_gate_fixtures(
            args.game_dir,
            args.fixture_root,
            picture_no=picture_no,
            dos_prefix=args.dos_prefix,
        )
        result: dict = {
            "probe": "gr_v3_menu_interaction_gate",
            "game_dir": str(args.game_dir),
            "picture": picture_no,
            "view": GR_MENU_GATE_TEST_VIEW,
            "status_index": GR_MENU_GATE_STATUS,
            "accepted_marker_x": GR_MENU_GATE_ACCEPTED_X,
            "blocked_marker_x": GR_MENU_GATE_BLOCKED_X,
            "expected_matches": {
                "disabled_request_matches_blocked_control": True,
                "enabled_request_differs_blocked_control": True,
                "enabled_request_differs_disabled_request": True,
            },
            "cases": [probe_case_report(case) for case in cases],
            "qemu": {"ran": False},
        }
        if args.run_qemu:
            qemu_result = run_gr_menu_gate_qemu(
                cases,
                snapshot_raw=args.snapshot_raw,
                snapshot_qcow=args.snapshot_qcow,
                boot_wait=args.boot_wait,
                draw_wait=args.draw_wait,
            )
            result["qemu"] = {
                "ran": True,
                **qemu_result,
            }
            result["qemu"]["expected_matches"] = result["expected_matches"]
        write_report(args.output, result)
        print(args.output)
        if args.run_qemu and not result["qemu"]["passed"]:
            return 1
        return 0

    if args.probe == "restart-prompt-marker":
        picture_no = args.picture if args.picture is not None else GR_RESTART_TEST_PICTURE
        cases = build_gr_restart_prompt_marker_fixtures(
            args.game_dir,
            args.fixture_root,
            picture_no=picture_no,
            dos_prefix=args.dos_prefix,
        )
        result: dict = {
            "probe": "gr_v3_restart_prompt_marker_cancel_redraw",
            "game_dir": str(args.game_dir),
            "picture": picture_no,
            "prompt_message": GR_RESTART_PROMPT_MESSAGE,
            "prompt_rect": {
                "left": GR_RESTART_PROMPT_LEFT,
                "top": GR_RESTART_PROMPT_TOP,
                "right": GR_RESTART_PROMPT_RIGHT,
                "bottom": GR_RESTART_PROMPT_BOTTOM,
            },
            "cases": [probe_case_report(case) for case in cases],
            "qemu": {"ran": False},
        }
        if args.run_qemu:
            result["qemu"] = {
                "ran": True,
                **run_gr_restart_prompt_marker_qemu(
                    cases,
                    snapshot_raw=args.snapshot_raw,
                    snapshot_qcow=args.snapshot_qcow,
                    boot_wait=args.boot_wait,
                    draw_wait=args.draw_wait,
                ),
            }
        write_report(args.output, result)
        print(args.output)
        if args.run_qemu and not result["qemu"]["passed"]:
            return 1
        return 0

    if args.probe == "signed-restore-roundtrip":
        picture_no = args.picture if args.picture is not None else GR_RESTORE_TEST_PICTURE
        save_stem = f"{GR_SAVE_SIGNATURE_MESSAGE}{GR_SAVE_STEM}"
        save_output = args.save_output
        if save_output is None:
            save_output = Path(f"build/gr-v3-behavior/{save_stem}_restore.{args.slot}")
        save_case = build_gr_signed_restore_save_fixture(
            args.game_dir,
            args.fixture_root,
            picture_no=picture_no,
            dos_prefix=args.dos_prefix,
        )
        result: dict = {
            "probe": "gr_v3_signed_restore_roundtrip",
            "game_dir": str(args.game_dir),
            "picture": picture_no,
            "view": GR_RESTORE_TEST_VIEW,
            "signature_prefix": GR_SAVE_SIGNATURE_MESSAGE,
            "save_stem": save_stem,
            "slot": args.slot,
            "saved_marker_x": GR_RESTORE_SAVED_X,
            "unrestored_marker_x": GR_RESTORE_UNRESTORED_X,
            "cases": [probe_case_report(save_case)],
            "qemu": {"ran": False},
        }
        if args.run_qemu:
            result["qemu"] = {
                "ran": True,
                **run_gr_signed_restore_qemu(
                    game_dir=args.game_dir,
                    fixture_root=args.fixture_root,
                    picture_no=picture_no,
                    dos_prefix=args.dos_prefix,
                    snapshot_raw=args.snapshot_raw,
                    snapshot_qcow=args.snapshot_qcow,
                    post_run_raw=args.post_run_raw,
                    save_output=save_output,
                    boot_wait=args.boot_wait,
                    draw_wait=args.draw_wait,
                    path_prompt_wait=args.path_prompt_wait,
                    path_keys=args.path_keys,
                    slot_wait=args.slot_wait,
                    slot_keys=args.slot_keys,
                    description_wait=args.description_wait,
                    description=args.description,
                    confirmation_wait=args.confirmation_wait,
                    confirmation_keys=args.confirmation_keys,
                    key_delay=args.key_delay,
                    slot=args.slot,
                ),
            }
            result["cases"] = result["qemu"]["cases"]
        write_report(args.output, result)
        print(args.output)
        if args.run_qemu and not result["qemu"]["passed"]:
            return 1
        return 0

    if args.probe == "save-xor-extract":
        picture_no = args.picture if args.picture is not None else GR_SAVE_TEST_PICTURE
        effective_save_stem = args.save_stem
        if effective_save_stem is None:
            effective_save_stem = (
                f"{GR_SAVE_SIGNATURE_MESSAGE}{GR_SAVE_STEM}"
                if args.verify_signature
                else GR_SAVE_STEM
            )
        save_output = args.save_output
        if save_output is None:
            save_output = Path(f"build/gr-v3-behavior/{effective_save_stem}.{args.slot}")
        case = build_gr_save_extract_fixture(
            args.game_dir,
            args.fixture_root,
            picture_no=picture_no,
            dos_prefix=args.dos_prefix,
            verify_signature=args.verify_signature,
        )
        signature_prefix = GR_SAVE_SIGNATURE_MESSAGE if args.verify_signature else ""
        result: dict = {
            "probe": "gr_v3_save_xor_extract_signed" if args.verify_signature else "gr_v3_save_xor_extract",
            "game_dir": str(args.game_dir),
            "picture": picture_no,
            "uses_verify_game_signature": args.verify_signature,
            "signature_prefix": signature_prefix or "blank",
            "save_stem": effective_save_stem,
            "slot": args.slot,
            "expected_save_file": f"{effective_save_stem}.{args.slot}",
            "cases": [probe_case_report(case)],
            "qemu": {"ran": False},
        }
        if args.run_qemu:
            result["qemu"] = {
                "ran": True,
                **run_gr_save_extract_qemu(
                    case,
                    snapshot_raw=args.snapshot_raw,
                    snapshot_qcow=args.snapshot_qcow,
                    post_run_raw=args.post_run_raw,
                    save_output=save_output,
                    boot_wait=args.boot_wait,
                    draw_wait=args.draw_wait,
                    path_prompt_wait=args.path_prompt_wait,
                    path_keys=args.path_keys,
                    slot_wait=args.slot_wait,
                    slot_keys=args.slot_keys,
                    description_wait=args.description_wait,
                    description=args.description,
                    confirmation_wait=args.confirmation_wait,
                    confirmation_keys=args.confirmation_keys,
                    key_delay=args.key_delay,
                    save_stem=effective_save_stem,
                    slot=args.slot,
                    expected_signature_prefix=signature_prefix,
                ),
            }
        write_report(args.output, result)
        print(args.output)
        if args.run_qemu and not result["qemu"]["passed"]:
            return 1
        return 0

    if args.probe == "frame-selection-gate":
        picture_no = args.picture if args.picture is not None else FRAME_GATE_TEST_PICTURE
        cases = build_frame_selection_gate_fixtures(
            args.game_dir,
            args.fixture_root,
            picture_no=picture_no,
            dos_prefix=args.dos_prefix,
        )
        result: dict = {
            "probe": "gr_v3_frame_selection_gate",
            "game_dir": str(args.game_dir),
            "picture": picture_no,
            "object": FRAME_GATE_OBJECT,
            "direction": FRAME_GATE_DIRECTION,
            "gate_flag": FRAME_GATE_FLAG,
            "exact_four_group_view": FRAME_GATE_EXACT4_VIEW,
            "more_than_four_group_view": FRAME_GATE_MORE4_VIEW,
            "expected_matches": {
                "exact4_controls_distinct": True,
                "exact4_flag_clear_matches_group1": True,
                "exact4_flag_set_matches_group1": True,
                "exact4_flag_clear_matches_group0": False,
                "exact4_flag_set_matches_group0": False,
                "more4_controls_distinct": True,
                "more4_flag_clear_matches_group0": True,
                "more4_flag_clear_matches_group1": False,
                "more4_flag_set_matches_group1": True,
                "more4_flag_set_matches_group0": False,
            },
            "cases": [probe_case_report(case) for case in cases],
            "qemu": {"ran": False},
        }
        if args.run_qemu:
            run_qemu_cases(
                cases,
                snapshot_raw=args.snapshot_raw,
                snapshot_qcow=args.snapshot_qcow,
                boot_wait=args.boot_wait,
                draw_wait=args.draw_wait,
            )
            captures = {case.label: case.capture.read_bytes() for case in cases}
            comparisons = {
                "exact4_controls_distinct": captures["exact4_group0_control"] != captures["exact4_group1_control"],
                "exact4_flag_clear_matches_group1": captures["exact4_flag_clear"] == captures["exact4_group1_control"],
                "exact4_flag_set_matches_group1": captures["exact4_flag_set"] == captures["exact4_group1_control"],
                "exact4_flag_clear_matches_group0": captures["exact4_flag_clear"] == captures["exact4_group0_control"],
                "exact4_flag_set_matches_group0": captures["exact4_flag_set"] == captures["exact4_group0_control"],
                "more4_controls_distinct": captures["more4_group0_control"] != captures["more4_group1_control"],
                "more4_flag_clear_matches_group0": captures["more4_flag_clear"] == captures["more4_group0_control"],
                "more4_flag_clear_matches_group1": captures["more4_flag_clear"] == captures["more4_group1_control"],
                "more4_flag_set_matches_group1": captures["more4_flag_set"] == captures["more4_group1_control"],
                "more4_flag_set_matches_group0": captures["more4_flag_set"] == captures["more4_group0_control"],
            }
            passed = comparisons == result["expected_matches"]
            result["qemu"] = {
                "ran": True,
                "passed": passed,
                "comparisons": comparisons,
                "snapshot_raw": str(args.snapshot_raw),
                "snapshot_qcow": str(args.snapshot_qcow),
            }
        write_report(args.output, result)
        print(args.output)
        if args.run_qemu and not result["qemu"]["passed"]:
            return 1
        return 0

    if args.probe == "motion-mode-4":
        picture_no = args.picture if args.picture is not None else MOTION_MODE_TEST_PICTURE
        cases = build_motion_mode_4_fixtures(
            args.game_dir,
            args.fixture_root,
            picture_no=picture_no,
            dos_prefix=args.dos_prefix,
        )
        result: dict = {
            "probe": "gr_v3_instrumented_motion_mode_4_dispatch",
            "game_dir": str(args.game_dir),
            "picture": picture_no,
            "view": MOTION_MODE_TEST_VIEW,
            "group": MOTION_MODE_TEST_GROUP,
            "frame": MOTION_MODE_TEST_FRAME,
            "start_x": MOTION_MODE_TEST_START_X,
            "target_x": MOTION_MODE_TEST_TARGET_X,
            "baseline_y": MOTION_MODE_TEST_BASELINE_Y,
            "step": MOTION_MODE_TEST_STEP,
            "instrumented_interpreter_patch": {
                "file": "AGI",
                "offset": f"0x{GR_ACTION_51_MODE_STORE_OFFSET:04x}",
                "original_byte": "0x03",
                "patched_byte": "0x04",
                "meaning": "action 0x51 seeds object byte +0x22 with mode 4 instead of mode 3",
            },
            "expected_matches": {
                "mode4_instrumented_move_object_to_matches_mode3": True,
                "stationary_control_matches_mode3": False,
            },
            "cases": [probe_case_report(case) for case in cases],
            "qemu": {"ran": False},
        }
        if args.run_qemu:
            run_qemu_cases(
                cases,
                snapshot_raw=args.snapshot_raw,
                snapshot_qcow=args.snapshot_qcow,
                boot_wait=args.boot_wait,
                draw_wait=args.draw_wait,
            )
            stationary_capture = cases[0].capture.read_bytes()
            mode3_capture = cases[1].capture.read_bytes()
            mode4_capture = cases[2].capture.read_bytes()
            comparisons = {
                "mode4_instrumented_move_object_to_matches_mode3": mode4_capture == mode3_capture,
                "stationary_control_matches_mode3": stationary_capture == mode3_capture,
            }
            passed = comparisons == result["expected_matches"]
            result["qemu"] = {
                "ran": True,
                "passed": passed,
                "comparisons": comparisons,
                "snapshot_raw": str(args.snapshot_raw),
                "snapshot_qcow": str(args.snapshot_qcow),
            }
        write_report(args.output, result)
        print(args.output)
        if args.run_qemu and not result["qemu"]["passed"]:
            return 1
        return 0

    if args.probe == "key-map-capacity":
        picture_no = args.picture if args.picture is not None else KEY_MAP_TEST_PICTURE
        cases = build_key_map_capacity_fixtures(
            args.game_dir,
            args.fixture_root,
            picture_no=picture_no,
            dos_prefix=args.dos_prefix,
        )
        result: dict = {
            "probe": "gr_v3_key_map_slot_48_capacity",
            "game_dir": str(args.game_dir),
            "picture": picture_no,
            "sq2_slot_count": SQ2_KEY_MAP_SLOT_COUNT,
            "gr_slot_count": GR_KEY_MAP_SLOT_COUNT,
            "target_slot_index": GR_KEY_MAP_SLOT_COUNT - 1,
            "target_key_word": KEY_MAP_TEST_KEY_WORD,
            "target_status_index": KEY_MAP_TEST_STATUS,
            "expected_matches_direct": {
                "slot_48_key_map": True,
                "slot_48_no_key": False,
            },
            "cases": [probe_case_report(case) for case in cases],
            "qemu": {"ran": False},
        }
        if args.run_qemu:
            run_qemu_cases(
                cases,
                snapshot_raw=args.snapshot_raw,
                snapshot_qcow=args.snapshot_qcow,
                boot_wait=args.boot_wait,
                draw_wait=args.draw_wait,
            )
            direct_capture = cases[0].capture.read_bytes()
            matches_direct = {
                case.label: case.capture.read_bytes() == direct_capture
                for case in cases[1:]
            }
            expected_matches = result["expected_matches_direct"]
            passed = matches_direct == expected_matches
            result["qemu"] = {
                "ran": True,
                "passed": passed,
                "matches_direct": matches_direct,
                "snapshot_raw": str(args.snapshot_raw),
                "snapshot_qcow": str(args.snapshot_qcow),
            }
        write_report(args.output, result)
        print(args.output)
        if args.run_qemu and not result["qemu"]["passed"]:
            return 1
        return 0

    if args.probe == "direct-draw":
        picture_no = args.picture if args.picture is not None else ROOM_REMAP_DESTINATION
        case = build_direct_draw_fixture(
            args.game_dir,
            args.fixture_root,
            picture_no=picture_no,
            dos_prefix=args.dos_prefix,
        )
        result: dict = {
            "probe": "gr_v3_direct_draw_logic0",
            "game_dir": str(args.game_dir),
            "picture": picture_no,
            "cases": [probe_case_report(case)],
            "qemu": {"ran": False},
        }
        if args.run_qemu:
            run_qemu_cases(
                [case],
                snapshot_raw=args.snapshot_raw,
                snapshot_qcow=args.snapshot_qcow,
                boot_wait=args.boot_wait,
                draw_wait=args.draw_wait,
            )
            result["qemu"] = {
                "ran": True,
                "snapshot_raw": str(args.snapshot_raw),
                "snapshot_qcow": str(args.snapshot_qcow),
            }
        write_report(args.output, result)
        print(args.output)
        return 0

    picture_no = args.picture if args.picture is not None else ROOM_REMAP_DESTINATION
    cases = build_room_remap_fixtures(
        args.game_dir,
        args.fixture_root,
        picture_no=picture_no,
        dos_prefix=args.dos_prefix,
    )
    result: dict = {
        "probe": "gr_v3_room_remap_0x7e_0x80_to_0x49",
        "game_dir": str(args.game_dir),
        "picture": picture_no,
        "cases": [case_report(case) for case in cases],
        "qemu": {"ran": False},
    }
    if args.run_qemu:
        captures_equal = run_room_remap_qemu(
            cases,
            snapshot_raw=args.snapshot_raw,
            snapshot_qcow=args.snapshot_qcow,
            boot_wait=args.boot_wait,
            draw_wait=args.draw_wait,
        )
        result["qemu"] = {
            "ran": True,
            "captures_equal": all(captures_equal.values()),
            "matches_direct": captures_equal,
            "snapshot_raw": str(args.snapshot_raw),
            "snapshot_qcow": str(args.snapshot_qcow),
        }
    write_report(args.output, result)
    print(args.output)
    if args.run_qemu and not result["qemu"]["captures_equal"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
