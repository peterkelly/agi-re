#!/usr/bin/env python3
"""Compare unchanged and XOR-encoded inventory metadata under a local engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from agi_save import SQ2_OBJECT_FILE_XOR_KEY, xor_with_repeating_key
from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases


def copy_game(source: Path, destination: Path) -> Path:
    source = source.resolve()
    destination = destination.resolve()
    if "games" in destination.parts:
        raise ValueError("fixture destination must not be under games/")
    if destination.exists():
        for path in (destination, *destination.rglob("*")):
            path.chmod(path.stat().st_mode | 0o700)
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    for path in (destination, *destination.rglob("*")):
        path.chmod(path.stat().st_mode | 0o700)
    return destination


def build_fixtures(game_dir: Path, fixture_root: Path) -> tuple[Path, Path]:
    unchanged = copy_game(game_dir, fixture_root / "object_unchanged")
    encoded = copy_game(game_dir, fixture_root / "object_xor_encoded")
    object_path = encoded / "OBJECT"
    object_path.write_bytes(
        xor_with_repeating_key(object_path.read_bytes(), SQ2_OBJECT_FILE_XOR_KEY)
    )
    return unchanged, encoded


def file_summary(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game-dir", required=True, type=Path)
    parser.add_argument("--fixture-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-qemu", action="store_true")
    parser.add_argument("--snapshot-raw", type=Path)
    parser.add_argument("--snapshot-qcow", type=Path)
    parser.add_argument("--dos-prefix", default="VO")
    parser.add_argument("--boot-wait", type=float, default=5.0)
    parser.add_argument("--draw-wait", type=float, default=8.0)
    parser.add_argument("--advance-loader", action="store_true")
    parser.add_argument("--loader-wait", type=float, default=3.0)
    args = parser.parse_args()

    unchanged, encoded = build_fixtures(args.game_dir, args.fixture_root)
    captures = {
        "unchanged": args.fixture_root / "object_unchanged.ppm",
        "xor_encoded": args.fixture_root / "object_xor_encoded.ppm",
    }
    case_options = {
        "post_launch_wait": args.loader_wait if args.advance_loader else 0.0,
        "post_launch_key_names": ["ret"] if args.advance_loader else None,
    }
    cases = [
        SnapshotFixtureCase(
            f"{args.dos_prefix}U",
            unchanged,
            captures["unchanged"],
            **case_options,
        ),
        SnapshotFixtureCase(
            f"{args.dos_prefix}X",
            encoded,
            captures["xor_encoded"],
            **case_options,
        ),
    ]

    if args.run_qemu:
        if args.snapshot_raw is None or args.snapshot_qcow is None:
            parser.error("--run-qemu requires --snapshot-raw and --snapshot-qcow")
        disk = build_snapshot_boot_disk(cases, args.snapshot_raw, args.snapshot_qcow)
        run_snapshot_qemu_cases(disk, cases, args.boot_wait, args.draw_wait)

    report = {
        "game_dir": str(args.game_dir),
        "key_ascii": SQ2_OBJECT_FILE_XOR_KEY.decode("ascii"),
        "advanced_loader": args.advance_loader,
        "fixtures": {
            "unchanged_object": file_summary(unchanged / "OBJECT"),
            "xor_encoded_object": file_summary(encoded / "OBJECT"),
        },
        "captures": {
            label: file_summary(path) if path.exists() else {"path": str(path), "present": False}
            for label, path in captures.items()
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
