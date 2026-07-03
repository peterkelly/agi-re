# Logic bytecode interpreter notes

This page records clean-room observations about the interpreter for logic
payload bytecode. It is based on local disassembly of
`build/cleanroom/AGI.decrypted.exe`, the runtime tables in `SQ2/AGIDATA.OVL`,
and decoded SQ2 logic payloads.

For a compact generated coverage index that lists every action opcode, every
known condition opcode, operand shapes, and current evidence level, see
[Logic Opcode Evidence Matrix](./logic_opcode_evidence.md).

## Runtime tables

After startup, `DS` points at `AGIDATA.OVL`. Both bytecode dispatchers use
tables in that overlay rather than in the executable image.

The action dispatcher at image offset `0x02c4` calls through:

```text
handler = u16le(DS:0x061d + opcode * 4)
```

Each action-table entry is four bytes:

```text
u16 handler_image_offset
u8  fixed_operand_count
u8  variable_operand_bitmask
```

The condition dispatcher at image offset `0x07e3` calls through:

```text
handler = u16le(DS:0x08fd + opcode * 4)
```

Each condition-table entry has the same four-byte shape. The condition scanner
uses the third byte as the fixed operand count when it needs to skip an
unexecuted condition.

The fourth byte is an operand metadata bitmask. From decoded handlers, bit 7
corresponds to operand 0, bit 6 to operand 1, and so on. A set bit means that
the corresponding operand is a variable slot/reference rather than an immediate
literal for table-aware decoding. The dispatcher does not apply this bitmask
generically; each handler still consumes operands directly and decides whether a
variable slot is read from or written to.

Examples:

| Entry | Metadata | Meaning confirmed by handler |
| --- | ---: | --- |
| action `0x03` (`assignn`) | `0x80` | Operand 0 is a variable slot, operand 1 is an immediate literal. |
| action `0x04` (`assignv`) | `0xc0` | Operands 0 and 1 are variable slots. |
| action `0x26` (`set_object_pos_var`) | `0x60` | Operand 0 is an object index; operands 1 and 2 are variable slots. |
| action `0x52` (`move_object_to_var`) | `0x70` | Operand 0 is an object index; operands 1, 2, and 3 are variable slots; operand 4 is immediate. |
| action `0x7b` (`setup_transient_object_var`) | `0xfe` | Seven operands are variable slots. |
| condition `0x0a` (`obj_table_room_eq_var`) | `0x40` | Operand 0 is a table/object index; operand 1 is a variable slot. |

`AGIDATA.OVL` contains valid-looking condition entries for opcodes `0x00`
through `0x12`. Bytes after that are strings and zero-filled data, even though
the dispatcher only rejects condition opcodes `>= 0x26`. In the current local
SQ2 scan, condition opcodes above `0x12` were not needed for successfully
parsing ordinary condition lists.

## Main interpreter loop

The main logic interpreter is at image offset `0x293c`. It starts from the
current instruction pointer stored in a logic cache record:

```text
si = logic_record[0x06]

loop:
    opcode = *si++

    if opcode == 0x00:
        logic_record[0x06] = 0
        return 0

    if opcode == 0xfe:
        delta = s16le(*si); si += 2
        si += delta
        continue

    if opcode == 0xff:
        evaluate_condition_then_maybe_execute_block()
        continue

    execute_action(opcode)
    if action returns si == 0:
        return 0
    continue
```

The `0xfe` branch is visible at image offsets `0x2953..0x295a`: it reads a
little-endian word with `lodsw` and adds it to `SI`.

Action execution is delegated to `0x02c4`. That dispatcher rejects opcodes
`0x00` and `0xfc..0xff`, reports an error for opcodes above `0xaf`, then calls
the action table at `DS:0x061d`.

Putting the observed dispatch ranges together:

| Main-stream byte/range | Observed role |
| --- | --- |
| `0x00` | Logic-path terminator handled before the action dispatcher. |
| `0x01..0xaf` | Normal action opcodes. The action table contains one entry for each byte in this range. |
| `0xb0..0xfb` | Invalid as action opcodes in this build. They reach the action dispatcher and take its "opcode above `0xaf`" error path. |
| `0xfc` | Invalid outside condition parsing. It is rejected by the action dispatcher as a structural/control byte. |
| `0xfd` | Invalid outside condition parsing. It is rejected by the action dispatcher as a structural/control byte. |
| `0xfe` | Relative jump handled by the main interpreter loop. |
| `0xff` | Conditional block marker handled by the main interpreter loop. |

## Conditional blocks

Opcode `0xff` introduces a condition list. The condition parser uses these
marker bytes:

| Byte | Observed role |
| --- | --- |
| `0xfd` | Invert the next condition result. |
| `0xfc` | OR-group marker. |
| `0xff` | End of condition list. |

The condition parser keeps two state bytes in `BX`. `BL` is the pending
inversion flag for `0xfd`; after each condition result is XORed with `BL`, the
parser clears `BL`. `BH` tracks whether parsing is inside an OR group.

Observed `0xfc` behavior:

- If `BH == 0`, `0xfc` starts an OR group by setting `BH = 1`.
- If `BH != 0`, a second `0xfc` means the OR group ended without a true term,
  so the whole condition list fails.
- A false condition inside an OR group continues scanning for another OR term.
- A true condition inside an OR group clears `BH`, skips the remaining OR terms
  until the next `0xfc`, then resumes normal condition parsing.
- A false condition outside an OR group fails the whole condition list.
- A true condition outside an OR group simply advances to the next condition.

When all required conditions pass, execution continues with the following
bytecode. When the condition list fails, the interpreter scans forward without
executing actions until it finds a block-ending `0xff`, then reads a
little-endian relative offset and adds it to `SI`.

When a condition list has already failed, or when a true OR-term needs to skip
the rest of its OR group, the condition-list scanner must know condition
instruction lengths. For most condition opcodes it uses the fixed operand count
in the condition dispatch table. There is a special case for condition opcode
`0x0e` (`input_word_sequence`): the scanner reads one count byte and skips `count * 2` additional
bytes. This special case appears in the condition skip paths at image offsets
`0x29af..0x29b8` and `0x29d7..0x29e0`.

## Condition table

The current `DS:0x08fd` condition table entries are:

| Opcode | Label | Handler | Fixed operands | Metadata |
| ---: | --- | ---: | ---: | ---: |
| `0x00` | `always_false` | `0x09d8` | 0 | `0x00` |
| `0x01` | `var_eq_imm` | `0x0823` | 2 | `0x80` |
| `0x02` | `var_eq_var` | `0x0834` | 2 | `0xc0` |
| `0x03` | `var_lt_imm` | `0x084b` | 2 | `0x80` |
| `0x04` | `var_lt_var` | `0x085c` | 2 | `0xc0` |
| `0x05` | `var_gt_imm` | `0x0873` | 2 | `0x80` |
| `0x06` | `var_gt_var` | `0x0884` | 2 | `0xc0` |
| `0x07` | `flag_set` | `0x089b` | 1 | `0x00` |
| `0x08` | `flag_set_var` | `0x08a0` | 1 | `0x80` |
| `0x09` | `obj_table_room_ff` | `0x08ad` | 1 | `0x00` |
| `0x0a` | `obj_table_room_eq_var` | `0x093b` | 2 | `0x40` |
| `0x0b` | `object_left_baseline_in_rect` | `0x08c6` | 5 | `0x00` |
| `0x0c` | `status_byte_1218` | `0x0931` | 1 | `0x00` |
| `0x0d` | `raw_key_event_available` | `0x09be` | 0 | `0x00` |
| `0x0e` | `input_word_sequence` | `0x095c` | 0 | `0x00` |
| `0x0f` | `string_slots_equal_normalized` | `0x09db` | 2 | `0x00` |
| `0x10` | `object_width_baseline_in_rect` | `0x08e8` | 5 | `0x00` |
| `0x11` | `object_center_baseline_in_rect` | `0x08cc` | 5 | `0x00` |
| `0x12` | `object_right_baseline_in_rect` | `0x08db` | 5 | `0x00` |

The bytes after condition-table entry `0x12` decode as string/data bytes and
then zero fill if forced through the same 4-byte entry parser. Although the
condition dispatcher only rejects opcodes `>= 0x26`, no valid local condition
list uses opcodes `0x13..0x25`; for this build they are treated as
invalid/reserved rather than real predicates.

Condition-list byte ranges:

| Condition byte/range | Observed role |
| --- | --- |
| `0x00..0x12` | Valid predicates in this SQ2 build, listed above. |
| `0x13..0x25` | Reserved/invalid for the portable model of this build. The dispatcher bound would allow them, but the underlying bytes are not a valid dispatch-table region. |
| `0x26..0xfb` | Rejected by the condition dispatcher if encountered as predicate opcodes. |
| `0xfc` | OR-group marker interpreted by the condition-list scanner. |
| `0xfd` | Invert-next-condition marker interpreted by the condition-list scanner. |
| `0xfe` | Rejected by the condition dispatcher if encountered as a predicate opcode. |
| `0xff` | Condition-list terminator interpreted by the condition-list scanner. |

The first seven handlers directly expose byte variable comparisons. The byte
variable array begins at `DS:0x0009`.

| Opcode | Label | Observed predicate |
| ---: | --- | --- |
| `0x00` | `always_false` | Always false. Handler `0x09d8` returns zero. |
| `0x01` | `var_eq_imm` | `byte[0x0009 + arg0] == arg1` |
| `0x02` | `var_eq_var` | `byte[0x0009 + arg0] == byte[0x0009 + arg1]` |
| `0x03` | `var_lt_imm` | `byte[0x0009 + arg0] < arg1` |
| `0x04` | `var_lt_var` | `byte[0x0009 + arg0] < byte[0x0009 + arg1]` |
| `0x05` | `var_gt_imm` | `byte[0x0009 + arg0] > arg1` |
| `0x06` | `var_gt_var` | `byte[0x0009 + arg0] > byte[0x0009 + arg1]` |
| `0x07` | `flag_set` | Tests flag bit `arg0`. |
| `0x08` | `flag_set_var` | Tests flag bit `byte[0x0009 + arg0]`. |
| `0x09` | `obj_table_room_ff` | Looks up a 3-byte table entry at `[0x0971] + arg0 * 3` and tests whether byte `+2` is `0xff`. |
| `0x0a` | `obj_table_room_eq_var` | Compares byte `+2` of that 3-byte table entry with `byte[0x0009 + arg1]`. |
| `0x0c` | `status_byte_1218` | Returns byte `DS:0x1218 + arg0`. |
| `0x0d` | `raw_key_event_available` | Checks or obtains a raw key-like event byte through helper `0x459e`, caching a non-zero byte at `DS:0x001c`. |
| `0x0e` | `input_word_sequence` | Variable-length parsed-input word sequence test. |
| `0x0f` | `string_slots_equal_normalized` | Compares two fixed string slots after a small normalization pass. |

The handler reads two byte operands and passes them to helper `0x0eac`.
Helper `0x0eac` builds two temporary normalized strings through helper
`0x0ef8`, then compares the resulting zero-terminated byte strings exactly.
The string-slot address is computed as `0x020d + slot * 0x28`.

The `0x0ef8` normalization step:

- walks the source slot until a zero byte;
- skips bytes present in the zero-terminated table at `DS:0x094b`;
- in local SQ2 data, `DS:0x094b` contains space, tab, `.`, `,`, `;`, `:`,
  `'`, `!`, and `-`;
- converts ASCII uppercase `A..Z` to lowercase `a..z` through helper `0x4fea`;
- writes a zero terminator to the temporary buffer.

Unlike action `0x75` (`parse_string_slot`), this predicate does not parse
dictionary words and does not use the parsed-word tables. It is a direct
case-insensitive comparison after dropping the listed punctuation/spacing
bytes.

Condition opcodes `0x0b` (`object_left_baseline_in_rect`),
`0x10` (`object_width_baseline_in_rect`),
`0x11` (`object_center_baseline_in_rect`), and
`0x12` (`object_right_baseline_in_rect`) all load an entry from a
43-byte structure array rooted at `[0x096b]` using the first operand as an
index. They compare that object's baseline position or horizontal extent
against four subsequent byte operands:

```text
arg0: object index
arg1: left bound
arg2: top/Y bound
arg3: right bound
arg4: bottom/Y bound
```

The shared helper at `0x091a` loads:

```text
object = [0x096b] + arg0 * 0x2b
dh = object[+0x03]
ch = object[+0x03]
dl = object[+0x05]
```

The common comparison at `0x08f0` returns true when:

```text
dh >= arg1
dl >= arg2
ch <= arg3
dl <= arg4
```

The four handlers differ only in how they choose `dh` and `ch` before the
comparison:

| Opcode | Label | Horizontal test before shared rectangle comparison |
| ---: | --- | --- |
| `0x0b` | `object_left_baseline_in_rect` | Tests object left X and baseline Y inside the rectangle: `dh = ch = x`. |
| `0x10` | `object_width_baseline_in_rect` | Tests the full object horizontal span at baseline Y: `dh = x`, `ch = x + width - 1`. |
| `0x11` | `object_center_baseline_in_rect` | Tests object horizontal center and baseline Y: `dh = ch = x + floor(width / 2)`. |
| `0x12` | `object_right_baseline_in_rect` | Tests object right X and baseline Y: `dh = ch = x + width - 1`. |

Flag helpers use a bitfield rooted at `DS:0x0109`. Helper `0x7511` computes:

```text
byte_address = DS:0x0109 + flag_number / 8
mask = 0x80 >> (flag_number & 7)
```

Helper `0x74ee` sets the bit, `0x74f4` clears it, `0x74fc` toggles it, and
`0x7502` tests it. Initialization helper `0x752a` clears `0x20` bytes starting
at `DS:0x0109`.

Condition opcode `0x0e` (`input_word_sequence`) is the most common condition in the local SQ2 scripts.
Its bytecode operands are variable length:

```text
u8 count
u16le word_id[count]
```

Handler `0x095c` compares those word IDs with a parsed input-word buffer rooted
at `DS:0x0c7b`; word `[0x0ca3]` is used as the parsed-word count. The handler
returns false without consuming the word list when the parsed-word count is
zero, when flag 4 is already set, or when flag 2 is clear. Otherwise it walks
the operand word IDs and the parsed input words together. Operand word
`0x270f` terminates the test successfully, and operand word `0x0001` behaves as
a wildcard for a parsed word. On a full match the handler sets flag 4 and
returns true; on a mismatch it skips the remaining operand words and returns
false.

### Parsed input producer

Action `0x75` (`parse_string_slot`) is the observed producer for the parsed-word state consumed by
condition `0x0e` (`input_word_sequence`). It reads a string-slot index, accepts only slots `0..11`, and
passes fixed string slot `0x020d + slot * 0x28` to parser helper `0x18ac`.
Before parsing it clears flags 2 and 4.

Helper `0x18ac` clears two 20-byte word tables:

```text
0x0c7b: parsed dictionary word IDs, up to 10 words
0x0c8f: pointers to the normalized words in buffer 0x0ca7, up to 10 words
```

It normalizes the source string through helper `0x199d` into buffer `0x0ca7`.
The normalization step:

- treats bytes from `DS:0x0c67` as separators. In SQ2 this string is
  ` ,.?!();:[]{}`.
- treats bytes from `DS:0x0c75` as ignored punctuation. In SQ2 these bytes are
  `0x27`, `0x60`, `0x2d`, and `0x22`.
- collapses runs of separators to one space.
- drops ignored punctuation instead of making a new word.
- trims a trailing space and writes a zero terminator.

Helper `0x1a6b` then looks up each normalized word in `WORDS.TOK`, whose loaded
base pointer is stored at `[0x0ca5]`. The file starts with 26 big-endian word
offsets, one for each lowercase initial letter. A zero offset means no words
for that initial. Dictionary entries are prefix-compressed:

```text
u8 prefix_len_from_previous_decoded_word
encoded suffix bytes, last byte has bit 7 set
u16be word_id
```

For each suffix byte, `(byte & 0x7f) ^ 0x7f` gives the decoded lowercase
character. The high bit only marks the final suffix byte. Local inspection of
`SQ2/WORDS.TOK` finds 1,099 entries; for example `look` has word ID `0x0002`,
`get` has word ID `0x0005`, and `anyword` has word ID `0x0001`.

Parser result handling in `0x18ac`:

- Recognized words with nonzero IDs are appended to `0x0c7b`, and their
  normalized-word pointers are appended to `0x0c8f`.
- Word ID zero is ignored; single-letter `a` and `i` followed by a space or
  terminator are handled this way, as are entries whose dictionary ID is zero.
- An unrecognized token stores its pointer in `0x0c8f`, sets byte variable
  `[0x0012]` and word `[0x0ca3]` to the one-based token position, and stops
  parsing.
- If at least one token position is produced, flag 2 is set. Condition `0x0e` (`input_word_sequence`)
  later sets flag 4 after a successful command-pattern match.

### Raw event queue

Condition `0x0d` (`raw_key_event_available`) is separate from parsed-word matching. Handler `0x09be` first
checks byte variable `[0x001c]`; if it is already nonzero, the condition
returns true. Otherwise it calls helper `0x459e` until that helper returns
something other than `0xffff`:

```text
event = dequeue_event()                         # 0x44f9
if no event:
    return false
normalize_enter_escape(event)                   # 0x4634
if event.type == 1:
    return event.value
return 0xffff
```

When `0x459e` returns a nonzero key-like value, condition `0x0d` (`raw_key_event_available`) stores the low
byte in `[0x001c]` and returns true. A zero return means no available event and
the condition returns false. A `0xffff` return means a non-key event was
discarded and polling should continue.

The queue itself is a 20-entry circular buffer of 4-byte records:

```text
storage: 0x11ba .. 0x1209
[0x120a]: write pointer
[0x120c]: read pointer

record +0x00: event type word
record +0x02: event value word
```

Helper `0x44a9(type, value)` enqueues a record and fails if advancing the write
pointer would collide with the read pointer. Helper `0x44f9()` dequeues one
record, returning zero when the queue is empty.

Keyboard helper `0x5a89` uses BIOS `int 16h`: it returns zero if no key is
waiting, otherwise reads one key. If the ASCII byte is nonzero it clears `AH`
and returns just that byte; if ASCII is zero, the BIOS scan-code word is
returned intact.

Helper `0x467f` drains available BIOS key events through `0x5a89` and enqueues
them:

- If helper `0x46b6` finds the returned key word in table `DS:0x16b3`, it
  enqueues type `2` with the mapped value.
- Otherwise it enqueues type `1` with the raw key word.

The local `DS:0x16b3` table maps BIOS arrow/keypad scan words to direction-like
values:

| Key word | Mapped value |
| ---: | ---: |
| `0x4800` | `1` |
| `0x4900` | `2` |
| `0x4d00` | `3` |
| `0x5100` | `4` |
| `0x5000` | `5` |
| `0x4f00` | `6` |
| `0x4b00` | `7` |
| `0x4700` | `8` |

Helper `0x4634` normalizes some multi-byte key words after dequeue: values
`0x0101` and `0x0301` become `0x000d`, while `0x0201` and `0x0401` become
`0x001b`.

Helper `0x4566(event_record)` performs a script-configured remap for type-1
events. It scans four-byte slots rooted at `0x0145`; when slot word `+0` equals
the event value, it changes the event type to `3` and replaces the value with
slot word `+2`. Action `0x79` (`map_key_event`) appends entries to this table.

When display adapter word `[0x112e] == 2`, helper `0x46e8` can also remap
type-1 event values through table `DS:0x16d7`, changing the event type to `2`.
The local table maps ASCII digits to direction-like values:

| Key word | Mapped value |
| ---: | ---: |
| `0x0038` | `1` |
| `0x0039` | `2` |
| `0x0036` | `3` |
| `0x0033` | `4` |
| `0x0032` | `5` |
| `0x0031` | `6` |
| `0x0034` | `7` |
| `0x0037` | `8` |

## Action table

The action table at `DS:0x061d` has entries for opcodes `0x00..0xaf`. The main
dispatcher only executes opcodes `0x01..0xaf`; `0x00` terminates the current
logic loop and `0xfc..0xff` are structural bytes.

All action-table entries through `0xaf` now have local labels. Some labels
remain deliberately implementation-shaped where the handler's state mutation is
clear but the user-facing command name is not.

Coverage audit:

- `tools/disassemble_logic.py` labels every action byte `0x00..0xaf`.
- `0x00` is a structural byte handled by the main interpreter loop, not by the
  normal action dispatcher.
- `0xfc..0xff` are structural bytes and are rejected by the action dispatcher.
- The current condition catalog labels all valid-looking condition-table
  entries `0x00..0x12`; bytes `0x13..0x25` are treated as reserved/invalid in
  this SQ2 build even though the dispatcher only rejects `>= 0x26`.

Examples of action entries:

| Opcode | Label | Handler | Fixed operands | Metadata |
| ---: | --- | ---: | ---: | ---: |
| `0x00` | `end` | `0x5051` | 0 | `0x00` |
| `0x01` | `inc_var` | `0x7355` | 1 | `0x80` |
| `0x02` | `dec_var` | `0x7368` | 1 | `0x80` |
| `0x03` | `assignn` | `0x737b` | 2 | `0x80` |
| `0x0c` | `set_flag` | `0x7484` | 1 | `0x00` |
| `0x14` | `load_logic` | `0x113d` | 1 | `0x00` |
| `0x16` | `call_logic` | `0x125a` | 1 | `0x00` |
| `0x1e` | `load_view` | `0x39b1` | 1 | `0x00` |
| `0x21` | `reset_object_state` | `0x04d9` | 1 | `0x00` |
| `0x23` | `activate_object` | `0x09ea` | 1 | `0x00` |
| `0x25` | `set_object_pos` | `0x7c1a` | 3 | `0x00` |
| `0x29` | `set_object_resource` | `0x3a77` | 2 | `0x00` |
| `0x3f` | `set_global_012d` | `0x7e7c` | 1 | `0x00` |
| `0x51` | `move_object_to` | `0x6ce4` | 5 | `0x00` |
| `0x62` | `load_sound` | `0x510a` | 1 | `0x00` |
| `0x64` | `stop_sound_or_clear_sound_state` | `0x5225` | 0 | `0x00` |
| `0x7a` | `setup_transient_object` | `0x2c7a` | 7 | `0x00` |
| `0x82` | `random_range_to_var` | `0x5009` | 3 | `0x20` |
| `0x93` | `set_object_pos_dirty` | `0x7d77` | 3 | `0x00` |
| `0xa7` | `divn` | `0x744c` | 2 | `0x80` |

This table entry points at the same no-op helper used by action `0x7f`, but the
main interpreter loop handles opcode byte `0x00` before entering the action
dispatcher. Runtime opcode `0x00` stores zero in the current logic record's
resume pointer field `[logic_record+0x06]` and returns from the interpreter.
Later bytes in the same logic payload can still be reached by a jump from
earlier code.

The action dispatcher itself does not use the operand-count byte; handlers
consume operands directly from `SI` and return the next `SI` in `AX`. The table
metadata is used by scanner/debug paths that need to skip or display bytecode.

## Decoded action families

Variable action handlers directly operate on the byte array rooted at
`DS:0x0009`.

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x01` | `inc_var` | `0x7355` | Increment `var[arg0]` unless it is already `0xff`. |
| `0x02` | `dec_var` | `0x7368` | Decrement `var[arg0]` unless it is already `0x00`. |
| `0x03` | `assignn` | `0x737b` | `var[arg0] = arg1` |
| `0x04` | `assignv` | `0x7388` | `var[arg0] = var[arg1]` |
| `0x05` | `addn` | `0x739b` | `var[arg0] += arg1` |
| `0x06` | `addv` | `0x73a8` | `var[arg0] += var[arg1]` |
| `0x07` | `subn` | `0x73bb` | `var[arg0] -= arg1` |
| `0x08` | `subv` | `0x73c8` | `var[arg0] -= var[arg1]` |
| `0x09` | `indirect_assignv` | `0x73db` | `var[var[arg0]] = var[arg1]` |
| `0x0a` | `assign_indirectv` | `0x7405` | `var[arg0] = var[var[arg1]]` |
| `0x0b` | `indirect_assignn` | `0x73f4` | `var[var[arg0]] = arg1` |
| `0xa5` | `muln` | `0x741e` | `var[arg0] *= arg1`; low byte of the product is stored. |
| `0xa6` | `mulv` | `0x7431` | `var[arg0] *= var[arg1]`; low byte of the product is stored. |
| `0xa7` | `divn` | `0x744c` | `var[arg0] /= arg1`; 8-bit quotient is stored. |
| `0xa8` | `divv` | `0x7465` | `var[arg0] /= var[arg1]`; 8-bit quotient is stored. |

Flag action handlers use the same bitfield helpers as condition opcodes
`0x07` and `0x08`.

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x0c` | `set_flag` | `0x7484` | Set flag bit `arg0`. |
| `0x0d` | `clear_flag` | `0x748b` | Clear flag bit `arg0`. |
| `0x0e` | `toggle_flag` | `0x7492` | Toggle flag bit `arg0`. |
| `0x0f` | `set_flag_var` | `0x7499` | Set flag bit `var[arg0]`. |
| `0x10` | `clear_flag_var` | `0x74a8` | Clear flag bit `var[arg0]`. |
| `0x11` | `toggle_flag_var` | `0x74b7` | Toggle flag bit `var[arg0]`. |

Several object/view actions use entries in the 43-byte structure array rooted
at `[0x096b]`. Field names remain provisional; these notes record observed
storage and calls rather than assigning final game-level names.

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x23` | `activate_object` | `0x09ea` | Reads an object index and calls `0x0a06`. The helper validates the object, requires word `[object+0x10] != 0`, copies `[+0x10]` to `[+0x12]`, `[+0x03]` to `[+0x16]`, and `[+0x05]` to `[+0x18]`, sets bits in word `[+0x25]`, and calls several list/graphics helpers. |
| `0x24` | `deactivate_object` | `0x0a8f` | Calls helper `0x0aab` for object `arg0`. If the object has bit `0x0001` set in `[+0x25]`, the helper clears that bit and calls list/graphics helpers to remove or deactivate the object. |
| `0x25` | `set_object_pos` | `0x7c1a` | Set object position-like fields from immediate bytes: `[+0x16] = [+0x03] = arg1`, `[+0x18] = [+0x05] = arg2`. |
| `0x26` | `set_object_pos_var` | `0x7c57` | Set the same fields from variables `var[arg1]` and `var[arg2]`. |
| `0x27` | `get_object_pos` | `0x7ca4` | Store low bytes of object fields `[+0x03]` and `[+0x05]` into `var[arg1]` and `var[arg2]`. |
| `0x28` | `add_object_pos_from_vars` | `0x7ce7` | Reads object index `arg0`, signed deltas from `var[arg1]` and `var[arg2]`, adds those deltas to object fields `[+0x03]` and `[+0x05]`, clamps each field to zero when a negative delta would underflow, sets bit `0x0400` in `[+0x25]`, then calls `0x593a`. |
| `0x29` | `set_object_resource` | `0x3a77` | Resolve object `arg0`, pass immediate `arg1` to helper `0x3ae7`. |
| `0x2a` | `set_object_resource_var` | `0x3aab` | Resolve object `arg0`, pass `var[arg1]` to helper `0x3ae7`. |
| `0x2b` | `set_object_subresource` | `0x3b47` | Resolve object `arg0`, pass immediate `arg1` to helper `0x3bb7`. |
| `0x2c` | `set_object_subresource_var` | `0x3b7b` | Resolve object `arg0`, pass `var[arg1]` to helper `0x3bb7`. |
| `0x2f` | `set_object_derived_resource_2` | `0x3c55` | Resolve object `arg0`, pass immediate `arg1` to helper `0x3ccb`, then clear bit `0x1000` in object word field `[+0x25]`. |
| `0x30` | `set_object_derived_resource_2_var` | `0x3c8c` | Same as `0x2f`, but the helper argument is read from `var[arg1]`. Helper `0x3ccb` selects a derived subresource/loop-like entry, updates object byte `[+0x0e]`, pointer `[+0x10]`, width-like word `[+0x1a]`, and height-like word `[+0x1c]`, then clamps object fields `[+0x03]` and `[+0x05]` against visible bounds and sets bit `0x0400` when it adjusts them. |
| `0x31` | `get_object_resource_loop_count` | `0x3d9f` | Stores byte `[*([object+0x0c])] - 1` into `var[arg1]`. This appears to report a count from the object's loaded resource table. |
| `0x32` | `get_object_field_0e` | `0x3ded` | Stores object byte `[+0x0e]` into `var[arg1]`. |
| `0x33` | `get_object_field_0a` | `0x3e25` | Stores object byte `[+0x0a]` into `var[arg1]`. |
| `0x34` | `get_object_field_07` | `0x3e5d` | Stores object byte `[+0x07]` into `var[arg1]`. |
| `0x35` | `get_object_field_0b` | `0x3e95` | Stores object byte `[+0x0b]` into `var[arg1]`. This opcode was present in the action table but not encountered in the current SQ2 scan. |

Helper `0x3ae7` finds a cached resource record via `0x3979`, stores the
resource payload pointer at object field `[+0x08]`, stores the selected resource
number at byte `[+0x07]`, copies byte `[payload+0x02]` to object byte
`[+0x0b]`, then calls `0x3bb7`. Helper `0x3bb7` validates object field
`[+0x08]`, checks its second argument against byte `[+0x0b]`, then calls
`0x3c1b` and `0x3ccb` to update derived object fields.

Resource and interpreter-control actions observed so far:

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x12` | `switch_room_like` | `0x175c` | Reads immediate `arg0` and calls helper `0x1792`. The helper stops active sound state, restores heap/update-list state through `0x1485`, calls cleanup helpers `0x4482`, `0x707c`, and `0x706d`, resets every object entry's active/resource/frame state, sets `[0x0139] = 1`, stores `0x24` in word `[0x012d]`, copies byte variable 0 from `DS:0x0009` to `DS:0x000a`, writes `arg0` to byte variable 0, clears bytes `DS:0x000d` and `DS:0x000e`, records object 0's current view/resource byte in `DS:0x0019`, calls `0x117d` to load logic `arg0`, optionally loads another logic from `[0x1d12]`, may reposition object 0 from boundary byte `[0x000b]`, sets flag 5, and calls redraw/reinitialization helpers. This is a broad room/state switch action; the final name is still provisional. |
| `0x13` | `switch_room_like_var` | `0x1773` | Same as `0x12`, but the target number is read from `var[arg0]`. |
| `0x14` | `load_logic` | `0x113d` | Reads immediate `arg0`, calls `0x117d`. Helper `0x117d` loads logic resource `arg0` through `0x119a`, then records pair `(0, arg0)` through helper `0x70b1`. |
| `0x15` | `load_logic_var` | `0x1159` | Same as `0x14`, but logic number is `var[arg0]`. |
| `0x16` | `call_logic` | `0x125a` | Reads immediate `arg0`, calls `0x12ae`, and returns zero to the action dispatcher if `0x12ae` returns zero. Helper `0x12ae` preserves the previous current logic pointer at `[0x0981]`, finds or loads the target logic, calls main interpreter `0x293c`, and frees the target record afterward only if it had to be loaded transiently for this call. |
| `0x17` | `call_logic_var` | `0x1280` | Same as `0x16`, but logic number is `var[arg0]`. |
| `0x18` | `load_picture_var` | `0x4a16` | Reads a picture-like resource number from `var[arg0]` and calls loader helper `0x4a3b`. The helper uses directory accessor `0x43d9` and the generic volume reader `0x2e32`, then stores the loaded payload pointer in a linked cache entry rooted at `0x120e`. |
| `0x19` | `prepare_picture_var` | `0x4aaa` | Reads a picture-like resource number from `var[arg0]`, ensures a cached entry exists through `0x4acf`, stores the resource payload pointer at global `0x1377`, and calls helpers `0x6a54`, `0x6445`, and `0x6a8e`. |
| `0x1a` | `show_picture_like` | `0x4b82` | Clears flag 15 through wrapper `0x74d0`, calls helper `0x1f2b` with argument 0, calls `0x5546`, and sets global word `[0x1216] = 1`. This appears to be a picture/display finalization action. |
| `0x1b` | `discard_picture_var` | `0x4baa` | Reads a picture-like resource number from `var[arg0]` and calls helper `0x4bce`, which unlinks or releases the matching cached entry and calls helpers `0x143c`, `0x6a8e`, and `0x14a0`. |
| `0x1c` | `overlay_picture_var` | `0x4b17` | Reads a picture-like resource number from `var[arg0]`, ensures a cached entry exists through helper `0x4b3b`, stores that resource's payload pointer at global `[0x1377]`, calls helpers `0x6a54`, `0x6440`, `0x6a8e`, and `0x6aab`, and clears word `[0x1216]`. Unlike `0x19` (`prepare_picture_var`), this path enters the picture decoder at `0x6440` rather than `0x6445`, so it skips the extra buffer-fill setup performed by `0x6445`. |
| `0x1d` | `show_priority_screen` | `0x731b` | Sets word `[0x1755] = 1`, calls full-screen refresh helper `0x5546`, waits for an event through `0x4618`, calls `0x5546` again, then clears `[0x1755]`. Helper `0x5546` swaps the high and low nibbles of every byte in the logical graphics buffer while `[0x1755] & 1` is set before copying the full screen to the display. The only observed local input phrase reaching this action is `show pri`, where WORDS.TOK word id `0x0028` maps to "show" and word id `0x003f` maps to "pri". |
| `0x1e` | `load_view` | `0x39b1` | Loads or refreshes a view-like resource through helper `0x39f7` using immediate `arg0`. |
| `0x1f` | `load_view_var` | `0x39d0` | Same as `0x1e`, but resource number is `var[arg0]`. |
| `0x20` | `discard_view` | `0x3ecd` | Reads immediate view-like resource number `arg0` and calls helper `0x3f0d`. That helper requires a matching cached view record through `0x3979`, records pair `(7, resource)` through `0x70b1`, clears word `*([0x1000])`, flushes update lists with `0x6a54`, rewinds/frees the resource record with `0x143c`, rebuilds update lists with `0x6a8e`, and calls `0x14a0`. |
| `0x62` | `load_sound` | `0x510a` | Loads a sound-like resource through helper `0x5126` using immediate `arg0`; the helper uses sound directory accessor `0x440d` and builds four internal pointers from the loaded payload. |
| `0x63` | `start_sound_with_flag` | `0x51d3` | Stops any active sound-like state through `0x5234`, reads immediate sound number `arg0` and immediate flag number `arg1`, stores `arg1` in word `[0x126a]`, clears flag `arg1`, locates or loads sound `arg0` through helper `0x50d8`, and starts it through helper `0x7f96`. If the sound cannot be loaded, it reports error code 9 with the sound number. |
| `0x64` | `stop_sound_or_clear_sound_state` | `0x5225` | Calls helper `0x5234`, which clears a pending sound-like state at `[0x1258]`, sets flag `[0x126a]`, and calls `0x080af` when that state was active. |

QEMU fixture `load_view_var_allows_following_draw` validates the variable view
load path by starting without the usual preloaded view 11, setting a variable to
11, executing `0x1f`, and then successfully drawing that view.

Room/state switch helper `0x1792`, reached by actions `0x12` (`switch_room_like`) and
`0x13` (`switch_room_like_var`),
resets all object records from `[0x096b]` to `[0x096d]`. For each 43-byte
record it clears active/update bits `0x0001` and `0x0040`, sets bit `0x0010`,
clears fields `+0x08`, `+0x10`, `+0x14`, `+0x1e`, `+0x1f`, and `+0x20`, and
stores `1` in bytes `+0x00` and `+0x01`. After loading the destination logic,
it interprets byte variable `[0x000b]` as an entry boundary for object 0:
`1` places Y at `0xa7`, `2` places X at `0`, `3` places Y at `0x25`, and `4`
places X at `0xa0 - object_width`; the byte is then cleared.

Additional object-state actions:

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x21` | `reset_object_state` | `0x04d9` | Calls helper `0x04f5` for object `arg0`. If object word `[+0x25]` does not have bit `0x0040`, the helper sets `[+0x25] = 0x0070` and clears bytes `[+0x22]`, `[+0x23]`, and `[+0x21]`. |
| `0x22` | `clear_all_object_bits` | `0x053d` | Iterates all 43-byte object entries from `[0x096b]` to `[0x096d]` and clears bits `0x0041` in word field `[+0x25]`. |
| `0x2d` | `set_object_bit_2000` | `0x497b` | Sets object bit `0x2000` in `[+0x25]`. |
| `0x2e` | `clear_object_bit_2000` | `0x49a3` | Clears object bit `0x2000` in `[+0x25]`. |
| `0x3a` | `clear_object_bit_0010` | `0x6ac8` | Calls helper `0x6b44`, which clears object bit `0x0010` if it was set and wraps the update in helpers `0x6a54` and `0x6a8e`. |
| `0x3b` | `set_object_bit_0010` | `0x6af0` | Calls helper `0x6b62`, which sets object bit `0x0010` if it was clear and wraps the update in helpers `0x6a54` and `0x6a8e`. |
| `0x3c` | `refresh_object_helper` | `0x6b18` | Calls helpers `0x6a54`, `0x6a8e`, and `0x6aab` for object `arg0`, with no direct object field writes in the handler itself. |
| `0x3d` | `set_object_bit_0008` | `0x7e94` | Sets object bit `0x0008` in `[+0x25]`. |
| `0x3e` | `clear_object_bit_0008` | `0x7eb9` | Clears object bit `0x0008` in `[+0x25]`. |
| `0x3f` | `set_global_012d` | `0x7e7c` | Stores immediate `arg0` as a word at `DS:0x012d`. |
| `0x40` | `set_object_bit_0100` | `0x7e0d` | Sets bit `0x0100` in object word field `[+0x25]`. QEMU validates that this makes a priority-14 object on a full control-class-2 picture remain visible but unable to move from `(20,80)` to `(50,80)`. |
| `0x41` | `set_object_bit_0800` | `0x7e32` | Sets bit `0x0800` in object word field `[+0x25]`. QEMU validates that this makes a priority-14 object on a full control-class-3 picture remain visible but unable to move from `(20,80)` to `(50,80)`. |
| `0x42` | `clear_object_bits_0900` | `0x7e57` | Clears object bits `0x0100` and `0x0800` by ANDing `[+0x25]` with `0xf6ff`. QEMU validates that clearing after `0x40` or `0x41` restores movement to `(50,80)` on the same synthetic control-class pictures. |
| `0x43` | `set_object_bit_0200` | `0x479f` | Sets bit `0x0200` in object word field `[+0x25]`. |
| `0x44` | `clear_object_bit_0200` | `0x47c7` | Clears bit `0x0200` in object word field `[+0x25]`. |
| `0x45` | `object_distance_to_var` | `0x47ef` | Reads two object indices and a destination variable index. If either object lacks bit `0x0001`, stores `0xff` in the destination variable. Otherwise computes `abs(y0-y1) + abs((x0 + width0/2) - (x1 + width1/2))`, caps the result at `0xfe`, and stores it in the destination variable. |
| `0x46` | `clear_object_bit_0020` | `0x6c97` | Clears object bit `0x0020` in `[+0x25]`. |
| `0x47` | `set_object_bit_0020` | `0x6cbc` | Sets object bit `0x0020` in `[+0x25]`. |
| `0x48` | `set_object_field_23_mode0` | `0x6b82` | Sets object byte `[+0x23] = 0` and sets bit `0x0020` in `[+0x25]`. |
| `0x49` | `set_object_field_23_mode1` | `0x6bae` | Sets object byte `[+0x23] = 1`, sets bits `0x1030` in `[+0x25]`, stores immediate `arg1` in byte `[+0x27]`, and clears flag `arg1`. |
| `0x4a` | `set_object_field_23_mode3` | `0x6beb` | Sets object byte `[+0x23] = 3` and sets bit `0x0020` in `[+0x25]`. |
| `0x4b` | `set_object_field_23_mode2` | `0x6c17` | Sets object byte `[+0x23] = 2`, sets bits `0x1030` in `[+0x25]`, stores immediate `arg1` in byte `[+0x27]`, and clears flag `arg1`. |
| `0x4c` | `set_object_field_1f_var` | `0x6c54` | Stores `var[arg1]` in object byte `[+0x1f]` and copies the same byte to object byte `[+0x20]`. These bytes are the reload and current countdown for `code.object.frame_timer_update`. |
| `0x4d` | `clear_object_fields_21_22` | `0x6ec8` | Clears object bytes `[+0x21]` and `[+0x22]`; if the object is the first object entry, also clears byte `DS:0x000f` and word `[0x0139]`. |
| `0x4e` | `clear_object_field_22_and_global` | `0x6f05` | Clears object byte `[+0x22]`; if the object is the first object entry, clears byte `DS:0x000f` and sets word `[0x0139] = 1`. A QEMU movement probe validates the byte `[+0x22]` effect by starting random motion with `0x54`, immediately executing `0x4e`, and observing that the object remains at its starting position. |
| `0x4f` | `set_object_field_1e_var` | `0x6f3e` | Stores `var[arg1]` in object byte `[+0x1e]`. |
| `0x50` | `set_object_field_01_var` | `0x6f7c` | Stores `var[arg1]` in object byte `[+0x01]` and clears object byte `[+0x00]`. |

QEMU probes validate the observable flag-clearing side effect of `0x49` and
`0x4b`: each clears its flag operand before following bytecode tests that the
flag is no longer set. Separate dispatch-smoke probes show `0x48` and `0x4a`
execute and return to following bytecode; those probes do not directly observe
the hidden object byte `+0x23`.

Static analysis now ties `0x46..0x4c` to the frame-cycling path. Per-cycle
helper `code.object.frame_timer_update` (`0x0563`) scans active objects with
`(flags & 0x0051) == 0x0051`; when bit `0x0020` is set, byte `+0x20` is
nonzero, and decrementing `+0x20` reaches zero, it calls
`code.object.advance_frame_by_mode` (`0x48b3`) and reloads `+0x20` from
`+0x1f`. The advance helper treats `+0x23` as a frame mode: mode 0 loops
forward, mode 1 advances forward and completes at the last frame, mode 2 steps
backward until it reaches frame 0 and completes, and mode 3 loops backward.
Completion in modes 1 and 2 sets flag `+0x27`, clears bit `0x0020`, clears
direction byte `+0x21`, and resets `+0x23` to 0. Actions `0x49` and `0x4b`
also set bit `0x1000`; the first advance callback after setup clears that bit
and returns without changing frame.

QEMU movement batch `frame_timer_001` validates the visible mode-1 path: after
`0x4c` seeds the interval and `0x49` starts mode 1, view 11/group 0 advances
from frame 0 to frame 1. The same batch validates that `0x46` prevents the
advance by clearing bit `0x0020`, and `0x47` restores the advance when executed
after `0x46`.

QEMU movement batch `frame_timer_modes_002` validates the remaining visible
frame-mode actions: `0x48` mode 0 wraps view 11/group 0 from frame 1 to frame
0, `0x4b` mode 2 moves from frame 1 to frame 0 and stops, and `0x4a` mode 3
wraps backward from frame 0 to frame 1. The looping-mode fixtures stop the
timer with `0x46` after a bytecode guard observes the expected frame through
`0x32`.

Movement probe `move_collision_clear_skip_bit_blocks_again` validates `0x44` by
first setting collision-skip bit `0x0200` with `0x43`, then clearing it with
`0x44`, and observing that the default object-object collision stop returns.

QEMU horizon probes validate `0x3f`, `0x3d`, and `0x3e` together. With
`0x3f` setting `[0x012d] = 100`, ordinary placement at baseline `80` clamps to
baseline `101`. Setting bit `0x0008` with `0x3d` keeps the object at baseline
`80`, and clearing the bit with `0x3e` restores the clamp.

Movement-mode actions have compact setup contracts but richer per-cycle
semantics, so the entry points are summarized in a table and the state machines
are described below it.

| Opcode | Label | Handler | Setup contract |
| ---: | --- | ---: | --- |
| `0x51` | `move_object_to` | `0x6ce4` | Starts targeted object movement. Operand 0 is the object index, operand 1 is target X, operand 2 is target Y, operand 3 is an optional step-size override, and operand 4 is the completion flag. |
| `0x52` | `move_object_to_var` | `0x6d61` | Same contract as `0x51`, but target X, target Y, and optional step-size override are read through variables while the object index and completion flag remain immediate operands. |
| `0x53` | `approach_first_object_until_near` | `0x6e02` | Starts autonomous movement for object operand 0 toward the first object entry. Operand 1 is a proximity threshold or step floor, and operand 2 is a completion flag. |
| `0x54` | `start_random_motion` | `0x6e68` | Starts autonomous random movement for object operand 0. If the object is the first object entry, sets `[0x0139] = 0`; then stores `[+0x22] = 1` and sets object bit `0x0010`. |

Actions `0x51` and `0x52` share the same targeted-movement state machine.

The handler sets object byte `[+0x22] = 3`, stores target X/Y in `[+0x27]` and
`[+0x28]`, copies old step size `[+0x1e]` to `[+0x29]`, stores the completion
flag in `[+0x2a]`, clears that flag, sets object bit `0x0010`, and calls
helper `0x1672`. If operand 3 is nonzero, it temporarily replaces `[+0x1e]`
with that step size; completion helper `0x16b9` restores `[+0x1e]` from
`[+0x29]`, sets the completion flag through `0x74c6`, clears `[+0x22]`, and
clears ego direction byte `[0x000f]` when the object is object 0.

Helper `0x1672` computes the initial direction byte `[+0x21]` from current
position `[+0x03]`/`[+0x05]` to target `[+0x27]`/`[+0x28]` using step size
`[+0x1e]`. The direction lookup table at `DS:0x0a85` is:

```text
target above:  8 1 2
target level:  7 0 3
target below:  6 5 4
               left near right
```

The center value is zero, so an object already within one step of both target
coordinates completes immediately.

QEMU probes with generated logic resources confirm two valid ways this target
mode can complete. A script can reissue `0x51` each cycle while the completion
flag is clear; that matched QEMU for reachable horizontal and vertical targets,
and for unreachable right/bottom targets that complete at the movement clamp. A
one-shot `0x51` setup can also complete without script reissue when object byte
`+0x01` is set to `1`, because the pre-movement dispatcher path
`0x067a -> 0x1672` recomputes the direction and detects arrival.

For action `0x53`, the setup handler sets object byte `[+0x22] = 2`; stores `max(operand1,
object[+0x1e])` in `[+0x27]`; stores the completion flag number in `[+0x28]`;
clears that flag; stores sentinel `0xff` in `[+0x29]`; and sets object bit
`0x0010`. The per-cycle helper at `0x0b36` computes the object's horizontal
center and the first object's horizontal center, calls direction helper
`0x16ed(object_center_x, object_y, first_object_center_x, first_object_y,
object[+0x27])`, and writes the returned direction to `[+0x21]` when its local
delay permits. If the returned direction is zero, the object is already within
the threshold: the helper clears `[+0x21]` and `[+0x22]` and sets the completion
flag through `0x74c6`. If object bit `0x4000` says the object did not move in
the last position comparison, the helper temporarily chooses a random nonzero
direction and computes a retry delay in `[+0x29]` before returning to the direct
approach direction.

QEMU validates the direct autonomous mode-2 path with object 1 approaching
object 0: with step `5`, countdown byte `+0x01 = 1`, and threshold `35`, object
1 stops at `(50,80)` when object 0 is at `(80,80)`. An exploratory threshold
`25` probe landed at `(60,75)`, consistent with the source path that enters
stuck recovery after a blocked or stationary comparison.

For action `0x54`, the per-cycle helper at `0x3f5a` decrements `[+0x27]` as a
countdown; when it reaches zero, or when object bit `0x4000` reports no
movement, it chooses a random direction `0..8` via helper `0x3fa3`, stores it
in `[+0x21]`, mirrors it to byte `[0x000f]` for the first object, and reseeds
`[+0x27]` to a random delay in the range `6..50`.

A QEMU property probe validates this path without assuming a deterministic final
coordinate: after setting step `5`, countdown byte `+0x01 = 1`, and starting
`0x54`, the object rendered exactly at a valid final position. In the recorded
run the final position was `(140,112)`.

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x55` | `stop_motion_mode` | `0x6ea1` | Stops the autonomous motion mode for object operand 0 by clearing object byte `[+0x22]`. Unlike `0x4d` (`clear_object_fields_21_22`) it does not clear direction byte `[+0x21]`, and unlike `0x4e` (`clear_object_field_22_and_global`) it does not update the first-object globals. |
| `0x56` | `set_object_field_21_var` | `0x6fbe` | Stores `var[arg1]` in object byte `[+0x21]`. |
| `0x57` | `get_object_field_21` | `0x6ffc` | Stores object byte `[+0x21]` into `var[arg1]`. |
| `0x58` | `set_object_bit_0002` | `0x7b9c` | Sets bit `0x0002` in object word field `[+0x25]`. QEMU validates that this bypasses the rectangle-boundary crossing stop configured by `0x5a`; the object reaches `(50,80)` instead of stopping at `(30,80)`. |
| `0x59` | `clear_object_bit_0002` | `0x7bc1` | Clears bit `0x0002` in object word field `[+0x25]`. QEMU validates that clearing after `0x58` restores the rectangle-boundary crossing stop at `(30,80)`. |
| `0x83` | `clear_global_0139` | `0x702f` | Sets global word `[0x0139] = 0`. |
| `0x84` | `set_global_0139_and_clear_object0_field_22` | `0x7041` | Sets global word `[0x0139] = 1` and clears byte `[+0x22]` on the first object entry. |
| `0x85` | `display_object_diagnostics_var` | `0x72b5` | Reads an object index from `var[arg0]`, gathers object fields `[+0x03]`, `[+0x05]`, `[+0x1a]`, `[+0x1c]`, `[+0x24]`, and `[+0x1e]`, formats them with string template `DS:0x1713` through helper `0x2374`, and displays the result through `0x1ce8`. |

In local SQ2 data, the template at `DS:0x1713` is:

```text
Object %d:
x: %d  xsize: %d
y: %d  ysize: %d
pri: %d
stepsize: %d
```

The single observed local use is in logic 99. The script accepts parsed words
`object` or `sp`, prompts with message 7 (`object #:`), stores the number in
variable 64, and then executes this action. This makes `0x85` a developer or
diagnostic object-inspection command, and it independently confirms that object
fields `[+0x03]`, `[+0x05]`, `[+0x1a]`, `[+0x1c]`, `[+0x24]`, and `[+0x1e]`
are displayed as X, Y, width, height, priority/control, and step size.

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x93` | `set_object_pos_dirty` | `0x7d77` | Sets object fields `[+0x03] = arg1` and `[+0x05] = arg2`, sets bit `0x0400` in `[+0x25]`, then calls helper `0x593a`. |
| `0x94` | `set_object_pos_dirty_var` | `0x7dba` | Same broad shape as `0x93`, but fields `[+0x03]` and `[+0x05]` are loaded from `var[arg1]` and `var[arg2]`. It also sets object bit `0x0400` and calls helper `0x593a`. |

Actions that update object byte `[+0x24]`:

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x36` | `set_object_field_24` | `0x7a80` | Sets bit `0x0004` in object word field `[+0x25]` and writes immediate `arg1` to byte `[+0x24]`. |
| `0x37` | `set_object_field_24_var` | `0x7b08` | Same as `0x36`, but writes `var[arg1]` to byte `[+0x24]`. |
| `0x38` | `clear_object_bit_0004` | `0x7ab0` | Clears bit `0x0004` in object word field `[+0x25]`. A QEMU probe confirms that this stops using the fixed byte `[+0x24]`; a view placed at baseline `80` then derives priority `7` and draws over a control-6 background. |
| `0x39` | `get_object_field_24` | `0x7ad5` | Stores object byte `[+0x24]` into `var[arg1]`. |

Message-display actions use the current logic resource's message table through
helper `0x21f0`.

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x65` | `display_message` | `0x1c06` | Resolve message `arg0` with `0x21f0`, then pass the string pointer to display helper `0x1ce8`. |
| `0x66` | `display_message_var` | `0x1c29` | Same as `0x65`, but message number is `var[arg0]`. |
| `0x67` | `display_formatted_message` | `0x2250` | Calls setup helper `0x2b28`, passes immediate operands `arg0` and `arg1` to helper `0x2b0d`, resolves message `arg2`, copies or formats it into a 1000-byte stack buffer with helper `0x1f54` and maximum `0x28`, sends the resulting string to formatter/display helper `0x2390`, then calls cleanup helper `0x2b4f`. This appears to be a positioned or configured formatted-message display action. |
| `0x68` | `display_formatted_message_var` | `0x22a7` | Same as `0x67`, but all three operands are read through variables. |
| `0x97` | `display_message_configured` | `0x1c54` | Reads immediate message number `arg0`, then reads three additional bytes into globals `[0x0d0b]`, `[0x0d0d]`, and `[0x0d09]` before resolving and displaying the message; the globals are reset to `0xffff` afterward. |
| `0x98` | `display_message_configured_var` | `0x1c71` | Same as `0x97`, but message number is `var[arg0]`. |

Menu/list-like UI actions use a circular list rooted at word globals
`[0x1d2c]`, `[0x1d2e]`, and `[0x1d30]`. The final user-level names remain
provisional; the observed structures look like a top-level list of headings
with per-heading circular sublists of selectable items.

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x9c` | `add_menu_heading_like` | `0x911d` | Resolves message `arg0`, allocates an 18-byte node through `0x13d6`, links it into the top-level circular list rooted at `[0x1d2c]`, stores the message pointer at `[node+0x04]`, stores the current horizontal/text position from `[0x1d24]` at `[node+0x08]`, marks `[node+0x0a] = 1`, clears its item-list pointer at `[node+0x0c]`, advances `[0x1d24]` by the message width plus one using helper `0x4d99`, clears `[0x1d30]`, and resets `[0x1d26] = 1`. |
| `0x9d` | `add_menu_item_like` | `0x91cf` | Resolves message `arg0`, reads immediate item id `arg1`, allocates a 14-byte node, links it into the current heading's circular item list at `[current_heading+0x0c]`, stores the message pointer at `[node+0x04]`, stores a 1-based row/order at `[node+0x06]`, stores a column-like value at `[node+0x08]`, marks `[node+0x0a] = 1`, stores item id `arg1` at `[node+0x0c]`, and increments `[current_heading+0x10]`. |
| `0x9e` | `finalize_menu_like` | `0x92ba` | Finalizes the current menu/list setup: if the current heading has no item list, clears `[heading+0x0a]`; calls helper `0x1476`; sets current heading `[0x1d2e]` to the list root `[0x1d2c]`; sets current item `[0x1d30]` from `[heading+0x0c]`; and sets `[0x1d2a] = 1`, which makes later `0x9c`/`0x9d` additions no-op. |
| `0x9f` | `enable_menu_item_like` | `0x92ee` | Calls helper `0x935f(arg0, 1)`. The helper walks all active heading/item lists, finds item nodes whose id at `[node+0x0c]` equals `arg0`, and writes `[node+0x0a] = 1`. |
| `0xa0` | `disable_menu_item_like` | `0x9340` | Calls helper `0x935f(arg0, 0)`, clearing `[node+0x0a]` for matching item ids. |
| `0xa1` | `mark_menu_if_flag_0e` | `0x93b1` | Tests flag `0x0e` through helper `0x74e4`; if set, stores word `[0x1d22] = 1`. Its role is likely tied to the same menu/list UI state, but no direct list traversal occurs in this handler. |

Text-window and input-line actions:

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x69` | `clear_text_rect` | `0x7714` | Reads immediates `arg0`, `arg1`, and `arg2`; transforms `arg2` through helper `0x78ad`; then calls helper `0x2b78(arg0, arg1, transformed_arg2)`. Helper `0x2b78` is a wrapper around BIOS `int 10h` scroll/clear-window service `AH=0x06`, using row/column bounds and an attribute byte. |
| `0x9a` | `clear_text_rect_bounds` | `0x7753` | Reads five immediates. The first four are passed as the top row, left column, bottom row, and right column to helper `0x2bc4`; the fifth is transformed through helper `0x78ad` and passed as the text attribute. Helper `0x2bc4` saves the current cursor, calls BIOS `int 10h` scroll/clear-window service `AH=0x06` with those bounds, then restores the cursor. |
| `0x6a` | `enable_text_attr_mode_1757` | `0x76ca` | Calls prompt/input cleanup helper `0x382e`, sets byte `[0x1757] = 1`, derives text attributes through `0x77d5` using globals `[0x05cd]` and `[0x05cf]`, calls helper `0x9803`, then clears or fills a text rectangle through `0x2b78`. This appears to enable an alternate text-attribute mode. |
| `0x6b` | `disable_text_attr_mode_1757` | `0x7702` | Calls prompt/input cleanup helper `0x382e`, then helper `0x78cb`, which clears byte `[0x1757]`, recomputes text attributes from `[0x05cd]` and `[0x05cf]`, calls helper `0x9806`, redraws the status-line-like area through `0x34bd`, and refreshes the input-line-like area through `0x38d7`. |
| `0x6c` | `set_input_prompt_char` | `0x38b4` | Resolves current-logic message `arg0` through `0x21f0` and stores the first byte of that message in `[0x05d7]`. Helpers `0x37f7`, `0x382e`, and `0x38d7` test `[0x05d7]` while drawing or erasing the prompt/input marker, so this appears to configure the input prompt character. |
| `0x6d` | `set_text_window_pair` | `0x77af` | Reads immediates `arg0` and `arg1`, then calls helper `0x77d5(arg0, arg1)`. That helper stores derived values in globals `[0x05d1]`, `[0x05cd]`, and `[0x05cf]` using helpers `0x7803`, `0x78a1`, and `0x78ad`. |
| `0x6e` | `shake_screen_like` | `0x7a00` | Reads an immediate count into `CL` and performs a display-shake-like loop. Depending on display-mode globals `[0x1130]` and `[0x112e]`, it either dispatches to helpers `0x99b8`, `0x9be3`, or `0x9916`, or directly writes CRT controller registers at ports `0x3d4/0x3d5`, using bytes at `0x177a` and global offset bytes `[0x1365]` and `[0x1779]`. |
| `0x6f` | `set_input_line_config` | `0x78f0` | Reads immediates `arg0`, `arg1`, and `arg2`; stores `arg0` in `[0x05dd]`, `arg0 + 0x15` in `[0x05df]`, `arg1` in `[0x05d5]`, and `arg2` in `[0x05db]`. It also computes `[0x1379]` from `arg0`: normally `arg0 << 3`, but in display mode `[0x1130] == 2` it stores `arg0 * 6` for values 0 or 1, and clamps larger values to 6. Nearby redraw helpers use these globals for the input-line/status text areas, so the user-level name remains provisional. |
| `0x70` | `show_status_line_like` | `0x3547` | Sets word `[0x05d9] = 1` and calls helper `0x34bd`, which redraws a status-line-like text area using helpers `0x2b28`, `0x7989`, `0x2ba6`, `0x2b0d`, `0x2390`, `0x79c3`, and `0x2b4f`. |
| `0x71` | `hide_status_line_like` | `0x355c` | Sets word `[0x05d9] = 0`, then calls helper `0x2ba6([0x05db], 0)` to clear the associated text area. |
| `0x72` | `set_string_slot_from_message` | `0x0d37` | Computes destination `0x020d + arg0 * 0x28`, resolves current-logic message `arg1`, and copies up to `0x28` bytes into that fixed-size string slot through helper `0x4de8`. |
| `0x73` | `prompt_string_to_slot` | `0x0c44` | Reads fixed string slot `arg0`, message number `arg1`, row-like byte `arg2`, column-like byte `arg3`, and max-length byte `arg4`. It clears the destination string slot, optionally positions text with `0x2b0d(arg2, arg3)` when `arg2 < 0x19`, displays the resolved current-logic message, accepts edited input through helper `0x0da9`, then restores the input-line/status display as needed. The accepted length is `min(arg4 + 1, 0x28)`. |
| `0x74` | `set_string_slot_from_table` | `0x0d70` | Computes destination `0x020d + arg0 * 0x28`, reads a word pointer from `DS:0x0c8f + arg1 * 2`, and copies up to `0x28` bytes from that pointer into the string slot through helper `0x4de8`. In the static SQ2 `AGIDATA.OVL`, the sampled table entries at `0x0c8f` are zero-filled and this opcode was not encountered in the current local logic scan, so the label is provisional. |
| `0x75` | `parse_string_slot` | `0x1958` | Clears flags 2 and 4, reads a string-slot index `arg0`, and if `arg0 < 12` parses fixed string slot `0x020d + arg0 * 0x28` through helper `0x18ac`. The parser normalizes the string, looks words up in `WORDS.TOK`, and fills parsed-word tables used by condition `0x0e` (`input_word_sequence`). |
| `0x76` | `prompt_number_to_var` | `0x71ed` | Displays current-logic message `arg0` as a prompt, accepts/edits up to four characters through helper `0x0da9`, parses the resulting buffer as a decimal number through helper `0x4e8d`, and stores the low byte in `var[arg1]`. It has two display paths: one using text helpers `0x2b0d`, `0x1f54`, `0x2390`, `0x37f7`, and `0x38d7`, and another using helpers `0x9c52` and `0x9d93` when display mode `[0x1130] == 2` and `[0x0d0f] == 0`. |
| `0x77` | `disable_input_line_like` | `0x386f` | Sets word `[0x05d3] = 0`; unless display mode `[0x1130] == 2`, it calls helper `0x382e` and clears a text area through `0x2ba6([0x05d5], 0)`. This disables or hides an input-line-like display. |
| `0x78` | `enable_input_line_like` | `0x3898` | Sets word `[0x05d3] = 1`; unless display mode `[0x1130] == 2`, calls helper `0x38d7` to redraw the input-line-like display. |
| `0x89` | `refresh_input_line` | `0x3753` | If the input line is enabled through word `[0x05d3]`, refreshes the input-line display. In display mode `[0x1130] == 2` with word `[0x0d0f] == 0`, it displays the string at `0x1e2e` ("ENTER COMMAND") through the alternate display helpers, clears or rewrites the current input character byte `[0x001c]`, and passes that byte to helper `0x3652`. In other modes it calls helper `0x37a5`, which appends bytes from the buffer/string at `0x0fce` into the visible input buffer `0x0fa4` until the input length word `[0x0ff8]` reaches that string's length. |
| `0x8a` | `erase_input_line` | `0x3726` | Erases the visible input-line buffer by repeatedly passing byte `0x08` to helper `0x3652` while word `[0x0ff8]` is nonzero. In display mode `[0x1130] == 2`, it skips the erase loop when word `[0x0d0f] == 0`. |
| `0xa3` | `set_global_0d0f` | `0x3939` | Sets word `[0x0d0f] = 1`; helper `0x3652` uses this global while computing input-line width and redraw behavior. |
| `0xa4` | `clear_global_0d0f` | `0x394b` | Clears word `[0x0d0f]`. |
| `0xa9` | `close_text_window_state` | `0x1f2b` | If word `[0x0d1d]` is nonzero, calls helper `0x560c([0x0d23], [0x0d25])`, which restores a saved display rectangle. It then clears words `[0x0d0f]` and `[0x0d1d]`. This is used both as a no-operand action and as an internal cleanup helper after message/window paths. |

Resource/table actions outside the main object table:

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x5a` | `set_rect_bounds_0131` | `0x7b4e` | Sets word `[0x013d] = 1` and stores four immediate operands as words at `[0x0131]`, `[0x0133]`, `[0x0135]`, and `[0x0137]`. Helper `0x7be6` later tests whether an `(x,y)` pair lies strictly inside those bounds. |
| `0x5b` | `clear_rect_bounds_0131` | `0x7b8a` | Clears word `[0x013d]`. |
| `0x5c` | `set_entry_0971_marker_ff` | `0x7538` | Resolves a 3-byte entry from the table rooted at `[0x0971]` using immediate index `arg0`, validates it against end pointer `[0x0973]`, and stores byte `[entry+0x02] = 0xff`. Invalid indices report error code `0x17` through helper `0x3fe8`. |
| `0x5d` | `set_entry_0971_marker_ff_var` | `0x7554` | Same as `0x5c`, but the entry index is read from `var[arg0]`. |
| `0x5e` | `clear_entry_0971_marker` | `0x7570` | Resolves a 3-byte entry from the table rooted at `[0x0971]` using immediate index `arg0` and stores byte `[entry+0x02] = 0`. |
| `0x5f` | `set_entry_0971_marker_from_var` | `0x758c` | Resolves a table entry using immediate index `arg0`, then stores `var[arg1]` in byte `[entry+0x02]`. |
| `0x60` | `set_entry_0971_marker_from_var_var` | `0x75b7` | Resolves a table entry using index `var[arg0]`, then stores `var[arg1]` in byte `[entry+0x02]`. |
| `0x61` | `get_entry_0971_marker_to_var` | `0x75e2` | Resolves a table entry using index `var[arg0]`, then stores byte `[entry+0x02]` into `var[arg1]`. |
| `0x7c` | `show_inventory_selection` | `0x31d8` | Builds a temporary 8-byte-per-row list from the 3-byte table rooted at `[0x0971]`, including only entries whose marker byte `[entry+0x02]` is `0xff`. For each included entry it stores the original table index, an item-name pointer computed as `[0x0971] + word[entry+0x00]`, and a two-column row/column position. It displays the header string at `0x0f26` ("You are carrying:"), a fallback string at `0x0f1e` ("nothing") when no rows exist, and either a selection prompt at `0x0f38` or a noninteractive return prompt at `0x0f5d` depending on flag 13. In interactive mode Enter writes the selected table index to byte variable `[0x22]`; Escape writes `0xff`. |
| `0x79` | `map_key_event` | `0x4c3d` | Combines `arg0` and `arg1` into a little-endian key/event word, scans up to 39 four-byte slots rooted at `0x0145` for an empty first word, and stores the combined word at slot offset `+0` and `arg2` at slot offset `+2`. Helper `0x4566` later uses this table to convert matching type-1 event records into type-3 records carrying the mapped value. |
| `0x81` | `display_view_resource_text_like` | `0x5ebf` | Displays or previews a view-like resource selected by immediate `arg0`. Helper `0x5edb` ensures the resource is loaded, temporarily sets `[0x0f18] = 1` around `0x39f7`, builds a temporary object-like record through `0x3ae7`, may render/cache it through helpers `0x9097`, `0x9db0`, `0x9db6`, and `0x5762` if enough memory is available, displays a string pointer derived from the loaded resource through `0x1ce8`, then cleans up any temporary allocation. |
| `0xa2` | `display_view_resource_text_like_var` | `0x5e9b` | Same as `0x81`, but the resource number is read from `var[arg0]`. The action table metadata byte is `0x01`, but the handler itself clearly performs the variable lookup. |
| `0x99` | `discard_view_var` | `0x3ee9` | Same helper path as `0x20` (`discard_view`), but the view-like resource number is read from `var[arg0]`. |

Interpreter/session control actions:

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x86` | `confirm_and_restart_like` | `0x027f` | Stops active sound state through helper `0x5234`, reads immediate `arg0`, and if `arg0 == 1` calls helper `0x02ae` immediately. Otherwise it displays string pointer `0x05e3` through `0x1ce8` and calls `0x02ae` only if the display helper returns 1. Helper `0x02ae` calls `0x8275` and then `0x00ae(0)`. This is a confirmation-gated restart/exit-like action; the final user-level name is still provisional. |
| `0x87` | `show_heap_status` | `0x14bd` | Formats a diagnostic heap/status message into a 100-byte stack buffer with helper `0x2374`, then displays it with `0x1ce8`. The format string at `0x0a19` is `heapsize: %u`, `now: %u  max: %u`, `rm.0, etc.: %u`, and `max script: %d`. The values are derived from globals `[0x0a55]`, `[0x0a57]`, `[0x0a59]`, `[0x0a5b]`, `[0x0a5f]`, and `[0x170f]`. |
| `0x88` | `pause_game_message` | `0x0257` | Sets word `[0x0615] = 1`, calls helper `0x4482`, stops sound through `0x5234`, displays the fixed message at `0x0c0d` ("Game paused. Press Enter to continue."), then clears `[0x0615]`. |
| `0x8b` | `calibrate_joystick` | `0x613c` | Initializes joystick-related globals `[0x15c5]` and `[0x15c7]` to `0xffff`, calls helper `0x63be`, and if joystick axes/state globals `[0x15c1]` and `[0x15c3]` are nonzero, displays the message at `0x1549`, which starts "Please center your joystick." It waits for Enter to continue or Escape to cancel. On acceptance it closes any active text window, computes min/max centered bounds around `[0x15c1]` and `[0x15c3]` into `[0x15c9]`, `[0x15cd]`, `[0x15cb]`, and `[0x15cf]`, then repeatedly calls helper `0x6425` while calibration records at `0x1531` or `0x153d` remain active. It finishes by calling helper `0x4482`. |
| `0x80` | `confirm_restart_game` | `0x2472` | Stops active sound state, clears the prompt/input line, and either proceeds immediately if flag 16 is set or displays the confirmation text at `0x0adb` ("Press ENTER to restart the game... Press ESC to continue this game."). On confirmation it calls input/display cleanup helper `0x3726`, preserves flag 9, resets heap/update-list state through `0x1485`, calls helpers `0x0fa5` and `0x30d6`, sets flag 6, restores flag 9 if it had been set, clears timer/event words `[0x0129]` and `[0x012b]`, reloads logic `[0x1d12]` if configured, and calls menu/list refresh helper `0x930e`. It then redraws the input prompt through `0x37f7`. When restart is accepted it returns zero to the dispatcher. |
| `0x7d` | `save_game_state` | `0x2753` | Save-game-state path. It asks helper `0x85e5(0x73)` for a selected slot/path, optionally displays the confirmation text at `0x0db6`, creates file `0x1c8c` through DOS wrapper `0x5cad`, writes a 31-byte description/header from `0x1c6c`, then writes several length-prefixed memory blocks through helper `0x28c6`. On write failure it closes and deletes the file, displays the error text at `0x0e46`, and returns through cleanup helper `0x1f2b`. |
| `0x7e` | `restore_game_state` | `0x2512` | Restore-game-state path. It asks helper `0x85e5(0x72)` for a selected slot/path, optionally displays the confirmation text at `0x0d34`, opens file `0x1c8c` through DOS wrapper `0x5cce`, seeks past a 31-byte description/header, then reads several length-prefixed memory blocks through helper `0x26b0`. On read failure it displays the error text at `0x0d87` and calls `0x02ae`; on success it refreshes display/resource state through helpers including `0x681c`, `0x4c23`, `0x30d6`, and `0x930e`. |
| `0x8e` | `set_global_0141_and_refresh` | `0x716a` | Stores immediate `arg0` as word `[0x0141]`, then wraps refresh helper `0x707c` with calls to `0x6a54` and `0x6a8e`. |
| `0x8c` | `toggle_display_mode_bit` | `0x794c` | If word `[0x112e] == 0`, byte variable 0 is nonzero, and display mode word `[0x1130]` is neither 2 nor 3, calls helper `0x1364`, toggles bit 0 of word `[0x1130]`, and refreshes display state through helpers `0x2b28`, `0x5528`, `0x2b4f`, and `0x681c`. This appears to switch an available display mode or display attribute variant; the hardware-facing meaning of `[0x1130]` still needs dynamic confirmation. |
| `0x8f` | `verify_game_signature` | `0x0e7e` | Reads immediate message number `arg0`, resolves that current-logic message through `0x21f0`, copies up to seven bytes into absolute buffer `0x0002` with `0x4de8`, then calls helper `0x5b49`. Helper `0x5b49` compares bytes at `0x0002` against an embedded `SQ2\0` string at code offset `0x5b6c`, calling helper `0x02ae` on the first mismatch. The one observed local use is in logic 140 immediately before action `0x6f` (`set_input_line_config`), consistent with a game-signature/configuration guard. |
| `0x90` | `append_message_to_log_file` | `0x828f` | Reads immediate message number `arg0`. If global file handle `[0x1823]` is `0xffff`, helper `0x833f` opens or creates the file named at `0x1825` (`logfile`) and seeks it to the end. The handler then appends a formatted room/input-line record using template `0x1809` (`Room %d\nInput line: %s\n`) with byte variable 0 and string/input buffer `0x0fce`, resolves message `arg0` through `0x21f0`, formats it into the same stack buffer through `0x1f54`, appends it, and closes the file handle with `0x5d52`. If opening fails, it returns after consuming the operand. |
| `0x91` | `save_logic_resume_ip` | `0x1335` | Stores the current bytecode pointer `SI` into word `[current_logic+0x06]`, where `current_logic` is the record pointed to by `[0x0981]`. |
| `0x92` | `restore_logic_entry_ip` | `0x134a` | Restores word `[current_logic+0x06]` from `[current_logic+0x04]`. |
| `0x95` | `enable_action_trace_window` | `0x8c91` | If word `[0x1d10]` is nonzero, returns `SI + 1`, consuming one byte beyond the opcode. Otherwise it calls helper `0x8cae`, which starts an action-trace display only when flag 10 is set: it sets `[0x1d10] = 1`, computes a text-window rectangle from input-line row `[0x05dd]`, trace offset `[0x1d08]`, and trace height `[0x1d0a]`, stores the derived bounds in `[0x1d14]`, `[0x1d16]`, `[0x1d18]`, `[0x1d1a]`, `[0x1d1c]`, and `[0x1d1e]`, then draws a boxed area through helper `0x5590`. |
| `0x96` | `configure_action_trace_window` | `0x8d3d` | Reads three immediates into `[0x1d12]`, `[0x1d08]`, and `[0x1d0a]`, clamping `[0x1d0a]` upward to at least 2. The first value names an optional logic resource used by the action-trace formatter around `0x8e0b`; the second and third values control the trace window's row offset and height. Restart and room-switch paths also reload logic `[0x1d12]` when it is nonzero, so this configuration participates in both trace display and session reset. |

Miscellaneous actions:

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x7a` | `setup_transient_object` | `0x2c7a` | Copies seven immediate operands into globals `0x0eae..0x0eb3`, with operand 6 shifted into the high nibble of `0x0eb3`, then calls helper `0x2d52`. The staged values select view resource, group, frame, X, Y, and priority/control nibbles. Helper `0x2d52` initializes a transient object-like record at `0x0eb4` through `0x3ae7`, `0x3bb7`, and `0x3ccb`, places it with `0x593a`, draws/marks it through `0x57cf`, rebuilds update lists, and calls `0x5762`. |
| `0x7b` | `setup_transient_object_var` | `0x2cca` | Same as `0x7a`, but all seven operands are read through variables before the seventh value is shifted into the high nibble of `0x0eb3`. |
| `0x82` | `random_range_to_var` | `0x5009` | Reads low bound `arg0`, high bound `arg1`, and destination variable index `arg2`. Calls helper `0x71c0`, takes the returned value modulo `(high - low + 1)`, adds `low`, and stores the low byte in `var[arg2]`. Helper `0x71c0` seeds from BIOS timer interrupt `1a` when needed and advances a 16-bit state at `0x1711`. |
| `0x8d` | `show_interpreter_version` | `0x733c` | Displays the static interpreter identification string at `0x0aab` through helper `0x1ce8`. In the sampled SQ2 overlay this string reads `Adventure Game Interpreter` followed by `Version 2.936`. |

Remaining table entries:

| Opcode | Label | Handler | Observed action |
| ---: | --- | ---: | --- |
| `0x7f` | `noop` | `0x5051` | Performs no state change and returns the current bytecode pointer unchanged. This opcode was present in the action table but not encountered in the local SQ2 logic scan. |
| `0x9b` | `noop_2` | `0x4c15` | Consumes two operand bytes and performs no state change. The handler returns `SI + 2`. |
| `0xaa` | `copy_save_description_to_string_slot` | `0x2726` | Reads immediate string-slot index `arg0`, computes destination string slot `0x020d + arg0 * 0x28`, and copies up to `0x1f` bytes from buffer `0x0e72` into that slot through helper `0x4de8`. Save/restore handlers test byte `[0x0e72]` after slot/path selection, so this action appears to expose that save-description buffer to logic string storage. |
| `0xab` | `save_event_buffer_count` | `0x718b` | Copies word `[0x0143]` to word `[0x05e1]`. Helper `0x70b1` increments `[0x0143]` when appending `(kind, resource)` pairs to the event/resource pair buffer rooted at `[0x1707]`, so this preserves the active pair count. |
| `0xac` | `restore_event_buffer_count` | `0x719d` | Restores word `[0x0143]` from `[0x05e1]`, then recomputes the pair-buffer write pointer `[0x1709] = [0x1707] + [0x0143] * 2`. |
| `0xad` | `increment_global_1530` | `0x602f` | Increments byte `[0x1530]` and returns the current bytecode pointer. Nearby interrupt-hook code tests `[0x1530]` before calling display/input helper `0x44a9` on selected key release paths, but the exact user-facing purpose remains open. |
| `0xae` | `rebuild_priority_table_from_y` | `0x4d10` | Reads immediate row/value `arg0`, clears word `[0x124a]`, and rebuilds the 168-byte priority/control table at `0x127a`. Entries below `arg0` are set to `4`; entries from `arg0` upward are assigned a rising value starting at `5`, using a scale derived from `(0xa8 - arg0) * 0xa8 / 10`, and capped at `0x0f`. Helper `0x4cbb` later maps priority/control values back through this table when `[0x124a] == 0`. |
| `0xaf` | `noop_1_table_count` | `0x5051` | Uses the same no-op handler as action `0x7f`, returning the bytecode pointer it was given. The action table gives this opcode one fixed operand byte, so table-driven static scans skip one byte, but the handler itself does not read or advance past that operand. This opcode was not encountered in the local SQ2 logic scan. |

## Local SQ2 scan

The local helper `tools/disassemble_logic.py` extracts logic resources, applies
the dispatch tables, and prints decoded bytecode. It also has a `--stats` mode
for linear opcode counts. This is still a static bytecode listing, not a live
execution trace.

One `LOGDIR` entry decodes to `VOL.0:0x1ffff` but does not have a valid volume
record header; the stats mode reports this as logic 141 and skips it.

Using the action table operand counts and the condition table operand counts,
the current local scan of present SQ2 logic resources found these structural
byte counts:

| Byte | Count | Meaning |
| ---: | ---: | --- |
| `0x00` | 144 | End of the current execution path. Later bytecode in the same logic can still be reached by jumps. |
| `0xfe` | 365 | Relative jump. |
| `0xff` | 2224 | Conditional block marker. |

Frequently encountered action opcodes at statement boundaries included:

| Opcode | Label | Count | Fixed operands |
| ---: | --- | ---: | ---: |
| `0x03` | `assignn` | 2019 | 2 |
| `0x65` | `display_message` | 1301 | 1 |
| `0x2b` | `set_object_subresource` | 532 | 2 |
| `0x29` | `set_object_resource` | 520 | 2 |
| `0x23` | `activate_object` | 516 | 1 |
| `0x2f` | `set_object_derived_resource_2` | 466 | 2 |
| `0x0c` | `set_flag` | 464 | 1 |
| `0x25` | `set_object_pos` | 448 | 3 |
| `0x36` | `set_object_field_24` | 345 | 2 |
| `0x1e` | `load_view` | 323 | 1 |

Frequently encountered condition opcodes included:

| Opcode | Label | Count | Fixed operands |
| ---: | --- | ---: | --- |
| `0x0e` | `input_word_sequence` | 2472 | variable |
| `0x01` | `var_eq_imm` | 1949 | 2 |
| `0x07` | `flag_set` | 1098 | 1 |
| `0x05` | `var_gt_imm` | 504 | 2 |
| `0x0b` | `object_left_baseline_in_rect` | 450 | 5 |
| `0x03` | `var_lt_imm` | 198 | 2 |
| `0x09` | `obj_table_room_ff` | 153 | 1 |

The current scanner is intentionally conservative. It correctly identifies the
main structural bytes and many statement boundaries. Remaining interpreter work
is concentrated less on unnamed action opcodes and more on refining
implementation-level contracts for object/view fields, display-specific buffer
variants, and the more hardware-facing input and graphics helpers.
