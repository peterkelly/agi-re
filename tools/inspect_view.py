#!/usr/bin/env python3
"""Inspect local SQ2 view-like resource payloads.

This is a clean-room helper derived from the interpreter code paths around
0x3ae7, 0x3c1b, and 0x3d6a. It intentionally reports structural fields without
assigning final user-level names.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from disassemble_logic import SQ2, read_dir_entries, read_volume_payload, u16le


@dataclass(frozen=True)
class FrameSummary:
    index: int
    offset: int
    width: int
    height: int
    control: int
    row_end_count: int
    data_end: int


@dataclass(frozen=True)
class GroupSummary:
    index: int
    offset: int
    frame_count: int
    frames: list[FrameSummary]


def scan_frame(payload: bytes, frame_offset: int) -> FrameSummary:
    if frame_offset + 3 > len(payload):
        raise ValueError(f"frame offset {frame_offset:#x} outside payload")
    width = payload[frame_offset]
    height = payload[frame_offset + 1]
    control = payload[frame_offset + 2]
    pos = frame_offset + 3
    row_end_count = 0
    while pos < len(payload) and row_end_count < height:
        value = payload[pos]
        pos += 1
        if value == 0:
            row_end_count += 1
    return FrameSummary(
        index=-1,
        offset=frame_offset,
        width=width,
        height=height,
        control=control,
        row_end_count=row_end_count,
        data_end=pos,
    )


def parse_view(payload: bytes, max_groups: int, max_frames: int) -> list[GroupSummary]:
    if len(payload) < 5:
        raise ValueError("payload too short for observed view-like header")

    group_count = payload[2]
    groups: list[GroupSummary] = []
    for group_index in range(min(group_count, max_groups)):
        group_table_entry = 5 + group_index * 2
        group_offset = u16le(payload, group_table_entry)
        if group_offset >= len(payload):
            raise ValueError(
                f"group {group_index} offset {group_offset:#x} outside payload"
            )
        group = payload[group_offset:]
        frame_count = group[0]
        frames: list[FrameSummary] = []
        for frame_index in range(min(frame_count, max_frames)):
            frame_table_entry = group_offset + 1 + frame_index * 2
            frame_offset = group_offset + u16le(payload, frame_table_entry)
            frame = scan_frame(payload, frame_offset)
            frames.append(
                FrameSummary(
                    index=frame_index,
                    offset=frame.offset,
                    width=frame.width,
                    height=frame.height,
                    control=frame.control,
                    row_end_count=frame.row_end_count,
                    data_end=frame.data_end,
                )
            )
        groups.append(GroupSummary(group_index, group_offset, frame_count, frames))
    return groups


def describe_view(view_no: int, max_groups: int, max_frames: int) -> str:
    entries = read_dir_entries(SQ2 / "VIEWDIR")
    entry = entries[view_no]
    if entry is None:
        raise ValueError(f"view {view_no} is absent")
    payload = read_volume_payload(*entry)
    preview_text_offset = u16le(payload, 3) if len(payload) >= 5 else None
    if preview_text_offset is None:
        preview_text = "??"
    elif preview_text_offset < len(payload):
        preview_text = f"{preview_text_offset:#04x}"
    else:
        preview_text = f"{preview_text_offset:#04x} outside"
    lines = [
        f"view {view_no}: bytes={len(payload)} header="
        f"{payload[:5].hex(' ')} groups={payload[2] if len(payload) > 2 else '??'} "
        f"preview_text_off={preview_text}"
    ]
    for group in parse_view(payload, max_groups, max_frames):
        lines.append(
            f"  group {group.index}: off={group.offset:#04x} "
            f"frames={group.frame_count}"
        )
        for frame in group.frames:
            lines.append(
                f"    frame {frame.index}: off={frame.offset:#04x} "
                f"size={frame.width}x{frame.height} control={frame.control:#04x} "
                f"row_ends={frame.row_end_count} data_end={frame.data_end:#04x}"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("views", nargs="*", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--groups", type=int, default=4)
    parser.add_argument("--frames", type=int, default=4)
    args = parser.parse_args()

    view_numbers = args.views
    if args.limit is not None:
        entries = read_dir_entries(SQ2 / "VIEWDIR")
        view_numbers = [
            idx for idx in range(min(args.limit, len(entries))) if entries[idx] is not None
        ]
    if not view_numbers:
        view_numbers = [0]

    for idx, view_no in enumerate(view_numbers):
        if idx:
            print()
        print(describe_view(view_no, args.groups, args.frames))


if __name__ == "__main__":
    main()
