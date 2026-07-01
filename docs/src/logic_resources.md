# Logic resource notes

This page records clean-room observations about logic resource payloads after
they have been loaded from `VOL.*` by the generic resource reader. It is based
on the local SQ2 resource files, `SQ2/AGIDATA.OVL`, and the decrypted
executable.

## Loader path

The high-level logic loader starts at image offset `0x119a`.

Observed load path:

```text
load_logic(number):
    existing = find_cached_logic(number)        # 0x110f
    if existing:
        return existing

    record = allocate(10)
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
        end = message_pointer(0)                # 0x21f0
        text_start = record[0x08] + (message_count + 1) * 2
        xor_range(text_start, end)              # 0x07ab

    return record
```

The `payload` pointer returned by the volume reader begins after the 5-byte
`VOL.*` record header. The first two bytes of a logic payload are not executed
as bytecode; they are a little-endian length used to find the message metadata.

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

## Open questions

The bytecode beginning at `payload + 2` is not decoded yet. The next step is to
follow the instruction interpreter around image offset `0x07e3`, where a byte
is loaded from `SI`, compared against `0x26`, and used to dispatch through a
function table near image offset `0x08fd`.
