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


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
        )
        for case in cases
    ]
    build_snapshot_boot_disk(qemu_cases, snapshot_raw, snapshot_qcow)
    run_snapshot_qemu_cases(snapshot_qcow, qemu_cases, boot_wait, draw_wait)


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
