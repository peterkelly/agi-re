#!/usr/bin/env python3
"""Targeted QEMU probes for object/view overlay behavior."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from agi_graphics import (
    HEIGHT,
    WIDTH,
    PictureRenderer,
    compose_frame_on_picture,
    render_view_frame,
)
from compare_picture_capture import downsample_qemu_picture_nibbles
from ppm_tools import read_ppm
from qemu_fixture import build_synthetic_picture_view_fixture
from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases


DEFAULT_FIXTURES = Path("build/object-overlay-probes/fixtures")
DEFAULT_RESULTS = Path("build/object-overlay-probes/batches")
DEFAULT_SNAPSHOT_RAW = Path("build/object-overlay-probes/snapshot/object_overlay.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/object-overlay-probes/snapshot/object_overlay.qcow2")


@dataclass(frozen=True)
class ObjectOverlayCase:
    case_id: str
    description: str
    picture_payload_hex: str
    picture_no: int
    view_no: int
    group_no: int
    frame_no: int
    x: int
    baseline_y: int
    priority: int
    control: int | None = None

    @property
    def picture_payload(self) -> bytes:
        return bytes.fromhex(self.picture_payload_hex)


@dataclass(frozen=True)
class OverlayComparison:
    case_id: str
    status: str
    mismatches: int | None
    total: int | None
    mismatch_bbox: tuple[int, int, int, int] | None
    samples: list[tuple[int, int, int, int]] | None
    error: str | None

    @property
    def matches(self) -> bool:
        return self.status == "match"


@dataclass(frozen=True)
class OverlayBatchResult:
    case_id: str
    status: str
    dos_dir: str
    capture: str
    elapsed_seconds: float
    comparison: OverlayComparison | None
    error: str | None


def _case(
    case_id: str,
    description: str,
    payload: bytes,
    priority: int,
    control: int | None = None,
) -> ObjectOverlayCase:
    return ObjectOverlayCase(case_id, description, payload.hex(), 0, 11, 0, 0, 20, 80, priority, control)


def base_cases() -> list[ObjectOverlayCase]:
    scan_down_payload = bytes(
        [
            0xF2,
            0x02,
            0xF6,
            20,
            76,
            39,
            76,
            0xF2,
            0x06,
            0xF6,
            20,
            77,
            39,
            77,
            0xFF,
        ]
    )
    return [
        _case(
            "default_control4_priority3_hidden",
            "Default picture control priority 4 should hide object priority 3.",
            b"\xff",
            3,
        ),
        _case(
            "default_control4_priority4_draws",
            "Default picture control priority 4 should allow equal object priority 4.",
            b"\xff",
            4,
        ),
        _case(
            "filled_control6_priority5_hidden",
            "Synthetic full-screen control priority 6 should hide object priority 5.",
            bytes([0xF2, 0x06, 0xF8, 0x00, 0x00, 0xFF]),
            5,
        ),
        _case(
            "filled_control6_priority6_draws",
            "Synthetic full-screen control priority 6 should allow equal object priority 6.",
            bytes([0xF2, 0x06, 0xF8, 0x00, 0x00, 0xFF]),
            6,
        ),
        _case(
            "priority3_control6_uses_low_hidden",
            "Operand-6 low nibble priority 3 should be hidden despite operand-7 high nibble control 6.",
            b"\xff",
            3,
            6,
        ),
        _case(
            "priority6_control3_uses_low_draws",
            "Operand-6 low nibble priority 6 should draw despite operand-7 high nibble control 3.",
            bytes([0xF2, 0x06, 0xF8, 0x00, 0x00, 0xFF]),
            6,
            3,
        ),
        _case(
            "scan_down_control6_priority5_hidden",
            "Low destination control should scan downward to a control-6 barrier and hide object priority 5.",
            scan_down_payload,
            5,
        ),
        _case(
            "scan_down_control6_priority6_draws",
            "Low destination control should scan downward to a control-6 barrier and allow equal object priority 6.",
            scan_down_payload,
            6,
        ),
    ]


def load_cases(path: Path | None) -> list[ObjectOverlayCase]:
    if path is None:
        return base_cases()
    data = json.loads(path.read_text(encoding="ascii"))
    return [ObjectOverlayCase(**item) for item in data]


def qemu_batch_dos_dir(prefix: str, index: int) -> str:
    clean = "".join(character for character in prefix.upper() if character.isalnum()) or "OP"
    return f"{clean[:3]}{index:05d}"[:8]


def compare_capture(case: ObjectOverlayCase, capture: Path) -> OverlayComparison:
    try:
        captured = downsample_qemu_picture_nibbles(read_ppm(capture))
        picture = PictureRenderer(case.picture_payload).render(case.picture_no)
        frame = render_view_frame(case.view_no, case.group_no, case.frame_no)
        expected_picture = compose_frame_on_picture(
            picture,
            frame,
            case.x,
            case.baseline_y,
            case.priority,
        )
    except Exception as exc:  # noqa: BLE001 - probe records exact local exception.
        return OverlayComparison(case.case_id, "error", None, None, None, None, f"{type(exc).__name__}: {exc}")

    expected = expected_picture.visual_nibbles
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
    return OverlayComparison(
        case.case_id,
        "match" if mismatches == 0 else "mismatch",
        mismatches,
        len(expected),
        bbox,
        mismatch_samples,
        None,
    )


def run_snapshot_batch(
    cases: list[ObjectOverlayCase],
    fixture_root: Path,
    boot_wait: float,
    draw_wait: float,
    dos_prefix: str,
    stop_on_failure: bool,
    snapshot_raw: Path,
    snapshot_qcow: Path,
) -> list[OverlayBatchResult]:
    qemu_cases: list[SnapshotFixtureCase] = []
    started_at: dict[str, float] = {}
    for index, case in enumerate(cases):
        dos_dir = qemu_batch_dos_dir(dos_prefix, index)
        fixture = fixture_root / case.case_id
        capture = fixture / "qemu_capture.ppm"
        started_at[case.case_id] = time.monotonic()
        print(f"[{index + 1}/{len(cases)}] build {case.case_id} -> {dos_dir}", file=sys.stderr, flush=True)
        build_synthetic_picture_view_fixture(
            case.picture_payload,
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

    results: list[OverlayBatchResult] = []
    for index, (case, qemu_case) in enumerate(zip(cases, qemu_cases)):
        comparison: OverlayComparison | None = None
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
            OverlayBatchResult(case.case_id, status, qemu_case.dos_dir, str(qemu_case.capture), elapsed, comparison, error)
        )
        if stop_on_failure and status != "match":
            break
    return results


def write_report(results: list[OverlayBatchResult], output: Path) -> dict[str, object]:
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
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS / "object_overlay_base.json")
    parser.add_argument("--dos-prefix", default="OP")
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
