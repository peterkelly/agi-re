# AGI reverse engineering

[![docs](https://img.shields.io/badge/docs-online-blue)](https://peterkelly.github.io/agi-re/)

Sierra On-Line's [Adventure Game Interpreter (AGI)](https://en.wikipedia.org/wiki/Adventure_Game_Interpreter)
is the 1980s adventure-game system behind early *King's Quest*, *Space Quest*,
*Leisure Suit Larry*, and related titles. An AGI game combines an interpreter
with data-driven `LOGIC` scripts, vector-drawn `PICTURE` resources, animated
`VIEW` loops and cels, `WORDS.TOK` vocabulary, `OBJECT` inventory data, sound,
and saved-game state.

This repository asks a practical question: **what must a compatible AGI engine
actually do?** It examines original DOS interpreters and game resources to
recover their externally observable behavior, including differences between
interpreter versions. The work covers the parts an AGI developer would expect:
v2 and v3 directory/volume formats, logic opcodes, picture drawing and
priority/control planes, view decoding and mirroring, animated-object and ego
movement, text and parser behavior, menus, sound streams, and save/restore.

## What this project produces

The deliverable is **not a replacement engine**. It is a self-contained,
human-readable behavioral specification detailed enough for an independent
person or team to implement a compatible engine without seeing Sierra's
interpreter or this project's disassembly notes.

The repository contains two separate mdBooks:

- [`spec/`](spec/) is the implementation-facing behavioral specification. It
  defines inputs, game-visible state, state transitions, rendered and sound
  output, timing, persistence, and version-specific variants in portable terms.
  [Read the published specification](https://peterkelly.github.io/agi-re/spec/).
- [`docs/`](docs/) is the reverse-engineering evidence record. It contains the
  disassembly observations, addresses, commands, hypotheses, corrections, and
  original-engine experiments that support the specification.
  [Read the published evidence book](https://peterkelly.github.io/agi-re/docs/).

The scripts under `tools/` and the compatibility tests under `tests/` turn
those observations into reproducible checks. They support the specification;
they are not an unfinished replacement engine.

## Clean-room boundary

AGI-specific findings in this project are derived from locally held original
binaries and game data, disassembly, and controlled experiments. Existing AGI
documentation and source implementations are deliberately not used as
reverse-engineering evidence. Evidence and implementation details remain in
`docs/`; only portable, externally observable contracts are promoted to
`spec/`.

Original games and interpreter binaries are not distributed with this
repository. Local evidence copies belong under ignored `games/` directories or
another explicitly selected path outside version control.

## Requirements

- Python 3
- QEMU (`qemu-system-i386` and `qemu-img`)
- mtools (`mcopy`, `mmd`, `mdir`)
- mdBook for documentation checks
- NASM, used to build the QEMU VGA BIOS compatibility patch
- Optional reverse-engineering tools used by the notes: `ndisasm`, `rizin`,
  and `radare2`

Build both books with:

```bash
mdbook build docs
mdbook build spec
```

## Game directories

No game is selected by default. Pass a game directory explicitly:

```bash
python3 -B tools/disassemble_logic.py --game-dir games/SQ2 0
```

For repeated commands, set the environment variable instead:

```bash
export AGI_GAME_DIR=games/SQ2
python3 -B -m unittest discover -s tests
```

Future runs can point at other private game copies in the same way, for example
`games/LSL1` or `games/KQ4`.

## FreeDOS image setup

The old generated `build/` directory and the old MS-DOS installer disk images
are not required. Build a private FreeDOS image from the
[official FreeDOS 1.4 LiteUSB distribution](https://www.freedos.org/download/):

```bash
python3 -B tools/setup_freedos_image.py --force
```

To also copy one local game onto the image for manual QEMU runs:

```bash
python3 -B tools/setup_freedos_image.py --force --copy-game --game-dir games/SQ2 --dos-game-dir SQ2
```

The script downloads `FD14-LiteUSB.zip`, checks its SHA-256, extracts the raw
source image, and constructs a new 1 GiB bootable raw disk at
`build/freedos/freedos.img`. The generated disk has a 1 MiB-aligned active
FAT16-LBA partition with 32 KiB clusters. The builder preserves the verified
FreeDOS MBR and partition boot code, reformats the enlarged filesystem, copies
the complete FreeDOS tree, detects the new partition offset for mtools, patches
the root boot scripts so QEMU lands at a DOS prompt, and builds the VGA BIOS
compatibility ROM described below.

Use `--image-size-mib N` to select another FAT16 size between 64 and 2048 MiB.
Use `--url` and `--sha256` to test a newer FreeDOS release when the official
stable download changes. Use `--skip-vgabios` only when intentionally testing
QEMU's bundled VGA firmware.

## Working with the image

Ask the setup script for the mtools image target. This includes the partition
offset, which may change if the FreeDOS image changes:

```bash
python3 -B tools/setup_freedos_image.py --print-mtools-image
```

List the root directory:

```bash
mdir -i "$(python3 -B tools/setup_freedos_image.py --print-mtools-image)" ::
```

Create a DOS directory and copy files into it:

```bash
mmd -i "$(python3 -B tools/setup_freedos_image.py --print-mtools-image)" ::/WORK
mcopy -o -i "$(python3 -B tools/setup_freedos_image.py --print-mtools-image)" path/to/file.dat ::/WORK
```

Copy a whole local game directory using the setup helper:

```bash
python3 -B tools/setup_freedos_image.py --force --copy-game --game-dir games/SQ2 --dos-game-dir SQ2
```

Copy every top-level private game directory into an already built image:

```bash
IMAGE=$(python3 -B tools/setup_freedos_image.py --print-mtools-image)
mcopy -s -o -i "$IMAGE" games/* ::/
```

Or copy selected files manually:

```bash
mmd -i "$(python3 -B tools/setup_freedos_image.py --print-mtools-image)" ::/SQ2
mcopy -o -i "$(python3 -B tools/setup_freedos_image.py --print-mtools-image)" games/SQ2/* ::/SQ2
```

Launch the generated image with QEMU:

```bash
qemu-system-i386 -m 16 -boot c \
  -drive file=build/freedos/freedos.img,format=raw,if=ide,index=0,media=disk \
  -vga none \
  -device VGA,romfile="$(pwd)/build/vgabios/vgabios-0.7a-int43.bin" \
  -display vnc=127.0.0.1:5 -monitor stdio
```

FreeDOS may print an `InitDiskWARNING` about CHS values while booting this
1 GiB image. The active partition is explicitly FAT16-LBA and extends beyond
legacy CHS cylinder capacity; the warning is informational in this QEMU
configuration. A successful boot reports a roughly 1023 MiB `C:` volume and
lands at `C:\>`.

The QEMU monitor accepts commands on stdin. Useful monitor commands:

```text
sendkey c
sendkey d
sendkey spc
sendkey backslash
sendkey s
sendkey q
sendkey 2
sendkey ret
screendump build/freedos/screen.ppm
quit
```

If a game was copied to `C:\SQ2`, run it inside DOS by typing these commands
through VNC or by sending equivalent monitor `sendkey` events:

```bat
cd \SQ2
SIERRA
```

Convert a QEMU screenshot for viewing with ImageMagick:

```bash
magick build/freedos/screen.ppm build/freedos/screen.png
```

## QEMU VGA BIOS compatibility

QEMU's supplied VGA BIOS does not honor a temporary change to the BIOS
`INT 43h` font vector when its graphics-mode character service draws a glyph.
Some locally observed DOS interpreters depend on that standard BIOS interface
to draw inverse text. The result under an unmodified QEMU installation is a
dialog filled with repetitions of one glyph even though the game and the
8-by-8 font data are intact.

Build the local compatibility VGA BIOS with:

```bash
python3 -B tools/setup_vgabios.py --force
```

The script verifies the pristine LGPL VGABIOS 0.7a option ROM staged at
`third_party/vgabios/vgabios-0.7a.bin`, assembles the planar EGA glyph-fetch
patch, validates the exact binary patch locations, updates the option-ROM
checksum, and verifies the deterministic output digest. The generated ROM is
written under disposable `build/` output and is never committed.

The tracked binary is the unmodified official upstream release. Its license,
source-release URL, binary/source checksums, and provenance are recorded in
`third_party/vgabios/README.md`. The complete upstream source remains available
from the linked official Savannah archive.

Launch QEMU with the patched option ROM by disabling the default VGA device
and supplying an explicit standard VGA device. Use an absolute ROM path:

```bash
qemu-system-i386 -m 16 -boot c \
  -drive file=build/freedos/freedos.img,format=raw,if=ide,index=0,media=disk \
  -vga none \
  -device VGA,romfile="$(pwd)/build/vgabios/vgabios-0.7a-int43.bin" \
  -display vnc=127.0.0.1:5 -monitor stdio
```

This is an emulator-firmware compatibility workaround. It does not modify a
game directory, game executable, or the FreeDOS image, and `FIXAGI.COM` is not
needed with it. A utility that merely copies font bytes to `F000:FA6E` cannot
fix this case because the failure is in the VGA BIOS glyph-fetch path rather
than in the contents of that system-BIOS address.

The automated QEMU harnesses use this ROM automatically whenever it exists at
the generated default path. Set `AGI_VGABIOS=/path/to/another.bin` to compare a
different option ROM, or set `AGI_VGABIOS=default` to deliberately use QEMU's
bundled VGA BIOS.

## Validation

Run local checks from the repository root with an explicit game directory:

```bash
AGI_GAME_DIR=games/SQ2 python3 -B -m unittest discover -s tests
python3 -B tools/compatibility_suite.py --game-dir games/SQ2 --dry-run
mdbook build docs
mdbook build spec
```

QEMU compatibility commands also use `build/freedos/freedos.img` by default.
Override it with `AGI_DOS_IMAGE=/path/to/image.img` when needed.

`build/` is disposable generated output. `games/` is ignored because it may
contain copyrighted local game data.
