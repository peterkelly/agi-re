#!/usr/bin/env python3
"""Tests for FreeDOS large-image geometry and partition construction."""

from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import setup_freedos_image  # noqa: E402


class SetupFreedosImageTests(unittest.TestCase):
    def source_mbr(self) -> bytes:
        mbr = bytearray(setup_freedos_image.SECTOR_SIZE)
        mbr[:446] = bytes((index * 17) & 0xFF for index in range(446))
        mbr[510:512] = b"\x55\xaa"
        return bytes(mbr)

    def test_partition_start_chs_matches_declared_geometry(self) -> None:
        self.assertEqual(
            setup_freedos_image.chs_address(setup_freedos_image.PARTITION_START_LBA),
            bytes((0, 33, 1)),
        )

    def test_chs_saturates_beyond_legacy_cylinder_limit(self) -> None:
        self.assertEqual(setup_freedos_image.chs_address(10_000_000), b"\xfe\xff\xff")

    def test_one_gib_mbr_contains_active_fat16_lba_partition(self) -> None:
        image_size = 1024 * 1024 * 1024
        source = self.source_mbr()
        result = setup_freedos_image.partitioned_mbr(source, image_size)
        entry = result[446:462]

        self.assertEqual(result[:446], source[:446])
        self.assertEqual(result[510:512], b"\x55\xaa")
        self.assertEqual(entry[0], 0x80)
        self.assertEqual(entry[4], setup_freedos_image.PARTITION_TYPE_FAT16_LBA)
        start_lba, sectors = struct.unpack("<II", entry[8:16])
        self.assertEqual(start_lba, setup_freedos_image.PARTITION_START_LBA)
        self.assertEqual(
            sectors,
            image_size // setup_freedos_image.SECTOR_SIZE
            - setup_freedos_image.PARTITION_START_LBA,
        )
        self.assertEqual(result[462:510], b"\x00" * 48)

    def test_partition_builder_rejects_invalid_source_mbr(self) -> None:
        with self.assertRaisesRegex(SystemExit, "valid MBR"):
            setup_freedos_image.partitioned_mbr(bytes(512), 1024 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
