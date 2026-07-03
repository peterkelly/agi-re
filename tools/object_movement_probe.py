#!/usr/bin/env python3
"""QEMU probes for persistent object movement behavior."""

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
    assignn_action,
    approach_first_object_until_near_action,
    build_synthetic_picture_persistent_object_fixture,
    clear_object_field_22_and_global_action,
    clear_object_bits_0900_action,
    clear_object_bit_0002_action,
    clear_object_bit_0020_action,
    clear_object_bit_0200_action,
    get_object_field_0e_action,
    if_then,
    move_object_to_action,
    set_object_field_1f_from_var_action,
    set_object_field_23_mode0_action,
    set_object_field_23_mode1_action,
    set_object_field_23_mode2_action,
    set_object_field_23_mode3_action,
    set_object_bit_0002_action,
    set_object_bit_0100_action,
    set_object_bit_0020_action,
    set_object_bit_0200_action,
    set_object_bit_0800_action,
    set_rect_bounds_action,
    set_object_step_from_var_action,
    set_object_tick_from_var_action,
    setup_persistent_object_actions,
    start_random_motion_action,
    var_eq_imm_condition,
)
from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases


DEFAULT_INIT_FLAG = 199
DEFAULT_FIXTURES = Path("build/object-movement-probes/fixtures")
DEFAULT_RESULTS = Path("build/object-movement-probes/batches")
DEFAULT_SNAPSHOT_RAW = Path("build/object-movement-probes/snapshot/object_movement.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/object-movement-probes/snapshot/object_movement.qcow2")
MOTION_VALUE_VAR = 249
MOTION_TICK_VAR = 248
FRAME_OBS_VAR = 247


@dataclass(frozen=True)
class ObjectMovementCase:
    case_id: str
    description: str
    picture_payload_hex: str
    picture_no: int
    view_no: int
    group_no: int
    frame_no: int
    start_x: int
    start_baseline_y: int
    priority: int
    target_x: int
    target_y: int
    step_size: int
    completion_flag: int
    expected_x: int
    expected_baseline_y: int
    init_flag: int = DEFAULT_INIT_FLAG
    object_no: int = 0
    motion_kind: str = "move_to"
    comparison_kind: str = "exact"
    approach_threshold: int = 0
    moving_skip_collision: bool = False
    moving_clear_skip_collision: bool = False
    moving_set_bit_0002: bool = False
    moving_clear_bit_0002: bool = False
    moving_set_bit_0100: bool = False
    moving_set_bit_0800: bool = False
    moving_clear_bits_0900: bool = False
    rect_left: int | None = None
    rect_top: int | None = None
    rect_right: int | None = None
    rect_bottom: int | None = None
    obstacle_x: int | None = None
    obstacle_baseline_y: int | None = None
    obstacle_view_no: int = 11
    obstacle_group_no: int = 0
    obstacle_frame_no: int = 0
    obstacle_priority: int = 15
    obstacle_object_no: int = 1
    expected_group_no: int | None = None
    expected_frame_no: int | None = None
    animation_interval: int = 0
    animation_flag: int = 0
    animation_mode: int = 1
    animation_stop_frame: int | None = None
    animation_clear_bit_0020: bool = False
    animation_set_bit_0020: bool = False

    @property
    def picture_payload(self) -> bytes:
        return bytes.fromhex(self.picture_payload_hex)


@dataclass(frozen=True)
class MovementComparison:
    case_id: str
    status: str
    mismatches: int | None
    total: int | None
    mismatch_bbox: tuple[int, int, int, int] | None
    samples: list[tuple[int, int, int, int]] | None
    best_position: tuple[int, int, int] | None
    error: str | None


@dataclass(frozen=True)
class MovementBatchResult:
    case_id: str
    status: str
    dos_dir: str
    capture: str
    elapsed_seconds: float
    comparison: MovementComparison | None
    error: str | None


def base_cases() -> list[ObjectMovementCase]:
    return [
        ObjectMovementCase(
            "move_right_to_target",
            "Persistent object moves horizontally right to a nearby target.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            50,
            80,
            5,
            200,
            50,
            80,
        ),
        ObjectMovementCase(
            "move_down_to_target",
            "Persistent object moves downward to a nearby target.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            20,
            100,
            5,
            201,
            20,
            100,
        ),
        ObjectMovementCase(
            "move_right_to_screen_edge",
            "Persistent object moving toward an unreachable right target stops at the screen edge.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            250,
            80,
            5,
            202,
            140,
            80,
        ),
        ObjectMovementCase(
            "move_down_to_bottom_edge",
            "Persistent object moving toward an unreachable low target stops at the bottom edge.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            20,
            250,
            5,
            203,
            20,
            167,
        ),
        ObjectMovementCase(
            "move_allowed_on_control_zero",
            "Persistent object movement can reach its target on a synthetic control-zero background.",
            bytes([0xF2, 0x00, 0xF8, 0, 0, 0xFF]).hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            50,
            80,
            5,
            204,
            50,
            80,
        ),
        ObjectMovementCase(
            "move_control_1_without_bit_0002_blocks",
            "Control class 1 rejects movement when bit 0x0002 is clear and object priority is not the scan-bypass value 15.",
            bytes([0xF2, 0x01, 0xF8, 0, 0, 0xFF]).hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            14,
            50,
            80,
            5,
            219,
            20,
            80,
            comparison_kind="picture_only",
        ),
        ObjectMovementCase(
            "move_control_1_set_bit_0002_still_hidden",
            "Action 0x58 sets bit 0x0002, but a priority-14 object on full control class 1 still remains hidden in this fixture.",
            bytes([0xF2, 0x01, 0xF8, 0, 0, 0xFF]).hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            14,
            50,
            80,
            5,
            220,
            20,
            80,
            comparison_kind="picture_only",
            moving_set_bit_0002=True,
        ),
        ObjectMovementCase(
            "move_control_1_clear_bit_0002_still_hidden",
            "Action 0x59 clears bit 0x0002 after 0x58; a priority-14 object on full control class 1 remains hidden.",
            bytes([0xF2, 0x01, 0xF8, 0, 0, 0xFF]).hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            14,
            50,
            80,
            5,
            221,
            20,
            80,
            comparison_kind="picture_only",
            moving_set_bit_0002=True,
            moving_clear_bit_0002=True,
        ),
        ObjectMovementCase(
            "move_rect_boundary_without_bit_0002_stops_at_edge",
            "Rectangle-boundary crossing stops movement when bit 0x0002 is clear.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            50,
            80,
            5,
            222,
            30,
            80,
            motion_kind="move_to_once_autonomous",
            rect_left=30,
            rect_top=70,
            rect_right=60,
            rect_bottom=90,
        ),
        ObjectMovementCase(
            "move_rect_boundary_set_bit_0002_reaches_target",
            "Action 0x58 sets bit 0x0002, bypassing rectangle-boundary crossing stops.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            50,
            80,
            5,
            223,
            50,
            80,
            motion_kind="move_to_once_autonomous",
            moving_set_bit_0002=True,
            rect_left=30,
            rect_top=70,
            rect_right=60,
            rect_bottom=90,
        ),
        ObjectMovementCase(
            "move_rect_boundary_clear_bit_0002_stops_again",
            "Action 0x59 clears bit 0x0002 after 0x58, restoring rectangle-boundary crossing stops.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            50,
            80,
            5,
            224,
            30,
            80,
            motion_kind="move_to_once_autonomous",
            moving_set_bit_0002=True,
            moving_clear_bit_0002=True,
            rect_left=30,
            rect_top=70,
            rect_right=60,
            rect_bottom=90,
        ),
        ObjectMovementCase(
            "move_control_2_set_bit_0100_blocks",
            "Action 0x40 sets bit 0x0100, causing control class 2 movement acceptance to reject.",
            bytes([0xF2, 0x02, 0xF8, 0, 0, 0xFF]).hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            14,
            50,
            80,
            5,
            225,
            20,
            80,
            moving_set_bit_0100=True,
        ),
        ObjectMovementCase(
            "move_control_2_clear_bits_0900_reaches_target",
            "Action 0x42 clears bit 0x0100 after 0x40, allowing control class 2 movement again.",
            bytes([0xF2, 0x02, 0xF8, 0, 0, 0xFF]).hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            14,
            50,
            80,
            5,
            226,
            50,
            80,
            moving_set_bit_0100=True,
            moving_clear_bits_0900=True,
        ),
        ObjectMovementCase(
            "move_control_3_set_bit_0800_blocks",
            "Action 0x41 sets bit 0x0800, causing all-control-class-3 movement acceptance to reject.",
            bytes([0xF2, 0x03, 0xF8, 0, 0, 0xFF]).hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            14,
            50,
            80,
            5,
            227,
            20,
            80,
            moving_set_bit_0800=True,
        ),
        ObjectMovementCase(
            "move_control_3_clear_bits_0900_reaches_target",
            "Action 0x42 clears bit 0x0800 after 0x41, allowing all-control-class-3 movement again.",
            bytes([0xF2, 0x03, 0xF8, 0, 0, 0xFF]).hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            14,
            50,
            80,
            5,
            228,
            50,
            80,
            moving_set_bit_0800=True,
            moving_clear_bits_0900=True,
        ),
        ObjectMovementCase(
            "animation_interval_mode1_reaches_frame1",
            "Action 0x4c seeds the callback interval; mode-1 object animation reaches view 11 frame 1.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            50,
            80,
            15,
            0,
            0,
            0,
            229,
            50,
            80,
            motion_kind="animation_only",
            expected_frame_no=1,
            animation_interval=1,
            animation_flag=229,
        ),
        ObjectMovementCase(
            "animation_clear_bit_0020_prevents_frame_advance",
            "Action 0x46 clears bit 0x0020 after mode-1 setup, preventing the frame-advance callback.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            50,
            80,
            15,
            0,
            0,
            0,
            230,
            50,
            80,
            motion_kind="animation_only",
            expected_frame_no=0,
            animation_interval=1,
            animation_flag=230,
            animation_clear_bit_0020=True,
        ),
        ObjectMovementCase(
            "animation_set_bit_0020_restores_frame_advance",
            "Action 0x47 sets bit 0x0020 after 0x46, restoring the frame-advance callback.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            50,
            80,
            15,
            0,
            0,
            0,
            231,
            50,
            80,
            motion_kind="animation_only",
            expected_frame_no=1,
            animation_interval=1,
            animation_flag=231,
            animation_clear_bit_0020=True,
            animation_set_bit_0020=True,
        ),
        ObjectMovementCase(
            "animation_mode0_forward_loop_wraps_to_frame0",
            "Action 0x48 starts mode 0; from frame 1, the frame callback increments and wraps to frame 0.",
            b"\xff".hex(),
            0,
            11,
            0,
            1,
            50,
            80,
            15,
            0,
            0,
            0,
            232,
            50,
            80,
            motion_kind="animation_only",
            expected_frame_no=0,
            animation_interval=1,
            animation_mode=0,
            animation_stop_frame=0,
        ),
        ObjectMovementCase(
            "animation_mode2_backward_completion_reaches_frame0",
            "Action 0x4b starts mode 2; from frame 1, the frame callback decrements to frame 0 and stops.",
            b"\xff".hex(),
            0,
            11,
            0,
            1,
            50,
            80,
            15,
            0,
            0,
            0,
            233,
            50,
            80,
            motion_kind="animation_only",
            expected_frame_no=0,
            animation_interval=1,
            animation_flag=233,
            animation_mode=2,
        ),
        ObjectMovementCase(
            "animation_mode3_backward_loop_wraps_to_frame1",
            "Action 0x4a starts mode 3; from frame 0, the frame callback decrements and wraps to the last frame.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            50,
            80,
            15,
            0,
            0,
            0,
            234,
            50,
            80,
            motion_kind="animation_only",
            expected_frame_no=1,
            animation_interval=1,
            animation_mode=3,
            animation_stop_frame=1,
        ),
        ObjectMovementCase(
            "move_left_to_target",
            "Persistent object moves horizontally left to a nearby target.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            80,
            80,
            15,
            50,
            80,
            5,
            205,
            50,
            80,
        ),
        ObjectMovementCase(
            "move_up_to_target",
            "Persistent object moves upward to a nearby target.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            100,
            15,
            20,
            80,
            5,
            206,
            20,
            80,
        ),
        ObjectMovementCase(
            "move_diagonal_down_right",
            "Persistent object moves diagonally, then straightens when one axis reaches the target band first.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            50,
            100,
            5,
            207,
            50,
            100,
        ),
        ObjectMovementCase(
            "move_non_divisible_distance",
            "Persistent object completes when it is within one step of a target not divisible by the step size.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            52,
            80,
            5,
            208,
            50,
            80,
        ),
        ObjectMovementCase(
            "move_near_target_immediate",
            "Persistent object already within one step of the target completes without moving.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            23,
            80,
            5,
            209,
            20,
            80,
        ),
        ObjectMovementCase(
            "move_already_at_target",
            "Persistent object already at the exact target completes without moving.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            20,
            80,
            5,
            210,
            20,
            80,
        ),
        ObjectMovementCase(
            "move_zero_step_override",
            "A zero step-size operand preserves the object's current zero step, so it does not move.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            50,
            80,
            0,
            211,
            20,
            80,
        ),
        ObjectMovementCase(
            "move_blocked_by_object_collision",
            "Object 0 stops before crossing object 1 when their horizontal rectangles touch at the same baseline.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            80,
            80,
            5,
            212,
            25,
            80,
            obstacle_x=50,
            obstacle_baseline_y=80,
        ),
        ObjectMovementCase(
            "move_collision_skip_bit_reaches_target",
            "Object bit 0x0200 on the moving object skips object-object collision testing.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            80,
            80,
            5,
            213,
            80,
            80,
            moving_skip_collision=True,
            obstacle_x=50,
            obstacle_baseline_y=80,
        ),
        ObjectMovementCase(
            "move_collision_clear_skip_bit_blocks_again",
            "Clearing object bit 0x0200 after setting it restores object-object collision testing.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            80,
            80,
            5,
            217,
            25,
            80,
            moving_skip_collision=True,
            moving_clear_skip_collision=True,
            obstacle_x=50,
            obstacle_baseline_y=80,
        ),
        ObjectMovementCase(
            "approach_first_object_until_near_band",
            "Object 1 autonomously approaches object 0 and stops once their centers are within the configured near threshold.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            0,
            0,
            5,
            214,
            50,
            80,
            object_no=1,
            motion_kind="approach_first",
            approach_threshold=35,
            obstacle_x=80,
            obstacle_baseline_y=80,
            obstacle_object_no=0,
        ),
        ObjectMovementCase(
            "move_to_once_countdown_gated_completion",
            "A single move_object_to setup can complete through the countdown-gated mode-3 dispatcher when object tick byte +0x01 is one.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            20,
            80,
            15,
            50,
            80,
            5,
            215,
            50,
            80,
            motion_kind="move_to_once_autonomous",
        ),
        ObjectMovementCase(
            "random_motion_visible_somewhere",
            "Random autonomous motion renders the object exactly at some valid final position.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            60,
            80,
            15,
            0,
            0,
            5,
            216,
            60,
            80,
            motion_kind="random_motion",
            comparison_kind="any_position",
        ),
        ObjectMovementCase(
            "clear_field_22_after_random_motion_stops_motion",
            "Action 0x4e clears object byte +0x22 after random motion setup, so the object does not continue moving.",
            b"\xff".hex(),
            0,
            11,
            0,
            0,
            60,
            80,
            15,
            0,
            0,
            5,
            218,
            60,
            80,
            motion_kind="random_motion_then_clear_4e",
        ),
    ]


def load_cases(path: Path | None, selected_ids: list[str] | None = None) -> list[ObjectMovementCase]:
    if path is None:
        cases = base_cases()
    else:
        data = json.loads(path.read_text(encoding="ascii"))
        cases = [ObjectMovementCase(**item) for item in data]
    if selected_ids:
        selected = set(selected_ids)
        cases = [case for case in cases if case.case_id in selected]
        missing = selected - {case.case_id for case in cases}
        if missing:
            raise ValueError(f"unknown case id(s): {', '.join(sorted(missing))}")
    return cases


def qemu_batch_dos_dir(prefix: str, index: int) -> str:
    clean = "".join(character for character in prefix.upper() if character.isalnum()) or "MV"
    return f"{clean[:3]}{index:05d}"[:8]


def compare_capture(case: ObjectMovementCase, capture: Path) -> MovementComparison:
    try:
        captured = downsample_qemu_picture_nibbles(read_ppm(capture))
        picture = PictureRenderer(case.picture_payload).render(case.picture_no)
        expected_group_no = case.group_no if case.expected_group_no is None else case.expected_group_no
        expected_frame_no = case.frame_no if case.expected_frame_no is None else case.expected_frame_no
        frame = render_view_frame(case.view_no, expected_group_no, expected_frame_no)
        if case.comparison_kind == "picture_only":
            expected = picture
        else:
            expected = compose_frame_on_picture(
                picture,
                frame,
                case.expected_x,
                case.expected_baseline_y,
                case.priority,
            )
        if case.obstacle_x is not None and case.obstacle_baseline_y is not None:
            obstacle_frame = render_view_frame(case.obstacle_view_no, case.obstacle_group_no, case.obstacle_frame_no)
            expected = compose_frame_on_picture(
                expected,
                obstacle_frame,
                case.obstacle_x,
                case.obstacle_baseline_y,
                case.obstacle_priority,
            )
        expected_nibbles = expected.visual_nibbles
    except Exception as exc:  # noqa: BLE001 - probe records exact local exception.
        return MovementComparison(case.case_id, "error", None, None, None, None, None, f"{type(exc).__name__}: {exc}")

    mismatch_samples: list[tuple[int, int, int, int]] = []
    min_x = WIDTH
    min_y = HEIGHT
    max_x = -1
    max_y = -1
    mismatches = 0
    for idx, (left, right) in enumerate(zip(captured, expected_nibbles)):
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
    best_position = None if mismatches == 0 else find_best_position(captured, picture, frame, case.priority)
    if case.comparison_kind == "any_position" and mismatches != 0:
        assert best_position is not None
        best_mismatches, best_x, best_y = best_position
        if best_mismatches == 0 and 0 <= best_x < WIDTH and 0 <= best_y < HEIGHT:
            return MovementComparison(
                case.case_id,
                "match",
                0,
                len(expected_nibbles),
                None,
                [],
                best_position,
                None,
            )
    return MovementComparison(
        case.case_id,
        "match" if mismatches == 0 else "mismatch",
        mismatches,
        len(expected_nibbles),
        bbox,
        mismatch_samples,
        best_position,
        None,
    )


def find_best_position(
    captured: bytes,
    picture: object,
    frame: object,
    priority: int,
) -> tuple[int, int, int]:
    best: tuple[int, int, int] | None = None
    for y in range(HEIGHT):
        for x in range(WIDTH):
            expected = compose_frame_on_picture(picture, frame, x, y, priority).visual_nibbles
            mismatches = sum(left != right for left, right in zip(captured, expected))
            if best is None or mismatches < best[0]:
                best = (mismatches, x, y)
                if mismatches == 0:
                    return best
    assert best is not None
    return best


def run_snapshot_batch(
    cases: list[ObjectMovementCase],
    fixture_root: Path,
    boot_wait: float,
    draw_wait: float,
    dos_prefix: str,
    stop_on_failure: bool,
    snapshot_raw: Path,
    snapshot_qcow: Path,
) -> list[MovementBatchResult]:
    qemu_cases: list[SnapshotFixtureCase] = []
    started_at: dict[str, float] = {}
    for index, case in enumerate(cases):
        dos_dir = qemu_batch_dos_dir(dos_prefix, index)
        fixture = fixture_root / case.case_id
        capture = fixture / "qemu_capture.ppm"
        started_at[case.case_id] = time.monotonic()
        print(f"[{index + 1}/{len(cases)}] build {case.case_id} -> {dos_dir}", file=sys.stderr, flush=True)
        build_synthetic_picture_persistent_object_fixture(
            case.picture_payload,
            case.picture_no,
            case.view_no,
            case.group_no,
            case.frame_no,
            case.start_x,
            case.start_baseline_y,
            case.priority,
            fixture,
            case.object_no,
            post_activate_actions=post_activate_actions(case),
            per_cycle_actions=per_cycle_actions(case),
            per_cycle_until_flag=per_cycle_until_flag(case),
            init_flag=case.init_flag,
        )
        qemu_cases.append(SnapshotFixtureCase(dos_dir, fixture, capture))

    print(f"building snapshot disk: {snapshot_qcow}", file=sys.stderr, flush=True)
    build_snapshot_boot_disk(qemu_cases, snapshot_raw, snapshot_qcow)
    print(f"running {len(qemu_cases)} cases from one QEMU snapshot", file=sys.stderr, flush=True)
    run_snapshot_qemu_cases(snapshot_qcow, qemu_cases, boot_wait, draw_wait)

    results: list[MovementBatchResult] = []
    for index, (case, qemu_case) in enumerate(zip(cases, qemu_cases)):
        comparison: MovementComparison | None = None
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
            MovementBatchResult(case.case_id, status, qemu_case.dos_dir, str(qemu_case.capture), elapsed, comparison, error)
        )
        if stop_on_failure and status != "match":
            break
    return results


def post_activate_actions(case: ObjectMovementCase) -> bytes:
    actions = b""
    if case.rect_left is not None:
        if case.rect_top is None or case.rect_right is None or case.rect_bottom is None:
            raise ValueError(f"{case.case_id}: all rectangle bounds must be set together")
        actions += set_rect_bounds_action(case.rect_left, case.rect_top, case.rect_right, case.rect_bottom)
    if case.moving_set_bit_0002:
        actions += set_object_bit_0002_action(case.object_no)
    if case.moving_clear_bit_0002:
        actions += clear_object_bit_0002_action(case.object_no)
    if case.moving_set_bit_0100:
        actions += set_object_bit_0100_action(case.object_no)
    if case.moving_set_bit_0800:
        actions += set_object_bit_0800_action(case.object_no)
    if case.moving_clear_bits_0900:
        actions += clear_object_bits_0900_action(case.object_no)
    if case.animation_interval:
        actions += assignn_action(MOTION_VALUE_VAR, case.animation_interval)
        actions += set_object_field_1f_from_var_action(case.object_no, MOTION_VALUE_VAR)
        if case.animation_mode == 0:
            actions += set_object_field_23_mode0_action(case.object_no)
        elif case.animation_mode == 1:
            actions += set_object_field_23_mode1_action(case.object_no, case.animation_flag)
        elif case.animation_mode == 2:
            actions += set_object_field_23_mode2_action(case.object_no, case.animation_flag)
        elif case.animation_mode == 3:
            actions += set_object_field_23_mode3_action(case.object_no)
        else:
            raise ValueError(f"{case.case_id}: unsupported animation mode {case.animation_mode}")
        if case.animation_clear_bit_0020:
            actions += clear_object_bit_0020_action(case.object_no)
        if case.animation_set_bit_0020:
            actions += set_object_bit_0020_action(case.object_no)
    if case.moving_skip_collision:
        actions += set_object_bit_0200_action(case.object_no)
    if case.moving_clear_skip_collision:
        actions += clear_object_bit_0200_action(case.object_no)
    if case.obstacle_x is not None and case.obstacle_baseline_y is not None:
        actions += setup_persistent_object_actions(
            case.obstacle_view_no,
            case.obstacle_group_no,
            case.obstacle_frame_no,
            case.obstacle_x,
            case.obstacle_baseline_y,
            case.obstacle_priority,
            case.obstacle_object_no,
        )
    if case.motion_kind == "approach_first":
        actions += assignn_action(MOTION_VALUE_VAR, case.step_size)
        actions += set_object_step_from_var_action(case.object_no, MOTION_VALUE_VAR)
        actions += assignn_action(MOTION_TICK_VAR, 1)
        actions += set_object_tick_from_var_action(case.object_no, MOTION_TICK_VAR)
        actions += approach_first_object_until_near_action(
            case.object_no,
            case.approach_threshold,
            case.completion_flag,
        )
    if case.motion_kind == "move_to_once_autonomous":
        actions += assignn_action(MOTION_TICK_VAR, 1)
        actions += set_object_tick_from_var_action(case.object_no, MOTION_TICK_VAR)
        actions += move_object_to_action(
            case.object_no,
            case.target_x,
            case.target_y,
            case.step_size,
            case.completion_flag,
        )
    if case.motion_kind in {"random_motion", "random_motion_then_clear_4e"}:
        actions += assignn_action(MOTION_VALUE_VAR, case.step_size)
        actions += set_object_step_from_var_action(case.object_no, MOTION_VALUE_VAR)
        actions += assignn_action(MOTION_TICK_VAR, 1)
        actions += set_object_tick_from_var_action(case.object_no, MOTION_TICK_VAR)
        actions += start_random_motion_action(case.object_no)
        if case.motion_kind == "random_motion_then_clear_4e":
            actions += clear_object_field_22_and_global_action(case.object_no)
    return actions


def per_cycle_actions(case: ObjectMovementCase) -> bytes:
    if case.animation_stop_frame is not None:
        return get_object_field_0e_action(case.object_no, FRAME_OBS_VAR) + if_then(
            var_eq_imm_condition(FRAME_OBS_VAR, case.animation_stop_frame),
            clear_object_bit_0020_action(case.object_no),
        )
    if case.motion_kind == "move_to":
        return move_object_to_action(
            case.object_no,
            case.target_x,
            case.target_y,
            case.step_size,
            case.completion_flag,
        )
    if case.motion_kind in {
        "approach_first",
        "move_to_once_autonomous",
        "random_motion",
        "random_motion_then_clear_4e",
        "animation_only",
    }:
        return b""
    raise ValueError(f"unsupported motion kind: {case.motion_kind}")


def per_cycle_until_flag(case: ObjectMovementCase) -> int | None:
    if case.motion_kind == "move_to":
        return case.completion_flag
    return None


def write_report(results: list[MovementBatchResult], output: Path) -> dict[str, object]:
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
    parser.add_argument("--case", dest="case_ids", action="append", default=[])
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS / "object_movement_base.json")
    parser.add_argument("--dos-prefix", default="MV")
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
