#!/usr/bin/env python3
"""Capture visual and priority/control screens from an original AGI interpreter."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from agi_resources import (
    ResourceFormatError,
    detect_layout,
    read_directory_entries,
    read_volume_record,
    volume_path,
)
from conformance_results import (
    FRAME_HEIGHT,
    FRAME_WIDTH,
    canonical_frame_from_artifact_ppm,
    canonical_frame_from_ppm,
    canonical_ppm_bytes,
)
from ppm_tools import read_ppm
from project_paths import game_dir as configured_game_dir
from qemu_fixture import (
    build_original_picture_channel_fixture,
    build_synthetic_picture_channel_fixture,
    original_picture_record_bytes,
    picture_support_file_names,
)
from qemu_snapshot import (
    DEFAULT_DOS_IMAGE,
    SnapshotFixtureCase,
    build_snapshot_boot_disk,
    qemu_vga_args,
    run_snapshot_qemu_cases,
)


FORMAT_NAME = "agi-original-picture-screen-captures"
FORMAT_VERSION = 2
DEFAULT_OUTPUT = Path("build/picture-screen-capture")
CHANNELS = ("visual", "priority")


@dataclass(frozen=True)
class PictureSource:
    picture_no: int
    status: str
    volume: int | None
    offset: int | None
    stored_length: int | None
    expanded_length: int | None
    transform: str | None
    record_sha256: str | None
    error: str | None


@dataclass
class PendingCapture:
    case_id: str
    picture_no: int
    channel: str
    source: PictureSource
    fixture: Path | None
    capture: Path
    build_seconds: float
    build_error: str | None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def game_file_hashes(game_dir: Path, sources: list[PictureSource]) -> dict[str, str]:
    layout = detect_layout(game_dir)
    support_names = picture_support_file_names(game_dir)
    paths = {
        path
        for path in Path(game_dir).iterdir()
        if path.is_file() and path.name.upper() in support_names
    }
    for source in sources:
        if source.volume is not None:
            paths.add(volume_path(game_dir, layout, source.volume))
    return {
        path.name: sha256_file(path)
        for path in sorted(paths, key=lambda item: item.name.upper())
    }


def detect_launch_command(game_dir: Path) -> str:
    files = {path.name.upper(): path for path in Path(game_dir).iterdir() if path.is_file()}
    if "SIERRA.COM" in files:
        return "SIERRA"
    com_files = sorted(path for name, path in files.items() if name.endswith(".COM"))
    if len(com_files) == 1:
        return com_files[0].stem
    if "AGI.EXE" in files:
        return "AGI"
    if "AGI" in files:
        return "AGI"
    raise ValueError("could not detect a DOS launch command; pass --launch-command")


def enumerate_picture_sources(
    game_dir: Path,
    selected: list[int] | None = None,
) -> tuple[list[PictureSource], int, int]:
    entries = read_directory_entries(game_dir, "picture")
    selected_numbers = list(dict.fromkeys(selected)) if selected else [
        number for number, entry in enumerate(entries) if entry is not None
    ]
    sources: list[PictureSource] = []
    for picture_no in selected_numbers:
        if not 0 <= picture_no <= 0xFF:
            sources.append(
                PictureSource(
                    picture_no,
                    "error",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "picture number must fit in one byte",
                )
            )
            continue
        if picture_no >= len(entries) or entries[picture_no] is None:
            sources.append(
                PictureSource(
                    picture_no,
                    "absent",
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "picture directory entry is absent",
                )
            )
            continue
        try:
            record = read_volume_record(game_dir, "picture", picture_no)
            raw = original_picture_record_bytes(game_dir, picture_no)
            sources.append(
                PictureSource(
                    picture_no,
                    "valid",
                    record.entry.volume,
                    record.entry.offset,
                    record.stored_length,
                    record.expanded_length,
                    record.transform,
                    sha256_bytes(raw),
                    None,
                )
            )
        except (OSError, IndexError, ResourceFormatError, ValueError) as exc:
            sources.append(
                PictureSource(
                    picture_no,
                    "error",
                    entries[picture_no].volume,
                    entries[picture_no].offset,
                    None,
                    None,
                    None,
                    None,
                    f"{type(exc).__name__}: {exc}",
                )
            )
    return sources, len(entries), sum(entry is not None for entry in entries)


def capture_case_id(picture_no: int, channel: str) -> str:
    return f"picture_{picture_no:03d}/{channel}"


def capture_dos_dir(picture_no: int, channel: str) -> str:
    suffix = "V" if channel == "visual" else "P"
    return f"PC{picture_no:03X}{suffix}"


def relative_path(path: Path, parent: Path) -> str:
    return os.path.relpath(path, parent)


def qemu_version() -> str | None:
    try:
        result = subprocess.run(
            ["qemu-system-i386", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.splitlines()[0] if result.stdout else None


def vga_configuration() -> dict[str, object]:
    args = qemu_vga_args()
    rom_path: Path | None = None
    for argument in args:
        if argument.startswith("VGA,romfile="):
            rom_path = Path(argument.split("=", 1)[1])
            break
    return {
        "arguments": args,
        "rom": None if rom_path is None else str(rom_path),
        "rom_sha256": None if rom_path is None else sha256_file(rom_path),
    }


def build_pending_captures(
    game_dir: Path,
    sources: list[PictureSource],
    fixture_root: Path,
    raw_root: Path,
    include_invalid_results: bool = True,
) -> tuple[list[PendingCapture], list[SnapshotFixtureCase]]:
    pending: list[PendingCapture] = []
    qemu_cases: list[SnapshotFixtureCase] = []
    total = sum(source.status == "valid" for source in sources) * len(CHANNELS)
    index = 0
    for source in sources:
        if source.status != "valid" and not include_invalid_results:
            continue
        for channel in CHANNELS:
            capture = (raw_root / f"picture_{source.picture_no:03d}_{channel}.ppm").resolve()
            if source.status != "valid":
                pending.append(
                    PendingCapture(
                        capture_case_id(source.picture_no, channel),
                        source.picture_no,
                        channel,
                        source,
                        None,
                        capture,
                        0.0,
                        source.error or f"source status is {source.status}",
                    )
                )
                continue
            index += 1
            fixture = fixture_root / f"picture_{source.picture_no:03d}_{channel}"
            started = time.monotonic()
            error: str | None = None
            print(
                f"[{index}/{total}] build picture {source.picture_no:03d} {channel}",
                file=sys.stderr,
                flush=True,
            )
            try:
                build_original_picture_channel_fixture(
                    source.picture_no,
                    channel,
                    fixture,
                    game_dir=game_dir,
                )
                qemu_cases.append(
                    SnapshotFixtureCase(
                        capture_dos_dir(source.picture_no, channel),
                        fixture,
                        capture,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - report exact fixture failure.
                error = f"{type(exc).__name__}: {exc}"
            pending.append(
                PendingCapture(
                    capture_case_id(source.picture_no, channel),
                    source.picture_no,
                    channel,
                    source,
                    fixture,
                    capture,
                    round(time.monotonic() - started, 3),
                    error,
                )
            )
    return pending, qemu_cases


def build_preflight_captures(
    game_dir: Path,
    sources: list[PictureSource],
    fixture_root: Path,
    raw_root: Path,
) -> tuple[list[PendingCapture], list[SnapshotFixtureCase]]:
    source = next((item for item in sources if item.status == "valid"), None)
    if source is None or source.volume is None:
        return [], []
    picture_payload = bytes([0xFF])
    synthetic_source = PictureSource(
        source.picture_no,
        "synthetic",
        source.volume,
        None,
        1,
        1,
        "controlled_blank",
        sha256_bytes(picture_payload),
        None,
    )
    pending: list[PendingCapture] = []
    cases: list[SnapshotFixtureCase] = []
    for channel in CHANNELS:
        fixture = fixture_root / channel
        capture = (raw_root / f"preflight_{channel}.ppm").resolve()
        started = time.monotonic()
        error: str | None = None
        try:
            build_synthetic_picture_channel_fixture(
                source.picture_no,
                channel,
                picture_payload,
                fixture,
                game_dir=game_dir,
                volume=source.volume,
            )
            cases.append(
                SnapshotFixtureCase(
                    "PCPFV" if channel == "visual" else "PCPFP",
                    fixture,
                    capture,
                )
            )
        except Exception as exc:  # noqa: BLE001 - report exact preflight failure.
            error = f"{type(exc).__name__}: {exc}"
        pending.append(
            PendingCapture(
                f"preflight/{channel}",
                source.picture_no,
                channel,
                synthetic_source,
                fixture,
                capture,
                round(time.monotonic() - started, 3),
                error,
            )
        )
    return pending, cases


def materialize_results(
    pending: list[PendingCapture],
    manifest_path: Path,
    canonical_root: Path,
    qemu_error: str | None,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    canonical_root.mkdir(parents=True, exist_ok=True)
    for item in pending:
        result: dict[str, object] = {
            "case_id": item.case_id,
            "picture_no": item.picture_no,
            "channel": item.channel,
            "status": "error",
            "source": asdict(item.source),
            "fixture": None if item.fixture is None else relative_path(item.fixture, manifest_path.parent),
            "capture": relative_path(item.capture, manifest_path.parent),
            "build_seconds": item.build_seconds,
            "raw_sha256": None,
            "canonical_ppm": None,
            "canonical_sha256": None,
            "error": item.build_error,
        }
        if item.build_error is not None:
            results.append(result)
            continue
        if not item.capture.is_file():
            result["error"] = qemu_error or "QEMU capture file was not produced"
            results.append(result)
            continue
        try:
            image = read_ppm(item.capture)
            if (image.width, image.height, image.max_value) != (640, 400, 255):
                raise ValueError(
                    f"raw QEMU capture is {image.width}x{image.height} max {image.max_value}, "
                    "expected 640x400 max 255"
                )
            frame = canonical_frame_from_ppm(item.capture)
            stem = f"picture_{item.picture_no:03d}_{item.channel}"
            ppm_path = canonical_root / f"{stem}.ppm"
            ppm_path.write_bytes(canonical_ppm_bytes(frame))
            result.update(
                {
                    "status": "ok",
                    "raw_sha256": sha256_file(item.capture),
                    "canonical_ppm": relative_path(ppm_path, manifest_path.parent),
                    "canonical_sha256": sha256_bytes(frame),
                    "error": None,
                }
            )
        except Exception as exc:  # noqa: BLE001 - preserve exact artifact failure.
            result["error"] = f"{type(exc).__name__}: {exc}"
        results.append(result)
    return results


def validate_preflight(results: list[dict[str, object]], manifest_parent: Path) -> dict[str, object]:
    expected = {"visual": [15], "priority": [4]}
    observed: dict[str, list[int] | None] = {}
    errors: list[str] = []
    by_channel = {result.get("channel"): result for result in results}
    for channel in CHANNELS:
        result = by_channel.get(channel)
        if result is None or result.get("status") != "ok":
            error = None if result is None else result.get("error")
            errors.append(f"{channel} preflight capture failed: {error or 'missing result'}")
            observed[channel] = None
            continue
        artifact = result.get("canonical_ppm")
        if not isinstance(artifact, str):
            errors.append(f"{channel} preflight lacks a canonical PPM")
            observed[channel] = None
            continue
        values = sorted(set(canonical_frame_from_artifact_ppm(manifest_parent / artifact)))
        observed[channel] = values
        if values != expected[channel]:
            errors.append(
                f"{channel} preflight colors {values} do not match expected {expected[channel]}"
            )
    return {
        "passed": not errors,
        "picture_no": results[0]["picture_no"] if results else None,
        "expected_palette_indexes": expected,
        "observed_palette_indexes": observed,
        "error": None if not errors else "; ".join(errors),
        "results": results,
    }


def write_manifest(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii")


def main() -> None:
    selected_game = configured_game_dir().resolve()
    parser = argparse.ArgumentParser(
        description="Capture all present picture visual and priority screens from QEMU. "
        "Pass --game-dir PATH or set AGI_GAME_DIR."
    )
    parser.add_argument("--picture", type=int, action="append", dest="pictures")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fixture-root", type=Path)
    parser.add_argument("--snapshot-raw", type=Path)
    parser.add_argument("--snapshot-qcow", type=Path)
    parser.add_argument("--dos-image", type=Path, default=DEFAULT_DOS_IMAGE)
    parser.add_argument("--launch-command")
    parser.add_argument("--boot-wait", type=float, default=5.0)
    parser.add_argument("--draw-wait", type=float, default=8.0)
    parser.add_argument(
        "--reuse-captures",
        action="store_true",
        help="reuse existing raw PPM files instead of starting QEMU",
    )
    args = parser.parse_args()

    output = args.output
    manifest_path = output / "manifest.json"
    fixture_root = args.fixture_root or output / "fixtures"
    snapshot_raw = args.snapshot_raw or output / "snapshot" / "picture_screens.raw"
    snapshot_qcow = args.snapshot_qcow or output / "snapshot" / "picture_screens.qcow2"
    raw_root = output / "raw"
    canonical_root = output / "canonical"
    raw_root.mkdir(parents=True, exist_ok=True)

    layout = detect_layout(selected_game)
    sources, directory_entry_count, directory_present_count = enumerate_picture_sources(
        selected_game,
        args.pictures,
    )
    initial_hashes = game_file_hashes(selected_game, sources)
    launch_command = args.launch_command or detect_launch_command(selected_game)
    pending, qemu_cases = build_pending_captures(
        selected_game,
        sources,
        fixture_root,
        raw_root,
        include_invalid_results=args.pictures is not None,
    )
    preflight_pending, preflight_cases = build_preflight_captures(
        selected_game,
        sources,
        fixture_root / "preflight",
        output / "preflight" / "raw",
    )
    all_qemu_cases = preflight_cases + qemu_cases

    qemu_error: str | None = None
    qemu_started = time.monotonic()
    if args.reuse_captures:
        missing = [case.capture for case in all_qemu_cases if not case.capture.is_file()]
        if missing:
            qemu_error = f"reuse requested but {len(missing)} raw capture files are missing"
        else:
            print(f"reusing {len(all_qemu_cases)} existing raw captures", file=sys.stderr, flush=True)
    elif all_qemu_cases:
        try:
            print(
                f"building snapshot disk for {len(all_qemu_cases)} captures",
                file=sys.stderr,
                flush=True,
            )
            build_snapshot_boot_disk(
                all_qemu_cases,
                snapshot_raw,
                snapshot_qcow,
                base_image=args.dos_image,
            )
            adjusted_cases = [
                SnapshotFixtureCase(
                    case.dos_dir,
                    case.fixture,
                    case.capture,
                    launch_command=launch_command,
                )
                for case in all_qemu_cases
            ]
            print("running original-interpreter captures", file=sys.stderr, flush=True)
            run_snapshot_qemu_cases(
                snapshot_qcow,
                adjusted_cases,
                args.boot_wait,
                args.draw_wait,
                progress=True,
            )
        except Exception as exc:  # noqa: BLE001 - manifest records exact QEMU failure.
            qemu_error = f"{type(exc).__name__}: {exc}"
            print(qemu_error, file=sys.stderr)
    else:
        qemu_error = "no valid picture captures were built"

    preflight_results = materialize_results(
        preflight_pending,
        manifest_path,
        output / "preflight" / "canonical",
        qemu_error,
    )
    preflight = validate_preflight(preflight_results, manifest_path.parent)
    results = materialize_results(pending, manifest_path, canonical_root, qemu_error)
    if not preflight["passed"]:
        for result in results:
            if result["status"] == "ok":
                result["status"] = "error"
                result["error"] = f"interpreter preflight failed: {preflight['error']}"
    final_hashes = game_file_hashes(selected_game, sources)
    report: dict[str, object] = {
        "format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
        "game": {
            "path": str(selected_game),
            "layout": layout.version,
            "prefix": layout.prefix,
            "directory_entry_count": directory_entry_count,
            "directory_present_count": directory_present_count,
            "selected_count": len(sources),
            "selected_valid_count": sum(source.status == "valid" for source in sources),
            "invalid_source_count": sum(source.status == "error" for source in sources),
            "source_inventory": [asdict(source) for source in sources],
            "files_sha256": initial_hashes,
            "input_unchanged": initial_hashes == final_hashes,
        },
        "capture_contract": {
            "raw": "QEMU screendump P6 PPM, 640x400",
            "canonical_width": FRAME_WIDTH,
            "canonical_height": FRAME_HEIGHT,
            "canonical": "P6 PPM, 160x168, max value 255, exact EGA16 RGB palette",
            "source_scaling": {"x": 4, "y": 2, "origin": [0, 0]},
            "priority_channel": "interpreter action 0x1d displayed priority/control view",
        },
        "preflight": preflight,
        "qemu": {
            "version": qemu_version(),
            "launch_command": launch_command,
            "dos_image": str(args.dos_image),
            "dos_image_sha256": sha256_file(args.dos_image) if args.dos_image.is_file() else None,
            "vga": vga_configuration(),
            "boot_wait": args.boot_wait,
            "draw_wait": args.draw_wait,
            "snapshot_raw": str(snapshot_raw),
            "snapshot_qcow": str(snapshot_qcow),
            "elapsed_seconds": round(time.monotonic() - qemu_started, 3),
            "error": qemu_error,
            "reused_captures": args.reuse_captures,
        },
        "summary": {
            "pictures_requested": (
                len(sources)
                if args.pictures is not None
                else sum(source.status == "valid" for source in sources)
            ),
            "channels_expected": len(pending),
            "captures_ok": sum(result["status"] == "ok" for result in results),
            "errors": sum(result["status"] != "ok" for result in results),
            "invalid_source_entries": sum(source.status == "error" for source in sources),
        },
        "results": results,
    }
    if initial_hashes != final_hashes:
        report["qemu"]["error"] = "selected game input changed during capture"
    write_manifest(manifest_path, report)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    print(f"manifest: {manifest_path}")
    if report["summary"]["errors"] or not report["game"]["input_unchanged"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
