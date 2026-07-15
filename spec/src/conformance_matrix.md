# Conformance Matrix

This chapter classifies the contracts in this book. It distinguishes behavior
shared by the promoted profiles, explicit profile variants, dimensions supplied
by the selected game data, unresolved behavior, and behavior outside the
current target.

The classifications are:

| Classification | Meaning |
| --- | --- |
| Common | The stated contract applies to all promoted profiles. |
| Profile variant | The profile selects a stated alternative. |
| Game data | The format and interpretation are fixed, but counts, names, sizes, or values come from the selected game. |
| Partial | Some observable behavior is specified, but the listed gap prevents a complete claim for that domain. |
| Outside target | No compatibility claim is made for this behavior. |

An unlisted difference must not be inferred from a version-number similarity.

The common core applies to profiles 2.089, 2.230, 2.272, 2.411, 2.440, 2.917, 2.936,
3.002.086, 3.002.102, and 3.002.149. The two-column tables compare 2.936 and
3.002.149, while separate tables select the other promoted variants.

## Common behavioral core

These contracts apply to every promoted profile unless a profile-variant row
below says otherwise:

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
| Immediate room aliases | None. | None in the base MH2 build; the Gold Rush build maps `0x7e`, `0x7f`, and `0x80` to `0x49`. |
| Direction-selected loops | Four-or-more-loop table applies without `f20`. | Exactly four loops always use the table; more than four require `f20`. |

### Persistence variants

| Domain | 2.936 | 3.002.149 |
| --- | --- | --- |
| Save envelope | 31-byte description plus five `u16le` length-prefixed blocks. | Same envelope. |
| Block layout | All five observed game blocks are mapped in the persistence chapter. | All five observed Gold Rush blocks are mapped in the persistence chapter. |
| Block transform | No transform for block 3. | Block 3 is XOR-transformed with the specified repeating `Avis Durgan` key. |
| Binary save interchange status | Defined for the mapped game/profile dimensions; reserved bytes use canonical initialization and byte preservation. | Defined for the mapped Gold Rush/profile dimensions; reserved bytes use canonical initialization and byte preservation. |

### 2.089 variant selection

| Domain | 2.089 behavior |
| --- | --- |
| Resource container | Split direct resources; inventory metadata is stored expanded. |
| Action and condition ranges | Actions `0x00..0x9a`; conditions `0x00..0x12`. |
| Exit and menu actions | `0x86` is an unconditional zero-operand exit; `0x9b` and later are unavailable. |
| Position and composition | Position actions remove old drawn state before updating the saved position. The earlier partition uses object-number order; the later partition uses drawing-key order. |
| Picture commands | Dispatch `0xf0..0xf8`; no pattern-command slots. |
| Show picture | Present and mark shown without clearing `f15` or closing an active text window. |
| Direction-selected loops | Evaluate every eligible post-logic pass, without a cadence gate; exactly four loops use the four-loop table. |
| String and parser profile | Six string slots; exact-count word matching without the `0x270f` tail terminator. |
| Object distance and target motion | Store wrapped low-byte distance; defer the first target direction/completion calculation. |
| Movement-clear actions | `0x4d` clears direction but not autonomous mode; `0x4e` leaves both unchanged and only applies object-0 coupling/navigation effects. |
| Inventory display | Always acknowledgement-only; never writes a selected item to `v25`. |
| Sound output | Selector zero uses one channel; all others use four. Emit both tone bytes; device 2 adds 3 to low attenuation values below 8, then emit the control byte. |
| Save envelope | Four blocks; no logic-resume block. Block 1 has a complete semantic partition. |
| Binary save interchange status | Existing saves can be parsed and restored state can be preserved; pristine synthesis requires canonical initial reserved bytes that are not currently specified. |

### 2.230 variant selection

| Domain | 2.230 behavior |
| --- | --- |
| Resource container | Split direct resources; inventory metadata is stored expanded. |
| Action and condition ranges | Actions `0x00..0x9a`; conditions `0x00..0x12`. |
| Exit and menu actions | `0x86` is an unconditional zero-operand exit; `0x9b` and later are unavailable. |
| Position and composition | Position actions update current/saved coordinates together. Both draw partitions use drawing-key order. |
| View loop encoding | The loop-header low nibble is the cel count; upper bits hold mutable loop-wide orientation and mirroring state. Action `0x31` masks to the low nibble. |
| Picture commands | Dispatch `0xf0..0xf8`; no pattern-command slots. |
| Show picture | Same retained-`f15` and retained-window behavior as 2.089. |
| Direction-selected loops | Same cadence-independent, exact-four behavior as 2.089. |
| String and parser profile | Six string slots; `0x270f` has tail-terminator meaning. |
| Object distance and target motion | Same wrapped distance and deferred first target update as 2.089. |
| Movement-clear actions | Same as 2.089: `0x4d` clears direction but not autonomous mode; `0x4e` leaves both unchanged and only applies object-0 coupling/navigation effects. |
| Inventory display | Always acknowledgement-only; never writes a selected item to `v25`. |
| Sound output | Same as 2.089: selector zero uses one channel; all others use four; emit both tone bytes and apply only the device-2 low-attenuation adjustment. |
| Save envelope | Five blocks with a semantically partitioned `0x03db` block 1. |
| Binary save interchange status | Existing state bytes can be parsed and preserved; pristine synthesis requires canonical initial reserved bytes that are not currently specified. |

### 2.272 variant selection

| Domain | 2.272 behavior |
| --- | --- |
| Resource container | Split direct resources; inventory metadata is stored expanded. |
| Action and condition ranges | Actions `0x00..0xa0`; conditions `0x00..0x12`. |
| Exit and menu actions | `0x86` consumes its selector; `0x9b` consumes two bytes; `0x9c..0xa0` consume their operands without constructing menu state. |
| Position and composition | Position actions update current/saved coordinates together. Both draw partitions use drawing-key order. |
| Picture commands | Dispatch `0xf0..0xf8`; no pattern-command slots. |
| Show picture | Same retained-`f15` and retained-window behavior as 2.089. |
| Direction-selected loops | Same cadence-independent, exact-four behavior as 2.089. |
| String and parser profile | Six string slots; `0x270f` has tail-terminator meaning. |
| Object distance and target motion | Same wrapped distance and deferred first target update as 2.089. |
| Movement-clear actions | `0x4d` clears direction and autonomous mode; `0x4e` clears autonomous mode while retaining direction. |
| Inventory display | Always acknowledgement-only; never writes a selected item to `v25`. |
| Sound output | Early channel selection; emit both tone bytes; apply the device-2 adjustment, then adjust and signed-clamp the entire control byte. |
| Save envelope | Five blocks with a semantically partitioned `0x03db` block 1. |
| Binary save interchange status | Existing saves can be parsed and restored state can be preserved; pristine synthesis requires canonical initial reserved bytes that are not currently specified. |

### 2.411 variant selection

| Domain | 2.411 behavior |
| --- | --- |
| Resource container | Four split family directories and five-byte direct volume records. |
| Action and condition ranges | Actions `0x00..0xa9`; conditions `0x00..0x12`. |
| Configured messages | `0x97` and `0x98` consume message, row, column, and width. |
| Restart confirmation | Always display the confirmation prompt; `f16` does not bypass it. |
| Heap diagnostic | Omit the `rm.0, etc.` line. |
| Pattern commands | `0xf9` consumes and ignores one byte; `0xfa` writes one pixel per X,Y pair without seeds. |
| Direction-selected loops | Exactly four loops use the four-loop table; larger counts do not receive automatic selection. |
| Sound channels | Selector 0 uses channel 0; every nonzero selector uses all four channels. |
| Sound command output | No attenuation envelopes or device-2 adjustment; always emit both non-PC tone bytes. |
| Save envelope | Five blocks with a `0x05df` block 1 and no block-3 transform. |
| Binary save interchange status | Defined for the mapped KQ2 dimensions. |

### 2.440 variant selection

| Domain | 2.440 behavior |
| --- | --- |
| Resource, opcode, configured-message, loop, and save profile | Same early boundaries as 2.411. |
| Restart confirmation | `f16` bypasses the prompt and accepts restart immediately. |
| Heap diagnostic | Omit the `rm.0, etc.` line. |
| Pattern commands | Use the common shaped/stippled `0xf9`/`0xfa` behavior. |
| Sound channels and attenuation | Early selector rule and no attenuation envelopes or device-2 adjustment. |
| Tone-byte output | Suppress the low byte when the high byte's top three bits are all set. |
| Binary save interchange status | Defined for the mapped LSL1 dimensions. |

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

### 3.002.086 variant selection

| Domain | 3.002.086 behavior |
| --- | --- |
| Resource container | Combined v3 directory and seven-byte volume records with direct, dictionary-expanded, or picture-nibble-expanded payloads. |
| Action range and extra slots | `0x00..0xb1`; `0xb0` consumes one ignored byte, and `0xb1` sets the menu gate. |
| Condition range | `0x00..0x12`. |
| Script key-map capacity | 39 entries. |
| Release-event gate action `0xad` | Increment modulo 256. |
| Input-width actions | `0xa3` and `0xa4` retain their v2 effects. |
| Immediate room aliases | None. |
| Direction-selected loops | Four-or-more-loop table applies without `f20`. |
| Exact-zero left proposal | Clamp to zero and report left-boundary code 4. |
| Pictures, views, and objects | Other full-EGA command, raster, composition, movement, collision, animation, update-list, and refresh contracts are common. |
| Save envelope and transform | Five length-prefixed blocks; block 3 uses the v3 repeating-key XOR transform. |
| Binary save interchange status | Defined for the mapped full KQ4 dimensions; block 1 uses the 2.936 partition and reserved-state rules. |

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
| Drawable-object count | The selected profile and game data define the runtime object-table capacity. In the fully mapped profiles this is `maximum_drawable_object_index + 1` from inventory metadata; that derivation must not be assumed for an unmapped profile. |
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

A **2.089 full-EGA gameplay** claim requires the common core plus every 2.089
resource, opcode-range, exit, picture, parser, object, motion, inventory,
composition, and sound variant. A **2.089 SQ1 binary save interchange** claim
additionally requires the selected SQ1 dimensions and a supplied rule for
canonical initial reserved bytes or preservation of bytes from an existing
save/state image.

A **2.230 full-EGA gameplay** claim requires the common core plus every 2.230
resource, opcode-range, exit, packed-view-loop, picture, parser, object,
motion, inventory, composition, and sound variant. A **2.230 XMAS.230 binary save interchange**
claim additionally requires the selected XMAS.230
dimensions and a supplied rule for canonical initial reserved bytes or
preservation of bytes from an existing save/state image.

A **2.272 full-EGA gameplay** claim requires the common core plus every 2.272
resource, opcode-range, exit/menu-stub, picture, parser, object, motion,
inventory, composition, and sound variant.

A **2.272 XMAS binary save interchange** claim additionally requires the
selected XMAS dimensions and a supplied rule for canonical initial reserved
bytes or preservation of bytes from an existing save/state image.

A **2.411 full-EGA gameplay** claim requires the common core plus every 2.411
opcode-range, restart, diagnostic, point-pattern, object-loop, and sound-output
variant. A **2.411 KQ2 binary save interchange** claim additionally requires
the mapped KQ2 dimensions, shortened block-1 partition, five-block mapping,
first-match logic-resume lookup, replay reconstruction, and reserved-state
rules.

A **2.440 full-EGA gameplay** claim requires the common core plus every 2.440
opcode-range, restart, diagnostic, pattern, object-loop, and sound-output
variant. A **2.440 LSL1 binary save interchange** claim additionally requires
the mapped LSL1 dimensions and the same early persistence rules.

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

A **2.917 PQ1 binary save interchange** claim uses the same profile rules with
the mapped PQ1 object, inventory, replay, signature, and logic-resume
dimensions.

A **2.936 KQ3 binary save interchange** claim uses the 2.936 profile rules with
the mapped KQ3 object, inventory, replay, signature, and logic-resume
dimensions.

A **3.002.086 full-EGA gameplay** claim requires the common core plus every
3.002.086 resource, opcode, input, menu, room, loop-selection, and exact-zero
left-boundary variant.

A **3.002.086 full KQ4 binary save interchange** claim additionally requires
the mapped full-game dimensions, five-block mapping, block-3 transform,
first-match logic-resume lookup, replay reconstruction, and canonical
initialization or byte-preservation of reserved state as applicable.

A **3.002.149 full-EGA gameplay** claim requires the common core plus every
3.002.149 resource, opcode, input, menu, room, and object-loop variant, and
must state whether it selects the base room behavior or the Gold Rush alias
variant.

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

No claim for another interpreter version follows automatically from a promoted
profile.
