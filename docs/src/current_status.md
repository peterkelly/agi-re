# Current Status

This page is a short handoff note for resuming the clean-room reverse
engineering work.

## Current Focus

The final deliverable is the separate mdBook under `spec/`: a self-contained
description of externally observable AGI behavior suitable for an independent
implementation team. The existing `docs/` book remains the reverse-engineering
evidence record and may contain original implementation details. New findings
must continue to be documented in `docs/`, then promoted to `spec/` only as
portable behavioral contracts.

The logic bytecode catalog is complete for the current SQ2 interpreter. The
standalone specification now also covers picture commands, view/cel decoding,
object behavior, parser/input/menu/inventory behavior, sound command-output
behavior, and the room/replay/save state machine. All five observed profile
2.936 save blocks now have exhaustive block-relative maps. The profile
3.002.149 Gold Rush save map is also complete for the observed local save
envelope. Former opaque block-1 ranges are classified as reserved words,
inactive key-map/string records, and alignment bytes; the clean spec defines
canonical initialization and byte preservation. The subsystem/version
conformance matrix is now
present. The exact text-glyph bitmap question is now resolved as a font-profile
boundary: core compatibility specifies text cells, bytes, attributes, geometry,
and modal behavior, while bitmap-identical text screenshots must declare a font
set. The KQ4D/3.002.102 picture, view, and object-update comparison is now
complete. Fifty-two role pairs cover the primary full-EGA renderer/object path
and match Gold Rush after relocation; the remaining renderer differences are
alternate display-mode branches outside the target. The highest-value future
work is applying the completed workflow to newly supplied interpreter builds,
followed by any concrete renderer edge behavior that still affects the portable
full-EGA target.

The top-level 2.936 cycle is now instruction-backed and promoted as a portable
phase order. Timer and sound ticks are asynchronous inputs; synchronous work
orders pacing, transient input reset, input processing, direction mirroring,
pre-motion, logic-0 execution and immediate re-entry, status refresh, transient
cleanup, and the alternate-text-mode-gated object update.

Portable conformance bundles are no longer visual-only. In addition to the
canonical 160 by 168 EGA frame, a case may carry semantic JSON `values` for
state, input, ordered sound commands, and persistence outcomes. The comparator
validates portable JSON types and reports typed differences by semantic path,
without requiring DOS memory layouts or another implementation's object model.

KQ2/2.411 and LSL1/2.440 are now separate promoted profiles. Both end at action
`0xa9`, use exact-four-loop selection, lack later sound attenuation envelopes,
and serialize a `0x05df` first save block. KQ2 has point-only pattern commands,
always prompts for restart, and always emits both non-PC tone bytes. LSL1 has
the later brush patterns, honors the `f16` restart bypass, and conditionally
suppresses the low tone byte. KQ2 and LSL1 selected-game save dimensions are
mapped and confirmed from existing save files.

That same-version check is now complete. PQ1/KQ1 and KQ3/SQ2 have identical
action, condition, and subsystem code; their loaded images differ only in game
signature bytes. PQ1 and KQ3 save dimensions are mapped as selected-game data.
The new `tools/match_interpreter_roles.py` performs normalized first-pass role
relocation for future builds and reports unique, ambiguous, and unmatched
candidates for manual source review.

XMAS.230 is now identified as AGI 2.230 and has its own promoted full-EGA
profile. It is a source-backed hybrid of the neighboring early builds: its
position/composition/parser/save paths follow 2.272, while exit, motion-clear,
and sound output follow 2.089. Its unique view format packs cel count and
mutable orientation/mirroring state into the loop header; six selected view
resources exercise that path. The selected save dimensions are also mapped.

Full KQ4 is now separated from the KQ4D demo. The full game uses AGI
3.002.086, a 178-action range ending at `0xb1`, and a distinct promoted
profile. It combines the v3 inventory/save/restart/motion changes with the
earlier increment-style release gate, 39 key mappings, direct room targets,
and v2 input-width actions. Its two source-visible object variants are the
2.936 four-or-more-loop rule and a left-boundary report for an exact-zero X
proposal. Full KQ4 save dimensions are mapped as 26 object records, 45
inventory entries, and 250 replay pairs. KQ4D remains the later 3.002.102 demo
profile with its own smaller selected-game save dimensions.

KQ1/2.917 remains a promoted full-EGA profile. Its valid action range ends at
`0xad`; all shared action and condition handlers match 2.936. The sole
renderer/object delta in the 52-role pass is exact-four-loop automatic
selection, and the selected KQ1 save dimensions are mapped for binary
interchange.

The current top-level compatibility runner is `tools/compatibility_suite.py`.
The latest smoke report is
`build/compatibility-suite/qemu_smoke_002.json`, covering local tests, mdBook,
opcode-evidence freshness, parser QEMU probes, picture scanner command-resume
probes, raw command-looking operands, and relative-line underflow. The latest
broad report is `build/compatibility-suite/qemu_broad_002.json`, which includes
the smoke layer plus the eight-picture timed carousel and the 19-case
view/object stress carousel. Every selected command returned zero.

The user intentionally deleted `build/`. Those report paths are historical
generated-artifact locations rather than preserved project inputs. The source
tools and private `games/` inputs regenerate required fixtures and reports; no
specification evidence depends on retaining generated disk images or captures.

The latest resource-lifecycle source pass corrected an overly map-like clean
model. Picture and view retention is ordered within each family. Discarding a
selected retained resource clears that record and every later same-family
record; replay event kinds 6 and 7 reproduce the same truncation. Source shows
the family-link mutation and shared heap rewind directly, so no QEMU probe was
needed. The clean spec excludes continued use of a discarded payload and a
portable transition model now has focused regression coverage.

All current local logic resources were also scanned for discard usage. Every
profile uses picture or view discard, and KQ2 logic 67 provides a particularly
clear LIFO example: views `53,59,51,52,57,60` are later discarded as
`60,57,52,51,59,53`. This supports the valid-script discipline independently
of the executable source that proves the broader truncation effect.

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

- `spec/src/README.md`: entry point for the independent behavioral
  specification.
- `spec/src/resource_containers.md`: normative v2/v3 container and expansion
  contract.
- `spec/src/runtime_state.md`: normative portable state and cycle model.
- `spec/src/logic_bytecode.md`: complete normative condition/action catalog.
- `spec/src/picture_resources.md`: picture commands and exact raster rules.
- `spec/src/view_resources.md`: view/cel format, mirroring, and composition.
- `spec/src/object_behavior.md`: lifecycle, animation, movement, collision,
  control acceptance, and draw ordering.
- `spec/src/input_text_and_menus.md`: parser, events, text state, inventory,
  and menus.
- `spec/src/session_and_persistence.md`: room transitions, resource replay,
  save framing, restore, and restart.
- `spec/src/sound.md`: normative sound payload, scheduling, and output boundary.
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
- `tools/resource_reference_audit.py`: compares immediate script-visible
  resource references with the complete readable set for explicit local game
  directories, including absent and malformed entries.
- `tools/compare_interpreter_tables.py`: detects and compares dispatch-table
  contracts and normalized handler-entry shapes across two explicit local
  interpreter inputs.
- `tools/v3_object_encoding_probe.py`: builds copied unchanged/XOR-encoded
  inventory-metadata fixtures and can compare them in one QEMU snapshot run.
- `tools/logic_interpreter_probe.py`: QEMU logic-interpreter compatibility
  harness for small bytecode behavior probes.
- `tools/qemu_snapshot.py`: shared snapshot runner; fixtures can now request
  post-launch keystrokes for deterministic prompt/message probes.
- `tools/logic_opcode_evidence.py`: generator for the opcode evidence matrix.
- `tools/object_movement_probe.py`: QEMU movement/motion compatibility harness.
- `tools/object_overlay_probe.py`: QEMU object/view drawing compatibility
  harness.

## Immediate Next Work

1. Convert the fresh MH1/MH2 static winning-route specifications into
   deterministic original-interpreter replays. The terminal predicates and
   formerly missing late-game chains are now mapped; exact movement, report
   answers, and arcade/control inputs remain.
2. Continue v3 and other cross-version probes from source-mapped deltas only
   when the portable specification still has an observable ambiguity.
3. Keep source-first renderer work going only when disassembly reveals a
   concrete valid-stream edge. Use QEMU as confirmation or regression coverage,
   not as the primary discovery method.
4. Keep `tools/compatibility_suite.py` current as new local/QEMU evidence is
   promoted. Re-run `--include-qemu-smoke` or `--include-qemu-broad` when the
   manifest changes.
5. Continue assigning symbolic labels for helpers, globals, dispatch tables, and
   overlay entries so later interpreter versions can be compared by role rather
   than by absolute address.
6. Apply the cross-version workflow to the additional local interpreter/game
   inputs when a selected version can add or refine an observable spec variant.

## Deferred Or Conditional Work

The remaining open rows in `PROGRESS.md` are mostly conditional:

- Most mapped cross-version work is no longer blocked. Replacement MH1/MH2
  inputs close their resource gaps, and fresh static route analyses now cover
  their complete valid late-game scripts. Whole-game replay claims require
  deterministic input capture rather than additional source files. Other work
  should be prioritized by the value of an observed version difference to the
  behavioral spec.
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

Use `PROGRESS.md` as the completion dashboard and `spec/src/` as the normative
source. Use `docs/src/clean_room_executable_notes.md` when the exact evidence
trail or command history is needed.
