# Logic Opcode Evidence Matrix

This chapter is generated from local clean-room artifacts by
`tools/logic_opcode_evidence.py`. It is a coverage index, not the full
semantic specification; detailed behavior remains in
`logic_bytecode.md` and the command/evidence trail remains in
`clean_room_executable_notes.md`.

Evidence levels:

- **QEMU-validated**: a generated fixture has been run through the
  original SQ2 interpreter in QEMU and compared against the local
  expected output.
- **QEMU dispatch-smoke**: a generated fixture proves the opcode executes,
  consumes operands, and returns to following bytecode under the original
  interpreter, but it does not yet expose every downstream state mutation.
- **source-backed**: behavior is derived from local disassembly and local
  SQ2 bytecode/resource scans, but no targeted QEMU fixture is recorded
  for the opcode yet.
- **source-backed structural**: handled directly by the interpreter loop
  or condition scanner rather than by the normal action/condition
  handler dispatch path.
- **reserved/invalid**: outside the valid opcode catalog for this SQ2
  build.

## Structural and Invalid Bytes

| Context | Byte or range | Label | Evidence level | Evidence |
| --- | ---: | --- | --- | --- |
| Main stream | `0x00` | `end` | source-backed structural | Terminates the current logic path before action dispatch. |
| Main stream | `0x01..0xaf` | action opcodes | mixed | See the action matrix below. |
| Main stream | `0xb0..0xfb` | invalid action bytes | reserved/invalid | Action dispatcher rejects opcodes above `0xaf`. |
| Main stream | `0xfc` | invalid outside conditions | reserved/invalid | Action dispatcher rejects structural/control byte. |
| Main stream | `0xfd` | invalid outside conditions | reserved/invalid | Action dispatcher rejects structural/control byte. |
| Main stream | `0xfe` | `jump` | QEMU-validated | logic_interpreter_probe: jump_skips_first_draw |
| Main stream | `0xff` | `if` | QEMU-validated | logic_interpreter_probe: all conditional probes |
| Condition list | `0xfc` | `OR_MARK` | QEMU-validated | logic_interpreter_probe: or_group_true_runs_then_draw |
| Condition list | `0xfd` | `NOT_NEXT` | QEMU-validated | logic_interpreter_probe: not_condition_runs_then_draw |
| Condition list | `0xfe` | invalid predicate byte | reserved/invalid | Rejected if seen as a predicate opcode. |
| Condition list | `0xff` | condition terminator | QEMU-validated | Ends condition list and precedes the false-path delta. |
| Condition list | `0x13..0x25` | reserved predicate range | reserved/invalid | Bytes after condition-table entry `0x12` are not a valid table region in this build. |
| Condition list | `0x26..0xfb` | invalid predicate range | reserved/invalid | Condition dispatcher rejects predicate opcodes `>= 0x26`. |

## Action Opcodes

| Opcode | Label | Operand shape | Behavior summary | Evidence level | Probe/evidence |
| ---: | --- | --- | --- | --- | --- |
| `0x00` | `end` | - | end | source-backed structural | Handled by code.logic.interpret_main before action dispatch; table entry is not executed. |
| `0x01` | `inc_var` | var0 | inc var | QEMU-validated | logic_interpreter_probe: var_inc_reaches_expected_value, var_inc_saturates_at_ff |
| `0x02` | `dec_var` | var0 | dec var | QEMU-validated | logic_interpreter_probe: var_dec_reaches_expected_value, var_dec_saturates_at_zero |
| `0x03` | `assignn` | var0, imm1 | assignn | QEMU-validated | logic_interpreter_probe: variable setup in all state probes |
| `0x04` | `assignv` | var0, var1 | assignv | QEMU-validated | logic_interpreter_probe: assignv_copies_source_variable |
| `0x05` | `addn` | var0, imm1 | addn | QEMU-validated | logic_interpreter_probe: addn_uses_low_byte_arithmetic |
| `0x06` | `addv` | var0, var1 | addv | QEMU-validated | logic_interpreter_probe: addv_uses_source_variable |
| `0x07` | `subn` | var0, imm1 | subn | QEMU-validated | logic_interpreter_probe: subn_uses_low_byte_arithmetic |
| `0x08` | `subv` | var0, var1 | subv | QEMU-validated | logic_interpreter_probe: subv_uses_source_variable |
| `0x09` | `indirect_assignv` | var0, var1 | indirect assignv | QEMU-validated | logic_interpreter_probe: indirect_assignv_writes_indexed_destination |
| `0x0a` | `assign_indirectv` | var0, var1 | assign indirectv | QEMU-validated | logic_interpreter_probe: assign_indirectv_reads_indexed_source |
| `0x0b` | `indirect_assignn` | var0, imm1 | indirect assignn | QEMU-validated | logic_interpreter_probe: indirect_assignn_writes_immediate_to_indexed_destination |
| `0x0c` | `set_flag` | imm0 | set flag | QEMU-validated | logic_interpreter_probe: flag_set_clear_toggle_actions, or_group_true_runs_then_draw |
| `0x0d` | `clear_flag` | imm0 | clear flag | QEMU-validated | logic_interpreter_probe: flag_set_clear_toggle_actions |
| `0x0e` | `toggle_flag` | imm0 | toggle flag | QEMU-validated | logic_interpreter_probe: flag_set_clear_toggle_actions |
| `0x0f` | `set_flag_var` | var0 | set flag var | QEMU-validated | logic_interpreter_probe: flag_var_actions_and_condition |
| `0x10` | `clear_flag_var` | var0 | clear flag var | QEMU-validated | logic_interpreter_probe: flag_var_actions_and_condition |
| `0x11` | `toggle_flag_var` | var0 | toggle flag var | QEMU-validated | logic_interpreter_probe: flag_var_actions_and_condition |
| `0x12` | `switch_room_like` | imm0 | switch room like | QEMU-validated | logic_interpreter_probe: switch_room_reentry_dispatches_current_room, switch_room_sets_current_previous_and_clears_boundary, switch_room_boundary_1..4, and switch_room_removes_preexisting_persistent_object |
| `0x13` | `switch_room_like_var` | var0 | switch room like var | QEMU-validated | logic_interpreter_probe: switch_room_v_reentry_dispatches_current_room, switch_room_v_sets_current_previous_and_clears_boundary, switch_room_v_boundary_1..4, and switch_room_v_removes_preexisting_persistent_object |
| `0x14` | `load_logic` | imm0 | load logic | QEMU-validated | logic_interpreter_probe: load_logic_then_call_logic_draws |
| `0x15` | `load_logic_var` | var0 | load logic var | QEMU-validated | logic_interpreter_probe: load_logic_var_then_call_logic_draws |
| `0x16` | `call_logic` | imm0 | call logic | QEMU-validated | logic_interpreter_probe: call_logic_draws_from_called_logic, load_logic_then_call_logic_draws |
| `0x17` | `call_logic_var` | var0 | call logic var | QEMU-validated | logic_interpreter_probe: call_logic_var_draws_selected_logic, switch_room_reentry_dispatches_current_room |
| `0x18` | `load_picture_var` | var0 | load picture var | QEMU-validated | picture/view QEMU fixtures load generated picture resources |
| `0x19` | `prepare_picture_var` | var0 | prepare picture var | QEMU-validated | picture/view QEMU fixtures prepare generated picture resources |
| `0x1a` | `show_picture_like` | - | show picture like | QEMU-validated | picture/view QEMU fixtures show generated picture resources; logic_interpreter_probe: overlay_picture_var_composes_extra_picture |
| `0x1b` | `discard_picture_var` | var0 | discard picture var | QEMU-validated | logic_interpreter_probe: discard_picture_var_allows_reload_and_overlay |
| `0x1c` | `overlay_picture_var` | var0 | overlay picture var | QEMU-validated | logic_interpreter_probe: overlay_picture_var_composes_extra_picture |
| `0x1d` | `show_priority_screen` | - | show priority screen | QEMU-validated | logic_interpreter_probe: priority_screen_enter_returns |
| `0x1e` | `load_view` | imm0 | load view | QEMU-validated | view/object QEMU fixtures load view resources |
| `0x1f` | `load_view_var` | var0 | load view var | QEMU-validated | logic_interpreter_probe: load_view_var_allows_following_draw |
| `0x20` | `discard_view` | imm0 | discard view | QEMU-validated | logic_interpreter_probe: discard_view_allows_reload_and_draw |
| `0x21` | `reset_object_state` | imm0 | reset object state | QEMU-validated | object overlay and movement probes reset object state |
| `0x22` | `clear_all_object_bits` | - | clear all object bits | QEMU-validated | logic_interpreter_probe: clear_all_object_bits_keeps_current_draw_entry |
| `0x23` | `activate_object` | imm0 | activate object | QEMU-validated | object overlay and movement probes activate persistent objects |
| `0x24` | `deactivate_object` | imm0 | deactivate object | QEMU-validated | logic_interpreter_probe: deactivate_object_removes_persistent_draw |
| `0x25` | `set_object_pos` | imm0, imm1, imm2 | set object pos | QEMU-validated | logic_interpreter_probe: object_position_getter_observes_setter |
| `0x26` | `set_object_pos_var` | imm0, var1, var2 | set object pos var | QEMU-validated | logic_interpreter_probe: set_object_pos_var_getter_observes_values |
| `0x27` | `get_object_pos` | imm0, var1, var2 | get object pos | QEMU-validated | logic_interpreter_probe: object_position_getter_observes_setter |
| `0x28` | `add_object_pos_from_vars` | imm0, var1, var2 | add object pos from vars | QEMU-validated | logic_interpreter_probe: object_add_pos_from_vars_getter_observes_sum |
| `0x29` | `set_object_resource` | imm0, imm1 | set object resource | QEMU-validated | object overlay and movement probes bind object resources |
| `0x2a` | `set_object_resource_var` | imm0, var1 | set object resource var | QEMU-validated | logic_interpreter_probe: var_resource_group_frame_setup_draws_persistent_object |
| `0x2b` | `set_object_subresource` | imm0, imm1 | set object subresource | QEMU-validated | object overlay and movement probes select object groups |
| `0x2c` | `set_object_subresource_var` | imm0, var1 | set object subresource var | QEMU-validated | logic_interpreter_probe: var_resource_group_frame_setup_draws_persistent_object |
| `0x2d` | `set_object_bit_2000` | imm0 | set object bit 2000 | QEMU-validated | logic_interpreter_probe: object_bit_2000_002 |
| `0x2e` | `clear_object_bit_2000` | imm0 | clear object bit 2000 | QEMU-validated | logic_interpreter_probe: object_bit_2000_002 |
| `0x2f` | `set_object_derived_resource_2` | imm0, imm1 | set object derived resource 2 | QEMU-validated | object overlay and movement probes select object frames |
| `0x30` | `set_object_derived_resource_2_var` | imm0, var1 | set object derived resource 2 var | QEMU-validated | logic_interpreter_probe: var_resource_group_frame_setup_draws_persistent_object |
| `0x31` | `get_object_resource_loop_count` | imm0, var1 | get object resource loop count | QEMU-validated | logic_interpreter_probe: object_view_metadata_getters |
| `0x32` | `get_object_field_0e` | imm0, var1 | get object field 0e | QEMU-validated | logic_interpreter_probe: object_view_metadata_getters |
| `0x33` | `get_object_field_0a` | imm0, var1 | get object field 0a | QEMU-validated | logic_interpreter_probe: object_view_metadata_getters |
| `0x34` | `get_object_field_07` | imm0, var1 | get object field 07 | QEMU-validated | logic_interpreter_probe: object_view_metadata_getters |
| `0x35` | `get_object_field_0b` | imm0, var1 | get object field 0b | QEMU-validated | logic_interpreter_probe: object_view_metadata_getters |
| `0x36` | `set_object_field_24` | imm0, imm1 | set object field 24 | QEMU-validated | logic_interpreter_probe: object_field_24_getter_observes_setter |
| `0x37` | `set_object_field_24_var` | imm0, var1 | set object field 24 var | QEMU-validated | logic_interpreter_probe: object_field_24_var_getter_observes_value |
| `0x38` | `clear_object_bit_0004` | imm0 | clear object bit 0004 | QEMU-validated | logic_interpreter_probe: clear_fixed_priority_bit_uses_derived_priority |
| `0x39` | `get_object_field_24` | imm0, var1 | get object field 24 | QEMU-validated | logic_interpreter_probe: object_field_24_getter_observes_setter |
| `0x3a` | `clear_object_bit_0010` | imm0 | clear object bit 0010 | QEMU-validated | logic_interpreter_probe: object_root_partition_004 |
| `0x3b` | `set_object_bit_0010` | imm0 | set object bit 0010 | QEMU-validated | logic_interpreter_probe: object_root_partition_004 |
| `0x3c` | `refresh_object_lists` | imm0 | refresh object lists | QEMU-validated | logic_interpreter_probe: object_root_partition_004 |
| `0x3d` | `set_object_bit_0008` | imm0 | set object bit 0008 | QEMU-validated | logic_interpreter_probe: horizon_exempt_bit_keeps_object_above_horizon |
| `0x3e` | `clear_object_bit_0008` | imm0 | clear object bit 0008 | QEMU-validated | logic_interpreter_probe: horizon_clear_exempt_bit_restores_clamp |
| `0x3f` | `set_global_012d` | imm0 | set global 012d | QEMU-validated | logic_interpreter_probe: horizon_clamps_object_when_bit_clear |
| `0x40` | `set_object_bit_0100` | imm0 | set object bit 0100 | QEMU-validated | object_movement_probe: control_bits_0900_002 |
| `0x41` | `set_object_bit_0800` | imm0 | set object bit 0800 | QEMU-validated | object_movement_probe: control_bits_0900_002 |
| `0x42` | `clear_object_bits_0900` | imm0 | clear object bits 0900 | QEMU-validated | object_movement_probe: control_bits_0900_002 |
| `0x43` | `set_object_bit_0200` | imm0 | set object bit 0200 | QEMU-validated | object_movement_probe: movement_collision |
| `0x44` | `clear_object_bit_0200` | imm0 | clear object bit 0200 | QEMU-validated | object_movement_probe: clear_skip_bit_001 |
| `0x45` | `object_distance_to_var` | imm0, imm1, var2 | object distance to var | QEMU-validated | logic_interpreter_probe: object_distance_inactive_pair_sets_ff |
| `0x46` | `clear_object_bit_0020` | imm0 | clear object bit 0020 | QEMU-validated | object_movement_probe: frame_timer_001 |
| `0x47` | `set_object_bit_0020` | imm0 | set object bit 0020 | QEMU-validated | object_movement_probe: frame_timer_001 |
| `0x48` | `set_object_field_23_mode0` | imm0 | set object field 23 mode0 | QEMU-validated | object_movement_probe: frame_timer_modes_002 |
| `0x49` | `set_object_field_23_mode1` | imm0, imm1 | set object field 23 mode1 | QEMU-validated | logic_interpreter_probe: object_field_23_mode1_clears_flag |
| `0x4a` | `set_object_field_23_mode3` | imm0 | set object field 23 mode3 | QEMU-validated | object_movement_probe: frame_timer_modes_002 |
| `0x4b` | `set_object_field_23_mode2` | imm0, imm1 | set object field 23 mode2 | QEMU-validated | logic_interpreter_probe: object_field_23_mode2_clears_flag; object_movement_probe: frame_timer_modes_002 |
| `0x4c` | `set_object_field_1f_var` | imm0, var1 | set object field 1f var | QEMU-validated | object_movement_probe: frame_timer_001 |
| `0x4d` | `clear_object_fields_21_22` | imm0 | clear object fields 21 22 | QEMU-validated | logic_interpreter_probe: clear_object_fields_21_22_clears_direction |
| `0x4e` | `clear_object_field_22_and_global` | imm0 | clear object field 22 and global | QEMU-validated | object_movement_probe: clear_field_22_001 |
| `0x4f` | `set_object_field_1e_var` | imm0, var1 | set object field 1e var | QEMU-validated | object_movement_probe: autonomous_modes_003 and motion_modes_004 |
| `0x50` | `set_object_field_01_var` | imm0, var1 | set object field 01 var | QEMU-validated | object_movement_probe: autonomous_modes_003 and motion_modes_004 |
| `0x51` | `move_object_to` | imm0, imm1, imm2, imm3, imm4 | move object to | QEMU-validated | object_movement_probe: motion_modes_004 |
| `0x52` | `move_object_to_var` | imm0, var1, var2, var3, imm4 | move object to var | QEMU-validated | logic_interpreter_probe: move_object_to_var_sets_flag_at_existing_target |
| `0x53` | `approach_first_object_until_near` | imm0, imm1, imm2 | approach first object until near | QEMU-validated | object_movement_probe: autonomous_modes_003 |
| `0x54` | `start_random_motion` | imm0 | start random motion | QEMU-validated | object_movement_probe: motion_modes_004 |
| `0x55` | `stop_motion_mode` | imm0 | stop motion mode | QEMU-validated | object_movement_probe setup paths |
| `0x56` | `set_object_field_21_var` | imm0, var1 | set object field 21 var | QEMU-validated | logic_interpreter_probe: object_field_21_getter_observes_setter |
| `0x57` | `get_object_field_21` | imm0, var1 | get object field 21 | QEMU-validated | logic_interpreter_probe: object_field_21_getter_observes_setter |
| `0x58` | `set_object_bit_0002` | imm0 | set object bit 0002 | QEMU-validated | object_movement_probe: rect_bit_0002_001 |
| `0x59` | `clear_object_bit_0002` | imm0 | clear object bit 0002 | QEMU-validated | object_movement_probe: rect_bit_0002_001 |
| `0x5a` | `set_rect_bounds_0131` | imm0, imm1, imm2, imm3 | set rect bounds 0131 | QEMU-validated | object_movement_probe: rect_bit_0002_001 and rect_bounds_clear_001 |
| `0x5b` | `clear_rect_bounds_0131` | - | clear rect bounds 0131 | QEMU-validated | object_movement_probe: rect_bounds_clear_001 |
| `0x5c` | `set_entry_0971_marker_ff` | imm0 | set entry 0971 marker ff | QEMU-validated | logic_interpreter_probe: inventory_marker_ff_condition_true |
| `0x5d` | `set_entry_0971_marker_ff_var` | var0 | set entry 0971 marker ff var | QEMU-validated | logic_interpreter_probe: inventory_marker_ff_var_and_getter |
| `0x5e` | `clear_entry_0971_marker` | imm0 | clear entry 0971 marker | QEMU-validated | logic_interpreter_probe: inventory_marker_clear_and_getter |
| `0x5f` | `set_entry_0971_marker_from_var` | imm0, imm1 | set entry 0971 marker from var | QEMU-validated | logic_interpreter_probe: inventory_marker_from_var |
| `0x60` | `set_entry_0971_marker_from_var_var` | imm0, var1 | set entry 0971 marker from var var | QEMU-validated | logic_interpreter_probe: inventory_marker_from_var_var |
| `0x61` | `get_entry_0971_marker_to_var` | var0, var1 | get entry 0971 marker to var | QEMU-validated | logic_interpreter_probe: inventory marker getter probes |
| `0x62` | `load_sound` | imm0 | load sound | QEMU-validated | logic_interpreter_probe: sound_stop_sets_completion_flag |
| `0x63` | `start_sound_with_flag` | imm0, imm1 | start sound with flag | QEMU-validated | logic_interpreter_probe: sound_stop_sets_completion_flag |
| `0x64` | `stop_sound_or_clear_sound_state` | - | stop sound or clear sound state | QEMU-validated | logic_interpreter_probe: sound_stop_sets_completion_flag |
| `0x65` | `display_message` | imm0 | display message | QEMU-validated | logic_interpreter_probe: display_message_then_ack_continues_to_draw |
| `0x66` | `display_message_var` | var0 | display message var | QEMU-validated | logic_interpreter_probe: display_message_var_then_ack_continues_to_draw |
| `0x67` | `display_formatted_message` | imm0, imm1, imm2 | display formatted message | QEMU-validated | logic_interpreter_probe: display_formatted_message_then_ack_continues_to_draw |
| `0x68` | `display_formatted_message_var` | var0, var1, var2 | display formatted message var | QEMU-validated | logic_interpreter_probe: display_formatted_message_var_then_ack_continues_to_draw |
| `0x69` | `clear_text_rect` | imm0, imm1, imm2 | clear text rect | QEMU-validated | logic_interpreter_probe: text_rect_clear_rows_removes_formatted_text |
| `0x6a` | `enable_text_attr_mode_1757` | - | enable text attr mode 1757 | QEMU-validated | logic_interpreter_probe: text_attribute_enable_clears_visible_surface |
| `0x6b` | `disable_text_attr_mode_1757` | - | disable text attr mode 1757 | QEMU-validated | logic_interpreter_probe: text_attribute_disable_restores_picture_draw |
| `0x6c` | `set_input_prompt_char` | imm0 | set input prompt char | QEMU-validated | logic_interpreter_probe: input_prompt_empty_message_suppresses_marker |
| `0x6d` | `set_text_window_pair` | imm0, imm1 | set text window pair | QEMU-validated | logic_interpreter_probe: text_attribute_pair_changes_attr_mode_clear_color |
| `0x6e` | `shake_screen_like` | imm0 | shake screen like | source-backed | Disassembly: action reads a count byte and performs display-mode-specific screen shake; in the normal path it writes CRT controller registers 0x02/0x07 from a small offset table with timer-tick waits. QEMU dispatch smoke confirms return to following bytecode. |
| `0x6f` | `set_input_line_config` | imm0, imm1, imm2 | set input line config | QEMU-validated | logic_interpreter_probe: input_line_config_operand1_offsets_display_by_8 |
| `0x70` | `show_status_line_like` | - | show status line like | QEMU-validated | logic_interpreter_probe: status_line_show_draws_configured_row |
| `0x71` | `hide_status_line_like` | - | hide status line like | QEMU-validated | logic_interpreter_probe: status_line_hide_clears_configured_row |
| `0x72` | `set_string_slot_from_message` | imm0, imm1 | set string slot from message | QEMU-validated | logic_interpreter_probe: set_string_from_message_equal_normalized and parse_string_slot_sets_input_word_sequence |
| `0x73` | `prompt_string_to_slot` | imm0, imm1, imm2, imm3, imm4 | prompt string to slot | QEMU-validated | logic_interpreter_probe: prompt_string_to_slot_stores_typed_word |
| `0x74` | `set_string_slot_from_table` | imm0, imm1 | set string slot from table | QEMU-validated | logic_interpreter_probe: set_string_from_table_copies_patched_pointer |
| `0x75` | `parse_string_slot` | imm0 | parse string slot | QEMU-validated | logic_interpreter_probe: parse_string_slot_sets_input_word_sequence |
| `0x76` | `prompt_number_to_var` | imm0, var1 | prompt number to var | QEMU-validated | logic_interpreter_probe: prompt_number_to_var_accepts_digits |
| `0x77` | `disable_input_line_like` | - | disable input line like | QEMU-validated | logic_interpreter_probe: input_line_disable_clears_configured_row |
| `0x78` | `enable_input_line_like` | - | enable input line like | QEMU-validated | logic_interpreter_probe: input_line_enable_clears_configured_row |
| `0x79` | `map_key_event` | imm0, imm1, imm2 | map key event | QEMU-validated | logic_interpreter_probe: mapped_key_sets_status_byte |
| `0x7a` | `setup_transient_object` | imm0, imm1, imm2, imm3, imm4, imm5, imm6 | setup transient object | QEMU-validated | logic_interpreter_probe and object_overlay_probe transient drawing |
| `0x7b` | `setup_transient_object_var` | var0, var1, var2, var3, var4, var5, var6 | setup transient object var | QEMU-validated | logic_interpreter_probe: setup_transient_object_var_draws_selected_cel |
| `0x7c` | `show_inventory_selection` | - | show inventory selection | QEMU-validated | logic_interpreter_probe: inventory_selection_enter_sets_var19, inventory_selection_escape_sets_var19_ff, and inventory_selection_noninteractive_ack_returns |
| `0x7d` | `save_game_state` | - | save game state | QEMU-validated | logic_interpreter_probe: save_game_escape_continues_to_draw |
| `0x7e` | `restore_game_state` | - | restore game state | QEMU-validated | logic_interpreter_probe: restore_game_escape_continues_to_draw |
| `0x7f` | `noop` | - | noop | QEMU-validated | logic_interpreter_probe: noop_7f_continues_to_draw |
| `0x80` | `confirm_restart_game` | - | confirm restart game | QEMU-validated | logic_interpreter_probe: restart_confirm_escape_continues_to_draw |
| `0x81` | `display_view_resource_text_like` | imm0 | display view resource text like | QEMU-validated | logic_interpreter_probe: view_resource_display_immediate_returns |
| `0x82` | `random_range_to_var` | imm0, imm1, var2 | random range to var | QEMU-validated | logic_interpreter_probe: random_equal_bounds_stores_bound |
| `0x83` | `clear_global_0139` | - | clear global 0139 | source-backed | Disassembly: action clears [0x0139]; code.engine.main_cycle uses that selector before logic to choose object0->global direction mirroring, then restores object0 direction from global after logic. |
| `0x84` | `set_global_0139_and_clear_object0_field_22` | - | set global 0139 and clear object0 field 22 | QEMU-validated | object_movement_probe: action_84_after_random_motion_stops_motion |
| `0x85` | `display_object_diagnostics_var` | var0 | display object diagnostics var | QEMU-validated | logic_interpreter_probe: object_diagnostics_var_enter_returns |
| `0x86` | `confirm_and_restart_like` | imm0 | confirm and restart like | QEMU-validated | logic_interpreter_probe: confirm_restart_like_escape_continues_to_draw |
| `0x87` | `show_heap_status` | - | show heap status | QEMU-validated | logic_interpreter_probe: heap_status_then_ack_continues_to_draw |
| `0x88` | `pause_game_message` | - | pause game message | QEMU-validated | logic_interpreter_probe: pause_message_then_ack_continues_to_draw |
| `0x89` | `refresh_input_line` | - | refresh input line | QEMU-validated | logic_interpreter_probe: input_line_refresh_repaints_entered_buffer |
| `0x8a` | `erase_input_line` | - | erase input line | QEMU-validated | logic_interpreter_probe: input_line_erase_clears_typed_buffer |
| `0x8b` | `calibrate_joystick` | - | calibrate joystick | QEMU-validated | logic_interpreter_probe: joystick_calibration_no_joystick_returns |
| `0x8c` | `toggle_display_mode_bit` | - | toggle display mode bit | QEMU-validated | logic_interpreter_probe: display_mode_toggle_guarded_noop_continues |
| `0x8d` | `show_interpreter_version` | - | show interpreter version | QEMU-validated | logic_interpreter_probe: interpreter_version_then_ack_continues_to_draw |
| `0x8e` | `set_global_0141_and_refresh` | imm0 | set global 0141 and refresh | source-backed | Disassembly: action writes data.event.pair_capacity and calls code.event.reset_pair_buffer inside update-list flush/rebuild helpers; reset allocates capacity*2 bytes on first use and clears pair count/write cursor. |
| `0x8f` | `verify_game_signature` | imm0 | verify game signature | QEMU-validated | logic_interpreter_probe: signature_check_matching_message_returns |
| `0x90` | `append_message_to_log_file` | imm0 | append message to log file | QEMU-validated | logic_interpreter_probe: log_file_append_dispatch_smoke plus extracted LOGFILE content |
| `0x91` | `save_logic_resume_ip` | - | save logic resume ip | QEMU-validated | logic_interpreter_probe: save_restore_resume_actions_continue_to_draw |
| `0x92` | `restore_logic_entry_ip` | - | restore logic entry ip | QEMU-validated | logic_interpreter_probe: save_restore_resume_actions_continue_to_draw |
| `0x93` | `set_object_pos_dirty` | imm0, imm1, imm2 | set object pos dirty | QEMU-validated | logic_interpreter_probe: set_object_pos_dirty_getter_observes_values |
| `0x94` | `set_object_pos_dirty_var` | imm0, var1, var2 | set object pos dirty var | QEMU-validated | logic_interpreter_probe: set_object_pos_dirty_var_getter_observes_values |
| `0x95` | `enable_action_trace_window` | - | enable action trace window | QEMU-validated | logic_interpreter_probe: trace_window_enable_draws_box_when_flag10_set |
| `0x96` | `configure_action_trace_window` | imm0, imm1, imm2 | configure action trace window | QEMU-validated | logic_interpreter_probe: trace_window_enable_draws_box_when_flag10_set |
| `0x97` | `display_message_configured` | imm0, imm1, imm2, imm3 | display message configured | QEMU-validated | logic_interpreter_probe: display_message_configured_then_ack_continues_to_draw |
| `0x98` | `display_message_configured_var` | var0, imm1, imm2, imm3 | display message configured var | QEMU-validated | logic_interpreter_probe: display_message_configured_var_then_ack_continues_to_draw |
| `0x99` | `discard_view_var` | var0 | discard view var | QEMU-validated | logic_interpreter_probe: discard_view_var_allows_reload_and_draw |
| `0x9a` | `clear_text_rect_bounds` | imm0, imm1, imm2, imm3, imm4 | clear text rect bounds | QEMU-validated | logic_interpreter_probe: text_rect_clear_bounds_removes_formatted_text |
| `0x9b` | `noop_2` | imm0, imm1 | noop 2 | QEMU-validated | logic_interpreter_probe: noop_9b_consumes_two_operands_then_draws |
| `0x9c` | `add_menu_heading_like` | imm0 | add menu heading like | QEMU-validated | logic_interpreter_probe: menu_interactive/menu_edges setup cases |
| `0x9d` | `add_menu_item_like` | imm0, imm1 | add menu item like | QEMU-validated | logic_interpreter_probe: menu_interactive/menu_edges setup cases |
| `0x9e` | `finalize_menu_like` | - | finalize menu like | QEMU-validated | logic_interpreter_probe: menu_interactive/menu_edges setup cases |
| `0x9f` | `enable_menu_item_like` | imm0 | enable menu item like | QEMU-validated | logic_interpreter_probe: menu_enable_after_disable_allows_enter_status_byte |
| `0xa0` | `disable_menu_item_like` | imm0 | disable menu item like | QEMU-validated | logic_interpreter_probe: menu_disabled_item_enter_does_not_set_status_byte and menu_enable_after_disable_allows_enter_status_byte |
| `0xa1` | `mark_menu_if_flag_0e` | - | mark menu if flag 0e | QEMU-validated | logic_interpreter_probe: menu_interactive_enter_sets_status_byte and menu_edges_002 |
| `0xa2` | `display_view_resource_text_like_var` | imm0 | display view resource text like var | QEMU-validated | logic_interpreter_probe: view_resource_display_var_returns |
| `0xa3` | `set_global_0d0f` | - | set global 0d0f | QEMU-validated | logic_interpreter_probe: input_width_flag_a3_allows_long_live_input |
| `0xa4` | `clear_global_0d0f` | - | clear global 0d0f | QEMU-validated | logic_interpreter_probe: input_width_flag_a4_restores_long_slot_limit |
| `0xa5` | `muln` | var0, imm1 | muln | QEMU-validated | logic_interpreter_probe: muln_keeps_low_product_byte |
| `0xa6` | `mulv` | var0, var1 | mulv | QEMU-validated | logic_interpreter_probe: mulv_keeps_low_product_byte |
| `0xa7` | `divn` | var0, imm1 | divn | QEMU-validated | logic_interpreter_probe: divn_stores_quotient_byte |
| `0xa8` | `divv` | var0, var1 | divv | QEMU-validated | logic_interpreter_probe: divv_stores_quotient_byte |
| `0xa9` | `close_text_window_state` | - | close text window state | QEMU-validated | logic_interpreter_probe: close_text_window_state_clears_input_width_flag |
| `0xaa` | `copy_save_description_to_string_slot` | imm0 | copy save description to string slot | source-backed | Disassembly: action copies up to 0x1f bytes from runtime save-description buffer [0x0e72] into string slot 0x020d + arg0*0x28 via the shared bounded-copy helper. |
| `0xab` | `save_event_buffer_count` | - | save event buffer count | QEMU-validated | logic_interpreter_probe: display_mode_replay_uses_rolled_back_event_count |
| `0xac` | `restore_event_buffer_count` | - | restore event buffer count | QEMU-validated | logic_interpreter_probe: display_mode_replay_uses_rolled_back_event_count |
| `0xad` | `increment_global_1530` | - | increment global 1530 | source-backed | Disassembly: action increments [0x1530]; the keyboard IRQ hook tests this nonzero gate before enqueueing a type-2 zero event on selected tracked-key release paths. |
| `0xae` | `rebuild_priority_table_from_y` | imm0 | rebuild priority table from y | QEMU-validated | object_overlay_probe: priority-table rebuild effects |
| `0xaf` | `noop_1_table_count` | imm0 | noop 1 table count | QEMU-validated | logic_interpreter_probe: noop_af_runtime_consumes_no_operand |

## Condition Opcodes

| Opcode | Label | Operand shape | Behavior summary | Evidence level | Probe/evidence |
| ---: | --- | --- | --- | --- | --- |
| `0x00` | `always_false` | - | always false | QEMU-validated | logic_interpreter_probe: always_false_condition_skips_then_draw |
| `0x01` | `var_eq_imm` | var0, imm1 | var eq imm | QEMU-validated | logic_interpreter_probe: if_false_skips_then_draw and state probes |
| `0x02` | `var_eq_var` | var0, var1 | var eq var | QEMU-validated | logic_interpreter_probe: var_comparison_conditions_all_true |
| `0x03` | `var_lt_imm` | var0, imm1 | var lt imm | QEMU-validated | logic_interpreter_probe: var_comparison_conditions_all_true |
| `0x04` | `var_lt_var` | var0, var1 | var lt var | QEMU-validated | logic_interpreter_probe: var_comparison_conditions_all_true |
| `0x05` | `var_gt_imm` | var0, imm1 | var gt imm | QEMU-validated | logic_interpreter_probe: var_comparison_conditions_all_true |
| `0x06` | `var_gt_var` | var0, var1 | var gt var | QEMU-validated | logic_interpreter_probe: var_comparison_conditions_all_true |
| `0x07` | `flag_set` | imm0 | flag set | QEMU-validated | logic_interpreter_probe: flag_set_clear_toggle_actions and OR-group probe |
| `0x08` | `flag_set_var` | var0 | flag set var | QEMU-validated | logic_interpreter_probe: flag_var_actions_and_condition |
| `0x09` | `obj_table_room_ff` | imm0 | obj table room ff | QEMU-validated | logic_interpreter_probe: inventory_marker_ff_condition_true |
| `0x0a` | `obj_table_room_eq_var` | imm0, var1 | obj table room eq var | QEMU-validated | logic_interpreter_probe: inventory_marker_eq_var_condition_true |
| `0x0b` | `object_left_baseline_in_rect` | imm0, imm1, imm2, imm3, imm4 | object left baseline in rect | QEMU-validated | logic_interpreter_probe: object_left_rect_condition_true |
| `0x0c` | `status_byte_1218` | imm0 | status byte 1218 | QEMU-validated | logic_interpreter_probe: mapped_key_sets_status_byte |
| `0x0d` | `raw_key_event_available` | - | raw key event available | QEMU-validated | logic_interpreter_probe: raw_key_event_available_draws_after_typed_key |
| `0x0e` | `input_word_sequence` | varlen word sequence | input word sequence | QEMU-validated | logic_interpreter_probe: parse_string_slot_sets_input_word_sequence, parser_edges_001, and parser_unknown_terminator_001 |
| `0x0f` | `string_slots_equal_normalized` | imm0, imm1 | string slots equal normalized | QEMU-validated | logic_interpreter_probe: set_string_from_message_equal_normalized |
| `0x10` | `object_width_baseline_in_rect` | imm0, imm1, imm2, imm3, imm4 | object width baseline in rect | QEMU-validated | logic_interpreter_probe: object_width_rect_condition_true |
| `0x11` | `object_center_baseline_in_rect` | imm0, imm1, imm2, imm3, imm4 | object center baseline in rect | QEMU-validated | logic_interpreter_probe: object_center_rect_condition_true |
| `0x12` | `object_right_baseline_in_rect` | imm0, imm1, imm2, imm3, imm4 | object right baseline in rect | QEMU-validated | logic_interpreter_probe: object_right_rect_condition_true |
