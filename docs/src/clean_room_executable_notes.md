# Clean-room executable notes

This file records local observations made while inspecting the Space Quest 2
files in this repository. No external AGI documentation, source code, or prior
AGI-specific knowledge is used here.

## 2026-07-01: initial executable inventory

Commands run from `/Users/peter/ai/agi/reverse`:

- `cat AGENTS.md`
- `rg --files`
- `ls -la`
- `git status --short`
- `ls -l SQ2`
- `file SQ2/SIERRA.COM SQ2/AGI SQ2/AGIDATA.OVL SQ2/EGA_GRAF.OVL SQ2/IBM_OBJS.OVL SQ2/VOL.0 SQ2/LOGDIR`
- `xxd -l 256 -g 1 SQ2/SIERRA.COM`
- `xxd -l 256 -g 1 SQ2/AGI`
- `command -v objdump ndisasm r2 rizin ghidraRun retdec-decompiler llvm-objdump strings dosbox qemu-system-i386`
- `strings -a -t x SQ2/SIERRA.COM`
- `strings -a -t x SQ2/AGI`
- `xxd -s 0x2a0 -l 512 -g 1 SQ2/SIERRA.COM`
- `python3 -c "import capstone; print(capstone.__version__)"`
- `python3 -c "import distorm3; print(distorm3.__version__)"`
- `python3 -c "import iced_x86; print(iced_x86.__version__)"`
- `python3 --version`
- `which gobjdump nasm ndisasm radare2 rizin`

Local tooling result:

- `/usr/bin/objdump` and `/usr/bin/strings` are present.
- The installed `objdump` rejects `-b`, so it cannot directly disassemble a raw
  DOS COM binary in the usual GNU objdump style.
- `ndisasm`, `r2`, `rizin`, `ghidraRun`, `retdec-decompiler`,
  `qemu-system-i386`, and DOSBox were not found on PATH.
- Python 3.14.6 is present, but `capstone`, `distorm3`, and `iced_x86` are not
  installed.

File inventory observations:

- `SQ2/SIERRA.COM` is 3,121 bytes and `file` identifies it as a DOS executable
  COM file.
- `SQ2/AGI` is 39,424 bytes and `file` identifies it only as `data`.
- Several overlay files exist. `file` identifies at least `EGA_GRAF.OVL` and
  `IBM_OBJS.OVL` as DOS executable COM-like data.
- `SQ2/SIERRA.COM` begins with bytes `e9 9d 02`, an 8086 near jump in a COM
  program. With the COM load origin at offset `0x100`, this jumps from memory
  `0x0100` to memory `0x03a0`, corresponding to file offset `0x02a0`.
- The bytes immediately after that jump contain text:
  `LOADER v3.0  (c) Copyright Sierra On-Line, Inc.  1987`, followed by
  `keyOfs8`.
- `SQ2/AGI` begins with high-entropy-looking bytes and has no obvious header in
  the first 256 bytes.

Loader string observations from `strings -a -t x SQ2/SIERRA.COM`:

- File-related strings include `agi` at file offset about `0x01c1` and
  `agidata.ovl` at file offset `0x01c5`.
- Error/retry strings include:
  - `Can't find the file 'agi'.`
  - `Can't find the file 'agidata.ovl'.`
  - `Press Enter to try again.`
  - `Press ESC to quit.`
- Display-adapter messages mention color/graphics and Hercules-compatible
  adapters.
- Disk-prompt strings mention an original disk and a play disk.
- Later strings include `Bad program image.` and a nearby byte sequence that
  includes `MZ`, suggesting a check or message related to an executable image.

Initial loader code observations from bytes at file offset `0x02a0`:

- The loader disables interrupts, sets `SS` to `CS`, sets `SP` to a low internal
  offset, and re-enables interrupts.
- It copies the DOS PSP command tail from memory offset `0x80` to an internal
  buffer near memory offset `0x037a`.
- It calls code that attempts to open `agi`, and if that fails it displays the
  local retry/quit prompt strings and reads keyboard input.
- It similarly has a path for opening `agidata.ovl`.
- A visible subroutine beginning at file offset `0x0310` performs DOS interrupt
  `21h` calls with AH values matching open/read/close style operations based on
  the local byte sequence:
  - `b4 3d cd 21`
  - `b4 3f cd 21`
  - `b4 3e cd 21`

Current working hypotheses to verify:

- `SIERRA.COM` is a loader rather than the main interpreter.
- `AGI` is likely packed, encrypted, relocated, or otherwise transformed by
  `SIERRA.COM` before execution.
- The `keyOfs8` text and adjacent bytes may relate to the transformation of
  `AGI`.
- `AGIDATA.OVL` may contain additional runtime data loaded by the loader.

## 2026-07-01: loader transform reproduced

Additional tools installed by the user:

- `nasm` / `ndisasm`
- `rizin`

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `command -v nasm ndisasm rizin r2 radare2`
- `ndisasm -v`
- `rizin -v`
- `python3 tools/decrypt_agi.py`
- `ndisasm -b 16 -o 0x3a0 -e 0x2a0 SQ2/SIERRA.COM`
- `ndisasm -b 16 -o 0x6777 -e 0x6977 build/cleanroom/AGI.decrypted.exe`
- `rizin -q -e scr.color=false -A -c iH -c ie -c iS -c iz -c q build/cleanroom/AGI.decrypted.exe`
- `strings -a -t x build/cleanroom/AGI.decrypted.exe`
- `rizin -q -e scr.color=false -A -c afl -c q build/cleanroom/AGI.decrypted.exe`
- `rizin -q -e scr.color=false -A -c izz -c q build/cleanroom/AGI.decrypted.exe`
- Commands above were also re-run with shell redirection to preserve derived
  disassembly and Rizin output under `build/cleanroom/`.

Derived local artifacts:

- `tools/decrypt_agi.py`
- `build/cleanroom/AGI.decrypted.exe`
- `build/cleanroom/SIERRA.COM.entry.ndisasm`
- `build/cleanroom/AGI.decrypted.entry.ndisasm`
- `build/cleanroom/AGI.decrypted.rizin-info.txt`
- `build/cleanroom/AGI.decrypted.rizin-functions.txt`
- `build/cleanroom/AGI.decrypted.rizin-strings.txt`

Important `ndisasm` confirmations from `SIERRA.COM`:

- Loader entry at memory `0x03a0`, file offset `0x02a0`.
- `0x03c7` loads the string at memory `0x02c1` (`agi`) into `DX`; `0x03cb`
  calls `0x0415`, the open/read/close loader routine.
- `0x03e0` loads the string at memory `0x02c5` (`agidata.ovl`) into `DX`;
  `0x03e4` calls `0x045f`, which opens and immediately closes the file. This
  means the loader checks for `AGIDATA.OVL` but does not load it at this stage.
- `0x03f9` calls `0x08fc`, which prepares arguments for the transform routine.
- `0x08fc` computes an end segment from `[0x0371] + [0x0373]`, passes the
  loader key table address `CS:0x0141`, and calls `0x09f4`.
- `0x09f4` performs the observed transform:
  - Source segment begins at `[0x0371]`.
  - End segment is `[0x0371] + [0x0373]`.
  - Key table is `ES:DI`, called as `CS:0x0141`.
  - For each byte, it loads the key byte, XORs the source byte in place,
    rotates the key byte right through carry (`rcr al,1`), and stores the
    updated key byte back.
  - It processes 128 bytes per source segment pass, advances the source segment
    by 8 paragraphs, and preserves carry across passes.
- `0x0c46` validates that the transformed image begins with MZ, applies
  relocation entries, copies the executable image down from its MZ header
  location, prepares PSP state, sets `SS:SP`, copies the command tail, and far
  jumps to the MZ entry point.

Reproduced transform result:

- `tools/decrypt_agi.py` applies the observed transform to `SQ2/AGI`.
- The result starts with `4d 5a`, an MZ signature.
- `file build/cleanroom/AGI.decrypted.exe` reports `MS-DOS executable`.
- Header values printed by the script and confirmed by Rizin:
  - `last_page_bytes = 0x0000`
  - `pages = 0x004d`
  - `relocations = 0x0021`
  - `header_paragraphs = 0x0020`
  - `minalloc = 0x0271`
  - `maxalloc = 0xffff`
  - `initial_ss = 0x0be9`
  - `initial_sp = 0x0080`
  - `initial_ip = 0x6777`
  - `initial_cs = 0x0000`
  - `relocation_table = 0x001c`

Strings recovered from the decrypted MZ image:

- At file offset `0x0200`, the image contains:
  `Adventure Game Interpreter`, copyright text, and author text.
- Near file offsets `0x9986` through `0x99eb`, the image contains overlay/file
  names:
  - `CGA_GRAF.OVL`
  - `JR_GRAF.OVL`
  - `EGA_GRAF.OVL`
  - `HGC_GRAF.OVL`
  - `VG_GRAF.OVL`
  - `IBM_OBJS.OVL`
  - `HGC_OBJS.OVL`
  - `AGIDATA.OVL`
  - `AGI.EXE`

## 2026-07-01: decrypted executable startup and overlays

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -c ...` one-off local parsers over
  `build/cleanroom/AGI.decrypted.exe` to print MZ relocation entries and the
  overlay descriptor table.
- `xxd -s 0x9900 -l 256 -g 1 build/cleanroom/AGI.decrypted.exe`
- `rizin -q -e scr.color=false -A -c 'pD ...' ... build/cleanroom/AGI.decrypted.exe`
  over focused address ranges around `0x00c4`, `0x5cce`, `0x5cef`, `0x5d12`,
  `0x5d52`, `0x5d6b`, `0x6777`, `0x67c3`, and `0x821c`.
- `xxd` and small Python byte dumps over `SQ2/AGIDATA.OVL` to compare loaded
  data offsets with strings observed in the executable.

Documented result:

- Added `docs/src/agi_executable.md`.
- The decrypted executable starts at image offset `0x6777`, loads overlay 8
  (`AGIDATA.OVL`) through a generic overlay loader at image offset `0x67c3`,
  then switches `DS` to segment `0x0a01` and jumps to image offset `0x0078`.
- The overlay descriptor table begins at file offset `0x9900`, image offset
  `0x9700`. Descriptors are 16 bytes, with the first descriptor at image offset
  `0x9704`.
- The loader routine uses descriptor offset `+0x04` as destination segment,
  `+0x08` as filename offset within the table segment, and `+0x0e` as maximum
  read paragraph count.
- A later routine at image offset `0x821c` chooses one graphics overlay and one
  object overlay based on mode variables at `0x1130` and `0x112e`, then calls
  the same overlay loader for both.

## 2026-07-01: resource directory and volume observations

Additional commands run from `/Users/peter/ai/agi/reverse`:

- One-off local Python searches for immediate values matching AGIDATA string
  offsets such as `0x0955`, `0x0ee8`, `0x0eef`, `0x116a`, `0x1172`, `0x117a`,
  and `0x1182` in `build/cleanroom/AGI.decrypted.exe`.
- Focused Rizin disassembly around image offsets `0x3030`, `0x30f0`,
  `0x3113`, `0x42d0`, `0x4305`, `0x4371`, `0x43a5`, `0x43d9`, `0x440d`,
  and `0x4441`.
- `strings -a -t x SQ2/AGIDATA.OVL`
- `xxd -s 0x0ee0 -l 160 -g 1 SQ2/AGIDATA.OVL`
- A local Python parser over `SQ2/LOGDIR`, `SQ2/PICDIR`, `SQ2/VIEWDIR`,
  `SQ2/SNDDIR`, and `SQ2/VOL.*` to decode sampled 3-byte entries and inspect
  target bytes.
- Focused Rizin disassembly around image offsets `0x2e32`, `0x2e56`,
  `0x2f70`, `0x39f7`, `0x4a3b`, and `0x5126`.
- Rizin cross-reference checks for calls to `0x2e32`, `0x2e56`, `0x4371`,
  `0x43a5`, `0x43d9`, and `0x440d`.
- Local Python validation over all non-absent directory entries to check volume
  header magic, volume byte, payload length, and end offsets.

Documented result:

- Added `docs/src/resource_files.md`.
- The executable loads `logdir`, `picdir`, `viewdir`, and `snddir` as complete
  files via a whole-file loader at image offset `0x3113`.
- Loaded directory pointers are stored at `0x11b2`, `0x11b6`, `0x11b4`, and
  `0x11b8`.
- Directory entries are 3 bytes. The high nibble of byte 0 selects `VOL.n`, and
  the low nibble plus the next two bytes form a 20-bit offset.
- Sampled directory entries point to `VOL.*` offsets beginning with bytes
  `12 34`; the third byte in those sampled resource headers matches the decoded
  volume number.
- The generic volume reader at image offset `0x2e56` reads a 5-byte volume
  record header, validates `12 34` and the volume byte, interprets the next two
  bytes as a little-endian payload length, then reads exactly that many payload
  bytes into either a supplied destination pointer or newly allocated memory.
- The retry wrapper at image offset `0x2e32` calls `0x2e56` repeatedly until it
  succeeds or error state `[0x0f02]` becomes `5`.
- Four higher-level loaders call this generic reader through the four directory
  accessors:
  - Logic loader `0x119a`: `0x4371` then `0x2e32`.
  - View loader `0x39f7`: `0x43a5` then `0x2e32`.
  - Picture loader `0x4a3b`: `0x43d9` then `0x2e32`.
  - Sound loader `0x5126`: `0x440d` then `0x2e32`.

## 2026-07-01: logic payload structure and message decoding

Additional commands run from `/Users/peter/ai/agi/reverse`:

- Python one-off extraction of selected `LOGDIR` payloads from `VOL.*`, using
  the locally derived directory entry and volume record formats.
- `xxd -s 0x8f1 -l 80 -g 1 SQ2/AGIDATA.OVL`
- `strings -a -t x SQ2/AGIDATA.OVL`
- Focused Rizin disassembly around image offsets `0x07ab`, `0x119a`,
  `0x11e8`, and `0x21f0`.
- Corrected a segment assumption: routine `0x07ab` uses `DS:0x08f1`, which at
  runtime is `AGIDATA.OVL`, not the executable image bytes at image offset
  `0x08f1`.

Documented result:

- Added `docs/src/logic_resources.md`.
- Logic payload byte 0 and byte 1 form a little-endian bytecode length.
- The logic bytecode begins at payload offset `0x0002`.
- The byte after the bytecode is the message count.
- The message table begins one byte after the count and contains
  `message_count + 1` little-endian offsets relative to the table base.
- Message table entry 0 is used as the end pointer for the encrypted message
  area. Entries 1 through `message_count` point to individual messages.
- The message text region starts after the offset table and is XOR-decoded in
  place by image offset `0x07ab`.
- The XOR key is the zero-terminated string at `SQ2/AGIDATA.OVL` offset
  `0x08f1`: `Avis Durgan`.

## 2026-07-01: logic bytecode dispatcher

Additional commands run from `/Users/peter/ai/agi/reverse`:

- Focused Rizin and `ndisasm` disassembly around image offsets `0x02c4`,
  `0x07e3`, `0x0823`, `0x091a`, `0x293c`, and related handler ranges.
- Local Python dumps of raw executable bytes around image offsets `0x07d0`,
  `0x08f0`, and of `SQ2/AGIDATA.OVL` around data offsets `0x061d` and
  `0x08fd`.
- Local Python parser over present `LOGDIR` resources to use the derived
  action and condition operand-count tables for a conservative bytecode scan.

Documented result:

- Added `docs/src/logic_bytecode.md`.
- The main logic interpreter at image offset `0x293c` executes from
  `logic_record[0x06]`.
- Main bytecode structural opcodes:
  - `0x00` (`end`): terminate current logic execution.
  - `0xfe`: little-endian relative jump.
  - `0xff`: conditional block.
- The action dispatcher at image offset `0x02c4` uses the table at
  `DS:0x061d`, which is in `AGIDATA.OVL` at runtime.
- The condition dispatcher at image offset `0x07e3` uses the table at
  `DS:0x08fd`, also in `AGIDATA.OVL`.
- Both dispatch tables use 4-byte entries: handler image offset, fixed operand
  count, and one metadata byte.
- Condition predicates `0x01..0x06` are direct byte-variable comparisons over
  the array rooted at `DS:0x0009`.
- The condition parser uses marker bytes `0xfd`, `0xfc`, and `0xff`; the exact
  OR-group grammar around `0xfc` remains to be refined.

## 2026-07-01: condition parser and initial action families

Additional commands run from `/Users/peter/ai/agi/reverse`:

- Focused Rizin disassembly around image offsets `0x296c`, `0x7355`,
  `0x744c`, `0x74ee`, `0x09ea`, `0x7c1a`, `0x3a77`, and `0x3b47`.
- Local Python dump of selected action table entries from `SQ2/AGIDATA.OVL`
  offset `0x061d`, covering opcodes `0x01..0x11`, `0x23`, `0x25..0x27`,
  `0x29..0x2c`, and `0xa5..0xa8`.

Documented result:

- Updated `docs/src/logic_bytecode.md`.
- Refined the `0xfc` condition marker behavior. The parser uses `BH` to track
  an active OR group. A true condition inside an OR group skips the remaining
  OR terms until the closing `0xfc`; a second `0xfc` while still in an OR group
  fails the condition list.
- Identified the flag bitfield at `DS:0x0109`. Helper `0x7511` maps a flag
  number to `byte = 0x0109 + flag / 8` and `mask = 0x80 >> (flag & 7)`.
- Identified flag helpers:
  - `0x74ee`: set flag bit.
  - `0x74f4`: clear flag bit.
  - `0x74fc`: toggle flag bit.
  - `0x7502`: test flag bit.
  - `0x752a`: clear `0x20` bytes of flags starting at `0x0109`.
- Condition opcode `0x07` (`flag_set`) tests an immediate flag number; condition opcode
  `0x08` (`flag_set_var`) tests a flag number read from the byte-variable array rooted at
  `DS:0x0009`.
- Decoded variable actions:
  - `0x01` (`inc_var`): saturated increment of `var[arg0]`.
  - `0x02` (`dec_var`): saturated decrement of `var[arg0]`.
  - `0x03` (`assignn`): assign immediate to variable.
  - `0x04` (`assignv`): assign variable to variable.
  - `0x05` (`addn`)/`0x06` (`addv`): add immediate or variable.
  - `0x07` (`subn`)/`0x08` (`subv`): subtract immediate or variable.
  - `0x09` (`indirect_assignv`), `0x0a` (`assign_indirectv`), `0x0b` (`indirect_assignn`): indirect variable assignment forms.
  - `0xa5` (`muln`)/`0xa6` (`mulv`): multiply by immediate or variable, storing the low byte.
  - `0xa7` (`divn`)/`0xa8` (`divv`): divide by immediate or variable, storing the 8-bit quotient.
- Decoded flag actions:
  - `0x0c` (`set_flag`)/`0x0d` (`clear_flag`)/`0x0e` (`toggle_flag`): set, clear, or toggle an immediate flag number.
  - `0x0f` (`set_flag_var`)/`0x10` (`clear_flag_var`)/`0x11` (`toggle_flag_var`): set, clear, or toggle a flag number read from a
    variable.
- Added conservative object/view action notes:
  - `0x23` calls helper `0x0a06`, which validates a 43-byte object entry,
    copies several position/resource fields, sets bits in word field
    `[object+0x25]`, and calls list/graphics helpers.
  - `0x25` and `0x26` set position-like fields `[+0x03]`, `[+0x05]`,
    `[+0x16]`, and `[+0x18]` from immediates or variables.
  - `0x27` stores the low bytes of `[+0x03]` and `[+0x05]` into variables.
  - `0x29`, `0x2a`, `0x2b`, and `0x2c` resolve an object and dispatch to
    helpers `0x3ae7` or `0x3bb7` with either immediate or variable operands.

## 2026-07-01: additional common action handlers

Additional commands run from `/Users/peter/ai/agi/reverse`:

- Focused Rizin disassembly around image offsets `0x113d`, `0x125a`,
  `0x39b1`, `0x04d9`, `0x7e7c`, `0x6ce4`, `0x2c7a`, `0x5009`, `0x510a`,
  `0x5225`, `0x7d77`, `0x70b1`, and `0x71c0`.
- Local Python dump of selected action table entries from `SQ2/AGIDATA.OVL`
  offset `0x061d`, covering opcodes `0x14..0x17`, `0x1e..0x1f`,
  `0x21..0x22`, `0x3f..0x40`, `0x51..0x52`, `0x62..0x64`, `0x7a..0x7b`,
  `0x82`, and `0x93`.

Documented result:

- Updated `docs/src/logic_bytecode.md` with another batch of action semantics.
- Action `0x14` (`load_logic`) loads a logic resource by immediate number via `0x117d`;
  action `0x15` (`load_logic_var`) does the same with a variable-sourced number.
- Action `0x16` (`call_logic`) invokes helper `0x12ae`, which locates or loads a logic
  resource and calls the main interpreter at `0x293c` on that logic, preserving
  the previous current logic pointer at `[0x0981]`; action `0x17` (`call_logic_var`) uses a
  variable-sourced logic number.
- Actions `0x1e` (`load_view`) and `0x1f` (`load_view_var`) call the view-like resource loader `0x39f7` with
  immediate or variable-sourced resource numbers.
- Action `0x62` (`load_sound`) calls the sound-like resource loader `0x5126`, which uses the
  sound directory accessor `0x440d`, generic volume reader `0x2e32`, and builds
  four internal pointers from the payload. Action `0x64` (`stop_sound_or_clear_sound_state`) clears an active
  sound-like state through helper `0x5234`.
- Actions `0x21` (`reset_object_state`), `0x22` (`clear_all_object_bits`),
  `0x3f` (`set_global_012d`), `0x40` (`set_object_bit_0100`),
  `0x51` (`move_object_to`), `0x52` (`move_object_to_var`),
  and `0x93` (`set_object_pos_dirty`) update
  object/global state fields and object word flags. Field names remain
  provisional.
- Actions `0x7a` (`setup_transient_object`) and `0x7b` (`setup_transient_object_var`) fill globals `0x0eae..0x0eb3`, combine one operand
  into the high nibble of `0x0eb3`, then call helper `0x2d52`, which uses the
  object/resource helpers `0x3ae7`, `0x3bb7`, and `0x3ccb`.
- Action `0x82` (`random_range_to_var`) stores a generated value in a variable within an inclusive
  range. Helper `0x71c0` seeds a 16-bit state at `0x1711` from BIOS interrupt
  `1a` if needed, advances that state, and returns an 8-bit mixed value.
- Inferred the dispatch-table metadata bit rule from decoded handlers and
  table dumps. Bit 7 corresponds to operand 0, bit 6 to operand 1, and so on.
  Set bits mark variable-slot/reference operands for table-aware decoding,
  while each handler still decides whether the slot is read or written.

## 2026-07-01: local logic disassembler and input/message handlers

Additional commands run from `/Users/peter/ai/agi/reverse`:

- Added and ran `tools/disassemble_logic.py`, a local parser/disassembler for
  SQ2 logic resources using only the derived `LOGDIR`, `VOL.*`, logic payload,
  and dispatch table formats.
- `python3 tools/disassemble_logic.py 0`
- `python3 tools/disassemble_logic.py --stats`
- Focused Rizin disassembly around image offsets `0x095c`, `0x1c06`,
  `0x1ce8`, `0x0a8f`, `0x3c55`, `0x479f`, `0x7a80`, and `0x7b9c`.

Documented result:

- Updated `docs/src/logic_bytecode.md`.
- Corrected the interpretation of the `0x0e` variable-length skip rule. It
  applies to condition-list scanning paths, not to ordinary action opcode
  `0x0e` (`toggle_flag`); action `0x0e` (`toggle_flag`) remains the one-byte immediate flag toggle handler at
  `0x7492`.
- Refined linear bytecode listing behavior: action `0x00` (`end`) ends the current
  execution path, but later bytes in the same logic code area can still be
  branch targets, so the local static disassembler keeps scanning after `0x00`.
- Decoded condition opcode `0x0e` (`input_word_sequence`) as a variable-length parsed-input word
  sequence test. Its operand stream is a byte count followed by that many
  little-endian word IDs. Handler `0x095c` compares those word IDs with a
  parsed input-word buffer rooted at `DS:0x0c7b`, using word `[0x0ca3]` as the
  parsed-word count. Operand word `0x270f` terminates the test successfully,
  and operand word `0x0001` behaves as a wildcard for one parsed word. On full
  match the handler sets flag 4.
- Decoded action `0x65` (`display_message`) as immediate message display and action `0x66` (`display_message_var`) as
  variable-sourced message display. Both resolve the current logic message
  through helper `0x21f0` and pass the string pointer to display helper
  `0x1ce8`.
- Decoded actions `0x97` (`display_message_configured`) and
  `0x98` (`display_message_configured_var`) as configured message display variants.
  They set temporary globals `[0x0d0b]`, `[0x0d0d]`, and `[0x0d09]` from three
  operand bytes before display, then reset those globals to `0xffff`.
- Added more conservative object-action notes:
  - `0x24` (`deactivate_object`): deactivates/removes an active object by clearing bit `0x0001` in
    `[object+0x25]` and calling list/graphics helpers.
  - `0x2f` (`set_object_derived_resource_2`): calls helper `0x3ccb` with an immediate operand and clears object
    bit `0x1000`.
  - `0x36` (`set_object_field_24`), `0x37` (`set_object_field_24_var`), `0x38` (`clear_object_bit_0004`), and `0x39` (`get_object_field_24`): set, set-from-variable, clear, or read
    object byte `[+0x24]` with bit `0x0004` in `[+0x25]`.
  - `0x43` (`set_object_bit_0200`) and `0x44` (`clear_object_bit_0200`): set or clear object bit `0x0200`.
  - `0x58` (`set_object_bit_0002`) and `0x59` (`clear_object_bit_0002`): set or clear object bit `0x0002`.
- The local stats pass reports `LOGDIR` entry 141 as an invalid-looking target:
  it decodes to `VOL.0` offset `0x1ffff`, where no valid `12 34` volume header
  is present.

## 2026-07-01: additional object and picture action handlers

Additional local tools and artifacts used:

- The MS-DOS 6.22 hard disk image at `build/dos622/dos622.img` was created
  locally with QEMU and mtools.
- SQ2 was copied into that image under `C:\SQ2`.
- QEMU was used to boot DOS, run `SIERRA.COM`, and capture screenshots showing
  the title sequence and intro scene. This confirmed that the local DOS/QEMU
  setup can execute the game, but the handler work below is still based on
  static disassembly.

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/disassemble_logic.py --stats`
- `python3 -B tools/disassemble_logic.py 0 1 2`
- Focused Rizin disassembly around image offsets `0x1700`, `0x4a00`,
  `0x6a80`, and `0x6c80`.
- Focused `ndisasm` disassembly around image offsets `0x47e0`, `0x497b`,
  `0x4b80`, `0x6b80`, `0x6c54`, `0x6e02`, `0x6f3e`, `0x7000`, `0x74b0`, and
  `0x7e00`.
- Additional focused `ndisasm` disassembly around image offsets `0x2250`,
  `0x7dba`, `0x911d`, `0x91cf`, and `0x93b1`. These runs used file skips
  equal to image offset plus `0x200`; an earlier shifted dump around the
  `0x7dba` area was rejected after the exact handler offset was rechecked.
- Local Python dump of selected action table entries from
  `SQ2/AGIDATA.OVL` offset `0x061d`, covering opcodes `0x18..0x1b`,
  `0x2d..0x2e`, and `0x3a..0x57`.

Documented result:

- Updated `tools/disassemble_logic.py` with conservative names for newly
  decoded common action opcodes.
- Updated `docs/src/logic_bytecode.md`.
- Added picture-like action notes:
  - `0x18` (`load_picture_var`): variable-sourced picture-like resource load through helper
    `0x4a3b`.
  - `0x19` (`prepare_picture_var`): variable-sourced picture-like resource preparation through helper
    `0x4acf`.
  - `0x1a` (`show_picture_like`): picture/display finalization-like action that clears flag 15,
    calls helpers `0x1f2b` and `0x5546`, and sets `[0x1216] = 1`.
  - `0x1b` (`discard_picture_var`): variable-sourced picture-like resource unlink/release helper.
- Added object bit actions:
  - `0x2d` (`set_object_bit_2000`)/`0x2e` (`clear_object_bit_2000`): set/clear object bit `0x2000`.
  - `0x3a` (`clear_object_bit_0010`)/`0x3b` (`set_object_bit_0010`): clear/set object bit `0x0010` through helpers that wrap
    the update in redraw/cache calls.
  - `0x3d` (`set_object_bit_0008`)/`0x3e` (`clear_object_bit_0008`): set/clear object bit `0x0008`.
  - `0x40` (`set_object_bit_0100`): set object bit `0x0100`.
  - `0x41` (`set_object_bit_0800`): set object bit `0x0800`.
  - `0x42` (`clear_object_bits_0900`): clear object bits `0x0100` and `0x0800`.
  - `0x46` (`clear_object_bit_0020`)/`0x47` (`set_object_bit_0020`): clear/set object bit `0x0020`.
- Added object field/action notes:
  - `0x45` (`object_distance_to_var`): computes a capped distance-like value between two active objects
    and stores it in a variable, or stores `0xff` if either object is inactive.
  - `0x48..0x4b`: set object byte `[+0x23]` to modes 0, 1, 3, or 2, with the
    mode 1 and mode 2 forms also setting bits `0x1030`, storing an immediate
    in `[+0x27]`, and clearing the corresponding flag.
  - `0x4c` (`set_object_field_1f_var`), `0x4f` (`set_object_field_1e_var`), `0x50` (`set_object_field_01_var`), `0x56` (`set_object_field_21_var`), and `0x57` (`get_object_field_21`): move values between
    variables and object bytes `[+0x1f]`, `[+0x1e]`, `[+0x01]`, and `[+0x21]`.
  - `0x4d` (`clear_object_fields_21_22`), `0x4e` (`clear_object_field_22_and_global`), `0x53` (`approach_first_object_until_near`), `0x54` (`start_random_motion`), `0x55` (`stop_motion_mode`), `0x83` (`clear_global_0139`), and `0x84` (`set_global_0139_and_clear_object0_field_22`): update
    object byte `[+0x22]` and related globals, especially `[0x0139]`.
- Added interpreter/resource-control notes:
  - `0x12` (`switch_room_like`)/`0x13` (`switch_room_like_var`): broad room/state switch helpers that stop active sound,
    reset object entries, update byte variable 0, load the target logic, set
    flag 5, clear the status table at `0x1218`, and call redraw/reinit helpers.
  - `0x63` (`start_sound_with_flag`): starts a sound-like resource and associates a flag with completion
    or active-state handling by storing it in `[0x126a]`.
- Added formatted-message and menu/list-like UI notes:
  - `0x67` (`display_formatted_message`)/`0x68` (`display_formatted_message_var`): configured formatted-message display helpers. They call
    setup helper `0x2b28`, pass two placement/configuration values to
    `0x2b0d`, resolve a current-logic message through `0x21f0`, format/copy it
    into a large stack buffer via `0x1f54`, send it to `0x2390`, then call
    cleanup helper `0x2b4f`. The `0x68` form reads all three operands through
    variables.
  - `0x9c` (`add_menu_heading_like`): allocates and links an 18-byte top-level node that stores a
    message pointer, active marker, and position-like value.
  - `0x9d` (`add_menu_item_like`): allocates and links a 14-byte item node under the current
    top-level node, storing message pointer, item id, active marker, and
    row/column-like values.
  - `0x9e` (`finalize_menu_like`): finalizes the menu/list-like structure and sets `[0x1d2a] = 1`,
    after which later additions are ignored by the handlers.
  - `0x9f` (`enable_menu_item_like`)/`0xa0` (`disable_menu_item_like`): walk the menu/list-like structure and set or clear the
    active marker on item nodes whose stored id matches the operand.
  - `0xa1` (`mark_menu_if_flag_0e`): tests flag `0x0e`; if set, writes `[0x1d22] = 1`.
- Corrected action `0x94` (`set_object_pos_dirty_var`): exact disassembly at image offset `0x7dba` shows
  that it is the variable-coordinate counterpart to `0x93`, storing
  `var[arg1]` and `var[arg2]` into object fields `[+0x03]` and `[+0x05]`,
  setting bit `0x0400`, and calling helper `0x593a`.

## 2026-07-01: text-window and auxiliary table action handlers

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/disassemble_logic.py --stats`
- `python3 -B tools/disassemble_logic.py 0 1 2 3 4 5 6 7 8 9 10`
- Local Python dump of selected action table entries from
  `SQ2/AGIDATA.OVL` offset `0x061d`, covering opcodes `0x5a..0x61`,
  `0x69..0x71`, `0x76..0x79`, `0x81`, and `0xa2..0xa4`.
- Focused `ndisasm` disassembly around image offsets `0x2b78`, `0x34bd`,
  `0x3547`, `0x382e`, `0x386f`, `0x4c3d`, `0x5e9b`, `0x5ebf`, `0x7538`,
  `0x7663`, `0x7714`, `0x7803`, `0x7a00`, and `0x7b4e`.

Documented result:

- Updated `tools/disassemble_logic.py` with conservative names for another
  batch of action opcodes, mostly text-window, prompt/status, and auxiliary
  table handlers.
- Added an operand metadata override for action `0xa2` (`display_view_resource_text_like_var`): the table byte is
  `0x01`, but exact handler disassembly at `0x5e9b` shows it reads the
  resource number from `var[arg0]`.
- Added text-window/action notes:
  - `0x69` (`clear_text_rect`): clears/fills a text rectangle through BIOS `int 10h` service
    `AH=0x06` via helper `0x2b78`.
  - `0x6a` (`enable_text_attr_mode_1757`)/`0x6b` (`disable_text_attr_mode_1757`): enable/disable an alternate text-attribute mode tracked by
    byte `[0x1757]`, then refresh related text areas.
  - `0x6d` (`set_text_window_pair`): updates globals `[0x05d1]`, `[0x05cd]`, and `[0x05cf]` through
    helper `0x77d5`.
  - `0x6e` (`shake_screen_like`): display-shake-like action that either calls display-mode-specific
    helpers or writes CRT controller ports `0x3d4/0x3d5` directly.
  - `0x70` (`show_status_line_like`)/`0x71` (`hide_status_line_like`): show/hide a status-line-like area controlled by word
    `[0x05d9]`.
  - `0x77` (`disable_input_line_like`)/`0x78` (`enable_input_line_like`): disable/enable an input-line-like area controlled by word
    `[0x05d3]`.
  - `0xa3` (`set_global_0d0f`)/`0xa4` (`clear_global_0d0f`): set/clear word `[0x0d0f]`, which helper `0x3652` consults
    while updating input-line display state.
- Added auxiliary resource/table notes:
  - `0x5a` (`set_rect_bounds_0131`)/`0x5b` (`clear_rect_bounds_0131`): set/clear a rectangle/bounds filter stored in globals
    `[0x0131]`, `[0x0133]`, `[0x0135]`, `[0x0137]`, and `[0x013d]`.
  - `0x5c..0x61`: manipulate byte `[+0x02]` in 3-byte entries from the table
    rooted at `[0x0971]`, validating against end pointer `[0x0973]`.
  - `0x79` (`map_key_event`): stores `(arg0 | arg1 << 8, arg2)` into the first free four-byte
    slot among 39 slots rooted at `0x0145`.
  - `0x81` (`display_view_resource_text_like`)/`0xa2` (`display_view_resource_text_like_var`): immediate and variable forms of a view-like resource
    display/preview helper that loads the resource, builds a temporary
    object-like record, displays a resource-derived string through `0x1ce8`,
    and cleans up temporary allocations.

## 2026-07-01: resource accessors and prompt/session handlers

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/disassemble_logic.py --stats`
- Local Python dump of selected action table entries from
  `SQ2/AGIDATA.OVL` offset `0x061d`, covering opcodes `0x2f..0x35`,
  `0x72..0x76`, `0x85..0x86`, `0x8e`, and `0x91..0x92`.
- Focused `ndisasm` disassembly around image offsets `0x027f`, `0x0d37`,
  `0x1335`, `0x3c8c`, `0x3e25`, `0x4de8`, `0x4e8d`, `0x5234`, `0x716a`, and
  `0x71ed`.
- `python3 -B tools/disassemble_logic.py --limit 200 | rg ...` was attempted
  for call-site sampling, but the helper aborted at the known invalid `LOGDIR`
  entry 141. The partial output before that abort was used only as supporting
  call-site evidence; the verification pass continues to use `--stats`, which
  records and skips the bad entry.

Documented result:

- Added resource-derived object accessor notes:
  - `0x30` (`set_object_derived_resource_2_var`): variable-argument counterpart to `0x2f`, calling helper `0x3ccb`.
    The helper selects a derived subresource/loop-like entry, updates object
    byte `[+0x0e]`, pointer `[+0x10]`, words `[+0x1a]` and `[+0x1c]`, clamps
    object coordinates, and sets bit `0x0400` if it adjusts them.
  - `0x31` (`get_object_resource_loop_count`): stores `*([object+0x0c]) - 1` into a variable, apparently a count
    from the object's loaded resource table.
  - `0x32` (`get_object_field_0e`), `0x33` (`get_object_field_0a`), `0x34` (`get_object_field_07`), and `0x35` (`get_object_field_0b`): copy object bytes `[+0x0e]`,
    `[+0x0a]`, `[+0x07]`, and `[+0x0b]` into variables. `0x35` was present in
    the table but not encountered in the current SQ2 scan.
- Added string/prompt notes:
  - `0x72` (`set_string_slot_from_message`): copies a current-logic message into fixed string slot
    `0x020d + arg0 * 0x28` through helper `0x4de8`.
  - `0x76` (`prompt_number_to_var`): displays a current-logic message prompt, accepts up to four
    characters through helper `0x0da9`, parses the result as decimal via
    `0x4e8d`, and stores the low byte in a variable.
  - `0x85` (`display_object_diagnostics_var`): formats several object fields into a display string using template
    pointer `0x1713`, then displays it through `0x1ce8`.
- Added interpreter/session-control notes:
  - `0x86` (`confirm_and_restart_like`): stops sound state and conditionally calls helper `0x02ae`, which
    calls `0x8275` and `0x00ae(0)`. The handler displays string `0x05e3` as a
    confirmation path when the operand is not 1.
  - `0x8e` (`set_global_0141_and_refresh`): stores a word at `[0x0141]` and calls refresh helper `0x707c`
    wrapped in `0x6a54`/`0x6a8e`.
  - `0x91` (`save_logic_resume_ip`): saves the current bytecode pointer into `[current_logic+0x06]`.
  - `0x92` (`restore_logic_entry_ip`): restores `[current_logic+0x06]` from `[current_logic+0x04]`.

## 2026-07-01: graphics and object pipeline synthesis

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,220p' AGENTS.md`
- `rg -n "picture|draw|object|graphics|0x4a3b|0x4acf|0x6445|0x6a54|0x6a8e|0x593a|0x59fa|0x3ae7|0x3ccb|0x09ea|0x0a06" docs/src tools`
- `ls docs/src`
- `python3 -B tools/disassemble_logic.py --stats`
- Focused `ndisasm` disassembly around image offsets `0x0307`, `0x09ea`,
  `0x3979`, `0x3bb7`, `0x4a16`, `0x5200`, `0x5546`, `0x593a`, `0x6440`,
  `0x6a20`, `0x6a54`, and `0x9097`. These runs used file skips equal to image
  offset plus `0x200`, matching the decrypted MZ header size.
- Additional reads of existing docs with `sed` and `rg` to avoid duplicating
  opcode tables already captured in `logic_bytecode.md`.

Documented result:

- Added `docs/src/graphics_object_pipeline.md`.
- Added the new chapter to `docs/src/SUMMARY.md`.
- Consolidated the picture load/decode path:
  - Action `0x18` (`load_picture_var`) calls loader `0x4a3b`, which uses cache lookup `0x49e8`,
    directory accessor `0x43d9`, and generic reader `0x2e32`.
  - Action `0x19` (`prepare_picture_var`) calls helper `0x4acf`, stores the selected payload pointer at
    `[0x1377]`, wraps the operation in `0x6a54`/`0x6a8e`, and decodes the
    picture through `0x6445`.
  - Action `0x1a` (`show_picture_like`) clears flag 15, calls display helpers, and sets
    `[0x1216] = 1`.
- Documented the picture command scanner at `0x6475`, including the
  `0xf0..0xfa` dispatch range, the `0xff` terminator, and the observed drawing
  globals `[0x1369]`, `[0x136b]`, `[0x136c]`, `[0x136d]`, `[0x136e]`, and
  `[0x136f]`.
- Expanded the view/object binding model:
  - Helper `0x3ae7` binds a cached view-like payload to object fields `+0x07`
    and `+0x08`, copies payload byte `+0x02` into object byte `+0x0b`, and
    delegates to `0x3bb7`.
  - Helpers `0x3c1b`, `0x3ccb`, and `0x3d6a` select nested subresources,
    update object pointer/size fields, and clamp object coordinates.
- Added a field map for the 43-byte object records rooted at `[0x096b]`.
- Documented object activation/deactivation helpers `0x0a06` and `0x0aab`,
  including their list flushing/rebuild calls and the observed active bit
  `0x0001`.
- Documented placement helper `0x593a` and bounds helper `0x5a14`, including
  the screen limits `0xa0` and `0xa7` and the horizon-like global `[0x012d]`.
- Clarified the update-list wrappers:
  - `0x6a26` builds list root `0x16ff` through shared builder `0x0358`.
  - `0x6a3d` builds list root `0x1703` through shared builder `0x0358`.
  - `0x6a54` flushes both roots through `0x0307`.
  - `0x6a8e` rebuilds and processes both roots through `0x045e`.
  - `0x6aab` compares current and saved object fields through `0x0488`.

## 2026-07-01: view payload and object overlay rendering

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "0x3d6a|0x9097|0x9177|0x9db0|0x9db6|0x5762|view payload|render/update|update node|0x042f|0x0358" docs/src tools`
- Focused `ndisasm` disassembly around main executable image offsets `0x0307`,
  `0x0358`, `0x3d6a`, `0x587d`, and `0x9097`. A few intermediate disassembly
  commands used mismatched `-o`/`-e` values and were rejected; the observations
  documented here use the corrected convention `-o image_offset` and
  `-e image_offset + 0x200`.
- `wc -c build/cleanroom/AGI.decrypted.exe SQ2/EGA_GRAF.OVL SQ2/IBM_OBJS.OVL SQ2/AGIDATA.OVL`
- `file SQ2/EGA_GRAF.OVL SQ2/IBM_OBJS.OVL SQ2/AGIDATA.OVL`
- `xxd -l 128 -g 1 SQ2/EGA_GRAF.OVL`
- `xxd -l 128 -g 1 SQ2/IBM_OBJS.OVL`
- `ndisasm -b 16 -o 0x9db0 SQ2/IBM_OBJS.OVL`
- `ndisasm -b 16 -o 0x9800 SQ2/EGA_GRAF.OVL`
- `python3 -B tools/inspect_view.py 0 1 2 10 --groups 4 --frames 5`
- `python3 -B tools/inspect_view.py --limit 12 --groups 2 --frames 3`
- `python3 -B tools/inspect_view.py 11 --groups 4 --frames 4`
- `python3 -B -m py_compile tools/disassemble_logic.py tools/inspect_view.py`

Documented result:

- Added `tools/inspect_view.py`, a deterministic local helper for printing the
  observed view-like payload structure using only the locally derived
  directory and volume readers.
- Confirmed that calls to `0x9db0`, `0x9db3`, and `0x9db6` target
  `IBM_OBJS.OVL`, which is loaded at segment `0x09db` and therefore appears at
  near offsets starting at `0x9db0`.
- Documented the three IBM object-overlay entry jumps:
  - `0x9db0 -> 0x9db9`: save a screen rectangle into a node backing buffer.
  - `0x9db3 -> 0x9df8`: restore a screen rectangle from a node backing buffer.
  - `0x9db6 -> 0x9e35`: draw an object's selected frame into the graphics
    buffer.
- Documented render/update node layout from allocator `0x9097`: next pointer,
  previous pointer, object pointer, rectangle coordinates/dimensions, and a
  backing-buffer pointer.
- Expanded the view-like payload format:
  - Payload byte `+0x02` is the top-level group count.
  - The group offset table begins at payload `+0x05`, with 16-bit offsets
    relative to the payload base.
  - Each group starts with a frame count, followed by 16-bit frame offsets
    relative to the group base.
  - Each frame begins with width, height, and a control byte, followed by
    row-terminated encoded data.
- Local `tools/inspect_view.py` samples matched the helper-derived layout. For
  example, view 11 has two groups; group 0 starts at offset `0x09`, has two
  frames, and its first frame starts at offset `0x0e` with size `20x5` and
  control byte `0x01`.
- Documented the current frame-data model from object overlay draw routine
  `0x9e35`: zero bytes terminate rows; nonzero bytes use the high nibble as a
  color-like value and the low nibble as a run length; a run whose high nibble
  matches the frame control byte's low nibble advances without writing.

## 2026-07-01: object update-list selection and movement pass

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,260p' AGENTS.md`
- `sed -n '1,260p' docs/src/graphics_object_pipeline.md`
- `tail -n 180 docs/src/clean_room_executable_notes.md`
- `rg -n "0x150a|0x4719|0x56b8|0x69e4|0x6a05|0x6b44|0x6b62|0x0400|0x0051" docs/src tools`
- Focused `ndisasm` disassembly around main executable image offsets `0x13f0`,
  `0x4619`, `0x55b8`, `0x583a`, and `0x69c0`. Some intermediate commands used
  mismatched file skips and were rejected; the observations below use the
  corrected convention `-o image_offset` and `-e image_offset + 0x200` for
  `build/cleanroom/AGI.decrypted.exe`.

Documented result:

- Refined the update-list predicates:
  - Callback `0x69e4`, used by builder wrapper `0x6a26` for root `0x16ff`,
    accepts objects when `(object[+0x25] & 0x0051) == 0x0051`.
  - Callback `0x6a05`, used by builder wrapper `0x6a3d` for root `0x1703`,
    accepts objects when `(object[+0x25] & 0x0051) == 0x0041`.
  - Therefore flag bit `0x0010` partitions otherwise active/eligible objects
    between the two update-list roots. Helpers `0x6b44` and `0x6b62` clear and
    set that bit while wrapping the change with `0x6a54`/`0x6a8e`.
- Documented movement pass `0x150a`:
  - It clears event globals `[0x000e]`, `[0x000d]`, and `[0x000b]`.
  - It scans object records from `[0x096b]` to `[0x096d]` in `0x2b`-byte
    strides, processing only objects whose flag word satisfies
    `(object[+0x25] & 0x0051) == 0x0051`.
  - Object byte `+0x01` is a countdown/tick divider reloaded from byte `+0x00`.
  - Unless bit `0x0400` is set, direction byte `+0x21`, step byte `+0x1e`, and
    signed-delta tables at `0x0a61` and `0x0a73` produce proposed X/Y movement.
  - Proposed movement is clamped to left, right, top, bottom, and horizon-like
    bounds, producing boundary codes 1 through 4.
  - The move is accepted only when `0x4719(object)` returns zero and
    `0x56b8(object)` returns nonzero. Otherwise the previous X/Y coordinates
    are restored and placement search helper `0x593a(object)` is called.
  - Boundary events are written to `[0x000b]` for objects with byte `+0x02 == 0`
    or to `[0x000d]`/`[0x000e]` for nonzero byte `+0x02`. If byte `+0x22 == 3`,
    helper `0x16b9(object)` ends that motion/control state.
  - The pass clears object bit `0x0400` before leaving an object.
- Documented helper `0x4719(object)` as an object-object collision/crossing
  test. It skips objects with bit `0x0200`, skips candidates with matching byte
  `+0x02`, checks horizontal rectangle overlap from X and width, then checks
  whether current and previous Y positions cross.
- Documented helper `0x56b8(object)` as a control/priority-buffer acceptance
  test. It may derive object byte `+0x24` from table `0x127a`, scans high
  nibbles in the graphics/control buffer at `[0x136f]`, reacts to nibble classes
  `0x10`, `0x20`, and `0x30`, and returns nonzero to permit a proposed move.
- Added targeted-motion notes for helpers `0x1672`, `0x16ed`, and `0x16b9`:
  direction-like byte `+0x21` can be computed from the current object position
  to target fields `+0x27`/`+0x28`, and `0x16b9` restores byte `+0x1e` from
  `+0x29` while setting completion flag `+0x2a` and clearing motion/control
  byte `+0x22`.

## 2026-07-01: graphics/control buffer helper pass

Additional commands run from `/Users/peter/ai/agi/reverse`:

- Focused `ndisasm` disassembly around main executable image offsets `0x4c80`,
  `0x5200`, `0x5480`, `0x5528`, `0x5660`, `0x5700`, and `0x57c0`.
- `xxd -s 0x52b5 -l 8 -g 2 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x0 -e 0x200 build/cleanroom/AGI.decrypted.exe | rg "call 0x4d10|call 0x56a2|call 0x4cbb|call 0x5666|call 0x56b8|call 0x5762|call 0x57cf"`
- A raw `xxd` read at file offset `0x127a` and an origin-shifted whole-image
  call-site scan were rejected. The `0x127a` table described below is a runtime
  table initialized by code, and the accepted whole-image call-site scan uses
  `-o 0x0 -e 0x200`.

Documented result:

- Added a graphics/control buffer helper section to
  `docs/src/graphics_object_pipeline.md`.
- Documented helper `0x5257` as a buffer fill routine for the segment stored in
  `[0x136f]`. It writes `0x3480` words, matching a `0x6900`-byte grid. Picture
  decoding calls it with `AX = 0x4f4f`, while helper `0x5528` calls it with
  `AX = 0x4040`.
- Documented helper `0x5666` as the direct coordinate-to-buffer conversion
  `DI = y * 0xa0 + x`, with `AL = y` and `AH = x`.
- Documented helper `0x56a2` as the default initializer for the 168-byte table
  rooted at `0x127a`: rows `0..47` map to 4, and subsequent 12-row bands map to
  values 5 through 14.
- Documented helper `0x4cbb(value)` as a reverse mapping from a
  priority/control value toward a Y row. In one mode it scans the `0x127a`
  table downward; when `[0x124a]` is nonzero it uses
  `(value - 5) * 12 + 0x30`.
- Documented helper `0x57cf(object)` as a post-draw buffer marker. It calls the
  object overlay draw entry `0x9db6`, ensures object byte `+0x24` has a low
  nibble derived from the Y table if absent, and writes the high nibble of
  `+0x24` around the object's buffer footprint while preserving low nibbles.
- Refined helper `0x56b8(object)`: it scans the high nibbles of the selected
  frame width at the object's X/Y buffer row. High nibble `0x00` rejects
  immediately; `0x10` requires object flag bit `0x0002`; `0x20` records a seen
  class; `0x30` continues without changing the tracked class. After the scan,
  bits `0x0100` and `0x0800` can reject the final class state, and objects with
  byte `+0x02 == 0` update global flags 3 and 0 through `0x74ee`/`0x74f4`.

## 2026-07-01: transient object and view-preview rendering pass

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,220p' AGENTS.md`
- `sed -n '1,460p' docs/src/graphics_object_pipeline.md`
- `tail -n 180 docs/src/clean_room_executable_notes.md`
- `rg -n "0x57cf|0x5a14|0x5a3a|0x5fd3|0x6006|0x56b8|0x5762|0x980c|0x9812|0x9db6|0x1c54|0x2e1b|0x2e28" docs/src tools`
- Focused `ndisasm` disassembly around main executable image offsets `0x1c20`,
  `0x2c40`, and `0x5e80`, using `-e image_offset + 0x200`.
- `python3 -B tools/disassemble_logic.py --limit 5 | sed -n '1,220p'`
- Follow-up reads of the existing `0x7a`, `0x7b`, `0x81`, and `0xa2` opcode
  notes in `docs/src/logic_bytecode.md`.
- `python3 -B tools/inspect_view.py --limit 40 --groups 1 --frames 1`
- `sed -n '1,260p' tools/inspect_view.py`

Documented result:

- Added a transient/preview object section to
  `docs/src/graphics_object_pipeline.md`.
- Refined the `0x7a` and `0x7b` entries in `docs/src/logic_bytecode.md`.
- Updated `tools/inspect_view.py` to print the observed preview/display string
  offset from `u16(payload + 0x03)`.
- Documented actions `0x7a` (`setup_transient_object`)/`0x7b` (`setup_transient_object_var`)
  as callers of helper `0x2d52`, which uses a
  fixed 43-byte object-like record at `0x0eb4`.
  - Staged byte `0x0eae` selects the view-like resource.
  - `0x0eaf` selects the top-level group.
  - `0x0eb0` selects the frame/derived entry.
  - `0x0eb1` and `0x0eb2` are X/Y coordinates.
  - The low and high nibbles of `0x0eb3` feed object byte `+0x24`.
  - The helper binds the view through `0x3ae7`, selects group/frame through
    `0x3bb7` and `0x3ccb`, places the object with `0x593a`, draws/marks it
    through `0x57cf`, rebuilds update lists with `0x6a54`/`0x6a8e`, and calls
    `0x5762`.
- Documented the fixed transient record's initialization:
  - Its selected frame pointer is copied to saved-frame field `+0x12`.
  - Staged X/Y are copied into both current and saved coordinate fields.
  - Flag word `+0x25` starts as `0x020c`, combining fixed-priority,
    horizon-exempt, and collision-skip behavior.
  - If the staged priority/control low nibble is zero, the helper later
    replaces the flag word with `0x0008` before drawing/marking.
- Refined the `0x81`/`0xa2` view-resource preview path:
  - Helper `0x5edb` records whether the view resource was already cached,
    temporarily sets `[0x0f18] = 1` while loading it, and initializes a
    stack-local 43-byte object-like record with group/frame zero.
  - The temporary preview object is centered with `x = (0x9f - width) / 2`,
    given `y = 0xa7`, fixed priority/control byte `+0x24 = 0x0f`, and grouping
    byte `+0x02 = 0xff`.
  - If enough memory is available, the helper allocates a render node through
    `0x9097`, saves the backing rectangle with `0x9db0`, draws with `0x9db6`,
    and later restores with `0x9db3` and frees with `0x910a`.
  - The displayed string pointer is `payload + u16(payload + 0x03)`, giving the
    first observed consumer for view payload bytes `+0x03..+0x04`.
  - The first 40 present SQ2 view resources sampled by `tools/inspect_view.py`
    all had `u16(payload + 0x03) == 0`, so a nonzero local example remains to
    be found.
  - If the resource was not cached before the preview, the helper releases it
    through `0x3f0d`.

## 2026-07-01: object rectangle conditions and configured motion bounds

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,220p' AGENTS.md`
- `rg -n "condition|0x0b|object_rect|rect_test|0x08c6|0x7be6|0x013d|0x0131|0x4719|0x47ef" docs/src tools`
- `sed -n '260,360p' docs/src/logic_bytecode.md`
- `sed -n '1,520p' docs/src/graphics_object_pipeline.md`
- Focused `ndisasm` disassembly around main executable image offsets `0x0800`,
  `0x0680`, `0x06c0`, `0x47e0`, and `0x7b40`, using
  `-e image_offset + 0x200`.
- `ndisasm -b 16 -o 0x0 -e 0x200 build/cleanroom/AGI.decrypted.exe | rg "call 0x7be6|call 0x08c6|call 0x08cc|call 0x08db|call 0x08e8|call 0x091a|call 0x47ef"`
- Follow-up reads of the condition-name table in `tools/disassemble_logic.py`
  and the condition documentation in `docs/src/logic_bytecode.md`.

Documented result:

- Refined the local names for condition opcodes `0x0b` (`object_left_baseline_in_rect`),
  `0x10` (`object_width_baseline_in_rect`), `0x11` (`object_center_baseline_in_rect`), and
  `0x12` (`object_right_baseline_in_rect`) in `tools/disassemble_logic.py`.
- Expanded the condition documentation for object rectangle tests:
  - Shared helper `0x091a` resolves object index `arg0`, loads object X into
    `DH` and `CH`, and loads object Y into `DL`.
  - Common comparison helper `0x08f0` checks `DH >= arg1`, `DL >= arg2`,
    `CH <= arg3`, and `DL <= arg4`.
  - Condition `0x0b` (`object_left_baseline_in_rect`) tests object left X/baseline Y.
  - Condition `0x10` (`object_width_baseline_in_rect`) tests the full horizontal span from left X to
    `x + width - 1`.
  - Condition `0x11` (`object_center_baseline_in_rect`) tests horizontal center X.
  - Condition `0x12` (`object_right_baseline_in_rect`) tests right X.
- Documented the configured rectangle helper:
  - Action `0x5a` (`set_rect_bounds_0131`) stores bounds in `[0x0131]`, `[0x0133]`, `[0x0135]`, and
    `[0x0137]`, and sets `[0x013d] = 1`.
  - Action `0x5b` (`clear_rect_bounds_0131`) clears `[0x013d]`.
  - Helper `0x7be6(x, y)` returns true only for points strictly inside the
    configured rectangle.
  - Helper `0x06d9(object)` compares whether the object's current baseline
    point and next step point are on the same side of that rectangle. A crossing
    sets object bit `0x0080`, clears direction byte `+0x21`, and clears global
    byte `[0x000f]` when the object is the first object record. No crossing
    clears bit `0x0080`.

## 2026-07-01: object dirty rectangles and graphics-overlay refresh entries

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n '1,240p' AGENTS.md`
- `sed -n '1,260p' docs/src/graphics_object_pipeline.md`
- `tail -n 120 docs/src/clean_room_executable_notes.md`
- `rg -n "0x5762|0x970c|0x9812|0x9815|0x5546|0x5528|0x9db0|0x9db3|0x9db6|display" docs/src tools`
- Focused `ndisasm` disassembly around main executable image offsets `0x5500`,
  `0x5700`, and `0x9600`, using `-e image_offset + 0x200`.
- `sed -n '430,530p' docs/src/graphics_object_pipeline.md`
- `sed -n '160,210p' docs/src/agi_executable.md`
- `rg -n "0x9800|0x980c|0x9812|0x9815|0x9837|JR_GRAF|CGA_GRAF|IBM_OBJS|load overlay|OVL" docs/src tools`
- `ls -l build/cleanroom/AGI.decrypted.exe SQ2/*.OVL`
- `ndisasm -b 16 -o 0x9800 SQ2/EGA_GRAF.OVL`
- `ndisasm -b 16 -o 0x9800 SQ2/CGA_GRAF.OVL`
- `ndisasm -b 16 -o 0x9800 SQ2/VG_GRAF.OVL`
- Follow-up reads of the render/update section in
  `docs/src/graphics_object_pipeline.md`.

Documented result:

- Replaced the previous tentative note about helper `0x5762` with a concrete
  dirty-rectangle interpretation:
  - It returns immediately unless word `[0x1216]` is nonzero.
  - It compares the current frame pointer `object+0x10` and saved frame pointer
    `object+0x12`, plus current/saved X/Y fields `+0x03/+0x05` and
    `+0x16/+0x18`.
  - It copies the current frame pointer to `+0x12`.
  - It computes the union rectangle covering the old and new object frame
    footprints.
  - It calls graphics-overlay entry `0x980c` with that union rectangle.
- Documented the common rectangle argument contract used by `0x980c` and
  `0x9812`:
  - `AH = left X`
  - `AL = bottom Y`
  - `BL = width`
  - `BH = height`
- Documented graphics-overlay entry `0x980c` as a rectangle copy from the
  interpreter's logical graphics buffer segment `[0x136f]` to display memory
  segment `[0x1371]`.
- Documented graphics-overlay entry `0x9812` as a rectangle fill; in the EGA
  and VGA overlays, low byte `DL` supplies the fill value.
- Refined helpers around the full-screen display path:
  - `0x5528` clears the logical graphics buffer with fill word `0x4040`, calls
    graphics-overlay entry `0x980f`, rebuilds the default priority/control
    table with `0x56a2`, then calls entry `0x9800`.
  - `0x5546` can swap nibbles across the logical graphics buffer when
    `[0x1755] & 1` is set, calls HGC-specific helper `0x9899` in display mode
    2, then calls `0x980c` for the full `0xa0` by `0xa8` screen rectangle.
  - `0x5624` converts the common coordinate tuple into display-memory offsets,
    with display-mode branches controlled by `[0x1130]` and `[0x112e]`.
- Added the EGA graphics overlay entry table from local disassembly of
  `SQ2/EGA_GRAF.OVL` loaded at near origin `0x9800`:
  - `0x9800 -> 0x9815`: set graphics mode `0x0d` and store video segment
    `0xa000` in `[0x1371]`.
  - `0x9803 -> 0x9835`: return to text mode and clear/configure the text
    screen.
  - `0x9806 -> 0x986f`: reinitialize graphics and call `0x5546`.
  - `0x9809 -> 0x9884`: no-op in EGA.
  - `0x980c -> 0x9885`: copy a logical-buffer rectangle to EGA display memory.
  - `0x980f -> 0x9983`: initialize row-offset table `0x137b` and clear a
    display-memory range.
  - `0x9812 -> 0x9907`: fill a display rectangle.

## 2026-07-01: update-list phase order and stationary object flag

Additional commands run from `/Users/peter/ai/agi/reverse`:

- Focused `ndisasm` disassembly around main executable image offsets `0x0300`,
  `0x0400`, and `0x69c0`, using `-e image_offset + 0x200`.
- `ndisasm -b 16 -o 0x0 -e 0x200 build/cleanroom/AGI.decrypted.exe | rg "4000|6a54|6a8e|6aab|045e|0488|0307|0358"`
- Focused follow-up disassembly around image offsets `0x0b80`, `0x3f30`, and
  `0x67f0`, using `sed` to limit the visible output.

Documented result:

- Refined the update-list lifecycle:
  - `0x0307(root)` walks root nodes, restores each saved rectangle through
    `0x9db3`, then calls `0x032d(root)` to free nodes and clear root pointers.
  - `0x032d(root)` frees nodes through `0x910a` without doing the restore pass.
  - `0x045e(root)` walks from the list tail backward, saving each node's
    backing rectangle with `0x9db0` and drawing the node's object through
    `0x9db6`.
  - `0x6a54` restores/frees roots `0x16ff` and `0x1703` through `0x0307`.
  - `0x6a71` frees both roots through `0x032d` without restoration.
  - `0x6a8e` rebuilds and draws root `0x1703` first, then root `0x16ff`.
  - `0x6aab` runs `0x0488` over root `0x1703` first, then root `0x16ff`.
- Refined helper `0x0488(root)`:
  - For each node it calls `0x5762(object)` before comparing saved fields.
  - It only performs the position comparison when object byte `+0x01` equals
    reload byte `+0x00`.
  - If current X/Y `+0x03/+0x05` equal saved X/Y `+0x16/+0x18`, it sets flag
    bit `0x4000`.
  - Otherwise it copies current X/Y to saved X/Y and clears bit `0x4000`.
- Refined object flag bit `0x4000` from a generic comparison marker to a
  stationary/stuck marker used by later motion helpers.
- Observed two consumers of bit `0x4000`:
  - Helper `0x3f5a`, reached from motion/control mode byte `+0x22 == 1`, picks
    a new random direction through `0x3fa3` when its local countdown expires or
    when bit `0x4000` is set.
  - The helper around `0x0bb3`, reached from the `+0x22 == 2` path, can also
    replace direction byte `+0x21` with a random nonzero direction when bit
    `0x4000` reports no movement.

## 2026-07-01: logic cache lifetime and room-switch scheduler path

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n '1,220p' AGENTS.md`
- `sed -n '1,360p' docs/src/logic_bytecode.md`
- `sed -n '1,280p' docs/src/logic_resources.md`
- `tail -n 220 docs/src/clean_room_executable_notes.md`
- `rg -n "0x117d|0x119a|0x12ae|0x1364|0x13a5|0x1792|heap|cache|logic record|0x0977|0x0985|0x0983" docs/src tools/disassemble_logic.py`
- Initial raw `ndisasm` reads around the same regions. These produced too much
  output because `-e` is the input skip amount, not an end offset; they were
  used only for coarse orientation.
- Focused follow-up `ndisasm` disassembly around main executable image offsets
  `0x10d0`, `0x117d`, `0x1364`, and `0x1792`, using the decrypted executable
  header skip and `sed` to limit the visible output.

Documented result:

- Expanded `docs/src/logic_resources.md` with the 10-byte logic cache record
  layout:
  - `+0x00` next record pointer.
  - `+0x02` logic number byte.
  - `+0x03` message count byte.
  - `+0x04` bytecode base pointer, equal to `payload + 2`.
  - `+0x06` current interpreter instruction pointer.
  - `+0x08` message offset table base pointer.
- Documented helper `0x110f(logic_number)` as the logic-cache scan. It walks
  the list rooted at `[0x0977]` and stores the link slot for the matching or
  insertion position in `[0x0983]`.
- Refined loader `0x119a(logic_number)`:
  - On cache miss it calls `0x6a54`, allocates a 10-byte record through
    `0x13d6`, links it through `[0x0983]`, loads the resource through
    `0x4371` and `0x2e32`, derives bytecode/message pointers, temporarily sets
    `[0x0981]` while decrypting message text, then calls `0x6a8e`.
  - On cache hit it returns the existing record.
- Documented call helper `0x12ae(logic_number)`:
  - It preserves the previous current logic pointer `[0x0981]`.
  - If the target logic is already cached, it interprets that record in place.
  - If the target logic is missing, it loads it through `0x119a`, runs
    interpreter `0x293c`, unlinks it afterward through the saved `[0x0983]`
    slot, and rewinds the heap top to the start of that transient record
    through `0x143c`.
  - Actions `0x16` (`call_logic`) and `0x17` (`call_logic_var`) propagate a zero interpreter result as a zero
    next-instruction pointer, stopping the current logic loop.
- Documented routine `0x1364` as a snapshot writer for loaded logic execution
  positions. It emits 4-byte entries at `0x0985` containing logic number and
  `current_ip - bytecode_base`, followed by a `0xffff` terminator.
- Documented routine `0x13a5(record)` as the matching restore path, setting
  `record[0x06] = record[0x04] + saved_offset` when it finds the record's
  logic number in the `0x0985` table.
- Added heap-pointer helpers used by this path:
  - `0x13d6(size)` allocates from `[0x0a55]`.
  - `0x143c(ptr)` sets or rewinds `[0x0a55]`.
  - `0x1485` restores the heap pointer from mark `[0x0a59]` after freeing
    update-list nodes.
  - `0x14a0` updates the free-memory status byte `[0x0011]`.
- Refined room/state switch helper `0x1792`, reached by actions `0x12` (`switch_room_like`) and
  `0x13` (`switch_room_like_var`):
  - It stops active sound, restores heap/update-list state through `0x1485`,
    calls cleanup helpers `0x4482`, `0x707c`, and `0x706d`, and resets every
    object record's active/resource/frame state.
  - It sets `[0x0139] = 1`, stores `0x24` in `[0x012d]`, saves old byte
    variable 0 in byte variable 1, writes the destination logic number to byte
    variable 0, clears bytes `[0x000d]` and `[0x000e]`, and stores object 0's
    view/resource byte in `[0x0019]`.
  - It loads the destination logic through `0x117d`, optionally loads the
    logic named by `[0x1d12]`, may reposition object 0 from boundary byte
    `[0x000b]`, sets flag 5, and calls redraw/reinitialization helpers.

## 2026-07-01: input parsing action and WORDS.TOK dictionary format

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n '1,220p' AGENTS.md`
- `rg -n "action_75|0x75|0x1958|0x18ac|0x0c7b|0x0c8f|0x0ca3|input_word_sequence|parsed input|word" docs/src tools/disassemble_logic.py`
- Focused `ndisasm` disassembly around main executable image offsets `0x1800`,
  `0x0c00`, `0x0e00`, `0x1a30`, `0x4d80`, `0x4f50`, and `0x5000`, using
  the decrypted executable header skip and `sed` to limit output.
- `xxd -s 0x0940 -l 0x50 -g 1 SQ2/AGIDATA.OVL`
- `xxd -s 0x0c60 -l 0x70 -g 1 SQ2/AGIDATA.OVL`
- `ls -l SQ2`
- `xxd -l 160 -g 1 SQ2/WORDS.TOK`
- `xxd -s 0x40 -l 160 -g 1 SQ2/WORDS.TOK`
- `xxd -s 0x1a50 -l 160 -g 1 SQ2/WORDS.TOK`
- Local Python sanity check of the inferred `WORDS.TOK` decoder, followed by
  the deterministic script `tools/inspect_words.py`.
- `python3 -B tools/inspect_words.py --limit 60`
- `python3 -B tools/inspect_words.py --prefix look --limit 20`
- `python3 -B tools/inspect_words.py --id 0x0001 --limit 20`
- `python3 -B tools/inspect_words.py --prefix get --limit 20`

Documented result:

- Added `tools/inspect_words.py`, a deterministic local inspector for
  `SQ2/WORDS.TOK` based on the parser format inferred from the executable.
- Named action opcode `0x75` (`parse_string_slot`) as `parse_string_slot` in
  `tools/disassemble_logic.py`.
- Expanded `docs/src/logic_bytecode.md` with the producer side for condition
  opcode `0x0e`.
- Documented action `0x75` (`parse_string_slot`) at image offset `0x1958`:
  - It clears flags 2 and 4.
  - It reads one immediate string-slot index.
  - If the index is below 12, it parses fixed string slot
    `0x020d + index * 0x28` through helper `0x18ac`.
- Documented parser helper `0x18ac`:
  - It clears parsed-word ID table `0x0c7b` and parsed-word pointer table
    `0x0c8f`.
  - It normalizes the input string into buffer `0x0ca7` through helper
    `0x199d`.
  - It fills `0x0c7b`, `0x0c8f`, word `[0x0ca3]`, and byte variable
    `[0x0012]`, then sets flag 2 when a parse result exists.
- Documented normalization helper `0x199d`:
  - Bytes at `DS:0x0c67` are separators. SQ2 contains
    `20 2c 2e 3f 21 28 29 3b 3a 5b 5d 7b 7d 00`.
  - Bytes at `DS:0x0c75` are ignored punctuation. SQ2 contains
    `27 60 2d 22 00`.
  - It collapses separator runs to single spaces, removes ignored punctuation,
    trims a trailing space, and zero-terminates the normalized buffer.
- Documented dictionary lookup helper `0x1a6b` and the `WORDS.TOK` format:
  - Startup loads `WORDS.TOK` into memory and stores the base pointer at
    `[0x0ca5]`.
  - The file begins with 26 big-endian offsets for lowercase initial letters.
    The local SQ2 file has a zero offset for `x`.
  - Entries are prefix-compressed as `u8 prefix_len`, encoded suffix bytes with
    the final byte marked by bit 7, and a big-endian 16-bit word ID.
  - Decoding each suffix byte with `(byte & 0x7f) ^ 0x7f` yields the lowercase
    character.
  - Local inspection found 1,099 entries. Sample decoded IDs include
    `look -> 0x0002`, `get -> 0x0005`, and `anyword -> 0x0001`.
- Refined parsed-input behavior:
  - Recognized nonzero dictionary IDs are appended to `0x0c7b`.
  - ID zero words are ignored, including the special single-letter `a` and
    `i` paths in helper `0x1a6b`.
  - An unrecognized token stores its pointer in `0x0c8f`, records its one-based
    position in `[0x0012]` and `[0x0ca3]`, and stops parsing.
  - Condition `0x0e` (`input_word_sequence`) consumes the parsed IDs from `0x0c7b` and uses dictionary
    ID `0x0001` as a wildcard word.

## 2026-07-01: raw input event queue and condition 0x0d

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "0x0d|input_or_event_check|0x09be|0x459e|0x001c|0x45d7|0x382e|0x37f7|event|input" docs/src tools`
- Focused `ndisasm` disassembly around main executable image offsets `0x09a0`,
  `0x43f0`, `0x4500`, `0x4660`, `0x5a40`, `0x7f70`, and `0x3200`, using the
  decrypted executable header skip and `sed` to limit output.
- Full-executable `ndisasm` call-site search for calls to `0x44a9`, `0x44f9`,
  `0x459e`, `0x4529`, `0x4566`, `0x45d7`, `0x45f0`, `0x4618`, `0x467f`, and
  `0x466f`.
- A focused `ndisasm` read around `0x6100` was rejected because it used the
  wrong file skip. Follow-up reads around image offsets `0x5f80`, `0x8e80`,
  and `0x93d0` used the corrected `image_offset + 0x200` skip.
- `xxd -s 0x16b0 -l 0x50 -g 2 SQ2/AGIDATA.OVL`
- `xxd -s 0x16d0 -l 0x50 -g 2 SQ2/AGIDATA.OVL`
- `xxd -s 0x11ba -l 0x70 -g 2 SQ2/AGIDATA.OVL`
- Focused `ndisasm` disassembly around image offset `0x0c44`, showing action
  handler `0x73`. A follow-up read around `0x0e7e` used the wrong skip and was
  rejected; no conclusions from that shifted read were documented.
- Corrected focused `ndisasm` disassembly around image offset `0x0e7e`.
- `python3 -B tools/disassemble_logic.py --limit 142 | rg -n "\b8f\b|action_8f|logic="`
- `python3 -B tools/disassemble_logic.py --limit 142 | sed -n '/action_8f/,+4p'`

Documented result:

- Renamed condition opcode `0x0d` (`raw_key_event_available`) in `tools/disassemble_logic.py` to
  `raw_key_event_available`.
- Renamed action opcode `0x79` (`map_key_event`) in `tools/disassemble_logic.py` to
  `map_key_event`.
- Expanded `docs/src/logic_bytecode.md` with the raw event queue:
  - Event records are 4 bytes: type word at `+0`, value word at `+2`.
  - Queue storage is `0x11ba..0x1209`.
  - Word `[0x120a]` is the write pointer, and word `[0x120c]` is the read
    pointer.
  - Helper `0x44a9(type, value)` enqueues one record unless the queue is full.
  - Helper `0x44f9()` dequeues one record or returns zero when empty.
- Documented condition handler `0x09be`:
  - It first checks byte `[0x001c]`.
  - If empty, it calls helper `0x459e`.
  - Helper `0x459e` dequeues events, normalizes some key values through
    `0x4634`, returns the event value for type-1 records, returns zero for no
    event, and returns `0xffff` for non-type-1 records.
  - Handler `0x09be` loops past `0xffff`, stores a nonzero low byte in
    `[0x001c]`, and returns true.
- Documented keyboard helper `0x5a89` as the BIOS `int 16h` polling path:
  - It returns zero when no key is waiting.
  - It returns the low ASCII byte when the key has nonzero ASCII.
  - It preserves the BIOS scan-code word when ASCII is zero.
- Documented helper `0x467f` as the BIOS-key drain into the event queue:
  - Key words found in table `DS:0x16b3` are enqueued as type 2 with a mapped
    direction-like value.
  - Other key words are enqueued as type 1 with the raw value.
  - The local `0x16b3` table maps key words `0x4800`, `0x4900`, `0x4d00`,
    `0x5100`, `0x5000`, `0x4f00`, `0x4b00`, and `0x4700` to values `1..8`.
- Documented helper `0x4566(event_record)`:
  - For type-1 events, it scans script-populated four-byte slots rooted at
    `0x0145`.
  - On a match between event value and slot word `+0`, it changes the event
    type to 3 and replaces the event value with slot word `+2`.
  - Action `0x79` (`map_key_event`) appends those mapping slots.
- Documented display-mode-specific helper `0x46e8(event_record)`:
  - When `[0x112e] == 2`, it scans table `DS:0x16d7`.
  - Matching type-1 values are changed to type 2 with mapped values.
  - The local table maps ASCII digit key words `8,9,6,3,2,1,4,7` to values
    `1..8`.
- Named action opcode `0x73` (`prompt_string_to_slot`) as `prompt_string_to_slot`:
  - It reads fixed string slot `arg0`, message number `arg1`, placement-like
    bytes `arg2` and `arg3`, and max-length byte `arg4`.
  - It clears the destination slot `0x020d + arg0 * 0x28`.
  - It displays the resolved current-logic message, optionally after calling
    `0x2b0d(arg2, arg3)` when `arg2 < 0x19`.
  - It accepts edited text through helper `0x0da9`, using
    `min(arg4 + 1, 0x28)` as the accepted length.
- Recorded a tentative observation for action opcode `0x8f` (`action_8f`) without assigning a
  name:
  - Handler `0x0e7e` reads one message-number operand.
  - It resolves that current-logic message through `0x21f0`.
  - It calls `0x4de8(destination=0x0002, source=message, count=7)`.
  - It then calls helper `0x5b49`.
  - The one local occurrence is in logic 140 before action `0x6f` (`set_input_line_config`) and string
    setup actions; the role remains open.

## Follow-up on action `0x6f` (`set_input_line_config`), action `0x8f` (`action_8f`), and DOS path helpers

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n '1,220p' AGENTS.md`
- `rg -n "0x6f|0x8f|action_6f|action_8f|Text-window|input-line|DOS file|file helper" docs/src tools/disassemble_logic.py`
- Corrected focused `ndisasm` disassemblies around image offsets `0x0e7e`,
  `0x78f0`, and `0x5b49`, using the decrypted executable header skip and
  `sed` to limit the displayed output.
- `xxd -s 0x5d6c -l 0x10 -g 1 build/cleanroom/AGI.decrypted.exe`
- `xxd -s 0x1320 -l 0x60 -g 1 SQ2/AGIDATA.OVL`
- `python3 -B tools/disassemble_logic.py --limit 141 | sed -n '/action_8f/,+8p'`
- `rg -n "0x5dd|0x05dd|0x05d5|0x05db|0x1379|0x5df|0x05df" docs/src`

Documented result:

- Named action opcode `0x6f` (`set_input_line_config`) in `tools/disassemble_logic.py` as
  `set_input_line_config`.
- Documented handler `0x78f0`:
  - It stores `arg0` in `[0x05dd]`, `arg0 + 0x15` in `[0x05df]`, `arg1` in
    `[0x05d5]`, and `arg2` in `[0x05db]`.
  - It computes `[0x1379]` from `arg0`, normally as `arg0 << 3`.
  - In display mode `[0x1130] == 2`, `[0x1379]` is `arg0 * 6` for `arg0 <= 1`
    and is clamped to 6 for larger values.
  - Nearby redraw helpers use these globals for input-line/status text areas,
    so the final user-facing meaning remains provisional.
- Refined the action `0x8f` (`action_8f`) observation:
  - Handler `0x0e7e` copies the resolved message into absolute buffer `0x0002`
    and calls `0x5b49`.
  - Helper `0x5b49` compares bytes at `0x0002` against the embedded `SQ2\0`
    string at image offset `0x5b6c`.
  - On the first mismatch it calls helper `0x02ae`, already observed in
    restart/exit-like paths.
  - This looks like a game-signature/configuration guard, but the exact runtime
    role remains open until dynamically traced.
- Expanded `docs/src/agi_executable.md` with the DOS file wrapper cluster from
  image offsets `0x5cad..0x5e73`, the shared pre-call helper `0x5e8d`, and the
  savegame/path helpers around `0x5b73` and `0x5bdd`.

## Follow-up on relative object positioning and state-file actions

Additional commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n '1,220p' AGENTS.md`
- `sed -n '1,260p' docs/src/graphics_object_pipeline.md`
- `sed -n '500,580p' docs/src/logic_bytecode.md`
- `python3 -B tools/disassemble_logic.py --stats | rg " action_|^28 |^7c |^7d |^7e |^80 |^87 |^88 |^89 |^8a |^8b |^8c |^8d |^96 |^a9 |^9a |^6c "`
- Correct focused `ndisasm` disassemblies around image offsets `0x7ce7`,
  `0x3726`, `0x3753`, `0x38b4`, `0x2472`, `0x2512`, `0x2753`, `0x28c6`,
  `0x26b0`, `0x31d8`, and `0x1f2b`, using the decrypted executable header
  skip of `image_offset + 0x200`.
- Two preliminary `ndisasm` probes around image offsets `0x3726` and `0x0257`
  were rejected because the file skip was wrong; no conclusions from those
  shifted outputs were used.
- `python3 -B tools/disassemble_logic.py --limit 141 | rg -n "action (28|7c|7d|7e|80|87|88|89|8a|8b|8c|8d|96|a9|9a|6c)" -C 5`
- `xxd -s 0x0d20 -l 0xe0 -g 1 SQ2/AGIDATA.OVL`
- `xxd -s 0x1c60 -l 0x50 -g 1 SQ2/AGIDATA.OVL`
- `xxd -s 0x0a90 -l 0x70 -g 1 SQ2/AGIDATA.OVL`
- `sed -n '170,230p' tools/disassemble_logic.py`
- `sed -n '440,545p' docs/src/logic_bytecode.md`
- `sed -n '604,650p' docs/src/logic_bytecode.md`
- `sed -n '45,125p' docs/src/agi_executable.md`
- `sed -n '200,235p' docs/src/graphics_object_pipeline.md`
- One `rg` probe for a markdown backtick pattern in
  `docs/src/graphics_object_pipeline.md` failed due shell quoting; it produced
  no evidence and was replaced by the `sed` read above.

Documented result:

- Named action opcode `0x28` (`add_object_pos_from_vars`) as `add_object_pos_from_vars`.
  - Handler `0x7ce7` reads object index `arg0`.
  - It reads signed deltas from byte variables named by `arg1` and `arg2`.
  - It adds them to object fields `[+0x03]` and `[+0x05]`, clamping underflow at
    zero.
  - It sets object flag bit `0x0400` and calls placement helper `0x593a`.
- Named action opcode `0x6c` (`set_input_prompt_char`) as `set_input_prompt_char`.
  - Handler `0x38b4` resolves message `arg0` and stores its first byte in
    `[0x05d7]`.
  - Input redraw helpers `0x37f7`, `0x382e`, and `0x38d7` test `[0x05d7]`
    while drawing or erasing the prompt/input marker.
- Named action opcodes `0x7d` (`save_game_state`) and `0x7e` (`restore_game_state`) as
  `save_game_state` and `restore_game_state`.
  - Save handler `0x2753` creates file `0x1c8c`, writes a 31-byte
    description/header from `0x1c6c`, then writes several length-prefixed
    blocks through helper `0x28c6`.
  - Restore handler `0x2512` opens file `0x1c8c`, seeks to offset `0x1f`, then
    reads matching length-prefixed blocks through helper `0x26b0`.
  - Local strings around `0x0d34`, `0x0d73`, `0x0d87`, `0x0db6`, and `0x0e46`
    identify the restore/save confirmation and error paths.

## Runtime model synthesis and string-table action follow-up

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,220p' docs/src/logic_bytecode.md`
- `sed -n '1,260p' docs/src/graphics_object_pipeline.md`
- `sed -n '1,260p' docs/src/logic_resources.md`
- `ndisasm -b 16 -o 0x7350 -e 0x7550 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x0c30 -e 0x0e30 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x1940 -e 0x1b40 build/cleanroom/AGI.decrypted.exe`
- Local Python dump of `AGIDATA.OVL` action-table entries for opcodes
  `0x70..0x78`.
- `xxd -g 1 -s 0xc8f -l 192 SQ2/AGIDATA.OVL`
- Local Python dump of words at `AGIDATA.OVL` offset `0x0c8f`.

Documented result:

- Added `docs/src/runtime_model.md` and linked it from the mdBook summary and
  overview. This page groups the lower-level handler notes into
  implementation-facing runtime types:
  - byte variables rooted at `DS:0x0009`;
  - packed flags rooted at `DS:0x0109`;
  - fixed string slots rooted at `DS:0x020d`;
  - parsed-word buffers consumed by condition `0x0e` (`input_word_sequence`);
  - 10-byte logic cache/activation records linked from `[0x0977]`;
  - resource cache handles for logic, view-like, picture-like, and sound-like
    payloads;
  - 43-byte object records and their operation families;
  - the graphics/update pipeline phases needed by a replacement
    implementation.
- Decoded action opcode `0x74` (`set_string_slot_from_table`) from handler
  `0x0d70`:
  - It computes destination string slot `0x020d + arg0 * 0x28`.
  - It reads a word pointer from `DS:0x0c8f + arg1 * 2`.
  - It copies up to `0x28` bytes from that pointer into the slot through
    helper `0x4de8`.
  - The sampled static SQ2 `AGIDATA.OVL` table at `0x0c8f` is zero-filled, and
    this opcode was not encountered in the current local SQ2 logic scan, so the
    label remains provisional.
- Added the `0x74` label to `tools/disassemble_logic.py` and documented the
  handler in `docs/src/logic_bytecode.md`.

## Inventory selector, restart prompt, and text-window cleanup actions

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `python3 -B tools/disassemble_logic.py --stats`
- `sed -n '1,220p' docs/src/logic_bytecode.md`
- `sed -n '1,220p' docs/src/runtime_model.md`
- `rg -n "action (1d|7c|80|87|88|89|8a|8b|8c|8d|96|9a|a9)" -C 4`
  over `python3 -B tools/disassemble_logic.py --limit 141`
- Local Python dump of action-table entries for opcodes `0x1d`, `0x7c`,
  `0x80`, `0x87..0x8d`, `0x96`, `0x9a`, and `0xa9`.
- Initial orientation `ndisasm` probes around image offsets `0x1f00`,
  `0x7300`, `0x7700`, and `0x8d00`; these were used only to find nearby
  functions. Final conclusions below were rechecked with the correct executable
  header skip.
- Correct focused `ndisasm` disassemblies using `-e image_offset + 0x200`
  around image offsets `0x1f2b`, `0x2472`, `0x2b78`, `0x31d8`, `0x33bf`,
  `0x5546`, `0x731b`, `0x7753`, and `0x8d3d`.
- Local Python string dump of `SQ2/AGIDATA.OVL` offsets `0x0aab`, `0x0adb`,
  `0x0f1e`, `0x0f26`, `0x0f38`, `0x0f5d`, and menu diagnostic strings around
  `0x1ccc..0x1d04`.
- `rg -n "0x7c|0x80|0x8d|0x96|0x9a|0xa9|0x1d|draw_box|window|text_attr|1755|1d12|1d0a" docs/src tools/disassemble_logic.py`
- `sed -n '160,280p' tools/disassemble_logic.py`
- `sed -n '520,600p' docs/src/logic_bytecode.md`
- `sed -n '700,940p' docs/src/logic_bytecode.md`
- `sed -n '100,190p' docs/src/runtime_model.md`
- `sed -n '1300,1465p' docs/src/clean_room_executable_notes.md`

Documented result:

- Named action opcode `0x7c` (`show_inventory_selection`).
  - Handler `0x31d8` clears the input prompt, saves/restores text attributes,
    enables the alternate text-attribute mode, and calls helper `0x3203`.
  - Helper `0x3203` scans 3-byte entries from `[0x0971]` to `[0x0973]`,
    keeping only entries whose byte `[entry+0x02] == 0xff`.
  - Each kept entry becomes an 8-byte temporary row containing the original
    entry index, a name pointer computed as `[0x0971] + word[entry+0x00]`, and
    row/column display coordinates.
  - The strings at `0x0f26`, `0x0f1e`, `0x0f38`, and `0x0f5d` identify the UI
    as the carried-object list, with an interactive selection mode when flag 13
    is set.
  - Enter stores the selected entry index in byte variable `[0x22]`; Escape
    stores `0xff`.
- Named action opcode `0x80` (`confirm_restart_game`).
  - Handler `0x2472` stops sound, clears input, and uses flag 16 to decide
    whether to skip a confirmation dialog.
  - The confirmation string at `0x0adb` asks whether to restart the game.
  - On confirmation it resets heap/update state, sets flag 6, preserves flag 9,
    clears words `[0x0129]` and `[0x012b]`, optionally reloads logic
    `[0x1d12]`, calls menu/list refresh helper `0x930e`, redraws the prompt, and
    returns zero to the dispatcher.
- Named action opcode `0x9a` (`clear_text_rect_bounds`).
  - Handler `0x7753` reads five immediates and calls helper `0x2bc4`.
  - Helper `0x2bc4` is the full-bounds form of the text rectangle clear helper:
    it saves the cursor, passes top/left/bottom/right and attribute to BIOS
    `int 10h` scroll/clear-window service `AH=0x06`, then restores the cursor.
  - Existing action `0x69` is a narrower wrapper that clears full-width rows
    through helper `0x2b78`, which in turn calls `0x2bc4`.
- Named action opcode `0xa9` (`close_text_window_state`).
  - Handler `0x1f2b` tests word `[0x0d1d]`; if nonzero, it restores a saved
    display rectangle by calling helper `0x560c([0x0d23], [0x0d25])`.
  - It then clears words `[0x0d0f]` and `[0x0d1d]`.
  - The same routine is used both as an action handler and as an internal
    cleanup helper in picture/message/save paths.
- Named action opcode `0x8d` (`show_interpreter_version`).
  - Handler `0x733c` displays the static string at `0x0aab`, which identifies
    the interpreter and version in this executable.
- Decoded action opcode `0x96` without assigning a stable user-level label yet.
  - Handler `0x8d3d` reads three immediates, storing them in words `[0x1d12]`,
    `[0x1d08]`, and `[0x1d0a]`.
  - The third value is clamped upward to at least 2.
  - The first value `[0x1d12]` is later used by the restart and room-switch
    paths as an optional logic resource to load. The other two globals feed the
    menu/list rendering cluster around `0x8e0b`, so this remains a configured
    UI/session state action until that cluster is fully decoded.
- Reconfirmed action opcode `0x1d` as unresolved.
  - Handler `0x731b` sets word `[0x1755] = 1`, calls full refresh helper
    `0x5546`, waits for an event through `0x4618`, refreshes again, then clears
    `[0x1755]`.
  - Helper `0x5546` has a special branch when bit 0 of `[0x1755]` is set that
    rotates every byte of the logical graphics buffer before copying it to the
    display path. The visual/user-level purpose still needs a dynamic trace or
    screenshot before naming.

## Follow-up on diagnostic, pause, input-line, display-toggle, and joystick actions

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/disassemble_logic.py --stats`
- `ndisasm -b 16 -o 0x0250 -e 0x0450 build/cleanroom/AGI.decrypted.exe`
  as an over-broad first probe for the low-offset handler cluster. The useful
  bytes were later narrowed by direct handler inspection; the extra trailing
  output was ignored.
- `ndisasm -b 16 -o 0x14a0 -e 0x16a0 build/cleanroom/AGI.decrypted.exe`
  as an over-broad first probe around the diagnostic handler; conclusions were
  taken only from the aligned handler at `0x14bd`.
- `ndisasm -b 16 -o 0x3700 -e 0x3900 build/cleanroom/AGI.decrypted.exe`
  as an over-broad first probe around input-line refresh helpers; conclusions
  were taken from aligned handlers `0x3726` and `0x3753`.
- Local Python string dump of `SQ2/AGIDATA.OVL` offsets `0x0a19`, `0x0c0d`,
  `0x0fce`, and `0x1e2e`.
- `ndisasm -b 16 -o 0x794c -e 0x7b4c build/cleanroom/AGI.decrypted.exe | sed -n '1,90p'`
- `ndisasm -b 16 -o 0x613c -e 0x633c build/cleanroom/AGI.decrypted.exe | sed -n '1,140p'`
- `python3 -B tools/disassemble_logic.py --limit 141 | rg -n "action (87|88|89|8a|8b|8c|1d|96)" -C 5`
- Local Python hex/text dump of `SQ2/AGIDATA.OVL` offsets `0x1549`, `0x15c1`,
  `0x15c3`, `0x1531`, and `0x153d`.
- `rg -n "0x87|0x88|0x89|0x8a|0x8b|0x8c|Miscellaneous|Interpreter/session|Text-window" docs/src/logic_bytecode.md`
- `wc -l docs/src/logic_bytecode.md docs/src/clean_room_executable_notes.md docs/src/runtime_model.md`
- `sed -n '780,900p' docs/src/logic_bytecode.md`
- `sed -n '220,260p' tools/disassemble_logic.py`

Documented result:

- Named action opcode `0x87` (`show_heap_status`).
  - Handler `0x14bd` formats a 100-byte stack message with helper `0x2374` and
    displays it through `0x1ce8`.
  - The format string at `0x0a19` reads `heapsize: %u`, `now: %u  max: %u`,
    `rm.0, etc.: %u`, and `max script: %d`.
  - The numeric values are computed from heap/script globals `[0x0a55]`,
    `[0x0a57]`, `[0x0a59]`, `[0x0a5b]`, `[0x0a5f]`, and `[0x170f]`.
- Named action opcode `0x88` (`pause_game_message`).
  - Handler `0x0257` sets `[0x0615] = 1`, calls helper `0x4482`, stops sound,
    displays the fixed pause string at `0x0c0d`, then clears `[0x0615]`.
- Named action opcode `0x89` (`refresh_input_line`).
  - Handler `0x3753` runs only when input-line enabled word `[0x05d3]` is
    nonzero.
  - In display mode `[0x1130] == 2` with `[0x0d0f] == 0`, it displays the
    string at `0x1e2e` (`ENTER COMMAND`) through the alternate display helpers
    and sends the current input character byte `[0x001c]` through helper
    `0x3652`.
  - In the other path, helper `0x37a5` appends bytes from the buffer/string at
    `0x0fce` into visible input buffer `0x0fa4` until `[0x0ff8]` reaches that
    source string length.
- Named action opcode `0x8a` (`erase_input_line`).
  - Handler `0x3726` repeatedly calls helper `0x3652(0x08)` while input length
    word `[0x0ff8]` remains nonzero, except that display mode 2 with
    `[0x0d0f] == 0` skips the erase loop.
- Named action opcode `0x8b` (`calibrate_joystick`).
  - Handler `0x613c` initializes joystick/calibration globals, displays the
    string at `0x1549` (`Please center your joystick...`) when joystick state is
    available, waits for Enter or Escape, then computes centered bounds around
    `[0x15c1]` and `[0x15c3]` into `[0x15c9]`, `[0x15cd]`, `[0x15cb]`, and
    `[0x15cf]`.
  - It then loops helper `0x6425` while calibration records at `0x1531` or
    `0x153d` are active, and finishes with helper `0x4482`.
- Named action opcode `0x8c` (`toggle_display_mode_bit`).
  - Handler `0x794c` requires `[0x112e] == 0`, byte variable 0 nonzero, and
    display mode word `[0x1130]` not equal to 2 or 3.
  - It calls `0x1364`, toggles bit 0 of `[0x1130]`, and rebuilds display state
    through helpers `0x2b28`, `0x5528`, `0x2b4f`, and `0x681c`.
- Added implementation-facing notes to `docs/src/runtime_model.md` grouping
  these as UI, diagnostics, and device-state services around the VM.

## Priority-screen action and trace-window configuration

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/disassemble_logic.py --stats`
- `python3 -B tools/disassemble_logic.py --limit 141 | rg -n "action (1d|87|88|89|8a|8b|8c|96|8f)" -C 6`
- `ndisasm -b 16 -o 0x14a0 -e 0x16a0 build/cleanroom/AGI.decrypted.exe | sed -n '1,130p'`
- `ndisasm -b 16 -o 0x0250 -e 0x0450 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x36f0 -e 0x38f0 build/cleanroom/AGI.decrypted.exe | sed -n '1,170p'`
- `ndisasm -b 16 -o 0x6100 -e 0x6300 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x7930 -e 0x7b30 build/cleanroom/AGI.decrypted.exe | sed -n '1,130p'`
- `xxd -g 1 -s 0x0a10 -l 0x80 SQ2/AGIDATA.OVL`
- `xxd -g 1 -s 0x0c00 -l 0x40 SQ2/AGIDATA.OVL`
- `xxd -g 1 -s 0x0fbc -l 0x30 SQ2/AGIDATA.OVL`
- An attempted `python3 -B tools/inspect_words.py 40 62 63 44 55 102 89 36 146`
  command failed because `inspect_words.py` accepts `--id`, not positional
  ids. It produced no evidence and was replaced by the local Python import
  below.
- Local Python use of `tools.inspect_words.decode_entries` over `SQ2/WORDS.TOK`
  for word ids `0x0024`, `0x0028`, `0x002c`, `0x0037`, `0x003e`, `0x003f`,
  `0x0059`, `0x0066`, and `0x0092`.
- Full static `ndisasm` with `rg` for references to globals `[0x1d08]`,
  `[0x1d0a]`, `[0x1d10]`, `[0x1d12]`, `[0x1d14]`, `[0x1d16]`, `[0x1d18]`,
  `[0x1d1a]`, `[0x1d1c]`, and `[0x1d1e]`.
- `ndisasm -b 16 -o 0x8c60 -e 0x8e60 build/cleanroom/AGI.decrypted.exe | sed -n '1,170p'`
- `ndisasm -b 16 -o 0x8e0b -e 0x900b build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x900b -e 0x920b build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- Local Python action-table dump for opcodes `0x90..0x96`.
- `ndisasm -b 16 -o 0x02c0 -e 0x04c0 build/cleanroom/AGI.decrypted.exe | sed -n '1,90p'`
- `python3 -B tools/disassemble_logic.py 140 | sed -n '1,80p'`
- An attempted `rg` command containing markdown backticks in the search pattern
  was misparsed by the shell and produced no evidence; the useful searches above
  were run with simpler patterns.

Documented result:

- Named action opcode `0x1d` (`show_priority_screen`).
  - Handler `0x731b` sets `[0x1755] = 1`, calls full-screen refresh helper
    `0x5546`, waits for an event through `0x4618`, calls `0x5546` again, then
    clears `[0x1755]`.
  - Helper `0x5546` swaps the high and low nibbles of every logical
    graphics-buffer byte while `[0x1755] & 1` is set.
  - The only observed local phrase reaching this action is `show pri`;
    `WORDS.TOK` maps word id `0x0028` to "show" and word id `0x003f` to "pri".
  - The replacement-level behavior is therefore a temporary priority/control
    inspection display that returns to the normal display after input.
- Named action opcode `0x95` (`enable_action_trace_window`) even though no local
  SQ2 logic path currently reaches it.
  - Handler `0x8c91` returns `SI + 1` when word `[0x1d10]` is already nonzero.
  - Otherwise it calls helper `0x8cae`, which starts a trace display only if
    flag 10 is set.
  - Helper `0x8cae` sets `[0x1d10] = 1`, computes box bounds from input-line
    row `[0x05dd]`, trace row offset `[0x1d08]`, and trace height `[0x1d0a]`,
    stores derived values in `[0x1d14]`, `[0x1d16]`, `[0x1d18]`, `[0x1d1a]`,
    `[0x1d1c]`, and `[0x1d1e]`, then draws the trace box with `0x5590`.
- Named action opcode `0x96` (`configure_action_trace_window`).
  - Handler `0x8d3d` stores its three immediates in `[0x1d12]`, `[0x1d08]`,
    and `[0x1d0a]`, clamping `[0x1d0a]` upward to at least 2.
  - The dispatcher at `0x02c3` tests `[0x1d10] == 1` before each action
    dispatch and calls formatter helper `0x8da3`.
  - Formatter helper `0x8e0b` uses optional logic resource `[0x1d12]` for
    trace text, draws opcode/operand values into the trace box, and waits for
    input while trace mode is active.
  - Restart and room-switch paths also reload logic `[0x1d12]` when nonzero,
    so a new implementation should treat it as part of VM trace/session
    configuration, not as ordinary game-state logic.

## Game-signature guard action

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/disassemble_logic.py --stats`
- `python3 -B tools/disassemble_logic.py 140 | rg -n "action 8f|message_count|logic 140|set_input_line_config|set_string_slot_from_message" -C 4`
- Two initial `ndisasm` probes around image offsets `0x0e70` and `0x5b40`
  accidentally used the image offset as the file skip. Those shifted outputs
  were rejected and produced no conclusions.
- Corrected focused disassemblies with the executable header skip included:
  - `ndisasm -b 16 -o 0x0e70 -e 0x1070 build/cleanroom/AGI.decrypted.exe | sed -n '1,140p'`
  - `ndisasm -b 16 -o 0x5b40 -e 0x5d40 build/cleanroom/AGI.decrypted.exe | sed -n '1,110p'`
- Local Python read of logic 140's payload/message table for orientation. That
  raw dump did not decode the encrypted/compressed message text, but it did
  confirm the local bytecode context around the single static `0x8f` use.

Documented result:

- Named action opcode `0x8f` (`verify_game_signature`).
  - Handler `0x0e7e` reads one immediate message number.
  - It resolves that message through `0x21f0`, pushes maximum length 7, and
    copies the string to absolute buffer `0x0002` through helper `0x4de8`.
  - It then calls helper `0x5b49`.
  - Helper `0x5b49` compares bytes at `0x0002` against an embedded `SQ2\0`
    string at image offset `0x5b6c`.
  - On the first mismatch it calls helper `0x02ae`, the same helper seen in
    restart/exit-like paths.
  - The only observed local static use is in logic 140 immediately before
    `0x6f` (`set_input_line_config`), consistent with a game-signature or
    game-configuration guard.

## Normalized string-slot equality condition

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/disassemble_logic.py --stats`
- `sed -n '120,230p' docs/src/logic_bytecode.md`
- `rg -n "helper_0eac|0x0f|0eac|09db|condition" docs/src tools`
- `ndisasm -b 16 -o 0x09c0 -e 0x0bc0 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x0e80 -e 0x1080 build/cleanroom/AGI.decrypted.exe`
- `xxd -g 1 -s 0x0b40 -l 0x40 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x4f90 -e 0x5190 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x18a0 -e 0x1aa0 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `sed -n '80,230p' tools/disassemble_logic.py`
- `rg -n "0x094b|0x0c67|0xc67|0x0c75|0xc75|delimiter|punct|normalize|string slot|0x020d|0x20d" docs/src tools`
- `xxd -g 1 -s 0x0e60 -l 0xa0 build/cleanroom/AGI.decrypted.exe`
- `xxd -g 1 -s 0x0f40 -l 0x80 build/cleanroom/AGI.decrypted.exe`
- `xxd -g 1 -s 0x1140 -l 0x100 build/cleanroom/AGI.decrypted.exe`
- `sed -n '280,325p' docs/src/logic_bytecode.md`
- `sed -n '1150,1185p' docs/src/clean_room_executable_notes.md`
- `sed -n '30,65p' docs/src/runtime_model.md`
- `rg -n "094b|0x94b|0x094b" -S .`
- Local byte-pattern probes over `build/cleanroom/AGI.decrypted.exe`,
  `SQ2/AGIDATA.OVL`, and related files to map known delimiter tables back to
  their storage file.
- `strings -a -t x build/cleanroom/AGI.decrypted.exe | rg "ENTER COMMAND|You are carrying|nothing|AGI|COMMAND|carrying|Press ENTER|Press ESC"`
- `xxd -g 1 -s 0x0940 -l 0x80 SQ2/AGIDATA.OVL`
- `xxd -g 1 -s 0x0c60 -l 0x30 SQ2/AGIDATA.OVL`
- Local byte reads of zero-terminated data at `SQ2/AGIDATA.OVL` offsets
  `0x094b`, `0x0c67`, `0x0c75`, and `0x020d`.
- `sed -n '140,225p' docs/src/logic_bytecode.md`

Documented result:

- Renamed condition opcode `0x0f` from provisional `helper_0eac` to
  `string_slots_equal_normalized`.
- The condition table entry dispatches to handler `0x09db`, has two fixed
  operands, and has metadata byte `0x00`.
- Handler `0x09db` reads two immediate byte operands, pushes them, and calls
  helper `0x0eac`.
- Helper `0x0eac` allocates two local buffers, calls helper `0x0ef8` for each
  operand, and then compares the normalized buffers byte-for-byte through their
  zero terminators.
- Helper `0x0ef8` computes a source string slot as
  `0x020d + slot * 0x28`, walks it until a zero byte, skips bytes found in the
  zero-terminated table at `DS:0x094b`, lowercases ASCII uppercase bytes through
  helper `0x4fea`, writes kept bytes to the destination buffer, and appends a
  zero terminator.
- `DS:0x094b` is data in `SQ2/AGIDATA.OVL`, not the same offset in the EXE
  body. The local SQ2 table contains
  `20 09 2e 2c 3b 3a 27 21 2d 00`, meaning space, tab, `.`, `,`, `;`, `:`,
  `'`, `!`, and `-` are ignored for this comparison.
- Updated `docs/src/runtime_model.md` to separate this direct normalized string
  comparison from the dictionary-backed parsed-word condition `0x0e`.

## Object diagnostic action and field-name confirmation

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/disassemble_logic.py --stats`
- `rg -n "provisional|unknown|needs|still|action_00|object_motion_or_state|refresh_object_helper|picture|draw|0x5546|0x5762|0x593a|0x57cf|0x3ae7|0x39f7|0x4a3b|0x4acf" docs/src tools`
- `python3 -B tools/disassemble_logic.py --limit 142 | rg -n "action 85|display_object_state_summary_var|logic [0-9]+|message_count" -C 8`
- `ndisasm -b 16 -o 0x7280 -e 0x7480 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x1c00 -e 0x1e00 build/cleanroom/AGI.decrypted.exe | sed -n '1,200p'`
- `rg -n "0x85|display_object_state_summary_var|72b5|0x72b5|object state|summary" docs/src tools`
- `xxd -g 1 -s 0x1700 -l 0x80 SQ2/AGIDATA.OVL`
- `python3 -B tools/inspect_words.py --id 0x0031 --limit 20`
- `python3 -B tools/inspect_words.py --id 0x0017 --limit 20`
- `python3 -B tools/inspect_words.py --id 0x001a --limit 20`
- `python3 -B tools/inspect_words.py --id 0x002c --limit 20`
- `sed -n '1,120p' tools/disassemble_logic.py`
- `rg -n "message|messages|decode|crypt|logic_payload|message_count|21f0" tools docs/src/logic_resources.md docs/src/clean_room_executable_notes.md`
- `python3 -B tools/disassemble_logic.py 99 | sed -n '1,140p'`
- `sed -n '92,118p' docs/src/logic_resources.md`
- `sed -n '255,295p' docs/src/clean_room_executable_notes.md`
- Local Python decoding of logic 99 messages using the previously documented
  logic-message format and XOR key at `SQ2/AGIDATA.OVL:0x08f1`.
- `sed -n '180,205p' docs/src/graphics_object_pipeline.md`
- `sed -n '704,722p' docs/src/logic_bytecode.md`
- `sed -n '632,646p' docs/src/clean_room_executable_notes.md`
- An attempted `rg` command containing a markdown backtick in the search pattern
  was misparsed by the shell and produced no evidence.
- `rg -n "display_object_state_summary_var|display_object_diagnostics_var|0x85|object #:|Object %d|stepsize" docs/src tools`
- `sed -n '130,165p' docs/src/runtime_model.md`

Documented result:

- Renamed action opcode `0x85` from `display_object_state_summary_var` to
  `display_object_diagnostics_var`.
- Handler `0x72b5` reads one operand as a variable slot, then reads the object
  index from `var[arg0]`.
- It multiplies the object index by `0x2b`, adds the object array base
  `[0x096b]`, and formats fields from that object:
  - object index from the variable value;
  - `[object+0x03]` as `x`;
  - `[object+0x05]` as `y`;
  - `[object+0x1a]` as `xsize`;
  - `[object+0x1c]` as `ysize`;
  - `[object+0x24]` as `pri`;
  - `[object+0x1e]` as `stepsize`.
- The format string at `DS:0x1713` in `SQ2/AGIDATA.OVL` reads:

```text
Object %d:
x: %d  xsize: %d
y: %d  ysize: %d
pri: %d
stepsize: %d
```

- The only local SQ2 use is in logic 99. The script accepts WORDS.TOK id
  `0x0031` (`object`) or `0x0017` (`sp`), prompts with decoded message 7
  (`object #:`), stores the number in variable 64, and then calls action
  `0x85`.
- Logic 99 is a diagnostic command hub: nearby decoded messages include
  `new room:`, `x:`, `y:`, `object number:`, `var number:`, `var value:`,
  `flag number:`, and flag status messages.
- Updated the object runtime model and graphics/object pipeline notes to use
  this diagnostic template as additional evidence for the field meanings.

## Targeted object movement actions

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x6cc0 -e 0x6ec0 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x1620 -e 0x1820 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `rg -n "object_motion_or_state|0x51|0x52|0x1672|\\+0x27|\\+0x28|\\+0x29|\\+0x2a|boundary completion|motion/control" docs/src tools`
- `python3 -B tools/disassemble_logic.py --stats | sed -n '/actions/,$p' | sed -n '1,80p'`
- `sed -n '430,455p' docs/src/graphics_object_pipeline.md`
- `sed -n '780,812p' docs/src/clean_room_executable_notes.md`
- `sed -n '136,160p' docs/src/runtime_model.md`
- `xxd -g 2 -s 0x0a80 -l 0x40 SQ2/AGIDATA.OVL`
- `xxd -g 1 -s 0x0a80 -l 0x28 SQ2/AGIDATA.OVL`
- Local Python read of the nine little-endian direction table words at
  `SQ2/AGIDATA.OVL:0x0a85`.
- `python3 -B tools/disassemble_logic.py 1 2 3 4 5 6 7 8 9 10 | rg -n "action (51|52)" -C 3`
- `python3 -B tools/disassemble_logic.py --limit 141 | rg -n "action (51|52)" -C 2 | sed -n '1,160p'`
- `sed -n '40,58p' docs/src/logic_bytecode.md`
- `sed -n '470,488p' docs/src/logic_bytecode.md`
- `sed -n '686,701p' docs/src/logic_bytecode.md`
- `rg -n "object_motion_or_state|object_motion_or_state_var|motion_parameters|Motion control|Targeted-motion|targeted-motion|0x1672" docs/src tools/disassemble_logic.py`
- `rg -n "object_motion_or_state|object_motion_or_state_var|move_object_to|0x0a85|target above|completion flag" docs/src tools/disassemble_logic.py`
- `python3 -B tools/disassemble_logic.py 1 | rg -n "move_object_to|action 5[12]" -C 2`

Documented result:

- Renamed action opcode `0x51` from `object_motion_or_state` to
  `move_object_to`.
- Renamed action opcode `0x52` from `object_motion_or_state_var` to
  `move_object_to_var`.
- Handler `0x6ce4` (`0x51`) reads:
  - object index;
  - target X;
  - target Y;
  - optional step-size override, where zero means keep the current step size;
  - completion flag.
- Handler `0x6d61` (`0x52`) has the same contract, except target X, target Y,
  and step-size override are read from variables.
- Both handlers set object byte `[+0x22] = 3`, store target X/Y in
  `[+0x27]`/`[+0x28]`, save old step size `[+0x1e]` into `[+0x29]`, store the
  completion flag in `[+0x2a]`, clear the completion flag, set object bit
  `0x0010`, and call helper `0x1672`.
- Helper `0x1672` calls `0x16ed(current_x, current_y, target_x, target_y,
  step)` and stores the returned direction-like byte in object byte `[+0x21]`.
  For object 0 it also mirrors that direction byte to global byte `[0x000f]`.
- Helper `0x16ed` classifies the target X and Y relative to the current
  position and step size, then indexes the nine-word table at `DS:0x0a85`.
  The local SQ2 table is:

```text
target above:  8 1 2
target level:  7 0 3
target below:  6 5 4
               left near right
```

- The zero center entry means an object already at, or within one step of, the
  target completes immediately.
- Completion helper `0x16b9` restores step byte `[+0x1e]` from `[+0x29]`, sets
  flag `[+0x2a]`, clears object byte `[+0x22]`, and for object 0 sets
  `[0x0139] = 1` and clears global direction byte `[0x000f]`.
- Updated the bytecode spec, object/graphics pipeline, and runtime model with
  the higher-level targeted-movement contract.

## Autonomous object motion modes 1 and 2

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '680,735p' docs/src/logic_bytecode.md`
- `sed -n '180,205p' docs/src/graphics_object_pipeline.md`
- `sed -n '520,550p' docs/src/graphics_object_pipeline.md`
- `sed -n '140,165p' docs/src/runtime_model.md`
- `sed -n '1038,1064p' docs/src/clean_room_executable_notes.md`
- `sed -n '160,190p' tools/disassemble_logic.py`
- `ndisasm -b 16 -o 0x6df0 -e 0x6ec0 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x6df0 -e 0x6ff0 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x0b80 -e 0x0d80 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x3f30 -e 0x4130 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x0a80 -e 0x0c80 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x3f30 -e 0x4130 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x6df0 -e 0x6ff0 build/cleanroom/AGI.decrypted.exe`
- `rg -n "0bb3|0x0bb3|3f5a|0x3f5a|16ed|0x16ed|\\+0x22 == 2|field_22_mode1|object_step_or_state_limited" docs/src tools`
- `ndisasm -b 16 -o 0x1660 -e 0x1860 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x09f0 -e 0x0bf0 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x0b30 -e 0x0d30 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x1680 -e 0x1880 build/cleanroom/AGI.decrypted.exe | sed -n '1,160p'`
- `python3 -B tools/disassemble_logic.py --opcode 0x53`
- `python3 -B tools/disassemble_logic.py --opcode 0x54`
- `python3 -B tools/disassemble_logic.py --opcode 0x55`
- `python3 -B tools/disassemble_logic.py --stats`
- `tail -n 80 docs/src/clean_room_executable_notes.md`
- `rg -n "object_step_or_state_limited|set_object_field_22_mode1|clear_object_field_22\\)|approach_first_object_until_near|start_random_motion|stop_motion_mode|min\\(arg1" docs/src tools/disassemble_logic.py`

Rejected or non-evidence probes:

- The first `ndisasm` command around `0x6df0` used `-e 0x6ec0`. For this
  decrypted executable image, the file skip must include the `0x200`-byte MZ
  header, so the correct skip for image offset `0x6df0` is `0x6ff0`. The
  shifted command was treated as rejected evidence.
- The three `python3 -B tools/disassemble_logic.py --opcode ...` commands only
  produced argument-parser errors because the local disassembler has no
  `--opcode` option. They were not used as evidence.
- The broad `ndisasm` commands without `sed` produced excessive trailing
  disassembly. Only the leading ranges later rechecked with focused `sed`
  commands were used as evidence.

Documented result:

- Corrected action `0x53`: handler `0x6e02` sets object byte `[+0x22] = 2`,
  reads operand 1, compares it with current step byte `[+0x1e]`, and stores the
  larger value in `[+0x27]`. The earlier `min(...)` description was wrong.
- Action `0x53` stores operand 2 as completion flag byte `[+0x28]`, clears that
  flag through `0x74d0`, initializes byte `[+0x29] = 0xff`, and sets object bit
  `0x0010`.
- Helper `0x0b36`, reached from mode byte `+0x22 == 2`, computes the first
  object entry's center X as `first[+0x03] + first[+0x1a] / 2` and the current
  object's center X as `object[+0x03] + object[+0x1a] / 2`.
- The same helper calls `0x16ed(object_center_x, object_y,
  first_object_center_x, first_object_y, object[+0x27])`. If the returned
  direction is zero, it clears object bytes `[+0x21]` and `[+0x22]` and sets
  completion flag `[+0x28]` through `0x74c6`.
- If mode 2 sees object bit `0x4000`, it chooses a random nonzero direction
  through `0x3fa3`, stores it in `[+0x21]`, and computes a delay in `[+0x29]`
  from the object/first-object separation and current step byte. While
  `[+0x29]` is nonzero, the helper counts it down by step byte `[+0x1e]`; when
  the delay reaches zero it writes the direct approach direction to `[+0x21]`.
- Renamed opcode label `0x53` to `approach_first_object_until_near`.
- Action `0x54` handler `0x6e68` sets `[0x0139] = 0` when operating on the
  first object entry, then sets object byte `[+0x22] = 1` and object bit
  `0x0010`.
- Helper `0x3f5a`, reached from mode byte `+0x22 == 1`, decrements countdown
  byte `[+0x27]`. When the old countdown is zero, or object bit `0x4000` is set,
  it calls `0x3fa3`, stores the random direction `0..8` in `[+0x21]`, mirrors
  that direction to global byte `[0x000f]` for the first object, and reseeds
  `[+0x27]` by repeatedly taking random `% 0x33` until the value is at least 6.
- Renamed opcode label `0x54` to `start_random_motion`.
- Action `0x55` handler `0x6ea1` only clears object byte `[+0x22]`. It does not
  clear direction byte `[+0x21]` or update the first-object globals.
- Renamed opcode label `0x55` to `stop_motion_mode`.
- Updated the bytecode spec, graphics/object pipeline, runtime model, and local
  disassembler labels with these higher-level motion-mode contracts.

## Remaining action-table opcode pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,260p' tools/disassemble_logic.py`
- `sed -n '260,430p' tools/disassemble_logic.py`
- `rg -n "action_[0-9a-f]{2}|condition_[0-9a-f]{2}|unknown|provisional|thin|remaining|TODO|needs" docs/src tools`
- `python3 -B tools/disassemble_logic.py --stats`
- `rg -n "061d|action table|condition table|dispatch table|TableEntry|load_table" docs/src tools/disassemble_logic.py`
- `sed -n '1,80p' docs/src/logic_bytecode.md`
- `sed -n '240,330p' docs/src/clean_room_executable_notes.md`
- Python one-off dump of all unnamed action-table entries at
  `SQ2/AGIDATA.OVL:0x061d` and condition-table bytes through opcode `0x25`.
- `ndisasm -b 16 -o 0x4b00 -e 0x4d00 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x3ec0 -e 0x40c0 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x8270 -e 0x8470 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x4c00 -e 0x4e00 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x2700 -e 0x2900 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x7180 -e 0x7380 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x6020 -e 0x6220 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x5040 -e 0x5240 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `rg -n "0x0e72|0xe72|0x1530|1530|0x124a|124a|0x127a|127a|0x0143|0x143|0x05e1|0x5e1|0x1823|1823|0x1809|1809|0x1c8c|1c8c|0x5051|0x4b17|0x3ecd|0x828f|0x3ee9|0x4c15|0x2726|0x718b|0x719d|0x602f|0x4d10" docs/src tools`
- `strings -a -t x build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `xxd -g 1 -s 0xe60 -l 0x90 SQ2/AGIDATA.OVL`
- `xxd -g 1 -s 0x1800 -l 0x60 SQ2/AGIDATA.OVL`
- `ndisasm -b 16 -o 0x02a0 -e 0x04a0 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `sed -n '90,140p' docs/src/agi_executable.md`
- `sed -n '780,850p' docs/src/clean_room_executable_notes.md`
- `sed -n '680,710p' docs/src/graphics_object_pipeline.md`
- `sed -n '1360,1380p' docs/src/clean_room_executable_notes.md`
- `sed -n '50,90p' docs/src/graphics_object_pipeline.md`
- `sed -n '600,618p' docs/src/logic_bytecode.md`
- `sed -n '440,470p' docs/src/logic_bytecode.md`
- `sed -n '580,620p' docs/src/logic_bytecode.md`
- `sed -n '138,170p' docs/src/logic_bytecode.md`
- `sed -n '112,170p' docs/src/logic_bytecode.md`
- `sed -n '600,630p' docs/src/logic_bytecode.md`
- `sed -n '900,950p' docs/src/logic_bytecode.md`
- `sed -n '960,1035p' docs/src/logic_bytecode.md`
- `sed -n '930,990p' docs/src/logic_bytecode.md`
- `sed -n '850,930p' docs/src/logic_bytecode.md`
- `sed -n '45,75p' docs/src/graphics_object_pipeline.md`
- `rg -n "action_[0-9a-f]{2}|object_step_or_state_limited|set_object_field_22_mode1|clear_object_field_22\\)|\\b0x1c\\b|\\b0x20\\b|\\b0x90\\b|\\b0x99\\b|\\b0x9b\\b|\\b0xaa\\b|\\b0xab\\b|\\b0xac\\b|\\b0xad\\b|\\b0xae\\b|\\b0xaf\\b" docs/src tools/disassemble_logic.py`
- Python one-off import of `tools/disassemble_logic.py` with `sys.modules`
  registration, followed by an unnamed-action audit.

Rejected or non-evidence probes:

- The first Python one-off import of `tools/disassemble_logic.py` omitted
  `sys.modules[spec.name] = module`. Python 3.14's `dataclass` implementation
  expected that registration and raised an `AttributeError`; this failed probe
  was not used as evidence.

Documented result:

- Dumped the full action table at `SQ2/AGIDATA.OVL:0x061d`. Before this pass,
  unnamed action entries were `0x00`, `0x1c`, `0x20`, `0x7f`, `0x90`, `0x99`,
  `0x9b`, and `0xaa..0xaf`.
- Added local labels for all remaining action-table entries:
  - `0x00` (`end`), a structural main-loop terminator.
  - `0x1c` (`overlay_picture_var`), a variable-sourced picture path that
    selects a cached picture payload and enters picture decoder `0x6440`
    instead of `0x6445`.
  - `0x20` (`discard_view`) and `0x99` (`discard_view_var`), which release or
    rewind cached view-like resources through helper `0x3f0d`.
  - `0x7f` (`noop`), `0x9b` (`noop_2`), and `0xaf`
    (`noop_1_table_count`), no-op table entries with different observed
    pointer-advance behavior.
  - `0x90` (`append_message_to_log_file`), which opens or creates `logfile`,
    appends room/input-line context, appends a resolved message, and closes the
    handle.
  - `0xaa` (`copy_save_description_to_string_slot`), which copies up to
    `0x1f` bytes from buffer `0x0e72` into a logic string slot.
  - `0xab` (`save_event_buffer_count`) and `0xac`
    (`restore_event_buffer_count`), which preserve and restore the pair-buffer
    count `[0x0143]` through `[0x05e1]`.
  - `0xad` (`increment_global_1530`), which only increments byte `[0x1530]`.
  - `0xae` (`rebuild_priority_table_from_y`), which rebuilds the 168-byte
    priority/control table at `0x127a` from an immediate row/value.
- The follow-up unnamed-action audit reports `unnamed actions: []`.
- Dumped condition-table bytes through opcode `0x25`. Entries `0x00..0x12`
  remain the valid-looking condition table; bytes after `0x12` decode as
  string/data bytes and then zero fill if forced through the same 4-byte shape.
  No local SQ2 condition list uses condition opcodes `0x13..0x25`, so they are
  documented as invalid/reserved for this build rather than as real predicates.
- Updated the bytecode spec, graphics/object pipeline note, and local
  disassembler labels.

## Symbolic label map setup

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,220p' AGENTS.md`
- `rg -n "symbolic|label|labels|address|offset|0x293c|0x061d|AGI.decrypted|clean_room_executable_notes|SUMMARY" docs/src tools AGENTS.md`
- `sed -n '1,220p' docs/src/SUMMARY.md`
- `git status --short`
- `sed -n '1,120p' docs/src/README.md`
- `sed -n '1,220p' docs/src/agi_executable.md`
- `sed -n '1,120p' docs/src/runtime_model.md`
- `tail -n 120 docs/src/clean_room_executable_notes.md`
- `rg -n "0x293c|0x02c4|0x07e3|0x061d|0x08fd|0x07ab|0x08f1|0x21f0|0x119a|0x117d|0x12ae|0x4305|0x2e32|0x2e56|0x4a3b|0x4acf|0x4b3b|0x4bce|0x6445|0x6440|0x6475|0x5546|0x5528|0x5257|0x52f9" docs/src`
- `rg -n "0x39f7|0x3ae7|0x3bb7|0x3c1b|0x3ccb|0x593a|0x5762|0x9db6|0x9db0|0x9db3|0x150a|0x16ed|0x1672|0x16b9|0x3fa3|0x3f5a|0x0b36|0x1ce8|0x1f2b|0x2374|0x1f54|0x2753|0x2512|0x28c6|0x26b0|0x85e5" docs/src`
- `rg -n "0x096b|0x096d|0x0971|0x0977|0x0981|0x11b2|0x1377|0x1130|0x112e|0x136f|0x127a|0x0a85|0x1707|0x1709|0x0143|0x0009|0x0109|0x020d|0x0c7b|0x0ca3|0x094b" docs/src`
- `sed -n '18,34p' docs/src/resource_files.md`
- `sed -n '60,72p' docs/src/resource_files.md`
- `rg -n "11b2|11b4|11b6|11b8|11ba" docs/src/clean_room_executable_notes.md docs/src/resource_files.md docs/src/symbolic_labels.md`
- ``rg -n 'Symbolic label map setup|symbolic_labels|Maintain `docs/src/symbolic_labels.md`|Symbolic Labels' AGENTS.md docs/src/SUMMARY.md docs/src/README.md docs/src/clean_room_executable_notes.md docs/src/symbolic_labels.md``

Rejected or non-evidence probes:

- A final `rg` sanity command used double quotes around a pattern containing
  backticks. The shell attempted command substitution of
  `docs/src/symbolic_labels.md` and printed a permission-denied diagnostic.
  The same search was rerun with single quotes and the failed command was not
  used as evidence.

Documented result:

- Added `docs/src/symbolic_labels.md` as the cross-version label map. The map
  separates stable project names from SQ2-specific image, overlay, and data
  offsets.
- Seeded the first map with labels already supported by the existing evidence
  trail: logic interpreter dispatch, message handling, resource loading, DOS
  wrappers, picture/display helpers, object/view/motion helpers, save/text
  helpers, and key runtime globals.
- Rechecked the directory pointer order against the resource-file chapter and
  recorded view directory `[0x11b4]`, picture directory `[0x11b6]`, and sound
  directory `[0x11b8]`.
- Updated the mdBook summary and overview so the label map is part of the
  rendered documentation.
- Updated `AGENTS.md` to require future passes to update the symbolic label map
  when assigning or revising routine/global/table names.

## Picture and view decode/draw pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,240p' AGENTS.md`
- `sed -n '1,260p' docs/src/graphics_object_pipeline.md`
- `sed -n '260,760p' docs/src/graphics_object_pipeline.md`
- `sed -n '1,220p' docs/src/symbolic_labels.md`
- `ndisasm -b 16 -o 0x6440 -e 0x6640 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x5200 -e 0x5400 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x5680 -e 0x5880 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x9db0 SQ2/IBM_OBJS.OVL`
- `xxd -g 2 -s 0x15d6 -l 0x20 SQ2/AGIDATA.OVL`
- `ndisasm -b 16 -o 0x6475 -e 0x6675 build/cleanroom/AGI.decrypted.exe | sed -n '1,170p'`
- `ndisasm -b 16 -o 0x6600 -e 0x6800 build/cleanroom/AGI.decrypted.exe | sed -n '1,210p'`
- `ndisasm -b 16 -o 0x52f9 -e 0x54f9 build/cleanroom/AGI.decrypted.exe | sed -n '1,95p'`
- `xxd -g 2 -s 0x15f8 -l 0x60 SQ2/AGIDATA.OVL`
- `xxd -g 2 -s 0x1618 -l 0x50 SQ2/AGIDATA.OVL`
- `ndisasm -b 16 -o 0x526f -e 0x546f build/cleanroom/AGI.decrypted.exe | sed -n '1,80p'`
- `ndisasm -b 16 -o 0x533b -e 0x553b build/cleanroom/AGI.decrypted.exe | sed -n '1,230p'`
- `sed -n '1,260p' tools/inspect_view.py`
- `python3 -B tools/inspect_view.py 11`
- `ndisasm -b 16 -o 0x9db0 SQ2/IBM_OBJS.OVL | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x587d -e 0x5a7d build/cleanroom/AGI.decrypted.exe | sed -n '1,170p'`
- Python one-off scan of all local view payloads through `tools/inspect_view.py`
  to count frame control-byte values and nonzero preview string offsets.
- Python one-off scan to find the first local frame with control bit `0x80`;
  the first match was view 0, group 0, frame 0.

Rejected or non-evidence probes:

- The broad `ndisasm` reads around `0x6440`, `0x5200`, and `0x5680` produced
  excessive trailing disassembly because no output filter was applied. They
  were useful for orientation only; the focused `sed`-limited reruns above are
  the cited evidence for the documented details.

Documented result:

- Expanded the picture decoder notes from a handler sketch into opcode-level
  semantics for command bytes `0xf0..0xfa`, grounded in the local dispatch
  table at `SQ2/AGIDATA.OVL:0x15d6`.
- Identified `0xf0`/`0xf1` as low-nibble draw enable/disable commands and
  `0xf2`/`0xf3` as high-nibble control draw enable/disable commands.
- Identified the coordinate reader contract: `0x66c1` reads/clamps X to
  `0x9f`, `0x66d4` reads/clamps Y to `0xa7`, and bytes above `0xef` terminate
  the current drawing command for the main scanner.
- Split the path-drawing families:
  - `0xf4` starts with a vertical segment and then alternates
    horizontal/vertical corners.
  - `0xf5` starts with a horizontal segment and then alternates
    vertical/horizontal corners.
  - `0xf6` draws absolute point-to-point lines through helper `0x66e1`.
  - `0xf7` draws relative vector steps from packed delta bytes.
- Documented `0xf8` conservatively as a seed-fill command through helper
  `0x533b`; its stack-state names remain open, but its seed/expand/write shape
  is stable.
- Documented pattern command `0xf9` and patterned draw command `0xfa`, including
  pattern pointer table `DS:0x1619` and mask data rooted at `DS:0x15f9`.
- Expanded the view frame model from the IBM object overlay:
  - frame byte `+0x00` is width;
  - frame byte `+0x01` is height/row count;
  - frame byte `+0x02` low nibble is the transparent color/run code;
  - row data begins at `+0x03`;
  - zero ends a row;
  - nonzero bytes encode high-nibble color and low-nibble run length.
- Documented object drawing's priority/control comparison: the overlay writes
  object priority/control from object byte `+0x24` into the destination high
  nibble, skips writes behind higher existing control values, and may scan
  downward in the same column to find a comparison value.
- Documented helper `0x587d` as the bit-`0x80` frame rewrite path. It compares
  frame control bits `0x70` with object byte `+0x0a`, updates those bits, and
  rebuilds the row-encoded frame stream in place when they differ.
- Added symbolic labels for the new picture command handlers, line/fill
  helpers, pattern data, picture draw-state globals, and the view-frame rewrite
  helper.

## 2026-07-03: source-first lifecycle pass for room, menu, save, and sound

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,260p' docs/src/symbolic_labels.md`
- `rg -n "room\\.switch|switch_state|main_cycle|menu_direction|sound|save|restore|selection|0x1792|0x0150|0x44a9|0x16b3" docs/src tools tests`
- `python3 -B tools/disassemble_logic.py 0`
- `ndisasm -b 16 -o 0x175c -e 0x195c build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x0150 -e 0x0350 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x4529 -e 0x4729 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x93d1 -e 0x95d1 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x2470 -e 0x2670 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x2700 -e 0x2900 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x51d0 -e 0x53d0 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x85e0 -e 0x87e0 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x10d0 -e 0x12d0 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x1485 -e 0x1685 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x7060 -e 0x7260 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x681c -e 0x6a1c build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x4480 -e 0x4680 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `xxd -g 2 -s 0x16b3 -l 0x30 SQ2/AGIDATA.OVL`
- `xxd -g 2 -s 0x16d7 -l 0x30 SQ2/AGIDATA.OVL`

Rejected or corrected observations:

- A first `xxd` read of offset `0x16b3` used
  `build/cleanroom/AGI.decrypted.exe`. That offset belongs to AGIDATA runtime
  data, so the dump was not used. The command was rerun against
  `SQ2/AGIDATA.OVL`, confirming the movement table bytes.

Documented result:

- Refined `code.room.switch_state` (`0x1792`) from disassembly. The helper
  stops sound, resets heap/update-list state, clears parser/input state,
  initializes and enables resource-event recording, resets all object records,
  clears the logic cache root, sets object-boundary word `[0x0139]`, resets
  horizon-like word `[0x012d]` to `0x24`, updates current/previous room byte
  variables, loads the destination logic, reloads trace logic `[0x1d12]` when
  configured, consumes byte variable 2 as the entry-boundary selector, sets
  flag 5, refreshes display/status/input state, and returns zero.
- Re-read `code.engine.main_cycle` (`0x0150`) to explain the zero return. When
  `code.logic.call_logic(0)` returns zero, the main cycle clears temporary
  boundary bytes and calls logic 0 again immediately. This supports the model
  that room-switch bytecode intentionally aborts the current script stream so
  logic 0 can re-enter and later dispatch the current room with
  `call_logic_var(v0)`.
- Mapped input/event queue helpers around `0x44a9`, `0x44f9`, `0x4529`,
  `0x467f`, `0x46b6`, and `0x46e8`. The raw event queue is a 20-record
  circular queue rooted at `DS:0x11ba`, with write pointer `0x120a` and read
  pointer `0x120c`.
- Confirmed `data.input.menu_direction_event_map` at AGIDATA `0x16b3` maps
  raw BIOS arrow/keypad words `0x4800`, `0x4900`, `0x4d00`, `0x5100`,
  `0x5000`, `0x4f00`, `0x4b00`, and `0x4700` to movement codes `1..8`.
  The adjacent display-adapter remap table at `0x16d7` maps numeric keypad
  bytes `0x38`, `0x39`, `0x36`, `0x33`, `0x32`, `0x31`, `0x34`, and `0x37`
  to movement codes `1..8`.
- Refined `code.menu.interact` (`0x93d1`). Event type 1 handles Enter/Escape:
  Enter enqueues type-3 item ids only for enabled items, while Escape exits
  without a selection. Event type 2 dispatches movement codes through the
  navigation table and persists current heading/item globals `[0x1d2e]` and
  `[0x1d30]` after each non-exit movement.
- Refined save/restore from `0x2472`, `0x2512`, `0x2753`, and
  `0x85e5`. The shared selector handles modal text/path UI and returns zero
  for cancel. Save writes a 31-byte header followed by length-prefixed engine,
  object, inventory, resource-event, and logic/cache blocks. Restore reads the
  same block families and calls `code.restore.replay_resource_events` (`0x681c`)
  to rebuild loaded resource/display/object state before menu refresh.
- Refined sound source notes. Action `0x63` stops any prior active sound,
  stores and clears the completion flag, looks up an already loaded sound
  record through `0x50d8`, and calls driver start helper `0x7f96`. Action
  `0x64` calls `0x5234`; that helper only sets the configured completion flag
  when active-state word `[0x1258]` is nonzero, then clears active state and
  calls driver stop helper `0x80af`.
- Added symbolic labels for the newly mapped room, heap, input/event, menu,
  restore, save, sound, and event-queue roles.

## Initial graphics compatibility test scaffold

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `find . -maxdepth 3 -type f | sort | sed -n '1,220p'`
- `sed -n '1,260p' tools/disassemble_logic.py`
- `sed -n '1,260p' tools/inspect_view.py`
- `sed -n '1,200p' .gitignore`
- `sed -n '1,200p' docs/.gitignore`
- `rg -n "test|suite|compat|QEMU|picture decoder|View payload|0xf8|seed_fill" docs/src tools AGENTS.md`
- `find . -maxdepth 2 -type d | sort`
- `python3 -B -m unittest tests.test_graphics_rendering`
- Python one-off import of `tools.agi_graphics` to locate present `PICDIR`
  entries; the first present picture entry was picture 1.
- Python one-off import of `tools.agi_graphics` to calculate current renderer
  hashes for picture 1, view 0 group 0 frame 0, and view 11 group 0 frame 0.
- `python3 -B tools/render_picture.py 1 --output build/rendered/picture_001_visual.ppm`
- `python3 -B tools/render_picture.py 1 --channel control --output build/rendered/picture_001_control.ppm`
- `python3 -B tools/render_view.py 0 0 0 --output build/rendered/view_000_00_00.ppm`
- `python3 -B tools/render_view.py 11 0 0 --output build/rendered/view_011_00_00.ppm`
- `magick build/rendered/picture_001_visual.ppm build/rendered/picture_001_visual.png`
- `magick build/rendered/picture_001_control.ppm build/rendered/picture_001_control.png`
- `magick build/rendered/view_000_00_00.ppm build/rendered/view_000_00_00.png`
- `magick build/rendered/view_011_00_00.ppm build/rendered/view_011_00_00.png`
- `identify -verbose build/rendered/picture_001_visual.png | sed -n '1,80p'`
- `identify -verbose build/rendered/picture_001_control.png | sed -n '1,80p'`
- `identify -verbose build/rendered/view_000_00_00.png | sed -n '1,80p'`
- `identify -verbose build/rendered/view_011_00_00.png | sed -n '1,80p'`
- `python3 -B -m unittest`
- `python3 -B -m unittest discover -s tests`
- `mdbook build docs`
- `git diff --check`

Rejected or non-evidence probes:

- The first renderer smoke test assumed picture 0 was present. The local
  directory entry for picture 0 is absent, so this failed with
  `ValueError: picture 0 is absent` and was not used as evidence.
- The first unit-test run used placeholder hashes. Those failures only proved
  that expected values had not yet been seeded.
- Plain `python3 -B -m unittest` reported zero tests, so it is not the suite
  command for this repository. The documented command now uses explicit test
  discovery with `discover -s tests`.

Documented result:

- Added `tools/agi_graphics.py` as the first reusable local graphics decoding
  module. It parses picture and view resources from the local directory and
  volume files, writes simple PPM output, and exposes deterministic render
  buffers for tests.
- Added `tools/render_picture.py` and `tools/render_view.py` as command-line
  helpers for generating picture and view fixtures under `build/rendered/`.
- Added `tests/test_graphics_rendering.py` with six initial unit tests covering
  picture directory presence, picture 1 scan termination, deterministic picture
  rendering, all-view frame parsing, and deterministic rendering for two sample
  view cels.
- The local test suite passed with `python3 -B -m unittest discover -s tests`.
- ImageMagick inspection reported nonblank sample outputs:
  - `picture_001_visual.png`: 160 by 168, 11 colors.
  - `picture_001_control.png`: 160 by 168, 2 colors.
  - `view_000_00_00.png`: 7 by 33, 6 colors.
  - `view_011_00_00.png`: 20 by 5, 7 colors.
- The picture renderer remains provisional for seed fill and pattern plotting.
  The new picture hashes are regression checks for the current implementation
  hypothesis, not final original-engine compatibility claims.

## Graphics compatibility census expansion

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,260p' docs/src/graphics_object_pipeline.md`
- `sed -n '1,240p' docs/src/compatibility_testing.md`
- `sed -n '1,460p' tools/agi_graphics.py`
- `sed -n '1,220p' tests/test_graphics_rendering.py`
- Python one-off scan of all non-null `PICDIR` entries using
  `read_volume_payload`; 74 entries had valid volume headers, and entry 147
  decoded to invalid target `(0, 0x2ffff)`.
- Python one-off scan of all valid picture payloads through
  `render_picture`; all 74 valid pictures rendered without an exception.
- Python one-off command-byte census over all valid picture payloads.
- Python one-off view-row scan over all valid view payloads; all decoded rows
  stayed within their declared frame widths.
- `xxd -g 1 SQ2/PICDIR | tail -n 8`
- Python one-off print of final bytes for `LOGDIR`, `PICDIR`, `VIEWDIR`, and
  `SNDDIR`.
- `python3 -B -m unittest discover -s tests`
- `python3 -B tools/render_picture.py 45 --output build/rendered/picture_045_visual.ppm`
- `python3 -B tools/render_picture.py 45 --channel control --output build/rendered/picture_045_control.ppm`
- `magick build/rendered/picture_045_visual.ppm build/rendered/picture_045_visual.png`
- `magick build/rendered/picture_045_control.ppm build/rendered/picture_045_control.png`
- `identify -verbose build/rendered/picture_045_visual.ppm | sed -n '1,80p'`
- `identify -verbose build/rendered/picture_045_control.ppm | sed -n '1,80p'`
- Python one-off hash calculation for rendered picture 45 cells, visual
  nibbles, and control nibbles.

Rejected or non-evidence probes:

- The first all-picture scan treated every non-null directory entry as a valid
  resource. It failed on `PICDIR` entry 147 with `ValueError('bad VOL.0
  resource header at 0x2ffff')`. This failure is now recorded as evidence of a
  sentinel-like directory entry, but the failed scan's incomplete totals were
  not used.

Documented result:

- Added `iter_valid_resources(dir_name)` to `tools/agi_graphics.py`. It keeps
  the raw directory reader unchanged but skips entries whose volume headers do
  not validate.
- Expanded `tests/test_graphics_rendering.py` from 6 to 12 tests.
- The picture tests now assert:
  - 74 valid `PICDIR` payloads;
  - invalid/sentinel-like entry 147 as `(0, 0x2ffff)`;
  - every valid picture renders to a 160 by 168 buffer;
  - every valid picture payload ends with `0xff`;
  - the exact all-picture command-byte census;
  - deterministic hashes for picture 1 and picture 45.
- The view tests now assert:
  - 2,066 decoded frames;
  - 50,640 decoded rows;
  - no decoded row exceeds its frame width;
  - maximum observed cel dimensions of 88 by 129;
  - deterministic hashes for two sample cels.
- Picture 45 is the longest valid picture payload observed in this pass, at
  4,974 bytes. Its current provisional renderer full-cell hash is
  `7e8132ddf0658ada246440e409f0801a416d88f003495b7a9f55fbee23fb3974`.
- The all-picture command-byte census over valid payloads is:
  - `0xf0`: 4,746
  - `0xf1`: 309
  - `0xf2`: 1,018
  - `0xf3`: 425
  - `0xf6`: 7,736
  - `0xf7`: 9,282
  - `0xf8`: 1,447
  - `0xf9`: 22
  - `0xfa`: 701
  - `0xff`: 74
- No valid local SQ2 picture payload uses command `0xf4` or `0xf5` in this
  scan.
- ImageMagick inspection reported nonblank picture 45 samples:
  - `picture_045_visual.ppm`: 160 by 168, 11 colors.
  - `picture_045_control.ppm`: 160 by 168, 11 colors.

## PPM inspection helper for QEMU validation

Commands run from `/Users/peter/ai/agi/reverse`:

- `find build -maxdepth 3 -type f | sort | sed -n '1,160p'`
- `find . -maxdepth 3 -type f -name '*screen*' -o -name '*.ppm' -o -name '*.png' | sort | sed -n '1,160p'`
- `identify build/dos622/sq2_01.ppm build/dos622/sq2_02.ppm build/dos622/screen0.ppm build/rendered/picture_001_visual.ppm build/rendered/picture_045_visual.ppm`
- Python one-off read of the first 64 bytes of selected QEMU PPM captures.
- `python3 -B -m unittest discover -s tests`
- `python3 -B tools/inspect_ppm.py build/dos622/sq2_01.ppm`
- `python3 -B tools/inspect_ppm.py build/rendered/picture_045_visual.ppm`
- `python3 -B tools/inspect_ppm.py build/rendered/picture_045_control.ppm`

Documented result:

- Added `tools/ppm_tools.py` with a small binary PPM reader, RGB digest helper,
  unique-color collection, and first-pixel-background bounding-box helper.
- Added `tools/inspect_ppm.py` as a CLI wrapper around those helpers.
- Added a unit test proving local picture PPM output can be parsed by the same
  helper intended for QEMU screenshots.
- Existing QEMU screenshots under `build/dos622/` include both 720 by 400 DOS
  text-mode captures and 640 by 400 SQ2 game captures. For example,
  `build/dos622/sq2_01.ppm` parsed as 640 by 400, 4 colors, RGB SHA-256
  `80605890a86b4cfe5304c389a7fec9c7ece9c809812bec8923c60e464fcda12f`, with
  non-background bounds `(0, 16, 639, 331)`.
- Local generated picture renders remain in the logical 160 by 168 coordinate
  space. Picture 45 visual PPM parsed as 160 by 168, 11 colors, RGB SHA-256
  `92dc42b905eab360dcec460dbdba5f2382c7c833d461efa2c9c5fc3e86ba213b`; its
  control PPM parsed as 160 by 168, 11 colors, RGB SHA-256
  `354e29e62f1e27ef9f56a3a4db251ac04d5e86a2e095f3ff541d9232a08ef055`.
- The QEMU-to-local comparison layer still needs an explicit normalization
  transform because the emulator screenshot is a full VGA frame, not the raw
  160 by 168 logical picture buffer.

## Pattern plot renderer refinement

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x6524 -e 0x6724 build/cleanroom/AGI.decrypted.exe | sed -n '1,190p'`
- `ndisasm -b 16 -o 0x64f0 -e 0x66f0 build/cleanroom/AGI.decrypted.exe | sed -n '1,80p'`
- `xxd -g 1 -s 0x15f8 -l 0x80 SQ2/AGIDATA.OVL`
- `xxd -g 2 -s 0x1618 -l 0x40 SQ2/AGIDATA.OVL`
- `rg -n "pattern|0x652a|0x15f8|0x15f9|0x1619|0xfa|0xf9" docs/src tools`
- Python one-off print of `pattern_column_mask()` and `pattern_row_words()` from
  the local AGIDATA bytes.
- `python3 -B -m unittest discover -s tests`

Documented result:

- Replaced the local picture renderer's placeholder circular pattern plotting
  with the observed helper `0x652a` algorithm.
- Added `pattern_column_mask(column)` and `pattern_row_words(radius)` helpers
  that read the local `AGIDATA.OVL` pattern tables instead of hard-coding row
  shapes in the renderer.
- Added a unit test for the observed column masks and selected row-word tables.
- The observed column masks selected from `DS:0x15f9 + column * 4` are:
  `0x8000`, `0x2000`, `0x0800`, `0x0200`, `0x0080`, `0x0020`, `0x0008`,
  and `0x0002`.
- The pattern helper draws `radius + 1` columns and `2 * radius + 1` rows after
  clipping from the source coordinate.
- Mode bit `0x10` bypasses the row-word/column-mask test.
- Mode bit `0x20` enables the byte recurrence seeded from `[0x15f8] | 1`:
  shift right, XOR with `0xb8` when carry was set, and draw only when bit 0 is
  clear and bit 1 is set.
- Existing picture regression hashes for pictures 1 and 45 remained unchanged
  after this refinement, but they still require QEMU comparison before being
  treated as original-engine parity checks.

## Seed fill renderer refinement

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x533b -e 0x563b build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x52f9 -e 0x543b build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `rg -n "0x533b|seed_fill|fill|0xf8|0x534|0x53" docs/src tools`
- `ndisasm -b 16 -o 0x53f9 -e 0x553b build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x54a0 -e 0x55e2 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x5724 -e 0x5866 build/cleanroom/AGI.decrypted.exe | sed -n '1,120p'`
- `python3 -B -m unittest discover -s tests`
- Python one-off hash calculation for pictures 1 and 45 after the seed-fill
  model update.
- `python3 -B tools/render_picture.py 45 --output build/rendered/picture_045_visual.ppm`
- `python3 -B tools/render_picture.py 45 --channel control --output build/rendered/picture_045_control.ppm`
- `python3 -B tools/inspect_ppm.py build/rendered/picture_045_visual.ppm`
- `python3 -B tools/inspect_ppm.py build/rendered/picture_045_control.ppm`
- `magick build/rendered/picture_045_visual.ppm build/rendered/picture_045_visual.png`
- `magick build/rendered/picture_045_control.ppm build/rendered/picture_045_control.png`

Rejected or non-evidence probes:

- The first disassembly command in this pass used the previously noted seed
  label but landed on an unhelpful alignment window. The focused reruns around
  `0x53f9..0x55e5` are the evidence for this pass.

Documented result:

- Refined the local seed-fill model from "fill each active channel separately"
  to the observed interpreter contract:
  - if visual drawing is active, select low nibble target `0xf`;
  - otherwise, if control drawing is active, select high nibble target `0x40`;
  - exit immediately if the selected replacement is the default target value;
  - for accepted cells, call the normal pixel write path, so both active
    channels can be changed by the fill.
- The executable helper is a stack-backed horizontal span fill. The local
  renderer still uses an explicit queue over four-neighbor cells for traversal,
  but now uses the observed test-channel priority and normal pixel-write rule.
- Picture 1 hashes did not change. Picture 45's visual hash did not change, but
  its control and combined-cell hashes changed, matching the expectation that
  the refinement affects control side effects when both draw channels are
  active.
- Updated the picture 45 full-cell regression hash to
  `7e8132ddf0658ada246440e409f0801a416d88f003495b7a9f55fbee23fb3974`.
- Updated the generated picture 45 control PPM RGB hash to
  `354e29e62f1e27ef9f56a3a4db251ac04d5e86a2e095f3ff541d9232a08ef055`.
- Added two synthetic picture bytecode tests for seed fill:
  - `f2 02 f0 01 f8 00 00 ff` starts with both control and visual drawing
    active. It expands through the low-nibble default target and writes every
    cell to `0x21`, proving that visual is the test channel but both active
    channels can be written.
  - `f2 02 f8 00 00 ff` has only control drawing active. It expands through
    the high-nibble default target and writes every cell to `0x2f`.
- The local compatibility suite passed with 16 tests after these synthetic
  checks were added.

## Picture line helper refinement

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x66e1 -e 0x68c0 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x526f -e 0x5460 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x66e1 -e 0x68e1 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x526f -e 0x546f build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- Python one-off comparison of the observed accumulator stepping model with
  the previous generic line algorithm over small coordinate ranges.
- `python3 -B -m unittest discover -s tests`

Rejected or non-evidence probes:

- The first `0x66e1` disassembly command used the wrong file skip offset and
  landed slightly early. The rerun with `-e 0x68e1` is the evidence used for
  the line-helper notes.

Documented result:

- Replaced the local diagonal line routine with the observed helper `0x66e1`
  accumulator structure:
  - horizontal and vertical special cases use dedicated helpers;
  - the caller plots the starting point before entering the helper;
  - the major axis supplies the loop count;
  - the minor-axis accumulator starts at half the major delta;
  - Y accumulator/step is processed before X accumulator/step;
  - each generated point is written through the normal pixel helper.
- Existing SQ2 picture regression hashes did not change after this refinement.
- Added synthetic tests for an absolute `0xf6` line and a packed relative
  `0xf7` line. Both forms currently assert the plotted point set
  `(0,0)`, `(1,0)`, `(2,1)`, `(3,1)`.
- The local compatibility suite passed with 18 tests after these line checks
  were added.

## Object-frame composition helper

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "object drawing|IBM_OBJS|0x9db|view frame|transparent|priority|\\+0x24|0x587d|rewrite" docs/src/graphics_object_pipeline.md docs/src/clean_room_executable_notes.md docs/src/symbolic_labels.md tools`
- `ndisasm -b 16 -o 0x9db0 SQ2/IBM_OBJS.OVL | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x587d -e 0x5a7d build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `sed -n '260,860p' docs/src/graphics_object_pipeline.md`
- `sed -n '1,260p' tools/inspect_view.py`
- `python3 -B -m unittest discover -s tests`

Documented result:

- Added `draw_frame_on_buffer()` and `compose_frame_on_picture()` to
  `tools/agi_graphics.py`.
- The helper models the central object overlay draw rule from
  `IBM_OBJS.OVL:0x9db6`: object top is `baseline_y - frame.height + 1`,
  transparent-color pixels do not write, and nontransparent pixels write
  `(priority << 4) | color` only when the destination high-nibble
  priority/control comparison permits it.
- Added tests for baseline placement, transparent pixels, direct rejection by a
  higher existing priority, and rejection after scanning downward from a
  low-control cell.

## Generated logic fixture for QEMU picture validation

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,260p' docs/src/logic_resources.md`
- `sed -n '1,220p' docs/src/logic_bytecode.md`
- `rg -n "load_picture|prepare_picture|show_picture|draw|return|end|0x18|0x19|0x1a|logic header|message|messages|LOGIC" docs/src tools/disassemble_logic.py`
- `python3 -B tools/disassemble_logic.py 0 | sed -n '1,220p'`
- `xxd -g 1 -l 160 SQ2/VOL.1`
- Python one-off print of action-table entries for `assignn`,
  `load_picture_var`, `prepare_picture_var`, `show_picture_like`, and related
  display/input actions.
- Python one-off scan of valid local logic resources to inspect zero-message
  payload trailers.
- Python one-off print of `VOL.*` file sizes and first `LOGDIR` entries.
- `xxd -g 1 -l 32 SQ2/VOL.3`
- `python3 -B -m unittest discover -s tests`
- `python3 -B tools/qemu_fixture.py picture 45 --output build/qemu-fixtures/picture_045`
- `xxd -g 1 -l 32 build/qemu-fixtures/picture_045/LOGDIR`
- `xxd -g 1 -l 64 build/qemu-fixtures/picture_045/VOL.3`
- `find build/qemu-fixtures/picture_045 -maxdepth 1 -type f | wc -l`
- Python one-off check of generated `VOL.3` header/payload bytes and patched
  `LOGDIR[0]`.
- `mdir -i build/dos622/dos622.img@@32256 ::`
- `mmd -i build/dos622/dos622.img@@32256 ::/SQ2P45`
- `mcopy -i build/dos622/dos622.img@@32256 build/qemu-fixtures/picture_045/* ::/SQ2P45`
- `qemu-system-i386 -m 16 -boot c -drive file=build/dos622/dos622.img,format=raw,if=ide,index=0,media=disk -display vnc=127.0.0.1:5 -monitor stdio`
- QEMU monitor `sendkey` commands for `cd \SQ2P45` and `SIERRA`.
- QEMU monitor command
  `screendump build/qemu-fixtures/picture_045/qemu_picture_045.ppm`.
- QEMU monitor command `quit`.
- `python3 -B tools/inspect_ppm.py build/qemu-fixtures/picture_045/qemu_picture_045.ppm`
- `identify build/qemu-fixtures/picture_045/qemu_picture_045.ppm`
- Python one-off nearest-palette/downsample comparison between the QEMU capture
  and `render_picture(45).visual_nibbles`.
- `python3 -B tools/compare_picture_capture.py 45 build/qemu-fixtures/picture_045/qemu_picture_045.ppm`
- `magick build/qemu-fixtures/picture_045/qemu_picture_045.ppm build/qemu-fixtures/picture_045/qemu_picture_045.png`

Rejected or non-evidence probes:

- `python3 -B tools/disassemble_logic.py --logic 0` failed because the local
  disassembler takes logic numbers as positional arguments.
- One `rg` command used a search pattern containing markdown backticks and
  failed shell quoting; it was not used as evidence.
- The first synthetic scaled-PPM unit test wrote only 200 rows while declaring
  a 400-row image. The PPM parser rejected it, the test was corrected, and the
  malformed generated file was not used as evidence.

Documented result:

- Added `tools/qemu_fixture.py`. For `picture N`, it copies the local `SQ2/`
  files into `build/qemu-fixtures/picture_NNN`, replaces `VOL.3` with a custom
  logic resource, and patches `LOGDIR[0]` to point to `VOL.3` offset zero.
- The generated picture-45 logic payload is:
  - resource header in `VOL.3`: `12 34 03 10 00`;
  - logic code length: `0b 00`;
  - bytecode: `03 fa 2d 18 fa 19 fa 1a fe fd ff`;
  - message trailer: `00 02 00`.
- The bytecode means:
  - `assignn(v250, 45)`;
  - `load_picture_var(v250)`;
  - `prepare_picture_var(v250)`;
  - `show_picture_like()`;
  - `jump -3`, looping on the jump after the picture has been shown.
- Copied the generated fixture to `C:\SQ2P45` inside
  `build/dos622/dos622.img` and launched it with the original interpreter in
  QEMU.
- Captured `build/qemu-fixtures/picture_045/qemu_picture_045.ppm` from QEMU.
  The capture is 640 by 400, has 11 nearest-palette colors, and has RGB
  SHA-256 `615a1a8ae22d4e04774f725adb395bc3d05372b10d41c81a61a99eb098d1d34c`.
- A top-left aligned `4x2` downsample from the 640 by 400 QEMU capture to the
  160 by 168 logical picture space matched `render_picture(45).visual_nibbles`
  with 0 mismatches out of 26,880 pixels.
- Added `tools/compare_picture_capture.py` and a synthetic scaled-capture unit
  test for the comparison path.
- The local compatibility suite passed with 25 tests after adding the fixture
  and comparison helpers.

## Generated logic fixture for QEMU picture plus view validation

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/qemu_fixture.py picture-view 1 11 0 0 20 80 15 --output build/qemu-fixtures/picture_001_view_011_00_00`
- `python3 -B -m unittest discover -s tests`
- `mmd -i build/dos622/dos622.img@@32256 ::/SQ2V11`
- `mcopy -i build/dos622/dos622.img@@32256 build/qemu-fixtures/picture_001_view_011_00_00/* ::/SQ2V11`
- `qemu-system-i386 -m 16 -boot c -drive file=build/dos622/dos622.img,format=raw,if=ide,index=0,media=disk -display vnc=127.0.0.1:5 -monitor stdio`
- QEMU monitor `sendkey` commands for `cd \SQ2V11` and `SIERRA`.
- QEMU monitor command
  `screendump build/qemu-fixtures/picture_001_view_011_00_00/qemu_picture_001_view_011_00_00.ppm`.
- QEMU monitor command `quit`.
- `python3 -B tools/inspect_ppm.py build/qemu-fixtures/picture_001_view_011_00_00/qemu_picture_001_view_011_00_00.ppm`
- `magick build/qemu-fixtures/picture_001_view_011_00_00/qemu_picture_001_view_011_00_00.ppm build/qemu-fixtures/picture_001_view_011_00_00/qemu_picture_001_view_011_00_00.png`
- `python3 -B tools/compare_picture_capture.py 1 build/qemu-fixtures/picture_001_view_011_00_00/qemu_picture_001_view_011_00_00.ppm --view 11 0 0 --view-x 20 --view-baseline-y 80 --view-priority 15`

Documented result:

- Extended `tools/qemu_fixture.py` with `picture-view`, which draws a selected
  picture, loads a selected view, draws one selected cel at a controlled
  position, and then loops.
- The generated picture-1/view-11/group-0/frame-0 logic payload is:
  - resource header in `VOL.3`: `12 34 03 1a 00`;
  - logic code length: `15 00`;
  - bytecode:
    `03 fa 01 18 fa 19 fa 1a 1e 0b 7a 0b 00 00 14 50 0f 0f fe fd ff`;
  - message trailer: `00 02 00`.
- The bytecode means:
  - `assignn(v250, 1)`;
  - `load_picture_var(v250)`;
  - `prepare_picture_var(v250)`;
  - `show_picture_like()`;
  - `load_view(11)`;
  - `setup_transient_object(view=11, group=0, frame=0, x=20, baseline_y=80, priority=15, control=15)`;
  - `jump -3`, looping on the jump after the picture and cel have been shown.
- Copied the generated fixture to `C:\SQ2V11` inside
  `build/dos622/dos622.img` and launched it with the original interpreter in
  QEMU.
- Captured
  `build/qemu-fixtures/picture_001_view_011_00_00/qemu_picture_001_view_011_00_00.ppm`
  from QEMU. The capture is 640 by 400, has 15 unique RGB colors, has a
  non-background bounding box of `(0, 0, 639, 335)`, and has RGB SHA-256
  `f63b82fb30ab0c2796f695e2678937f1c0a90e9cb3bbb85338bfccea5a6ac816`.
- Using the same top-left aligned `4x2` downsample as the picture-only fixture,
  the QEMU capture matched `compose_frame_on_picture(render_picture(1),
  render_view_frame(11, 0, 0), left=20, baseline_y=80, priority=15)` with
  0 mismatches out of 26,880 pixels.
- The local compatibility suite passed with 26 tests before running the QEMU
  fixture.

## Bit-0x80 view-frame orientation rewrite

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/inspect_view.py 0 1 2 11 --groups 8 --frames 8`
- `ndisasm -b 16 -o 0x587d -e 0x5a7d build/cleanroom/AGI.decrypted.exe`
- Python one-off scan of valid `VIEWDIR` resources for frames with control bit
  `0x80` whose cached bits `(control & 0x70) >> 4` differ from the selected
  group number.
- Python one-off print of view 0/group 0/frame 0 row bytes before and after
  the local rewrite model.
- `python3 -B -m unittest discover -s tests`
- `python3 -B tools/qemu_fixture.py picture-view 1 0 1 0 20 80 15 --output build/qemu-fixtures/picture_001_view_000_01_00`
- `mmd -i build/dos622/dos622.img@@32256 ::/SQ2V01`
- `mcopy -i build/dos622/dos622.img@@32256 build/qemu-fixtures/picture_001_view_000_01_00/* ::/SQ2V01`
- `qemu-system-i386 -m 16 -boot c -drive file=build/dos622/dos622.img,format=raw,if=ide,index=0,media=disk -display vnc=127.0.0.1:5 -monitor stdio`
- QEMU monitor `sendkey` commands for `cd \SQ2V01` and `SIERRA`.
- QEMU monitor command
  `screendump build/qemu-fixtures/picture_001_view_000_01_00/qemu_picture_001_view_000_01_00.ppm`.
- QEMU monitor command `quit`.
- `python3 -B tools/inspect_ppm.py build/qemu-fixtures/picture_001_view_000_01_00/qemu_picture_001_view_000_01_00.ppm`
- `magick build/qemu-fixtures/picture_001_view_000_01_00/qemu_picture_001_view_000_01_00.ppm build/qemu-fixtures/picture_001_view_000_01_00/qemu_picture_001_view_000_01_00.png`
- `python3 -B tools/compare_picture_capture.py 1 build/qemu-fixtures/picture_001_view_000_01_00/qemu_picture_001_view_000_01_00.ppm --view 0 1 0 --view-x 20 --view-baseline-y 80 --view-priority 15`

Rejected or non-evidence probes:

- The first local row-rewrite model treated the mirrored row's emitted leading
  transparent width as `width - tail_width`, where `tail_width` started at the
  first nontransparent run. The disassembly keeps explicit leading transparent
  width in the accumulator before the first nontransparent run, so the correct
  emitted width is `width - total_explicit_row_width`. The failing unit test
  was not used as evidence.

Documented result:

- Added `_mirror_view_row_runs()` and `_orient_view_rows()` to
  `tools/agi_graphics.py`.
- The rewrite model matches helper `0x587d`:
  - only frames with control bit `0x80` are candidates;
  - bits `0x70` of the frame control byte cache the current orientation/group;
  - when cached bits differ from the selected group, those bits are replaced;
  - each row is rebuilt by emitting the original implicit trailing transparent
    width, then copying the counted run bytes in reverse order, then writing a
    zero row terminator.
- A local scan found 229 valid SQ2 frames where bit `0x80` is set and the
  selected group differs from the cached bits. View 0/group 1/frame 0 is the
  first such sample.
- Added a unit test proving that `render_view_frame(0, 1, 0)` is the
  horizontal mirror of `render_view_frame(0, 0, 0)` and reports rewritten
  control byte `0x91`.
- Captured
  `build/qemu-fixtures/picture_001_view_000_01_00/qemu_picture_001_view_000_01_00.ppm`
  from QEMU. The capture is 640 by 400, has 14 unique RGB colors, has a
  non-background bounding box of `(0, 0, 639, 335)`, and has RGB SHA-256
  `1fb4fbfaa4d7b93b15fa007930e87d7c1982cb78626441a28d56ae46fdd8bd96`.
- Using the same top-left aligned `4x2` downsample as the previous fixtures,
  the QEMU capture matched `compose_frame_on_picture(render_picture(1),
  render_view_frame(0, 1, 0), left=20, baseline_y=80, priority=15)` with
  0 mismatches out of 26,880 pixels.
- The local compatibility suite passed with 27 tests after the rewrite model
  and orientation test were added.

## Synthetic picture fuzzing framework

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,260p' tools/qemu_fixture.py`
- `sed -n '1,220p' tools/compare_picture_capture.py`
- `sed -n '1,620p' tools/agi_graphics.py`
- `find tests -maxdepth 2 -type f -print`
- `sed -n '1,220p' tests/test_qemu_fixture.py`
- `python3 -B -m unittest discover -s tests`
- `python3 -B tools/picture_fuzz.py generate --count 64 --seed 4097 --output build/picture-fuzz/corpus --clean`
- `python3 -B tools/picture_fuzz.py run-qemu base_003_visual_point --dos-dir FZVPOINT --boot-wait 5 --draw-wait 8`
- `python3 -B tools/picture_fuzz.py generate --count 1024 --seed 4097 --output build/picture-fuzz/corpus --clean`
- `python3 -B tools/picture_fuzz.py run-qemu base_002_unknown_commands --dos-dir FZUNK --boot-wait 5 --draw-wait 8`
- `python3 -B tools/picture_fuzz.py run-qemu base_004_clamped_absolute --dos-dir FZCLAMP --boot-wait 5 --draw-wait 8`
- `python3 -B tools/picture_fuzz.py run-qemu base_009_visual_control_fill --dos-dir FZFILL --boot-wait 5 --draw-wait 8`
- `python3 -B tools/picture_fuzz.py run-qemu base_011_pattern_random --dos-dir FZPATT --boot-wait 5 --draw-wait 8`
- `python3 -B tools/picture_fuzz.py run-qemu base_013_truncated_pair --dos-dir FZTRUNC --boot-wait 5 --draw-wait 8`
- `python3 -B tools/picture_fuzz.py compare-capture base_004_clamped_absolute build/picture-fuzz/fixtures/base_004_clamped_absolute/qemu_capture.ppm`
- `ndisasm -b 16 -o 0x66e1 -e 0x68e1 build/cleanroom/AGI.decrypted.exe`
- Python one-off comparing captured and locally rendered changed pixels for
  `base_004_clamped_absolute`.
- `xxd -g 1 -l 96 build/picture-fuzz/fixtures/base_004_clamped_absolute/VOL.3`
- `xxd -g 1 -l 12 build/picture-fuzz/fixtures/base_004_clamped_absolute/PICDIR`
- `cat build/picture-fuzz/corpus/base_004_clamped_absolute/case.json`
- Python one-off simulating line helper `0x66e1` with and without 8-bit
  accumulator wrap.
- `python3 -B tools/picture_fuzz.py run-qemu base_005_exact_edge_absolute --dos-dir FZEDGE --boot-wait 5 --draw-wait 8`
- `python3 -B tools/picture_fuzz.py compare-capture base_004_clamped_absolute build/picture-fuzz/fixtures/base_004_clamped_absolute/qemu_capture.ppm`
- `python3 -B tools/picture_fuzz.py run-qemu base_010_visual_control_fill --dos-dir FZFIL3 --boot-wait 5 --draw-wait 8`
- `python3 -B tools/picture_fuzz.py run-qemu base_012_pattern_random --dos-dir FZPAT3 --boot-wait 5 --draw-wait 8`
- `python3 -B tools/picture_fuzz.py run-qemu base_014_truncated_pair --dos-dir FZTRN3 --boot-wait 5 --draw-wait 8`

Rejected or non-evidence probes:

- The first `run-qemu base_003_visual_point` attempt hid QEMU output and
  surfaced only a broken pipe. The harness was corrected to preserve QEMU
  output on early exit.
- Picture fuzz cases marked `safe_for_qemu: false` are excluded from
  original-engine compatibility evidence. They can make the interpreter read
  past the synthetic resource and begin interpreting unrelated memory, which is
  security/exploit behavior rather than a stable semantic contract for AGI
  resource decoding.
- Python-launched QEMU initially failed under the restricted sandbox with
  `Failed to bind socket: Operation not permitted`; the same command succeeded
  after the user allowed full access.
- Running three QEMU fuzz cases in parallel was rejected as a bad probe. QEMU
  needs a single VNC display socket, and concurrent mtools/QEMU fixture copying
  can collide on the DOS image.
- A compare for `base_005_exact_edge_absolute` was started in parallel with a
  corpus regeneration command. The compare raced the regenerated manifest and
  failed with `FileNotFoundError`; the case was present after regeneration and
  the QEMU comparison was rerun sequentially.
- While probing mtools behavior, directory `FZNEW99` was created in the DOS
  image. It was not used as evidence.

Documented result:

- Added generic `patch_dir_entry()` and
  `build_synthetic_picture_fixture()` to `tools/qemu_fixture.py`.
  A synthetic fixture copies local `SQ2/`, writes `VOL.3` with both custom
  `LOGIC.0` and a synthetic picture payload, patches `LOGDIR[0]` to the logic
  record, and patches `PICDIR[picture_no]` to the picture record.
- Added `tools/picture_fuzz.py`. It can:
  - generate deterministic curated and random picture-resource corpora;
  - record payload hashes and Python render hashes in `case.json` and
    `manifest.json`;
  - build original-engine fixture directories for a selected fuzz case;
  - copy a fixture into the DOS image, run it in QEMU, capture a `screendump`,
    and compare the original-engine output against the Python renderer;
  - compare an existing QEMU capture and report mismatch count, bounding box,
    and sample mismatched pixels.
- Added `tests/test_picture_fuzz.py` and expanded `tests/test_qemu_fixture.py`.
  The local suite passed with 34 tests after the fuzz framework and line
  regression were added.
- The current corpus command
  `python3 -B tools/picture_fuzz.py generate --count 1024 --seed 4097 --output build/picture-fuzz/corpus --clean`
  generates 1,040 cases: 16 curated base cases and 1,024 deterministic random
  cases. It currently marks 1,038 cases safe for automated QEMU runs.
- Updated `tools/picture_fuzz.py run-qemu` to reject cases marked
  `safe_for_qemu: false` before building or launching a fixture. This preserves
  the project boundary that malformed overread/exploit behavior is not part of
  the compatibility spec being built.
- The first representative QEMU fuzz cases matched:
  - `base_002_unknown_commands`: 0 mismatches;
  - `base_003_visual_point`: 0 mismatches;
  - `base_009_visual_control_fill` before renumbering: 0 mismatches;
  - `base_011_pattern_random` before renumbering: 0 mismatches;
  - `base_013_truncated_pair` before renumbering: 0 mismatches.
- `base_004_clamped_absolute` initially mismatched with 312 pixels. The
  mismatch samples showed a screen-scale diagonal line displaced relative to
  the Python renderer. The exact payload in the fixture was
  `f0 02 f6 ef ef 00 00 ff`, and `PICDIR[0]` correctly pointed to the
  synthetic picture in `VOL.3`, so the mismatch was treated as behavioral
  evidence rather than a fixture error.
- A new curated case, `base_005_exact_edge_absolute`, using payload
  `f0 02 f6 9f a7 00 00 ff`, reproduced the same mismatch. That proved the gap
  was not out-of-range coordinate clamping but the diagonal line helper.
- Simulating `code.picture.draw_line` (`0x66e1`) with 8-bit accumulator wrap
  reproduced the original-engine edge shape. In particular, the long line from
  `(159,167)` to `(0,0)` includes `(25,0)` and `(25,1)` and does not include
  `(0,0)`.
- Updated `PictureRenderer.draw_line()` to wrap the X and Y accumulators to
  8 bits after addition and subtraction. Added
  `test_long_diagonal_uses_byte_width_line_accumulators`.
- After the fix, `base_004_clamped_absolute` and
  `base_005_exact_edge_absolute` both matched QEMU with 0 mismatches out of
  26,880 pixels.
- Reran representative cases after the fix:
  - `base_010_visual_control_fill`: 0 mismatches;
  - `base_012_pattern_random`: 0 mismatches;
  - `base_014_truncated_pair`: 0 mismatches.

## Picture fuzz batch runner and pattern edge correction

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest tests.test_picture_fuzz`
- `python3 -B tools/picture_fuzz.py generate --count 64 --seed 4097 --output build/picture-fuzz/corpus --clean`
- `python3 -B tools/picture_fuzz.py batch-qemu --case base_000_stop_only --case base_001_ignored_data --case base_002_unknown_commands --case base_003_visual_point --case base_004_clamped_absolute --case base_005_exact_edge_absolute --case base_006_relative_mixed --case base_007_corner_y_first --case base_008_corner_x_first --case base_009_control_fill --case base_010_visual_control_fill --case base_011_pattern_mask --case base_012_pattern_random --case base_014_truncated_pair --dos-prefix FB --output build/picture-fuzz/batches/base_curated_001.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/picture_fuzz.py batch-qemu --case rand_00000 --case rand_00001 --case rand_00002 --case rand_00003 --case rand_00004 --case rand_00005 --case rand_00006 --case rand_00007 --case rand_00008 --case rand_00009 --case rand_00010 --case rand_00011 --case rand_00012 --case rand_00013 --case rand_00014 --case rand_00015 --dos-prefix FR --output build/picture-fuzz/batches/random_00000_00015.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/picture_fuzz.py batch-qemu --case base_016_visual_fill_box --case base_017_visual_fill_outside_box --case base_018_pattern_edge_circle --case base_019_pattern_edge_rectangle --case base_020_pattern_random_sequence --dos-prefix FT --output build/picture-fuzz/batches/targeted_fill_pattern_001.json --boot-wait 5 --draw-wait 8`
- `mdir -i build/dos622/dos622.img@@32256 ::`
- `python3 -B tools/picture_fuzz.py batch-qemu --case base_016_visual_fill_box --case base_017_visual_fill_outside_box --case base_018_pattern_edge_circle --case base_019_pattern_edge_rectangle --case base_020_pattern_random_sequence --dos-prefix FV --output build/picture-fuzz/batches/targeted_fill_pattern_003.json --boot-wait 5 --draw-wait 8`

Documented result:

- Added `batch-qemu` to `tools/picture_fuzz.py`. It selects only safe cases,
  runs them serially through QEMU, prints per-case progress, and writes JSON
  reports containing status, capture paths, elapsed seconds, mismatch boxes,
  and mismatch samples.
- The 14-case curated safe batch matched with 0 mismatches and 0 errors.
- The first 16 safe random cases matched with 0 mismatches and 0 errors.
- Added curated cases `base_016` through `base_020` for bounded fill barriers,
  lower-right pattern edge placement, rectangular pattern masks, and multiple
  pseudo-random pattern seeds.
- The first targeted fill/pattern batch showed that bounded fill and
  pseudo-random pattern sequences matched, but lower-right circle and rectangle
  pattern plots mismatched at X `0`.
- The mismatch proved that pattern plotting can compute X `160` and write
  through the linear picture buffer address. This makes the byte appear at X
  `0` on the next scanline instead of being clipped.
- Updated `PictureRenderer.pattern_plot()` to write through a linear buffer
  helper. After regenerating the corpus, `base_018_pattern_edge_circle` and
  `base_019_pattern_edge_rectangle` both matched QEMU with 0 mismatches.
- A rerun initially failed with DOS-image `Disk full` errors, not renderer
  mismatches. The cause was old generated `.ppm` captures being copied back into
  the DOS image with fixture files. `copy_fixture_to_dos()` now excludes `.ppm`
  files, and generated fuzz directories were removed from the DOS image.

## View/object QEMU batch validation

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest discover -s tests`
- `python3 -B tools/view_batch.py --dos-prefix VB --output build/view-batch/batches/view_base_001.json --boot-wait 5 --draw-wait 8`
- Cached Python comparison of `view_011_top_clip` against alternate local
  `left` and `baseline_y` values.
- `python3 -B -m unittest tests.test_graphics_rendering tests.test_view_batch`
- `python3 -B tools/view_batch.py --dos-prefix VC --output build/view-batch/batches/view_base_002.json --boot-wait 5 --draw-wait 8`

Documented result:

- Added `tools/view_batch.py`, a serial QEMU harness for picture-plus-view
  fixtures. It builds fixtures with `build_picture_view_fixture()`, runs each
  one in QEMU, compares the capture with local picture/view composition, and
  writes a JSON report.
- Extended `tools/compare_picture_capture.py` to include mismatch bounding
  boxes and sample pixels in addition to mismatch counts.
- Added `tests/test_view_batch.py` for case loading, stable DOS directory names,
  and report summaries.
- The first six-case view batch matched normal view drawing, cached group-0
  bit-`0x80` drawing, mirrored group-1 bit-`0x80` drawing, left-edge clipping,
  and a low-priority object case. The top-edge case mismatched with 75 pixels
  in rows 0 through 4.
- Comparing the top-edge capture against local placements found an exact match
  at left `18`, baseline `4`, even though the fixture requested left `20`,
  baseline `2`. Since view 11/group 0/frame 0 has height 5, the requested top
  was `-2`; the observed overlay behavior is to add that negative top to left,
  raise the baseline by the absolute amount, and draw from top row 0.
- Updated `draw_frame_on_buffer()` with that top-edge adjustment and added a
  regression test. The second view batch matched all six cases with 0
  mismatches and 0 errors.

## QEMU host-directory fixture access

Commands run from `/Users/peter/ai/agi/reverse`:

- `qemu-system-i386 --version`
- Python QEMU launch probe with:
  `-drive file=fat:rw:build/qemu-share,format=raw,if=ide,index=1,media=disk`
- `python3 -B tools/qemu_fixture.py picture 1 --output build/qemu-share/PIC001`
- QEMU monitor-driven run from DOS drive `D:`:
  `D:`, `cd \PIC001`, `SIERRA`, followed by `screendump build/qemu-share/from_share_pic001.ppm`
- `python3 -B tools/compare_picture_capture.py 1 build/qemu-share/from_share_pic001.ppm`
- `qemu-img create -f qcow2 -F raw -b /Users/peter/ai/agi/reverse/build/dos622/dos622.img build/dos622/dos622-test.qcow2`
- QEMU snapshot probes with writable vvfat hard disk, read-only vvfat CD-ROM,
  and `fat:floppy:` host shares.

Documented result:

- QEMU 11.0.2 accepts `file=fat:rw:build/qemu-share` as a secondary IDE disk.
  DOS 6.22 sees it as drive `D:` with volume label `QEMU VVFAT`.
- A generated picture-1 fixture placed at `build/qemu-share/PIC001` ran
  directly from `D:\PIC001` without copying it into the DOS hard disk image.
  The capture `build/qemu-share/from_share_pic001.ppm` matched the local
  picture-1 renderer with 0 mismatches.
- The generated fixture does not return to DOS after drawing; sending `DIR`
  after the draw left the game screen visible. Running multiple cases in one
  guest session therefore needs a reset/restore mechanism.
- QEMU `savevm` fails when a writable vvfat drive is attached:
  `The vvfat (rw) format ... does not support live migration`.
- A qcow2 overlay for the DOS boot disk can hold VM snapshots. A read-only
  vvfat CD-ROM permits `savevm`, but the current DOS image lacks an IDE/ATAPI
  CD-ROM driver, so `DIR D:\` reports `Invalid drive specification`.
- `fat:floppy:` read-only host shares can be snapshotted and are visible as
  `A:` only when the host directory fits FAT12 constraints. This is too small
  and awkward for full AGI fixture directories; a nested fixture directory
  appeared empty, and a root-level fixture exposed only a subset of files.
- Practical next options:
  - use `fat:rw:` as `D:` now to avoid mtools copies and DOS-image pollution,
    still launching/resetting QEMU per case;
  - install/configure a DOS CD-ROM driver and use read-only vvfat CD-ROM plus
    `savevm`/`loadvm` for no-boot batches;
  - or generate a qcow2/FAT test disk containing prebuilt fixtures and use
    QEMU snapshots at the DOS prompt.

## QEMU snapshot fixture disk

Commands run from `/Users/peter/ai/agi/reverse`:

- Built a picture-only fixture and a picture-plus-view fixture:
  `python3 -B tools/qemu_fixture.py picture 1 --output build/qcow-fixture-test/fixtures/PIC001`
  and
  `python3 -B tools/qemu_fixture.py picture-view 1 11 0 0 20 80 15 --output build/qcow-fixture-test/fixtures/VIEW11`.
- Probed a partitionless FAT image, an MBR-partitioned FAT image starting at
  sector 63, and a DOS-geometry-like secondary hard disk. All could either be
  manipulated by mtools or attached to QEMU, but DOS did not expose them as a
  usable `D:` drive.
- Copied `build/dos622/dos622.img` to a disposable raw image, copied fixture
  directories into its DOS partition with mtools at offset `32256`, converted
  it to qcow2, booted it as `C:`, ran `savevm ready`, then used `loadvm ready`
  between `PIC001` and `VIEW11`.
- Compared the captures with:
  `python3 -B tools/compare_picture_capture.py 1 build/qcow-fixture-test/snapshot_pic001.ppm`
  and
  `python3 -B tools/compare_picture_capture.py 1 build/qcow-fixture-test/snapshot_view11.ppm --view 11 0 0 --view-x 20 --view-baseline-y 80 --view-priority 15`.

Documented result:

- The secondary qcow2/FAT fixture disk approach is not yet usable with DOS 6.22
  in this setup.
- A disposable qcow2 clone of the DOS boot disk with fixture directories
  preloaded onto `C:` supports QEMU internal snapshots.
- Both snapshot-run captures matched with 0 mismatches, proving that one QEMU
  boot plus `savevm`/`loadvm` can replace repeated boots for batches whose
  fixture set is known in advance.
- Added `tools/qemu_snapshot.py` and `tools/view_batch.py --snapshot` to make
  this reusable for the view/object validation cases.
- Added `tools/picture_fuzz.py batch-qemu --snapshot` so known-ahead fuzz
  batches can use the same one-boot fixture disk rather than rebooting QEMU for
  each case.
- Verified the reusable path with `tools/view_batch.py --snapshot`: all six
  built-in view/object cases matched from one QEMU boot.
- Verified `tools/picture_fuzz.py batch-qemu --snapshot` with
  `base_016_visual_fill_box` and `base_019_pattern_edge_rectangle`: both cases
  matched with 0 mismatches from one QEMU boot.

## 2026-07-02: object overlay priority probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest discover -s tests`
- `python3 -B tools/object_overlay_probe.py --dos-prefix OP --output build/object-overlay-probes/batches/base_priority.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_overlay_probe.py --dos-prefix OQ --output build/object-overlay-probes/batches/priority_scan_down.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_overlay_probe.py --dos-prefix OR --output build/object-overlay-probes/batches/priority_nibbles.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_overlay_probe.py --dos-prefix OG --output build/object-overlay-probes/batches/expanded_all5_final.json --boot-wait 5 --draw-wait 8`

Documented result:

- Added `build_synthetic_picture_view_fixture()` to `tools/qemu_fixture.py`.
  This patches both `LOGDIR[0]` and a chosen `PICDIR` entry so the original
  engine can draw a generated picture resource and then overlay a chosen view
  cel through action `0x7a` (`setup_transient_object`).
- Added `tools/object_overlay_probe.py`, a snapshot-backed QEMU harness for
  targeted object overlay cases with controlled synthetic picture backgrounds.
- The eight built-in priority probes matched QEMU with 0 mismatches. The cases
  confirm:
  - default cleared control priority `4` hides object priority `3` and allows
    object priority `4`;
  - full-screen synthetic control priority `6` hides object priority `5` and
    allows object priority `6`;
  - visible overlay gating uses the low nibble of object byte `+0x24`, not the
    high nibble staged by operand 7 of action `0x7a`;
  - when the destination cell contains low control `2`, the overlay routine
    scans downward to a control-`6` row and applies the same comparison there.
- The expanded 19-case object overlay batch matched QEMU with 0 mismatches.
  It adds evidence for:
  - right-edge transient placement: requested left `154`, baseline `80` for
    view 11/group 0/frame 0 matched a local draw at left `140`, baseline `67`;
  - bottom-edge drawing for view 11 at baseline `167`;
  - transparent-color variants in views 21, 29, and 10;
  - derived priority when `0x7a` stages low priority zero, including the
    effect of action `0xae` rebuilding the priority table at row `100`;
  - persistent object-table setup and activation for a static object;
  - persistent fixed priority bytes with nonzero high nibbles hiding in the
    controlled priority probes, so those byte values should not yet be treated
    as normal visible priorities.

## 2026-07-02: targeted object movement QEMU probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest discover -s tests`
- `python3 -B tools/object_movement_probe.py --dos-prefix MV --output build/object-movement-probes/batches/base_movement_once.json --boot-wait 5 --draw-wait 8`
- Local best-position scan over the failed one-shot captures.
- `python3 -B tools/object_movement_probe.py --dos-prefix MV --output build/object-movement-probes/batches/base_movement_reissued.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_movement_probe.py --dos-prefix MV --output build/object-movement-probes/batches/base_movement_edges.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_movement_probe.py --dos-prefix MV --output build/object-movement-probes/batches/base_movement_control.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_movement_probe.py --dos-prefix MV --output build/object-movement-probes/batches/base_movement_control_final.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_movement_probe.py --dos-prefix MX --output build/object-movement-probes/batches/expanded_movement_edges.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_movement_probe.py --dos-prefix MX --output build/object-movement-probes/batches/expanded_movement_edges_final.json --boot-wait 5 --draw-wait 8`
- `ndisasm -b 16 -o 0x4719 -e 0x4919 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- Focused search for writes to object byte `+0x02`.
- `python3 -B tools/object_movement_probe.py --dos-prefix MC --output build/object-movement-probes/batches/movement_collision.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_movement_probe.py --dos-prefix MA --output build/object-movement-probes/batches/autonomous_modes_001.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_movement_probe.py --dos-prefix MB --output build/object-movement-probes/batches/autonomous_modes_002.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_movement_probe.py --dos-prefix MD --output build/object-movement-probes/batches/autonomous_modes_003.json --boot-wait 5 --draw-wait 8`
- Local Python scan for near call sites to `0x0b36`, `0x3f5a`, `0x1672`, and
  `0x16b9`.
- `ndisasm -b 16 -o 0x0563 -e 0x0763 build/cleanroom/AGI.decrypted.exe | sed -n '1,230p'`

Documented result:

- Added reusable generated-logic helpers to `tools/qemu_fixture.py`:
  `logic_resource`, `if_then`, `not_flag_set_condition`, `set_flag_action`,
  `run_once_logic`, and persistent-object fixture support for guarded
  per-cycle action blocks.
- Added `tools/object_movement_probe.py`, a snapshot-backed QEMU harness for
  persistent object-table movement tests. It builds generated logic resources
  that load a synthetic picture, initialize a persistent object once, then run
  selected per-cycle actions while a completion flag is clear.
- A one-shot `0x51` (`move_object_to`) fixture initialized the object and
  called the action once. QEMU showed that the object moved in the initial
  direction but did not stop at the requested target: the horizontal case
  matched exactly at left `140`, and the vertical case matched exactly at
  baseline `167`. This establishes that a single action call does not
  recompute target arrival on later ticks.
- The corrected fixture reissues `0x51` every interpreter cycle while the
  completion flag is clear. With that shape, the base horizontal target
  `(50,80)` and vertical target `(20,100)` both matched QEMU with 0 mismatches.
- The expanded four-case movement batch also matched QEMU with 0 mismatches.
  It adds right-edge completion for an unreachable target X of `250`, where
  view 11/group 0/frame 0 stops at left `140`, and bottom-edge completion for
  an unreachable target Y of `250`, where the same cel stops at baseline `167`.
- A first control-buffer acceptance hypothesis used a synthetic picture payload
  `f2 00 f8 00 00 ff`, which fills the decoded control channel with zero in the
  local renderer. The initial expectation was that movement would be rejected,
  but QEMU's capture matched exact target arrival at `(50,80)`. After updating
  the expected result, the final five-case batch matched QEMU with 0
  mismatches. This records that this controlled control-zero picture is not a
  blanket movement blocker.
- The movement comparison report now includes an optional `best_position`
  tuple `(mismatches, x, baseline_y)` for mismatches, so future failures can
  identify where QEMU actually drew the object.
- The expanded 12-case movement batch matched QEMU with 0 mismatches after
  correcting the zero-step expectation. It confirms:
  - left and up directions use the same repeated-call target semantics;
  - diagonal movement can continue on one axis after the other axis enters the
    target band;
  - non-divisible distances complete when the remaining distance is within one
    step, not necessarily at the exact target coordinate;
  - already-at-target and already-within-step cases complete without movement;
  - operand 3 value zero preserves the current object step byte, and the
    generated persistent object has current step zero unless the fixture sets
    it.
- Disassembled `0x4719` with the corrected MZ-header offset. The helper returns
  zero immediately when the moving object has bit `0x0200`; otherwise it scans
  active candidates with `(flags & 0x41) == 0x41`, skips candidates with bit
  `0x0200`, skips equal `+0x02` grouping bytes, checks horizontal rectangle
  overlap, then checks baseline equality/crossing using current `+0x05` and
  saved `+0x18`.
- Startup initialization writes object byte `+0x02 = object_index`, so ordinary
  generated persistent object 0 and object 1 naturally have different grouping
  bytes and can collide.
- Added two-object cases to `tools/object_movement_probe.py`. The final
  14-case batch matched QEMU with 0 mismatches:
  - object 0 moving from `(20,80)` toward `(80,80)` stops at `(25,80)` before
    touching object 1 parked at `(50,80)`;
  - setting bit `0x0200` on object 0 with action `0x43` lets the same movement
    reach `(80,80)`.
- Added bytecode fixture helpers for `assignn`, `set_object_field_1e_var`,
  `set_object_field_01_var`, `approach_first_object_until_near`,
  `start_random_motion`, and `stop_motion_mode`, then added a mode-2 approach
  case to the movement probe.
- The first mode-2 QEMU pass used threshold `25` and did not isolate direct
  completion: the capture best fit was object 1 at `(60,75)`, indicating that
  the object had reached the collision/stuck-recovery region near object 0.
- The second pass used threshold `35` and initially expected boundary position
  `(45,80)`, but QEMU's best fit was `(50,80)`. This records that the near-band
  completion check did not complete at the exact threshold boundary.
- The corrected 15-case batch in
  `build/object-movement-probes/batches/autonomous_modes_003.json` matched QEMU
  with 0 mismatches. The new passing case initializes object 1 once, sets step
  `5`, sets countdown byte `+0x01` to `1`, starts `0x53` toward object 0 with
  near threshold `35`, and confirms autonomous mode 2 completes at `(50,80)`
  without reissuing `0x53` from script logic.
- Later call-site analysis corrected this per-cycle ordering. Helper `0x0644`,
  not `0x0563`, scans active/update-eligible objects before logic execution
  and calls dispatcher `0x067a` for objects whose countdown byte `+0x01` is
  exactly `1`. Dispatcher `0x067a` calls `0x3f5a` for mode `+0x22 == 1`,
  `0x0b36` for mode `2`, and `0x1672` for mode `3`. It then calls extra
  rectangle-boundary logic when global `[0x013d]` is nonzero and direction byte
  `+0x21` is nonzero. Helper `0x0563` is called later, after logic 0, and
  performs automatic group/frame work before invoking `0x150a` and
  rebuilding/drawing/refreshing the update list rooted at `0x16ff`. A later
  generated QEMU movement fixture isolates the countdown-gated
  `0x067a -> 0x1672` path directly.

## Countdown-gated motion and additional view cel probes

Commands/evidence:

- `python3 -B -m unittest discover -s tests`
- `python3 -B tools/object_movement_probe.py --dos-prefix ME --output build/object-movement-probes/batches/motion_modes_004.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/object_overlay_probe.py --dos-prefix OE --output build/object-overlay-probes/batches/view_cel_selection_002.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/inspect_view.py 11 --groups 4 --frames 8`
- `ndisasm -b 16 -o 0x0b36 -e 0x0d36 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x6b82 -e 0x6d82 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `python3 -B tools/disassemble_logic.py 1 | rg -n "set_object_field_23|clear_object_bit_0020|set_object_bit_0020|0x48|0x49|0x4a|0x4b" -C 2`

Documented result:

- Added two more motion cases to `tools/object_movement_probe.py`:
  - `move_to_once_countdown_gated_completion` sets object countdown byte
    `+0x01` to `1`, calls `0x51` once, and expects completion at `(50,80)`;
  - `random_motion_visible_somewhere` sets step `5`, sets countdown byte
    `+0x01` to `1`, starts `0x54`, and accepts any capture that exactly matches
    the object at a valid final position.
- The 17-case QEMU movement batch matched with 0 mismatches. It confirms that
  target mode 3 can complete through the autonomous `0x067a -> 0x1672` path
  without reissuing `0x51` from script logic when countdown byte `+0x01` is
  ready. The recorded random-motion final position was `(140,112)`.
- Added three object overlay cases for view 11 group/frame selection: group 0
  frame 1, group 1 frame 0, and group 1 frame 1. The 22-case QEMU overlay batch
  matched with 0 mismatches.
- Disassembly of `0x0b36` refined the approach stuck-recovery model:
  - mode 2 computes object and first-object center X values by adding half the
    frame width to object X;
  - it calls `0x16ed` with the near threshold stored in object byte `+0x27`;
  - a zero direction clears `+0x21` and `+0x22` and sets completion flag
    `+0x28`;
  - initial sentinel `+0x29 == 0xff` changes to `0` after the first
    non-complete direct approach step;
  - if bit `0x4000` says the object did not move, the helper chooses a random
    nonzero direction, computes a delay from half the center/baseline distance
    plus one, and stores either the current step size or a random delay at
    least as large as the step in `+0x29`;
  - while `+0x29` is nonzero, the helper subtracts the current step byte from
    it on each pass and delays returning to the direct approach direction.
- A source pass over action handlers `0x48..0x4b` confirmed the setup side of
  object byte `+0x23`: mode 0 and mode 3 set bit `0x0020`; mode 1 and mode 2
  set bits `0x1030`, store an immediate flag in `+0x27`, and clear that flag.
  The current QEMU work validates static cel/group selection, not automatic
  frame-cycling semantics; the runtime consumers of `+0x23` remain a separate
  follow-up target.

## 2026-07-02: logic interpreter opcode coverage and control-flow probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B - <<'PY' ...` comparing `tools/disassemble_logic.py`
  `ACTION_NAMES` and `COND_NAMES` against opcode paragraphs in
  `docs/src/logic_bytecode.md`.
- `python3 -B -m unittest discover -s tests`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LI --output build/logic-interpreter-probes/batches/control_flow_001.json --boot-wait 5 --draw-wait 8`
- Local best-position scan over the failed logic-interpreter captures.
- `ndisasm -b 16 -o 0x293c -e 0x2b3c build/cleanroom/AGI.decrypted.exe | sed -n '1,190p'`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LJ --output build/logic-interpreter-probes/batches/control_flow_002.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/disassemble_logic.py --stats | sed -n '1,140p'`

Documented result:

- The opcode-label audit found that `tools/disassemble_logic.py` labels all
  action opcodes `0x00..0xaf` and all valid-looking SQ2 condition-table entries
  `0x00..0x12`. The only missing paragraph in `logic_bytecode.md` was the
  structural action byte `0x00` (`end`), which is now documented as a normal
  catalog entry as well as in the interpreter-loop prose.
- The logic bytecode chapter now also records the invalid and structural byte
  ranges: action bytes `0xb0..0xfb` take the action dispatcher's invalid-opcode
  path, `0xfc` and `0xfd` are invalid outside conditions, `0xfe` is the
  main-stream jump byte, and `0xff` is the main-stream condition byte.
  Condition bytes `0x13..0x25` are reserved/invalid for this SQ2 build,
  `0x26..0xfb` are rejected by the condition dispatcher, and `0xfc..0xff` are
  condition-list markers rather than predicates.
- Added `tests/test_logic_doc_coverage.py` so the documentation now fails the
  local test suite if any action label or known condition label disappears from
  `logic_bytecode.md`.
- Added `tools/logic_interpreter_probe.py`, a snapshot-backed QEMU harness that
  patches generated logic bytecode into `LOGIC.0`, replaces picture 0 with a
  blank synthetic picture, captures the original interpreter's visible output,
  and compares it to local `compose_frame_on_picture()` expectations.
- Added `setup_transient_object_action()` to `tools/qemu_fixture.py` so logic
  probes can draw a view cel without duplicating bytecode encoding.
- The first QEMU run, `control_flow_001.json`, matched only
  `if_false_skips_then_draw`. `jump_skips_first_draw`,
  `not_condition_runs_then_draw`, and `or_group_true_runs_then_draw` captured a
  blank background where the expected transient view should have been. A local
  best-position scan found no exact object match anywhere in those captures.
- Disassembly of `code.logic.interpret_main` (`0x293c`) confirmed the static
  control-flow model:
  - `0xfe` reads a little-endian word through `lodsw` and adds it to `SI`;
  - `0xff` scans a condition list and, on the true path, skips the false-delta
    word before executing the block;
  - on the false path, the scanner skips to the condition-list terminator,
    reads the false-delta word, and adds it to `SI`;
  - the `0xfd` and `0xfc` markers are handled in the condition-list parser, not
    the action dispatcher.
- The failing generated bytecode ended immediately after a transient draw. The
  corrected fixtures append the same self-loop shape used by existing
  picture/view fixtures (`fe fd ff`) after the final draw so the screenshot is
  taken while the intended draw state remains visible.
- The rerun saved at
  `build/logic-interpreter-probes/batches/control_flow_002.json` matched all
  four cases with 0 mismatches and 0 errors:
  - `jump_skips_first_draw`;
  - `if_false_skips_then_draw`;
  - `not_condition_runs_then_draw`;
  - `or_group_true_runs_then_draw`.

## 2026-07-02: expanded logic opcode-family probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- `python3 -B - <<'PY' ...` to list the expanded
  `tools.logic_interpreter_probe.base_cases()` set.
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LK --output build/logic-interpreter-probes/batches/opcode_families_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `python3 -B tools/logic_opcode_evidence.py`
- `python3 -B tools/logic_opcode_evidence.py --check`

Documented result:

- Expanded `tools/logic_interpreter_probe.py` from four control-flow cases to
  27 default QEMU cases. The new cases use a common pattern: set up state,
  execute the opcode or opcode family under test, then draw view 11 only if a
  condition observes the expected result. If the original interpreter disagrees
  with the expected behavior, the capture is missing the transient object and
  the comparison fails.
- The expanded batch matched QEMU with 27 matches, 0 mismatches, and 0 errors.
- Newly QEMU-validated families include:
  - condition `0x00` (`always_false`);
  - variable `inc`, `dec`, `assignv`, `addn`, `addv`, `subn`, `subv`;
  - indirect variable forms `0x09..0x0b`;
  - multiplication/division forms `0xa5..0xa8`, including low-product-byte and
    quotient behavior;
  - immediate and variable-selected flag actions `0x0c..0x11`;
  - comparison predicates `0x02..0x06`;
  - object position setter/getter `0x25`/`0x27`;
  - object field `+0x24` setter/getter `0x36`/`0x39`;
  - object field `+0x21` setter/getter `0x56`/`0x57`.
- Added `tools/logic_opcode_evidence.py` and generated
  `docs/src/logic_opcode_evidence.md`. The chapter records every action opcode
  `0x00..0xaf`, every known condition opcode `0x00..0x12`, and structural or
  invalid byte ranges with an evidence level. Rows are marked QEMU-validated
  only when a generated or existing QEMU harness has actually exercised the
  behavior; otherwise they remain source-backed or reserved/invalid.

## 2026-07-02: five follow-up logic-interpreter probe groups

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_qemu_fixture`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LL --output build/logic-interpreter-probes/batches/five_steps_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LA --output build/logic-interpreter-probes/batches/step1_call_resume_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case call_logic_draws_from_called_logic --case load_logic_then_call_logic_draws --case call_logic_var_draws_selected_logic --case save_restore_resume_actions_continue_to_draw`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LB --output build/logic-interpreter-probes/batches/step2_var_backed_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case set_object_pos_var_getter_observes_values --case var_resource_group_frame_setup_draws_persistent_object --case setup_transient_object_var_draws_selected_cel --case move_object_to_var_sets_flag_at_existing_target`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LC --output build/logic-interpreter-probes/batches/step3_object_predicates_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case object_left_rect_condition_true --case object_width_rect_condition_true --case object_center_rect_condition_true --case object_right_rect_condition_true`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LD --output build/logic-interpreter-probes/batches/step4_string_message_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case set_string_from_message_equal_normalized --case parse_string_slot_sets_input_word_sequence`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LE --output build/logic-interpreter-probes/batches/step5_inventory_table_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case inventory_marker_ff_condition_true --case inventory_marker_eq_var_condition_true --case inventory_marker_ff_var_and_getter --case inventory_marker_clear_and_getter --case inventory_marker_from_var --case inventory_marker_from_var_var`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Extended `tools/qemu_fixture.py` so `logic_resource()` can encode custom
  logic message tables. The helper builds the offset table relative to the
  table base and XOR-encrypts the message text with the locally documented
  `Avis Durgan` key, matching the loader's decryption path.
- Extended `tools/logic_interpreter_probe.py` so one fixture can patch multiple
  logic resources into `VOL.3`, patch the corresponding `LOGDIR` entries, and
  filter runs with repeated `--case` options.
- A first attempt to run all 47 default logic probe cases in one snapshot disk
  filled the DOS image while copying the forty-fourth full SQ2 fixture
  directory. No interpreter behavior was observed in that run; it is a harness
  capacity limit caused by copying complete fixture directories.
- The requested steps were then run as five filtered QEMU batches:
  - Step 1, logic call/load/resume smoke probes: 4 matches, 0 mismatches.
  - Step 2, variable-backed object/resource probes: 4 matches, 0 mismatches.
  - Step 3, object rectangle predicates: 4 matches, 0 mismatches.
  - Step 4, string/message probes: 2 matches, 0 mismatches.
  - Step 5, inventory/object-table marker probes: 6 matches, 0 mismatches.
- New QEMU evidence from these batches covers:
  - actions `0x14`, `0x16`, and `0x17` for logic loading and calls;
  - actions `0x91` and `0x92` as executable resume-state opcodes that continue
    to subsequent bytecode in the smoke fixture;
  - variable-backed object/resource actions `0x26`, `0x2a`, `0x2c`, `0x30`,
    `0x52`, and `0x7b`;
  - condition opcodes `0x0b`, `0x10`, `0x11`, and `0x12`;
  - action `0x72`, action `0x75`, condition `0x0f`, and condition `0x0e`
    using custom messages `HELLO!`, `hello`, and `look`;
  - condition opcodes `0x09` and `0x0a`, plus marker actions `0x5c..0x61`.

## 2026-07-03: object/view getter and bitfield follow-up probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LF --output build/logic-interpreter-probes/batches/object_getter_bitfield_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case object_view_metadata_getters --case object_field_24_var_getter_observes_value --case object_distance_inactive_pair_sets_ff --case clear_object_fields_21_22_clears_direction --case object_bitfield_actions_dispatch_smoke`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Added five object/view follow-up cases to `tools/logic_interpreter_probe.py`.
- The QEMU batch matched with 5 matches, 0 mismatches, and 0 errors.
- Value probes now validate:
  - `0x31..0x35` reading view/object metadata after binding view 11 group 1
    frame 1;
  - `0x37` writing object byte `+0x24` from a variable, observed through
    getter `0x39`;
  - `0x45` storing `0xff` when measuring distance between inactive objects;
  - `0x4d` clearing object byte `+0x21`, observed through getter `0x57`.
- Added a separate `QEMU dispatch-smoke` evidence level to
  `docs/src/logic_opcode_evidence.md`. The smoke case proves that selected
  bitfield/helper opcodes execute, consume operands, and return to subsequent
  bytecode under the original interpreter, but does not claim to expose every
  downstream state mutation. At the time of this pass, smoke rows included
  `0x38`, `0x3a..0x3e`, `0x40..0x42`, `0x44`, `0x46..0x47`, `0x4c`, `0x4e`,
  and `0x58..0x59`; later passes promoted several of those rows to behavior
  evidence.

## 2026-07-03: object state, random, and no-op runtime probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LG --output build/logic-interpreter-probes/batches/object_state_misc_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case object_add_pos_from_vars_getter_observes_sum --case random_equal_bounds_stores_bound --case noop_7f_continues_to_draw --case noop_9b_consumes_two_operands_then_draws --case noop_af_runtime_consumes_no_operand --case set_object_pos_dirty_getter_observes_values --case set_object_pos_dirty_var_getter_observes_values --case deactivate_object_removes_persistent_draw --case clear_all_object_bits_removes_persistent_draw`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LG --output build/logic-interpreter-probes/batches/object_state_misc_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_all_object_bits_keeps_current_draw_entry`
- `python3 -B tools/logic_opcode_evidence.py`
- `python3 -B tools/logic_opcode_evidence.py --check`

Documented result:

- Added QEMU-visible logic probes for additional object-state and misc actions:
  - `0x28` adds positive variable-sourced deltas to object position fields,
    observed through getter `0x27`;
  - `0x82` stores the bound when its low and high random bounds are equal;
  - `0x7f`, `0x9b`, and `0xaf` execute and continue to following drawing
    bytecode in the original interpreter;
  - `0x93` and `0x94` write object position fields, observed through getter
    `0x27`;
  - `0x24` deactivates an active persistent object so only the following
    transient draw remains visible in the fixture.
- The first nine-case batch matched 8 cases and mismatched the initial `0x22`
  hypothesis. The mismatch box was `x=20..39, y=76..80`, exactly the footprint
  of the previously activated persistent object. This showed that action
  `0x22` clearing active/update bits does not immediately unlink an object that
  was already activated for the current draw.
- Extended `tools/logic_interpreter_probe.py` comparison expectations so a case
  can include additional expected sprites. The corrected `0x22` case,
  `clear_all_object_bits_keeps_current_draw_entry`, expects both the old
  persistent object at `x=20` and the following transient object at `x=50`.
- The corrected single-case rerun in
  `build/logic-interpreter-probes/batches/object_state_misc_002.json` matched
  with 1 match, 0 mismatches, and 0 errors.
- Regenerated `docs/src/logic_opcode_evidence.md`; actions `0x22`, `0x24`,
  `0x28`, `0x7f`, `0x82`, `0x93`, `0x94`, `0x9b`, and `0xaf` are now recorded
  with QEMU-backed evidence.

## 2026-07-03: variable view load and object field +0x23 probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LH --output build/logic-interpreter-probes/batches/load_view_field23_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case load_view_var_allows_following_draw --case object_field_23_mode0_dispatch_smoke --case object_field_23_mode1_clears_flag --case object_field_23_mode3_dispatch_smoke --case object_field_23_mode2_clears_flag`
- `python3 -B tools/logic_opcode_evidence.py`
- `python3 -B tools/logic_opcode_evidence.py --check`

Documented result:

- Added a `preload_view_no` option to `tools/logic_interpreter_probe.py` so
  individual cases can start without the default `load_view 11` prelude. This
  was necessary for the `0x1f` probe: if view 11 were preloaded, a following
  draw would not prove that `load_view_var` did the loading.
- The five-case QEMU batch
  `build/logic-interpreter-probes/batches/load_view_field23_001.json` matched
  with 5 matches, 0 mismatches, and 0 errors.
- `0x1f` (`load_view_var`) is now QEMU-validated: a fixture assigns variable 1
  to view 11, executes `0x1f`, and then draws view 11 successfully without any
  earlier view preload.
- `0x49` (`set_object_field_23_mode1`) and `0x4b`
  (`set_object_field_23_mode2`) are QEMU-validated for the observable part of
  their setup contract: each clears its flag operand, and the generated logic
  draws only if that flag is observed clear.
- `0x48` (`set_object_field_23_mode0`) and `0x4a`
  (`set_object_field_23_mode3`) are recorded as QEMU dispatch-smoke evidence:
  the fixtures prove each opcode executes and returns to following draw
  bytecode, but they do not directly expose object byte `+0x23`.

## 2026-07-03: collision-skip clear-bit movement probe

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest tests.test_qemu_fixture tests.test_object_movement_probe`
- `python3 -B tools/object_movement_probe.py --dos-prefix MD --output build/object-movement-probes/batches/clear_skip_bit_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case move_collision_clear_skip_bit_blocks_again`
- `python3 -B tools/logic_opcode_evidence.py`
- `python3 -B tools/logic_opcode_evidence.py --check`

Documented result:

- Added `clear_object_bit_0200_action()` to `tools/qemu_fixture.py`, encoding
  action `0x44` with one fixed object operand.
- Added filtered `--case` support to `tools/object_movement_probe.py` so a
  single movement case can be rerun without rebuilding the whole movement
  corpus.
- Added movement case `move_collision_clear_skip_bit_blocks_again`: object 0
  first sets collision-skip bit `0x0200` with `0x43`, then clears it with
  `0x44`, then moves toward object 1. QEMU matched the expected blocked result
  at `(25,80)`, proving that `0x44` restores normal object-object collision
  testing after the bit was set.
- Regenerated `docs/src/logic_opcode_evidence.md`; action `0x44` is now
  recorded as QEMU-validated instead of dispatch-smoke.

## 2026-07-03: horizon-bit placement probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LZ --output build/logic-interpreter-probes/batches/horizon_bits_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case horizon_clamps_object_when_bit_clear --case horizon_exempt_bit_keeps_object_above_horizon --case horizon_clear_exempt_bit_restores_clamp`
- `python3 -B tools/logic_opcode_evidence.py`
- `python3 -B tools/logic_opcode_evidence.py --check`

Documented result:

- Added three logic-interpreter QEMU cases around the horizon-like placement
  clamp:
  - `horizon_clamps_object_when_bit_clear`: `0x3f` sets `[0x012d] = 100`; a
    reset object placed at baseline `80` clamps to baseline `101`;
  - `horizon_exempt_bit_keeps_object_above_horizon`: after `0x3d` sets object
    bit `0x0008`, the same placement remains at baseline `80`;
  - `horizon_clear_exempt_bit_restores_clamp`: after `0x3d` sets and `0x3e`
    clears bit `0x0008`, the placement clamps to baseline `101` again.
- The QEMU batch `build/logic-interpreter-probes/batches/horizon_bits_001.json`
  matched with 3 matches, 0 mismatches, and 0 errors.
- Regenerated `docs/src/logic_opcode_evidence.md`; actions `0x3d`, `0x3e`, and
  `0x3f` are now QEMU-validated instead of source-backed or dispatch-smoke.

## 2026-07-03: fixed-priority clear-bit probe

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LP --output build/logic-interpreter-probes/batches/fixed_priority_bit_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_fixed_priority_bit_uses_derived_priority`
- The first attempt failed under the restricted sandbox because QEMU could not
  bind `127.0.0.1:5` for VNC. The same command was rerun with elevated QEMU
  permission.
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Added logic-interpreter QEMU case
  `clear_fixed_priority_bit_uses_derived_priority`.
- The fixture draws a synthetic control-6 picture, sets object 10 to fixed
  priority/control byte `5` with action `0x36`, then clears object bit `0x0004`
  with action `0x38` before drawing.
- QEMU matched the expected visible output: at baseline `80`, placement derived
  priority `7` from Y and drew over the control-6 background. This validates
  the observable effect of `0x38`, not just its dispatch.
- Regenerated `docs/src/logic_opcode_evidence.md`; action `0x38` is now
  recorded as QEMU-validated instead of dispatch-smoke.

## 2026-07-03: clear motion mode with action 0x4e

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest tests.test_object_movement_probe tests.test_qemu_fixture`
- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- `python3 -B tools/object_movement_probe.py --dos-prefix ME --output build/object-movement-probes/batches/clear_field_22_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_field_22_after_random_motion_stops_motion`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Added `clear_object_field_22_and_global_action()` to `tools/qemu_fixture.py`,
  encoding action `0x4e` with one fixed object operand.
- Added movement case `clear_field_22_after_random_motion_stops_motion`: object
  0 is initialized at `(60,80)`, random motion is started with action `0x54`,
  and action `0x4e` is executed immediately afterward.
- QEMU matched the expected stationary result at `(60,80)`. This validates the
  visible object byte `+0x22` clearing effect of `0x4e`; the static side effect
  on global `[0x0139]` remains documented from disassembly rather than this
  capture.
- Regenerated `docs/src/logic_opcode_evidence.md`; action `0x4e` is now
  recorded as QEMU-validated instead of dispatch-smoke.

## 2026-07-03: control and rectangle object-bit probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest tests.test_object_movement_probe tests.test_qemu_fixture`
- Exploratory batch:
  `python3 -B tools/object_movement_probe.py --dos-prefix MC --output build/object-movement-probes/batches/control_bit_0002_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case move_control_1_without_bit_0002_blocks --case move_control_1_set_bit_0002_reaches_target --case move_control_1_clear_bit_0002_blocks_again`
- Exploratory batch:
  `python3 -B tools/object_movement_probe.py --dos-prefix MR --output build/object-movement-probes/batches/control_bit_0002_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case move_control_1_without_bit_0002_reaches_target --case move_control_1_set_bit_0002_reaches_target --case move_control_1_clear_bit_0002_still_reaches_target --case move_rect_boundary_without_bit_0002_stops_at_edge --case move_rect_boundary_set_bit_0002_reaches_target --case move_rect_boundary_clear_bit_0002_stops_again`
- Matched rectangle-boundary batch:
  `python3 -B tools/object_movement_probe.py --dos-prefix MB --output build/object-movement-probes/batches/rect_bit_0002_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case move_rect_boundary_without_bit_0002_stops_at_edge --case move_rect_boundary_set_bit_0002_reaches_target --case move_rect_boundary_clear_bit_0002_stops_again`
- Exploratory full acceptance batch:
  `python3 -B tools/object_movement_probe.py --dos-prefix MX --output build/object-movement-probes/batches/control_bits_acceptance_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case move_control_1_without_bit_0002_blocks --case move_control_1_set_bit_0002_reaches_target --case move_control_1_clear_bit_0002_blocks_again --case move_rect_boundary_without_bit_0002_stops_at_edge --case move_rect_boundary_set_bit_0002_reaches_target --case move_rect_boundary_clear_bit_0002_stops_again --case move_control_2_set_bit_0100_blocks --case move_control_2_clear_bits_0900_reaches_target --case move_control_3_set_bit_0800_blocks --case move_control_3_clear_bits_0900_reaches_target`
- Matched control-class-1 hidden batch:
  `python3 -B tools/object_movement_probe.py --dos-prefix M1 --output build/object-movement-probes/batches/control_class_1_hidden_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case move_control_1_without_bit_0002_blocks --case move_control_1_set_bit_0002_still_hidden --case move_control_1_clear_bit_0002_still_hidden`
- Matched control-class-2/3 rejection batch:
  `python3 -B tools/object_movement_probe.py --dos-prefix M9 --output build/object-movement-probes/batches/control_bits_0900_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case move_control_2_set_bit_0100_blocks --case move_control_2_clear_bits_0900_reaches_target --case move_control_3_set_bit_0800_blocks --case move_control_3_clear_bits_0900_reaches_target`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Added fixture helpers for actions `0x40`, `0x41`, `0x42`, `0x58`, `0x59`,
  and `0x5a`.
- Added `picture_only` comparison support to `tools/object_movement_probe.py`
  for cases where the original engine leaves no visible object and the capture
  should equal the rendered picture alone.
- The first control-class-1 probes used fixed priority/control `15` and reached
  the target, exposing that `code.object.control_acceptance` skips the scan when
  object byte `+0x24 == 0x0f`.
- Repeating control-class-1 probes at fixed priority/control `14` produced
  plain-picture captures whether bit `0x0002` was clear, set by `0x58`, or set
  then cleared by `0x59`. This is recorded as control-class/visibility evidence,
  not as the positive `0x58` movement oracle.
- The positive `0x58`/`0x59` oracle is rectangle-boundary behavior in
  `code.motion.pre_mode_and_boundary_update`: with rectangle bounds
  `(30,70)..(60,90)`, countdown-gated movement from `(20,80)` toward `(50,80)`
  stops at `(30,80)` when bit `0x0002` is clear, reaches `(50,80)` after
  `0x58`, and stops at `(30,80)` again after `0x59`.
- QEMU validates `0x40`: setting bit `0x0100` leaves a priority-14 object
  visible at `(20,80)` on a full control-class-2 picture and prevents movement
  to `(50,80)`.
- QEMU validates `0x41`: setting bit `0x0800` leaves a priority-14 object
  visible at `(20,80)` on a full control-class-3 picture and prevents movement
  to `(50,80)`.
- QEMU validates `0x42`: clearing bits `0x0100`/`0x0800` after `0x40` or
  `0x41` restores movement to `(50,80)`.
- Added symbolic labels `code.object.control_acceptance`,
  `code.motion.pre_mode_and_boundary_update`, and
  `code.motion.rectangle_boundary_check`.
- Regenerated `docs/src/logic_opcode_evidence.md`; actions `0x40`, `0x41`,
  `0x42`, `0x58`, and `0x59` are now QEMU-validated instead of
  dispatch-smoke.

## 2026-07-03: static frame-timer and frame-mode analysis

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -c "import struct; data=open('build/cleanroom/AGI.decrypted.exe','rb').read(64); print(struct.unpack_from('<14H', data, 0))"`
- `python3 -B -c "import sys; sys.path.insert(0,'tools'); from disassemble_logic import AGIDATA, load_table; data=AGIDATA.read_bytes(); table=load_table(data,0x061d,0xb0); [print(f'{op:02x} handler={table[op].handler:04x} argc={table[op].argc} meta={table[op].meta:02x}') for op in [0x3a,0x3b,0x3c,0x46,0x47,0x48,0x49,0x4a,0x4b,0x4c,0x58,0x59,0x5a]]"`
- `ndisasm -b 16 -o 0 build/cleanroom/AGI.decrypted.exe > build/cleanroom/AGI.decrypted.ndisasm`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_6ac8.bin bs=1 skip=27848 count=570`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_0400.bin bs=1 skip=1536 count=1700`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_4800.bin bs=1 skip=18944 count=1200`
- `ndisasm -b 16 -o 0x6ac8 build/cleanroom/slice_6ac8.bin`
- `ndisasm -b 16 -o 0x0400 build/cleanroom/slice_0400.bin`
- `ndisasm -b 16 -o 0x4800 build/cleanroom/slice_4800.bin`
- `rg -n "call 0x48|call 0x4[0-9a-f]{3}|\\[di\\+0x20\\]|\\[di\\+0x23\\]|\\[di\\+0x1f\\]" build/cleanroom/AGI.decrypted.ndisasm`

Documented result:

- Re-centered this pass on static disassembly after the user pointed out that
  the work had drifted too far toward trial-and-error QEMU probing. QEMU remains
  useful as a validation tool, but the behavior model in this section comes
  from the executable.
- Confirmed the MZ/header address convention for handler disassembly. The
  action dispatch table in `SQ2/AGIDATA.OVL` stores loaded-image offsets; the
  decrypted executable file stores the corresponding bytes at image offset
  `+0x0200`, because the executable header is 32 paragraphs. For example action
  `0x5a` is table/image `0x7b4e` and its bytes are at file offset `0x7d4e`.
- Confirmed action table entries:
  - `0x46` handler `0x6c97`, one operand: clears object flag bit `0x0020`.
  - `0x47` handler `0x6cbc`, one operand: sets object flag bit `0x0020`.
  - `0x48` handler `0x6b82`, one operand: sets byte `+0x23 = 0` and bit
    `0x0020`.
  - `0x49` handler `0x6bae`, two operands: sets byte `+0x23 = 1`, sets bits
    `0x1030`, stores operand 1 in byte `+0x27`, and clears that flag.
  - `0x4a` handler `0x6beb`, one operand: sets byte `+0x23 = 3` and bit
    `0x0020`.
  - `0x4b` handler `0x6c17`, two operands: sets byte `+0x23 = 2`, sets bits
    `0x1030`, stores operand 1 in byte `+0x27`, and clears that flag.
  - `0x4c` handler `0x6c54`, two operands: reads `var[arg1]` and copies the
    byte into both object bytes `+0x1f` and `+0x20`. This corrects the earlier
    wording that said `+0x20` was cleared.
- Labeled `code.object.frame_timer_update` at image `0x0563`. It scans object
  records from `[0x096b]` to `[0x096d]`, selecting records whose flag word
  satisfies `(flags & 0x0051) == 0x0051`. If bit `0x0020` is set and byte
  `+0x20` is nonzero, it decrements `+0x20`; when the decrement reaches zero,
  it calls `code.object.advance_frame_by_mode` and reloads `+0x20` from
  `+0x1f`.
- Labeled `code.object.advance_frame_by_mode` at image `0x48b3`. If bit
  `0x1000` is set, the helper clears that bit and returns without changing the
  selected frame. Otherwise byte `+0x23` selects one of four frame behaviors:
  mode 0 increments and wraps; mode 1 increments toward the last frame and
  completes there; mode 2 decrements toward frame 0 and completes there, or
  completes immediately if already at frame 0; mode 3 decrements and wraps from
  frame 0 to the last frame.
- Completion in frame modes 1 and 2 sets flag byte `+0x27`, clears object bit
  `0x0020`, clears direction byte `+0x21`, and resets byte `+0x23` to zero.
- Updated `docs/src/symbolic_labels.md`, `docs/src/logic_bytecode.md`,
  `docs/src/graphics_object_pipeline.md`, and `docs/src/current_status.md` with
  this static model.

## 2026-07-03: QEMU validation of frame-timer actions

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -m unittest tests.test_qemu_fixture tests.test_object_movement_probe`
- `python3 -B tools/logic_opcode_evidence.py --check`
- `python3 -B tools/object_movement_probe.py --dos-prefix MA --output build/object-movement-probes/batches/frame_timer_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case animation_interval_mode1_reaches_frame1 --case animation_clear_bit_0020_prevents_frame_advance --case animation_set_bit_0020_restores_frame_advance`
- The first QEMU attempt failed under the restricted sandbox because QEMU could
  not bind `127.0.0.1:5` for VNC. The same command was rerun with approved
  elevated permission for `python3 -B tools/object_movement_probe.py`.
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Focused tests `tests.test_qemu_fixture` and `tests.test_object_movement_probe`
  passed, covering the newly added helper encodings and movement case registry.
- QEMU batch `build/object-movement-probes/batches/frame_timer_001.json`
  matched with 3 matches, 0 mismatches, and 0 errors:
  - `animation_interval_mode1_reaches_frame1`: action `0x4c` seeds the frame
    timer and action `0x49` starts mode 1; view 11/group 0 advances from frame
    0 to frame 1.
  - `animation_clear_bit_0020_prevents_frame_advance`: action `0x46` clears
    bit `0x0020` after setup, so the frame remains 0.
  - `animation_set_bit_0020_restores_frame_advance`: action `0x47` sets bit
    `0x0020` after `0x46`, restoring the frame advance to frame 1.
- Promoted actions `0x46`, `0x47`, and `0x4c` in
  `tools/logic_opcode_evidence.py` from QEMU dispatch-smoke to QEMU behavior
  evidence backed by `object_movement_probe: frame_timer_001`, then regenerated
  `docs/src/logic_opcode_evidence.md`.
- Updated `docs/src/logic_bytecode.md`, `docs/src/graphics_object_pipeline.md`,
  and `docs/src/compatibility_testing.md` with the replay command and result.

## 2026-07-03: QEMU validation of remaining frame modes

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_48b3_49c8.bin bs=1 skip=19123 count=280`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_6b82_6ce0.bin bs=1 skip=28034 count=350`
- `ndisasm -b 16 -o 0x48b3 build/cleanroom/slice_48b3_49c8.bin`
- `ndisasm -b 16 -o 0x6b82 build/cleanroom/slice_6b82_6ce0.bin`
- `python3 -B -c "import sys; sys.path.insert(0,'tools'); from disassemble_logic import AGIDATA, load_table; data=AGIDATA.read_bytes(); table=load_table(data,0x061d,0xb0); [print(f'{op:02x} handler={table[op].handler:04x} argc={table[op].argc} meta={table[op].meta:02x}') for op in [0x46,0x47,0x48,0x49,0x4a,0x4b,0x4c]]"`
- `python3 -B -m unittest tests.test_qemu_fixture tests.test_object_movement_probe`
- `python3 -B tools/object_movement_probe.py --dos-prefix MF --output build/object-movement-probes/batches/frame_timer_modes_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case animation_mode0_forward_loop_wraps_to_frame0 --case animation_mode2_backward_completion_reaches_frame0 --case animation_mode3_backward_loop_wraps_to_frame1`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Re-read the frame-mode dispatcher and corrected the previous source note for
  mode 2. The branch at `0x4934` completes immediately only when the current
  frame is already 0; otherwise it decrements, and the shared completion path is
  reached only when the new frame becomes 0.
- Added fixture helpers for action `0x48`, `0x4a`, `0x4b`, condition
  `var == immediate`, and action `0x32` so looping frame modes can be stopped
  deterministically after the desired frame appears.
- Added movement cases `animation_mode0_forward_loop_wraps_to_frame0`,
  `animation_mode2_backward_completion_reaches_frame0`, and
  `animation_mode3_backward_loop_wraps_to_frame1`.
- Focused tests `tests.test_qemu_fixture` and `tests.test_object_movement_probe`
  passed with 37 tests.
- QEMU batch `build/object-movement-probes/batches/frame_timer_modes_002.json`
  matched with 3 matches, 0 mismatches, and 0 errors:
  - `animation_mode0_forward_loop_wraps_to_frame0`: action `0x48` mode 0 wraps
    view 11/group 0 from frame 1 to frame 0.
  - `animation_mode2_backward_completion_reaches_frame0`: action `0x4b` mode 2
    moves from frame 1 to frame 0 and stops.
  - `animation_mode3_backward_loop_wraps_to_frame1`: action `0x4a` mode 3 wraps
    backward from frame 0 to frame 1.
- Promoted actions `0x48` and `0x4a` from QEMU dispatch-smoke to behavior
  evidence, and extended `0x4b` behavior evidence with the visible mode-2
  completion probe. Regenerated `docs/src/logic_opcode_evidence.md`.

## 2026-07-03: object update-list partition actions

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B -c "import sys; sys.path.insert(0,'tools'); from disassemble_logic import AGIDATA, load_table; data=AGIDATA.read_bytes(); table=load_table(data,0x061d,0xb0); [print(f'{op:02x} handler={table[op].handler:04x} argc={table[op].argc} meta={table[op].meta:02x}') for op in range(0x36,0x3d)]"`
- `rg -n "0x3a|0x3b|0x3c|clear_object_bit_0010|set_object_bit_0010|refresh_object_helper|0x0010|refresh" docs/src/logic_bytecode.md docs/src/graphics_object_pipeline.md docs/src/clean_room_executable_notes.md docs/src/symbolic_labels.md tools tests`
- `ndisasm -b 16 -o 0x6a30 -e 0x6c30 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x0440 -e 0x0640 build/cleanroom/AGI.decrypted.exe`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_logic_doc_coverage`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LR --output build/logic-interpreter-probes/batches/object_root_partition_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_bit_0010_moves_object_behind_set_partition --case set_bit_0010_moves_object_over_clear_partition`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LR --output build/logic-interpreter-probes/batches/object_root_partition_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_bit_0010_moves_object_behind_set_partition --case set_bit_0010_moves_object_over_clear_partition`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LR --output build/logic-interpreter-probes/batches/object_root_partition_003.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_bit_0010_moves_object_behind_set_partition --case set_bit_0010_moves_object_over_clear_partition`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix LR --output build/logic-interpreter-probes/batches/object_root_partition_004.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_bit_0010_moves_object_behind_set_partition --case set_bit_0010_moves_object_over_clear_partition`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Re-read action handlers `0x3a..0x3c` and renamed action `0x3c` from
  `refresh_object_helper` to `refresh_object_lists`. The handler computes the
  object record address from its operand, but the called helpers do not receive
  that address; the observed action is a global update-list refresh.
- Added symbolic labels for the update-list wrappers and the bit-`0x0010`
  membership helpers:
  - `code.object.build_active_update_list` at image `0x6a26`.
  - `code.object.build_inactive_partition_list` at image `0x6a3d`.
  - `code.object.flush_update_lists_restore` at image `0x6a54`.
  - `code.object.rebuild_draw_update_lists` at image `0x6a8e`.
  - `code.object.refresh_update_lists` at image `0x6aab`.
  - `code.object.clear_root_16ff_membership` at image `0x6b44`.
  - `code.object.set_root_16ff_membership` at image `0x6b62`.
- Source model: bit `0x0010` partitions active objects between root `0x16ff`
  (`(flags & 0x0051) == 0x0051`) and root `0x1703`
  (`(flags & 0x0051) == 0x0041`). `0x3a` clears the bit through helper
  `0x6b44`; `0x3b` sets it through helper `0x6b62`; `0x3c` flushes, rebuilds,
  draws, and refreshes both roots.
- The first three QEMU batches were deliberately kept in the record as fixture
  corrections:
  - `_001` placed two active objects at the same coordinates during activation;
    placement helper `0x593a` could adjust an object before the partition effect
    was isolated.
  - `_002` used `0x93` after activation; static re-read confirmed `0x93` calls
    placement helper `0x593a`.
  - `_003` used `0x25` after activation; the capture showed the object at both
    the old and new X positions because `0x25` rewrites both current and saved
    coordinates, so the restore pass no longer erases the old drawing.
- Final QEMU batch `build/logic-interpreter-probes/batches/object_root_partition_004.json`
  matched with 2 matches, 0 mismatches, and 0 errors after the expected image
  explicitly modeled the stale `0x25` drawing as setup:
  - `clear_bit_0010_moves_object_behind_set_partition`: after `0x3a`, the
    frame-1 object is drawn behind the still-bit-set frame-0 object.
  - `set_bit_0010_moves_object_over_clear_partition`: after `0x3a` then `0x3b`,
    the frame-1 object is drawn over a frame-0 object left in the clear
    partition.
- Promoted actions `0x3a`, `0x3b`, and `0x3c` in
  `tools/logic_opcode_evidence.py` from QEMU dispatch-smoke to QEMU behavior
  evidence backed by `logic_interpreter_probe: object_root_partition_004`, then
  regenerated `docs/src/logic_opcode_evidence.md`.

## 2026-07-03: object bit `0x2000` and automatic direction group selection

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_0563_0620.bin bs=1 skip=1891 count=190`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_497b_49d0.bin bs=1 skip=19323 count=100`
- `ndisasm -b 16 -o 0x0563 build/cleanroom/slice_0563_0620.bin`
- `ndisasm -b 16 -o 0x497b build/cleanroom/slice_497b_49d0.bin`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_logic_doc_coverage`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix L2 --output build/logic-interpreter-probes/batches/object_bit_2000_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_bit_2000_allows_direction_group_selection --case set_bit_2000_suppresses_direction_group_selection`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix L2 --output build/logic-interpreter-probes/batches/object_bit_2000_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_bit_2000_allows_direction_group_selection --case set_bit_2000_suppresses_direction_group_selection`

Documented result:

- Action handler `0x2d` at image `0x497b` sets object bit `0x2000`; handler
  `0x2e` at image `0x49a3` clears that bit.
- `code.object.frame_timer_update` at image `0x0563` tests bit `0x2000` at
  image `0x0593`. If the bit is set, it skips automatic direction-based group
  selection. If the bit is clear, it may index one of two `AGIDATA.OVL` tables
  by object direction byte `+0x21`:
  - `data.object.group_for_direction_two_or_three_groups` at data `0x08dd`
    when object byte `+0x0b` is 2 or 3.
  - `data.object.group_for_direction_four_plus_groups` at data `0x08e7` when
    object byte `+0x0b` is at least 4.
- The helper only calls `code.object.select_group` (`0x3bb7`) when object byte
  `+0x01 == 1`, the table target is not sentinel `4`, and the target differs
  from the current group byte `+0x0a`.
- Initial QEMU batch `object_bit_2000_001` used view 11 and a self-looping
  fixture. The first case mismatched because the persistent object still drew
  as group 0 frame 0. Direct comparison against rendered view-11 frames showed
  the original capture exactly matched group 0 frame 0, so the fixture was not
  exposing the per-cycle selection path.
- The corrected fixture uses a guarded one-time initialization and a normal
  `0x00` end action so the engine can advance later cycles without the logic
  script repainting or resetting the object. It also uses view 4, whose four
  groups exercise the `data.object.group_for_direction_four_plus_groups` table.
- Final QEMU batch `object_bit_2000_002` matched with 2 matches, 0 mismatches,
  and 0 errors:
  - `clear_bit_2000_allows_direction_group_selection`: action `0x2e` leaves
    bit `0x2000` clear; direction `6` selects view 4 group 1.
  - `set_bit_2000_suppresses_direction_group_selection`: action `0x2d` sets
    bit `0x2000`; the same direction leaves view 4 on group 0.
- Promoted actions `0x2d` and `0x2e` in `tools/logic_opcode_evidence.py` to
  QEMU behavior evidence backed by `logic_interpreter_probe:
  object_bit_2000_002`, then regenerated `docs/src/logic_opcode_evidence.md`.

## 2026-07-03: expanded direction groups, scheduler order, and rectangle bounds

Commands run from `/Users/peter/ai/agi/reverse`:

- `xxd -g1 -l 32 -s 0x08dd SQ2/AGIDATA.OVL`
- `xxd -g1 -l 32 -s 0x08e7 SQ2/AGIDATA.OVL`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_0100_0270.bin bs=1 skip=768 count=368`
- `ndisasm -b 16 -o 0x0100 build/cleanroom/slice_0100_0270.bin`
- Local Python scan for near calls to `0x0563`, `0x0644`, `0x150a`,
  `0x293c`, `0x6a8e`, and `0x6aab`.
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_logic_doc_coverage`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix L3 --output build/logic-interpreter-probes/batches/object_bit_2000_003.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_bit_2000_two_or_three_group_direction6_selects_group1 --case clear_bit_2000_two_or_three_group_direction5_is_sentinel --case clear_bit_2000_requires_field01_equal_one`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix L3 --output build/logic-interpreter-probes/batches/object_bit_2000_004.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_bit_2000_two_or_three_group_direction6_selects_group1 --case clear_bit_2000_two_or_three_group_direction5_is_sentinel --case clear_bit_2000_field01_countdown_eventually_selects_group --case clear_bit_2000_requires_field01_equal_one_when_forced`
- `python3 -B -m unittest tests.test_qemu_fixture tests.test_object_movement_probe`
- `python3 -B tools/object_movement_probe.py --dos-prefix RB --output build/object-movement-probes/batches/rect_bounds_clear_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case move_rect_boundary_clear_bounds_reaches_target`

Documented result:

- Expanded the `0x2000` direction/group probes:
  - `object_bit_2000_004` matched with 4 matches, 0 mismatches, and 0 errors.
  - View 5 validates the two/three-group table at `AGIDATA.OVL:0x08dd`:
    direction `6` selects group 1.
  - Direction `5` in the same table maps to sentinel `4`, so the group remains
    unchanged.
  - A one-shot `+0x01 = 2` does not permanently block selection. The first
    `code.object.frame_timer_update` pass sees `+0x01 != 1`, then
    `code.motion.update_objects` decrements the countdown; a later cycle sees
    `+0x01 == 1` and selects the direction group.
  - A per-cycle logic write that keeps `+0x01 = 2` prevents the group change,
    confirming the exact gate.
- Re-read the top-level cycle at image `0x0150`:
  - `0x0198` calls `code.motion.pre_mode_and_boundary_update` at image
    `0x0644`.
  - `0x01bd` calls `code.logic.call_logic` (`0x12ae`) with logic number 0.
  - `0x024b` calls `code.object.frame_timer_update` (`0x0563`) unless byte
    `[0x1757]` is nonzero.
  - `code.object.frame_timer_update` calls `code.motion.update_objects`
    (`0x150a`) at image `0x061e`, then rebuilds/draws/refreshes the root
    `0x16ff` update list.
- Corrected symbolic labels for the pre-motion pass and rectangle helper:
  - `code.motion.pre_mode_and_boundary_update` is image `0x0644`.
  - `code.motion.rectangle_boundary_check` is image `0x06d9`.
- Added QEMU movement case `move_rect_boundary_clear_bounds_reaches_target`.
  Batch `rect_bounds_clear_001` matched with 1 match, 0 mismatches, and 0
  errors, validating action `0x5b` by setting bounds with `0x5a`, clearing them
  with `0x5b`, and observing that the object reaches `(50,80)` instead of
  stopping at the old boundary.
- Promoted actions `0x5a` and `0x5b` in `tools/logic_opcode_evidence.py` to
  QEMU behavior evidence, then regenerated `docs/src/logic_opcode_evidence.md`.

## 2026-07-03: resource lifecycle, text input, menu, and sound probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "overlay_picture_var_composes_extra_picture|load_logic_var_then_call_logic_draws|discard_view_allows_reload" tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py docs/src`
- `sed -n '620,820p' tools/logic_interpreter_probe.py`
- `sed -n '1,180p' tools/qemu_snapshot.py`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_qemu_snapshot tests.test_logic_doc_coverage`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix RL --output build/logic-interpreter-probes/batches/resource_lifecycle_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case load_logic_var_then_call_logic_draws --case overlay_picture_var_composes_extra_picture --case discard_picture_var_allows_reload_and_overlay --case discard_view_allows_reload_and_draw --case discard_view_var_allows_reload_and_draw`
- `python3 -B -m json.tool build/logic-interpreter-probes/batches/resource_lifecycle_002.json`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix RL --output build/logic-interpreter-probes/batches/resource_lifecycle_003.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case load_logic_var_then_call_logic_draws --case overlay_picture_var_composes_extra_picture --case discard_picture_var_allows_reload_and_overlay --case discard_view_allows_reload_and_draw --case discard_view_var_allows_reload_and_draw`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TX --output build/logic-interpreter-probes/batches/text_input_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case display_message_then_ack_continues_to_draw --case display_message_var_then_ack_continues_to_draw --case display_message_configured_then_ack_continues_to_draw --case prompt_string_to_slot_accepts_typed_word --case prompt_number_to_var_accepts_digits`
- `python3 -B -m json.tool build/logic-interpreter-probes/batches/text_input_001.json`
- `magick build/logic-interpreter-probes/fixtures/prompt_string_to_slot_accepts_typed_word/qemu_capture.ppm build/logic-interpreter-probes/fixtures/prompt_string_to_slot_accepts_typed_word/qemu_capture.png`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TI --output build/logic-interpreter-probes/batches/text_input_prompt_string_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case prompt_string_to_slot_accepts_typed_word`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TN --output build/logic-interpreter-probes/batches/text_input_prompt_number_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case prompt_number_to_var_accepts_digits`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TX --output build/logic-interpreter-probes/batches/text_input_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case display_message_then_ack_continues_to_draw --case display_message_var_then_ack_continues_to_draw --case display_message_configured_then_ack_continues_to_draw --case prompt_number_to_var_accepts_digits`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix MS --output build/logic-interpreter-probes/batches/menu_sound_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case menu_setup_dispatch_smoke --case menu_flag_dispatch_smoke --case sound_load_stop_dispatch_smoke`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Extended `tools/qemu_snapshot.py` so each `SnapshotFixtureCase` can request
  `post_launch_keys` and `post_launch_wait`. Existing callers keep the default
  no-input behavior. `tools/logic_interpreter_probe.py` passes those fields
  through from each logic case to the shared snapshot runner.
- Extended `LogicInterpreterCase` and fixture generation to support additional
  synthetic picture resources and a separate `expected_picture_payload` for
  comparison. This lets one fixture load/overlay picture 1 while rendering the
  expected final picture state as picture 0 plus the overlay payload.
- Added resource lifecycle cases:
  - `load_logic_var_then_call_logic_draws` validates `0x15` followed by
    `0x16`.
  - `overlay_picture_var_composes_extra_picture` validates that `0x1c` can
    overlay an already-loaded picture resource. The first QEMU run,
    `resource_lifecycle_002`, mismatched only on the overlay pixels because
    `0x1c` updated logical picture state without a visible full-screen
    refresh. Adding `0x1a` after `0x1c` made the composed picture visible.
  - `discard_picture_var_allows_reload_and_overlay` validates a
    discard/reload/overlay path for `0x1b`.
  - `discard_view_allows_reload_and_draw` and
    `discard_view_var_allows_reload_and_draw` validate `0x20` and `0x99`
    before a reload with `0x1e`.
- Final lifecycle batch `resource_lifecycle_003` matched with 5 matches, 0
  mismatches, and 0 errors.
- Added message-window/input cases:
  - `display_message_then_ack_continues_to_draw` for `0x65`.
  - `display_message_var_then_ack_continues_to_draw` for `0x66`.
  - `display_message_configured_then_ack_continues_to_draw` for `0x97`.
  - `prompt_number_to_var_accepts_digits` for `0x76`, typing `42` and checking
    the destination variable through a conditional draw.
- Trial case `prompt_string_to_slot_accepts_typed_word` for `0x73` visibly
  displayed `WORD?` and accepted typed `look`, but the editor remained active
  after Enter in the QEMU capture. It was removed from the default
  compatibility set until the exact completion/event path is isolated.
- Final text/input batch `text_input_002` matched with 4 matches, 0 mismatches,
  and 0 errors.
- Added menu and sound smoke cases:
  - `menu_setup_dispatch_smoke` runs `0x9c`, `0x9d`, `0x9e`, `0xa0`, and
    `0x9f`, then draws.
  - `menu_flag_dispatch_smoke` sets flag `0x0e`, runs `0xa1`, then draws.
  - `sound_load_stop_dispatch_smoke` runs `0x62` for sound 1, then `0x64`,
    then draws.
- Batch `menu_sound_001` matched with 3 matches, 0 mismatches, and 0 errors.
  These are dispatch-smoke probes only; they do not claim full interactive menu
  selection, audio playback, or sound-completion flag semantics.
- Regenerated `docs/src/logic_opcode_evidence.md` so the new rows are marked
  as QEMU-validated or QEMU dispatch-smoke as appropriate.

## 2026-07-03: string editor, text UI, and diagnostics probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "0x0da9|0x73|prompt_string|text_ui|diagnostics_system" docs/src tools`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_0c20_10a0.bin bs=1 skip=3616 count=1152`
- `ndisasm -b 16 -o 0x0c20 build/cleanroom/slice_0c20_10a0.bin`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_4420_46c0.bin bs=1 skip=17952 count=672`
- `ndisasm -b 16 -o 0x4420 build/cleanroom/slice_4420_46c0.bin`
- `xxd -g 1 -s 0x1060 -l 0x20 build/cleanroom/AGI.decrypted.exe`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_qemu_snapshot`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix PS --output build/logic-interpreter-probes/batches/prompt_string_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case prompt_string_to_slot_returns_after_enter --case prompt_string_to_slot_stores_typed_word`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix PS --output build/logic-interpreter-probes/batches/prompt_string_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case prompt_string_to_slot_returns_after_enter --case prompt_string_to_slot_stores_typed_word`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix PS --output build/logic-interpreter-probes/batches/prompt_string_003.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case prompt_string_to_slot_returns_after_enter --case prompt_string_to_slot_stores_typed_word`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TU --output build/logic-interpreter-probes/batches/text_ui_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case display_formatted_message_then_ack_continues_to_draw --case display_formatted_message_var_then_ack_continues_to_draw --case display_message_configured_var_then_ack_continues_to_draw --case input_line_toggle_refresh_erase_dispatch_smoke --case text_rect_clear_dispatch_smoke --case close_text_window_state_dispatch_smoke`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TU --output build/logic-interpreter-probes/batches/text_ui_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case display_formatted_message_then_ack_continues_to_draw --case display_formatted_message_var_then_ack_continues_to_draw --case display_message_configured_var_then_ack_continues_to_draw --case input_line_toggle_refresh_erase_dispatch_smoke --case text_rect_clear_dispatch_smoke --case close_text_window_state_dispatch_smoke`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TC --output build/logic-interpreter-probes/batches/text_clear_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case text_rect_clear_dispatch_smoke --case close_text_window_state_dispatch_smoke`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TU --output build/logic-interpreter-probes/batches/text_ui_003.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case display_formatted_message_then_ack_continues_to_draw --case display_formatted_message_var_then_ack_continues_to_draw --case display_message_configured_var_then_ack_continues_to_draw --case input_line_toggle_refresh_erase_dispatch_smoke --case text_rect_clear_dispatch_smoke --case close_text_window_state_dispatch_smoke`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix DS --output build/logic-interpreter-probes/batches/diagnostics_system_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case pause_message_then_ack_continues_to_draw --case heap_status_then_ack_continues_to_draw --case interpreter_version_then_ack_continues_to_draw --case diagnostic_global_actions_dispatch_smoke`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Re-read action `0x73` around image `0x0c44` and the shared editor helper at
  image `0x0da9`. The handler clears fixed string slot
  `0x020d + slot * 0x28`, optionally positions the prompt with `0x2b0d`, shows
  the resolved message, calls the editor helper, then redraws or cleans up the
  prompt/status area.
- Named `code.input.edit_string` at image `0x0da9`. The helper clamps the
  requested length to `0x28`, copies the destination string into a local edit
  buffer, displays it, waits through `code.input.wait_event`, and dispatches
  key values through the table at image/data `0x0e64`.
- The observed key dispatch table bytes at file offset `0x1060` map `0x08` to
  one-character backspace, `0x03` and `0x18` to clear-current-input, `0x0d` to
  accept by zero-terminating and copying the local buffer back to the
  destination, and `0x1b` to cancel without copying.
- Re-read event helpers around image `0x4482..0x467f`. `0x45d7` blocks until
  the event normalizer returns neither `0x0000` nor `0xffff`; `0x4634` maps
  observed type-1 confirm/editor events `0x0101`/`0x0301` to Enter and
  `0x0201`/`0x0401` to Escape.
- Extended the shared QEMU snapshot runner to support a post-launch key delay,
  a wait between typed text and named keys, and a separate list of named QEMU
  `sendkey` names. This lets fixtures type literal text and then send `ret` as
  a distinct key event.
- Initial `prompt_string_001` and `prompt_string_002` runs showed the prompt
  text still visible in the comparison capture. The disassembly already showed
  Enter should accept; inspecting the output indicated that the interpreter had
  advanced, but the text-plane pixels remained over the later validation draw.
  Adding `0x1a` before the validation draw removed that false mismatch.
- Final batch `prompt_string_003` matched with 2 matches, 0 mismatches, and 0
  errors. It validates both return-after-Enter and copying typed `look` into the
  destination string slot for `0x73`.
- `text_ui_001` failed on the same visible text-overlay issue for formatted
  messages. Adding a full picture refresh before the validation draw fixed the
  first four cases in `text_ui_002`.
- The `text_rect_clear_dispatch_smoke` case initially mismatched because the
  fixture compared against the normal picture after intentionally clearing text
  rows. Adding a refresh before the validation draw made the probe test handler
  return instead of the permanent display-side clear.
- Final batch `text_ui_003` matched with 6 matches, 0 mismatches, and 0 errors.
  It validates `0x67`, `0x68`, and `0x98` as formatted/configured message
  paths, and dispatch-smokes `0x77`, `0x78`, `0x89`, `0x8a`, `0x69`, `0x9a`,
  and `0xa9`.
- Batch `diagnostics_system_001` matched with 4 matches, 0 mismatches, and 0
  errors. It validates message/ack/return behavior for `0x87`, `0x88`, and
  `0x8d`, and dispatch-smokes `0x83`, `0x84`, `0x8e`, `0xaa`, `0xab`,
  `0xac`, `0xad`, `0xa3`, and `0xa4`.
- Updated `tools/logic_opcode_evidence.py` and regenerated
  `docs/src/logic_opcode_evidence.md` with the new behavior and dispatch-smoke
  evidence rows.

## 2026-07-03: text/status configuration source pass and smoke probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `rg -n "0x6a|0x6b|0x6c|0x6d|0x6e|0x6f|0x70|0x71|0x74|0x79|0x77d5|0x78f0|0x3547|0x4c3d|0x38b4|status line|input prompt|map_key_event" docs/src tools tests`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_3400_3a00.bin bs=1 skip=13824 count=1536`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_7600_7b00.bin bs=1 skip=30720 count=1280`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_4c00_4d40.bin bs=1 skip=19968 count=320`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_0d60_0df0.bin bs=1 skip=3936 count=144`
- `ndisasm -b 16 -o 0x3400 build/cleanroom/slice_3400_3a00.bin`
- `ndisasm -b 16 -o 0x7600 build/cleanroom/slice_7600_7b00.bin`
- `ndisasm -b 16 -o 0x4c00 build/cleanroom/slice_4c00_4d40.bin`
- `ndisasm -b 16 -o 0x0d60 build/cleanroom/slice_0d60_0df0.bin`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_qemu_snapshot`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TS --output build/logic-interpreter-probes/batches/text_status_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case text_attribute_mode_dispatch_smoke --case screen_shake_dispatch_smoke --case input_prompt_config_dispatch_smoke --case status_line_show_hide_dispatch_smoke --case key_event_mapping_dispatch_smoke`
- `python3 -B -m json.tool build/logic-interpreter-probes/batches/text_status_001.json`
- `python3 -B tools/inspect_ppm.py build/logic-interpreter-probes/fixtures/input_prompt_config_dispatch_smoke/qemu_capture.ppm`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_qemu_snapshot`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TS --output build/logic-interpreter-probes/batches/text_status_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case text_attribute_mode_dispatch_smoke --case screen_shake_dispatch_smoke --case input_prompt_config_dispatch_smoke --case status_line_show_hide_dispatch_smoke --case key_event_mapping_dispatch_smoke`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Re-read status/input helpers around image `0x34bd..0x38d7`:
  - `code.text.redraw_status_line` at image `0x34bd` wraps a status redraw in
    text setup/cleanup helpers, tests word `[0x05d9]`, clears the configured
    status row through `0x2ba6`, positions output with `0x2b0d`, displays text
    through `0x2390`, and restores saved text attributes through `0x79c3`.
  - Action `0x70` at image `0x3547` sets word `[0x05d9] = 1` and calls the
    redraw helper.
  - Action `0x71` at image `0x355c` clears word `[0x05d9]` and clears the row
    from `[0x05db]`.
  - `code.input.show_prompt_marker` at image `0x37f7` and
    `code.input.erase_prompt_marker` at image `0x382e` gate on prompt marker
    byte `[0x05d7]` and marker-visible word `[0x0fa2]`.
  - Action `0x6c` at image `0x38b4` resolves a message and stores its first
    byte in `[0x05d7]`.
  - `code.input.redraw_input_line` at image `0x38d7` redraws the input-line
    area when word `[0x05d3]` is nonzero and display mode is not the special
    mode-2 path.
- Re-read text-attribute and status configuration handlers around image
  `0x76ca..0x7a7f`:
  - Action `0x6a` sets byte `[0x1757] = 1`, derives attributes through
    `0x77d5`, calls overlay entry `0x9803`, then clears a text rectangle.
  - Action `0x6b` calls helper `0x78cb`, which clears `[0x1757]`, recomputes
    attributes, calls overlay entry `0x9806`, redraws the status line, and
    redraws the input line.
  - Action `0x6d` calls `code.text.set_attribute_pair` (`0x77d5`), which
    stores derived values in `[0x05d1]`, `[0x05cd]`, and `[0x05cf]`.
  - Action `0x6e` reads a count byte and performs display-shake work through
    display-mode-specific helpers or direct CRT-controller writes.
  - Action `0x6f` stores operand 0 in `[0x05dd]`, operand 0 plus `0x15` in
    `[0x05df]`, operand 1 in `[0x05d5]`, operand 2 in `[0x05db]`, and derives
    display offset `[0x1379]` from operand 0.
  - Helpers `0x7989` and `0x79c3` save and restore up to five triples of text
    attribute globals in the table rooted at `0x1759`, with count word
    `[0x1777]`.
- Re-read action `0x79` at image `0x4c3d`: it combines operand 0 and operand 1
  into a little-endian key/event word, stores operand 2 as the mapped value, and
  inserts the pair into the first free four-byte slot in the table rooted at
  `0x0145`, scanning up to 39 slots.
- Re-read action `0x74` at image `0x0d70`: it copies up to `0x28` bytes from a
  pointer read from `DS:0x0c8f + operand1 * 2` into fixed string slot
  `0x020d + operand0 * 0x28`. The local SQ2 sampled table remains zero-filled,
  so this action was not promoted dynamically in this pass.
- Added five QEMU dispatch-smoke cases:
  - `text_attribute_mode_dispatch_smoke` for `0x6d`, `0x6a`, and `0x6b`.
  - `screen_shake_dispatch_smoke` for a one-count `0x6e`.
  - `input_prompt_config_dispatch_smoke` for `0x6c` and `0x6f`.
  - `status_line_show_hide_dispatch_smoke` for `0x70` and `0x71`.
  - `key_event_mapping_dispatch_smoke` for `0x79`.
- Batch `text_status_001` matched the first two cases, then mismatched
  `input_prompt_config_dispatch_smoke`. The mismatch bbox covered the
  validation sprite area, and the capture showed the interpreter had returned;
  the first `0x6f` operand value `1` changed display offset state enough that
  the local expected renderer no longer aligned with the captured sprite. This
  is useful behavior evidence for a later dedicated `0x6f` offset probe, but it
  was too broad for a dispatch-smoke fixture.
- Changed the smoke fixture to use first operand `0` for `0x6f`, preserving the
  handler dispatch while avoiding the non-default display offset.
- Final batch `text_status_002` matched with 5 matches, 0 mismatches, and 0
  errors.
- Updated symbolic labels for the status/input/text-attribute helpers and
  globals, promoted `0x6a..0x71` and `0x79` to QEMU dispatch-smoke evidence,
  and regenerated `docs/src/logic_opcode_evidence.md`.

## 2026-07-03: input offset, mapped-key, and string-table behavior probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "def compare_capture|expected_baseline_y|mismatch_bbox|0x1379|1379|set_input_line_config|key_event|0x79|map_key_event|input_prompt_config" tools docs/src tests`
- `python3 -B -m json.tool build/logic-interpreter-probes/batches/input_prompt_config_operand1_shift_demo.json`
- Local Python comparison of the recreated operand-1 capture against expected
  baselines `70..90`.
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_0900_0a40.bin bs=1 skip=2816 count=320`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_4520_45c0.bin bs=1 skip=18208 count=160`
- `ndisasm -b 16 -o 0x0900 build/cleanroom/slice_0900_0a40.bin`
- `ndisasm -b 16 -o 0x4520 build/cleanroom/slice_4520_45c0.bin`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_qemu_snapshot`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix IK --output build/logic-interpreter-probes/batches/input_key_behaviour_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_line_config_operand1_offsets_display_by_8 --case mapped_key_sets_status_byte`
- `xxd -g 1 -s 0x0c80 -l 0x80 SQ2/AGIDATA.OVL`
- `xxd -g 1 -s 0x0c80 -l 0x80 build/logic-interpreter-probes/fixtures/input_line_config_operand1_offsets_display_by_8/AGIDATA.OVL`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_qemu_snapshot`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix IK --output build/logic-interpreter-probes/batches/input_key_string_behaviour_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_line_config_operand1_offsets_display_by_8 --case mapped_key_sets_status_byte --case set_string_from_table_copies_patched_pointer`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Quantified the earlier `0x6f(1, 0, 22)` mismatch by comparing the recreated
  QEMU capture against expected baselines. The capture matched exactly at
  baseline `88`, while the script draw used baseline `80`. This confirms that
  in the observed display mode the first `0x6f` operand contributes an
  eight-logical-row visible offset, consistent with the static assignment
  `[0x1379] = arg0 << 3`.
- Added behavior case `input_line_config_operand1_offsets_display_by_8`, which
  runs `0x6f(1, 0, 22)`, refreshes with `0x1a`, draws at script baseline `80`,
  and expects the capture at baseline `88`. Batch `input_key_behaviour_001`
  matched this case.
- Re-read condition `0x0d` at image `0x09be` and event mapping helper `0x4566`.
  Condition `0x0d` calls `0x459e` directly and does not use the script mapping
  table. The top-level input helper path calls `0x4566`, and when a type-1
  event value matches a slot rooted at `0x0145`, helper `0x4566` changes the
  record type to `3` and replaces the value with the mapped value.
- The type-3 event path in the input helper writes byte
  `[0x1218 + mapped_value] = 1`. Condition `0x0c` reads exactly this byte
  range, making it a clean observation point for a mapped-key behavior probe.
- Added behavior case `mapped_key_sets_status_byte`: one-time logic installs
  `0x79('x', 0, 7)`, QEMU sends key `x`, and per-cycle logic draws only when
  condition `0x0c 7` is true. Batch `input_key_behaviour_001` matched this
  case, validating both action `0x79` and condition `0x0c` dynamically.
- Inspected the original `SQ2/AGIDATA.OVL` bytes at `0x0c80..0x0cff`; the
  pointer-table area around `0x0c8f` is zero-filled through `0x0cd2`, followed
  by static text. The same layout appears in generated fixtures.
- Added fixture-local `AGIDATA.OVL` patch support to
  `tools/logic_interpreter_probe.py`.
- Added behavior case `set_string_from_table_copies_patched_pointer`, which
  patches only the generated fixture: table entry 0 at `0x0c8f` points to
  `0x0cc0`, and `0x0cc0` contains `look\0`. The logic runs `0x74` into string
  slot 0, fills slot 1 from normal message text `look`, then draws only if
  condition `0x0f` finds the two slots equal. Batch
  `input_key_string_behaviour_001` matched this case.
- Promoted action `0x6f`, action `0x74`, action `0x79`, and condition `0x0c`
  to QEMU behavior evidence in `tools/logic_opcode_evidence.py`, then
  regenerated `docs/src/logic_opcode_evidence.md`.

## 2026-07-03: inventory selection source pass and QEMU probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "inventory|show.obj|0x7c|post_launch|post_launch_key|dos_key" tools/logic_interpreter_probe.py tools/qemu_snapshot.py tests/test_logic_interpreter_probe.py docs/src/logic_bytecode.md docs/src/symbolic_labels.md`
- `sed -n '1,220p' tools/qemu_snapshot.py`
- `sed -n '960,1085p' tools/logic_interpreter_probe.py`
- `sed -n '970,1030p' docs/src/logic_bytecode.md`
- `ndisasm -b 16 -o 0x3180 build/cleanroom/slice_3180_33c0.bin`
- `ndisasm -b 16 -o 0x9000 build/cleanroom/slice_9000_9480.bin`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_qemu_snapshot`
- Initial failed run: `python3 -B tools/logic_interpreter_probe.py --dos-prefix IN --output build/logic-interpreter-probes/batches/inventory_selection_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case inventory_selection_enter_sets_var22 --case inventory_selection_escape_sets_ff --case inventory_selection_noninteractive_ack_returns`
- `python3 -B -m json.tool build/logic-interpreter-probes/batches/inventory_selection_001.json`
- `magick build/logic-interpreter-probes/fixtures/inventory_selection_enter_sets_var22/qemu_capture.ppm build/logic-interpreter-probes/fixtures/inventory_selection_enter_sets_var22/qemu_capture.png`
- Corrected run: `python3 -B tools/logic_interpreter_probe.py --dos-prefix IN --output build/logic-interpreter-probes/batches/inventory_selection_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case inventory_selection_enter_sets_var19 --case inventory_selection_escape_sets_var19_ff --case inventory_selection_noninteractive_ack_returns`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- The inventory handler at `0x31d8` enters a text/list mode, calls a helper now
  labeled `code.inventory.build_selection_list`, restores text state, and
  returns. The list-building helper scans 3-byte entries rooted at
  `data.inventory.table_root` and includes only entries whose marker byte is
  `0xff`.
- Each displayed carried item row is an 8-byte stack-local record containing
  the original table index, item-name pointer, row, and column. The first item
  is drawn in the left column; the next item is drawn in the right column after
  computing `0x27 - strlen(name)`.
- If no entries are carried, the helper inserts one fallback row pointing at the
  fixed "nothing" text.
- Flag 13 controls interactivity. When flag 13 is clear, the handler displays
  the noninteractive prompt, waits through the blocking input helper, and
  returns without storing a selection result. When flag 13 is set, it waits for
  events, uses the normalizer, handles type-1 Enter/Escape, and handles type-2
  movement events through a selection-move/redraw helper.
- Enter stores the selected row's original table index to absolute byte
  `DS:0x0022`; Escape stores `0xff` to the same byte. Because the byte-variable
  array starts at `DS:0x0009`, this storage is exposed to logic bytecode as
  variable `0x19`.
- The first QEMU probe incorrectly checked variable `0x22`. It returned after
  Enter but did not draw the validation sprite, producing a mismatch over the
  sprite area. This was retained as evidence that the source address needed to
  be translated through the byte-variable base.
- Corrected QEMU batch `inventory_selection_001` matched all three cases:
  `inventory_selection_enter_sets_var19`, `inventory_selection_escape_sets_var19_ff`,
  and `inventory_selection_noninteractive_ack_returns`.
- The menu source pass assigned stable labels for heading allocation, item
  allocation, setup finalization, enable/disable-by-id, and the interactive
  menu path. The observed source path enqueues type-3 events with selected menu
  item ids for enabled items, but deterministic menu interaction probes are
  still pending.

## 2026-07-03: menu, view-resource, system, file/log, and sound follow-up probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_93d0_9900.bin bs=1 skip=38352 count=1328`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_5e80_60e0.bin bs=1 skip=24704 count=608`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_2470_28f0.bin bs=1 skip=9840 count=1152`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_8280_8400.bin bs=1 skip=33920 count=384`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_51d0_5280.bin bs=1 skip=21456 count=176`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_8c80_8df0.bin bs=1 skip=36480 count=368`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_0e70_0ed0.bin bs=1 skip=4208 count=96`
- `dd if=build/cleanroom/AGI.decrypted.exe of=build/cleanroom/slice_6130_61d0.bin bs=1 skip=25392 count=160`
- `ndisasm -b 16 -o 0x93d0 build/cleanroom/slice_93d0_9900.bin`
- `ndisasm -b 16 -o 0x5e80 build/cleanroom/slice_5e80_60e0.bin`
- `ndisasm -b 16 -o 0x2470 build/cleanroom/slice_2470_28f0.bin`
- `ndisasm -b 16 -o 0x8280 build/cleanroom/slice_8280_8400.bin`
- `ndisasm -b 16 -o 0x51d0 build/cleanroom/slice_51d0_5280.bin`
- `ndisasm -b 16 -o 0x8c80 build/cleanroom/slice_8c80_8df0.bin`
- `ndisasm -b 16 -o 0x0e70 build/cleanroom/slice_0e70_0ed0.bin`
- `ndisasm -b 16 -o 0x6130 build/cleanroom/slice_6130_61d0.bin`
- `rizin -q -c "/x 0x221d" -c q build/cleanroom/AGI.decrypted.exe`
- `rizin -q -c "/x 0x833e221d" -c q build/cleanroom/AGI.decrypted.exe`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_qemu_snapshot`
- Initial menu run: `python3 -B tools/logic_interpreter_probe.py --dos-prefix MN --output build/logic-interpreter-probes/batches/menu_interaction_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case menu_interactive_enter_sets_status_byte`
- Final menu run: same command after adding a picture refresh before the validation draw.
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix VW --output build/logic-interpreter-probes/batches/view_resource_display_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case view_resource_display_immediate_returns --case view_resource_display_var_returns`
- Initial system run: `python3 -B tools/logic_interpreter_probe.py --dos-prefix SY --output build/logic-interpreter-probes/batches/system_dialog_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case signature_check_matching_message_returns --case restart_confirm_escape_continues_to_draw --case confirm_restart_like_escape_continues_to_draw --case joystick_calibration_no_joystick_returns --case display_mode_toggle_guarded_noop_continues --case trace_window_config_enable_dispatch_smoke`
- Final system run: same command after narrowing the trace case to the flag-clear gated path.
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix FL --output build/logic-interpreter-probes/batches/file_log_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case log_file_append_dispatch_smoke --case save_game_escape_continues_to_draw --case restore_game_escape_continues_to_draw`
- Initial sound runs for `sound_start_clears_completion_flag` and then
  `sound_start_stop_dispatch_smoke`, both without a preceding `0x62` load.
- Final sound run: `python3 -B tools/logic_interpreter_probe.py --dos-prefix SN --output build/logic-interpreter-probes/batches/sound_completion_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case sound_start_stop_dispatch_smoke`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Corrected the slice workflow reminder: focused slices use the documented image
  offset plus the executable file-header adjustment (`+0x200`) when reading
  bytes from `build/cleanroom/AGI.decrypted.exe`.
- `code.menu.interact` (`0x93d1`) draws the menu, waits through
  `code.input.wait_event`, normalizes the event, and calls `0x46e8`. For a
  type-1 Enter event on an enabled item, it calls `0x44a9(3, item_id)`, cleans
  up the menu display, clears word `[0x1d22]`, and returns.
- The only observed direct references to menu request word `[0x1d22]` are the
  setter in `0xa1`, the input/event caller check around image `0x338b`, and the
  cleanup clear inside `code.menu.interact`.
- Added `menu_interactive_enter_sets_status_byte`: it creates a one-item menu
  with item id 7, sets flag `0x0e`, runs `0xa1`, sends Enter, and draws only
  when condition `0x0c 7` observes the enqueued type-3 menu event. The first run
  mismatched only because the menu text strip remained visible; adding `0x1a`
  before the validation draw produced a 1/1 QEMU match.
- Re-read the shared view-resource display helper `0x5edb`. It loads the view
  resource with temporary `[0x0f18] = 1`, builds a temporary object-like record,
  optionally renders/caches a preview if memory allows, displays text derived
  from the view resource, restores any preview rectangle, and discards the
  resource when it was not already cached.
- Added `view_resource_display_immediate_returns` and
  `view_resource_display_var_returns`; QEMU batch `view_resource_display_001`
  matched 2/2.
- Added system/dialog cases for signature acceptance (`0x8f`), restart
  confirmation Escape cancellation (`0x80`), `0x86(0)` confirmation Escape
  cancellation, no-joystick calibration return (`0x8b`), display-mode guarded
  no-op (`0x8c` with variable 0 clear), and trace configuration/flag-clear
  gated `0x95`. QEMU batch `system_dialog_001` matched 6/6 after narrowing the
  trace case.
- The initial enabled trace case drew a visible trace box and mismatched the
  normal graphics comparison. This confirms the source-backed enabled drawing
  path but is not a stable sprite-comparison fixture.
- Re-read `0x90` and helper `0x833f`: the handler opens or creates `logfile`,
  seeks to the end, appends the room/input/message text, closes the handle, and
  returns. QEMU batch `file_log_001` matched `log_file_append_dispatch_smoke`,
  `save_game_escape_continues_to_draw`, and
  `restore_game_escape_continues_to_draw`.
- Re-read `0x63`: it stops prior sound, stores completion flag word `[0x126a]`,
  clears that flag, locates the sound resource, then starts playback. Probes
  that ran `0x63` without first loading sound 1 did not reach the validation
  draw. Adding `0x62(1)` before `0x63(1,77)` and then `0x64` produced a 1/1
  match in `sound_completion_001`.
- Promoted the newly matched opcodes in `tools/logic_opcode_evidence.py` and
  regenerated `docs/src/logic_opcode_evidence.md`. Trace/log/sound are marked
  according to their current evidence scope rather than overclaiming deeper
  side effects.

## 2026-07-03: priority, diagnostics, menu edges, sound flag, and log file follow-up

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x175c -e 0x195c build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x731b -e 0x751b build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x72b5 -e 0x74b5 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x828f -e 0x848f build/cleanroom/AGI.decrypted.exe`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_qemu_snapshot`
- Attempted room-switch batch:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix RS --output build/logic-interpreter-probes/batches/room_priority_diag_sound_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case switch_room_immediate_sets_room_and_previous_room --case switch_room_var_sets_room_and_previous_room --case priority_screen_enter_returns --case object_diagnostics_var_enter_returns --case sound_stop_sets_completion_flag`
- Corrected but still-failing room attempts using target-room-only and
  target-logic-draw assertions, also under output
  `build/logic-interpreter-probes/batches/room_priority_diag_sound_001.json`.
- Stable priority/diagnostics/sound run:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix PS --output build/logic-interpreter-probes/batches/priority_diag_sound_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case priority_screen_enter_returns --case object_diagnostics_var_enter_returns --case sound_stop_sets_completion_flag`
- Initial menu edge run:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix ME --output build/logic-interpreter-probes/batches/menu_edges_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case menu_escape_exits_without_status_byte --case menu_disabled_item_enter_does_not_set_status_byte --case menu_enable_after_disable_allows_enter_status_byte --case menu_down_arrow_selects_second_item_status_byte`
- Focused down-arrow retry:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix MD --output build/logic-interpreter-probes/batches/menu_down_arrow_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case menu_down_arrow_selects_second_item_status_byte`
- Stable menu edge run:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix ME --output build/logic-interpreter-probes/batches/menu_edges_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case menu_escape_exits_without_status_byte --case menu_disabled_item_enter_does_not_set_status_byte --case menu_enable_after_disable_allows_enter_status_byte`
- Log file run and extraction:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix LF --output build/logic-interpreter-probes/batches/log_file_contents_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case log_file_append_dispatch_smoke`
- `qemu-img convert -f qcow2 -O raw build/logic-interpreter-probes/snapshot/logic_interpreter.qcow2 build/logic-interpreter-probes/snapshot/logic_interpreter_after_log.raw`
- `mdir -i build/logic-interpreter-probes/snapshot/logic_interpreter_after_log.raw@@32256 ::/LF00000`
- `mcopy -o -i build/logic-interpreter-probes/snapshot/logic_interpreter_after_log.raw@@32256 ::/LF00000/LOGFILE build/logic-interpreter-probes/fixtures/log_file_append_dispatch_smoke/logfile_from_qemu.txt`
- `xxd -g 1 build/logic-interpreter-probes/fixtures/log_file_append_dispatch_smoke/logfile_from_qemu.txt`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Reconfirmed `0x1792` room-switch helper from disassembly. It stops sound,
  restores heap/list state, clears active/update state for each object record,
  stores the target in byte variable 0, copies the previous room byte into byte
  variable 1, clears selected flags/bytes, loads the destination logic, handles
  entry-boundary placement from byte variable 2, sets flag 5, and refreshes
  display/input state.
- Three QEMU fixture shapes for `0x12`/`0x13` were attempted and rejected as
  reusable evidence: direct `var1 == 0` previous-room assertion, target-room
  `var0` assertion, and target-logic draw after making the target logic
  self-contained. These actions remain source-backed until a fuller synthetic
  room-cycle fixture models the logic-0/current-room relationship.
- Reconfirmed `0x1d` at image `0x731b`: it sets word `[0x1755]`, calls full
  refresh `0x5546`, waits for an event, refreshes again, then clears
  `[0x1755]`. QEMU case `priority_screen_enter_returns` matched.
- Reconfirmed `0x85` at image `0x72b5`: it reads an object index from a
  variable operand, gathers object fields, formats them through template
  `0x1713`, and displays the result. QEMU case
  `object_diagnostics_var_enter_returns` matched.
- QEMU case `sound_stop_sets_completion_flag` matched: after `0x62(1)` and
  `0x63(1,77)`, action `0x64` sets flag 77 before the validation draw. This
  validates the configured completion-flag effect of the stop helper, while
  exact audio output and asynchronous playback lifetime remain source-backed.
- QEMU batch `priority_diag_sound_001` matched 3/3.
- QEMU batch `menu_edges_002` matched 3/3. Escape exits without setting status
  byte 7. Enter on disabled item 7 does not set status byte 7 before Escape
  exits. Disabling and then re-enabling item 7 restores Enter selection and
  status byte 7.
- The attempted down-arrow menu navigation case did not reach status byte 8
  even after increasing the delay between Down and Enter. It remains an
  attempted-but-not-promoted QEMU fixture; arrow navigation is still
  source-backed from the `code.menu.interact` event dispatch table.
- `log_file_contents_001` matched visually. Converting the post-run qcow2 image
  to raw and extracting `LF00000\LOGFILE` showed bytes
  `0a 0a 52 6f 6f 6d 20 30 0a 49 6e 70 75 74 20 6c 69 6e 65 3a 20 0a 4c 4f 47`,
  which decodes as two leading newlines, `Room 0`, `Input line: `, and `LOG`.
- Promoted `0x1d`, `0x64`, `0x85`, `0x90`, and the tested `0x9c..0xa0` menu
  setup/toggle paths in the opcode evidence generator, regenerated
  `logic_opcode_evidence.md`, and updated symbolic labels for the newly touched
  routines/globals.

## 2026-07-03: room-switch re-entry and menu-direction source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x175c -e 0x195c build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x0150 -e 0x0350 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x4529 -e 0x4729 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x46e8 -e 0x48e8 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x93d1 -e 0x95d1 build/cleanroom/AGI.decrypted.exe`
- `xxd -s 0x16b3 -l 0x60 -g 2 SQ2/AGIDATA.OVL`
- `xxd -s 0x0145 -l 0x80 -g 2 SQ2/AGIDATA.OVL`
- `ndisasm -b 16 -o 0x10d0 -e 0x12d0 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x293c -e 0x2b3c build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x12ae -e 0x14ae build/cleanroom/AGI.decrypted.exe`
- `python3 -B -m unittest tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_base_cases_cover_core_control_flow`
- Attempted room re-entry batch:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix RV --output build/logic-interpreter-probes/batches/room_reentry_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case switch_room_immediate_sets_new_room_flag --case switch_room_var_sets_new_room_flag`
- Attempted corrected room re-entry batch with `0x92` before `0x12`/`0x13`:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix RV --output build/logic-interpreter-probes/batches/room_reentry_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case switch_room_immediate_sets_new_room_flag --case switch_room_var_sets_new_room_flag`
- Non-stopping room retry:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix RV --output build/logic-interpreter-probes/batches/room_reentry_003.json --boot-wait 5 --draw-wait 8 --case switch_room_immediate_sets_new_room_flag --case switch_room_var_sets_new_room_flag`
- Attempted down-arrow key-map probe:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix DK --output build/logic-interpreter-probes/batches/down_key_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case mapped_down_arrow_sets_status_byte`

Documented result:

- Re-read `code.engine.main_cycle` (`0x0150`). When `code.logic.call_logic(0)`
  returns zero, the loop clears selected variables/flags and immediately calls
  logic 0 again. It does not run the frame-timer branch until the logic call
  returns nonzero.
- Re-read `code.logic.interpret_main` (`0x293c`). It starts execution at the
  current logic record's resume pointer field `[record+0x06]`. Action `0x00`
  returns the current `SI`, and an action handler that returns zero stops the
  interpreter with `AX = 0`.
- Re-read `code.logic.call_logic` (`0x12ae`). It saves the old current-logic
  record, locates or loads the requested logic, calls `code.logic.interpret_main`,
  frees a transiently loaded record when needed, restores the old current record,
  and returns the interpreter result.
- Re-read `0x91`/`0x92`: `0x91` writes the current bytecode pointer to
  `[current_logic+0x06]`; `0x92` restores `[current_logic+0x06]` from the entry
  pointer `[current_logic+0x04]`.
- A new synthetic room-switch fixture attempted to use a private init flag and
  flag 5 as the validation condition after `0x12`/`0x13`. It did not reach the
  validation draw. Adding `0x92` before the room-switch action also did not
  reach the draw. The failing cases were removed from the reusable probe list;
  `0x12`/`0x13` remain source-backed.
- Re-read input/event path `0x4529..0x46e8`. Helper `0x467f` drains BIOS key
  events, maps raw key words through table `0x16b3` via helper `0x46b6`, and
  enqueues type-2 movement events through `code.input.enqueue_event` (`0x44a9`).
  The observed table maps `0x4800`, `0x4900`, `0x4d00`, `0x5100`, `0x5000`,
  `0x4f00`, `0x4b00`, and `0x4700` to movement codes `1..8`; code
  `0x5000 -> 5` is the source-backed down-arrow candidate.
- Re-read `code.menu.interact` (`0x93d1`). Type-1 Enter/Escape are handled
  separately; type-2 movement values dispatch through the table at `0x9517`.
  In that table, movement value 5 enters the branch at `0x94da`, which advances
  to the next item in the current menu's item list.
- A QEMU probe that mapped raw key word `0x5000` through action `0x79` and sent
  monitor key `down` did not set the requested status byte. This is treated as
  an input-instrumentation gap rather than a semantic result; the down-arrow
  source table is still source-backed, not QEMU-validated.
- Added symbolic labels for `code.logic.save_resume_ip_action`,
  `code.logic.restore_entry_ip_action`, `code.input.enqueue_event`, and
  `data.input.menu_direction_event_map`.

## 2026-07-03: real SQ2 logic-0 room dispatch pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/disassemble_logic.py 0`
- `python3 -B tools/disassemble_logic.py 0 | rg "action (12|13|14|15|16|17|91|92)"`
- `python3 -B tools/disassemble_logic.py 1 2 3 4`
- `python3 -B tools/disassemble_logic.py 1 2 3 4 5 6 7 8 9 10 | rg -n "^logic|^0000: if|cond 07 flag_set\\(#5\\)|then_start|action 00 end|call_logic_var\\(v0\\)|switch_room_like"`
- `python3 -B tools/disassemble_logic.py 99 100 101 103 104 105 | rg -n "^logic|code_len|switch_room_like|call_logic|call_logic_var|flag_set\\(#5\\)|save_logic_resume|restore_logic_entry| action 00 end"`
- `python3 -B -m unittest tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_base_cases_cover_core_control_flow`
- Attempted logic-0-shaped room dispatch batch:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix RD --output build/logic-interpreter-probes/batches/room_dispatch_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case switch_room_immediate_then_logic0_calls_current_room --case switch_room_var_then_logic0_calls_current_room`
- `xxd -g 1 -l 12 build/logic-interpreter-probes/fixtures/switch_room_immediate_then_logic0_calls_current_room/LOGDIR`
- `xxd -g 1 -s 0 -l 120 build/logic-interpreter-probes/fixtures/switch_room_immediate_then_logic0_calls_current_room/VOL.3`

Documented result:

- SQ2 logic 0 is the global per-cycle script. Its early blocks handle boot/menu
  setup, global status/menu/input handling, and special global transitions. The
  room dispatch point is logic bytecode offset `0x053e`, where it executes
  action `0x17` (`call_logic_var(v0)`). This calls the logic resource selected
  by byte variable 0.
- Room logics sampled from resources 1 through 10 begin with an `if flag 5`
  block. Those blocks perform room-entry setup: load views/sounds/pictures,
  prepare the picture, configure objects and ego, show the picture, and then
  end or fall through into per-cycle room behavior. Later blocks in those room
  logics handle room-local events and may call `switch_room_like`.
- Script variables now have clearer room roles:
  - byte variable 0 at `DS:0x0009` is the current room;
  - byte variable 1 at `DS:0x000a` is the previous room;
  - byte variable 2 at `DS:0x000b` is the room-entry boundary selector consumed
    and cleared by `code.room.switch_state`.
- Built a new synthetic fixture that more closely copied the SQ2 pattern:
  logic 0 switched rooms once, then used `call_logic_var(v0)` to invoke a
  self-contained target room logic. The QEMU batch still mismatched with the
  same blank-screen signature as earlier room probes. The fixture's `LOGDIR`
  and `VOL.3` bytes were inspected and showed the extra logic resource was
  patched at the expected directory offset, so this failure is not explained by
  a missing target logic resource.
- Removed the failed synthetic room-dispatch cases from the reusable probe
  registry. The source model is stronger, but `0x12`/`0x13` remain
  source-backed until a fixture can reproduce the full runtime room lifecycle.

## 2026-07-03: room-switch re-entry QEMU validation

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "room|switch_room|call_logic_var|restore_logic|save_resume|logic0|case|def .*logic|class|Fixture|extra_logic" tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py docs/src/compatibility_testing.md docs/src/clean_room_executable_notes.md`
- `sed -n '1,260p' tools/logic_interpreter_probe.py`
- `sed -n '240,620p' tools/logic_interpreter_probe.py`
- `sed -n '620,980p' tools/logic_interpreter_probe.py`
- `sed -n '980,1360p' tools/logic_interpreter_probe.py`
- `sed -n '1360,1760p' tools/logic_interpreter_probe.py`
- `sed -n '1,260p' tests/test_logic_interpreter_probe.py`
- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- First attempted run, rejected because this harness does not expose a bare
  `--snapshot` flag:
  `python3 -B tools/logic_interpreter_probe.py --snapshot --case switch_room_reentry_dispatches_current_room --case switch_room_v_reentry_dispatches_current_room --dos-prefix RS --output build/logic-interpreter-probes/batches/room_switch_reentry_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- Successful QEMU run:
  `python3 -B tools/logic_interpreter_probe.py --case switch_room_reentry_dispatches_current_room --case switch_room_v_reentry_dispatches_current_room --dos-prefix RS --output build/logic-interpreter-probes/batches/room_switch_reentry_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `python3 -B -m unittest discover -s tests`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Added two reusable logic-interpreter probe cases:
  `switch_room_reentry_dispatches_current_room` for action `0x12`, and
  `switch_room_v_reentry_dispatches_current_room` for action `0x13`.
- The fixture shape is deliberately source-like. Logic 0 sets a private init
  flag before the switch action. The switch action returns zero, so the current
  interpreter invocation aborts and `code.engine.main_cycle` immediately calls
  logic 0 again. On the second pass, logic 0 skips the switch and calls
  `call_logic_var(v0)`. The destination room logic checks flag 5 and performs
  its own picture/view load and validation draw.
- QEMU `room_switch_reentry_001` matched 2/2 with 0 mismatches. This promotes
  the visible room-switch re-entry/current-room dispatch shape from
  source-backed to QEMU-validated for both immediate and variable-selected room
  operands.
- The earlier failed room-switch fixtures remain useful negative evidence about
  fixture shape. A validation draw after `0x12`/`0x13`, or a destination logic
  that relies on pre-switch picture/view state, does not model the original
  runtime lifecycle.
- Full local compatibility suite passed after adding the cases:
  `Ran 99 tests in 18.114s, OK`.
- Regenerated `docs/src/logic_opcode_evidence.md`; action rows `0x12` and
  `0x13` now cite the matched room-switch re-entry probes. Broader internal
  effects of helper `0x1792`, including object/resource reset, previous-room
  update, entry-boundary placement, and resource-event recording, remain
  source-backed unless separately probed.
