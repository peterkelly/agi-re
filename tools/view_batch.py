#!/usr/bin/env python3
"""Run QEMU validation batches for picture plus view/cel fixtures."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from compare_picture_capture import PictureCaptureComparison, compare_picture_capture
from picture_fuzz import run_qemu_fixture
from qemu_fixture import build_picture_view_fixture
from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases


DEFAULT_FIXTURES = Path("build/view-batch/fixtures")
DEFAULT_RESULTS = Path("build/view-batch/batches")
DEFAULT_SNAPSHOT_RAW = Path("build/view-batch/snapshot/view_batch.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/view-batch/snapshot/view_batch.qcow2")


@dataclass(frozen=True)
class ViewBatchCase:
    case_id: str
    picture_no: int
    view_no: int
    group_no: int
    frame_no: int
    x: int
    baseline_y: int
    priority: int
    control: int | None = None


@dataclass(frozen=True)
class ViewBatchResult:
    case_id: str
    status: str
    dos_dir: str
    capture: str
    elapsed_seconds: float
    comparison: PictureCaptureComparison | None
    error: str | None


def base_cases() -> list[ViewBatchCase]:
    return [
        ViewBatchCase("view_011_normal_mid", 1, 11, 0, 0, 20, 80, 15),
        ViewBatchCase("view_000_group0_cached_mid", 1, 0, 0, 0, 20, 80, 15),
        ViewBatchCase("view_000_group1_mirrored_mid", 1, 0, 1, 0, 20, 80, 15),
        ViewBatchCase("view_011_left_clip", 1, 11, 0, 0, 0, 80, 15),
        ViewBatchCase("view_011_top_clip", 1, 11, 0, 0, 20, 2, 15),
        ViewBatchCase("view_011_low_priority", 1, 11, 0, 0, 20, 80, 1),
    ]


def load_cases(path: Path | None) -> list[ViewBatchCase]:
    if path is None:
        return base_cases()
    data = json.loads(path.read_text(encoding="ascii"))
    return [ViewBatchCase(**item) for item in data]


def qemu_batch_dos_dir(prefix: str, index: int) -> str:
    clean = "".join(character for character in prefix.upper() if character.isalnum()) or "VB"
    return f"{clean[:3]}{index:05d}"[:8]


def run_batch(
    cases: list[ViewBatchCase],
    fixture_root: Path,
    boot_wait: float,
    draw_wait: float,
    dos_prefix: str,
    stop_on_failure: bool,
) -> list[ViewBatchResult]:
    results: list[ViewBatchResult] = []
    for index, case in enumerate(cases):
        dos_dir = qemu_batch_dos_dir(dos_prefix, index)
        fixture = fixture_root / case.case_id
        capture = fixture / "qemu_capture.ppm"
        started = time.monotonic()
        comparison: PictureCaptureComparison | None = None
        error: str | None = None
        status = "error"
        print(f"[{index + 1}/{len(cases)}] {case.case_id} -> {dos_dir}", file=sys.stderr, flush=True)
        try:
            build_picture_view_fixture(
                case.picture_no,
                case.view_no,
                case.group_no,
                case.frame_no,
                case.x,
                case.baseline_y,
                case.priority,
                fixture,
                case.control,
            )
            run_qemu_fixture(fixture, dos_dir, capture, boot_wait, draw_wait)
            comparison = compare_picture_capture(
                case.picture_no,
                capture,
                view=(case.view_no, case.group_no, case.frame_no, case.x, case.baseline_y, case.priority),
            )
            status = "match" if comparison.matches else "mismatch"
        except Exception as exc:  # noqa: BLE001 - batch harness records exact local exception.
            error = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.monotonic() - started, 3)
        print(f"[{index + 1}/{len(cases)}] {case.case_id} {status}", file=sys.stderr, flush=True)
        results.append(
            ViewBatchResult(case.case_id, status, dos_dir, str(capture), elapsed, comparison, error)
        )
        if stop_on_failure and status != "match":
            break
    return results


def run_snapshot_batch(
    cases: list[ViewBatchCase],
    fixture_root: Path,
    boot_wait: float,
    draw_wait: float,
    dos_prefix: str,
    stop_on_failure: bool,
    snapshot_raw: Path,
    snapshot_qcow: Path,
) -> list[ViewBatchResult]:
    qemu_cases: list[SnapshotFixtureCase] = []
    started_at: dict[str, float] = {}
    results: list[ViewBatchResult] = []
    for index, case in enumerate(cases):
        dos_dir = qemu_batch_dos_dir(dos_prefix, index)
        fixture = fixture_root / case.case_id
        capture = fixture / "qemu_capture.ppm"
        started_at[case.case_id] = time.monotonic()
        print(f"[{index + 1}/{len(cases)}] build {case.case_id} -> {dos_dir}", file=sys.stderr, flush=True)
        build_picture_view_fixture(
            case.picture_no,
            case.view_no,
            case.group_no,
            case.frame_no,
            case.x,
            case.baseline_y,
            case.priority,
            fixture,
            case.control,
        )
        qemu_cases.append(SnapshotFixtureCase(dos_dir, fixture, capture))

    print(f"building snapshot disk: {snapshot_qcow}", file=sys.stderr, flush=True)
    build_snapshot_boot_disk(qemu_cases, snapshot_raw, snapshot_qcow)
    print(f"running {len(qemu_cases)} cases from one QEMU snapshot", file=sys.stderr, flush=True)
    run_snapshot_qemu_cases(snapshot_qcow, qemu_cases, boot_wait, draw_wait)

    for index, (case, qemu_case) in enumerate(zip(cases, qemu_cases)):
        comparison: PictureCaptureComparison | None = None
        error: str | None = None
        status = "error"
        try:
            comparison = compare_picture_capture(
                case.picture_no,
                qemu_case.capture,
                view=(case.view_no, case.group_no, case.frame_no, case.x, case.baseline_y, case.priority),
            )
            status = "match" if comparison.matches else "mismatch"
        except Exception as exc:  # noqa: BLE001 - batch harness records exact local exception.
            error = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.monotonic() - started_at[case.case_id], 3)
        print(f"[{index + 1}/{len(cases)}] {case.case_id} {status}", file=sys.stderr, flush=True)
        results.append(
            ViewBatchResult(case.case_id, status, qemu_case.dos_dir, str(qemu_case.capture), elapsed, comparison, error)
        )
        if stop_on_failure and status != "match":
            break
    return results


def write_report(results: list[ViewBatchResult], output: Path) -> dict[str, object]:
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
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS / "view_base.json")
    parser.add_argument("--dos-prefix", default="VB")
    parser.add_argument("--boot-wait", type=float, default=5.0)
    parser.add_argument("--draw-wait", type=float, default=8.0)
    parser.add_argument("--stop-on-failure", action="store_true")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--snapshot-raw", type=Path, default=DEFAULT_SNAPSHOT_RAW)
    parser.add_argument("--snapshot-qcow", type=Path, default=DEFAULT_SNAPSHOT_QCOW)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.snapshot:
        results = run_snapshot_batch(
            cases,
            args.fixture_root,
            args.boot_wait,
            args.draw_wait,
            args.dos_prefix,
            args.stop_on_failure,
            args.snapshot_raw,
            args.snapshot_qcow,
        )
    else:
        results = run_batch(
            cases,
            args.fixture_root,
            args.boot_wait,
            args.draw_wait,
            args.dos_prefix,
            args.stop_on_failure,
        )
    report = write_report(results, args.output)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    print(f"report: {args.output}")
    if report["summary"]["mismatches"] or report["summary"]["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
