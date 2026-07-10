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
| `code.engine.main_cycle` | image `0x0150` | Top-level interpreter cycle. Calls input/system helpers, mirrors object-0 direction/global direction state (`[0x0139] == 0` copies object0 `+0x21` to `[0x000f]`, nonzero copies `[0x000f]` to object0), runs pre-motion mode updates, invokes logic 0 through `code.logic.call_logic`, restores object0 `+0x21` from `[0x000f]`, then runs `code.object.frame_timer_update` unless text-attribute mode byte `[0x1757]` is nonzero. |
| `code.engine.wait_for_cycle_counter` | image `0x7f78` | Top-level cycle throttle called near the start of `code.engine.main_cycle`; reads byte `DS:0x0013` (`v10`), spins until word `[0x1784]` is at least that value, then clears `[0x1784]`. |
| `code.logic.interpret_main` | image `0x293c` | Main logic bytecode loop. Reads opcodes from current logic bytecode and dispatches actions/conditions. |
| `code.logic.action_dispatch` | image `0x02c4` | Action dispatcher. Uses `table.logic.action_dispatch`. |
| `code.logic.condition_dispatch` | image `0x07e3` | Condition dispatcher. Uses `table.logic.condition_dispatch`. |
| `code.logic.condition_input_word_sequence` | image `0x095c` | Condition handler for `0x0e`; matches the parsed word ID table against variable-length word ID operands, with `0x0001` as a wildcard and `0x270f` as an immediate successful terminator. |
| `table.logic.action_dispatch` | data `0x061d` | Four-byte action table entries for opcodes `0x00..0xaf`. |
| `table.logic.condition_dispatch` | data `0x08fd` | Four-byte condition table entries for opcodes `0x00..0x12` in this build. |
| `code.logic.message_xor_range` | image `0x07ab` | XORs logic message text in place. |
| `data.logic.message_xor_key` | data `0x08f1` | Zero-terminated XOR key bytes, observed as `Avis Durgan`. |
| `code.logic.resolve_message` | image `0x21f0` | Resolves a current-logic message number through the message pointer table. |
| `code.logic.load_cached` | image `0x117d` | Loads a logic resource and keeps it linked in the logic cache. |
| `code.logic.load_resource` | image `0x119a` | Reads, initializes, and message-decodes a logic resource. |
| `code.logic.truncate_cache_to_head` | image `0x10f7` | If `data.logic.cache_root` is nonzero, stores zero in the first logic cache record's `+0x00` next-link field. Room-switch cache reset uses this to preserve the first logic record while unlinking later cached logic records. |
| `code.logic.call_logic` | image `0x12ae` | Temporarily switches current logic, runs `code.logic.interpret_main`, and may unlink a transient record. |
| `code.logic.save_resume_ip_action` | image `0x1335` | Action handler for `0x91`; stores the current bytecode pointer in the current logic record's resume pointer field `+0x06`. |
| `code.logic.restore_entry_ip_action` | image `0x134a` | Action handler for `0x92`; copies the current logic record's entry pointer field `+0x04` back to resume pointer field `+0x06`. |
| `code.startup.allocate_runtime_memory` | image `0x43ea` | Startup memory setup around DOS `AH=4a`/`AH=48h`; seeds `data.heap.current_top_0a55` and `data.heap.base_0a57` from the allocated segment converted to a DS-relative byte offset, then computes `data.heap.limit_0a5b`. |
| `code.heap.allocate` | image `0x13d6` | Bump-allocates from `data.heap.current_top_0a55` up to `data.heap.limit_0a5b`. On success it returns the old top, advances the current top, refreshes `data.vars.free_memory_pages_0011` through `code.heap.update_free_memory_var`, and updates `data.heap.high_water_0a5f`. On exhaustion it displays the out-of-memory message and calls the restart/exit helper at `0x02ae`; no recoverable failure return was observed. |
| `code.heap.current_top` | image `0x1430` | Returns `data.heap.current_top_0a55`. |
| `code.heap.rewind_to` | image `0x143c` | Stores a caller-supplied pointer in `data.heap.current_top_0a55`; unlike allocation/reset paths, this helper does not refresh the free-memory byte. |
| `code.heap.save_temporary_mark` | image `0x144b` | Copies `data.heap.current_top_0a55` to `data.heap.temporary_mark_0a5d`. |
| `code.heap.restore_temporary_mark` | image `0x145a` | If `data.heap.temporary_mark_0a5d` is nonzero, rewinds `data.heap.current_top_0a55` to that mark and clears the mark. |
| `code.heap.save_room_reset_mark` | image `0x1476` | Copies `data.heap.current_top_0a55` to `data.heap.room_reset_mark_0a59`. Startup calls this after initial object/inventory setup and logic 0 load. |
| `code.heap.reset_dynamic_state` | image `0x1485` | Flushes object update lists through `code.object.flush_update_lists_restore`, clears the temporary heap mark, restores the current heap pointer from `data.heap.room_reset_mark_0a59`, and refreshes the free-memory byte. Used by room switch, restart, and restore paths. |
| `code.heap.update_free_memory_var` | image `0x14a0` | Computes `data.heap.limit_0a5b - data.heap.current_top_0a55`, stores the high byte at `data.vars.free_memory_pages_0011`, and returns the free-byte count. |
| `code.heap.show_status_action` | image `0x14bd` | Action handler for `0x87`; formats heap size, current usage, high-water usage, room/reset mark usage, and max resource-event/script count. |

## Resources and DOS Files

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `code.resource.load_all_directories` | image `0x4305` | Loads `LOGDIR`, `VIEWDIR`, `PICDIR`, and `SNDDIR`. |
| `code.resource.reset_room_caches` | image `0x10d0` | Room-switch cache reset helper. Calls `code.logic.truncate_cache_to_head`, clears the view cache root, clears the sound cache root, and clears the picture cache root. |
| `code.resource.read_volume_payload_retry` | image `0x2e32` | Retries the generic volume reader until it returns data or reports failure. |
| `code.resource.read_volume_payload_once` | image `0x2e56` | Reads one resource payload from a volume file using a directory entry. |
| `code.resource.logic_dir_entry` | image `0x4371` | Resolves logic directory entries from `data.resource.logic_dir`. |
| `code.resource.view_dir_entry` | image `0x43a5` | Resolves view-like directory entries from `data.resource.view_dir`. |
| `code.resource.picture_dir_entry` | image `0x43d9` | Resolves picture-like directory entries from `data.resource.picture_dir`. |
| `code.resource.sound_dir_entry` | image `0x440d` | Resolves sound-like directory entries from `data.resource.sound_dir`. |
| `code.view.clear_cache_root` | image `0x396d` | Clears the view-like resource cache root at `[0x0ffa]`; called by room-switch cache reset. |
| `code.picture.clear_cache_root` | image `0x49dc` | Clears the picture-like resource cache root at `[0x120e]`; called by room-switch cache reset. |
| `code.sound.clear_cache_root` | image `0x50cc` | Clears the sound-like resource cache root at `[0x125a]`; called by room-switch cache reset. |
| `code.dos.create_file` | image `0x5cad` | DOS `int 21h` wrapper for `AH=0x3c`. Returns `0xffff` on carry/error. |
| `code.dos.open_file` | image `0x5cce` | DOS `int 21h` wrapper for `AH=0x3d`. Returns `0xffff` on carry/error. |
| `code.dos.read_file` | image `0x5cef` | DOS `int 21h` wrapper for `AH=0x3f`. Returns zero on carry/error, so callers compare the returned byte count with the requested count. |
| `code.dos.write_file` | image `0x5d12` | DOS `int 21h` wrapper for `AH=0x40`. Returns zero on carry/error, so callers compare the returned byte count with the requested count. |
| `code.dos.delete_file` | image `0x5d35` | DOS `int 21h` wrapper for `AH=0x41`. Returns zero on carry/error. |
| `code.dos.close_file` | image `0x5d52` | DOS `int 21h` wrapper for `AH=0x3e`; callers observed so far do not inspect an error return. |
| `code.dos.seek_file` | image `0x5d6b` | DOS `int 21h` wrapper for `AH=0x42`. Returns `0xffff:0xffff` in `DX:AX` on carry/error. |
| `code.dos.duplicate_handle` | image `0x5d94` | DOS `int 21h` wrapper for `AH=0x45`. Returns `0xffff` on carry/error. |
| `code.dos.get_current_directory` | image `0x5db2` | Writes a leading slash/backslash then calls DOS `AH=0x47` for the default drive. Used by save-path prompting. |
| `code.dos.get_current_drive_letter` | image `0x5dea` | Calls DOS `AH=0x19` and returns lowercase drive letter `a` plus the zero-based drive number. |
| `code.dos.find_first` | image `0x5e01` | Sets the DTA with `AH=0x1a`, then calls DOS `AH=0x4e`; returns `0xffff` on carry/error. |
| `code.dos.find_next` | image `0x5e26` | DOS `int 21h` wrapper for `AH=0x4f`. Returns `0xffff` on carry/error. |
| `code.dos.probe_drive_selectable` | image `0x5e3e` | Saves the current drive, attempts to select a requested lowercase drive letter, checks whether DOS reports it as current, restores the original drive, and returns 1 on success. |
| `code.dos.get_file_time` | image `0x5e73` | DOS `int 21h` wrapper for `AH=0x57`, `AL=0`; selector code uses the returned time word from `CX`. |
| `code.dos.prepare_call` | image `0x5e8d` | Shared pre-call helper that temporarily switches `DS` to segment `0x0a01` and clears word `[0x184d]`. |
| `code.event.disable_recording` | image `0x705e` | Clears `data.event.recording_enabled`; restore replay and temporary view-resource display use this so replay/internal loads do not append new resource-event pairs. |
| `code.event.enable_recording` | image `0x706d` | Sets `data.event.recording_enabled`; room switch enables recording after resetting the pair buffer, restore/display-mode replay calls it from the post-table finish target at `0x6927`, and temporary view-resource display re-enables it before returning. |
| `code.event.reset_pair_buffer` | image `0x707c` | Allocates the pair buffer when `data.event.pair_capacity > 0` and no buffer exists, then resets write pointer and active pair count. |
| `code.event.record_pair` | image `0x70b1` | Appends a two-byte `(kind, value)` pair when flag 7 is clear and recording is enabled; enforces `data.event.pair_capacity` and updates `data.event.pair_high_water`. |
| `code.event.prepare_replay_cursor` | image `0x712f` | Sets replay read cursor to `data.event.pair_buffer_base` and recomputes the write/end cursor from `data.event.pair_count`. |
| `code.event.next_replay_pair` | image `0x714c` | Returns the current replay pair pointer and advances by two bytes, or returns zero at end. |
| `table.restore.replay_event_dispatch` | image `0x6915` | Nine-word jump table for resource-event replay kinds `0..8`. Linear disassembly from before the table can swallow the following `call 0x706d`; disassemble at `0x6927` to see the post-loop re-enable. |
| `code.restore.finish_replay_and_reenable_recording` | image `0x6927` | Exit target reached when `code.event.next_replay_pair` returns zero. Calls `code.event.enable_recording`, then rebinds object view payloads, restores saved object flags, refreshes display/input state, and returns from replay. |
| `code.event.set_pair_capacity_action` | image `0x716a` | Action handler for `0x8e`; writes `data.event.pair_capacity`, calls `code.event.reset_pair_buffer` inside update-list flush/rebuild calls, and thereby resets the pair-buffer write cursor and active count. |
| `code.event.save_pair_count_action` | image `0x718b` | Action handler for `0xab`; copies `data.event.pair_count` to `data.event.saved_pair_count`. |
| `code.event.restore_pair_count_action` | image `0x719d` | Action handler for `0xac`; restores `data.event.pair_count` and recomputes `data.event.pair_buffer_write`. |

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
| `data.picture.seed_fill_span_scratch` | data `0x126c..0x1279` | Scratch bytes/words used by `code.picture.seed_fill` to track current span limits, vertical direction, saved row/column state, and deferred branch bounds. Field meanings are source-backed but intertwined, so keep this as a conservative block label unless a future version requires per-field names. |
| `code.display.clear_logical_buffer` | image `0x5528` | Clears the logical graphics/control buffer. |
| `code.display.full_refresh` | image `0x5546` | Copies/rebuilds the visible display from logical buffers. |
| `code.display.fill_buffer_word` | image `0x5257` | Fills the logical buffer segment with a caller-supplied word. |
| `code.display.draw_horizontal_line` | image `0x526f` | Draws a horizontal line in the logical buffer using active picture draw state. |
| `code.display.draw_vertical_line` | image `0x52ab` | Draws a vertical line in the logical buffer using active picture draw state. |
| `code.display.pixel_write` | image `0x52f9` | Writes pixel/control nibbles into the logical buffer. |
| `code.display.map_visual_color_for_adapter` | image `0x5685` | Maps picture visual color bytes before they are stored in draw masks. Returns the input unchanged for the EGA target path; delegates to the graphics overlay at `0x9815` only for hardware selector `[0x112e] == 0` with modes other than `2` or `3`. |
| `code.display.shake_screen_action` | image `0x7a00` | Action handler for `0x6e`; reads a count byte and performs display-mode-specific transient screen-shake work. The normal path writes CRT controller registers `0x02` and `0x07` from `data.display.shake_offset_table`. |
| `overlay.cga.map_visual_color_for_mode` | `CGA_GRAF.OVL` near `0x9815` | CGA overlay color mapper called by `code.display.map_visual_color_for_adapter`; indexes three-byte entries in `data.display.cga_color_map` and returns either a duplicated byte for mode 0 or a two-byte word for mode 1. |

## Objects, Views, and Motion

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `code.view.load_resource` | image `0x39f7` | Loads/caches a view-like payload. |
| `code.object.bind_view` | image `0x3ae7` | Binds a cached view payload to an object record. |
| `code.object.select_group` | image `0x3bb7` | Selects a top-level view subresource/group. |
| `code.object.select_group_table` | image `0x3c1b` | Computes a group table pointer from the view payload. |
| `code.object.select_frame` | image `0x3ccb` | Selects a derived frame/entry and updates object size/pointers. |
| `code.object.setup_transient_display_object` | image `0x2d52` | Builds/draws the temporary object-like record rooted at `0x0eb4` from staged bytes `0x0eae..0x0eb3`; records event kind 5 plus three parameter pairs for restore replay. |
| `code.object.place` | image `0x593a` | Places an object and performs priority/control collision adjustment. If the initial candidate fails bounds/collision/control tests, it searches in a widening spiral: left 1, down 1, right 2, up 2, then repeats with increasing segment lengths. |
| `code.object.collision_test` | image `0x4719` | Object-object rectangle/crossing test used by placement and movement. Returns zero when object flag bit `0x0200` bypasses collision; otherwise scans eligible objects and rejects overlapping/crossing candidates. |
| `code.object.control_acceptance` | image `0x56b8` | Tests an object's proposed footprint against high-nibble control/priority classes in `data.display.logical_buffer_segment`; source and QEMU probes validate selected `0x0002`, `0x0100`, and `0x0800` flag effects, including the final scanned class state. |
| `code.object.frame_timer_update` | image `0x0563` | Per-cycle active-object scan that decrements frame timer byte `+0x20`, calls `code.object.advance_frame_by_mode` at zero, and reloads `+0x20` from `+0x1f`. |
| `code.object.advance_frame_by_mode` | image `0x48b3` | Dispatches object frame mode byte `+0x23`; modes loop or stop frames and may set completion flag byte `+0x27`. |
| `data.object.group_for_direction_two_or_three_groups` | data `0x08dd` | Direction-to-group table used by `code.object.frame_timer_update` when object byte `+0x0b` is 2 or 3 and bit `0x2000` is clear. |
| `data.object.group_for_direction_four_plus_groups` | data `0x08e7` | Direction-to-group table used by `code.object.frame_timer_update` when object byte `+0x0b` is at least 4 and bit `0x2000` is clear. |
| `code.object.build_update_list_sorted` | image `0x0358` | Shared update-list builder. It scans the object table, accepts records through a callback, computes a draw key from baseline Y or `code.control.priority_to_y`, selection-sorts by ascending key, and inserts nodes through `code.object.insert_update_node_head`. |
| `code.object.insert_update_node_head` | image `0x042f` | Allocates a 16-byte render/update node and inserts it at the head of the supplied root list while preserving the first inserted node as the tail. |
| `code.object.draw_update_list_tail_to_head` | image `0x045e` | Draws a root list from tail toward head, saving each backing rectangle and then drawing the object's selected frame. |
| `code.object.refresh_update_list_saved_pos` | image `0x0488` | Walks a root list from head toward tail, calls `code.object.update_dirty_rect`, and updates saved-position fields plus stationary bit `0x4000`. |
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
| `code.control.priority_to_y` | image `0x4cbb` | Maps a priority/control value back to a Y-like sort key. In SQ2's normal table mode it scans downward from sentinel index `0xa8`; the direct formula branch appears source-present but no SQ2 write has been found that enables it. |
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
| `code.text.display_message_window` | image `0x1d96` | Builds a modal message window: closes any prior active saved window, formats the message, computes packed save/restore rectangle coordinates, calls `code.text.draw_boxed_window`, sets `data.text.window_active_0d1d`, prints the formatted text, and refreshes text/input areas. |
| `code.text.close_window_state` | image `0x1f2b` | Restores/clears active text-window state and always clears `data.input.width_flag_0d0f`. If `data.text.window_active_0d1d` is set, it restores the rectangle saved by `code.text.display_message_window` through `code.text.restore_saved_rectangle`; QEMU `close_text_window_state_clears_input_width_flag` validates the inactive-window clear side. |
| `code.text.format_string` | image `0x2374` | Formats text into caller-provided buffers. |
| `code.text.format_message_to_buffer` | image `0x1f54` | Formats/copies a resolved logic message into a stack buffer. |
| `code.text.draw_boxed_window` | image `0x5590` | Helper called by the modal message window path with packed rectangle coordinates and attribute word `0x040f`; it delegates to overlay save/fill helpers around `0x9812`. |
| `code.text.restore_saved_rectangle` | image `0x560c` | Helper called by `code.text.close_window_state` with the packed saved-window rectangle words. It loads those words and delegates to overlay restore helper `0x980c`. |
| `code.text.clear_rows` | image `0x2b78` | Helper used by action `0x69`; wraps `code.text.clear_bounds` with left column 0 and right column `0x27`. QEMU `text_rect_clear_rows_removes_formatted_text` validates rows 5..6 clearing logical Y 40..55 to visual color 0. |
| `code.text.clear_row` | image `0x2ba6` | Wraps `code.text.clear_rows` with top row equal to bottom row. Used by status-line hide (`0x71`) and input-line disable (`0x77`); QEMU `text_hide_clear_behaviour_001` validates a configured row clearing to visual color 0. |
| `code.text.clear_bounds` | image `0x2bc4` | BIOS `int 10h` scroll/clear wrapper used by action `0x9a`; arguments map to top, left, bottom, right, attribute. QEMU validates text columns as four logical pixels wide and rows as eight logical pixels tall in the EGA target. |
| `code.text.redraw_status_line` | image `0x34bd` | Redraws the status-line-like area when `data.text.status_line_enabled` is nonzero, using the current text attribute globals and the status row global. QEMU `status_line_show_draws_configured_row` validates visible output on the configured row. |
| `code.text.show_status_line` | image `0x3547` | Action handler for `0x70`; sets `data.text.status_line_enabled` and calls `code.text.redraw_status_line`. QEMU `status_line_show_draws_configured_row` validates the row draw. |
| `code.text.hide_status_line` | image `0x355c` | Action handler for `0x71`; clears `data.text.status_line_enabled` and clears the configured status row. |
| `code.text.set_attribute_pair` | image `0x77d5` | Shared helper for action `0x6d` and text-mode transitions. Stores derived text/window attributes in globals `[0x05d1]`, `[0x05cd]`, and `[0x05cf]`. QEMU `text_attribute_pair_changes_attr_mode_clear_color` validates that pair `(0, 1)` changes the later `0x6a` clear to visual color 15. |
| `code.input.set_width_flag_action` | image `0x3939` | Action handler for `0xa3`; sets `data.input.width_flag_0d0f`. QEMU validates the wider live-input path with a long blank string slot 0. |
| `code.input.clear_width_flag_action` | image `0x394b` | Action handler for `0xa4`; clears `data.input.width_flag_0d0f`. QEMU validates the narrowed live-input path after `0xa3`. |
| `data.input.width_flag_0d0f` | data `0x0d0f` | Word tested by input helper `code.input.handle_input_char`; when set, the helper uses a fixed `0x24` character cap, otherwise it derives the cap from fixed string slot 0. Also cleared by `code.text.close_window_state`. |
| `data.text.window_active_0d1d` | data `0x0d1d` | Word set after a modal message window saves/draws its rectangle. `code.text.display_message_window` closes an existing active window before opening a new one; `code.text.close_window_state` tests this word before restoring the saved rectangle, then clears it. |
| `data.text.window_saved_lower_right_0d23` | data `0x0d23` | Packed rectangle word computed by `code.text.display_message_window` and passed as the first restore argument to `code.text.restore_saved_rectangle`. |
| `data.text.window_saved_upper_left_0d25` | data `0x0d25` | Packed rectangle word computed by `code.text.display_message_window` and passed as the second restore argument to `code.text.restore_saved_rectangle`. |
| `code.text.enter_attr_mode` | image `0x76ca` | Action handler for `0x6a`; erases the prompt marker, sets byte `[0x1757]`, derives attributes, enters the overlay text mode through entry `0x9803`, then clears a text rectangle. QEMU `text_attribute_enable_clears_visible_surface` validates a black visible logical surface with the default pair, and `text_attribute_pair_changes_attr_mode_clear_color` validates the stored pair path. |
| `code.text.leave_attr_mode` | image `0x78cb` | Shared cleanup for action `0x6b`; clears byte `[0x1757]`, recomputes attributes, calls overlay entry `0x9806`, then redraws status and input-line areas. QEMU `text_attribute_disable_restores_picture_draw` validates that ordinary picture/object drawing is visible again after this action. |
| `code.input.edit_string` | image `0x0da9` | Blocking string editor used by `0x73` and `0x76`. It copies the destination buffer to a local edit buffer, displays it, waits through `code.input.wait_event`, dispatches keys through `data.input.edit_key_table`, copies accepted text back on Enter, and returns without copying on Escape. |
| `code.input.handle_input_char` | image `0x3652` | Shared input-line character helper. Normal characters append to visible buffer `0x0fa4`; backspace erases one visible character; Enter copies the visible buffer into source buffer `0x0fce`, parses it, clears visible length `[0x0ff8]`, and redraws the input row. |
| `code.input.erase_input_line` | image `0x3726` | Action handler for `0x8a`; loops `code.input.handle_input_char(0x08)` while visible length `[0x0ff8]` is nonzero. QEMU `input_line_erase_clears_typed_buffer` validates the visible-row erase. |
| `code.input.refresh_input_line` | image `0x3753` | Action handler for `0x89`; when input is enabled, calls the source-to-visible refresh helper in the normal EGA path. QEMU `input_line_refresh_repaints_entered_buffer` validates repaint from source buffer `0x0fce` after Enter. |
| `code.input.append_source_to_visible` | image `0x37a5` | Appends bytes from source input buffer `0x0fce` into visible buffer `0x0fa4` until visible length `[0x0ff8]` reaches the source length, drawing each byte through `0x29f6`. |
| `code.input.wait_for_event_or_tick` | image `0x4529` | Blocks until an event queue record is available or timer globals `[0x0129]`/`[0x012b]` change, then returns the event record pointer. Menu interaction uses this before normalizing raw and movement events. |
| `code.input.wait_event` | image `0x45d7` | Blocking event wait helper. Calls the event normalizer at `0x459e` until the returned word is neither `0x0000` nor `0xffff`. |
| `code.input.enqueue_event` | image `0x44a9` | Enqueues an input/event record with a type word and value word in the circular queue rooted near `data.input.event_queue`. Menu selection uses this to enqueue type 3 item ids. |
| `code.input.dequeue_event` | image `0x44f9` | Dequeues one 4-byte event record from `data.input.event_queue_base`, returning zero when read and write pointers match. |
| `code.input.reset_event_state` | image `0x4482` | Resets input-related state around helper calls `0x466f` and `0x6326`, then resets event queue write/read pointers `[0x120a]` and `[0x120c]` to base `0x11ba`. Used by room switch and pause/calibration paths. |
| `code.input.keyboard_irq_hook` | image `0x6036` | Keyboard interrupt hook. Handles selected raw scan codes, tracks pressed/released latches, and when `data.input.key_release_enqueue_gate_1530` is nonzero can enqueue `(type=2, value=0)` through `code.input.enqueue_event` on selected key releases. Local model `tools/agi_input.py` pins the tracked-key latch contract. |
| `code.input.drain_bios_keys` | image `0x467f` | Repeatedly polls BIOS-key helper `0x5a89`, maps known movement keys through `code.input.map_raw_direction_key`, and enqueues type-2 movement events or type-1 raw key events. |
| `code.input.map_raw_direction_key` | image `0x46b6` | Scans `data.input.menu_direction_event_map` for a raw key word and returns the movement value, or `0xffff` when unmapped. |
| `code.input.remap_display_adapter_event` | image `0x46e8` | When display adapter word `[0x112e] == 2`, scans `data.input.display_adapter_event_map` and converts matching type-1 events to type-2 movement events. |
| `code.input.normalize_confirm_event` | image `0x4634` | Normalizes type-1 event values for confirm/editor paths: observed mappings include `0x0101`/`0x0301` to Enter (`0x0d`) and `0x0201`/`0x0401` to Escape (`0x1b`). |
| `code.input.show_prompt_marker` | image `0x37f7` | Draws the configured prompt marker byte from `data.input.prompt_marker_char` when the marker is not already visible and the display-mode gates allow it. |
| `code.input.erase_prompt_marker` | image `0x382e` | Clears the prompt-marker visible flag and echoes backspace when a prompt marker byte is configured. |
| `code.input.set_prompt_marker_char` | image `0x38b4` | Action handler for `0x6c`; resolves a message and stores its first byte in `data.input.prompt_marker_char`. QEMU `input_prompt_empty_message_suppresses_marker` validates that an empty message stores zero and suppresses marker drawing on input-line redraw. |
| `code.input.redraw_input_line` | image `0x38d7` | Redraws the configured input-line area when enabled, including the prompt marker, fixed string slot 0, and the visible input buffer. QEMU `input_line_enable_clears_configured_row` validates the configured row clear with empty prompt/input text. |
| `code.input.set_line_config` | image `0x78f0` | Action handler for `0x6f`; stores input/status row globals and computes display offset global `[0x1379]` from the first operand. |
| `code.input.map_key_event` | image `0x4c3d` | Action handler for `0x79`; appends a key/event mapping word and mapped value to the first free four-byte slot rooted at `data.input.key_event_map`. |
| `code.words.parse_string_slot_action` | image `0x1958` | Action handler for `0x75`; clears parser flags 2 and 4, validates slot index `< 12`, and parses fixed string slot `data.strings.slots + index * 0x28`. |
| `code.words.parse_buffer` | image `0x18ac` | Clears parsed word ID/pointer tables, normalizes the source string, looks up up to ten output words, sets parser flag 2 when any recognized or unknown output slot exists, and records count/error position in `data.words.parsed_count_or_error_position`. |
| `code.words.normalize_string_for_parse` | image `0x199d` | Collapses separator runs to spaces, drops ignored punctuation, trims a trailing space, and writes `data.words.normalized_parse_buffer`. |
| `code.words.lookup_next_normalized_word` | image `0x1a6b` | Looks up the current normalized token in `WORDS.TOK`, advances `data.words.current_parse_pointer_0cd1`, returns `0xffff` for unknown tokens, returns zero for ignored dictionary words, and returns nonzero dictionary IDs for parsed words. |
| `code.words.terminate_unknown_token` | image `0x1bc7` | Replaces the next space or terminator in the normalized parse buffer with zero for an unknown token. |
| `code.words.advance_dictionary_entry` | image `0x1be4` | Advances from one compressed dictionary entry to the next by finding the suffix byte with bit `0x80` and stepping over the two-byte ID. |
| `code.view.display_resource_text` | image `0x5edb` | Shared helper for actions `0x81` and `0xa2`; disables resource-event recording while it loads, displays, and optionally discards a temporary view resource. |
| `data.input.edit_key_table` | image/data `0x0e64` | Key dispatch table used by `code.input.edit_string`. The observed SQ2 bytes map `0x03` and `0x18` to clear-current-input, `0x08` to backspace, `0x0d` to accept/copy, and `0x1b` to cancel/return. Evidence: `xxd -g 1 -s 0x1060 -l 0x20 build/cleanroom/AGI.decrypted.exe`. |
| `code.save.restore_game_state` | image `0x2512` | Restore-game action handler. |
| `code.save.save_game_state` | image `0x2753` | Save-game action handler. |
| `code.save.copy_description_to_string_action` | image `0x2726` | Action handler for `0xaa`; copies up to `0x1f` bytes from runtime save-description buffer `[0x0e72]` into string slot `0x020d + arg0 * 0x28`. |
| `code.save.read_length_prefixed_block` | image `0x26b0` | Reads a length-prefixed memory block from a save file. |
| `code.save.write_length_prefixed_block` | image `0x28c6` | Writes a length-prefixed memory block to a save file. |
| `code.save.format_slot_filename` | image `0x5b73` | Formats a numbered save filename with `%s%s%ssg.%d`, using `data.save.path_buffer_1962`, a chosen slash/backslash separator, `data.save.signature_prefix_0002`, and the slot number. |
| `code.save.select_slot_or_path` | image `0x85e5` | Shared save/restore slot/path selection helper. Saves/restores text state, stops sound, delegates path prompting, scans selectable save slots, formats the selected filename, and returns zero for cancel/no selection. |
| `code.save.check_drive_or_path_available` | image `0x86a3` | Selector helper that compares the selected drive/path state and displays the insert-disk style message when the target is unavailable. |
| `code.save.prompt_path_if_needed` | image `0x8705` | Selector helper that fills a default path when needed, displays the save/restore path prompt, edits `data.save.path_buffer_1962`, validates it through the path validator at `0x5bdd`, and returns zero on cancel/failure. |
| `code.save.edit_modal_text_field` | image `0x8794` | Modal edit helper used by the save selector. Draws a prompt window, clears the edit row, calls the line editor with a 31-character cap, closes the window, and returns one only when Enter accepted the edit. |
| `code.save.select_numbered_slot` | image `0x8814` | Scans up to 12 numbered save files, displays description rows, handles Enter/Escape/up/down selection, and returns the selected slot number or zero. In save mode it prompts for a new description before accepting an empty-description slot. |
| `code.save.read_slot_summary` | image `0x8b9f` | Formats a numbered save filename, opens it, records the file timestamp, reads the 31-byte description, seeks past the first block length prefix, compares a short signature fragment with `data.save.signature_prefix_0002`, and returns whether the slot is a valid candidate. |
| `code.restore.replay_resource_events` | image `0x681c` | Restore/display-mode state rebuild. Stops sound, clears resource caches, disables resource-event recording while replaying saved resource/event pairs, then reaches `code.restore.finish_replay_and_reenable_recording` at `0x6927` to re-enable recording, rebind active object views, and refresh display/input/status state. |
| `code.dos.validate_path` | image `0x5bdd` | Save-selector path validator. Skips leading spaces, fills an empty path with the current directory, strips a trailing slash/backslash for multi-character paths, accepts a single separator, probes drive-only paths, and otherwise calls DOS find-first with directory attributes. |

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
| `code.menu.interact` | image `0x93d1` | Interactive menu path. Draws the menu, waits for input, and enqueues type-3 events with selected item ids for enabled items; QEMU `menu_interaction_001` validates one-item Enter selection and `menu_edges_002` validates Escape, disabled Enter, and re-enable behavior. |
| `table.menu.navigation_dispatch` | image `0x9526` | Eight-word movement dispatch table used by `code.menu.interact` for type-2 events. Values `1..8` branch to previous item, first item, next enabled heading, last item, next item, last heading, previous enabled heading, and root heading. |
| `code.menu.draw_heading` | image `0x9557` | Draws a menu heading and its item list, including highlighting the current item through helpers `0x95d0`, `0x9625`, and `0x95a9`. |
| `code.menu.remember_item_and_restore_rect` | image `0x95a9` | Stores the active item pointer in the heading node at `+0x0e`, redraws/unhighlights the heading, and restores the saved menu rectangle through helper `0x560c`. Used when leaving a heading and when exiting the modal menu. |
| `code.menu.draw_item` | image `0x95d0` | Positions and draws one menu item using row/column fields from an item node. |
| `code.menu.erase_or_unhighlight_item` | image `0x9625` | Redraws or clears the item's saved rectangle/highlight state while navigating menu items. |
| `data.menu.finalized` | data `0x1d2a` | Menu setup finalization flag set by `code.menu.finalize_setup`. |
| `data.menu.request_interaction` | data `0x1d22` | Word set by action `0xa1` when flag 14 is set; the input/event path enters `code.menu.interact` and clears this word after handling menu interaction. |
| `data.menu.heading_root` | data `0x1d2c` | Root pointer for the circular menu heading list used by setup and interaction routines. |
| `data.menu.current_heading` | data `0x1d2e` | Current/remembered heading pointer persisted by `code.menu.interact` after movement events and initialized by `code.menu.finalize_setup`. |
| `data.menu.current_item` | data `0x1d30` | Current/remembered item pointer persisted by `code.menu.interact` after movement events and initialized from the current heading's item root. |
| `data.menu.saved_rect_start` | data `0x1d32` | Packed rectangle coordinate computed by helper `0x968b` and consumed by menu save/restore rectangle helpers. |
| `data.menu.saved_rect_end` | data `0x1d34` | Packed rectangle coordinate computed by helper `0x968b` and consumed by menu save/restore rectangle helpers. |

## System, Restart, Trace, Sound, and Files

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `code.system.dos_terminate` | image `0x00ae` | DOS process termination wrapper. Loads exit code byte argument into `AL`, sets `AH=0x4c`, and invokes `int 21h`. |
| `code.system.exit_with_cleanup` | image `0x02ae` | Shared fatal/exit helper. Calls `code.system.shutdown_cleanup`, then calls `code.system.dos_terminate(0)`. Used by `0x86` confirmed exit/restart, restore read failure, verification failure, and allocation failure paths. |
| `code.system.pause_action` | image `0x0257` | Action handler for `0x88`; enters modal state, resets input/event state, stops sound, displays the pause message, and returns to the following bytecode. |
| `code.system.confirm_exit_action` | image `0x027f` | Action handler for `0x86`; stops sound, either exits immediately when operand byte is `1` or displays the confirmation message at `0x05e3` and exits only on confirmation. |
| `code.restart.confirm_restart_action` | image `0x2472` | Action handler for `0x80`; confirmation-gated in-engine restart. On acceptance it clears input, preserves flag 9, rewinds heap/update-list state, reruns initial object/inventory setup, refreshes display/menu state, optionally reloads trace logic, clears timer words, and returns zero to stop the current logic stream. Escape/cancel returns the following bytecode pointer. |
| `code.system.shutdown_cleanup` | image `0x8275` | Cleanup before DOS termination. Closes the log file if open, restores hooked interrupt vectors/timer state, then sets the BIOS video mode from `[0x1807]`. |
| `code.log.close_if_open` | image `0x838c` | If `data.log.file_handle` is not `0xffff`, closes it and resets the global to `0xffff`. Called by `code.system.shutdown_cleanup`. |
| `code.system.install_interrupt_hooks` | image `0x83ac` | Saves original interrupt vectors and installs interpreter hooks for keyboard/timer/critical-error style services. |
| `code.system.restore_interrupt_hooks` | image `0x849f` | Restores interrupt vectors saved by `code.system.install_interrupt_hooks` and resets the timer PIT divisor before DOS termination. |
| `code.video.set_mode` | image `0x5a5e` | BIOS video-mode wrapper used by shutdown cleanup; calls `int 10h` with `AH=0` and mode byte argument. |
| `code.room.switch_state` | image `0x1792` | Shared helper for actions `0x12` and `0x13`; stops sound, resets heap/update/input state, seeds selected object fields, resets room caches through `code.resource.reset_room_caches`, updates room variables, loads destination logic, handles entry-boundary placement, sets flag 5, redraws status/input state, and returns zero. QEMU now validates re-entry/current-room dispatch, current/previous/boundary variables, all four boundary placements, and visible absence of a pre-switch persistent object. Exact object/cache field effects are source-backed from disassembly. |
| `code.restart.initialize_game_tables` | image `0x0fa5` | Initial object/inventory/setup routine called during startup and accepted in-engine restart. It prepares inventory/object metadata, allocates or clears the object table, resets flags/input/display defaults, clears resource caches/update lists, and seeds room-entry globals. |
| `code.display.show_priority_screen_action` | image `0x731b` | Action handler for `0x1d`; sets `data.display.priority_screen_mode`, refreshes the screen, waits for an event, refreshes again, then clears the mode. QEMU `priority_diag_sound_001` validates return after Enter. |
| `data.display.priority_screen_mode` | data `0x1755` | Word tested by the full-screen refresh path to display priority/control nibbles instead of normal visual nibbles. |
| `code.object.display_diagnostics_action` | image `0x72b5` | Action handler for `0x85`; formats object fields into the diagnostic template at data `0x1713` and displays the text. QEMU `priority_diag_sound_001` validates return after Enter. |
| `code.trace.enable_window_action` | image `0x8c91` | Action handler for `0x95`; when the trace window is already active, consumes one extra byte, otherwise calls `code.trace.enable_window_if_flagged`. |
| `code.trace.enable_window_if_flagged` | image `0x8cae` | Enables and draws the trace window only when flag 10 is set. QEMU `trace_window_enable_002` validates the enabled red-border/white-fill/black-text path; `system_dialog_001` covers the flag-clear dispatch path. |
| `code.trace.configure_window_action` | image `0x8d3d` | Action handler for `0x96`; stores trace logic/resource, row offset, and height globals, clamping height to at least 2. QEMU validates `0x96(0,1,2)` feeding the enabled trace-window draw path. |
| `data.trace.active_state` | data `0x1d10` | Trace-window state word tested by `0x95` and cleared by helper `0x8d79`. |
| `data.trace.logic_resource` | data `0x1d12` | Optional logic resource number used by trace formatting and by restart/room-switch reload paths. |
| `data.trace.row_offset` | data `0x1d08` | Row offset configured by action `0x96`. |
| `data.trace.height` | data `0x1d0a` | Trace-window height configured by action `0x96`, clamped upward to at least 2. |
| `code.sound.start_with_flag` | image `0x51d3` | Action handler for `0x63`; stops prior sound, stores/clears completion flag, locates a loaded sound resource, and starts playback. QEMU `sound_completion_001` validates load/start/stop dispatch after a prior `0x62`. |
| `code.sound.stop_or_clear_state` | image `0x5234` | Shared stop helper used by `0x64` and before starting another sound. Clears active state and sets the configured completion flag when a sound was active; QEMU `priority_diag_sound_001` validates that stop sets flag 77 after `0x63(1,77)`. |
| `code.sound.find_loaded_resource` | image `0x50d8` | Looks up a loaded sound cache record by resource number for `code.sound.start_with_flag`; a zero result triggers an error path. |
| `code.sound.load_resource` | image `0x5126` | Loads/caches a sound-like payload. Restore-time resource replay calls this for saved sound load events. |
| `code.sound.driver_start` | image `0x7f96` | Hardware/driver-facing sound start helper called after `code.sound.start_with_flag` finds a loaded sound record. |
| `code.sound.driver_tick` | image `0x801c` | Timer-driven playback tick. Tests flag 9, advances active channel countdowns, consumes duration/tone/control records, and stops/completes playback when all active channels terminate. |
| `code.sound.driver_stop` | image `0x80af` | Hardware/driver-facing sound stop helper called by `code.sound.stop_or_clear_state` when sound state had been active. |
| `code.sound.driver_stop_core` | image `0x80c1` | Shared low-level stop/completion helper. Silences hardware, clears `data.sound.active_state`, and sets `data.sound.completion_flag`. |
| `code.sound.driver_write_tone` | image `0x80f3` | Hardware-specific tone/control output helper called after an event record is consumed and by the stop path for silence writes. Selector `0`/`8` uses PIT/PC-speaker ports and computes divisor `12 * (((tone_word & 0x3f) << 4) + ((tone_word >> 8) & 0x0f))`; other observed selectors write encoded tone bytes to port `0xc0`. |
| `code.sound.driver_write_attenuation` | image `0x8162` | Hardware-specific attenuation/envelope output helper called on countdown ticks, event reads, and channel termination. Maintains low-nibble attenuation, applies source envelope/delta state, and writes combined channel/attenuation bytes to port `0xc0` on non-PC-speaker paths. |
| `code.sound.timer_irq_hook` | image `0x8521` | Replacement timer interrupt hook. Calls `code.sound.driver_tick` while sound state is active, then chains to the original timer interrupt every third invocation through divider byte `data.sound.timer_irq_divider`. |
| `data.sound.active_state` | data `0x1258` | Word set while sound playback state is active. |
| `data.sound.completion_flag` | data `0x126a` | Word holding the flag number set by `code.sound.stop_or_clear_state`; `0x63` stores and clears this flag before starting playback. |
| `data.sound.channel_stream_pointers` | data `0x1788..0x178f` | Four current stream pointers copied from a sound cache record by `code.sound.driver_start`; the playback tick advances them through event records. |
| `data.sound.channel_countdowns` | data `0x1790..0x1797` | Four countdown words initialized to 1 and reloaded from event duration words during playback. |
| `data.sound.channel_active_words` | data `0x1798..0x179f` | Four nonzero/zero words used by the playback tick to decide whether a channel is still active. |
| `data.sound.channel_attenuation` | data `0x17a8..0x17af` | Per-channel low-nibble attenuation/control values; `0x0f` is the silent value used when a channel terminates. |
| `data.sound.active_channel_byte_limit` | data `0x1804` | Tick-loop byte offset limit. Value `2` advances only channel 0; value `8` advances channels 0 through 3. |
| `data.sound.remaining_active_channels` | data `0x1806` | Byte decremented as channel terminators are consumed; zero triggers the stop/completion path. |
| `data.sound.timer_irq_divider` | data `0x184f` | Timer-hook countdown byte. The hook acknowledges the interrupt directly until it reaches zero, then resets it to 3 and chains to the original timer interrupt. |
| `code.log.append_message` | image `0x828f` | Action handler for `0x90`; opens/creates `logfile`, appends a room/input/message record, closes the handle, and returns. QEMU `log_file_contents_001` validates the extracted `LOGFILE` content for a synthetic message. |
| `data.log.file_handle` | data `0x1823` | DOS file handle for the log file; `0xffff` means closed/unopened. |
| `data.log.filename` | data `0x1825` | Zero-terminated log filename, observed as `logfile`. |

## Runtime Globals and Data Tables

| Label | SQ2 address | Notes/evidence |
| --- | --- | --- |
| `data.vars.byte_variables` | data `0x0009` | Byte variable array used by many conditions/actions. |
| `data.vars.current_room` | data `0x0009` | Byte variable 0. `code.room.switch_state` writes the destination room here; SQ2 logic 0 later dispatches room logic with `call_logic_var(v0)` at logic bytecode offset `0x053e`. |
| `data.vars.previous_room` | data `0x000a` | Byte variable 1. `code.room.switch_state` copies the prior current-room byte here before overwriting `data.vars.current_room`. Many room-entry blocks branch on this value. |
| `data.vars.entry_boundary` | data `0x000b` | Byte variable 2. `code.room.switch_state` uses values `1..4` to place object 0 at a room edge, then clears the byte. |
| `data.vars.free_memory_pages_0011` | data `0x0011` | Byte variable 8. `code.heap.update_free_memory_var` stores the high byte of available heap bytes here after successful allocations and dynamic-state resets. |
| `data.motion.global_direction_000f` | data `0x000f` | Global direction byte mirrored with object0 byte `+0x21` by `code.engine.main_cycle`; also written by first-object motion helpers. |
| `data.motion.direction_mirror_selector_0139` | data `0x0139` | Word selector for the pre-logic object0/global direction mirror. Action `0x83` clears it; action `0x84`, room switch, and selected first-object stop/reset helpers set it. |
| `data.flags.packed_flags` | data `0x0109` | Packed flag bitfield; flag 0 is the high bit of byte `0x0109`. |
| `data.strings.slots` | data `0x020d` | Fixed 40-byte string slots. |
| `data.strings.normalization_drop_chars` | data `0x094b` | Zero-terminated bytes skipped during normalized string comparison. |
| `data.words.parser_separators_0c67` | data `0x0c67` | Zero-terminated separator bytes used by `code.words.normalize_string_for_parse`; SQ2 bytes are ` ,.?!();:[]{}`. |
| `data.words.parser_ignored_0c75` | data `0x0c75` | Zero-terminated ignored punctuation bytes dropped by `code.words.normalize_string_for_parse`; SQ2 bytes are apostrophe, backtick, hyphen, and double quote. |
| `data.words.parsed_ids` | data `0x0c7b` | Parsed dictionary word IDs. |
| `data.words.parsed_text_pointers` | data `0x0c8f` | Pointers into the normalized parse buffer for recognized words and the first unknown output slot. |
| `data.words.parsed_count_or_error_position` | data `0x0ca3` | Parsed word count, or one-based error position on parse failure. |
| `data.words.dictionary_base` | pointer global `[0x0ca5]` | Loaded `WORDS.TOK` base pointer used by dictionary lookup helper `0x1a6b`. |
| `data.words.normalized_parse_buffer` | data `0x0ca7` | Parser normalization output buffer consumed one token at a time by dictionary lookup. |
| `data.words.current_parse_pointer_0cd1` | pointer global `[0x0cd1]` | Current token pointer inside `data.words.normalized_parse_buffer`, advanced by dictionary lookup helper `0x1a6b`. |
| `data.objects.first_object` | pointer global `[0x096b]` | Start of 43-byte object record array. |
| `data.objects.end` | pointer global `[0x096d]` | End pointer for object record array. |
| `data.inventory.table_root` | pointer global `[0x0971]` | Root of 3-byte inventory/object metadata entries. |
| `data.logic.cache_root` | pointer global `[0x0977]` | Root of 10-byte logic cache records. |
| `data.logic.current_record` | pointer global `[0x0981]` | Current logic record used by message resolution and resume state. |
| `data.resource.logic_dir` | pointer global `[0x11b2]` | Loaded logic directory pointer. |
| `data.resource.view_dir` | pointer global `[0x11b4]` | Loaded view directory pointer. |
| `data.resource.picture_dir` | pointer global `[0x11b6]` | Loaded picture directory pointer. |
| `data.resource.sound_dir` | pointer global `[0x11b8]` | Loaded sound directory pointer. |
| `data.resource.view_cache_root` | pointer global `[0x0ffa]` | Root of cached view-like resource records. Cleared by `code.view.clear_cache_root` during room-switch cache reset. |
| `data.resource.picture_cache_root` | pointer/global record `[0x120e]` | Picture-like cache root/static first record used by picture loading. Cleared by `code.picture.clear_cache_root` during room-switch cache reset. |
| `data.resource.sound_cache_root` | pointer/global record `[0x125a]` | Sound-like cache root/static first record used by sound loading. Cleared by `code.sound.clear_cache_root` during room-switch cache reset. |
| `data.save.description_buffer` | data `0x0e72` | Runtime save-description/path buffer consumed by `0xaa` and tested by save/restore handlers after slot/path selection. |
| `data.save.signature_prefix_0002` | data `0x0002` | Runtime game signature/save filename prefix. Action `0x8f` copies a logic message here and verifies it against the embedded `SQ2` signature; save filename formatting and slot summary filtering also consume this string. |
| `data.save.path_buffer_1962` | data `0x1962` | Path buffer edited by `code.save.prompt_path_if_needed` and validated by the generic path helper. |
| `data.save.header_description_buffer_1c6c` | data `0x1c6c` | 31-byte save-file description/header buffer written before the length-prefixed state blocks. Filled by the empty-slot save-description prompt when needed. |
| `data.save.filename_buffer_1c8c` | data `0x1c8c` | Fully formatted save filename/path used by the save and restore DOS file wrappers after slot selection. |
| `data.display.hardware_kind` | global `[0x112e]` | Display adapter/hardware selector used by setup and display branches. |
| `data.display.mode` | global `[0x1130]` | Display mode selector affected by command-line flags and opcode `0x8c`. |
| `data.display.shake_low_base` | data `0x1779` | Base value added to the second byte of each normal-path screen-shake table pair before writing CRT controller register `0x07`; `0x6e` sets it to `0x70` or `0x38` from hardware selector `[0x112e]`. |
| `data.display.shake_offset_table` | data `0x177a` | Byte pairs consumed by the normal-path `0x6e` screen shake loop. The first byte plus `[0x1365]` is written to CRT register `0x02`; the second byte plus `data.display.shake_low_base` is written to register `0x07`. |
| `data.display.shake_high_offset` | data `0x1365` | Offset added to the first byte of each screen-shake table pair before writing CRT controller register `0x02`. |
| `data.display.cga_color_map` | `AGIDATA.OVL:0x1d36` | Three-byte-per-color table used by the CGA graphics overlay color mapper. Mode 0 uses byte 0 duplicated; mode 1 uses bytes 1 and 2 as the returned word. |
| `data.heap.current_top_0a55` | data `0x0a55` | Current top pointer for the interpreter's bump heap. Seeded with `data.heap.base_0a57` during startup memory allocation. |
| `data.heap.base_0a57` | data `0x0a57` | Heap base used by allocation and heap-status display. Startup derives it from the DOS allocated segment relative to the interpreter data segment. |
| `data.heap.room_reset_mark_0a59` | data `0x0a59` | Mark used by room switch, restart, and restore cleanup; `code.heap.reset_dynamic_state` rewinds the heap to this pointer. |
| `data.heap.limit_0a5b` | data `0x0a5b` | Heap limit pointer used by `code.heap.allocate` and `code.heap.update_free_memory_var`; startup sets it to `data.heap.base_0a57 + requested_runtime_paragraphs * 16`. |
| `data.heap.temporary_mark_0a5d` | data `0x0a5d` | Optional one-shot temporary heap mark saved by `code.heap.save_temporary_mark` and consumed by `code.heap.restore_temporary_mark`. |
| `data.heap.high_water_0a5f` | data `0x0a5f` | Highest current-top value observed after successful allocations; reported by `code.heap.show_status_action`. |
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
| `data.input.event_queue_base` | data `0x11ba` | Start of the 20-record circular raw event queue. Records are 4 bytes: type word, value word. |
| `data.input.event_queue_write` | data `0x120a` | Write pointer used by `code.input.enqueue_event`; wraps to `data.input.event_queue_base` at the queue end. |
| `data.input.event_queue_read` | data `0x120c` | Read pointer used by `code.input.dequeue_event`; equal read/write pointers mean the queue is empty. |
| `data.input.tracked_scan_enabled` | data `0x1519` | Byte table indexed by raw scan code minus `0x47`; nonzero entries enable special keyboard IRQ release tracking for selected scan codes. |
| `data.input.tracked_scan_pressed_latch` | data `0x1524` | Byte table indexed like `data.input.tracked_scan_enabled`; press paths set one latch and clear the others, release paths clear the latch before optionally enqueueing a release event. |
| `data.input.last_irq_scan_code` | data `0x152f` | Last raw scan byte captured by `code.input.keyboard_irq_hook` before range/latch handling. |
| `data.input.key_release_enqueue_gate_1530` | data `0x1530` | Byte gate incremented by action `0xad`; nonzero lets `code.input.keyboard_irq_hook` enqueue a type-2 zero event on selected tracked-key release paths. The source model covers 8-bit wraparound from `0xff` to zero. |
| `data.input.menu_direction_event_map` | data `0x16b3` | Four-byte raw key/event to movement-code table consulted by helper `0x46b6` before type-2 events are enqueued. Observed SQ2 entries map `0x4800`, `0x4900`, `0x4d00`, `0x5100`, `0x5000`, `0x4f00`, `0x4b00`, and `0x4700` to movement codes `1..8`. |
| `data.input.display_adapter_event_map` | data `0x16d7` | Four-byte remap table used when display adapter word `[0x112e] == 2`; observed entries map numeric keypad values `0x38`, `0x39`, `0x36`, `0x33`, `0x32`, `0x31`, `0x34`, and `0x37` to movement values `1..8`. |
| `data.input.prompt_marker_char` | data `0x05d7` | Prompt/input marker character configured by action `0x6c`; `code.input.show_prompt_marker` and `code.input.erase_prompt_marker` use it when drawing or erasing the marker. |
| `data.text.status_line_enabled` | data `0x05d9` | Word flag controlled by actions `0x70` and `0x71`; `code.text.redraw_status_line` only draws the status line when this is nonzero. |
| `data.text.input_line_enabled` | data `0x05d3` | Word flag controlled by actions `0x77` and `0x78`; input-line redraw/erase helpers test it before updating the visible input area. |
| `data.text.attr_mode_enabled` | data `0x1757` | Byte flag set by action `0x6a` and cleared by `code.text.leave_attr_mode`; text attribute derivation helpers branch on it. |
| `data.text.attribute_stack` | data `0x1759` | Five-entry stack of triples saved/restored by helpers `0x7989` and `0x79c3`; count lives at `[0x1777]`. |
| `data.event.pair_capacity` | global `[0x0141]` | Maximum number of two-byte resource/event pairs. Action `0x8e` writes this value before resetting the pair buffer. |
| `data.event.pair_count` | global `[0x0143]` | Active count of event/resource pairs. |
| `data.event.saved_pair_count` | global `[0x05e1]` | Saved pair count slot used by actions `0xab` and `0xac`. |
| `data.event.pair_buffer_base` | global `[0x1707]` | Base pointer for resource/event pair buffer. |
| `data.event.pair_buffer_write` | global `[0x1709]` | Current write pointer for appends and replay end pointer. |
| `data.event.pair_buffer_read` | global `[0x170b]` | Replay read cursor used by `code.event.next_replay_pair`. |
| `data.event.recording_enabled` | global `[0x170d]` | Word gate checked by `code.event.record_pair` after flag 7. |
| `data.event.pair_high_water` | global `[0x170f]` | Maximum observed pair count; heap/status display uses it and overflow error reporting passes it as context. |
| `data.motion.direction_table` | data `0x0a85` | Nine-word direction lookup used by `code.motion.compute_direction`. |

## Gold Rush / AGI v3 Address Associations

These are the first non-SQ2 mappings for existing or newly introduced symbolic
labels. They are loaded-image offsets in `games/GR/AGI` unless otherwise
noted. The GR executable has the same `0x200`-byte MZ header size as the
decrypted SQ2 executable, so file offsets are image offsets plus `0x200`.

| Label | GR address | Notes/evidence |
| --- | --- | --- |
| `code.logic.action_dispatch` | image `0x02bc` | Same structural role as SQ2 `0x02c4`, but the v3 max-action check accepts opcodes through `0xb5` and dispatches through AGIDATA table `0x0440`. |
| `table.logic.action_dispatch` | `AGIDATA.OVL:0x0440` | Four-byte v3 action table. `tools/disassemble_logic.py --game-dir games/GR --stats` parsed all present GR logic resources with this base. |
| `code.logic.condition_dispatch` | image `0x0a31` | Same structural role as SQ2 `0x07e3`. The GR dispatcher compares predicate bytes with `0x26`, but the observed structured table at `AGIDATA.OVL:0x0762` only covers shared entries `0x00..0x12`. |
| `table.logic.condition_dispatch` | `AGIDATA.OVL:0x0762` | Four-byte v3 condition table for entries `0x00..0x12`, matching SQ2 table `0x08fd` by contract and normalized handler snippets. Bytes after entry `0x12` overlap string/data, not confirmed predicates. Gold Rush scripts observed so far only use conditions through `0x0e`. |
| `opcode.action.reserved_noop_v3_0` | table slot `0xb0`, image `0x5286` | GR-only action slot. Zero operands, generic no-op/return handler. |
| `opcode.action.set_menu_interaction_gate` | table slot `0xb1`, image `0x970b` | GR-only action slot. Reads one immediate byte and stores it in `data.menu.interaction_gate_0403`; QEMU report `build/gr-v3-behavior/menu_gate_suite.json` validates zero as blocked and nonzero as modal-menu entry. |
| `opcode.action.reserved_noop_v3_2` | table slot `0xb2`, image `0x5286` | GR-only action slot. Zero operands, generic no-op/return handler. |
| `opcode.action.reserved_noop_v3_4args` | table slot `0xb3`, image `0x5286` | GR-only action slot. Four fixed operands are consumed by table-driven scanning, but the handler performs no state change. |
| `opcode.action.reserved_noop_v3_2varargs` | table slot `0xb4`, image `0x5286` | GR-only action slot. Two variable operands are declared with metadata `0xc0`, but the handler performs no state change. |
| `opcode.action.clear_key_release_event_gate` | table slot `0xb5`, image `0x63b0` | GR-only action slot. Stores zero in `data.input.key_release_enqueue_gate_0405`; GR action `0xad` stores one in the same byte. Local model `tools/agi_input.py` covers the set/clear gate. |
| `code.menu.interact` | image `0x9724` | GR address association for the interactive menu path. Tests `data.menu.interaction_gate_0403` before drawing/waiting; returns immediately while the gate is zero. QEMU `menu_gate_suite` confirms that only a nonzero gate lets a later `0xa1` request enter the modal menu. |
| `code.input.keyboard_irq_hook` | image `0x63b8` | GR keyboard interrupt hook. Tests `data.input.key_release_enqueue_gate_0405` before enqueueing `(type=2, value=0)` on selected key-release paths. The tracked-key latch contract matches SQ2 after relocation. |
| `code.input.set_line_config` | image `0x7c24` | GR association for SQ2 action `0x6f`. Stores the same input-line row/bounds roles at relocated globals and computes display offset `[0x11b1] = arg0 << 3` without SQ2's display-mode-2 branch. |
| `code.input.edit_string` | image `0x0fb7` | GR association for SQ2 image `0x0da9`; blocking string editor used by GR prompt actions `0x73` and `0x76`. |
| `code.input.handle_input_char` | image `0x3961` | GR association for SQ2 image `0x3652`; visible/source input buffer character helper. |
| `code.input.erase_input_line` | image `0x3a29` | GR association for SQ2 action `0x8a`. Loops on visible input length `[0x0e19]`; no SQ2 display-mode-2/input-width skip branch. |
| `code.input.refresh_input_line` | image `0x3a48` | GR association for SQ2 action `0x89`. Calls the relocated source-to-visible helper when input is enabled; no SQ2 alternate display-mode-2/input-width path. |
| `code.input.append_source_to_visible` | image `0x3a5e` | GR association for SQ2 image `0x37a5`; appends source input buffer bytes into the visible buffer. |
| `code.input.show_prompt_marker` | image `0x3ab0` | GR association for SQ2 image `0x37f7`; draws prompt marker byte `[0x03f7]` when marker state `[0x0dc3]` is clear and the byte is nonzero. |
| `code.input.erase_prompt_marker` | image `0x3ad9` | GR association for SQ2 image `0x382e`; clears the prompt-marker visible state and backspaces the marker when configured. |
| `code.input.prompt_marker_visible_state` | image `0x3b00` | GR association for SQ2 helper `0x3863`; returns prompt-marker visible word `[0x0dc3]`. |
| `code.input.set_prompt_marker_char` | image `0x3b43` | GR association for SQ2 action `0x6c`; stores the first byte of a resolved message in prompt-marker byte `[0x03f7]`. |
| `code.input.redraw_input_line` | image `0x3b66` | GR association for SQ2 image `0x38d7`; redraws the configured input row, prompt marker, fixed prompt string, and visible input buffer. |
| `code.input.set_width_flag_action` | image `0x5286` | GR maps SQ2 action `0xa3` to the generic no-op/return handler. |
| `code.input.clear_width_flag_action` | image `0x5286` | GR maps SQ2 action `0xa4` to the generic no-op/return handler. |
| `code.input.map_key_event` | image `0x4e98` | GR association for SQ2 action `0x79`; same three-operand key/event mapping shape, but scans `0x31` four-byte slots instead of SQ2's `0x27`. QEMU probe `build/gr-v3-behavior/key_map_capacity_qemu_pic001_002.json` validates slot 48 with a typed-key positive case and no-key control. |
| `code.text.close_window_state` | image `0x21a2` | GR association for SQ2 action `0xa9`. Restores a saved rectangle when `data.text.window_active_0b24` is nonzero and clears that active flag; it does not clear a GR input-width flag. |
| `code.text.restore_saved_rectangle` | image `0x582b` | GR association for SQ2 image `0x560c`; rectangle restore helper consumed by `code.text.close_window_state`. |
| `code.room.switch_room_action` | image `0x19d4` | GR association for SQ2 action `0x12`; calls `code.room.remap_reserved_room_target` before the relocated room-switch helper `0x1a0a`. |
| `code.room.remap_reserved_room_target` | image `0x0062` | GR-only helper used by action `0x12`: bytes `0x7e..0x80` return `0x49`; all other target bytes pass through unchanged. QEMU probe `build/gr-v3-behavior/room_remap_all_qemu_pic001_001.json` validates `0x7e`, `0x7f`, and `0x80` as aliases for `0x49` with matching nonblank captures. |
| `code.inventory.show_selection_action` | image `0x351e` | GR association for SQ2 action `0x7c`; relocated carried-item selector plus temporary word `data.inventory.selection_event_gate_0dc1`. |
| `code.save.save_game_state` | image `0x29e5` | GR association for SQ2 action `0x7d`; relocated five-block save writer with an XOR pass over the object/inventory chunk before and after save-file writes. QEMU report `build/gr-v3-behavior/save_xor_extract_qemu_001.json` validates a blank-prefix `SG.1` extraction, and `build/gr-v3-behavior/save_xor_extract_signed_qemu_001.json` validates `0x8f("GR")` producing `GRSG.1` with first-block prefix `GR\0`; both have third block length `1811` and round-trip through the modeled XOR transform. |
| `code.save.restore_game_state` | image `0x2792` | GR association for SQ2 action `0x7e`; relocated five-block restore reader. After loading the third block into `[0x07d6]`, the success path calls `code.save.object_inventory_xor_range` over `[0x07d6]..[0x07d6]+[0x07da]`, refreshes display/resource state, clears the caller return pointer, and returns through restored script state. QEMU report `build/gr-v3-behavior/signed_restore_roundtrip_suite.json` validates a signed `GRSG.1` restore by matching the restored capture to a direct saved-state control and differing from an unrestored control. |
| `code.save.object_inventory_xor_range` | image `0x07bc` | GR helper called by save and object/inventory setup paths. XORs bytes in a caller-supplied range with repeating key bytes at `0x072c` until a zero key byte. |
| `data.save.object_inventory_block_start_07d6` | GR data `[0x07d6]` | Pointer to the GR save block that is XOR-transformed before writing and transformed again before returning from action `0x7d`. |
| `data.save.object_inventory_block_length_07da` | GR data `[0x07da]` | Length of the GR save block rooted at `data.save.object_inventory_block_start_07d6`; save action `0x7d` writes this as the third length-prefixed state block. |
| `data.save.object_inventory_xor_key_072c` | GR image `0x072c..0x0766` | Observed 59-byte sequence used by `code.save.object_inventory_xor_range`; helper wraps when it reaches the zero byte at image `0x0767`. |
| `code.restart.confirm_restart_action` | image `0x26e0` | GR association for SQ2 action `0x80`; records prompt-marker visible state before confirmation, then redraws after accepted restart or after canceled restart only when the marker had been visible. QEMU report `build/gr-v3-behavior/restart_prompt_marker_qemu_001.json` confirms the canceled branch. |
| `code.resource.load_all_directories` | image `0x44de` | v3 combined-directory loader. Formats `"%sdir"`, reads a whole combined directory, derives four section pointers from the first eight bytes, and falls back to separate `logdir`/`picdir`/`viewdir`/`snddir` loads if the combined open fails. |
| `code.resource.dir_entry_or_null` | image `0x4599` | v3 shared absent-entry helper. Returns null only for exact `ff ff ff`, unlike SQ2's high-nibble `0xf` check. |
| `code.resource.logic_dir_entry` | image `0x45bc` | Uses v3 logic directory base `[0x0fda]`; missing-resource string `logic` at `AGIDATA.OVL:0x0f5e`. |
| `code.resource.view_dir_entry` | image `0x45f0` | Uses v3 view directory base `[0x0fdc]`; missing-resource string `view` at `AGIDATA.OVL:0x0f64`. |
| `code.resource.picture_dir_entry` | image `0x4624` | Uses v3 picture directory base `[0x0fde]`; missing-resource string `picture` at `AGIDATA.OVL:0x0f69`. |
| `code.resource.sound_dir_entry` | image `0x4658` | Uses v3 sound directory base `[0x0fe0]`; missing-resource string `sound` at `AGIDATA.OVL:0x0f71`. |
| `code.resource.open_volume_handles` | image `0x33c2` | Opens sixteen possible prefixed volume files with `"%svol.%d"`, explaining observed `GRVOL.9` through `GRVOL.12` entries. |
| `code.resource.close_volume_handles` | image `0x341c` | Closes the sixteen v3 handle slots and resets them to `0xffff`. |
| `code.resource.read_volume_payload_retry` | image `0x30ac` | v3 retry wrapper around `code.resource.read_volume_payload_once`. |
| `code.resource.read_volume_payload_once` | image `0x30d0` | v3 generic reader. Decodes 7-byte record headers, allocates expanded length, and selects direct, dictionary, or picture-nibble payload paths. |
| `code.resource.decompress_lzw_like` | image `0x07f4` | General v3 dictionary decompressor for compressed logic/view/sound records. Uses reset code `0x100`, end code `0x101`, and 9-to-11-bit codes. |
| `code.resource.decompress_picture_nibble` | image `0x9a5b` | v3 picture transform that expands packed nibbles after `0xf0`/`0xf2` into ordinary byte operands and stops after emitting `0xff`. |
| `code.view.load_resource` | image `0x3c5b` | GR address association for SQ2 image `0x39f7`; normalized static comparison matches after resource-reader relocation. |
| `code.object.bind_view` | image `0x3d4b` | GR address association for SQ2 image `0x3ae7`; normalized static comparison matches. |
| `code.object.select_group` | image `0x3e1b` | GR address association for SQ2 image `0x3bb7`; normalized static comparison matches. |
| `code.object.select_group_table` | image `0x3e7f` | GR address association for SQ2 image `0x3c1b`; normalized static comparison matches. |
| `code.object.select_frame` | image `0x3f2f` | GR address association for SQ2 image `0x3ccb`; normalized static comparison matches. |
| `code.view.discard` | image `0x4131` | GR address association for SQ2 image `0x3ecd`; normalized static comparison matches. |
| `code.picture.load_resource` | image `0x4c96` | GR address association for SQ2 image `0x4a3b`; normalized static comparison matches after resource-reader relocation. |
| `code.picture.prepare` | image `0x4d2a` | GR address association for SQ2 image `0x4acf`; normalized static comparison matches. |
| `code.picture.overlay_prepare` | image `0x4d96` | GR address association for SQ2 image `0x4b3b`; normalized static comparison matches. |
| `code.picture.discard` | image `0x4e29` | GR address association for SQ2 image `0x4bce`; normalized static comparison matches. |
| `code.picture.decode_no_clear` | image `0x67c2` | GR address association for SQ2 image `0x6440`; differs because GR returns after command scan where SQ2 checks display mode `2` and calls an overlay refresh path. |
| `code.picture.command_scan` | image `0x67ed` | GR address association for SQ2 image `0x6475`; normalized static comparison matches. |
| `table.picture.command_dispatch` | `AGIDATA.OVL:0x140d` | GR dispatch table for picture command bytes `0xf0..0xfa`; corresponds to SQ2 data table `0x15d6`. |
| `code.picture.cmd_set_visual_draw_nibble` | image `0x680c` | GR address association for SQ2 image `0x6494`; normalized static comparison matches. |
| `code.picture.cmd_disable_visual_draw_nibble` | image `0x682d` | GR address association for SQ2 image `0x64b5`; normalized static comparison matches. |
| `code.picture.cmd_set_control_draw_nibble` | image `0x683f` | GR address association for SQ2 image `0x64c7`; normalized static comparison matches. |
| `code.picture.cmd_disable_control_draw_nibble` | image `0x6865` | GR address association for SQ2 image `0x64ed`; normalized static comparison matches. |
| `code.picture.cmd_draw_corner_path_y_first` | image `0x698a` | GR address association for SQ2 image `0x6612`; normalized static comparison matches. |
| `code.picture.cmd_draw_corner_path_x_first` | image `0x697b` | GR address association for SQ2 image `0x6603`; normalized static comparison matches. |
| `code.picture.cmd_draw_absolute_lines` | image `0x69be` | GR address association for SQ2 image `0x6646`; normalized static comparison matches. |
| `code.picture.cmd_draw_relative_lines` | image `0x69d6` | GR address association for SQ2 image `0x665e`; normalized static comparison matches. |
| `code.picture.cmd_seed_fill` | image `0x6a23` | GR address association for SQ2 image `0x66ab`; normalized static comparison matches. |
| `code.picture.cmd_set_pattern_mode` | image `0x689c` | GR address association for SQ2 image `0x6524`; normalized static comparison matches. |
| `code.picture.cmd_pattern_plot` | image `0x6877` | GR address association for SQ2 image `0x64ff`; normalized static comparison matches. |
| `code.picture.read_coord_pair` | image `0x6a30` | GR address association for SQ2 image `0x66b8`; normalized static comparison matches. |
| `code.picture.draw_line` | image `0x6a59` | GR address association for SQ2 image `0x66e1`; normalized static comparison matches. |
| `code.display.fill_buffer_word` | image `0x548a` | GR address association for SQ2 image `0x5257`; the memory fill skeleton matches, but GR omits SQ2's display-mode-2 overlay refresh call. |
| `code.display.draw_horizontal_line` | image `0x5498` | GR address association for SQ2 image `0x526f`; normalized static comparison matches. |
| `code.display.draw_vertical_line` | image `0x54d4` | GR address association for SQ2 image `0x52ab`; normalized static comparison matches. |
| `code.display.pixel_write` | image `0x5522` | GR address association for SQ2 image `0x52f9`; normalized static comparison matches. |
| `code.picture.seed_fill` | image `0x5564` | GR address association for SQ2 image `0x533b`; normalized static comparison matches. |
| `code.display.clear_logical_buffer` | image `0x5751` | GR address association for SQ2 image `0x5528`; normalized static comparison matches. |
| `code.display.full_refresh` | image `0x576f` | GR address association for SQ2 image `0x5546`; GR omits SQ2's display-mode-2 overlay refresh branch. |
| `code.object.build_update_list_sorted` | image `0x0351` | GR address association for SQ2 image `0x0358`; normalized static comparison matches. |
| `code.object.insert_update_node_head` | image `0x0428` | GR address association for SQ2 image `0x042f`; normalized static comparison matches. |
| `code.object.draw_update_list_tail_to_head` | image `0x0457` | GR address association for SQ2 image `0x045e`; normalized static comparison matches, but GR calls main-image rectangle save/draw routines instead of SQ2 overlay entries. |
| `code.object.refresh_update_list_saved_pos` | image `0x0481` | GR address association for SQ2 image `0x0488`; normalized static comparison matches. |
| `code.object.frame_timer_update` | image `0x055c` | GR address association for SQ2 image `0x0563`; differs by sending exactly-four-loop views directly through the four-plus direction table, but gating views with more than four loops on flag `0x14`. QEMU report `build/gr-v3-behavior/frame_selection_gate_qemu_001.json` validates exact-four view 177 selecting group 1 regardless of flag `0x14`, and more-than-four view 39 selecting group 1 only when flag `0x14` is set. |
| `code.object.advance_frame_by_mode` | image `0x4b0e` | GR address association for SQ2 image `0x48b3`; apparent straight-line differences are embedded jump-table bytes, while manually inspected branch bodies match as relocated skeletons. |
| `code.object.collision_test` | image `0x4974` | GR address association for SQ2 image `0x4719`; normalized static comparison matches. |
| `code.object.control_acceptance` | image `0x58e5` | GR address association for SQ2 image `0x56b8`; normalized static comparison matches. |
| `code.object.update_dirty_rect` | image `0x598f` | GR address association for SQ2 image `0x5762`; normalized static comparison matches. |
| `code.object.place` | image `0x5cb3` | GR address association for SQ2 image `0x593a`; normalized static comparison matches. |
| `code.object.build_active_update_list` | image `0x6d9e` | GR address association for SQ2 image `0x6a26`; normalized static comparison matches. |
| `code.object.build_inactive_partition_list` | image `0x6db5` | GR address association for SQ2 image `0x6a3d`; normalized static comparison matches. |
| `code.object.flush_update_lists_restore` | image `0x6dcc` | GR address association for SQ2 image `0x6a54`; normalized static comparison matches. |
| `code.object.rebuild_draw_update_lists` | image `0x6e06` | GR address association for SQ2 image `0x6a8e`; normalized static comparison matches. |
| `code.object.refresh_update_lists` | image `0x6e23` | GR address association for SQ2 image `0x6aab`; normalized static comparison matches. |
| `code.object.clear_root_16ff_membership` | image `0x6ebc` | GR address association for SQ2 image `0x6b44`; normalized static comparison matches. |
| `code.object.set_root_16ff_membership` | image `0x6eda` | GR address association for SQ2 image `0x6b62`; normalized static comparison matches. |
| `code.motion.update_objects` | image `0x1720` | GR address association for SQ2 image `0x150a`; normalized static comparison matches. |
| `code.motion.pre_mode_and_boundary_update` | image `0x0654` | GR address association for SQ2 image `0x0644`; normalized static comparison matches. |
| `code.motion.dispatch_mode_step` | image `0x068a` | GR address association for SQ2 image `0x067a`; GR accepts motion mode `4` and dispatches it to the same target-direction helper as mode `3` before falling through to the same boundary-check tail. Instrumented QEMU report `build/gr-v3-behavior/motion_mode_4_qemu_pic001_001.json` confirms this internal branch by patching a copied action-`0x51` setup byte from mode `3` to mode `4`. |
| `code.motion.rectangle_boundary_check` | image `0x06eb` | GR address association for SQ2 image `0x06d9`; apparent straight-line differences are embedded direction jump-table bytes, while manually inspected post-table body matches as a relocated skeleton. |
| `code.motion.seed_first_object_mode4_target` | image `0x1975` | GR helper-shaped code that writes object 0 byte `+0x22 = 4`, seeds target X/Y bytes `+0x27/+0x28`, and preserves the current step in `+0x29` when `data.motion.direction_mirror_selector_0139` is nonzero. A direct near-call scan found no ordinary call into this address in the local GR main image, so the natural entry path remains unresolved/source-only. |
| `code.object.save_rect_overlay_entry` | image `0x5b67` | GR packages the rectangle-save routine in the main executable image; SQ2 reaches this role through `IBM_OBJS.OVL:0x9db0`. |
| `code.object.restore_rect_overlay_entry` | image `0x5ba6` | GR packages the rectangle-restore routine in the main executable image; SQ2 reaches this role through `IBM_OBJS.OVL:0x9db3`. |
| `code.object.draw_overlay_entry` | image `0x5be3` | GR packages the selected-frame draw routine in the main executable image; SQ2 reaches this role through `IBM_OBJS.OVL:0x9db6`. |
| `data.resource.logic_dir` | GR data `[0x0fda]` | Loaded v3 logic directory section pointer. |
| `data.resource.view_dir` | GR data `[0x0fdc]` | Loaded v3 view directory section pointer. |
| `data.resource.picture_dir` | GR data `[0x0fde]` | Loaded v3 picture directory section pointer. |
| `data.resource.sound_dir` | GR data `[0x0fe0]` | Loaded v3 sound directory section pointer. |
| `data.menu.interaction_gate_0403` | GR data `[0x0403]` | Word written by GR-only action `0xb1`; `code.menu.interact` returns immediately while this word is zero. QEMU `menu_gate_suite` validates zero and nonzero observable branches. |
| `data.input.key_release_enqueue_gate_0405` | GR data `[0x0405]` | Byte set by GR action `0xad`, cleared by GR-only action `0xb5`, and tested by `code.input.keyboard_irq_hook` before selected key-release event enqueue. Local model `tools/agi_input.py` covers this gate against the shared latch state machine. |
| `data.input.prompt_marker_char` | GR data `[0x03f7]` | Relocated prompt-marker byte used by GR input-line redraw helpers. |
| `data.input.visible_buffer` | GR data `[0x0dc5]` | Relocated visible input buffer used by GR `code.input.handle_input_char` and refresh helpers. |
| `data.input.source_buffer` | GR data `[0x0def]` | Relocated accepted/source input buffer used by GR refresh and parser paths. |
| `data.input.visible_length` | GR data `[0x0e19]` | Relocated visible input length tested by GR input erase/append helpers. |
| `data.input.display_offset` | GR data `[0x11b1]` | Relocated display offset written by GR action `0x6f`; computed as `arg0 << 3`. |
| `data.text.input_line_enabled` | GR data `[0x03f3]` | Relocated input-line enabled word controlled by GR actions `0x77` and `0x78`. |
| `data.text.window_active_0b24` | GR data `[0x0b24]` | Relocated active text-window state consumed and cleared by GR `code.text.close_window_state`. |
| `data.text.window_saved_lower_right_0b2a` | GR data `[0x0b2a]` | Relocated packed saved-window rectangle word passed to GR rectangle restore helper. |
| `data.text.window_saved_upper_left_0b2c` | GR data `[0x0b2c]` | Relocated packed saved-window rectangle word passed to GR rectangle restore helper. |
| `data.inventory.selection_event_gate_0dc1` | GR data `[0x0dc1]` | Temporary word set while GR's interactive carried-item selector waits/handles events and cleared before action `0x7c` returns. |
