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
  - `0x00`: terminate current logic execution.
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
- Condition opcode `0x07` tests an immediate flag number; condition opcode
  `0x08` tests a flag number read from the byte-variable array rooted at
  `DS:0x0009`.
- Decoded variable actions:
  - `0x01`: saturated increment of `var[arg0]`.
  - `0x02`: saturated decrement of `var[arg0]`.
  - `0x03`: assign immediate to variable.
  - `0x04`: assign variable to variable.
  - `0x05`/`0x06`: add immediate or variable.
  - `0x07`/`0x08`: subtract immediate or variable.
  - `0x09`, `0x0a`, `0x0b`: indirect variable assignment forms.
  - `0xa5`/`0xa6`: multiply by immediate or variable, storing the low byte.
  - `0xa7`/`0xa8`: divide by immediate or variable, storing the 8-bit quotient.
- Decoded flag actions:
  - `0x0c`/`0x0d`/`0x0e`: set, clear, or toggle an immediate flag number.
  - `0x0f`/`0x10`/`0x11`: set, clear, or toggle a flag number read from a
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
- Action `0x14` loads a logic resource by immediate number via `0x117d`;
  action `0x15` does the same with a variable-sourced number.
- Action `0x16` invokes helper `0x12ae`, which locates or loads a logic
  resource and calls the main interpreter at `0x293c` on that logic, preserving
  the previous current logic pointer at `[0x0981]`; action `0x17` uses a
  variable-sourced logic number.
- Actions `0x1e` and `0x1f` call the view-like resource loader `0x39f7` with
  immediate or variable-sourced resource numbers.
- Action `0x62` calls the sound-like resource loader `0x5126`, which uses the
  sound directory accessor `0x440d`, generic volume reader `0x2e32`, and builds
  four internal pointers from the payload. Action `0x64` clears an active
  sound-like state through helper `0x5234`.
- Actions `0x21`, `0x22`, `0x3f`, `0x40`, `0x51`, `0x52`, and `0x93` update
  object/global state fields and object word flags. Field names remain
  provisional.
- Actions `0x7a` and `0x7b` fill globals `0x0eae..0x0eb3`, combine one operand
  into the high nibble of `0x0eb3`, then call helper `0x2d52`, which uses the
  object/resource helpers `0x3ae7`, `0x3bb7`, and `0x3ccb`.
- Action `0x82` stores a generated value in a variable within an inclusive
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
  `0x0e`; action `0x0e` remains the one-byte immediate flag toggle handler at
  `0x7492`.
- Refined linear bytecode listing behavior: action `0x00` ends the current
  execution path, but later bytes in the same logic code area can still be
  branch targets, so the local static disassembler keeps scanning after `0x00`.
- Decoded condition opcode `0x0e` as a variable-length parsed-input word
  sequence test. Its operand stream is a byte count followed by that many
  little-endian word IDs. Handler `0x095c` compares those word IDs with a
  parsed input-word buffer rooted at `DS:0x0c7b`, using word `[0x0ca3]` as the
  parsed-word count. Operand word `0x270f` terminates the test successfully,
  and operand word `0x0001` behaves as a wildcard for one parsed word. On full
  match the handler sets flag 4.
- Decoded action `0x65` as immediate message display and action `0x66` as
  variable-sourced message display. Both resolve the current logic message
  through helper `0x21f0` and pass the string pointer to display helper
  `0x1ce8`.
- Decoded actions `0x97` and `0x98` as configured message display variants.
  They set temporary globals `[0x0d0b]`, `[0x0d0d]`, and `[0x0d09]` from three
  operand bytes before display, then reset those globals to `0xffff`.
- Added more conservative object-action notes:
  - `0x24`: deactivates/removes an active object by clearing bit `0x0001` in
    `[object+0x25]` and calling list/graphics helpers.
  - `0x2f`: calls helper `0x3ccb` with an immediate operand and clears object
    bit `0x1000`.
  - `0x36`, `0x37`, `0x38`, and `0x39`: set, set-from-variable, clear, or read
    object byte `[+0x24]` with bit `0x0004` in `[+0x25]`.
  - `0x43` and `0x44`: set or clear object bit `0x0200`.
  - `0x58` and `0x59`: set or clear object bit `0x0002`.
- The local stats pass reports `LOGDIR` entry 141 as an invalid-looking target:
  it decodes to `VOL.0` offset `0x1ffff`, where no valid `12 34` volume header
  is present.
