# Resource Containers

AGI game data is divided into four resource families:

| Family | Purpose |
| --- | --- |
| Logic | Executable game bytecode and its messages. |
| Picture | Commands that construct the room's visual and priority/control surfaces. |
| View | Animated cel images used for actors, objects, and previews. |
| Sound | Timed tone and attenuation events. |

Within a family, bytecode addresses a resource by an unsigned 8-bit resource
number. A directory maps that number to a volume file and byte offset. Loading
a resource removes its volume-record header and, when required by the profile,
expands its stored representation before passing the payload to the
family-specific decoder.

All 16-bit integers in the container formats are little-endian.

## Directory entries

Both current container profiles use three-byte directory entries:

```text
volume = entry[0] >> 4
offset = ((entry[0] & 0x0f) << 16) | (entry[1] << 8) | entry[2]
```

The volume occupies the high nibble of the first byte. The remaining 20 bits
form a big-endian byte offset within that volume.

Each profile defines its own absent-entry rule. A conforming engine must apply
the rule for the selected profile before attempting to open a volume.

## Version 2 split container

The split container uses one directory file per family:

| Family | Directory file |
| --- | --- |
| Logic | `LOGDIR` |
| Picture | `PICDIR` |
| View | `VIEWDIR` |
| Sound | `SNDDIR` |

Each complete three-byte group in a directory is one resource entry. An entry
is absent when the high nibble of its first byte is `0xf`. Consequently,
`ff ff ff` is absent, but it is not the only byte pattern treated as absent.

Volume files are named `VOL.N`, where `N` is the decoded volume number. A
resource record at the directory offset has this five-byte header:

| Byte | Meaning |
| ---: | --- |
| `0` | Magic byte `0x12`. |
| `1` | Magic byte `0x34`. |
| `2` | Volume number; must match the directory entry. |
| `3..4` | Payload length. |

The header is followed by exactly `payload length` bytes. The split profile
does not transform those bytes: the stored payload is the expanded resource
payload.

### Inventory metadata file

The profile's inventory metadata file is XOR-decoded byte for byte with the
repeating ASCII key:

```text
Avis Durgan
```

The decoded bytes have this form:

```text
item_table_size:u16le
maximum_drawable_object_index:u8
runtime_inventory_data[]
```

`runtime_inventory_data` begins with `item_table_size / 3` item entries. The
size must be divisible by three. Each entry is:

```text
name_offset:u16le
location:u8
```

Name offsets are relative to the start of `runtime_inventory_data`. The name
pool begins at `item_table_size`; names are zero-terminated byte strings. More
than one item may refer to the same name. The one-based drawable-object record
count is `maximum_drawable_object_index + 1`.

For the observed 2.936 game data, the header is `78 00 14`: 40 inventory
entries occupy 120 bytes and 21 drawable-object records are available. The
complete decoded file is 331 bytes, leaving 328 runtime bytes after the header.

## Version 3 combined container

The combined container uses a game-specific filename prefix `P`. Its primary
directory is named `PDIR`, and its volumes are named `PVOL.N`. For example, a
prefix of `GR` produces `GRDIR` and `GRVOL.N`.

The first eight bytes of the combined directory are four section offsets:

| Bytes | Section |
| ---: | --- |
| `0..1` | Logic entries. |
| `2..3` | Picture entries. |
| `4..5` | View entries. |
| `6..7` | Sound entries. |

The logic section extends from its offset to the picture offset, the picture
section to the view offset, the view section to the sound offset, and the sound
section to end of file. Each section is an array of three-byte directory
entries. In this profile, only the exact sequence `ff ff ff` denotes an absent
resource.

If the combined directory cannot be opened, this profile falls back to the
four split directory filenames. This fallback changes directory discovery but
does not change the seven-byte volume-record format below.

### Volume record

A combined-profile volume record has this header:

| Byte | Meaning |
| ---: | --- |
| `0` | Magic byte `0x12`. |
| `1` | Magic byte `0x34`. |
| `2` | Volume metadata. Bit `0x80` selects picture-nibble expansion; the low nibble identifies the volume when that bit is set. |
| `3..4` | Expanded payload length. |
| `5..6` | Stored payload length. |

When metadata bit `0x80` is clear, the entire metadata byte must match the
directory volume number. When it is set, the metadata low nibble must match.
Exactly `stored length` bytes follow the header.

The payload transform is selected in this order:

1. If metadata bit `0x80` is set, apply picture-nibble expansion.
2. Otherwise, if stored and expanded lengths are equal, use the bytes directly.
3. Otherwise, apply dictionary expansion.

The resulting payload must contain exactly the declared expanded length.

## Dictionary expansion

Dictionary-compressed data is a least-significant-bit-first stream of variable
width codes. Codes do not have to begin on byte boundaries. A valid compressed
resource begins with reset code `0x100`.

| Code | Meaning |
| ---: | --- |
| `0x000..0x0ff` | One literal byte. |
| `0x100` | Reset the dictionary and code width. |
| `0x101` | End the expanded stream. |
| `0x102` and above | Dictionary entries. |

After reset, the code width is 9 bits and the next dictionary index is
`0x102`. The first non-end code after reset is expanded and emitted without
adding an entry.

For each later ordinary code:

1. Expand the code to its byte string. The special next-code case expands to
   the previous string followed by the previous string's first byte.
2. Emit the expanded string.
3. Add `previous string + first byte of current string` at the next dictionary
   index.
4. Advance the next index and make the current string the previous string.

When the next index reaches `0x200`, increase the code width to 10 bits. When
it reaches `0x400`, increase the width to 11 bits. A reset returns the width to
9 bits, clears generated entries, and restores the next index to `0x102`.

Expansion ends at code `0x101`. For a valid record, the number of emitted bytes
equals the expanded length in the volume header.

## Picture-nibble expansion

The picture transform packs an expanded picture command stream as a sequence
of nibbles. Nibbles are stored high nibble first within each byte.

Ordinary expanded bytes use two nibbles: high nibble followed by low nibble.
The color operand immediately following picture command `0xf0`, and the
control-color operand immediately following command `0xf2`, use only one
nibble. After that operand, ordinary two-nibble decoding resumes.

For example:

```text
stored:   f0 af 2b ff
expanded: f0 0a f2 0b ff
```

Expansion stops after emitting command `0xff`. A low zero nibble may pad the
stored stream when the meaningful nibble count is odd. The emitted byte count
must equal the expanded length in the volume header.

## Valid-data boundary

This chapter defines valid resource lookup and expansion. It does not specify
behavior for offsets outside a volume, incorrect magic, mismatched volume
metadata, truncated records, unknown dictionary codes, or expansion beyond the
declared length. Such data is not part of the current compatibility target.
