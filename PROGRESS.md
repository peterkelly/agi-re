# Reverse Engineering Progress

This is the high-level completion tracker for the clean-room AGI/SQ2 reverse
engineering project. It is intentionally more compact than the mdBook evidence
chapters: use it to see what is done, what is partial, and what still needs
work.

Update this file whenever an opcode changes status, a major engine subsystem is
better understood, or a new remaining-work item is discovered.

## Legend

- `[x]` Covered well enough for the current spec target. The behavior is either
  QEMU-validated or structurally source-backed and documented.
- `[~]` Partially covered. The behavior is source-backed, QEMU dispatch-smoked,
  or validated only for selected cases; more specification or compatibility
  testing is still useful.
- `[ ]` Not yet covered in useful detail.

## Current Snapshot

- Logic action opcodes: 162 of 176 are covered at `[x]` level
  (`161` QEMU-validated plus `0x00` structural); 14 remain `[~]`.
- Logic condition opcodes: all 19 of 19 are QEMU-validated.
- Main remaining risk areas: full picture/view renderer edge behavior, text and
  input UI details, sound/audio semantics, final compatibility suite breadth,
  and turning the accumulated notes into implementation-ready subsystem specs.

## Logic Structural Bytes

- [x] `0x00` `end` - terminates the current logic stream before action
  dispatch.
- [x] `0xfe` `jump` - unconditional relative jump in the main stream.
- [x] `0xff` `if` - condition block marker in the main stream.
- [x] `0xfc` `OR_MARK` - OR-group marker inside a condition list.
- [x] `0xfd` `NOT_NEXT` - inverts the next predicate inside a condition list.
- [x] `0xff` `condition_terminator` - ends a condition list and precedes the
  false-path delta.
- [x] `0xb0..0xfb` `invalid_action_range` - outside the SQ2 action opcode
  catalog.
- [x] `0x13..0xfb` `invalid_condition_range` - outside the SQ2 predicate
  opcode catalog, except structural condition bytes `0xfc`, `0xfd`, and `0xff`.

## Logic Action Opcodes

- [x] `0x00` `end` - source-backed structural
- [x] `0x01` `inc_var` - QEMU-validated
- [x] `0x02` `dec_var` - QEMU-validated
- [x] `0x03` `assignn` - QEMU-validated
- [x] `0x04` `assignv` - QEMU-validated
- [x] `0x05` `addn` - QEMU-validated
- [x] `0x06` `addv` - QEMU-validated
- [x] `0x07` `subn` - QEMU-validated
- [x] `0x08` `subv` - QEMU-validated
- [x] `0x09` `indirect_assignv` - QEMU-validated
- [x] `0x0a` `assign_indirectv` - QEMU-validated
- [x] `0x0b` `indirect_assignn` - QEMU-validated
- [x] `0x0c` `set_flag` - QEMU-validated
- [x] `0x0d` `clear_flag` - QEMU-validated
- [x] `0x0e` `toggle_flag` - QEMU-validated
- [x] `0x0f` `set_flag_var` - QEMU-validated
- [x] `0x10` `clear_flag_var` - QEMU-validated
- [x] `0x11` `toggle_flag_var` - QEMU-validated
- [x] `0x12` `switch_room_like` - QEMU-validated
- [x] `0x13` `switch_room_like_var` - QEMU-validated
- [x] `0x14` `load_logic` - QEMU-validated
- [x] `0x15` `load_logic_var` - QEMU-validated
- [x] `0x16` `call_logic` - QEMU-validated
- [x] `0x17` `call_logic_var` - QEMU-validated
- [x] `0x18` `load_picture_var` - QEMU-validated
- [x] `0x19` `prepare_picture_var` - QEMU-validated
- [x] `0x1a` `show_picture_like` - QEMU-validated
- [x] `0x1b` `discard_picture_var` - QEMU-validated
- [x] `0x1c` `overlay_picture_var` - QEMU-validated
- [x] `0x1d` `show_priority_screen` - QEMU-validated
- [x] `0x1e` `load_view` - QEMU-validated
- [x] `0x1f` `load_view_var` - QEMU-validated
- [x] `0x20` `discard_view` - QEMU-validated
- [x] `0x21` `reset_object_state` - QEMU-validated
- [x] `0x22` `clear_all_object_bits` - QEMU-validated
- [x] `0x23` `activate_object` - QEMU-validated
- [x] `0x24` `deactivate_object` - QEMU-validated
- [x] `0x25` `set_object_pos` - QEMU-validated
- [x] `0x26` `set_object_pos_var` - QEMU-validated
- [x] `0x27` `get_object_pos` - QEMU-validated
- [x] `0x28` `add_object_pos_from_vars` - QEMU-validated
- [x] `0x29` `set_object_resource` - QEMU-validated
- [x] `0x2a` `set_object_resource_var` - QEMU-validated
- [x] `0x2b` `set_object_subresource` - QEMU-validated
- [x] `0x2c` `set_object_subresource_var` - QEMU-validated
- [x] `0x2d` `set_object_bit_2000` - QEMU-validated
- [x] `0x2e` `clear_object_bit_2000` - QEMU-validated
- [x] `0x2f` `set_object_derived_resource_2` - QEMU-validated
- [x] `0x30` `set_object_derived_resource_2_var` - QEMU-validated
- [x] `0x31` `get_object_resource_loop_count` - QEMU-validated
- [x] `0x32` `get_object_field_0e` - QEMU-validated
- [x] `0x33` `get_object_field_0a` - QEMU-validated
- [x] `0x34` `get_object_field_07` - QEMU-validated
- [x] `0x35` `get_object_field_0b` - QEMU-validated
- [x] `0x36` `set_object_field_24` - QEMU-validated
- [x] `0x37` `set_object_field_24_var` - QEMU-validated
- [x] `0x38` `clear_object_bit_0004` - QEMU-validated
- [x] `0x39` `get_object_field_24` - QEMU-validated
- [x] `0x3a` `clear_object_bit_0010` - QEMU-validated
- [x] `0x3b` `set_object_bit_0010` - QEMU-validated
- [x] `0x3c` `refresh_object_lists` - QEMU-validated
- [x] `0x3d` `set_object_bit_0008` - QEMU-validated
- [x] `0x3e` `clear_object_bit_0008` - QEMU-validated
- [x] `0x3f` `set_global_012d` - QEMU-validated
- [x] `0x40` `set_object_bit_0100` - QEMU-validated
- [x] `0x41` `set_object_bit_0800` - QEMU-validated
- [x] `0x42` `clear_object_bits_0900` - QEMU-validated
- [x] `0x43` `set_object_bit_0200` - QEMU-validated
- [x] `0x44` `clear_object_bit_0200` - QEMU-validated
- [x] `0x45` `object_distance_to_var` - QEMU-validated
- [x] `0x46` `clear_object_bit_0020` - QEMU-validated
- [x] `0x47` `set_object_bit_0020` - QEMU-validated
- [x] `0x48` `set_object_field_23_mode0` - QEMU-validated
- [x] `0x49` `set_object_field_23_mode1` - QEMU-validated
- [x] `0x4a` `set_object_field_23_mode3` - QEMU-validated
- [x] `0x4b` `set_object_field_23_mode2` - QEMU-validated
- [x] `0x4c` `set_object_field_1f_var` - QEMU-validated
- [x] `0x4d` `clear_object_fields_21_22` - QEMU-validated
- [x] `0x4e` `clear_object_field_22_and_global` - QEMU-validated
- [x] `0x4f` `set_object_field_1e_var` - QEMU-validated
- [x] `0x50` `set_object_field_01_var` - QEMU-validated
- [x] `0x51` `move_object_to` - QEMU-validated
- [x] `0x52` `move_object_to_var` - QEMU-validated
- [x] `0x53` `approach_first_object_until_near` - QEMU-validated
- [x] `0x54` `start_random_motion` - QEMU-validated
- [x] `0x55` `stop_motion_mode` - QEMU-validated
- [x] `0x56` `set_object_field_21_var` - QEMU-validated
- [x] `0x57` `get_object_field_21` - QEMU-validated
- [x] `0x58` `set_object_bit_0002` - QEMU-validated
- [x] `0x59` `clear_object_bit_0002` - QEMU-validated
- [x] `0x5a` `set_rect_bounds_0131` - QEMU-validated
- [x] `0x5b` `clear_rect_bounds_0131` - QEMU-validated
- [x] `0x5c` `set_entry_0971_marker_ff` - QEMU-validated
- [x] `0x5d` `set_entry_0971_marker_ff_var` - QEMU-validated
- [x] `0x5e` `clear_entry_0971_marker` - QEMU-validated
- [x] `0x5f` `set_entry_0971_marker_from_var` - QEMU-validated
- [x] `0x60` `set_entry_0971_marker_from_var_var` - QEMU-validated
- [x] `0x61` `get_entry_0971_marker_to_var` - QEMU-validated
- [x] `0x62` `load_sound` - QEMU-validated
- [x] `0x63` `start_sound_with_flag` - QEMU-validated
- [x] `0x64` `stop_sound_or_clear_sound_state` - QEMU-validated
- [x] `0x65` `display_message` - QEMU-validated
- [x] `0x66` `display_message_var` - QEMU-validated
- [x] `0x67` `display_formatted_message` - QEMU-validated
- [x] `0x68` `display_formatted_message_var` - QEMU-validated
- [x] `0x69` `clear_text_rect` - QEMU-validated
- [x] `0x6a` `enable_text_attr_mode_1757` - QEMU-validated
- [x] `0x6b` `disable_text_attr_mode_1757` - QEMU-validated
- [x] `0x6c` `set_input_prompt_char` - QEMU-validated
- [~] `0x6d` `set_text_window_pair` - QEMU dispatch-smoke
- [~] `0x6e` `shake_screen_like` - QEMU dispatch-smoke
- [x] `0x6f` `set_input_line_config` - QEMU-validated
- [~] `0x70` `show_status_line_like` - QEMU dispatch-smoke
- [x] `0x71` `hide_status_line_like` - QEMU-validated
- [x] `0x72` `set_string_slot_from_message` - QEMU-validated
- [x] `0x73` `prompt_string_to_slot` - QEMU-validated
- [x] `0x74` `set_string_slot_from_table` - QEMU-validated
- [x] `0x75` `parse_string_slot` - QEMU-validated
- [x] `0x76` `prompt_number_to_var` - QEMU-validated
- [x] `0x77` `disable_input_line_like` - QEMU-validated
- [x] `0x78` `enable_input_line_like` - QEMU-validated
- [x] `0x79` `map_key_event` - QEMU-validated
- [x] `0x7a` `setup_transient_object` - QEMU-validated
- [x] `0x7b` `setup_transient_object_var` - QEMU-validated
- [x] `0x7c` `show_inventory_selection` - QEMU-validated
- [x] `0x7d` `save_game_state` - QEMU-validated
- [x] `0x7e` `restore_game_state` - QEMU-validated
- [x] `0x7f` `noop` - QEMU-validated
- [x] `0x80` `confirm_restart_game` - QEMU-validated
- [x] `0x81` `display_view_resource_text_like` - QEMU-validated
- [x] `0x82` `random_range_to_var` - QEMU-validated
- [~] `0x83` `clear_global_0139` - QEMU dispatch-smoke
- [x] `0x84` `set_global_0139_and_clear_object0_field_22` - QEMU-validated
- [x] `0x85` `display_object_diagnostics_var` - QEMU-validated
- [x] `0x86` `confirm_and_restart_like` - QEMU-validated
- [x] `0x87` `show_heap_status` - QEMU-validated
- [x] `0x88` `pause_game_message` - QEMU-validated
- [~] `0x89` `refresh_input_line` - QEMU dispatch-smoke
- [~] `0x8a` `erase_input_line` - QEMU dispatch-smoke
- [x] `0x8b` `calibrate_joystick` - QEMU-validated
- [x] `0x8c` `toggle_display_mode_bit` - QEMU-validated
- [x] `0x8d` `show_interpreter_version` - QEMU-validated
- [~] `0x8e` `set_global_0141_and_refresh` - QEMU dispatch-smoke
- [x] `0x8f` `verify_game_signature` - QEMU-validated
- [x] `0x90` `append_message_to_log_file` - QEMU-validated
- [x] `0x91` `save_logic_resume_ip` - QEMU-validated
- [x] `0x92` `restore_logic_entry_ip` - QEMU-validated
- [x] `0x93` `set_object_pos_dirty` - QEMU-validated
- [x] `0x94` `set_object_pos_dirty_var` - QEMU-validated
- [~] `0x95` `enable_action_trace_window` - QEMU dispatch-smoke
- [~] `0x96` `configure_action_trace_window` - QEMU dispatch-smoke
- [x] `0x97` `display_message_configured` - QEMU-validated
- [x] `0x98` `display_message_configured_var` - QEMU-validated
- [x] `0x99` `discard_view_var` - QEMU-validated
- [x] `0x9a` `clear_text_rect_bounds` - QEMU-validated
- [x] `0x9b` `noop_2` - QEMU-validated
- [x] `0x9c` `add_menu_heading_like` - QEMU-validated
- [x] `0x9d` `add_menu_item_like` - QEMU-validated
- [x] `0x9e` `finalize_menu_like` - QEMU-validated
- [x] `0x9f` `enable_menu_item_like` - QEMU-validated
- [x] `0xa0` `disable_menu_item_like` - QEMU-validated
- [x] `0xa1` `mark_menu_if_flag_0e` - QEMU-validated
- [x] `0xa2` `display_view_resource_text_like_var` - QEMU-validated
- [~] `0xa3` `set_global_0d0f` - QEMU dispatch-smoke
- [~] `0xa4` `clear_global_0d0f` - QEMU dispatch-smoke
- [x] `0xa5` `muln` - QEMU-validated
- [x] `0xa6` `mulv` - QEMU-validated
- [x] `0xa7` `divn` - QEMU-validated
- [x] `0xa8` `divv` - QEMU-validated
- [~] `0xa9` `close_text_window_state` - QEMU dispatch-smoke
- [~] `0xaa` `copy_save_description_to_string_slot` - QEMU dispatch-smoke
- [x] `0xab` `save_event_buffer_count` - QEMU-validated
- [x] `0xac` `restore_event_buffer_count` - QEMU-validated
- [~] `0xad` `increment_global_1530` - QEMU dispatch-smoke
- [x] `0xae` `rebuild_priority_table_from_y` - QEMU-validated
- [x] `0xaf` `noop_1_table_count` - QEMU-validated

## Logic Condition Opcodes

- [x] `0x00` `always_false` - QEMU-validated
- [x] `0x01` `var_eq_imm` - QEMU-validated
- [x] `0x02` `var_eq_var` - QEMU-validated
- [x] `0x03` `var_lt_imm` - QEMU-validated
- [x] `0x04` `var_lt_var` - QEMU-validated
- [x] `0x05` `var_gt_imm` - QEMU-validated
- [x] `0x06` `var_gt_var` - QEMU-validated
- [x] `0x07` `flag_set` - QEMU-validated
- [x] `0x08` `flag_set_var` - QEMU-validated
- [x] `0x09` `obj_table_room_ff` - QEMU-validated
- [x] `0x0a` `obj_table_room_eq_var` - QEMU-validated
- [x] `0x0b` `object_left_baseline_in_rect` - QEMU-validated
- [x] `0x0c` `status_byte_1218` - QEMU-validated
- [x] `0x0d` `raw_key_event_available` - QEMU-validated
- [x] `0x0e` `input_word_sequence` - QEMU-validated
- [x] `0x0f` `string_slots_equal_normalized` - QEMU-validated
- [x] `0x10` `object_width_baseline_in_rect` - QEMU-validated
- [x] `0x11` `object_center_baseline_in_rect` - QEMU-validated
- [x] `0x12` `object_right_baseline_in_rect` - QEMU-validated

## Engine Coverage Areas

- [x] Clean-room evidence trail and project rules
  - Evidence: `AGENTS.md`, `docs/src/clean_room_executable_notes.md`,
    `docs/src/progress_log.md`.
  - Remaining: keep updated continuously.
- [~] Executable and overlay symbolic map
  - Evidence: `docs/src/symbolic_labels.md`.
  - Remaining: continue assigning role-based labels for cross-version work.
- [~] Startup, command-line flags, adapter selection, and display modes
  - Evidence: startup parser, display-mode `0x8c`, CGA/EGA overlay notes.
  - Remaining: full EGA behavior is the target; non-EGA adapter behavior should
    be documented only where it explains observed SQ2 behavior.
- [~] Resource directories, volume records, and cache records
  - Evidence: local resource parsers, loader labels, room-switch cache reset.
  - Remaining: formalize allocation/failure behavior and cache record layout in
    implementation-ready text.
- [x] Logic resource format, messages, dispatch, and control flow
  - Evidence: logic resource docs, interpreter source pass, QEMU opcode probes.
  - Remaining: keep opcode tracker aligned with new findings.
- [~] Variables, flags, strings, parser words, and input buffers
  - Evidence: string/message/input probes and local parser notes.
  - Remaining: broaden parser/vocabulary edge cases and promote remaining
    visible input-line/text actions beyond dispatch-smoke.
- [~] Picture resource decoding and drawing
  - Evidence: picture decoder notes, Python renderer, fuzz corpus, QEMU
    comparison harness.
  - Remaining: finish edge-case semantics for valid EGA picture streams and
    expand comparison fixtures.
- [~] View resource decoding and cel drawing
  - Evidence: view layout notes, view/object snapshot batches, focused edge
    placement captures.
  - Remaining: broaden cel corpus coverage, mirroring/transparent-color edge
    cases, and formal implementation text.
- [~] Object records, priority/control screens, and drawing pipeline
  - Evidence: object overlay probes, priority/control bit probes, labels, and
    implementation-facing drawing lifecycle state machine.
  - Remaining: finish draw ordering, dirty-rectangle, and placement-search edge
    semantics.
- [~] Object movement, collision, animation, and boundary handling
  - Evidence: object movement QEMU batches, disassembly-backed scheduler, and
    implementation-facing motion state machine.
  - Remaining: add any missing edge probes for valid movement and collision
    behavior.
- [~] Room switching, restart, save/restore, and resource-event replay
  - Evidence: room-switch probes, save/restore source map, replay re-enable
    correction at `0x6927`, and rollback probe for `0xab`/`0xac`.
  - Remaining: deepen save-file path/selection semantics and restore/restart
    state transitions.
- [~] Text windows, status line, prompts, and interactive input
  - Evidence: message/string/numeric input probes, dispatch-smoke coverage, and
    implementation-facing UI lifecycle state machine.
  - Remaining: promote dispatch-smoke rows to behavior coverage where visible
    state matters.
- [~] Menus and inventory UI
  - Evidence: inventory selection, menu setup, disabled/enabled item probes.
  - Remaining: validate movement/navigation events with direct event injection
    or a more precise QEMU input path.
- [~] Sound and audio
  - Evidence: load/start/stop completion-flag behavior.
  - Remaining: actual sound resource format, playback timing, driver/hardware
    behavior, and completion semantics beyond current stop helper evidence.
- [~] DOS file I/O, logging, save descriptions, and path selection
  - Evidence: log-file QEMU content check and save/restore source map.
  - Remaining: save-description copy behavior, full selector/path behavior, and
    file error paths.
- [~] Memory, heap, allocation, and diagnostics
  - Evidence: heap helpers, reset paths, high-water diagnostics.
  - Remaining: formal allocator/free-list model and error semantics.
- [~] Compatibility test suite and harnesses
  - Evidence: `tests/`, `tools/logic_interpreter_probe.py`,
    `tools/object_movement_probe.py`, `tools/object_overlay_probe.py`,
    `tools/picture_fuzz.py`, QEMU snapshot support.
  - Remaining: assemble a final broad suite that can validate a clean-room
    implementation against original-engine outputs.
- [ ] Cross-version comparison workflow
  - Evidence: symbolic labels are being curated for SQ2.
  - Remaining: apply the labels and subsystem trackers to additional
    interpreter versions bundled with other games.
- [~] Final human-readable implementation spec
  - Evidence: mdBook chapters exist and are growing.
  - Remaining: convert source/evidence notes into polished, subsystem-oriented
    normative spec text.

## Highest-Value Remaining Work

1. Promote the remaining QEMU dispatch-smoke action opcodes to behavior-level
   coverage where they affect visible state, saved state, or input/UI state.
2. Deepen text/input UI semantics now that condition `0x0d` is validated:
   input-line enable/refresh/erase, prompt/status-line state, and menu
   navigation events are the most useful next targets.
3. Continue the picture/view renderer compatibility work with valid synthetic
   resources and original-engine captures.
4. Continue turning the remaining subsystem notes into implementation-ready
   state machines, especially text windows, save/file selection, sound, and
   heap/allocation.
5. Keep expanding the final compatibility suite as each subsystem solidifies.
