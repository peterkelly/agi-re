#!/usr/bin/env python3
"""Tests for QEMU snapshot batch helper plumbing."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from qemu_snapshot import SnapshotFixtureCase, dos_key_name, fixture_input_files, mtools_image  # noqa: E402


class QemuSnapshotTests(unittest.TestCase):
    def test_fixture_input_files_skip_generated_captures(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir)
            (fixture / "VOL.0").write_bytes(b"")
            (fixture / "qemu_capture.ppm").write_bytes(b"")
            (fixture / "OBJECT").write_bytes(b"")
            self.assertEqual([path.name for path in fixture_input_files(fixture)], ["OBJECT", "VOL.0"])

    def test_mtools_image_uses_partition_offset(self) -> None:
        self.assertEqual(mtools_image(Path("disk.raw")), "disk.raw@@32256")

    def test_snapshot_case_defaults_to_no_post_launch_input(self) -> None:
        case = SnapshotFixtureCase("CASE", Path("fixture"), Path("capture.ppm"))
        self.assertEqual(case.post_launch_keys, "")
        self.assertEqual(case.post_launch_wait, 0.0)

    def test_dos_key_names_cover_monitor_specials(self) -> None:
        self.assertEqual(dos_key_name("\\"), "backslash")
        self.assertEqual(dos_key_name("\n"), "ret")
        self.assertEqual(dos_key_name(" "), "spc")
        self.assertEqual(dos_key_name(":"), "shift-semicolon")
        self.assertEqual(dos_key_name("."), "dot")


if __name__ == "__main__":
    unittest.main()
