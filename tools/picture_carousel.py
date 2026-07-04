#!/usr/bin/env python3
"""Run fast in-engine QEMU sweeps over picture resources."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from compare_picture_capture import PictureCaptureComparison, compare_picture_capture
from picture_batch import PictureBatchCase, load_cases
from qemu_fixture import build_picture_carousel_fixture, build_picture_timed_carousel_fixture
from qemu_snapshot import (
    SnapshotFixtureCase,
    build_snapshot_boot_disk,
    monitor_command,
    monitor_send_key_names,
    monitor_type,
)


DEFAULT_FIXTURE_ROOT = Path("build/picture-carousel/fixtures")
DEFAULT_RESULTS = Path("build/picture-carousel/batches")
DEFAULT_SNAPSHOT_RAW = Path("build/picture-carousel/snapshot/picture_carousel.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/picture-carousel/snapshot/picture_carousel.qcow2")
DEFAULT_ADVANCE_KEYS = "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10"
BIOS_KEY_WORDS = {
    "f1": 0x3B00,
    "f2": 0x3C00,
    "f3": 0x3D00,
    "f4": 0x3E00,
    "f5": 0x3F00,
    "f6": 0x4000,
    "f7": 0x4100,
    "f8": 0x4200,
    "f9": 0x4300,
    "f10": 0x4400,
    "esc": 0x001B,
    "ret": 0x000D,
}


@dataclass(frozen=True)
class PictureCarouselResult:
    case_id: str
    picture_no: int
    status: str
    capture: str
    elapsed_seconds: float
    comparison: PictureCaptureComparison | None
    error: str | None


def parse_advance_keys(text: str) -> list[str]:
    keys = [key.strip() for key in text.split(",") if key.strip()]
    if not keys:
        raise ValueError("at least one advance key is required")
    return keys


def advance_key_words(keys: list[str]) -> list[int]:
    words: list[int] = []
    for key in keys:
        lowered = key.lower()
        if lowered in BIOS_KEY_WORDS:
            words.append(BIOS_KEY_WORDS[lowered])
        elif len(key) == 1:
            words.append(ord(key))
        else:
            raise ValueError("mapped carousel advance keys must be single ASCII characters or known key names")
    return words


def run_picture_carousel_qemu(
    disk_image: Path,
    dos_dir: str,
    captures: list[Path],
    boot_wait: float,
    first_wait: float,
    advance_wait: float,
    advance_key: str | None = "x",
    vnc_display: str = "127.0.0.1:5",
) -> None:
    advance_keys = parse_advance_keys(advance_key) if advance_key is not None else []
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
        for index, capture in enumerate(captures):
            monitor_command(proc, f"screendump {capture}")
            time.sleep(1.0)
            if index + 1 < len(captures):
                if advance_keys:
                    monitor_send_key_names(proc, [advance_keys[index % len(advance_keys)]])
                time.sleep(advance_wait)
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


def run_picture_carousel_qemu_poll(
    disk_image: Path,
    dos_dir: str,
    cases: list[PictureBatchCase],
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
        for case, capture in zip(cases, captures):
            deadline = time.monotonic() + poll_timeout
            while True:
                monitor_command(proc, f"screendump {capture}")
                time.sleep(0.2)
                comparison = compare_picture_capture(case.picture_no, capture)
                if comparison.matches:
                    break
                if time.monotonic() >= deadline:
                    break
                time.sleep(poll_interval)
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


def qemu_dos_dir(name: str) -> str:
    clean = "".join(character for character in name.upper() if character.isalnum()) or "PICSWEEP"
    return clean[:8]


def run_carousel(
    cases: list[PictureBatchCase],
    fixture_root: Path,
    dos_dir: str,
    boot_wait: float,
    first_wait: float,
    advance_wait: float,
    advance_key: str,
    mode: str,
    delay_cycles: int,
    speed_value: int,
    poll: bool,
    poll_interval: float,
    poll_timeout: float,
    snapshot_raw: Path,
    snapshot_qcow: Path,
) -> list[PictureCarouselResult]:
    if not cases:
        return []
    fixture = fixture_root / "carousel"
    captures = [fixture / f"qemu_picture_{case.picture_no:03d}.ppm" for case in cases]
    if mode == "key":
        key_names = parse_advance_keys(advance_key)
        key_words = advance_key_words(key_names)
        if len(key_words) < len(cases) - 1:
            raise ValueError("picture carousel requires one mapped advance key per transition")
        qemu_advance_key = ",".join(key_names)
        print(f"building key carousel fixture with {len(cases)} pictures -> {dos_dir}", file=sys.stderr, flush=True)
        build_picture_carousel_fixture([case.picture_no for case in cases], fixture, key_words)
    elif mode == "timed":
        qemu_advance_key = None
        print(
            f"building timed carousel fixture with {len(cases)} pictures, {delay_cycles} delay cycles, speed {speed_value} -> {dos_dir}",
            file=sys.stderr,
            flush=True,
        )
        build_picture_timed_carousel_fixture([case.picture_no for case in cases], fixture, delay_cycles, speed_value)
    else:
        raise ValueError(f"unknown carousel mode: {mode}")
    print(f"building snapshot disk: {snapshot_qcow}", file=sys.stderr, flush=True)
    build_snapshot_boot_disk([SnapshotFixtureCase(dos_dir, fixture, captures[0])], snapshot_raw, snapshot_qcow)
    print(f"running one-engine carousel for {len(cases)} pictures", file=sys.stderr, flush=True)
    started = time.monotonic()
    if poll:
        run_picture_carousel_qemu_poll(
            snapshot_qcow,
            dos_dir,
            cases,
            captures,
            boot_wait,
            first_wait,
            poll_interval,
            poll_timeout,
        )
    else:
        run_picture_carousel_qemu(snapshot_qcow, dos_dir, captures, boot_wait, first_wait, advance_wait, qemu_advance_key)

    results: list[PictureCarouselResult] = []
    for index, (case, capture) in enumerate(zip(cases, captures)):
        comparison: PictureCaptureComparison | None = None
        error: str | None = None
        status = "error"
        try:
            comparison = compare_picture_capture(case.picture_no, capture)
            status = "match" if comparison.matches else "mismatch"
        except Exception as exc:  # noqa: BLE001 - batch harness records exact local exception.
            error = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.monotonic() - started, 3)
        print(f"[{index + 1}/{len(cases)}] {case.case_id} {status}", file=sys.stderr, flush=True)
        results.append(
            PictureCarouselResult(
                case.case_id,
                case.picture_no,
                status,
                str(capture),
                elapsed,
                comparison,
                error,
            )
        )
    return results


def write_report(results: list[PictureCarouselResult], output: Path) -> dict[str, object]:
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
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS / "picture_carousel_base.json")
    parser.add_argument("--dos-dir", default="PICSWEEP")
    parser.add_argument("--boot-wait", type=float, default=5.0)
    parser.add_argument("--first-wait", type=float, default=8.0)
    parser.add_argument("--advance-wait", type=float, default=1.0)
    parser.add_argument("--advance-key", default=DEFAULT_ADVANCE_KEYS)
    parser.add_argument("--mode", choices=["key", "timed"], default="key")
    parser.add_argument("--delay-cycles", type=int, default=120)
    parser.add_argument("--speed-value", type=int, default=1)
    parser.add_argument("--poll", action="store_true")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--poll-timeout", type=float, default=20.0)
    parser.add_argument("--snapshot-raw", type=Path, default=DEFAULT_SNAPSHOT_RAW)
    parser.add_argument("--snapshot-qcow", type=Path, default=DEFAULT_SNAPSHOT_QCOW)
    args = parser.parse_args()

    cases = load_cases(args.cases, args.case_ids, args.preset)
    results = run_carousel(
        cases,
        args.fixture_root,
        qemu_dos_dir(args.dos_dir),
        args.boot_wait,
        args.first_wait,
        args.advance_wait,
        args.advance_key,
        args.mode,
        args.delay_cycles,
        args.speed_value,
        args.poll,
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
