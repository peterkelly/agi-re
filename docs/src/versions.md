# Versions

This chapter tracks observed differences between local interpreter/game inputs.
The goal is to keep version-specific facts separate from the portable AGI
behavioral spec. Entries here are evidence from local files and local tools,
not external AGI documentation.

## Observed Inputs

| Local input | Version evidence | Executable form | Resource container | Fixture status |
| --- | --- | --- | --- | --- |
| `games/SQ2` | `AGIDATA.OVL` string `Version 2.936` | `AGI` is decrypted from the loader-managed local bytes before disassembly | Split `LOGDIR`, `PICDIR`, `VIEWDIR`, `SNDDIR`; `VOL.N` files; 5-byte record headers; direct resource payloads | Current generated QEMU fixtures target this v2 split layout |
| `games/GR` | `AGIDATA.OVL` string `Version 3.002.149` | `AGI` is already an MZ executable | Combined `GRDIR`; prefixed `GRVOL.N` files; 7-byte record headers; dictionary and picture-nibble transforms | Decoding/parsing is implemented locally; generated QEMU fixture writing is not yet version-3-aware |

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

The GR condition dispatcher compares predicate bytes with `0x26`, matching the
loose bound shape also seen in SQ2, but only the first 19 entries
`0x00..0x12` are structured table records in the observed `AGIDATA.OVL`. Bytes
after that overlap punctuation/filename/string data and zeros, so they are
treated as reserved/unconfirmed rather than implemented predicates. Local GR
scripts observed so far use conditions only through `0x0e`.

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

Current fixture writers still assume the SQ2/v2 split-directory format. Before
using generated fixtures with a v3 game, add a writer that can produce a valid
combined directory, prefixed volume records, and any required v3 transform or
direct-read headers for the target interpreter.
