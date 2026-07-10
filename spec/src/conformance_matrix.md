# Conformance Matrix

This chapter classifies the contracts in this book. It distinguishes behavior
shared by the promoted profiles, explicit profile variants, dimensions supplied
by the selected game data, unresolved behavior, and behavior outside the
current target.

The classifications are:

| Classification | Meaning |
| --- | --- |
| Common | The stated contract applies to both promoted profiles. |
| Profile variant | The profile selects a stated alternative. |
| Game data | The format and interpretation are fixed, but counts, names, sizes, or values come from the selected game. |
| Partial | Some observable behavior is specified, but the listed gap prevents a complete claim for that domain. |
| Outside target | No compatibility claim is made for this behavior. |

An unlisted difference must not be inferred from a version-number similarity.

## Common behavioral core

These contracts apply to both 2.936 and 3.002.149 unless a profile-variant row
below says otherwise:

| Domain | Contract |
| --- | --- |
| Logic payloads | Code-length framing, message table, message XOR decoding, control-flow markers, conditions `0x00..0x12`, and shared action semantics. |
| Runtime values | Unsigned byte variables, packed flags, 40-byte strings, parsed words, inventory locations, object selectors, and cycle-visible state transitions. |
| Pictures | Expanded command stream, prepare/overlay/show lifecycle, visual and priority/control channels, line/fill/pattern raster rules, and terminator behavior. |
| Views | Expanded view/loop/cel structure, row-run decoding, transparency, mirroring, baseline placement, and priority composition. |
| Objects | Lifecycle, placement, cadence, movement, collision, priority/control acceptance, cel cycling, draw partitions, and refresh ordering. |
| Input and text | Event records, parser normalization and matching, mapped keys, modal input, text geometry, inventory selection, and menu construction. |
| Rooms and replay | Room-switch state changes, top-level re-entry, replay-pair language, checkpoints, and replay-without-rerecording. |
| Sound | Resource event structure, per-channel countdown scheduling, terminators, completion flags, and stop behavior. |

## Profile variants

### Resource and bytecode variants

| Domain | 2.936 | 3.002.149 |
| --- | --- | --- |
| Resource directory | Four split family directories. Any entry with first-byte high nibble `0xf` is absent. | One combined prefixed directory, with split-directory fallback. Only `ff ff ff` is absent. |
| Volume record | Five-byte header; payload stored directly. | Seven-byte header; direct, dictionary-expanded, or picture-nibble-expanded payload. |
| Action range | `0x00..0xaf`. | `0x00..0xb5`. |
| Extra actions | None. | `0xb1` sets menu gate; `0xb5` clears release gate; `0xb0`, `0xb2`, `0xb3`, and `0xb4` consume operands without another effect. |
| Condition range | `0x00..0x12`. | `0x00..0x12`. |

### Runtime and presentation variants

| Domain | 2.936 | 3.002.149 |
| --- | --- | --- |
| Script key-map capacity | 39 entries. | 49 entries. |
| Release-event gate action `0xad` | Increment modulo 256. | Set to one. |
| Menu interaction gate | No separate gate. | Action `0xb1` selects whether a pending request may enter modal interaction. |
| Input-width actions `0xa3`/`0xa4` | Enable and clear the fixed width override. | No effect. |
| Immediate room aliases | None. | `0x7e`, `0x7f`, and `0x80` map to `0x49`. |
| Direction-selected loops | Four-or-more-loop table applies without `f20`. | Exactly four loops always use the table; more than four require `f20`. |

### Persistence variants

| Domain | 2.936 | 3.002.149 |
| --- | --- | --- |
| Save envelope | 31-byte description plus five `u16le` length-prefixed blocks. | Same envelope. |
| Block layout | All five observed game blocks are mapped in the persistence chapter. | Block lengths are known for the observed game, but field maps are incomplete. |
| Block transform | No transform for block 3. | Block 3 is XOR-transformed with the specified repeating `Avis Durgan` key. |
| Binary save interchange status | Defined for mapped fields; opaque block-1 ranges must be preserved. | Partial; do not claim arbitrary binary interchange. |

## Game-data dimensions

These values are not universal interpreter constants:

| Dimension | Source and effect |
| --- | --- |
| Resource presence and count | Directory entries determine which numbered logic, picture, view, and sound resources exist. |
| Resource bytes | Logic behavior, pictures, cels, sounds, messages, and dictionary words come from the selected game. |
| Combined-container prefix | The selected game supplies the v3 directory and volume filename prefix. |
| Inventory item count and names | The decoded inventory metadata header and item/name region define them. |
| Drawable-object count | `maximum_drawable_object_index + 1` from inventory metadata defines the record count. |
| Save blocks 2 and 3 lengths | Object count and decoded inventory metadata length determine them. |
| Replay storage length | The configured replay-pair capacity determines block 4 length. |
| Logic-resume block length | The cache population at save time determines block 5 length. |
| Signature and save stem | The accepted game signature establishes candidate validation and filename stem. |
| Room and object initial state | Logic resources and inventory locations establish game-specific state within the common transition rules. |

Conformance tests must state both the interpreter profile and selected game
data. A result obtained with one game does not establish another game's counts,
resource availability, names, save dimensions, or scripted behavior.

## Partial domains

| Domain | Specified portion | Remaining limitation |
| --- | --- | --- |
| Ordinary text presentation | Character cells, rows, columns, attributes, windows, configured modal-message row/column/width, prompt/status behavior, and modal ordering. | Exact glyph bitmaps remain outside the current portable core. |
| Glyph output | Text consumes an 8-by-8 font input. | This revision does not prescribe one exact platform glyph bitmap set. |
| Four-channel sound | Event timing, tone order, attenuation output boundary, silence, and completion. | The full attenuation-envelope initialization and transition contract is incomplete. |
| 2.936 save opaque state | Every byte has a field or opaque-range assignment. | Five block-1 ranges have no resolved valid-execution meaning; preserve them for byte interchange. |
| 3.002.149 save state | Envelope, observed Gold Rush block lengths, restore control flow, signature behavior, byte-complete block-1 partition, 23 object records, decoded 131-entry transformed inventory block, 50 replay pairs, and block-5 resume grammar. | Opaque block-1 ranges preserve bytes but do not yet have resolved valid-execution meanings. |
| Additional interpreter versions | They may be inventoried separately. | They have no normative profile until each observable delta is promoted. |

## Outside the current target

The following behavior is excluded from a current full-EGA conformance claim:

- malformed resources that escape their declared payload and consume unrelated
  memory or execute unintended code;
- non-EGA display adapters and alternate display-mode rendering;
- exact analog waveform synthesis beyond the specified sound-event/output
  boundary;
- original process memory organization, addresses, overlays, allocation
  strategy, and instruction-level timing; and
- unspecified failure presentation such as out-of-memory UI unless a chapter
  explicitly promotes that path.

## Claim requirements

A **2.936 full-EGA gameplay** claim requires the common core, every 2.936
variant, selected-game dimensions, and all non-persistence state transitions.
It may exclude the partial text-parameter and exact-amplitude gaps only when the
claim states those exclusions.

A **2.936 binary save interchange** claim additionally requires the five-block
mapping, first-match logic-resume lookup, replay reconstruction, and
byte-preservation of opaque ranges.

A **3.002.149 full-EGA gameplay** claim requires the common core plus every
3.002.149 resource, opcode, input, menu, room, and object-loop variant. This
revision does not yet support a complete 3.002.149 binary save interchange
claim.

No claim for another interpreter version follows automatically from either
promoted profile.
