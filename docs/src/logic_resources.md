# Logic resource notes

This page records clean-room observations about logic resource payloads after
they have been loaded from `VOL.*` by the generic resource reader. It is based
on the local SQ2 resource files, `SQ2/AGIDATA.OVL`, and the decrypted
executable. Current tools require the game directory to be selected explicitly
with `--game-dir PATH` or `AGI_GAME_DIR=PATH`.

## Loader path

The high-level logic loader starts at image offset `0x119a`.

Logic cache records are 10 bytes and are linked from word `[0x0977]`:

```text
+0x00: next logic cache record, or 0
+0x02: logic number byte
+0x03: message count byte
+0x04: bytecode base pointer, payload + 2
+0x06: current interpreter instruction pointer
+0x08: message offset table base pointer
```

Helper `0x110f(logic_number)` scans the list. While scanning, it also stores
the link slot that led to the current record in `[0x0983]`. On a miss, that
slot is where a newly allocated record should be linked. For the first record
the slot is the global root `[0x0977]`; for later records it is the previous
record's `+0x00` field.

Observed load path:

```text
load_logic(number):
    existing = find_cached_logic(number)        # 0x110f
    if existing:
        return existing

    suspend_update_lists()                      # 0x6a54
    record = allocate(10)
    *last_link_slot = record                    # [0x0983]
    record[0x00] = 0
    record[0x02] = number

    dir_entry = logic_directory_entry(number)   # 0x4371
    payload = read_volume_resource(dir_entry, 0) # 0x2e32 -> 0x2e56

    record[0x04] = payload + 2
    record[0x06] = payload + 2

    code_length = payload[0] | (payload[1] << 8)
    count_position = payload + 2 + code_length
    message_count = *count_position
    record[0x03] = message_count
    record[0x08] = count_position + 1

    if message_count != 0:
        old_current = current_logic             # [0x0981]
        current_logic = record
        end = message_pointer(0)                # 0x21f0
        text_start = record[0x08] + (message_count + 1) * 2
        xor_range(text_start, end)              # 0x07ab
        current_logic = old_current

    rebuild_update_lists()                      # 0x6a8e
    return record
```

The `payload` pointer returned by the volume reader begins after the 5-byte
`VOL.*` record header. The first two bytes of a logic payload are not executed
as bytecode; they are a little-endian length used to find the message metadata.

## Room-switch cache reset

Room switching does not simply clear every resource cache root. The helper at
image `0x10d0` performs a cache reset tuned for room transition:

```text
reset_room_caches():                 # 0x10d0
    truncate_logic_cache_to_head()    # 0x10f7
    clear_view_cache_root()           # 0x396d -> [0x0ffa] = 0
    clear_sound_cache_root()          # 0x50cc -> [0x125a] = 0
    clear_picture_cache_root()        # 0x49dc -> [0x120e] = 0
```

The logic helper at image `0x10f7` is narrower than a root clear. If
`[0x0977]` is nonzero, it treats that word as the first logic cache record and
stores zero at record offset `+0x00`. This preserves the first linked logic
record while unlinking later records. In SQ2's normal room-switch path that
matches the observed control-flow model: logic 0 survives the switch and later
dispatches the destination room, while old room-specific cached logic records
are discarded.

## Payload layout

The loader supports this layout:

```text
payload + 0x0000: u16 little-endian code_length
payload + 0x0002: bytecode, length code_length
payload + 0x0002 + code_length: u8 message_count
next byte: u16 little-endian message offsets, message_count + 1 entries
after table: encrypted message text bytes
```

The message offset table base is the byte immediately after `message_count`.
Routine `0x21f0` reads `u16le(table_base + message_number * 2)` and returns
`table_base + offset`. This makes message offsets relative to the table base,
not relative to the payload start.

Offset entry 0 is used by the loader as the end pointer for the encrypted text
area. Entries 1 through `message_count` are the game-visible message pointers.
An offset value of zero is treated as an error path by `0x21f0` when requested.

## Message text decryption

Routine `0x07ab` XORs a memory range in place. It uses a zero-terminated key at
`DS:0x08f1`, restarting from the first key byte when it reaches the zero byte.
At runtime `DS` points at `AGIDATA.OVL`, whose offset `0x08f1` contains:

```text
Avis Durgan
```

The loader calls this XOR routine over:

```text
start = table_base + (message_count + 1) * 2
end = message_pointer(0)
```

So the message table itself remains unencrypted, while the message text region
is decrypted in place after loading.

Version note: Gold Rush / AGI v3 still uses encrypted logic-message text in the
loaded resources observed so far. Local logic 101 has action `0x8f(#3)`;
message 3 is stored encrypted in the resource bytes and decrypts to `GR\0`,
matching the interpreter's embedded verifier string. Generated fixtures should
therefore keep `tools/qemu_fixture.py`'s encrypted-message default unless a
targeted negative/control case intentionally needs plain text with
`logic_resource(..., encrypt_messages=False)`.

## Local samples

Examples from SQ2:

| Logic | Payload length | Code length | Message count | Table base | Text start | End offset |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 911 | 868 | 2 | 871 | 877 | 911 |
| 2 | 4536 | 1972 | 35 | 1975 | 2047 | 4536 |
| 3 | 3564 | 1424 | 38 | 1427 | 1505 | 3564 |
| 4 | 3614 | 1303 | 24 | 1306 | 1356 | 3614 |
| 7 | 470 | 277 | 1 | 280 | 284 | 470 |
| 8 | 2325 | 1105 | 15 | 1108 | 1140 | 2325 |

For logic 1, the payload bytes at the message area decrypt to a null-terminated
string beginning with `Type RUN`.

For logic 2, table entry 0 is `0x0a01`, and `table_base + 0x0a01` equals the
payload length. Entry 1 is `0x0048`, which points exactly at the first decrypted
message byte because `table_base + 0x0048 == text_start`.

The bytecode beginning at `payload + 2` is interpreted by the main logic loop
at image offset `0x293c`; see the logic bytecode notes for opcode dispatch and
condition parsing.

## Call and cache lifetime

Action helpers `0x113d` and `0x1159` load a logic resource through
`0x117d(logic_number)`. That wrapper calls the loader above and records the
pair `(0, logic_number)` through helper `0x70b1`. It leaves the logic cache
record linked from `[0x0977]`.

Action helpers `0x125a` and `0x1280` use a different path,
`0x12ae(logic_number)`, for invoking another logic resource as a subroutine:

```text
call_logic(number):
    old_current = current_logic                 # [0x0981]
    cached = find_cached_logic(number)          # 0x110f

    if cached:
        current_logic = cached
        loaded_for_call = false
    else:
        saved_link_slot = last_link_slot        # [0x0983]
        current_logic = load_logic(number)      # 0x119a
        loaded_for_call = true

    if word[0x1d10] == 2:
        word[0x1d10] = 1
    if number == 0:
        word[0x1d20] = 1

    result = interpret(current_logic)           # 0x293c

    if loaded_for_call:
        *saved_link_slot = 0
        suspend_update_lists()                  # 0x6a54
        heap_rewind_to(current_logic)           # 0x143c
        rebuild_update_lists()                  # 0x6a8e

    current_logic = old_current
    return result
```

The action handlers propagate the interpreter result: if `0x12ae` returns zero,
the action dispatcher receives zero as the next instruction pointer and the
current logic loop stops. A normal opcode `0x00` termination returns the
callee's nonzero instruction pointer, so the caller advances to its next
action. Zero is reserved for action paths that deliberately abort/restart the
current logic flow, such as room switching.

This shows two distinct lifetimes:

- Logic loaded through `0x117d` remains cached.
- Logic that is first encountered through `0x12ae` is temporary. After the
  nested interpreter returns, the record is unlinked and the heap top is rewound
  to the start of that record.

## Saved interpreter positions

Routine `0x1364` serializes logic resume metadata into a table at `0x0985`.
Each entry is four bytes:

```text
+0x00: logic number as a word
+0x02: current_ip - bytecode_base
```

It begins by treating the static head at `0x0977` as a 10-byte cache-shaped
record, so the first emitted pair comes from bytes `0x0979`, `0x097b`, and
`0x097d`; in current state this produces `(0, 0)`. It then follows the head's
next pointer and emits one entry for each linked cache record. Finally it writes
terminator word `0xffff` without clearing that record's second word, and returns
the total table byte count including the full four-byte terminator record.

Routine `0x13a5(record)` performs the reverse lookup for one record. It scans
from the first table entry, stops at the first matching logic number, and
restores `record[0x06] = record[0x04] + saved_offset`. If no record matches
before `0xffff`, the loaded logic keeps its entry pointer. Resource replay,
rather than this table, decides which logic records are loaded and receive this
lookup.

## Heap and lifetime model

The logic cache records, resource payloads, menu nodes, and selected render
nodes are allocated from a bump pointer stored at `[0x0a55]`. No source-backed
general free-list behavior has been observed for this heap. Instead, the engine
uses marks and rewinds for broad lifetime changes: startup stores a room/reset
mark with `0x1476` after initial setup and logic 0 load; room switch, restart,
and restore paths call `0x1485` to return to that mark after freeing update-list
nodes; temporary `call_logic` cleanup rewinds directly to the transient record
pointer with `0x143c`.

| Helper | Observed role |
| --- | --- |
| `0x13d6(size)` | Allocate `size` bytes from `[0x0a55]`. If `size > [0x0a5b] - [0x0a55]`, formats the out-of-memory message at `0x09fd`, displays it, and calls the restart/exit helper `0x02ae`. Otherwise returns the old heap pointer, advances `[0x0a55]`, refreshes byte variable 8 at `[0x0011]`, and updates high-water pointer `[0x0a5f]` when the new top is larger. |
| `0x1430` | Return the current heap pointer `[0x0a55]`. |
| `0x143c(ptr)` | Rewind or set `[0x0a55]` to `ptr`. It does not itself refresh `[0x0011]`; callers that need the free-memory byte current call `0x14a0` separately. |
| `0x144b` | Save the current heap pointer in `[0x0a5d]`. |
| `0x145a` | Restore `[0x0a55]` from temporary mark `[0x0a5d]` if it is nonzero, then clear `[0x0a5d]`. |
| `0x1476` | Store the current heap pointer in `[0x0a59]`. |
| `0x1485` | Free update-list nodes, clear `[0x0a5d]`, restore `[0x0a55]` from `[0x0a59]`, and refresh memory status. |
| `0x14a0` | Compute free heap bytes as `[0x0a5b] - [0x0a55]` and store the high byte in byte variable `[0x0011]`. |

The heap-status diagnostic `0x87` formats the same pointers as offsets from
heap base `[0x0a57]`: heap size is `[0x0a5b] - [0x0a57]`, current use is
`[0x0a55] - [0x0a57]`, maximum use is `[0x0a5f] - [0x0a57]`, and the room/reset
mark is `[0x0a59] - [0x0a57]`. It also displays the maximum observed
resource-event pair count `[0x170f]` as the script/resource-event budget line.
