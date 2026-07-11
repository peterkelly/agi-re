#!/usr/bin/env python3
"""QEMU snapshot batch helpers for original-engine fixture runs."""

from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from project_paths import dos_image

DEFAULT_DOS_IMAGE = dos_image()
DOS_IMAGE_OFFSET = "auto"


@dataclass(frozen=True)
class SnapshotFixtureCase:
    dos_dir: str
    fixture: Path
    capture: Path
    launch_command: str = "SIERRA"
    post_launch_keys: str = ""
    post_launch_wait: float = 0.0
    post_launch_key_delay: float = 0.03
    post_launch_after_text_wait: float = 0.0
    post_launch_key_names: list[str] | None = None


def fixture_input_files(fixture: Path) -> list[Path]:
    """Return fixture files that should be copied into a DOS test directory."""
    return sorted(path for path in fixture.iterdir() if path.is_file() and path.suffix.lower() != ".ppm")


def detect_partition_offset(raw_image: Path) -> str:
    """Return the byte offset of the first partition in a raw disk image."""
    mbr = raw_image.read_bytes()[:512]
    if len(mbr) < 512 or mbr[510:512] != b"\x55\xaa":
        return "0"
    for table_offset in range(0x1BE, 0x1FE, 16):
        entry = mbr[table_offset : table_offset + 16]
        partition_type = entry[4]
        first_lba = int.from_bytes(entry[8:12], "little")
        sectors = int.from_bytes(entry[12:16], "little")
        if partition_type and first_lba and sectors:
            return str(first_lba * 512)
    return "0"


def mtools_image(raw_image: Path, offset: str | int | None = DOS_IMAGE_OFFSET) -> str:
    if offset == "auto":
        offset = detect_partition_offset(raw_image)
    if offset is None or str(offset) in ("", "0"):
        return str(raw_image)
    return f"{raw_image}@@{offset}"


def snapshot_chunk_path(path: Path, chunk_index: int) -> Path:
    return path.with_name(f"{path.stem}_chunk_{chunk_index:03d}{path.suffix}")


def remove_dos_dir(image: str, dos_dir: str) -> None:
    subprocess.run(["mdel", "-i", image, f"::/{dos_dir}/*"], check=False, capture_output=True, text=True)
    subprocess.run(["mrd", "-i", image, f"::/{dos_dir}"], check=False, capture_output=True, text=True)


def copy_fixture_to_image(fixture: Path, image: str, dos_dir: str) -> None:
    remove_dos_dir(image, dos_dir)
    subprocess.run(["mmd", "-i", image, f"::/{dos_dir}"], check=True)
    files = [str(path) for path in fixture_input_files(fixture)]
    if not files:
        raise ValueError(f"fixture has no input files: {fixture}")
    subprocess.run(["mcopy", "-o", "-i", image, *files, f"::/{dos_dir}"], check=True)


def build_snapshot_boot_disk(
    cases: list[SnapshotFixtureCase],
    raw_output: Path,
    qcow_output: Path,
    base_image: Path = DEFAULT_DOS_IMAGE,
    offset: str = DOS_IMAGE_OFFSET,
) -> Path:
    """Clone the DOS boot image, preload fixture dirs, and convert it to qcow2."""
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    qcow_output.parent.mkdir(parents=True, exist_ok=True)
    if raw_output.exists():
        raw_output.unlink()
    if qcow_output.exists():
        qcow_output.unlink()
    shutil.copyfile(base_image, raw_output)
    image = mtools_image(raw_output, offset)
    for case in cases:
        copy_fixture_to_image(case.fixture, image, case.dos_dir)
    subprocess.run(["qemu-img", "convert", "-f", "raw", "-O", "qcow2", str(raw_output), str(qcow_output)], check=True)
    return qcow_output


def dos_key_name(character: str) -> str:
    if character == "\\":
        return "backslash"
    if character == "-":
        return "minus"
    if character == " ":
        return "spc"
    if character == "\n":
        return "ret"
    if character == ":":
        return "shift-semicolon"
    if character == ".":
        return "dot"
    return character.lower()


def monitor_type(proc: subprocess.Popen[str], text: str, delay: float = 0.03) -> None:
    assert proc.stdin is not None
    for character in text:
        if proc.poll() is not None:
            raise RuntimeError(f"qemu exited before monitor input completed: {proc.returncode}")
        proc.stdin.write(f"sendkey {dos_key_name(character)}\n")
        proc.stdin.flush()
        time.sleep(delay)


def monitor_send_key_names(proc: subprocess.Popen[str], names: list[str], delay: float = 0.03) -> None:
    assert proc.stdin is not None
    for name in names:
        if proc.poll() is not None:
            raise RuntimeError(f"qemu exited before monitor key input completed: {proc.returncode}")
        proc.stdin.write(f"sendkey {name}\n")
        proc.stdin.flush()
        time.sleep(delay)


def monitor_command(proc: subprocess.Popen[str], command: str) -> None:
    if proc.poll() is not None:
        raise RuntimeError(f"qemu exited before monitor command: {proc.returncode}")
    assert proc.stdin is not None
    proc.stdin.write(command.rstrip() + "\n")
    proc.stdin.flush()


def run_snapshot_qemu_cases(
    disk_image: Path,
    cases: list[SnapshotFixtureCase],
    boot_wait: float,
    draw_wait: float,
    snapshot_name: str = "ready",
    vnc_display: str = "127.0.0.1:5",
) -> None:
    """Boot once, save a DOS-prompt snapshot, and restore it between cases."""
    for case in cases:
        case.capture.parent.mkdir(parents=True, exist_ok=True)
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
        monitor_command(proc, f"savevm {snapshot_name}")
        time.sleep(1.0)
        for case in cases:
            monitor_command(proc, f"loadvm {snapshot_name}")
            time.sleep(0.5)
            monitor_type(proc, f"cd \\{case.dos_dir}\n")
            time.sleep(0.5)
            monitor_type(proc, f"{case.launch_command}\n")
            if case.post_launch_wait:
                time.sleep(case.post_launch_wait)
            if case.post_launch_keys:
                monitor_type(proc, case.post_launch_keys, delay=case.post_launch_key_delay)
            if case.post_launch_after_text_wait:
                time.sleep(case.post_launch_after_text_wait)
            if case.post_launch_key_names:
                monitor_send_key_names(proc, case.post_launch_key_names, delay=case.post_launch_key_delay)
            time.sleep(draw_wait)
            monitor_command(proc, f"screendump {case.capture}")
            time.sleep(1.0)
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
