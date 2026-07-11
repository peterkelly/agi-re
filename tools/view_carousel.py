#!/usr/bin/env python3
"""Run fast in-engine QEMU sweeps over picture plus view/cel cases."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from compare_picture_capture import PictureCaptureComparison, compare_picture_capture
from qemu_fixture import build_view_timed_carousel_fixture
from qemu_snapshot import (
    SnapshotFixtureCase,
    build_snapshot_boot_disk,
    monitor_command,
    monitor_type,
    qemu_vga_args,
)
from view_batch import ViewBatchCase, expected_view_tuple, load_cases


DEFAULT_FIXTURE_ROOT = Path("build/view-carousel/fixtures")
DEFAULT_RESULTS = Path("build/view-carousel/batches")
DEFAULT_SNAPSHOT_RAW = Path("build/view-carousel/snapshot/view_carousel.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/view-carousel/snapshot/view_carousel.qcow2")


@dataclass(frozen=True)
class ViewCarouselResult:
    case_id: str
    picture_no: int
    view_no: int
    group_no: int
    frame_no: int
    status: str
    capture: str
    elapsed_seconds: float
    comparison: PictureCaptureComparison | None
    error: str | None


def qemu_dos_dir(name: str) -> str:
    clean = "".join(character for character in name.upper() if character.isalnum()) or "VIEWSW"
    return clean[:8]


def qemu_chunk_dos_dir(name: str, chunk_index: int) -> str:
    if chunk_index < 0:
        raise ValueError("chunk index must be non-negative")
    clean = "".join(character for character in name.upper() if character.isalnum()) or "VIEW"
    return f"{clean[:5]}{chunk_index:03d}"[:8]


def numbered_path(path: Path, index: int) -> Path:
    return path.with_name(f"{path.stem}_chunk_{index:03d}{path.suffix}")


def carousel_case_tuple(case: ViewBatchCase) -> tuple[int, int, int, int, int, int, int, int | None]:
    return (
        case.picture_no,
        case.view_no,
        case.group_no,
        case.frame_no,
        case.x,
        case.baseline_y,
        case.priority,
        case.control,
    )


def run_view_carousel_qemu_poll(
    disk_image: Path,
    dos_dir: str,
    cases: list[ViewBatchCase],
    captures: list[Path],
    boot_wait: float,
    first_wait: float,
    poll_interval: float,
    poll_timeout: float,
    vnc_display: str = "127.0.0.1:5",
) -> None:
    for capture in captures:
        capture.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "qemu-system-i386",
        "-m",
        "16",
        "-boot",
        "c",
        "-drive",
        f"file={disk_image},format=qcow2,if=ide,index=0,media=disk",
        *qemu_vga_args(),
        "-display",
        f"vnc={vnc_display}",
        "-monitor",
        "stdio",
    ]
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        time.sleep(boot_wait)
        monitor_type(proc, f"cd \\{dos_dir}\n")
        time.sleep(0.5)
        monitor_type(proc, "SIERRA\n")
        time.sleep(first_wait)
        total = len(cases)
        for index, (case, capture) in enumerate(zip(cases, captures), start=1):
            deadline = time.monotonic() + poll_timeout
            matched = False
            while True:
                monitor_command(proc, f"screendump {capture}")
                time.sleep(0.2)
                comparison = compare_picture_capture(case.picture_no, capture, view=expected_view_tuple(case))
                if comparison.matches:
                    matched = True
                    break
                if time.monotonic() >= deadline:
                    break
                time.sleep(poll_interval)
            status = "matched" if matched else "timed out"
            print(
                f"poll {status} [{index}/{total}] {case.case_id}",
                file=sys.stderr,
                flush=True,
            )
        monitor_command(proc, "quit")
        proc.wait(timeout=10)
        if proc.returncode != 0:
            output = proc.stdout.read() if proc.stdout is not None else ""
            raise RuntimeError(f"qemu exited with {proc.returncode}:\n{output}")
    except Exception as exc:
        output = proc.stdout.read() if proc.stdout is not None else ""
        if output:
            raise RuntimeError(f"{exc}\nqemu output:\n{output}") from exc
        raise
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)


def run_carousel(
    cases: list[ViewBatchCase],
    fixture_root: Path,
    dos_dir: str,
    boot_wait: float,
    first_wait: float,
    delay_cycles: int,
    speed_value: int,
    poll_interval: float,
    poll_timeout: float,
    snapshot_raw: Path,
    snapshot_qcow: Path,
) -> list[ViewCarouselResult]:
    if not cases:
        return []
    fixture = fixture_root / "carousel"
    captures = [fixture / f"qemu_view_{index:03d}_{case.case_id}.ppm" for index, case in enumerate(cases)]
    print(
        f"building timed view carousel fixture with {len(cases)} cases, {delay_cycles} delay cycles, speed {speed_value} -> {dos_dir}",
        file=sys.stderr,
        flush=True,
    )
    build_view_timed_carousel_fixture(
        [carousel_case_tuple(case) for case in cases],
        fixture,
        delay_cycles,
        speed_value,
    )
    print(f"building snapshot disk: {snapshot_qcow}", file=sys.stderr, flush=True)
    build_snapshot_boot_disk([SnapshotFixtureCase(dos_dir, fixture, captures[0])], snapshot_raw, snapshot_qcow)
    print(f"running one-engine view carousel for {len(cases)} cases", file=sys.stderr, flush=True)
    started = time.monotonic()
    run_view_carousel_qemu_poll(
        snapshot_qcow,
        dos_dir,
        cases,
        captures,
        boot_wait,
        first_wait,
        poll_interval,
        poll_timeout,
    )

    results: list[ViewCarouselResult] = []
    for index, (case, capture) in enumerate(zip(cases, captures)):
        comparison: PictureCaptureComparison | None = None
        error: str | None = None
        status = "error"
        try:
            comparison = compare_picture_capture(case.picture_no, capture, view=expected_view_tuple(case))
            status = "match" if comparison.matches else "mismatch"
        except Exception as exc:  # noqa: BLE001 - batch harness records exact local exception.
            error = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.monotonic() - started, 3)
        print(f"[{index + 1}/{len(cases)}] {case.case_id} {status}", file=sys.stderr, flush=True)
        results.append(
            ViewCarouselResult(
                case.case_id,
                case.picture_no,
                case.view_no,
                case.group_no,
                case.frame_no,
                status,
                str(capture),
                elapsed,
                comparison,
                error,
            )
        )
    return results


def run_chunked_carousel(
    cases: list[ViewBatchCase],
    chunk_size: int,
    fixture_root: Path,
    dos_dir: str,
    boot_wait: float,
    first_wait: float,
    delay_cycles: int,
    speed_value: int,
    poll_interval: float,
    poll_timeout: float,
    snapshot_raw: Path,
    snapshot_qcow: Path,
) -> list[ViewCarouselResult]:
    if chunk_size <= 0:
        return run_carousel(
            cases,
            fixture_root,
            dos_dir,
            boot_wait,
            first_wait,
            delay_cycles,
            speed_value,
            poll_interval,
            poll_timeout,
            snapshot_raw,
            snapshot_qcow,
        )

    results: list[ViewCarouselResult] = []
    chunks = [
        cases[index : index + chunk_size]
        for index in range(0, len(cases), chunk_size)
    ]
    for chunk_index, chunk in enumerate(chunks):
        print(
            f"running view carousel chunk {chunk_index + 1}/{len(chunks)} with {len(chunk)} cases",
            file=sys.stderr,
            flush=True,
        )
        results.extend(
            run_carousel(
                chunk,
                fixture_root / f"chunk_{chunk_index:03d}",
                qemu_chunk_dos_dir(dos_dir, chunk_index),
                boot_wait,
                first_wait,
                delay_cycles,
                speed_value,
                poll_interval,
                poll_timeout,
                numbered_path(snapshot_raw, chunk_index),
                numbered_path(snapshot_qcow, chunk_index),
            )
        )
    return results


def write_report(results: list[ViewCarouselResult], output: Path) -> dict[str, object]:
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
    parser.add_argument("--include-stress", action="store_true")
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS / "view_carousel_base.json")
    parser.add_argument("--dos-dir", default="VIEWSW")
    parser.add_argument("--boot-wait", type=float, default=5.0)
    parser.add_argument("--first-wait", type=float, default=3.0)
    parser.add_argument("--delay-cycles", type=int, default=120)
    parser.add_argument("--speed-value", type=int, default=1)
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--poll-timeout", type=float, default=20.0)
    parser.add_argument("--chunk-size", type=int, default=0)
    parser.add_argument("--snapshot-raw", type=Path, default=DEFAULT_SNAPSHOT_RAW)
    parser.add_argument("--snapshot-qcow", type=Path, default=DEFAULT_SNAPSHOT_QCOW)
    args = parser.parse_args()

    cases = load_cases(args.cases, args.include_stress, args.case_ids)
    results = run_chunked_carousel(
        cases,
        args.chunk_size,
        args.fixture_root,
        qemu_dos_dir(args.dos_dir),
        args.boot_wait,
        args.first_wait,
        args.delay_cycles,
        args.speed_value,
        args.poll_interval,
        args.poll_timeout,
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
