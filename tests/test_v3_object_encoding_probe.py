#!/usr/bin/env python3
"""Tests for copied v3 inventory-metadata encoding fixtures."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_save import SQ2_OBJECT_FILE_XOR_KEY, xor_with_repeating_key  # noqa: E402
from v3_object_encoding_probe import build_fixtures  # noqa: E402


class V3ObjectEncodingProbeTests(unittest.TestCase):
    def test_build_fixtures_preserves_source_and_encodes_only_copy(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "build") as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            source.mkdir()
            (source / "AGI").write_bytes(b"engine")
            (source / "OBJECT").write_bytes(b"metadata")

            unchanged, encoded = build_fixtures(source, root / "fixtures")

            self.assertEqual((source / "OBJECT").read_bytes(), b"metadata")
            self.assertEqual((unchanged / "OBJECT").read_bytes(), b"metadata")
            self.assertEqual(
                (encoded / "OBJECT").read_bytes(),
                xor_with_repeating_key(b"metadata", SQ2_OBJECT_FILE_XOR_KEY),
            )


if __name__ == "__main__":
    unittest.main()
