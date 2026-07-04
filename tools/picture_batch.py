#!/usr/bin/env python3
"""Run QEMU validation batches for real SQ2 picture resources."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from agi_graphics import iter_valid_resources
from compare_picture_capture import PictureCaptureComparison, compare_picture_capture
from picture_fuzz import run_qemu_fixture
from qemu_fixture import build_packed_picture_fixture
from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases


DEFAULT_FIXTURES = Path("build/picture-batch/fixtures")
DEFAULT_RESULTS = Path("build/picture-batch/batches")
DEFAULT_SNAPSHOT_RAW = Path("build/picture-batch/snapshot/picture_batch.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/picture-batch/snapshot/picture_batch.qcow2")


@dataclass(frozen=True)
class PictureBatchCase:
    case_id: str
    picture_no: int
    description: str


@dataclass(frozen=True)
class PictureBatchResult:
    case_id: str
    picture_no: int
    status: str
    dos_dir: str
    capture: str
    elapsed_seconds: float
    comparison: PictureCaptureComparison | None
    error: str | None


def base_cases() -> list[PictureBatchCase]:
    return [
        PictureBatchCase(
            "picture_001_first_present",
            1,
            "First present SQ2 picture resource; includes pattern plots.",
        ),
        PictureBatchCase(
            "picture_045_largest_payload",
            45,
            "Largest valid SQ2 picture payload in the local corpus.",
        ),
    ]


def broad_cases() -> list[PictureBatchCase]:
    return [
        PictureBatchCase(
            "picture_001_first_present",
            1,
            "First present SQ2 picture resource; includes pattern plots.",
        ),
        PictureBatchCase(
            "picture_006_pattern_fill_dense",
            6,
            "Early picture with many fills and pattern plots.",
        ),
        PictureBatchCase(
            "picture_017_full_command_mix",
            17,
            "Uses all observed picture command families, including multiple pattern-mode changes.",
        ),
        PictureBatchCase(
            "picture_043_dense_large_fill_pattern",
            43,
            "Dense large picture with many fill, line, and pattern commands.",
        ),
        PictureBatchCase(
            "picture_044_fill_heavy_large",
            44,
            "Large fill-heavy picture with many control toggles.",
        ),
        PictureBatchCase(
            "picture_045_largest_payload",
            45,
            "Largest valid SQ2 picture payload in the local corpus.",
        ),
        PictureBatchCase(
            "picture_046_pattern_heavy",
            46,
            "Pattern-heavy large picture with the broadest command-family mix in the local corpus.",
        ),
        PictureBatchCase(
            "picture_076_pattern_dense",
            76,
            "High pattern-count picture outside the largest-payload cluster.",
        ),
    ]


def all_present_cases() -> list[PictureBatchCase]:
    return [
        PictureBatchCase(
            f"picture_{picture_no:03d}_present",
            picture_no,
            "Present valid SQ2 picture resource.",
        )
        for picture_no, _payload in iter_valid_resources("PICDIR")
    ]


def preset_cases(name: str) -> list[PictureBatchCase]:
    if name == "base":
        return base_cases()
    if name == "broad":
        return broad_cases()
    if name == "all":
        return all_present_cases()
    raise ValueError(f"unknown preset: {name}")


def load_cases(
    path: Path | None,
    selected_ids: list[str] | None = None,
    preset: str = "base",
) -> list[PictureBatchCase]:
    if path is None:
        cases = preset_cases(preset)
    else:
        data = json.loads(path.read_text(encoding="ascii"))
        cases = [PictureBatchCase(**item) for item in data]
    if selected_ids:
        selected = set(selected_ids)
        cases = [case for case in cases if case.case_id in selected]
        missing = selected - {case.case_id for case in cases}
        if missing:
            raise ValueError(f"unknown case id(s): {', '.join(sorted(missing))}")
    return cases


def qemu_batch_dos_dir(prefix: str, index: int) -> str:
    clean = "".join(character for character in prefix.upper() if character.isalnum()) or "PB"
    return f"{clean[:3]}{index:05d}"[:8]


def run_batch(
    cases: list[PictureBatchCase],
    fixture_root: Path,
    boot_wait: float,
    draw_wait: float,
    dos_prefix: str,
    stop_on_failure: bool,
) -> list[PictureBatchResult]:
    results: list[PictureBatchResult] = []
    for index, case in enumerate(cases):
        dos_dir = qemu_batch_dos_dir(dos_prefix, index)
        fixture = fixture_root / case.case_id
        capture = fixture / f"qemu_picture_{case.picture_no:03d}.ppm"
        started = time.monotonic()
        comparison: PictureCaptureComparison | None = None
        error: str | None = None
        status = "error"
        print(f"[{index + 1}/{len(cases)}] {case.case_id} -> {dos_dir}", file=sys.stderr, flush=True)
        try:
            build_packed_picture_fixture(case.picture_no, fixture)
            run_qemu_fixture(fixture, dos_dir, capture, boot_wait, draw_wait)
            comparison = compare_picture_capture(case.picture_no, capture)
            status = "match" if comparison.matches else "mismatch"
        except Exception as exc:  # noqa: BLE001 - batch harness records exact local exception.
            error = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.monotonic() - started, 3)
        print(f"[{index + 1}/{len(cases)}] {case.case_id} {status}", file=sys.stderr, flush=True)
        results.append(
            PictureBatchResult(
                case.case_id,
                case.picture_no,
                status,
                dos_dir,
                str(capture),
                elapsed,
                comparison,
                error,
            )
        )
        if stop_on_failure and status != "match":
            break
    return results


def run_snapshot_batch(
    cases: list[PictureBatchCase],
    fixture_root: Path,
    boot_wait: float,
    draw_wait: float,
    dos_prefix: str,
    stop_on_failure: bool,
    snapshot_raw: Path,
    snapshot_qcow: Path,
) -> list[PictureBatchResult]:
    qemu_cases: list[SnapshotFixtureCase] = []
    started_at: dict[str, float] = {}
    for index, case in enumerate(cases):
        dos_dir = qemu_batch_dos_dir(dos_prefix, index)
        fixture = fixture_root / case.case_id
        capture = fixture / f"qemu_picture_{case.picture_no:03d}.ppm"
        started_at[case.case_id] = time.monotonic()
        print(f"[{index + 1}/{len(cases)}] build {case.case_id} -> {dos_dir}", file=sys.stderr, flush=True)
        build_packed_picture_fixture(case.picture_no, fixture)
        qemu_cases.append(SnapshotFixtureCase(dos_dir, fixture, capture))

    print(f"building snapshot disk: {snapshot_qcow}", file=sys.stderr, flush=True)
    build_snapshot_boot_disk(qemu_cases, snapshot_raw, snapshot_qcow)
    print(f"running {len(qemu_cases)} cases from one QEMU snapshot", file=sys.stderr, flush=True)
    run_snapshot_qemu_cases(snapshot_qcow, qemu_cases, boot_wait, draw_wait)

    results: list[PictureBatchResult] = []
    for index, (case, qemu_case) in enumerate(zip(cases, qemu_cases)):
        comparison: PictureCaptureComparison | None = None
        error: str | None = None
        status = "error"
        try:
            comparison = compare_picture_capture(case.picture_no, qemu_case.capture)
            status = "match" if comparison.matches else "mismatch"
        except Exception as exc:  # noqa: BLE001 - batch harness records exact local exception.
            error = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.monotonic() - started_at[case.case_id], 3)
        print(f"[{index + 1}/{len(cases)}] {case.case_id} {status}", file=sys.stderr, flush=True)
        results.append(
            PictureBatchResult(
                case.case_id,
                case.picture_no,
                status,
                qemu_case.dos_dir,
                str(qemu_case.capture),
                elapsed,
                comparison,
                error,
            )
        )
        if stop_on_failure and status != "match":
            break
    return results


def write_report(results: list[PictureBatchResult], output: Path) -> dict[str, object]:
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
    parser.add_argument("--preset", choices=["base", "broad", "all"], default="base")
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS / "picture_base.json")
    parser.add_argument("--dos-prefix", default="PB")
    parser.add_argument("--boot-wait", type=float, default=5.0)
    parser.add_argument("--draw-wait", type=float, default=8.0)
    parser.add_argument("--stop-on-failure", action="store_true")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--snapshot-raw", type=Path, default=DEFAULT_SNAPSHOT_RAW)
    parser.add_argument("--snapshot-qcow", type=Path, default=DEFAULT_SNAPSHOT_QCOW)
    args = parser.parse_args()

    cases = load_cases(args.cases, args.case_ids, args.preset)
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
