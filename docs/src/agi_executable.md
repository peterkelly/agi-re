# Decrypted AGI executable notes

This page records observations from `build/cleanroom/AGI.decrypted.exe`, the
MZ image reproduced from local `SQ2/AGI` bytes by `tools/decrypt_agi.py`.

## Address model

The decrypted file is a DOS MZ executable with `header_paragraphs = 0x20`.
Therefore file offset `0x0200` maps to runtime image offset `0x0000`.

In this note:

- `file offset` means an offset in `build/cleanroom/AGI.decrypted.exe`.
- `image offset` means `file offset - 0x0200`.
- Segment constants in the executable are MZ-relocated at load time. The values
  shown here are the pre-relocation values as stored in the decrypted image.

## Startup overlay load

The MZ entry point is `CS:IP = 0000:6777`.

The entry routine at image offset `0x6777` performs a two-stage startup:

```text
temporary_ss = 0x0be9 + (0x0080 >> 4)
temporary_sp = ((0x0be9 - 0x0a01) << 4) + 0x1000
SS:SP = temporary_ss:temporary_sp

save caller ES
DS = temporary_ss
ES = temporary_ss
load_overlay(8)
restore caller ES

SS:SP = 0x0be9:0x1000
DS = 0x0a01
[0x16af] = DS
[0x16b1] = caller ES
ES = DS
[0x16ab] = 0x0be9
jump 0x0078
```

The important point is that overlay number 8 is loaded before the program
switches `DS` to `0x0a01`. Overlay 8 is `AGIDATA.OVL`, so the interpreter's
main data segment is populated from that file before the main startup body at
image offset `0x0078` runs.

## DOS file wrappers

Several small routines wrap DOS interrupt `21h` file services:

| Image offset | DOS function | Observed behavior |
| --- | --- | --- |
| `0x5cad` | `AH=3c` | Create/truncate file. Takes path pointer in `DX` and attributes in `CX`; returns `0xffff` on carry/error. The byte at `0x5cac` is padding before the prologue. |
| `0x5cce` | `AH=3d` | Open file. Takes path pointer in `DX` and mode in `AL`; returns `0xffff` on carry/error. |
| `0x5cef` | `AH=3f` | Read file. Takes handle in `BX`, buffer in `DS:DX`, byte count in `CX`; returns zero on carry/error. |
| `0x5d12` | `AH=40` | Write file. Takes handle in `BX`, buffer in `DS:DX`, byte count in `CX`; returns zero on carry/error. |
| `0x5d35` | `AH=41` | Delete file. Takes path pointer in `DX`; returns zero on carry/error. |
| `0x5d52` | `AH=3e` | Close file handle in `BX`. |
| `0x5d6b` | `AH=42` | Seek. Takes handle in `BX`, offset in `CX:DX`, origin in `AL`; returns `0xffff:0xffff` on carry/error. |
| `0x5d94` | `AH=45` | Duplicate file handle in `BX`; returns `0xffff` on carry/error. |
| `0x5db2` | `AH=47` | Get current directory for the default drive into caller buffer after first writing a leading backslash. If the returned path contains `/`, the helper writes `/` over the first byte, so slash normalization remains a little odd and should be rechecked dynamically. |
| `0x5dea` | `AH=19` | Return current drive as a lowercase letter by adding `0x61` to DOS's zero-based drive number. |
| `0x5e01` | `AH=1a`, then `AH=4e` | Set the DTA pointer from the third argument, then perform find-first with pattern pointer in `DX` and attributes in `CX`; returns `0xffff` on carry/error. |
| `0x5e26` | `AH=4f` | Find-next using the current DTA; returns `0xffff` on carry/error. |
| `0x5e3e` | `AH=19`, `AH=0e`, `AH=19`, `AH=0e` | Probe whether a lowercase drive letter can be selected. It saves the current drive, tries to set the requested drive, checks whether DOS reports that drive as current, restores the original drive, and returns 1 on success or 0 on failure. |
| `0x5e73` | `AH=57`, `AL=0` | Get file date/time for handle `BX`; returns the time word in `CX`. |

Before most file-service calls, helper `0x5e8d` temporarily switches `DS` to
segment `0x0a01` and clears word `[0x184d]`. The exact meaning of that global
is still open.

The helper at image offset `0x5b49` compares absolute buffer `0x0002` against
the embedded string `SQ2\0` at image offset `0x5b6c`, calling helper `0x02ae`
on mismatch. It is reached by logic action handler `0x0e7e`.

The helper at image offset `0x5b73` formats savegame-like names with the local
format string at data offset `0x132c`, `%s%s%ssg.%d`. Nearby local strings
include slash/backslash separators at `0x1327`, `0x1328`, and `0x135f`, plus
the user-facing example `(For example, "B:" or "C:\savegame")` at `0x1339`.

The helper at image offset `0x5bdd` validates or probes a user-supplied path:
it trims leading spaces, fills an empty path with the current directory helper
`0x5db2`, strips a trailing slash/backslash except for one-character paths,
records a drive-like letter in byte `[0x1363]`, tests bare separators and
drive-only strings specially, and otherwise calls the find-first wrapper
`0x5e01` with attribute mask `0x10`. It returns 1 for accepted/probed paths and
0 for failure.

## Save/restore state file

Logic actions `0x7d` (`save_game_state`) and `0x7e` (`restore_game_state`) are the observed save and restore paths. Both
use helper `0x85e5` to select or prepare a target slot/path and use the
savegame filename buffer at `0x1c8c`.

Save action `0x7d` (`save_game_state`) at image offset `0x2753`:

1. Sets word `[0x0615] = 1` and temporarily changes byte `[0x0d15]` to `0x40`.
2. Calls `0x85e5(0x73)`.
3. If byte `[0x0e72]` is zero, formats and displays confirmation text rooted at
   `0x0db6`, then waits through helper `0x4618`.
4. Creates file `0x1c8c` through DOS wrapper `0x5cad`.
5. Writes 31 raw bytes from `0x1c6c`.
6. Writes length-prefixed blocks through helper `0x28c6`.

Helper `0x28c6(handle, pointer, length)` writes:

```text
u8 length_low
u8 length_high
length bytes from pointer
```

The observed save blocks are:

| Source pointer | Length source | Observed role |
| ---: | ---: | --- |
| `0x05e1` | `0x0002` | Small global state block; exact fields still open. |
| `[0x096b]` | `[0x096f]` | Object table bytes. |
| `[0x0971]` | `[0x0975]` | Three-byte entry table bytes. |
| `[0x1707]` | `[0x0141] * 2` | Word table whose active count is stored in `[0x0141]`. |
| `0x0985` | return value from `0x1364` | Heap or interpreter-state region sized by helper `0x1364`. |

Restore action `0x7e` (`restore_game_state`) at image offset `0x2512`:

1. Sets word `[0x0615] = 1` and temporarily changes byte `[0x0d15]` to `0x40`.
2. Calls `0x85e5(0x72)`.
3. If byte `[0x0e72]` is zero, formats and displays confirmation text rooted at
   `0x0d34`, then waits through helper `0x4618`.
4. Opens file `0x1c8c` through DOS wrapper `0x5cce`.
5. Seeks to offset `0x1f` from the start of the file, skipping the raw
   description/header.
6. Reads length-prefixed blocks through helper `0x26b0`.

Helper `0x26b0(handle, destination)` reads a little-endian 16-bit length from
two one-byte reads, then reads that many bytes into `destination`, returning 1
only when all reads return the requested byte count.

The observed restore destinations mirror the saved blocks:

```text
0x0002
[0x096b]
[0x0971]
[0x1707]
0x0985
```

Local strings in `AGIDATA.OVL` confirm the path roles: `0x0d34` starts
`About to restore the game`, `0x0d73` starts `Can't open file`, `0x0d87` starts
`Error in restoring game`, `0x0db6` starts `About to save the game`, and
`0x0e46` is the save-error display path.

## Overlay loader

The routine at image offset `0x67c3` loads one numbered overlay.

Pseudocode:

```text
load_overlay(number):
    saved_ds = DS
    DS = relocated_segment(0x0970)

    descriptor = 0x0004 + (number - 1) * 0x10

    handle = dos_open(path = DS:[descriptor + 0x08], mode = 0)
    saved_handle = handle

    byte_count = DS:[descriptor + 0x0e] << 4
    destination_segment = DS:[descriptor + 0x04]

    BX = handle
    CX = byte_count
    DX = 0
    DS = destination_segment
    dos_read(BX, DS:DX, CX)

    dos_close(saved_handle)
    DS = saved_ds
```

There is no observed check of the read byte count in this routine. It asks DOS
to read the descriptor-provided maximum byte count and then closes the file.

## Overlay descriptor table

The overlay table is in the decrypted executable at file offset `0x9900`, image
offset `0x9700`. The first descriptor starts at image offset `0x9704`. Each
descriptor is 16 bytes.

Observed fields used by `load_overlay`:

| Descriptor offset | Meaning |
| --- | --- |
| `+0x04` | Destination segment. |
| `+0x08` | Filename offset inside the overlay-table segment. |
| `+0x0e` | Maximum read size in paragraphs; byte count is this value shifted left four bits. |

Other descriptor words are not yet fully explained. The word at `+0x06`
matches the destination segment plus the paragraph count for overlays 1-7. For
overlay 8 it is `0x0bf1`, while destination plus paragraph count is `0x0be9`;
this may be related to the temporary stack used during startup, but that remains
only a hypothesis.

Parsed descriptors:

| Number | File | Destination segment | Word `+0x06` | Name offset | Paragraph count | Max bytes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `CGA_GRAF.OVL` | `0x0980` | `0x09ab` | `0x0086` | `0x002b` | `0x02b0` |
| 2 | `JR_GRAF.OVL` | `0x0980` | `0x099e` | `0x0093` | `0x001e` | `0x01e0` |
| 3 | `EGA_GRAF.OVL` | `0x0980` | `0x09a5` | `0x009f` | `0x0025` | `0x0250` |
| 4 | `HGC_GRAF.OVL` | `0x0980` | `0x09db` | `0x00ac` | `0x005b` | `0x05b0` |
| 5 | `VG_GRAF.OVL` | `0x0980` | `0x0997` | `0x00b9` | `0x0017` | `0x0170` |
| 6 | `IBM_OBJS.OVL` | `0x09db` | `0x09f1` | `0x00c5` | `0x0016` | `0x0160` |
| 7 | `HGC_OBJS.OVL` | `0x09db` | `0x0a01` | `0x00d2` | `0x0026` | `0x0260` |
| 8 | `AGIDATA.OVL` | `0x0a01` | `0x0bf1` | `0x00df` | `0x01e8` | `0x1e80` |

The filename offsets are relative to the table segment. For example, descriptor
8 has name offset `0x00df`, and the table segment begins at image offset
`0x9700`, so the string `AGIDATA.OVL` is at image offset `0x97df`.

## Command-line flags observed so far

The routine at image offset `0x00c4` reads the PSP command tail through the
segment saved at `[0x16b1]`. It scans for `-` followed by a single lower-case
letter and stores mode values in the interpreter data segment through `ES`.

Observed flags:

| Flag | Store |
| --- | --- |
| `-c` | `[0x1130] = 0` |
| `-r` | `[0x1130] = 1` |
| `-e` | `[0x1130] = 3` |
| `-h` | `[0x1130] = 2` |
| `-v` | `[0x1130] = 4` |
| `-p` | `[0x112e] = 0` |
| `-t` | `[0x112e] = 2` |
| `-s` | `[0x112e] = 8` |

The meanings of these variables are not fully proven yet. However, the overlay
selection routine below uses these locations to choose graphics and object
overlays.

## Graphics and object overlay selection

The routine at image offset `0x821c` chooses and loads two overlays using
`load_overlay`.

Pseudocode from observed control flow:

```text
saved_value = call 0x5a74()
[0x1807] = saved_value

if [0x1130] == 2:
    object_overlay = 7        # HGC_OBJS.OVL
    graphics_overlay = 4      # HGC_GRAF.OVL
else:
    object_overlay = 6        # IBM_OBJS.OVL

    if [0x1130] == 3:
        graphics_overlay = 3  # EGA_GRAF.OVL
    else if [0x1130] == 4:
        graphics_overlay = 5  # VG_GRAF.OVL
    else if [0x112e] == 0:
        graphics_overlay = 1  # CGA_GRAF.OVL
    else:
        graphics_overlay = 2  # JR_GRAF.OVL

load_overlay(graphics_overlay)
load_overlay(object_overlay)
call 0x5528()
```

This proves that `AGIDATA.OVL` is loaded during executable startup, while the
selected graphics and object overlays are loaded later by normal interpreter
initialization code.
