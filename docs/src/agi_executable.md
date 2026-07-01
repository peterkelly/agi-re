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
| `0x5cce` | `AH=3d` | Open file. Takes path pointer in `DX` and mode in `AL`; returns `0xffff` on carry/error. |
| `0x5cef` | `AH=3f` | Read file. Takes handle in `BX`, buffer in `DS:DX`, byte count in `CX`; returns zero on carry/error. |
| `0x5d12` | `AH=40` | Write file. Takes handle in `BX`, buffer in `DS:DX`, byte count in `CX`; returns zero on carry/error. |
| `0x5d52` | `AH=3e` | Close file handle in `BX`. |
| `0x5d6b` | `AH=42` | Seek. Takes handle in `BX`, offset in `CX:DX`, origin in `AL`; returns `0xffff:0xffff` on carry/error. |

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

