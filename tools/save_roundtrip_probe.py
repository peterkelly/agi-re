#!/usr/bin/env python3
"""Drive the original engine's save UI and parse the produced save file."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from agi_graphics import PictureRenderer, compose_frame_on_picture, render_view_frame
from agi_save import (
    SAVE_HEADER_LENGTH,
    SOURCE_BACKED_FIXED_BLOCK_LENGTHS,
    load_save,
    u16le_bytes,
)
from compare_picture_capture import downsample_qemu_picture_nibbles
from ppm_tools import non_background_bbox, read_ppm, unique_colors
from qemu_fixture import (
    copy_sq2_tree,
    if_then,
    load_show_picture_actions,
    logic_resource,
    patch_dir_entry,
    patch_logdir_entry_zero,
    self_loop,
    set_flag_action,
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
DEFAULT_SAVE_OUTPUT = Path("build/save-roundtrip/SQ2SG.1")
SAVE_ACTION = 0x7D
RESTORE_ACTION = 0x7E
SIGNATURE_MESSAGE = "SQ2"
SAVED_MARKER_X = 50
UNRESTORED_MARKER_X = 90
VALIDATION_VIEW_VAR = 0xE0
VALIDATION_GROUP_VAR = 0xE1
VALIDATION_FRAME_VAR = 0xE2
VALIDATION_X_VAR = 0xE3
VALIDATION_Y_VAR = 0xE4
VALIDATION_PRIORITY_VAR = 0xE5
VALIDATION_CONTROL_VAR = 0xE6
RESTORED_MARKER_FLAG = 0xC6


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


@dataclass(frozen=True)
class RestoreReadErrorResult:
    status: str
    dos_dir: str
    capture: str
    save_file: str
    description: str
    save_length: int
    first_block_declared_length: int
    first_block_payload_prefix_hex: str
    capture_sha256_rgb: str | None
    capture_unique_colors: int | None
    capture_non_background_bbox: list[int] | None
    elapsed_seconds: float
    error: str | None


def byte_action(opcode: int, *operands: int) -> bytes:
    values = [opcode, *operands]
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("logic action bytes must fit in one byte")
    return bytes(values)


def validation_var_setup(marker_x: int) -> bytes:
    return (
        byte_action(0x03, VALIDATION_VIEW_VAR, 11)
        + byte_action(0x03, VALIDATION_GROUP_VAR, 0)
        + byte_action(0x03, VALIDATION_FRAME_VAR, 0)
        + byte_action(0x03, VALIDATION_X_VAR, marker_x)
        + byte_action(0x03, VALIDATION_Y_VAR, 80)
        + byte_action(0x03, VALIDATION_PRIORITY_VAR, 15)
        + byte_action(0x03, VALIDATION_CONTROL_VAR, 15)
    )


def validation_draw_from_vars() -> bytes:
    return byte_action(
        0x7B,
        VALIDATION_VIEW_VAR,
        VALIDATION_GROUP_VAR,
        VALIDATION_FRAME_VAR,
        VALIDATION_X_VAR,
        VALIDATION_Y_VAR,
        VALIDATION_PRIORITY_VAR,
        VALIDATION_CONTROL_VAR,
    )


def flag_set_condition(flag_no: int) -> bytes:
    if not 0 <= flag_no <= 0xFF:
        raise ValueError("flag number must fit in one byte")
    return bytes([0x07, flag_no])


def restore_success_branch() -> bytes:
    return (
        load_show_picture_actions(0)
        + byte_action(0x1E, 11)
        + byte_action(0x1A)
        + validation_draw_from_vars()
        + self_loop()
    )


def save_fixture_logic_payload() -> bytes:
    code = (
        load_show_picture_actions(0)
        + byte_action(0x1E, 11)
        + byte_action(0x8F, 1)
        + set_flag_action(RESTORED_MARKER_FLAG)
        + validation_var_setup(SAVED_MARKER_X)
        + byte_action(SAVE_ACTION)
        + byte_action(0x1A)
        + validation_draw_from_vars()
        + self_loop()
    )
    return logic_resource(code, messages=[SIGNATURE_MESSAGE])


def restore_fixture_logic_payload() -> bytes:
    code = (
        if_then(flag_set_condition(RESTORED_MARKER_FLAG), restore_success_branch())
        + load_show_picture_actions(0)
        + byte_action(0x1E, 11)
        + byte_action(0x8F, 1)
        + validation_var_setup(UNRESTORED_MARKER_X)
        + byte_action(RESTORE_ACTION)
        + byte_action(0x1A)
        + validation_draw_from_vars()
        + self_loop()
    )
    return logic_resource(code, messages=[SIGNATURE_MESSAGE])


def remove_existing_save_files(fixture: Path) -> None:
    for pattern in ("SQ2SG.*", "SG.*"):
        for path in fixture.glob(pattern):
            if path.is_file():
                path.unlink()


def save_description_header(description: str) -> bytes:
    raw = description.encode("ascii", errors="replace").split(b"\0", 1)[0][:30]
    return (raw + b"\0").ljust(SAVE_HEADER_LENGTH, b"\0")


def truncated_restore_save_payload(description: str = "codex broken restore") -> bytes:
    signature_prefix = SIGNATURE_MESSAGE.encode("ascii")[:7].ljust(7, b"\0")
    return (
        save_description_header(description)
        + u16le_bytes(SOURCE_BACKED_FIXED_BLOCK_LENGTHS[0])
        + signature_prefix
    )


def build_state_fixture(
    destination: Path,
    action_opcode: int,
    *,
    remove_saves: bool = True,
    save_input: Path | None = None,
    save_bytes: bytes | None = None,
    save_stem: str = "SQ2SG",
    slot: int = 1,
) -> Path:
    if save_input is not None and save_bytes is not None:
        raise ValueError("provide either save_input or save_bytes, not both")
    copy_sq2_tree(destination)
    if remove_saves:
        remove_existing_save_files(destination)
    if save_input is not None:
        shutil.copy2(save_input, destination / f"{save_stem}.{slot}")
    if save_bytes is not None:
        (destination / f"{save_stem}.{slot}").write_bytes(save_bytes)

    payload = save_fixture_logic_payload() if action_opcode == SAVE_ACTION else restore_fixture_logic_payload()
    logic_record = volume_record(payload, volume=3)
    picture_offset = len(logic_record)
    picture_record = volume_record(b"\xff", volume=3)
    (destination / "VOL.3").write_bytes(logic_record + picture_record)

    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))

    picdir = (destination / "PICDIR").read_bytes()
    (destination / "PICDIR").write_bytes(patch_dir_entry(picdir, 0, volume=3, offset=picture_offset))
    return destination


def build_save_fixture(destination: Path, *, remove_saves: bool = True) -> Path:
    return build_state_fixture(destination, SAVE_ACTION, remove_saves=remove_saves)


def build_restore_fixture(
    destination: Path,
    save_input: Path,
    *,
    remove_saves: bool = True,
    save_stem: str = "SQ2SG",
    slot: int = 1,
) -> Path:
    return build_state_fixture(
        destination,
        RESTORE_ACTION,
        remove_saves=remove_saves,
        save_input=save_input,
        save_stem=save_stem,
        slot=slot,
    )


def build_restore_read_error_fixture(
    destination: Path,
    *,
    description: str = "codex broken restore",
    remove_saves: bool = True,
    save_stem: str = "SQ2SG",
    slot: int = 1,
) -> Path:
    return build_state_fixture(
        destination,
        RESTORE_ACTION,
        remove_saves=remove_saves,
        save_bytes=truncated_restore_save_payload(description),
        save_stem=save_stem,
        slot=slot,
    )


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


def run_restore_qemu_case(
    disk_image: Path,
    dos_dir: str,
    capture: Path,
    boot_wait: float,
    path_prompt_wait: float,
    path_keys: str,
    slot_wait: float,
    slot_keys: str,
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
        if confirmation_keys:
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
    expected = compose_frame_on_picture(picture, frame, SAVED_MARKER_X, 80, 15).visual_nibbles
    mismatches = sum(1 for left, right in zip(captured, expected) if left != right)
    return ("match" if mismatches == 0 else "mismatch", mismatches)


def capture_summary(capture: Path) -> tuple[str, int, list[int] | None]:
    image = read_ppm(capture)
    bbox = non_background_bbox(image)
    return image.digest, len(unique_colors(image)), list(bbox) if bbox is not None else None


def write_report(result: SaveRoundTripResult | RestoreReadErrorResult, output: Path) -> dict[str, object]:
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


def run_restore_read_error_probe(
    fixture: Path,
    dos_dir: str,
    path_keys: str,
    slot_keys: str,
    description: str,
    capture: Path,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    report_output: Path,
    boot_wait: float,
    draw_wait: float,
    path_prompt_wait: float,
    slot_wait: float,
    confirmation_wait: float,
    confirmation_keys: str,
    key_delay: float,
    save_stem: str,
    slot: int,
) -> RestoreReadErrorResult:
    started = time.monotonic()
    error: str | None = None
    capture_sha256_rgb: str | None = None
    capture_unique_colors: int | None = None
    capture_non_background_bbox: list[int] | None = None
    status = "error"

    save_bytes = truncated_restore_save_payload(description)
    save_file = fixture / f"{save_stem}.{slot}"

    try:
        build_restore_read_error_fixture(
            fixture,
            description=description,
            remove_saves=True,
            save_stem=save_stem,
            slot=slot,
        )
        case = SnapshotFixtureCase(dos_dir, fixture, capture)
        build_snapshot_boot_disk([case], snapshot_raw, snapshot_qcow)
        run_restore_qemu_case(
            snapshot_qcow,
            dos_dir,
            capture,
            boot_wait,
            path_prompt_wait,
            path_keys,
            slot_wait,
            slot_keys,
            confirmation_wait,
            confirmation_keys,
            key_delay,
            draw_wait,
        )
        capture_sha256_rgb, capture_unique_colors, capture_non_background_bbox = capture_summary(
            capture
        )
        status = "captured"
    except Exception as exc:  # noqa: BLE001 - probe records exact local failure.
        error = f"{type(exc).__name__}: {exc}"

    result = RestoreReadErrorResult(
        status,
        dos_dir,
        str(capture),
        str(save_file),
        description,
        len(save_bytes),
        SOURCE_BACKED_FIXED_BLOCK_LENGTHS[0],
        save_bytes[SAVE_HEADER_LENGTH + 2 :].hex(),
        capture_sha256_rgb,
        capture_unique_colors,
        capture_non_background_bbox,
        round(time.monotonic() - started, 3),
        error,
    )
    write_report(result, report_output)
    return result


def run_restore_probe(
    fixture: Path,
    dos_dir: str,
    path_keys: str,
    slot_keys: str,
    save_input: Path,
    capture: Path,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    report_output: Path,
    boot_wait: float,
    draw_wait: float,
    path_prompt_wait: float,
    slot_wait: float,
    confirmation_wait: float,
    confirmation_keys: str,
    key_delay: float,
    save_stem: str,
    slot: int,
) -> SaveRoundTripResult:
    started = time.monotonic()
    error: str | None = None
    parsed_description: str | None = None
    block_lengths: list[int] | None = None
    visual_status: str | None = None
    visual_mismatches: int | None = None
    status = "error"

    try:
        parsed = load_save(save_input)
        parsed_description = parsed.description
        block_lengths = [block.length for block in parsed.blocks]
        build_restore_fixture(
            fixture,
            save_input,
            remove_saves=True,
            save_stem=save_stem,
            slot=slot,
        )
        case = SnapshotFixtureCase(dos_dir, fixture, capture)
        build_snapshot_boot_disk([case], snapshot_raw, snapshot_qcow)
        run_restore_qemu_case(
            snapshot_qcow,
            dos_dir,
            capture,
            boot_wait,
            path_prompt_wait,
            path_keys,
            slot_wait,
            slot_keys,
            confirmation_wait,
            confirmation_keys,
            key_delay,
            draw_wait,
        )
        visual_status, visual_mismatches = compare_validation_capture(capture)
        status = "match" if visual_status == "match" else "mismatch"
    except Exception as exc:  # noqa: BLE001 - probe records exact local failure.
        error = f"{type(exc).__name__}: {exc}"

    result = SaveRoundTripResult(
        status,
        dos_dir,
        str(capture),
        str(save_input),
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
    parser.add_argument("--mode", choices=["save", "restore", "restore-read-error"], default="save")
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
    parser.add_argument("--save-input", type=Path)
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
    parser.add_argument("--save-stem", default="SQ2SG")
    parser.add_argument("--slot", type=int, default=1)
    parser.add_argument("--keep-existing-saves", action="store_true")
    args = parser.parse_args()

    if args.mode == "save":
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
    elif args.mode == "restore":
        if args.save_input is None:
            parser.error("--mode restore requires --save-input")
        result = run_restore_probe(
            args.fixture,
            args.dos_dir,
            args.path_keys,
            args.slot_keys,
            args.save_input,
            args.capture,
            args.snapshot_raw,
            args.snapshot_qcow,
            args.output,
            args.boot_wait,
            args.draw_wait,
            args.path_prompt_wait,
            args.slot_wait,
            args.confirmation_wait,
            args.confirmation_keys,
            args.key_delay,
            args.save_stem,
            args.slot,
        )
    else:
        result = run_restore_read_error_probe(
            args.fixture,
            args.dos_dir,
            args.path_keys,
            args.slot_keys,
            args.description,
            args.capture,
            args.snapshot_raw,
            args.snapshot_qcow,
            args.output,
            args.boot_wait,
            args.draw_wait,
            args.path_prompt_wait,
            args.slot_wait,
            args.confirmation_wait,
            args.confirmation_keys,
            args.key_delay,
            args.save_stem,
            args.slot,
        )
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    if result.status in {"error", "mismatch"}:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
