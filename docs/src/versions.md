# Versions

This chapter tracks observed differences between local interpreter/game inputs.
The goal is to keep version-specific facts separate from the portable AGI
behavioral spec. Entries here are evidence from local files and local tools,
not external AGI documentation.

## Observed Inputs

| Local input | Version evidence | Executable form | Resource container | Fixture status |
| --- | --- | --- | --- | --- |
| `games/KQ1` | `AGIDATA.OVL` string `Version 2.917` | `AGI` is decrypted with the selected game's `SIERRA.COM` key before disassembly | Split `LOGDIR`, `PICDIR`, `VIEWDIR`, `SNDDIR`; direct `VOL.N` records | Full-EGA resource, logic, input, persistence, renderer, and object profile is promoted; KQ1 save dimensions are mapped |
| `games/SQ2` | `AGIDATA.OVL` string `Version 2.936` | `AGI` is decrypted from the loader-managed local bytes before disassembly | Split `LOGDIR`, `PICDIR`, `VIEWDIR`, `SNDDIR`; `VOL.N` files; 5-byte record headers; direct resource payloads | Current generated QEMU fixtures target this v2 split layout |
| `games/KQ4D` | `AGIDATA.OVL` string `Version 3.002.102` | `AGI` is an MZ executable | Combined `DMDIR`; prefixed `DMVOL.N` files; v3 transforms | Full-EGA resource, logic, input, persistence, renderer, and object profile is promoted |
| `games/GR` | `AGIDATA.OVL` string `Version 3.002.149` | `AGI` is already an MZ executable | Combined `GRDIR`; prefixed `GRVOL.N` files; 7-byte record headers; dictionary and picture-nibble transforms | Decoding/parsing is implemented locally; generated fixtures can patch copied v3 directories/volumes with direct logic/view records and picture-nibble picture records under `build/` |

## Local census snapshot

The read-only census tool `tools/game_census.py` now provides a repeatable
starting point for comparing the private local games without modifying them.
The current command used was:

```bash
python3 -B tools/game_census.py --games-root games \
  --format markdown \
  --output build/cross-version/game_census.md
```

The local snapshot found these version/layout groups:

| Local input | Version string | Layout | Notes |
| --- | --- | --- | --- |
| `games/KQ2` | `Version 2.411` | v2 split | Direct `VOL.N` records. |
| `games/LSL1` | `Version 2.440` | v2 split | Direct `VOL.N` records. |
| `games/KQ1` | `Version 2.917` | v2 split | Direct records for most resources; four sound entries currently fail the generic v2 header check and need source inspection before modeling. |
| `games/PQ1` | `Version 2.917` | v2 split | Direct `VOL.N` records. |
| `games/KQ3` | `Version 2.936` | v2 split | Direct `VOL.N` records. |
| `games/SQ2` | `Version 2.936` | v2 split | Two known out-of-range end entries remain record errors in the generic census. |
| `games/KQ4D` | `Version 3.002.102` | v3 combined | Combined `DMDIR`/`DMVOL.N`; dispatch tables are at AGIDATA offsets `0x0620`/`0x0942`. Decoded scripts currently reference only sound resources `70..79`, which are clean records; later suspect sound-section entries need source inspection before modeling. |
| `games/GR` | `Version 3.002.149` | v3 combined | Combined `GRDIR`/`GRVOL.N`; all present records expand with the current v3 reader. |

This is an inventory for planning. The portable spec should only gain a
version-specific rule when disassembly or a valid-resource dynamic check shows
that game scripts can observe the behavior.

## KQ1 / AGI 2.917

KQ1's `AGI` file uses the same loader-managed evolving-key transform previously
observed for SQ2, but with the key bytes from KQ1's own `SIERRA.COM`. The local
transform command was:

```bash
python3 -B tools/decrypt_agi.py --game-dir games/KQ1 \
  --output build/cross-version/kq1_agi.decrypted.exe
```

Comparing the still-transformed file produced nonsense at every handler entry.
The transformed-state report was discarded. The decoded MZ image yields a
clean table comparison:

- the action table starts at `AGIDATA.OVL:0x061d` and has 174 entries
  `0x00..0xad`;
- the condition table starts at `0x08f5` and has the common 19 entries;
- every shared action/condition operand contract and normalized handler body
  matches 2.936; and
- the action dispatcher at image `0x02c4` accepts through `0xad`, while 2.936
  accepts through `0xaf`.

The v2 table count is derived from the fixed `0x20`-byte data trailer between
the action and condition tables. Across current local inputs this yields 170
actions for 2.411/2.440, 174 for 2.917, and 176 for 2.936.

A 52-role subsystem comparison found relocation matches for resource loading,
views, picture lifecycle and command/raster helpers, update lists, placement,
collision, control acceptance, dirty rectangles, motion, and cel-mode branch
bodies. The one observable branch difference is in frame-timer helper
`0x0563`:

- 2.917 applies the four-direction loop table only when loop count equals four;
- 2.936 applies it when loop count is four or greater.

The selected KQ1 save writer uses the common five-block envelope and the same
`0x05e1` block-1 partition as 2.936. Its decoded `OBJECT` metadata defines 18
object records and a `0x0148`-byte inventory block containing 27 entries.
Logic 0 calls action `0x8e(100)`, so replay block 4 remains `0x00c8` bytes.
The resulting block dimensions are `0x05e1`, `0x0306`, `0x0148`, `0x00c8`,
and a variable logic-resume block.

Four KQ1 sound directory entries fail the generic record-header check, but the
script-visible reference audit finds no immediate logic reference to them.
They are not included in the promoted valid-data contract.

This evidence promotes a 2.917 full-EGA gameplay profile and KQ1-specific
binary-save interchange dimensions.

## Script-visible resource reference audit

The helper `tools/resource_reference_audit.py` compares immediate resource
numbers used by decoded logic bytecode against the selected game's readable and
unreadable directory entries. It is intentionally conservative: variable-based
resource numbers are not counted as fixed script references.

The current focused command was:

```bash
python3 -B tools/resource_reference_audit.py \
  --game-dir games/KQ1 \
  --game-dir games/KQ4D \
  --output build/cross-version/resource_reference_audit_kq1_kq4d.json
```

Current result:

| Local input | Resource family | Immediate script references | Unreadable directory entries | Referenced unreadable entries |
| --- | --- | ---: | --- | --- |
| `games/KQ1` | sound | 21 entries, max `21` | `34`, `35`, `36`, `37` | none |
| `games/KQ4D` | sound | 10 entries, max `79` | `221`, `223..236`, `387..394`, `423..427`, `583..587`, `660..661` | none |

Conclusion: these unreadable sound-directory entries remain cross-version
planning evidence, not valid-resource behavior for the clean spec. If a future
game script computes those numbers through variables, or if another interpreter
version accepts the same directory bytes through a source-mapped path, inspect
that case directly before promoting a rule.

## Save reserved-state comparison

The SQ2 and Gold Rush block-1 layouts resolve the ranges that were previously
recorded only as opaque bytes:

| Serialized role | SQ2 / 2.936 | Gold Rush / 3.002.149 | Conclusion |
| --- | --- | --- | --- |
| Key-map tail | Ten zeroed four-byte records follow SQ2's 39 active slots. | The active capacity grows to 49 and consumes those ten records. | Inactive profile capacity, not hidden runtime state. |
| Pre-string bytes | Four zero bytes precede the common string root. | The same four zero bytes remain after the expanded key map. | Reserved serialization padding. |
| Post-string bank | Twelve zeroed 40-byte records follow the 12 valid SQ2 slots. | The bank is absent; text state immediately follows the 12 valid slots. | Reserved legacy capacity, not 12 additional valid slots. |
| Standalone words | Canonical `0000` and `0f00`; no direct references in the complete code scan. | Same serialized positions and canonical values; no direct references in the complete code scan. | Reserved words preserved for save interchange. |
| Prompt/status gap | One canonical zero byte between byte and word state. | The same one-byte boundary exists at the relocated text-state tail. | Reserved alignment byte. |

Valid string actions remain limited to the twelve specified string slots, and
the key-map action's source loop bounds define the profile capacities. Restoring
and re-saving an existing file preserves supplied reserved bytes; a newly
initialized state uses the canonical bytes above. No separate game-visible
field is assigned to these ranges.

## KQ4D / AGI 3.002.102

The generic table comparator was run in both directions:

```bash
python3 -B tools/compare_interpreter_tables.py \
  --left-label KQ4D-3.002.102 --left-game-dir games/KQ4D \
  --left-exe games/KQ4D/AGI \
  --right-label GR-3.002.149 --right-game-dir games/GR \
  --right-exe games/GR/AGI \
  --output build/cross-version/kq4d_gr_table_comparison.md

python3 -B tools/compare_interpreter_tables.py \
  --left-label KQ4D-3.002.102 --left-game-dir games/KQ4D \
  --left-exe games/KQ4D/AGI \
  --right-label SQ2-2.936 --right-game-dir games/SQ2 \
  --right-exe build/cleanroom/SQ2_AGI.decrypted.exe \
  --output build/cross-version/kq4d_sq2_table_comparison.md
```

All 182 KQ4D/GR action parser contracts and all 19 condition contracts match.
The condition handler entries also normalize identically. Twelve shared action
handlers differ between KQ4D and GR:

```text
12 6f 73 76 77 78 79 89 8a a3 a4 a9
```

Focused disassembly assigns these differences to three observable clusters:

| Cluster | KQ4D 3.002.102 | GR 3.002.149 |
| --- | --- | --- |
| Room action `0x12` | Passes the immediate room byte directly to the room-switch helper. | Remaps `0x7e..0x80` to `0x49`. |
| Input actions `0x6f`, `0x73`, `0x76..0x78`, `0x89`, `0x8a`, `0xa3`, `0xa4`, `0xa9` | Retains the SQ2 display-mode/input-width branches; `0xa3`/`0xa4` set/clear the width word and `0xa9` clears it. | Uses the normal EGA path, no-ops `0xa3`/`0xa4`, and has no width word to clear. |
| Key map `0x79` | Stops after `0x27` (39) records. | Stops after `0x31` (49) records. |

Direct KQ4D/SQ2 comparison finds only five shared handler-entry differences:
`0x7c`, `0x7d`, `0x80`, `0x84`, and `0xad`. KQ4D shares GR's inventory
temporary-state branch, block-3 save XOR, restart prompt-marker branch,
motion-mode-4 preservation, and set-style release gate. Its six v3-only slots
`0xb0..0xb5` have the same contracts and normalized handlers as GR, including
the menu interaction gate and release-gate clear action.

The KQ4D save writer serializes block 1 from the common start through data
address `0x05e5`, yielding length `0x05e4`. This is exactly the 2.936 block-1
partition plus menu-gate word `[0x05e3]` and release-gate byte `[0x05e5]`.
The intended decoded eight-byte inventory metadata is:

```text
03 00 0f 03 00 00 3f 00
```

It defines one three-byte inventory entry, name pool `?\0`, and maximum object
index 15, therefore 16 object records. Demo logic 0 sets replay capacity to one.
The source-derived save dimensions are consequently block 1 `0x05e4`, block 2
`16 * 0x2b = 0x02b0`, block 3 `5`, block 4 `2`, and a variable block 5.

The selected local `OBJECT` file already contains the intended decoded bytes,
while the interpreter source applies the repeating `Avis Durgan` XOR to the
file buffer. A copied-fixture QEMU experiment compared the local bytes unchanged
with an XOR-encoded copy. Both reached the same intro frame after advancing the
Sierra loader; the demo had not yet exercised inventory metadata there. This is
recorded as a local packaging anomaly, not as valid dual-encoding behavior.
The clean profile follows the source reader's XOR-decoded valid-data contract.

The renderer/object source pass compared 52 symbolic roles with GR 3.002.149.
Core helpers normalize identically after relocation; the few wrapper-level
differences are classified below the table.

| Cluster | Compared roles | Result |
| --- | ---: | --- |
| View loading and selection | 6 | Resource load/discard, view bind, loop table, loop selection, and cel selection match. |
| Picture lifecycle | 4 | Load, prepare, overlay prepare, and discard match. |
| Picture scanner and commands | 15 | Decode completion, scanner, channel controls, pattern controls, both corner paths, absolute/relative lines, fill, coordinate reader, and line raster entry were compared. |
| Logical display and raster | 6 | Buffer fill, horizontal/vertical lines, pixel write, seed fill, and full refresh were compared. |
| Object lists and composition | 15 | Sorted-list construction, draw/refresh ordering, collision, control acceptance, dirty rectangles, placement, partitions, and list rebuild/refresh match. |
| Motion and animation | 6 | Frame timer, frame-mode bodies, object movement, pre-mode pass, mode dispatch bodies, and rectangle-boundary bodies match. |

Three display wrappers retain KQ4D's older display-mode-2 branches: picture
decode completion, buffer fill, and full refresh. Their primary EGA paths match
GR, and alternate display modes are outside the current conformance target.
The two reported motion/frame differences occur inside embedded jump-table
bytes; manual disassembly confirms that the selected branch bodies and their
post-table state transitions are relocation matches.

This closes the independent renderer/object blocker. The clean 3.002.102
profile now supports a full-EGA valid-data gameplay claim, plus binary save
interchange for the mapped KQ4D demo dimensions.

## SQ2 / AGI 2.936

SQ2 remains the main behavioral evidence target for the current spec. The
resource directory files are split by family. Directory entries are 3-byte
packed volume/offset records, and absent resources are identified by a high
volume nibble of `0xf`.

The volume record header is:

```text
12 34 volume length_lo length_hi payload...
```

The current generated original-engine fixtures patch writable copies of
`LOGDIR`, `PICDIR`, `VIEWDIR`, and `VOL.3` to point at synthetic logic,
picture, and view records. These fixture builders copy the selected game input
to a generated destination first; `games/` is treated as read-only evidence.

## Gold Rush / AGI 3.002.149

Gold Rush is the first observed AGI v3 input. It keeps the decoded resource
families recognizable, but changes the container and resource-reader path.

The combined `GRDIR` header contains four little-endian section offsets:

| Section | Header word | Offset | Present entries |
| --- | ---: | ---: | ---: |
| logic | `+0` | `0x0008` | 182 |
| picture | `+2` | `0x02e7` | 186 |
| view | `+4` | `0x05c6` | 247 |
| sound | `+6` | `0x08c6` | 44 |

The v3 volume record header is:

```text
12 34 metadata expanded_len_lo expanded_len_hi stored_len_lo stored_len_hi stored...
```

Observed transform selection:

| Header condition | Transform |
| --- | --- |
| metadata bit `0x80` set | picture nibble expansion |
| expanded length equals stored length | direct read |
| expanded length differs from stored length | dictionary expansion |

The v3 action table is larger than SQ2's v2 table. The Gold Rush interpreter
accepts action opcodes through `0xb5`, but the decoded local Gold Rush scripts
observed so far only use action opcodes through `0xa9`.

Source-backed GR-only action slot notes:

| Opcode | Local label | Evidence-backed effect |
| ---: | --- | --- |
| `0xb0` | `reserved_noop_v3_0` | Table entry has zero operands and routes to the generic no-op/return handler at image `0x5286`. |
| `0xb1` | `set_menu_interaction_gate` | Reads one immediate byte, zero-extends it, and stores it in word `[0x0403]`. GR `code.menu.interact` at image `0x9724` returns immediately while `[0x0403] == 0`, so nonzero values enable the menu interaction path after the usual menu-request flag is set. QEMU `menu_gate_suite` validates zero as blocked and nonzero as modal-menu entry. |
| `0xb2` | `reserved_noop_v3_2` | Table entry has zero operands and routes to the generic no-op/return handler at image `0x5286`. |
| `0xb3` | `reserved_noop_v3_4args` | Table entry declares four fixed operands, but the handler is the generic no-op/return handler. |
| `0xb4` | `reserved_noop_v3_2varargs` | Table entry declares two variable operands via metadata `0xc0`, but the handler is the generic no-op/return handler. |
| `0xb5` | `clear_key_release_event_gate` | Stores zero in byte `[0x0405]`. GR action `0xad` sets the same byte to one, and the keyboard IRQ hook tests it before enqueueing a type-2 zero event on selected key-release paths. Local source model `tools/agi_input.py` covers this set/clear gate with the shared tracked-key latch semantics. |

Source-backed shared action deltas, relative to SQ2 / AGI 2.936:

| Area | Opcodes | Observed GR / AGI 3.002.149 difference |
| --- | --- | --- |
| Input line and prompts | `0x6f`, `0x73`, `0x76`, `0x77`, `0x78`, `0x89`, `0x8a`, `0xa3`, `0xa4`, `0xa9` | GR keeps the normal EGA-style input-line model but removes SQ2's display-mode-2/input-width branches. It computes the display offset as `arg0 << 3`, always uses the normal prompt/editor path for string and number prompts, maps the SQ2 input-width set/clear actions to no-op, and closes active text-window state without clearing a width flag. |
| Key and menu events | `0x79`, `0xad`, `0xb1`, `0xb5` | GR expands the script key-map table from `0x27` to `0x31` four-byte slots. A QEMU fixture validates slot 48 by filling 48 dummy slots, mapping typed `x` in the final slot, and comparing against a direct nonblank picture draw; the no-key control remains blank. GR also replaces SQ2's incrementing key-release byte `[0x1530]` with set/clear byte `[0x0405]`, and adds menu interaction gate word `[0x0403]`. The source-modeled IRQ latch helper covers the key-release gate change; the menu-gate QEMU fixture validates that `0xb1(0)` makes a requested menu match the blocked control, while `0xb1(1)` yields a distinct modal-menu capture. |
| Room and state actions | `0x12`, `0x7c`, `0x7d`, `0x7e`, `0x80`, `0x84` | GR remaps immediate room targets `0x7e..0x80` to `0x49` before the ordinary room-switch helper; the decoded local GR scripts do contain those operands. The carried-item selector sets temporary word `[0x0dc1]` while handling a flag-13 input path and clears it on return. Save wraps the object/inventory chunk in an XOR pass before and after writing the save envelope; restore applies the same repeating `Avis Durgan` XOR transform after reading that block. The observed transform key is data at `DS:0x072c`, is modeled by `gr_v3_object_inventory_save_xor()`, and is QEMU-validated against blank-prefix `SG.1`, signed `GRSG.1`, and a signed restore round trip with block lengths `1028`, `989`, `1811`, `100`, and `12`. Restart records prompt-marker visibility before confirmation; accepted restart redraws the marker, and canceled restart redraws only if it had been visible. The canceled branch is QEMU-validated by hidden/visible prompt-row captures. Action `0x84` preserves object 0 motion mode `4` instead of always clearing byte `+0x22`. |
| Object animation and motion | frame timer, motion dispatch | GR uses the four-plus direction table immediately for exactly-four-loop views, but gates views with more than four loops on flag `0x14`. QEMU `frame_selection_gate_qemu_001` validates exact-four view 177 selecting group 1 regardless of flag `0x14`, and more-than-four view 39 selecting group 1 only when flag `0x14` is set. GR also dispatches motion mode `4` to the same target-direction helper used by mode `3`; that branch is instrumented-QEMU-validated by patching only the copied GR action-`0x51` mode seed from `3` to `4`, while ordinary bytecode still has no observed direct setter for mode `4`. |

The first dynamic v3 behavior probe is `tools/gr_v3_behavior_probe.py`. The
room-remap probe patches a copied GR game so logic 0 switches once and then
continues dispatching `call_logic_var(v0)`, while logic `0x49` draws a fixed
picture. Under QEMU, direct target `0x49` and alias target `0x7e` produced
identical nonblank captures first; the expanded run then validated alias targets
`0x7e`, `0x7f`, and `0x80` against direct target `0x49` in
`build/gr-v3-behavior/room_remap_all_qemu_pic001_001.json`.

The same probe tool now includes `--probe key-map-capacity`. The promoted run
`build/gr-v3-behavior/key_map_capacity_qemu_pic001_002.json` builds three
copied GR fixtures: a direct picture draw, a slot-48 key-map fixture that sends
`x`, and the same slot-48 fixture without a key. QEMU reports the keyed capture
matching the direct draw and the no-key capture not matching, with the no-key
capture blank. This confirms the observed `0x31` slot loop bound has an
observable event-mapping consequence in the original GR interpreter.

The probe tool also includes `--probe menu-gate`. The promoted suite run
`build/gr-v3-behavior/menu_gate_suite.json` builds a blocked control plus two
requested-menu fixtures. The `0xb1(0)` fixture matches the blocked control,
while the `0xb1(1)` fixture differs from both the control and the zero-gate
case. That confirms that `[0x0403]` is not part of menu construction; it gates
whether a later `0xa1` menu request may enter the modal menu path.

The probe tool also includes `--probe save-xor-extract`. The promoted run
`build/gr-v3-behavior/save_xor_extract_qemu_001.json` omits
`verify_game_signature`, so the original interpreter writes a blank-prefix
`SG.1` save. The extracted file has five blocks with lengths `1028`, `989`,
`1811`, `100`, and `12`; block 3 changes when passed through
`gr_v3_object_inventory_save_xor()` and a second pass restores the emitted
bytes. This validates the source-mapped v3 object/inventory save transform
without relying on GR's verifier/save-prefix path.

The signed run
`build/gr-v3-behavior/save_xor_extract_signed_qemu_001.json` corrects the
fixture message encoding to use the normal encrypted logic-message text,
executes `verify_game_signature("GR")`, and validates that the original
interpreter writes `GRSG.1`. The first saved-state block begins with bytes
`47 52 00`, and the same five block lengths and third-block XOR hashes match
the blank-prefix run.

The signed restore run
`build/gr-v3-behavior/signed_restore_roundtrip_suite.json` uses the original
GR interpreter to generate `GRSG.1`, then restores it in a second generated
fixture. The restored capture matches a direct saved-state control and differs
from an unrestored control, confirming that GR action `0x7e` decodes the
object/inventory block and resumes through restored state for valid signed
saves.

The restart prompt-marker run
`build/gr-v3-behavior/restart_prompt_marker_suite.json` builds hidden and
visible prompt-marker controls plus matching Escape-cancel restart cases. The
hidden cancel capture matches the hidden control with 0 prompt-row foreground
pixels; the visible cancel capture matches the visible control with 8
foreground pixels. This validates the source-mapped canceled branch of GR
action `0x80` without relying on whole-screen text semantics.

The GR condition dispatcher compares predicate bytes with `0x26`, matching the
loose bound shape also seen in SQ2, but only the first 19 entries
`0x00..0x12` are structured table records in the observed `AGIDATA.OVL`. Bytes
after that overlap punctuation/filename/string data and zeros, so they are
treated as reserved/unconfirmed rather than implemented predicates. Local GR
scripts observed so far use conditions only through `0x0e`.

Generated v3 logic fixtures can be built with:

```bash
python3 -B tools/qemu_fixture.py v3-logic payload.bin \
  --game-dir games/GR \
  --logic 0 \
  --output build/qemu-fixtures/gr_logic_000
```

This copies the selected v3 game to the generated output directory, appends a
direct/uncompressed v3 record to the existing prefixed volume for the selected
logic resource, and patches that logic entry inside the combined directory.

Generated v3 picture fixtures can be built with:

```bash
python3 -B tools/qemu_fixture.py v3-synthetic-picture payload.pic \
  --game-dir games/GR \
  --picture 0 \
  --volume 1 \
  --output build/qemu-fixtures/gr_picture_000
```

The picture payload is the expanded picture command stream ending with `0xff`;
the fixture writer stores it through the observed v3 picture-nibble transform
and patches the selected picture directory entry. Passing `--volume` is useful
when replacing a previously absent resource; otherwise the existing directory
entry volume can be reused.

Generated v3 picture/view fixtures can be built with:

```bash
python3 -B tools/qemu_fixture.py v3-synthetic-picture-view payload.pic \
  0 0 0 0 20 80 15 \
  --view-payload payload.view \
  --game-dir games/GR \
  --volume 1 \
  --output build/qemu-fixtures/gr_picture_view_000
```

The optional view payload is appended as a direct v3 record. This is sufficient
for controlled synthetic probes that need a known view body, but it is not a
general dictionary-compression writer. Original compressed GR resources remain
decoded through `tools/agi_resources.py`.

The generated v3 picture/view path is QEMU-validated by
`build/gr-v3-behavior/synthetic_picture_view_suite.json`. That run builds a
blank control, a generated picture-only fixture, and a generated
picture-plus-view fixture. The original GR interpreter renders the
picture-nibble fixture differently from blank and renders the direct view record
differently from the picture-only fixture.

The static GR/SQ2 comparison report currently lives at
`build/gr-sq2-static/opcode_static_report.md`. Source-level comparison found
identical parser contracts for all shared actions and conditions, 17 changed
shared action entry snippets, six GR-only action slots, unchanged ordinary view
and picture command skeletons after resource expansion, and a small set of GR
object/display-path deltas to test later.

## Fixture Compatibility Notes

Generated fixtures must never patch files under `games/`. The source game is
copied into a destination under `build/`, copied files are made writable, and
only that generated copy is modified. This matters because private game inputs
may intentionally be read-only and because each interpreter version can require
different container-writing rules.

Current v2 fixture writers still assume the SQ2-style split-directory format.
The v3 path supports direct/uncompressed logic and view replacement plus
picture-nibble picture replacement in a copied combined-directory game. Future
v3 probes that need generated compressed logic/view/sound records would still
need a dictionary encoder, but controlled fixtures can use direct records. The
current direct view and picture-nibble picture path has been checked against the
original GR interpreter with the synthetic picture/view QEMU probe.
