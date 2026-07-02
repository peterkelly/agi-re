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

    @property
    def code(self) -> bytes:
        return bytes.fromhex(self.code_hex)

    @property
    def picture_payload(self) -> bytes:
        return bytes.fromhex(self.picture_payload_hex)


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


def base_code(body: bytes, picture_no: int = 0) -> bytes:
    return load_show_picture_actions(picture_no) + bytes([0x1E, 11]) + body + self_loop()


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


def _case(case_id: str, description: str, body: bytes, expected_x: int) -> LogicInterpreterCase:
    return LogicInterpreterCase(
        case_id,
        description,
        base_code(body).hex(),
        b"\xff".hex(),
        0,
        11,
        0,
        0,
        expected_x,
        80,
        15,
    )


def _draw_if_case(
    case_id: str,
    description: str,
    setup: bytes,
    condition: bytes,
    expected_x: int = 50,
) -> LogicInterpreterCase:
    return _case(case_id, description, setup + if_then(condition, draw_view11_at(expected_x)), expected_x)


def assignn(var_no: int, value: int) -> bytes:
    return byte_action(0x03, var_no, value)


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
    ]


def load_cases(path: Path | None) -> list[LogicInterpreterCase]:
    if path is None:
        return base_cases()
    data = json.loads(path.read_text(encoding="ascii"))
    return [LogicInterpreterCase(**item) for item in data]


def qemu_batch_dos_dir(prefix: str, index: int) -> str:
    clean = "".join(character for character in prefix.upper() if character.isalnum()) or "LI"
    return f"{clean[:3]}{index:05d}"[:8]


def build_logic_fixture(case: LogicInterpreterCase, destination: Path) -> Path:
    copy_sq2_tree(destination)
    logic_record = volume_record(logic_resource(case.code), volume=3)
    picture_offset = len(logic_record)
    picture_record = volume_record(case.picture_payload, volume=3)
    (destination / "VOL.3").write_bytes(logic_record + picture_record)

    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))

    picdir = (destination / "PICDIR").read_bytes()
    (destination / "PICDIR").write_bytes(
        patch_dir_entry(picdir, case.picture_no, volume=3, offset=picture_offset)
    )
    return destination


def compare_capture(case: LogicInterpreterCase, capture: Path) -> LogicComparison:
    try:
        captured = downsample_qemu_picture_nibbles(read_ppm(capture))
        picture = PictureRenderer(case.picture_payload).render(case.picture_no)
        frame = render_view_frame(case.expected_view_no, case.expected_group_no, case.expected_frame_no)
        expected = compose_frame_on_picture(
            picture,
            frame,
            case.expected_x,
            case.expected_baseline_y,
            case.expected_priority,
        ).visual_nibbles
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
        qemu_cases.append(SnapshotFixtureCase(dos_dir, fixture, capture))

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
