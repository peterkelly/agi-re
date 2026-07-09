#!/usr/bin/env python3
"""Static clean-room comparison of local SQ2 and Gold Rush interpreters.

This helper intentionally uses only local executables, local AGIDATA.OVL files,
and ndisasm output. It is a triage tool: "same" means the normalized handler
entry snippet matches, while "different" means the disassembly should be read
and documented before any behavioral conclusion is made.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SQ2_ACTION_BASE = 0x061D
SQ2_ACTION_COUNT = 0xB0
SQ2_COND_BASE = 0x08FD
SQ2_COND_COUNT = 0x13

GR_ACTION_BASE = 0x0440
GR_ACTION_COUNT = 0xB6
GR_COND_BASE = 0x0762
GR_STRUCTURED_COND_COUNT = 0x13
GR_DISPATCH_COND_BOUND = 0x26


@dataclass(frozen=True)
class TableEntry:
    handler: int
    argc: int
    meta: int


@dataclass(frozen=True)
class SnippetComparison:
    opcode: int
    name: str
    sq2_handler: int
    gr_handler: int
    same_contract: bool
    same_normalized_snippet: bool
    first_diff_index: int | None
    sq2_first_diff: str
    gr_first_diff: str


@dataclass(frozen=True)
class SubsystemPair:
    group: str
    label: str
    sq2_handler: int
    gr_handler: int
    note: str = ""


SUBSYSTEM_PAIRS: tuple[SubsystemPair, ...] = (
    SubsystemPair("resources", "code.resource.load_all_directories", 0x4305, 0x44DE, "v3 combined-directory path expected to differ"),
    SubsystemPair("resources", "code.resource.read_volume_payload_once", 0x2E56, 0x30D0, "v3 7-byte header/decompression path expected to differ"),
    SubsystemPair("view", "code.view.load_resource", 0x39F7, 0x3C5B),
    SubsystemPair("view", "code.object.bind_view", 0x3AE7, 0x3D4B),
    SubsystemPair("view", "code.object.select_group", 0x3BB7, 0x3E1B),
    SubsystemPair("view", "code.object.select_group_table", 0x3C1B, 0x3E7F),
    SubsystemPair("view", "code.object.select_frame", 0x3CCB, 0x3F2F),
    SubsystemPair("view", "code.view.discard", 0x3ECD, 0x4131),
    SubsystemPair("picture", "code.picture.load_resource", 0x4A3B, 0x4C96),
    SubsystemPair("picture", "code.picture.prepare", 0x4ACF, 0x4D2A),
    SubsystemPair("picture", "code.picture.overlay_prepare", 0x4B3B, 0x4D96),
    SubsystemPair("picture", "code.picture.discard", 0x4BCE, 0x4E29),
    SubsystemPair("picture", "code.picture.decode_no_clear", 0x6440, 0x67C2),
    SubsystemPair("picture", "code.picture.command_scan", 0x6475, 0x67ED),
    SubsystemPair("picture", "code.picture.cmd_set_visual_draw_nibble", 0x6494, 0x680C),
    SubsystemPair("picture", "code.picture.cmd_disable_visual_draw_nibble", 0x64B5, 0x682D),
    SubsystemPair("picture", "code.picture.cmd_set_control_draw_nibble", 0x64C7, 0x683F),
    SubsystemPair("picture", "code.picture.cmd_disable_control_draw_nibble", 0x64ED, 0x6865),
    SubsystemPair("picture", "code.picture.cmd_draw_corner_path_y_first", 0x6612, 0x698A),
    SubsystemPair("picture", "code.picture.cmd_draw_corner_path_x_first", 0x6603, 0x697B),
    SubsystemPair("picture", "code.picture.cmd_draw_absolute_lines", 0x6646, 0x69BE),
    SubsystemPair("picture", "code.picture.cmd_draw_relative_lines", 0x665E, 0x69D6),
    SubsystemPair("picture", "code.picture.cmd_seed_fill", 0x66AB, 0x6A23),
    SubsystemPair("picture", "code.picture.cmd_set_pattern_mode", 0x6524, 0x689C),
    SubsystemPair("picture", "code.picture.cmd_pattern_plot", 0x64FF, 0x6877),
    SubsystemPair("picture", "code.picture.read_coord_pair", 0x66B8, 0x6A30),
    SubsystemPair("picture", "code.picture.draw_line", 0x66E1, 0x6A59),
    SubsystemPair("picture", "code.display.fill_buffer_word", 0x5257, 0x548A, "GR omits SQ2's display-mode-2 overlay refresh call after the memory fill"),
    SubsystemPair("picture", "code.display.draw_horizontal_line", 0x526F, 0x5498),
    SubsystemPair("picture", "code.display.draw_vertical_line", 0x52AB, 0x54D4),
    SubsystemPair("picture", "code.display.pixel_write", 0x52F9, 0x5522),
    SubsystemPair("picture", "code.picture.seed_fill", 0x533B, 0x5564),
    SubsystemPair("picture", "code.display.clear_logical_buffer", 0x5528, 0x5751),
    SubsystemPair("picture", "code.display.full_refresh", 0x5546, 0x576F, "GR omits SQ2's display-mode-2 overlay refresh branch in this path"),
    SubsystemPair("object", "code.object.build_update_list_sorted", 0x0358, 0x0351),
    SubsystemPair("object", "code.object.insert_update_node_head", 0x042F, 0x0428),
    SubsystemPair("object", "code.object.draw_update_list_tail_to_head", 0x045E, 0x0457, "GR calls main-image rectangle save/draw routines where SQ2 calls overlay entries"),
    SubsystemPair("object", "code.object.refresh_update_list_saved_pos", 0x0488, 0x0481),
    SubsystemPair("object", "code.object.frame_timer_update", 0x0563, 0x055C, "GR adds an extra helper-gated branch before using the four-plus-group direction table"),
    SubsystemPair("object", "code.object.advance_frame_by_mode", 0x48B3, 0x4B0E, "first normalized difference is embedded jump-table bytes; manually inspected branch bodies match as relocated skeletons"),
    SubsystemPair("object", "code.object.collision_test", 0x4719, 0x4974),
    SubsystemPair("object", "code.object.control_acceptance", 0x56B8, 0x58E5),
    SubsystemPair("object", "code.object.update_dirty_rect", 0x5762, 0x598F),
    SubsystemPair("object", "code.object.place", 0x593A, 0x5CB3),
    SubsystemPair("object", "code.object.build_active_update_list", 0x6A26, 0x6D9E),
    SubsystemPair("object", "code.object.build_inactive_partition_list", 0x6A3D, 0x6DB5),
    SubsystemPair("object", "code.object.flush_update_lists_restore", 0x6A54, 0x6DCC),
    SubsystemPair("object", "code.object.rebuild_draw_update_lists", 0x6A8E, 0x6E06),
    SubsystemPair("object", "code.object.refresh_update_lists", 0x6AAB, 0x6E23),
    SubsystemPair("object", "code.object.clear_root_16ff_membership", 0x6B44, 0x6EBC),
    SubsystemPair("object", "code.object.set_root_16ff_membership", 0x6B62, 0x6EDA),
    SubsystemPair("object", "code.motion.update_objects", 0x150A, 0x1720),
    SubsystemPair("object", "code.motion.pre_mode_and_boundary_update", 0x0644, 0x0654),
    SubsystemPair("object", "code.motion.dispatch_mode_step", 0x067A, 0x068A, "GR accepts one additional object mode selector before falling through to the same boundary-check tail"),
    SubsystemPair("object", "code.motion.rectangle_boundary_check", 0x06D9, 0x06EB, "first normalized difference is embedded direction jump-table bytes; manually inspected post-table body matches as a relocated skeleton"),
)


CHANGED_ACTION_NOTES: dict[int, str] = {
    0x12: "GR runs the immediate target through helper 0x0062, which remaps bytes 0x7e..0x80 to 0x49 before entering the relocated room-switch helper; SQ2 passes the immediate byte directly.",
    0x6F: "GR computes the input/display offset as arg0<<3 unconditionally; SQ2 has a display-mode-2 branch that uses 6-pixel spacing and clamps operands above one.",
    0x73: "GR removes SQ2's display-mode-2/input-width branch and always uses the normal prompt/editor path with a 0x28 character formatting cap.",
    0x76: "GR removes SQ2's alternate display-mode-2/input-width number-prompt path and always enters the normal prompt/editor path.",
    0x77: "GR always erases/clears the configured input line when disabling input; SQ2 skips that visible clear in display mode 2.",
    0x78: "GR always redraws the configured input line when enabling input; SQ2 skips redraw in display mode 2.",
    0x79: "Key-map table capacity changes from 0x27 four-byte slots in SQ2 to 0x31 four-byte slots in GR.",
    0x7C: "GR sets a temporary inventory/input word during the carried-item selector and clears it on return; the surrounding list UI skeleton is relocated from SQ2.",
    0x7D: "GR XOR-transforms the object/inventory chunk with helper 0x07bc before and after saving; block layout otherwise follows the relocated SQ2 five-block save envelope with v3 addresses.",
    0x80: "GR records prompt-marker visibility before confirmation; after cancel it redraws only if the marker had been visible, while accepted restart still redraws before returning zero.",
    0x84: "GR preserves object0 field +0x22 when it is already 4; SQ2 clears it unconditionally.",
    0x89: "GR refreshes through the normal source-to-visible input path without SQ2's display-mode-2/input-width special branch.",
    0x8A: "GR erases visible input directly without SQ2's display-mode-2/input-width skip branch.",
    0xA3: "GR maps this SQ2 input-width setter to the generic no-op/return handler.",
    0xA4: "GR maps this SQ2 input-width clearer to the generic no-op/return handler.",
    0xA9: "GR close-text-window state restores and clears the active rectangle flag only; SQ2 also clears the input-width flag that GR no-ops through 0xa3/0xa4.",
    0xAD: "SQ2 increments byte [0x1530]; GR sets byte [0x0405] to 1. GR keyboard IRQ code later tests [0x0405] before enqueueing a type-2 zero event on selected key-release paths.",
}


GR_ONLY_ACTION_NOTES: dict[int, str] = {
    0xB0: "generic no-op/return handler with no operands",
    0xB1: "stores its one operand into word [0x0403]; GR code.menu.interact at image 0x9724 returns immediately while that word is zero",
    0xB2: "generic no-op/return handler with no operands",
    0xB3: "generic no-op/return handler after four consumed operands",
    0xB4: "generic no-op/return handler after two operands, both marked variable by metadata 0xc0",
    0xB5: "sets byte [0x0405] to 0; shared GR action 0xad sets the same byte to 1, and the keyboard IRQ hook tests it before key-release event enqueue",
}


def u16le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def load_table(data: bytes, base: int, count: int) -> list[TableEntry]:
    entries: list[TableEntry] = []
    for index in range(count):
        offset = base + index * 4
        entries.append(TableEntry(u16le(data, offset), data[offset + 2], data[offset + 3]))
    return entries


def mz_image(data: bytes) -> bytes:
    if len(data) >= 0x20 and data[:2] == b"MZ":
        header_size = u16le(data, 0x08) * 16
        return data[header_size:]
    return data


def disassemble_snippet(image: bytes, address: int, max_bytes: int = 512, max_lines: int = 80) -> list[str]:
    chunk = image[address : address + max_bytes]
    result = subprocess.run(
        ["ndisasm", "-b", "16", "-o", f"0x{address:x}", "-"],
        input=chunk,
        check=True,
        stdout=subprocess.PIPE,
    )
    lines: list[str] = []
    for raw_line in result.stdout.decode("utf-8").splitlines():
        match = re.match(r"^[0-9A-F]{8}\s+[0-9A-F]+\s+(.*)$", raw_line)
        if not match:
            continue
        instruction = match.group(1).strip().lower()
        lines.append(instruction)
        if instruction.startswith("ret"):
            break
        if len(lines) >= max_lines:
            break
    return lines


def normalize_instruction(instruction: str) -> str:
    instruction = instruction.lower()
    instruction = re.sub(r"\b(call|jmp|j[a-z]+) 0x[0-9a-f]+", r"\1 target", instruction)
    instruction = re.sub(r"\[(0x[0-9a-f]+)\]", "[abs]", instruction)

    def replace_hex(match: re.Match[str]) -> str:
        value = int(match.group(0), 16)
        if value >= 0x300:
            return "imm16"
        return hex(value)

    instruction = re.sub(r"0x[0-9a-f]+", replace_hex, instruction)
    return re.sub(r"\s+", " ", instruction)


def normalized_snippet(image: bytes, address: int) -> list[str]:
    return [normalize_instruction(line) for line in disassemble_snippet(image, address)]


def first_difference(left: list[str], right: list[str]) -> tuple[int | None, str, str]:
    for index, (left_line, right_line) in enumerate(zip(left, right)):
        if left_line != right_line:
            return index, left_line, right_line
    if len(left) != len(right):
        index = min(len(left), len(right))
        return (
            index,
            left[index] if index < len(left) else "<end>",
            right[index] if index < len(right) else "<end>",
        )
    return None, "", ""


def compare_table(
    kind: str,
    names: dict[int, str],
    sq2_table: list[TableEntry],
    gr_table: list[TableEntry],
    sq2_image: bytes,
    gr_image: bytes,
    count: int,
) -> list[SnippetComparison]:
    comparisons: list[SnippetComparison] = []
    for opcode in range(count):
        sq2_entry = sq2_table[opcode]
        gr_entry = gr_table[opcode]
        sq2_norm = normalized_snippet(sq2_image, sq2_entry.handler)
        gr_norm = normalized_snippet(gr_image, gr_entry.handler)
        first_index, sq2_diff, gr_diff = first_difference(sq2_norm, gr_norm)
        comparisons.append(
            SnippetComparison(
                opcode=opcode,
                name=names.get(opcode, f"{kind}_{opcode:02x}"),
                sq2_handler=sq2_entry.handler,
                gr_handler=gr_entry.handler,
                same_contract=(sq2_entry.argc, sq2_entry.meta) == (gr_entry.argc, gr_entry.meta),
                same_normalized_snippet=first_index is None,
                first_diff_index=first_index,
                sq2_first_diff=sq2_diff,
                gr_first_diff=gr_diff,
            )
        )
    return comparisons


def compare_subsystem_pair(pair: SubsystemPair, sq2_image: bytes, gr_image: bytes) -> SnippetComparison:
    sq2_norm = normalized_snippet(sq2_image, pair.sq2_handler)
    gr_norm = normalized_snippet(gr_image, pair.gr_handler)
    first_index, sq2_diff, gr_diff = first_difference(sq2_norm, gr_norm)
    return SnippetComparison(
        opcode=0,
        name=pair.label,
        sq2_handler=pair.sq2_handler,
        gr_handler=pair.gr_handler,
        same_contract=True,
        same_normalized_snippet=first_index is None,
        first_diff_index=first_index,
        sq2_first_diff=sq2_diff,
        gr_first_diff=gr_diff,
    )


def markdown_table(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> list[str]:
    header_list = list(headers)
    lines = ["| " + " | ".join(header_list) + " |", "| " + " | ".join("---" for _ in header_list) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def emit_report(args: argparse.Namespace) -> str:
    os.environ["AGI_GAME_DIR"] = str(args.sq2_game_dir)
    from disassemble_logic import ACTION_NAMES, COND_NAMES  # noqa: WPS433

    sq2_game_dir = Path(args.sq2_game_dir)
    gr_game_dir = Path(args.gr_game_dir)
    sq2_agidata = (sq2_game_dir / "AGIDATA.OVL").read_bytes()
    gr_agidata = (gr_game_dir / "AGIDATA.OVL").read_bytes()
    sq2_image = mz_image(Path(args.sq2_exe).read_bytes())
    gr_image = mz_image(Path(args.gr_exe).read_bytes())

    sq2_actions = load_table(sq2_agidata, SQ2_ACTION_BASE, SQ2_ACTION_COUNT)
    gr_actions = load_table(gr_agidata, GR_ACTION_BASE, GR_ACTION_COUNT)
    sq2_conditions = load_table(sq2_agidata, SQ2_COND_BASE, SQ2_COND_COUNT)
    gr_structured_conditions = load_table(gr_agidata, GR_COND_BASE, GR_STRUCTURED_COND_COUNT)
    gr_dispatch_bound_conditions = load_table(gr_agidata, GR_COND_BASE, GR_DISPATCH_COND_BOUND)

    action_comparisons = compare_table(
        "action",
        ACTION_NAMES,
        sq2_actions,
        gr_actions,
        sq2_image,
        gr_image,
        SQ2_ACTION_COUNT,
    )
    condition_comparisons = compare_table(
        "cond",
        COND_NAMES,
        sq2_conditions,
        gr_structured_conditions,
        sq2_image,
        gr_image,
        SQ2_COND_COUNT,
    )
    subsystem_comparisons = [(pair, compare_subsystem_pair(pair, sq2_image, gr_image)) for pair in SUBSYSTEM_PAIRS]

    changed_actions = [item for item in action_comparisons if not item.same_normalized_snippet]
    changed_conditions = [item for item in condition_comparisons if not item.same_normalized_snippet]
    action_contract_diffs = [item for item in action_comparisons if not item.same_contract]
    condition_contract_diffs = [item for item in condition_comparisons if not item.same_contract]

    lines: list[str] = [
        "# GR / SQ2 Static Comparison Report",
        "",
        "Inputs:",
        "",
        f"- SQ2 game dir: `{sq2_game_dir}`",
        f"- SQ2 executable image: `{Path(args.sq2_exe)}`",
        f"- GR game dir: `{gr_game_dir}`",
        f"- GR executable image: `{Path(args.gr_exe)}`",
        "",
        "## Logic Opcode Tables",
        "",
        f"- Shared action opcodes compared: `{SQ2_ACTION_COUNT}` (`0x00..0xaf`).",
        f"- Shared action parser-contract differences: `{len(action_contract_diffs)}`.",
        f"- Shared action normalized handler-snippet differences: `{len(changed_actions)}`.",
        f"- Shared condition opcodes compared as structured entries: `{SQ2_COND_COUNT}` (`0x00..0x12`).",
        f"- Shared condition parser-contract differences: `{len(condition_contract_diffs)}`.",
        f"- Shared condition normalized handler-snippet differences: `{len(changed_conditions)}`.",
        "",
        "### Changed Shared Action Snippets",
        "",
    ]
    lines.extend(
        markdown_table(
            ["Opcode", "Name", "SQ2 handler", "GR handler", "First normalized difference"],
            (
                [
                    f"`0x{item.opcode:02x}`",
                    f"`{item.name}`",
                    f"`0x{item.sq2_handler:04x}`",
                    f"`0x{item.gr_handler:04x}`",
                    f"`{item.first_diff_index}`: SQ2 `{item.sq2_first_diff}` / GR `{item.gr_first_diff}`"
                    + (f"; {CHANGED_ACTION_NOTES[item.opcode]}" if item.opcode in CHANGED_ACTION_NOTES else ""),
                ]
                for item in changed_actions
            ),
        )
    )
    lines.extend(["", "### Changed Shared Condition Snippets", ""])
    if changed_conditions:
        lines.extend(
            markdown_table(
                ["Opcode", "Name", "SQ2 handler", "GR handler", "First normalized difference"],
                (
                    [
                        f"`0x{item.opcode:02x}`",
                        f"`{item.name}`",
                        f"`0x{item.sq2_handler:04x}`",
                        f"`0x{item.gr_handler:04x}`",
                        f"`{item.first_diff_index}`: SQ2 `{item.sq2_first_diff}` / GR `{item.gr_first_diff}`",
                    ]
                    for item in changed_conditions
                ),
            )
        )
    else:
        lines.append("No normalized differences in structured shared condition handlers.")

    lines.extend(["", "### GR-Only Action Slots", ""])
    lines.extend(
        markdown_table(
            ["Opcode", "GR handler", "Argc", "Meta", "Normalized entry snippet", "Static note"],
            (
                [
                    f"`0x{opcode:02x}`",
                    f"`0x{entry.handler:04x}`",
                    f"`{entry.argc}`",
                    f"`0x{entry.meta:02x}`",
                    "`" + " ; ".join(normalized_snippet(gr_image, entry.handler)[:4]) + "`",
                    GR_ONLY_ACTION_NOTES.get(opcode, ""),
                ]
                for opcode, entry in enumerate(gr_actions[SQ2_ACTION_COUNT:], start=SQ2_ACTION_COUNT)
            ),
        )
    )

    lines.extend(
        [
            "",
            "### GR Condition Bytes Past Shared Table",
            "",
            "The GR condition dispatcher compares the predicate byte with `0x26`, but the bytes after",
            "the first `0x13` four-byte entries overlap local string/data bytes. They are listed here",
            "as raw table-shaped bytes, not as confirmed predicate implementations.",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["Opcode", "Raw handler", "Raw argc", "Raw meta"],
            (
                [f"`0x{opcode:02x}`", f"`0x{entry.handler:04x}`", f"`{entry.argc}`", f"`0x{entry.meta:02x}`"]
                for opcode, entry in enumerate(
                    gr_dispatch_bound_conditions[GR_STRUCTURED_COND_COUNT:],
                    start=GR_STRUCTURED_COND_COUNT,
                )
            ),
        )
    )
    lines.extend(["", "## Object / View / Picture Subsystem Slices", ""])
    lines.extend(
        markdown_table(
            ["Group", "Label", "SQ2", "GR", "Status", "First normalized difference / note"],
            (
                [
                    pair.group,
                    f"`{pair.label}`",
                    f"`0x{comparison.sq2_handler:04x}`",
                    f"`0x{comparison.gr_handler:04x}`",
                    "`same`" if comparison.same_normalized_snippet else "`different`",
                    (
                        pair.note
                        if comparison.same_normalized_snippet
                        else f"`{comparison.first_diff_index}`: SQ2 `{comparison.sq2_first_diff}` / GR `{comparison.gr_first_diff}`"
                        + (f"; {pair.note}" if pair.note else "")
                    ),
                ]
                for pair, comparison in subsystem_comparisons
            ),
        )
    )
    lines.extend(
        [
            "",
            "Object-overlay packaging note: this report compares main executable image slices only.",
            "SQ2's rectangle save/restore/draw entries are in `IBM_OBJS.OVL` at near offsets",
            "`0x9db0`, `0x9db3`, and `0x9db6`; GR does not have a separate `IBM_OBJS.OVL`",
            "in the selected local input and calls analogous routines in the main executable image.",
            "",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sq2-game-dir", required=True, type=Path)
    parser.add_argument("--gr-game-dir", required=True, type=Path)
    parser.add_argument("--sq2-exe", required=True, type=Path)
    parser.add_argument("--gr-exe", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = emit_report(args)
    if args.output is None:
        print(report)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n")


if __name__ == "__main__":
    main()
