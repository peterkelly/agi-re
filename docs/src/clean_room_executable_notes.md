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
  resets room caches through `0x10d0`, sets object-boundary word `[0x0139]`,
  resets horizon-like word `[0x012d]` to `0x24`, updates current/previous room
  byte variables, loads the destination logic, reloads trace logic `[0x1d12]`
  when configured, consumes byte variable 2 as the entry-boundary selector,
  sets flag 5, refreshes display/status/input state, and returns zero. The
  exact cache behavior was refined later: `0x10d0` preserves the first logic
  cache record while clearing view, sound, and picture cache roots.
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

## 2026-07-03: room entry-boundary selector QEMU validation

Commands run from `/Users/peter/ai/agi/reverse`:

- Oversized first disassembly attempt, useful for confirming the helper but too
  broad for citation:
  `ndisasm -b 16 -o 0x1792 -e 0x1992 build/cleanroom/AGI.decrypted.exe`
- Focused corrected dump of room-switch helper `0x1792`:
  `ndisasm -b 16 -o 0x1792 -e 0x1992 build/cleanroom/AGI.decrypted.exe | sed -n '1,90p'`
- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- First attempted boundary batch:
  `python3 -B tools/logic_interpreter_probe.py --case switch_room_boundary_1_sets_object0_bottom_y --case switch_room_boundary_2_sets_object0_left_x --case switch_room_boundary_3_sets_object0_top_y --case switch_room_boundary_4_sets_object0_right_x --dos-prefix RB --output build/logic-interpreter-probes/batches/room_boundary_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `sed -n '1,220p' build/logic-interpreter-probes/batches/room_boundary_001.json`
- `python3 -B tools/inspect_ppm.py build/logic-interpreter-probes/fixtures/switch_room_boundary_1_sets_object0_bottom_y/qemu_capture.ppm`
- Generated diagnostic object-0 getter case under
  `build/logic-interpreter-probes/diagnostics/object0_getter.json`.
- Diagnostic getter run:
  `python3 -B tools/logic_interpreter_probe.py --cases build/logic-interpreter-probes/diagnostics/object0_getter.json --dos-prefix DG --output build/logic-interpreter-probes/batches/diagnostic_object0_getter_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- Generated diagnostic marker-map case under
  `build/logic-interpreter-probes/diagnostics/boundary1_marker_map.json`.
- Diagnostic marker-map run:
  `python3 -B tools/logic_interpreter_probe.py --cases build/logic-interpreter-probes/diagnostics/boundary1_marker_map.json --dos-prefix DM --output build/logic-interpreter-probes/batches/diagnostic_boundary1_marker_map_001.json --boot-wait 5 --draw-wait 8`
- Corrected boundary batch:
  `python3 -B tools/logic_interpreter_probe.py --case switch_room_boundary_1_sets_object0_bottom_y --case switch_room_boundary_2_sets_object0_left_x --case switch_room_boundary_3_sets_object0_top_y --case switch_room_boundary_4_sets_object0_right_x --dos-prefix RB --output build/logic-interpreter-probes/batches/room_boundary_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Re-read helper `0x1792`: after loading the destination logic, it reads byte
  variable 2 at `DS:0x000b`, dispatches selector values 1 through 4 through a
  small jump table, writes object 0 fields, clears `DS:0x000b`, sets flag 5,
  and refreshes display/input state.
- Added four reusable logic-interpreter probe cases:
  `switch_room_boundary_1_sets_object0_bottom_y`,
  `switch_room_boundary_2_sets_object0_left_x`,
  `switch_room_boundary_3_sets_object0_top_y`, and
  `switch_room_boundary_4_sets_object0_right_x`.
- The first QEMU batch `room_boundary_001` mismatched on the first case with an
  all-white capture. A diagnostic case proved action `0x27` can read object 0
  fields after ordinary setup. The actual fixture issue was pre-switch setup:
  object 0 was being bound to view 11 without first loading view 11, so the
  fixture did not reach the intended room-switch path.
- After changing the pre-switch setup to load view 11 before binding object 0,
  QEMU batch `room_boundary_002` matched 4/4 with 0 mismatches.
- The matched cases validate bytecode-visible entry-boundary behavior for
  action `0x12`: selector 1 sets object 0 Y to `0xa7`; selector 2 sets object 0
  X to `0`; selector 3 sets object 0 Y to `0x25`; selector 4 sets object 0 X to
  `0xa0 - object_width`. In the fixture, view 11 frame 0 has width 20, so
  selector 4 yields X `140`. All four selectors clear byte variable 2.
- Regenerated `docs/src/logic_opcode_evidence.md`; action row `0x12` now cites
  both the re-entry fixture and the boundary selector cases.

## 2026-07-03: room current/previous variable QEMU validation

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "room_reentry_logic0_code|room_boundary_logic0_code|room_switch_reentry_case|room_boundary_case|switch_room_boundary|switch_room_reentry" tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py docs/src/current_status.md docs/src/logic_bytecode.md docs/src/compatibility_testing.md`
- `sed -n '240,380p' tools/logic_interpreter_probe.py`
- `sed -n '780,850p' tools/logic_interpreter_probe.py`
- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- `python3 -B -m py_compile tools/logic_interpreter_probe.py`
- QEMU validation:
  `python3 -B tools/logic_interpreter_probe.py --case switch_room_sets_current_previous_and_clears_boundary --case switch_room_v_sets_current_previous_and_clears_boundary --dos-prefix RP --output build/logic-interpreter-probes/batches/room_previous_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Added two reusable logic-interpreter probe cases:
  `switch_room_sets_current_previous_and_clears_boundary` for action `0x12`,
  and `switch_room_v_sets_current_previous_and_clears_boundary` for action
  `0x13`.
- Each fixture writes a synthetic old room number into byte variable 0 before
  switching to room 1 and writes invalid boundary selector 7 into byte variable
  2. The switch helper should copy old `v0` into `v1`, write destination room
  1 into `v0`, and clear `v2` even though selector 7 is not a placement case.
- The destination room logic validates these bytes with normal logic
  conditions before drawing a validation sprite.
- QEMU batch `room_previous_001` matched 2/2 with 0 mismatches. This validates
  the byte-variable current/previous-room update for both immediate and
  variable-selected room-switch actions.
- Regenerated `docs/src/logic_opcode_evidence.md`; action rows `0x12` and
  `0x13` now cite the previous-room variable probes in addition to the existing
  room re-entry evidence.

## 2026-07-03: variable-room entry-boundary selector QEMU validation

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '240,390p' tools/logic_interpreter_probe.py`
- `sed -n '780,865p' tools/logic_interpreter_probe.py`
- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- `python3 -B -m py_compile tools/logic_interpreter_probe.py`
- QEMU validation:
  `python3 -B tools/logic_interpreter_probe.py --case switch_room_v_boundary_1_sets_object0_bottom_y --case switch_room_v_boundary_2_sets_object0_left_x --case switch_room_v_boundary_3_sets_object0_top_y --case switch_room_v_boundary_4_sets_object0_right_x --dos-prefix VB --output build/logic-interpreter-probes/batches/room_boundary_var_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Parameterized `room_boundary_case` so it can use either the immediate
  `0x12` action or a caller-supplied variable-selected `0x13` action.
- Added four reusable logic-interpreter probe cases:
  `switch_room_v_boundary_1_sets_object0_bottom_y`,
  `switch_room_v_boundary_2_sets_object0_left_x`,
  `switch_room_v_boundary_3_sets_object0_top_y`, and
  `switch_room_v_boundary_4_sets_object0_right_x`.
- The variable-selected fixtures set variable 10 to destination room 1, set
  byte variable 2 to selector 1 through 4, then execute `0x13(v10)`. The
  destination room logic reads object 0 with action `0x27` and validates the
  expected position plus cleared byte variable 2 before drawing.
- QEMU batch `room_boundary_var_001` matched 4/4 with 0 mismatches. This
  confirms that the variable-selected room-switch action shares the same
  bytecode-visible entry-boundary side effects as the immediate action:
  selector 1 sets object 0 Y to `0xa7`, selector 2 sets object 0 X to `0`,
  selector 3 sets object 0 Y to `0x25`, selector 4 sets object 0 X to
  `0xa0 - object_width`, and all four clear `v2`.
- Regenerated `docs/src/logic_opcode_evidence.md`; action row `0x13` now cites
  the variable-room boundary selector cases.

## 2026-07-03: room-switch persistent-object reset QEMU validation

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "expected_extra_sprites|setup_object_for_view11|activate|clear_all_object_bits|compose_frame_on_picture|extra_sprites|room_boundary_case|previous_room" tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py docs/src/logic_bytecode.md`
- `sed -n '390,470p' tools/logic_interpreter_probe.py`
- `sed -n '1810,1828p' tools/logic_interpreter_probe.py`
- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- `python3 -B -m py_compile tools/logic_interpreter_probe.py`
- QEMU validation:
  `python3 -B tools/logic_interpreter_probe.py --case switch_room_removes_preexisting_persistent_object --case switch_room_v_removes_preexisting_persistent_object --dos-prefix RO --output build/logic-interpreter-probes/batches/room_object_reset_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Added reusable helper `room_pre_switch_logic0_code` for room-switch probes
  that need setup work before the switch action runs.
- Added `room_pre_switch_object_reset_case`, which loads and shows picture 0,
  loads view 11, binds object 10 to that view, places it at X 20 / baseline Y
  80, activates it as a persistent object with action `0x23`, and then changes
  rooms.
- Added two QEMU-backed cases:
  `switch_room_removes_preexisting_persistent_object` for immediate action
  `0x12`, and `switch_room_v_removes_preexisting_persistent_object` for
  variable-selected action `0x13`.
- The destination room logic draws only a validation sprite. The local expected
  renderer therefore fails if the object activated before the switch survives
  into the destination room as an extra drawn sprite.
- QEMU batch `room_object_reset_001` matched 2/2 with 0 mismatches. This
  validates that pre-switch active persistent-object draw state is not visibly
  carried into the destination room for either `0x12` or `0x13`.
- This does not yet prove the contents of every object table field after the
  switch. It is an observable rendering compatibility fact; broader field reset
  details remain to be mapped from the disassembly or narrower bytecode probes.

## 2026-07-03: room-switch object and cache reset source correction

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,240p' docs/src/current_status.md`
- `sed -n '1,220p' docs/src/symbolic_labels.md`
- `rg -n "000017[0-9A-Fa-f]|000014[0-9A-Fa-f]|1792|1485|code\\.room\\.switch_state|reset_dynamic_state|room switch|room-switch" build/cleanroom/AGI.decrypted.ndisasm docs/src/*.md tools/*.py`
- Oversized exploratory disassembly reads, corrected by the focused reads
  below:
  - `ndisasm -b 16 -o 0x175c -e 0x195c build/cleanroom/AGI.decrypted.exe`
  - `ndisasm -b 16 -o 0x1485 -e 0x1685 build/cleanroom/AGI.decrypted.exe`
  - `ndisasm -b 16 -o 0x7060 -e 0x7260 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x10d0 -e 0x12d0 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x30c0 -e 0x32c0 build/cleanroom/AGI.decrypted.exe | sed -n '1,160p'`
- `ndisasm -b 16 -o 0x4470 -e 0x4670 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x4c00 -e 0x4e00 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x3920 -e 0x3b20 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x49c0 -e 0x4bc0 build/cleanroom/AGI.decrypted.exe | sed -n '1,190p'`
- `ndisasm -b 16 -o 0x50a0 -e 0x52a0 build/cleanroom/AGI.decrypted.exe | sed -n '1,170p'`
- `sed -n '300,380p' docs/src/graphics_object_pipeline.md`
- `rg -n "\\+0x1e|\\+0x1f|\\+0x20|0x0010|0x0040|0x0001|0xffbe|0x17b6|17B6|room-switch object|object reset" docs/src tools tests`
- Compact confirmation reads:
  - `ndisasm -b 16 -o 0x175c -e 0x195c build/cleanroom/AGI.decrypted.exe | sed -n '1,90p'`
  - `ndisasm -b 16 -o 0x10d0 -e 0x12d0 build/cleanroom/AGI.decrypted.exe | sed -n '1,55p'`
  - `ndisasm -b 16 -o 0x3920 -e 0x3b20 build/cleanroom/AGI.decrypted.exe | sed -n '30,65p'`
  - `ndisasm -b 16 -o 0x49c0 -e 0x4bc0 build/cleanroom/AGI.decrypted.exe | sed -n '1,35p'`
  - `ndisasm -b 16 -o 0x50a0 -e 0x52a0 build/cleanroom/AGI.decrypted.exe | sed -n '15,42p'`
  - `ndisasm -b 16 -o 0x4470 -e 0x4670 build/cleanroom/AGI.decrypted.exe | sed -n '8,28p'`

Documented result:

- Corrected the room-switch object reset description. At `0x17b6..0x17e5`,
  `code.room.switch_state` iterates object records in `0x2b`-byte steps,
  clears bits `0x0001` and `0x0040` with `AND 0xffbe`, sets bit `0x0010`,
  clears pointer fields `+0x10`, `+0x08`, and `+0x14`, then stores byte `1`
  into `+0x00`, `+0x01`, `+0x20`, `+0x1f`, and `+0x1e`.
- The previous prose saying `+0x1e`, `+0x1f`, and `+0x20` are cleared was
  wrong. The instruction stream keeps `AL = 1`; the repeated `sub ah,ah`
  clears only the high byte and does not change `AL`. Those bytes are therefore
  seeded to `1`. In the object field map they are step size, frame-timer
  reload, and frame-timer current countdown.
- Refined the room-switch cache reset model. Helper `0x10d0` calls
  `0x10f7`, `0x396d`, `0x50cc`, and `0x49dc`. The logic helper `0x10f7` does
  not clear the root word `[0x0977]`; if the root is nonzero, it writes zero to
  the first logic cache record's `+0x00` next-link field. This preserves the
  first logic cache record and unlinks later records.
- The remaining cache helpers clear their roots directly: view-like cache root
  `[0x0ffa] = 0` through `0x396d`, sound-like cache root `[0x125a] = 0`
  through `0x50cc`, and picture-like cache root/static record word
  `[0x120e] = 0` through `0x49dc`.
- Added symbolic labels for `code.logic.truncate_cache_to_head`,
  `code.resource.reset_room_caches`, `code.view.clear_cache_root`,
  `code.picture.clear_cache_root`, `code.sound.clear_cache_root`, and
  `code.input.reset_event_state`, plus data labels for the view/picture/sound
  cache roots.
- Updated `docs/src/logic_bytecode.md`, `docs/src/logic_resources.md`,
  `docs/src/current_status.md`, and `docs/src/symbolic_labels.md` so the
  high-level room-switch model distinguishes QEMU-validated visible behavior
  from source-backed exact memory-field effects.

## 2026-07-03: resource-event recording and restore replay source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,260p' docs/src/current_status.md`
- `rg -n "0x70b1|0x707c|0x706d|0x681c|resource.event|resource-event|1707|1709|0141|0143|code.restore.replay_resource_events|data.resource" docs/src tools tests`
- `git status --short`
- `ndisasm -b 16 -o 0x7058 -e 0x7258 build/cleanroom/AGI.decrypted.exe | sed -n '1,130p'`
- `ndisasm -b 16 -o 0x705e -e 0x725e build/cleanroom/AGI.decrypted.exe | sed -n '1,95p'`
- `ndisasm -b 16 -o 0x681c -e 0x6a1c build/cleanroom/AGI.decrypted.exe | sed -n '1,190p'`
- `ndisasm -b 16 -o 0x716a -e 0x736a build/cleanroom/AGI.decrypted.exe | sed -n '1,95p'`
- `ndisasm -b 16 -o 0x0000 -e 0x0200 build/cleanroom/AGI.decrypted.exe | rg "call 0x70b1|call 0x7060|call 0x706d|call 0x707c|call 0x712f|call 0x714c|call 0x681c"`
- `ndisasm -b 16 -o 0x113d -e 0x133d build/cleanroom/AGI.decrypted.exe | sed -n '1,75p'`
- `ndisasm -b 16 -o 0x39b1 -e 0x3bb1 build/cleanroom/AGI.decrypted.exe | sed -n '1,95p'`
- `ndisasm -b 16 -o 0x39f7 -e 0x3bf7 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x4a16 -e 0x4c16 build/cleanroom/AGI.decrypted.exe | sed -n '1,95p'`
- `ndisasm -b 16 -o 0x4a3b -e 0x4c3b build/cleanroom/AGI.decrypted.exe | sed -n '1,230p'`
- `ndisasm -b 16 -o 0x3f0d -e 0x410d build/cleanroom/AGI.decrypted.exe | sed -n '1,190p'`
- `ndisasm -b 16 -o 0x5126 -e 0x5326 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x2d52 -e 0x2f52 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x5ebf -e 0x60bf build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x1720 -e 0x1920 build/cleanroom/AGI.decrypted.exe | sed -n '1,160p'`
- `ndisasm -b 16 -o 0x78f0 -e 0x7af0 build/cleanroom/AGI.decrypted.exe | sed -n '1,190p'`
- `rg -n "0x8e|0xab|0xac|load_view|prepare_picture|overlay_picture|discard_view|load_sound|resource event|event buffer|code.event|data.event" docs/src/logic_bytecode.md docs/src/symbolic_labels.md docs/src/clean_room_executable_notes.md docs/src/current_status.md docs/src/progress_log.md`
- Follow-up check for re-enable paths:
  - `ndisasm -b 16 -o 0x2512 -e 0x2712 build/cleanroom/AGI.decrypted.exe | sed -n '1,230p'`
  - `ndisasm -b 16 -o 0x2753 -e 0x2953 build/cleanroom/AGI.decrypted.exe | sed -n '1,230p'`
  - `ndisasm -b 16 -o 0x0000 -e 0x0200 build/cleanroom/AGI.decrypted.exe | rg "call 0x705e|call 0x706d|call 0x681c"`

Documented result:

- Assigned stable labels for the resource-event helpers:
  `code.event.disable_recording`, `code.event.enable_recording`,
  `code.event.reset_pair_buffer`, `code.event.record_pair`,
  `code.event.prepare_replay_cursor`, `code.event.next_replay_pair`, and the
  action handlers for opcodes `0x8e`, `0xab`, and `0xac`.
- Refined the data labels for the replay log: `data.event.pair_capacity`
  (`[0x0141]`), `data.event.pair_count` (`[0x0143]`),
  `data.event.saved_pair_count` (`[0x05e1]`),
  `data.event.pair_buffer_base` (`[0x1707]`),
  `data.event.pair_buffer_write` (`[0x1709]`),
  `data.event.pair_buffer_read` (`[0x170b]`),
  `data.event.recording_enabled` (`[0x170d]`), and
  `data.event.pair_high_water` (`[0x170f]`).
- The event log is a sequence of two-byte pairs `(kind, value)`. Capacity is
  stored as a pair count, while the allocated byte size is `capacity * 2`.
  `code.event.record_pair` appends only if flag 7 is clear and
  `data.event.recording_enabled` is nonzero. It reports error code `0x0b`
  when the write pointer reaches `base + capacity * 2`.
- Room switching calls `code.event.reset_pair_buffer` and then
  `code.event.enable_recording`, so each new room starts with a fresh event
  log. Restore replay calls `code.event.disable_recording` before replaying
  saved events so the replayed operations do not append duplicate pairs.
- Mapped restore event kinds from the dispatch table at `0x6915`:
  - `0`: load logic, then restore logic resume metadata through `0x13a5`;
  - `1`: load/refresh view through `code.view.load_resource`;
  - `2`: load picture through `code.picture.load_resource`;
  - `3`: load sound through `code.sound.load_resource`;
  - `4`: prepare/decode picture through `code.picture.prepare`;
  - `5`: replay the transient-display-object packet;
  - `6`: discard picture through `code.picture.discard`;
  - `7`: discard view through `0x3f0d`;
  - `8`: overlay picture through `code.picture.overlay_prepare`.
- Kind `5` is a four-pair packet. Helper `0x2d52` records `(5, 0)`, then
  records byte pairs from `0x0eae..0x0eb3`; replay reads those next three
  pairs back into the same globals before calling `0x2d52`.
- Mapped event-producing resource paths:
  - `0x14`/`0x15` record kind `0` after loading logic through `0x117d`;
  - `0x1e`/`0x1f` record kind `1` only when creating a new cached view entry;
  - `0x18` records kind `2` only when creating a new cached picture entry;
  - `0x62` records kind `3` only when creating a new cached sound entry;
  - `0x19`, `0x1c`, `0x1b`, `0x20`, and `0x99` record kinds `4`, `8`, `6`,
    and `7` through their shared helpers.
- The temporary view-resource display helper `0x5edb`, used by actions
  `0x81` and `0xa2`, disables recording before its internal load/display
  sequence and re-enables recording before returning. If it loaded the view
  only for the display, it discards that view while recording is still
  disabled. This keeps temporary preview work out of the persistent restore
  model.
- The restore action at `0x2512` calls replay at `0x681c` and then continues
  through display/menu refresh helpers, but the checked caller slice does not
  call `code.event.enable_recording`. A full call-site scan found only two
  `code.event.enable_recording` calls: room switching at `0x17a3` and the
  temporary view-display cleanup at `0x6024`. Display-mode toggle action
  `0x8c` also calls replay at `0x797f` without an observed re-enable in that
  immediate path. Therefore the post-replay event-recording lifecycle remains
  an explicit open question; the docs no longer assume automatic re-enable
  after restore replay.
- Updated `docs/src/logic_bytecode.md` with the higher-level event-log model,
  and updated `docs/src/symbolic_labels.md` with the new code/data labels.

## 2026-07-03: replay save-block correction and display-mode QEMU probe

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n` reads of `docs/src/progress_log.md`,
  `docs/src/clean_room_executable_notes.md`,
  `docs/src/symbolic_labels.md`, `docs/src/logic_bytecode.md`,
  `docs/src/current_status.md`, `docs/src/compatibility_testing.md`, and
  `docs/src/graphics_object_pipeline.md`
- `ndisasm` slices around image offsets `0x2512`, `0x2753`, `0x681c`,
  `0x794c`, `0x00c4`, and `0x821c`
- Pattern scans of `build/cleanroom/AGI.decrypted.exe` and
  `build/cleanroom/AGI.decrypted.ndisasm` for stores to `[0x170d]` and calls
  to `code.event.disable_recording`, `code.event.enable_recording`, and
  `code.restore.replay_resource_events`
- `python3 -B -m unittest discover -s tests`
- QEMU monitor-driven display-mode replay probes using
  `build/logic-interpreter-probes/snapshot/logic_interpreter.qcow2`, followed
  by `info registers`, memory reads, and `screendump`
- `python3 -B tools/inspect_ppm.py
  build/logic-interpreter-probes/fixtures/display_mode_replay_skips_flag7_unrecorded_picture/manual_memory_probe.ppm`

Important correction:

- The saved whole-file disassembly uses file offsets, while MZ code image
  addresses are two hundredh bytes lower. For this executable,
  `file offset = image offset + 0x200`. Earlier helper slices that did not
  account for that relationship were plausible-looking but pointed at the wrong
  bytes.

Save/restore dependency map:

- In the save action (`0x2753`, file offset `0x2953`), helper `0x28c6` writes
  length-prefixed blocks. The first large state block is length `0x05e1` bytes
  starting at `DS:0x0002`, not a small block rooted at `[0x05e1]`. That range
  includes `data.event.pair_capacity` (`[0x0141]`) and
  `data.event.pair_count` (`[0x0143]`).
- The active replay pair bytes are a later block whose length is
  `[0x0141] << 1` and whose pointer is `data.event.pair_buffer_base`
  (`[0x1707]`).
- `data.event.recording_enabled` (`[0x170d]`) is not part of those save blocks.
- Restore action `0x2512` reads the same block families through helper
  `0x26b0`, then calls `code.restore.replay_resource_events`.
- Helper `0x1364` serializes logic-cache resume metadata into `[0x0985]` as
  four-byte entries containing a logic resource byte and a resume offset,
  terminated by word `0xffff`. Helper `0x13a5` restores a loaded logic record's
  resume pointer by matching the resource number and adding the saved offset to
  the loaded entry pointer.

Static recording-gate scan:

- Direct stores to `data.event.recording_enabled` were found only in the helper
  bodies:
  - file `0x7263` / image `0x705e`: clear to zero;
  - file `0x7272` / image `0x706d`: set to one.
- Direct calls to the enable helper were found at file `0x19a3` / image
  `0x17a3` (room switch) and file `0x6224` / image `0x6024` (temporary
  view-resource display helper).
- Direct calls to the disable helper were found at file `0x60e3` / image
  `0x5ee3` (temporary view-resource display helper) and file `0x6a2a` / image
  `0x682a` (restore/display-mode replay).
- Direct calls to `code.restore.replay_resource_events` were found at file
  `0x287a` / image `0x267a` (restore success path) and file `0x7b7f` / image
  `0x797f` (display-mode toggle action `0x8c`).
- This scan did not show a direct re-enable inside replay or its immediate
  restore/display-mode callers. The dynamic probe below proved recording was
  enabled again by the time the following script action recorded a transient
  object packet. A later source pass corrected this apparent open question:
  the replay dispatch table hid the post-loop `call 0x706d` at image `0x6927`.

Display-mode replay QEMU probe:

- The fixture patched `AGIDATA.OVL` words `0x112e` and `0x1130` to zero and
  launched the game with `SIERRA -p -c`, so action `0x8c` could pass its source
  guard and call replay.
- Runtime `info registers` showed `DS = 0x16a5`, so the data segment physical
  base was `0x16a50`.
- Memory reads after the fixture stopped:
  - `[0x112e]` at physical `0x17b7e`: `00 00`;
  - `[0x1130]` at physical `0x17b80`: `01 00`, proving `0x8c` toggled bit 0;
  - around `[0x0141]`/`[0x0143]`: bytes `00 32 00 08`, meaning capacity
    `0x32` and active pair count `8`;
  - `[0x1707] = 0x4f33`, `[0x1709] = 0x4f43`, `[0x170b] = 0x4f3b`,
    `[0x170d] = 0x0001`, and `[0x170f] = 0x0008`.
- Pair buffer at physical `DS*16 + 0x4f33 = 0x1b983`:

  ```text
  00 01  02 00  04 00  01 0b  05 00  0b 00  00 32  50 ff
  ```

  Decoded as pairs: `(0,1)`, `(2,0)`, `(4,0)`, `(1,11)`, `(5,0)`, `(11,0)`,
  `(0,50)`, `(80,255)`.

- The pair buffer proves the replay log includes the room-switch logic load,
  picture 0 load/prepare, view 11 load, and final transient object packet. It
  does not include picture 1 when that picture was drawn with flag 7 set or
  after `0xab`/`0xac` rolled the pair count back.
- A fresh screenshot from the same paused VM still matched the earlier
  automated capture and visibly showed an alternating-row background:
  `sha256_rgb e0f5d9669c5d1ecc326a42b28c0b517d4cdc3d1770f53ce38b49a887e1ed5123`.
  Comparing it against the picture-0-only expectation produced 13,473
  mismatches with bbox `(0,1,159,167)`, while comparing it against the
  picture-1-only expectation produced 13,466 mismatches with bbox
  `(0,0,159,166)`. The downsampled rows alternate: even rows are nibble `6`,
  odd rows are nibble `4`.

Documentation and harness result:

- Added per-case launch-command support to the QEMU snapshot harness and mapped
  the DOS monitor key name for `-`, allowing logic fixtures to launch as
  `SIERRA -p -c`.
- Added two display-mode replay fixtures:
  `display_mode_replay_skips_flag7_unrecorded_picture` and
  `display_mode_replay_uses_rolled_back_event_count`.
- The automated screenshot expectations now reflect the original engine's
  observable behavior in this fixture: the background alternates rows from the
  recorded and unrecorded/rolled-back pictures. The replay-log semantics are
  documented from source plus memory inspection rather than inferred from the
  screenshot.
- The corrected QEMU batch
  `build/logic-interpreter-probes/batches/replay_visible_001.json` matched with
  2 matches, 0 mismatches, and 0 errors.

## 2026-07-04: display-mode replay classified as CGA remapping artifact

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,280p' docs/src/current_status.md`
- `rg -n "0x8c|display-mode|row-interleav|CGA|EGA|\\[0x1130\\]|0x1130|0x112e|0x2b28|0x5528|0x2b4f|0x681c|0x5685|0x9899" docs/src/logic_bytecode.md docs/src/graphics_object_pipeline.md docs/src/clean_room_executable_notes.md docs/src/symbolic_labels.md docs/src/current_status.md tools tests`
- `rg -n "1130|112e|1365|1379|5685|9899|99b8|9be3|9916|794c|2b28|5528|2b4f|681c" build/cleanroom/AGI.decrypted.ndisasm`
- `ndisasm -b 16 -o 0x00c4 -e 0x02c4 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x40a0 -e 0x42a0 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x794c -e 0x7b4c build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x2b20 -e 0x2d20 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x5520 -e 0x5720 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x9800 SQ2/EGA_GRAF.OVL`
- `ndisasm -b 16 -o 0x9800 SQ2/CGA_GRAF.OVL`
- `ndisasm -b 16 -o 0x9800 SQ2/VG_GRAF.OVL`
- `ndisasm -b 16 -o 0x9800 SQ2/JR_GRAF.OVL`
- `xxd -g 1 -s 0x1d30 -l 0x90 SQ2/AGIDATA.OVL`
- local Python table parse of `SQ2/AGIDATA.OVL` bytes at `0x1d36`
- `ndisasm -b 16 -o 0x4a80 -e 0x4c80 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x6440 -e 0x6640 build/cleanroom/AGI.decrypted.exe`

Corrected interpretation:

- The row-interleaved display observed after the `0x8c` QEMU replay probe is a
  CGA-style display remapping artifact. It is not evidence that the unrecorded
  or rolled-back picture survives the replay.
- The command-line parser at image `0x00c4` sets display mode word `[0x1130]`
  directly from single-letter switches: `-c` stores `0`, `-r` stores `1`,
  `-e` stores `3`, `-h` stores `2`, and `-v` stores `4`. The same parser
  stores hardware selector `[0x112e] = 0` for `-p`, `2` for `-t`, and `8` for
  `-s`.
- Action `0x8c` at image `0x794c` only enters its rebuild path when
  `[0x112e] == 0`, byte variable 0 is nonzero, and `[0x1130]` is not `2` or
  `3`. Therefore the fixture that launches `SIERRA -p -c` is intentionally
  forcing the hardware-0 CGA-style path; the full 16-color EGA target path is
  outside this handler's active branch.
- Picture command `0xf0` calls `code.display.map_visual_color_for_adapter`
  (`0x5685`) before storing the visual draw value and masks. That mapper
  returns the input color unchanged for `[0x112e] != 0`, and also returns
  unchanged for modes `2` and `3`. It delegates to graphics-overlay entry
  `0x9815` only when `[0x112e] == 0` and the mode is not `2` or `3`.
- In `SQ2/CGA_GRAF.OVL`, entry `0x9815` is a color mapper, not a mode setup
  entry. It indexes a three-byte-per-color table at `AGIDATA.OVL:0x1d36`.
  When `[0x1130] != 1`, it returns table byte 0 duplicated into `AL` and `AH`;
  when `[0x1130] == 1`, it returns the following two-byte word. For AGI color
  `6`, the observed table bytes are `08 0b 0e`.
- In `SQ2/EGA_GRAF.OVL`, entry `0x9815` is instead a graphics-mode setup
  routine that sets BIOS mode `0x0d`, configures palette/register state, and
  stores video segment `0xa000` in `[0x1371]`. The EGA target path does not use
  the CGA color-mapping table for picture command `0xf0`.
- Replay kind `4` calls `code.picture.prepare` (`0x4acf`), which calls
  `code.picture.decode_with_clear` (`0x6445`). That entry fills the logical
  buffer with `0x4f4f` through `code.display.fill_buffer_word` (`0x5257`) before
  decoding the picture command stream. Combined with the QEMU memory proof that
  the event log excludes picture 1, this rules out the old picture as the source
  of the row-interleaved background.

Documentation result:

- Updated the bytecode, graphics pipeline, compatibility, status, and symbolic
  label docs so the row-interleaved replay fixture is described as CGA-only
  adapter evidence rather than a full EGA compatibility requirement.
- Added symbolic labels for `code.display.map_visual_color_for_adapter`,
  `overlay.cga.map_visual_color_for_mode`, and
  `data.display.cga_color_map`.

## 2026-07-04: replay recording re-enable source correction

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,240p' docs/src/current_status.md`
- `tail -80 docs/src/clean_room_executable_notes.md`
- `git status --short`
- An exploratory `rg` command containing unescaped backticks was rejected by
  the shell before producing useful evidence; no interpretation was derived
  from that failed command.
- `sed -n '4728,4905p' docs/src/clean_room_executable_notes.md`
- `sed -n '60,95p' docs/src/symbolic_labels.md`
- `sed -n '185,200p' docs/src/symbolic_labels.md`
- `sed -n '236,270p' docs/src/runtime_model.md`
- `ndisasm -b 16 -o 0x681c -e 0x6a1c build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x705e -e 0x725e build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x2512 -e 0x2712 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x794c -e 0x7b4c build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x1364 -e 0x1564 build/cleanroom/AGI.decrypted.exe | sed -n '1,150p'`
- `ndisasm -b 16 -o 0x1720 -e 0x1920 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x5ebf -e 0x60bf build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `rg -n "call 0x705e|call 0x706d|call 0x681c|mov word \\[0x170d\\]|\\[0x170d\\]" build/cleanroom/AGI.decrypted.ndisasm`
- `ndisasm -b 16 -o 0x6927 -e 0x6b27 build/cleanroom/AGI.decrypted.exe | sed -n '1,90p'`
- `xxd -g 1 -s 0x6b10 -l 0x30 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x6904 -e 0x6b04 build/cleanroom/AGI.decrypted.exe | sed -n '1,45p'`

Correction:

- The earlier static scan that failed to find a replay-time re-enable was a
  disassembly-boundary false negative, not an engine behavior. In the linear
  slice that starts before the event-kind dispatch table, `ndisasm` treats the
  bytes immediately after the table as data-like instructions.
- The replay loop at `code.restore.replay_resource_events` (`0x681c`) branches
  to image `0x6927` when `code.event.next_replay_pair` (`0x714c`) returns zero.
  Disassembling at `0x6927` decodes bytes `e8 43 07` as `call 0x706d`, which is
  `code.event.enable_recording`.
- The event-kind dispatch table is at image `0x6915`; the raw bytes around
  file offset `0x6b10` show the table words for handlers `0x688e`, `0x689e`,
  `0x68ab`, `0x68b1`, `0x68b7`, `0x68bd`, `0x68f2`, `0x68f8`, and `0x68fe`,
  followed by `e8 43 07` at file offset `0x6b27` / image `0x6927`.
- Therefore restore/display-mode replay disables recording only while replaying
  the saved pairs. After the pair stream ends, replay re-enables recording,
  then scans object records to restore saved flags, rebind view payloads, and
  refresh display/input state.
- The save-block correction remains unchanged: `data.event.recording_enabled`
  is not saved as part of the length-prefixed state blocks. Restore establishes
  the runtime gate by replay control flow, not by reading a saved word.

Documentation result:

- Updated `logic_bytecode.md`, `graphics_object_pipeline.md`,
  `compatibility_testing.md`, `current_status.md`, and `symbolic_labels.md` to
  remove the stale unresolved re-enable note.
- Added symbolic labels for `table.restore.replay_event_dispatch` and
  `code.restore.finish_replay_and_reenable_recording`.

## 2026-07-04: raw-key predicate and focused edge-render probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n` reads of `PROGRESS.md`, `tools/logic_interpreter_probe.py`,
  `tests/test_logic_interpreter_probe.py`, `tools/logic_opcode_evidence.py`,
  `tools/object_overlay_probe.py`, `tests/test_object_overlay_probe.py`,
  `docs/src/logic_bytecode.md`, `docs/src/compatibility_testing.md`,
  `docs/src/graphics_object_pipeline.md`, and `docs/src/runtime_model.md`
- `rg -n "raw_key|0x0d|0D|key event|keyboard|status byte|condition 0x0d|key_event|last key" docs/src/logic_bytecode.md docs/src/clean_room_executable_notes.md docs/src/symbolic_labels.md tools/logic_interpreter_probe.py`
- `rg -n "def load_cases|--case|args.case|case_id" tools/logic_interpreter_probe.py`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_object_overlay_probe`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix RK --output build/logic-interpreter-probes/batches/raw_key_condition_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case raw_key_event_available_draws_after_typed_key`
- Sandboxed attempt:
  `python3 -B tools/object_overlay_probe.py --dos-prefix OC --output build/object-overlay-probes/batches/clip_edges_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case left_clip_view11_priority15 --case top_clip_view11_priority15`
- Escalated rerun of the same object-overlay command, after QEMU reported
  `Failed to bind socket: Operation not permitted` for its local VNC display.
- `python3 -B tools/logic_opcode_evidence.py`

Results:

- Added logic probe case `raw_key_event_available_draws_after_typed_key`. It
  installs no `0x79` key mapping, sends plain key `x`, and draws only when
  condition `0x0d` succeeds. Batch `raw_key_condition_001` matched QEMU with
  1 match, 0 mismatches, and 0 errors, promoting condition `0x0d`
  (`raw_key_event_available`) from source-backed to QEMU-validated.
- Promoted actions `0x62` (`load_sound`) and `0x63`
  (`start_sound_with_flag`) from dispatch-smoke to QEMU-validated opcode-level
  evidence because existing QEMU case `sound_stop_sets_completion_flag` loads
  sound 1, starts it with completion flag 77, stops it with `0x64`, and reaches
  the validation draw only after flag 77 is set. Actual audio playback and
  asynchronous timing remain partial.
- Promoted actions `0xab` (`save_event_buffer_count`) and `0xac`
  (`restore_event_buffer_count`) from dispatch-smoke to QEMU-validated
  replay-log evidence through
  `display_mode_replay_uses_rolled_back_event_count`. The automated capture
  and paired memory notes show the rolled-back picture is excluded from the
  active pair buffer used by replay.
- Added `--case CASE_ID` filtering to `tools/object_overlay_probe.py`, matching
  the existing logic-probe workflow for focused QEMU runs.
- Added object overlay cases `left_clip_view11_priority15` and
  `top_clip_view11_priority15`. The first validates view 11 flush with the left
  edge at left `0`, baseline `80`; the second revalidates the top-edge
  placement adjustment where requested left `20`, baseline `2` matches local
  output at left `18`, baseline `4`.
- Focused object overlay batch `clip_edges_001` matched QEMU with 2 matches, 0
  mismatches, and 0 errors after rerunning with permission for QEMU's VNC bind.
- Regenerated `docs/src/logic_opcode_evidence.md` from the local evidence
  generator. `PROGRESS.md` now counts 153 covered action opcodes (`152`
  QEMU-validated plus structural `0x00`), 23 partial action opcodes, and all 19
  condition opcodes QEMU-validated.
- Added implementation-facing state-machine summaries for resource lifecycle,
  object drawing lifecycle, and motion/animation lifecycle to
  `docs/src/runtime_model.md`.

## 2026-07-04: action 0x84 movement effect and text/input lifecycle model

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,380p' PROGRESS.md`
- `rg -n "QEMU dispatch-smoke|source-backed|0x69|0x6a|0x6b|0x6c|0x6d|0x6e|0x70|0x71|0x77|0x78|0x83|0x84|0x89|0x8a|0x8e|0x95|0x96|0x9a|0xa3|0xa4|0xa9|0xaa|0xad" docs/src/logic_opcode_evidence.md PROGRESS.md docs/src/logic_bytecode.md`
- `sed -n` reads of `tools/qemu_snapshot.py`,
  `tools/logic_interpreter_probe.py`, `tools/object_movement_probe.py`,
  `tools/qemu_fixture.py`, `tests/test_logic_interpreter_probe.py`,
  `tests/test_object_movement_probe.py`, and the relevant docs sections.
- Attempted `0xaa` probe:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix SD --output build/logic-interpreter-probes/batches/save_description_copy_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case copy_save_description_to_string_slot_copies_buffer`
- `cat build/logic-interpreter-probes/batches/save_description_copy_001.json`
- `xxd -g 1 -s 0x0e60 -l 0x60 build/logic-interpreter-probes/fixtures/copy_save_description_to_string_slot_copies_buffer/AGIDATA.OVL`
- `ndisasm -b 16 -o 0x2720 -e 0x2920 build/cleanroom/AGI.decrypted.exe`
- `python3 -B -m unittest tests.test_object_movement_probe tests.test_logic_interpreter_probe tests.test_qemu_fixture`
- `python3 -B tools/logic_opcode_evidence.py`
- `python3 -B tools/object_movement_probe.py --dos-prefix G84 --output build/object-movement-probes/batches/action_84_motion_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case action_84_after_random_motion_stops_motion`

Results:

- Attempted to promote action `0xaa`
  (`copy_save_description_to_string_slot`) with a fixture-local patch that put
  `look` at `AGIDATA.OVL:0x0e72`, the source pointer used by the handler at
  image `0x2726`. The QEMU run did not reach the validation draw: the capture
  mismatched exactly where the expected view would have been, indicating the
  string comparison failed. The fixture file did contain `look` at offset
  `0x0e72`, so this attempt suggests runtime initialization or save-selector
  state controls that buffer. The case was removed from the reusable base-case
  registry and `0xaa` remains dispatch-smoke only.
- Added helper `set_global_0139_and_clear_object0_field_22_action()` for action
  `0x84` and object movement case
  `action_84_after_random_motion_stops_motion`. The fixture starts random
  motion on object 0, immediately executes `0x84`, and expects the object to
  remain at `(60,80)`.
- QEMU batch `action_84_motion_001` matched with 1 match, 0 mismatches, and 0
  errors. This promotes the object-0 motion-byte effect of action `0x84` to
  QEMU-validated; the global `[0x0139] = 1` side effect remains documented from
  source.
- Updated `tools/logic_opcode_evidence.py` and regenerated
  `docs/src/logic_opcode_evidence.md`, promoting `0x84` out of dispatch-smoke.
- Added an implementation-facing text/input UI lifecycle state machine to
  `docs/src/runtime_model.md`, tying input-line enable/disable, prompt/status
  configuration, modal text windows, alternate text mode, and event/edit loops
  to the current opcode evidence.
- Updated `PROGRESS.md`: logic action opcode coverage is now 154 of 176 at
  `[x]` level (`153` QEMU-validated plus structural `0x00`), with 22 partial
  action opcodes remaining.

## 2026-07-04: text rectangle clear behavior probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,260p' PROGRESS.md`
- `sed -n '240,380p' PROGRESS.md`
- `rg -n "0x69|0x6a|0x6b|0x6c|0x6d|0x70|0x71|0x77|0x78|0x83|0x89|0x8a|0x8e|0x95|0x96|0x9a|0xa3|0xa4|0xa9|0xaa|0xad" docs/src/logic_bytecode.md docs/src/runtime_model.md docs/src/compatibility_testing.md docs/src/clean_room_executable_notes.md tools tests`
- `sed -n` reads of `tools/logic_interpreter_probe.py`,
  `tools/qemu_fixture.py`, `tests/test_logic_interpreter_probe.py`,
  `docs/src/logic_bytecode.md`, and `docs/src/runtime_model.md`.
- `ndisasm -b 16 -o 0x34bd -e 0x36bd build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x3726 -e 0x3926 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x76ca -e 0x78ca build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x78cb -e 0x7acb build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x2bc4 -e 0x2dc4 build/cleanroom/AGI.decrypted.exe | sed -n '1,90p'`
- `ndisasm -b 16 -o 0x2b78 -e 0x2d78 build/cleanroom/AGI.decrypted.exe | sed -n '1,80p'`
- `python3 -B -m unittest tests.test_logic_interpreter_probe`
- `python3 -B -m py_compile tools/logic_interpreter_probe.py`
- First attempted QEMU run:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix TC --output build/logic-interpreter-probes/batches/text_rect_clear_behaviour_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case text_rect_clear_rows_removes_formatted_text --case text_rect_clear_bounds_removes_formatted_text`
- Corrected QEMU runs:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix TC --output build/logic-interpreter-probes/batches/text_rect_clear_behaviour_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case text_rect_clear_rows_removes_formatted_text --case text_rect_clear_bounds_removes_formatted_text`
  and
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix TC --output build/logic-interpreter-probes/batches/text_rect_clear_behaviour_003.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case text_rect_clear_rows_removes_formatted_text --case text_rect_clear_bounds_removes_formatted_text`
- `cat build/logic-interpreter-probes/batches/text_rect_clear_behaviour_001.json`
- `cat build/logic-interpreter-probes/batches/text_rect_clear_behaviour_002.json`
- `python3 -B tools/inspect_ppm.py build/logic-interpreter-probes/fixtures/text_rect_clear_bounds_removes_formatted_text/qemu_capture.ppm`
- Local one-off PPM measurement of black pixel ranges in rows 60..75 of
  `build/logic-interpreter-probes/fixtures/text_rect_clear_bounds_removes_formatted_text/qemu_capture.ppm`.
- `python3 -B tools/logic_opcode_evidence.py`

Results:

- Added `LogicInterpreterCase.expected_visual_rects` to model display-surface
  effects that are not picture-resource mutations. The comparator applies these
  rectangles to the low visual nibble before composing any expected view cels,
  preserving the priority/control nibble.
- Added QEMU cases `text_rect_clear_rows_removes_formatted_text` and
  `text_rect_clear_bounds_removes_formatted_text`. Each displays formatted
  message text, accepts Enter, runs the clear action, and compares the capture
  without using `0x1a` to repaint the picture.
- The first row-clear attempt mismatched because the expected screen assumed
  the original white picture remained. The actual capture had a black band at
  logical Y 40..55, proving that `0x69(5, 6, 0)` clears the visible display
  surface rather than restoring picture pixels.
- After adding an expected black rectangle, `text_rect_clear_behaviour_002`
  matched the `0x69` case but mismatched the bounded `0x9a` case. Measuring the
  capture showed that `0x9a(8, 5, 8, 20, 0)` clears logical X 20..83/Y 64..71.
  This validates the EGA target's text grid as four logical pixels per text
  column and eight logical pixels per text row.
- Final QEMU batch `text_rect_clear_behaviour_003` matched with 2 matches, 0
  mismatches, and 0 errors. Actions `0x69` (`clear_text_rect`) and `0x9a`
  (`clear_text_rect_bounds`) were promoted from dispatch-smoke to
  QEMU-validated behavior coverage.
- Added symbolic labels `code.text.clear_rows` (`0x2b78`) and
  `code.text.clear_bounds` (`0x2bc4`), updated the opcode/runtime docs, and
  regenerated `docs/src/logic_opcode_evidence.md`.
- Updated `PROGRESS.md`: logic action opcode coverage is now 156 of 176 at
  `[x]` level (`155` QEMU-validated plus structural `0x00`), with 20 partial
  action opcodes remaining.

## 2026-07-04: status/input single-row clear behavior probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n` reads of `PROGRESS.md`, `docs/src/progress_log.md`,
  `docs/src/logic_bytecode.md`, `docs/src/runtime_model.md`,
  `docs/src/logic_opcode_evidence.md`, `docs/src/compatibility_testing.md`,
  `docs/src/symbolic_labels.md`, `tools/logic_interpreter_probe.py`,
  `tools/logic_opcode_evidence.py`, and `tests/test_logic_interpreter_probe.py`.
- `rg -n "0x70|0x71|0x77|disable_input|show_status|hide_status|status_line|input_line" docs/src/clean_room_executable_notes.md docs/src/logic_bytecode.md docs/src/runtime_model.md docs/src/logic_opcode_evidence.md`
- `ndisasm -b 16 -o 0x2ba6 -e 0x2da6 build/cleanroom/AGI.decrypted.exe | sed -n '1,60p'`
- `python3 -B -m unittest tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_base_cases_cover_core_control_flow tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_text_rect_clear_cases_expect_display_surface_rectangles`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TH --output build/logic-interpreter-probes/batches/text_hide_clear_behaviour_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_line_disable_clears_configured_row --case status_line_hide_clears_configured_row`
- `python3 -B tools/logic_opcode_evidence.py`

Results:

- Re-read `code.text.clear_row` at image `0x2ba6`. The helper pushes
  `[bp+0xa]`, `[bp+0x8]`, and `[bp+0x8]`, then calls `code.text.clear_rows`
  (`0x2b78`). This makes it a single-row wrapper: top row and bottom row are
  identical, and the second argument is the clear attribute.
- Added QEMU case `input_line_disable_clears_configured_row`. The fixture
  displays formatted text on row 5, acknowledges it, runs `0x6f(0, 5, 22)` to
  set the input-row global `[0x05d5]`, then runs `0x77`. The original-engine
  capture matches only when logical Y 40..47 is modeled as cleared to visual
  color 0 before the final object draw.
- Added QEMU case `status_line_hide_clears_configured_row`. The fixture
  displays formatted text on row 5, acknowledges it, runs `0x6f(0, 0, 5)` to
  set the status-row global `[0x05db]`, then runs `0x71`. The capture likewise
  matches with logical Y 40..47 cleared to visual color 0.
- QEMU batch `text_hide_clear_behaviour_001` matched with 2 matches, 0
  mismatches, and 0 errors. Actions `0x71` (`hide_status_line_like`) and
  `0x77` (`disable_input_line_like`) are now behavior-level QEMU-validated for
  the normal EGA display path.
- Added symbolic label `code.text.clear_row` (`0x2ba6`), updated the
  opcode/runtime/compatibility docs, and regenerated
  `docs/src/logic_opcode_evidence.md`.
- Updated `PROGRESS.md`: logic action opcode coverage is now 158 of 176 at
  `[x]` level (`157` QEMU-validated plus structural `0x00`), with 18 partial
  action opcodes remaining.

## 2026-07-04: input-line enable and alternate text-attribute surface probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n` reads of `PROGRESS.md`, `docs/src/logic_bytecode.md`,
  `docs/src/runtime_model.md`, `docs/src/compatibility_testing.md`,
  `docs/src/symbolic_labels.md`, `docs/src/clean_room_executable_notes.md`,
  `tools/logic_interpreter_probe.py`, `tools/logic_opcode_evidence.py`, and
  `tests/test_logic_interpreter_probe.py`.
- `rg -n "0x70|0x78|0x89|0x8a|0x6c|0x6d|0xa3|0xa4|0x0d0f|0x05d3|0x05d7|0x05d9|0x0ff8|0x0fa4|0x0fce|0x38d7|0x37a5|0x3652|0x34bd" docs/src/clean_room_executable_notes.md docs/src/logic_bytecode.md docs/src/runtime_model.md tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py`
- `ndisasm -b 16 -o 0x34bd -e 0x36bd build/cleanroom/AGI.decrypted.exe | sed -n '1,120p'`
- `ndisasm -b 16 -o 0x3726 -e 0x3926 build/cleanroom/AGI.decrypted.exe | sed -n '1,170p'`
- `ndisasm -b 16 -o 0x38b4 -e 0x3ab4 build/cleanroom/AGI.decrypted.exe | sed -n '1,160p'`
- `ndisasm -b 16 -o 0x76ca -e 0x78ca build/cleanroom/AGI.decrypted.exe | sed -n '1,150p'`
- `ndisasm -b 16 -o 0x78cb -e 0x7acb build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x77d5 -e 0x79d5 build/cleanroom/AGI.decrypted.exe | sed -n '1,120p'`
- `python3 -B -m unittest tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_base_cases_cover_core_control_flow tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_text_rect_clear_cases_expect_display_surface_rectangles`
- First attempted QEMU run:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix TE --output build/logic-interpreter-probes/batches/text_enable_attr_behaviour_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_line_enable_clears_configured_row --case text_attribute_enable_clears_visible_surface`
- Corrected QEMU run:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix TE --output build/logic-interpreter-probes/batches/text_enable_attr_behaviour_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_line_enable_clears_configured_row --case text_attribute_enable_clears_visible_surface`
- `cat build/logic-interpreter-probes/batches/text_enable_attr_behaviour_001.json`
- `python3 -B tools/inspect_ppm.py build/logic-interpreter-probes/fixtures/text_attribute_enable_clears_visible_surface/qemu_capture.ppm`
- `python3 -B tools/logic_opcode_evidence.py`

Results:

- Re-read action `0x78` at image `0x3898` and helper
  `code.input.redraw_input_line` at image `0x38d7`. The action sets word
  `[0x05d3] = 1`; in the normal non-display-mode-2 path, the helper erases any
  visible prompt marker, calls `code.text.clear_row` (`0x2ba6`) for row
  `[0x05d5]` with attribute `[0x05cf]`, positions the cursor at that row, and
  writes fixed string slot 0, the visible input buffer, and the prompt marker.
- Added QEMU case `input_line_enable_clears_configured_row`. The fixture sets
  the prompt marker to an empty message, displays formatted text on row 5,
  acknowledges it, runs `0x6f(0, 5, 22)`, and then runs `0x78`. The capture
  matches only when logical Y 40..47 is cleared to visual color 0 before the
  final object draw.
- Re-read action `0x6a` at image `0x76ca`. The handler erases the prompt
  marker, sets byte `[0x1757] = 1`, derives text attributes through
  `code.text.set_attribute_pair` (`0x77d5`), calls overlay entry `0x9803`, then
  calls `code.text.clear_rows` (`0x2b78`) for rows 0..24.
- Added QEMU case `text_attribute_enable_clears_visible_surface`. The first
  expected model composed the usual transient-object validation draw after
  `0x6a`, but QEMU batch `text_enable_attr_behaviour_001` mismatched only in
  the object area. Inspecting the capture showed a single black color across
  the screen, so the visible surface clear was correct and the object
  composition expectation was wrong for this active alternate text mode.
- Updated the probe helper with an explicit `compare_view` switch and changed
  the `0x6a` case to compare only the visible surface. QEMU batch
  `text_enable_attr_behaviour_002` then matched with 2 matches, 0 mismatches,
  and 0 errors.
- Actions `0x78` (`enable_input_line_like`) and `0x6a`
  (`enable_text_attr_mode_1757`) are now behavior-level QEMU-validated for the
  observed EGA paths.
- Updated `tools/logic_opcode_evidence.py`, regenerated
  `docs/src/logic_opcode_evidence.md`, and updated opcode, runtime,
  compatibility, and symbolic-label docs.
- Updated `PROGRESS.md`: logic action opcode coverage is now 160 of 176 at
  `[x]` level (`159` QEMU-validated plus structural `0x00`), with 16 partial
  action opcodes remaining.

## 2026-07-04: prompt-marker suppression and text-attribute exit probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n` reads of `PROGRESS.md`, `tools/logic_interpreter_probe.py`,
  `tests/test_logic_interpreter_probe.py`, `tools/logic_opcode_evidence.py`,
  `docs/src/logic_bytecode.md`, `docs/src/compatibility_testing.md`,
  `docs/src/runtime_model.md`, `docs/src/symbolic_labels.md`, and this notes
  file.
- `rg -n "0xfce|0FA4|0ff8|parse_string|set_string|input buffer|prompt_marker|0x6C|0x89|0x8A" tools/logic_interpreter_probe.py docs/src/logic_bytecode.md docs/src/clean_room_executable_notes.md docs/src/runtime_model.md tests/test_logic_interpreter_probe.py`
- `ndisasm -b 16 -o 0x38b4 -e 0x39b4 build/cleanroom/AGI.decrypted.exe | sed -n '1,80p'`
- `ndisasm -b 16 -o 0x37f7 -e 0x38b4 build/cleanroom/AGI.decrypted.exe | sed -n '1,95p'`
- `python3 -B -m unittest tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_base_cases_cover_core_control_flow tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_text_rect_clear_cases_expect_display_surface_rectangles`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TP --output build/logic-interpreter-probes/batches/text_prompt_attr_behaviour_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case text_attribute_disable_restores_picture_draw --case input_prompt_empty_message_suppresses_marker`
- `python3 -B tools/logic_opcode_evidence.py`

Results:

- Added QEMU case `text_attribute_disable_restores_picture_draw`. The fixture
  runs `0x6a`, then `0x6b`, then refreshes the picture and draws the validation
  object. The original-engine capture matched the normal composed object view,
  validating that `0x6b` leaves the alternate text-attribute mode and restores
  ordinary picture/object drawing.
- Added QEMU case `input_prompt_empty_message_suppresses_marker`. The fixture
  first runs `0x6c` with a nonempty message, displays and acknowledges text on
  row 5, then runs `0x6c` with an empty message before `0x6f(0, 5, 22)` and
  `0x78`. The capture matches only when the input row is black with no prompt
  marker glyph, validating the source-backed behavior that `0x6c` stores the
  first byte of the resolved message and that byte zero suppresses marker
  drawing.
- QEMU batch `text_prompt_attr_behaviour_001` matched with 2 matches, 0
  mismatches, and 0 errors.
- Actions `0x6b` (`disable_text_attr_mode_1757`) and `0x6c`
  (`set_input_prompt_char`) are now behavior-level QEMU-validated for the
  focused visible effects above. Nonempty prompt-marker glyph shape remains a
  text-rendering detail not yet modeled.
- Updated `tools/logic_opcode_evidence.py`, regenerated
  `docs/src/logic_opcode_evidence.md`, and updated opcode, runtime,
  compatibility, and symbolic-label docs.
- Updated `PROGRESS.md`: logic action opcode coverage is now 162 of 176 at
  `[x]` level (`161` QEMU-validated plus structural `0x00`), with 14 partial
  action opcodes remaining.

## 2026-07-04: text-attribute pair behavior probe

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n` reads of `PROGRESS.md`, `tools/logic_interpreter_probe.py`,
  `tests/test_logic_interpreter_probe.py`, `tools/logic_opcode_evidence.py`,
  `docs/src/logic_bytecode.md`, `docs/src/runtime_model.md`,
  `docs/src/compatibility_testing.md`, `docs/src/symbolic_labels.md`, and this
  notes file.
- `rg -n "0x77d5|0x7803|0x78a1|0x78ad|set_attribute_pair|0x6d|0x6D" docs/src/clean_room_executable_notes.md docs/src/symbolic_labels.md docs/src/logic_bytecode.md docs/src/runtime_model.md`
- `ndisasm -b 16 -o 0x77d5 -e 0x79d5 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x76ca -e 0x78ca build/cleanroom/AGI.decrypted.exe`
- `python3 -B -m unittest tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_base_cases_cover_core_control_flow tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_text_rect_clear_cases_expect_display_surface_rectangles`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix TA --output build/logic-interpreter-probes/batches/text_attr_pair_behaviour_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case text_attribute_pair_changes_attr_mode_clear_color`
- `python3 -B tools/logic_opcode_evidence.py`

Results:

- Re-read action `0x6d` at image `0x77af`. It reads two immediate operands and
  calls `code.text.set_attribute_pair` (`0x77d5`).
- Re-read `code.text.set_attribute_pair` at image `0x77d5`. It stores
  `[0x05d1] = helper_0x7803(arg0, arg1)`, `[0x05cd] = helper_0x78a1(arg0)`,
  and `[0x05cf] = helper_0x78ad(arg1)`. In normal text mode, `0x78ad`
  returns `0xff` for a nonzero argument; when byte `[0x1757]` is set, `0x7803`
  packs the pair as `arg0 | (arg1 << 4)`.
- Added QEMU case `text_attribute_pair_changes_attr_mode_clear_color`. The
  fixture runs `0x6d(0, 1)`, then `0x6a`, and compares the visible surface
  without expecting the normal validation sprite while alternate text mode is
  active.
- QEMU batch `text_attr_pair_behaviour_001` matched with 1 match, 0 mismatches,
  and 0 errors. This validates that the stored pair is reused by `0x6a` and
  produces a full-screen visual color 15 clear, matching packed text attribute
  low byte `0xf0` for the observed EGA path.
- Promoted action `0x6d` (`set_text_window_pair`) to behavior-level
  QEMU-validated evidence. Updated `tools/logic_opcode_evidence.py`,
  regenerated `docs/src/logic_opcode_evidence.md`, and updated opcode,
  runtime, compatibility, and symbolic-label docs.
- Updated `PROGRESS.md`: logic action opcode coverage is now 163 of 176 at
  `[x]` level (`162` QEMU-validated plus structural `0x00`), with 13 partial
  action opcodes remaining.

## 2026-07-04: input-line refresh/erase and status-line show probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n` reads of `PROGRESS.md`, `tools/logic_interpreter_probe.py`,
  `tests/test_logic_interpreter_probe.py`, `tools/logic_opcode_evidence.py`,
  `docs/src/logic_bytecode.md`, `docs/src/runtime_model.md`,
  `docs/src/compatibility_testing.md`, `docs/src/symbolic_labels.md`, and this
  notes file.
- `rg -n "\\[~\\]|Highest-Value|Remaining|0x70|0x89|0x8a|0xa3|0xa4|0xa9|0xaa|0xad|0x83|0x8e|0x95|0x96|0x6e" PROGRESS.md docs/src/logic_bytecode.md docs/src/runtime_model.md docs/src/clean_room_executable_notes.md tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py tools/logic_opcode_evidence.py`
- `ndisasm -b 16 -o 0x3652 -e 0x3852 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x3726 -e 0x3926 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x34bd -e 0x36bd build/cleanroom/AGI.decrypted.exe`
- `python3 -B -m unittest tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_base_cases_cover_core_control_flow tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_text_rect_clear_cases_expect_display_surface_rectangles tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_rect_checks_can_match_without_glyph_model tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_rect_checks_report_mismatch`
- First QEMU attempt:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix IR --output build/logic-interpreter-probes/batches/input_refresh_status_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case status_line_show_draws_configured_row --case input_line_typed_text_visible_baseline --case input_line_erase_clears_typed_buffer --case input_line_erase_then_refresh_restores_typed_buffer`
- Capture checks:
  `python3 -B -m json.tool build/logic-interpreter-probes/batches/input_refresh_status_001.json`
  and `python3 -B tools/inspect_ppm.py` over the three input-line captures.
- Local row-count script over the downsampled captures for
  `input_line_typed_text_visible_baseline`,
  `input_line_erase_clears_typed_buffer`, and the failed refresh case.
- Focused unit rerun:
  `python3 -B -m unittest tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_base_cases_cover_core_control_flow tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_rect_checks_can_match_without_glyph_model tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_rect_checks_report_mismatch`
- Corrected QEMU input batch:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix IR --output build/logic-interpreter-probes/batches/input_refresh_status_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_line_typed_text_visible_baseline --case input_line_erase_clears_typed_buffer --case input_line_refresh_repaints_entered_buffer`
- QEMU status batch:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix ST --output build/logic-interpreter-probes/batches/status_show_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case status_line_show_draws_configured_row`
- `python3 -B tools/logic_opcode_evidence.py`

Results:

- Added a narrow rectangle-check comparison mode to
  `tools/logic_interpreter_probe.py` for UI text rows whose exact font glyphs
  are not yet modeled by the local renderer. Existing exact full-frame
  comparisons remain the default.
- Re-read helper `code.input.handle_input_char` (`0x3652`), action `0x8a`
  (`0x3726`), action `0x89` (`0x3753`), helper
  `code.input.append_source_to_visible` (`0x37a5`), and status-line helper
  `0x34bd`.
- Added QEMU baseline `input_line_typed_text_visible_baseline`, which validates
  that typed live-edit characters produce visible color-15 pixels on the
  configured input row.
- Added QEMU case `input_line_erase_clears_typed_buffer`. The fixture
  configures input row 5, sends `look`, then runs `0x8a` every cycle. It
  matched only when logical Y 40..47 was black before the final object draw,
  validating the visible erase path for action `0x8a`.
- The first attempted refresh case assumed `0x89` would repaint unaccepted
  live-edit characters after `0x8a`. QEMU batch `input_refresh_status_001`
  matched the baseline and erase cases but mismatched the refresh case. Row
  counts showed the baseline row had color-15 glyph pixels while both the
  erase and failed refresh captures had zero color-15 pixels in logical Y
  40..47.
- Corrected the refresh case to type `look` plus Enter before checking `0x89`.
  This matches the disassembly: Enter copies visible buffer `0x0fa4` into
  source buffer `0x0fce`, clears visible length `[0x0ff8]`, and redraws; the
  normal EGA `0x89` path then copies from `0x0fce` back into `0x0fa4`.
- QEMU batch `input_refresh_status_002` matched with 3 matches, 0 mismatches,
  and 0 errors. This promotes actions `0x89` (`refresh_input_line`) and
  `0x8a` (`erase_input_line`) to behavior-level QEMU-validated evidence for
  the observed EGA path.
- Added QEMU case `status_line_show_draws_configured_row`. The fixture
  configures status row 5 through `0x6f(0, 0, 5)`, runs `0x70`, and checks for
  visible color-15 pixels in logical Y 40..47. QEMU batch `status_show_001`
  matched with 1 match, 0 mismatches, and 0 errors, promoting action `0x70`
  (`show_status_line_like`) to behavior-level QEMU-validated evidence.
- Updated `tools/logic_opcode_evidence.py`, regenerated
  `docs/src/logic_opcode_evidence.md`, and updated opcode, runtime,
  compatibility, symbolic-label, and tracker docs.
- Updated `PROGRESS.md`: logic action opcode coverage is now 166 of 176 at
  `[x]` level (`165` QEMU-validated plus structural `0x00`), with 10 partial
  action opcodes remaining.

## 2026-07-04: enabled trace-window validation

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `rg -n "trace_window|0x95|0x96|1d10|1d08|1d0a" tools/logic_interpreter_probe.py docs/src/logic_bytecode.md docs/src/clean_room_executable_notes.md docs/src/symbolic_labels.md PROGRESS.md`
- `sed -n` reads of `tools/logic_interpreter_probe.py`,
  `tests/test_logic_interpreter_probe.py`, `docs/src/logic_bytecode.md`,
  `docs/src/symbolic_labels.md`, `docs/src/runtime_model.md`,
  `docs/src/compatibility_testing.md`, `PROGRESS.md`, and this notes file.
- `ndisasm -b 16 -o 0x8c91 -e 0x8e91 build/cleanroom/AGI.decrypted.exe`
  during the preceding trace inspection pass.
- Focused unit tests:
  `python3 -B -m unittest tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_base_cases_cover_core_control_flow tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_trace_window_rect_check_tracks_source_bounds tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_rect_checks_can_match_without_glyph_model tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_rect_checks_report_mismatch`
- First enabled trace QEMU run:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix TR --output build/logic-interpreter-probes/batches/trace_window_enable_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case trace_window_enable_draws_box_when_flag10_set`
- Capture inspection:
  `python3 -B tools/inspect_ppm.py build/logic-interpreter-probes/fixtures/trace_window_enable_draws_box_when_flag10_set/qemu_capture.ppm`
- Local downsample/color-count script over the same PPM capture.
- `magick build/logic-interpreter-probes/fixtures/trace_window_enable_draws_box_when_flag10_set/qemu_capture.ppm build/logic-interpreter-probes/fixtures/trace_window_enable_draws_box_when_flag10_set/qemu_capture.png`
- Stricter focused unit rerun, same unittest command as above.
- Final enabled trace QEMU run:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix TR --output build/logic-interpreter-probes/batches/trace_window_enable_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case trace_window_enable_draws_box_when_flag10_set`
- `python3 -B tools/logic_opcode_evidence.py`

Results:

- Re-read the trace action pair from disassembly. Handler `0x95` at image
  `0x8c91` either consumes an extra byte when trace state `[0x1d10]` is already
  nonzero, or calls helper `0x8cae` to enable the trace window only if flag 10
  is set. Handler `0x96` at image `0x8d3d` stores trace logic/resource,
  row-offset, and height globals in `[0x1d12]`, `[0x1d08]`, and `[0x1d0a]`,
  clamping height upward to at least 2.
- Added QEMU case `trace_window_enable_draws_box_when_flag10_set`. The fixture
  configures the base text row with `0x6f(0, 0, 5)`, configures the trace window
  with `0x96(0, 1, 2)`, sets flag 10, and runs `0x95` as a one-shot path so the
  repeated-active `SI + 1` behavior cannot consume fixture bytes by accident.
- The first enabled trace run matched a broad white-window check. Inspection of
  the capture showed the original engine draws a red-bordered, white-filled
  trace box with black text such as `0: 12(94)`. The downsampled capture has
  red border pixels around logical row 5, large white fill through the trace
  window, and black glyph pixels in rows 18..30.
- Tightened the case to require all three visible signals: red border, white
  fill, and black trace text. QEMU batch `trace_window_enable_002` matched with
  1 match, 0 mismatches, and 0 errors.
- Promoted actions `0x95` (`enable_action_trace_window`) and `0x96`
  (`configure_action_trace_window`) from QEMU dispatch-smoke to behavior-level
  QEMU-validated evidence. The older flag-clear case remains useful as gated
  no-draw coverage.
- Updated `tools/logic_opcode_evidence.py`, regenerated
  `docs/src/logic_opcode_evidence.md`, and updated opcode, runtime,
  compatibility, symbolic-label, and tracker docs.
- Updated `PROGRESS.md`: logic action opcode coverage is now 168 of 176 at
  `[x]` level (`167` QEMU-validated plus structural `0x00`), with 8 partial
  action opcodes remaining.

## 2026-07-04: input-width flag and inactive close-window cleanup probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "Highest-Value|Remaining|0x6e|0x83|0x8e|0xa3|0xa4|0xa9|0xaa|0xad" PROGRESS.md docs/src/logic_bytecode.md docs/src/runtime_model.md docs/src/symbolic_labels.md tools/logic_interpreter_probe.py tools/logic_opcode_evidence.py`
- `sed -n` reads of `PROGRESS.md`, `docs/src/logic_bytecode.md`,
  `docs/src/runtime_model.md`, `docs/src/symbolic_labels.md`,
  `docs/src/compatibility_testing.md`, `tools/logic_interpreter_probe.py`,
  `tests/test_logic_interpreter_probe.py`, `tools/qemu_snapshot.py`, and this
  notes file.
- `ndisasm -b 16 -o 0x3652 -e 0x3852 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x3939 -e 0x3b39 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x1f2b -e 0x212b build/cleanroom/AGI.decrypted.exe`
- Focused unit tests:
  `python3 -B -m unittest tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_base_cases_cover_core_control_flow tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_input_width_flag_cases_have_distinct_row_checks tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_rect_checks_can_match_without_glyph_model tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_rect_checks_report_mismatch`
- First QEMU attempt with a visible long slot-0 prefix:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix IW --output build/logic-interpreter-probes/batches/input_width_flag_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_width_flag_a3_allows_long_live_input --case input_width_flag_a4_restores_long_slot_limit --case close_text_window_state_clears_input_width_flag`
- Capture/report inspections using `python3 -B tools/inspect_ppm.py` and local
  downsample/color-count scripts over the generated `input_width_flag_*`
  fixture captures.
- Second QEMU attempt with a long blank slot-0 prefix:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix IW --output build/logic-interpreter-probes/batches/input_width_flag_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_width_flag_a3_allows_long_live_input --case input_width_flag_a4_restores_long_slot_limit --case close_text_window_state_clears_input_width_flag`
- Third QEMU attempt with the check moved to the wrapped row:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix IW --output build/logic-interpreter-probes/batches/input_width_flag_003.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_width_flag_a3_allows_long_live_input --case input_width_flag_a4_restores_long_slot_limit --case close_text_window_state_clears_input_width_flag`
- Final QEMU batch:
  `python3 -B tools/logic_interpreter_probe.py --dos-prefix IW --output build/logic-interpreter-probes/batches/input_width_flag_004.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_width_flag_a3_allows_long_live_input --case input_width_flag_a4_restores_long_slot_limit --case close_text_window_state_clears_input_width_flag`
- `python3 -B tools/logic_opcode_evidence.py`

Results:

- Re-read `code.input.handle_input_char` (`0x3652`). At entry it computes a
  live-input cap in `DI`: if word `[0x0d0f]` is nonzero it uses `0x24`;
  otherwise it computes `0x28 - strlen(0x020d)`, where `0x020d` is fixed string
  slot 0. The prompt marker byte can reduce this by one, and byte `[0x21]`
  applies another cap. The printable-character path appends to visible buffer
  `0x0fa4` only while current visible length `[0x0ff8]` is below this cap.
- Re-read action `0xa3` at `0x3939`: it sets word `[0x0d0f] = 1` and returns
  the current bytecode pointer. Action `0xa4` at `0x394b` clears the same word.
- Re-read action `0xa9` at `0x1f2b`: if word `[0x0d1d]` is nonzero, it restores
  saved display rectangle `[0x0d23]`/`[0x0d25]` through helper `0x560c`, then
  clears both `[0x0d0f]` and `[0x0d1d]`. The QEMU case below validates the
  unconditional `[0x0d0f]` clear with no active saved window; the active
  rectangle restore remains source-backed from this disassembly.
- Added cases `input_width_flag_a3_allows_long_live_input`,
  `input_width_flag_a4_restores_long_slot_limit`, and
  `close_text_window_state_clears_input_width_flag`.
- First attempt used a visible 38-character string slot 0. `0xa3` matched, but
  `0xa4` mismatched because the long prefix itself painted many white pixels on
  the input row, masking the accepted-input distinction.
- Second attempt changed slot 0 to 38 spaces. This removed the visible prefix
  glyphs, but QEMU showed the typed characters wrapping into logical rows
  48..55, not rows 40..47.
- Third attempt checked for white pixels on the wrapped row. `0xa3` matched,
  but `0xa4` still mismatched because the wrapped row is blank white fill even
  without accepted typed glyphs.
- Final attempt checked for black glyph pixels inside logical rows 48..55.
  With `0xa3`, accepted typed characters create black glyph pixels in that
  white-filled wrapped row. With `0xa4`, and with `0xa9` after `0xa3`, the same
  row remains blank white fill with no black glyph signal.
- QEMU batch `input_width_flag_004` matched 3/3 with 0 mismatches and 0 errors.
  This promotes `0xa3` and `0xa4` to behavior-level QEMU evidence for the
  input-width flag and promotes `0xa9` for the inactive-window unconditional
  flag-clear side.
- Updated `tools/logic_opcode_evidence.py`, regenerated
  `docs/src/logic_opcode_evidence.md`, and updated opcode, runtime,
  compatibility, symbolic-label, and tracker docs.
- Updated `PROGRESS.md`: logic action opcode coverage is now 171 of 176 at
  `[x]` level (`170` QEMU-validated plus structural `0x00`), with 5 partial
  action opcodes remaining.

## 2026-07-04: action `0x83` direction-mirror timing

Commands:

- `rg -n "0139|0x0139|clear_global_0139|set_global_0139|field_22|object0|first object" ...`
- `ndisasm -b 16 -o 0x702f -e 0x722f build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x0150 -e 0x0350 build/cleanroom/AGI.decrypted.exe | sed -n '1,90p'`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix L83 --output build/logic-interpreter-probes/batches/object0_direction_mirror_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_global_0139_allows_object0_direction_to_seed_global`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix L83 --output build/logic-interpreter-probes/batches/object0_direction_mirror_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_global_0139_allows_object0_direction_to_seed_global`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix L83 --output build/logic-interpreter-probes/batches/object0_direction_mirror_003.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_global_0139_allows_object0_direction_to_seed_global`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix L83 --output build/logic-interpreter-probes/batches/object0_direction_mirror_004.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case clear_global_0139_allows_object0_direction_to_seed_global`
- `python3 -B tools/logic_interpreter_probe.py --cases build/logic-interpreter-probes/manual_direction_value_cases.json --dos-prefix L8D --output build/logic-interpreter-probes/batches/object0_direction_value_diag_001.json --boot-wait 5 --draw-wait 8 --case diagnostic_object0_direction_value_after_0139_mirror`
- `python3 -B tools/logic_interpreter_probe.py --cases build/logic-interpreter-probes/manual_direction_phase_cases.json --dos-prefix L8P --output build/logic-interpreter-probes/batches/object0_direction_phase_diag_001.json --boot-wait 5 --draw-wait 8 --case diagnostic_object0_direction_phase2_reached`
- `python3 -B tools/logic_interpreter_probe.py --cases build/logic-interpreter-probes/manual_direction_active_cases.json --dos-prefix L8A --output build/logic-interpreter-probes/batches/object0_direction_active_diag_001.json --boot-wait 5 --draw-wait 8 --case diagnostic_object0_active_direction_phase2`

Observations:

- Action `0x83` at image `0x702f` is a tiny handler: it stores word
  `[0x0139] = 0` and returns the current bytecode pointer.
- Action `0x84` at image `0x7041` stores word `[0x0139] = 1` and clears byte
  `+0x22` on the first object entry.
- `code.engine.main_cycle` uses `[0x0139]` before logic execution. When the
  word is zero, it copies first-object direction byte `+0x21` to global byte
  `[0x000f]`. When the word is nonzero, it copies `[0x000f]` back to first
  object byte `+0x21`.
- The same main-cycle source later writes `[0x000f]` back to first-object
  `+0x21` after the logic-0 call returns. This means a logic script that sets
  object0 byte `+0x21` after the pre-logic mirror is too late to seed
  `[0x000f]` for the next cycle by itself.
- Several attempted permanent QEMU fixtures tried to set object0 byte `+0x21`
  to `6`, execute `0x83`, wait a cycle, execute `0x84`, and then read byte
  `+0x21` through `0x57`. These did not validate the intended model:
  `object0_direction_mirror_001..004` mismatched or produced no validation
  marker.
- Disposable diagnostics confirmed the phase scaffolding reached phase 2, but
  the observed object0 direction after the sequence was `0`, not `6`. Activating
  object0 during the seed phase did not change that result.
- Conclusion: `0x83` should be specified from source as the selector clear for
  the pre-logic object0/global direction mirror. A script-level QEMU fixture is
  not a clean validation shape because the relevant branch point happens before
  logic bytecode runs, and cycle-end restoration can clobber script-written
  object0 direction bytes.
- Removed the attempted reusable `clear_global_0139_allows_object0_direction_to_seed_global`
  fixture from `tools/logic_interpreter_probe.py` after the diagnostics showed
  it was testing the wrong timing point.
- Updated `tools/logic_opcode_evidence.py`, regenerated
  `docs/src/logic_opcode_evidence.md`, and updated opcode, runtime,
  compatibility, symbolic-label, and tracker docs.
- Updated `PROGRESS.md`: logic action opcode coverage is now 172 of 176 at
  `[x]` level (`170` QEMU-validated, structural `0x00`, and source-backed
  `0x83`), with 4 partial action opcodes remaining.

## 2026-07-04: action `0xad` key-release enqueue gate

Commands:

- `rg -n "0xad|increment_global_1530|1530|0x1530|Highest-Value|\\[~\\]" PROGRESS.md docs/src/logic_bytecode.md docs/src/runtime_model.md docs/src/symbolic_labels.md docs/src/clean_room_executable_notes.md tools/logic_opcode_evidence.py tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py`
- `ndisasm -b 16 -o 0x6000 -e 0x6200 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `rizin -q -c "/x 3015" -c q build/cleanroom/AGI.decrypted.exe`
- `rizin -q -c "/x 1915" -c "/x 3015" -c "/x 2f15" -c q build/cleanroom/AGI.decrypted.exe`
- `rg -n "44a9|code\\.event|enqueue|event queue|keyboard|raw event|type-2|type 2|0x44a9" docs/src/symbolic_labels.md docs/src/logic_bytecode.md docs/src/runtime_model.md docs/src/clean_room_executable_notes.md`

Observations:

- Action `0xad` at image `0x602f` consists of `inc byte [0x1530]`, then
  returns the current bytecode pointer.
- Local byte-pattern searches found only the action increment and the keyboard
  IRQ hook test of `[0x1530]`.
- The keyboard IRQ hook at image `0x6036` stores the raw scan byte in
  `[0x152f]`, maps scan codes `0x47..0x51` to an index by subtracting `0x47`,
  checks enable table `[0x1519 + index]`, and tracks press/release state in
  `[0x1524 + index]`.
- On release (`scan & 0x80` set), if the latch was set, the hook clears the
  latch and tests byte `[0x1530]`. If the gate is nonzero, it calls
  `code.input.enqueue_event` (`0x44a9`) with `(type=2, value=0)`.
- On press, if no latch is set for that index, the hook clears the latch table
  range and increments the selected `[0x1524 + index]` latch.
- Conclusion: `0xad` is a source-backed input/keyboard action. It increments a
  nonzero gate that allows selected tracked-key releases to enqueue a type-2
  zero event from the interrupt hook. A QEMU fixture for this would depend on
  raw scan-code press/release timing and is less appropriate than direct source
  evidence for the current spec target.
- Updated `tools/logic_opcode_evidence.py`, regenerated
  `docs/src/logic_opcode_evidence.md`, and updated opcode, runtime,
  compatibility, symbolic-label, and tracker docs.
- Updated `PROGRESS.md`: logic action opcode coverage is now 173 of 176 at
  `[x]` level (`170` QEMU-validated, structural `0x00`, and source-backed
  `0x83`/`0xad`), with 3 partial action opcodes remaining.

## 2026-07-04: action `0x8e` event-pair capacity reset

Commands:

- `rg -n "0x8e|set_global_0141|pair_capacity|0x0141|data.event.pair_capacity|reset_pair_buffer|event buffer|resource-event|replay" PROGRESS.md docs/src/logic_bytecode.md docs/src/runtime_model.md docs/src/symbolic_labels.md docs/src/compatibility_testing.md docs/src/clean_room_executable_notes.md tools/logic_opcode_evidence.py tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py`
- `ndisasm -b 16 -o 0x7140 -e 0x7220 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x7060 -e 0x7130 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`

Observations:

- Action `0x8e` at image `0x716a` reads one immediate byte, writes it to
  `data.event.pair_capacity` (`[0x0141]`), calls an update-list flush helper,
  calls `code.event.reset_pair_buffer`, calls the matching update-list rebuild
  helper, and returns the advanced bytecode pointer.
- `code.event.reset_pair_buffer` checks `data.event.pair_capacity`. If the
  capacity is positive and no pair buffer exists, it allocates
  `capacity * 2` bytes, stores the resulting pointer in
  `data.event.pair_buffer_base` (`[0x1707]`), and initializes allocator state.
  It then sets `data.event.pair_buffer_write` (`[0x1709]`) to the base pointer
  and clears `data.event.pair_count` (`[0x0143]`).
- Existing replay-source and QEMU work already validates downstream pair-log
  semantics for `0xab`/`0xac` rollback and display-mode/restore replay. The
  `0x8e` action itself is compact enough to cover from source as the capacity
  and reset entry point for that same log.
- Updated `tools/logic_opcode_evidence.py`, regenerated
  `docs/src/logic_opcode_evidence.md`, and updated opcode, runtime,
  compatibility, symbolic-label, and tracker docs.
- Updated `PROGRESS.md`: logic action opcode coverage is now 174 of 176 at
  `[x]` level (`170` QEMU-validated, structural `0x00`, and source-backed
  `0x83`/`0x8e`/`0xad`), with 2 partial action opcodes remaining.

## 2026-07-04: action `0xaa` save-description buffer copy

Commands:

- `rg -n "0xaa|copy_save_description|0x0e72|0e72|save description|description buffer|select_slot|0x2726|0x4de8|0x7d|0x7e" PROGRESS.md docs/src/logic_bytecode.md docs/src/runtime_model.md docs/src/symbolic_labels.md docs/src/compatibility_testing.md docs/src/clean_room_executable_notes.md tools/logic_opcode_evidence.py tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py`
- `ndisasm -b 16 -o 0x2700 -e 0x2860 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x4d80 -e 0x4e40 build/cleanroom/AGI.decrypted.exe | sed -n '1,160p'`

Observations:

- Action `0xaa` at image `0x2726` reads one immediate string-slot index,
  computes destination `0x020d + index * 0x28`, and copies up to `0x1f` bytes
  from runtime buffer `[0x0e72]` through the shared bounded-copy helper.
- Save and restore handlers test byte `[0x0e72]` after `code.save.select_slot_or_path`
  returns, so this buffer is populated by save/restore selector state rather
  than by static resource data.
- Earlier attempted QEMU fixture `save_description_copy_001` patched
  `AGIDATA.OVL` bytes at offset `0x0e72` to `look`, then tried to compare the
  copied string slot against a message string. The validation draw did not
  occur even though the fixture file contained the bytes. This is now
  explained as a fixture-shape problem: action `0xaa` reads the interpreter's
  runtime data segment at `[0x0e72]`, not the fixture file's static overlay
  bytes.
- Dynamic validation remains possible but should drive the real save/restore
  selector path that fills the runtime description buffer. The action itself is
  compact and is now covered as source-backed.
- Updated `tools/logic_opcode_evidence.py`, regenerated
  `docs/src/logic_opcode_evidence.md`, and updated opcode, runtime,
  compatibility, symbolic-label, and tracker docs.
- Updated `PROGRESS.md`: logic action opcode coverage is now 175 of 176 at
  `[x]` level (`170` QEMU-validated, structural `0x00`, and source-backed
  `0x83`/`0x8e`/`0xaa`/`0xad`), with only `0x6e` partial.

## 2026-07-04: action `0x6e` screen-shake source pass

Commands:

- `rg -n "0x6e|shake_screen|screen_shake|shake|0x6e\\b|screen-shake|display offset|0x1379|0x112e|0x1130" PROGRESS.md docs/src/logic_bytecode.md docs/src/runtime_model.md docs/src/symbolic_labels.md docs/src/compatibility_testing.md docs/src/clean_room_executable_notes.md tools/logic_opcode_evidence.py tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py`
- `ndisasm -b 16 -o 0x79c0 -e 0x7b60 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `rizin -q -c "/x 7a17" -c "/x 7913" -c "/x 6513" -c "/x 7917" -c q build/cleanroom/AGI.decrypted.exe`

Observations:

- Action `0x6e` reads one immediate count byte into `CL` and advances the
  bytecode pointer before doing the display work.
- Display mode `[0x1130] == 3`, `2`, or `4` delegates to display/overlay helper
  paths observed at `0x99b8`, `0x9be3`, and `0x9916`.
- The normal path sets byte `[0x1779]` to `0x70` when hardware selector
  `[0x112e] == 0`, otherwise to `0x38`.
- It writes CRT controller registers via ports `0x3d4` and `0x3d5`: register
  `0x02` receives a byte from table `0x177a` plus `[0x1365]`; register `0x07`
  receives the following table byte plus `[0x1779]`.
- After each register-pair write, it waits for timer word `[0x0129]` to change.
  It advances through table pairs until the register-7 value returns to the
  base `[0x1779]`, then repeats for the requested count.
- Existing QEMU case `screen_shake_dispatch_smoke` validates that a one-count
  action returns to following bytecode. A screenshot-after-return fixture cannot
  capture the transient register animation reliably, so the timing/display
  effect is source-backed.
- Updated `tools/logic_opcode_evidence.py`, regenerated
  `docs/src/logic_opcode_evidence.md`, and updated opcode, runtime,
  compatibility, symbolic-label, and tracker docs.
- Updated `PROGRESS.md`: all 176 logic action opcodes are now covered at `[x]`
  level (`170` QEMU-validated, structural `0x00`, and source-backed
  `0x6e`/`0x83`/`0x8e`/`0xaa`/`0xad`).

## 2026-07-04: menu navigation source-table refinement

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x93d1 -e 0x95d1 build/cleanroom/AGI.decrypted.exe`
- `xxd -g 2 -s 0x16b3 -l 0x50 SQ2/AGIDATA.OVL`
- `sed -n '2140,2255p' tools/logic_interpreter_probe.py`
- `sed -n '1088,1178p' docs/src/logic_bytecode.md`

Documented result:

- Re-read `code.menu.interact` (`0x93d1`) and its type-2 movement dispatch
  table at image `0x9526`. The eight little-endian target words are `0x9492`,
  `0x94a6`, `0x94b2`, `0x94cb`, `0x94da`, `0x94e5`, `0x94f6`, and `0x9509`.
- Confirmed from `SQ2/AGIDATA.OVL` that the raw movement table rooted at
  `0x16b3` maps BIOS-style key words `0x4800`, `0x4900`, `0x4d00`, `0x5100`,
  `0x5000`, `0x4f00`, `0x4b00`, and `0x4700` to movement values `1..8`.
- Refined the menu/navigation prose: item movement branches select previous,
  first, last, or next item nodes directly and do not skip disabled item nodes.
  The item enable word is tested only by the Enter branch before enqueueing a
  type-3 selection event. Heading left/right movement skips disabled headings,
  while root/last-heading jumps select the root or root-previous heading
  directly.
- Added symbolic label `table.menu.navigation_dispatch` and split
  `data.menu.heading_root`, `data.menu.current_heading`, and
  `data.menu.current_item` so future interpreter-version comparisons do not
  depend on the SQ2 addresses alone.

## 2026-07-04: menu interaction state-machine source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1140,1225p' docs/src/logic_bytecode.md`
- `sed -n '5800,5865p' docs/src/clean_room_executable_notes.md`
- `sed -n '244,274p' docs/src/symbolic_labels.md`
- `ndisasm -b 16 -o 0x93d1 -e 0x95d1 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x911d -e 0x931d build/cleanroom/AGI.decrypted.exe`
- `xxd -g 2 -s 0x16b0 -l 0x60 SQ2/AGIDATA.OVL`

Documented result:

- Re-read the setup handlers at `0x911d`, `0x91cf`, and `0x92ba`, the
  enable/disable helper at `0x935f`, and the modal interaction loop at
  `0x93d1`.
- Converted the source observations into an implementation-facing menu data
  model in `docs/src/runtime_model.md`: 18-byte circular heading nodes,
  14-byte circular item nodes, global root/current pointers, finalization, and
  the interaction request word.
- Documented the modal interaction lifecycle. `0xa1` only requests the menu
  when flag 14 is set. `code.menu.interact` waits through the shared event
  helpers, treats event type 1 as Enter/Escape, treats event type 2 as movement
  values `1..8`, and persists the current heading/item before looping.
- Confirmed the Enter semantics from source and existing QEMU probes: enabled
  items enqueue a type-3 status event with the item id, disabled items continue
  waiting, and Escape exits without enqueueing a selection. Dynamic arrow-key
  validation remains a compatibility-suite gap, but the movement semantics are
  source-backed from `table.menu.navigation_dispatch` and the AGIDATA raw-key
  table.

## 2026-07-04: picture scanner command-resume fuzz expansion

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "base_0|corner|f4|f5|interleav|random|pattern|seed_fill|draw_corner" tools/picture_fuzz.py tests/test_picture_fuzz.py tests/test_graphics_rendering.py`
- `sed -n '1,260p' tools/picture_fuzz.py`
- `sed -n '1,430p' tests/test_graphics_rendering.py`
- `python3 -B -m unittest tests.test_graphics_rendering tests.test_picture_fuzz`
- `python3 -B tools/picture_fuzz.py generate --count 1024 --seed 4097 --output build/picture-fuzz/corpus --clean`
- `python3 -B tools/picture_fuzz.py batch-qemu --snapshot --case base_030_line_pair_command_resume --case base_031_corner_command_resume --case base_032_fill_command_resume --dos-prefix FR --fixture-root build/picture-fuzz/fixtures --output build/picture-fuzz/batches/command_resume_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`

Documented result:

- Added three safe curated picture fuzz cases. They exercise the common
  coordinate/list-reader rule that a byte above `0xef` terminates the active
  drawing command and remains pending for the scanner.
- Added local renderer tests for an incomplete absolute-line coordinate pair
  terminated by command `0xf0`, a Y-first corner path terminated after one
  segment by command `0xf0`, and a seed-fill point list terminated by command
  `0xf0`.
- Regenerated the corpus with 1,057 cases, of which 1,055 are safe for QEMU.
  The two unsafe cases remain out-of-spec guardrails for over-read behavior.
- QEMU snapshot batch `command_resume_001` matched all three new cases with
  0 mismatches, promoting this scanner-resume behavior to original-engine
  compatibility evidence.

## 2026-07-04: timed view/object carousel harness

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,280p' tools/view_batch.py`
- `sed -n '1,320p' tools/picture_carousel.py`
- `sed -n '1,260p' tests/test_view_batch.py`
- `sed -n '1,980p' tools/qemu_fixture.py`
- `sed -n '1,620p' tests/test_qemu_fixture.py`
- `python3 -B -m unittest tests.test_qemu_fixture tests.test_view_batch tests.test_view_carousel`
- `python3 -B tools/view_carousel.py --case view_011_normal_mid --case view_000_group1_mirrored_mid --fixture-root build/view-carousel/smoke-fixtures --dos-dir VCARSMK --output build/view-carousel/batches/view_carousel_smoke_001.json --boot-wait 5 --first-wait 3 --delay-cycles 120 --speed-value 1 --poll-interval 0.5 --poll-timeout 20`
- `python3 -B tools/view_carousel.py --fixture-root build/view-carousel/base-fixtures --dos-dir VCARBASE --output build/view-carousel/batches/view_carousel_base_001.json --boot-wait 5 --first-wait 3 --delay-cycles 120 --speed-value 1 --poll-interval 0.5 --poll-timeout 20`
- `python3 -B tools/view_carousel.py --include-stress --fixture-root build/view-carousel/stress-fixtures --dos-dir VCARSTR --output build/view-carousel/batches/view_carousel_stress_001.json --boot-wait 5 --first-wait 3 --delay-cycles 120 --speed-value 1 --poll-interval 0.5 --poll-timeout 20`

Documented result:

- Added `view_timed_carousel_logic_payload` and
  `build_view_timed_carousel_fixture` to `tools/qemu_fixture.py`. The fixture
  packs generated `LOGIC.0`, selected picture resources, and selected view
  resources into `VOL.3` and patches `PICDIR`, `VIEWDIR`, and `LOGDIR`.
- Added `tools/view_carousel.py`, a timed polling QEMU harness for
  picture-plus-view cases. It keeps one original-engine process running,
  refreshes the picture and transient object after a cycle delay, and polls
  `screendump` output until the expected local comparison matches.
- Added local tests for the new logic payload, packed fixture layout, runner
  naming/report behavior, and mocked runner flow.
- The first sandboxed QEMU attempt failed because QEMU could not bind the local
  VNC socket; rerunning with the approved `python3 -B tools/view_carousel.py`
  command prefix allowed the local socket bind.
- QEMU `view_carousel_smoke_001` matched two cases, `view_carousel_base_001`
  matched all 8 current base view cases, and `view_carousel_stress_001` matched
  all 19 current base-plus-stress cases with 0 mismatches and 0 errors from one
  original-engine process.

## 2026-07-04: picture/view runtime contract synthesis

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '230,295p' docs/src/compatibility_testing.md`
- `sed -n '1008,1024p' docs/src/compatibility_testing.md`
- `sed -n '1216,1230p' docs/src/compatibility_testing.md`
- `sed -n '383,398p' PROGRESS.md`

Documented result:

- Added implementation-facing picture decoder lifecycle text to
  `docs/src/runtime_model.md`, covering cache selection, fresh versus overlay
  decode, scanner command/data behavior, draw-state channels, seed-fill
  contract, and display finalization.
- Added implementation-facing view/cel drawing contract text to
  `docs/src/runtime_model.md`, covering payload layout, row runs,
  bit-`0x80` orientation rewrite, baseline placement, priority/control gating,
  pixel writes, and transient versus persistent object use.
- Updated `PROGRESS.md` so picture/view implementation text is no longer listed
  as the main renderer gap; remaining renderer work is now broader
  priority/control, animation, future edge probes, and cross-version/resource
  parity.

## 2026-07-04: parser wildcard and terminator probes

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/inspect_words.py --prefix look --limit 20`
- `python3 -B tools/inspect_words.py --prefix around --limit 20`
- `python3 -B tools/inspect_words.py --prefix get --limit 20`
- `sed -n '1240,1310p' tools/logic_interpreter_probe.py`
- `python3 -B -m unittest tests.test_logic_interpreter_probe.LogicInterpreterProbeTests.test_base_cases_cover_core_control_flow`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix PW --output build/logic-interpreter-probes/batches/parser_edges_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_word_sequence_matches_two_words --case input_word_sequence_wildcard_matches_word --case input_word_sequence_terminator_accepts_prefix`

Documented result:

- Confirmed from the local `WORDS.TOK` decoder that `look` maps to word ID
  `0x0002` and `get` maps to word ID `0x0005`. The word `around` maps to
  `0x0000`, so it was not used as the positive edge probe.
- Added three `tools/logic_interpreter_probe.py` cases. They parse message
  string `look get` with action `0x75`, then test condition `0x0e` for exact
  two-word matching, wildcard word ID `0x0001`, and terminator word ID
  `0x270f`.
- QEMU batch `parser_edges_001` matched all three cases with 0 mismatches. The
  runtime model now treats the wildcard and terminator behavior as
  QEMU-backed, not merely source-backed.

## 2026-07-04: object placement spiral source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x593a -e 0x5b3a build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x56b8 -e 0x58b8 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `rg -n '0x593a|0x56b8|placement|right-edge|right edge|baseline `67`|baseline_y=67|expected_baseline_y=67|place' docs/src/graphics_object_pipeline.md docs/src/clean_room_executable_notes.md docs/src/symbolic_labels.md tools/object_overlay_probe.py tests/test_object_overlay_probe.py`
- Local simulation of the `0x593a` movement sequence for view 11/group 0/frame
  0 at requested placements `(20, 2)`, `(0, 80)`, and `(154, 80)`.
- `python3 -B -m unittest tests.test_graphics_rendering tests.test_object_overlay_probe`
- `python3 -B -m unittest tests.test_view_batch`
- Compared existing QEMU captures for `top_clip_view11_priority15` and
  `right_clip_view11_priority15` against the updated local model.

Documented result:

- Re-read placement helper `code.object.place` (`0x593a`). It tests the initial
  object position with bounds helper `0x5a14`, object collision helper
  `0x4719`, and control/priority acceptance helper `0x56b8`. If the position
  fails, it searches in a widening spiral.
- The source movement sequence is `left 1`, `down 1`, `right 2`, `up 2`,
  `left 3`, `down 3`, `right 4`, `up 4`, and so on. The candidate is tested
  before each move.
- Added `search_object_placement()` and `placement_bounds_ok()` to
  `tools/agi_graphics.py` for the bounds-only portion of this source model.
  The helper reproduces the previously QEMU-observed top-edge placement
  `(18, 4)` and right-edge placement `(140, 67)` for view 11/group 0/frame 0,
  and reproduces horizon clamping to `[0x012d] + 1` when bit `0x0008` is not
  modeled as set.
- Updated `tools/object_overlay_probe.py` so ordinary top/right expected
  positions are derived from the placement search instead of hard-coded in the
  case registry. Existing QEMU captures for both edge cases still compare with
  0 mismatches.
- Updated object-pipeline, compatibility, symbolic-label, progress-tracker, and
  unit-test coverage. Collision/control rejection can extend the search beyond
  the first bounds-acceptable candidate, so those cases remain future work.

## 2026-07-04: picture seed-fill span-stack source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x533b -e 0x533b build/cleanroom/AGI.decrypted.exe`
- `sed -n '185,220p' docs/src/graphics_object_pipeline.md`
- `sed -n '770,790p' docs/src/compatibility_testing.md`
- `sed -n '968,984p' docs/src/compatibility_testing.md`
- `sed -n '88,118p' docs/src/symbolic_labels.md`
- `sed -n '2415,2490p' docs/src/clean_room_executable_notes.md`

Rejected or limited evidence:

- The broad disassembly command above printed far past the seed-fill helper,
  so only the known helper body around `code.picture.seed_fill` and the
  pre-existing focused seed-fill notes were used as evidence for this pass.

Documented result:

- Re-read the seed-fill helper enough to make the implementation-facing contract
  sharper. The helper chooses exactly one expansion test channel per seed:
  visual low nibble first when visual drawing is active, otherwise control high
  nibble when control drawing is active.
- Confirmed the early exits: no active drawing channel, selected visual value
  equal to the visual default target, selected control value equal to the
  control default target, or a seed cell that does not match the selected
  default target.
- Confirmed that accepted pixels still use the normal active draw byte and
  odd/even masks, so both logical nibbles can change even though only one
  channel controls expansion.
- Documented the SQ2 traversal class as a stack-backed horizontal span fill.
  It fills the current row left/right, records span state in the scratch block
  around `0x126c..0x1279`, scans adjacent rows in a current vertical direction,
  pushes deferred branch spans on the CPU stack, reverses direction when needed,
  and terminates after popping the sentinel row state.
- Added conservative symbolic label `data.picture.seed_fill_span_scratch`
  instead of naming each byte in the scratch block prematurely.
- Updated compatibility notes to say the remaining seed-fill work is broadened
  parity coverage for barriers, odd/even masks, and multi-seed cases, not
  unknown traversal class.

## 2026-07-04: seed-fill fuzz case expansion

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "base_0|visual_fill|seed|fill|cases|safe_for_qemu" tools/picture_fuzz.py tests/test_picture_fuzz.py tests/test_graphics_rendering.py`
- `sed -n '1,260p' tests/test_picture_fuzz.py`
- `sed -n '1,260p' tools/picture_fuzz.py`
- `sed -n '1,240p' tools/agi_graphics.py`
- `sed -n '115,160p' tests/test_graphics_rendering.py`
- `python3 -B -m unittest tests.test_graphics_rendering tests.test_picture_fuzz`
- `python3 -B tools/picture_fuzz.py generate --count 8 --seed 4097 --output build/picture-fuzz/seed-fill-cases --clean`
- `python3 -B tools/picture_fuzz.py batch-qemu --snapshot --corpus build/picture-fuzz/seed-fill-cases --fixture-root build/picture-fuzz/seed-fill-fixtures --case base_021_visual_fill_full_height_barrier --case base_022_visual_fill_multi_seed_boxes --case base_023_control_fill_ignores_visual_barrier --dos-prefix SF --output build/picture-fuzz/batches/seed_fill_edges_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `cat build/picture-fuzz/batches/seed_fill_edges_001.json`
- `python3 -B tools/picture_fuzz.py generate --count 1024 --seed 4097 --output build/picture-fuzz/corpus --clean`

Rejected or limited evidence:

- The first QEMU batch attempt failed before any interpreter behavior was
  observed because sandboxed QEMU could not bind `127.0.0.1:5` for VNC. The
  same command was rerun with approved escalation and produced the evidence
  result below.

Documented result:

- Added safe curated fuzz cases:
  - `base_021_visual_fill_full_height_barrier`: a full-height one-pixel visual
    barrier blocks a visual seed fill.
  - `base_022_visual_fill_multi_seed_boxes`: one `0xf8` command contains two
    seed pairs and fills two isolated boxed regions.
  - `base_023_control_fill_ignores_visual_barrier`: a control-channel fill
    crosses a visual-only barrier because the selected expansion channel is
    control, while the visible barrier remains undisturbed.
- Added local renderer assertions for all three cases. The tests check final
  cell values rather than only screenshot hashes, including the control-channel
  crossing in `base_023`.
- Regenerated a small corpus; it reported 32 cases total, with 30 marked safe
  for QEMU. The standard 1,024-random corpus command reports 1,048 cases total
  and 1,046 safe cases.
- The QEMU snapshot batch `seed_fill_edges_001` matched the local renderer:
  3 matches, 0 mismatches, 0 errors, with each comparison covering 26,880
  logical pixels.

## 2026-07-04: optional view stress batch expansion

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "mirror|mirroring|transparent|cel|view" docs/src/graphics_object_pipeline.md docs/src/compatibility_testing.md PROGRESS.md tests/test_graphics_rendering.py tools/agi_graphics.py tools/view_batch.py`
- `sed -n '390,620p' tools/agi_graphics.py`
- `sed -n '520,620p' docs/src/graphics_object_pipeline.md`
- Local Python corpus scan over `VIEWDIR` frames to count frames, mirror-bit
  frames, transparent-color representatives, and largest cels.
- Local Python validation that selected stress cases fit within the screen at
  their chosen placements.
- `python3 -B -m unittest tests.test_view_batch tests.test_graphics_rendering`
- `python3 -B tools/view_batch.py --snapshot --include-stress --dos-prefix VXS --output build/view-batch/batches/view_stress_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `cat build/view-batch/batches/view_stress_001.json`

Documented result:

- Added `stress_cases()` to `tools/view_batch.py` and exposed it through
  optional CLI flag `--include-stress`. The default six-case view batch remains
  unchanged for quick smoke runs.
- The stress suite adds eleven cases selected from the local SQ2 view corpus:
  large cels, the 129-row tall cel, transparent colors `0`, `1`, `2`, `5`,
  `6`, `7`, `8`, `10`, `13`, `14`, and `15`, and a bit-`0x80` transparent-10
  frame.
- The local unit tests confirm that stress cases are optional and that the
  stress placements fit on screen.
- The QEMU snapshot run `view_stress_001` covered 17 cases total: the six
  existing base cases plus the eleven stress cases. All 17 matched with 0
  mismatches and 0 errors, each over 26,880 logical pixels.

## 2026-07-04: pattern and interleaved picture fuzz expansion

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "pattern|0x10|0x20|pattern_mode|base_02" tests/test_graphics_rendering.py tools/picture_fuzz.py docs/src/graphics_object_pipeline.md docs/src/compatibility_testing.md`
- `sed -n '245,270p' docs/src/graphics_object_pipeline.md`
- `sed -n '250,278p' tests/test_graphics_rendering.py`
- `python3 -B -m unittest tests.test_graphics_rendering tests.test_picture_fuzz`
- `python3 -B tools/picture_fuzz.py generate --count 1024 --seed 4097 --output build/picture-fuzz/corpus --clean`
- `python3 -B tools/picture_fuzz.py batch-qemu --snapshot --case base_024_pattern_bypass_mask --case base_025_interleaved_line_fill_pattern --case base_026_pattern_random_bypass_sequence --dos-prefix PF --output build/picture-fuzz/batches/pattern_interleaved_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `cat build/picture-fuzz/batches/pattern_interleaved_001.json`

Documented result:

- Added safe curated picture fuzz cases:
  - `base_024_pattern_bypass_mask`: isolates pattern mode bit `0x10` bypassing
    the row/column mask test.
  - `base_025_interleaved_line_fill_pattern`: draws a rectangle outline, fills
    it, draws a line through it, and overlays a pattern plot in one valid
    picture stream.
  - `base_026_pattern_random_bypass_sequence`: uses both mode bits `0x10` and
    `0x20` across two pseudo-random pattern plots.
- Added local renderer assertions for the first two cases. The mask-bypass test
  checks the expected 4-by-7 filled footprint for radius 3, and the interleaved
  test checks that later line and pattern commands overwrite earlier fill
  results sequentially.
- Regenerated the standard fuzz corpus. It now reports 1,051 cases total and
  1,049 safe for QEMU.
- The QEMU snapshot batch `pattern_interleaved_001` matched the local renderer:
  3 matches, 0 mismatches, 0 errors, with each comparison covering 26,880
  logical pixels.

## 2026-07-04: placement-search predicate hook clarification

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "0x4719|0x56b8|collision|control rejection|placement search|spiral|code.object.place|code.object.*collision|control-buffer" docs/src/graphics_object_pipeline.md docs/src/clean_room_executable_notes.md docs/src/symbolic_labels.md tools/agi_graphics.py tests/test_graphics_rendering.py tools/object_overlay_probe.py tests/test_object_overlay_probe.py`
- `ndisasm -b 16 -o 0x4719 -e 0x4919 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x56b8 -e 0x58b8 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `sed -n '700,866p' docs/src/graphics_object_pipeline.md`

Rejected or limited evidence:

- The first disassembly rerun used image addresses as file offsets and landed
  in the wrong window. The corrected commands above add the MZ header offset
  when skipping into the file and show the expected helper bodies.

Documented result:

- Reconfirmed from `code.object.place` and its callees that every placement
  candidate is tested in this order: bounds/horizon helper `0x5a14`, collision
  helper `0x4719`, and control-buffer acceptance helper `0x56b8`.
- Added a docstring to `search_object_placement()` explaining that its optional
  `accept` predicate models the two non-bounds predicates.
- Added a local regression test that rejects the first four otherwise-valid
  candidates `(20,80)`, `(19,80)`, `(19,81)`, and `(20,81)`. The helper then
  returns `(21,81)`, matching the source spiral order and showing how
  collision/control rejection extends the search without changing movement
  order.
- Added symbolic label `code.object.collision_test` for helper `0x4719` so both
  placement predicates have stable cross-version names.

## 2026-07-04: text/input tracker audit

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "dispatch-smoke|text window|input line|prompt|status line|close_text|clear_text|trace window|0x69|0x70|0xa3|0xa4|0xa9|text/input|Text windows" PROGRESS.md docs/src/logic_bytecode.md docs/src/runtime_model.md docs/src/compatibility_testing.md tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py`
- `ndisasm -b 16 -o 0x1f2b -e 0x212b build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `rg -n "0x0d1d|0x0d23|0x0d25|0x560c|close_text_window|saved rectangle|text window" docs/src/clean_room_executable_notes.md docs/src/logic_bytecode.md docs/src/runtime_model.md tools/logic_interpreter_probe.py`
- `rg -n "0x79|set_input|input row|key_event_mapping|status_line_show_hide|input_line_erase|0x8a|0x6f" docs/src/logic_bytecode.md docs/src/compatibility_testing.md docs/src/runtime_model.md tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py`

Documented result:

- Audited the current text/input coverage against `PROGRESS.md`. The broad
  "promote dispatch-smoke rows" wording was stale: focused QEMU cases already
  cover prompt marker behavior, status/input row show-hide/clear, input
  refresh/erase, mapped-key and raw-key paths, text attribute mode entry/exit,
  and the input-width flag effects of `0xa3`, `0xa4`, and inactive `0xa9`.
- Re-read `0xa9` at `0x1f2b`: it conditionally calls
  `0x560c([0x0d23], [0x0d25])` only when `[0x0d1d]` is nonzero, then clears
  `[0x0d0f]` and `[0x0d1d]`.
- Updated `PROGRESS.md` to name the remaining text/input gap more precisely:
  active saved-window restore for `0xa9`, plus non-EGA text paths only if they
  become necessary for SQ2 behavior.

## 2026-07-04: sound resource format source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x50d8 -e 0x52d8 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x7f96 -e 0x8196 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- Local Python scans over `SQ2/SNDDIR` and the referenced `VOL.*` payloads.
- `python3 -B -m unittest tests.test_sound_resources`

Documented result:

- `code.sound.find_loaded_resource` starts at `0x50d8`.
- Action `0x62` enters `code.sound.load_resource` at `0x5126`. On cache miss,
  it records resource event `(3, resource)`, resolves the sound directory entry
  through `0x440d`, reads the payload through the generic volume reader
  `0x2e32`, stores the raw payload pointer at cache-record `+0x04`, then reads
  four little-endian words from the payload and stores derived payload-relative
  channel pointers at record offsets `+0x06`, `+0x08`, `+0x0a`, and `+0x0c`.
- Action `0x63` stores/clears the completion flag, locates the already loaded
  sound record through `0x50d8`, and calls `code.sound.driver_start` at
  `0x7f96`.
- `code.sound.driver_start` copies the four cached channel pointers into data
  `0x1788..0x178f`, initializes the four countdown words at `0x1790..0x1797`
  to 1, initializes per-channel state words, and sets active-state word
  `[0x1258] = 1`.
- The playback tick reads channel records as `duration u16`; `0xffff`
  terminates a channel. Otherwise it reads a 16-bit tone/control word followed
  by one control byte and uses the low nibble as the observed
  attenuation/control value.
- Added `tools/agi_sound.py` with a deterministic parser for the observed sound
  payload shape and `tests/test_sound_resources.py` to scan all present SQ2
  sound resources.
- The targeted sound test passed: 49 present sound resources; every present
  payload has four sorted in-bounds channel offsets with first offset 8; every
  channel parses to an in-payload terminator. Sound 1 has offsets
  `(8, 15, 22, 29)`, channel 0 first event `(duration=0x0027,
  tone_word=0x8037, control_byte=0x9f)`, and channel 0 terminator offset 13.
- This is source-backed resource-format evidence. Audible pitch, timing, and
  hardware-driver output remain provisional.

## 2026-07-04: sound playback tick scheduling source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x7f60 -e 0x8160 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x8160 -e 0x8360 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x74c0 -e 0x76c0 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x83a0 -e 0x85a0 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x84f0 -e 0x86f0 build/cleanroom/AGI.decrypted.exe`
- Local Python scans over parsed SQ2 sound events and completion ticks.
- `python3 -B -m unittest tests.test_sound_resources`

Documented result:

- `code.sound.driver_start` chooses the active channel set from hardware
  selector `[0x112e]`: selector values `0` and `8` set
  `data.sound.active_channel_byte_limit = 2` and
  `data.sound.remaining_active_channels = 1`, so only channel 0 is advanced.
  Other observed selector values set the byte limit to 8 and the remaining
  count to 4, advancing channel offsets `0`, `2`, `4`, and `6`.
- `code.sound.driver_tick` starts by testing flag 9 through `code.flags.test`
  at `0x7502`. If flag 9 is clear, it calls the low-level stop/completion path
  immediately.
- The timer interrupt hook at `0x8521` calls `code.sound.driver_tick` only when
  `data.sound.active_state` is nonzero, then either acknowledges the interrupt
  or chains to the original timer interrupt every third hook call through byte
  `0x184f`.
- Every channel countdown is initialized to 1, so the first event or terminator
  is consumed on the first active tick. After an event is consumed, its duration
  word is stored as the next 16-bit countdown. A duration of zero would wrap and
  delay the next channel record read for 65,536 ticks.
- The local SQ2 corpus contains 3,619 parsed sound events. The minimum duration
  is 1, the maximum is 688, and no present event uses duration zero.
- Added source-backed scheduling helpers to `tools/agi_sound.py`:
  `active_sound_channel_indices`, `schedule_sound_channel`, and
  `sound_completion_tick`.
- Expanded `tests/test_sound_resources.py` from four to nine tests. New checks
  validate the one-channel/four-channel selector rule, sound 1's tick-40
  natural termination, sound 60's differing one-channel and four-channel
  completion ticks (`3403` and `3404`), the synthetic zero-duration wrap, and
  immediate first-tick completion when flag 9 is clear.
- The targeted sound-resource tests passed: 9 tests in `tests.test_sound_resources`.
  Hardware pitch, attenuation envelopes, and port-level output remain
  provisional.

## 2026-07-04: active text-window restore source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "0d1d|0D1D|0d23|0D23|0d25|0D25|560c|5590|text window|saved-window|saved window|close_text" build/cleanroom docs/src tools tests`
- `ndisasm -b 16 -o 0x5500 -e 0x5700 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x1cc0 -e 0x1ec0 build/cleanroom/AGI.decrypted.exe`

Documented result:

- `code.text.display_string` at `0x1ce8` calls the modal message-window setup
  helper at `0x1d96`, waits for the relevant acknowledgement/event path, and
  later calls `code.text.close_window_state` at `0x1f2b` with argument zero on
  the normal close path.
- `code.text.display_message_window` at `0x1d96` first checks word `[0x0d1d]`.
  If a saved window is already active, it calls `code.text.close_window_state`
  before building the next window. This prevents stacking multiple saved
  rectangles in the observed modal-message path.
- The same opener formats/copies the current message text through helper
  `0x1f54`, derives text-window row/column and size words from the text metrics
  and configuration globals, computes packed rectangle words `[0x0d23]` and
  `[0x0d25]`, then calls helper `0x5590` with those words and attribute
  `0x040f`.
- Helper `0x5590` is the boxed-window draw/save helper. It delegates the actual
  surface save/fill/draw operations to overlay/helper calls around `0x9812`.
  After that call returns, the opener sets `[0x0d1d] = 1`, prints the formatted
  text, refreshes text/input areas, and sets `[0x0d0f] = 1`.
- `code.text.close_window_state` at `0x1f2b` tests `[0x0d1d]`; when nonzero it
  calls helper `0x560c([0x0d23], [0x0d25])`. Helper `0x560c` loads those packed
  rectangle words and delegates to overlay restore helper `0x980c`.
- After the conditional restore, `code.text.close_window_state` always clears
  `[0x0d0f]` and `[0x0d1d]`. The existing QEMU probe validates the inactive
  unconditional `[0x0d0f]` clear; the active saved-rectangle lifecycle is now
  source-backed by both the producer at `0x1d96` and consumer at `0x1f2b`.

## 2026-07-04: save-file selector and block-envelope source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x2500 -e 0x2700 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x2700 -e 0x2900 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x85e5 -e 0x87e5 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x8814 -e 0x8a14 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x8a80 -e 0x8c80 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x8794 -e 0x8994 build/cleanroom/AGI.decrypted.exe | sed -n '1,110p'`
- `ndisasm -b 16 -o 0x8b9f -e 0x8d9f build/cleanroom/AGI.decrypted.exe | sed -n '1,190p'`
- `xxd -g 1 -s 0x1860 -l 0x400 SQ2/AGIDATA.OVL`
- Local Python scan over `SQ2/SQ2SG.*` save files.
- `python3 -B -m unittest tests.test_save_resources`

Documented result:

- Rechecked the save and restore handlers at `0x2753` and `0x2512`. The save
  block table in earlier notes had the first write reversed. Source argument
  order and the local save files show that the first length-prefixed block is
  `0x05e1` bytes from data address `0x0002`, not two bytes from `0x05e1`.
- The five save-file blocks written by `code.save.write_length_prefixed_block`
  and read by `code.save.read_length_prefixed_block` are:
  - `0x05e1` bytes from/to `0x0002`.
  - `[0x096f]` bytes from/to `[0x096b]`.
  - `[0x0975]` bytes from/to `[0x0971]`.
  - `[0x0141] * 2` bytes from/to `[0x1707]`.
  - `0x1364()` bytes from/to `0x0985`.
- The checked-in local SQ2 saves `SQ2/SQ2SG.1` through `SQ2/SQ2SG.11` all parse
  as a 31-byte description/header followed by five little-endian
  length-prefixed blocks. The first four block lengths are fixed in this local
  corpus: `1505`, `903`, `328`, and `200`. The fifth block is present and
  variable-sized (`16..28` bytes observed).
- Added `tools/agi_save.py`, a narrow parser for the source-backed save-file
  envelope. Added `tests/test_save_resources.py`; the targeted test run passed
  four tests and checks all local SQ2 save files, description extraction,
  truncated-block rejection, and trailing-byte rejection.
- Refined `code.save.select_slot_or_path` at `0x85e5`. It saves prompt-marker
  visibility, erases the marker, saves/restores text state, stops active sound,
  sets a text attribute pair, delegates path prompting, scans selectable slots,
  formats the selected filename into `0x1c8c`, and returns zero for cancel/no
  selection.
- Labeled selector subhelpers:
  - `code.save.check_drive_or_path_available` at `0x86a3`.
  - `code.save.prompt_path_if_needed` at `0x8705`.
  - `code.save.edit_modal_text_field` at `0x8794`.
  - `code.save.select_numbered_slot` at `0x8814`.
  - `code.save.read_slot_summary` at `0x8b9f`.
- `code.save.prompt_path_if_needed` displays the save or restore path prompt
  when `[0x0e72]` is empty, edits path buffer `0x1962`, and validates it
  through the generic path validator at `0x5bdd`.
- `code.save.select_numbered_slot` scans up to 12 numbered save files, displays
  descriptions, marks the current row with glyph `0x1a`, clears the old row
  with a space, accepts Enter, cancels Escape, and handles movement events `1`
  and `5` as up/down with wrap.
- In save mode, accepting an empty-description slot calls
  `code.save.edit_modal_text_field` with prompt text at `0x1baa` and fills the
  31-byte header/description buffer at `0x1c6c` before the save handler creates
  the file.

## 2026-07-04: heap allocation and mark/rewind source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x1300 -e 0x1500 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x1480 -e 0x1680 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x0f80 -e 0x1180 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- Source/local searches over heap globals `0x0a55`, `0x0a57`, `0x0a59`,
  `0x0a5b`, `0x0a5d`, and `0x0a5f` in the disassembly notes, docs, tools, and
  tests.

Documented result:

- The interpreter heap is source-backed as a bump allocator with mark/rewind
  cleanup. No general free-list behavior has been observed in the allocator
  helpers.
- `code.heap.allocate` at `0x13d6` computes available bytes as
  `[0x0a5b] - [0x0a55]`. If the requested size is larger, it formats the
  out-of-memory message at `0x09fd`, displays it through the text helper, and
  calls restart/exit helper `0x02ae`. No recoverable allocation-failure return
  was observed.
- On successful allocation, `0x13d6` returns the old current heap pointer,
  advances `[0x0a55]` by the requested size, calls `code.heap.update_free_memory_var`
  at `0x14a0`, and updates high-water pointer `[0x0a5f]` when the new current
  top exceeds the prior high-water value.
- `code.heap.current_top` at `0x1430` returns `[0x0a55]`. `code.heap.rewind_to`
  at `0x143c` stores a caller-provided pointer in `[0x0a55]` without refreshing
  the free-memory byte.
- `code.heap.save_temporary_mark` at `0x144b` stores `[0x0a55]` in `[0x0a5d]`.
  `code.heap.restore_temporary_mark` at `0x145a` rewinds to `[0x0a5d]` only
  when that mark is nonzero, then clears the mark.
- Startup calls `code.heap.save_room_reset_mark` at `0x1476` after initial
  object/inventory setup and logic 0 load. `code.heap.reset_dynamic_state` at
  `0x1485`, used by room switch, restart, and restore paths, frees update-list
  nodes, clears the temporary mark, restores `[0x0a55]` from `[0x0a59]`, and
  refreshes the free-memory byte through `0x14a0`.
- `code.heap.update_free_memory_var` computes `[0x0a5b] - [0x0a55]`, stores the
  high byte in byte variable `[0x0011]`, and returns the full free-byte count.
- `code.heap.show_status_action` at `0x14bd` formats heap diagnostics from the
  same globals: heap size `[0x0a5b] - [0x0a57]`, current use
  `[0x0a55] - [0x0a57]`, maximum use `[0x0a5f] - [0x0a57]`, room/reset mark
  `[0x0a59] - [0x0a57]`, and resource-event high-water `[0x170f]`.

## 2026-07-04: restart, restore-failure, and shutdown cleanup source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x02ae -e 0x04ae build/cleanroom/AGI.decrypted.exe | sed -n '1,120p'`
- `ndisasm -b 16 -o 0x0240 -e 0x0440 build/cleanroom/AGI.decrypted.exe | sed -n '1,120p'`
- `ndisasm -b 16 -o 0x2460 -e 0x2660 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x2500 -e 0x2700 build/cleanroom/AGI.decrypted.exe | sed -n '1,240p'`
- `ndisasm -b 16 -o 0x2700 -e 0x2900 build/cleanroom/AGI.decrypted.exe | sed -n '80,260p'`
- `ndisasm -b 16 -o 0x8240 -e 0x8440 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x8380 -e 0x8580 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x5a20 -e 0x5c20 build/cleanroom/AGI.decrypted.exe | sed -n '1,160p'`
- `ndisasm -b 16 -o 0x0f80 -e 0x1180 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- Source/document searches for `0x80`, `0x86`, `0x02ae`, `0x8275`,
  restore-success/failure paths, interrupt-vector cleanup, and log-file handle
  cleanup.

Addressing note:

- A first exploratory `ndisasm` command used `-e` too broadly. `ndisasm -e`
  is a file skip, not an end address. The documented slices above use the
  project's existing convention: display image offset with `-o IMAGE`, and skip
  to the corresponding EXE file offset with `-e IMAGE+0x200`.

Documented result:

- `code.restart.confirm_restart_action` at image `0x2472` is an in-engine
  restart, not DOS process termination. It stops sound, clears the prompt/input
  line, tests flag 16 to optionally skip the confirmation prompt, and only
  enters the reset block when the confirmation result is nonzero.
- On accepted restart, `0x2472` erases visible input, saves the current flag 9
  state, calls `code.heap.reset_dynamic_state` (`0x1485`), calls
  `code.restart.initialize_game_tables` (`0x0fa5`), refreshes display/list
  state through `0x30d6`, sets flag 6, restores flag 9 if it was previously
  set, clears timer/event words `[0x0129]` and `[0x012b]`, reloads trace logic
  `[0x1d12]` if configured, calls menu/list refresh helper `0x930e`, redraws
  the prompt marker, and returns zero to the dispatcher.
- On canceled restart, the reset block is skipped and `0x2472` returns the
  following bytecode pointer after redrawing the prompt marker.
- `code.system.confirm_exit_action` at image `0x027f` is the smaller
  confirmation-gated exit path. It stops sound, exits immediately when operand
  byte `arg0 == 1`, or displays message `0x05e3` and exits only if the display
  helper returns one.
- `code.system.exit_with_cleanup` at image `0x02ae` calls
  `code.system.shutdown_cleanup` (`0x8275`) and then calls
  `code.system.dos_terminate(0)` at `0x00ae`. The DOS terminate wrapper uses
  `int 21h` with `AH=0x4c`.
- `code.system.shutdown_cleanup` closes the log file if open through
  `code.log.close_if_open` (`0x838c`), restores saved interrupt vectors/timer
  state through `0x849f`, then calls the BIOS video-mode wrapper `0x5a5e` with
  mode byte `[0x1807]`.
- `code.system.install_interrupt_hooks` at `0x83ac` saves original vectors and
  installs interpreter keyboard/timer/critical-error style hooks. The restore
  helper at `0x849f` restores saved vectors for interrupts `0x1f`, `0x05`,
  `0x08`, `0x1c`, `0x09`, `0x23`, `0x24`, and conditionally `0x10`, and resets
  the PIT timer divisor before returning.
- Restore action `0x7e` uses the fatal exit helper for read failure: after any
  length-prefixed state block read fails, it closes the save file, displays
  message `0x0d87`, and calls `code.system.exit_with_cleanup`. This is not
  modeled as a recoverable restore error.
- Restore success has a different continuation: after all five blocks are read,
  it restores display adapter/mode bytes, sets hardware flag 11 for nonzero
  adapter kinds, calls `code.restore.replay_resource_events`, refreshes display
  and list state, clears the saved caller return pointer on the stack, and
  returns zero so execution resumes through the restored state.

## 2026-07-04: save envelope round-trip and DOS wrapper correction

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,220p' tools/agi_save.py`
- `sed -n '1,240p' tests/test_save_resources.py`
- `sed -n '680,760p' docs/src/compatibility_testing.md`
- `sed -n '70,190p' docs/src/agi_executable.md`
- `sed -n '290,370p' PROGRESS.md`
- `rg -n "code\\.dos\\.|0x5cef|0x5d12|0x5d35|0x5d6b|0x5db2|0x5e01|0x5e3e|0x5e73" docs/src PROGRESS.md tools tests`
- `ndisasm -b 16 -o 0x5c80 -e 0x5e80 build/cleanroom/AGI.decrypted.exe`
- `ndisasm -b 16 -o 0x5ca8 -e 0x5ea8 build/cleanroom/AGI.decrypted.exe | sed -n '1,160p'`
- `python3 -B -m unittest tests.test_save_resources`

Documented result:

- `tools/agi_save.py` now serializes the parsed save-file envelope back to
  bytes. The serializer requires the same source-backed structure used by the
  parser: a 31-byte header, exactly five blocks, matching block order, and each
  block's stored length matching the number of data bytes. This preserves the
  interpreter's envelope instead of inventing a higher-level save format.
- `tests/test_save_resources.py` now checks that all 11 checked-in
  `SQ2/SQ2SG.*` files parse and serialize back to identical bytes. The focused
  save test module ran 6 tests successfully.
- The DOS wrapper symbol rows in `docs/src/symbolic_labels.md` were corrected
  against disassembly. The previous table had several post-open wrappers mapped
  to later helper addresses; the corrected source-backed map is:

| Label | Image offset | DOS function / behavior |
| --- | ---: | --- |
| `code.dos.create_file` | `0x5cad` | `AH=0x3c`; returns `0xffff` on carry/error. |
| `code.dos.open_file` | `0x5cce` | `AH=0x3d`; returns `0xffff` on carry/error. |
| `code.dos.read_file` | `0x5cef` | `AH=0x3f`; returns zero on carry/error, so callers check the returned byte count. |
| `code.dos.write_file` | `0x5d12` | `AH=0x40`; returns zero on carry/error, so callers check the returned byte count. |
| `code.dos.delete_file` | `0x5d35` | `AH=0x41`; returns zero on carry/error. |
| `code.dos.close_file` | `0x5d52` | `AH=0x3e`; callers observed so far ignore a close error. |
| `code.dos.seek_file` | `0x5d6b` | `AH=0x42`; returns `0xffff:0xffff` in `DX:AX` on carry/error. |
| `code.dos.duplicate_handle` | `0x5d94` | `AH=0x45`; returns `0xffff` on carry/error. |
| `code.dos.get_current_directory` | `0x5db2` | Writes a leading separator and calls `AH=0x47` for the default drive. |
| `code.dos.get_current_drive_letter` | `0x5dea` | `AH=0x19`; returns lowercase `a` plus the zero-based current-drive number. |
| `code.dos.find_first` | `0x5e01` | Sets DTA with `AH=0x1a`, then calls `AH=0x4e`; returns `0xffff` on carry/error. |
| `code.dos.find_next` | `0x5e26` | `AH=0x4f`; returns `0xffff` on carry/error. |
| `code.dos.probe_drive_selectable` | `0x5e3e` | Tries selecting a lowercase drive letter, checks whether DOS reports it as current, then restores the original drive. |
| `code.dos.get_file_time` | `0x5e73` | `AH=0x57`, `AL=0`; selector code uses the returned `CX` time word. |
| `code.dos.prepare_call` | `0x5e8d` | Temporarily switches `DS` to segment `0x0a01` and clears word `[0x184d]`. |

- This pass strengthens save-file fixture generation but does not yet prove a
  dynamic original-engine save/restore round trip from a generated save file.

## 2026-07-04: save/restore file-error source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x2500 -e 0x2700 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x26a0 -e 0x28a0 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x2750 -e 0x2950 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `rg -n "0x28c6|0x26b0|0x2753|0x2512|0x0e46|0x0d87|write_length|read_length|save_game_state|restore_game_state|About to save|Error in" docs/src tools tests PROGRESS.md`
- `strings -a -t x SQ2/AGIDATA.OVL | rg "Can't|Error|About|save|restore|file"`
- `xxd -g 1 -s 0xd20 -l 0x160 SQ2/AGIDATA.OVL`
- `sed -n '270,300p' docs/src/runtime_model.md`
- `sed -n '1350,1360p' docs/src/logic_bytecode.md`

Documented result:

- `code.save.write_length_prefixed_block` at image `0x28c6` writes the low
  length byte, high length byte, and payload separately. It returns 1 only when
  the two one-byte writes each return 1 and the payload write returns the full
  requested length.
- Save action `0x7d` treats create failure and write failure differently.
  `code.dos.create_file` returning `0xffff` formats message `0x0df0` with path
  buffer `0x1962`, displays it, restores modal/text state, and returns to the
  following bytecode. A short header write or failed length-prefixed block
  closes the handle, deletes filename `0x1c8c`, displays message `0x0e46`,
  restores modal/text state, and also returns to the following bytecode.
- `code.save.read_length_prefixed_block` at image `0x26b0` reads the low length
  byte, high length byte, and payload separately. It returns 1 only when the
  one-byte reads each return 1 and the payload read returns the decoded length.
- Restore action `0x7e` also splits open and read failures. Open failure
  formats/displays message `0x0d73`, restores modal/text state, and returns to
  the following bytecode. Any failure after the file has opened and block reads
  have begun closes the file, displays message `0x0d87`, and calls
  `code.system.exit_with_cleanup`; this path terminates the DOS process.
- Local strings confirm the visible prompts:
  - `0x0d73`: can't-open-file message;
  - `0x0d87`: restoring error followed by an enter-to-quit prompt;
  - `0x0df0`: directory full or disk write-protected;
  - `0x0e46`: disk full.

## 2026-07-04: view-batch right/bottom placement validation

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "Picture|picture|view|renderer|Remaining|Highest-Value|fuzz|line|pattern|fill|priority|cel|mirror|clip" PROGRESS.md docs/src/graphics_object_pipeline.md docs/src/picture_resources.md docs/src/view_resources.md docs/src/compatibility_testing.md tests tools | head -n 240`
- `ls docs/src`
- `sed -n '1,260p' tests/test_picture_fuzz.py`
- `sed -n '1,260p' tests/test_view_batch.py`
- `sed -n '1,260p' tools/view_batch.py`
- `sed -n '260,620p' tools/view_batch.py`
- `rg -n "right_clip|bottom_clip|left_clip|top_clip|clip" tools/view_batch.py tools/object_overlay_probe.py tests/test_view_batch.py tests/test_object_overlay_probe.py docs/src/compatibility_testing.md docs/src/graphics_object_pipeline.md`
- `sed -n '640,710p' tools/agi_graphics.py`
- `python3 -B -m unittest tests.test_view_batch`
- Local Python probes using `tools/agi_graphics.render_view_frame` and
  `tools/agi_graphics.search_object_placement` to compute view 11 frame size
  and placement-search results.
- `python3 -B tools/view_batch.py --snapshot --dos-prefix VC --output build/view-batch/batches/clip_right_bottom_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case view_011_right_clip --case view_011_bottom_clip`
- `sed -n '1,220p' build/view-batch/batches/clip_right_bottom_001.json`
- `python3 -B tools/inspect_ppm.py build/view-batch/fixtures/view_011_right_clip/qemu_capture.ppm`
- `sed -n '180,235p' tools/object_overlay_probe.py`
- `sed -n '340,380p' tools/object_overlay_probe.py`
- `python3 -B tools/view_batch.py --snapshot --dos-prefix VC --output build/view-batch/batches/clip_right_bottom_002.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case view_011_right_clip --case view_011_bottom_clip`

Documented result:

- The simple view-batch registry now includes right and bottom edge-placement
  cases for view 11/group 0/frame 0, in addition to the previous normal,
  cached, mirrored, left-edge, top-edge, and low-priority cases.
- `tools/view_batch.py` now supports repeated `--case CASE_ID` filters, matching
  the focused-run pattern used by the other QEMU probe harnesses.
- The first focused QEMU run, `clip_right_bottom_001`, mismatched the
  right-edge case. The mismatch was not an original-engine failure; it showed
  that direct view composition expected a simple right clamp while the original
  engine routed the transient object through `code.object.place` (`0x593a`) and
  its source-backed spiral placement search.
- `tools/view_batch.py` now computes the expected comparison placement with
  `search_object_placement` by default, with optional expected-position and
  expected-priority overrides available for future cases.
- Local placement probes for view 11/group 0/frame 0 showed:
  - request `(150, 80)` resolves to placement `(140, 71)`;
  - request `(20, 170)` resolves to placement `(23, 167)`.
- The corrected focused QEMU run, `clip_right_bottom_002`, matched both cases
  with 2 matches, 0 mismatches, and 0 errors.

## 2026-07-04: real-picture batch harness and base QEMU parity

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "compare_picture_capture.py|qemu_fixture.py picture|picture [0-9]|real-resource|real resource|picture_N|PICDIR|all 74|74 valid|render_picture" docs/src tools tests`
- `sed -n '620,730p' tools/qemu_fixture.py`
- `sed -n '1,180p' tools/qemu_fixture.py`
- Local Python scan of `SQ2/PICDIR` to find present picture resources, picture
  streams that use pattern commands, and the largest valid picture payload.
- `sed -n '1,140p' tests/test_graphics_rendering.py`
- `sed -n '40,110p' docs/src/compatibility_testing.md`
- Added `tools/picture_batch.py` and `tests/test_picture_batch.py`.
- `python3 -B -m unittest tests.test_picture_batch tests.test_view_batch`
- `python3 -B tools/picture_batch.py --snapshot --dos-prefix PB --output build/picture-batch/batches/picture_base_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- Escalated rerun of the same `tools/picture_batch.py` command after the
  first unprivileged QEMU attempt could not bind `vnc=127.0.0.1:5` from the
  sandbox.

Documented result:

- `tools/picture_batch.py` provides a reusable QEMU validation batch for real
  local SQ2 picture resources. It builds picture fixtures with
  `build_picture_fixture`, can run them serially or from one QEMU snapshot, and
  writes a JSON report with match/mismatch/error counts.
- The base case registry intentionally starts small: picture 1 is the first
  present local picture resource and includes pattern plotting, while picture
  45 is the largest valid local picture payload observed in this corpus.
- The first unprivileged batch attempt failed before the interpreter ran because
  QEMU could not bind its VNC socket from the sandbox. That is an execution
  environment failure, not compatibility evidence.
- The escalated `picture_base_001` snapshot run matched both base cases:
  `picture_001_first_present` and `picture_045_largest_payload` each had 0
  mismatches over 26,880 logical pixels, for 2 matches, 0 mismatches, and 0
  errors overall.

## 2026-07-04: pattern channel-mask source pass and QEMU visible parity

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '230,285p' docs/src/graphics_object_pipeline.md`
- `sed -n '380,430p' tools/agi_graphics.py`
- `ndisasm -b 16 -o 0x64e0 -e 0x64e0 build/cleanroom/AGI.decrypted.exe | sed -n '1,150p'`
- `ndisasm -b 16 -o 0x5200 -e 0x5200 build/cleanroom/AGI.decrypted.exe | sed -n '1,120p'`
- `ndisasm -b 16 -o 0x6470 -e 0x6470 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x66a0 -e 0x66a0 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x54e0 -e 0x54e0 build/cleanroom/AGI.decrypted.exe | sed -n '1,110p'`
- `ndisasm -b 16 -o 0x6670 -e 0x6670 build/cleanroom/AGI.decrypted.exe | sed -n '1,150p'`
- `ndisasm -b 16 -o 0x66f0 -e 0x66f0 build/cleanroom/AGI.decrypted.exe | sed -n '1,150p'`
- `ndisasm -b 16 -o 0x68b0 -e 0x68b0 build/cleanroom/AGI.decrypted.exe | sed -n '1,120p'`
- `ndisasm -b 16 -o 0x5860 -e 0x5860 build/cleanroom/AGI.decrypted.exe | sed -n '1,90p'`
- `sed -n '90,150p' tools/picture_fuzz.py`
- `sed -n '270,330p' tests/test_graphics_rendering.py`
- `python3 -B -m unittest tests.test_graphics_rendering tests.test_picture_fuzz`
- `python3 -B tools/picture_fuzz.py generate --count 8 --seed 4097 --output build/picture-fuzz/pattern-channel-cases --clean`
- `python3 -B tools/picture_fuzz.py batch-qemu --snapshot --corpus build/picture-fuzz/pattern-channel-cases --fixture-root build/picture-fuzz/pattern-channel-fixtures --case base_027_pattern_visual_control_channels --case base_028_pattern_visual_disabled_control_only --case base_029_pattern_control_disabled_visual_only --dos-prefix PC --output build/picture-fuzz/batches/pattern_channel_masks_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `python3 -B tools/picture_fuzz.py generate --count 1024 --seed 4097 --output build/picture-fuzz/corpus --clean`

Documented result:

- The first pattern-source disassembly window intentionally proved a label
  convention detail: existing picture symbols are loaded-image offsets, while
  `ndisasm -e` consumes file offsets. In this file-offset pass, the relevant
  windows are shifted by `0x200`; prose continues using the established
  symbolic loaded-image labels.
- Source inspection confirms that pattern helper `code.picture.cmd_pattern_plot`
  and its draw helper do not implement separate channel rules. For every
  accepted candidate pixel, the helper writes the current X/Y pair into
  `[0x150b]` and calls the common pixel writer. The pixel writer selects
  `[0x136d]` for odd Y rows or `[0x136e]` for even Y rows, ORs active draw bits
  from `[0x1369]`, ANDs with the selected mask, and stores the resulting byte.
- In the full 16-color EGA target path, `code.display.map_visual_color_for_adapter`
  returns with `AH == AL`, so visual odd/even masks are identical. The parity
  branch remains part of the implementation model, but visual parity divergence
  is a non-EGA concern unless it is needed to explain observed SQ2 behavior.
- Added curated safe fuzz cases:
  - `base_027_pattern_visual_control_channels`: both channels active; local
    tests assert visual and nondefault control nibbles change together.
  - `base_028_pattern_visual_disabled_control_only`: visual disabled, control
    active; local tests assert only the control nibble changes.
  - `base_029_pattern_control_disabled_visual_only`: control disabled, visual
    active; local tests assert the default control nibble is preserved.
- A test correction during this pass clarified that the default control nibble
  is already `4`, so the both-active case uses control class `5` to make the
  control-channel change observable in local cell tests.
- The QEMU snapshot batch `pattern_channel_masks_001` matched the visible EGA
  surface for all three cases: 3 matches, 0 mismatches, and 0 errors. Screenshots
  do not expose the control buffer directly, so the control-channel assertions
  remain source-backed plus local renderer evidence rather than screenshot
  evidence.
- Regenerating the standard deterministic corpus after adding the three cases
  reports 1,054 total cases and 1,052 safe-for-QEMU cases.

## 2026-07-04: broad real-picture preset parity

Commands run from `/Users/peter/ai/agi/reverse`:

- Local Python scan of all valid `PICDIR` payloads, counting local command bytes
  `0xf0..0xfa` by picture and listing largest payloads, pattern-heavy pictures,
  fill-heavy pictures, and broad command-family mixes.
- Added `broad_cases`, `all_present_cases`, and preset selection to
  `tools/picture_batch.py`.
- Added preset and discovery tests to `tests/test_picture_batch.py`.
- `python3 -B -m unittest tests.test_picture_batch`
- `python3 -B tools/picture_batch.py --preset broad --snapshot --dos-prefix PB --output build/picture-batch/batches/picture_broad_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `sed -n '1,220p' build/picture-batch/batches/picture_broad_001.json`

Documented result:

- The local corpus scan found 74 present valid picture resources. The broad
  preset is intentionally representative rather than exhaustive:
  - picture 1: first present local picture resource;
  - picture 6: early resource with many fills and pattern plots;
  - picture 17: all observed picture command families, including multiple
    pattern-mode changes;
  - picture 43: dense large picture with many fills, lines, and pattern plots;
  - picture 44: large fill-heavy picture with many control toggles;
  - picture 45: largest valid picture payload in the local corpus;
  - picture 46: pattern-heavy large picture with broad command-family mix;
  - picture 76: high pattern-count resource outside the largest-payload cluster.
- `tools/picture_batch.py --preset all` can now discover all 74 present valid
  local picture resources for a future full-corpus QEMU run. The default preset
  remains the two-case base set so quick checks stay cheap.
- The QEMU snapshot batch `picture_broad_001` matched all eight broad cases:
  8 matches, 0 mismatches, and 0 errors, with each comparison covering 26,880
  logical pixels.

## 2026-07-04: packed picture fixtures and full SQ2 picture parity

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,260p' tools/qemu_snapshot.py`
- Local Python check of `picture_batch.all_present_cases()`, confirming 74
  valid present picture cases from the local `PICDIR`.
- `du -sh SQ2 build/picture-batch/fixtures`
- `ls -lh build/dos622/dos622.img build/picture-batch/snapshot/picture_batch.raw build/picture-batch/snapshot/picture_batch.qcow2 2>/dev/null`
- `find build/picture-batch/fixtures/picture_001_first_present -maxdepth 1 -type f -print0 | xargs -0 ls -lh`
- `du -sh build/picture-batch/fixtures/picture_001_first_present build/picture-batch/fixtures/picture_046_pattern_heavy`
- `mdir -i build/picture-batch/snapshot/picture_batch.raw@@32256 :: | tail -n 20`
- Added `copy_minimal_picture_tree` and `build_packed_picture_fixture` to
  `tools/qemu_fixture.py`.
- Updated `tools/picture_batch.py` to use packed picture fixtures.
- Added packed-fixture structural coverage to `tests/test_qemu_fixture.py`.
- `python3 -B -m unittest tests.test_qemu_fixture tests.test_picture_batch`
- Local Python packed-fixture size probe for pictures 1 and 45.
- `python3 -B tools/picture_batch.py --preset base --snapshot --fixture-root build/picture-batch/packed-fixtures --dos-prefix PP --output build/picture-batch/batches/picture_base_packed_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `python3 -B tools/picture_batch.py --preset all --snapshot --fixture-root build/picture-batch/all-fixtures --dos-prefix PA --output build/picture-batch/batches/picture_all_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`

Documented result:

- A direct all-picture batch using full copied SQ2 fixture directories would put
  too much pressure on the 64 MB DOS snapshot image. One full picture fixture
  directory was about 1.7 MB because it included the original volumes and saved
  games, so 74 copies would exceed the image before filesystem overhead.
- Packed picture fixtures solve that for picture-only parity checks. They copy
  the minimal engine/support files, write generated `LOGIC.0` into `VOL.3`,
  append the tested local picture payload as the next `VOL.3` record, patch
  `LOGDIR[0]` to the generated logic, and patch the selected `PICDIR` entry to
  the appended picture record. A packed picture fixture for pictures 1 or 45 is
  roughly 72 KB of input files.
- The packed fixture preserves the tested original picture payload while
  avoiding duplicate copies of unrelated resource volumes. The original one-off
  `qemu_fixture.py picture` command still uses the historical full-tree fixture
  path; `picture_batch.py` now uses packed fixtures for batch throughput.
- Packed base QEMU batch `picture_base_packed_001` matched pictures 1 and 45
  with 2 matches, 0 mismatches, and 0 errors, validating that the original
  engine accepts the trimmed picture fixture layout.
- Full present-picture QEMU batch `picture_all_001` matched all 74 valid local
  SQ2 picture resources with 74 matches, 0 mismatches, and 0 errors.
- User feedback during this long run identified an important future throughput
  direction: for resource sweeps, generate a single in-engine carousel fixture
  that displays the next resource after input or a timed event, then drive it
  from QEMU with `screendump` plus key sends. The isolated one-process-per-case
  snapshot harness remains the simplest reference oracle, but carousel-style
  sweeps should become part of the infrastructure before comparing many games
  and interpreter versions.
- If future fixture sets genuinely need more DOS disk space, the right answer
  is a larger formatted/bootable DOS test image or a purpose-built large fixture
  image. Appending bytes to `build/dos622/dos622.img` would not by itself help,
  because the FAT partition geometry inside the image would still describe the
  old volume.

## 2026-07-04: picture carousel prototype

Commands run from `/Users/peter/ai/agi/reverse`:

- Added carousel bytecode helpers and `build_picture_carousel_fixture` to
  `tools/qemu_fixture.py`.
- Added `tools/picture_carousel.py`.
- Added `tests/test_picture_carousel.py` and carousel structural coverage in
  `tests/test_qemu_fixture.py`.
- `python3 -B -m unittest tests.test_qemu_fixture tests.test_picture_carousel`
- `python3 -B tools/picture_carousel.py --preset base --fixture-root build/picture-carousel/base-fixtures --dos-dir PICSWEEP --output build/picture-carousel/batches/picture_carousel_base_001.json --boot-wait 5 --first-wait 8 --advance-wait 2`
- `python3 -B tools/picture_carousel.py --preset base --fixture-root build/picture-carousel/base-fixtures --dos-dir PICSWEEP --output build/picture-carousel/batches/picture_carousel_base_002.json --boot-wait 5 --first-wait 8 --advance-wait 2`
- `python3 -B tools/picture_carousel.py --preset base --fixture-root build/picture-carousel/base-fixtures --dos-dir PICSWEEP --output build/picture-carousel/batches/picture_carousel_base_003.json --boot-wait 5 --first-wait 8 --advance-wait 2`
- `python3 -B tools/picture_carousel.py --preset broad --fixture-root build/picture-carousel/broad-fixtures --dos-dir PICSWEEP --output build/picture-carousel/batches/picture_carousel_broad_001.json --boot-wait 5 --first-wait 8 --advance-wait 2`
- `python3 -B tools/picture_carousel.py --preset broad --fixture-root build/picture-carousel/broad-fixtures --dos-dir PICSWEEP --output build/picture-carousel/batches/picture_carousel_broad_002.json --boot-wait 5 --first-wait 8 --advance-wait 8`
- Manual four-picture case file `build/picture-carousel/manual_four_cases.json`.
- `python3 -B tools/picture_carousel.py --cases build/picture-carousel/manual_four_cases.json --fixture-root build/picture-carousel/manual-four-fixtures --dos-dir PICSWEEP --output build/picture-carousel/batches/picture_carousel_manual_four_001.json --boot-wait 5 --first-wait 8 --advance-wait 4`
- `python3 -B tools/picture_carousel.py --cases build/picture-carousel/manual_four_cases.json --fixture-root build/picture-carousel/manual-four-fixtures --dos-dir PICSWEEP --output build/picture-carousel/batches/picture_carousel_manual_four_002.json --boot-wait 5 --first-wait 8 --advance-wait 4`
- `python3 -B tools/picture_carousel.py --cases build/picture-carousel/manual_four_cases.json --fixture-root build/picture-carousel/manual-four-fixtures --dos-dir PICSWEEP --output build/picture-carousel/batches/picture_carousel_manual_four_keys_001.json --boot-wait 5 --first-wait 8 --advance-wait 4 --advance-key x,y,z`
- `python3 -B tools/picture_carousel.py --cases build/picture-carousel/manual_four_cases.json --fixture-root build/picture-carousel/manual-four-fixtures --dos-dir PICSWEEP --output build/picture-carousel/batches/picture_carousel_manual_four_mapped_001.json --boot-wait 5 --first-wait 8 --advance-wait 4`
- `python3 -B tools/picture_carousel.py --cases build/picture-carousel/manual_four_cases.json --fixture-root build/picture-carousel/manual-four-fixtures --dos-dir PICSWEEP --output build/picture-carousel/batches/picture_carousel_manual_four_fkeys_001.json --boot-wait 5 --first-wait 8 --advance-wait 4`
- `python3 -B tools/picture_carousel.py --preset base --fixture-root build/picture-carousel/base-fixtures --dos-dir PICSWEEP --output build/picture-carousel/batches/picture_carousel_base_mapped_fkey_001.json --boot-wait 5 --first-wait 8 --advance-wait 4`

Documented result:

- `tools/picture_carousel.py` builds one packed fixture containing multiple
  picture payloads, launches one engine process, captures the first picture,
  sends an advance key, waits, captures the next picture, and compares each
  capture to the local renderer.
- The first raw-key implementation matched the first capture but failed the
  second because it cleared the wrong byte variable. The raw-key predicate
  caches at absolute `[0x001c]`; because script variables start at `[0x0009]`,
  the matching script variable index is `0x13`, not `0x1c`. Clearing the wrong
  slot let a single key event advance twice and wrap back to picture 1.
- Correcting that raw-key cache clear made the two-picture base carousel
  `picture_carousel_base_003` pass with 2 matches and 0 mismatches.
- Longer raw-key carousels still stalled after the third displayed picture.
  Changing the persistent carousel index from high variable `v249` to `v32` did
  not change that behavior.
- The mapped-key/status-byte variant uses action `0x79` to map advance keys to
  unique status bytes and tests `(index == n) && status[n]`. Printable keys and
  function-key mappings both still failed broader four/eight-picture sweeps:
  later captures either remained on the previous picture or showed the expected
  picture with a visible input/message-window artifact in logical rectangle
  approximately `x=35..124`, `y=67..92`.
- The current mapped function-key base smoke
  `picture_carousel_base_mapped_fkey_001` passed with 2 matches and 0
  mismatches from one engine process. This proves the general packed-carousel
  fixture can work, but the advance/ack strategy is not robust enough yet for
  broad compatibility evidence.
- Keep `tools/picture_carousel.py` as infrastructure prototype and unit-tested
  scaffolding. Before using it for cross-game sweeps, it needs a deterministic
  way to advance multiple resources without parser/UI side effects and with a
  reliable acknowledgement that the next picture has completed drawing.

## 2026-07-04: timed polling picture carousel and speed variable

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x0150 -e 0x0350 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `ndisasm -b 16 -o 0x7f60 -e 0x8160 build/cleanroom/AGI.decrypted.exe | sed -n '1,120p'`
- Local message scan over readable SQ2 logic resources for `speed`, `fast`, and
  `slow`.
- Added timed-carousel helpers to `tools/qemu_fixture.py`.
- Added timed and polling modes to `tools/picture_carousel.py`.
- `python3 -B -m unittest tests.test_qemu_fixture tests.test_picture_carousel`
- `python3 -B tools/picture_carousel.py --preset base --mode timed --delay-cycles 120 --speed-value 1 --fixture-root build/picture-carousel/timed-base-fixtures --dos-dir PICTIME --output build/picture-carousel/batches/picture_carousel_base_timed_001.json --boot-wait 5 --first-wait 5 --advance-wait 7`
- `python3 -B tools/picture_carousel.py --preset broad --mode timed --delay-cycles 120 --speed-value 1 --fixture-root build/picture-carousel/timed-broad-fixtures --dos-dir PICTIME --output build/picture-carousel/batches/picture_carousel_broad_timed_001.json --boot-wait 5 --first-wait 5 --advance-wait 7 --snapshot-raw build/picture-carousel/snapshot/picture_carousel_broad.raw --snapshot-qcow build/picture-carousel/snapshot/picture_carousel_broad.qcow2`
- `python3 -B tools/picture_carousel.py --preset broad --case picture_017_full_command_mix --case picture_043_dense_large_fill_pattern --mode timed --delay-cycles 120 --speed-value 1 --fixture-root build/picture-carousel/timed-17-43-fixtures --dos-dir PT1743 --output build/picture-carousel/batches/picture_carousel_17_43_timed_001.json --boot-wait 5 --first-wait 5 --advance-wait 7 --snapshot-raw build/picture-carousel/snapshot/picture_carousel_17_43.raw --snapshot-qcow build/picture-carousel/snapshot/picture_carousel_17_43.qcow2`
- `python3 -B tools/picture_carousel.py --preset broad --mode timed --delay-cycles 240 --speed-value 1 --fixture-root build/picture-carousel/timed-broad-fixtures-v4 --dos-dir PICTIME --output build/picture-carousel/batches/picture_carousel_broad_timed_004.json --boot-wait 5 --first-wait 5 --advance-wait 7 --snapshot-raw build/picture-carousel/snapshot/picture_carousel_broad_v4.raw --snapshot-qcow build/picture-carousel/snapshot/picture_carousel_broad_v4.qcow2`
- `python3 -B tools/picture_carousel.py --preset broad --mode timed --poll --delay-cycles 240 --speed-value 1 --fixture-root build/picture-carousel/timed-broad-poll-fixtures --dos-dir PICPOLL --output build/picture-carousel/batches/picture_carousel_broad_timed_poll_001.json --boot-wait 5 --first-wait 3 --poll-interval 1 --poll-timeout 25 --snapshot-raw build/picture-carousel/snapshot/picture_carousel_broad_poll.raw --snapshot-qcow build/picture-carousel/snapshot/picture_carousel_broad_poll.qcow2`
- `python3 -B tools/picture_carousel.py --preset broad --mode timed --poll --delay-cycles 120 --speed-value 1 --fixture-root build/picture-carousel/timed-broad-poll-fast-fixtures --dos-dir PICPOLL --output build/picture-carousel/batches/picture_carousel_broad_timed_poll_fast_001.json --boot-wait 5 --first-wait 3 --poll-interval 0.5 --poll-timeout 15 --snapshot-raw build/picture-carousel/snapshot/picture_carousel_broad_poll_fast.raw --snapshot-qcow build/picture-carousel/snapshot/picture_carousel_broad_poll_fast.qcow2`
- `python3 -B tools/picture_carousel.py --preset broad --mode timed --poll --delay-cycles 60 --speed-value 1 --fixture-root build/picture-carousel/timed-broad-poll-faster-fixtures --dos-dir PICPOLL --output build/picture-carousel/batches/picture_carousel_broad_timed_poll_faster_001.json --boot-wait 5 --first-wait 3 --poll-interval 0.25 --poll-timeout 10 --snapshot-raw build/picture-carousel/snapshot/picture_carousel_broad_poll_faster.raw --snapshot-qcow build/picture-carousel/snapshot/picture_carousel_broad_poll_faster.qcow2`

Documented result:

- The local SQ2 logic message scan did not find obvious script-level speed-menu
  text, so the speed investigation moved to the executable.
- `code.engine.main_cycle` calls helper `0x7f78` near the start of each cycle.
  That helper reads byte `DS:0x0013`, which is script variable `v10` because
  byte variables start at `DS:0x0009`, spins until word `[0x1784]` is greater
  than or equal to that value, then clears `[0x1784]`. Setting `v10` lower
  makes the top-level cycle run faster; timed-carousel fixtures use `v10 = 1`
  as a fast but capturable pace.
- The timed carousel avoids parser/key-event side effects by advancing after a
  generated per-cycle counter rather than a keyboard event. It also sets flag
  7 before generated picture loads to suppress resource-event pair recording
  during the artificial sweep.
- Fixed-sleep timed captures were brittle. With `delay-cycles 120`, a broad run
  captured pictures `1,17,43,44,46,76,76,76`; with `delay-cycles 240`, it
  captured `1,6,6,17,43,43,44,45`. These were cadence misses: identity checks
  found exact matches to other broad-preset pictures.
- Reordering each transition to update carousel state before discarding the
  old picture let the timed sequence advance through the whole broad list, but
  fixed sleeps still drifted as picture load/draw time varied.
- Polling mode solves the cadence problem for this use case. It repeatedly
  captures a QEMU `screendump` and compares it to the expected local render
  until that expected picture appears, then moves to the next expected picture.
- Timed polling run `picture_carousel_broad_timed_poll_001` matched all eight
  broad pictures with `delay-cycles 240`, `speed-value 1`, and 0 mismatches.
- Faster timed polling run `picture_carousel_broad_timed_poll_fast_001` also
  matched all eight broad pictures with `delay-cycles 120`, `speed-value 1`,
  0.5-second polling, and 0 mismatches. This is the current recommended
  one-engine broad picture sweep.
- `delay-cycles 60` was too short for reliable polling and missed all
  intermediate broad pictures except the final picture 76. Do not use that as
  a default for broad resource sweeps.

## 2026-07-04: all-picture timed polling carousel chunking

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/picture_carousel.py --preset all --mode timed --poll --delay-cycles 120 --speed-value 1 --fixture-root build/picture-carousel/timed-all-poll-fixtures --dos-dir PICALL --output build/picture-carousel/batches/picture_carousel_all_timed_poll_001.json --boot-wait 5 --first-wait 3 --poll-interval 0.5 --poll-timeout 20 --snapshot-raw build/picture-carousel/snapshot/picture_carousel_all_poll.raw --snapshot-qcow build/picture-carousel/snapshot/picture_carousel_all_poll.qcow2`
- Local identity comparison of mismatched captures against all present local SQ2
  picture renders.
- `magick build/picture-carousel/timed-all-poll-fixtures/carousel/qemu_picture_020.ppm build/picture-carousel/timed-all-poll-fixtures/carousel/qemu_picture_020.png`
- `mdir -i build/picture-carousel/snapshot/picture_carousel_all_poll.raw@@32256 ::/PICALL`
- `xxd -g 1 -s 61353 -l 32 build/picture-carousel/timed-all-poll-fixtures/carousel/VOL.3`
- `xxd -g 1 -s 60 -l 9 build/picture-carousel/timed-all-poll-fixtures/carousel/PICDIR`
- Added `--chunk-size` support and per-case polling progress to
  `tools/picture_carousel.py`.
- Added chunking coverage to `tests/test_picture_carousel.py`.
- `python3 -B -m unittest tests.test_picture_carousel`
- `python3 -B tools/picture_carousel.py --preset all --mode timed --poll --chunk-size 16 --delay-cycles 120 --speed-value 1 --fixture-root build/picture-carousel/timed-all-poll-chunk16-fixtures --dos-dir PICALL --output build/picture-carousel/batches/picture_carousel_all_timed_poll_chunk16_001.json --boot-wait 5 --first-wait 3 --poll-interval 0.5 --poll-timeout 20 --snapshot-raw build/picture-carousel/snapshot/picture_carousel_all_poll_chunk16.raw --snapshot-qcow build/picture-carousel/snapshot/picture_carousel_all_poll_chunk16.qcow2`

Documented result:

- A single all-present-picture timed polling carousel matched the first 19
  pictures, then all later expected captures were closest to picture 19.
- Inspecting the picture 20 capture showed the original engine's disk prompt:
  `Please insert disk 3 and press ENTER.` The prompt was drawn over picture 19.
- The generated fixture disk still contained `VOL.3` in `C:\PICALL`, and that
  file size was 180,430 bytes. The packed picture 20 record at offset `0xefa9`
  began with the expected record header bytes `12 34 03 86 0e`, and the
  `PICDIR` entry for picture 20 was `30 ef a9`. This rules out the simple
  fixture-copy/header explanation for the prompt.
- Treat this as an original-engine resource lifecycle or disk-prompt boundary
  for oversized generated carousel fixtures, not as renderer behavior to model
  in the clean-room spec.
- The chunked all-present-picture timed polling run used chunks of 16 pictures
  and matched all 74 valid local SQ2 pictures with 74 matches, 0 mismatches,
  and 0 errors across five engine launches.
- Chunking is the current recommended path for larger real-resource carousel
  sweeps: it preserves the faster timed polling workflow while avoiding the
  oversized single-fixture prompt boundary.

## 2026-07-04: dynamic save-write probe

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "save|restore|file-error|file error|0x7d|0x7e|save_game|restore_game|SAVE" tools tests docs/src PROGRESS.md`
- `sed -n '740,825p' docs/src/compatibility_testing.md`
- `sed -n '1,260p' tools/agi_save.py`
- `sed -n '1,320p' tools/qemu_fixture.py`
- `sed -n '1,320p' tools/qemu_snapshot.py`
- Added `tools/save_roundtrip_probe.py`.
- Added `tests/test_save_roundtrip_probe.py`.
- `python3 -B -m unittest tests.test_save_roundtrip_probe`
- `python3 -B tools/save_roundtrip_probe.py --output build/save-roundtrip/save_roundtrip_001.json --boot-wait 5 --draw-wait 8 --post-launch-wait 2 --post-launch-after-text-wait 1 --key-delay 0.08`
- `python3 -B tools/save_roundtrip_probe.py --keys $'codex probe\n' --output build/save-roundtrip/save_roundtrip_002.json --capture build/save-roundtrip/qemu_capture_002.ppm --snapshot-raw build/save-roundtrip/snapshot/save_roundtrip_002.raw --snapshot-qcow build/save-roundtrip/snapshot/save_roundtrip_002.qcow2 --post-run-raw build/save-roundtrip/snapshot/save_roundtrip_after_002.raw --save-output build/save-roundtrip/SQ2SG_002.1 --boot-wait 5 --draw-wait 8 --post-launch-wait 5 --post-launch-after-text-wait 1 --key-delay 0.08`
- `magick build/save-roundtrip/qemu_capture_002.ppm build/save-roundtrip/qemu_capture_002.png`
- `mdir -i build/save-roundtrip/snapshot/save_roundtrip_after_002.raw@@32256 ::/SVRT`
- `python3 -B tools/save_roundtrip_probe.py --description abc --no-submit-description --output build/save-roundtrip/save_roundtrip_debug_no_submit.json --capture build/save-roundtrip/qemu_capture_no_submit.ppm --snapshot-raw build/save-roundtrip/snapshot/save_roundtrip_no_submit.raw --snapshot-qcow build/save-roundtrip/snapshot/save_roundtrip_no_submit.qcow2 --post-run-raw build/save-roundtrip/snapshot/save_roundtrip_after_no_submit.raw --save-output build/save-roundtrip/SQ2SG_no_submit.1 --boot-wait 5 --draw-wait 4 --path-prompt-wait 2 --description-wait 3 --key-delay 0.12`
- `python3 -B tools/save_roundtrip_probe.py --output build/save-roundtrip/save_roundtrip_005.json --capture build/save-roundtrip/qemu_capture_005.ppm --snapshot-raw build/save-roundtrip/snapshot/save_roundtrip_005.raw --snapshot-qcow build/save-roundtrip/snapshot/save_roundtrip_005.qcow2 --post-run-raw build/save-roundtrip/snapshot/save_roundtrip_after_005.raw --save-output build/save-roundtrip/SQ2SG_005.1 --boot-wait 5 --draw-wait 8 --path-prompt-wait 2 --slot-wait 1 --description-wait 1 --key-delay 0.08`
- `python3 -B tools/save_roundtrip_probe.py --output build/save-roundtrip/save_roundtrip_006.json --capture build/save-roundtrip/qemu_capture_006.ppm --snapshot-raw build/save-roundtrip/snapshot/save_roundtrip_006.raw --snapshot-qcow build/save-roundtrip/snapshot/save_roundtrip_006.qcow2 --post-run-raw build/save-roundtrip/snapshot/save_roundtrip_after_006.raw --save-output build/save-roundtrip/SQ2SG_006.1 --boot-wait 5 --draw-wait 8 --path-prompt-wait 2 --slot-wait 1 --description-wait 1 --confirmation-wait 1 --key-delay 0.08`
- `mdir -i build/save-roundtrip/snapshot/save_roundtrip_after_006.raw@@32256 ::/SVRT`
- `mcopy -o -i build/save-roundtrip/snapshot/save_roundtrip_after_006.raw@@32256 ::/SVRT/SG.1 build/save-roundtrip/SG_006.1`
- `python3 -B -c "import sys; from pathlib import Path; sys.path.insert(0, 'tools'); from agi_save import load_save; s=load_save(Path('build/save-roundtrip/SG_006.1')); print(s.description); print([b.length for b in s.blocks]); print(Path('build/save-roundtrip/SG_006.1').stat().st_size)"`
- `python3 -B tools/save_roundtrip_probe.py --output build/save-roundtrip/save_roundtrip_007.json --capture build/save-roundtrip/qemu_capture_007.ppm --snapshot-raw build/save-roundtrip/snapshot/save_roundtrip_007.raw --snapshot-qcow build/save-roundtrip/snapshot/save_roundtrip_007.qcow2 --post-run-raw build/save-roundtrip/snapshot/save_roundtrip_after_007.raw --save-output build/save-roundtrip/SG_007.1 --boot-wait 5 --draw-wait 8 --path-prompt-wait 2 --slot-wait 1 --description-wait 1 --confirmation-wait 1 --key-delay 0.08`

Documented result:

- The new probe builds a synthetic fixture that removes existing save files,
  displays a blank picture, loads view 11, calls action `0x7d`, redraws the
  picture, draws view 11 at X 50 after the save action returns, and loops.
- The first one-shot key sequence did not write a save. Its capture showed the
  save-description prompt with a blank input line, proving the original action
  had reached the save UI but the typed description had not landed in the
  correct editor.
- A no-leading-Enter sequence appended `codex probe` to the path prompt and
  produced the visible message `There is no directory named \SVRTcodex probe.`
  This established that the first save UI stage is path acceptance.
- A no-submit debug run after accepting the path showed the numbered save-slot
  selector. This established the second UI stage: select a slot before typing
  the description.
- After adding path, slot, description, and final confirmation stages, the
  original engine wrote `SG.1` in the synthetic `C:\SVRT` fixture directory.
  The name lacks the `SQ2` prefix seen in the checked-in `SQ2/SQ2SG.*` files;
  the probe therefore exposes `--save-stem` for future game/interpreter runs.
- The extracted dynamic save file parsed through `tools/agi_save.py` with
  description `codex probe`, block lengths `1505`, `903`, `328`, `100`, and
  `12`, and total size 2889 bytes.
- The fourth block length differs from the checked-in local SQ2 saves'
  observed `200` byte fourth block. The source-backed writer uses
  `[0x0141] * 2`, so this dynamic fixture's shorter object/list state implies
  a runtime count of 50 entries for the generated no-save scenario.
- The post-save QEMU capture matched the expected validation screen with
  0 visual mismatches, proving that the save action returned to following
  bytecode after the original engine wrote the file.
- This section establishes dynamic save-write evidence. The following section
  records the restore probe built from the generated save bytes.

## 2026-07-04: dynamic restore probe from generated save

Commands run from `/Users/peter/ai/agi/reverse`:

- Extended `tools/save_roundtrip_probe.py` with restore fixture generation and
  `--mode restore`.
- Added restore fixture coverage to `tests/test_save_roundtrip_probe.py`.
- `python3 -B -m unittest tests.test_save_roundtrip_probe`
- `python3 -B tools/save_roundtrip_probe.py --mode restore --save-input build/save-roundtrip/SG_007.1 --output build/save-roundtrip/restore_roundtrip_001.json --fixture build/save-roundtrip/restore-fixture --dos-dir RSVT --capture build/save-roundtrip/restore_capture_001.ppm --snapshot-raw build/save-roundtrip/snapshot/restore_roundtrip_001.raw --snapshot-qcow build/save-roundtrip/snapshot/restore_roundtrip_001.qcow2 --boot-wait 5 --draw-wait 8 --path-prompt-wait 2 --slot-wait 1 --confirmation-wait 1 --key-delay 0.08`
- `magick build/save-roundtrip/restore_capture_001.ppm build/save-roundtrip/restore_capture_001.png`
- `python3 -B tools/save_roundtrip_probe.py --mode restore --save-input build/save-roundtrip/SG_007.1 --output build/save-roundtrip/restore_roundtrip_002.json --fixture build/save-roundtrip/restore-fixture --dos-dir RSVT --capture build/save-roundtrip/restore_capture_002.ppm --snapshot-raw build/save-roundtrip/snapshot/restore_roundtrip_002.raw --snapshot-qcow build/save-roundtrip/snapshot/restore_roundtrip_002.qcow2 --boot-wait 5 --draw-wait 8 --path-prompt-wait 5 --slot-wait 1 --confirmation-wait 1 --key-delay 0.08`
- `mdir -i build/save-roundtrip/snapshot/restore_roundtrip_002.raw@@32256 ::/RSVT`
- `python3 -B tools/save_roundtrip_probe.py --mode restore --save-input build/save-roundtrip/SG_007.1 --save-stem SQ2SG --output build/save-roundtrip/restore_roundtrip_sq2stem_001.json --fixture build/save-roundtrip/restore-fixture-sq2stem --dos-dir RSV2 --capture build/save-roundtrip/restore_capture_sq2stem_001.ppm --snapshot-raw build/save-roundtrip/snapshot/restore_roundtrip_sq2stem_001.raw --snapshot-qcow build/save-roundtrip/snapshot/restore_roundtrip_sq2stem_001.qcow2 --boot-wait 5 --draw-wait 8 --path-prompt-wait 5 --slot-wait 1 --confirmation-wait 1 --key-delay 0.08`
- Source rereads around `0x5b73`, `0x8b9f`, `0x85e5`, and `0x2512` showed
  that `DS:0x0002` supplies both the filename prefix in `%s%s%ssg.%d` and the
  saved-state signature checked by the slot summary reader.
- Updated `tools/save_roundtrip_probe.py` so generated fixtures call
  `0x8f verify_game_signature` with message `SQ2` before save/restore, then
  reran:
  `python3 -B tools/save_roundtrip_probe.py --output build/save-roundtrip/save_roundtrip_010.json --capture build/save-roundtrip/qemu_capture_010.ppm --snapshot-raw build/save-roundtrip/snapshot/save_roundtrip_010.raw --snapshot-qcow build/save-roundtrip/snapshot/save_roundtrip_010.qcow2 --post-run-raw build/save-roundtrip/snapshot/save_roundtrip_after_010.raw --save-output build/save-roundtrip/SQ2SG_010.1 --boot-wait 5 --draw-wait 8 --path-prompt-wait 2 --slot-wait 1 --description-wait 1 --confirmation-wait 1 --key-delay 0.08`
- Updated the restore fixture oracle so success is distinguished from ordinary
  continuation after `0x7e`: the save fixture sets a packed flag and validation
  variables with X=50, while the restore fixture starts with X=90 and draws
  from restored variables only when the saved flag is present. Reran:
  `python3 -B tools/save_roundtrip_probe.py --mode restore --save-input build/save-roundtrip/SQ2SG_010.1 --output build/save-roundtrip/restore_roundtrip_sq2stem_006.json --fixture build/save-roundtrip/restore-fixture-signed --dos-dir RST6 --capture build/save-roundtrip/restore_capture_sq2stem_006.ppm --snapshot-raw build/save-roundtrip/snapshot/restore_roundtrip_sq2stem_006.raw --snapshot-qcow build/save-roundtrip/snapshot/restore_roundtrip_sq2stem_006.qcow2 --boot-wait 5 --draw-wait 8 --path-prompt-wait 8 --path-keys $'\n\n' --slot-wait 2 --slot-keys $'\n\n' --confirmation-wait 1 --confirmation-keys $'\n\n' --key-delay 0.12`

Documented result:

- The first restore fixture logic used the same byte layout as the save fixture,
  but the action byte was `0x7e` instead of `0x7d`. That proved too weak as a
  restore oracle: source at `0x2512..0x26af` shows a successful restore returns
  zero and ends the current logic stream, while cancel/open-failure paths can
  continue after `0x7e`.
- The first restore run copied the generated save bytes into the fixture as
  `SG.1`, matching the filename that the synthetic save action wrote. The
  capture stayed at the restore path prompt and mismatched the validation
  screen.
- Increasing the path prompt wait did not change that result. The fixture disk
  did contain `SG.1`, so the likely failure was filename selection rather than
  missing copied data.
- Copying the same generated save bytes into the restore fixture as `SQ2SG.1`
  made the old restore selector advance, but the later X=90/X=50 oracle showed
  that this was still just the continuation path, not a proven restore.
- Source explains the filename-stem behavior: action `0x8f` copies a logic
  message into `DS:0x0002` and verifies it against the embedded `SQ2` string;
  formatter `0x5b73` then uses `DS:0x0002` as the third `%s` in
  `%s%s%ssg.%d`; slot summary reader `0x8b9f` also compares the first payload
  bytes of a candidate save against the same string. The early synthetic
  fixture skipped `0x8f`, so it saved a blank-prefix `SG.1` whose state block
  started with zeroes. The corrected fixture calls `0x8f("SQ2")`, writes
  `SQ2SG.1`, and the first state block starts `53 51 32 00`.
- `restore_roundtrip_sq2stem_006` is the first restore probe in this sequence
  that proves actual restored state: it matched the X=50 branch gated by the
  restored flag/variables with 0 visual mismatches. A failure/cancel return
  after `0x7e` draws X=90 and mismatches the X=50 oracle.

## 2026-07-04: dynamic restore read-error UI probe

Commands run from `/Users/peter/ai/agi/reverse`:

- Extended `tools/save_roundtrip_probe.py` with `--mode restore-read-error`.
  The generated fixture writes `SQ2SG.1` as a malformed save that is still
  selector-visible: a 31-byte description, declared first-block length
  `0x05e1`, and seven payload bytes `53 51 32 00 00 00 00`.
- Added fixture-shape tests to `tests/test_save_roundtrip_probe.py`.
- `python3 -B -m unittest tests.test_save_roundtrip_probe`
- First broad-key run, which sent redundant Enters and therefore captured DOS
  after the fatal dialog was dismissed:
  `python3 -B tools/save_roundtrip_probe.py --mode restore-read-error --output build/save-roundtrip/restore_read_error_001.json --fixture build/save-roundtrip/restore-read-error-fixture --dos-dir RERR --capture build/save-roundtrip/restore_read_error_001.ppm --snapshot-raw build/save-roundtrip/snapshot/restore_read_error_001.raw --snapshot-qcow build/save-roundtrip/snapshot/restore_read_error_001.qcow2 --boot-wait 5 --draw-wait 8 --path-prompt-wait 8 --path-keys $'\n\n' --slot-wait 2 --slot-keys $'\n\n' --confirmation-wait 1 --confirmation-keys $'\n' --key-delay 0.12`
- Prompt-timing captures:
  `restore_read_error_prompt_001`, `restore_read_error_slot_001`,
  `restore_read_error_after_slot_001`, and `restore_read_error_exact_001`.
- Stable capture using exactly one Enter per prompt:
  `python3 -B tools/save_roundtrip_probe.py --mode restore-read-error --output build/save-roundtrip/restore_read_error_002.json --fixture build/save-roundtrip/restore-read-error-fixture --dos-dir RERR --capture build/save-roundtrip/restore_read_error_002.ppm --snapshot-raw build/save-roundtrip/snapshot/restore_read_error_002.raw --snapshot-qcow build/save-roundtrip/snapshot/restore_read_error_002.qcow2 --boot-wait 5 --draw-wait 8 --path-prompt-wait 8 --path-keys $'\n' --slot-wait 2 --slot-keys $'\n' --confirmation-wait 1 --confirmation-keys $'\n' --key-delay 0.12`
- `python3 -B tools/inspect_ppm.py build/save-roundtrip/restore_read_error_002.ppm`
- `magick build/save-roundtrip/restore_read_error_002.ppm build/save-roundtrip/restore_read_error_002.png`

Documented result:

- The malformed `SQ2SG.1` is 40 bytes long and intentionally cannot parse as a
  complete save envelope. It is still valid enough for the selector summary
  path: after the 31-byte description, `code.save.read_slot_summary` skips the
  first length prefix and reads the seven available payload bytes, which match
  the `SQ2` signature prefix established by `0x8f`.
- The timing captures show the expected UI sequence: restore directory prompt,
  selector row with description `codex probe`, confirmation dialog naming
  `\rerr\sq2sg.1`, then the read-error dialog.
- The stable final capture remains on the read-error dialog after an 8-second
  wait, proving that the dialog waits for an Enter rather than immediately
  exiting. Its text is `Error in restoring game. Press ENTER to quit.`
- `restore_read_error_002.ppm` has geometry `640x400`, RGB SHA-256
  `556971f26fc34deb32497a9d10c08eedeb28f6bdb0957cd7676a8ef26830849c`,
  3 unique colors, and non-background bounding box `(0, 136, 639, 399)`.
  Sending extra Enters after confirmation dismisses this fatal dialog and
  leaves the process back at DOS, explaining the first failed capture.

## 2026-07-04: heap startup initialization source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `grep -n "heap initialization\|heap init\|0x0a55\|0x0a57\|0x1476\|0x1485\|0x13d6" docs/src/clean_room_executable_notes.md docs/src/runtime_model.md docs/src/symbolic_labels.md docs/src/agi_executable.md`
- `ndisasm -b 16 -o 0x13a0 -e 0x13a0 build/cleanroom/AGI.decrypted.exe | sed -n '1,220p'`
- `rg -n "0a55|0a57|0a5b|0a5f|0a59|heap\\.base|heap\\.limit|current_top" build docs/src tools tests`
- Local byte-pattern scan over `build/cleanroom/AGI.decrypted.exe` for writes
  to `0x0a55`, `0x0a57`, `0x0a5b`, and `0x0a5f`.
- `ndisasm -b 16 -o 0x1600 -e 0x1600 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x43d0 -e 0x43d0 build/cleanroom/AGI.decrypted.exe | sed -n '1,160p'`
- `xxd -g 1 -s 0x1620 -l 0x90 build/cleanroom/AGI.decrypted.exe`
- `xxd -g 1 -s 0x4400 -l 0x60 build/cleanroom/AGI.decrypted.exe`

Documented result:

- The existing heap helper labels remain correct for allocator behavior:
  `[0x0a55]` is the current top, `[0x0a57]` is the base, `[0x0a59]` is the
  room/reset mark, `[0x0a5b]` is the limit, `[0x0a5d]` is the temporary mark,
  and `[0x0a5f]` is the high-water pointer. The helper cluster around image
  `0x1600` includes the direct rewind, temporary mark, room/reset mark, reset,
  free-memory-byte update, and heap-status display paths already documented in
  earlier notes.
- Startup memory setup around image `0x43ea` is the missing initialization
  source. It computes memory sizing globals, resizes/probes the resident block
  with DOS `AH=4a`, requests a runtime memory block with DOS `AH=48h`, and on
  success converts the returned segment into a DS-relative byte offset by
  subtracting `0x0a01` and shifting left four bits.
- That converted offset is stored into both `[0x0a55]` and `[0x0a57]`, so the
  heap current pointer initially equals the heap base. The limit is then
  computed from word `[0x112c]` as `([0x112c] << 4) + [0x0a57]` and stored into
  `[0x0a5b]`.
- If either DOS allocation in this startup routine fails, the path displays a
  startup memory error and terminates through DOS rather than entering the
  interpreter with a partial heap.

## 2026-07-04: sound hardware-output source pass

Commands run from `/Users/peter/ai/agi/reverse`:

- `grep -n "sound\|tone\|attenuation\|speaker\|driver\|0x80f3\|0x1790\|0x1806" docs/src/clean_room_executable_notes.md docs/src/runtime_model.md docs/src/symbolic_labels.md docs/src/logic_bytecode.md docs/src/compatibility_testing.md`
- `ndisasm -b 16 -o 0x80e0 -e 0x80e0 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x8150 -e 0x8150 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- `ndisasm -b 16 -o 0x7f80 -e 0x7f80 build/cleanroom/AGI.decrypted.exe | sed -n '1,260p'`
- `ndisasm -b 16 -o 0x82c0 -e 0x82c0 build/cleanroom/AGI.decrypted.exe | sed -n '1,180p'`
- Added `pc_speaker_divisor()` and `pc_speaker_event_enabled()` to
  `tools/agi_sound.py`.
- `python3 -B -m unittest tests.test_sound_resources`

Documented result:

- The already documented channel scheduling remains the portable gameplay
  contract: active channel set, countdown/event timing, per-channel attenuation
  nibble, and completion flag. The hardware-output pass adds only the
  source-backed driver-interface details.
- On hardware selectors `0` and `8`, `code.sound.driver_write_tone` uses the
  PIT/PC-speaker path. If the current attenuation nibble is `0x0f`, it clears
  bits `0` and `1` of port `0x61`. Otherwise it computes a divisor from the
  16-bit tone word as
  `12 * (((tone_word & 0x3f) << 4) + ((tone_word >> 8) & 0x0f))`, writes mode
  byte `0xb6` to port `0x43`, writes the low and high divisor bytes to port
  `0x42`, and sets bits `0` and `1` of port `0x61`.
- On stop, the selector `0`/`8` path calls the same tone helper with a silence
  control byte, while other selector paths write bytes `0x9f`, `0xbf`, `0xdf`,
  and `0xff` to port `0xc0`.
- For non-`0`/`8` selectors, `code.sound.driver_write_tone` writes encoded
  tone/control bytes to port `0xc0`: it writes the high tone byte, and writes
  the low tone byte unless the high byte's top three bits are all set.
  Selector `2` first applies the small control-byte adjustment at helper
  `0x8345`.
- `code.sound.driver_write_attenuation` maintains the low-nibble attenuation
  value, applies a per-channel envelope/delta table when active, adjusts
  selector `2` attenuation values below 8 upward by 2, combines the low nibble
  with a stored high-nibble channel mask, and writes the result to port `0xc0`.
- The new local test locks down the source formula for sound 1's first event:
  tone word `0x8037` produces PC-speaker divisor `10560`, and its control byte
  `0x9f` has attenuation nibble `0x0f`, so it is silent on the PC-speaker
  gate.

## 2026-07-04: sound attenuation envelope source model

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x8362)) count=360 2>/dev/null | ndisasm -b 16 -o 0x8162 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x82f3)) count=140 2>/dev/null | ndisasm -b 16 -o 0x80f3 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x8196)) count=180 2>/dev/null | ndisasm -b 16 -o 0x7f96 -`
- `xxd -g 1 -s 0x17b8 -l 72 SQ2/AGIDATA.OVL`
- `python3 -B -m unittest tests.test_sound_resources`

Documented result:

- `code.sound.driver_start` initializes each channel's envelope table pointer
  at `[0x17b0..0x17b7]` to `0x17b8`, each envelope index at
  `[0x17a0..0x17a7]` to `0xffff`, and the per-channel active words to
  `0xffff`.
- On event reads, `code.sound.driver_tick` resets envelope index `+0x17a0` to
  zero for channels with `BX != 6` before reading a new duration/tone/control
  record. Channel 3 (`BX == 6`) keeps its current envelope index across event
  reads in the observed source.
- `code.sound.driver_write_attenuation` (`0x8162`) reads the base attenuation
  byte from `[BX+0x17a8]`. If it is `0x0f`, the helper skips envelope and
  selector-2 adjustment and writes the silent low nibble with the channel mask.
- If the base attenuation is not `0x0f` and envelope index `[BX+0x17a0]` is not
  `0xffff`, the helper reads one byte from table pointer `[BX+0x17b0]` at that
  index. Byte `0x80` disables the envelope and copies previous envelope value
  `[BX+0x17a9]` into the base attenuation byte. Other bytes are applied as
  signed-ish deltas from the base attenuation, not cumulative deltas from the
  previous envelope value; negative underflow clamps to zero and positive
  overflow clamps to `0x0f`. The clamped value is stored in `[BX+0x17a9]`.
- After envelope processing, the helper adds runtime byte `[0x0020]` and clamps
  to `0x0f`. Hardware selector `2` then raises non-silent attenuation values
  below `8` by `2`. Finally it ORs the low nibble with the high channel mask
  from `[BX+0x17fc]` and writes the result to port `0xc0`.
- The default table at `0x17b8` begins
  `fe fd fe ff 00 00 01 01 ...` and terminates with `0x80`. The observed
  channel masks are `0x90`, `0xb0`, `0xd0`, and `0xf0`.
- Added `SoundAttenuationState`, `SoundAttenuationOutput`,
  `default_attenuation_envelope()`, `sound_channel_output_mask()`, and
  `sound_attenuation_output()` to `tools/agi_sound.py`. Local tests cover the
  source table bytes, channel masks, selector-2 adjustment, delta clamps, and
  `0x80` terminator behavior.

## 2026-07-04: source-backed opcode dynamic-probe audit

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1080,1112p' docs/src/compatibility_testing.md`
- `sed -n '1268,1298p' docs/src/compatibility_testing.md`
- `rg -n "0x6e|0x83|0x8e|0xaa|0xad|source-backed" docs/src/logic_bytecode.md docs/src/runtime_model.md docs/src/compatibility_testing.md PROGRESS.md`
- `sed -n '387,397p' PROGRESS.md`

Documented result:

- The five non-QEMU-validated action rows are intentionally source-backed for
  the current full-EGA spec target rather than unfinished core semantics.
- `0x6e` (`shake_screen_like`) is source-backed for its CRT/display-register
  timing loop. The existing dispatch smoke proves bytecode continuation, but a
  screenshot is not a useful portable oracle for the transient hardware effect.
- `0x83` (`clear_global_0139`) is source-backed at the main-cycle mirror point.
  Logic script writes occur after the pre-logic mirror and can be overwritten
  by the next restore path, so a bytecode-only QEMU fixture would mostly prove
  the harness timing rather than the interpreter contract.
- `0x8e` (`set_global_0141_and_refresh`) resets the event-pair capacity state.
  The downstream save/restore replay behavior is already QEMU-backed through
  `0xab`/`0xac`; probing the raw reset directly would require a narrow internal
  state hook.
- `0xaa` (`copy_save_description_to_string_slot`) copies from runtime data
  segment buffer `0x0e72`; the earlier failed static `AGIDATA.OVL` patch did
  not populate that runtime buffer. A representative dynamic probe would need
  to drive the save/restore selector that fills it.
- `0xad` (`increment_global_1530`) is source-backed in the keyboard IRQ release
  gate. A direct QEMU fixture would depend on raw scan-code release timing
  rather than a stable high-level gameplay observable.
- Updated `PROGRESS.md` and `docs/src/compatibility_testing.md` so these rows
  are no longer treated as high-value dynamic-probe work unless a future harness
  can drive their runtime state directly.

## 2026-07-04: update-list draw-order source model

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "draw ordering|draw order|update-list|update list|dirty|persistent|0x6a54|0x6a8e|0x16ff|0x1703|0x57cf|0x9db6|0x9e35" docs/src/graphics_object_pipeline.md docs/src/runtime_model.md docs/src/symbolic_labels.md tools tests`
- Initial exploratory `ndisasm` windows around `0x69f0`, `0x5700`, and
  `0x9d80`; the first executable windows were discarded because `ndisasm -e`
  was again easy to misread as an end address rather than a file skip.
- Corrected source slices with the EXE header offset included:
  `ndisasm -b 16 -o 0x6a20 -e 0x6c20 build/cleanroom/AGI.decrypted.exe`,
  `ndisasm -b 16 -o 0x5728 -e 0x5928 build/cleanroom/AGI.decrypted.exe`,
  `ndisasm -b 16 -o 0x0358 -e 0x0558 build/cleanroom/AGI.decrypted.exe`,
  `ndisasm -b 16 -o 0x042f -e 0x062f build/cleanroom/AGI.decrypted.exe`,
  `ndisasm -b 16 -o 0x045e -e 0x065e build/cleanroom/AGI.decrypted.exe`,
  and `ndisasm -b 16 -o 0x4cbb -e 0x4ebb build/cleanroom/AGI.decrypted.exe`.
- `rg -n "0x1322|1322|127a|priority_table|data\\.priority|0x124a" docs/src/symbolic_labels.md docs/src/graphics_object_pipeline.md docs/src/runtime_model.md tools`
- `xxd -g 1 -s 0x1240 -l 0x20 SQ2/AGIDATA.OVL`
- `xxd -g 1 -s 0x1320 -l 0x20 SQ2/AGIDATA.OVL`
- Local byte-pattern scan over `build/cleanroom/AGI.decrypted.exe` for writes
  to word `0x124a`.
- Added update-list ordering helpers to `tools/agi_graphics.py`.
- `python3 -B -m unittest tests.test_graphics_rendering`

Documented result:

- Source confirms the two root wrappers already documented: `0x6a8e` rebuilds
  and draws root `0x1703`, then root `0x16ff`; `0x6aab` refreshes root `0x1703`,
  then root `0x16ff`.
- Shared builder `0x0358(root, callback)` scans the 43-byte object table in
  memory order. Accepted records are stored with a draw key. The key is object
  baseline field `+0x05` unless flag bit `0x0004` is set, in which case it is
  `0x4cbb(object[+0x24])`.
- The builder then selects the smallest remaining key on each pass. It uses a
  signed comparison against an initial `0x00ff` best key and preserves the
  first object-table entry for equal keys. Consumed keys are overwritten with
  `0x00ff`.
- Helper `0x042f` inserts newly allocated 16-byte render nodes at the head of
  the root list; the first inserted node remains the root tail. Helper `0x045e`
  draws from tail toward previous pointers, saving a backing rectangle through
  `IBM_OBJS.OVL:0x9db0` and then drawing through `IBM_OBJS.OVL:0x9db6`.
  Combining these paths means objects draw in ascending key order within a
  root, while equal-key objects draw in object-table order and later entries
  can cover earlier entries.
- Helper `0x4cbb(value)` in SQ2's normal mode scans the priority table from
  one-past index `0xa8` downward and returns the first index whose byte is less
  than `value`; `value == 0` returns `0xffff`. The local AGIDATA byte at
  `0x127a + 0xa8` is zero, and a local byte-pattern scan found only the
  `0x4d10` helper clearing word `[0x124a]`, not a write that enables the
  alternate direct formula branch.
- Added `ObjectDrawCandidate`, `priority_value_to_sort_y`,
  `object_update_root`, `object_update_sort_key`, and
  `object_update_draw_order` to the local renderer helpers. The focused
  graphics test module now includes source-model tests for root order, stable
  equal-key order, and the SQ2 sentinel behavior in the fixed-priority reverse
  mapping.

## 2026-07-04: dirty-rectangle union source model

Commands run from `/Users/peter/ai/agi/reverse`:

- `ndisasm -b 16 -o 0x5762 -e 0x5962 build/cleanroom/AGI.decrypted.exe`
  (the command was useful for the first routine body but also confirmed again
  that `ndisasm -e` is a skip offset, not an end offset, so the terminal output
  continued past `0x57ce`).
- `python3 -B -m unittest tests.test_graphics_rendering`

Documented result:

- Helper `0x5762(object)` returns without display work when word `[0x1216]` is
  zero.
- Otherwise it loads the current frame pointer from object word `+0x10`, the
  saved frame pointer from object word `+0x12`, stores the current frame pointer
  back into `+0x12`, and computes one display rectangle covering both the
  current and saved object footprints.
- The vertical calculation treats object Y fields as baselines. The current top
  is `object[+0x05] - current_frame[+0x01] + 1`; the saved top is
  `object[+0x18] - saved_frame[+0x01] + 1`.
- The horizontal calculation uses left X plus frame width. The rectangle passed
  to overlay entry `0x980c` is `left = min(current_left, saved_left)`,
  `bottom = max(current_bottom, saved_bottom)`, `width = max(current_right,
  saved_right) - left`, and `height = bottom - min(current_top, saved_top) + 1`.
- Added `DirtyRect` and `dirty_rect_union()` to `tools/agi_graphics.py`, with
  focused tests for identical footprints and old/current footprints on opposite
  sides of the union.

## 2026-07-04: control-acceptance source model

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x58b8)) count=220 2>/dev/null | ndisasm -b 16 -o 0x56b8 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x4919)) count=260 2>/dev/null | ndisasm -b 16 -o 0x4719 -`
- `python3 -B -m unittest tests.test_graphics_rendering`

Documented result:

- `code.object.control_acceptance` (`0x56b8`) derives object byte `+0x24` from
  the baseline priority table unless object flag bit `0x0004` is set, computes
  the logical-buffer offset for the object coordinate, and scans one row using
  the current frame width.
- Object priority/control byte `+0x24 == 0x0f` bypasses the buffer scan and
  returns accepted.
- High nibble `0x00` rejects immediately. High nibble `0x10` rejects unless
  object flag bit `0x0002` is set. High nibble `0x20` leaves final class state
  `(flag3=true, flag0=false)`. High nibble `0x30` leaves final class state
  `(flag3=false, flag0=true)`. Other nonzero high nibbles leave final class
  state `(flag3=false, flag0=false)`.
- The source resets class state for each scanned cell, so the final scanned
  class state controls the post-scan gates. This corrects the earlier wording
  that implied class `0x20` was latched once encountered anywhere.
- After a complete scan, object flag bit `0x0100` rejects states whose flag0
  component is false, and object flag bit `0x0800` rejects states whose flag0
  component is true. When object byte `+0x02` is zero, the final class state is
  also written to global flags 3 and 0.
- Added `ControlAcceptance` and `control_acceptance_scan()` to
  `tools/agi_graphics.py`, with focused local tests for class rejection,
  priority-15 bypass, final-class ordering, and event-byte-zero global flag
  values.
- A neighboring slice of `code.object.collision_test` (`0x4719`) confirmed the
  previously documented object-object skip bit `0x0200`, object-table scan,
  grouping-byte skip, horizontal overlap test, and current/saved Y crossing
  test.

## 2026-07-04: view header reserved bytes

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x3bf7)) count=360 2>/dev/null | ndisasm -b 16 -o 0x39f7 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x3e1b)) count=180 2>/dev/null | ndisasm -b 16 -o 0x3c1b -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x60db)) count=180 2>/dev/null | ndisasm -b 16 -o 0x5edb -`
- `python3 -B tools/inspect_view.py | head -n 40`
- `python3 -B -c "import sys; sys.path.insert(0,'tools'); from agi_graphics import iter_valid_resources; from collections import Counter; c=Counter(payload[:2] for _,payload in iter_valid_resources('VIEWDIR')); print(c); print(sorted((k.hex(),v) for k,v in c.items()))"`
- `python3 -B -m unittest tests.test_graphics_rendering`

Documented result:

- `code.view.load_resource` (`0x39f7`) loads/caches a view payload, then calls
  display-mode helper `0x591f` and the update-list rebuild path. It does not
  interpret payload bytes `+0x00` or `+0x01`.
- `code.object.bind_view` (`0x3ae7`) copies the cached payload pointer into the
  object record and reads payload byte `+0x02` as the group count.
- `code.object.select_group_table` (`0x3c1b`) reads group offsets from
  `payload + 0x05 + selected_group * 2`, then reads the selected group count
  from the group pointer.
- The preview/display helper at `0x5edb` binds the view and uses the existing
  object/frame selection path; previous source notes also identified its
  consumer of the preview text offset at payload bytes `+0x03..+0x04`.
- A local census found all 203 valid SQ2 view resources have first two payload
  bytes `01 01`.
- The current clean-room model therefore treats view payload bytes `+0x00` and
  `+0x01` as reserved header bytes for SQ2: preserved in the format model, but
  unused by the observed loader, binder, group/frame selector, and preview
  paths. Future interpreter-version comparisons should flag any divergent use.

## 2026-07-04: direct corner-path unit coverage

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "0xF4|0xf4|corner|draw_corner|base_.*corner|F5|0xf5" tools tests docs/src/compatibility_testing.md docs/src/graphics_object_pipeline.md`
- `python3 -B -m unittest tests.test_graphics_rendering`

Documented result:

- The picture fuzz corpus and prior QEMU batches already include synthetic
  corner-path streams, but the focused graphics unit tests only made the
  command-resume behavior explicit.
- Added direct local regression tests for `0xf4` (`draw_corner_path_y_first`)
  and `0xf5` (`draw_corner_path_x_first`) point sets. These tests do not add a
  new original-engine observation; they make the existing source-modeled rare
  handlers harder to accidentally regress while picture renderer work
  continues.

## 2026-07-04: WORDS.TOK decoder tests

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/inspect_words.py --prefix look --limit 10`
- `python3 -B tools/inspect_words.py --prefix get --limit 10`
- `python3 -B tools/inspect_words.py --prefix anyword --limit 10`
- `python3 -B tools/inspect_words.py --limit 5`
- `python3 -B -m unittest tests.test_words`
- `python3 -B -m unittest tests.test_graphics_rendering`

Documented result:

- The local WORDS.TOK decoder reads 26 big-endian letter offsets followed by
  prefix-compressed entries. The local SQ2 file has 1,099 decoded entries and a
  zero offset for the `x` bucket.
- Known IDs used by parser probes are now locked down in local tests:
  `anyword` has ID `0x0001`, `look` has ID `0x0002`, and `get` has ID
  `0x0005`.
- Prefix-compressed phrase reconstruction is covered by tests for phrases such
  as `look across`, `look down`, and `get inside`.
- This complements the original-engine `parser_edges_001` QEMU batch, which
  validates matching `look get`, wildcard ID `0x0001`, and terminator ID
  `0x270f` through condition `0x0e`.

## 2026-07-04: save path validation plan

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x5ddd)) count=360 2>/dev/null | ndisasm -b 16 -o 0x5bdd -`
- `xxd -g 1 -s 0x135f -l 16 SQ2/AGIDATA.OVL`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x5fea)) count=120 2>/dev/null | ndisasm -b 16 -o 0x5dea -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x603e)) count=120 2>/dev/null | ndisasm -b 16 -o 0x5e3e -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x51ea)) count=120 2>/dev/null | ndisasm -b 16 -o 0x4fea -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x5fb2)) count=90 2>/dev/null | ndisasm -b 16 -o 0x5db2 -`
- `python3 -B -m unittest tests.test_save_resources`

Documented result:

- `code.dos.validate_path` (`0x5bdd`) skips leading spaces before measuring the
  path. If the resulting string is empty it calls `code.dos.get_current_directory`
  (`0x5db2`) to fill the same buffer.
- If the last character is slash or backslash and the path length is greater
  than one, the validator strips that trailing separator in place before
  selecting a validation path. The separator table at `AGIDATA.OVL:0x135f`
  contains backslash, slash, and a terminator.
- If the effective path has a drive prefix (`text[1] == ':'`), the drive letter
  is lowercased by helper `0x4fea` and stored in byte `[0x1363]`; otherwise
  helper `0x5dea` reads the current DOS drive letter into `[0x1363]`.
- A single slash/backslash path returns success immediately. A two-character
  drive path such as `A:` calls helper `0x5e3e`, which switches to the requested
  drive, checks whether DOS accepted it, and switches back. Other paths call
  DOS find-first helper `0x5e01` with attribute `0x10`.
- Added `SavePathValidationPlan` and `save_path_validation_plan()` to
  `tools/agi_save.py`, with tests for leading spaces, empty-current-directory
  fallback, root acceptance, trailing separator stripping, drive-only paths,
  and normal directory lookup classification. The helper models source-level
  string handling and DOS-check selection; it does not claim to know whether a
  given path exists in a future DOS environment.

## 2026-07-04: resource cache record layout polish

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x3b79)) count=130 2>/dev/null | ndisasm -b 16 -o 0x3979 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x4be8)) count=130 2>/dev/null | ndisasm -b 16 -o 0x49e8 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x4c5e)) count=130 2>/dev/null | ndisasm -b 16 -o 0x4a5e -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x52d8)) count=90 2>/dev/null | ndisasm -b 16 -o 0x50d8 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x5326)) count=240 2>/dev/null | ndisasm -b 16 -o 0x5126 -`

Documented result:

- View cache lookup `0x3979` walks the list rooted at `[0x0ffa]`, compares
  record byte `+0x02` against the requested view number, and leaves the link
  slot for insertion in `[0x1000]`. View loader `0x39f7` allocates 5 bytes on a
  miss, links the record through that slot, stores the view number at `+0x02`,
  and stores the payload pointer at `+0x03`.
- Picture cache lookup `0x49e8` walks the list rooted at the static first record
  `[0x120e]`, compares record byte `+0x02`, and leaves the insertion slot in
  `[0x1214]`. Picture loader `0x4a3b` uses the static first record when that
  insertion slot is zero; otherwise it allocates 5 bytes, links it from the
  previous record, stores the picture number at `+0x02`, and stores the payload
  pointer at `+0x03`.
- Sound cache lookup `0x50d8` walks the list rooted at static record
  `[0x125a]`, compares record word `+0x02`, and leaves the insertion slot in
  `[0x1268]`. Sound loader `0x5126` uses the static first record for the first
  sound, otherwise allocates 14 bytes. It stores the sound number word at
  `+0x02`, the payload pointer at `+0x04`, and derives four channel stream
  pointers at `+0x06`, `+0x08`, `+0x0a`, and `+0x0c` from the first four
  little-endian payload offsets.
- Existing logic loader notes already pinned down the 10-byte logic cache
  record: next pointer at `+0x00`, logic number byte at `+0x02`, message count
  at `+0x03`, bytecode pointer at `+0x04`, current instruction pointer at
  `+0x06`, and message-offset-table pointer at `+0x08`.

## 2026-07-04: picture raw-operand scanner edge

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x6675)) count=80 2>/dev/null | ndisasm -b 16 -o 0x6475 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x6694)) count=260 2>/dev/null | ndisasm -b 16 -o 0x6494 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x6803)) count=260 2>/dev/null | ndisasm -b 16 -o 0x6603 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x68ab)) count=260 2>/dev/null | ndisasm -b 16 -o 0x66ab -`
- `python3 -B -m unittest tests.test_graphics_rendering`
- `python3 -B -m unittest tests.test_picture_fuzz`
- `python3 -B tools/picture_fuzz.py generate --count 1024 --seed 4097 --output build/picture-fuzz/corpus --clean`
- `python3 -B tools/picture_fuzz.py batch-qemu --snapshot --case base_033_raw_visual_operand --case base_034_raw_control_operand --case base_035_raw_pattern_mode_operand --dos-prefix RO --fixture-root build/picture-fuzz/fixtures --output build/picture-fuzz/batches/raw_operand_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`

Documented result:

- The top-level picture scanner at `0x6475` dispatches command bytes
  `0xf0..0xfa`, then resumes at `0x647a` using the `AL` byte left by the
  handler. This makes handler-local byte consumption significant.
- Handlers `0x6494` (`0xf0` set visual), `0x64c7` (`0xf2` set control), and
  `0x6524` (`0xf9` set pattern mode) each use a raw `lodsb` operand read and
  then preload the next byte. They do not reject operands `>= 0xf0`.
- Coordinate/list readers `0x66c1`, `0x66d4`, and `0x66b8` do reject bytes
  above `0xef`, returning carry with the command-looking byte in `AL` for the
  scanner to process next. This is the source distinction between raw one-byte
  operands and coordinate/list data.
- Updated `PictureRenderer` with `read_raw_byte()` and changed `0xf0`, `0xf2`,
  and `0xf9` to use it. Added local graphics tests showing that command-looking
  bytes after those opcodes are operands, not commands.
- Added three safe curated fuzz cases:
  `base_033_raw_visual_operand`, `base_034_raw_control_operand`, and
  `base_035_raw_pattern_mode_operand`. Regenerating the deterministic corpus
  produced 1,060 cases, of which 1,058 are marked safe for QEMU.
- Original-engine snapshot batch `raw_operand_001` matched all three new cases
  with 0 mismatches and 0 errors. This confirms the source-modeled scanner edge
  on the visible EGA surface.

## 2026-07-04: picture relative-line underflow edge

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x685e)) count=180 2>/dev/null | ndisasm -b 16 -o 0x665e -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x68e1)) count=260 2>/dev/null | ndisasm -b 16 -o 0x66e1 -`
- `python3 -B -m unittest tests.test_graphics_rendering`
- `python3 -B -m unittest tests.test_picture_fuzz`
- `python3 -B tools/picture_fuzz.py generate --count 1024 --seed 4097 --output build/picture-fuzz/corpus --clean`
- `python3 -B tools/picture_fuzz.py batch-qemu --snapshot --case base_036_relative_x_underflow_wraps --case base_037_relative_y_underflow_wraps --dos-prefix RU --fixture-root build/picture-fuzz/fixtures --output build/picture-fuzz/batches/relative_underflow_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`
- `python3 -B -m unittest tests.test_compatibility_suite`
- `python3 -B tools/compatibility_suite.py --dry-run --include-qemu-smoke`
- `python3 -B tools/compatibility_suite.py --include-qemu-smoke --report build/compatibility-suite/qemu_smoke_002.json`

Documented result:

- Handler `0x665e` reads the initial coordinate pair through `0x66b8`, plots
  it, then consumes relative bytes while they are `<= 0xef`.
- For X, bits `0x70` supply a magnitude and bit `0x80` chooses subtraction.
  The handler adds or subtracts that magnitude in `BH`, an 8-bit coordinate
  register, then clamps only if `BH > 0x9f`. Subtracting from zero therefore
  underflows to a high unsigned byte and is clamped to `0x9f`, not to zero.
- For Y, bits `0x07` supply a magnitude and bit `0x08` chooses subtraction.
  The same byte-register behavior applies, followed by a high-side clamp to
  `0xa7`.
- Updated `PictureRenderer.draw_relative_lines()` to model this 8-bit
  wrap-and-high-clamp behavior. Added local graphics tests for X underflow from
  `(0,10)` to the right edge and Y underflow from `(10,0)` to the bottom edge.
- Added safe curated fuzz cases `base_036_relative_x_underflow_wraps` and
  `base_037_relative_y_underflow_wraps`. Regenerating the deterministic corpus
  produced 1,062 cases, of which 1,060 are marked safe for QEMU.
- Original-engine snapshot batch `relative_underflow_001` matched both new
  cases with 0 mismatches and 0 errors.
- Promoted the new pair into the QEMU smoke layer as
  `picture_fuzz_relative_underflow_qemu`. The updated smoke report
  `qemu_smoke_002.json` passed after running 235 local tests, mdBook,
  opcode-evidence check, parser QEMU probes, command-resume probes,
  raw-operand probes, and the new relative-underflow probes.

## 2026-07-04: parser normalization and output-slot model

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x1b58)) count=180 2>/dev/null | ndisasm -b 16 -o 0x1958 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x1aac)) count=260 2>/dev/null | ndisasm -b 16 -o 0x18ac -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x1b9d)) count=260 2>/dev/null | ndisasm -b 16 -o 0x199d -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x1c6b)) count=360 2>/dev/null | ndisasm -b 16 -o 0x1a6b -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x1dc7)) count=130 2>/dev/null | ndisasm -b 16 -o 0x1bc7 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x1de4)) count=100 2>/dev/null | ndisasm -b 16 -o 0x1be4 -`
- `xxd -g 1 -s 0x0940 -l 48 SQ2/AGIDATA.OVL`
- `xxd -g 1 -s 0x0c70 -l 80 SQ2/AGIDATA.OVL`
- `python3 -B -m unittest tests.test_words`

Documented result:

- Re-read action `0x75` at `0x1958`, parser helper `0x18ac`, normalization
  helper `0x199d`, dictionary lookup helper `0x1a6b`, unknown-token helper
  `0x1bc7`, and dictionary-entry advance helper `0x1be4`.
- Added symbolic labels for the parser action/helper routines and data labels
  for separator bytes `0x0c67`, ignored bytes `0x0c75`, parsed IDs `0x0c7b`,
  parsed word pointers `0x0c8f`, dictionary base pointer `[0x0ca5]`, normalized
  parse buffer `0x0ca7`, and current parse pointer `[0x0cd1]`.
- Added local source-model helpers to `tools/inspect_words.py`:
  `parser_separator_bytes()`, `parser_ignored_bytes()`,
  `normalize_parser_text()`, and `parse_words()`.
- Local tests now validate the SQ2 separator table (` ,.?!();:[]{}`), ignored
  punctuation table (apostrophe, backtick, hyphen, double quote), separator
  collapse, ignored-punctuation removal, case-insensitive lookup, zero-ID word
  filtering, unknown-word reporting, and the ten-output-word limit.
- The output-slot model corrects an easy-to-miss detail: ignored zero-ID
  dictionary words such as `the`, `a`, and `i` do not increment the parser's
  output index. An unknown word after ignored terms therefore records
  `parsed_nonzero_word_count + 1`; for example a phrase shaped like
  `the <unknown> look` reports output slot 1, not raw token ordinal 2.

## 2026-07-04: heap formula test model

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x15d6)) count=260 2>/dev/null | ndisasm -b 16 -o 0x13d6 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x16bd)) count=240 2>/dev/null | ndisasm -b 16 -o 0x14bd -`
- `rg -n "bump|heap|0x13d6|0x14bd|memory" docs/src/runtime_model.md docs/src/symbolic_labels.md docs/src/clean_room_executable_notes.md`
- `python3 -B -m unittest tests.test_heap`

Documented result:

- Rechecked the allocator helper `code.heap.allocate` (`0x13d6`) and the
  heap-status action `code.heap.show_status_action` (`0x14bd`) against the
  existing heap notes and symbolic labels.
- Added `tools/agi_heap.py` as a local source-model helper for the bump heap:
  allocation returns the old current pointer, advances the current pointer,
  recomputes the free-byte count and byte variable 8 page value, and updates
  the high-water pointer only when the new current pointer exceeds the prior
  high-water value.
- The helper also models fatal allocation overflow, one-shot temporary-mark
  restore, dynamic reset to the room/reset mark, and the five heap-status
  numbers printed by action `0x87`.
- Added `tests/test_heap.py`; the focused suite passed 7 tests. This makes the
  allocator/status formulas executable compatibility evidence while leaving
  the visibly rendered out-of-memory path as optional future coverage.

## 2026-07-04: bit-0x80 view mirror edge tests

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x5a7d)) count=420 2>/dev/null | ndisasm -b 16 -o 0x587d -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x5bac)) count=260 2>/dev/null | ndisasm -b 16 -o 0x59ac -`
- `sed -n '2668,2734p' docs/src/clean_room_executable_notes.md`
- `python3 -B -m unittest tests.test_graphics_rendering`

Documented result:

- Re-read `code.object.rewrite_frame_orientation` (`0x587d`) and the nearby
  placement helpers before expanding local coverage for the view/cel mirror
  model.
- The source loop skips explicit leading transparent runs until it sees the
  first nontransparent run. If the row terminator is reached first, it writes
  an empty rebuilt row.
- For rows with visible data, the helper emits the original implicit trailing
  transparent width before reversing the counted run bytes. Widths larger than
  15 are emitted as multiple transparent run bytes because a run length is only
  four bits.
- Added focused local tests for all-transparent rows, implicit transparent
  padding, long transparent chunking, and reversal from the first visible run.
  The graphics suite passed 57 tests after correcting one arithmetic mistake in
  the expected transparent width.

## 2026-07-04: object-overlay priority gate edge tests

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg --files SQ2 build/cleanroom | rg "IBM|OBJ|OVL|AGI.decrypted"`
- `ls -l SQ2 build/cleanroom`
- `sed -n '700,770p' docs/src/clean_room_executable_notes.md`
- `sed -n '2520,2550p' docs/src/clean_room_executable_notes.md`
- `ndisasm -b 16 -o 0x9db0 SQ2/IBM_OBJS.OVL | sed -n '1,260p'`
- `python3 -B -m unittest tests.test_graphics_rendering`

Documented result:

- Confirmed again that the draw entry is in `SQ2/IBM_OBJS.OVL`, not the base
  executable image: entry `0x9db6` jumps to `0x9e35`.
- The draw loop extracts each run byte as color/high nibble plus count/low
  nibble. If the run color is the transparent nibble from frame control byte
  `+0x02`, it advances by the run length without writing.
- For nontransparent pixels, destination high nibbles above `0x20` are compared
  directly with the object's shifted priority/control nibble. The `ja` branch
  rejects only strictly greater values, so equal priority writes are allowed.
- Destination high nibbles `<= 0x20` enter the downward scan at `0x9ec6`. If
  the scan finds a high nibble above `0x20`, that value is compared with the
  same inclusive rule; if the scan reaches the lower limit first, `CH` remains
  zero and even priority 0 passes the local gate.
- Rejection at `0x9ee5` increments the destination pointer and continues the
  run loop, so a blocked pixel does not suppress later pixels in the same run.
- Added local tests for equal scanned priority, no-hit priority 0, and
  per-pixel run continuation. The graphics suite passed 60 tests.

## 2026-07-04: input-word sequence matcher edge

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x0b5c)) count=220 2>/dev/null | ndisasm -b 16 -o 0x095c -`
- `sed -n '336,420p' docs/src/logic_bytecode.md`
- `sed -n '56,104p' docs/src/runtime_model.md`
- `sed -n '5950,5985p' docs/src/clean_room_executable_notes.md`
- `python3 -B -m unittest tests.test_words`
- `python3 -B -m unittest tests.test_logic_interpreter_probe tests.test_words`
- `python3 -B tools/logic_interpreter_probe.py --dos-prefix PU --output build/logic-interpreter-probes/batches/parser_unknown_terminator_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure --case input_word_sequence_terminator_matches_unknown_word`
- `python3 -B tools/logic_opcode_evidence.py`

Documented result:

- Re-read condition handler `code.logic.condition_input_word_sequence`
  (`0x095c`). The handler first rejects when `data.words.parsed_count_or_error_position`
  is zero, flag 4 is already set, or flag 2 is clear. Otherwise it walks the
  variable-length operand word IDs against `data.words.parsed_ids`.
- Operand word ID `0x0001` is a one-word wildcard. Operand word ID `0x270f`
  immediately forces success, skips any remaining operand words, and sets flag
  4 through the normal success path.
- A non-terminator operand after all parsed words have been consumed fails. A
  too-short operand list also fails because the parsed count remains nonzero
  when the operand loop ends.
- Added `InputWordSequenceResult` and `input_word_sequence_matches()` to
  `tools/inspect_words.py`, with local tests for exact match, wildcard,
  terminator skip, extra/non-terminator failure, too-short failure, flag gates,
  and the unknown-token terminator edge.
- The unknown-token edge is now dynamically confirmed: parsing `flarble` stores
  a nonzero parser count/error-position and sets flag 2; condition `0x0e` with
  only word ID `0x270f` matched in QEMU batch
  `parser_unknown_terminator_001` with 1 match, 0 mismatches, and 0 errors.

## 2026-07-04: compatibility suite manifest runner

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "compatibility suite|runner|manifest|broad suite|run_.*suite|snapshot|preset broad|parser_edges|raw_operand" tools tests docs/src/compatibility_testing.md PROGRESS.md AGENTS.md`
- `ls tools tests`
- `sed -n '1,180p' docs/src/compatibility_testing.md`
- `sed -n '380,398p' PROGRESS.md`
- `python3 -B -m unittest tests.test_compatibility_suite`
- `python3 -B tools/compatibility_suite.py --dry-run`
- `python3 -B tools/compatibility_suite.py --dry-run --include-qemu-smoke`
- `python3 -B tools/compatibility_suite.py --report build/compatibility-suite/local_001.json`

Documented result:

- Added `tools/compatibility_suite.py`, a local-by-default manifest/runner for
  the current compatibility layers. The default selection runs the full local
  unit suite, `mdbook build docs`, and
  `python3 -B tools/logic_opcode_evidence.py --check`.
- QEMU checks are explicit opt-ins. The smoke layer includes parser edge
  batches and targeted picture-fuzz scanner/raw-operand batches. The broad
  layer includes the representative picture timed carousel and the current
  view/object stress carousel.
- Added `tests/test_compatibility_suite.py` to lock down manifest contents,
  default layer selection, explicit QEMU layer selection, unknown-name
  rejection, stop-on-first-failure behavior, and report writing without running
  real subprocesses.
- The focused runner tests passed. A real default runner invocation wrote
  `build/compatibility-suite/local_001.json` after the local unit suite passed
  with 230 tests, the mdBook built, and opcode evidence checked cleanly.

## 2026-07-04: sound tone-output boundary model

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x821c)) count=220 2>/dev/null | ndisasm -b 16 -o 0x801c -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x82f3)) count=260 2>/dev/null | ndisasm -b 16 -o 0x80f3 -`
- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x8362)) count=180 2>/dev/null | ndisasm -b 16 -o 0x8162 -`
- `python3 -B -m unittest tests.test_sound_resources`

Documented result:

- Re-read `code.sound.driver_tick` (`0x801c`), tone output helper
  `code.sound.driver_write_tone` (`0x80f3`), the selector-2 internal control
  adjustment helper at `0x8145`, and the attenuation helper at `0x8162`.
- Added `SoundToneOutput`, `sound_tone_output()`, and
  `sound_stop_silence_output()` to `tools/agi_sound.py`.
- For selectors `0` and `8`, the model reports whether the PC-speaker gate is
  enabled and, when enabled, the source PIT divisor. A silent attenuation nibble
  produces disabled gate state and no divisor.
- For other selectors, the model reports the port-`0xc0` tone bytes: high tone
  byte first, low tone byte only when the high byte's top three bits are not
  all set. The stop-core path writes `0x9f`, `0xbf`, `0xdf`, and `0xff`.
- Local sound tests now cover these tone/silence outputs in addition to the
  prior resource parser, schedule, PC-speaker divisor, attenuation envelope,
  and completion tests. `tests.test_sound_resources` passed with 16 tests.

## 2026-07-04: cross-version workflow chapter

Commands run from `/Users/peter/ai/agi/reverse`:

- `sed -n '1,220p' docs/src/SUMMARY.md`
- `sed -n '1,120p' docs/src/symbolic_labels.md`
- `rg -n "cross-version|cross version|symbolic label|other games|future interpreter" docs/src AGENTS.md PROGRESS.md`

Documented result:

- Added `docs/src/cross_version_workflow.md` and linked it from the mdBook
  summary.
- The chapter defines the evidence package to collect for each future
  interpreter/game pair, the structural anchors to use when mapping existing
  symbolic labels to moved routines, the recommended source-first pass order,
  compatibility suite tiers, and delta-recording rules.
- The workflow explicitly avoids claiming that another interpreter has already
  been compared. It moves the cross-version tracker from an empty placeholder to
  a documented process that is blocked only on future local inputs.

## 2026-07-04: compatibility suite QEMU smoke layer

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/compatibility_suite.py --include-qemu-smoke --report build/compatibility-suite/qemu_smoke_001.json`

Documented result:

- A first sandboxed attempt reached the QEMU smoke layer but failed when QEMU
  tried to bind the local VNC socket with `Operation not permitted`. This was a
  sandbox permission failure, not an interpreter or fixture mismatch.
- The rerun with local VNC/socket access passed and wrote
  `build/compatibility-suite/qemu_smoke_001.json`.
- The selected command set included the local unit suite, `mdbook build docs`,
  `tools/logic_opcode_evidence.py --check`, parser-edge QEMU probes,
  unknown-word terminator parser QEMU probe, picture command-resume fuzz QEMU
  probes, and raw-operand picture fuzz QEMU probes.
- Every selected command returned zero. The original-engine probe reports were:
  `parser_edges_suite.json` with 3 matches, `parser_unknown_terminator_suite.json`
  with 1 match, `command_resume_suite.json` with 3 matches, and
  `raw_operand_suite.json` with 3 matches.

## 2026-07-04: compatibility suite QEMU broad layer

Commands run from `/Users/peter/ai/agi/reverse`:

- `python3 -B tools/compatibility_suite.py --include-qemu-broad --report build/compatibility-suite/qemu_broad_002.json`

Documented result:

- The broad suite selection includes the local checks, all QEMU smoke checks,
  and the broad QEMU resource sweeps.
- The smoke checks repeated the same clean results as the dedicated smoke run:
  parser edge probes matched 3/3, the unknown-word terminator probe matched
  1/1, command-resume picture fuzz probes matched 3/3, raw-operand picture
  fuzz probes matched 3/3, and relative-line underflow probes matched 2/2.
- The suite-level broad picture carousel
  `build/picture-carousel/batches/picture_carousel_broad_suite.json` matched
  all 8 broad real-picture cases from one engine process.
- The suite-level view/object stress carousel
  `build/view-carousel/batches/view_carousel_stress_suite.json` matched all 19
  current base-plus-stress cases from one engine process.
- `build/compatibility-suite/qemu_broad_002.json` records return code 0 for
  all selected commands.

## 2026-07-04: object control-acceptance branch tests

Commands run from `/Users/peter/ai/agi/reverse`:

- `dd if=build/cleanroom/AGI.decrypted.exe bs=1 skip=$((0x58b8)) count=360 2>/dev/null | ndisasm -b 16 -o 0x56b8 -`
- `python3 -B -m unittest tests.test_graphics_rendering`

Documented result:

- Re-read `code.object.control_acceptance` at `0x56b8`. The high-nibble scanner
  resets its class-state bytes for each scanned cell. Classes `0x10`, `0x20`,
  and `0x30` have explicit branches; other nonzero high nibbles fall through
  after setting the final state to `(flag3=false, flag0=false)`.
- Added local tests for that fall-through branch: it accepts with no rejection
  bits, rejects when bit `0x0100` is set, and accepts when bit `0x0800` is set.
- Added a local test for priority/control byte `0x0f`, which bypasses scanning
  and clears both reported event flags when object byte `+0x02` is zero.
- `tests.test_graphics_rendering` passed with 64 tests.

## 2026-07-07: Gold Rush AGI v3 resource compression first pass

Context:

- The user identified `games/GR` as a local Gold Rush data set using AGI
  interpreter version 3 and asked for a source-first comparison with the SQ2
  version 2 interpreter.
- The known QEMU BIOS text-rendering problem was set aside as an on-screen text
  caveat. Dynamic checks, if needed later, should use the FreeDOS image path
  rather than the old MS-DOS image.

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `rg --files`
- `ls -la games && ls -la games/GR && ls -la games/SQ2`
- `file games/GR/AGI games/SQ2/AGI`
- `xxd -g 1 -l 64 games/GR/AGI`
- `xxd -g 1 -l 64 games/GR/GRDIR`
- `python3 -B tools/decrypt_agi.py --game-dir games/SQ2 --output build/cleanroom/SQ2_AGI.decrypted.exe`
- `dd if=games/GR/AGI bs=1 skip=$((0x30a0+0x200)) count=760 2>/dev/null | ndisasm -b 16 -o 0x30a0 -`
- `dd if=games/GR/AGI bs=1 skip=$((0x44d0+0x200)) count=520 2>/dev/null | ndisasm -b 16 -o 0x44d0 -`
- `dd if=games/GR/AGI bs=1 skip=$((0x07d0+0x200)) count=720 2>/dev/null | ndisasm -b 16 -o 0x07d0 -`
- `dd if=games/GR/AGI bs=1 skip=$((0x9a40+0x200)) count=420 2>/dev/null | ndisasm -b 16 -o 0x9a40 -`
- `dd if=games/GR/AGI bs=1 skip=$((0x33c0+0x200)) count=520 2>/dev/null | ndisasm -b 16 -o 0x33c0 -`
- `dd if=games/GR/AGI bs=1 skip=$((0x0200+0x200)) count=520 2>/dev/null | ndisasm -b 16 -o 0x0200 -`
- `xxd -g 1 -s 0xf50 -l 128 games/GR/AGIDATA.OVL`
- `strings -a -t d games/GR/AGIDATA.OVL`
- `strings -a -t d games/SQ2/AGIDATA.OVL`
- `python3 -B tools/agi_resources.py --game-dir games/GR --summary --kind logic --number 0`
- `python3 -B tools/agi_resources.py --game-dir games/GR --kind picture --number 1`
- `python3 -B tools/agi_resources.py --game-dir games/GR --kind view --number 0`
- `python3 -B tools/agi_resources.py --game-dir games/SQ2 --summary --kind logic --number 0`
- `python3 -B tools/disassemble_logic.py --game-dir games/GR --stats`
- `python3 -B -m unittest tests/test_agi_resources.py`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests/test_logic_doc_coverage.py tests/test_sound_resources.py`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests`

Documented result:

- `games/GR/AGI` is already an MZ executable. `games/SQ2/AGI` remains an
  encrypted/data file and was decrypted to
  `build/cleanroom/SQ2_AGI.decrypted.exe` for comparison.
- GR `AGIDATA.OVL` contains `Version 3.002.149`; SQ2 `AGIDATA.OVL` contains
  `Version 2.936`.
- GR uses a combined `GRDIR`. Its first four little-endian words are section
  offsets: logic `0x0008`, picture `0x02e7`, view `0x05c6`, and sound
  `0x08c6`. The resulting section counts are 245 logic entries, 245 picture
  entries, 256 view entries, and 51 sound entries.
- The GR directory loader at image `0x44de` first formats a combined directory
  name using the runtime prefix and `"%sdir"`, then falls back to separate
  `logdir`, `picdir`, `viewdir`, and `snddir` files if the combined open
  fails.
- The v3 absent-entry helper at image `0x4599` rejects only exact
  `ff ff ff`. This differs from SQ2 v2's high-nibble `0xf` rejection.
- GR image `0x33c2` opens sixteen volume handles using `"%svol.%d"`. This
  explains observed local directory entries pointing at `GRVOL.9` through
  `GRVOL.12`.
- The v3 generic record reader at image `0x30d0` reads a 7-byte header:
  `12 34`, a metadata/volume byte, an expanded little-endian length, and a
  stored little-endian length.
- Metadata bit `0x80` selects the picture-nibble transform at image `0x9a5b`.
  Otherwise equal expanded/stored lengths are read directly, and unequal
  lengths use the dictionary decompressor at image `0x07f4`.
- The dictionary decompressor uses 9-bit initial codes, reset code `0x100`,
  end code `0x101`, and grows to 10 and 11 bits. The picture-nibble transform
  expands packed color/control nibbles after picture commands `0xf0` and
  `0xf2` back into ordinary byte operands.
- Added `tools/agi_resources.py` with split v2 and combined v3 container
  detection, v3 dictionary expansion, v3 picture-nibble expansion, and a small
  CLI summary/inspection mode.
- Added `tests/test_agi_resources.py`. The new focused tests passed.
- Extended `tools/disassemble_logic.py` so logic payload loading uses
  `tools/agi_resources.py`; v3 combined games select action table base
  `0x0440` and condition table base `0x0762`.
- The decoded GR logic census had no parse errors. The v3 action dispatcher
  accepts action slots through `0xb5`, but this Gold Rush data set uses action
  opcodes only through `0xa9`. The condition dispatcher compares predicate
  bytes with `0x26`; a later static comparison pass corrected this note by
  showing that only entries `0x00..0x12` are structured table records in the
  observed `AGIDATA.OVL`, while bytes above that overlap string/data.
- Focused regression checks passed: `tests/test_agi_resources.py`, plus
  `tests/test_logic_doc_coverage.py` and `tests/test_sound_resources.py` with
  `AGI_GAME_DIR=games/SQ2`.
- A full local unit-suite run with `AGI_GAME_DIR=games/SQ2` currently fails in
  older fixture builders because the private game files are read-only and
  copied fixtures try to overwrite files such as `LOGDIR` and `VOL.3` without
  changing destination permissions. This appears unrelated to the new GR
  resource parser and should be handled separately if full-suite green status
  is needed before the next commit.

## 2026-07-07: GR / SQ2 static opcode, object, view, and picture comparison

Context:

- The user asked for a source-only pass through every GR logic opcode compared
  with SQ2, plus the same style of comparison for object, view, and picture
  implementation code. Observable behavior checks were intentionally deferred.
- All evidence in this pass comes from local game directories, the local SQ2
  decrypted executable, local disassembly with `ndisasm`, and local parsing
  tools.

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n '1,220p' PROGRESS.md`
- `sed -n '1,260p' docs/src/clean_room_executable_notes.md`
- `tail -n 80 docs/src/progress_log.md`
- `sed -n '1,220p' docs/src/symbolic_labels.md`
- `ndisasm -b 16 -o 0x0000 -e 0x200 games/GR/AGI > build/gr-sq2-static/gr_agi_image.ndisasm`
- `ndisasm -b 16 -o 0x0000 -e 0x200 build/cleanroom/SQ2_AGI.decrypted.exe > build/gr-sq2-static/sq2_agi_image.ndisasm`
- `python3 -B tools/compare_gr_sq2_static.py --sq2-game-dir games/SQ2 --gr-game-dir games/GR --sq2-exe build/cleanroom/SQ2_AGI.decrypted.exe --gr-exe games/GR/AGI --output build/gr-sq2-static/opcode_static_report.md`
- `python3 -B tools/compare_gr_sq2_static.py --help`
- `python3 -B -m py_compile tools/compare_gr_sq2_static.py`
- `python3 -B -m py_compile tools/compare_gr_sq2_static.py tools/disassemble_logic.py`
- `AGI_GAME_DIR=games/GR python3 -B tools/disassemble_logic.py --stats`
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/disassemble_logic.py --stats`
- `mdbook build docs`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests`
- `python3 -B tools/compatibility_suite.py`
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py`
- `xxd -g 1 -s 0x0762 -l 192 games/GR/AGIDATA.OVL`
- Local one-off Python census using `tools.agi_resources` to read all present
  SQ2 and GR picture/view resources and count transform types.
- Focused `ndisasm`/`sed` reads over GR and SQ2 image ranges around action
  dispatch, condition dispatch, picture command dispatch, view selectors,
  object update lists, frame timers, motion helpers, and display refresh
  helpers.
- `xxd -g 1 -l 16 games/SQ2/OBJECT`
- `xxd -g 1 -l 16 games/GR/OBJECT`
- `xxd -g 1 -s 315 -l 16 games/SQ2/OBJECT`
- `xxd -g 1 -s 1798 -l 16 games/GR/OBJECT`

Generated local artifacts:

- `tools/compare_gr_sq2_static.py`: deterministic comparison helper requiring
  explicit SQ2 and GR game/executable paths.
- `build/gr-sq2-static/gr_agi_image.ndisasm`: full GR loaded-image
  disassembly.
- `build/gr-sq2-static/sq2_agi_image.ndisasm`: full SQ2 loaded-image
  disassembly.
- `build/gr-sq2-static/opcode_static_report.md`: generated static comparison
  report.

Documented result:

- Shared action opcode table entries `0x00..0xaf` have identical argument
  counts and operand metadata in SQ2 and GR.
- Normalized handler-entry snippets match for 159 shared action opcodes and
  differ for 17 shared actions: `0x12`, `0x6f`, `0x73`, `0x76`, `0x77`,
  `0x78`, `0x79`, `0x7c`, `0x7d`, `0x80`, `0x84`, `0x89`, `0x8a`, `0xa3`,
  `0xa4`, `0xa9`, and `0xad`.
- The changed shared action snippets cluster around room switching,
  input/text/window handling, save/restart/inventory UI paths, key-map
  capacity, and two GR state bytes. Important static observations:
  - GR action `0x79` raises the key-map loop limit from `0x27` to `0x31`.
  - GR actions `0xa3` and `0xa4` route to the generic no-op/return handler
    rather than setting/clearing SQ2's input-width word.
  - GR action `0xad` sets byte `[0x0405]` to `1`; GR-only action `0xb5` sets
    the same byte to `0`. SQ2 action `0xad` increments byte `[0x1530]`.
  - GR action `0x84` preserves object0 byte `+0x22` when it is already `4`;
    SQ2 clears that field unconditionally.
- GR-only action slots `0xb0..0xb5` are present in the v3 action table.
  `0xb0`, `0xb2`, `0xb3`, and `0xb4` route to the generic no-op/return
  handler after operand consumption. `0xb1` stores its one operand in word
  `[0x0403]`; local cross-references show later code tests `[0x0403]` before
  a menu/popup-like path. `0xb5` clears byte `[0x0405]`.
- Shared condition table entries `0x00..0x12` have identical parser contracts
  and no normalized handler-entry differences.
- GR condition dispatch code compares predicate bytes with `0x26`, but the
  bytes after the first 19 four-byte entries are not a confirmed handler table.
  Forced decoding of `AGIDATA.OVL:0x07ae..` yields punctuation/filename bytes
  such as `.,;:'!-`, `words.tok`, and `object`, followed by zeros. The
  disassembler now treats only `0x00..0x12` as the structured condition table
  for the observed GR input.
- The local GR logic census still has no parse errors after that conservative
  condition-table correction. Observed GR scripts use condition opcodes only
  through `0x0e`.
- Resource-reader implementation is the major known container difference:
  `code.resource.load_all_directories` and
  `code.resource.read_volume_payload_once` are different as expected because GR
  uses combined `GRDIR`, prefixed `GRVOL.N`, 7-byte headers, dictionary
  expansion, and picture-nibble expansion.
- View runtime slices match as relocated skeletons after the v3 resource
  reader produces an expanded payload: view load/cache, object-view binding,
  group table selection, frame selection, and view discard all compared cleanly.
- Picture runtime slices mostly match as relocated skeletons: load/cache,
  prepare/overlay/discard, command scan, all eleven picture command handlers
  `0xf0..0xfa`, coordinate reads, line drawing, pixel write, seed fill, and
  pattern plotting. Differences are display-mode refresh paths:
  `code.picture.decode_no_clear`, `code.display.fill_buffer_word`, and
  `code.display.full_refresh` omit SQ2's display-mode-2 overlay refresh branch
  in GR.
- Object runtime slices mostly match as relocated skeletons: update-list
  sorting/insertion/draw/refresh, collision test, control acceptance,
  dirty-rectangle update, placement, active/inactive list rebuild/flush/refresh,
  and membership toggles. GR packages rectangle save/restore/draw routines in
  the main executable image (`0x5b67`, `0x5ba6`, `0x5be3`) while SQ2 uses
  object-overlay entry points in `IBM_OBJS.OVL`.
- Static object/motion differences that still need semantic naming:
  - GR frame-timer update adds an extra helper-gated branch before using the
    four-plus-group direction table.
  - GR motion dispatch accepts one additional object mode selector
    (`cmp ax,0x3` instead of SQ2's `cmp ax,0x2`) before falling through to the
    same boundary-check tail.
  - Straight-line `ndisasm` differences inside
    `code.object.advance_frame_by_mode` and
    `code.motion.rectangle_boundary_check` are embedded jump-table bytes, not
    enough by themselves to claim behavioral differences; the surrounding
    branch bodies were manually inspected as relocated skeletons.
- Local resource data census:
  - SQ2 pictures: 75 directory-present entries, 74 decoded direct payloads, one
    bad v2 header at picture 147.
  - SQ2 views: 203 present direct payloads.
  - GR pictures: 186 present payloads, all using the picture-nibble transform.
  - GR views: 247 present payloads, all using the dictionary transform.
- `OBJECT` file bytes differ in length and content (`games/SQ2/OBJECT` length
  331, `games/GR/OBJECT` length 1814), but the interpreter-side object-table
  initialization skeleton is the same: it reads/decrypts the file, computes
  inventory/object table roots, uses a 43-byte object-record stride, clears and
  initializes the object table, and seeds the same prompt/direction defaults
  after address relocation.
- Verification: `mdbook build docs` passed. `AGI_GAME_DIR=games/SQ2 python3 -B
  -m unittest discover -s tests` passed 251 tests. Running
  `python3 -B tools/compatibility_suite.py` without `AGI_GAME_DIR` failed at
  import time because the project now requires an explicit game directory;
  rerunning as `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py`
  passed the same 251 tests and mdBook build.

## 2026-07-07: Version ledger and read-only fixture copy fix

Context:

- The user asked for a `Versions` documentation chapter to track differences
  between observed interpreter versions.
- The user also clarified that generated test/original-engine fixtures should
  never modify private files under `games/`; fixture builders should copy the
  selected game into `build/` and modify that generated copy.

Commands run from `/Users/peter/ai/agi/reverse`:

- `rg -n "fixture|LOGDIR|VOL\\.3|games/|AGI_GAME_DIR|copytree|copy2|chmod|write_bytes|open\\(" tests tools docs/src PROGRESS.md AGENTS.md`
- `sed -n '1,260p' tools/qemu_fixture.py`
- `sed -n '620,980p' tools/qemu_fixture.py`
- `sed -n '1,520p' tests/test_qemu_fixture.py`
- `rg -n "shutil\\.copy|copytree|copy2|LOGDIR\\)\\.write|VOL\\.3\\)\\.write|PICDIR\\)\\.write|VIEWDIR\\)\\.write|AGIDATA\\.OVL\\)\\.write|destination / \\\"LOGDIR\\\"|fixture / \\\"LOGDIR\\\"|games/" tools tests`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests/test_qemu_fixture.py`
- `mdbook build docs`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests`

Documented result:

- Added `docs/src/versions.md` and linked it from `docs/src/SUMMARY.md`.
  The chapter currently records SQ2 / AGI 2.936 and Gold Rush / AGI 3.002.149
  differences: executable form, resource container, compression/transform
  paths, dispatch-table range, and generated-fixture readiness.
- Updated `tools/qemu_fixture.py` so generated fixture copies are writable even
  when the selected game input is read-only. The shared copy primitive now
  cleans generated destinations, preserves `.ppm` capture files, copies source
  files, and adds owner read/write permission on the copy before patching.
- Added a fixture-destination guard: paths under repository `games/` are
  rejected before any generated directory is created or patched. Destinations
  that are the selected game directory, a child of it, or a parent of it are
  rejected for the same reason.
- Added focused tests proving that a read-only copied `LOGDIR` can be patched
  in the fixture copy, that a destination under `games/` is rejected, and that
  a destination parent of the selected game is rejected.
- Updated `AGENTS.md` to state the immutable-`games/` rule explicitly.
- Verification passed: `mdbook build docs`, the focused
  `tests/test_qemu_fixture.py` slice, and the full local unit suite with
  `AGI_GAME_DIR=games/SQ2` (`251` tests).

## 2026-07-07: Gold Rush v3 extra action opcode source pass

Context:

- The user asked to figure out the extra opcodes. This pass focuses on the
  Gold Rush / AGI v3 action slots beyond the SQ2 action table, `0xb0..0xb5`,
  using local disassembly and local decoded resources.
- No external AGI documentation or source was consulted.
- No targeted QEMU fixture was run for this pass. The current generated
  original-engine fixture writers are still v2/SQ2-container-oriented, while
  the relevant GR effects were directly visible in the opcode handlers and
  their local consumers. Observable v3 fixture tests remain useful later.

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `rg -n "0xb0|0xb1|0xb2|0xb3|0xb4|0xb5|0x0403|0x0405|GR-only|extra action|extra opcodes|v3-only" PROGRESS.md docs/src tools tests`
- `sed -n '1,260p' tools/compare_gr_sq2_static.py`
- `sed -n '1,240p' tools/agi_resources.py`
- `rg -n "0403|0405|970B|9724|63A8|63B0|000097|000063A|000064" build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '11140,11320p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '17280,17480p' build/gr-sq2-static/gr_agi_image.ndisasm`
- Local Python using `tools.compare_gr_sq2_static.load_table` to print GR
  action-table entries `0xb0..0xb5`.
- `sed -n '6120,6260p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '17030,17240p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `rg -n "1b67|1b71|1b73|1b75|1b79|1b77|1b7b|1b7d|1b7f|1b81|1b83|1b85|1b87|1b88|03f9|03fd|0403|0405" build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '16680,17040p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '9240,9320p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '1,240p' tests/test_logic_doc_coverage.py`
- `rg -n "0x403|0x405|\\[0x403\\]|\\[0x405\\]" build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '11180,11340p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '17030,17230p' build/gr-sq2-static/gr_agi_image.ndisasm`

Observed GR action-table entries:

| Opcode | Handler | Args | Metadata | Source-backed interpretation |
| ---: | ---: | ---: | ---: | --- |
| `0xb0` | `0x5286` | 0 | `0x00` | Reserved/no-op slot. Handler `0x5286` only returns the bytecode pointer passed to it. |
| `0xb1` | `0x970b` | 1 | `0x00` | Reads one immediate byte, zero-extends it, and stores it in word `[0x0403]`. |
| `0xb2` | `0x5286` | 0 | `0x00` | Reserved/no-op slot. |
| `0xb3` | `0x5286` | 4 | `0x00` | Reserved/no-op slot after four table-declared fixed operands. |
| `0xb4` | `0x5286` | 2 | `0xc0` | Reserved/no-op slot after two table-declared variable operands. |
| `0xb5` | `0x63b0` | 0 | `0x00` | Stores zero in byte `[0x0405]`. |

Detailed observations:

- Generic handler `0x5286` saves/restores registers, loads `AX` from
  `[bp+0x8]`, and returns. It has no state writes and no operand reads.
- Handler `0x970b` (`0xb1`) reads the byte at the incoming bytecode pointer,
  increments the pointer, zero-extends the byte, stores the word at `[0x0403]`,
  and returns the incremented pointer.
- GR menu interaction routine `0x9724` begins with
  `cmp word [0x403],0` and returns without drawing/waiting if the word is zero.
  The same routine otherwise draws the menu structure rooted at `[0x1b71]`,
  waits for input, navigates enabled menu nodes, and enqueues type-3 item
  events through `0x46f4`.
- Existing shared menu actions build and request the menu separately:
  `0x9c` builds menu headings in the linked structure rooted at `[0x1b71]`,
  `0x9d` adds menu items, `0x9e` finalizes the structure, `0x9f`/`0xa0`
  enable/disable items, and `0xa1` sets request word `[0x1b67]` when flag
  `0x0e` is set. The main cycle path calls `0x9724` only when `[0x1b67]` is
  nonzero, so `0xb1` is a separate interaction gate rather than a menu-build
  opcode.
- GR shared action `0xad` at `0x63a8` stores one in byte `[0x0405]`. GR-only
  action `0xb5` at `0x63b0` stores zero in the same byte.
- The GR keyboard interrupt hook at `0x63b8` tests `[0x0405]` on selected
  tracked-key release paths. When the byte is nonzero, it calls event enqueue
  helper `0x46f4` with type `2` and value `0`.

Documentation/tooling updates from this pass:

- Added v3-specific action names in `tools/disassemble_logic.py` without
  changing the SQ2 `ACTION_NAMES` catalog: `set_menu_interaction_gate` for
  `0xb1`, `clear_key_release_event_gate` for `0xb5`, and reserved/no-op names
  for `0xb0`, `0xb2`, `0xb3`, and `0xb4`.
- Updated `tools/compare_gr_sq2_static.py` notes so the generated static report
  records the local consumers of `[0x0403]` and `[0x0405]`.
- Updated `PROGRESS.md`, `docs/src/versions.md`,
  `docs/src/logic_bytecode.md`, and `docs/src/symbolic_labels.md` with the
  v3-only opcode interpretations and new symbolic data labels
  `data.menu.interaction_gate_0403` and
  `data.input.key_release_enqueue_gate_0405`.

Verification after the documentation/tooling updates:

- Regenerated `build/gr-sq2-static/opcode_static_report.md` with
  `python3 -B tools/compare_gr_sq2_static.py --sq2-game-dir games/SQ2 --gr-game-dir games/GR --sq2-exe build/cleanroom/SQ2_AGI.decrypted.exe --gr-exe games/GR/AGI --output build/gr-sq2-static/opcode_static_report.md`.
- `AGI_GAME_DIR=games/GR python3 -B tools/disassemble_logic.py --stats`
  parsed the local GR logic resources with no errors.
- `python3 -B -m py_compile tools/disassemble_logic.py tools/compare_gr_sq2_static.py`
  passed.
- `mdbook build docs` passed.
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests` passed
  251 tests.
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py` passed
  the same 251 tests and mdBook build.
- `git diff --check` passed.

## 2026-07-09: Gold Rush / SQ2 shared action delta source pass

Context:

- The user asked to update `PROGRESS.md` with the planned GR/SQ2 comparison
  items, then continue.
- This pass used local disassembly first. No external AGI documentation/source
  and no QEMU confirmation were used.
- Inputs were the already generated `build/gr-sq2-static/*_agi_image.ndisasm`
  files plus exact-offset disassembly from local executable bytes where linear
  `ndisasm` swallowed handler-entry bytes as neighboring inline data.

Commands run from `/Users/peter/ai/agi/reverse`:

- `git status --short`
- `sed -n '1,260p' PROGRESS.md`
- `sed -n '1,260p' docs/src/versions.md`
- `sed -n '1,260p' docs/src/symbolic_labels.md`
- `sed -n '1,220p' docs/src/progress_log.md`
- `sed -n '1,260p' tools/compare_gr_sq2_static.py`
- `tail -n 180 docs/src/clean_room_executable_notes.md`
- `rg -n "0x6f|0x73|0x76|0x77|0x78|0x79|0x7c|0x7d|0x80|0x84|0x89|0x8a|0xa3|0xa4|0xa9|0xad|0xb1|0xb5|Gold Rush|GR / SQ2|v3" docs/src/logic_bytecode.md docs/src/versions.md docs/src/clean_room_executable_notes.md docs/src/symbolic_labels.md PROGRESS.md`
- Local Python using `tools.compare_gr_sq2_static.load_table` to print the
  SQ2/GR action-table entries for the changed shared action set.
- `sed -n '8548,8628p' build/gr-sq2-static/sq2_agi_image.ndisasm`
- `sed -n '8768,8855p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '10900,11040p' build/gr-sq2-static/sq2_agi_image.ndisasm`
- `sed -n '11272,11445p' build/gr-sq2-static/gr_agi_image.ndisasm`
- Exact-offset local Python disassembly for handlers `0x175c`, `0x19d4`,
  `0x31d8`, `0x351e`, `0x2753`, `0x29e5`, `0x2472`, `0x26e0`, `0x7041`,
  and `0x73b9`.
- `AGI_GAME_DIR=games/GR python3 -B tools/disassemble_logic.py --limit 256 | rg "switch_room_like|0x12|\\broom"`
- Exact-offset local Python disassembly for GR helpers `0x0062`, `0x07bc`,
  `0x169b`, `0x11b3`, `0x341c`, `0x9648`, `0x3b00`, and `0x3ab0`.
- `rg -n "0dc1|DC1|\\[0xdc1\\]|03f9|0dc3|0dc5" build/gr-sq2-static/gr_agi_image.ndisasm docs/src/symbolic_labels.md docs/src/clean_room_executable_notes.md`
- Exact-offset local Python disassembly for SQ2/GR
  `code.object.frame_timer_update`, `code.motion.pre_mode_and_boundary_update`,
  `code.motion.dispatch_mode_step`, and
  `code.motion.rectangle_boundary_check`.
- Local Python byte dump of the SQ2 and GR motion-mode dispatch tables at image
  offsets `0x06ad` and `0x06bd`.

Input/text cluster observations:

- GR action-table entries match SQ2 parser contracts for actions `0x6f`,
  `0x73`, `0x76`, `0x77`, `0x78`, `0x89`, `0x8a`, `0xa3`, `0xa4`, and
  `0xa9`, but the handler bodies remove SQ2's display-mode-2/input-width
  branches.
- SQ2 `0x6f` at image `0x78f0` stores input-line bounds and computes display
  offset `[0x1379]` with an alternate display-mode-2 branch. GR `0x6f` at
  image `0x7c24` stores relocated globals and computes display offset
  `[0x11b1] = arg0 << 3` unconditionally.
- SQ2 string/number prompt actions `0x73` and `0x76` have alternate paths for
  display mode `[0x1130] == 2` when input-width word `[0x0d0f] == 0`. GR
  prompt handlers `0x0e92` and `0x756b` use the normal prompt/editor path only.
- SQ2 `0x77`, `0x78`, `0x89`, and `0x8a` test display mode and input-width
  state before clearing/redrawing/refreshing/erasing. GR handlers `0x3b0c`,
  `0x3b2e`, `0x3a48`, and `0x3a29` use the normal relocated input buffers and
  visible row helpers without those special branches.
- SQ2 actions `0xa3` and `0xa4` set/clear word `[0x0d0f]`; GR maps both table
  entries to the generic no-op/return handler `0x5286`.
- SQ2 action `0xa9` at `0x1f2b` restores active saved-window state and clears
  both `[0x0d0f]` and `[0x0d1d]`. GR action `0xa9` at `0x21a2` restores the
  relocated active saved-window rectangle and clears only active word
  `[0x0b24]`.

Event/key/menu observations:

- SQ2 action `0x79` at image `0x4c3d` reads a two-byte key word and one mapped
  value, then scans up to `0x27` four-byte slots rooted at `[0x0145]` for the
  first empty key word. GR action `0x79` at `0x4e98` is the same shape but
  scans up to `0x31` slots.
- SQ2 action `0xad` at `0x602f` increments byte `[0x1530]`. The SQ2 keyboard
  IRQ hook tests `[0x1530] != 0` before enqueueing `(type=2, value=0)` on
  selected tracked-key release paths.
- GR action `0xad` at `0x63a8` sets byte `[0x0405] = 1`; GR-only action
  `0xb5` at `0x63b0` clears the same byte. GR keyboard IRQ hook `0x63b8`
  tests `[0x0405]` before the selected key-release enqueue.
- GR-only action `0xb1` at `0x970b` stores its immediate operand in word
  `[0x0403]`. GR menu interaction routine `0x9724` returns immediately while
  `[0x0403] == 0`, so this is a separate interaction gate after menu request
  state has been set.

Room/inventory/save/restart/object-state observations:

- SQ2 action `0x12` at image `0x175c` reads the immediate room byte and calls
  room-switch helper `0x1792`. GR action `0x12` at `0x19d4` calls helper
  `0x0062` first: bytes below `0x7e` or above `0x80` pass through unchanged,
  while bytes `0x7e`, `0x7f`, and `0x80` return `0x49`.
- Decoded local GR scripts contain `switch_room_like(#126)`,
  `switch_room_like(#127)`, and `switch_room_like(#128)`, so the GR remap is
  live behavior for this interpreter/game pair, not dead code.
- SQ2 action `0x7c` at `0x31d8` enters the carried-item selector through the
  established text/input save-restore path. GR action `0x7c` at `0x351e`
  follows the relocated skeleton but clears word `[0x0dc1]` before return. The
  selector helper sets `[0x0dc1] = 1` while handling the flag-13 interactive
  input path, so the current label is a temporary selector/input gate.
- SQ2 save action `0x7d` at `0x2753` writes the known five-block envelope.
  GR save action `0x7d` at `0x29e5` writes the relocated five-block envelope
  but calls helper `0x07bc` over the object/inventory chunk before and after
  the save writes. Helper `0x07bc` XORs a caller-supplied byte range with
  repeating key bytes at data address `DS:0x072c` until the key byte is zero.
- SQ2 restart action `0x80` at `0x2472` redraws the prompt marker at the end of
  the accepted path. GR restart action `0x80` at `0x26e0` first records the
  prompt-marker visible word through helper `0x3b00`, erases the marker, and
  redraws it when restart was accepted or, after a canceled restart, only if
  the marker had been visible before entry.
- SQ2 action `0x84` at `0x7041` sets `[0x0139] = 1` and clears object 0 byte
  `+0x22` unconditionally. GR action `0x84` at `0x73b9` sets `[0x0139] = 1`
  but skips the clear when object 0 byte `+0x22` is already `4`.

Object/motion observations:

- SQ2 `code.object.frame_timer_update` at `0x0563` uses the direction-to-loop
  table for object views with group count byte `+0x0b >= 4` when bit `0x2000`
  is clear. GR `0x055c` keeps the two/three-group table path, but the
  four-plus path is split: exactly four groups uses the direction table without
  the new flag gate, and more than four groups uses the direction table only
  when flag `0x14` is set. A later targeted QEMU probe in these notes corrected
  the earlier no-auto-select shorthand for the exactly-four case.
- SQ2 `code.motion.dispatch_mode_step` at `0x067a` accepts modes `1..3` after
  decrementing object byte `+0x22`. GR `0x068a` accepts modes `1..4`. The GR
  jump table at `0x06bd` maps mode `1` to random motion, mode `2` to
  approach-first-object, and both modes `3` and `4` to the target-direction
  helper.
- The surrounding GR pre-mode/boundary and rectangle-boundary helpers remain
  relocated skeletons of the SQ2 logic after accounting for embedded jump-table
  bytes in linear disassembly.

Documentation/tooling updates from this pass:

- Updated `PROGRESS.md` with the requested ordered comparison queue, then
  replaced the queue with source-pass status and the remaining v3 fixture work.
- Refined `tools/compare_gr_sq2_static.py` changed-action notes so regenerated
  reports describe the now-source-backed deltas.
- Updated `docs/src/versions.md`, `docs/src/logic_bytecode.md`,
  `docs/src/runtime_model.md`, and `docs/src/symbolic_labels.md` with the
  source-backed GR/SQ2 differences and new GR address associations.

## v3 Direct Logic Fixture Writer

Goal: turn the source-backed Gold Rush / AGI v3 deltas into testable behavior
without modifying private inputs under `games/`.

Commands and local reads:

- `sed -n '1,1240p' tools/qemu_fixture.py`
- `sed -n '1,760p' tools/agi_resources.py`
- `sed -n '1,620p' tests/test_qemu_fixture.py`
- `sed -n '1,90p' tools/project_paths.py`
- `rg -n "copy_game_tree|build_.*fixture|patch_dir_entry|SQ2|AGI_GAME_DIR|--game-dir|detect_layout|v3|GRDIR|GRVOL" tools tests docs/src PROGRESS.md`
- Local Python `detect_layout(games/GR)` / `read_directory_entries(...)`
  inspection.
- `AGI_GAME_DIR=games/GR python3 -B tools/disassemble_logic.py --stats`
- Local Python count of GR combined-directory slots and present entries.
- `python3 -B -m py_compile tools/qemu_fixture.py tools/agi_resources.py`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests/test_qemu_fixture.py tests/test_agi_resources.py`

Observations:

- `tools/qemu_fixture.py` previously imported `SQ2` from
  `tools/disassemble_logic.py`, which made fixture construction depend on the
  selected game at module import time and hid an SQ2-oriented source path inside
  copy helpers.
- The copy path now accepts `game_dir=...` explicitly or uses
  `AGI_GAME_DIR` through `project_paths.game_dir()` only when the caller omits
  a source. Fixture destinations are still rejected under `games/` and when
  they would overwrite the selected source game.
- Existing v2 fixture builders retain the split-directory `VOL.3` packing
  behavior. The compatibility alias `copy_sq2_tree()` remains for older probes,
  but it no longer imports or references a global SQ2 path.
- Added `v3_volume_record(...)` for the observed direct/uncompressed v3 header:
  `12 34 metadata expanded_len stored_len payload`. The writer uses equal
  expanded and stored lengths and keeps the metadata low nibble aligned with the
  patched directory volume.
- Added `patch_combined_dir_entry(...)` for v3 combined directories. It uses
  the section offsets and section ends recovered by `detect_layout()` and
  patches the selected resource entry at `section_offset + resource_no * 3`.
- Added `build_v3_logic_fixture(...)`. It copies the selected v3 game into the
  generated destination, detects the copied combined layout, appends a direct
  record to the existing prefixed volume for the selected logic resource, and
  patches that logic entry in the combined directory.
- Added `python3 -B tools/qemu_fixture.py v3-logic payload.bin --game-dir ...`
  as a reusable CLI wrapper for the direct logic fixture path.
- The test fixture uses a tiny synthetic `GRDIR`/`GRVOL.1` layout, not private
  game files, to prove the direct-record append and directory patch can be read
  back through `read_volume_record(...)`.
- The current local GR combined-directory counts are: logic `245` slots /
  `182` present, picture `245` slots / `186` present, view `256` slots /
  `247` present, and sound `51` slots / `44` present.

Status:

- Basic v3 logic fixture writing is implemented and covered by focused unit
  tests.
- Generated v3 picture/view packing is intentionally still absent. Add it only
  when a targeted behavior probe needs generated picture or view payloads
  rather than original game resources.
- Verification after the CLI/docs update:
  `python3 -B -m py_compile tools/qemu_fixture.py tools/agi_resources.py`,
  `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests`
  (`254` tests), `mdbook build docs`,
  `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py`, and
  `git diff --check` all passed.

## Gold Rush v3 Room-Remap Behavior Probe

Goal: convert the source-backed GR action `0x12` room-target remap into an
original-engine compatibility check.

Commands and local reads:

- `AGI_GAME_DIR=games/GR python3 -B tools/disassemble_logic.py 73`
- `AGI_GAME_DIR=games/GR python3 -B tools/disassemble_logic.py 0`
- `python3 -B tools/setup_freedos_image.py --force`
- `python3 -B tools/gr_v3_behavior_probe.py --game-dir games/GR --output build/gr-v3-behavior/room_remap_build_001.json`
- `python3 -B tools/gr_v3_behavior_probe.py --game-dir games/GR --run-qemu --output build/gr-v3-behavior/room_remap_qemu_001.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/gr_v3_behavior_probe.py --probe direct-draw --game-dir games/GR --picture 1 --fixture-root build/gr-v3-behavior/direct-draw-fixtures --output build/gr-v3-behavior/direct_draw_pic001_qemu_001.json --run-qemu --boot-wait 5 --draw-wait 8`
- `python3 -B tools/gr_v3_behavior_probe.py --game-dir games/GR --picture 1 --run-qemu --output build/gr-v3-behavior/room_remap_dispatch_qemu_pic001_001.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/gr_v3_behavior_probe.py --game-dir games/GR --picture 1 --run-qemu --output build/gr-v3-behavior/room_remap_all_qemu_pic001_001.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/inspect_ppm.py` on the generated QEMU captures.

Probe construction:

- A direct draw sanity fixture patches GR logic `0` to `picture_logic_payload(1)`.
  QEMU capture `build/gr-v3-behavior/direct-draw-fixtures/direct_draw/qemu_capture.ppm`
  was nonblank (`14` unique colors), proving that direct v3 logic replacement
  executes under the original GR interpreter.
- The first room-remap fixture pair only patched logic `0` to switch rooms and
  logic `0x49` to draw a marker picture. It produced equal but all-black
  captures. This was not accepted as evidence.
- The failure exposed an important harness requirement: replacing logic `0`
  removes the original global dispatch tail. GR logic `0` normally reaches
  `call_logic_var(v0)` near bytecode offset `0x0ca0`, so a custom logic `0`
  that switches rooms must also continue dispatching the current room.
- The corrected `switch_room_payload()` fires the switch once behind guard
  variable `v250`, then executes `call_logic_var(v0)` and `end` on each cycle.
  Logic `0x49` in both fixtures is patched to draw picture `1`.

QEMU result:

- Report:
  `build/gr-v3-behavior/room_remap_dispatch_qemu_pic001_001.json`.
- Direct target fixture: logic `0` uses `switch_room_like(#0x49)`.
- Alias target fixtures: logic `0` uses `switch_room_like(#0x7e)`,
  `switch_room_like(#0x7f)`, or `switch_room_like(#0x80)`.
- All fixtures patch logic `0x49` to the same picture-display payload.
- The expanded QEMU report is
  `build/gr-v3-behavior/room_remap_all_qemu_pic001_001.json`; all alias
  captures match direct target `0x49`.
- The four QEMU captures are byte-identical:
  `45518c409f738a1fb2f4233db202f64d2e0e94011a9559e8ace0d952362814ab`.
- `inspect_ppm` reports all four captures as `640x400`, `14` unique colors,
  and non-background bounding box `(0, 0, 639, 399)`.

Conclusion:

- The source-backed GR helper `code.room.remap_reserved_room_target` is now
  dynamically validated for `0x7e`, `0x7f`, and `0x80` all mapping to `0x49`.
- Final verification for this pass:
  `python3 -B -m py_compile tools/gr_v3_behavior_probe.py tools/qemu_fixture.py tools/agi_resources.py`,
  `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests`
  (`257` tests), `mdbook build docs`,
  `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py`, and
  `git diff --check` all passed.

## Gold Rush v3 Key-Map Capacity Behavior Probe

Goal: convert the source-backed GR action `0x79` key-map capacity delta into an
observable original-engine check.

Commands and local reads:

- `rg -n "00004E9[0-9A-F]|00004EA[0-9A-F]|00004EB[0-9A-F]|00004EC[0-9A-F]|00004ED[0-9A-F]|00004EE[0-9A-F]|00004EF[0-9A-F]" build/gr-sq2-static/gr_agi_image.ndisasm`
- `rg -n "000063A[0-9A-F]|000063B[0-9A-F]|000063C[0-9A-F]|000063D[0-9A-F]|000063E[0-9A-F]" build/gr-sq2-static/gr_agi_image.ndisasm`
- `rg -n "0000970[0-9A-F]|0000971[0-9A-F]|0000972[0-9A-F]|0000973[0-9A-F]|0000974[0-9A-F]|0000975[0-9A-F]|0000976[0-9A-F]" build/gr-sq2-static/gr_agi_image.ndisasm`
- `python3 -B tools/gr_v3_behavior_probe.py --probe key-map-capacity --game-dir games/GR --picture 1 --fixture-root build/gr-v3-behavior/key-map-capacity-fixtures --dos-prefix GRK --run-qemu --output build/gr-v3-behavior/key_map_capacity_qemu_pic001_002.json --boot-wait 5 --draw-wait 8`
- `python3 -B tools/inspect_ppm.py` on each generated capture.

Source observations:

- GR action `0x79` at image `0x4e98` reads two operand bytes into a little-endian
  key/event word, reads one mapped status value, then scans slots rooted at
  `[0x0145]`.
- The GR loop compares `DI` with `0x31`, so it can fill slots `0..48`.
  The SQ2 source-backed comparison showed the same handler shape but a loop
  bound of `0x27`, so SQ2 fills slots `0..38`.
- GR action `0xad` at image `0x63a8` stores byte `[0x0405] = 1`, GR-only action
  `0xb5` at image `0x63b0` stores `[0x0405] = 0`, and the GR keyboard IRQ hook
  at `0x63b8` tests `[0x0405]` before enqueueing a type-2 zero event on the
  selected scan-code release path.
- GR-only action `0xb1` at image `0x970b` stores its immediate operand into word
  `[0x0403]`; `code.menu.interact` at `0x9724` returns immediately while that
  word is zero.

Probe construction:

- The new `key_map_capacity_payload()` emits 48 dummy `0x79` mappings, then
  emits `0x79('x', 0, 7)` as the 49th mapping. The generated payload has
  `49` occurrences of opcode `0x79`, and the target mapping appears after
  `48` earlier mapping opcodes.
- The positive fixture patches copied GR logic `0` with that payload, sends
  typed key `x` through the QEMU monitor, and draws original GR picture `1`
  only when status byte `7` is observed.
- The direct fixture patches logic `0` to draw picture `1` immediately.
- The no-key control uses the same slot-48 mapping payload but sends no key.

QEMU result:

- Report:
  `build/gr-v3-behavior/key_map_capacity_qemu_pic001_002.json`.
- Expected matches: `slot_48_key_map` should match `direct_picture`;
  `slot_48_no_key` should not.
- The report matches those expectations exactly.
- Direct and keyed captures are byte-identical PPM files with SHA-256
  `45518c409f738a1fb2f4233db202f64d2e0e94011a9559e8ace0d952362814ab`.
- `inspect_ppm` reports direct and keyed captures as `640x400`, `14` unique
  colors, and non-background bounding box `(0, 0, 639, 399)`.
- The no-key capture has one unique color and no non-background bounding box.

Conclusion:

- The source-backed GR key-map loop bound of `0x31` is now dynamically validated
  for the final slot, showing that a mapping beyond SQ2's `0x27` slot count is
  observable through the original GR interpreter's event/status path.
- The `[0x0405]` key-release gate and `[0x0403]` menu-interaction gate remain
  source-backed; add raw scan-code/menu timing probes only if the final spec
  needs observable confirmation for those gate paths.
- Final verification for this pass:
  `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests`
  (`259` tests), `mdbook build docs`,
  `python3 -B -m py_compile tools/gr_v3_behavior_probe.py tools/qemu_fixture.py tools/agi_resources.py`,
  `git diff --check`, and
  `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py` all passed.

## Gold Rush v3 Save Object/Inventory XOR Model

Goal: turn the source-backed GR save transform into implementation-ready helper
code and tests.

Commands and local reads:

- `sed -n '1,260p' tools/save_roundtrip_probe.py`
- `sed -n '1,240p' tools/agi_save.py`
- `python3 -B tools/disassemble_logic.py --game-dir games/GR --limit 256 | rg "verify_game_signature|save_game_state|restore_game_state|copy_save_description|0x8f|0x7d|0x7e|0xaa"`
- Exact-offset local Python/`ndisasm` reads for GR image offsets `0x29e5`,
  `0x2aba`, `0x2b5b`, `0x2b7c`, `0x07bc`, and `0x2792`.
- Local Python byte read of the sequence starting at numeric image offset
  `0x072c`; this was later recognized as a segment-confusion error, because the
  helper uses `DI = 0x072c` as a data-segment address.
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests/test_save_resources.py`
- `python3 -B -m py_compile tools/agi_save.py`

Source observations:

- GR save action `0x7d` at image `0x29e5` begins by computing
  `[0x07d6] + [0x07da]`, then calls helper `0x07bc(start=[0x07d6],
  end=[0x07d6]+[0x07da])`.
- The same action calls `0x07bc` over the same range again at `0x2b61` before
  returning, after the selector/file I/O cleanup path.
- The write sequence calls length-prefixed writer `0x2b7c` for five blocks. The
  third call writes start `[0x07d6]` with length `[0x07da]`, so the XORed range
  is exactly the third saved state block.
- Helper `0x07bc` initializes `DI = 0x072c`, XORs each byte in the caller range
  with byte `[DI]`, increments both pointers, and when byte `[DI]` is zero it
  resets `DI` to `0x072c`.
- Rechecking the addressing against `games/GR/AGIDATA.OVL` shows that
  data-segment address `0x072c` contains the zero-terminated ASCII text
  `Avis Durgan`. The earlier 59-byte byte sequence came from reading main-code
  bytes at the same numeric offset and is not the save transform key.

Implementation/test updates:

- Added `GR_V3_OBJECT_INVENTORY_XOR_KEY`,
  `xor_with_repeating_key(...)`, and
  `gr_v3_object_inventory_save_xor(...)` to `tools/agi_save.py`.
- Added tests proving the GR transform uses the exact `Avis Durgan` key, wraps
  after byte 10, matches the original-engine save prefix known vector, round
  trips, and rejects an empty generic XOR key.

Conclusion:

- The GR v3 save transform is now source-backed and executable in the local
  save helper model. The current model describes the on-disk third block as the
  `Avis Durgan` XOR-transformed form of the runtime object/inventory block,
  with the second in-memory pass restoring runtime bytes before action return.
- A later QEMU save-file extraction probe promoted the source-backed transform
  to original-engine evidence; see the next section. The promoted fixture uses
  a blank save prefix and does not resolve the GR verifier/save-prefix path.
- Final verification for this pass:
  `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests`
  (`262` tests), `mdbook build docs`,
  `python3 -B -m py_compile tools/agi_save.py tools/gr_v3_behavior_probe.py tools/qemu_fixture.py tools/agi_resources.py`,
  `git diff --check`, and
  `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py` all passed.

## Gold Rush v3 Save Extraction Probe

Goal: confirm the source-mapped GR save XOR transform against a save file
written by the original interpreter.

Commands and local reads:

- `sed -n` reads of `PROGRESS.md`, `tools/gr_v3_behavior_probe.py`,
  `tools/save_roundtrip_probe.py`, `tools/qemu_fixture.py`,
  `tools/agi_save.py`, and the relevant tests.
- Initial local Python parsing used the wrong message offset base and led to
  the provisional, later-corrected hypothesis that GR message text might be
  plain in resource bytes. A follow-up pass below corrected this: GR logic
  message text is encrypted in the same observed message-text region.
- `strings -a -t x games/GR/AGIDATA.OVL` and `xxd -s 0x0700 -l 0x260 -g 1
  games/GR/AGIDATA.OVL` confirmed the same message XOR key text exists in GR
  data at offset `0x072c`, while GR logic message resources observed in this
  pass are already readable.
- `ndisasm` reads around GR image offsets `0x108c`, `0x245e`, `0x5035`, and
  `0x5ede`, plus byte reads around file offset `0x60d7`, confirmed the local
  `0x8f` verifier/copy shape and embedded verifier string bytes.
- Local script scan found GR's original `0x8f` use in logic `101` at bytecode
  offset `0x0004`, with message number `3`. The raw encrypted bytes for that
  message are `35 35 61`; after decrypting from the message text-region start,
  the message is `GR\0`.
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests.test_gr_v3_behavior_probe tests.test_qemu_fixture`
- `python3 -B -m py_compile tools/gr_v3_behavior_probe.py tools/qemu_fixture.py tests/test_gr_v3_behavior_probe.py tests/test_qemu_fixture.py`
- Initial exploratory QEMU run with a synthetic `0x8f("GR")` fixture exited
  before saving; `mdir` found no save file, and the capture showed the later
  typed description at DOS. This result was not promoted as save behavior.
- Promoted QEMU run:

```bash
python3 -B tools/gr_v3_behavior_probe.py --probe save-xor-extract --game-dir games/GR --fixture-root build/gr-v3-behavior/save-xor-fixtures --dos-prefix GRS --run-qemu --output build/gr-v3-behavior/save_xor_extract_qemu_001.json --snapshot-raw build/gr-v3-behavior/snapshot/save_xor_extract.raw --snapshot-qcow build/gr-v3-behavior/snapshot/save_xor_extract.qcow2 --post-run-raw build/gr-v3-behavior/snapshot/save_xor_extract_after.raw --save-output build/gr-v3-behavior/SG_001.1 --boot-wait 5 --draw-wait 8 --path-prompt-wait 2 --slot-wait 1 --description-wait 1 --confirmation-wait 1 --key-delay 0.08
```

Implementation/test updates:

- `tools/qemu_fixture.py` now lets generated logic resources opt out of
  SQ2-style message text encryption with `encrypt_messages=False`; the default
  encrypted behavior remains correct for observed SQ2 and GR logic resources.
- `tools/gr_v3_behavior_probe.py` now has `--probe save-xor-extract`. The
  promoted fixture omits `0x8f verify_game_signature`, so it writes a
  blank-prefix `SG.1` save and keeps the test focused on action `0x7d`.
- `tests/test_qemu_fixture.py` covers encrypted-default and plain-message
  logic-resource construction.
- `tests/test_gr_v3_behavior_probe.py` covers the GR save extraction payload,
  the optional verifier-message form, and stale save removal in copied
  fixtures.
- `tools/compatibility_suite.py` now has an opt-in `qemu-v3` layer containing
  the GR save-XOR extraction probe; it is intentionally separate from the
  SQ2-oriented smoke/broad layers because it depends on private `games/GR`.

QEMU result:

- Report: `build/gr-v3-behavior/save_xor_extract_qemu_001.json`.
- Suite-level report: `build/compatibility-suite/qemu_v3_save_001.json`, whose
  named `gr_save_xor_extract_qemu` command returned zero and wrote
  `build/gr-v3-behavior/save_xor_extract_suite.json`.
- Extracted save: `build/gr-v3-behavior/SG_001.1`.
- Description: `codex gr probe`.
- Block lengths: `1028`, `989`, `1811`, `100`, and `12`.
- First block begins with a blank signature prefix, as expected for a fixture
  that does not call `0x8f`.
- The third block's on-disk prefix is
  `c87769f82158e57363fb6f5dd6686f91457dca6606ac4011`.
- After `gr_v3_object_inventory_save_xor()`, the third block prefix is
  `8901008b011c9001049a011ca0011cb10108b80167c20167`.
- Applying the same XOR helper a second time restores the emitted third-block
  bytes. The report marks all checks passed.

Conclusion:

- GR action `0x7d` is now both source-backed and original-engine validated for
  the v3 save envelope and third-block XOR transform.
- This first promoted QEMU evidence deliberately avoids GR's
  verifier/save-prefix path; the following correction section covers that path.

## Gold Rush v3 Signed Save Extraction Correction

Goal: correct the GR message-encoding hypothesis and promote the
`0x8f("GR")` save-prefix path to original-engine evidence.

Commands and local reads:

- `python3 -B tools/disassemble_logic.py --game-dir games/GR 101`
- Exact-offset `ndisasm` reads around GR image offsets `0x108c`, `0x245e`,
  `0x5035`, and `0x5ec2..0x5eff`.
- Local Python parse of GR logic 101's message area using table-base-relative
  offsets and decryption from the start of the message text region.
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest
  tests.test_gr_v3_behavior_probe tests.test_qemu_fixture
  tests.test_compatibility_suite`
- `python3 -B -m py_compile tools/gr_v3_behavior_probe.py
  tools/compatibility_suite.py tests/test_gr_v3_behavior_probe.py
  tests/test_compatibility_suite.py`
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py --dry-run
  --include-qemu-v3`
- Signed QEMU run:

```bash
python3 -B tools/gr_v3_behavior_probe.py --probe save-xor-extract --verify-signature --game-dir games/GR --fixture-root build/gr-v3-behavior/save-xor-signed-fixtures --dos-prefix GRS --run-qemu --output build/gr-v3-behavior/save_xor_extract_signed_qemu_001.json --snapshot-raw build/gr-v3-behavior/snapshot/save_xor_extract_signed.raw --snapshot-qcow build/gr-v3-behavior/snapshot/save_xor_extract_signed.qcow2 --post-run-raw build/gr-v3-behavior/snapshot/save_xor_extract_signed_after.raw --save-output build/gr-v3-behavior/GRSG_001.1 --boot-wait 5 --draw-wait 8 --path-prompt-wait 2 --slot-wait 1 --description-wait 1 --confirmation-wait 1 --key-delay 0.08
```

Source observations:

- GR action `0x8f` at image `0x108c` reads the immediate message number,
  resolves it through message helper `0x245e`, copies from that message pointer
  into `DS:0x0002` with bounded copy helper `0x5035`, and then calls verifier
  helper `0x5ede`.
- Helper `0x5ec2` copies the embedded `GR\0` string from code offset `0x5ed7`
  into data buffer `0x0f88`. Helper `0x5ede` compares `DS:0x0002` against the
  embedded code string and calls the shared exit helper on the first mismatch.
- GR logic 101 uses `0x8f(#3)` near bytecode offset `0x0004`. Its message table
  has encrypted text bytes `6f 76 4c 14 16 7d 75 35 35 61`; decrypting the
  text region yields messages `.\0`, `%g69\0`, and `GR\0`. The earlier
  synthetic signed fixture failed because it stored `GR\0` in plain text, so
  the loader decrypted it into the wrong runtime bytes before the verifier
  compared it.

Implementation/test updates:

- `gr_save_extract_payload(verify_signature=True)` now uses the normal
  encrypted-message default instead of `encrypt_messages=False`.
- `tools/gr_v3_behavior_probe.py --probe save-xor-extract
  --verify-signature` now expects `GRSG.N`, checks that the first save-state
  block starts with `GR\0`, and reports `signature_prefix: "GR"`.
- `tools/compatibility_suite.py` adds named command
  `gr_signed_save_xor_extract_qemu` in the opt-in `qemu-v3` layer.
- `tests/test_gr_v3_behavior_probe.py` now asserts that the verifier message is
  encrypted in the fixture payload and decrypts to `GR\0`.

QEMU result:

- Report: `build/gr-v3-behavior/save_xor_extract_signed_qemu_001.json`.
- Extracted save: `build/gr-v3-behavior/GRSG_001.1`.
- Expected save file inside DOS: `GRSG.1`.
- Description: `codex gr probe`.
- Block lengths: `1028`, `989`, `1811`, `100`, and `12`.
- First block prefix bytes: `47 52 00 00 00 00 00 00`.
- Third-block encoded prefix and SHA-256 match the blank-prefix run:
  `c87769f82158e57363fb6f5dd6686f91457dca6606ac4011` and
  `00c9fc2f1cc1ff71f2779804f993dea7389227c486a016556c45a9a0fb63f6a8`.
- Third-block decoded prefix and SHA-256 also match the blank-prefix run:
  `8901008b011c9001049a011ca0011cb10108b80167c20167` and
  `5a833f40a62fc2e367e60600592d8033219586797a3e0a1b3a142accb64bc237`.

Conclusion:

- GR's `0x8f` verifier/save-prefix path is now source-backed and
  original-engine validated for save creation. The correct generated fixture
  shape uses encrypted logic-message text, just like observed GR logic 101.
- A follow-up pass below validates the restore side of the same signed save
  path.

## Gold Rush v3 Signed Restore Round Trip

Goal: validate the source-mapped GR restore path for a signature-prefixed
`GRSG.1` save without treating malformed save data as part of the behavioral
model.

Commands and local reads:

- `git status --short`
- `rg -n "Highest-Value|signed|restore|Gold Rush|v3" PROGRESS.md
  docs/src/clean_room_executable_notes.md docs/src/runtime_model.md
  docs/src/versions.md docs/src/compatibility_testing.md
  docs/src/symbolic_labels.md docs/src/progress_log.md`
- `sed -n` reads of `tools/gr_v3_behavior_probe.py`,
  `tools/save_roundtrip_probe.py`, `tools/qemu_fixture.py`,
  `tools/qemu_snapshot.py`, `tools/compatibility_suite.py`, and the focused
  tests.
- `rizin -q -a x86 -b 16 -c "pd 145 @ 0x2994" games/GR/AGI`
- `rizin -q -a x86 -b 16 -c "pd 75 @ 0x2b44" games/GR/AGI`
- `rizin -q -a x86 -b 16 -c "pd 35 @ 0x2ac8" games/GR/AGI`
- `rizin -q -a x86 -b 16 -c "pd 35 @ 0x09be" games/GR/AGI`
- A prior exploratory `rizin` read without explicit `-a x86 -b 16` decoded the
  bytes as the host architecture. That output was discarded and not used as
  evidence.
- `python3 -B -m py_compile tools/gr_v3_behavior_probe.py
  tests/test_gr_v3_behavior_probe.py`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest
  tests.test_gr_v3_behavior_probe`
- `python3 -B tools/gr_v3_behavior_probe.py --probe signed-restore-roundtrip
  --game-dir games/GR --fixture-root
  build/gr-v3-behavior/signed-restore-dryrun-fixtures --dos-prefix GRT
  --output build/gr-v3-behavior/signed_restore_roundtrip_dryrun_001.json`
- Direct QEMU run:

```bash
python3 -B tools/gr_v3_behavior_probe.py --probe signed-restore-roundtrip --game-dir games/GR --fixture-root build/gr-v3-behavior/signed-restore-qemu-fixtures --dos-prefix GRT --run-qemu --output build/gr-v3-behavior/signed_restore_roundtrip_qemu_001.json --snapshot-raw build/gr-v3-behavior/snapshot/signed_restore_roundtrip_001.raw --snapshot-qcow build/gr-v3-behavior/snapshot/signed_restore_roundtrip_001.qcow2 --post-run-raw build/gr-v3-behavior/snapshot/signed_restore_roundtrip_after_001.raw --save-output build/gr-v3-behavior/GRSG_restore_001.1 --boot-wait 5 --draw-wait 8 --path-prompt-wait 2 --slot-wait 1 --description-wait 1 --confirmation-wait 1 --key-delay 0.08
```

- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest
  tests.test_gr_v3_behavior_probe tests.test_compatibility_suite`
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py --dry-run
  --include-qemu-v3`
- The first suite-wrapper run of `gr_signed_restore_roundtrip_qemu` failed
  before boot because sandboxed QEMU could not bind VNC
  (`Failed to bind socket: Operation not permitted`). The same named command
  passed after rerunning with escalation for local VNC binding:

```bash
AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py --name gr_signed_restore_roundtrip_qemu --report build/compatibility-suite/qemu_v3_signed_restore_001.json
```

Source observations:

- GR restore action `0x7e` is at image `0x2792`, which appears at raw file
  offset `0x2994` in the local MZ image. The prologue sets `[0x0438] = 1`,
  saves the caller continuation in `[bp-0xce]`, temporarily stores `0x40` in
  `[0x0b1c]`, and calls selector helper `0x8aeb` with mode/message byte
  `0x72`.
- The success path opens the selected file through `0x625c`, reads the 31-byte
  description with `0x62f9`, then calls the length-prefixed read helper
  at image `0x2942`/raw `0x2b44` for five blocks.
- The five restore destinations mirror the GR save writer: first block into
  `0x0002`, second into `[0x07d0]`, third into `[0x07d6]`, fourth into
  `[0x153e]`, and fifth into `0x07ea`.
- After the third block has been loaded and all five reads have succeeded, raw
  `0x2ad1..0x2ae0` computes `[0x07d6] + [0x07da]` and calls image `0x07bc`
  / raw `0x09be`, the same repeating-key XOR helper used by the save writer.
  This makes restore decode the on-disk object/inventory block back into its
  runtime representation.
- The restore success path then restores display bytes from `[0x0f4f]` and
  `[0x0f51]`, updates the hardware-mode flag byte `[0x001f]`, calls display
  and resource refresh helpers, clears `[bp-0xce]` to zero, refreshes menu/list
  state, and returns that zero continuation. This matches the existing model:
  successful restore restarts execution through restored state rather than
  continuing after opcode `0x7e`.

Implementation/test updates:

- `tools/gr_v3_behavior_probe.py` now has `--probe
  signed-restore-roundtrip`.
- The probe builds a save-producing fixture whose logic calls `0x8f("GR")`,
  sets a restored-marker flag and marker variables, and invokes `0x7d`. The
  generated `GRSG.1` is extracted from the QEMU disk image.
- A restore fixture copies that generated save into its generated game
  directory, starts with a deliberately different marker X coordinate, calls
  `0x8f("GR")`, and invokes `0x7e`.
- The restore fixture begins each cycle with an `if flag` branch. Only a
  successful restore brings back the saved flag and saved X coordinate, causing
  the next cycle to draw the saved-state marker. If restore fails/cancels and
  continues after `0x7e`, the fixture draws the unrestored marker instead.
- Direct comparison fixtures draw the expected saved-state marker and the
  unrestored-control marker without using save/restore UI.
- `tests/test_gr_v3_behavior_probe.py` now covers the signed restore save
  payload, restore payload, generated fixture copy of `GRSG.1`, and direct
  comparison fixtures.
- `tools/compatibility_suite.py` adds named `qemu-v3` command
  `gr_signed_restore_roundtrip_qemu`, with a manifest test in
  `tests/test_compatibility_suite.py`.

QEMU result:

- Direct report:
  `build/gr-v3-behavior/signed_restore_roundtrip_qemu_001.json`.
- Suite report:
  `build/compatibility-suite/qemu_v3_signed_restore_001.json`.
- Underlying suite probe report:
  `build/gr-v3-behavior/signed_restore_roundtrip_suite.json`.
- The save-generation phase wrote and extracted
  `build/gr-v3-behavior/GRSG_restore_suite.1`.
- Save description: `codex gr probe`.
- Block lengths: `1028`, `989`, `1811`, `100`, and `12`.
- First block prefix bytes: `47 52 00 00 00 00 00 00`.
- Third block encoded SHA-256:
  `00c9fc2f1cc1ff71f2779804f993dea7389227c486a016556c45a9a0fb63f6a8`.
- Third block decoded SHA-256:
  `5a833f40a62fc2e367e60600592d8033219586797a3e0a1b3a142accb64bc237`.
- Capture comparison hashes from the suite probe:
  - restored: `b16282219c5608e75e5b22a1fe3fe016f3ebeed52fa20b0b301260f02a3f713c`
  - expected direct: `b16282219c5608e75e5b22a1fe3fe016f3ebeed52fa20b0b301260f02a3f713c`
  - unrestored control: `160a4ed1bab5ec6eb901ae2c5e3198a081000c0261cf6ad89eec4033e88861b4`
- Checks all passed:
  `save_generation_passed`, `restored_matches_expected_direct`,
  `restored_differs_unrestored_control`, and
  `expected_direct_differs_unrestored_control`.

Conclusion:

- GR action `0x7e` is now source-backed and original-engine validated for a
  valid, signature-prefixed `GRSG.1` restore. The v3 save/restore model should
  apply the repeating `Avis Durgan` XOR transform to the object/inventory block
  on both write and read sides, with successful restore returning through
  restored state rather than continuing after the restore opcode.
- Malformed save behavior remains intentionally out of scope for the
  compatibility spec because invalid files can drive the original interpreter
  into garbage-memory/exploit-like behavior.

## Gold Rush v3 Restart Prompt-Marker Truth Table

Goal: correct and model the GR-specific prompt-marker redraw branch in action
`0x80`.

Commands and local reads:

- `rg -n "GR restart|prompt-marker visible|redraws? (the )?marker|only if.*visible|restart preserves prompt|0x0403|0x0405|0x26e0" docs/src PROGRESS.md tools tests`
- Exact-offset local Python/`ndisasm` reads for GR image offsets `0x26e0`,
  `0x3b00`, `0x3ab0`, and `0x3ad9`.
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests/test_restart_model.py`
- `python3 -B -m py_compile tools/agi_restart.py`

Source observations:

- GR action `0x80` at image `0x26e0` calls helper `0x3b00` and stores the
  current prompt-marker visible word from `[0x0dc3]` in a local before erasing
  the marker through `0x3ad9`.
- After confirmation/reset work, the branch at `0x276f` calls
  `code.input.show_prompt_marker` (`0x3ab0`) when the confirmation result is
  nonzero, or when the confirmation result is zero and the saved visible word
  is nonzero.
- Therefore the redraw predicate is:

```text
restart_was_accepted OR prompt_marker_was_visible_before_entry
```

Implementation/test updates:

- Added `tools/agi_restart.py` with
  `gr_v3_restart_redraws_prompt_marker(accepted, marker_was_visible)`.
- Added `tests/test_restart_model.py` covering all four truth-table rows.

Conclusion:

- The earlier shorthand "redraws only if it had been visible" was too narrow.
  The source-backed GR v3 model is: accepted restart redraws the marker; canceled
  restart redraws only when the marker had been visible on entry.
  A QEMU probe remains optional because this is a text/prompt-marker effect and
  the disassembly branch is direct.
- Final verification for this pass:
  `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests`
  (`263` tests), `mdbook build docs`,
  `python3 -B -m py_compile tools/agi_restart.py tools/agi_save.py tools/gr_v3_behavior_probe.py tools/qemu_fixture.py tools/agi_resources.py tools/compare_gr_sq2_static.py`,
  `git diff --check`, and
  `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py` all passed.

## Gold Rush v3 Instrumented Motion Mode 4 Probe

Goal: validate the GR-specific motion dispatcher branch for object mode `4`
without pretending ordinary bytecode can set that internal state directly.

Commands and local reads:

- `sed -n '560,640p' PROGRESS.md`
- `sed -n '1,620p' tools/gr_v3_behavior_probe.py`
- `sed -n '320,900p' tools/qemu_fixture.py`
- `sed -n '2700,2945p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '12880,13150p' build/gr-sq2-static/gr_agi_image.ndisasm`
- Local Python scan of direct near-call targets in `games/GR/AGI` for image
  offsets `0x1975`, `0x1888`, `0x18cf`, and `0x1909`.
- Local Python scan of present GR picture/view resources through
  `tools/agi_resources.py`.
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests.test_gr_v3_behavior_probe`
- `python3 -B tools/gr_v3_behavior_probe.py --probe motion-mode-4 --game-dir games/GR --fixture-root build/gr-v3-behavior/motion-mode-4-fixtures --dos-prefix GRM --run-qemu --output build/gr-v3-behavior/motion_mode_4_qemu_pic001_001.json --snapshot-raw build/gr-v3-behavior/snapshot/motion_mode_4.raw --snapshot-qcow build/gr-v3-behavior/snapshot/motion_mode_4.qcow2 --boot-wait 5 --draw-wait 8`

Source observations:

- GR `code.motion.dispatch_mode_step` at image `0x068a` reads object byte
  `+0x22`, decrements it, accepts values through `3`, and uses the embedded
  jump table at `0x06bd`. The fourth slot dispatches to the same helper at
  `0x1888` used by mode `3`.
- SQ2 dispatcher `0x067a` accepts only decremented values through `2`, so SQ2
  modes above `3` skip autonomous-mode dispatch.
- GR action `0x51` at image `0x705c` normally stores byte `3` into object
  field `+0x22`, then seeds target X/Y and completion state and calls helper
  `0x1888` once. Action `0x52` follows the same mode-3 shape with variable
  operands.
- The helper-shaped code at image `0x1975` writes object 0 byte `+0x22 = 4`,
  target X/Y bytes `+0x27/+0x28`, and saved step byte `+0x29` when
  `[0x0139]` is nonzero. A direct near-call scan found no ordinary call to
  `0x1975` in the local GR main image, and no bytecode action table entry
  points at it. Its natural entry path remains unresolved/source-only.
- The first attempt to patch action `0x51` used the loaded-image offset as a
  file offset and failed with context bytes `8b f8 a1 d0` instead of
  `c6 45 22 03`. The patch helper now translates loaded-image offsets through
  the MZ header size when the copied interpreter begins with `MZ`.

Implementation/test updates:

- Added `--probe motion-mode-4` to `tools/gr_v3_behavior_probe.py`.
- The probe builds three copied GR fixtures under `build/`:
  stationary object, unmodified action-`0x51` mode-3 movement, and an
  instrumented copy where byte `0x03` at loaded-image offset `0x707f` is
  patched to `0x04`.
- Added tests covering the generated motion payload, the expected patch context,
  rejection of unexpected interpreter bytes, and fixture construction.

QEMU result:

- Report `build/gr-v3-behavior/motion_mode_4_qemu_pic001_001.json` passed.
- The instrumented mode-4 capture matched the unmodified mode-3 movement
  capture from `(20,80)` to `(50,80)` on GR picture 1/view 0.
- The stationary control did not match the moving capture.

Conclusion:

- The GR v3 internal dispatcher branch for object motion mode `4` is now
  instrumented-QEMU-validated: once mode `4` exists in object byte `+0x22`, it
  follows the same visible target-direction path as mode `3`.
- This is not evidence that ordinary logic bytecode can create mode `4`; the
  natural seeding path is still source-only and should remain separate in the
  implementation spec.

## Gold Rush v3 Frame-Selection Gate Probe

Goal: resolve and validate the GR-specific branch inside
`code.object.frame_timer_update` (`0x055c`) for automatic direction-based group
selection on views with exactly four groups versus more than four groups.

Commands and local reads:

- `sed -n '560,700p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '600,690p' build/gr-sq2-static/sq2_agi_image.ndisasm`
- Local Python census of GR view resources through `tools/agi_resources.py`,
  using payload byte `+0x02` as the group count and group offsets at `+0x05`.
- Local decoded-frame comparison of candidate GR views 33, 39, 177, and other
  four-plus-group resources.
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests.test_gr_v3_behavior_probe`
- `python3 -B tools/gr_v3_behavior_probe.py --probe frame-selection-gate --game-dir games/GR --fixture-root build/gr-v3-behavior/frame-selection-fixtures --dos-prefix GRF --run-qemu --output build/gr-v3-behavior/frame_selection_gate_qemu_001.json --snapshot-raw build/gr-v3-behavior/snapshot/frame_selection_gate.raw --snapshot-qcow build/gr-v3-behavior/snapshot/frame_selection_gate.qcow2 --boot-wait 5 --draw-wait 8`

Source observations:

- SQ2 `code.object.frame_timer_update` at image `0x0563` uses the two/three
  group table when object byte `+0x0b` is 2 or 3. When `+0x0b >= 4`, it indexes
  the four-plus group table at data `0x08e7`.
- GR `code.object.frame_timer_update` at image `0x055c` keeps the two/three
  group path, then differs at image `0x05ac`:
  - If `+0x0b == 4`, it jumps directly to the four-plus table path at `0x05c6`.
  - Otherwise it tests flag `0x14` via helper `0x7818`.
  - If flag `0x14` is clear, it skips selection and leaves the target as
    sentinel `4`.
  - If flag `0x14` is set, it still requires `+0x0b > 4` before using the
    four-plus table.
- Therefore the earlier shorthand was backwards for exactly-four-loop views:
  exactly four groups are not excluded; they bypass the new flag gate and use
  the same four-plus table as SQ2. Only group counts greater than four are
  gated on flag `0x14`.
- Local GR resources include suitable stock views, so no synthetic v3 view
  packing was needed:
  - View 177 has exactly four groups, with visibly distinct group 0 and group 1
    frames.
  - View 39 has more than four groups, with visibly distinct group 0 and group
    1 frames.

Implementation/test updates:

- Added `--probe frame-selection-gate` to `tools/gr_v3_behavior_probe.py`.
- The probe builds copied GR fixtures under `build/` for group-0/group-1
  controls, exact-four flag-clear/flag-set cases, and more-than-four
  flag-clear/flag-set cases. It uses ordinary logic bytecode only; the GR
  interpreter is not patched.
- Added focused tests covering the generated gate payload, control payload, and
  fixture case list.

QEMU result:

- Report `build/gr-v3-behavior/frame_selection_gate_qemu_001.json` passed.
- Exact-four view 177 selected group 1 for direction `6` both with flag `0x14`
  clear and with flag `0x14` set; both captures matched the group-1 control
  and did not match the group-0 control.
- More-than-four view 39 remained on group 0 while flag `0x14` was clear; after
  flag `0x14` was set, it selected group 1. The group-0 and group-1 controls
  were distinct.

Conclusion:

- GR / AGI v3 automatic direction group selection should be modeled as:
  two/three groups use the two/three table; exactly four groups use the
  four-plus table; more than four groups use the four-plus table only when flag
  `0x14` is set. Sentinel target `4` still means "do not change group."

## 2026-07-10: GR v3 restart prompt-marker QEMU confirmation

Goal: confirm the source-mapped GR action `0x80` canceled-restart
prompt-marker branch with an original-engine fixture.

Commands and local reads:

- `sed -n '619,700p' PROGRESS.md`
- `sed -n '8960,9035p' docs/src/clean_room_executable_notes.md`
- `sed -n '1,260p' tools/agi_restart.py`
- `sed -n '1,260p' tests/test_restart_model.py`
- `sed -n '1,360p' tools/gr_v3_behavior_probe.py`
- `sed -n '820,1320p' tools/gr_v3_behavior_probe.py`
- `rg -n "restart|prompt|input_line|0x77|0x78|confirm_restart|show_prompt" tools/logic_interpreter_probe.py tests/test_logic_interpreter_probe.py docs/src/runtime_model.md docs/src/logic_bytecode.md`
- `python3 -B -m py_compile tools/gr_v3_behavior_probe.py tools/compatibility_suite.py tests/test_gr_v3_behavior_probe.py tests/test_compatibility_suite.py`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests.test_gr_v3_behavior_probe tests.test_compatibility_suite tests.test_restart_model`
- `python3 -B tools/gr_v3_behavior_probe.py --probe restart-prompt-marker --game-dir games/GR --fixture-root build/gr-v3-behavior/restart-prompt-dryrun-fixtures --dos-prefix GRP --output build/gr-v3-behavior/restart_prompt_marker_dryrun_001.json`
- `python3 -B tools/gr_v3_behavior_probe.py --probe restart-prompt-marker --game-dir games/GR --fixture-root build/gr-v3-behavior/restart-prompt-qemu-fixtures --dos-prefix GRP --run-qemu --output build/gr-v3-behavior/restart_prompt_marker_qemu_001.json --snapshot-raw build/gr-v3-behavior/snapshot/restart_prompt_marker_001.raw --snapshot-qcow build/gr-v3-behavior/snapshot/restart_prompt_marker_001.qcow2 --boot-wait 5 --draw-wait 8`
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py --name gr_restart_prompt_marker_qemu --report build/compatibility-suite/qemu_v3_restart_prompt_001.json`

Source-first model:

- The earlier source pass showed GR action `0x80` recording the current
  prompt-marker visible word before erasing it.
- After confirmation, accepted restart always redraws the marker; canceled
  restart redraws the marker only when it was visible on entry.
- The local helper `gr_v3_restart_redraws_prompt_marker()` keeps this truth
  table pinned for implementation use.

Fixture implementation:

- Added `--probe restart-prompt-marker` to `tools/gr_v3_behavior_probe.py`.
- The probe builds four copied GR fixtures under `build/`: hidden control,
  visible control, hidden then Escape-canceled restart, and visible then
  Escape-canceled restart.
- The fixture logic uses ordinary bytecode only: picture load/show, prompt
  marker message setup through `0x6c`, input row setup through `0x6f`, hidden
  or visible marker setup through `0x77`/`0x78`, and restart confirmation
  through `0x80`.
- The QEMU report compares both whole captures and the foreground-pixel count
  in logical prompt rectangle `(0,40)..(39,47)`.
- The v3 compatibility suite now has named command
  `gr_restart_prompt_marker_qemu`.

QEMU result:

- Direct report `build/gr-v3-behavior/restart_prompt_marker_qemu_001.json`
  passed.
- Suite report `build/compatibility-suite/qemu_v3_restart_prompt_001.json`
  passed after rerunning with VNC socket permission; the first unprivileged
  attempt failed before QEMU saved the DOS snapshot with
  `Failed to bind socket: Operation not permitted`.
- Hidden control and hidden canceled restart had 0 prompt-row foreground
  pixels and identical capture hash
  `82d824134a00e40ae092e86b396b4b712e1d8ad48e7ad181d484ffbe8fa79f28`.
- Visible control and visible canceled restart had 8 prompt-row foreground
  pixels and identical capture hash
  `cd7a1c8f5bf5eee32a6e818fb1c49d274db9175de9cbc7ed3f95a721df0e5a96`.

Conclusion:

- The original GR interpreter confirms the canceled-restart half of the
  source-backed truth table: Escape-canceled restart restores the prompt marker
  only when it was visible before action `0x80` erased it. The accepted-restart
  half remains source-backed because the reset path immediately restarts engine
  state, making a clean visual oracle less useful than the direct branch.

## 2026-07-10: GR v3 menu interaction gate QEMU confirmation

Goal: confirm the source-mapped GR-only action `0xb1`
`set_menu_interaction_gate` with an original-engine fixture.

Commands and local reads:

- `git status --short`
- `rg -n "menu-gate|menu gate|0xb1|Highest-Value|raw key-release|GR / SQ2|Menus|Compatibility|restart prompt|set_menu_interaction|code.menu.interact|0403" PROGRESS.md docs/src/versions.md docs/src/runtime_model.md docs/src/logic_bytecode.md docs/src/compatibility_testing.md docs/src/symbolic_labels.md docs/src/clean_room_executable_notes.md docs/src/progress_log.md AGENTS.md`
- `sed -n '1,220p' PROGRESS.md`
- `tail -n 80 docs/src/progress_log.md`
- `sed -n '40,180p' docs/src/versions.md`
- `sed -n '470,530p' docs/src/runtime_model.md`
- `sed -n '110,140p' docs/src/logic_bytecode.md`
- `sed -n '1488,1504p' docs/src/logic_bytecode.md`
- `sed -n '1080,1135p' docs/src/compatibility_testing.md`
- `sed -n '150,190p' AGENTS.md`
- `tail -n 120 docs/src/clean_room_executable_notes.md`
- `sed -n '500,640p' PROGRESS.md`
- `sed -n '250,285p' docs/src/symbolic_labels.md`
- `sed -n '428,545p' docs/src/symbolic_labels.md`
- `sed -n '540,610p' PROGRESS.md`
- `rg -n "282|test" PROGRESS.md docs/src/compatibility_testing.md`
- `sed -n '1,260p' tools/gr_v3_behavior_probe.py`
- `sed -n '494,516p' docs/src/runtime_model.md`
- `sed -n '976,990p' docs/src/compatibility_testing.md`
- `sed -n '70,90p' docs/src/compatibility_testing.md`
- `sed -n '1478,1530p' docs/src/compatibility_testing.md`
- `sed -n '380,438p' tools/compatibility_suite.py`
- `rg -n "0403|1b67|970B|9724|038D|38d|000097|000038" build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '17600,17760p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '4250,4320p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `python3 -B -m py_compile tools/gr_v3_behavior_probe.py tools/compatibility_suite.py tests/test_gr_v3_behavior_probe.py tests/test_compatibility_suite.py`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests.test_gr_v3_behavior_probe tests.test_compatibility_suite`
- `python3 -B tools/gr_v3_behavior_probe.py --probe menu-gate --game-dir games/GR --fixture-root build/gr-v3-behavior/menu-gate-dryrun-fixtures --dos-prefix GRG --output build/gr-v3-behavior/menu_gate_dryrun_001.json`
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py --dry-run --include-qemu-v3`
- `python3 -B tools/gr_v3_behavior_probe.py --probe menu-gate --game-dir games/GR --fixture-root build/gr-v3-behavior/menu-gate-qemu-fixtures --dos-prefix GRG --run-qemu --output build/gr-v3-behavior/menu_gate_qemu_001.json --snapshot-raw build/gr-v3-behavior/snapshot/menu_gate_001.raw --snapshot-qcow build/gr-v3-behavior/snapshot/menu_gate_001.qcow2 --boot-wait 5 --draw-wait 8`
- `python3 -B tools/gr_v3_behavior_probe.py --probe menu-gate --game-dir games/GR --fixture-root build/gr-v3-behavior/menu-gate-qemu-fixtures-2 --dos-prefix GRG --run-qemu --output build/gr-v3-behavior/menu_gate_qemu_002.json --snapshot-raw build/gr-v3-behavior/snapshot/menu_gate_002.raw --snapshot-qcow build/gr-v3-behavior/snapshot/menu_gate_002.qcow2 --boot-wait 5 --draw-wait 8`
- `python3 -B tools/gr_v3_behavior_probe.py --probe menu-gate --game-dir games/GR --fixture-root build/gr-v3-behavior/menu-gate-qemu-fixtures-3 --dos-prefix GRG --run-qemu --output build/gr-v3-behavior/menu_gate_qemu_003.json --snapshot-raw build/gr-v3-behavior/snapshot/menu_gate_003.raw --snapshot-qcow build/gr-v3-behavior/snapshot/menu_gate_003.qcow2 --boot-wait 5 --draw-wait 8`
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py --name gr_menu_gate_qemu --report build/compatibility-suite/qemu_v3_menu_gate_001.json`

Source-first model:

- GR-only action handler `0x970b` reads one immediate byte, zero-extends it,
  and stores the word at `[0x0403]`.
- GR action `0xa1` at `0x96eb` still tests flag 14 and writes word
  `[0x1b67] = 1` as the ordinary menu request.
- The GR main-cycle path around image `0x38dd` notices `[0x1b67] != 0` and
  calls `code.menu.interact` at image `0x9724`.
- `code.menu.interact` first compares word `[0x0403]` with zero. If it is
  zero, it returns immediately; if nonzero, it proceeds into the existing
  draw/wait modal menu path. Therefore `0xb1` is an interaction gate, not part
  of menu construction.

Fixture implementation:

- Added `--probe menu-gate` to `tools/gr_v3_behavior_probe.py`.
- The final probe builds three copied GR fixtures under `build/`:
  `menu_gate_blocked_control`, `menu_gate_enabled_request`, and
  `menu_gate_disabled_request`.
- The blocked control draws a visible object marker at the blocked location.
- The request fixtures build a one-heading, one-item menu, finalize it, set
  flag 14, execute `0xb1(1)` or `0xb1(0)`, execute `0xa1`, and then end the
  logic stream so the top-level engine cycle can service `[0x1b67]`.
- The promoted oracle does not depend on pressing Enter inside the menu. It
  checks only the gate: `0xb1(0)` should match the blocked control, while
  `0xb1(1)` should differ by entering the modal menu path.

Important correction:

- An earlier fixture ended with a self-loop. That kept logic 0 executing inside
  the interpreter and prevented the top-level main cycle from reaching the
  `[0x1b67]` check. Both enabled and disabled cases therefore matched the
  blocked control even though the generated `0xb1` bytes were correct.
- Replacing the self-loop with the structural `end` action allowed the
  original engine's main cycle to process the request. The Enter-driven
  accepted-marker oracle still was not stable, so the final evidence uses a
  no-key modal-gate oracle.

QEMU result:

- Direct report `build/gr-v3-behavior/menu_gate_qemu_003.json` passed.
- `menu_gate_disabled_request` matched `menu_gate_blocked_control`.
- `menu_gate_enabled_request` differed from both the blocked control and the
  disabled request.
- Capture SHA-256 values:
  - blocked control and disabled request:
    `160a4ed1bab5ec6eb901ae2c5e3198a081000c0261cf6ad89eec4033e88861b4`
  - enabled request:
    `e463cb17d86267bda970277df82d51c6b51dc743327f51c856a25de65399155b`
- The named suite command
  `build/compatibility-suite/qemu_v3_menu_gate_001.json` passed after rerunning
  with VNC socket permission; the first unprivileged attempt failed before QEMU
  launched with `Failed to bind socket: Operation not permitted`.

Conclusion:

- The original GR interpreter confirms the disassembly model for action
  `0xb1`: zero blocks a requested menu before the modal menu draw/wait path,
  and nonzero permits the existing menu interaction path to run after `0xa1`.

## 2026-07-10: SQ2/GR tracked key-release IRQ source model

Goal: turn the remaining source-backed raw key-release gate into an
implementation-facing state model without relying on QEMU keyboard-release
timing.

Commands and local reads:

- `git status --short`
- `sed -n '621,640p' PROGRESS.md`
- `rg -n "key-release|key release|0xad|0xb5|0405|1530|release_event|tracked-key|type-2 zero|raw key" PROGRESS.md docs/src tools tests build/gr-sq2-static/gr_agi_image.ndisasm build/gr-sq2-static/sq2_agi_image.ndisasm`
- `rg -n "map_key|raw_key|status_byte|key_release|release|sendkey|post_launch_key_names|post_launch_keys|key_names" tools/logic_interpreter_probe.py tools/gr_v3_behavior_probe.py tests/test_logic_interpreter_probe.py tests/test_gr_v3_behavior_probe.py`
- `sed -n '10870,11140p' build/gr-sq2-static/sq2_agi_image.ndisasm`
- `sed -n '11220,11480p' build/gr-sq2-static/gr_agi_image.ndisasm`
- `sed -n '188,240p' docs/src/symbolic_labels.md`
- `sed -n '470,505p' docs/src/logic_bytecode.md`
- `sed -n '1285,1305p' docs/src/compatibility_testing.md`
- `sed -n '5677,5708p' docs/src/clean_room_executable_notes.md`
- `rg -n "Restart|Save|heap|motion|keyboard|input|model|source-modeled|class .*Model|def .*model|gr_v3" tools tests | head -n 200`
- `ls tools | sort`
- `ls tests | sort`
- `sed -n '1,220p' tools/agi_restart.py`
- `sed -n '1,220p' tests/test_restart_model.py`
- `python3 -B -m py_compile tools/agi_input.py tests/test_input_model.py`
- `python3 -B -m unittest tests.test_input_model`

Source observations:

- SQ2 action `0xad` at image `0x602f` is `inc byte [0x1530]`, so the gate is
  an unsigned byte and wraps from `0xff` to zero.
- GR action `0xad` at image `0x63a8` stores byte `[0x0405] = 1`.
- GR-only action `0xb5` at image `0x63b0` stores byte `[0x0405] = 0`.
- The SQ2 keyboard IRQ hook at image `0x6036` and the GR hook at image
  `0x63b8` have the same tracked-key latch shape after relocation:
  - read the raw scan byte from port `0x60`;
  - mask off bit `0x80` and accept only scan codes `0x47..0x51`;
  - require the corresponding enable-table byte to be nonzero;
  - on keydown, if the selected latch was clear, clear all tracked latches and
    set only the selected latch;
  - on duplicate keydown, do not enqueue a script event;
  - on key release, clear the selected latch only if it had been set;
  - enqueue event `(type=2, value=0)` only when that release path cleared a
    latch and the version-specific gate byte is nonzero.

Implementation/test updates:

- Added `tools/agi_input.py` with a portable `KeyReleaseIrqState` model,
  SQ2/GR gate-writer helpers, and `process_tracked_key_irq_scan()`.
- Added `tests/test_input_model.py` to cover:
  - SQ2 `0xad` enabling a later release event;
  - SQ2 byte wraparound from `0xff` to zero;
  - GR `0xad`/`0xb5` set/clear behavior;
  - keydown clearing other tracked latches;
  - disabled and out-of-range scan bytes producing no event;
  - model validation for table lengths and gate byte range.

Conclusion:

- The tracked release-key behavior is now source-modeled at a portable state
  level. A direct QEMU fixture remains optional only if the final target needs
  raw hardware IRQ timing evidence; it is not necessary for the valid-data AGI
  semantics currently being specified.

## 2026-07-10: v3 generated picture/view fixture packing

Goal: remove the remaining fixture-writer gap for targeted Gold Rush / AGI v3
graphics probes without modifying private local inputs under `games/`.

Commands and local reads:

- `git status --short`
- `sed -n '621,640p' PROGRESS.md`
- `rg -n "does not yet pack|direct-record logic|v3.*picture/view|picture-nibble|v3-synthetic|v3 fixture" AGENTS.md PROGRESS.md docs/src tests tools`
- `sed -n '220,340p' docs/src/resource_files.md`
- `sed -n '1,220p' docs/src/versions.md`
- `sed -n '660,900p' tools/qemu_fixture.py`
- `sed -n '900,980p' tools/qemu_fixture.py`
- `sed -n '1260,1365p' tools/qemu_fixture.py`
- `rg -n "def encode_picture_nibbles|encode_picture_nibbles" tools/agi_resources.py tests/test_agi_resources.py tests/test_qemu_fixture.py`
- `sed -n '265,345p' tools/agi_resources.py`
- `python3 -B -m py_compile tools/agi_resources.py tools/qemu_fixture.py tests/test_agi_resources.py tests/test_qemu_fixture.py`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests.test_agi_resources tests.test_qemu_fixture`

Source/model observations:

- The v3 generic reader accepts direct records when the expanded and stored
  lengths in the 7-byte record header are equal. That path is already present
  in original GR resources and is suitable for controlled generated logic/view
  fixtures.
- The v3 picture path is selected by metadata bit `0x80`; the low nibble still
  names the volume and must match the directory entry volume. The stored
  payload is a nibble stream that expands to ordinary picture bytes.
- The inverse picture-nibble writer packs ordinary bytes as two nibbles, except
  the operand following picture commands `0xf0` and `0xf2`, which is stored as
  one nibble. The generated expanded stream must end at `0xff`.

Implementation/test updates:

- Added `encode_picture_nibbles()` to `tools/agi_resources.py` as the inverse
  of the observed GR picture-nibble expansion for valid expanded picture
  streams.
- Added v3 fixture helpers in `tools/qemu_fixture.py`:
  `v3_picture_volume_record()`, generic `patch_v3_resource()`,
  `patch_v3_picture_resource()`, `patch_v3_view_resource()`,
  `build_v3_synthetic_picture_fixture()`, and
  `build_v3_synthetic_picture_view_fixture()`.
- Added CLI commands `v3-synthetic-picture` and `v3-synthetic-picture-view`.
- Added local read-back tests for the picture-nibble record wrapper, copied v3
  picture patching, copied v3 view patching, and full synthetic picture/view
  fixture construction.

Conclusion:

- Targeted v3 picture/view probes can now be generated under `build/` without
  patching `games/`. The project still does not implement a v3 dictionary
  compressor; generated view payloads use the original interpreter's
  direct-record path, while original compressed local resources continue to be
  decoded through the observed reader model.

## 2026-07-10: v3 synthetic picture/view fixture QEMU probe

Goal: confirm the generated GR v3 picture/view fixture writer against the
original interpreter after adding local read-back tests.

Commands and local reads:

- `git status --short`
- `sed -n '1,180p' PROGRESS.md`
- `sed -n '180,360p' PROGRESS.md`
- `sed -n '620,660p' PROGRESS.md`
- `sed -n '1,260p' tools/gr_v3_behavior_probe.py`
- `sed -n '260,620p' tools/gr_v3_behavior_probe.py`
- `sed -n '620,980p' tools/gr_v3_behavior_probe.py`
- `sed -n '980,1380p' tools/gr_v3_behavior_probe.py`
- `sed -n '1380,1760p' tools/gr_v3_behavior_probe.py`
- `sed -n '1760,2140p' tools/gr_v3_behavior_probe.py`
- `sed -n '1,260p' tests/test_gr_v3_behavior_probe.py`
- `sed -n '260,620p' tests/test_gr_v3_behavior_probe.py`
- `sed -n '1,220p' tests/test_compatibility_suite.py`
- `sed -n '1,340p' tools/compatibility_suite.py`
- `sed -n '430,510p' tests/test_qemu_fixture.py`
- `python3 -B -m py_compile tools/gr_v3_behavior_probe.py tools/compatibility_suite.py tests/test_gr_v3_behavior_probe.py tests/test_compatibility_suite.py`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests.test_gr_v3_behavior_probe tests.test_compatibility_suite`
- `python3 -B tools/gr_v3_behavior_probe.py --probe synthetic-picture-view --game-dir games/GR --fixture-root build/gr-v3-behavior/synthetic-picture-view-fixtures --dos-prefix GSP --output build/gr-v3-behavior/synthetic_picture_view_001.json`
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py --name gr_synthetic_picture_view_qemu --report build/compatibility-suite/qemu_v3_synthetic_picture_view_001.json`
- Repeated the same compatibility-suite command with elevated execution after
  the first QEMU attempt failed before launch with `Failed to bind socket:
  Operation not permitted`.

Fixture design:

- The blank control patches logic 0 to loop without drawing.
- The picture-only fixture patches logic 0 to show generated picture 0 and
  stores picture 0 as a v3 picture-nibble record in `GRVOL.1`.
- The picture/view fixture uses the same generated picture plus a direct v3
  view 0 record. The logic draws the picture, loads view 0, and uses action
  `0x7a` to place group 0 frame 0 at `(20,80)` with priority `15`.
- The generated picture payload is `f0 01 f8 50 50 ff`: select visual color 1,
  seed fill at `(80,80)`, then terminate.
- The generated view payload is a one-loop, one-frame, 4x4 opaque run-length
  encoded cel with color 4 and transparent color 0:
  `00 00 01 00 00 07 00 01 03 00 04 04 00 44 00 44 00 44 00 44 00`.

Implementation/test updates:

- Added `--probe synthetic-picture-view` to `tools/gr_v3_behavior_probe.py`.
- Added `build_gr_synthetic_picture_view_fixtures()` and a QEMU reducer that
  compares blank, picture-only, and picture-plus-view captures.
- Added local tests that read the generated v3 records back through
  `tools/agi_resources.py` and confirm the expected picture-nibble/direct
  transforms.
- Added compatibility-suite command `gr_synthetic_picture_view_qemu`.

QEMU result:

- `build/gr-v3-behavior/synthetic_picture_view_suite.json` passed.
- The blank control had one unique color.
- The picture-only capture had two unique colors and differed from blank by
  215,040 pixels.
- The picture-plus-view capture had three unique colors and differed from
  picture-only by 128 pixels.
- Capture hashes:
  - blank control:
    `f3ee47648d6ba080ffab59f9c5cc84d66a44ee6de07c5fa3edbe222e95021062`
  - picture only:
    `e9b3a51fc2fe85e39ba7c88c726e4835d8586d6cfa50bea45727e08e71a424a4`
  - picture plus view:
    `a1680189d4c06001263bbcec3edcea29b9323ca584e2a533918693d5cc60113a`

Conclusion:

- The original GR interpreter accepts the generated picture-nibble picture
  record and direct view record for this controlled fixture. This promotes the
  v3 fixture writer as reusable compatibility infrastructure while preserving
  the source-backed renderer/model distinction.

## 2026-07-10: sound/audio subsystem specification pass

Goal: consolidate the already source-backed sound findings into a dedicated
implementation-facing mdBook chapter.

Commands and local reads:

- `git status --short`
- `sed -n '1,220p' PROGRESS.md`
- `sed -n '420,660p' PROGRESS.md`
- `tail -n 60 docs/src/progress_log.md`
- `rg -n "Sound|sound|audio|tone|PC-speaker|speaker|duration|waveform|Remaining|0x62|0x63|0x64" PROGRESS.md docs/src tools tests`
- `rg --files docs/src tools tests | rg "sound|audio"`
- `sed -n '1,220p' docs/src/SUMMARY.md`
- `sed -n '135,205p' docs/src/runtime_model.md`
- `sed -n '300,340p' docs/src/symbolic_labels.md`
- `sed -n '1,260p' tests/test_sound_resources.py`
- `sed -n '1,260p' tools/agi_sound.py`
- `sed -n '260,360p' tools/agi_sound.py`
- `rg -n "Sound/audio|Sound|sound|audio|Highest-Value|Final spec|Remaining" PROGRESS.md`
- `tail -n 80 docs/src/progress_log.md`
- `tail -n 80 docs/src/clean_room_executable_notes.md`
- `sed -n '100,220p' docs/src/current_status.md`
- `sed -n '520,552p' PROGRESS.md`
- `sed -n '630,652p' PROGRESS.md`
- `sed -n '1,80p' docs/src/resource_files.md`
- `sed -n '1,80p' docs/src/graphics_object_pipeline.md`
- `python3 -B -m unittest tests.test_sound_resources`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests.test_sound_resources`
- `mdbook build docs`
- `git diff --check`
- `git status --short`
- `find tests tools -type d -name __pycache__ -print`

Observations consolidated:

- Sound payloads begin with four little-endian channel offsets, followed by
  duration/tone/control channel streams terminated by duration `0xffff`.
- The current SQ2 corpus has 49 present sound resources, all with four sorted
  in-bounds channel offsets and terminating streams.
- `0x62`, `0x63`, and `0x64` expose sound loading, start-with-completion-flag,
  and stop/clear behavior to logic bytecode.
- Driver start initializes channel countdowns to `1`, so the first channel
  record is consumed on the first active sound tick.
- Selectors `0` and `8` advance only channel 0; other observed selectors
  advance all four channels.
- Flag 9 is a playback gate tested at the start of the tick path. Clearing it
  causes immediate stop/completion on tick 1.
- The PC-speaker path computes a divisor from the event tone word and treats
  attenuation nibble `0x0f` as silence.
- The non-PC path emits tone bytes and channel/attenuation bytes to port
  `0xc0`; the stop path emits `0x9f 0xbf 0xdf 0xff`.
- The attenuation envelope table uses signed deltas from the event base
  attenuation and terminates with sentinel `0x80`.

Documentation updates:

- Added `docs/src/sound_and_audio.md`.
- Added the new chapter to `docs/src/SUMMARY.md`.
- Updated `PROGRESS.md` and `docs/src/current_status.md` to reference the
  dedicated sound/audio chapter.

Validation:

- The first focused sound test command failed with the expected explicit-game
  guard: `game directory required; pass --game-dir PATH or set AGI_GAME_DIR`.
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests.test_sound_resources`
  passed 16 tests.
- `mdbook build docs` passed.
- `git diff --check` passed.
- No Python `__pycache__` directories were present under `tests/` or `tools/`
  after the focused test run.

Conclusion:

- The sound/audio subsystem now has a chapter-level contract for resource
  parsing, playback scheduling, completion flags, and hardware-driver output
  boundaries. Analog waveform synthesis remains explicitly outside the current
  interpreter compatibility target.

## 2026-07-10: read-only multi-game census tooling

Goal: create a reproducible source-first inventory step for the additional
local game directories without modifying private inputs under `games/`.

Commands and local reads:

- `sed -n '640,670p' PROGRESS.md`
- `sed -n '1,260p' docs/src/versions.md`
- `sed -n '1,220p' docs/src/cross_version_workflow.md`
- `rg -n "v3|GR|Gold|compression|picture-nibble|direct view|loader error|static delta|behavioral" docs/src PROGRESS.md tools tests`
- `rg -n "v3|GR|combined|dictionary|nibble|prefixed|expanded|stored|compression|Version|SQ2|sound" docs/src/resource_files.md`
- `sed -n '80,240p' docs/src/resource_files.md`
- `sed -n '228,390p' docs/src/resource_files.md`
- `sed -n '1,260p' tools/agi_resources.py`
- `sed -n '260,560p' tools/agi_resources.py`
- `sed -n '1,180p' tests/test_agi_resources.py`
- `find games -maxdepth 2 -type f`
- `find games -maxdepth 1 -type d`
- `git ls-files tools`
- `sed -n '1,220p' tools/project_paths.py`
- `sed -n '1,220p' tests/test_compatibility_suite.py`
- `sed -n '1,220p' tests/test_qemu_fixture.py`
- `sed -n '1,120p' .gitignore`
- `python3 -B -m py_compile tools/game_census.py tests/test_game_census.py`
- `python3 -B -m unittest tests.test_game_census`
- `python3 -B tools/game_census.py --games-root games --format json --output build/cross-version/game_census.json`
- `python3 -B tools/game_census.py --games-root games --format markdown --output build/cross-version/game_census.md`
- `sed -n '1,80p' build/cross-version/game_census.md`
- `python3 -m json.tool build/cross-version/game_census.json`
- `mdbook build docs`
- `git diff --check`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests`
- `find tests tools -type d -name __pycache__ -print`
- `rm -rf tests/__pycache__ tools/__pycache__`
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/logic_opcode_evidence.py --check`
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py --report build/compatibility-suite/local_game_census_dispatch_001.json`
- `python3 -m json.tool build/compatibility-suite/local_game_census_dispatch_001.json`

Implementation:

- Added `tools/game_census.py`.
- The tool requires one or more explicit `--game-dir` paths or an explicit
  `--games-root` path.
- It detects v2 split and v3 combined layouts through `tools/agi_resources.py`.
- It extracts local `Version ...` strings from known interpreter data files.
- It counts entries, present entries, volumes, readable record transforms, and
  stored/expanded byte totals per resource family.
- It records per-record header/expansion errors instead of aborting the whole
  inventory.
- Added synthetic tests in `tests/test_game_census.py` for split layout,
  combined layout, version extraction, deduplication, and Markdown formatting.

Validation:

- `python3 -B -m py_compile tools/game_census.py tests/test_game_census.py`
  passed.
- `python3 -B -m unittest tests.test_game_census` passed 5 tests.
- `python3 -B -m unittest tests.test_game_census tests.test_agi_resources`
  passed 13 tests.
- `mdbook build docs` passed.
- `git diff --check` passed.
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests` passed
  304 tests.
- Removed the generated `tests/__pycache__` and `tools/__pycache__`
  directories after the full test run.

Current private-input census:

- v2 split layouts: KQ1 `Version 2.917`, KQ2 `Version 2.411`, KQ3
  `Version 2.936`, LSL1 `Version 2.440`, PQ1 `Version 2.917`, and SQ2
  `Version 2.936`.
- v3 combined layouts: KQ4D `Version 3.002.102` with `DMDIR`/`DMVOL.N`, and
  GR `Version 3.002.149` with `GRDIR`/`GRVOL.N`.
- GR has no record errors under the current v3 reader.
- SQ2 still reports the two known out-of-range end entries from LOGDIR/PICDIR.
- KQ1 has four sound entries that fail the generic v2 header check.
- KQ4D has multiple suspect sound-section entries that fail the generic v3
  header check. These should be source-inspected before any behavioral rule is
  added.

Conclusion:

- The project now has a repeatable first-pass inventory for future
  cross-version comparison. Record errors are planning evidence for later
  disassembly, not part of the clean-room behavioral model for valid resources.

## 2026-07-10: KQ4D dispatch-table detection and sound references

Goal: follow up on the KQ4D census errors by fixing v3 logic disassembly for
non-GR table bases and checking whether decoded KQ4D scripts reference the
suspect sound-section entries.

Commands and local reads:

- `ls -l games/KQ4D/DMDIR games/KQ4D/DMVOL.* games/KQ4D/AGI`
- `xxd -g1 -l 96 games/KQ4D/DMDIR`
- `xxd -g1 -s 0x2d5 -l 256 games/KQ4D/DMDIR`
- `file games/KQ4D/AGI games/GR/AGI games/SQ2/AGI`
- Python local decode of KQ4D `DMDIR` sound entries, printing present-like
  indices, raw triples, target volume/offsets, and target header bytes.
- `python3 -B tools/disassemble_logic.py --help` without a game directory,
  which failed with the expected explicit-game guard.
- `AGI_GAME_DIR=games/KQ4D python3 -B tools/disassemble_logic.py --help`
- `AGI_GAME_DIR=games/KQ4D python3 -B tools/disassemble_logic.py --stats`
  before the fix, showing garbage table data from the old GR-specific v3
  table bases.
- Python local scans comparing SQ2/GR/KQ4D AGIDATA table bytes and searching
  for action/condition argc/meta signatures.
- `rg -n "dispatch_table_layout|load_table|ACTION_NAMES|COND_NAMES|disassemble_logic" tests tools docs/src`
- `sed -n '430,530p' tools/disassemble_logic.py`
- `rg -n "0x0440|0x0762|0x061D|0x08FD|dispatch table|AGIDATA dispatch" docs/src tests tools`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m py_compile tools/disassemble_logic.py tests/test_disassemble_logic_tables.py`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests.test_disassemble_logic_tables`
- `AGI_GAME_DIR=games/KQ4D python3 -B tools/disassemble_logic.py --stats`
- `AGI_GAME_DIR=games/KQ4D python3 -B tools/disassemble_logic.py --limit 80 | rg -n "load_sound|start_sound|stop_sound|sound"`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest tests.test_disassemble_logic_tables tests.test_game_census tests.test_agi_resources`
- `mdbook build docs`
- `git diff --check`
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests`
- `find tests tools -type d -name __pycache__ -print`
- `rm -rf tests/__pycache__ tools/__pycache__`

Observations:

- KQ4D `DMDIR` has header offsets `0x0008`, `0x00f8`, `0x01e5`, and `0x02d5`.
- The KQ4D sound section contains clean v3 records at sound indices `70..79`.
- Later present-looking sound-section triples often point into compressed data
  rather than to `12 34` volume record headers.
- The old `tools/disassemble_logic.py` v3 path hard-coded GR table bases
  `0x0440` and `0x0762`, so KQ4D stats were decoded with the wrong operand
  table.
- The first 16 action-table argc/meta pairs form an exact signature at:
  - SQ2 `AGIDATA.OVL:0x061d`
  - GR `AGIDATA.OVL:0x0440`
  - KQ4D `AGIDATA.OVL:0x0620`
- The 19 structured condition-table argc/meta pairs form an exact signature at:
  - SQ2 `AGIDATA.OVL:0x08fd`
  - GR `AGIDATA.OVL:0x0762`
  - KQ4D `AGIDATA.OVL:0x0942`
- KQ4D has the same v3 action-table shape through opcode `0xb5`; the extra
  slots at `0xb0..0xb5` have the same operand metadata shape as GR.
- After table detection, KQ4D stats are coherent. Decoded KQ4D scripts use
  `load_sound`, `start_sound_with_flag`, and `stop_sound_or_clear_sound_state`,
  but only with sound resource numbers `70..79`.

Implementation:

- Added signature-based dispatch table detection to `tools/disassemble_logic.py`.
- Added `tests/test_disassemble_logic_tables.py` covering SQ2, GR, and KQ4D
  table bases.
- Updated resource, bytecode, version, symbolic-label, and progress docs to
  treat v3 action/condition table bases as build-specific associations.

Validation:

- `AGI_GAME_DIR=games/SQ2 python3 -B -m py_compile
  tools/disassemble_logic.py tests/test_disassemble_logic_tables.py
  tools/game_census.py tests/test_game_census.py` passed.
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest
  tests.test_disassemble_logic_tables tests.test_game_census
  tests.test_agi_resources` passed 16 tests.
- `mdbook build docs` passed.
- `git diff --check` passed.
- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests` passed
  307 tests.
- Removed the generated `tests/__pycache__` and `tools/__pycache__`
  directories after the full test run.
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/logic_opcode_evidence.py --check`
  passed.
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py --report
  build/compatibility-suite/local_game_census_dispatch_001.json` passed. The
  report records zero return codes for local unit tests, mdBook build, and the
  opcode-evidence freshness check.

Conclusion:

- KQ4D can now be used as a v3 logic-disassembly input. Its current scripts
  only reference the clean sound records, so later bad KQ4D sound-section
  triples remain out-of-model planning evidence until source inspection proves a
  valid script path can observe them.

## 2026-07-10: separate clean-room specification book

The project deliverable was clarified as a human-readable specification of
externally observable AGI behavior, not a replacement engine. The existing
`docs/` mdBook remains the reverse-engineering evidence record, including
disassembly and DOS implementation details. A separate `spec/` mdBook now
serves as the clean-room interface for an independent implementation team.

The specification starts with an explicit behavioral boundary and conformance
model. It excludes original addresses, registers, instruction sequences,
overlay organization, memory layout, and inferred source structure unless an
item itself has an externally observable effect. Evidence must first be
recorded here, then deliberately restated in `spec/` as a portable behavioral
contract.

The default compatibility manifest now builds both mdBooks. This keeps the
evidence record and the clean-room deliverable independently renderable as the
project evolves.

Initial validation found that the installed mdBook version does not accept the
newer `book.multilingual` configuration key. The unsupported key was removed;
it did not affect the specification content or directory structure.

Validation:

- `mdbook build spec` passed.
- `AGI_GAME_DIR=games/SQ2 python3 -B tools/compatibility_suite.py --report
  build/compatibility-suite/local_spec_split_001.json` passed all 307 local
  tests, built both mdBooks, and passed the opcode-evidence freshness check.
- `git diff --check` passed.

## 2026-07-10: first behavioral-specification promotion pass

The first substantive clean-room specification pass promoted evidence into
four implementation-independent chapters:

- version profiles for the currently promoted 2.936 and 3.002.149 behavior;
- split-v2 and combined-v3 resource container formats, including dictionary
  and picture-nibble expansion;
- portable scalar, logic, resource, object, inventory, graphics, and cycle
  state; and
- sound resource parsing, countdown scheduling, completion flags, channel
  participation, PC-speaker divisor output, and four-channel tone/silence
  output.

No original addresses, symbolic machine-code labels, disassembly commands,
local paths, or test-harness references were copied into the substantive
chapters. A new structural test verifies mdBook summary targets and rejects
evidence-only terminology in future substantive spec chapters.

The four-channel attenuation-envelope contract was intentionally not promoted
as complete. The evidence records that channels 0 through 2 reset their
envelope index on each event while channel 3 preserves it, but the complete
portable initialization/transition contract still needs a focused source pass.
The spec states this limitation rather than filling the gap by inference.

A direct scan of all 468 readable dictionary-compressed Gold Rush records found
initial 9-bit code `0x100` in every case. The valid v3 dictionary stream contract
therefore requires a reset code at the beginning, removing ambiguity around
decoder startup state.

The next specification pass added logic payload/message framing, message XOR
decoding, main-stream jumps and conditional blocks, AND/OR/NOT condition-list
semantics, all 19 valid 2.936 condition opcodes, and action opcodes
`0x00..0x20`. Room switching is stated as portable state transitions and
re-entry ordering rather than as cleanup routine calls. Picture load, prepare,
overlay, and show remain separate operations in the normative text because
their visibility distinction is observable.

Before validation, the nested-call return rule was checked directly against
the local instruction stream. This exposed a stale earlier statement in the
evidence chapters: ordinary opcode `0x00` returns the instruction pointer after
the terminator and does not clear the logic record's resume field. Therefore a
normally terminated callee returns to the caller's next action. Only an action
path that returns a zero continuation, such as room switching, propagates an
abort through `call_logic`. Both the evidence book and specification were
corrected before the chapter was promoted as validated.

The next action-catalog group promotes opcodes `0x21..0x64` using portable
object concepts rather than record offsets. It covers object activation and
position, view/loop/cel selection, priority and update partitions, horizon and
control gates, collision distance, four animation modes, targeted/approach/
random movement, rectangle bounds, inventory locations, and sound control.

The final action-catalog group promotes `0x65..0xaf` plus v3 slots
`0xb0..0xb5`. It preserves two unusual byte-stream effects: `0x95` consumes an
extra byte when tracing is already active, while runtime `0xaf` consumes no
operand despite table-driven scanners assigning it length one. The configured
message parameters used by `0x97`/`0x98` were later resolved from source as
row, column, and width overrides. A structural test now requires every accepted
v2 and v3 action opcode to appear in the specification.

Validation:

- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests` passed
  309 tests.
- `mdbook build docs` passed.
- `mdbook build spec` passed.
- `AGI_GAME_DIR=games/SQ2 python3 -B
  tools/logic_opcode_evidence.py --check` passed.
- `git diff --check` passed.

## 2026-07-10: picture-command specification promotion

The picture evidence was restated as a portable full-EGA behavioral contract
in `spec/src/picture_resources.md`. The chapter separates picture loading,
prepare-time clearing, overlay decoding, and visible presentation; specifies
the guarded data-reader versus raw-operand distinction; and covers every
command from `0xf0` through `0xfa` plus the `0xff` terminator.

Raster semantics are explicit rather than delegated to conventional graphics
primitives. The specification includes modulo-256 relative endpoints and line
error accumulators, the visual-first seed-fill connectivity rule, all eight
pattern row-word families and column masks, the seeded stipple transition, and
the pattern plotter's linear X-160 write into the next logical row. These are
all externally distinguishable for valid command streams.

The specification deliberately excludes truncated operands and unsupported
command-boundary bytes `0xfb..0xfe` as malformed-data behavior. A structural
test requires all valid picture commands and the terminator to remain present
in the chapter.

## 2026-07-10: view, object, input, and persistence specification promotion

The next clean-room promotion pass added four portable chapters:

- `spec/src/view_resources.md` for view offsets, row runs, mutable mirrored-cel
  orientation, baseline placement, transparent pixels, priority scanning, and
  preview strings;
- `spec/src/object_behavior.md` for lifecycle, placement, update cadence,
  direction-based loop selection, cel cycling, movement, crossing collision,
  footprint-control acceptance, target/approach/random motion, drawing order,
  and refresh;
- `spec/src/input_text_and_menus.md` for the dictionary file, string slots,
  parser normalization/results/matching, event types and mappings, text
  surfaces, inventory selection, and menu state; and
- `spec/src/session_and_persistence.md` for room transitions, resource replay,
  selector behavior, save framing, the v3 block transform, restore/restart,
  and process termination.

The object pass reopened source ranges before promotion. The disposable SQ2
image was regenerated with:

```text
python3 -B tools/decrypt_agi.py --game-dir games/SQ2 \
  --output build/cleanroom/AGI.decrypted.exe
```

Focused instruction reads covered the collision helper at image `0x4719`,
approach helper `0x0b36`, random-motion helper `0x3f5a`, target-motion helper
`0x1672`, and shared direction classifier `0x16ed`. The collision helper proves
that horizontal equality counts as overlap and that a vertical collision is
current-baseline equality or strict saved/current order reversal. The action
catalog was corrected accordingly: object reset action `0x21` also enables
update/cycling state and selects the later partition; movement-rectangle
membership is strict; and actions `0x40`/`0x41` gate the final footprint class
state rather than latching whether one class appeared anywhere.

The motion helpers prove these portable details:

- target/near classification uses strict bands, so equality with either
  threshold remains directional;
- random mode uses random value modulo 9 for direction and repeatedly samples
  modulo 51 until its countdown is at least 6;
- approach recovery chooses a nonzero modulo-9 direction, calculates half the
  center/baseline Manhattan distance plus one, and samples a delay no smaller
  than the step; and
- retry-delay subtraction uses byte arithmetic followed by a signed
  nonnegative branch.

`tools/agi_graphics.py` now contains deterministic source-model helpers for
those transitions. `tests/test_graphics_rendering.py` supplies random words
explicitly and checks strict threshold edges, random countdown rejection,
initial approach sentinel handling, stuck recovery, and retry-delay return to
direct movement.

The persistence promotion deliberately stops short of claiming arbitrary
binary save interchange. The 31-byte header, five little-endian
length-prefixed blocks, known profile lengths, signature checks, replay
language, control flow, and Gold Rush block-3 XOR key are specified. A complete
portable mapping for every byte within all five blocks remains the next major
serialization task.

Focused validation had three harmless false starts caused by stale guessed
module names: `tests.test_agi_graphics`, `tests.test_logic_opcode_evidence`, and
`tests.test_agi_input`. The actual modules are
`tests.test_graphics_rendering`, `tests.test_logic_doc_coverage`, and
`tests.test_input_model`. Corrected focused runs passed 68, 69, 75, 83, 90,
and finally 101 tests as the chapters accumulated.

Full validation after the complete promotion pass:

- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests` passed
  323 tests.
- `mdbook build docs` passed.
- `mdbook build spec` passed.
- `AGI_GAME_DIR=games/SQ2 python3 -B
  tools/logic_opcode_evidence.py --check` passed.
- `git diff --check` passed.

## 2026-07-10: profile 2.936 save-block mapping

The save-state work resumed with a byte-complete map rather than a list of only
recognized fields. A fresh static instruction listing was generated from the
disposable decrypted executable:

```text
ndisasm -b 16 -o 0 -e 512 build/cleanroom/AGI.decrypted.exe \
  > build/cleanroom/SQ2_AGI_image.ndisasm
```

The first saved block starts with the seven-byte signature area and continues
through all 256 variables, 32 packed-flag bytes, timer/horizon/movement globals,
the key map, string storage, text configuration, and replay checkpoint. Block
positions in the clean specification are relative to the block start; the
evidence-side source association is the contiguous range `0x0002..0x05e2`.

An absolute-data-reference scan plus focused reads of the string actions found
five unresolved ranges. All 11 local SQ2 saves agree on their current contents:

| Block-1 position | Size | Observed bytes |
| ---: | ---: | --- |
| `0x012d` | 2 | `00 00` |
| `0x013d` | 2 | `0f 00` |
| `0x01df` | 44 | all zero |
| `0x03eb` | 480 | all zero |
| `0x05d6` | 1 | zero |

The 960-byte range beginning at source address `0x020d` is exactly 24 groups
of 40 bytes, but that arithmetic alone is not a slot contract. The parser action
at image `0x750b` explicitly accepts only indexes below 12, and current local
logic resources use only the lower slots. The first 480 bytes are therefore
mapped as twelve script-visible string slots; the following 480 bytes remain an
opaque bank. String-copy actions can calculate beyond the lower bank without a
bounds check, but malformed/out-of-range script behavior is outside the valid
data model and is not evidence for 24 portable slots.

Block 2 has length `0x0387`, exactly 21 records times the already source-mapped
43-byte object stride. Its field map covers every byte without padding. The
restore routine at `code.restore.replay_resource_events` first preserves each
record's low X byte and flag word while caches/lists are reset. After resource
replay it restores X, replaces object byte `+0x02` with the object index, reloads
the selected view when available, and calls the normal view-binding path. That
path preserves valid selected loop/cel indexes while rebuilding payload, loop,
and cel pointers, loop/cel counts, width, and height. Active/list state is
rebuilt from the saved flags before the exact saved flag word is restored.
Consequently the serialized pointer-shaped words are compatibility tokens, not
portable object identity, and the event byte is normalized to object index on
successful restore. All 11 local saves already contain indexes `0..20` there.

Block 4 has length `0x00c8`, exactly 100 two-byte replay-pair slots. The active
pair count and checkpoint count are in block 1. Only the active prefix is replay
semantics; the remaining pairs are inactive capacity but still serialized.

The block-3 pass reopened `code.inventory.initialize_metadata_and_objects` at
image `0x0fa5`, the carried-item list builder at `0x3203`, and inventory actions
`0x5c..0x61`. The local 331-byte `OBJECT` file XOR-decodes with the already
source-derived repeating `Avis Durgan` key. Its decoded prefix is:

```text
78 00 14
```

The loader interprets the first word as the item-table byte size and the third
byte as the maximum drawable-object index. It advances the runtime inventory
root past that header, sets the item-table end to root plus `0x78`, records the
runtime/save length as file length minus 3, and allocates `(0x14 + 1)` object
records. This derives the observed structures rather than merely fitting them:

- 40 three-byte inventory entries occupy block-3 positions `0x0000..0x0077`;
- 21 drawable objects times 43 bytes produce block-2 length `0x0387`; and
- the remaining 208 block-3 bytes are the zero-terminated item-name pool.

Each inventory entry is `name_offset:u16le, location:u8`; name offsets are
relative to the runtime block. The current block has 40 entries, including 20
placeholder entries sharing the `?` string and 20 distinct later names. Across
all 11 local saves, only 11 location-byte positions vary. Every name offset and
all 208 name-pool bytes match the decoded metadata file exactly. The location
value `0xff` is the carried-item marker consumed by the inventory list builder.

Block 5 was resolved directly from `code.logic.serialize_resume_table` at image
`0x1364` and `code.logic.restore_resume_from_table` at `0x13a5`. The serializer
starts with `SI = 0x0977`, not the pointer stored there. It therefore emits a
four-byte pair from the static cache-shaped head before following its `+0x00`
next pointer through the linked logic records. Current state makes that leading
pair `(logic 0, offset 0)`. Each linked record contributes:

```text
logic_number:u16le = zero-extended record byte +0x02
resume_offset:u16le = word(+0x06) - word(+0x04)
```

After the last linked record, the serializer writes only `0xffff` into the next
record's first word. It includes all four bytes of that terminator record in the
returned block length, so the second word is ignored/stale rather than
necessarily initialized by this pass. All 11 local saves happen to contain zero
there. Their block lengths `16`, `20`, `24`, and `28` are exact multiples of
four and their nonterminal records begin with the static `(0,0)` head followed
by the cached logic-0 record and other cached logics.

The restore helper scans block 5 from the beginning for the first record whose
logic number matches a newly loaded cache record. On a match it sets the resume
pointer to the newly loaded bytecode-entry pointer plus the saved offset; on
`0xffff` it returns without changing the default entry pointer. Only resource
replay kind 0 calls this helper. The replay-pair sequence is therefore
authoritative for which logics are loaded, while block 5 only supplies relative
resume metadata. Corpus comparison confirms the two lists need not be equal:
some block-5 cache records have no replay load, and some replayed logic numbers
have no matching block-5 record and retain offset zero.

`tools/agi_save.py` now contains exhaustive maps/parsers for blocks 1 through 4
and the decoded metadata header that relates blocks 2 and 3. Region validation
rejects gaps, overlaps, duplicate names, nonpositive sizes, and wrong total
lengths. Tests cover all 1505 block-1 bytes, every field in each 43-byte object
record, the fixed 21-record count, all 328 inventory/name bytes, the 100 replay
pairs, the five unresolved block-1 ranges across all local saves, and the
object-index event-byte invariant. The block-5 parser additionally validates
four-byte alignment, byte-sized logic numbers, terminal placement, first-match
lookup, duplicate entries, and ignored terminator payload. All five observed
profile 2.936 save blocks now have byte-complete maps; the next specification
task is the subsystem/version conformance matrix.

## 2026-07-10: clean specification conformance matrix

`spec/src/conformance_matrix.md` now turns the accumulated chapter boundaries
into explicit claim guidance. It classifies the shared behavior of promoted
profiles, the known 2.936/3.002.149 variants, dimensions supplied by each
selected game's data, partially specified domains, and behavior outside the
current full-EGA target.

The matrix separates gameplay conformance from binary save interchange. The
2.936 save claim requires all five block maps, replay reconstruction,
first-match logic-resume lookup, and byte preservation for opaque block-1
ranges. The 3.002.149 gameplay variants are listed, but arbitrary binary save
interchange remains explicitly unavailable until its five blocks receive the
same portable field mapping. A structural test requires all matrix sections and
both profile claim statements to remain present.

Validation after the save mapping and matrix pass:

- `AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests` passed
  341 tests.
- `mdbook build docs` passed.
- `mdbook build spec` passed.
- `AGI_GAME_DIR=games/SQ2 python3 -B
  tools/logic_opcode_evidence.py --check` passed.
- `git diff --check` passed.

## 2026-07-10: Gold Rush v3 save XOR key correction

The GR v3 save-map pass reopened the save helper at image `0x07bc` after the
original-engine save block failed to decode to a plausible runtime block under
the previously modeled 59-byte key. The key observation is that helper `0x07bc`
loads `DI = 0x072c` and reads `[DI]`, so `0x072c` is a data-segment address.
Reading the same numeric offset from the main executable image had accidentally
sampled code bytes.

Local evidence:

- `games/GR/AGIDATA.OVL` contains zero-terminated ASCII `Avis Durgan` at offset
  `0x072c`.
- The original-engine encoded save-block prefix
  `c87769f82158e57363fb6f5dd6686f91457dca6606ac4011` decodes with repeating
  `Avis Durgan` to
  `8901008b011c9001049a011ca0011cb10108b80167c20167`.
- The decoded block matches the decoded GR `OBJECT` runtime payload, confirming
  the block transform rather than merely proving XOR round-trip behavior.

Implementation/test correction:

- `GR_V3_OBJECT_INVENTORY_XOR_KEY` is now `b"Avis Durgan"`.
- The focused tests assert the exact key, the 11-byte wrap point, and the
  original save prefix known vector. This prevents any arbitrary repeating XOR
  key from passing by self-inverse round-trip behavior alone.

## 2026-07-10: Gold Rush v3 save blocks 2-5 structure pass

After correcting the GR v3 block-3 transform, the generated original-engine
saves and decoded local metadata were rechecked for portable block dimensions.

Local reads:

- `games/GR/OBJECT`, decoded with repeating `Avis Durgan`.
- Generated original-engine saves under `build/gr-v3-behavior/`, including
  `GRSG_001.1`, `GRSG_restore_001.1`, and suite-generated signed/blank-prefix
  saves.

Observed metadata and save layout:

- Decoded `OBJECT` header:
  - item-table byte size `0x0189`;
  - maximum drawable object index `0x16` (`22`);
  - runtime inventory payload length `0x0713`.
- All checked generated GR saves have block lengths `1028`, `989`, `1811`,
  `100`, and `12`.
- Block 2 length `989` is exactly `23 * 43`, matching object indexes `0..22`
  and the already source-mapped object-record stride.
- Block 3 decodes with `gr_v3_object_inventory_save_xor()` to the decoded
  `OBJECT` runtime payload byte-for-byte. The decoded block contains 131
  three-byte inventory entries followed by a 1418-byte zero-terminated name
  pool.
- Block 4 length `100` is exactly 50 replay pairs.
- The observed block 5 payload is
  `00 00 00 00 00 00 00 00 ff ff 00 00`, matching the same four-byte
  logic-resume grammar used by the 2.936 profile: leading head record, cached
  logic-0 record, and terminator.

Implementation/test updates:

- `tools/agi_save.py` now exposes generic object-record, replay-pair,
  inventory-block, and decoded-object-metadata helpers, plus GR-specific
  constants/wrappers for the observed profile 3.002.149 dimensions.
- `tests/test_save_resources.py` now checks the GR `OBJECT` metadata dimensions
  when `games/GR` is present and checks the generated signed save dimensions
  when `build/gr-v3-behavior/GRSG_001.1` is present.

Conclusion:

- Blocks 2 through 5 of the observed Gold Rush v3 save state now have portable
  structure maps. Block 1 remains the outstanding byte-complete mapping task
  for profile 3.002.149 binary save interchange.

## 2026-07-10: Gold Rush v3 save block 1 structure pass

Goal: map the first observed profile 3.002.149 save block with the same
byte-complete discipline used for profile 2.936.

Source observations:

- GR save action `0x7d` at image `0x29e5` writes the first state block at
  image `0x2aba..0x2ac9`.
- The writer helper call receives:
  - file handle from `[bp-0xcc]`;
  - start address `0x0002`;
  - length `0x0406 - 0x0002 = 0x0404`.
- Therefore block 1 is exactly `DS:0x0002..0x0405`, serialized as 1028 bytes.
- The same action uses `[0x0141] * 2` for block 4 length; observed saves have
  `[0x0141] = 0x0032`, matching 50 replay pairs.

Mapped block-1 partition:

| Position | Size | Meaning |
| ---: | ---: | --- |
| `0x0000` | 7 | Signature prefix. |
| `0x0007` | 256 | Variables. |
| `0x0107` | 32 | Flags. |
| `0x0127` | 4 | Timer ticks. |
| `0x012b` | 2 | Horizon. |
| `0x012d` | 2 | Opaque word. |
| `0x012f` | 12 | Movement rectangle/coupling/prepared-picture fields. |
| `0x013b` | 2 | Movement rectangle enabled word. |
| `0x013d` | 2 | Opaque word, observed `0f 00`. |
| `0x013f` | 2 | Replay-pair capacity, observed `0x0032`. |
| `0x0141` | 2 | Active replay-pair count. |
| `0x0143` | 196 | Forty-nine four-byte key-map entries. |
| `0x0207` | 4 | Opaque gap before string slots. |
| `0x020b` | 480 | Twelve 40-byte string slots rooted at `DS:0x020d`. |
| `0x03eb` | 22 | Text/status/display/replay-checkpoint words and prompt byte. |
| `0x0401` | 2 | Menu interaction gate word at `DS:0x0403`. |
| `0x0403` | 1 | Key-release enqueue gate byte at `DS:0x0405`. |

The detailed clean spec table expands the grouped ranges above into individual
fields. The region map covers every byte exactly once and keeps four opaque
ranges explicit: `0x012d..0x012e`, `0x013d..0x013e`, `0x0207..0x020a`, and
`0x03f6`.

Implementation/test updates:

- `tools/agi_save.py` now defines `GR_V3_BLOCK1_REGIONS` and
  `split_gr_v3_block1(...)`.
- `tests/test_save_resources.py` validates full byte coverage, the expanded
  49-slot key map, twelve string slots, observed `GR\0` signature prefix,
  replay capacity `0x0032`, row defaults, menu gate, key-release gate, and
  explicit opaque ranges.

Conclusion:

- The observed Gold Rush profile 3.002.149 save state now has a byte-complete
  structural map for all five blocks. The remaining save-related work is to
  resolve whether the explicit opaque ranges change during valid execution and
  to repeat this process for other interpreter/game profiles when promoted.

## 2026-07-10: configured modal-message parameters

Goal: resolve the action `0x97`/`0x98` parameter meanings from source before
leaving text-window behavior as a partial clean-spec gap.

Source observations:

- SQ2 action `0x97` at image `0x1c54` reads an immediate message number and
  calls shared helper `0x1c96`.
- SQ2 action `0x98` at image `0x1c71` reads a variable number, fetches
  `var[arg0]` as the message number, and calls the same helper.
- Helper `0x1c96` reads three following bytes into:
  - `[0x0d0b]`;
  - `[0x0d0d]`;
  - `[0x0d09]`.
- If the third byte is zero, helper `0x1c96` stores `0x001e` in `[0x0d09]`
  before display.
- After the display path returns, helper `0x1c96` resets all three globals to
  `0xffff`.
- `code.text.display_message_window` at image `0x1d96` consumes those globals:
  - `[0x0d09]`, when not `0xffff`, overrides the maximum formatted text width;
  - `[0x0d0b]`, when not `0xffff`, overrides the computed message-window row;
  - `[0x0d0d]`, when not `0xffff`, overrides the computed message-window
    column.
- Without a row override, the helper centers vertically from the formatted line
  count and the current display text area; it then adds the display base row
  `[0x05dd]`.
- Without a column override, the helper centers horizontally with
  `(40 - formatted_line_width) / 2`.

Conclusion:

- The three configured-message operands are now resolved as one-shot
  row/column/width parameters. The remaining text presentation limitation is
  exact glyph bitmap selection for a target platform, not the meaning of
  actions `0x97` and `0x98`.
