#!/usr/bin/env python3
"""Compare logic dispatch tables and handler-entry shapes across local builds."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

from agi_resources import detect_layout
from compare_gr_sq2_static import (
    TableEntry,
    first_difference,
    load_table,
    markdown_table,
    mz_image,
    normalized_snippet,
)


@dataclass(frozen=True)
class InterpreterBuild:
    label: str
    game_dir: Path
    executable: Path
    layout: str
    action_base: int
    condition_base: int
    actions: tuple[TableEntry, ...]
    conditions: tuple[TableEntry, ...]
    image: bytes


@dataclass(frozen=True)
class EntryComparison:
    opcode: int
    left: TableEntry
    right: TableEntry
    same_contract: bool
    same_normalized_snippet: bool
    first_diff_index: int | None
    left_first_diff: str
    right_first_diff: str


def load_build(label: str, game_dir: Path, executable: Path) -> InterpreterBuild:
    game_dir = game_dir.resolve()
    executable = executable.resolve()
    previous_game_dir = os.environ.get("AGI_GAME_DIR")
    os.environ["AGI_GAME_DIR"] = str(game_dir)
    try:
        from disassemble_logic import dispatch_table_layout_for
    finally:
        if previous_game_dir is None:
            os.environ.pop("AGI_GAME_DIR", None)
        else:
            os.environ["AGI_GAME_DIR"] = previous_game_dir

    layout = detect_layout(game_dir).version
    agidata = (game_dir / "AGIDATA.OVL").read_bytes()
    action_base, action_count, condition_base, condition_count = dispatch_table_layout_for(
        agidata,
        layout,
    )
    return InterpreterBuild(
        label=label,
        game_dir=game_dir,
        executable=executable,
        layout=layout,
        action_base=action_base,
        condition_base=condition_base,
        actions=tuple(load_table(agidata, action_base, action_count)),
        conditions=tuple(load_table(agidata, condition_base, condition_count)),
        image=mz_image(executable.read_bytes()),
    )


def compare_entries(
    left_entries: tuple[TableEntry, ...],
    right_entries: tuple[TableEntry, ...],
    left_image: bytes,
    right_image: bytes,
) -> tuple[EntryComparison, ...]:
    comparisons: list[EntryComparison] = []
    for opcode, (left, right) in enumerate(zip(left_entries, right_entries)):
        left_norm = normalized_snippet(left_image, left.handler)
        right_norm = normalized_snippet(right_image, right.handler)
        index, left_diff, right_diff = first_difference(left_norm, right_norm)
        comparisons.append(
            EntryComparison(
                opcode=opcode,
                left=left,
                right=right,
                same_contract=(left.argc, left.meta) == (right.argc, right.meta),
                same_normalized_snippet=index is None,
                first_diff_index=index,
                left_first_diff=left_diff,
                right_first_diff=right_diff,
            )
        )
    return tuple(comparisons)


def entry_name(kind: str, opcode: int) -> str:
    from disassemble_logic import ACTION_NAMES, COND_NAMES, action_name

    if kind == "action":
        return action_name(opcode, 0xB6)
    return COND_NAMES.get(opcode, f"condition_{opcode:02x}")


def comparison_rows(
    kind: str,
    comparisons: tuple[EntryComparison, ...],
    left_label: str,
    right_label: str,
) -> list[list[str]]:
    return [
        [
            f"`0x{item.opcode:02x}`",
            f"`{entry_name(kind, item.opcode)}`",
            f"`0x{item.left.handler:04x}`",
            f"`0x{item.right.handler:04x}`",
            "same" if item.same_contract else "different",
            "same"
            if item.same_normalized_snippet
            else (
                f"`{item.first_diff_index}`: {left_label} `{item.left_first_diff}` / "
                f"{right_label} `{item.right_first_diff}`"
            ),
        ]
        for item in comparisons
        if not item.same_contract or not item.same_normalized_snippet
    ]


def parse_role_pair(text: str) -> tuple[str, int, int]:
    try:
        label, addresses = text.split("=", 1)
        left_text, right_text = addresses.split(",", 1)
        return label, int(left_text, 0), int(right_text, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "role pair must be LABEL=LEFT_ADDRESS,RIGHT_ADDRESS"
        ) from exc


def emit_report(
    left: InterpreterBuild,
    right: InterpreterBuild,
    role_pairs: tuple[tuple[str, int, int], ...] = (),
) -> str:
    actions = compare_entries(left.actions, right.actions, left.image, right.image)
    conditions = compare_entries(left.conditions, right.conditions, left.image, right.image)
    action_contract_diffs = [item for item in actions if not item.same_contract]
    action_snippet_diffs = [item for item in actions if not item.same_normalized_snippet]
    condition_contract_diffs = [item for item in conditions if not item.same_contract]
    condition_snippet_diffs = [item for item in conditions if not item.same_normalized_snippet]

    lines = [
        f"# {left.label} / {right.label} Interpreter Table Comparison",
        "",
        "This is a triage report. Matching parser contracts are structural evidence. A",
        "normalized handler-entry difference is only a prompt for manual disassembly; it",
        "does not by itself establish an observable behavior difference.",
        "",
        "## Inputs",
        "",
        f"- {left.label}: `{left.game_dir}` / `{left.executable}` / `{left.layout}`",
        f"- {right.label}: `{right.game_dir}` / `{right.executable}` / `{right.layout}`",
        f"- Action table bases: `{left.action_base:#06x}` / `{right.action_base:#06x}`",
        f"- Condition table bases: `{left.condition_base:#06x}` / `{right.condition_base:#06x}`",
        "",
        "## Summary",
        "",
        f"- Shared actions: `{len(actions)}`.",
        f"- Action parser-contract differences: `{len(action_contract_diffs)}`.",
        f"- Action normalized entry-snippet differences: `{len(action_snippet_diffs)}`.",
        f"- Shared conditions: `{len(conditions)}`.",
        f"- Condition parser-contract differences: `{len(condition_contract_diffs)}`.",
        f"- Condition normalized entry-snippet differences: `{len(condition_snippet_diffs)}`.",
        "",
        "## Action Triage",
        "",
    ]
    action_rows = comparison_rows("action", actions, left.label, right.label)
    if action_rows:
        lines.extend(
            markdown_table(
                ["Opcode", "Name", left.label, right.label, "Contract", "First normalized difference"],
                action_rows,
            )
        )
    else:
        lines.append("No shared action differences were found.")

    lines.extend(["", "## Condition Triage", ""])
    condition_rows = comparison_rows("condition", conditions, left.label, right.label)
    if condition_rows:
        lines.extend(
            markdown_table(
                ["Opcode", "Name", left.label, right.label, "Contract", "First normalized difference"],
                condition_rows,
            )
        )
    else:
        lines.append("No shared condition differences were found.")

    if len(left.actions) != len(right.actions):
        longer = left if len(left.actions) > len(right.actions) else right
        start = min(len(left.actions), len(right.actions))
        lines.extend(["", "## Unshared Action Entries", ""])
        lines.extend(
            markdown_table(
                ["Build", "Opcode", "Handler", "Argc", "Meta"],
                [
                    [
                        longer.label,
                        f"`0x{opcode:02x}`",
                        f"`0x{entry.handler:04x}`",
                        str(entry.argc),
                        f"`0x{entry.meta:02x}`",
                    ]
                    for opcode, entry in enumerate(longer.actions[start:], start=start)
                ],
            )
        )
    if role_pairs:
        lines.extend(["", "## Role-Pair Triage", ""])
        role_rows: list[list[str]] = []
        for label, left_address, right_address in role_pairs:
            left_norm = normalized_snippet(left.image, left_address)
            right_norm = normalized_snippet(right.image, right_address)
            index, left_diff, right_diff = first_difference(left_norm, right_norm)
            role_rows.append(
                [
                    f"`{label}`",
                    f"`0x{left_address:04x}`",
                    f"`0x{right_address:04x}`",
                    "same"
                    if index is None
                    else (
                        f"`{index}`: {left.label} `{left_diff}` / "
                        f"{right.label} `{right_diff}`"
                    ),
                ]
            )
        lines.extend(
            markdown_table(
                ["Role", left.label, right.label, "Normalized result"],
                role_rows,
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--left-label", required=True)
    parser.add_argument("--left-game-dir", required=True, type=Path)
    parser.add_argument("--left-exe", required=True, type=Path)
    parser.add_argument("--right-label", required=True)
    parser.add_argument("--right-game-dir", required=True, type=Path)
    parser.add_argument("--right-exe", required=True, type=Path)
    parser.add_argument("--role-pair", action="append", default=[], type=parse_role_pair)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = emit_report(
        load_build(args.left_label, args.left_game_dir, args.left_exe),
        load_build(args.right_label, args.right_game_dir, args.right_exe),
        tuple(args.role_pair),
    )
    if args.output is None:
        print(report)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
