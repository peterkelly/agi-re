#!/usr/bin/env python3
"""Clean-room logic bytecode disassembler for the local SQ2 data set.

This script uses only formats and dispatch-table rules derived in this
repository. It intentionally keeps names conservative where handler semantics
are still unknown.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQ2 = ROOT / "SQ2"
AGIDATA = SQ2 / "AGIDATA.OVL"


@dataclass(frozen=True)
class TableEntry:
    handler: int
    argc: int
    meta: int


def u16le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def s16le(data: bytes, offset: int) -> int:
    value = u16le(data, offset)
    return value - 0x10000 if value & 0x8000 else value


def load_table(data: bytes, base: int, count: int) -> list[TableEntry]:
    out: list[TableEntry] = []
    for opcode in range(count):
        off = base + opcode * 4
        out.append(TableEntry(u16le(data, off), data[off + 2], data[off + 3]))
    return out


def read_dir_entries(path: Path) -> list[tuple[int, int] | None]:
    data = path.read_bytes()
    entries: list[tuple[int, int] | None] = []
    for off in range(0, len(data), 3):
        chunk = data[off : off + 3]
        if len(chunk) < 3:
            break
        volume = chunk[0] >> 4
        if volume == 0x0F:
            entries.append(None)
            continue
        res_off = ((chunk[0] & 0x0F) << 16) | (chunk[1] << 8) | chunk[2]
        entries.append((volume, res_off))
    return entries


def read_volume_payload(volume: int, offset: int) -> bytes:
    data = (SQ2 / f"VOL.{volume}").read_bytes()
    header = data[offset : offset + 5]
    if len(header) != 5 or header[0:2] != b"\x12\x34" or header[2] != volume:
        raise ValueError(f"bad VOL.{volume} resource header at {offset:#x}")
    length = u16le(header, 3)
    start = offset + 5
    return data[start : start + length]


def logic_payload(logic_no: int) -> bytes:
    entries = read_dir_entries(SQ2 / "LOGDIR")
    entry = entries[logic_no]
    if entry is None:
        raise ValueError(f"logic {logic_no} is absent")
    return read_volume_payload(*entry)


COND_NAMES = {
    0x00: "always_false",
    0x01: "var_eq_imm",
    0x02: "var_eq_var",
    0x03: "var_lt_imm",
    0x04: "var_lt_var",
    0x05: "var_gt_imm",
    0x06: "var_gt_var",
    0x07: "flag_set",
    0x08: "flag_set_var",
    0x09: "obj_table_room_ff",
    0x0A: "obj_table_room_eq_var",
    0x0B: "object_rect_test_0b",
    0x0C: "status_byte_1218",
    0x0D: "input_or_event_check",
    0x0E: "input_word_sequence",
    0x0F: "helper_0eac",
    0x10: "object_rect_test_10",
    0x11: "object_rect_test_11",
    0x12: "object_rect_test_12",
}


ACTION_NAMES = {
    0x01: "inc_var",
    0x02: "dec_var",
    0x03: "assignn",
    0x04: "assignv",
    0x05: "addn",
    0x06: "addv",
    0x07: "subn",
    0x08: "subv",
    0x09: "indirect_assignv",
    0x0A: "assign_indirectv",
    0x0B: "indirect_assignn",
    0x0C: "set_flag",
    0x0D: "clear_flag",
    0x0E: "toggle_flag",
    0x0F: "set_flag_var",
    0x10: "clear_flag_var",
    0x11: "toggle_flag_var",
    0x14: "load_logic",
    0x15: "load_logic_var",
    0x16: "call_logic",
    0x17: "call_logic_var",
    0x1E: "load_view",
    0x1F: "load_view_var",
    0x21: "reset_object_state",
    0x22: "clear_all_object_bits",
    0x23: "activate_object",
    0x24: "deactivate_object",
    0x25: "set_object_pos",
    0x26: "set_object_pos_var",
    0x27: "get_object_pos",
    0x29: "set_object_resource",
    0x2A: "set_object_resource_var",
    0x2B: "set_object_subresource",
    0x2C: "set_object_subresource_var",
    0x2F: "set_object_derived_resource_2",
    0x36: "set_object_field_24",
    0x37: "set_object_field_24_var",
    0x38: "clear_object_bit_0004",
    0x39: "get_object_field_24",
    0x3F: "set_global_012d",
    0x40: "set_object_bit_0100",
    0x43: "set_object_bit_0200",
    0x44: "clear_object_bit_0200",
    0x51: "object_motion_or_state",
    0x52: "object_motion_or_state_var",
    0x58: "set_object_bit_0002",
    0x59: "clear_object_bit_0002",
    0x62: "load_sound",
    0x64: "stop_sound_or_clear_sound_state",
    0x65: "display_message",
    0x66: "display_message_var",
    0x7A: "setup_transient_object",
    0x7B: "setup_transient_object_var",
    0x82: "random_range_to_var",
    0x93: "set_object_pos_dirty",
    0x97: "display_message_configured",
    0x98: "display_message_configured_var",
    0xA5: "muln",
    0xA6: "mulv",
    0xA7: "divn",
    0xA8: "divv",
}


def operand_text(args: list[int], meta: int) -> str:
    parts = []
    for idx, value in enumerate(args):
        bit = 0x80 >> idx
        prefix = "v" if meta & bit else "#"
        parts.append(f"{prefix}{value}")
    return ", ".join(parts)


def parse_varlen_condition(data: bytes, ip: int) -> tuple[list[int], int]:
    count = data[ip]
    ip += 1
    raw = list(data[ip : ip + count * 2])
    return [count, *raw], ip + count * 2


def parse_conditions(
    data: bytes, ip: int, cond_table: list[TableEntry]
) -> tuple[list[str], int, int]:
    lines: list[str] = []
    while ip < len(data):
        at = ip
        opcode = data[ip]
        ip += 1
        if opcode == 0xFC:
            lines.append(f"{at:04x}:   OR_MARK")
            continue
        if opcode == 0xFD:
            lines.append(f"{at:04x}:   NOT_NEXT")
            continue
        if opcode == 0xFF:
            if ip + 2 > len(data):
                lines.append(f"{at:04x}:   COND_END <missing false delta>")
                return lines, ip, ip
            delta = s16le(data, ip)
            target = ip + 2 + delta
            lines.append(f"{at:04x}:   COND_END false_delta={delta:+d} false_target={target:04x}")
            ip += 2
            return lines, ip, target
        if opcode == 0x0E:
            args, ip = parse_varlen_condition(data, ip)
            text = ", ".join(str(x) for x in args)
            lines.append(f"{at:04x}:   cond 0e {COND_NAMES.get(opcode)}({text})")
            continue
        if opcode >= len(cond_table):
            lines.append(f"{at:04x}:   cond {opcode:02x} <no table entry>")
            continue
        entry = cond_table[opcode]
        args = list(data[ip : ip + entry.argc])
        ip += entry.argc
        name = COND_NAMES.get(opcode, f"cond_{opcode:02x}")
        lines.append(f"{at:04x}:   cond {opcode:02x} {name}({operand_text(args, entry.meta)})")
    return lines, ip, ip


def disassemble_logic(logic_no: int, action_table: list[TableEntry], cond_table: list[TableEntry]) -> str:
    payload = logic_payload(logic_no)
    code_len = u16le(payload, 0)
    code = payload[2 : 2 + code_len]
    message_count = payload[2 + code_len] if 2 + code_len < len(payload) else 0

    lines = [
        f"logic {logic_no}",
        f"code_len={code_len} message_count={message_count}",
    ]

    ip = 0
    while ip < len(code):
        at = ip
        opcode = code[ip]
        ip += 1
        if opcode == 0x00:
            lines.append(f"{at:04x}: action 00 end")
            continue
        if opcode == 0xFE:
            if ip + 2 > len(code):
                lines.append(f"{at:04x}: jump <missing delta>")
                break
            delta = s16le(code, ip)
            target = ip + 2 + delta
            lines.append(f"{at:04x}: jump {delta:+d} -> {target:04x}")
            ip += 2
            continue
        if opcode == 0xFF:
            lines.append(f"{at:04x}: if")
            cond_lines, ip, false_target = parse_conditions(code, ip, cond_table)
            lines.extend(cond_lines)
            lines.append(f"{at:04x}: then_start={ip:04x} false_target={false_target:04x}")
            continue
        if opcode in (0xFC, 0xFD):
            lines.append(f"{at:04x}: structural {opcode:02x} outside condition")
            continue
        if opcode >= len(action_table):
            lines.append(f"{at:04x}: action {opcode:02x} <no table entry>")
            continue
        entry = action_table[opcode]
        args = list(code[ip : ip + entry.argc])
        ip += entry.argc
        name = ACTION_NAMES.get(opcode, f"action_{opcode:02x}")
        lines.append(
            f"{at:04x}: action {opcode:02x} {name}({operand_text(args, entry.meta)})"
            f" ; h={entry.handler:04x} meta={entry.meta:02x}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("logic", nargs="*", type=int, help="logic numbers to disassemble")
    parser.add_argument("--limit", type=int, default=None, help="disassemble present logic numbers below this limit")
    parser.add_argument("--stats", action="store_true", help="print linear opcode counts instead of disassembly")
    args = parser.parse_args()

    agidata = AGIDATA.read_bytes()
    action_table = load_table(agidata, 0x061D, 0xB0)
    cond_table = load_table(agidata, 0x08FD, 0x13)

    if args.stats:
        entries = read_dir_entries(SQ2 / "LOGDIR")
        action_counts: Counter[int] = Counter()
        cond_counts: Counter[int] = Counter()
        errors: list[tuple[int, int, str]] = []
        for logic_no, entry in enumerate(entries):
            if entry is None:
                continue
            try:
                payload = read_volume_payload(*entry)
            except ValueError as exc:
                errors.append((logic_no, 0, str(exc)))
                continue
            code = payload[2 : 2 + u16le(payload, 0)]
            ip = 0
            try:
                while ip < len(code):
                    opcode = code[ip]
                    ip += 1
                    if opcode == 0x00:
                        action_counts[opcode] += 1
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
                            cond_counts[cond] += 1
                            if cond == 0x0E:
                                count = code[ip]
                                ip += 1 + count * 2
                            elif cond < len(cond_table):
                                ip += cond_table[cond].argc
                        continue
                    action_counts[opcode] += 1
                    if opcode < len(action_table):
                        ip += action_table[opcode].argc
            except Exception as exc:  # pragma: no cover - diagnostic path
                errors.append((logic_no, ip, str(exc)))

        print("errors")
        for logic_no, ip, message in errors[:20]:
            print(f"logic={logic_no} ip={ip:04x} {message}")
        print("actions")
        for opcode, count in action_counts.most_common():
            if opcode < len(action_table):
                entry = action_table[opcode]
                name = ACTION_NAMES.get(opcode, f"action_{opcode:02x}")
                print(
                    f"{opcode:02x} {count:5d} h={entry.handler:04x} "
                    f"argc={entry.argc} meta={entry.meta:02x} {name}"
                )
        print("conditions")
        for opcode, count in cond_counts.most_common():
            if opcode < len(cond_table):
                entry = cond_table[opcode]
                name = COND_NAMES.get(opcode, f"cond_{opcode:02x}")
                print(
                    f"{opcode:02x} {count:5d} h={entry.handler:04x} "
                    f"argc={entry.argc} meta={entry.meta:02x} {name}"
                )
        return

    logic_numbers = args.logic
    if args.limit is not None:
        entries = read_dir_entries(SQ2 / "LOGDIR")
        logic_numbers = [idx for idx in range(min(args.limit, len(entries))) if entries[idx] is not None]
    if not logic_numbers:
        logic_numbers = [0]

    for idx, logic_no in enumerate(logic_numbers):
        if idx:
            print()
        print(disassemble_logic(logic_no, action_table, cond_table))


if __name__ == "__main__":
    main()
