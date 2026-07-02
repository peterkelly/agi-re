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
    move_object_to_action,
    set_object_bit_0200_action,
    set_object_step_from_var_action,
    set_object_tick_from_var_action,
    setup_persistent_object_actions,
)
from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases


DEFAULT_INIT_FLAG = 199
DEFAULT_FIXTURES = Path("build/object-movement-probes/fixtures")
DEFAULT_RESULTS = Path("build/object-movement-probes/batches")
DEFAULT_SNAPSHOT_RAW = Path("build/object-movement-probes/snapshot/object_movement.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/object-movement-probes/snapshot/object_movement.qcow2")
MOTION_VALUE_VAR = 249
MOTION_TICK_VAR = 248


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
    approach_threshold: int = 0
    moving_skip_collision: bool = False
    obstacle_x: int | None = None
    obstacle_baseline_y: int | None = None
    obstacle_view_no: int = 11
    obstacle_group_no: int = 0
    obstacle_frame_no: int = 0
    obstacle_priority: int = 15
    obstacle_object_no: int = 1

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
    ]


def load_cases(path: Path | None) -> list[ObjectMovementCase]:
    if path is None:
        return base_cases()
    data = json.loads(path.read_text(encoding="ascii"))
    return [ObjectMovementCase(**item) for item in data]


def qemu_batch_dos_dir(prefix: str, index: int) -> str:
    clean = "".join(character for character in prefix.upper() if character.isalnum()) or "MV"
    return f"{clean[:3]}{index:05d}"[:8]


def compare_capture(case: ObjectMovementCase, capture: Path) -> MovementComparison:
    try:
        captured = downsample_qemu_picture_nibbles(read_ppm(capture))
        picture = PictureRenderer(case.picture_payload).render(case.picture_no)
        frame = render_view_frame(case.view_no, case.group_no, case.frame_no)
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
    if case.moving_skip_collision:
        actions += set_object_bit_0200_action(case.object_no)
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
    return actions


def per_cycle_actions(case: ObjectMovementCase) -> bytes:
    if case.motion_kind == "move_to":
        return move_object_to_action(
            case.object_no,
            case.target_x,
            case.target_y,
            case.step_size,
            case.completion_flag,
        )
    if case.motion_kind == "approach_first":
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
        load_cases(args.cases),
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
