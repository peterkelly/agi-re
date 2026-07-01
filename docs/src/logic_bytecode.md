# Logic bytecode interpreter notes

This page records clean-room observations about the interpreter for logic
payload bytecode. It is based on local disassembly of
`build/cleanroom/AGI.decrypted.exe`, the runtime tables in `SQ2/AGIDATA.OVL`,
and decoded SQ2 logic payloads.

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

| Opcode | Metadata | Meaning confirmed by handler |
| ---: | ---: | --- |
| action `0x03` | `0x80` | Operand 0 is a variable slot, operand 1 is an immediate literal. |
| action `0x04` | `0xc0` | Operands 0 and 1 are variable slots. |
| action `0x26` | `0x60` | Operand 0 is an object index; operands 1 and 2 are variable slots. |
| action `0x52` | `0x70` | Operand 0 is an object index; operands 1, 2, and 3 are variable slots; operand 4 is immediate. |
| action `0x7b` | `0xfe` | Seven operands are variable slots. |
| condition `0x0a` | `0x40` | Operand 0 is a table/object index; operand 1 is a variable slot. |

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
`0x0e`: the scanner reads one count byte and skips `count * 2` additional
bytes. This special case appears in the condition skip paths at image offsets
`0x29af..0x29b8` and `0x29d7..0x29e0`.

## Condition table

The current `DS:0x08fd` condition table entries are:

| Opcode | Handler | Fixed operands | Metadata |
| ---: | ---: | ---: | ---: |
| `0x00` | `0x09d8` | 0 | `0x00` |
| `0x01` | `0x0823` | 2 | `0x80` |
| `0x02` | `0x0834` | 2 | `0xc0` |
| `0x03` | `0x084b` | 2 | `0x80` |
| `0x04` | `0x085c` | 2 | `0xc0` |
| `0x05` | `0x0873` | 2 | `0x80` |
| `0x06` | `0x0884` | 2 | `0xc0` |
| `0x07` | `0x089b` | 1 | `0x00` |
| `0x08` | `0x08a0` | 1 | `0x80` |
| `0x09` | `0x08ad` | 1 | `0x00` |
| `0x0a` | `0x093b` | 2 | `0x40` |
| `0x0b` | `0x08c6` | 5 | `0x00` |
| `0x0c` | `0x0931` | 1 | `0x00` |
| `0x0d` | `0x09be` | 0 | `0x00` |
| `0x0e` | `0x095c` | 0 | `0x00` |
| `0x0f` | `0x09db` | 2 | `0x00` |
| `0x10` | `0x08e8` | 5 | `0x00` |
| `0x11` | `0x08cc` | 5 | `0x00` |
| `0x12` | `0x08db` | 5 | `0x00` |

The first seven handlers directly expose byte variable comparisons. The byte
variable array begins at `DS:0x0009`.

| Opcode | Observed predicate |
| ---: | --- |
| `0x00` | Always false. Handler `0x09d8` returns zero. |
| `0x01` | `byte[0x0009 + arg0] == arg1` |
| `0x02` | `byte[0x0009 + arg0] == byte[0x0009 + arg1]` |
| `0x03` | `byte[0x0009 + arg0] < arg1` |
| `0x04` | `byte[0x0009 + arg0] < byte[0x0009 + arg1]` |
| `0x05` | `byte[0x0009 + arg0] > arg1` |
| `0x06` | `byte[0x0009 + arg0] > byte[0x0009 + arg1]` |
| `0x07` | Tests flag bit `arg0`. |
| `0x08` | Tests flag bit `byte[0x0009 + arg0]`. |
| `0x09` | Looks up a 3-byte table entry at `[0x0971] + arg0 * 3` and tests whether byte `+2` is `0xff`. |
| `0x0a` | Compares byte `+2` of that 3-byte table entry with `byte[0x0009 + arg1]`. |
| `0x0c` | Returns byte `DS:0x1218 + arg0`. |
| `0x0d` | Checks or obtains a byte through helper `0x459e`, caching a non-zero byte at `DS:0x001c`. |
| `0x0e` | Variable-length parsed-input word sequence test. |
| `0x0f` | Reads two byte operands and calls helper `0x0eac`. |

Condition opcodes `0x0b`, `0x10`, `0x11`, and `0x12` all load an entry from a
43-byte structure array rooted at `[0x096b]` using the first operand as an
index. They compare that object's position or bounds against four subsequent
byte operands. The exact game-level names remain open, but the shared helper at
`0x091a` loads:

```text
object = [0x096b] + arg0 * 0x2b
dh = object[0x03]
ch = object[0x03]
dl = object[0x05]
```

The handlers then adjust `dh` or `ch` using `object[0x1a]` before comparing
against a rectangle-like four-byte operand sequence.

Flag helpers use a bitfield rooted at `DS:0x0109`. Helper `0x7511` computes:

```text
byte_address = DS:0x0109 + flag_number / 8
mask = 0x80 >> (flag_number & 7)
```

Helper `0x74ee` sets the bit, `0x74f4` clears it, `0x74fc` toggles it, and
`0x7502` tests it. Initialization helper `0x752a` clears `0x20` bytes starting
at `DS:0x0109`.

Condition opcode `0x0e` is the most common condition in the local SQ2 scripts.
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

## Action table

The action table at `DS:0x061d` has entries for opcodes `0x00..0xaf`. The main
dispatcher only executes opcodes `0x01..0xaf`; `0x00` terminates the current
logic loop and `0xfc..0xff` are structural bytes.

Examples of action entries:

| Opcode | Handler | Fixed operands | Metadata |
| ---: | ---: | ---: | ---: |
| `0x01` | `0x7355` | 1 | `0x80` |
| `0x02` | `0x7368` | 1 | `0x80` |
| `0x03` | `0x737b` | 2 | `0x80` |
| `0x0c` | `0x7484` | 1 | `0x00` |
| `0x14` | `0x113d` | 1 | `0x00` |
| `0x16` | `0x125a` | 1 | `0x00` |
| `0x1e` | `0x39b1` | 1 | `0x00` |
| `0x21` | `0x04d9` | 1 | `0x00` |
| `0x23` | `0x09ea` | 1 | `0x00` |
| `0x25` | `0x7c1a` | 3 | `0x00` |
| `0x29` | `0x3a77` | 2 | `0x00` |
| `0x3f` | `0x7e7c` | 1 | `0x00` |
| `0x51` | `0x6ce4` | 5 | `0x00` |
| `0x62` | `0x510a` | 1 | `0x00` |
| `0x64` | `0x5225` | 0 | `0x00` |
| `0x7a` | `0x2c7a` | 7 | `0x00` |
| `0x82` | `0x5009` | 3 | `0x20` |
| `0x93` | `0x7d77` | 3 | `0x00` |
| `0xa7` | `0x744c` | 2 | `0x80` |

The action dispatcher itself does not use the operand-count byte; handlers
consume operands directly from `SI` and return the next `SI` in `AX`. The table
metadata is used by scanner/debug paths that need to skip or display bytecode.

## Decoded action families

Variable action handlers directly operate on the byte array rooted at
`DS:0x0009`.

| Opcode | Handler | Observed action |
| ---: | ---: | --- |
| `0x01` | `0x7355` | Increment `var[arg0]` unless it is already `0xff`. |
| `0x02` | `0x7368` | Decrement `var[arg0]` unless it is already `0x00`. |
| `0x03` | `0x737b` | `var[arg0] = arg1` |
| `0x04` | `0x7388` | `var[arg0] = var[arg1]` |
| `0x05` | `0x739b` | `var[arg0] += arg1` |
| `0x06` | `0x73a8` | `var[arg0] += var[arg1]` |
| `0x07` | `0x73bb` | `var[arg0] -= arg1` |
| `0x08` | `0x73c8` | `var[arg0] -= var[arg1]` |
| `0x09` | `0x73db` | `var[var[arg0]] = var[arg1]` |
| `0x0a` | `0x7405` | `var[arg0] = var[var[arg1]]` |
| `0x0b` | `0x73f4` | `var[var[arg0]] = arg1` |
| `0xa5` | `0x741e` | `var[arg0] *= arg1`; low byte of the product is stored. |
| `0xa6` | `0x7431` | `var[arg0] *= var[arg1]`; low byte of the product is stored. |
| `0xa7` | `0x744c` | `var[arg0] /= arg1`; 8-bit quotient is stored. |
| `0xa8` | `0x7465` | `var[arg0] /= var[arg1]`; 8-bit quotient is stored. |

Flag action handlers use the same bitfield helpers as condition opcodes
`0x07` and `0x08`.

| Opcode | Handler | Observed action |
| ---: | ---: | --- |
| `0x0c` | `0x7484` | Set flag bit `arg0`. |
| `0x0d` | `0x748b` | Clear flag bit `arg0`. |
| `0x0e` | `0x7492` | Toggle flag bit `arg0`. |
| `0x0f` | `0x7499` | Set flag bit `var[arg0]`. |
| `0x10` | `0x74a8` | Clear flag bit `var[arg0]`. |
| `0x11` | `0x74b7` | Toggle flag bit `var[arg0]`. |

Several object/view actions use entries in the 43-byte structure array rooted
at `[0x096b]`. Field names remain provisional; these notes record observed
storage and calls rather than assigning final game-level names.

| Opcode | Handler | Observed action |
| ---: | ---: | --- |
| `0x23` | `0x09ea` | Reads an object index and calls `0x0a06`. The helper validates the object, requires word `[object+0x10] != 0`, copies `[+0x10]` to `[+0x12]`, `[+0x03]` to `[+0x16]`, and `[+0x05]` to `[+0x18]`, sets bits in word `[+0x25]`, and calls several list/graphics helpers. |
| `0x24` | `0x0a8f` | Calls helper `0x0aab` for object `arg0`. If the object has bit `0x0001` set in `[+0x25]`, the helper clears that bit and calls list/graphics helpers to remove or deactivate the object. |
| `0x25` | `0x7c1a` | Set object position-like fields from immediate bytes: `[+0x16] = [+0x03] = arg1`, `[+0x18] = [+0x05] = arg2`. |
| `0x26` | `0x7c57` | Set the same fields from variables `var[arg1]` and `var[arg2]`. |
| `0x27` | `0x7ca4` | Store low bytes of object fields `[+0x03]` and `[+0x05]` into `var[arg1]` and `var[arg2]`. |
| `0x29` | `0x3a77` | Resolve object `arg0`, pass immediate `arg1` to helper `0x3ae7`. |
| `0x2a` | `0x3aab` | Resolve object `arg0`, pass `var[arg1]` to helper `0x3ae7`. |
| `0x2b` | `0x3b47` | Resolve object `arg0`, pass immediate `arg1` to helper `0x3bb7`. |
| `0x2c` | `0x3b7b` | Resolve object `arg0`, pass `var[arg1]` to helper `0x3bb7`. |
| `0x2f` | `0x3c55` | Resolve object `arg0`, pass immediate `arg1` to helper `0x3ccb`, then clear bit `0x1000` in object word field `[+0x25]`. |

Helper `0x3ae7` finds a cached resource record via `0x3979`, stores the
resource payload pointer at object field `[+0x08]`, stores the selected resource
number at byte `[+0x07]`, copies byte `[payload+0x02]` to object byte
`[+0x0b]`, then calls `0x3bb7`. Helper `0x3bb7` validates object field
`[+0x08]`, checks its second argument against byte `[+0x0b]`, then calls
`0x3c1b` and `0x3ccb` to update derived object fields.

Resource and interpreter-control actions observed so far:

| Opcode | Handler | Observed action |
| ---: | ---: | --- |
| `0x14` | `0x113d` | Reads immediate `arg0`, calls `0x117d`. Helper `0x117d` loads logic resource `arg0` through `0x119a`, then records pair `(0, arg0)` through helper `0x70b1`. |
| `0x15` | `0x1159` | Same as `0x14`, but logic number is `var[arg0]`. |
| `0x16` | `0x125a` | Reads immediate `arg0`, calls `0x12ae`, and returns zero to the action dispatcher if `0x12ae` returns zero. Helper `0x12ae` locates or loads a logic resource and calls the main interpreter `0x293c` on it, preserving the previous current logic pointer at `[0x0981]`. |
| `0x17` | `0x1280` | Same as `0x16`, but logic number is `var[arg0]`. |
| `0x1e` | `0x39b1` | Loads or refreshes a view-like resource through helper `0x39f7` using immediate `arg0`. |
| `0x1f` | `0x39d0` | Same as `0x1e`, but resource number is `var[arg0]`. |
| `0x62` | `0x510a` | Loads a sound-like resource through helper `0x5126` using immediate `arg0`; the helper uses sound directory accessor `0x440d` and builds four internal pointers from the loaded payload. |
| `0x64` | `0x5225` | Calls helper `0x5234`, which clears a pending sound-like state at `[0x1258]`, sets flag `[0x126a]`, and calls `0x080af` when that state was active. |

Additional object-state actions:

| Opcode | Handler | Observed action |
| ---: | ---: | --- |
| `0x21` | `0x04d9` | Calls helper `0x04f5` for object `arg0`. If object word `[+0x25]` does not have bit `0x0040`, the helper sets `[+0x25] = 0x0070` and clears bytes `[+0x22]`, `[+0x23]`, and `[+0x21]`. |
| `0x22` | `0x053d` | Iterates all 43-byte object entries from `[0x096b]` to `[0x096d]` and clears bits `0x0041` in word field `[+0x25]`. |
| `0x3f` | `0x7e7c` | Stores immediate `arg0` as a word at `DS:0x012d`. |
| `0x40` | `0x7e0d` | Sets bit `0x0100` in object word field `[+0x25]`. |
| `0x43` | `0x479f` | Sets bit `0x0200` in object word field `[+0x25]`. |
| `0x44` | `0x47c7` | Clears bit `0x0200` in object word field `[+0x25]`. |
| `0x51` | `0x6ce4` | Sets object byte `[+0x22] = 3`; stores immediates in `[+0x27]`, `[+0x28]`, and `[+0x2a]`; copies old `[+0x1e]` to `[+0x29]`; optionally updates `[+0x1e]` when operand 3 is nonzero; clears the flag named by operand 4; sets object bit `0x0010`; calls helper `0x1672`. |
| `0x52` | `0x6d61` | Same broad shape as `0x51`, but operands 1, 2, and 3 are read through variables while operand 4 remains immediate. |
| `0x58` | `0x7b9c` | Sets bit `0x0002` in object word field `[+0x25]`. |
| `0x59` | `0x7bc1` | Clears bit `0x0002` in object word field `[+0x25]`. |
| `0x93` | `0x7d77` | Sets object fields `[+0x03] = arg1` and `[+0x05] = arg2`, sets bit `0x0400` in `[+0x25]`, then calls helper `0x593a`. |

Actions that update object byte `[+0x24]`:

| Opcode | Handler | Observed action |
| ---: | ---: | --- |
| `0x36` | `0x7a80` | Sets bit `0x0004` in object word field `[+0x25]` and writes immediate `arg1` to byte `[+0x24]`. |
| `0x37` | `0x7b08` | Same as `0x36`, but writes `var[arg1]` to byte `[+0x24]`. |
| `0x38` | `0x7ab0` | Clears bit `0x0004` in object word field `[+0x25]`. |
| `0x39` | `0x7ad5` | Stores object byte `[+0x24]` into `var[arg1]`. |

Message-display actions use the current logic resource's message table through
helper `0x21f0`.

| Opcode | Handler | Observed action |
| ---: | ---: | --- |
| `0x65` | `0x1c06` | Resolve message `arg0` with `0x21f0`, then pass the string pointer to display helper `0x1ce8`. |
| `0x66` | `0x1c29` | Same as `0x65`, but message number is `var[arg0]`. |
| `0x97` | `0x1c54` | Reads immediate message number `arg0`, then reads three additional bytes into globals `[0x0d0b]`, `[0x0d0d]`, and `[0x0d09]` before resolving and displaying the message; the globals are reset to `0xffff` afterward. |
| `0x98` | `0x1c71` | Same as `0x97`, but message number is `var[arg0]`. |

Miscellaneous actions:

| Opcode | Handler | Observed action |
| ---: | ---: | --- |
| `0x7a` | `0x2c7a` | Copies seven immediate operands into globals `0x0eae..0x0eb3`, with operand 6 shifted into the high nibble of `0x0eb3`, then calls helper `0x2d52`. The helper emits several `(a, b)` pairs through `0x70b1`, initializes a transient object-like structure at `0x0eb4` through `0x3ae7`, `0x3bb7`, and `0x3ccb`, and copies additional derived fields. |
| `0x7b` | `0x2cca` | Same broad shape as `0x7a`, but the first six operands are variable references and the seventh is also read through a variable before being shifted into `0x0eb3`. |
| `0x82` | `0x5009` | Reads low bound `arg0`, high bound `arg1`, and destination variable index `arg2`. Calls helper `0x71c0`, takes the returned value modulo `(high - low + 1)`, adds `low`, and stores the low byte in `var[arg2]`. Helper `0x71c0` seeds from BIOS timer interrupt `1a` when needed and advances a 16-bit state at `0x1711`. |

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

| Opcode | Count | Fixed operands |
| ---: | ---: | ---: |
| `0x03` | 2019 | 2 |
| `0x65` | 1301 | 1 |
| `0x2b` | 532 | 2 |
| `0x29` | 520 | 2 |
| `0x23` | 516 | 1 |
| `0x2f` | 466 | 2 |
| `0x0c` | 464 | 1 |
| `0x25` | 448 | 3 |
| `0x36` | 345 | 2 |
| `0x1e` | 323 | 1 |

Frequently encountered condition opcodes included:

| Opcode | Count | Fixed operands |
| ---: | ---: | ---: |
| `0x0e` | 2472 | variable |
| `0x01` | 1949 | 2 |
| `0x07` | 1098 | 1 |
| `0x05` | 504 | 2 |
| `0x0b` | 450 | 5 |
| `0x03` | 198 | 2 |
| `0x09` | 153 | 1 |

The current scanner is intentionally conservative. It correctly identifies the
main structural bytes and many statement boundaries. Remaining interpreter work
is concentrated on assigning stable names to the object/view fields and decoding
the larger action families around drawing, text, input, sound, and resource
management.
