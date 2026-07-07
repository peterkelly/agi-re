# SIERRA.COM loader decompilation notes

This note summarizes the current clean-room understanding of `SQ2/SIERRA.COM`.
Current tooling derives this path from an explicitly selected game directory,
not from a repository-default SQ2 copy.
It is derived from local bytes, `ndisasm`, Rizin output, and the reproducible
transform in `tools/decrypt_agi.py`.

## Address model

`SIERRA.COM` is a DOS COM file. File offset `0x0000` is loaded at memory offset
`0x0100`, so memory offset = file offset + `0x0100`.

The first instruction is `e9 9d 02`, a near jump from memory `0x0100` to memory
`0x03a0`. The loader body therefore begins at file offset `0x02a0`.

## Key internal variables

These names are provisional and based on observed use:

| Memory offset | Provisional name | Evidence |
| --- | --- | --- |
| `0x036d` | `file_handle` | Written after DOS open and later used for read/close. |
| `0x0371` | `agi_load_segment` | Written after DOS memory allocation; used as the segment into which `AGI` is read. |
| `0x0373` | `agi_loaded_paragraphs` | Cleared before loading `AGI`; incremented by rounded-up read byte counts. |
| `0x0375` | `next_read_segment` | Starts as `agi_load_segment` and advances during file reads. |
| `0x037a` | `command_tail_copy` | Receives PSP bytes from `0x80` before the MZ jump. |
| `0x0141` | `decode_key_table` | Passed as `CS:0x0141` to the transform routine. |

## High-level loader flow

Pseudocode:

```text
entry:
    disable_interrupts()
    SS = CS
    SP = 0x02c1
    enable_interrupts()

    install_critical_error_handler()
    copy PSP command tail from 0x80 to command_tail_copy

    perform_machine_or_memory_setup()
    save_video_state()

    agi_load_segment = allocate_largest_available_dos_block()

retry_files:
    if not load_file_to_segments("agi", agi_load_segment):
        display("Can't find the file 'agi'...")
        key = wait_for_enter_or_escape()
        if key == Enter:
            goto retry_files
        else:
            goto exit

    if not can_open("agidata.ovl"):
        display("Can't find the file 'agidata.ovl'...")
        key = wait_for_enter_or_escape()
        if key == Enter:
            goto retry_files
        else:
            goto exit

    decode_loaded_agi()
    mark_graphics_check_flag()
    load_and_jump_to_mz_image()

exit:
    restore_critical_error_handler()
    set_cursor_position(row=0x18, col=0)
    dos_exit()
```

The loader only checks that `agidata.ovl` exists. It does not load that file
before transferring control to the transformed MZ executable.

## File loading routine

The routine at memory `0x0415`:

```text
load_file_to_segments(path_dx, agi_load_segment):
    handle = dos_open_readonly(path_dx)
    if open_failed:
        return carry_set

    agi_loaded_paragraphs = 0
    next_read_segment = agi_load_segment

    loop:
        bytes_read = dos_read(handle, segment=next_read_segment, offset=0,
                              count=0xfe00)
        if read_failed:
            return carry_set
        if bytes_read == 0:
            break

        paragraphs = (bytes_read + 0x0f) >> 4
        agi_loaded_paragraphs += paragraphs
        next_read_segment += paragraphs
        if next_read_segment != 0:
            continue loop

    dos_close(handle)
    return carry_clear
```

The separate routine at memory `0x045f` only opens and closes a file to test
existence.

## AGI decode routine

The call at memory `0x08fc` prepares:

```text
source_start_segment = agi_load_segment
source_end_segment = agi_load_segment + agi_loaded_paragraphs
key_segment = CS
key_offset = 0x0141
call transform(source_start_segment, source_end_segment, key_segment, key_offset)
```

The transform routine at memory `0x09f4`:

```text
carry = 0
source_segment = source_start_segment

while source_segment < source_end_segment:
    DS = source_segment
    ES = key_segment
    SI = 0
    DI = key_offset

    repeat 128 times:
        key_byte = ES[DI]
        DS[SI] = DS[SI] XOR key_byte
        SI += 1

        rotated_key_byte = rotate_right_through_carry(key_byte, carry)
        carry = low_bit(key_byte)
        ES[DI] = rotated_key_byte
        DI += 1

    DI = key_offset
    if carry:
        ES[DI] = ES[DI] OR 0x80

    source_segment += 8
```

Applying this transform to the selected SQ2 `AGI` with the key table from
`SIERRA.COM` file offset `0x0041` produces
`build/cleanroom/AGI.decrypted.exe`, a valid DOS MZ executable.

## MZ transfer routine

The routine at memory `0x0c46` treats the decoded `AGI` image as an MZ
executable:

```text
image = agi_load_segment:0000
if image[0:2] != "MZ":
    display("Bad program image.")
    exit

psp_segment = agi_load_segment
load_base = psp_segment + 0x10
source_image_segment = psp_segment + image.header_paragraphs

entry_cs = load_base + image.initial_cs
entry_ip = image.initial_ip
entry_ss = load_base + image.initial_ss
entry_sp = image.initial_sp

for each relocation entry:
    relocation_segment = source_image_segment + relocation.segment
    relocation_offset = relocation.offset
    word_at_relocation += load_base

copy executable image from source_image_segment to load_base
dos_set_psp(psp_segment)
SS:SP = entry_ss:entry_sp
copy command_tail_copy back to PSP:0x80
DS = psp_segment
far_jump(entry_cs:entry_ip)
```

Header values recovered from the decoded image:

| Field | Value |
| --- | --- |
| Signature | `MZ` |
| Blocks/pages | `0x004d` |
| Relocations | `0x0021` |
| Header paragraphs | `0x0020` |
| Minimum extra paragraphs | `0x0271` |
| Maximum extra paragraphs | `0xffff` |
| Initial SS:SP | `0x0be9:0x0080` |
| Initial CS:IP | `0x0000:0x6777` |
| Relocation table offset | `0x001c` |

## Decrypted executable observations

The decoded image begins with visible interpreter identity text at file offset
`0x0200`:

```text
Adventure Game Interpreter
Copyright (C) 1984, 1985, 1986 Sierra On-Line, Inc.
Authors: Jeff Stephenson & Chris Iden
```

The decoded image also contains local overlay/file names near file offsets
`0x9986` through `0x99eb`:

```text
CGA_GRAF.OVL
JR_GRAF.OVL
EGA_GRAF.OVL
HGC_GRAF.OVL
VG_GRAF.OVL
IBM_OBJS.OVL
HGC_OBJS.OVL
AGIDATA.OVL
AGI.EXE
```
