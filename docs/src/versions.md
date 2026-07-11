# Versions

This chapter tracks observed differences between local interpreter/game inputs.
The goal is to keep version-specific facts separate from the portable AGI
behavioral spec. Entries here are evidence from local files and local tools,
not external AGI documentation.

## Observed Inputs

| Local input | Version evidence | Executable form | Resource container | Fixture status |
| --- | --- | --- | --- | --- |
| `games/SQ1` | `AGIDATA.OVL` string `Version 2.089` | `SQ.EXE` is an MZ executable | Split direct v2 resources | Initial source comparison complete; partial profile records early opcode and plain-OBJECT differences |
| `games/XMAS` | `AGIDATA.OVL` string `Version 2.272` | `AGI.EXE` is an MZ executable | Split direct v2 resources in a multi-disk distribution layout | Initial source comparison complete; partial profile records menu stubs, exit selector, and plain-OBJECT behavior |
| `games/BC` | `AGIDATA.OVL` string `Version 2.439` | `AGI` is decoded with the selected game's `SIERRA.COM` key | Split direct v2 resources | Mapped full-EGA core matches 2.440 after relocation; selected save dimensions observed |
| `games/KQ2` | `AGIDATA.OVL` string `Version 2.411` | `AGI` is decoded with the selected game's `SIERRA.COM` key before disassembly | Split direct v2 resources | Full-EGA resource, logic, input, persistence, renderer, object, and sound profile is promoted; KQ2 save dimensions are mapped |
| `games/LSL1` | `AGIDATA.OVL` string `Version 2.440` | `LL.COM` is already a complete MZ interpreter despite its extension | Split direct v2 resources | Full-EGA profile is promoted; LSL1 save dimensions are mapped |
| `games/MG` | `AGIDATA.OVL` string `Version 2.915` | `AGI` is an MZ executable | Split direct v2 resources | Mapped full-EGA core matches 2.917 after relocation; selected save dimensions observed |
| `games/KQ1` | `AGIDATA.OVL` string `Version 2.917` | `AGI` is decrypted with the selected game's `SIERRA.COM` key before disassembly | Split `LOGDIR`, `PICDIR`, `VIEWDIR`, `SNDDIR`; direct `VOL.N` records | Full-EGA resource, logic, input, persistence, renderer, and object profile is promoted; KQ1 save dimensions are mapped |
| `games/SQ1.22` | `AGIDATA.OVL` string `Version 2.917` | `AGI` is decoded with the selected game's `SIERRA.COM` key | Split direct v2 resources | Loaded interpreter differs from KQ1 at only three signature bytes; selected save dimensions observed |
| `games/PQ1` | `AGIDATA.OVL` string `Version 2.917` | `AGI` is already an MZ executable | Split direct v2 resources | Same-version executable cross-check; PQ1 save dimensions are mapped |
| `games/SQ2` | `AGIDATA.OVL` string `Version 2.936` | `AGI` is decrypted from the loader-managed local bytes before disassembly | Split `LOGDIR`, `PICDIR`, `VIEWDIR`, `SNDDIR`; `VOL.N` files; 5-byte record headers; direct resource payloads | Current generated QEMU fixtures target this v2 split layout |
| `games/KQ3` | `AGIDATA.OVL` string `Version 2.936` | `AGI` is decoded with the selected game's `SIERRA.COM` key before disassembly | Split direct v2 resources | Same-version executable cross-check; KQ3 save dimensions are mapped |
| `games/KQ4` | `AGIDATA.OVL` string `Version 3.002.086` | `AGI` is an MZ executable | Combined `KQ4DIR`; prefixed `KQ4VOL.N` files; v3 transforms | Full-game full-EGA resource, logic, input, persistence, renderer, and object profile is promoted |
| `games/KQ4D` | `AGIDATA.OVL` string `Version 3.002.102` | `AGI` is an MZ executable | Combined `DMDIR`; prefixed `DMVOL.N` files; v3 transforms | Full-EGA resource, logic, input, persistence, renderer, and object profile is promoted |
| `games/MH1` | `AGIDATA.OVL` string `Version 3.002.107` | `AGI` is an MZ executable | Combined `MHDIR`; prefixed `MHVOL.N` files; v3 transforms | Dispatch contracts and currently mapped full-EGA core match 3.002.102 after relocation |
| `games/GR` | `AGIDATA.OVL` string `Version 3.002.149` | `AGI` is already an MZ executable | Combined `GRDIR`; prefixed `GRVOL.N` files; 7-byte record headers; dictionary and picture-nibble transforms | Decoding/parsing is implemented locally; generated fixtures can patch copied v3 directories/volumes with direct logic/view records and picture-nibble picture records under `build/` |
| `games/MH2` | `AGIDATA.OVL` string `Version 3.002.149` | `AGI` is an MZ executable | Combined `MH2DIR`; prefixed `MH2VOL.N` files; v3 transforms | Same-version control proves the Gold Rush room aliases are build-specific |

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
| `games/SQ1` | `Version 2.089` | v2 split | Direct records; 155 actions `0x00..0x9a`. |
| `games/XMAS` | `Version 2.272` | v2 split | Original multi-disk package records three disk numbers while selecting a single `VOL.0`; generic installed-layout record errors are packaging artifacts. |
| `games/BC` | `Version 2.439` | v2 split | Direct records. |
| `games/KQ2` | `Version 2.411` | v2 split | Direct `VOL.N` records. |
| `games/LSL1` | `Version 2.440` | v2 split | Direct `VOL.N` records. |
| `games/MG` | `Version 2.915` | v2 split | Direct records. |
| `games/KQ1` | `Version 2.917` | v2 split | Direct records for most resources; four sound entries currently fail the generic v2 header check and need source inspection before modeling. |
| `games/SQ1.22` | `Version 2.917` | v2 split | Direct records; same loaded interpreter core as KQ1. |
| `games/PQ1` | `Version 2.917` | v2 split | Direct `VOL.N` records. |
| `games/KQ3` | `Version 2.936` | v2 split | Direct `VOL.N` records. |
| `games/SQ2` | `Version 2.936` | v2 split | Two known out-of-range end entries remain record errors in the generic census. |
| `games/KQ4` | `Version 3.002.086` | v3 combined | Full game; combined `KQ4DIR`/`KQ4VOL.N`. The selected copy lacks volumes 6 and 7, leaving pictures `150..151` and views `198..199` unreadable. |
| `games/KQ4D` | `Version 3.002.102` | v3 combined | Combined `DMDIR`/`DMVOL.N`; dispatch tables are at AGIDATA offsets `0x0620`/`0x0942`. Decoded scripts currently reference only sound resources `70..79`, which are clean records; later suspect sound-section entries need source inspection before modeling. |
| `games/MH1` | `Version 3.002.107` | v3 combined | Combined `MHDIR`/`MHVOL.N`; readable scripts directly reference six unreadable views, so the selected copy is incomplete for full valid-data analysis. |
| `games/GR` | `Version 3.002.149` | v3 combined | Combined `GRDIR`/`GRVOL.N`; all present records expand with the current v3 reader. |
| `games/MH2` | `Version 3.002.149` | v3 combined | Combined `MH2DIR`/`MH2VOL.N`; readable scripts do not directly reference unreadable resources, but 31 unreadable logic records prevent a complete reachability claim. |

This is an inventory for planning. The portable spec should only gain a
version-specific rule when disassembly or a valid-resource dynamic check shows
that game scripts can observe the behavior.

## KQ2 / AGI 2.411 and LSL1 / AGI 2.440

KQ2's transformed `AGI` was decoded with its local loader key:

```bash
python3 -B tools/decrypt_agi.py --game-dir games/KQ2 \
  --output build/cross-version/kq2_agi.decrypted.exe
```

LSL1 packages its complete 38 KiB MZ image as `LL.COM`; no separate `AGI` or
`SIERRA.COM` is present. Both builds have action table
`AGIDATA.OVL:0x061b`, condition table `0x08e3`, and a geometry-derived count of
170 actions `0x00..0xa9` plus 19 conditions `0x00..0x12`. Their dispatchers at
image `0x0291` independently compare the action byte with `0xa9`.

The table and subsystem reports are:

```bash
python3 -B tools/compare_interpreter_tables.py \
  --left-label KQ2-2.411 --left-game-dir games/KQ2 \
  --left-exe build/cross-version/kq2_agi.decrypted.exe \
  --right-label LSL1-2.440 --right-game-dir games/LSL1 \
  --right-exe games/LSL1/LL.COM \
  --output build/cross-version/kq2_lsl1_table_comparison.md
```

All 170 action table records and all 19 condition records match. All condition
handlers match after normalization. The only action-handler difference is
restart `0x80`:

- KQ2 image `0x241f` always enters confirmation.
- LSL1 image `0x2435` tests `f16` and accepts restart without prompting while
  it is set, matching the later 2.917 behavior.

Both builds' configured-message handlers physically consume message, row,
column, and width. Their AGIDATA records for `0x97`/`0x98` report count 3,
which initially caused the local linear disassembler to drift after those
actions. Handler helpers KQ2 `0x1c43` and LSL1 `0x1c59` each read all three
bytes following the already-consumed message selector. The disassembler now
uses an effective width of four while preserving the raw table observation.

Compared with 2.917, both early builds omit actions `0xaa..0xad`. Their screen
shake lacks an alternate display-mode-4 branch outside the current target.
Their heap diagnostic formats only `heapsize`, `now/max`, and `max script`; the
later `rm.0, etc.` line is absent.

The 55-role KQ2/LSL1 renderer/object report covers resource and view loading,
picture lifecycle, every command/raster helper, update lists, collision,
placement, animation, and motion. The view, line, fill, composition, and motion
paths match after relocation. Both builds use automatic direction-loop
selection only for exactly four loops and accept object motion modes 1 through
3.

Picture-command differences are concentrated in the pattern commands:

- KQ2 `0xf9` at image `0x61f5` consumes its byte and returns without storing
  it. KQ2 `0xfa` at `0x625e` repeatedly reads coordinate pairs and calls the
  ordinary pixel writer once per pair.
- LSL1 `0xf9` at `0x62b9` stores the mode, and its pattern implementation from
  `0x6294` through `0x6397` normalizes fully with the 2.917 implementation.
- KQ2 uses byte operations for the low draw-state byte in `0xf0..0xf3`, while
  LSL1 uses word operations. The upper byte is initialized but never read;
  raster helpers read only the low byte, so this is not a full-EGA output
  difference.

The selected KQ2 pictures do not use `0xf9` or `0xfa`. Five selected LSL1
pictures use `0xfa` but never use `0xf9`, so they retain zero-radius single
pixel plots. The source difference remains valid for other valid picture data.

The early sound drivers share event parsing and countdown scheduling but have
no later attenuation-envelope arrays. Driver start initializes stream pointers,
countdowns, and active words only. Event output adds the global attenuation
adjustment directly to the control low nibble and clamps it to `0x0f`; no
attenuation output occurs on intervening countdown ticks. Selector zero uses
one PC-speaker channel, while every nonzero selector uses four channels.

KQ2 tone helper `0x7ce9` always writes both non-PC tone bytes. LSL1 helper
`0x7e0c` writes the high byte and suppresses the low byte when the high byte's
top three bits are set. Their driver starts are `0x7bc9`/`0x7cec`, ticks are
`0x7c2b`/`0x7d4e`, stop cores are `0x7cca`/`0x7ded`, and timer hooks are
`0x809a`/`0x81c3`.

Both save writers use the common five-block grammar but write only
`0x05e1 - 2 = 0x05df` bytes from the block-1 base. Relative to 2.917, this is
the common prefix through display-bottom-row state and omits the final
two-byte saved replay checkpoint.

| Selected game | Block 1 | Block 2 | Block 3 | Block 4 | Block 5 |
| --- | ---: | ---: | ---: | ---: | --- |
| KQ2 | `0x05df` | 17 records, `0x02db` | 85 items, `0x0256` | 60 pairs, `0x0078` | Variable |
| LSL1 | `0x05df` | 17 records, `0x02db` | 21 items, `0x0134` | 144 pairs, `0x0120` | Variable |

Two existing KQ2 saves and three LSL1 saves have exactly these first four block
lengths. Their block-3 bytes are stored directly without a transform.

This evidence promotes separate 2.411 and 2.440 full-EGA profiles and
selected-game binary-save dimensions.

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

## Same-version cross-checks: PQ1 and KQ3

PQ1 supplies a second 2.917 build and KQ3 supplies a second 2.936 build. KQ3
was decoded with its local loader key; PQ1's `AGI` is already an MZ image.

```bash
python3 -B tools/decrypt_agi.py --game-dir games/KQ3 \
  --output build/cross-version/kq3_agi.decrypted.exe

python3 -B tools/compare_interpreter_tables.py \
  --left-label PQ1-2.917 --left-game-dir games/PQ1 \
  --left-exe games/PQ1/AGI \
  --right-label KQ1-2.917 --right-game-dir games/KQ1 \
  --right-exe build/cross-version/kq1_agi.decrypted.exe \
  --output build/cross-version/pq1_kq1_table_comparison.md

python3 -B tools/compare_interpreter_tables.py \
  --left-label KQ3-2.936 --left-game-dir games/KQ3 \
  --left-exe build/cross-version/kq3_agi.decrypted.exe \
  --right-label SQ2-2.936 --right-game-dir games/SQ2 \
  --right-exe build/cleanroom/SQ2_AGI.decrypted.exe \
  --output build/cross-version/kq3_sq2_table_comparison.md
```

PQ1/KQ1 have identical 174 action records, action handlers, 19 condition
records, and condition handlers. Their loaded images are both 38,912 bytes and
differ at only three bytes in the embedded expected-game signature. Every one
of the 55 renderer/object/resource roles matches at the same address.

KQ3/SQ2 likewise have identical 176 action and 19 condition contracts and
handlers. Their loaded images are 38,912 bytes and differ at only two bytes,
changing the embedded signature from `S2` to `K3`. All subsystem roles remain
at the same address and normalize identically.

The engines therefore provide strong same-version evidence for the promoted
behavioral profiles. Their game-data save dimensions differ:

| Selected game | Profile | Block 1 | Block 2 | Block 3 | Block 4 | Block 5 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| PQ1 | 2.917 | `0x05e1` | 20 records, `0x035c` | 25 items, `0x016e` | 250 pairs, `0x01f4` | Variable |
| KQ3 | 2.936 | `0x05e1` | 17 records, `0x02db` | 55 items, `0x0307` | 127 pairs, `0x00fe` | Variable |

Two structurally valid local PQ1 saves confirm the PQ1 first-four block
lengths. A third file named `SQSG.1` is truncated before block 4 and is not
used as valid interchange evidence. KQ3 has no local save fixture; its
dimensions come from decoded `OBJECT` metadata, the identical save writer, and
logic 0 action `0x8e(127)`.

## Script-visible resource reference audit

The helper `tools/resource_reference_audit.py` compares immediate resource
numbers used by decoded logic bytecode against the selected game's readable and
unreadable directory entries. It is intentionally conservative: variable-based
resource numbers are not counted as fixed script references.

The current focused command was:

```bash
python3 -B tools/resource_reference_audit.py \
  --game-dir games/KQ1 \
  --game-dir games/KQ4 \
  --game-dir games/KQ4D \
  --output build/cross-version/resource_reference_audit_profiles.json
```

Current result:

| Local input | Resource family | Immediate script references | Unreadable directory entries | Referenced unreadable entries |
| --- | --- | ---: | --- | --- |
| `games/KQ1` | sound | 21 entries, max `21` | `34`, `35`, `36`, `37` | none |
| `games/KQ4` | picture | none immediate; picture selection is variable-based | `150`, `151` (missing `KQ4VOL.6`) | none immediate |
| `games/KQ4` | view | 241 entries, max `255` | `198`, `199` (missing `KQ4VOL.7`) | none |
| `games/KQ4D` | sound | 10 entries, max `79` | `221`, `223..236`, `387..394`, `423..427`, `583..587`, `660..661` | none |

Conclusion: these unreadable sound-directory entries remain cross-version
planning evidence, not valid-resource behavior for the clean spec. If a future
game script computes those numbers through variables, or if another interpreter
version accepts the same directory bytes through a source-mapped path, inspect
that case directly before promoting a rule.

The KQ4 picture result needs the strongest caveat: its scripts select pictures
through variables, so the absence of an immediate reference does not prove the
missing-volume entries are unreachable. They are excluded from the valid-data
profile because their selected volume files are absent.

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

## KQ4 full game / AGI 3.002.086

The newly selected `games/KQ4` input is the full game, not the KQ4D demo. Its
embedded version is `3.002.086`, earlier than KQ4D's `3.002.102`. The combined
directory prefix is `KQ4`, and the census finds 177 present logic resources,
148 readable pictures, 243 readable views, and 96 readable sounds. Most present
records use the v3 dictionary transform; three logic records and one sound
record are direct.

The first generic comparison falsely assigned KQ4 the later 182-action v3
table and interpreted trailer bytes as opcodes. The v3 table geometry has a
fixed `0x4a`-byte trailer between the action and condition tables. Computing
`(condition_base - action_base - 0x4a) / 4` gives 178 actions for KQ4 and 182
for KQ4D and Gold Rush. The generic detector now derives this count.

KQ4's action table begins at `AGIDATA.OVL:0x061d`, contains entries
`0x00..0xb1`, and is followed by the condition table at `0x092f`. Its action
dispatcher accepts through `0xb1`. All 178 shared action operand contracts and
all 19 condition contracts match KQ4D. The only shared action-handler
differences are:

| Opcode | KQ4 3.002.086 | KQ4D 3.002.102 |
| ---: | --- | --- |
| `0xad` | Increment the key-release gate byte modulo 256. | Set the gate to one. |
| `0xb0` | Consume one ignored operand and otherwise do nothing. | Consume no operand and otherwise do nothing. |

Action `0xb1` consumes one byte and stores it as the menu interaction gate.
The later `0xb2..0xb5` slots do not exist in this profile. Compared with SQ2,
KQ4 already has the v3 inventory-selector temporary state, block-3 save XOR,
restart prompt-marker behavior, and motion-mode-4 preservation. It retains
SQ2's direct room destinations, input-width actions, 39-entry key map, and
increment-style `0xad` release gate.

A 52-role KQ4/KQ4D source comparison covers view loading and cel selection,
picture lifecycle and every command/raster helper, object-list construction,
composition, placement, collision, control acceptance, dirty rectangles,
motion, and animation. All primary full-EGA roles match after relocation except
two observable edge branches:

- KQ4 applies automatic four-direction loop selection to every view with four
  or more loops, matching 2.936. KQ4D uses the later rule in which exactly four
  loops always qualify and larger counts require `f20`.
- KQ4 clamps a due proposed object X coordinate of exactly zero to zero and
  reports left-boundary code 4. KQ4D accepts exact zero without a boundary
  report. Both clamp negative proposals to zero and report code 4.

The KQ4 save and restore paths use the common five-block envelope. Block 1 is
the 2.936-shaped `0x05e1` bytes; KQ4's menu and release gates lie outside that
serialized range. The object/inventory block is XOR-transformed with the same
observed repeating key as the later v3 profiles. Decoded full-game metadata and
logic 0 establish these selected-game dimensions:

| Block | Full KQ4 dimension |
| ---: | --- |
| 1 | `0x05e1` bytes |
| 2 | 26 object records: `26 * 0x2b = 0x045e` bytes |
| 3 | 45 inventory entries and name pool: `0x02c6` bytes on decoding |
| 4 | 250 replay pairs: `0x01f4` bytes |
| 5 | Variable common logic-resume grammar |

This evidence promotes full KQ4/3.002.086 as a distinct full-EGA gameplay
profile and defines binary-save interchange for the mapped full-game
dimensions. It must not be conflated with the later KQ4D demo build.

## KQ4D demo / AGI 3.002.102

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

## Additional local builds: 2.089 through 3.002.149

The expanded census added seven independent interpreter inputs. The generated
snapshot is `build/cross-version/game_census_expanded.md`. Table comparison
reports under `build/cross-version/` use geometry-derived action counts; early
v2 builds required recognizing the observed `0x26`-byte trailer in addition to
the later `0x20`-byte trailer.

### SQ1 2.089 and XMAS 2.272

SQ1 accepts 155 actions `0x00..0x9a`; XMAS accepts 161 actions
`0x00..0xa0`. Both retain 19 conditions. Direct disassembly establishes these
early action differences:

| Behavior | SQ1 2.089 | XMAS 2.272 |
| --- | --- | --- |
| Action `0x86` | No operands; stops sound, performs shutdown cleanup, and terminates. | One selector byte; `1` exits directly, while other values ask for confirmation. |
| Action `0x9b` | Unavailable. | Consumes two bytes and has no other effect. |
| Actions `0x9c..0xa0` | Unavailable. | Dispatch to operand-advance stubs at image `0x8400..0x8404`; no menu state is constructed. |
| Position actions `0x25`/`0x26` | Write current coordinates, remove old rendered state if drawn, then update the previous-position snapshot. | Write current and previous coordinates together without first removing rendered state. |

The XMAS string-equality predicate's shorter entry merely delegates to a
normalization helper; its helper still removes ignored characters, normalizes
case, and compares normalized strings. It is not an observable predicate
difference.

Both games store `OBJECT` metadata directly rather than through the later
repeating-key XOR. SQ1's plain header is `4e 00 11`, defining 26 inventory
entries and 18 drawable-object records. XMAS uses `03 00 11`, defining one
inventory entry and 18 drawable-object records. Local parser tests preserve
both observations.

XMAS also retains three installation methods. `ORIGINAL.BAT` selects
`VOL.ORG`, `LOGDIR.ORG`, and `PICDIR.ORG`; `LOGMETH.BAT` and `VOLMETH.BAT`
select modified alternatives. The active local files match the original set.
Its directory volume nibbles represent three distribution disks while the
selected payload is named `VOL.0`, so an installed-layout census incorrectly
reports missing `VOL.1`/`VOL.2`. This is packaging evidence, not malformed
resource semantics.

### BC 2.439, MG 2.915, and SQ1.22 2.917

BC's loader-transformed executable was decoded with its own `SIERRA.COM`.
Its 170 action and 19 condition table records match LSL1 2.440 exactly. Of 38
principal symbolic roles, 33 uniquely relocate, two list wrappers are
ambiguous, and three short embedded entries are not uniquely searchable.
Manual source inspection confirms that the shaped/stippled pattern code and
timer-driven sound path are relocated byte matches. The mapped full-EGA core
therefore follows the 2.440 behavior.

MG 2.915 has the same 174 action and 19 condition contracts as KQ1 2.917.
Twenty-nine of 32 principal roles uniquely relocate and match; two wrappers are
ambiguous and the embedded frame jump table requires manual mapping. The
mapped full-EGA core follows 2.917.

SQ1.22's loaded interpreter image and KQ1's are the same length and differ at
only three bytes in the embedded game-signature region. All 34 mapped roles
match at the same addresses. It is a second 2.917 build, not a new behavioral
profile.

Original saves supply these selected-game dimensions:

| Selected game | Profile | Block 1 | Block 2 | Block 3 | Block 4 | Block 5 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| BC | 2.439/2.440 rules | `0x05df` | 17 records, `0x02db` | 26 items, `0x0135` | 127 pairs, `0x00fe` | Variable |
| MG | 2.915/2.917 rules | `0x05df` | 21 records, `0x0387` | one item, `0x0005` | 110 pairs, `0x00dc` | Variable |
| SQ1.22 | 2.917 | `0x05e1` | 18 records, `0x0306` | 25 items, `0x0148` | 50 pairs, `0x0064` | Variable |

MG's decoded `OBJECT` header byte would imply 91 drawable records, while its
original save and save-writer globals select 21 records. The portable meaning
of that header byte is therefore not universal across these builds; the MG
case remains an explicit metadata/save-dimension investigation.

### MH1 3.002.107 and MH2 3.002.149

MH1 has 182 actions and 19 conditions. Its contracts and every currently
mapped full-EGA core handler match KQ4D 3.002.102 after relocation. The whole
loaded images are not identical and MH1 is 64 bytes longer, so startup,
diagnostic, and alternate paths not represented by the role map are not yet
claimed equivalent.

MH2 and Gold Rush are both labeled 3.002.149 and their loaded images have the
same length. Only 29 bytes differ. Those bytes classify completely as:

- a Gold Rush-only helper that maps immediate room operands `0x7e..0x80` to
  `0x49`, plus the `0x12` call site that uses it;
- three startup allocation-size words (`0x0a00` in Gold Rush and `0x0b80` in
  MH2); and
- the embedded expected game signature (`GR` versus `MH2`).

MH2 action `0x12` reads its operand and calls the ordinary room-switch path
directly. This same-version control corrects the earlier generalization: the
room aliases are a Gold Rush build feature, not universal 3.002.149 behavior.
The startup allocation-size difference is retained as diagnostic/capacity
evidence until a portable observable consequence is established.

Both selected v3 copies contain present directory entries that the current
census cannot read. The tolerant reference audit records unreadable source
logics instead of aborting:

| Selected game | Skipped source logics | Direct references from readable scripts to unreadable resources |
| --- | ---: | --- |
| MH1 | `136` | Views `7`, `74`, `75`, `76`, `77`, and `85` |
| MH2 | 31 logics | None observed |

MH1 is therefore incomplete for ordinary valid-data gameplay analysis. MH2's
readable subset is internally clean for immediate references, but skipped
logic resources mean absence of a reference is not a full reachability proof.
The generated report is
`build/cross-version/mh_resource_reference_audit.json`.

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
