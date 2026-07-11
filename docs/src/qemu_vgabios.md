# QEMU VGA BIOS compatibility

## Purpose

The full 16-color EGA target uses QEMU as an observation environment. QEMU's
bundled VGA BIOS does not reproduce one BIOS font-vector behavior required by
the observed 2.936 interpreter, causing inverse text to appear as repetitions
of one glyph. This chapter documents the fault, the evidence distinguishing it
from game corruption, and the reproducible firmware workaround used by the
test harnesses.

The workaround patches emulator firmware only. It does not alter a game,
interpreter executable, resource, FreeDOS disk image, or clean-room behavioral
specification.

## Observable symptom

Ordinary white-on-black graphics text renders correctly. Black-on-white dialog
text instead contains repeated copies of one symbol. Pictures, views, palette,
window borders, and text placement remain correct.

The repeated symbol is significant: it is the VGA BIOS's compiled-in glyph for
the character code selected by the interpreter. It is not random memory and is
not evidence of damaged game data.

## Rejected causes

The investigation tested and rejected these explanations:

| Hypothesis | Evidence |
| --- | --- |
| The font at `F000:FA6E` is absent or corrupt. | The system BIOS already contains the correct 1024 bytes, matching the font returned by the VGA BIOS. |
| The interpreter cannot read the font because of i440FX shadow settings. | Read-only, write-only, and read/write PAM0 experiments did not change the result; live memory retained the correct bytes. |
| Copying the font after DOS boot repairs the problem. | A corrected and byte-verified copy still produced the repeated glyph. |
| The selected emulated VGA card is responsible. | QEMU standard VGA and Cirrus VGA reproduced the same behavior. |
| SeaVGABIOS alone is responsible. | The older LGPL VGABIOS 0.7a binary reproduced the failure too. |

The first `FIXAGI.COM` experiment also contained an independent bug: it changed
`DS` before reading its saved source offset and consequently copied unrelated
ROM bytes. Correcting the order and verifying the copy repaired the helper but
not the dialog, which separated that helper defect from the actual firmware
incompatibility.

## Decisive interpreter trace

For an inverse character, the interpreter performs this observable sequence at
the BIOS boundary:

1. Read the selected eight-byte glyph from the platform font.
2. Copy it to a scratch glyph and invert all eight bytes.
3. Temporarily redirect interrupt vector `43h` so character `80h` addresses
   that scratch glyph.
4. Ask `INT 10h/AH=09h` to draw character `80h` with the requested attribute.
5. Restore vector `43h`.

On the first dialog `S`, the source bytes were:

```text
78 cc e0 70 1c cc 78 00
```

The scratch bytes after inversion were:

```text
87 33 1f 8f e3 33 87 ff
```

Immediately before the BIOS call, vector `43h`, the eight-byte character
height, and character code `80h` resolved exactly to the inverted scratch
bytes. A hardware read watchpoint on those bytes did not trigger during the
BIOS call. The game-side data and vector were correct; the VGA BIOS did not
consult the live vector.

Inspection of LGPL VGABIOS 0.7a independently confirmed that its planar, CGA,
and linear graphics character renderers use private compiled-in font arrays.
The project's EGA-only correction therefore changes the planar renderer's
glyph-byte source while retaining its existing plane, mask, attribute,
destination, and pixel-writing behavior.

## Repository artifacts

| Path | Policy |
| --- | --- |
| `third_party/vgabios/vgabios-0.7a.bin` | Tracked pristine upstream binary; never modify in place. |
| `third_party/vgabios/COPYING` | Tracked upstream LGPL 2.1 license. |
| `third_party/vgabios/README.md` | Tracked provenance, source availability, and checksums. |
| `tools/vgabios_int43_patch.asm` | Tracked 16-bit patch source. |
| `tools/setup_vgabios.py` | Tracked deterministic validator and patch builder. |
| `build/vgabios/vgabios-0.7a-int43.bin` | Generated patched ROM; ignored and never committed. |

The pristine binary is 41,472 bytes with SHA-256:

```text
cd9fdd6a789dcd22b8a6b3b152788d43238de49cce674cff57bdeb94580246c6
```

The deterministic patched binary has SHA-256:

```text
cfbbc5e3f97cb40cbc315b68e1e52d4488e6e27a47b339452a6a4ebf00f01247
```

## Patch construction

The builder performs all of these checks and transformations:

1. Verify the complete pristine-ROM SHA-256.
2. Assemble `tools/vgabios_int43_patch.asm` with NASM and require exactly 44
   bytes.
3. Verify the original planar glyph-fetch instruction bytes at ROM offset
   `0x5251`.
4. Verify that the destination range beginning at `0xa1a4` is unused padding.
5. Replace the original glyph calculation with a near call and padding.
6. Install the patch routine at `0xa1a4`.
7. Recalculate the final option-ROM checksum byte so the complete byte sum is
   zero modulo 256.
8. Verify the complete generated-ROM SHA-256 shown above.

The inserted routine reads the current offset and segment from vector `43h`,
adds the selected character, character-height, and glyph-row offsets, fetches
the corresponding byte, applies the existing pixel mask, and returns to the
unchanged renderer.

## Reproduction

Build or verify the generated option ROM directly:

```bash
python3 -B tools/setup_vgabios.py --force
```

Normal FreeDOS environment setup performs the same step automatically:

```bash
python3 -B tools/setup_freedos_image.py --force
```

Use `--skip-vgabios` only for an intentional control environment using QEMU's
bundled VGA BIOS.

Launch QEMU manually with the generated ROM:

```bash
qemu-system-i386 -m 16 -boot c \
  -drive file=build/freedos/freedos.img,format=raw,if=ide,index=0,media=disk \
  -vga none \
  -device VGA,romfile="$(pwd)/build/vgabios/vgabios-0.7a-int43.bin" \
  -display cocoa -monitor stdio
```

The monitor/VNC variant replaces `-display cocoa` with:

```text
-display vnc=127.0.0.1:5
```

Shared QEMU harnesses automatically select the generated ROM when it exists.
Set `AGI_VGABIOS=/absolute/path/to/another.bin` to test another option ROM, or
set `AGI_VGABIOS=default` to force QEMU's bundled firmware for a control run.

## Validation

The corrected ROM was validated by booting FreeDOS, running the immutable SQ2
input without `FIXAGI.COM`, and advancing through the introduction, station
scene, and default-name prompt. The first playable-room dialog rendered its
complete black-on-white text with distinct glyphs.

Automated validation includes:

- complete pristine binary size and digest checks;
- exact call-site and unused-area guards;
- oversized-patch rejection;
- generated option-ROM checksum verification;
- deterministic final digest verification;
- QEMU argument selection, override, and explicit-default tests; and
- the complete local compatibility suite and both mdBooks.

If inverse text regresses, first run `python3 -B tools/setup_vgabios.py
--force` and compare the printed output digest with the value above. Then check
the QEMU command for both `-vga none` and the explicit `VGA,romfile=...`
device. Merely placing a ROM in `build/` does not make a manually constructed
QEMU command use it.

## License and source availability

VGABIOS 0.7a is redistributed under the GNU Lesser General Public License,
version 2.1. The repository stores the unmodified upstream binary and license.
`third_party/vgabios/README.md` identifies the official Savannah binary and
complete source archive and records SHA-256 values for both. The modified ROM
is generated locally from the tracked patch source and is intentionally not
stored in version control.
