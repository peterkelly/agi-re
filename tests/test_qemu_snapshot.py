#!/usr/bin/env python3
"""Tests for QEMU snapshot batch helper plumbing."""

from __future__ import annotations

import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from qemu_snapshot import (  # noqa: E402
    SnapshotFixtureCase,
    detect_partition_offset,
    dos_key_name,
    fixture_input_files,
    mtools_image,
    qemu_vga_args,
    snapshot_chunk_path,
)


class QemuSnapshotTests(unittest.TestCase):
    def test_fixture_input_files_skip_generated_captures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir)
            (fixture / "VOL.0").write_bytes(b"")
            (fixture / "qemu_capture.ppm").write_bytes(b"")
            (fixture / "OBJECT").write_bytes(b"")
            self.assertEqual([path.name for path in fixture_input_files(fixture)], ["OBJECT", "VOL.0"])

    def test_mtools_image_uses_partition_offset(self) -> None:
        self.assertEqual(mtools_image(Path("disk.raw"), "32256"), "disk.raw@@32256")

    def test_mtools_image_omits_zero_partition_offset(self) -> None:
        self.assertEqual(mtools_image(Path("floppy.img"), "0"), "floppy.img")

    def test_mtools_image_auto_detects_first_mbr_partition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            image = Path(temp_dir) / "disk.raw"
            mbr = bytearray(512)
            mbr[0x1BE + 4] = 0x06
            mbr[0x1BE + 8 : 0x1BE + 12] = (2048).to_bytes(4, "little")
            mbr[0x1BE + 12 : 0x1BE + 16] = (4096).to_bytes(4, "little")
            mbr[510:512] = b"\x55\xaa"
            image.write_bytes(bytes(mbr))
            self.assertEqual(detect_partition_offset(image), "1048576")
            self.assertEqual(mtools_image(image), f"{image}@@1048576")

    def test_snapshot_case_defaults_to_no_post_launch_input(self) -> None:
        case = SnapshotFixtureCase("CASE", Path("fixture"), Path("capture.ppm"))
        self.assertEqual(case.launch_command, "SIERRA")
        self.assertEqual(case.post_launch_keys, "")
        self.assertEqual(case.post_launch_wait, 0.0)
        self.assertEqual(case.post_launch_key_delay, 0.03)
        self.assertEqual(case.post_launch_after_text_wait, 0.0)
        self.assertIsNone(case.post_launch_key_names)

    def test_snapshot_chunk_path_preserves_parent_and_suffix(self) -> None:
        self.assertEqual(
            snapshot_chunk_path(Path("build/snapshot/disk.qcow2"), 3),
            Path("build/snapshot/disk_chunk_003.qcow2"),
        )

    def test_dos_key_names_cover_monitor_specials(self) -> None:
        self.assertEqual(dos_key_name("\\"), "backslash")
        self.assertEqual(dos_key_name("-"), "minus")
        self.assertEqual(dos_key_name("\n"), "ret")
        self.assertEqual(dos_key_name(" "), "spc")
        self.assertEqual(dos_key_name(":"), "shift-semicolon")
        self.assertEqual(dos_key_name("."), "dot")

    def test_qemu_vga_args_use_generated_rom_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            rom = Path(temp_dir) / "vgabios.bin"
            rom.write_bytes(b"rom")
            with mock.patch.dict("os.environ", {"AGI_VGABIOS": str(rom)}):
                self.assertEqual(
                    qemu_vga_args(),
                    ["-vga", "none", "-device", f"VGA,romfile={rom.resolve()}"],
                )

    def test_qemu_vga_args_can_request_qemu_default(self) -> None:
        with mock.patch.dict("os.environ", {"AGI_VGABIOS": "default"}):
            self.assertEqual(qemu_vga_args(), [])

    def test_qemu_vga_args_reject_missing_explicit_rom(self) -> None:
        with mock.patch.dict("os.environ", {"AGI_VGABIOS": "/missing/vgabios.bin"}):
            with self.assertRaises(FileNotFoundError):
                qemu_vga_args()


if __name__ == "__main__":
    unittest.main()
