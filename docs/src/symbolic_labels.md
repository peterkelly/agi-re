# Symbolic Labels

This file records project-local symbolic names for interpreter routines, tables,
and globals. The names are intended to survive comparison with later interpreter
versions whose code may move to different offsets.

Addresses in this chapter are observations from the current Space Quest 2 build.
They are not part of the portable specification. When a later executable has a
matching routine at a different address, map that address to the same symbolic
label and note any behavioral differences in the evidence trail.

## Naming Rules

- `code.*` labels name executable routines or overlay entry points.
- `data.*` labels name runtime globals, data tables, or pointers.
- `table.*` labels name dispatch or lookup tables.
- `opcode.action.*` and `opcode.cond.*` labels name bytecode operations. The
  complete opcode catalog lives in the logic bytecode chapter and in
  `tools/disassemble_logic.py`.
- Prefer symbolic labels in prose once a label exists, followed by the SQ2
  address when useful for verification.
- Mark uncertain labels as provisional in the notes/evidence column rather than
  encoding uncertainty in the label itself.

Address columns use these meanings:

- `SQ2 image offset`: offset in `build/cleanroom/AGI.decrypted.exe`.
- `SQ2 data offset`: runtime `DS` offset in `SQ2/AGIDATA.OVL` unless otherwise
  noted.
- `SQ2 overlay offset`: near offset in the named overlay file.

## Core Logic Interpreter

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `code.engine.main_cycle` | image `0x0150` | Top-level interpreter cycle. Calls input/system helpers, mirrors object-0 direction/global direction state, runs pre-motion mode updates, invokes logic 0 through `code.logic.call_logic`, then runs `code.object.frame_timer_update` unless text-attribute mode byte `[0x1757]` is nonzero. |
| `code.logic.interpret_main` | image `0x293c` | Main logic bytecode loop. Reads opcodes from current logic bytecode and dispatches actions/conditions. |
| `code.logic.action_dispatch` | image `0x02c4` | Action dispatcher. Uses `table.logic.action_dispatch`. |
| `code.logic.condition_dispatch` | image `0x07e3` | Condition dispatcher. Uses `table.logic.condition_dispatch`. |
| `table.logic.action_dispatch` | data `0x061d` | Four-byte action table entries for opcodes `0x00..0xaf`. |
| `table.logic.condition_dispatch` | data `0x08fd` | Four-byte condition table entries for opcodes `0x00..0x12` in this build. |
| `code.logic.message_xor_range` | image `0x07ab` | XORs logic message text in place. |
| `data.logic.message_xor_key` | data `0x08f1` | Zero-terminated XOR key bytes, observed as `Avis Durgan`. |
| `code.logic.resolve_message` | image `0x21f0` | Resolves a current-logic message number through the message pointer table. |
| `code.logic.load_cached` | image `0x117d` | Loads a logic resource and keeps it linked in the logic cache. |
| `code.logic.load_resource` | image `0x119a` | Reads, initializes, and message-decodes a logic resource. |
| `code.logic.call_logic` | image `0x12ae` | Temporarily switches current logic, runs `code.logic.interpret_main`, and may unlink a transient record. |

## Resources and DOS Files

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `code.resource.load_all_directories` | image `0x4305` | Loads `LOGDIR`, `VIEWDIR`, `PICDIR`, and `SNDDIR`. |
| `code.resource.read_volume_payload_retry` | image `0x2e32` | Retries the generic volume reader until it returns data or reports failure. |
| `code.resource.read_volume_payload_once` | image `0x2e56` | Reads one resource payload from a volume file using a directory entry. |
| `code.resource.logic_dir_entry` | image `0x4371` | Resolves logic directory entries from `data.resource.logic_dir`. |
| `code.resource.view_dir_entry` | image `0x43a5` | Resolves view-like directory entries from `data.resource.view_dir`. |
| `code.resource.picture_dir_entry` | image `0x43d9` | Resolves picture-like directory entries from `data.resource.picture_dir`. |
| `code.resource.sound_dir_entry` | image `0x440d` | Resolves sound-like directory entries from `data.resource.sound_dir`. |
| `code.dos.create_file` | image `0x5cad` | DOS file wrapper used by save/log paths. |
| `code.dos.open_file` | image `0x5cce` | DOS open wrapper. |
| `code.dos.close_file` | image `0x5d52` | DOS close wrapper. |
| `code.dos.delete_file` | image `0x5d6b` | DOS delete wrapper. |
| `code.dos.write_file` | image `0x5db2` | DOS write wrapper. |
| `code.dos.read_file` | image `0x5e01` | DOS read wrapper. |
| `code.dos.seek_file` | image `0x5e3e` | DOS seek wrapper. |

## Pictures and Display

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `code.picture.load_resource` | image `0x4a3b` | Loads/caches a picture-like payload. |
| `code.picture.prepare` | image `0x4acf` | Selects cached picture payload and prepares decode state. |
| `code.picture.overlay_prepare` | image `0x4b3b` | Overlay picture path used before decoder entry `code.picture.decode_no_clear`. |
| `code.picture.discard` | image `0x4bce` | Releases or unlinks a picture-like cache entry. |
| `code.picture.decode_with_clear` | image `0x6445` | Fills logical buffer, then falls into picture command decoding. |
| `code.picture.decode_no_clear` | image `0x6440` | Decodes picture commands without the extra clear/fill entry work. |
| `code.picture.command_scan` | image `0x6475` | Walks picture command bytes from `data.picture.current_payload`. |
| `table.picture.command_dispatch` | data `0x15d6` | Dispatch table for picture command bytes `0xf0..0xfa`. |
| `code.picture.cmd_set_visual_draw_nibble` | image `0x6494` | Picture command `0xf0`; enables low-nibble drawing state. |
| `code.picture.cmd_disable_visual_draw_nibble` | image `0x64b5` | Picture command `0xf1`; disables low-nibble drawing state. |
| `code.picture.cmd_set_control_draw_nibble` | image `0x64c7` | Picture command `0xf2`; enables high-nibble control drawing state. |
| `code.picture.cmd_disable_control_draw_nibble` | image `0x64ed` | Picture command `0xf3`; disables high-nibble control drawing state. |
| `code.picture.cmd_draw_corner_path_y_first` | image `0x6612` | Picture command `0xf4`; draws alternating vertical/horizontal corner paths. |
| `code.picture.cmd_draw_corner_path_x_first` | image `0x6603` | Picture command `0xf5`; draws alternating horizontal/vertical corner paths. |
| `code.picture.cmd_draw_absolute_lines` | image `0x6646` | Picture command `0xf6`; draws point-to-point absolute lines. |
| `code.picture.cmd_draw_relative_lines` | image `0x665e` | Picture command `0xf7`; draws relative vector steps. |
| `code.picture.cmd_seed_fill` | image `0x66ab` | Picture command `0xf8`; seed-fill entry. |
| `code.picture.cmd_set_pattern_mode` | image `0x6524` | Picture command `0xf9`; stores pattern mode byte. |
| `code.picture.cmd_pattern_plot` | image `0x64ff` | Picture command `0xfa`; patterned plot/fill-family command. |
| `code.picture.read_coord_pair` | image `0x66b8` | Reads clamped X/Y coordinate pair for picture commands. |
| `code.picture.draw_line` | image `0x66e1` | Draws a line between current and target picture coordinates. |
| `code.picture.seed_fill` | image `0x533b` | Expands from a seed coordinate through matching buffer nibbles. |
| `code.display.clear_logical_buffer` | image `0x5528` | Clears the logical graphics/control buffer. |
| `code.display.full_refresh` | image `0x5546` | Copies/rebuilds the visible display from logical buffers. |
| `code.display.fill_buffer_word` | image `0x5257` | Fills the logical buffer segment with a caller-supplied word. |
| `code.display.draw_horizontal_line` | image `0x526f` | Draws a horizontal line in the logical buffer using active picture draw state. |
| `code.display.draw_vertical_line` | image `0x52ab` | Draws a vertical line in the logical buffer using active picture draw state. |
| `code.display.pixel_write` | image `0x52f9` | Writes pixel/control nibbles into the logical buffer. |

## Objects, Views, and Motion

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `code.view.load_resource` | image `0x39f7` | Loads/caches a view-like payload. |
| `code.object.bind_view` | image `0x3ae7` | Binds a cached view payload to an object record. |
| `code.object.select_group` | image `0x3bb7` | Selects a top-level view subresource/group. |
| `code.object.select_group_table` | image `0x3c1b` | Computes a group table pointer from the view payload. |
| `code.object.select_frame` | image `0x3ccb` | Selects a derived frame/entry and updates object size/pointers. |
| `code.object.place` | image `0x593a` | Places an object and performs priority/control collision adjustment. |
| `code.object.control_acceptance` | image `0x56b8` | Tests an object's proposed footprint against high-nibble control/priority classes in `data.display.logical_buffer_segment`; QEMU probes validate selected `0x0002`, `0x0100`, and `0x0800` flag effects. |
| `code.object.frame_timer_update` | image `0x0563` | Per-cycle active-object scan that decrements frame timer byte `+0x20`, calls `code.object.advance_frame_by_mode` at zero, and reloads `+0x20` from `+0x1f`. |
| `code.object.advance_frame_by_mode` | image `0x48b3` | Dispatches object frame mode byte `+0x23`; modes loop or stop frames and may set completion flag byte `+0x27`. |
| `data.object.group_for_direction_two_or_three_groups` | data `0x08dd` | Direction-to-group table used by `code.object.frame_timer_update` when object byte `+0x0b` is 2 or 3 and bit `0x2000` is clear. |
| `data.object.group_for_direction_four_plus_groups` | data `0x08e7` | Direction-to-group table used by `code.object.frame_timer_update` when object byte `+0x0b` is at least 4 and bit `0x2000` is clear. |
| `code.object.build_active_update_list` | image `0x6a26` | Builds update-list root `0x16ff` using callback `code.object.accept_active_root_16ff`. |
| `code.object.build_inactive_partition_list` | image `0x6a3d` | Builds update-list root `0x1703` using callback `code.object.accept_root_1703`. |
| `code.object.flush_update_lists_restore` | image `0x6a54` | Flushes roots `0x16ff` and `0x1703` through helper `0x0307`, restoring saved backing rectangles and freeing nodes. |
| `code.object.rebuild_draw_update_lists` | image `0x6a8e` | Rebuilds/draws root `0x1703`, then rebuilds/draws root `0x16ff`. |
| `code.object.refresh_update_lists` | image `0x6aab` | Runs dirty-rectangle/saved-position refresh helper `0x0488` over root `0x1703`, then root `0x16ff`. |
| `code.object.clear_root_16ff_membership` | image `0x6b44` | Clears object bit `0x0010` when set, moving an active object from root `0x16ff` eligibility to root `0x1703` eligibility after a flush/rebuild. |
| `code.object.set_root_16ff_membership` | image `0x6b62` | Sets object bit `0x0010` when clear, moving an active object from root `0x1703` eligibility to root `0x16ff` eligibility after a flush/rebuild. |
| `code.object.update_dirty_rect` | image `0x5762` | Refreshes object dirty-rectangle state. |
| `code.object.save_rect_overlay_entry` | overlay `IBM_OBJS.OVL:0x9db0` | Entry jump to rectangle save routine. |
| `code.object.restore_rect_overlay_entry` | overlay `IBM_OBJS.OVL:0x9db3` | Entry jump to rectangle restore routine. |
| `code.object.draw_overlay_entry` | overlay `IBM_OBJS.OVL:0x9db6` | Entry jump to selected-frame drawing routine. |
| `code.object.rewrite_frame_orientation` | image `0x587d` | Rewrites bit-`0x80` frame data when cached orientation bits differ from object `+0x0a`. |
| `code.motion.update_objects` | image `0x150a` | Per-cycle object movement/update pass. |
| `code.motion.pre_mode_and_boundary_update` | image `0x0644` | Scans active objects with countdown byte `+0x01 == 1`, dispatches mode byte `+0x22`, then applies rectangle-boundary helper `code.motion.rectangle_boundary_check` when enabled. |
| `code.motion.rectangle_boundary_check` | image `0x06d9` | Compares current and next baseline points against script rectangle globals `[0x0131..0x013d]`, setting bit `0x0080` and clearing direction on crossing when bit `0x0002` is clear. |
| `code.motion.dispatch_mode_step` | image `0x067a` | Dispatches object mode byte `+0x22` to random, approach-first-object, or target-direction helpers when countdown byte `+0x01` is ready. |
| `code.motion.start_target_direction` | image `0x1672` | Computes initial direction toward object target fields. |
| `code.motion.compute_direction` | image `0x16ed` | Direction lookup from current and target coordinates. |
| `code.motion.complete_target_motion` | image `0x16b9` | Restores step state, sets completion flag, clears target mode. |
| `code.motion.random_mode_step` | image `0x3f5a` | Per-cycle random-motion mode handler. |
| `code.motion.random_direction` | image `0x3fa3` | Picks a random direction-like byte. |
| `code.motion.approach_first_object_step` | image `0x0b36` | Per-cycle approach-first-object mode handler. |

## Text, Input, and Save State

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `code.text.display_string` | image `0x1ce8` | Displays a resolved string and returns an interaction result in some paths. |
| `code.text.close_window_state` | image `0x1f2b` | Restores/clears active text-window state. |
| `code.text.format_string` | image `0x2374` | Formats text into caller-provided buffers. |
| `code.text.format_message_to_buffer` | image `0x1f54` | Formats/copies a resolved logic message into a stack buffer. |
| `code.text.redraw_status_line` | image `0x34bd` | Redraws the status-line-like area when `data.text.status_line_enabled` is nonzero, using the current text attribute globals and the status row global. |
| `code.text.show_status_line` | image `0x3547` | Action handler for `0x70`; sets `data.text.status_line_enabled` and calls `code.text.redraw_status_line`. |
| `code.text.hide_status_line` | image `0x355c` | Action handler for `0x71`; clears `data.text.status_line_enabled` and clears the configured status row. |
| `code.text.set_attribute_pair` | image `0x77d5` | Shared helper for action `0x6d` and text-mode transitions. Stores derived text/window attributes in globals `[0x05d1]`, `[0x05cd]`, and `[0x05cf]`. |
| `code.text.enter_attr_mode` | image `0x76ca` | Action handler for `0x6a`; erases the prompt marker, sets byte `[0x1757]`, derives attributes, enters the overlay text mode through entry `0x9803`, then clears a text rectangle. |
| `code.text.leave_attr_mode` | image `0x78cb` | Shared cleanup for action `0x6b`; clears byte `[0x1757]`, recomputes attributes, calls overlay entry `0x9806`, then redraws status and input-line areas. |
| `code.input.edit_string` | image `0x0da9` | Blocking string editor used by `0x73` and `0x76`. It copies the destination buffer to a local edit buffer, displays it, waits through `code.input.wait_event`, dispatches keys through `data.input.edit_key_table`, copies accepted text back on Enter, and returns without copying on Escape. |
| `code.input.wait_event` | image `0x45d7` | Blocking event wait helper. Calls the event normalizer at `0x459e` until the returned word is neither `0x0000` nor `0xffff`. |
| `code.input.normalize_confirm_event` | image `0x4634` | Normalizes type-1 event values for confirm/editor paths: observed mappings include `0x0101`/`0x0301` to Enter (`0x0d`) and `0x0201`/`0x0401` to Escape (`0x1b`). |
| `code.input.show_prompt_marker` | image `0x37f7` | Draws the configured prompt marker byte from `data.input.prompt_marker_char` when the marker is not already visible and the display-mode gates allow it. |
| `code.input.erase_prompt_marker` | image `0x382e` | Clears the prompt-marker visible flag and echoes backspace when a prompt marker byte is configured. |
| `code.input.set_prompt_marker_char` | image `0x38b4` | Action handler for `0x6c`; resolves a message and stores its first byte in `data.input.prompt_marker_char`. |
| `code.input.redraw_input_line` | image `0x38d7` | Redraws the configured input-line area when enabled, including the prompt marker, fixed string slot 0, and the visible input buffer. |
| `code.input.set_line_config` | image `0x78f0` | Action handler for `0x6f`; stores input/status row globals and computes display offset global `[0x1379]` from the first operand. |
| `code.input.map_key_event` | image `0x4c3d` | Action handler for `0x79`; appends a key/event mapping word and mapped value to the first free four-byte slot rooted at `data.input.key_event_map`. |
| `data.input.edit_key_table` | image/data `0x0e64` | Key dispatch table used by `code.input.edit_string`. The observed SQ2 bytes map `0x03` and `0x18` to clear-current-input, `0x08` to backspace, `0x0d` to accept/copy, and `0x1b` to cancel/return. Evidence: `xxd -g 1 -s 0x1060 -l 0x20 build/cleanroom/AGI.decrypted.exe`. |
| `code.save.restore_game_state` | image `0x2512` | Restore-game action handler. |
| `code.save.save_game_state` | image `0x2753` | Save-game action handler. |
| `code.save.read_length_prefixed_block` | image `0x26b0` | Reads a length-prefixed memory block from a save file. |
| `code.save.write_length_prefixed_block` | image `0x28c6` | Writes a length-prefixed memory block to a save file. |
| `code.save.select_slot_or_path` | image `0x85e5` | Shared save/restore slot/path selection helper. |

## Inventory and Menus

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `code.inventory.show_selection_action` | image `0x31d8` | Action handler for `0x7c`. Enters a text/list mode, builds the carried-item list through `code.inventory.build_selection_list`, restores text state, and returns to the caller after acknowledgement or selection. |
| `code.inventory.build_selection_list` | image `0x3203` | Builds a stack-local 8-byte-per-row list from the 3-byte metadata table rooted at `data.inventory.table_root`; includes only entries with marker byte `0xff`. |
| `code.inventory.draw_selection_list` | image `0x3346` | Draws the inventory header, carried item names or fallback text, and optional highlighted row/prompt depending on flag 13. |
| `data.inventory.selection_result_byte` | data `0x0022` | Absolute byte written by `code.inventory.build_selection_list` on interactive Enter/Escape. Since script byte variables begin at `data.vars.byte_variables` (`0x0009`), this is script variable `0x19`. QEMU `inventory_selection_001` validates Enter and Escape effects. |
| `code.menu.add_heading` | image `0x911d` | Action handler for `0x9c`; allocates and links an 18-byte menu heading node. |
| `code.menu.add_item` | image `0x91cf` | Action handler for `0x9d`; allocates and links a 14-byte menu item node and stores the item id at node offset `+0x0c`. |
| `code.menu.finalize_setup` | image `0x92ba` | Action handler for `0x9e`; finalizes/freezes menu setup. |
| `code.menu.set_item_enabled` | image `0x935f` | Shared helper used by `0x9f` and `0xa0` to enable or disable menu items by id. |
| `code.menu.interact` | image `0x93d1` | Interactive menu path. Draws the menu, waits for input, and enqueues type-3 events with selected item ids for enabled items; QEMU `menu_interaction_001` validates one-item Enter selection. |
| `data.menu.finalized` | data `0x1d2a` | Menu setup finalization flag set by `code.menu.finalize_setup`. |
| `data.menu.request_interaction` | data `0x1d22` | Word set by action `0xa1` when flag 14 is set; the input/event path enters `code.menu.interact` and clears this word after handling menu interaction. |
| `data.menu.heading_root` | data `0x1d2c` | Root/current circular menu heading list pointer used by menu setup and interaction routines. |

## System, Trace, Sound, and Files

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `code.trace.enable_window_action` | image `0x8c91` | Action handler for `0x95`; when the trace window is already active, consumes one extra byte, otherwise calls `code.trace.enable_window_if_flagged`. |
| `code.trace.enable_window_if_flagged` | image `0x8cae` | Enables and draws the trace window only when flag 10 is set. QEMU covers the flag-clear dispatch path; enabled drawing is source-backed and visibly leaves a trace box. |
| `code.trace.configure_window_action` | image `0x8d3d` | Action handler for `0x96`; stores trace logic/resource, row offset, and height globals, clamping height to at least 2. |
| `data.trace.active_state` | data `0x1d10` | Trace-window state word tested by `0x95` and cleared by helper `0x8d79`. |
| `data.trace.logic_resource` | data `0x1d12` | Optional logic resource number used by trace formatting and by restart/room-switch reload paths. |
| `data.trace.row_offset` | data `0x1d08` | Row offset configured by action `0x96`. |
| `data.trace.height` | data `0x1d0a` | Trace-window height configured by action `0x96`, clamped upward to at least 2. |
| `code.sound.start_with_flag` | image `0x51d3` | Action handler for `0x63`; stops prior sound, stores/clears completion flag, locates a loaded sound resource, and starts playback. QEMU `sound_completion_001` validates load/start/stop dispatch after a prior `0x62`. |
| `code.sound.stop_or_clear_state` | image `0x5234` | Shared stop helper used by `0x64` and before starting another sound. Clears active state and sets the configured completion flag when a sound was active. |
| `data.sound.active_state` | data `0x1258` | Word set while sound playback state is active. |
| `data.sound.completion_flag` | data `0x126a` | Word holding the flag number set by `code.sound.stop_or_clear_state`; `0x63` stores and clears this flag before starting playback. |
| `code.log.append_message` | image `0x828f` | Action handler for `0x90`; opens/creates `logfile`, appends a room/input/message record, closes the handle, and returns. |
| `data.log.file_handle` | data `0x1823` | DOS file handle for the log file; `0xffff` means closed/unopened. |
| `data.log.filename` | data `0x1825` | Zero-terminated log filename, observed as `logfile`. |

## Runtime Globals and Data Tables

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `data.vars.byte_variables` | data `0x0009` | Byte variable array used by many conditions/actions. |
| `data.flags.packed_flags` | data `0x0109` | Packed flag bitfield; flag 0 is the high bit of byte `0x0109`. |
| `data.strings.slots` | data `0x020d` | Fixed 40-byte string slots. |
| `data.strings.normalization_drop_chars` | data `0x094b` | Zero-terminated bytes skipped during normalized string comparison. |
| `data.words.parsed_ids` | data `0x0c7b` | Parsed dictionary word IDs. |
| `data.words.parsed_count_or_error_position` | data `0x0ca3` | Parsed word count, or one-based error position on parse failure. |
| `data.objects.first_object` | pointer global `[0x096b]` | Start of 43-byte object record array. |
| `data.objects.end` | pointer global `[0x096d]` | End pointer for object record array. |
| `data.inventory.table_root` | pointer global `[0x0971]` | Root of 3-byte inventory/object metadata entries. |
| `data.logic.cache_root` | pointer global `[0x0977]` | Root of 10-byte logic cache records. |
| `data.logic.current_record` | pointer global `[0x0981]` | Current logic record used by message resolution and resume state. |
| `data.resource.logic_dir` | pointer global `[0x11b2]` | Loaded logic directory pointer. |
| `data.resource.view_dir` | pointer global `[0x11b4]` | Loaded view directory pointer. |
| `data.resource.picture_dir` | pointer global `[0x11b6]` | Loaded picture directory pointer. |
| `data.resource.sound_dir` | pointer global `[0x11b8]` | Loaded sound directory pointer. |
| `data.display.hardware_kind` | global `[0x112e]` | Display adapter/hardware selector used by setup and display branches. |
| `data.display.mode` | global `[0x1130]` | Display mode selector affected by command-line flags and opcode `0x8c`. |
| `data.control.priority_table` | data `0x127a` | Runtime 168-byte row-to-priority/control table. |
| `data.display.logical_buffer_segment` | global `[0x136f]` | Segment of logical graphics/control buffer. |
| `data.picture.current_payload` | global `[0x1377]` | Pointer to selected picture payload during decode. |
| `data.picture.draw_state` | global `[0x1369]` | Active picture low/high nibble draw state. |
| `data.picture.visual_draw_value` | global `[0x136b]` | Current low-nibble picture draw value. |
| `data.picture.control_draw_value` | global `[0x136c]` | Current high-nibble picture draw value. |
| `data.picture.odd_y_write_mask` | global `[0x136d]` | Mask selected by `code.display.pixel_write` for odd Y rows. |
| `data.picture.even_y_write_mask` | global `[0x136e]` | Mask selected by `code.display.pixel_write` for even Y rows. |
| `data.picture.pattern_bits` | data `0x15f9` | Bit masks used by patterned picture drawing. |
| `data.picture.pattern_pointer_table` | data `0x1619` | Pattern pointer table selected by low three bits of picture pattern mode. |
| `data.input.key_event_map` | data `0x0145` | Up to 39 four-byte key mapping slots populated by `code.input.map_key_event`; helper `0x4566` consults this table while normalizing events. |
| `data.input.prompt_marker_char` | data `0x05d7` | Prompt/input marker character configured by action `0x6c`; `code.input.show_prompt_marker` and `code.input.erase_prompt_marker` use it when drawing or erasing the marker. |
| `data.text.status_line_enabled` | data `0x05d9` | Word flag controlled by actions `0x70` and `0x71`; `code.text.redraw_status_line` only draws the status line when this is nonzero. |
| `data.text.input_line_enabled` | data `0x05d3` | Word flag controlled by actions `0x77` and `0x78`; input-line redraw/erase helpers test it before updating the visible input area. |
| `data.text.attr_mode_enabled` | data `0x1757` | Byte flag set by action `0x6a` and cleared by `code.text.leave_attr_mode`; text attribute derivation helpers branch on it. |
| `data.text.attribute_stack` | data `0x1759` | Five-entry stack of triples saved/restored by helpers `0x7989` and `0x79c3`; count lives at `[0x1777]`. |
| `data.event.pair_buffer_base` | global `[0x1707]` | Base pointer for resource/event pair buffer. |
| `data.event.pair_buffer_write` | global `[0x1709]` | Current write pointer for resource/event pair buffer. |
| `data.event.pair_count` | global `[0x0143]` | Active count of event/resource pairs. |
| `data.motion.direction_table` | data `0x0a85` | Nine-word direction lookup used by `code.motion.compute_direction`. |
