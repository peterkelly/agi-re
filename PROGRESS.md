# Reverse Engineering Progress

This is the high-level completion tracker for the clean-room AGI/SQ2 reverse
engineering project. It is intentionally more compact than the mdBook evidence
chapters: use it to see what is done, what is partial, and what still needs
work.

The current evidence set remains SQ2-centered, but tooling must not default to
SQ2. Select the local game/interpreter input explicitly with `--game-dir PATH`
or `AGI_GAME_DIR=PATH` so future LSL1/KQ4/etc. comparisons can reuse the same
tracker shape.

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

- Logic action opcodes: all 176 of 176 are covered at `[x]` level
  (`170` QEMU-validated, `0x00` structural, and
  `0x6e`/`0x83`/`0x8e`/`0xaa`/`0xad` source-backed).
- Logic condition opcodes: all 19 of 19 are QEMU-validated.
- A persistent SQ1.22 interpreter controller now owns visible QEMU through QMP
  and GDB, stops at every 2.917 cycle boundary, exposes variables, flags,
  objects, inventory, logic-cache state, visual/priority buffers, screenshots,
  modal detection, semantic input, predicates, and checkpoints over localhost
  HTTP. Profile-specific packaging, memory decoding, logical-screen handling,
  and modal recognition now sit behind an explicit adapter boundary. The
  generic orchestration layer adds postcondition-driven idempotent
  transactions, guarded waits and waypoint movement, baseline-footprint
  priority routing, key-release reconciliation, sequenced state/input traces,
  stable dialog identities, and atomic cycle recording bundles. A clean live
  validation exercised cycle-to-string and string-to-cycle transitions,
  transaction replay, live priority planning, no-input dialog dismissal,
  checkpoint restoration/cache invalidation, and repeated captures at one
  state revision. QEMU's observed one-breakpoint real-mode limit is handled by
  stack-classified hook switching.
- Main remaining risk areas: concrete picture/view edges exposed by future
  valid resources, compatibility-bundle breadth across additional versions,
  optional canonical initial save bytes for pristine 2.089/2.272 save
  synthesis, and conditional error paths. All currently promoted subsystems
  have standalone behavioral-specification chapters.
- Picture/view resource retention is now source-modeled as ordered within each
  family. Discard actions truncate the selected resource and every later
  same-family retention; restore replay kinds 6 and 7 reproduce that ordering.
  A portable transition model and local regression tests guard the rule. A
  nine-game script audit finds real use in every profile and an exact LIFO
  six-view unwind in KQ2 logic 67.
- Cross-version comparison has begun with Gold Rush (`games/GR`) / AGI v3:
  resource directory and volume compression differences are source-backed,
  locally decoded, and documented. Static opcode/subsystem comparison against
  SQ2 now has a repeatable helper and report; GR's extra action slots
  `0xb0..0xb5` are source-backed from disassembly, while only shared condition
  entries `0x00..0x12` are structured table records in the observed
  `AGIDATA.OVL`. Dynamic v3 delta probes now QEMU-validate the Gold Rush
  build's action `0x12` remapping immediate room targets `0x7e..0x80` to
  `0x49`, the expanded key-map
  slot count, the GR frame-selection gate, blank-prefix and signature-prefixed
  GR save extractions whose third block round-trips through the observed v3 XOR
  transform, a signature-prefixed GR restore round trip that returns through
  restored script state, the restart-cancel prompt-marker redraw branch, the
  GR menu interaction gate, and the motion-mode `4` dispatcher branch. The
  motion-mode probe is explicitly instrumented: it patches a copied GR
  interpreter under `build/` so action `0x51` seeds mode `4` instead of mode
  `3`, then compares the resulting capture with the unmodified mode-3 capture
  and a stationary control.
- KQ4D / 3.002.102 now has a promoted full-EGA profile. Generic static table
  comparison finds identical operand contracts for all 182 actions and 19
  conditions versus GR, with 12 shared-action handler differences. Direct SQ2
  comparison reduces those to five v3 deltas: inventory temporary state, save
  block-3 XOR, restart prompt handling, motion-mode-4 preservation, and the
  set-style release gate. KQ4D otherwise retains 2.936 room/input-width behavior
  and a 39-entry key map. Its source-derived KQ4D demo save dimensions are
  mapped. A 52-role KQ4D/GR source comparison now covers view loading and cel
  selection, picture lifecycle and every command/raster helper, object lists,
  animation, placement, collision, control acceptance, dirty rectangles, and
  motion. Primary full-EGA paths match after relocation; the only renderer
  deltas are retained alternate display-mode branches outside the target.
- Full KQ4 / 3.002.086 now has a distinct promoted full-EGA profile. Its
  geometry-derived v3 table contains 178 actions `0x00..0xb1`, rather than the
  KQ4D demo's 182 actions. All shared parser contracts match KQ4D; action
  `0xad` retains increment semantics, `0xb0` consumes one ignored byte, and
  `0xb1` sets the menu gate. A 52-role source comparison finds two observable
  object deltas: KQ4 uses the 2.936 four-or-more-loop rule and reports the left
  boundary when a due proposed X coordinate is exactly zero. The selected
  full-game save dimensions are mapped as 26 object records, 45 inventory
  entries, and 250 replay pairs, with the v3 block-3 XOR transform.
- KQ1 / 2.917 now has a promoted full-EGA profile. Decryption with KQ1's own
  loader key exposes 174 actions `0x00..0xad` and 19 conditions; every shared
  handler and parser contract matches 2.936. A 52-role subsystem pass finds one
  observable runtime delta: automatic direction-based selection uses the
  four-loop table only for exactly four loops, not for larger loop counts. The
  selected KQ1 five-block save dimensions are mapped, including 18 object
  records, 27 inventory entries, and 100 replay pairs.
- KQ2 / 2.411 and LSL1 / 2.440 now have separate promoted full-EGA profiles.
  Both expose 170 actions `0x00..0xa9`, 19 conditions, exact-four-loop object
  selection, and the shortened `0x05df` save block 1. KQ2's `0xf9` ignores its
  operand and `0xfa` plots single pixels; LSL1 implements the later brush
  patterns. KQ2 always prompts for restart and always emits both non-PC tone
  bytes; LSL1 honors the `f16` restart bypass and conditionally suppresses the
  low tone byte. Both early sound drivers lack attenuation envelopes and treat
  only selector zero as single-channel. KQ2 and LSL1 save dimensions are
  mapped and confirmed against five existing saves.
- Same-version checks now anchor PQ1 to 2.917 and KQ3 to 2.936. PQ1/KQ1 loaded
  images differ at only three game-signature bytes; KQ3/SQ2 differ at only two.
  Every action, condition, and 55-role subsystem entry matches at the same
  address. PQ1 and KQ3 selected-game save dimensions are mapped separately.
  `tools/match_interpreter_roles.py` now automates first-pass normalized role
  relocation for future builds while leaving ambiguous and unmatched entries
  for source inspection.
- Seven additional local inputs are inventoried. BC 2.439 matches the mapped
  LSL1 2.440 full-EGA core; MG 2.915 matches the mapped KQ1 2.917 core; and
  SQ1.22's 2.917 loaded image differs from KQ1 only in three signature bytes.
  The replacement MH1 uses 3.002.102: its AGIDATA is byte-identical to KQ4D
  and its AGI differs only at two game-signature bytes. The previously audited
  MH1 3.002.107 remains historical version evidence. MH2 provides
  a same-version 3.002.149 control for Gold Rush: the two loaded images differ
  by only 29 classified bytes, proving that room aliases `0x7e..0x80 -> 0x49`
  are Gold Rush-specific rather than universal to 3.002.149.
- SQ1 2.089 and XMAS 2.272 now have broad source-backed profiles. SQ1 accepts
  actions only through `0x9a`; its `0x86` is a zero-operand unconditional exit.
  XMAS accepts through `0xa0`; its `0x86` has the later selector, while menu
  actions `0x9c..0xa0` are operand-consuming no-ops. Their `OBJECT` files are
  plain expanded metadata rather than repeating-key XOR data. A source pass
  also records their drawn-object position-update ordering difference. Both
  stop picture command dispatch at `0xf8`, select automatic direction loops
  independently of movement cadence, expose six string slots, and use the
  early one-versus-four-channel sound scheduler. SQ1 has exact-count word
  matching, device-2-adjusted direct sound control bytes, 17 runtime object records, and a
  four-block save envelope. Its earlier-drawn object partition retains object
  number order while its later partition is drawing-key sorted. XMAS adds the
  `0x270f` tail terminator, whole-byte
  sound-control adjustment, 18 runtime object records, and a five-block save
  envelope, and drawing-key sorts both object partitions. Their movement,
  collision, control-acceptance, placement, frame-advance, and dirty-region
  cores otherwise match after relocation. XMAS's
  active files are the original multi-disk distribution variant, whose disk
  number nibbles and single selected `VOL.0` are not an installed-layout
  missing-volume error.
  Both early profiles defer the first target-motion direction/completion pass,
  retain `f15` and active text-window state when showing a picture, and wrap
  active-object distance to one byte instead of saturating it. SQ1 additionally
  leaves autonomous motion active in actions `0x4d` and `0x4e`; XMAS clears it.
  Both expose only the acknowledgement-only inventory display and never write
  an inventory selection to `v25`.
- Original saves add selected-game dimensions for BC, MG, and SQ1.22. BC uses
  blocks `0x05df`, `0x02db`, `0x0135`, and `0x00fe`; MG uses `0x05df`,
  `0x0387`, `0x0005`, and `0x00dc`; SQ1.22 uses `0x05e1`, `0x0306`,
  `0x0148`, and `0x0064`. All retain the variable fifth-block grammar. BC and
  SQ1.22 dimensions agree with decoded metadata. MG's mismatch is an
  artifact-version conflict: its save predates its interpreter and has
  incompatible block-1 and object-block lengths. The current interpreter/data
  derive 91 object records, so the older 21-record save is not a current
  binary-interchange oracle.
- Generated original-engine fixture builders now treat `games/` as immutable:
  they copy the selected game input to a generated destination, make copied
  files writable, and reject fixture destinations under `games/`. The v2
  builders still cover the existing split-directory harnesses. The v3 writer
  can now patch copied Gold Rush-style combined directories and prefixed
  volumes with direct logic/view records plus picture-nibble picture records,
  and QEMU confirms that the original GR interpreter renders a generated
  picture-only fixture and a generated picture-plus-view fixture distinctly.
- A read-only multi-game census tool now inventories explicit local game
  directories without modifying `games/`. The current private-input snapshot
  covers sixteen local games/builds, identifying v2 split and v3 combined
  layouts, version strings, resource counts, transform mixes, and record-header
  errors that require later source inspection before they are modeled.
  `tools/disassemble_logic.py` now detects per-build action/condition
  table bases from the observed argc/meta signatures, including KQ4D v3 bases
  `0x0620`/`0x0942`. `tools/resource_reference_audit.py` now checks immediate
  script-visible resource references against unreadable directory entries; the
  current focused audits find no immediate reference to unreadable KQ1/KQ4D
  sound entries or KQ4's missing-volume picture/view entries. KQ4 picture
  selection is variable-based, so that last result is not a reachability proof.
  The replacement MH1/MH2 copies close the previous resource blocker: all 66
  and 96 present logics decode, all present pictures/views decode, and every
  statically addressable resource is readable. Each directory has two
  unreferenced anomalous sound-tail entries outside valid-game semantics.
  The audit now reports references to absent entries as well as malformed
  present entries, and its corrected operand map treats `set.loop` as
  non-resource state while reading `add.to.pic`'s first operand as the view.

## Behavioral Specification Coverage

- [x] Clean-room scope and conformance boundary
  - Current: `spec/src/scope_and_conformance.md` defines externally observable
    behavior, valid-data scope, version variants, nondeterminism, and the
    separation from the evidence book.
- [x] Version profiles
  - Current: `spec/src/version_profiles.md` defines the primary 2.936 profile
    and promoted full-EGA 2.089, 2.272, 2.411, 2.440, 2.917, 3.002.086,
    3.002.102, and 3.002.149 profiles. SQ1, XMAS, KQ2, LSL1, KQ1, full KQ4,
    KQ4D, and Gold Rush supply mapped profile-specific save dimensions.
    Mapped-equivalent evidence now covers 2.439, 2.915, the historically
    observed 3.002.107 build, and a second
    3.002.149 build. The early profiles record source-proven resource, opcode,
    picture, view, object, motion, input, inventory, sound, and persistence
    variants.
- [x] Resource containers
  - Current: `spec/src/resource_containers.md` specifies split v2 and combined
    v3 directories, packed entries, volume records, direct payloads,
    dictionary expansion, picture-nibble expansion, and inventory metadata for
    valid data. Profiles 2.089/2.272 store expanded `OBJECT` metadata directly;
    later observed v2 profiles apply the repeating-key XOR transform.
- [x] Core runtime state and cycle ordering
  - Current: `spec/src/runtime_state.md` defines portable variable, flag,
    string, parsed-word, logic activation, resource, object, inventory, logical
    graphics, and top-level cycle concepts.
    The cycle contract now separates asynchronous timer/sound ticks from the
    synchronous cycle and specifies pacing, transient input/status reset,
    timed and queued input, direction mirroring, pre-motion, immediate logic-0
    re-entry, status redraw, cycle-marker cleanup, and the text-mode-gated
    post-logic object update in exact observable order.
- [x] Sound resources and playback
  - Current: `spec/src/sound.md` defines payload parsing, sound opcodes,
    countdown scheduling, completion flags, channel participation, PC-speaker
    divisors, four-channel tone order, silence, and four-channel attenuation
    envelope command output.
  - Remaining: analog waveform synthesis remains outside the current
    interpreter-output compatibility target.
- [x] Logic bytecode operation catalog
  - Current: `spec/src/logic_bytecode.md` specifies logic payload framing,
    message XOR decoding, main-stream control flow, AND/OR/NOT condition
    grammar, all 19 condition opcodes, all 176 action opcodes `0x00..0xaf`,
    and v3 extension slots `0xb0..0xb5`. A structural test checks every accepted
    profile opcode is represented. The 2.089 profile stops at `0x9a`
    and has a zero-operand unconditional `0x86`; 2.272 stops at `0xa0`, uses
    the later `0x86` selector, and treats `0x9c..0xa0` as operand-consuming
    menu no-ops.
  - Remaining refinements belong to subsystem chapters, especially configured
    text-window parameters and the complete save-file contract.
- [x] Picture command decoding and logical rendering
  - Current: `spec/src/picture_resources.md` defines the prepare/overlay/show
    lifecycle, scanner and operand boundaries, both drawing channels, all
    commands `0xf0..0xfa`, exact line rasterization, fill connectivity,
    pattern masks and stippling, and profile-specific right-edge writes. A
    source-first audit now covers every local interpreter: 2.089/2.272 end at
    `0xf8`; 2.411 has point-only `0xf9`/`0xfa`; complete v2 brushes use a
    filled radius-one mask and `0x0140` clamp; all observed v3 builds use a
    two-pixel radius-one center row and `0x013e` clamp. The renderer discovers
    relocated brush tables structurally. Tests guard every valid command, the
    terminator, table discovery, and both clamp families.
- [x] View/cel decoding and drawing
  - Current: `spec/src/view_resources.md` defines view/loop/cel offsets,
    row-run decoding, transparent colors, mutable shared-cel mirroring,
    baseline and edge placement, per-pixel priority scanning, and transient
    preview strings. A structural test guards the chapter's major contracts.
- [x] Object state, movement, collision, animation, and update ordering
  - Current: `spec/src/object_behavior.md` defines lifecycle, priority and
    horizon, placement search, cycle/cadence ordering, direction-based loop
    selection, cel cycling, movement clamps and events, exact crossing tests,
    footprint control classes, rectangle transitions, target motion, draw
    partitions, and refresh behavior.
  - Current: exact strict target bands, random direction/countdown reductions,
    and approach-mode stuck-recovery delay arithmetic are source-backed and
    covered by deterministic local transition tests using supplied random
    words.
- [x] Text, parser, keyboard, menu, and inventory behavior
  - Current: `spec/src/input_text_and_menus.md` defines dictionary compression,
    string slots, parser normalization/results/matching, the shared event
    queue, key mapping and release gates, text geometry and display offset,
    modal/alternate text state, inventory selection, and menu construction and
    navigation. Exact glyph bitmaps are a declared font-profile input outside
    the current portable core, not an unresolved interpreter behavior.
  - Remaining: bitmap-identical text claims must supply a font profile.
  - Harness note: QEMU's bundled VGA BIOS ignores temporary `INT 43h` font
    vector changes used by the observed 2.936 interpreter for inverse EGA
    text. `tools/setup_vgabios.py` now generates a patched LGPL VGABIOS 0.7a
    option ROM for faithful screenshots without modifying game inputs. The
    pristine upstream ROM, license, and provenance are tracked under
    `third_party/vgabios/`; the patched derivative remains ignored output.
  - Harness note: the generated FreeDOS disk is now a 1 GiB FAT16-LBA image,
    replacing the old small-volume constraint for multi-game and broad fixture
    work.
- [x] Room changes, restart, save/restore, and replay
  - Current: `spec/src/session_and_persistence.md` defines room-switch ordering,
    entry boundaries, replay pair kinds/packets/checkpoints, selector behavior,
    save names/signatures, five-block framing and known lengths, the v3 block-3
    XOR transform, recoverable/fatal failures, restore continuation, restart,
    and process cleanup. All five blocks in the observed profile 2.936 game
    data now have byte-complete maps: global state, 21 object records, 40
    inventory entries plus names, 100 replay pairs, and variable logic-resume
    records. The observed profile 3.002.149 Gold Rush save state now has a
    byte-complete structural map: 1028-byte global block with explicit reserved
    state, 23 object records, decoded 131-entry inventory/name data, 50
    replay pairs, and the same variable logic-resume grammar.
    The common 2.089/2.272 block 1 has a complete source-backed field
    partition covering scalar state, replay capacity/count, 39 key mappings,
    six live and six reserved string records, and text/input/status fields.
    Canonical initial bytes remain unmapped. Original BC
    and SQ1.22 saves add first-four-block dimensions for their
    selected game data. MG's historical save is explicitly incompatible with
    its selected interpreter/data combination and is not an interchange map.
    Cross-version layout and complete-code reference analysis classify the
    former block-1 gaps as inactive key-map records, a reserved string bank,
    fixed reserved words, and alignment bytes. The spec defines canonical
    initialization plus byte preservation for interchange.
  - Remaining: map save layouts for additional profiles when promoted.
- [x] Compatibility and version-conformance matrix
  - Current: `spec/src/conformance_matrix.md` separates the common core,
    2.936/3.002.149 variants, game-data dimensions, partial domains,
    out-of-scope behavior, and requirements for gameplay/save-interchange
    claims. Structural tests guard its section and claim boundaries.

## GR / SQ2 Static Comparison Tracker

This section tracks the current source-first comparison between Gold Rush
(`games/GR`, AGI 3.002.149) and Space Quest 2 (`games/SQ2`, AGI 2.936). The
scope for this pass is disassembled interpreter code and local resource bytes;
observable behavior/QEMU confirmation is added only after a delta is
source-mapped well enough to justify a targeted probe.

- [~] Evidence artifacts
  - Current: GR and SQ2 inputs are selected explicitly; SQ2 executable bytes are
    decrypted into `build/cleanroom/SQ2_AGI.decrypted.exe`; GR's `AGI` is
    already an MZ executable. Full linear `ndisasm` images and the generated
    report live under `build/gr-sq2-static/`; the repeatable helper is
    `tools/compare_gr_sq2_static.py`.
  - Remaining: keep expanding the report when newly labeled routines become
    relevant, and do not treat normalized straight-line differences across
    embedded jump tables as behavioral changes without manual disassembly.
- [~] Logic action opcode comparison
  - Current: table-level parser contracts match for shared action opcodes
    `0x00..0xaf`: argument counts and operand metadata are identical in GR and
    SQ2. Normalized handler-entry snippets match for 159 shared actions and
    differ for 17 shared actions: `0x12`, `0x6f`, `0x73`, `0x76`, `0x77`,
    `0x78`, `0x79`, `0x7c`, `0x7d`, `0x80`, `0x84`, `0x89`, `0x8a`, `0xa3`,
    `0xa4`, `0xa9`, and `0xad`. GR defines six extra action slots
    `0xb0..0xb5`; local GR scripts observed so far use only actions through
    `0xa9`.
  - Current v3-only slot notes: `0xb0` `reserved_noop_v3_0`, `0xb2`
    `reserved_noop_v3_2`, `0xb3` `reserved_noop_v3_4args`, and `0xb4`
    `reserved_noop_v3_2varargs` route to the generic no-op/return handler
    after the dispatcher/table contract has consumed their operands. `0xb1`
    `set_menu_interaction_gate` stores one immediate operand in word
    `[0x0403]`; GR `code.menu.interact` (`0x9724`) returns immediately while
    that word is zero. `0xb5` `clear_key_release_event_gate` clears byte
    `[0x0405]`, paired with GR's shared `0xad`
    `set_key_release_event_gate` setting that byte to `1`; the keyboard IRQ
    hook tests `[0x0405]` before enqueueing a type-2 zero event on selected
    key-release paths.
  - Current shared-delta source pass:
    - Input/text actions `0x6f`, `0x73`, `0x76`, `0x77`, `0x78`, `0x89`,
      `0x8a`, `0xa3`, `0xa4`, and `0xa9` are source-mapped. GR removes the
      SQ2 display-mode-2/input-width special paths for the observed normal
      EGA input UI, maps `0xa3`/`0xa4` to the generic no-op handler, and no
      longer clears the SQ2 input-width word from `0xa9`.
    - Event/key/menu actions `0x79`, `0xad`, `0xb1`, and `0xb5` are
      source-mapped. GR expands the script key-map table from `0x27` to
      `0x31` four-byte slots, replaces SQ2's incrementing key-release gate
      `[0x1530]` with set/clear byte `[0x0405]`, and adds a separate menu
      interaction gate word `[0x0403]`. Local source-model tests now pin the
      shared tracked-key IRQ latch semantics and the SQ2 incrementing-byte
      versus GR set/clear gate difference. A QEMU probe validates the expanded
      key-map capacity by filling 48 dummy slots, placing an `x` mapping in
      slot 48, and confirming that the typed-key fixture reaches the same
      nonblank picture capture as a direct draw while the no-key control stays
      blank. A separate QEMU probe validates the GR menu gate: a request after
      `0xb1(0)` matches the blocked control, while a request after `0xb1(1)`
      differs by entering the modal menu path.
    - Room/inventory/save/restart/object-state actions `0x12`, `0x7c`,
      `0x7d`, `0x80`, and `0x84` are source-mapped. GR's `0x12` remaps
      immediate room targets `0x7e..0x80` to `0x49` before room switch; local
      GR scripts contain those operands, and a QEMU probe now validates
      `0x7e..0x80 -> 0x49` by showing that direct target `0x49` and alias
      targets `0x7e`, `0x7f`, and `0x80` converge to the same nonblank
      destination-room capture. GR save wraps the object/inventory chunk in an
      XOR pass before and after writing the save envelope; local helper
      `gr_v3_object_inventory_save_xor()` models the observed repeating
      `Avis Durgan` data-segment key and is covered by known-vector,
      round-trip, and wrap tests. QEMU
      `save_xor_extract_qemu_001` extracts the original engine's blank-prefix
      `SG.1`, confirms five length-prefixed blocks with lengths `1028`, `989`,
      `1811`, `100`, and `12`, and proves the third block changes and
      round-trips under the modeled XOR transform. A corrected signed probe
      uses encrypted logic message text for `0x8f("GR")`, writes `GRSG.1`,
      and confirms the first save-state block begins with `GR\0`. A signed
      restore probe now generates `GRSG.1` through the original engine, restores
      it in a second fixture, and matches the restored capture to a direct
      saved-state control while differing from the unrestored control. GR
      restart records prompt-marker visibility before confirmation; accepted
      restart redraws the marker, and canceled restart redraws only if the
      marker had been visible. This branch is now modeled by a local
      truth-table helper/test and QEMU-validated for the canceled branch:
      hidden cancel matches a hidden control with 0 prompt-row foreground
      pixels, while visible cancel matches a visible control with 8 prompt-row
      foreground pixels. GR `0x84` preserves object 0 motion mode byte `+0x22`
      when it is already `4`. An instrumented QEMU probe now confirms that
      when action `0x51` seeds mode `4`, the GR dispatcher reaches the same
      visible target as unmodified mode `3`, while a stationary control remains
      different.
  - Remaining: raw key-release QEMU confirmation only if the final target
    requires hardware IRQ timing evidence beyond the source-modeled latch
    contract.
- [~] Logic condition opcode comparison
  - Current: table-level parser contracts match for shared condition opcodes
    `0x00..0x12`, and normalized handler-entry snippets have no differences.
    GR's dispatcher bound still compares with `0x26`, but bytes after the
    first 19 entries overlap punctuation/filename/string data and zero fill,
    so `0x13..0x25` are not confirmed predicate implementations. Local GR
    scripts observed so far use only conditions through `0x0e`.
  - Remaining: if a future local v3 game uses predicate bytes above `0x12`,
    investigate that interpreter/data pair directly instead of relying on the
    GR raw byte region.
- [~] Object runtime comparison
  - Current: core object record/update-list routines compare as relocated
    skeletons: sorted-list build, list node insertion, draw/refresh list walks,
    collision test, control acceptance, dirty-rectangle update, placement,
    active/inactive list rebuild/flush/refresh, and membership toggles. GR
    packages rectangle save/restore/draw routines in the main image rather than
    SQ2's `IBM_OBJS.OVL`. Static differences remain in object animation/motion:
    GR uses the four-plus direction table immediately for exactly-four-loop
    views, but gates views with more than four loops on flag `0x14`. The
    targeted v3 QEMU probe `frame_selection_gate_qemu_001` validates that
    exact-four view 177 selects group 1 with direction `6` whether flag `0x14`
    is clear or set, while more-than-four view 39 selects group 1 only after
    flag `0x14` is set and otherwise remains on group 0. GR also accepts motion
    mode `4` as another entry into the same target-direction helper used by
    mode `3`. The mode-4 dispatch path is now instrumented-QEMU-validated with
    a copied interpreter patch that changes only the action-`0x51` setup byte
    from mode `3` to mode `4`.
  - Remaining: optional raw key-release QEMU confirmation only if the final
    target requires hardware IRQ timing evidence beyond the source-modeled
    latch contract.
- [~] View runtime/resource comparison
  - Current: v3 container decoding can read GR view resources locally. Static
    comparison shows the view cache/load path, object-view binding, group table
    selection, frame selection, and view discard path match SQ2 as relocated
    skeletons after the v3 resource reader delivers an expanded payload.
  - Remaining: later behavior checks should focus on the GR-specific object
    group/motion branches rather than ordinary view decoding first.
- [~] Picture runtime/resource comparison
  - Current: v3 container decoding can read GR picture resources locally, with
    the documented picture-nibble transform before ordinary picture-command
    decoding. Static comparison shows picture cache/load, prepare/overlay,
    discard, command scanner, all eleven picture command handlers
    `0xf0..0xfa`, coordinate reads, line drawing, pixel writes, seed fill, and
    pattern plotting mostly match as relocated skeletons. The brush audit
    identifies two full-EGA differences: v3's two-pixel radius-one center row
    replaces v2's 2-by-3 logical block, and its `0x013e` horizontal clamp
    prevents the v2 X=160 linear wrap. Other shapes, masks, stipple evolution,
    and plot-loop code match. Additional differences are display-refresh
    paths: GR omits SQ2's display-mode-2 overlay refresh
    branch after buffer fill/full refresh, and `decode_no_clear` returns
    directly after command scan where SQ2 has the extra mode-2 refresh check.
  - Remaining: later QEMU checks should target display-mode-sensitive picture
    refresh only if the project decides to cover non-primary display modes for
    v3.

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
- [x] `0x6d` `set_text_window_pair` - QEMU-validated
- [x] `0x6e` `shake_screen_like` - source-backed CRT/display shake timing
- [x] `0x6f` `set_input_line_config` - QEMU-validated
- [x] `0x70` `show_status_line_like` - QEMU-validated
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
- [x] `0x83` `clear_global_0139` - source-backed main-cycle mirror selector
- [x] `0x84` `set_global_0139_and_clear_object0_field_22` - QEMU-validated
- [x] `0x85` `display_object_diagnostics_var` - QEMU-validated
- [x] `0x86` `confirm_and_restart_like` - QEMU-validated
- [x] `0x87` `show_heap_status` - QEMU-validated
- [x] `0x88` `pause_game_message` - QEMU-validated
- [x] `0x89` `refresh_input_line` - QEMU-validated
- [x] `0x8a` `erase_input_line` - QEMU-validated
- [x] `0x8b` `calibrate_joystick` - QEMU-validated
- [x] `0x8c` `toggle_display_mode_bit` - QEMU-validated
- [x] `0x8d` `show_interpreter_version` - QEMU-validated
- [x] `0x8e` `set_global_0141_and_refresh` - source-backed event-pair capacity reset
- [x] `0x8f` `verify_game_signature` - QEMU-validated
- [x] `0x90` `append_message_to_log_file` - QEMU-validated
- [x] `0x91` `save_logic_resume_ip` - QEMU-validated
- [x] `0x92` `restore_logic_entry_ip` - QEMU-validated
- [x] `0x93` `set_object_pos_dirty` - QEMU-validated
- [x] `0x94` `set_object_pos_dirty_var` - QEMU-validated
- [x] `0x95` `enable_action_trace_window` - QEMU-validated
- [x] `0x96` `configure_action_trace_window` - QEMU-validated
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
- [x] `0xa3` `set_global_0d0f` - QEMU-validated
- [x] `0xa4` `clear_global_0d0f` - QEMU-validated
- [x] `0xa5` `muln` - QEMU-validated
- [x] `0xa6` `mulv` - QEMU-validated
- [x] `0xa7` `divn` - QEMU-validated
- [x] `0xa8` `divv` - QEMU-validated
- [x] `0xa9` `close_text_window_state` - QEMU-validated
- [x] `0xaa` `copy_save_description_to_string_slot` - source-backed save-description buffer copy
- [x] `0xab` `save_event_buffer_count` - QEMU-validated
- [x] `0xac` `restore_event_buffer_count` - QEMU-validated
- [x] `0xad` `increment_global_1530` - source-backed key-release enqueue gate
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
  - Evidence: `docs/src/symbolic_labels.md`, now including initial Gold Rush
    / AGI v3 address associations for resource loading, decompression, and
    dispatch tables. `tools/game_census.py` provides the first repeatable
    inventory step for additional local interpreters before label mapping.
    Dispatch-table base detection now maps KQ4D/MH1 v3 tables and recognizes
    both observed v2 table trailers. New address associations cover SQ1,
    XMAS, BC, MG, MH1, and MH2, including the Gold Rush-only room-remap helper.
  - Remaining: continue assigning role-based labels for cross-version work,
    especially where later interpreters add features or move routines.
- [~] Startup, command-line flags, adapter selection, and display modes
  - Evidence: startup parser, display-mode `0x8c`, CGA/EGA overlay notes.
  - Remaining: full EGA behavior is the target; non-EGA adapter behavior should
    be documented only where it explains observed SQ2 behavior.
- [~] Resource directories, volume records, and cache records
  - Evidence: local resource parsers, loader labels, room-switch cache reset,
    and source-backed cache record layouts for logic, view, picture, and sound.
    Gold Rush / AGI v3 coverage now includes combined `GRDIR` sections,
    7-byte volume headers, prefixed `GRVOL.N` files, dictionary decompression,
    picture-nibble expansion/encoding in `tools/agi_resources.py`, and copied
    v3 fixture patching in `tools/qemu_fixture.py`. `tools/game_census.py`
    inventories additional local games and records header errors without
    treating them as valid-resource semantics. `tools/resource_reference_audit.py`
    distinguishes unreadable directory entries from entries immediately
    referenced by decoded scripts. The valid split/combined container and
    expansion contract is now promoted into `spec/src/resource_containers.md`.
    Picture/view discard source proves that retained resources are ordered:
    clearing the preceding cache link truncates the selected record and all
    later same-family records, and restore replay uses the same operation.
    `tools/agi_resources.py` models this portable transition independently of
    allocator addresses. Linear disassembly of all current local scripts finds
    picture/view discard in every promoted profile and confirms shipped scripts
    normally unwind retained resources in reverse load order.
    The new census distinguishes XMAS multi-disk packaging from installed v2
    volume naming. Replacement MH1/MH2 inputs now decode every present logic,
    picture, and view and every script-addressable sound. Source
    and resource-number analysis now caps directory sections at 256 addressable
    entries, preventing KQ4D's trailing directory-like bytes from becoming
    pseudo-resources. KQ1 sounds 34 through 37 are classified as offsets beyond
    `VOL.2`, not alternate record formats.
  - Remaining: loader error-path behavior only where needed by compatibility
    tests.
- [x] Logic resource format, messages, dispatch, and control flow
  - Evidence: logic resource docs, interpreter source pass, QEMU opcode probes.
  - Remaining: keep opcode tracker aligned with new findings.
- [~] Variables, flags, strings, parser words, and input buffers
  - Evidence: string/message/input probes, visible input-line refresh/erase
    probes, local parser notes, local `WORDS.TOK` prefix-decoder and
    tokenizer/output-slot tests, local source-modeled `input_word_sequence`
    matcher tests, and QEMU parser-edge probes for two-word matching, wildcard
    word ID `0x0001`, terminator word ID `0x270f`, and the unknown-token
    terminator-only edge.
  - Remaining: broaden vocabulary/tokenization edge cases only where needed for
    future compatibility tests; non-EGA input paths remain out of the current
    full-EGA target unless needed to explain SQ2 behavior.
- [~] Picture resource decoding and drawing
  - Evidence: picture decoder notes, Python renderer, fuzz corpus, QEMU
    comparison harness, source-backed seed-fill span traversal, and QEMU
    seed-fill edge cases for full-height barriers and multi-seed fills, plus
    QEMU pattern mask-bypass, channel-mask, and interleaved
    line/fill/pattern cases, command-byte scanner-resume cases, an
    implementation-facing picture decoder lifecycle, real-picture snapshot
    batches for base pictures 1/45, the 8-picture broad preset, and all 74
    valid local SQ2 pictures, direct local tests for rare corner-path commands
    `0xf4`/`0xf5`, and a chunked timed polling carousel run covering all 74
    valid local SQ2 pictures, plus QEMU-validated raw-operand scanner cases for
    `0xf0`, `0xf2`, and `0xf9`, and QEMU-validated relative-line underflow
    cases for `0xf7`.
  - Remaining: finish edge-case semantics for valid EGA picture streams and
    expand comparison fixtures, especially future cross-game/interpreter
    real-resource parity checks and any valid synthetic interleavings not yet
    represented by the fuzz corpus. Odd/even visual-mask divergence is outside
    the full EGA target path unless another observed SQ2 behavior requires it.
- [~] View resource decoding and cel drawing
  - Evidence: view layout notes, view/object snapshot batches, focused edge
    placement captures including right/bottom placement-search cases, an
    eight-case timed polling carousel, and a 19-case timed polling carousel for
    larger cels plus transparent-color variants, source-backed reserved header
    bytes `+0x00/+0x01`, plus an implementation-facing view/cel drawing
    contract, and source-modeled bit-`0x80` mirror row edge tests for
    all-transparent rows, implicit transparent padding, and long-run chunking.
    Runtime frame-animation modes are covered under the object
    movement/animation subsystem.
  - Remaining: broaden priority/control combinations only where needed for the
    final renderer compatibility suite.
- [~] Object records, priority/control screens, and drawing pipeline
  - Evidence: object overlay probes, priority/control bit probes, labels, and
    implementation-facing drawing lifecycle state machine; bounds-only
    placement search now modeled from `code.object.place`, with a tested
    predicate hook for collision/control rejection; update-list root ordering
    is QEMU-backed, and in-root sort/draw order is source-modeled in local
    tests; dirty-rectangle union is source-modeled in local tests; the
    `code.object.control_acceptance` scan is source-modeled in local tests and
    reconciled with the existing QEMU movement/control probes; object-overlay
    priority-gate tests now cover inclusive equal-priority writes, downward
    scan hits/misses, and per-pixel run continuation after rejection. Local
    control-acceptance tests also pin the "other nonzero high nibble" final
    state and priority-15 scan bypass/event-flag clear path from `0x56b8`.
  - Remaining: optional direct placement-search fixtures that combine full
    object records with control/collision rejection, if needed for the final
    compatibility suite.
- [~] Object movement, collision, animation, and boundary handling
  - Evidence: object movement QEMU batches, disassembly-backed scheduler, and
    implementation-facing motion state machine.
  - Remaining: add any missing edge probes for valid movement and collision
    behavior.
- [~] Room switching, restart, save/restore, and resource-event replay
  - Evidence: room-switch probes, save/restore source map, source-backed save
    selector subroutine map, local save-file parser/tests for the five-block
    file envelope including byte-for-byte serialization, replay re-enable
    correction at `0x6927`, rollback probe for `0xab`/`0xac`, and
    source-backed restart/termination and save/restore file-error lifecycles,
    plus dynamic original-engine save-write, restore, and restore-read-error UI
    probes. The generated fixture now calls `0x8f("SQ2")`, so `DS:0x0002`
    supplies both the `SQ2SG.N` filename prefix and the saved-state signature
    checked by the restore selector.
  - Remaining: any additional observable restore/restart edge cases needed by
    compatibility tests.
- [~] Text windows, status line, prompts, and interactive input
  - Evidence: message/string/numeric input probes, visible status/input-line
    probes, mapped-key/raw-key probes, prompt-marker behavior, input-width flag
    behavior, source-backed active `0xa9` saved-window restore lifecycle,
    source-modeled tracked key-release IRQ latch/gate tests, and an
    implementation-facing UI lifecycle state machine.
  - Remaining: non-EGA text paths only if they become relevant to explaining
    SQ2 behavior.
- [~] Menus and inventory UI
  - Evidence: inventory selection, menu setup, disabled/enabled item probes,
    a source-backed `code.menu.interact` movement dispatch table, and an
    implementation-facing menu/list data model plus interaction lifecycle. GR
    v3 action `0xb1` is QEMU-validated as a menu interaction gate: zero blocks
    the requested menu and nonzero lets the modal menu path take over.
  - Remaining: optional dynamic validation of movement/navigation events with
    direct event injection or a more precise QEMU input path; existing QEMU
    keyboard attempts did not produce reusable movement evidence, but the
    current movement semantics are source-backed.
- [x] Sound and audio
  - Evidence: load/start/stop completion-flag behavior; source-backed sound
    cache/channel pointer setup; local parser/tests for the four-channel sound
    payload header, duration/tone/control event streams, active-channel
    selection, countdown scheduling, flag-9 stop gate, natural completion ticks
    across all present SQ2 sound resources, and source-backed hardware driver
    port-write behavior including the PC-speaker divisor formula and
    tone/silence output boundary plus non-PC-speaker attenuation/envelope output
    bytes. `docs/src/sound_and_audio.md` now consolidates these observations
    into an evidence-facing subsystem contract. `spec/src/sound.md` now
    promotes the payload, scheduling, completion, tone, silence, and
    attenuation-envelope command-output behavior.
  - Remaining: analog waveform synthesis remains outside scope; optional
    dynamic confirmation of natural completion is useful only if the written
    scheduling contract exposes an unresolved ambiguity.
- [~] DOS file I/O, logging, save descriptions, and path selection
  - Evidence: log-file QEMU content check, save/restore source map, selector
    path/slot source map, save-description buffer copy source map, corrected
    DOS wrapper symbolic-label map, source-backed file-error continuation
    behavior, structural parse/serialize tests over the present local SQ2 save
    files, a dynamic save-write QEMU probe whose output parses through the
    source-backed envelope, a dynamic restore QEMU probe using those bytes, and
    a representative restore-read error UI capture from a selector-visible
    truncated save. Source now explains the filename stem:
    `code.save.format_slot_filename` uses `data.save.signature_prefix_0002`,
    `docs/src/runtime_model.md` now includes an implementation-facing
    save/restore selector state machine, and local tests model
    `code.dos.validate_path` string normalization/dispatch edges.
  - Remaining: dynamic path-validation UI failures only if needed for the final
    compatibility suite.
- [~] Memory, heap, allocation, and diagnostics
  - Evidence: source-backed bump-heap helper map, room/reset and temporary mark
    semantics, startup base/current/limit initialization from DOS memory
    allocation, allocation failure path, high-water tracking, free-memory byte
    update, heap-status diagnostic formulas, and local heap formula tests for
    allocation/free-byte/high-water, temporary mark restore, room-reset rewind,
    and diagnostic values.
  - Remaining: any representative observable out-of-memory UI behavior needed
    for final compatibility coverage.
- [~] Compatibility test suite and harnesses
  - Evidence: `tests/`, `tools/logic_interpreter_probe.py`,
    `tools/object_movement_probe.py`, `tools/object_overlay_probe.py`,
    `tools/picture_fuzz.py`, `tools/picture_batch.py`, QEMU snapshot support,
    a 1,062-case picture fuzz corpus with 1,060 QEMU-safe cases and focused
    original-engine batches,
    packed picture fixtures, two-picture key-driven `tools/picture_carousel.py`
    smoke validation, an eight-picture timed polling carousel validation from
    one engine process, and a chunked all-74-picture timed polling carousel
    validation across five engine launches. The view/object carousel now
    validates all 19 current base-plus-stress view cases from one engine
    process. A single all-74-picture carousel hit an original-engine disk prompt
    after picture 19, so chunking is the recommended path for large picture
    sweeps. `tools/compatibility_suite.py` now provides a local-by-default
    manifest/runner with opt-in QEMU smoke and broad layers; the QEMU smoke
    manifest passed in `build/compatibility-suite/qemu_smoke_002.json` with
    parser, command-resume, raw-operand, and relative-line-underflow
    original-engine probes. The QEMU
    broad manifest passed in `build/compatibility-suite/qemu_broad_002.json`,
    including the smoke layer, the eight-picture timed carousel, and the
    19-case view/object stress carousel. The suite now also has an explicit
    `qemu-exhaustive` layer that inherits smoke/broad and schedules all present
    pictures plus every deterministic movement and object-overlay case. The
    aggregate report `build/compatibility-suite/qemu_exhaustive_001.json`
    passed all 15 commands: 403 local tests with one optional historical-save
    skip, both books, opcode evidence, all smoke/broad probes, 74/74 present
    pictures, 36/36 deterministic movement cases, and 24/24 overlay cases.
    Movement and overlay fixtures use ten-case snapshot chunks after the first
    unchunked run exhausted the DOS test disk. The autonomous random-motion
    observation remains an explicit exploratory case because a zero random
    direction makes a stationary capture valid; the two deterministic
    random-motion clearing cases remain in the gate. The first aggregate
    attempt also exposed and fixed a missing smoke-layer prerequisite:
    deterministic picture-fuzz corpus generation is now part of the manifest.
    `tools/conformance_results.py` now exports a versioned, language-neutral
    visual result bundle and compares candidate bundles by canonical 160 by
    168 EGA-index frame digest, with artifact-backed pixel mismatch details.
    The first 2.936 reference bundle contains 165/165 successful cases in
    `build/conformance-results/sq2_2936_reference.json`; its self-comparison
    passed all 165 cases with zero failures. The adapter now also accepts
    completed v3 behavior-probe reports using stable `probe/label` IDs and
    path-safe artifact names. The first Gold Rush 3.002.149 bundle contains
    32/32 successful cases across eight source-mapped probe families and
    self-compares with zero failures.
    The suite also has an explicit
    `qemu-v3` layer for private-input v3 probes, and the named GR save-XOR
    extraction command passed in
    `build/compatibility-suite/qemu_v3_save_001.json`. Generated fixture
    copies now preserve private game inputs as read-only evidence and make only
    the generated copy writable;
    `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests`
    passed 251 tests after this fix. The v3 layer now includes separate
    blank-prefix and signed GR save-XOR extraction commands, a signed GR
    restore round-trip command, a GR restart prompt-marker cancel command, and
    a GR menu-gate command;
    the signed direct report
    `build/gr-v3-behavior/save_xor_extract_signed_qemu_001.json` and suite
    report `build/compatibility-suite/qemu_v3_signed_save_001.json` confirm
    `GRSG.1` and first-block prefix `47 52 00`, while
    `build/compatibility-suite/qemu_v3_signed_restore_001.json` confirms that
    the generated `GRSG.1` restores state and returns through restored script
    execution. `build/compatibility-suite/qemu_v3_restart_prompt_001.json`
    confirms the restart-cancel prompt-marker branch, and
    `build/compatibility-suite/qemu_v3_menu_gate_001.json` confirms that
    `0xb1(0)` blocks a requested menu while `0xb1(1)` enters the modal menu
    path. `build/compatibility-suite/qemu_v3_synthetic_picture_view_001.json`
    confirms generated v3 picture-nibble picture and direct view fixtures by
    comparing blank, picture-only, and picture-plus-view captures. The current
    full local run passes 419 tests after adding cross-version profile,
    directory-boundary, portable-result, and ordered resource-retention
    coverage. The top-level runner
    now accepts `--game-dir PATH`, exports that explicit selection to child
    commands, and records it in the JSON report without choosing a default
    game.
    Portable bundles now also carry canonical JSON `values` observations for
    deterministic state, input, ordered sound-command, and persistence results.
    The comparator reports semantic difference paths without exposing DOS
    memory or requiring a particular implementation layout.
  - Remaining: scale sweeps and bundles to additional interpreter versions as
    their source-mapped probes are promoted.
- [~] Cross-version comparison workflow
  - Evidence: symbolic labels are being curated for SQ2, and
    `docs/src/cross_version_workflow.md` now defines the local evidence package,
    label-mapping anchors, pass order, compatibility tiers, and delta-recording
    rules for future interpreter/game versions. The first application to
    Gold Rush / AGI v3 has mapped the changed resource container, v3
    dispatch/resource routines, shared/extra opcode-table differences, and the
    first object/view/picture runtime deltas. The same workflow now covers seven
    additional inputs: exact same-build comparison, normalized relocated-role
    matching, partial-profile extraction, selected-save dimensions, and
    incomplete-resource classification. `docs/src/versions.md` keeps the
    concise per-version difference ledger. `tools/qemu_fixture.py` can now
    write copied v3 fixtures with direct logic/view records and picture-nibble
    picture records for generated Gold Rush-style copies under `build/`; a
    QEMU compatibility probe confirms those generated records run under the
    original GR interpreter. `tools/resource_reference_audit.py` adds a
    script-visible reference check for deciding whether unreadable
    directory-looking entries are valid behavior candidates.
- [~] Final human-readable behavioral specification
  - Evidence: a separate clean-room mdBook now lives under `spec/`, with an
    explicit externally observable behavior boundary and conformance model.
    The existing `docs/` book remains the implementation-detail evidence
    record. Promoted chapters now include version profiles, resource
    containers, core runtime state, logic bytecode, pictures, views, objects,
    sound scheduling/output boundaries, input/text/menu/inventory behavior,
    and room/replay/persistence behavior.
    Structural tests reject evidence-only terminology in substantive spec
    chapters and verify every summary link.
    All five observed profile 2.936 and Gold Rush 3.002.149 save blocks now have
    exhaustive block-relative partitions. Former opaque block-1 ranges are
    classified as reserved serialization state with canonical initialization
    and byte-preservation rules.
  - Remaining: map other profile save layouts and close remaining conditional
    domains. The final spec must stand alone for a separate implementation
    team.

## Highest-Value Remaining Work

1. Continue v3 behavioral probes from source-mapped deltas only when the
   portable specification still has an observable ambiguity. Use synthetic v3
   resources when a focused confirmation requires them.
2. Continue source-first renderer work only when disassembly or a valid local
   resource exposes a concrete edge not already modeled. Use QEMU as
   confirmation/regression evidence.
3. Keep expanding `tools/compatibility_suite.py` when a new behavior is promoted
   to reusable evidence. Re-run the smoke or broad QEMU layer whenever the
   manifest changes.
4. Establish canonical initial 2.089/2.272 reserved save bytes only if pristine
   binary save synthesis for those selected games becomes a target.
5. Treat non-EGA paths, analog waveform synthesis, menu arrow injection, invalid
   path UI, and out-of-memory UI as optional/conditional work unless the final
   compatibility target expands beyond current full-EGA valid-data behavior.
