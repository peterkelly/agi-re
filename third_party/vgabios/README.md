# VGABIOS 0.7a pristine binary

This directory contains the **unmodified** standard VGA option-ROM binary from
the official Plex86/Bochs LGPL VGABios 0.7a release. It is retained as the
reproducible input to `tools/setup_vgabios.py`; generated patched ROMs belong
under ignored `build/` and must not be committed.

## Files

- `vgabios-0.7a.bin`: pristine upstream standard-VGA option ROM.
- `COPYING`: upstream GNU Lesser General Public License, version 2.1.

## Provenance

- Project: Plex86/Bochs LGPL VGABios
- Version: 0.7a
- Binary release:
  `https://download-mirror.savannah.gnu.org/releases/vgabios/vgabios-0.7a.bin`
- Complete source release:
  `https://download-mirror.savannah.gnu.org/releases/vgabios/vgabios-0.7a.tgz`
- Binary size: 41,472 bytes
- Binary SHA-256:
  `cd9fdd6a789dcd22b8a6b3b152788d43238de49cce674cff57bdeb94580246c6`
- Source archive SHA-256:
  `9d24c33d4bfb7831e2069cf3644936a53ef3de21d467872b54ce2ea30881b865`

The patch source is maintained separately in
`tools/vgabios_int43_patch.asm`. The build tool checks the pristine binary's
complete digest and exact expected patch locations before producing the
derived option ROM.
