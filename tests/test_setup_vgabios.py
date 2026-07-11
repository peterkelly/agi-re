#!/usr/bin/env python3
"""Tests for the reproducible QEMU VGA BIOS compatibility patch."""

from __future__ import annotations

import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import setup_vgabios  # noqa: E402


class SetupVgabiosTests(unittest.TestCase):
    def source_rom(self) -> bytearray:
        source = bytearray(0xA200)
        start = setup_vgabios.CALL_SITE
        expected = setup_vgabios.ORIGINAL_CALL_SITE
        source[start : start + len(expected)] = expected
        return source

    def test_repository_contains_exact_pristine_vgabios(self) -> None:
        source = setup_vgabios.DEFAULT_SOURCE.read_bytes()
        self.assertEqual(len(source), 0xA200)
        self.assertEqual(setup_vgabios.sha256(source), setup_vgabios.VGABIOS_SHA256)

    def test_patch_rom_installs_near_call_and_updates_checksum(self) -> None:
        source = self.source_rom()
        patch = b"\x53\x5b\xc3"
        with mock.patch.object(
            setup_vgabios, "sha256", return_value=setup_vgabios.VGABIOS_SHA256
        ):
            result = setup_vgabios.patch_rom(bytes(source), patch)

        displacement = setup_vgabios.PATCH_OFFSET - (setup_vgabios.CALL_SITE + 3)
        expected_call = b"\xe8" + displacement.to_bytes(2, "little", signed=True)
        self.assertEqual(
            result[setup_vgabios.CALL_SITE : setup_vgabios.CALL_SITE + 3],
            expected_call,
        )
        self.assertEqual(
            result[
                setup_vgabios.CALL_SITE + 3 :
                setup_vgabios.CALL_SITE + len(setup_vgabios.ORIGINAL_CALL_SITE)
            ],
            b"\x90" * (len(setup_vgabios.ORIGINAL_CALL_SITE) - 3),
        )
        self.assertEqual(
            result[setup_vgabios.PATCH_OFFSET : setup_vgabios.PATCH_OFFSET + len(patch)],
            patch,
        )
        self.assertEqual(sum(result) & 0xFF, 0)

    def test_patch_rom_rejects_wrong_call_site(self) -> None:
        source = self.source_rom()
        source[setup_vgabios.CALL_SITE] ^= 0xFF
        with mock.patch.object(
            setup_vgabios, "sha256", return_value=setup_vgabios.VGABIOS_SHA256
        ):
            with self.assertRaisesRegex(SystemExit, "call site"):
                setup_vgabios.patch_rom(bytes(source), b"\xc3")

    def test_patch_rom_rejects_oversized_patch(self) -> None:
        source = self.source_rom()
        patch = b"\x90" * (setup_vgabios.ORIGINAL_PATCH_AREA_SIZE + 1)
        with mock.patch.object(
            setup_vgabios, "sha256", return_value=setup_vgabios.VGABIOS_SHA256
        ):
            with self.assertRaisesRegex(SystemExit, "bytes are available"):
                setup_vgabios.patch_rom(bytes(source), patch)

    @unittest.skipUnless(shutil.which("nasm"), "nasm is required for ROM build test")
    def test_tracked_source_builds_expected_patched_rom(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "patched.bin"
            path, built = setup_vgabios.build_patched_vgabios(output_path=output)
            self.assertTrue(built)
            self.assertEqual(path, output)
            self.assertEqual(
                setup_vgabios.sha256(output.read_bytes()), setup_vgabios.PATCHED_SHA256
            )


if __name__ == "__main__":
    unittest.main()
