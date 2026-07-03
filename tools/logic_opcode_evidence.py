#!/usr/bin/env python3
"""Generate the logic opcode evidence matrix from local clean-room data."""

from __future__ import annotations

import argparse
from pathlib import Path

from disassemble_logic import ACTION_NAMES, AGIDATA, COND_NAMES, load_table


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "src" / "logic_opcode_evidence.md"


QEMU_ACTIONS = {
    0x01: "logic_interpreter_probe: var_inc_reaches_expected_value, var_inc_saturates_at_ff",
    0x02: "logic_interpreter_probe: var_dec_reaches_expected_value, var_dec_saturates_at_zero",
    0x03: "logic_interpreter_probe: variable setup in all state probes",
    0x04: "logic_interpreter_probe: assignv_copies_source_variable",
    0x05: "logic_interpreter_probe: addn_uses_low_byte_arithmetic",
    0x06: "logic_interpreter_probe: addv_uses_source_variable",
    0x07: "logic_interpreter_probe: subn_uses_low_byte_arithmetic",
    0x08: "logic_interpreter_probe: subv_uses_source_variable",
    0x09: "logic_interpreter_probe: indirect_assignv_writes_indexed_destination",
    0x0A: "logic_interpreter_probe: assign_indirectv_reads_indexed_source",
    0x0B: "logic_interpreter_probe: indirect_assignn_writes_immediate_to_indexed_destination",
    0x0C: "logic_interpreter_probe: flag_set_clear_toggle_actions, or_group_true_runs_then_draw",
    0x0D: "logic_interpreter_probe: flag_set_clear_toggle_actions",
    0x0E: "logic_interpreter_probe: flag_set_clear_toggle_actions",
    0x0F: "logic_interpreter_probe: flag_var_actions_and_condition",
    0x10: "logic_interpreter_probe: flag_var_actions_and_condition",
    0x11: "logic_interpreter_probe: flag_var_actions_and_condition",
    0x14: "logic_interpreter_probe: load_logic_then_call_logic_draws",
    0x16: "logic_interpreter_probe: call_logic_draws_from_called_logic, load_logic_then_call_logic_draws",
    0x17: "logic_interpreter_probe: call_logic_var_draws_selected_logic",
    0x18: "picture/view QEMU fixtures load generated picture resources",
    0x19: "picture/view QEMU fixtures prepare generated picture resources",
    0x1A: "picture/view QEMU fixtures show generated picture resources",
    0x1E: "view/object QEMU fixtures load view resources",
    0x21: "object overlay and movement probes reset object state",
    0x22: "logic_interpreter_probe: clear_all_object_bits_keeps_current_draw_entry",
    0x23: "object overlay and movement probes activate persistent objects",
    0x24: "logic_interpreter_probe: deactivate_object_removes_persistent_draw",
    0x25: "logic_interpreter_probe: object_position_getter_observes_setter",
    0x26: "logic_interpreter_probe: set_object_pos_var_getter_observes_values",
    0x27: "logic_interpreter_probe: object_position_getter_observes_setter",
    0x28: "logic_interpreter_probe: object_add_pos_from_vars_getter_observes_sum",
    0x29: "object overlay and movement probes bind object resources",
    0x2A: "logic_interpreter_probe: var_resource_group_frame_setup_draws_persistent_object",
    0x2B: "object overlay and movement probes select object groups",
    0x2C: "logic_interpreter_probe: var_resource_group_frame_setup_draws_persistent_object",
    0x2F: "object overlay and movement probes select object frames",
    0x30: "logic_interpreter_probe: var_resource_group_frame_setup_draws_persistent_object",
    0x31: "logic_interpreter_probe: object_view_metadata_getters",
    0x32: "logic_interpreter_probe: object_view_metadata_getters",
    0x33: "logic_interpreter_probe: object_view_metadata_getters",
    0x34: "logic_interpreter_probe: object_view_metadata_getters",
    0x35: "logic_interpreter_probe: object_view_metadata_getters",
    0x36: "logic_interpreter_probe: object_field_24_getter_observes_setter",
    0x37: "logic_interpreter_probe: object_field_24_var_getter_observes_value",
    0x39: "logic_interpreter_probe: object_field_24_getter_observes_setter",
    0x43: "object_movement_probe: movement_collision",
    0x4F: "object_movement_probe: autonomous_modes_003 and motion_modes_004",
    0x50: "object_movement_probe: autonomous_modes_003 and motion_modes_004",
    0x51: "object_movement_probe: motion_modes_004",
    0x52: "logic_interpreter_probe: move_object_to_var_sets_flag_at_existing_target",
    0x53: "object_movement_probe: autonomous_modes_003",
    0x54: "object_movement_probe: motion_modes_004",
    0x55: "object_movement_probe setup paths",
    0x56: "logic_interpreter_probe: object_field_21_getter_observes_setter",
    0x57: "logic_interpreter_probe: object_field_21_getter_observes_setter",
    0x45: "logic_interpreter_probe: object_distance_inactive_pair_sets_ff",
    0x4D: "logic_interpreter_probe: clear_object_fields_21_22_clears_direction",
    0x5C: "logic_interpreter_probe: inventory_marker_ff_condition_true",
    0x5D: "logic_interpreter_probe: inventory_marker_ff_var_and_getter",
    0x5E: "logic_interpreter_probe: inventory_marker_clear_and_getter",
    0x5F: "logic_interpreter_probe: inventory_marker_from_var",
    0x60: "logic_interpreter_probe: inventory_marker_from_var_var",
    0x61: "logic_interpreter_probe: inventory marker getter probes",
    0x72: "logic_interpreter_probe: set_string_from_message_equal_normalized and parse_string_slot_sets_input_word_sequence",
    0x75: "logic_interpreter_probe: parse_string_slot_sets_input_word_sequence",
    0x7A: "logic_interpreter_probe and object_overlay_probe transient drawing",
    0x7B: "logic_interpreter_probe: setup_transient_object_var_draws_selected_cel",
    0x7F: "logic_interpreter_probe: noop_7f_continues_to_draw",
    0x82: "logic_interpreter_probe: random_equal_bounds_stores_bound",
    0x91: "logic_interpreter_probe: save_restore_resume_actions_continue_to_draw",
    0x92: "logic_interpreter_probe: save_restore_resume_actions_continue_to_draw",
    0x93: "logic_interpreter_probe: set_object_pos_dirty_getter_observes_values",
    0x94: "logic_interpreter_probe: set_object_pos_dirty_var_getter_observes_values",
    0x9B: "logic_interpreter_probe: noop_9b_consumes_two_operands_then_draws",
    0xA5: "logic_interpreter_probe: muln_keeps_low_product_byte",
    0xA6: "logic_interpreter_probe: mulv_keeps_low_product_byte",
    0xA7: "logic_interpreter_probe: divn_stores_quotient_byte",
    0xA8: "logic_interpreter_probe: divv_stores_quotient_byte",
    0xAE: "object_overlay_probe: priority-table rebuild effects",
    0xAF: "logic_interpreter_probe: noop_af_runtime_consumes_no_operand",
}


QEMU_SMOKE_ACTIONS = {
    0x38: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x3A: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x3B: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x3C: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x3D: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x3E: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x40: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x41: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x42: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x44: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x46: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x47: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x4C: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x4E: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x58: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
    0x59: "logic_interpreter_probe: object_bitfield_actions_dispatch_smoke",
}


QEMU_CONDITIONS = {
    0x00: "logic_interpreter_probe: always_false_condition_skips_then_draw",
    0x01: "logic_interpreter_probe: if_false_skips_then_draw and state probes",
    0x02: "logic_interpreter_probe: var_comparison_conditions_all_true",
    0x03: "logic_interpreter_probe: var_comparison_conditions_all_true",
    0x04: "logic_interpreter_probe: var_comparison_conditions_all_true",
    0x05: "logic_interpreter_probe: var_comparison_conditions_all_true",
    0x06: "logic_interpreter_probe: var_comparison_conditions_all_true",
    0x07: "logic_interpreter_probe: flag_set_clear_toggle_actions and OR-group probe",
    0x08: "logic_interpreter_probe: flag_var_actions_and_condition",
    0x09: "logic_interpreter_probe: inventory_marker_ff_condition_true",
    0x0A: "logic_interpreter_probe: inventory_marker_eq_var_condition_true",
    0x0B: "logic_interpreter_probe: object_left_rect_condition_true",
    0x0E: "logic_interpreter_probe: parse_string_slot_sets_input_word_sequence",
    0x0F: "logic_interpreter_probe: set_string_from_message_equal_normalized",
    0x10: "logic_interpreter_probe: object_width_rect_condition_true",
    0x11: "logic_interpreter_probe: object_center_rect_condition_true",
    0x12: "logic_interpreter_probe: object_right_rect_condition_true",
}


QEMU_STRUCTURAL = {
    "0xfc": "logic_interpreter_probe: or_group_true_runs_then_draw",
    "0xfd": "logic_interpreter_probe: not_condition_runs_then_draw",
    "0xfe": "logic_interpreter_probe: jump_skips_first_draw",
    "0xff": "logic_interpreter_probe: all conditional probes",
}


def operand_shape(argc: int, meta: int) -> str:
    if argc == 0:
        return "-"
    parts = []
    for idx in range(argc):
        bit = 0x80 >> idx
        parts.append(f"var{idx}" if meta & bit else f"imm{idx}")
    return ", ".join(parts)


def summary_from_label(label: str) -> str:
    return label.replace("_", " ")


def action_evidence(opcode: int) -> tuple[str, str]:
    if opcode == 0x00:
        return (
            "source-backed structural",
            "Handled by code.logic.interpret_main before action dispatch; table entry is not executed.",
        )
    if opcode in QEMU_ACTIONS:
        return ("QEMU-validated", QEMU_ACTIONS[opcode])
    if opcode in QEMU_SMOKE_ACTIONS:
        return ("QEMU dispatch-smoke", QEMU_SMOKE_ACTIONS[opcode])
    return ("source-backed", "Handler disassembly and local SQ2 bytecode scan; see logic_bytecode.md.")


def condition_evidence(opcode: int) -> tuple[str, str]:
    if opcode in QEMU_CONDITIONS:
        return ("QEMU-validated", QEMU_CONDITIONS[opcode])
    return ("source-backed", "Handler disassembly and local SQ2 bytecode scan; see logic_bytecode.md.")


def markdown() -> str:
    data = AGIDATA.read_bytes()
    action_table = load_table(data, 0x061D, 0xB0)
    condition_table = load_table(data, 0x08FD, 0x13)

    lines = [
        "# Logic Opcode Evidence Matrix",
        "",
        "This chapter is generated from local clean-room artifacts by",
        "`tools/logic_opcode_evidence.py`. It is a coverage index, not the full",
        "semantic specification; detailed behavior remains in",
        "`logic_bytecode.md` and the command/evidence trail remains in",
        "`clean_room_executable_notes.md`.",
        "",
        "Evidence levels:",
        "",
        "- **QEMU-validated**: a generated fixture has been run through the",
        "  original SQ2 interpreter in QEMU and compared against the local",
        "  expected output.",
        "- **QEMU dispatch-smoke**: a generated fixture proves the opcode executes,",
        "  consumes operands, and returns to following bytecode under the original",
        "  interpreter, but it does not yet expose every downstream state mutation.",
        "- **source-backed**: behavior is derived from local disassembly and local",
        "  SQ2 bytecode/resource scans, but no targeted QEMU fixture is recorded",
        "  for the opcode yet.",
        "- **source-backed structural**: handled directly by the interpreter loop",
        "  or condition scanner rather than by the normal action/condition",
        "  handler dispatch path.",
        "- **reserved/invalid**: outside the valid opcode catalog for this SQ2",
        "  build.",
        "",
        "## Structural and Invalid Bytes",
        "",
        "| Context | Byte or range | Label | Evidence level | Evidence |",
        "| --- | ---: | --- | --- | --- |",
        "| Main stream | `0x00` | `end` | source-backed structural | Terminates the current logic path before action dispatch. |",
        "| Main stream | `0x01..0xaf` | action opcodes | mixed | See the action matrix below. |",
        "| Main stream | `0xb0..0xfb` | invalid action bytes | reserved/invalid | Action dispatcher rejects opcodes above `0xaf`. |",
        "| Main stream | `0xfc` | invalid outside conditions | reserved/invalid | Action dispatcher rejects structural/control byte. |",
        "| Main stream | `0xfd` | invalid outside conditions | reserved/invalid | Action dispatcher rejects structural/control byte. |",
        f"| Main stream | `0xfe` | `jump` | QEMU-validated | {QEMU_STRUCTURAL['0xfe']} |",
        f"| Main stream | `0xff` | `if` | QEMU-validated | {QEMU_STRUCTURAL['0xff']} |",
        f"| Condition list | `0xfc` | `OR_MARK` | QEMU-validated | {QEMU_STRUCTURAL['0xfc']} |",
        f"| Condition list | `0xfd` | `NOT_NEXT` | QEMU-validated | {QEMU_STRUCTURAL['0xfd']} |",
        "| Condition list | `0xfe` | invalid predicate byte | reserved/invalid | Rejected if seen as a predicate opcode. |",
        "| Condition list | `0xff` | condition terminator | QEMU-validated | Ends condition list and precedes the false-path delta. |",
        "| Condition list | `0x13..0x25` | reserved predicate range | reserved/invalid | Bytes after condition-table entry `0x12` are not a valid table region in this build. |",
        "| Condition list | `0x26..0xfb` | invalid predicate range | reserved/invalid | Condition dispatcher rejects predicate opcodes `>= 0x26`. |",
        "",
        "## Action Opcodes",
        "",
        "| Opcode | Label | Operand shape | Behavior summary | Evidence level | Probe/evidence |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]

    for opcode in range(0xB0):
        entry = action_table[opcode]
        label = ACTION_NAMES[opcode]
        level, evidence = action_evidence(opcode)
        lines.append(
            f"| `0x{opcode:02x}` | `{label}` | {operand_shape(entry.argc, entry.meta)} | "
            f"{summary_from_label(label)} | {level} | {evidence} |"
        )

    lines.extend(
        [
            "",
            "## Condition Opcodes",
            "",
            "| Opcode | Label | Operand shape | Behavior summary | Evidence level | Probe/evidence |",
            "| ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for opcode in range(0x13):
        entry = condition_table[opcode]
        label = COND_NAMES[opcode]
        level, evidence = condition_evidence(opcode)
        shape = "varlen word sequence" if opcode == 0x0E else operand_shape(entry.argc, entry.meta)
        lines.append(
            f"| `0x{opcode:02x}` | `{label}` | {shape} | "
            f"{summary_from_label(label)} | {level} | {evidence} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the output file is not current")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    text = markdown()
    if args.check:
        current = args.output.read_text(encoding="utf-8")
        if current != text:
            raise SystemExit(f"{args.output} is not current; run tools/logic_opcode_evidence.py")
        return
    args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
