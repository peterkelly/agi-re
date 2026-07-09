# Resource file notes

This page records clean-room observations about the SQ2 resource directory and
volume files. It is based on local files from an explicitly selected SQ2 game
directory (`*DIR`, `VOL.*`, `AGIDATA.OVL`) and the decrypted executable.

## Directory file loading

The decrypted executable references these AGIDATA strings:

| AGIDATA offset | String |
| --- | --- |
| `0x116a` | `logdir` |
| `0x1172` | `viewdir` |
| `0x117a` | `picdir` |
| `0x1182` | `snddir` |

The routine at image offset `0x4305` loads all four directory files with the
whole-file loader at image offset `0x3113`.

Observed load order and destination pointers:

| File string | Pointer destination |
| --- | --- |
| `logdir` | `[0x11b2]` |
| `picdir` | `[0x11b6]` |
| `viewdir` | `[0x11b4]` |
| `snddir` | `[0x11b8]` |

The whole-file loader at image offset `0x3113`:

```text
load_whole_file(path, optional_destination):
    handle = dos_open(path, mode=0)
    if open fails:
        display/retry error using AGIDATA string 0x0eef

    size = dos_seek(handle, offset=0, origin=end)
    dos_seek(handle, offset=0, origin=start)
    [0x0f1a] = size

    if optional_destination == 0:
        optional_destination = allocate(size)

    bytes_read = dos_read(handle, optional_destination, size)
    if bytes_read != size:
        display/retry disk error path

    dos_close(handle)
    return optional_destination
```

The exact retry behavior still needs refinement, but the open, seek-to-end,
seek-to-start, optional allocation, full read, and close steps are directly
visible in the disassembly.

## Directory entry accessors

The four accessors multiply a resource number by three, add the result to the
loaded directory base pointer, and reject entries whose first byte has a high
nibble of `0xf`.

| Image offset | Directory base | Missing-resource string |
| --- | --- | --- |
| `0x4371` | `[0x11b2]` (`logdir`) | `logic` at AGIDATA offset `0x1140` |
| `0x43a5` | `[0x11b4]` (`viewdir`) | `view` at AGIDATA offset `0x1146` |
| `0x43d9` | `[0x11b6]` (`picdir`) | `picture` at AGIDATA offset `0x114b` |
| `0x440d` | `[0x11b8]` (`snddir`) | `sound` at AGIDATA offset `0x1153` |

The shared check at image offset `0x434e`:

```text
entry_or_null(entry):
    if (entry[0] & 0xf0) == 0xf0:
        return 0
    return entry
```

So an absent resource directory entry is represented by a first byte whose high
nibble is `0xf`; in the SQ2 files observed so far this commonly appears as
`ff ff ff`.

## Directory entry format

Each loaded directory is an array of 3-byte entries.

The local SQ2 bytes support this interpretation:

```text
byte0 high nibble: volume number
byte0 low nibble plus byte1 plus byte2: 20-bit offset in that VOL file

volume = byte0 >> 4
offset = ((byte0 & 0x0f) << 16) | (byte1 << 8) | byte2
```

Evidence from local samples:

| Directory | Entry | Raw bytes | Decoded target | Bytes at target |
| --- | --- | --- | --- | --- |
| `LOGDIR` | 0 | `10 6d 1b` | `VOL.1` offset `0x06d1b` | `12 34 01 b2` |
| `PICDIR` | 1 | `10 96 8e` | `VOL.1` offset `0x0968e` | `12 34 01 a2` |
| `VIEWDIR` | 0 | `00 9a 51` | `VOL.0` offset `0x09a51` | `12 34 00 1e` |
| `SNDDIR` | 1 | `10 00 00` | `VOL.1` offset `0x00000` | `12 34 01 51` |

Many sampled entries across all four directories point to locations in `VOL.*`
whose first two bytes are `12 34`. The third byte in the sampled headers matches
the decoded volume number.

Observed directory sizes:

| File | Size | Entry count |
| --- | ---: | ---: |
| `LOGDIR` | 426 | 142 |
| `PICDIR` | 444 | 148 |
| `VIEWDIR` | 720 | 240 |
| `SNDDIR` | 210 | 70 |

Two entries at the ends of `LOGDIR` and `PICDIR` do not have an absent high
nibble, but decode beyond the end of `VOL.0`:

| Directory | Entry | Raw bytes | Decoded target |
| --- | ---: | --- | --- |
| `LOGDIR` | 141 | `01 ff ff` | `VOL.0` offset `0x1ffff` |
| `PICDIR` | 147 | `02 ff ff` | `VOL.0` offset `0x2ffff` |

The current working interpretation is only that the executable's generic
directory-entry check would not reject these bytes. No observed local call path
has attempted to load these resource numbers yet.

## Volume file handles

The routine at image offset `0x3080` loops over volume numbers `0` through `4`.
For each number it formats AGIDATA string `0x0ee8` (`vol.%d`) into a local
buffer, opens the resulting filename with the DOS open wrapper at `0x5cce`, and
stores the returned handle in a table starting at `[0x0f04]`.

The routine at image offset `0x30d6` loops over the same five handle slots and
closes every handle not equal to `0xffff`, then resets the slot to `0xffff`.

SQ2 contains `VOL.0`, `VOL.1`, `VOL.2`, and a tiny `VOL.3`; there is no `VOL.4`
in the current directory. The interpreter still has five handle slots.

## Volume record header and generic reader

The generic resource reader starts at image offset `0x2e56`. A retry wrapper at
image offset `0x2e32` calls it until it returns a non-zero pointer or sets error
state `[0x0f02]` to `5`.

Given a non-null directory entry pointer and an optional destination pointer,
the reader:

```text
read_volume_resource(entry, optional_destination):
    if volume handles are not open:
        open VOL.0 through VOL.4

    volume = entry[0] >> 4
    handle = volume_handles[volume]
    offset = ((entry[0] & 0x0f) << 16) | (entry[1] << 8) | entry[2]

    seek(handle, offset, origin=start)
    header = read(handle, 5)

    require header[0] == 0x12
    require header[1] == 0x34
    require header[2] == volume

    payload_length = header[3] | (header[4] << 8)
    [0x0f1a] = payload_length

    if optional_destination == 0:
        optional_destination = allocate(payload_length)

    require read(handle, optional_destination, payload_length) == payload_length
    return optional_destination
```

The little-endian length is pinned down by the stack offsets in the disassembly:
the 5-byte header is read to `[bp-0x0f]..[bp-0x0b]`; image offsets
`0x2f73..0x2f85` compute `([bp-0x0b] << 8) + [bp-0x0c]`. Since `[bp-0x0c]` is
the fourth header byte and `[bp-0x0b]` is the fifth, this is
`header[3] | (header[4] << 8)`.

Local samples confirm the same layout. `SNDDIR` entry 1 points to `VOL.1`
offset `0x00000`; the header bytes are `12 34 01 51 00`, so the payload length
is `0x0051`. The next sound entry starts at `0x00056`, exactly 5 header bytes
plus `0x51` payload bytes later.

The resulting volume record layout is:

```text
byte 0: 0x12
byte 1: 0x34
byte 2: volume number
byte 3: payload length low byte
byte 4: payload length high byte
byte 5..: payload bytes
```

Sampled validation over present entries:

| Directory | Present entries | Bad magic | Bad volume byte | Out of range |
| --- | ---: | ---: | ---: | ---: |
| `LOGDIR` | 119 | 0 | 0 | 1 |
| `PICDIR` | 75 | 0 | 0 | 1 |
| `VIEWDIR` | 203 | 0 | 0 | 0 |
| `SNDDIR` | 49 | 0 | 0 | 0 |

The two out-of-range entries are the end entries shown in the directory-format
section above.

## Resource load call graph

Four higher-level loaders call the directory accessors and then the generic
reader:

| Resource type | Loader | Existing-cache lookup | Directory accessor | Generic reader call |
| --- | --- | --- | --- | --- |
| Logic | `0x119a` | `0x110f` | `0x4371` | `0x11e0 -> 0x2e32` |
| View | `0x39f7` | `0x3979` | `0x43a5` | `0x3a54 -> 0x2e32` |
| Picture | `0x4a3b` | `0x49e8` | `0x43d9` | `0x4a90 -> 0x2e32` |
| Sound | `0x5126` | `0x50d8` | `0x440d` | `0x5185 -> 0x2e32` |

The loaded resource payload returned by `0x2e32` does not include the 5-byte
`VOL.*` record header; it begins at the resource-type-specific payload.

## Gold Rush / AGI v3 resource container comparison

Gold Rush (`games/GR`) uses interpreter version string `Version 3.002.149` in
`AGIDATA.OVL` and changes the resource container without changing the decoded
logic/picture/view/sound payload categories. Unlike SQ2, `games/GR/AGI` is
already an MZ executable, so no SIERRA.COM decrypt step was needed before
disassembling it.

The v3 game directory is a single combined `GRDIR` file instead of four split
directory files. Its first eight bytes are four little-endian section offsets:

| Header word | Section | Offset | Entry count | Present entries |
| --- | --- | ---: | ---: | ---: |
| `+0` | logic | `0x0008` | 245 | 182 |
| `+2` | picture | `0x02e7` | 245 | 186 |
| `+4` | view | `0x05c6` | 256 | 247 |
| `+6` | sound | `0x08c6` | 51 | 44 |

The section payloads are still 3-byte directory entries using the same packed
volume/offset calculation as SQ2. The absent-entry test changed, though:
SQ2's shared check rejects any entry whose first byte has high nibble `0xf`,
while the v3 shared check at GR image `0x4599` rejects only the exact byte
sequence `ff ff ff`.

GR image `0x44de` is the v3 directory loader corresponding to SQ2
`code.resource.load_all_directories`. It formats a combined directory filename
from the runtime prefix and the `"%sdir"` string in `AGIDATA.OVL`. When the
combined file opens, the loader reads it whole and stores section-base pointers
derived from the first four header words. If the combined open fails, the same
routine falls back to separate `logdir`, `picdir`, `viewdir`, and `snddir`
loads.

The v3 volume files are named with a prefix, for example `GRVOL.0` through
`GRVOL.12`. GR image `0x33c2` opens sixteen possible volume handles by
formatting `"%svol.%d"`, so higher volume numbers are part of the observed v3
container design rather than malformed directory entries.

The v3 generic reader starts at GR image `0x30d0`, with a retry wrapper at
`0x30ac`. It reads a 7-byte record header:

```text
byte 0: 0x12
byte 1: 0x34
byte 2: metadata/volume byte
byte 3: expanded length low byte
byte 4: expanded length high byte
byte 5: stored length low byte
byte 6: stored length high byte
byte 7..: stored bytes
```

If metadata bit `0x80` is clear, the metadata byte must equal the directory
entry volume. If metadata bit `0x80` is set, the reader records a
picture-specific transform flag, masks the metadata byte to its low nibble, and
then compares that low nibble with the directory entry volume.

After allocation, v3 has three payload paths:

| Condition | Transform | GR image offset | Observed resource families |
| --- | --- | --- | --- |
| metadata bit `0x80` set | picture nibble expansion | `0x9a5b` | pictures |
| expanded length equals stored length | direct read | `0x607d` DOS read wrapper | a few logic/sound resources |
| expanded length differs from stored length | dictionary expansion | `0x07f4` | most logic, all views, most sounds |

The dictionary path is a bitstream decoder with 9-bit initial codes, growth to
10 and 11 bits, reset code `0x100`, and end code `0x101`. Dictionary entries
are prefix/suffix pairs; after each ordinary code the decoder adds
`previous_string + first_byte(current_string)` at the next dictionary slot.

The picture path is not the same dictionary compression. It is a nibble
realigner: when the stream emits picture command `0xf0` or `0xf2`, the next
color/control operand is packed into one nibble. The transform expands those
nibbles back into ordinary byte-sized picture command operands and stops after
emitting `0xff`.

`tools/agi_resources.py` implements the observed split v2 and combined v3
container formats. Local tests in `tests/test_agi_resources.py` currently
validate:

- SQ2 detection as split-directory/direct-record layout.
- GR detection as combined-directory/7-byte-record layout.
- Synthetic dictionary reset/literal/end expansion.
- Synthetic `0xf0`/`0xf2` picture-nibble expansion.
- All present GR resources expanding to their header-declared lengths.

The full GR transform census from the local parser is:

| Resource family | Direct | Dictionary | Picture nibble |
| --- | ---: | ---: | ---: |
| logic | 2 | 180 | 0 |
| picture | 0 | 0 | 186 |
| view | 0 | 247 | 0 |
| sound | 3 | 41 | 0 |

The logic disassembler now uses `tools/agi_resources.py` for payload loading.
For GR it uses AGIDATA dispatch table bases `0x0440` for actions and `0x0762`
for conditions. The GR action dispatcher supports action opcodes through
`0xb5`, but the decoded Gold Rush scripts observed so far only use action
opcodes through `0xa9`. The GR condition dispatcher compares predicate bytes
with `0x26`, but only entries `0x00..0x12` are structured condition-table
records in the observed `AGIDATA.OVL`; bytes above that overlap string/data and
are not treated as confirmed predicates. Local GR scripts observed so far use
condition opcodes only through `0x0e`.

## Resource cache records

The four resource families keep separate singly linked cache lists. In every
observed record, word `+0x00` is the next-record pointer. The lookup helpers
walk the list for a matching resource number and also leave an insertion/link
slot in a family-specific global so the loader can append a miss without
rescanning.

| Resource type | Root and insertion state | Lookup | Record size | Record fields |
| --- | --- | --- | ---: | --- |
| Logic | root `[0x0977]`, previous-link slot `[0x0983]` | `0x110f` | 10 bytes | `+0x00` next, `+0x02` logic number byte, `+0x03` message count byte, `+0x04` bytecode pointer (`payload + 2`), `+0x06` current instruction pointer, `+0x08` message offset table pointer |
| View | root `[0x0ffa]`, previous-link slot `[0x1000]` | `0x3979` | 5 bytes | `+0x00` next, `+0x02` view number byte, `+0x03` payload pointer |
| Picture | static first record/root `[0x120e]`, previous-link slot `[0x1214]` | `0x49e8` | 5 bytes | `+0x00` next, `+0x02` picture number byte, `+0x03` payload pointer |
| Sound | static first record/root `[0x125a]`, previous-link slot `[0x1268]` | `0x50d8` | 14 bytes | `+0x00` next, `+0x02` sound number word, `+0x04` payload pointer, `+0x06`/`+0x08`/`+0x0a`/`+0x0c` channel stream pointers |

View loader `0x39f7` allocates a 5-byte cache record on a miss and writes it
through the link slot left in `[0x1000]`. Picture loader `0x4a3b` and sound
loader `0x5126` use their static first records when the previous-link slot is
zero, then allocate later records (`5` bytes for pictures and `14` bytes for
sounds). Sound loader `0x5126` derives the four channel stream pointers by
reading the first four little-endian words in the payload and adding each offset
to the payload base.

Early payload observations from these loaders:

- Logic payloads begin with a little-endian offset. Loader `0x119a` treats
  `payload + 2` as an instruction/data pointer, reads the first two payload
  bytes as a little-endian offset, then reads one byte at
  `payload + 2 + offset` into the logic cache record.
- Sound loader `0x5126` reads the first four little-endian words in the sound
  payload as offsets relative to the payload base and stores four derived
  pointers in its cache record.
- View and picture loaders store the returned payload pointer directly in their
  cache records. Later graphics/object routines parse view group/frame tables
  and picture command streams as described in
  [Graphics and Object Pipeline](./graphics_object_pipeline.md).
