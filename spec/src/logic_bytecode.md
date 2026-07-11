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

Profiles 2.411 and 2.440 end at `0xa9`. The 2.917 profile ends at `0xad`.
Profile 3.002.086 extends the range through `0xb1`; profiles 3.002.102 and
3.002.149 extend it through `0xb5`, as specified in
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

## Action opcodes: object setup and view selection

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x21` | object | If not already update-eligible, enable update eligibility and automatic cel cycling, select the later-drawn partition, and clear direction, motion mode, and frame-cycling mode. Otherwise leave the object unchanged. |
| `0x22` | none | Clear active and update-eligible state from every persistent object. |
| `0x23` | object | Activate an object that has a selected cel, snapshot its current cel and position, and add it to update/draw processing. |
| `0x24` | object | Deactivate the object and remove it from update/draw processing. |
| `0x25` | object, X, Y | Set both current and previous position to the immediate coordinates. |
| `0x26` | object, X variable, Y variable | Set both current and previous position from variables. |
| `0x27` | object, X destination, Y destination | Store current X and baseline Y in the destination variables. |
| `0x28` | object, X-delta variable, Y-delta variable | Add signed 8-bit deltas to current position, clamp negative underflow to zero, mark the object newly positioned, and run placement. |
| `0x29` | object, view | Bind the loaded view, then select its default loop and cel. |
| `0x2a` | object, view variable | Bind the loaded view selected by a variable. |
| `0x2b` | object, loop | Select the loop and its default cel. |
| `0x2c` | object, loop variable | Select the loop named by a variable. |
| `0x2d` | object | Disable automatic direction-based loop selection. |
| `0x2e` | object | Enable automatic direction-based loop selection. |
| `0x2f` | object, cel | Select a cel, refresh its dimensions, clamp placement if required, and remove the one-cycle animation-start delay. |
| `0x30` | object, cel variable | Select the cel named by a variable with the same effects. |
| `0x31` | object, destination variable | Store the highest valid cel index in the selected loop. |
| `0x32` | object, destination variable | Store the selected cel index. |
| `0x33` | object, destination variable | Store the selected loop index. |
| `0x34` | object, destination variable | Store the selected view number. |
| `0x35` | object, destination variable | Store the number of loops in the selected view. |

Selecting a view, loop, or cel requires the referenced view to be loaded and
the selected index to be valid for that view. Cel selection updates width and
height before applying placement bounds.

## Action opcodes: priority and update participation

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x36` | object, priority | Select fixed priority and store the supplied value. |
| `0x37` | object, priority variable | Select fixed priority from a variable. |
| `0x38` | object | Disable fixed priority so priority is derived from baseline Y. |
| `0x39` | object, destination variable | Store the object's current priority value. |
| `0x3a` | object | Move an active object to the earlier-drawn update partition. |
| `0x3b` | object | Move an active object to the later-drawn update partition. |
| `0x3c` | object | Flush, rebuild, draw, and refresh all object update lists. The operand does not select a narrower refresh. |
| `0x3d` | object | Exempt the object from the horizon clamp. |
| `0x3e` | object | Re-enable the horizon clamp. |
| `0x3f` | baseline | Set the horizon. A nonexempt object at or above it is placed at least one row below it. |
| `0x40` | object | Enable the post-footprint-scan gate that rejects when final class-state flag 0 is clear. |
| `0x41` | object | Enable the post-footprint-scan gate that rejects when final class-state flag 0 is set. |
| `0x42` | object | Clear both class-2 and class-3 rejection options. |
| `0x43` | object | Exempt the object from object-object crossing/collision tests. |
| `0x44` | object | Re-enable object-object crossing/collision tests. |
| `0x45` | object A, object B, destination variable | Store center-X plus baseline-Y Manhattan distance, capped at `254`; store `255` if either object is inactive. |

Objects in the earlier partition are drawn before all objects in the later
partition. Within a partition, objects are ordered by their drawing key; equal
keys retain object-number order.

## Action opcodes: animation

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x46` | object | Disable automatic cel cycling. |
| `0x47` | object | Enable automatic cel cycling. |
| `0x48` | object | Cycle forward, wrapping from the last cel to cel 0. |
| `0x49` | object, completion flag | Begin forward cycling toward the last cel; clear the flag now, then set it and stop cycling on completion. |
| `0x4a` | object | Cycle backward, wrapping from cel 0 to the last cel. |
| `0x4b` | object, completion flag | Begin backward cycling toward cel 0; clear the flag now, then set it and stop cycling on completion. |
| `0x4c` | object, interval variable | Set both the cel-cycle reload interval and current countdown from a variable. |

Cycling is countdown-driven. When enabled, a nonzero countdown is decremented
once per eligible object-update cycle. Reaching zero advances according to the
selected mode and reloads the interval. Modes `0x49` and `0x4b` have a
one-callback startup delay before their first cel change. Their completion path
also clears object direction and returns the animation mode to forward wrap.

## Action opcodes: movement

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x4d` | object | Clear direction and autonomous motion. For object 0, clear `v6` and select object-to-`v6` direction coupling. |
| `0x4e` | object | Clear autonomous motion without clearing object direction. For object 0, clear `v6` and select `v6`-to-object direction coupling. |
| `0x4f` | object, step variable | Set movement step size from a variable. |
| `0x50` | object, cadence variable | Set the object's movement/update cadence countdown from a variable and restart its cadence phase. |
| `0x51` | object, target X, target Y, step override, completion flag | Begin movement toward an immediate target. |
| `0x52` | object, X variable, Y variable, step variable, completion flag | Begin movement toward a variable-selected target. |
| `0x53` | object, near threshold, completion flag | Move autonomously toward object 0 until within the threshold. |
| `0x54` | object | Begin autonomous random-direction motion. |
| `0x55` | object | Stop the autonomous motion mode without clearing current direction. |
| `0x56` | object, direction variable | Set direction from a variable. |
| `0x57` | object, destination variable | Store current direction. |
| `0x58` | object | Ignore configured movement-rectangle transitions and permit control value 1 in the footprint scan. |
| `0x59` | object | Enforce configured movement-rectangle transitions and reject control value 1 in the footprint scan. |
| `0x5a` | left, top, right, bottom | Enable the global movement rectangle. Inside membership uses strict comparisons against all four bounds. |
| `0x5b` | none | Disable the global movement rectangle. |

Targeted movement stores the original step size, clears the completion flag,
and uses the nonzero step override temporarily. A zero override preserves the
existing step size. Completion occurs when both signed target deltas are
strictly between negative step and positive step, or when placement reaches the
corresponding reachable screen boundary. Completion restores the original
step, stops the motion mode, and sets the flag.

Approach motion uses object centers horizontally and baselines vertically. It
sets its completion flag and stops when the target-direction calculation
reports that the objects are near enough. If movement is blocked, it may choose
a temporary random nonzero direction and retry after a delay.

Direction values are:

| Value | Direction |
| ---: | --- |
| `0` | Stationary. |
| `1` | Up. |
| `2` | Up-right. |
| `3` | Right. |
| `4` | Down-right. |
| `5` | Down. |
| `6` | Down-left. |
| `7` | Left. |
| `8` | Up-left. |

Object 0 and `v6` have a cycle-level direction coupling selected by actions
`0x83` and `0x84`. In object-to-variable mode, the pre-logic stage copies the
object direction to `v6`. In variable-to-object mode, it copies `v6` to the
object. After logic, object 0 direction is restored from `v6` before movement.

## Action opcodes: inventory locations

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x5c` | item | Set the item's location to `0xff` (carried). |
| `0x5d` | item variable | Set the variable-selected item's location to `0xff`. |
| `0x5e` | item | Set the item's location to `0`. |
| `0x5f` | item, location variable | Set the immediate item's location from a variable. |
| `0x60` | item variable, location variable | Set a variable-selected item's location from a variable. |
| `0x61` | item variable, destination variable | Store a variable-selected item's location. |

## Action opcodes: sound

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x62` | sound resource | Load the sound. |
| `0x63` | sound resource, completion flag | Stop prior playback, clear the supplied flag, and start the loaded sound. |
| `0x64` | none | Stop active sound and set its remembered completion flag. |

The complete resource and scheduling contract is in
[Sound Resources and Playback](./sound.md).

## Action opcodes: text and input

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x65` | message | Display the current-logic message modally and return after acknowledgement. |
| `0x66` | message variable | Display the variable-selected message. |
| `0x67` | row, column, message | Expand substitutions in the message and display it at the configured text position. |
| `0x68` | row variable, column variable, message variable | Variable-selected form of `0x67`. |
| `0x69` | top row, bottom row, attribute | Clear full-width text rows inclusively with the selected text attribute. |
| `0x6a` | none | Enter the alternate full-screen text-attribute mode and clear/fill its visible surface. Object graphics updates are suppressed while this mode is active. |
| `0x6b` | none | Leave alternate text mode, restore normal graphics updates, and redraw status/input areas. |
| `0x6c` | message | Use the first byte of the message as the input prompt marker; an empty message suppresses the marker. |
| `0x6d` | foreground, background | Set the text color/attribute pair used by text windows and alternate text mode. |
| `0x6e` | count | Shake the visible display for the requested count, with pacing between offsets. |
| `0x6f` | display base row, input row, status row | Configure text/input/status row placement. |
| `0x70` | none | Enable and redraw the status line at its configured row. |
| `0x71` | none | Disable and clear the status line at its configured row. |
| `0x72` | string slot, message | Copy the message into the 40-byte string slot. |
| `0x73` | string slot, prompt message, row, column, maximum length | Clear the slot, display the prompt, edit input at the optional position, and store the accepted zero-terminated text. Accepted storage is limited to `min(maximum length + 1, 40)` bytes. |
| `0x74` | string slot, parsed-word index | Copy the selected normalized parsed-word text into the string slot. |
| `0x75` | string slot | Clear prior parser-match state and parse the slot into dictionary word identifiers. Slot numbers outside `0..11` produce no parse. |
| `0x76` | prompt message, destination variable | Prompt for up to four decimal characters, parse the accepted number, and store its low 8 bits. |
| `0x77` | none | Disable and clear the input line. |
| `0x78` | none | Enable and redraw the input line. |
| `0x79` | key low byte, key high byte, status number | Add a key mapping for the little-endian key word. A matching raw key becomes a mapped event carrying the status number. |

Profiles 2.411, 2.440, 2.917, 2.936, 3.002.086, and 3.002.102 accept at most
39 key-map entries. Mapped events set the status observed by condition `0x0c`.
The 3.002.149 profile accepts 49 entries.

## Action opcodes: transient views and inventory UI

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x7a` | view, loop, cel, X, baseline Y, priority, control/margin | Draw the selected loaded cel into persistent picture state at the supplied position and record enough state for restore replay. |
| `0x7b` | seven variables | Variable-selected form of `0x7a`. |
| `0x7c` | none | Display carried inventory items. In interactive mode, store the selected item in `v25`; store `0xff` on cancel. |

Inventory selection includes only items whose location is `0xff`. Its display
uses a two-column list when needed. When the profile's inventory-interaction
flag disables selection, the list is acknowledgement-only and does not produce
a chosen-item result.

## Action opcodes: persistence and session control

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x7d` | none | Enter the modal save selector. Cancel or a handled write failure returns to following bytecode; success writes the current game state and then returns. |
| `0x7e` | none | Enter the modal restore selector. Cancel or open failure returns to following bytecode. Successful restore replaces runtime state, rebuilds resources, and aborts the current continuation so execution resumes from restored state. |
| `0x7f` | none | No operation. |
| `0x80` | none | Request in-engine restart. Confirmation may be skipped by the restart-without-prompt flag. Cancel continues; acceptance resets game state, sets the restarted flag, and aborts current logic flow. |
| `0x81` | view resource | Temporarily load if needed, preview the view and its associated text, wait for acknowledgement, then discard it if this action loaded it. Do not add the temporary work to restore replay. |
| `0x82` | low, high, destination variable | Store a pseudorandom value in the inclusive range `low..high`. |
| `0x83` | none | Select object-0-to-`v6` direction coupling. |
| `0x84` | none | Select `v6`-to-object-0 direction coupling and stop object 0 autonomous motion. |
| `0x85` | object variable | Display object number, X, baseline Y, width, height, priority, and step size as a modal diagnostic. |
| `0x86` | immediate-exit selector | If the operand is `1`, terminate immediately. Otherwise request confirmation and terminate only when accepted. |
| `0x87` | none | Display heap/resource diagnostic values modally. These values are diagnostic and do not define a required internal allocator layout. |
| `0x88` | none | Stop sound, display the fixed pause message, wait for acknowledgement, and resume. |
| `0x89` | none | Redraw the enabled input line from the accepted input buffer. |
| `0x8a` | none | Erase all currently visible input-line characters. |
| `0x8b` | none | Run the interactive joystick-centering and range-calibration sequence when a joystick is available. |
| `0x8c` | none | Toggle the supported alternate display mode, rebuild display state from recorded resource events, and preserve only events still inside the active replay count. This path is outside the current full-EGA target. |
| `0x8d` | none | Display the interpreter name and version string modally. |
| `0x8e` | replay-pair capacity | Set resource replay capacity, allocate/reset its pair sequence, and refresh object update lists. |
| `0x8f` | message | Copy up to seven message bytes into the game signature and terminate on mismatch with the profile's expected signature. The 2.936 profile expects `SQ2`; 3.002.149 accepts `GR`. |
| `0x90` | message | Append current room, current input line, and the expanded message to `LOGFILE`. Failure to open the log returns without terminating the game. |
| `0x91` | none | Save the current following-bytecode position as this logic's future resume position. |
| `0x92` | none | Reset this logic's future resume position to its bytecode entry. Current execution continues normally. |

In profile 2.411, action `0x80` always displays the restart confirmation even
when `f16` is set. Other promoted profiles accept restart immediately while
`f16` is set.

Profiles 2.411 and 2.440 display three heap/resource diagnostic lines for
action `0x87`: heap size; current and maximum use; and maximum script use.
Later profiles also display an `rm.0, etc.` diagnostic line. These values do
not define a required allocation strategy.
| `0x93` | object, X, Y | Set current position, mark it newly positioned, and run placement without replacing the previous-position snapshot directly. |
| `0x94` | object, X variable, Y variable | Variable-selected form of `0x93`. |

The save-file envelope, replay sequence, and restore/restart transitions are in
[Rooms, Replay, and Persistence](./session_and_persistence.md).

## Action opcodes: trace and configured text

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x95` | normally none | When action tracing is inactive and `f10` is set, enable and draw the trace window. If tracing is already active, consume one additional byte after the opcode and otherwise return. |
| `0x96` | trace logic, row offset, height | Configure trace formatting and window placement; clamp height to at least 2. |
| `0x97` | message, row, column, width | Temporarily configure the modal message window, display the immediate message, then reset the temporary configuration. Row and column override the default centered placement; width controls message formatting and defaults to 30 when zero. |
| `0x98` | message variable, row, column, width | Variable-selected message form of `0x97`. |
| `0x99` | view variable | Discard the loaded variable-selected view. |
| `0x9a` | top row, left column, bottom row, right column, attribute | Clear the inclusive text-cell rectangle with the selected attribute. Text cells are four logical pixels wide and eight logical pixels high in the EGA target. |
| `0x9b` | two ignored bytes | Consume both bytes and otherwise do nothing. |

The temporary configuration exists only for that display action. After the
message window has been opened, the row, column, and width overrides are reset
to the ordinary default/centered behavior.

Profiles 2.411 and 2.440 use the same four-byte encoding listed above. The
message selector is followed by row, column, and width.

## Action opcodes: menus

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x9c` | heading message | Append a top-level menu heading using the message text. Ignored after finalization. |
| `0x9d` | item message, item ID | Append an enabled item to the current heading. Ignored after finalization. |
| `0x9e` | none | Finalize menu construction and establish the initial heading/item selection. |
| `0x9f` | item ID | Enable every menu item with the matching ID. |
| `0xa0` | item ID | Disable every menu item with the matching ID. |
| `0xa1` | none | If `f14` is set, request modal menu interaction on the input cycle. |

Selecting an enabled item enqueues a mapped status event carrying its item ID.
Escape exits without selection. Disabled items cannot produce selection events.
Heading and item navigation wrap through enabled entries.

## Action opcodes: remaining shared operations

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0xa2` | view variable | Variable-selected form of `0x81`. |
| `0xa3` | none | Enable the fixed input-width override, using a 36-character starting cap in profiles that support it. |
| `0xa4` | none | Disable the fixed input-width override and return to width derived from normal input state. |
| `0xa5` | variable, immediate | Multiply and retain the low 8 bits. |
| `0xa6` | destination variable, source variable | Multiply and retain the low 8 bits. |
| `0xa7` | variable, immediate | Store the unsigned quotient. Division by zero is outside valid bytecode. |
| `0xa8` | destination variable, divisor variable | Store the unsigned quotient. Division by zero is outside valid bytecode. |
| `0xa9` | none | Close/restore an active text window if present and clear the fixed input-width override even when no window is active. |
| `0xaa` | string slot | Copy up to 31 bytes of the current save-selector description/path buffer into the slot. |
| `0xab` | none | Save the current resource replay-pair count as a rollback point. |
| `0xac` | none | Restore the saved replay-pair count and place the next write after the restored final pair. |
| `0xad` | none | Increment the key-release event gate modulo 256 in the v2 and 3.002.086 profiles. A nonzero gate permits selected tracked-key releases to enqueue a movement-type zero event. |
| `0xae` | horizon row | Rebuild the baseline-to-priority table: rows below the argument map to 4; rows from it upward rise from 5 toward 15 across the remaining 168-row picture height. |
| `0xaf` | none at runtime | Do nothing and consume no following byte during execution, despite this opcode's one-byte scanner length metadata. |

## Version 3 extension actions

Profile 3.002.086 adds:

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0xb0` | one ignored byte | Consume the byte and otherwise do nothing. |
| `0xb1` | gate value | Set the menu-interaction gate; zero blocks modal entry and nonzero permits it. |

Profiles 3.002.102 and 3.002.149 extend this range through `0xb5` with these
contracts:

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0xb0` | none | No operation. |
| `0xb1` | gate value | Set the menu-interaction gate; zero blocks modal entry and nonzero permits it. |
| `0xb2` | none | No operation. |
| `0xb3` | four ignored bytes | Consume four bytes and otherwise do nothing. |
| `0xb4` | two variable operands | Consume two variable-index operands and otherwise do nothing. |
| `0xb5` | none | Clear the key-release event gate. |

In the two later profiles shared action `0xad` sets the key-release gate to one rather
than incrementing it. In 3.002.149, shared actions `0xa3` and `0xa4` do
nothing; 3.002.102 retains their v2 effects. Other shared differences are
listed in [Version Profiles](./version_profiles.md).

## Catalog completeness

Every action opcode accepted by the 2.936 profile (`0x00..0xaf`) now has an
operand and behavioral entry in this chapter. The 2.917 range is its
`0x00..0xad` subset. The version-3 extension ranges `0xb0..0xb1` and
`0xb0..0xb5` are also listed. Subsystem chapters may refine these summaries;
when they do, the more detailed subsystem contract controls.
