# Versions

This chapter tracks observed differences between local interpreter/game inputs.
The goal is to keep version-specific facts separate from the portable AGI
behavioral spec. Entries here are evidence from local files and local tools,
not external AGI documentation.

## Observed Inputs

| Local input | Version evidence | Executable form | Resource container | Fixture status |
| --- | --- | --- | --- | --- |
| `games/SQ2` | `AGIDATA.OVL` string `Version 2.936` | `AGI` is decrypted from the loader-managed local bytes before disassembly | Split `LOGDIR`, `PICDIR`, `VIEWDIR`, `SNDDIR`; `VOL.N` files; 5-byte record headers; direct resource payloads | Current generated QEMU fixtures target this v2 split layout |
| `games/GR` | `AGIDATA.OVL` string `Version 3.002.149` | `AGI` is already an MZ executable | Combined `GRDIR`; prefixed `GRVOL.N` files; 7-byte record headers; dictionary and picture-nibble transforms | Decoding/parsing is implemented locally; generated direct-record logic fixtures can patch copied v3 directories/volumes under `build/` |

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
| `0xb1` | `set_menu_interaction_gate` | Reads one immediate byte, zero-extends it, and stores it in word `[0x0403]`. GR `code.menu.interact` at image `0x9724` returns immediately while `[0x0403] == 0`, so nonzero values enable the menu interaction path after the usual menu-request flag is set. |
| `0xb2` | `reserved_noop_v3_2` | Table entry has zero operands and routes to the generic no-op/return handler at image `0x5286`. |
| `0xb3` | `reserved_noop_v3_4args` | Table entry declares four fixed operands, but the handler is the generic no-op/return handler. |
| `0xb4` | `reserved_noop_v3_2varargs` | Table entry declares two variable operands via metadata `0xc0`, but the handler is the generic no-op/return handler. |
| `0xb5` | `clear_key_release_event_gate` | Stores zero in byte `[0x0405]`. GR action `0xad` sets the same byte to one, and the keyboard IRQ hook tests it before enqueueing a type-2 zero event on selected key-release paths. |

Source-backed shared action deltas, relative to SQ2 / AGI 2.936:

| Area | Opcodes | Observed GR / AGI 3.002.149 difference |
| --- | --- | --- |
| Input line and prompts | `0x6f`, `0x73`, `0x76`, `0x77`, `0x78`, `0x89`, `0x8a`, `0xa3`, `0xa4`, `0xa9` | GR keeps the normal EGA-style input-line model but removes SQ2's display-mode-2/input-width branches. It computes the display offset as `arg0 << 3`, always uses the normal prompt/editor path for string and number prompts, maps the SQ2 input-width set/clear actions to no-op, and closes active text-window state without clearing a width flag. |
| Key and menu events | `0x79`, `0xad`, `0xb1`, `0xb5` | GR expands the script key-map table from `0x27` to `0x31` four-byte slots. A QEMU fixture validates slot 48 by filling 48 dummy slots, mapping typed `x` in the final slot, and comparing against a direct nonblank picture draw; the no-key control remains blank. GR also replaces SQ2's incrementing key-release byte `[0x1530]` with set/clear byte `[0x0405]`, and adds menu interaction gate word `[0x0403]`. |
| Room and state actions | `0x12`, `0x7c`, `0x7d`, `0x80`, `0x84` | GR remaps immediate room targets `0x7e..0x80` to `0x49` before the ordinary room-switch helper; the decoded local GR scripts do contain those operands. The carried-item selector sets temporary word `[0x0dc1]` while handling a flag-13 input path and clears it on return. Save wraps the object/inventory chunk in an XOR pass before and after writing the save envelope; the observed transform uses a 59-byte sequence from image `0x072c`, modeled by `gr_v3_object_inventory_save_xor()` and QEMU-validated against blank-prefix `SG.1` and signed `GRSG.1` saves with block lengths `1028`, `989`, `1811`, `100`, and `12`. Restart records prompt-marker visibility before confirmation; accepted restart redraws the marker, and canceled restart redraws only if it had been visible. Action `0x84` preserves object 0 motion mode `4` instead of always clearing byte `+0x22`. |
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
logic resource, and patches that logic entry inside the combined directory. It
does not yet pack generated v3 picture or view payloads; those should be added
only when a targeted behavioral probe needs them.

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
The v3 path currently supports direct/uncompressed logic-record replacement in
a copied combined-directory game. Future v3 picture/view probes may need
additional fixture packing for picture-nibble or view/general transforms.
