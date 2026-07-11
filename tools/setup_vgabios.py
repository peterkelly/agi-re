#!/usr/bin/env python3
"""Build a QEMU VGA BIOS that honors the live INT 43h font vector."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VGABIOS_BINARY_URL = (
    "https://download-mirror.savannah.gnu.org/releases/vgabios/"
    "vgabios-0.7a.bin"
)
VGABIOS_SOURCE_URL = (
    "https://download-mirror.savannah.gnu.org/releases/vgabios/"
    "vgabios-0.7a.tgz"
)
VGABIOS_SHA256 = "cd9fdd6a789dcd22b8a6b3b152788d43238de49cce674cff57bdeb94580246c6"
VGABIOS_SOURCE_SHA256 = "9d24c33d4bfb7831e2069cf3644936a53ef3de21d467872b54ce2ea30881b865"
PATCHED_SHA256 = "cfbbc5e3f97cb40cbc315b68e1e52d4488e6e27a47b339452a6a4ebf00f01247"
DEFAULT_SOURCE = ROOT / "third_party/vgabios/vgabios-0.7a.bin"
DEFAULT_OUTPUT = ROOT / "build/vgabios/vgabios-0.7a-int43.bin"
PATCH_SOURCE = Path(__file__).with_name("vgabios_int43_patch.asm")

# VGABIOS 0.7a's planar graphics renderer reads its private font array here.
# Replace that calculation with a near call into unused option-ROM padding.
CALL_SITE = 0x5251
PATCH_OFFSET = 0xA1A4
ORIGINAL_CALL_SITE = bytes.fromhex(
    "8b46f40246ff80d4000346fa89c38a072246fd"
)
ORIGINAL_PATCH_AREA_SIZE = 0xA1FF - PATCH_OFFSET
PATCH_LENGTH = 44


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assemble_patch() -> bytes:
    if shutil.which("nasm") is None:
        raise SystemExit("required tool not found on PATH: nasm")
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "int43.bin"
        subprocess.run(
            ["nasm", "-f", "bin", "-o", str(output), str(PATCH_SOURCE)],
            check=True,
        )
        return output.read_bytes()


def patch_rom(source: bytes, patch: bytes) -> bytes:
    if sha256(source) != VGABIOS_SHA256:
        raise SystemExit(
            "source VGA BIOS checksum mismatch: "
            f"expected {VGABIOS_SHA256}, got {sha256(source)}"
        )
    if source[CALL_SITE : CALL_SITE + len(ORIGINAL_CALL_SITE)] != ORIGINAL_CALL_SITE:
        raise SystemExit("source VGA BIOS call site does not match VGABIOS 0.7a")
    if any(source[PATCH_OFFSET:0xA1FF]):
        raise SystemExit("source VGA BIOS patch area is not empty")
    if len(patch) > ORIGINAL_PATCH_AREA_SIZE:
        raise SystemExit(
            f"assembled patch is {len(patch)} bytes; only "
            f"{ORIGINAL_PATCH_AREA_SIZE} bytes are available"
        )

    result = bytearray(source)
    displacement = PATCH_OFFSET - (CALL_SITE + 3)
    call = b"\xe8" + displacement.to_bytes(2, "little", signed=True)
    result[CALL_SITE : CALL_SITE + len(ORIGINAL_CALL_SITE)] = (
        call + b"\x90" * (len(ORIGINAL_CALL_SITE) - len(call))
    )
    result[PATCH_OFFSET : PATCH_OFFSET + len(patch)] = patch

    # The final byte is the option-ROM checksum. Preserve the declared size and
    # choose a value that makes the byte sum zero modulo 256.
    result[-1] = 0
    result[-1] = (-sum(result)) & 0xFF
    if sum(result) & 0xFF:
        raise AssertionError("failed to update option-ROM checksum")
    return bytes(result)


def build_patched_vgabios(
    source_path: Path = DEFAULT_SOURCE,
    output_path: Path = DEFAULT_OUTPUT,
    force: bool = False,
) -> tuple[Path, bool]:
    """Create the deterministic patched ROM and return (path, was_built)."""
    if not source_path.is_file():
        raise SystemExit(f"pristine VGA BIOS is missing: {source_path}")
    if output_path.exists() and not force:
        actual_sha = sha256(output_path.read_bytes())
        if actual_sha != PATCHED_SHA256:
            raise SystemExit(
                f"existing patched VGA BIOS checksum mismatch: {output_path}: "
                f"expected {PATCHED_SHA256}, got {actual_sha}; pass --force to replace it"
            )
        return output_path, False

    patch = assemble_patch()
    if len(patch) != PATCH_LENGTH:
        raise SystemExit(f"assembled patch length changed: expected {PATCH_LENGTH}, got {len(patch)}")
    result = patch_rom(source_path.read_bytes(), patch)
    actual_sha = sha256(result)
    if actual_sha != PATCHED_SHA256:
        raise SystemExit(
            "patched VGA BIOS checksum mismatch: "
            f"expected {PATCHED_SHA256}, got {actual_sha}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_bytes(result)
    temporary.replace(output_path)
    return output_path, True


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Patch the repository's pristine LGPL VGABIOS 0.7a image so its "
            "EGA graphics glyph renderer reads the current INT 43h font vector."
        )
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output, built = build_patched_vgabios(args.source, args.output, args.force)
    print(f"source: {args.source}")
    print(f"source sha256: {VGABIOS_SHA256}")
    print(f"patch bytes: {PATCH_LENGTH}")
    print(f"output: {output}")
    print(f"output sha256: {PATCHED_SHA256}")
    print("status: rebuilt" if built else "status: already verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
