#!/usr/bin/env python3
"""Drive the original engine's save UI and parse the produced save file."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from agi_graphics import PictureRenderer, compose_frame_on_picture, render_view_frame
from agi_save import load_save
from compare_picture_capture import downsample_qemu_picture_nibbles
from ppm_tools import read_ppm
from qemu_fixture import (
    copy_sq2_tree,
    load_show_picture_actions,
    logic_resource,
    patch_dir_entry,
    patch_logdir_entry_zero,
    self_loop,
    setup_transient_object_action,
    volume_record,
)
from qemu_snapshot import (
    DOS_IMAGE_OFFSET,
    SnapshotFixtureCase,
    build_snapshot_boot_disk,
    monitor_command,
    monitor_type,
    mtools_image,
)


DEFAULT_FIXTURE = Path("build/save-roundtrip/fixture")
DEFAULT_OUTPUT = Path("build/save-roundtrip/save_roundtrip_001.json")
DEFAULT_CAPTURE = Path("build/save-roundtrip/qemu_capture.ppm")
DEFAULT_SNAPSHOT_RAW = Path("build/save-roundtrip/snapshot/save_roundtrip.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/save-roundtrip/snapshot/save_roundtrip.qcow2")
DEFAULT_POST_RUN_RAW = Path("build/save-roundtrip/snapshot/save_roundtrip_after.raw")
DEFAULT_SAVE_OUTPUT = Path("build/save-roundtrip/SG.1")


@dataclass(frozen=True)
class SaveRoundTripResult:
    status: str
    dos_dir: str
    capture: str
    save_file: str | None
    description: str | None
    block_lengths: list[int] | None
    visual_status: str | None
    visual_mismatches: int | None
    elapsed_seconds: float
    error: str | None


def byte_action(opcode: int, *operands: int) -> bytes:
    values = [opcode, *operands]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("logic action bytes must fit in one byte")
    return bytes(values)


def save_fixture_logic_payload() -> bytes:
    code = (
        load_show_picture_actions(0)
        + byte_action(0x1E, 11)
        + byte_action(0x7D)
        + byte_action(0x1A)
        + setup_transient_object_action(11, 0, 0, 50, 80, 15, 15)
        + self_loop()
    )
    return logic_resource(code)


def remove_existing_save_files(fixture: Path) -> None:
    for path in fixture.glob("SQ2SG.*"):
        if path.is_file():
            path.unlink()


def build_save_fixture(destination: Path, *, remove_saves: bool = True) -> Path:
    copy_sq2_tree(destination)
    if remove_saves:
        remove_existing_save_files(destination)

    logic_record = volume_record(save_fixture_logic_payload(), volume=3)
    picture_offset = len(logic_record)
    picture_record = volume_record(b"\xff", volume=3)
    (destination / "VOL.3").write_bytes(logic_record + picture_record)

    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))

    picdir = (destination / "PICDIR").read_bytes()
    (destination / "PICDIR").write_bytes(patch_dir_entry(picdir, 0, volume=3, offset=picture_offset))
    return destination


def convert_qcow_to_raw(qcow: Path, raw: Path) -> None:
    raw.parent.mkdir(parents=True, exist_ok=True)
    if raw.exists():
        raw.unlink()
    subprocess.run(["qemu-img", "convert", "-f", "qcow2", "-O", "raw", str(qcow), str(raw)], check=True)


def run_save_qemu_case(
    disk_image: Path,
    dos_dir: str,
    capture: Path,
    boot_wait: float,
    path_prompt_wait: float,
    path_keys: str,
    slot_wait: float,
    slot_keys: str,
    description_wait: float,
    description: str,
    submit_description: bool,
    confirmation_wait: float,
    confirmation_keys: str,
    key_delay: float,
    draw_wait: float,
    vnc_display: str = "127.0.0.1:5",
) -> None:
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
        time.sleep(path_prompt_wait)
        monitor_type(proc, path_keys, delay=key_delay)
        time.sleep(slot_wait)
        monitor_type(proc, slot_keys, delay=key_delay)
        time.sleep(description_wait)
        suffix = "\n" if submit_description else ""
        monitor_type(proc, description + suffix, delay=key_delay)
        if submit_description:
            time.sleep(confirmation_wait)
            monitor_type(proc, confirmation_keys, delay=key_delay)
        time.sleep(draw_wait)
        monitor_command(proc, f"screendump {capture}")
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


def extract_save(raw_image: Path, dos_dir: str, save_stem: str, slot: int, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    subprocess.run(
        [
            "mcopy",
            "-o",
            "-i",
            mtools_image(raw_image, DOS_IMAGE_OFFSET),
            f"::/{dos_dir}/{save_stem}.{slot}",
            str(output),
        ],
        check=True,
    )
    return output


def compare_validation_capture(capture: Path) -> tuple[str, int]:
    captured = downsample_qemu_picture_nibbles(read_ppm(capture))
    picture = PictureRenderer(b"\xff").render(0)
    frame = render_view_frame(11, 0, 0)
    expected = compose_frame_on_picture(picture, frame, 50, 80, 15).visual_nibbles
    mismatches = sum(1 for left, right in zip(captured, expected) if left != right)
    return ("match" if mismatches == 0 else "mismatch", mismatches)


def write_report(result: SaveRoundTripResult, output: Path) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"result": asdict(result)}
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii")
    return report


def run_probe(
    fixture: Path,
    dos_dir: str,
    path_keys: str,
    slot_keys: str,
    save_description: str,
    capture: Path,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    post_run_raw: Path,
    save_output: Path,
    report_output: Path,
    boot_wait: float,
    draw_wait: float,
    path_prompt_wait: float,
    slot_wait: float,
    description_wait: float,
    submit_description: bool,
    confirmation_wait: float,
    confirmation_keys: str,
    key_delay: float,
    save_stem: str,
    slot: int,
    keep_existing_saves: bool,
) -> SaveRoundTripResult:
    started = time.monotonic()
    error: str | None = None
    save_file: str | None = None
    parsed_description: str | None = None
    block_lengths: list[int] | None = None
    visual_status: str | None = None
    visual_mismatches: int | None = None
    status = "error"

    try:
        build_save_fixture(fixture, remove_saves=not keep_existing_saves)
        case = SnapshotFixtureCase(dos_dir, fixture, capture)
        build_snapshot_boot_disk([case], snapshot_raw, snapshot_qcow)
        run_save_qemu_case(
            snapshot_qcow,
            dos_dir,
            capture,
            boot_wait,
            path_prompt_wait,
            path_keys,
            slot_wait,
            slot_keys,
            description_wait,
            save_description,
            submit_description,
            confirmation_wait,
            confirmation_keys,
            key_delay,
            draw_wait,
        )

        convert_qcow_to_raw(snapshot_qcow, post_run_raw)
        extracted = extract_save(post_run_raw, dos_dir, save_stem, slot, save_output)
        parsed = load_save(extracted)
        save_file = str(extracted)
        parsed_description = parsed.description
        block_lengths = [block.length for block in parsed.blocks]
        visual_status, visual_mismatches = compare_validation_capture(capture)
        status = "match" if visual_status == "match" else "mismatch"
    except Exception as exc:  # noqa: BLE001 - probe records exact local failure.
        error = f"{type(exc).__name__}: {exc}"

    result = SaveRoundTripResult(
        status,
        dos_dir,
        str(capture),
        save_file,
        parsed_description,
        block_lengths,
        visual_status,
        visual_mismatches,
        round(time.monotonic() - started, 3),
        error,
    )
    write_report(result, report_output)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--dos-dir", default="SVRT")
    parser.add_argument("--path-keys", default="\n")
    parser.add_argument("--slot-keys", default="\n")
    parser.add_argument("--description", default="codex probe")
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--snapshot-raw", type=Path, default=DEFAULT_SNAPSHOT_RAW)
    parser.add_argument("--snapshot-qcow", type=Path, default=DEFAULT_SNAPSHOT_QCOW)
    parser.add_argument("--post-run-raw", type=Path, default=DEFAULT_POST_RUN_RAW)
    parser.add_argument("--save-output", type=Path, default=DEFAULT_SAVE_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--boot-wait", type=float, default=5.0)
    parser.add_argument("--draw-wait", type=float, default=8.0)
    parser.add_argument("--path-prompt-wait", type=float, default=2.0)
    parser.add_argument("--slot-wait", type=float, default=1.0)
    parser.add_argument("--description-wait", type=float, default=1.0)
    parser.add_argument("--no-submit-description", action="store_true")
    parser.add_argument("--confirmation-wait", type=float, default=1.0)
    parser.add_argument("--confirmation-keys", default="\n")
    parser.add_argument("--key-delay", type=float, default=0.08)
    parser.add_argument("--save-stem", default="SG")
    parser.add_argument("--slot", type=int, default=1)
    parser.add_argument("--keep-existing-saves", action="store_true")
    args = parser.parse_args()

    result = run_probe(
        args.fixture,
        args.dos_dir,
        args.path_keys,
        args.slot_keys,
        args.description,
        args.capture,
        args.snapshot_raw,
        args.snapshot_qcow,
        args.post_run_raw,
        args.save_output,
        args.output,
        args.boot_wait,
        args.draw_wait,
        args.path_prompt_wait,
        args.slot_wait,
        args.description_wait,
        not args.no_submit_description,
        args.confirmation_wait,
        args.confirmation_keys,
        args.key_delay,
        args.save_stem,
        args.slot,
        args.keep_existing_saves,
    )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    if result.status != "match":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
