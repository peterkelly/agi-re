# Current Status

This page is a short handoff note for resuming the clean-room reverse
engineering work.

## Current Focus

The logic bytecode catalog is complete for the current SQ2 interpreter: all
action and condition opcode rows have either QEMU-backed behavior evidence or a
source-backed explanation where the behavior is outside the current full-EGA
dynamic target. The main remaining work is no longer "find an opcode"; it is to
keep converting the accumulated source/QEMU observations into implementation
contracts, broaden renderer compatibility where valid local data still exposes
edge cases, and keep the test harness ready for future interpreter versions.

The current top-level compatibility runner is `tools/compatibility_suite.py`.
The latest smoke report is
`build/compatibility-suite/qemu_smoke_002.json`, covering local tests, mdBook,
opcode-evidence freshness, parser QEMU probes, picture scanner command-resume
probes, raw command-looking operands, and relative-line underflow. The latest
broad report is `build/compatibility-suite/qemu_broad_002.json`, which includes
the smoke layer plus the eight-picture timed carousel and the 19-case
view/object stress carousel. Every selected command returned zero.

Recent source-first renderer work corrected picture relative-line endpoint
semantics: handler `0x665e` computes relative deltas in 8-bit coordinate
registers, then clamps only above `x=0x9f` or `y=0xa7`. A negative underflow
therefore reaches the right or bottom edge rather than zero. QEMU batch
`relative_underflow_001` and the current smoke suite validate this. The object
control-acceptance helper `0x56b8` also has tighter local source-model tests for
the "other nonzero high nibble" branch and priority-15 scan bypass/event-flag
clearing.

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
- Picture renderer parity is much broader now: real-picture snapshot batches
  cover pictures 1/45, the broad 8-picture preset, and all 74 valid local SQ2
  picture resources. The chunked timed polling carousel also matched all 74
  valid local SQ2 picture resources across five engine launches.
- The active compatibility suite's broad picture carousel matches the 8-picture
  preset from one engine process, and the view/object stress carousel matches
  19 base-plus-stress view/cel cases.
- Source-backed picture edge tests now include raw command-looking operands for
  `0xf0`, `0xf2`, and `0xf9`, command-byte resume for coordinate/list readers,
  byte-width diagonal-line accumulators, lower-right pattern linear writes,
  pattern channel masks, seed-fill target-channel behavior, and relative-line
  underflow for `0xf7`.
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
- `docs/src/sound_and_audio.md`: sound resource format, playback scheduling,
  completion flags, and driver output boundary.
- `docs/src/compatibility_testing.md`: QEMU and Python test commands.
- `docs/src/clean_room_executable_notes.md`: chronological command/evidence log.
- `docs/src/symbolic_labels.md`: symbolic address map for comparing interpreter
  versions.
- `tools/disassemble_logic.py`: local logic bytecode disassembler.
- `tools/game_census.py`: read-only multi-game resource/version/layout census
  for explicit local game directories.
- `tools/logic_interpreter_probe.py`: QEMU logic-interpreter compatibility
  harness for small bytecode behavior probes.
- `tools/qemu_snapshot.py`: shared snapshot runner; fixtures can now request
  post-launch keystrokes for deterministic prompt/message probes.
- `tools/logic_opcode_evidence.py`: generator for the opcode evidence matrix.
- `tools/object_movement_probe.py`: QEMU movement/motion compatibility harness.
- `tools/object_overlay_probe.py`: QEMU object/view drawing compatibility
  harness.

## Immediate Next Work

1. Keep source-first renderer work going only when disassembly reveals a
   concrete valid-stream edge. Use QEMU as confirmation or regression coverage,
   not as the primary discovery method.
2. Continue turning dense subsystem notes into implementation-ready contracts in
   `docs/src/runtime_model.md`, `docs/src/graphics_object_pipeline.md`, and
   subsystem-specific chapters.
3. Keep `tools/compatibility_suite.py` current as new local/QEMU evidence is
   promoted. Re-run `--include-qemu-smoke` or `--include-qemu-broad` when the
   manifest changes.
4. Continue assigning symbolic labels for helpers, globals, dispatch tables, and
   overlay entries so later interpreter versions can be compared by role rather
   than by absolute address.
5. Defer cross-version comparison and broader real-resource parity until
   additional local interpreter/game inputs are available.

## Deferred Or Conditional Work

The remaining open rows in `PROGRESS.md` are mostly conditional:

- Cross-version comparison is blocked until additional local interpreter/game
  inputs are available.
- Non-EGA display/input paths are outside the current full-EGA compatibility
  target unless another local interpreter version requires them.
- Menu arrow navigation and a few UI paths would benefit from direct event
  injection or a more precise keyboard harness; the source model is currently
  stronger than the QEMU input path for those details.
- Analog sound synthesis is outside the interpreter boundary currently being
  specified; the useful model is the source-backed scheduler and port-output
  behavior.
- Out-of-memory, invalid-path, and other error UI cases should be added only if
  they become necessary for the final compatibility suite.

Use `PROGRESS.md` as the completion dashboard and the subsystem chapters as the
normative source. Use `docs/src/clean_room_executable_notes.md` when the exact
evidence trail or command history is needed.
