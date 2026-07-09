# Runtime model

This page lifts the byte-level notes into implementation-facing data types and
operation families. It is still a clean-room model: every name here is derived
from local disassembly, local SQ2 resources, and the evidence recorded in the
other pages.

The names are intentionally descriptive rather than final API names. A new
implementation can use different public names, but should preserve the observed
storage widths, lifetimes, and side effects unless later evidence proves a
better model.

## Global scalar state

The interpreter uses a byte-variable array rooted at `DS:0x0009`. Variable
opcodes operate on unsigned bytes:

| Operation family | Observed handlers | Implementation contract |
| --- | --- | --- |
| Increment/decrement | `0x01` (`inc_var`), `0x02` (`dec_var`) | Saturating byte update. Increment stops at `0xff`; decrement stops at `0x00`. |
| Assignment | `0x03` (`assignn`), `0x04` (`assignv`) | Store an immediate byte or another variable byte. |
| Arithmetic | `0x05` (`addn`) through `0x08` (`subv`), `0xa5` (`muln`) through `0xa8` (`divv`) | Byte arithmetic. Multiply stores the low byte of the product; divide stores the 8-bit quotient. |
| Indirection | `0x09` (`indirect_assignv`), `0x0a` (`assign_indirectv`), `0x0b` (`indirect_assignn`) | Treat a variable's byte value as another variable index. |

The flag store is a packed bitfield rooted at `DS:0x0109`. The flag helper maps
a flag number to:

```text
byte_address = 0x0109 + flag_number / 8
mask = 0x80 >> (flag_number & 7)
```

This means flag 0 is the high bit of byte `0x0109`, flag 1 is the next bit, and
so on. Initialization helper `0x752a` clears `0x20` bytes, so the observed flag
storage spans 256 bits.

## Strings and parsed input

Fixed string slots begin at `DS:0x020d`. Each slot is `0x28` bytes, and the
parser-facing action `0x75` (`parse_string_slot`) accepts only slot indexes
`0..11`, giving twelve script-visible slots in the observed interpreter.

Observed string operations:

| Operation | Opcode | Contract |
| --- | ---: | --- |
| Copy current-logic message to slot | `0x72` (`set_string_slot_from_message`) | Resolve a message through the current logic record and copy at most `0x28` bytes into `0x020d + slot * 0x28`. |
| Prompt/edit a slot | `0x73` (`prompt_string_to_slot`) | Display a prompt message, accept edited input, and store a null-terminated result in the chosen slot. The requested max length is clamped to `0x28`. |
| Copy from pointer table to slot | `0x74` (`set_string_slot_from_table`) | Read a word pointer from `DS:0x0c8f + index * 2` and copy at most `0x28` bytes into the chosen slot. Static SQ2 data has zero-filled entries in the sampled table. |
| Parse a slot | `0x75` (`parse_string_slot`) | Normalize the slot text, look words up in `WORDS.TOK`, fill parsed-word buffers rooted around `0x0c7b`, and set/clear parser flags. |
| Compare two slots | condition `0x0f` (`string_slots_equal_normalized`) | Compare two slots after dropping bytes from `DS:0x094b` and lowercasing ASCII `A..Z`; this does not use `WORDS.TOK`. |

Parser normalization for action `0x75` uses two SQ2 tables. Bytes in
`data.words.parser_separators_0c67` (` ,.?!();:[]{}`) become word separators
and separator runs collapse to one space. Bytes in
`data.words.parser_ignored_0c75` (apostrophe, backtick, hyphen, and double
quote) are dropped without creating a separator. The normalized buffer is
trimmed of a trailing space and then scanned one token at a time.

Dictionary lookup is case-insensitive for ASCII letters. Recognized dictionary
entries whose word ID is zero are ignored and do not consume one of the ten
parsed output slots; local examples include `the`, `a`, `i`, `to`, and `with`.
Recognized nonzero IDs are appended to the parsed-ID table. If lookup finds an
unknown token, the parser stores the pointer for the next output slot, records
`len(parsed_ids) + 1` in byte variable `[0x0012]` and
`data.words.parsed_count_or_error_position`, sets parser flag 2, and stops.
So an unknown word after ignored zero-ID words still reports output slot 1.
If parsing reaches the end with at least one nonzero word ID, the same count
word stores the number of parsed IDs and flag 2 is set. If only zero-ID words
were present, flag 2 remains clear.

Condition `0x0e` (`input_word_sequence`) consumes the parsed-word buffer rather
than the raw string slot. Its bytecode operand is a count followed by that many
little-endian word IDs. Word ID `0x270f` terminates a successful match, and word
ID `0x0001` behaves as a wildcard for one parsed word. QEMU batch
`parser_edges_001` validates exact two-word matching for `look get`, wildcard
matching for `look *`, and `0x270f` accepting a `look` prefix while an
additional parsed word remains. Source helper `0x095c` also allows a
terminator-only pattern to match an unknown-token parse state when flag 2 is set
and `data.words.parsed_count_or_error_position` is nonzero; QEMU batch
`parser_unknown_terminator_001` confirms this behavior.

Condition `0x0f` (`string_slots_equal_normalized`) is the direct string-slot
comparison path. It treats space, tab, `.`, `,`, `;`, `:`, `'`, `!`, and `-` as
ignored bytes in the local SQ2 `AGIDATA.OVL`, lowercases ASCII uppercase
letters, and then requires exact byte equality through both strings' zero
terminators.

For a new implementation, the clean boundary is:

```text
StringSlots: fixed-size editable strings
WordParser: converts one slot into word IDs and parser flags
SaidLikeCondition: matches bytecode word sequences against WordParser output
StringCompareCondition: normalized direct slot equality, independent of WordParser
```

This separation matches the observed data flow and now has dynamic coverage for
the basic message-to-string parse path, exact parsed-word matching, wildcard
matching, terminator-prefix matching including the unknown-token edge, and
direct normalized string comparison.

## Logic resources and execution state

Loaded logic resources are represented by 10-byte cache records linked from
`[0x0977]`:

```text
+0x00: next record
+0x02: logic number
+0x03: message count
+0x04: bytecode base pointer
+0x06: current instruction pointer
+0x08: message offset table base
```

The interpreter loop reads from `record+0x06`. Action `0x91`
(`save_logic_resume_ip`) stores the current bytecode pointer there, and action
`0x92` (`restore_logic_entry_ip`) restores it from the bytecode base at
`record+0x04`.

Implementation-facing lifetimes:

| Load path | Observed actions | Lifetime |
| --- | --- | --- |
| Cached load | `0x14` (`load_logic`), `0x15` (`load_logic_var`) | The record remains linked from `[0x0977]`. |
| Nested call | `0x16` (`call_logic`), `0x17` (`call_logic_var`) | If the target was not already cached, it is loaded temporarily, executed, unlinked, and freed by rewinding the heap. |
| Room/state switch | `0x12` (`switch_room_like`), `0x13` (`switch_room_like_var`) | Resets object/resource state, changes byte variable 0, loads the destination logic, and reinitializes display/update state. |

The important higher-level type is not just "logic bytecode"; it is a logic
activation record containing bytecode, messages, and resumable instruction
state.

## Resource handles

All four resource types are addressed through directory entries and `VOL.*`
records, then cached as small linked records. After the generic volume reader,
payload pointers refer to the type-specific payload, not the five-byte `VOL.*`
header.

| Resource type | Main loader | Cache identity | Main consumer |
| --- | --- | --- | --- |
| Logic | `0x119a` | logic number | Bytecode interpreter and message resolver. |
| View-like | `0x39f7` | view number | Object records and transient preview objects. |
| Picture-like | `0x4a3b` | picture number | Picture command decoder, via global `[0x1377]`. |
| Sound-like | `0x5126` | sound number | Four derived payload pointers used by sound start/stop code. |

A replacement implementation should separate "resource id", "loaded payload",
and "typed decoded view" concepts. The original interpreter often decodes lazily
by storing raw payload pointers in object records, but the object contracts
depend on decoded fields such as group counts, frame pointers, width, and
height.

Sound resources have a small typed structure on top of the raw payload. The
loader reads the first four little-endian words and stores four payload-relative
channel stream pointers in the sound cache record. The playback start helper
copies those pointers into the runtime channel pointer table and initializes
per-channel countdown, active, and attenuation words. The tick routine then
consumes each channel as a sequence of records:

| Field | Size | Meaning |
| --- | --- | --- |
| Duration | 16-bit little-endian | Countdown value for the next sound event; `0xffff` terminates that channel. |
| Tone/control word | 16-bit little-endian | Driver-facing tone/control value. The PC-speaker path converts this word to the PIT divisor documented below; other hardware selectors pass encoded bytes to port `0xc0`. |
| Control byte | 8-bit | Low nibble is copied as the observed attenuation/control value; `0x0f` is used for silent/terminated channels. |

The local SQ2 corpus scan found 49 present sound resources. All present
resources have four sorted, in-bounds channel offsets, and the first offset is
8, immediately after the four-word header. The current clean-room model covers
the resource container and event stream shape, not full audio synthesis.

Source inspection also gives an implementation-facing playback schedule. The
timer interrupt hook calls the sound tick only while `data.sound.active_state`
is nonzero. At the start of each tick, flag 9 is tested; if flag 9 is clear,
the driver stops immediately and sets the configured completion flag. Driver
start initializes every channel countdown to 1, so the first event or channel
terminator is read on the first active tick. After a non-terminating event is
read, its duration word becomes the next 16-bit countdown. A duration of zero
would wrap and delay the next channel record read for 65,536 ticks; the local
SQ2 corpus has no zero-duration sound events.

The active channel set depends on the hardware selector. When selector
`[0x112e]` is `0` or `8`, the tick loop advances only channel 0. Other observed
selector values advance all four channels. Natural completion occurs when the
last active channel reaches its `0xffff` terminator; the stop path clears active
state and sets the flag stored by `start_sound_with_flag`.

Hardware output is source-backed only to the driver interface level. For
selector `0`/`8`, the driver uses the PC-speaker-style PIT path: an event with
attenuation nibble `0x0f` clears port `0x61` bits `0` and `1`; otherwise the
tone word is converted to a PIT divisor as
`12 * (((tone_word & 0x3f) << 4) + ((tone_word >> 8) & 0x0f))`, written low
byte then high byte to port `0x42` after mode byte `0xb6` is written to port
`0x43`, and port `0x61` bits `0` and `1` are set. Stop on this path emits the
same silence behavior.

Other observed selectors write driver bytes to port `0xc0`. Tone output sends
the high tone byte and, unless that high byte has top bits `0xe0`, also sends
the low tone byte. Stop on this path writes the four silence bytes `0x9f`,
`0xbf`, `0xdf`, and `0xff`. Selector `2` calls a small source helper that
adjusts an internal control byte whose high bits match `0x90` and whose low
nibble is below `8`; the observed port-facing tone bytes remain the high/low
tone bytes described above.

Attenuation output is also source-modeled. Each channel has a base attenuation
byte, an envelope index, and a previous envelope value. If the base attenuation
is `0x0f`, the helper writes the channel mask plus `0x0f` and skips envelope
processing. Otherwise, when the envelope index is not `0xffff`, the helper
reads a byte from the default table at `0x17b8`. Byte `0x80` disables the
envelope and copies the previous envelope value into the base attenuation.
Other table bytes are deltas from the base attenuation, not cumulative deltas:
negative underflow clamps to `0`, positive overflow clamps to `0x0f`, and the
result becomes the previous envelope value. A runtime adjustment byte at
`[0x0020]` is then added and clamped to `0x0f`; selector `2` also raises
non-silent values below `8` by `2`. The final port byte is the adjusted low
nibble ORed with the channel mask `0x90`, `0xb0`, `0xd0`, or `0xf0`.

These port writes are an implementation detail for hardware-facing
compatibility. The portable game-state contract remains the event schedule,
active-channel set, attenuation state, tone/attenuation port-output boundary,
and completion-flag behavior above. This is not a claim about faithfully
synthesizing the analog waveform from the original hardware.

## Object records

Persistent objects live in a table of 43-byte records from `[0x096b]` to
`[0x096d]`. The record is the central runtime type for visible, movable
entities:

```text
ObjectRecord {
    current_position: x at +0x03, y/baseline at +0x05
    selected_view: resource byte +0x07, payload pointer +0x08
    selected_group: byte +0x0a, group pointer +0x0c
    selected_frame: byte +0x0e, frame pointer +0x10
    saved_frame_and_position: +0x12, +0x16, +0x18
    dimensions: width +0x1a, height +0x1c
    motion: step +0x1e, direction +0x21, mode +0x22, mode2 +0x23
    priority_control: byte +0x24
    flags: word +0x25
    motion_parameters: mode-specific bytes +0x27..+0x2a
}
```

The implementation-facing object operations are:

| Operation family | Representative actions/helpers | Contract |
| --- | --- | --- |
| Bind view resource | `0x29` (`set_object_resource`), `0x2a` (`set_object_resource_var`), helper `0x3ae7` | Store a loaded view payload on the object and select a default or requested group/frame. |
| Select group/frame | `0x2b` (`set_object_subresource`), `0x2c` (`set_object_subresource_var`), `0x2f` (`set_object_derived_resource_2`), `0x30` (`set_object_derived_resource_2_var`) | Validate indexes, update selected pointers and dimensions, clamp coordinates when necessary. |
| Position | `0x25` (`set_object_pos`), `0x26` (`set_object_pos_var`), `0x28` (`add_object_pos_from_vars`), `0x93` (`set_object_pos_dirty`), `0x94` (`set_object_pos_dirty_var`) | Write current and/or saved coordinates; dirty-position forms set object flag `0x0400` and call placement. |
| Activate/deactivate | `0x23` (`activate_object`), `0x24` (`deactivate_object`) | Add/remove the object from graphics/update participation and refresh the update lists. |
| Motion control | `0x48..0x55`, `0x51` (`move_object_to`), `0x52` (`move_object_to_var`), `0x53` (`approach_first_object_until_near`), `0x54` (`start_random_motion`) | Configure object direction/motion modes, completion flags, and target/step parameters. `0x51/0x52` target an object at X/Y and set a completion flag when it arrives; `0x53` approaches the first object entry until within a threshold and sets a completion flag; `0x54` starts random autonomous direction changes. |
| Object0/global direction mirror | `0x83` (`clear_global_0139`), `0x84` (`set_global_0139_and_clear_object0_field_22`), `code.engine.main_cycle` | At the pre-logic mirror point, `[0x0139] == 0` copies object 0 direction byte `+0x21` to global byte `[0x000f]`; nonzero copies `[0x000f]` back to object 0. After logic returns, object 0 `+0x21` is restored from `[0x000f]`, so script writes to object 0 direction occur after the branch point and do not seed the next cycle by themselves. |
| Collision/control flags | `0x3d` (`set_object_bit_0008`), `0x43` (`set_object_bit_0200`), `0x58` (`set_object_bit_0002`), and companions | Toggle bits that affect horizon clamp, collision tests, and control-buffer acceptance. |
| Diagnostics | `0x85` (`display_object_diagnostics_var`) | Display object number, X/Y, width/height, priority/control, and step size using the interpreter's built-in diagnostic template. |

The separate 3-byte table rooted at `[0x0971]` stores object/item metadata used
by inventory-like logic. The third byte is a location/state marker. Actions
`0x5c..0x61` set, clear, and read that marker, and action `0x7c`
(`show_inventory_selection`) treats marker value `0xff` as "carried": it builds
a two-column list from those entries, displays their table-relative name
pointers, and stores the selected item index in byte variable `[0x22]` or
`0xff` on cancel.

Two temporary object forms reuse the same structure:

- Actions `0x7a` (`setup_transient_object`) and `0x7b`
  (`setup_transient_object_var`) use a fixed object-like record at `0x0eb4`.
- Actions `0x81` (`display_view_resource_text_like`) and `0xa2`
  (`display_view_resource_text_like_var`) use a stack-local 43-byte record.

That reuse is a strong signal that object rendering should be implemented
against a common object/frame interface rather than only against persistent
table entries.

## Graphics and update operations

The picture decoder, object renderer, and display overlay operate on a logical
graphics/control buffer segment stored at `[0x136f]`. The observed coordinate
space is `0xa0` columns by `0xa8` rows.

Implementation-facing phases:

1. Picture preparation decodes picture command bytes into the logical buffer.
2. View binding selects frame data and dimensions for object records.
3. Placement validates object coordinates against screen bounds, the
   horizon-like line `[0x012d]`, object-object crossing, and control-buffer
   classes.
4. Update-list builders partition active objects between roots `0x1703` and
   `0x16ff`. Each root draws objects in ascending key order, where the key is
   baseline Y unless fixed-priority bit `0x0004` routes object byte `+0x24`
   through the reverse-priority helper. Equal keys remain in object-table order,
   so later object-table entries draw later. Root `0x1703` is drawn completely
   before root `0x16ff`.
5. Render nodes save backing rectangles, draw frame data, and later restore old
   rectangles during list flushes.
6. Display-overlay entries copy full-screen or rectangular regions from the
   logical buffer to display memory.

This implies a useful replacement architecture:

```text
ResourceStore -> LogicVM -> ObjectTable -> PictureBuffer
                          -> RenderLists -> DisplayBackend
```

The original interpreter interleaves these concerns through global helpers, but
the observed side effects line up with those separable components.

## Implementation state machines

The source names and addresses are useful evidence, but a clean-room
implementation should model the main runtime objects as small state machines.
These states are implementation-facing summaries of the observed transitions;
they are not claims about the exact original memory layout.

Resource lifecycle:

| State | Entered by | Exited by | Observable contract |
| --- | --- | --- | --- |
| Uncached | Room reset, explicit discard, or startup | Load action/cache miss | No payload pointer should be usable by object, picture, logic, or sound consumers. |
| Cached raw payload | `load_logic`, `load_view`, `load_picture_var`, `load_sound`, and variable forms | Discard action or room reset | Directory and volume lookup has succeeded; cache identity is the resource number. Load-on-miss records a resource-event pair when recording is enabled. |
| Selected for use | Logic call, view binding, picture prepare/overlay, sound start | Return from operation or later selection | A cached payload is attached to a consumer: logic activation, object record, picture decoder global, or sound state. |
| Mutated/displayed | Picture decode/show, transient object draw, active object refresh, sound start/stop | Next refresh, discard, room switch, replay | User-visible or saved-state side effects occur. Picture/view/transient operations append replay pairs unless flag 7 or the recording gate suppresses recording. |
| Replay/restored | Restore or display-mode replay | Replay finish at `code.restore.finish_replay_and_reenable_recording` | Event recording is disabled while saved pairs are consumed, then re-enabled before normal execution continues. |

Heap and allocation lifecycle:

| State | Entered by | Exited by | Observable contract |
| --- | --- | --- | --- |
| Startup memory allocation | `code.startup.allocate_runtime_memory` | Successful DOS memory allocation, or fatal startup error | Startup shrinks/probes the resident DOS block, requests a runtime memory block with DOS `AH=48h`, converts the returned segment into a DS-relative byte offset, writes that offset to both `[0x0a55]` and `[0x0a57]`, and writes `[0x0a5b] = [0x0a57] + requested_runtime_paragraphs * 16`. Failure displays the startup memory error and terminates through DOS. |
| Bump heap active | Startup after heap base/limit initialization | Interpreter shutdown or fatal allocation failure | Current heap pointer `[0x0a55]` advances monotonically on ordinary allocations. Heap base `[0x0a57]`, room/reset mark `[0x0a59]`, limit `[0x0a5b]`, temporary mark `[0x0a5d]`, and high-water pointer `[0x0a5f]` define the allocator state. |
| Allocation | Helper `0x13d6(size)` | Success or fatal error path | If `size <= [0x0a5b] - [0x0a55]`, the helper returns the old heap top, advances `[0x0a55]`, refreshes byte variable 8 at `[0x0011]`, and updates high-water `[0x0a5f]`. If not, it displays the out-of-memory message and calls restart/exit helper `0x02ae`; no recoverable allocation failure return was observed. |
| Temporary mark | `0x144b` | `0x145a` | The current heap top is saved in `[0x0a5d]`; restore rewinds `[0x0a55]` only if that mark is nonzero, then clears it. |
| Room/reset mark | Startup `0x1476`, after initial setup and logic 0 load | `0x1485` | The mark at `[0x0a59]` is the broad cleanup target for room switch, restart, and restore. Reset helper `0x1485` frees update-list nodes, clears the temporary mark, rewinds `[0x0a55]` to `[0x0a59]`, and refreshes `[0x0011]`. |
| Direct rewind | Temporary `call_logic` cleanup or source helper `0x143c(ptr)` | Caller-controlled | `0x143c` stores `ptr` directly in `[0x0a55]`. It does not refresh `[0x0011]` by itself, so callers that need a current free-memory byte use `0x14a0`. |
| Diagnostics | `0x87` | Modal message close | Heap-status text reports heap size `[0x0a5b] - [0x0a57]`, current use `[0x0a55] - [0x0a57]`, maximum use `[0x0a5f] - [0x0a57]`, room/reset mark `[0x0a59] - [0x0a57]`, and resource-event high-water `[0x170f]`. |

Action `0x8e` configures the replay log capacity. It writes
`data.event.pair_capacity`, flushes update-list state, resets/allocates the
pair buffer through `code.event.reset_pair_buffer`, clears the active pair
count, and rebuilds update-list state.

Save/restore data model:

| Element | Producers | Consumers | Contract |
| --- | --- | --- | --- |
| Save description buffer | Save/restore selector helper | `0x7d`, `0x7e`, `0xaa` | Runtime buffer `[0x0e72]` holds the selected or entered save description/path text. The selector also edits path buffer `0x1962`, fills header/description buffer `0x1c6c` for newly described saves, and formats the selected filename into `0x1c8c`. `0xaa` copies up to `0x1f` bytes from `[0x0e72]` into a fixed 40-byte logic string slot. |
| Save selector lifecycle | `0x7d`, `0x7e` | DOS file I/O handlers | `code.save.select_slot_or_path` saves text/input state, erases the prompt marker, stops active sound, prompts for a path if needed, scans up to 12 numbered save files, displays descriptions, handles Enter/Escape/up/down selection, then restores text state and returns zero for cancel or a nonzero selection for file I/O. |
| Save filename/signature prefix | `0x8f` | Save/restore selector and slot reader | The string at `DS:0x0002` is set by `verify_game_signature`, used as the third string in the `%s%s%ssg.%d` save filename format, and compared against the first bytes of the first saved state block when scanning restore candidates. For SQ2, the normal initialized prefix is `SQ2`, producing `SQ2SG.N`. |
| Save file state blocks | `0x7d` | `0x7e` | Files store a 31-byte description/header followed by five little-endian length-prefixed blocks. The fixed local SQ2 block lengths are `1505`, `903`, `328`, and `200` for data rooted at `0x0002`, the object table, inventory/object metadata, and resource-event pairs; the fifth block rooted at `0x0985` has the variable size returned by `0x1364`. |
| Replay pair block | `0x8e`, resource load/display/discard actions, `0xab`/`0xac` | Restore/display-mode replay | The saved pair block length is `data.event.pair_capacity * 2`; active count controls how much of the buffer replay consumes. |

Save/restore selector state machine:

| State | Entry work | User-visible transition | Output contract |
| --- | --- | --- | --- |
| Selector entry | `code.save.select_slot_or_path` records whether the normal prompt marker is visible, erases that marker, saves text/window attribute state, stops active sound, and switches to the selector text attributes. | No direct choice yet; control moves to path preparation. | On every exit path, the helper restores the saved text state and redraws the prompt marker only if it was visible on entry. |
| Path preparation/edit | If `data.save.path_buffer_1962` is empty, the current DOS directory helper fills it. If the runtime save-description/path buffer `[0x0e72]` is already nonempty, the helper skips the path prompt. Otherwise it displays the save or restore path question, edits `data.save.path_buffer_1962` with a 31-character modal editor, and validates it through `code.dos.validate_path`. The validator skips leading spaces, fills an empty accepted string with the current directory, strips a trailing slash/backslash from multi-character paths, accepts a single slash/backslash, probes two-character drive paths such as `A:`, and otherwise uses DOS find-first with directory attributes. | Enter accepts the edited path if validation succeeds. Escape/cancel returns zero. An invalid or unavailable path displays the insert-disk/path failure message and loops while the acknowledgement helper returns nonzero. | Success leaves a validated path in `data.save.path_buffer_1962`; failure returns zero to the action, so save/restore continues down its cancel/failure continuation rather than performing file I/O. |
| Slot scan | The selector formats `1..12` candidate filenames with `code.save.format_slot_filename`. Restore candidates must pass `code.save.read_slot_summary`: open succeeds, a 31-byte description is read, the first length prefix is skipped, and seven first-block payload bytes compare against `data.save.signature_prefix_0002`. | The selector displays available descriptions in a modal list. Empty save slots can be accepted by the save path; restore only presents candidates that pass the signature check. | Each valid row has a description, slot number, and timestamp-like ordering metadata. The selected slot later formats the final filename into `data.save.filename_buffer_1c8c`. |
| Slot interaction | The current row is marked with the right-arrow glyph and the old row is cleared with a space. | Enter accepts the current row; Escape returns zero; normalized movement events `1` and `5` move up and down with wrap. | Enter yields a nonzero slot result. Escape/cancel yields zero and no caller file I/O should occur. |
| Save-description edit | In save mode, accepting an empty-description slot opens a second 31-character modal editor for the save description. | Enter stores the accepted description; Escape/cancel abandons the selection. | Accepted text fills the 31-byte save header buffer `data.save.header_description_buffer_1c6c` before action `0x7d` creates the file. Restore mode never writes this buffer from the selector. |
| Caller confirmation and I/O | The selector has restored modal state and returned to action `0x7d` or `0x7e`. | Save and restore each display their caller-side confirmation text before doing DOS file I/O. | Save create/write failures are recoverable and continue after `0x7d`; restore open failure is recoverable and continues after `0x7e`; restore read failure displays the fatal restore-error dialog and exits through cleanup. |

Gold Rush / AGI v3 keeps the five-block save-envelope shape but changes the
object/inventory block written from `[0x07d6]` with length `[0x07da]`: action
`0x7d` applies a repeating 59-byte XOR sequence observed at image `0x072c`
before the save path and applies the same transform again before return, so the
on-disk block is transformed while runtime memory is restored.

Restart, save/restore, and termination lifecycle:

| Transition | Trigger | State effects | Continuation |
| --- | --- | --- | --- |
| In-engine restart accepted | `0x80` confirmation succeeds, or flag 16 skips confirmation | Stops sound, erases input, preserves flag 9, rewinds heap/update-list state through `code.heap.reset_dynamic_state`, reruns initial object/inventory setup through `code.restart.initialize_game_tables`, refreshes display/menu state, sets flag 6, restores flag 9 if it had been set, clears timer words `[0x0129]` and `[0x012b]`, and reloads trace logic `[0x1d12]` if configured. | Returns zero to the action dispatcher, ending the current logic stream so the main loop continues from the reset state. |
| Restart canceled | `0x80` confirmation returns zero/Escape | Sound has already been stopped and the prompt/input line redrawn; the reset block is skipped. | Returns the following bytecode pointer, so the current logic continues. |
| Save create failure | `0x7d` receives `0xffff` from `code.dos.create_file` | Displays the directory-full or write-protected message rooted at `0x0df0`, restores modal text/window state, restores byte `[0x0d15]`, and clears modal-state word `[0x0615]`. | Returns the following bytecode pointer; the game continues. |
| Save write failure | `0x7d` short-writes the 31-byte header or any length-prefixed block | Closes the partial file, deletes filename buffer `0x1c8c`, displays the disk-full message rooted at `0x0e46`, restores modal text/window state, restores byte `[0x0d15]`, and clears modal-state word `[0x0615]`. | Returns the following bytecode pointer; the game continues. |
| Restore open failure | `0x7e` receives `0xffff` from `code.dos.open_file` | Displays the can't-open-file message rooted at `0x0d73`, restores modal text/window state, restores byte `[0x0d15]`, and clears modal-state word `[0x0615]`. | Returns the following bytecode pointer; the game continues. |
| Restore success | `0x7e` reads all five state blocks | Restores scalar/object/inventory/event/cache state from the save file, restores display adapter/mode bytes, adjusts hardware-mode flag 11, replays saved resource-event pairs with recording disabled only during replay, refreshes display/resource state, clears the caller return pointer, and refreshes menu/list state. | The action returns zero, so execution restarts through the restored state rather than continuing after the restore opcode. |
| Restore read failure | `0x7e` fails any length-prefixed block read | Closes the save file, displays the restore-error message, then enters `code.system.exit_with_cleanup`. | Terminates the DOS process through `int 21h AH=0x4c`; this is not a recoverable restore failure in the observed source. |
| Confirmed exit or fatal helper | `0x86(1)`, confirmed `0x86(0)`, verification failure, allocation failure, or restore read failure | `code.system.exit_with_cleanup` closes the log file if open, restores interrupt hooks and timer state, sets the BIOS video mode from the saved mode byte, and calls the DOS terminate wrapper with exit code zero. | DOS process exits. |

Gold Rush / AGI v3 changes the prompt-marker redraw branch in action `0x80`.
It records `data.input.prompt_marker_visible_state` before erasing the marker;
after confirmation it redraws the marker when restart was accepted or, for a
canceled restart, only when the marker had been visible before entry. The local
truth-table helper `gr_v3_restart_redraws_prompt_marker()` models this branch.

Picture decoder lifecycle:

| State | Entered by | Exited by | Observable contract |
| --- | --- | --- | --- |
| Picture cached | `0x18`/`0x19`/`0x1c` resource helpers | Discard, room/reset cache cleanup, or replacement selection | The resource cache stores the selected picture payload pointer. Loading records resource-event pairs unless event recording is blocked. |
| Fresh decode | `0x19` prepare path through `0x6445` | Scanner completion at `0xff` | The logical 160 by 168 byte buffer is initialized to default cell `0x4f`, draw globals are reset, and then the scanner runs over the selected payload. |
| Overlay decode | `0x1c` path through `0x6440` | Scanner completion at `0xff` | The scanner runs without the fresh-buffer fill, so valid commands compose over the existing logical buffer. |
| Command scanner | Picture bytes read from the selected payload | `0xff` sentinel or payload exhaustion in local tooling | Bytes below `0xf0` are ignored by the top-level scanner. Commands `0xf0..0xfa` dispatch to drawing handlers; `0xfb..0xfe` have no handler in the observed table. Raw one-byte operands for `0xf0`, `0xf2`, and `0xf9` consume the next byte even when it is `>= 0xf0`. Coordinate/list readers accept only bytes `<= 0xef`; a command/sentinel byte terminates the active drawing command and remains pending for the scanner. |
| Draw state | `0xf0..0xf3`, `0xf9` | Later draw-state command or scanner end | Low visual and high control nibbles can be independently enabled/disabled. Pixel writes always flow through the common writer using active draw bits and odd/even masks. In the full EGA target, the observed visual mask values are the same on odd and even rows. |
| Line/corner/pattern drawing | `0xf4..0xf7`, `0xfa` | Command reader sees another command/sentinel byte | Corner and line commands plot into the logical byte buffer with coordinate clamping. Relative-line endpoints use 8-bit coordinate arithmetic before the high-side clamp, so a negative underflow becomes the right or bottom edge rather than zero. Diagonal lines use the interpreter's byte-width accumulator behavior. Pattern plotting uses the AGIDATA pattern tables and can linearly write a computed column at X `160` as X `0` on the next row before the final buffer bound check. |
| Seed fill | `0xf8` | Seed list terminates | The selected expansion-test channel is visual when visual drawing is enabled, otherwise control when control drawing is enabled. The write itself still uses the common active-channel writer, so accepted cells can update both nibbles when both channels are active. A clean implementation may use any finite connected-region traversal that produces the same final logical buffer for valid data. |
| Display finalization | `0x1a`, replay/display helpers, object pipeline refresh | Next draw/update/display transition | The decoded logical buffer is converted to visible output by the active EGA display path, with text/modal overlays handled separately from picture decoding. |

View and cel drawing contract:

| Element | Implementation contract |
| --- | --- |
| View payload | Bytes `+0x00/+0x01` are reserved in the current SQ2 model; all local resources contain `0x01,0x01` and observed runtime paths begin meaningful parsing at `+0x02`. Header byte `+0x02` is the group count. Group offsets are relative to the payload base from `+0x05`; frame offsets are relative to their group base. Frame bytes are width, height, control byte, then row-terminated run data. |
| Cel rows | Each nonzero row byte encodes color in the high nibble and run length in the low nibble. A zero byte ends a row. The control low nibble is the transparent color; transparent runs advance X without writing. |
| Orientation rewrite | If frame control bit `0x80` is set and bits `0x70` do not match the selected group, the interpreter rewrites the frame stream in place so visible row runs are mirrored horizontally and bits `0x70` cache the selected group. |
| Baseline placement | The draw top is `baseline_y - frame.height + 1`. Placement helpers search/clamp requested object coordinates before activation/transient drawing, including horizon, screen bounds, collision, and control-buffer acceptance. |
| Priority/control gate | Visible object pixels compare the object's low priority nibble against the destination high nibble. High nibbles greater than `0x20` are compared directly; lower classes trigger a downward scan in the same column until a comparable high nibble is found or the lower buffer limit is reached. A pixel draws when the discovered value is less than or equal to the object's priority. |
| Pixel write | Nontransparent cel pixels write `(object_priority << 4) | cel_color` into the logical buffer. The high nibble left by object drawing becomes part of later priority/control tests. |
| Transient versus persistent | Action `0x7a` draws a transient view/cel against the current picture state. Persistent objects bind view payloads into 43-byte object records, enter update lists when activated, and are redrawn/restored by the object/update pipeline. |

Persistent placement and movement accept a proposed object position only when
the object-object crossing test accepts it and the control-buffer scan accepts
the selected frame-width scanline. In the control scan, class `0x00` rejects
immediately, class `0x10` requires object bit `0x0002`, class `0x20` leaves
final state `(flag3=true, flag0=false)`, class `0x30` leaves final state
`(flag3=false, flag0=true)`, and other nonzero classes leave
`(flag3=false, flag0=false)`. The final scanned class, not an accumulated
history of earlier cells, drives the post-scan `0x0100` and `0x0800` rejection
bits and the global flag updates for objects whose byte `+0x02` is zero.
Priority/control byte `0x0f` bypasses this scan.

Object drawing lifecycle:

| State | Entered by | Exited by | Observable contract |
| --- | --- | --- | --- |
| Empty/reset record | `reset_object_state`, room reset, startup | View bind and field setup | Active flag is clear; drawing and movement passes ignore the record. |
| Bound frame | `set_object_resource*`, group/frame selectors | Position/activation changes or discard/reset | Record has a view payload, selected group/frame pointer, width, and height. |
| Placed | Position setters and placement helper `0x593a` | Activation, movement, or another position setter | Coordinates have been clamped/searched against bounds, horizon, collision, and control-buffer acceptance. Dirty bit `0x0400` suppresses one movement delta and is then cleared. |
| Active/listed | `activate_object` | `deactivate_object`, reset, room switch | Active/update bits include `0x0001`; update-list roots are flushed/rebuilt and render nodes may save backing rectangles. |
| Rendered | Update-list processing or transient draw helper | List flush/rectangle restore or redraw | The selected frame's run data is composited into the logical buffer using transparent-color skip and priority/control gating. Dirty refreshes copy the union of the previous saved footprint and the current footprint, where top is `baseline_y - height + 1`. |

Motion and animation lifecycle:

| State | Entered by | Exited by | Observable contract |
| --- | --- | --- | --- |
| Stationary | Motion mode `+0x22` is zero or direction `+0x21` is zero | Script motion action or autonomous mode dispatch | Per-cycle movement writes no new position. Frame animation may still run when bit `0x0020` is set. |
| Countdown gated | Object byte `+0x01` is nonzero | Countdown reaches zero | Movement is skipped until due; the countdown reloads from `+0x00` after a due cycle. |
| Autonomous mode step | Mode `1`, `2`, or `3` with due countdown | Direction computed or completion helper | Mode `1` picks/randomizes direction, mode `2` approaches object 0 with stuck recovery, and mode `3` recomputes direction toward target X/Y. Completion restores step size, sets the configured flag, and clears mode. |
| Proposed move | Direction and step produce candidate X/Y | Accept/reject tests | Candidate is clamped to screen/horizon bounds; boundary globals are recorded when a clamp survives. |
| Accepted or restored | Control/collision tests complete | Next cycle | Accepted moves keep the candidate coordinates. Rejected moves restore saved coordinates, clear boundary code, and run placement search. |
| Frame callback | Bit `0x0020` set and frame timer reaches zero | Frame mode handler | Mode byte `+0x23` advances or wraps frames, with one-callback startup delay bit `0x1000` where applicable. |

Gold Rush / AGI 3.002.149 source comparison adds two version-specific motion
notes. First, object motion mode `4` dispatches to the same target-direction
helper as mode `3`; SQ2 treats modes above `3` as no autonomous-mode dispatch.
Second, GR's automatic direction-to-loop selection gates the more-than-four-loop
table on flag `0x14` and does not use that table for exactly-four-loop views in
the observed branch. These are not yet QEMU-validated with v3 fixtures.

Text/input UI lifecycle:

| State | Entered by | Exited by | Observable contract |
| --- | --- | --- | --- |
| Input line hidden/disabled | `0x77` or display/text cleanup paths | `0x78` | Word `[0x05d3]` is zero; refresh helpers should not redraw the normal input line. |
| Input line enabled | `0x78` | `0x77`, modal prompts, or text-window cleanup | Word `[0x05d3]` is one; `0x78` redraws/clears the configured input row in the normal EGA path, `0x89` redraws from the entered source input buffer, and `0x8a` erases visible input characters. |
| Prompt/status configured | `0x6c`, `0x6f`, `0x70`, `0x71` | Later configuration or cleanup | Prompt character, row/column-like globals, status-line enable word `[0x05d9]`, and display offset `[0x1379]` determine where text helpers draw and erase. QEMU validates that setting the prompt marker from an empty message suppresses marker drawing on the next input-line redraw, and that `0x70` visibly redraws the configured status row. |
| Modal text window active | Message display, prompt/edit, menu, or diagnostic helpers | `0xa9` or the helper's own close path | The message-window opener at `0x1d96` first closes any already active saved window, formats the text, computes packed rectangle words `[0x0d23]` and `[0x0d25]`, draws/saves the boxed region through helper `0x5590`, then sets `[0x0d1d] = 1`. Closing through `0xa9`/`0x1f2b` restores that saved rectangle through helper `0x560c([0x0d23], [0x0d25])` when active, then clears `[0x0d0f]` and `[0x0d1d]`. |
| Alternate text/input-width mode | `0x6a`, `0xa3`, and related display-mode helpers | `0x6b`, `0xa4`, or `0xa9`/cleanup paths | Byte `[0x1757]` alters text drawing, while word `[0x0d0f]` changes input-character width limits in helper `0x3652`. QEMU validates that `0x6a` clears the visible logical surface using the current text attribute pair in the observed EGA path, that `0x6b` restores ordinary picture/object drawing, that `0xa3` permits wrapped live input with a long blank string slot 0, and that both `0xa4` and inactive `0xa9` clear the width flag. |
| Event/edit loop | `code.input.edit_string`, menus, inventory selection, confirmation dialogs, keyboard IRQ hook | Enter, Escape, selected mapped/status event, or tracked key release | The shared event queue feeds raw key predicates, line editors, menu status-byte events, and confirmation exits. Action `0xad` increments `[0x1530]`, a source-backed nonzero gate that lets the keyboard IRQ hook enqueue type-2 zero events on selected tracked-key releases. |

Menu/list data model:

| Element | Source-backed layout | Contract |
| --- | --- | --- |
| Heading node | 18-byte heap node. Offsets `+0x00` and `+0x02` are next/previous heading links; `+0x04` is the heading text pointer; `+0x08` is the heading column; `+0x0a` is an enabled/usable word; `+0x0c` is the circular item-list root; `+0x0e` remembers the current item for this heading; `+0x10` is the item count. | Headings form a circular list rooted at `data.menu.heading_root`. Empty headings are marked disabled during later setup/finalization. Left/right navigation skips disabled headings. |
| Item node | 14-byte heap node. Offsets `+0x00` and `+0x02` are next/previous item links; `+0x04` is the item text pointer; `+0x06` is the menu row/order; `+0x08` is the menu column; `+0x0a` is the enable word; `+0x0c` is the script-visible item id. | Items form a per-heading circular list. Item navigation does not skip disabled entries; the enable word is checked only when Enter is pressed. |
| Menu globals | `data.menu.finalized`, `data.menu.request_interaction`, `data.menu.heading_root`, `data.menu.current_heading`, and `data.menu.current_item`. | Setup opcodes populate the list until finalized. Interactive movement persists the current heading/item before each event-loop iteration so later menu openings resume from the remembered position. |

Menu interaction lifecycle:

| State | Entry work | Event/transition | Output contract |
| --- | --- | --- | --- |
| Setup mutable | `0x9c` allocates and links heading nodes; `0x9d` allocates and links item nodes under the current heading. | Setup continues until `0x9e`. If a heading has no item list, setup marks its enable word zero. | List nodes live on the interpreter heap. After finalization, later `0x9c`/`0x9d` calls are ignored by the observed handlers. |
| Setup finalized | `0x9e` records the heap room/reset mark, sets `current_heading` to the root heading, sets `current_item` from the heading's item root, and sets the finalized word. | `0x9f` and `0xa0` can later enable or disable item ids by walking all heading/item lists. | The circular lists remain active until the broader heap/menu state is rebuilt by restart/restore/room lifecycle helpers. |
| Interaction requested | `0xa1` tests flag 14; when set, it writes `data.menu.request_interaction = 1`. The input/main-loop path enters `code.menu.interact` and clears the request word on exit. | No direct selection occurs in `0xa1`; it only requests the modal menu path. | QEMU validates the request plus one-item Enter, Escape, disabled-Enter, and re-enable paths. |
| Menu opened | `code.menu.interact` clears/redraws the text row, redraws each heading, loads `current_heading`/`current_item`, and draws the active heading and its item rectangle. | The loop waits through the shared input/event helpers, then branches on normalized event type. | The modal menu owns the visible text surface while active; tests refresh the picture after closing before comparing graphics output. |
| Raw-key event | Event type `1` supplies a raw key word. | Enter (`0x000d`) selects only if the current item's enable word is nonzero; Escape (`0x001b`) exits without selection; other keys loop. | Enter on an enabled item enqueues event type `3` with the item's id. Enter on a disabled item leaves no status event and continues waiting. |
| Movement event | Event type `2` supplies movement value `1..8`, mapped from the local raw-key table. | Values dispatch through `table.menu.navigation_dispatch`: previous item, first item, next enabled heading, last item, next item, last heading, previous enabled heading, and root heading. | Movement redraws/unhighlights affected rows, remembers a heading's current item before leaving it, stores updated `current_heading` and `current_item`, and waits for another event. |
| Exit cleanup | Selection or Escape calls the helper that remembers the active item for the heading and restores the saved menu rectangle. | Status line is redrawn when enabled; otherwise the associated row is cleared. | `data.menu.request_interaction` is cleared. Selection is observable through condition `0x0c` on the enqueued item id. |

Text rectangle clears (`0x69` and `0x9a`) are display-surface operations. They
do not decode or mutate a picture resource; they overwrite the visible text-cell
rectangle with the requested attribute/background. In the EGA target validated
so far, text columns are four logical pixels wide and text rows are eight
logical pixels tall.

Status-line hide (`0x71`) and input-line disable (`0x77`) use the same visible
text surface rather than the decoded picture buffer. In the normal EGA path,
`0x71` clears the single row configured as the status row by `0x6f` operand 2,
and `0x77` clears the single row configured as the input row by `0x6f` operand
1. The validated row geometry is eight logical pixels tall.

Input-line enable (`0x78`) also redraws the configured input row through the
text surface before it writes any configured prompt/input strings. With an empty
prompt marker and empty input buffers, the validated visible result is the same
single eight-pixel-tall black row. Input-line erase (`0x8a`) uses repeated
backspace handling to reduce visible input length `[0x0ff8]` to zero; QEMU
validates that typed live-edit glyphs disappear from the configured input row.
Input-line refresh (`0x89`) does not replay unaccepted live-edit characters in
the observed path. After Enter copies accepted text into the source input
buffer at `0x0fce`, `0x89` repaints visible glyphs by copying that source into
visible buffer `0x0fa4`. Entering alternate text-attribute mode
through `0x6a` is broader: the observed EGA result clears the full logical
surface using the current attribute pair and ordinary transient-object
composition is not visible while that mode remains active in the probe. With
the default pair this is a black clear. After `0x6d(0, 1)`, the disassembly
shows the stored pair is reinterpreted by `0x6a` with `[0x1757] = 1` as packed
text attribute `0xf0`; QEMU validates a full-screen visual color 15 clear for
that case.

The prompt marker configured by `0x6c` is a single byte copied from the start of
the resolved message. When that byte is zero, input-line redraw skips marker
drawing. The current QEMU evidence covers the empty-message suppression path;
nonempty prompt glyph shape is still a font/text-rendering detail rather than a
fully modeled compatibility contract.

Menu interaction is another consumer of the shared event queue. Menu setup
builds circular heading and item lists; each node's word at offset `+0x00` is
the next pointer and `+0x02` is the previous pointer. A heading's item root is
at `+0x0c`, its remembered/current item is at `+0x0e`, and its active/enabled
word is at `+0x0a`. Item nodes store their enabled word at `+0x0a` and their
script-visible selection id at `+0x0c`. Enter enqueues a type-3 event carrying
that id only when the current item is enabled. Movement events use values
`1..8`: up/previous item, page-up/first item, right/next enabled heading,
page-down/last item, down/next item, end/last heading, left/previous enabled
heading, and home/root heading. After each movement, the engine persists the
current heading and item in `[0x1d2e]` and `[0x1d30]`.

## Diagnostic and Trace Services

Several action opcodes are developer-facing or VM-facing services rather than
ordinary game-world operations:

- `0x87` (`show_heap_status`) formats heap/script memory counters into a message
  box.
- `0x1d` (`show_priority_screen`) temporarily swaps the high and low nibbles of
  every logical graphics-buffer byte during a full-screen refresh. The observed
  command phrase is `show pri`, and the displayed buffer is best modeled as a
  priority/control inspection view.
- `0x95` (`enable_action_trace_window`) and `0x96`
  (`configure_action_trace_window`) manage an action-trace window. When enabled,
  the dispatcher calls the trace formatter before each action handler. QEMU
  validates the enabled path as a red-bordered, white-filled trace window with
  black opcode/operand text. A new implementation can expose this as optional
  VM tracing rather than coupling it to normal game semantics.
- `0x8f` (`verify_game_signature`) resolves a short message string and compares
  it against the interpreter's embedded `SQ2` signature. A mismatch calls the
  same restart/exit helper used by confirmation-gated exit paths.

## UI, diagnostics, and device state

Several actions are better modeled as services around the VM rather than as
game-world operations:

- The input line has an enabled flag at `[0x05d3]`, a visible/input buffer at
  `0x0fa4`, an entered source buffer at `0x0fce`, and a length word at
  `[0x0ff8]`. Actions `0x77`, `0x78`, `0x89`, and `0x8a` disable, enable,
  refresh, and erase that line.
- Action `0x88` is a pause dialog. It stops sound, displays a fixed pause
  message, and returns to the script after the display helper completes.
- Action `0x87` is a heap/status diagnostic. It formats heap and script-budget
  globals into a message, so a replacement implementation can expose it as a
  diagnostic overlay without tying it to game state.
- Action `0x6e` is a transient display shake. In the normal path it does not
  mutate the logical picture/object buffers; it writes CRT/display-register
  offsets from a small table and waits on timer ticks. A portable
  implementation can model the observable contract as a short camera/display
  offset animation with no persistent surface change.
- Action `0x8b` is joystick calibration. It presents a centered-joystick prompt,
  samples joystick state through helpers around `0x63be` and `0x6425`, and
  stores calibrated bounds in globals near `0x15c9..0x15cf`.
- Action `0x8c` toggles bit 0 of display mode word `[0x1130]` when the current
  hardware/display configuration allows it, then rebuilds display state.
