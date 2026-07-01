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

