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

The common core applies to profiles 2.917, 2.936, 3.002.102, and 3.002.149. The
two-column tables compare 2.936 and 3.002.149, while separate tables select the
2.917 and 3.002.102 variants.

## Common behavioral core

These contracts apply to 2.917, 2.936, 3.002.102, and 3.002.149 unless a
profile-variant row below says otherwise:

| Domain | Contract |
| --- | --- |
| Logic payloads | Code-length framing, message table, message XOR decoding, control-flow markers, conditions `0x00..0x12`, and shared action semantics. |
| Runtime values | Unsigned byte variables, packed flags, 40-byte strings, parsed words, inventory locations, object selectors, and cycle-visible state transitions. |
| Pictures | Expanded command stream, prepare/overlay/show lifecycle, visual and priority/control channels, line/fill/pattern raster rules, and terminator behavior. |
| Views | Expanded view/loop/cel structure, row-run decoding, transparency, mirroring, baseline placement, and priority composition. |
| Objects | Lifecycle, placement, cadence, movement, collision, priority/control acceptance, cel cycling, draw partitions, and refresh ordering. |
| Input and text | Event records, parser normalization and matching, mapped keys, modal input, text geometry, font-input boundary, inventory selection, and menu construction. |
| Rooms and replay | Room-switch state changes, top-level re-entry, replay-pair language, checkpoints, and replay-without-rerecording. |
| Sound | Resource event structure, per-channel countdown scheduling, terminators, tone/divisor output, attenuation command output, completion flags, and stop behavior. |

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
| Block layout | All five observed game blocks are mapped in the persistence chapter. | All five observed Gold Rush blocks are mapped in the persistence chapter. |
| Block transform | No transform for block 3. | Block 3 is XOR-transformed with the specified repeating `Avis Durgan` key. |
| Binary save interchange status | Defined for the mapped game/profile dimensions; reserved bytes use canonical initialization and byte preservation. | Defined for the mapped Gold Rush/profile dimensions; reserved bytes use canonical initialization and byte preservation. |

### 2.917 variant selection

| Domain | 2.917 behavior |
| --- | --- |
| Resource container | Four split family directories and five-byte direct volume records. |
| Action range | `0x00..0xad`; `0xae` and `0xaf` are not valid actions. |
| Condition range | `0x00..0x12`. |
| Script key-map capacity | 39 entries. |
| Release-event gate action `0xad` | Increment modulo 256. |
| Input-width actions | `0xa3` and `0xa4` retain their common effects. |
| Immediate room aliases | None. |
| Direction-selected loops | Exactly four loops use the four-loop table; more than four do not receive automatic selection. |
| Pictures, views, and objects | The full-EGA command, raster, composition, movement, collision, animation, update-list, and refresh contracts are common. |
| Save envelope | Five length-prefixed blocks with no block-3 transform. |
| Binary save interchange status | Defined for the mapped KQ1 dimensions; reserved bytes use canonical initialization and byte preservation. |

### 3.002.102 variant selection

| Domain | 3.002.102 behavior |
| --- | --- |
| Resource container | Combined v3 directory and seven-byte volume records with direct, dictionary-expanded, or picture-nibble-expanded payloads. |
| Action range and extra slots | `0x00..0xb5`; extra slots have the 3.002.149 contracts and effects. |
| Script key-map capacity | 39 entries. |
| Release and menu gates | `0xad` sets the release gate to one; `0xb5` clears it; `0xb1` sets the menu interaction gate. |
| Input-width actions | `0xa3` and `0xa4` retain their 2.936 effects; closing window state clears the override. |
| Immediate room aliases | None. |
| Direction-selected loops | Exactly four loops always use the table; more than four require `f20`. |
| Pictures, views, and objects | The full-EGA command, raster, composition, movement, collision, animation, update-list, and refresh contracts are common. |
| Save envelope and transform | Five length-prefixed blocks; block 3 uses the v3 repeating-key XOR transform. |
| Binary save interchange status | Defined for the mapped KQ4D demo dimensions; reserved bytes use canonical initialization and byte preservation. |

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
| Additional interpreter versions | They may be inventoried separately. | They have no normative profile until each observable delta is promoted. |

## Outside the current target

The following behavior is excluded from a current full-EGA conformance claim:

- malformed resources that escape their declared payload and consume unrelated
  memory or execute unintended code;
- non-EGA display adapters and alternate display-mode rendering;
- exact text-glyph bitmaps unless a claim explicitly supplies a font profile;
- exact analog waveform synthesis beyond the specified sound-event,
  tone/divisor, and attenuation-command output boundary;
- original process memory organization, addresses, overlays, allocation
  strategy, and instruction-level timing; and
- unspecified failure presentation such as out-of-memory UI unless a chapter
  explicitly promotes that path.

## Claim requirements

A **2.936 full-EGA gameplay** claim requires the common core, every 2.936
variant, selected-game dimensions, and all non-persistence state transitions.
A **2.936 binary save interchange** claim additionally requires the five-block
mapping, first-match logic-resume lookup, replay reconstruction, and
canonical initialization or byte-preservation of reserved state as applicable.

A **2.917 full-EGA gameplay** claim requires the common core plus every 2.917
resource, opcode, input, room, and object-loop variant.

A **2.917 KQ1 binary save interchange** claim additionally requires the mapped
KQ1 dimensions, five-block mapping, first-match logic-resume lookup, replay
reconstruction, and canonical initialization or byte-preservation of reserved
state as applicable.

A **3.002.149 full-EGA gameplay** claim requires the common core plus every
3.002.149 resource, opcode, input, menu, room, and object-loop variant.

A **3.002.149 Gold Rush binary save interchange** claim additionally requires
the five-block mapping, block-3 transform, first-match logic-resume lookup,
replay reconstruction, and canonical initialization or byte-preservation of
reserved state as applicable.

A **3.002.102 full-EGA gameplay** claim requires the common core plus every
3.002.102 resource, opcode, input, menu, room, and object-loop variant.

A **3.002.102 KQ4D demo binary save interchange** claim additionally requires
the selected demo's dimensions, five-block mapping, block-3 transform,
first-match logic-resume lookup, replay reconstruction, and canonical
initialization or byte-preservation of reserved state as applicable.

No claim for another interpreter version follows automatically from either
promoted profile.
