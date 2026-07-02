#!/usr/bin/env python3
"""Generate clean-room QEMU fixture game directories."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from disassemble_logic import SQ2


SCRATCH_VAR = 250


def u16le(value: int) -> bytes:
    return bytes([value & 0xFF, (value >> 8) & 0xFF])


def picture_logic_payload(picture_no: int, scratch_var: int = SCRATCH_VAR) -> bytes:
    if not 0 <= picture_no <= 0xFF:
        raise ValueError("picture number must fit in one byte")
    if not 0 <= scratch_var <= 0xFF:
        raise ValueError("scratch variable must fit in one byte")
    code = bytes(
        [
            0x03,
            scratch_var,
            picture_no,
            0x18,
            scratch_var,
            0x19,
            scratch_var,
            0x1A,
            0xFE,
            0xFD,
            0xFF,
        ]
    )
    return u16le(len(code)) + code + bytes([0x00]) + u16le(0x0002)


def picture_view_logic_payload(
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority: int,
    control: int | None = None,
    scratch_var: int = SCRATCH_VAR,
    pre_overlay_actions: bytes = b"",
) -> bytes:
    values = [picture_no, view_no, group_no, frame_no, x, baseline_y, priority, scratch_var]
    if control is not None:
        values.append(control)
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("fixture operands must fit in one byte")
    if control is None:
        control = priority
    code = bytes(
        [
            0x03,
            scratch_var,
            picture_no,
            0x18,
            scratch_var,
            0x19,
            scratch_var,
            0x1A,
        ]
    )
    code += pre_overlay_actions
    code += bytes(
        [
            0x1E,
            view_no,
            0x7A,
            view_no,
            group_no,
            frame_no,
            x,
            baseline_y,
            priority,
            control,
            0xFE,
            0xFD,
            0xFF,
        ]
    )
    return u16le(len(code)) + code + bytes([0x00]) + u16le(0x0002)


def persistent_object_logic_payload(
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority_byte: int | None,
    object_no: int = 0,
    scratch_var: int = SCRATCH_VAR,
    pre_overlay_actions: bytes = b"",
) -> bytes:
    values = [picture_no, view_no, group_no, frame_no, x, baseline_y, object_no, scratch_var]
    if priority_byte is not None:
        values.append(priority_byte)
    if any(not 0 <= value <= 0xFF for value in values):
        raise ValueError("fixture operands must fit in one byte")
    code = bytes(
        [
            0x03,
            scratch_var,
            picture_no,
            0x18,
            scratch_var,
            0x19,
            scratch_var,
            0x1A,
        ]
    )
    code += pre_overlay_actions
    code += bytes(
        [
            0x1E,
            view_no,
            0x21,
            object_no,
            0x29,
            object_no,
            view_no,
            0x2B,
            object_no,
            group_no,
            0x2F,
            object_no,
            frame_no,
            0x25,
            object_no,
            x,
            baseline_y,
        ]
    )
    if priority_byte is not None:
        code += bytes([0x36, object_no, priority_byte])
    code += bytes([0x23, object_no, 0xFE, 0xFD, 0xFF])
    return u16le(len(code)) + code + bytes([0x00]) + u16le(0x0002)


def rebuild_priority_table_action(row: int) -> bytes:
    if not 0 <= row <= 0xFF:
        raise ValueError("priority-table row must fit in one byte")
    return bytes([0xAE, row])


def volume_record(payload: bytes, volume: int) -> bytes:
    if not 0 <= volume <= 0x0F:
        raise ValueError("volume number must fit in one nibble")
    return b"\x12\x34" + bytes([volume]) + u16le(len(payload)) + payload


def patch_logdir_entry_zero(logdir: bytes, volume: int, offset: int) -> bytes:
    return patch_dir_entry(logdir, 0, volume, offset)


def patch_dir_entry(directory: bytes, resource_no: int, volume: int, offset: int) -> bytes:
    if not 0 <= volume <= 0x0F:
        raise ValueError("volume number must fit in one nibble")
    if not 0 <= offset <= 0x0FFFFF:
        raise ValueError("resource offset must fit in 20 bits")
    entry_offset = resource_no * 3
    if entry_offset + 3 > len(directory):
        raise ValueError("resource number is outside directory")
    patched = bytearray(directory)
    patched[entry_offset] = (volume << 4) | ((offset >> 16) & 0x0F)
    patched[entry_offset + 1] = (offset >> 8) & 0xFF
    patched[entry_offset + 2] = offset & 0xFF
    return bytes(patched)


def copy_sq2_tree(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for source in SQ2.iterdir():
        if source.is_file():
            shutil.copy2(source, destination / source.name)


def build_picture_fixture(picture_no: int, destination: Path) -> Path:
    copy_sq2_tree(destination)
    logic_payload = picture_logic_payload(picture_no)
    (destination / "VOL.3").write_bytes(volume_record(logic_payload, volume=3))
    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))
    return destination


def build_picture_view_fixture(
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority: int,
    destination: Path,
    control: int | None = None,
) -> Path:
    copy_sq2_tree(destination)
    logic_payload = picture_view_logic_payload(
        picture_no,
        view_no,
        group_no,
        frame_no,
        x,
        baseline_y,
        priority,
        control,
    )
    (destination / "VOL.3").write_bytes(volume_record(logic_payload, volume=3))
    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))
    return destination


def build_synthetic_picture_fixture(
    picture_payload: bytes,
    destination: Path,
    picture_no: int = 0,
) -> Path:
    copy_sq2_tree(destination)
    logic_payload = picture_logic_payload(picture_no)
    logic_record = volume_record(logic_payload, volume=3)
    picture_offset = len(logic_record)
    picture_record = volume_record(picture_payload, volume=3)
    (destination / "VOL.3").write_bytes(logic_record + picture_record)

    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))

    picdir = (destination / "PICDIR").read_bytes()
    (destination / "PICDIR").write_bytes(
        patch_dir_entry(picdir, picture_no, volume=3, offset=picture_offset)
    )
    return destination


def build_synthetic_picture_view_fixture(
    picture_payload: bytes,
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority: int,
    destination: Path,
    control: int | None = None,
    pre_overlay_actions: bytes = b"",
) -> Path:
    copy_sq2_tree(destination)
    logic_payload = picture_view_logic_payload(
        picture_no,
        view_no,
        group_no,
        frame_no,
        x,
        baseline_y,
        priority,
        control,
        pre_overlay_actions=pre_overlay_actions,
    )
    logic_record = volume_record(logic_payload, volume=3)
    picture_offset = len(logic_record)
    picture_record = volume_record(picture_payload, volume=3)
    (destination / "VOL.3").write_bytes(logic_record + picture_record)

    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))

    picdir = (destination / "PICDIR").read_bytes()
    (destination / "PICDIR").write_bytes(
        patch_dir_entry(picdir, picture_no, volume=3, offset=picture_offset)
    )
    return destination


def build_synthetic_picture_persistent_object_fixture(
    picture_payload: bytes,
    picture_no: int,
    view_no: int,
    group_no: int,
    frame_no: int,
    x: int,
    baseline_y: int,
    priority_byte: int | None,
    destination: Path,
    object_no: int = 0,
    pre_overlay_actions: bytes = b"",
) -> Path:
    copy_sq2_tree(destination)
    logic_payload = persistent_object_logic_payload(
        picture_no,
        view_no,
        group_no,
        frame_no,
        x,
        baseline_y,
        priority_byte,
        object_no,
        pre_overlay_actions=pre_overlay_actions,
    )
    logic_record = volume_record(logic_payload, volume=3)
    picture_offset = len(logic_record)
    picture_record = volume_record(picture_payload, volume=3)
    (destination / "VOL.3").write_bytes(logic_record + picture_record)

    logdir = (destination / "LOGDIR").read_bytes()
    (destination / "LOGDIR").write_bytes(patch_logdir_entry_zero(logdir, volume=3, offset=0))

    picdir = (destination / "PICDIR").read_bytes()
    (destination / "PICDIR").write_bytes(
        patch_dir_entry(picdir, picture_no, volume=3, offset=picture_offset)
    )
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    picture = subparsers.add_parser("picture")
    picture.add_argument("picture", type=int)
    picture.add_argument("--output", type=Path)

    picture_view = subparsers.add_parser("picture-view")
    picture_view.add_argument("picture", type=int)
    picture_view.add_argument("view", type=int)
    picture_view.add_argument("group", type=int)
    picture_view.add_argument("frame", type=int)
    picture_view.add_argument("x", type=int)
    picture_view.add_argument("baseline_y", type=int)
    picture_view.add_argument("priority", type=int)
    picture_view.add_argument("--control", type=int)
    picture_view.add_argument("--output", type=Path)

    synthetic_picture = subparsers.add_parser("synthetic-picture")
    synthetic_picture.add_argument("payload", type=Path)
    synthetic_picture.add_argument("--picture", type=int, default=0)
    synthetic_picture.add_argument("--output", type=Path)

    synthetic_picture_view = subparsers.add_parser("synthetic-picture-view")
    synthetic_picture_view.add_argument("payload", type=Path)
    synthetic_picture_view.add_argument("picture", type=int)
    synthetic_picture_view.add_argument("view", type=int)
    synthetic_picture_view.add_argument("group", type=int)
    synthetic_picture_view.add_argument("frame", type=int)
    synthetic_picture_view.add_argument("x", type=int)
    synthetic_picture_view.add_argument("baseline_y", type=int)
    synthetic_picture_view.add_argument("priority", type=int)
    synthetic_picture_view.add_argument("--control", type=int)
    synthetic_picture_view.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.command == "picture":
        output = args.output or Path("build/qemu-fixtures") / f"picture_{args.picture:03d}"
        build_picture_fixture(args.picture, output)
        print(output)
    elif args.command == "picture-view":
        output = args.output or (
            Path("build/qemu-fixtures")
            / f"picture_{args.picture:03d}_view_{args.view:03d}_{args.group:02d}_{args.frame:02d}"
        )
        build_picture_view_fixture(
            args.picture,
            args.view,
            args.group,
            args.frame,
            args.x,
            args.baseline_y,
            args.priority,
            output,
            args.control,
        )
        print(output)
    elif args.command == "synthetic-picture":
        output = args.output or Path("build/qemu-fixtures") / f"synthetic_picture_{args.picture:03d}"
        build_synthetic_picture_fixture(args.payload.read_bytes(), output, args.picture)
        print(output)
    elif args.command == "synthetic-picture-view":
        output = args.output or (
            Path("build/qemu-fixtures")
            / f"synthetic_picture_{args.picture:03d}_view_{args.view:03d}_{args.group:02d}_{args.frame:02d}"
        )
        build_synthetic_picture_view_fixture(
            args.payload.read_bytes(),
            args.picture,
            args.view,
            args.group,
            args.frame,
            args.x,
            args.baseline_y,
            args.priority,
            output,
            args.control,
        )
        print(output)


if __name__ == "__main__":
    main()
