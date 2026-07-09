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

The v3 logic dispatcher tables are larger than SQ2's v2 tables. The Gold Rush
interpreter accepts action opcodes through `0xb5` and condition opcodes through
`0x25`, but the decoded local Gold Rush scripts observed so far only use action
opcodes through `0xa9` and condition opcodes through `0x0e`.

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
