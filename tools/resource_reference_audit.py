#!/usr/bin/env python3
"""Audit script-visible resource references for explicit local game dirs."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agi_resources import (
    KIND_ORDER,
    detect_layout,
    iter_present_entries,
    read_directory_entries,
    read_resource_payload,
    read_volume_record,
)


ACTION_META_SIGNATURE = (
    (0, 0x00),
    (1, 0x80),
    (1, 0x80),
    (2, 0x80),
    (2, 0xC0),
    (2, 0x80),
    (2, 0xC0),
    (2, 0x80),
    (2, 0xC0),
    (2, 0xC0),
    (2, 0xC0),
    (2, 0x80),
    (1, 0x00),
    (1, 0x00),
    (1, 0x00),
    (1, 0x80),
)

CONDITION_META_SIGNATURE = (
    (0, 0x00),
    (2, 0x80),
    (2, 0xC0),
    (2, 0x80),
    (2, 0xC0),
    (2, 0x80),
    (2, 0xC0),
    (1, 0x00),
    (1, 0x80),
    (1, 0x00),
    (2, 0x40),
    (5, 0x00),
    (1, 0x00),
    (0, 0x00),
    (0, 0x00),
    (2, 0x00),
    (5, 0x00),
    (5, 0x00),
    (5, 0x00),
)

IMMEDIATE_RESOURCE_OPERANDS = {
    "logic": {
        0x14: (0,),  # load_logic
        0x16: (0,),  # call_logic
    },
    "view": {
        0x1E: (0,),  # load_view
        0x20: (0,),  # discard_view
        0x29: (1,),  # set_object_resource
        0x2B: (1,),  # set_object_subresource
        0x7A: (2,),  # setup_transient_object
        0x81: (0,),  # display_view_resource_text_like
    },
    "sound": {
        0x62: (0,),  # load_sound
        0x63: (0,),  # start_sound_with_flag
    },
}


@dataclass(frozen=True)
class TableEntry:
    argc: int
    meta: int


def u16le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def find_table_by_meta_signature(data: bytes, signature: tuple[tuple[int, int], ...], name: str) -> int:
    span = len(signature) * 4
    matches: list[int] = []
    for base in range(0, len(data) - span + 1):
        if all(
            (data[base + opcode * 4 + 2], data[base + opcode * 4 + 3]) == expected
            for opcode, expected in enumerate(signature)
        ):
            matches.append(base)
    if len(matches) != 1:
        rendered = ", ".join(f"0x{match:04x}" for match in matches)
        raise ValueError(f"expected one {name} table signature match, found {len(matches)}: {rendered}")
    return matches[0]


def load_table(data: bytes, base: int, count: int) -> list[TableEntry]:
    return [TableEntry(data[base + opcode * 4 + 2], data[base + opcode * 4 + 3]) for opcode in range(count)]


def dispatch_tables(game_dir: Path) -> tuple[list[TableEntry], list[TableEntry]]:
    layout = detect_layout(game_dir)
    agidata = (game_dir / "AGIDATA.OVL").read_bytes()
    action_base = find_table_by_meta_signature(agidata, ACTION_META_SIGNATURE, "action")
    cond_base = find_table_by_meta_signature(agidata, CONDITION_META_SIGNATURE, "condition")
    action_count = 0xB6 if layout.version == "v3_combined" else 0xB0
    return (
        load_table(agidata, action_base, action_count),
        load_table(agidata, cond_base, 0x13),
    )


def _is_variable_operand(meta: int, index: int) -> bool:
    return bool(meta & (0x80 >> index))


def collect_immediate_references(game_dir: Path) -> dict[str, list[int]]:
    action_table, cond_table = dispatch_tables(game_dir)
    references: dict[str, set[int]] = {kind: set() for kind in KIND_ORDER}
    logic_entries = read_directory_entries(game_dir, "logic")

    for logic_no, entry in enumerate(logic_entries):
        if entry is None:
            continue
        payload = read_resource_payload(game_dir, "logic", logic_no)
        code = payload[2 : 2 + u16le(payload, 0)]
        ip = 0
        while ip < len(code):
            opcode = code[ip]
            ip += 1
            if opcode == 0x00:
                continue
            if opcode == 0xFE:
                ip += 2
                continue
            if opcode == 0xFF:
                while ip < len(code):
                    cond = code[ip]
                    ip += 1
                    if cond == 0xFF:
                        ip += 2
                        break
                    if cond in (0xFC, 0xFD):
                        continue
                    if cond == 0x0E:
                        count = code[ip]
                        ip += 1 + count * 2
                    elif cond < len(cond_table):
                        ip += cond_table[cond].argc
                continue
            if opcode >= len(action_table):
                continue
            entry = action_table[opcode]
            args = list(code[ip : ip + entry.argc])
            ip += entry.argc
            for kind, opcodes in IMMEDIATE_RESOURCE_OPERANDS.items():
                for arg_index in opcodes.get(opcode, ()):
                    if arg_index < len(args) and not _is_variable_operand(entry.meta, arg_index):
                        references[kind].add(args[arg_index])

    return {kind: sorted(values) for kind, values in references.items()}


def resource_readability(game_dir: Path, kind: str) -> dict[str, Any]:
    readable: list[int] = []
    unreadable: list[dict[str, Any]] = []
    for number, _entry in iter_present_entries(game_dir, kind):
        try:
            read_volume_record(game_dir, kind, number)
        except Exception as exc:
            unreadable.append(
                {
                    "number": number,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        else:
            readable.append(number)
    return {
        "readable": readable,
        "unreadable": unreadable,
    }


def audit_game(game_dir: Path) -> dict[str, Any]:
    game_dir = Path(game_dir)
    references = collect_immediate_references(game_dir)
    resources = {kind: resource_readability(game_dir, kind) for kind in KIND_ORDER}
    result: dict[str, Any] = {
        "name": game_dir.name,
        "path": str(game_dir),
        "references": references,
        "resources": resources,
    }
    for kind in KIND_ORDER:
        unreadable_numbers = {entry["number"] for entry in resources[kind]["unreadable"]}
        referenced = set(references[kind])
        result.setdefault("referenced_unreadable", {})[kind] = sorted(referenced & unreadable_numbers)
        result.setdefault("unreferenced_unreadable", {})[kind] = sorted(unreadable_numbers - referenced)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = {
        "games": [audit_game(path) for path in args.game_dir],
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="ascii")


if __name__ == "__main__":
    main()
