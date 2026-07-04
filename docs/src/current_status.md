# Current Status

This page is a short handoff note for resuming the clean-room reverse
engineering work.

## Current Focus

The most recent work returned to the logic interpreter. The opcode catalog now
has a test-backed coverage check against `tools/disassemble_logic.py`, and the
QEMU-backed logic batches validate jump, false-branch, inversion, OR-group,
variable, flag, comparison, arithmetic, selected object-field behavior,
logic load/call variants, variable-backed resource/object variants, object
rectangle predicates, string/message parsing, inventory/object marker
operations, resource lifecycle paths, message display helpers, typed numeric
input, string prompt editing, formatted text display, input-line/text-window
dispatch, text/status configuration dispatch, diagnostic/status message
actions, menu/list dispatch, sound load/clear dispatch, and additional
object/view getter and bitfield dispatch behavior through visible output.
The latest source-first pass refined the remaining lifecycle families and added
QEMU coverage for room-switch re-entry: room switches intentionally return zero
to force an immediate logic-0 re-entry, then logic 0 can dispatch the current
room with `call_logic_var(v0)`. Follow-up QEMU probes now also validate current
room `v0`, previous room `v1`, cleared boundary selector `v2`, and all four
`v2` entry-boundary placements for object 0 on both immediate and
variable-selected room-switch paths. A persistent object activated before the
switch is also QEMU-validated as absent from the destination-room render. A
follow-up source pass corrected the exact room-switch reset model: object bytes
`+0x1e`, `+0x1f`, and `+0x20` are seeded to `1` rather than cleared, and the
room cache reset preserves the first logic cache record while clearing
view/picture/sound cache roots. The resource-event replay log is now
source-mapped as a two-byte `(kind, value)` pair buffer with capacity/count,
read/write cursors, recording gates, event kinds `0..8`, and a special
four-pair transient-display-object packet for kind `5`. Menu arrow navigation
consumes type-2 movement events, save/restore selection is separated from
block I/O, restore replays saved resource events with recording disabled, and
the direct static scan has not found a matching event-recording re-enable in
the restore or display-mode replay callers. A QEMU display-mode replay memory
probe did observe recording enabled again after the following script action, so
the duplicate-prevention role is source-backed but the exact post-replay
re-enable timing remains unresolved. Sound completion flags are only set by the
stop helper when active sound state is nonzero.

## Confirmed Motion and Object Findings

- Persistent object movement has a QEMU-backed 17-case batch in
  `build/object-movement-probes/batches/motion_modes_004.json`; the batch
  matched with 17 matches, 0 mismatches, and 0 errors.
- `0x51` (`move_object_to`) and `0x52` (`move_object_to_var`) can complete in
  two ways:
  - script logic can reissue the setup action each interpreter cycle while the
    completion flag is clear;
  - a one-shot setup can complete through the countdown-gated dispatcher
    `0x067a -> 0x1672` when object byte `+0x01` is ready.
- `0x53` (`approach_first_object_until_near`) is validated for direct
  autonomous completion with step `5`, countdown byte `+0x01 = 1`, threshold
  `35`, and object 1 stopping at `(50,80)` while object 0 is at `(80,80)`.
- `0x54` (`start_random_motion`) has a property-style QEMU probe: the object
  must render exactly at some valid final position. The recorded run ended at
  `(140,112)`.
- `0x4e` (`clear_object_field_22_and_global`) has a focused QEMU probe for its
  visible mode-byte effect: after `0x54` starts random motion, `0x4e` clears
  object byte `+0x22`, and the object remains at `(60,80)`.
- Object-object collision helper `0x4719` is documented: moving-object bit
  `0x0200` skips the test, candidates need active/update flags, equal grouping
  byte `+0x02` is skipped, then horizontal overlap and Y equality/crossing are
  tested. A follow-up QEMU probe validates that action `0x44` clears this skip
  bit and restores the default collision stop.
- Horizon-like placement is QEMU-validated for `[0x012d] = 100`: with bit
  `0x0008` clear, an object placed at baseline `80` clamps to `101`; action
  `0x3d` exempts the object and action `0x3e` restores the clamp.
- Fixed-priority clearing is QEMU-validated: after `0x36` fixes an object's
  priority/control byte to `5`, action `0x38` clears bit `0x0004`; at baseline
  `80`, the object derives priority `7` and draws over a control-6 background.
- Control/priority acceptance bits now have focused QEMU probes. `0x58` and
  `0x59` set/clear bit `0x0002`, bypassing or restoring a rectangle-boundary
  crossing stop. `0x40` and `0x41` set bits `0x0100` and `0x0800`, blocking
  movement over full control-class-2 or control-class-3 pictures for a
  priority-14 object; `0x42` clears those bits and restores movement.
- Approach stuck recovery in `0x0b36` is source-backed: when bit `0x4000`
  reports no movement, the helper chooses a random nonzero direction and stores
  a retry delay in `+0x29`.
- Object frame-cycling is now modeled from static disassembly: `0x4c` seeds
  timer bytes `+0x1f`/`+0x20`, bit `0x0020` enables the countdown, and
  `code.object.advance_frame_by_mode` interprets modes `0..3` as forward loop,
  forward-to-last completion, backward completion, and backward loop. QEMU
  batch `frame_timer_001` validates visible mode-1 advancement and the
  `0x46`/`0x47` bit gate; batch `frame_timer_modes_002` validates visible
  modes 0, 2, and 3 for actions `0x48`, `0x4b`, and `0x4a`.
- Object update-list partitioning is now source- and QEMU-backed. Bit `0x0010`
  selects root `0x16ff` versus root `0x1703`; actions `0x3a` and `0x3b` move
  active objects between those partitions, and `0x3c` performs a global
  list-refresh pass. QEMU batch `object_root_partition_004` validates the
  visible draw-order effect with overlapping view-11 objects.
- Object bit `0x2000` is source- and QEMU-backed as the suppressor for
  automatic direction-based group selection in `code.object.frame_timer_update`.
  QEMU batch `object_bit_2000_002` validates that clearing the bit with `0x2e`
  lets direction `6` select view 4 group 1, while setting it with `0x2d` keeps
  the same object on group 0. Follow-up batch `object_bit_2000_004` validates
  the two/three-group table, sentinel group value `4`, countdown-to-1 timing,
  and the exact `+0x01 == 1` gate.
- The top-level cycle is source-mapped at `code.engine.main_cycle` (`0x0150`):
  a pre-logic motion/boundary pass at `0x0644` runs before logic 0, while
  `code.object.frame_timer_update` (`0x0563`) runs after logic 0 unless byte
  `[0x1757]` is nonzero.
- Rectangle-boundary actions `0x5a` and `0x5b` now have QEMU-backed movement
  evidence. Existing rectangle-boundary probes validate `0x5a`; batch
  `rect_bounds_clear_001` validates that `0x5b` clears the bounds and restores
  target arrival.

## Confirmed Graphics and View Findings

- Object overlay probes have a QEMU-backed 22-case batch in
  `build/object-overlay-probes/batches/view_cel_selection_002.json`; the batch
  matched with 22 matches, 0 mismatches, and 0 errors.
- View 11 group/frame selection has been validated beyond the first cel:
  group 0 frame 1, group 1 frame 0, and group 1 frame 1 all match the local
  renderer.
- Existing docs cover view resource layout, selected group/frame pointers,
  transparent-color behavior, bit-`0x80` orientation rewriting, priority/control
  draw gating, top/right/bottom placement adjustments, and persistent
  object-table drawing.

## Useful Files

- `docs/src/logic_bytecode.md`: main opcode and interpreter bytecode reference.
- `docs/src/logic_opcode_evidence.md`: generated opcode evidence matrix with
  QEMU/source-backed/reserved status for every action and condition row.
- `docs/src/logic_resources.md`: logic resource format and decoded script notes.
- `docs/src/graphics_object_pipeline.md`: object records, motion, view drawing,
  and update pipeline.
- `docs/src/compatibility_testing.md`: QEMU and Python test commands.
- `docs/src/clean_room_executable_notes.md`: chronological command/evidence log.
- `docs/src/symbolic_labels.md`: symbolic address map for comparing interpreter
  versions.
- `tools/disassemble_logic.py`: local logic bytecode disassembler.
- `tools/logic_interpreter_probe.py`: QEMU logic-interpreter compatibility
  harness for small bytecode behavior probes.
- `tools/qemu_snapshot.py`: shared snapshot runner; fixtures can now request
  post-launch keystrokes for deterministic prompt/message probes.
- `tools/logic_opcode_evidence.py`: generator for the opcode evidence matrix.
- `tools/object_movement_probe.py`: QEMU movement/motion compatibility harness.
- `tools/object_overlay_probe.py`: QEMU object/view drawing compatibility
  harness.

## Immediate Next Work

Return to the logic interpreter:

1. Expand `tools/logic_interpreter_probe.py` beyond control-flow bytes into
   additional action/condition groups that can expose state through pictures,
   transient objects, variables, flags, strings, and object fields. The current
   filtered QEMU batches cover the core variable/flag/comparison family,
   selected object fields, call/load/resume smoke behavior, var-backed resource
   setup, object predicates, string/message operations, and inventory marker
   operations. The object/view follow-up adds QEMU value probes for
   `0x31..0x35`, `0x37`, `0x45`, and `0x4d`; the root-partition follow-up
   promotes `0x3a`, `0x3b`, and `0x3c` to behavior evidence through visible
   update-list ordering. The bit-`0x2000` follow-up promotes `0x2d` and `0x2e`
   through automatic direction/group selection on view 4 and view 5, including
   sentinel and countdown-gate behavior. The subsequent
   object-state/misc batch adds
   QEMU-backed evidence for `0x22`, `0x24`, `0x28`, `0x7f`, `0x82`, `0x93`,
   `0x94`, `0x9b`, and `0xaf`; notably, `0x22` clears bits but does not
   immediately unlink an already activated current-cycle draw entry. The latest
   small batch adds QEMU evidence for variable-selected view loading (`0x1f`);
   the frame-timer batches add behavior evidence for object frame actions
   `0x46..0x4c`, including visible mode coverage for `0x48`, `0x4a`, and
   `0x4b`.
2. Prefer QEMU fixture evidence for additional opcodes whose behavior can be made
   visible. Resource lifecycle, message display, string/numeric input,
   formatted/positioned text, input-line/window dispatch, text/status
   configuration dispatch, selected diagnostics, menu dispatch, priority screen,
   object diagnostics, log-file content, and sound load/clear/stop-flag behavior
   now have targeted coverage; most remaining source-backed rows are
   key-map event conversion, `0x74` string-table copying in a non-empty table,
   selection UI, save/restore/restart, deeper room/system transition side
   effects, and full interactive menu/audio paths.
3. Extend the room-switch probes from the now-matched re-entry fixture. Useful
   follow-ups are QEMU validation of restore replay for selected event-log
   packets and object/resource reset details after the destination room logic
   performs its own entry setup.
4. For menu navigation, target type-2 movement event injection rather than
   relying on QEMU monitor `sendkey down` to behave like the interpreter's
   expected BIOS scan-word path.
5. Continue assigning symbolic labels to interpreter helpers, object globals,
   and scanner paths so later interpreter versions can be compared by role
   rather than by absolute address.

## Remaining Source-Backed Families

After the latest object/timing pass, the remaining source-backed action rows
cluster into families that need specialized probes:

- **Room/resource lifecycle:** `0x12` and `0x13` are broad room/state switch
  paths. Several early QEMU fixture attempts failed to produce stable reusable
  evidence: direct room-variable assertions, target-logic drawing, and a
  logic-0 re-entry fixture that restored the logic entry IP with `0x92` before
  switching. The matched fixture now preserves the helper's zero-return path:
  logic 0 sets an init flag before the switch, the main cycle immediately
  re-enters logic 0, and logic 0 calls `call_logic_var(v0)` to invoke a
  destination room logic that performs its own picture/view setup under flag 5.
  This validates the room-switch re-entry/current-room dispatch shape for both
  immediate and variable-selected room actions. A newer two-case batch
  validates the current/previous/boundary variable update: both `0x12` and
  `0x13` copy old `v0` to `v1`, write destination room 1 into `v0`, and clear
  `v2`. Two four-case batches validate `v2` entry-boundary placement for both
  immediate and variable-selected room switches: selector `1` sets object 0 Y
  to `0xa7`, selector `2` sets X to `0`, selector `3` sets Y to `0x25`,
  selector `4` sets X to `0xa0 - object_width`, and all four clear `v2`.
  A two-case object-reset batch validates that a persistent object activated
  before the switch is absent from the destination-room render for both
  opcodes. Deeper side effects are source-backed from the latest disassembly
  pass: every object record clears bits `0x0001`/`0x0040`, sets `0x0010`,
  clears pointer fields `+0x08`/`+0x10`/`+0x14`, and stores `1` into
  `+0x00`/`+0x01`/`+0x1e`/`+0x1f`/`+0x20`; room cache reset preserves the first
  logic cache record and clears view, sound, and picture cache roots.
  Destination logic load is source-mapped. Resource/event recording is also
  source-mapped: `0x14`/`0x15`, `0x1e`/`0x1f`, `0x18`, `0x62`, picture
  prepare/overlay/discard, view discard, and transient-display-object setup
  feed restore replay through `code.event.record_pair`; actions `0x81`/`0xa2`
  explicitly disable recording for temporary preview work. `0x15`, `0x1b`,
  `0x1c`, `0x20`, and `0x99` also have targeted QEMU-backed lifecycle
  fixtures.
- **Text/window/input:** `0x65`, `0x66`, `0x67`, `0x68`, `0x6a`, `0x6b`,
  `0x6c`, `0x6d`, `0x6e`, `0x6f`, `0x70`, `0x71`, `0x73`, `0x76`, `0x77`,
  `0x78`, `0x79`, `0x89`, `0x8a`, `0x97`, `0x98`, `0x9a`, and `0xa9` now have
  QEMU behavior or dispatch-smoke evidence. The string editor helper is
  statically mapped at `code.input.edit_string` and dynamically validated for
  accepting `look` into a string slot. The follow-up behavior batch validates
  `0x6f` nonzero display-offset semantics, `0x79` mapped-key event conversion
  through condition `0x0c`, and `0x74` string-table copying using a synthetic
  fixture-local table entry because the sampled SQ2 table is zero-filled.
- **Menus and inventory UI:** `0x7c` now has QEMU behavior evidence for
  interactive Enter, interactive Escape, and noninteractive acknowledgement.
  The selection result is absolute byte `DS:0x0022`, exposed as script variable
  `0x19`. `0x9c..0xa1` now have behavior evidence for setup, Escape without
  status, disabled-item Enter without status, re-enable, and one-item Enter via
  condition `0x0c 7`. Further menu work should cover heading movement and
  arrow-key navigation; a down-arrow QEMU fixture was attempted but did not
  reach the expected second-item event. A separate raw-key mapping attempt for
  `0x5000` with QEMU monitor `sendkey down` also failed to set a mapped status
  byte, so this is currently an input-instrumentation gap. `0xa2` now has
  view-resource display coverage. The source event path is now mapped more
  tightly: BIOS keys drain into a 20-record queue, raw arrow/keypad words are
  enqueued as type-2 movement events, display-adapter keypad bytes can be
  remapped to type-2 movement events, and menu interaction dispatches movement
  values 1..8 through a navigation table while persisting current heading/item
  globals.
- **Save/restore/restart/system:** `0x7d`, `0x7e`, `0x80`, `0x86`, `0x8b`,
  `0x8c`, `0x8f`, `0x95`, and `0x96` now have focused QEMU coverage for
  cancel/no-op/signature/gated-trace paths. `0x1d` now has priority-screen
  return coverage. `0x90` has file-content evidence from a post-run DOS image:
  the extracted `LOGFILE` contains the expected room/input/message record. The
  source model now separates selector UI from file I/O: helper `0x85e5`
  handles save/restore path selection and returns zero on cancel; save writes
  length-prefixed engine/object/inventory/resource-event/logic-cache blocks;
  restore reads the same block families and calls restore-time resource-event
  replay at `0x681c`.
- **Sound:** `0x62`, `0x63`, and `0x64` now have dispatch-smoke evidence using
  load/start/stop on sound resource 1, and `0x64` has behavior evidence for
  setting the completion flag configured by `0x63`. Exact audio output and
  asynchronous playback lifetime remain source-backed. Source inspection shows
  `0x63` stops prior sound before storing/clearing the completion flag and
  calling the driver start helper for an already loaded sound record; `0x64`
  sets the configured completion flag only when active-state word `[0x1258]`
  is nonzero.
- **Diagnostics/global toggles:** `0x83`, `0x84`, `0x87`, `0x88`, `0x8d`,
  `0x8e`, `0xa3`, `0xa4`, and `0xaa..0xad` now have QEMU message or
  dispatch-smoke evidence. `0x81` is covered together with `0xa2`; `0x85` now
  has QEMU return-to-bytecode evidence for the object diagnostics display.
