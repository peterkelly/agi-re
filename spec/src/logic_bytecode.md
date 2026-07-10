# Logic Bytecode

This chapter defines the logic resource framing, bytecode stream grammar, all
conditions, and the first promoted action families. Unless a version profile
says otherwise, opcode ranges and effects refer to AGI 2.936.

## Logic payload

An expanded logic resource has this layout:

```text
u16 code_length
u8  bytecode[code_length]
u8  message_count
u16 message_offset[message_count + 1]
u8  encrypted_message_text[]
```

The bytecode begins immediately after `code_length`. The message table begins
immediately after the bytecode. Every message offset is relative to the first
byte of the message-offset table.

Offset entry 0 identifies the end of the encrypted message-text region.
Entries 1 through `message_count` identify the corresponding game-visible
messages. A zero offset does not identify a valid message.

The encrypted region begins after all `message_count + 1` table entries and
ends at table entry 0. Its bytes are XORed with the repeating ASCII key:

```text
Avis Durgan
```

The key restarts after its final `n` byte. The offset table is not encrypted.
Messages in the resulting text region are zero-terminated byte strings.

## Operand notation

An action or condition opcode is followed by its operands. Unless an operation
states otherwise, each operand occupies one byte.

| Notation | Meaning |
| --- | --- |
| `imm` | The operand byte itself. |
| `vN` | Variable whose index is the operand byte. |
| `fN` | Flag whose index is the operand byte. |
| `item` | Inventory-item number. |
| `object` | Persistent-object number. |
| `resource` | Logic, picture, view, or sound resource number. |
| `message` | Message number in the current logic resource. |

An operation described as variable-selected reads the operand byte as a
variable index and then uses that variable's value as the effective argument.

## Main stream grammar

The main bytecode stream recognizes three structural opcodes before ordinary
action dispatch:

| Byte | Encoding | Behavior |
| ---: | --- | --- |
| `0x00` | `00` | End the current logic invocation and return normally to its caller, if any. |
| `0xfe` | `fe delta:s16le` | Add the signed displacement to the position immediately after the displacement. |
| `0xff` | `ff conditions ff delta:s16le` | Evaluate a conditional block as described below. |

Bytes `0x01..0xaf` are action opcodes in the 2.936 profile. Bytes
`0xb0..0xfb` are not valid actions in that profile. Bytes `0xfc` and `0xfd`
are condition-list markers and are invalid in the ordinary action stream.

The 3.002.149 profile extends the action range through `0xb5` as specified in
[Version Profiles](./version_profiles.md).

## Conditional blocks

A conditional block has this form:

```text
ff
condition-list
ff
false-delta:s16le
true-path bytecode
```

When the list succeeds, execution skips the two displacement bytes and begins
the true path. When the list fails, the signed displacement is added to the
position after those two bytes.

The condition list recognizes these markers:

| Byte | Meaning |
| ---: | --- |
| `0xfc` | Begin or end an OR group. |
| `0xfd` | Invert the result of the next predicate. |
| `0xff` | End the condition list. |

Outside an OR group, every predicate must be true. A false predicate fails the
list immediately.

The first `0xfc` begins an OR group. Predicates are evaluated until one is
true or a second `0xfc` is reached. A true term satisfies the group and skips
the remaining terms through the closing marker. Reaching the closing marker
without a true term fails the entire list. Evaluation then resumes with normal
AND behavior after a successful group.

`0xfd` affects one predicate only and is cleared after that predicate has been
evaluated.

## Condition opcodes

All comparisons of variables and coordinates below are unsigned and inclusive
where bounds are stated.

### Scalar and flag conditions

| Opcode | Operands | True when |
| ---: | --- | --- |
| `0x00` | none | Never. |
| `0x01` | variable, immediate | The variable equals the immediate byte. |
| `0x02` | variable A, variable B | A equals B. |
| `0x03` | variable, immediate | The variable is less than the immediate byte. |
| `0x04` | variable A, variable B | A is less than B. |
| `0x05` | variable, immediate | The variable is greater than the immediate byte. |
| `0x06` | variable A, variable B | A is greater than B. |
| `0x07` | flag | The selected flag is set. |
| `0x08` | variable | The flag whose number is stored in the variable is set. |

### Inventory and event conditions

| Opcode | Operands | True when |
| ---: | --- | --- |
| `0x09` | item | The item's location/state byte is `0xff`. |
| `0x0a` | item, variable | The item's location/state byte equals the variable value. |
| `0x0c` | status number | The selected mapped-event status byte is nonzero. |
| `0x0d` | none | A raw key event is available, or a previously captured raw key remains pending. |

Condition `0x0d` stores the low byte of a newly captured raw key in `v19`.
If `v19` is already nonzero, the condition succeeds without dequeuing another
event. While looking for a key, non-key events are discarded. A zero key value
does not satisfy the condition.

### Parsed-input condition

Condition `0x0e` is variable length:

```text
0e count:u8 word_id:u16le[count]
```

It can succeed only when parsed-input-ready state is set, parsed input is
nonempty, and the current parsed input has not already matched successfully.
It compares operand word identifiers with parsed words in order.

Operand word ID `0x0001` matches any one parsed word. Operand word ID `0x270f`
terminates the pattern successfully even when additional parsed words remain.
A successful match marks the current parsed input as consumed by a successful
word-sequence condition. A mismatch is false and does not set that marker.

A terminator-only pattern may also match parser state that stopped at an
unknown token, provided the parser recorded a nonzero token/error position.

Because this condition is variable length, condition scanners must skip one
count byte followed by `count * 2` word-ID bytes.

### String condition

Condition `0x0f` takes two string-slot numbers. It independently normalizes
both slots, then compares the resulting zero-terminated strings exactly.

Normalization removes space, tab, `.`, `,`, `;`, `:`, apostrophe, `!`, and
`-`, and converts ASCII `A..Z` to lowercase. This is direct string comparison;
it does not use dictionary parsing or parsed-word state.

### Object rectangle conditions

Conditions `0x0b`, `0x10`, `0x11`, and `0x12` each take:

```text
object, left, top, right, bottom
```

The vertical coordinate is always the object's baseline Y and must satisfy
`top <= baseline <= bottom`.

| Opcode | Horizontal point or span | True when |
| ---: | --- | --- |
| `0x0b` | Left X | `left <= x <= right`. |
| `0x10` | Full span from X through `x + width - 1` | Both ends lie within the horizontal bounds. |
| `0x11` | `x + floor(width / 2)` | The center lies within the horizontal bounds. |
| `0x12` | `x + width - 1` | The right edge lies within the horizontal bounds. |

Condition bytes `0x13..0xfb` are not valid predicates in the 2.936 profile,
except for structural markers `0xfc`, `0xfd`, and `0xff`.

## Action opcodes: scalar state

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x01` | variable | Increment, saturating at `255`. |
| `0x02` | variable | Decrement, saturating at `0`. |
| `0x03` | variable, immediate | Assign the immediate byte. |
| `0x04` | destination variable, source variable | Copy the source value. |
| `0x05` | variable, immediate | Add and retain the low 8 bits. |
| `0x06` | destination variable, source variable | Add the source and retain the low 8 bits. |
| `0x07` | variable, immediate | Subtract and retain the low 8 bits. |
| `0x08` | destination variable, source variable | Subtract the source and retain the low 8 bits. |
| `0x09` | index variable, source variable | Store the source value in the variable whose index is held by the index variable. |
| `0x0a` | destination variable, index variable | Read the variable whose index is held by the index variable into the destination. |
| `0x0b` | index variable, immediate | Store the immediate byte in the variable whose index is held by the index variable. |

## Action opcodes: flags

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x0c` | flag | Set the flag. |
| `0x0d` | flag | Clear the flag. |
| `0x0e` | flag | Toggle the flag. |
| `0x0f` | variable | Set the flag whose number is stored in the variable. |
| `0x10` | variable | Clear the flag whose number is stored in the variable. |
| `0x11` | variable | Toggle the flag whose number is stored in the variable. |

## Action opcodes: room and logic control

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x12` | destination logic/room | Switch immediately to the selected room state. |
| `0x13` | variable | Switch to the room whose number is stored in the variable. |
| `0x14` | logic resource | Load and retain the logic resource. |
| `0x15` | variable | Load and retain the logic resource whose number is stored in the variable. |
| `0x16` | logic resource | Invoke the selected logic. |
| `0x17` | variable | Invoke the logic whose number is stored in the variable. |

A logic invocation temporarily makes the callee the current logic, including
its message table. The caller activation is restored afterward. A callee that
was not already retained may be unloaded after the call. Ordinary opcode
`0x00` termination returns to the caller's next action. A callee action that
deliberately aborts logic flow with a zero continuation result propagates that
abort and ends the caller's current invocation as well.

Room switching performs these observable state changes:

1. Stop active sound and reset transient update, parser, object, and room
   resource state while retaining the global logic needed for the next cycle.
2. Copy old `v0` to `v1`, store the destination in `v0`, and preserve object
   0's selected view number in `v16`.
3. Load the destination logic resource.
4. Consume entry-boundary selector `v2`, repositioning object 0 when selected,
   then clear `v2`.
5. Set the new-room flag `f5` and refresh normal status/input display state.
6. Terminate the current logic invocation. The next top-level pass begins with
   logic 0; the destination logic is not executed implicitly by the room-switch
   action.

Entry-boundary selectors are:

| `v2` | Object 0 placement |
| ---: | --- |
| `1` | Baseline Y becomes `167`. |
| `2` | X becomes `0`. |
| `3` | Baseline Y becomes `37`. |
| `4` | X becomes `160 - object width`. |

The 3.002.149 profile applies its room-number aliases before these common room
effects.

## Action opcodes: picture and view resources

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x18` | variable | Load the picture whose number is stored in the variable. |
| `0x19` | variable | Clear/reset the logical picture surfaces, then decode the already loaded picture selected by the variable. The result is not required to become visible until a show action. |
| `0x1a` | none | Present the prepared logical visual surface, clear `f15`, and mark the picture as shown. |
| `0x1b` | variable | Discard the loaded picture selected by the variable. |
| `0x1c` | variable | Decode the already loaded picture selected by the variable over the existing logical surfaces without the prepare-time clear. Visibility still requires a show action. |
| `0x1d` | none | Temporarily display priority/control values, wait for an input event, then restore the normal visual display. |
| `0x1e` | view resource | Load the selected view resource. |
| `0x1f` | variable | Load the view whose number is stored in the variable. |
| `0x20` | view resource | Discard the selected loaded view resource. |

Loading, preparing, overlaying, and showing a picture are distinct operations.
An engine must not make an overlay visible merely because its logical surfaces
changed when no show operation followed.

## Catalog status

Actions `0x21..0xaf` remain to be promoted into this chapter. Their absence is
a specification gap, not an indication that they are invalid or optional.
