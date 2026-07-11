#!/usr/bin/env python3
"""Index game-visible logic transitions for clean-room playthrough analysis."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from agi_save import SQ2_OBJECT_FILE_XOR_KEY, decode_object_metadata_file, split_inventory_block
from disassemble_logic import (
    COND_NAMES,
    SQ2,
    action_name,
    action_operand_count,
    decode_logic_resource_messages,
    dispatch_table_layout,
    load_table,
    logic_directory_entries,
    logic_payload,
    s16le,
    u16le,
)
from inspect_words import decode_entries


@dataclass(frozen=True)
class ConditionRecord:
    ip: int
    opcode: int
    name: str
    inverted: bool
    args: tuple[int, ...]
    word_ids: tuple[int, ...]
    word_synonyms: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class IfRecord:
    ip: int
    then_start: int
    false_target: int
    conditions: tuple[ConditionRecord, ...]


@dataclass(frozen=True)
class ActionRecord:
    ip: int
    opcode: int
    name: str
    args: tuple[int, ...]


def word_synonyms() -> dict[int, tuple[str, ...]]:
    grouped: dict[int, list[str]] = {}
    for entry in decode_entries((SQ2 / "WORDS.TOK").read_bytes()):
        grouped.setdefault(entry.word_id, []).append(entry.word)
    return {word_id: tuple(words) for word_id, words in grouped.items()}


def parse_conditions(
    code: bytes,
    ip: int,
    condition_table,
    synonyms: dict[int, tuple[str, ...]],
) -> tuple[tuple[ConditionRecord, ...], int, int]:
    records: list[ConditionRecord] = []
    inverted = False
    while ip < len(code):
        at = ip
        opcode = code[ip]
        ip += 1
        if opcode == 0xFC:
            continue
        if opcode == 0xFD:
            inverted = not inverted
            continue
        if opcode == 0xFF:
            false_target = ip + 2 + s16le(code, ip)
            return tuple(records), ip + 2, false_target
        if opcode == 0x0E:
            count = code[ip]
            ip += 1
            word_ids = tuple(u16le(code, ip + index * 2) for index in range(count))
            ip += count * 2
            records.append(
                ConditionRecord(
                    at,
                    opcode,
                    COND_NAMES[opcode],
                    inverted,
                    (count,),
                    word_ids,
                    tuple(synonyms.get(word_id, ()) for word_id in word_ids),
                )
            )
        else:
            entry = condition_table[opcode]
            args = tuple(code[ip : ip + entry.argc])
            ip += entry.argc
            records.append(
                ConditionRecord(
                    at,
                    opcode,
                    COND_NAMES.get(opcode, f"cond_{opcode:02x}"),
                    inverted,
                    args,
                    (),
                    (),
                )
            )
        inverted = False
    raise ValueError("unterminated logic condition list")


def parse_logic(logic_number: int, action_table, condition_table, synonyms):
    payload = logic_payload(logic_number)
    code = payload[2 : 2 + u16le(payload, 0)]
    actions: list[ActionRecord] = []
    ifs: list[IfRecord] = []
    jumps: list[dict[str, int]] = []
    ip = 0
    while ip < len(code):
        at = ip
        opcode = code[ip]
        ip += 1
        if opcode == 0xFE:
            target = ip + 2 + s16le(code, ip)
            jumps.append({"ip": at, "target": target})
            ip += 2
            continue
        if opcode == 0xFF:
            conditions, then_start, false_target = parse_conditions(
                code, ip, condition_table, synonyms
            )
            ifs.append(IfRecord(at, then_start, false_target, conditions))
            ip = then_start
            continue
        if opcode in (0xFC, 0xFD):
            raise ValueError(f"structural opcode {opcode:#x} outside condition at {at:#x}")
        entry = action_table[opcode]
        argc = action_operand_count(opcode, entry)
        args = tuple(code[ip : ip + argc])
        ip += argc
        actions.append(ActionRecord(at, opcode, action_name(opcode, len(action_table)), args))
    return payload, tuple(actions), tuple(ifs), tuple(jumps)


def conditions_for(ip: int, ifs: tuple[IfRecord, ...]) -> list[dict]:
    enclosing = [record for record in ifs if record.then_start <= ip < record.false_target]
    return [asdict(record) for record in sorted(enclosing, key=lambda record: record.ip)]


def score_delta(action: ActionRecord) -> int | None:
    if action.opcode == 0x01 and action.args == (3,):
        return 1
    if action.opcode == 0x02 and action.args == (3,):
        return -1
    if action.opcode == 0x05 and action.args[0] == 3:
        return action.args[1]
    if action.opcode == 0x07 and action.args[0] == 3:
        return -action.args[1]
    return None


def referenced_messages(action: ActionRecord) -> tuple[int, ...]:
    if action.opcode in (0x65, 0x67, 0x72, 0x8F, 0x90, 0x97):
        return action.args[:1]
    return ()


def inventory_state() -> list[dict]:
    metadata = decode_object_metadata_file(
        (SQ2 / "OBJECT").read_bytes(), key=SQ2_OBJECT_FILE_XOR_KEY
    )
    state = split_inventory_block(metadata.runtime_block, item_table_size=metadata.item_table_size)
    return [
        {"number": item.index, "name": item.name, "initial_location": item.location}
        for item in state.items
    ]


def build_index() -> dict:
    action_base, action_count, condition_base, condition_count = dispatch_table_layout()
    agidata = (SQ2 / "AGIDATA.OVL").read_bytes()
    action_table = load_table(agidata, action_base, action_count)
    condition_table = load_table(agidata, condition_base, condition_count)
    synonyms = word_synonyms()
    logics: list[dict] = []
    unreadable_logics: list[dict] = []
    maximum_score_assignments: list[dict] = []

    for logic_number, entry in enumerate(logic_directory_entries()):
        if entry is None:
            continue
        try:
            payload, actions, ifs, jumps = parse_logic(
                logic_number, action_table, condition_table, synonyms
            )
        except (ValueError, OSError) as error:
            unreadable_logics.append(
                {
                    "logic": logic_number,
                    "volume": entry.volume,
                    "offset": entry.offset,
                    "error": str(error),
                }
            )
            continue
        messages = decode_logic_resource_messages(logic_number, payload)
        maximum_score_assignments.extend(
            {
                "logic": logic_number,
                "ip": action.ip,
                "value": action.args[1],
            }
            for action in actions
            if action.opcode == 0x03 and action.args[0] == 7
        )
        score_events = []
        for action in actions:
            delta = score_delta(action)
            if delta is None:
                continue
            following = [candidate for candidate in actions if action.ip < candidate.ip <= action.ip + 16]
            message_numbers = [
                number
                for candidate in following
                for number in referenced_messages(candidate)
                if 0 < number < len(messages)
            ]
            score_events.append(
                {
                    "ip": action.ip,
                    "delta": delta,
                    "conditions": conditions_for(action.ip, ifs),
                    "following_actions": [asdict(candidate) for candidate in following],
                    "following_messages": [
                        {"number": number, "text": messages[number]}
                        for number in message_numbers
                    ],
                }
            )

        logics.append(
            {
                "logic": logic_number,
                "messages": [
                    {"number": number, "text": text}
                    for number, text in enumerate(messages[1:], start=1)
                ],
                "parser_conditions": [
                    asdict(condition)
                    for record in ifs
                    for condition in record.conditions
                    if condition.opcode == 0x0E
                ],
                "score_events": score_events,
                "room_transitions": [
                    {
                        **asdict(action),
                        "conditions": conditions_for(action.ip, ifs),
                    }
                    for action in actions
                    if action.opcode in (0x12, 0x13)
                ],
                "inventory_actions": [
                    {
                        **asdict(action),
                        "conditions": conditions_for(action.ip, ifs),
                    }
                    for action in actions
                    if 0x5C <= action.opcode <= 0x61
                ],
                "jumps": jumps,
            }
        )

    return {
        "game_dir": str(SQ2),
        "maximum_score_assignments": maximum_score_assignments,
        "unreadable_logics": unreadable_logics,
        "inventory": inventory_state(),
        "logics": logics,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rendered = json.dumps(build_index(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
