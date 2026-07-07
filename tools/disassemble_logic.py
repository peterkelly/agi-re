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

from project_paths import game_dir


ROOT = Path(__file__).resolve().parents[1]
SQ2 = game_dir()
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
    0x0B: "object_left_baseline_in_rect",
    0x0C: "status_byte_1218",
    0x0D: "raw_key_event_available",
    0x0E: "input_word_sequence",
    0x0F: "string_slots_equal_normalized",
    0x10: "object_width_baseline_in_rect",
    0x11: "object_center_baseline_in_rect",
    0x12: "object_right_baseline_in_rect",
}


ACTION_NAMES = {
    0x00: "end",
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
    0x12: "switch_room_like",
    0x13: "switch_room_like_var",
    0x14: "load_logic",
    0x15: "load_logic_var",
    0x16: "call_logic",
    0x17: "call_logic_var",
    0x18: "load_picture_var",
    0x19: "prepare_picture_var",
    0x1A: "show_picture_like",
    0x1B: "discard_picture_var",
    0x1C: "overlay_picture_var",
    0x1D: "show_priority_screen",
    0x1E: "load_view",
    0x1F: "load_view_var",
    0x20: "discard_view",
    0x21: "reset_object_state",
    0x22: "clear_all_object_bits",
    0x23: "activate_object",
    0x24: "deactivate_object",
    0x25: "set_object_pos",
    0x26: "set_object_pos_var",
    0x27: "get_object_pos",
    0x28: "add_object_pos_from_vars",
    0x29: "set_object_resource",
    0x2A: "set_object_resource_var",
    0x2B: "set_object_subresource",
    0x2C: "set_object_subresource_var",
    0x2D: "set_object_bit_2000",
    0x2E: "clear_object_bit_2000",
    0x2F: "set_object_derived_resource_2",
    0x30: "set_object_derived_resource_2_var",
    0x31: "get_object_resource_loop_count",
    0x32: "get_object_field_0e",
    0x33: "get_object_field_0a",
    0x34: "get_object_field_07",
    0x35: "get_object_field_0b",
    0x36: "set_object_field_24",
    0x37: "set_object_field_24_var",
    0x38: "clear_object_bit_0004",
    0x39: "get_object_field_24",
    0x3A: "clear_object_bit_0010",
    0x3B: "set_object_bit_0010",
    0x3C: "refresh_object_lists",
    0x3D: "set_object_bit_0008",
    0x3E: "clear_object_bit_0008",
    0x3F: "set_global_012d",
    0x40: "set_object_bit_0100",
    0x41: "set_object_bit_0800",
    0x42: "clear_object_bits_0900",
    0x43: "set_object_bit_0200",
    0x44: "clear_object_bit_0200",
    0x45: "object_distance_to_var",
    0x46: "clear_object_bit_0020",
    0x47: "set_object_bit_0020",
    0x48: "set_object_field_23_mode0",
    0x49: "set_object_field_23_mode1",
    0x4A: "set_object_field_23_mode3",
    0x4B: "set_object_field_23_mode2",
    0x4C: "set_object_field_1f_var",
    0x4D: "clear_object_fields_21_22",
    0x4E: "clear_object_field_22_and_global",
    0x4F: "set_object_field_1e_var",
    0x50: "set_object_field_01_var",
    0x51: "move_object_to",
    0x52: "move_object_to_var",
    0x53: "approach_first_object_until_near",
    0x54: "start_random_motion",
    0x55: "stop_motion_mode",
    0x56: "set_object_field_21_var",
    0x57: "get_object_field_21",
    0x58: "set_object_bit_0002",
    0x59: "clear_object_bit_0002",
    0x5A: "set_rect_bounds_0131",
    0x5B: "clear_rect_bounds_0131",
    0x5C: "set_entry_0971_marker_ff",
    0x5D: "set_entry_0971_marker_ff_var",
    0x5E: "clear_entry_0971_marker",
    0x5F: "set_entry_0971_marker_from_var",
    0x60: "set_entry_0971_marker_from_var_var",
    0x61: "get_entry_0971_marker_to_var",
    0x62: "load_sound",
    0x63: "start_sound_with_flag",
    0x64: "stop_sound_or_clear_sound_state",
    0x65: "display_message",
    0x66: "display_message_var",
    0x67: "display_formatted_message",
    0x68: "display_formatted_message_var",
    0x69: "clear_text_rect",
    0x6A: "enable_text_attr_mode_1757",
    0x6B: "disable_text_attr_mode_1757",
    0x6C: "set_input_prompt_char",
    0x6D: "set_text_window_pair",
    0x6E: "shake_screen_like",
    0x6F: "set_input_line_config",
    0x70: "show_status_line_like",
    0x71: "hide_status_line_like",
    0x72: "set_string_slot_from_message",
    0x73: "prompt_string_to_slot",
    0x74: "set_string_slot_from_table",
    0x75: "parse_string_slot",
    0x76: "prompt_number_to_var",
    0x77: "disable_input_line_like",
    0x78: "enable_input_line_like",
    0x79: "map_key_event",
    0x7A: "setup_transient_object",
    0x7B: "setup_transient_object_var",
    0x7C: "show_inventory_selection",
    0x7D: "save_game_state",
    0x7E: "restore_game_state",
    0x7F: "noop",
    0x80: "confirm_restart_game",
    0x81: "display_view_resource_text_like",
    0x82: "random_range_to_var",
    0x83: "clear_global_0139",
    0x84: "set_global_0139_and_clear_object0_field_22",
    0x85: "display_object_diagnostics_var",
    0x86: "confirm_and_restart_like",
    0x87: "show_heap_status",
    0x88: "pause_game_message",
    0x89: "refresh_input_line",
    0x8A: "erase_input_line",
    0x8B: "calibrate_joystick",
    0x8C: "toggle_display_mode_bit",
    0x8D: "show_interpreter_version",
    0x8E: "set_global_0141_and_refresh",
    0x8F: "verify_game_signature",
    0x90: "append_message_to_log_file",
    0x91: "save_logic_resume_ip",
    0x92: "restore_logic_entry_ip",
    0x93: "set_object_pos_dirty",
    0x94: "set_object_pos_dirty_var",
    0x95: "enable_action_trace_window",
    0x96: "configure_action_trace_window",
    0x97: "display_message_configured",
    0x98: "display_message_configured_var",
    0x99: "discard_view_var",
    0x9A: "clear_text_rect_bounds",
    0x9B: "noop_2",
    0x9C: "add_menu_heading_like",
    0x9D: "add_menu_item_like",
    0x9E: "finalize_menu_like",
    0x9F: "enable_menu_item_like",
    0xA0: "disable_menu_item_like",
    0xA1: "mark_menu_if_flag_0e",
    0xA2: "display_view_resource_text_like_var",
    0xA3: "set_global_0d0f",
    0xA4: "clear_global_0d0f",
    0xA5: "muln",
    0xA6: "mulv",
    0xA7: "divn",
    0xA8: "divv",
    0xA9: "close_text_window_state",
    0xAA: "copy_save_description_to_string_slot",
    0xAB: "save_event_buffer_count",
    0xAC: "restore_event_buffer_count",
    0xAD: "increment_global_1530",
    0xAE: "rebuild_priority_table_from_y",
    0xAF: "noop_1_table_count",
}


ACTION_META_OVERRIDES = {
    # The table marks this as 0x01, but the handler reads var[arg0].
    0xA2: 0x80,
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
        operand_meta = ACTION_META_OVERRIDES.get(opcode, entry.meta)
        lines.append(
            f"{at:04x}: action {opcode:02x} {name}({operand_text(args, operand_meta)})"
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
