#!/usr/bin/env python3
"""Tests for read-only local game census tooling."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from game_census import build_census, census_game, extract_version_strings, format_markdown  # noqa: E402


def dir_entry(volume: int, offset: int) -> bytes:
    return bytes([((volume & 0x0F) << 4) | ((offset >> 16) & 0x0F), (offset >> 8) & 0xFF, offset & 0xFF])


def make_split_game(root: Path) -> Path:
    game = root / "SPLIT"
    game.mkdir()
    for name in ("LOGDIR", "PICDIR", "VIEWDIR", "SNDDIR"):
        (game / name).write_bytes(dir_entry(0, 0) + b"\xff\xff\xff")
    (game / "VOL.0").write_bytes(b"\x12\x34\x00\x03\x00abc")
    (game / "AGIDATA.OVL").write_bytes(b"header Version 2.000\x00tail")
    return game


def make_combined_game(root: Path) -> Path:
    game = root / "COMBINED"
    game.mkdir()
    directory = bytearray()
    directory.extend(bytes.fromhex("08 00 0b 00 0e 00 11 00"))
    directory.extend(dir_entry(0, 0))
    directory.extend(b"\xff\xff\xff" * 3)
    (game / "TSTDIR").write_bytes(bytes(directory))
    (game / "TSTVOL.0").write_bytes(b"\x12\x34\x00\x03\x00\x03\x00abc")
    (game / "AGIDATA.OVL").write_bytes(b"      Version 3.000.001\x00Press ENTER")
    return game


class GameCensusTests(unittest.TestCase):
    def test_extract_version_strings_from_agidata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game = make_split_game(Path(temp_dir))
            self.assertEqual(extract_version_strings(game), ["Version 2.000"])

    def test_census_split_directory_game(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game = make_split_game(Path(temp_dir))
            census = census_game(game)

        self.assertEqual(census["layout"], "v2_split")
        self.assertEqual(census["versions"], ["Version 2.000"])
        self.assertEqual(census["resources"]["logic"]["entries"], 2)
        self.assertEqual(census["resources"]["logic"]["present"], 1)
        self.assertEqual(census["transform_counts"], {"direct": 4})

    def test_census_identifies_directory_offset_beyond_volume(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game = make_split_game(Path(temp_dir))
            (game / "SNDDIR").write_bytes(dir_entry(0, 0x1234))
            census = census_game(game)

        self.assertEqual(
            census["resources"]["sound"]["record_errors"],
            [
                "sound 0: ResourceFormatError: directory offset 0x1234 "
                "is beyond volume 0 size 0x8"
            ],
        )

    def test_census_combined_directory_game(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game = make_combined_game(Path(temp_dir))
            census = census_game(game)

        self.assertEqual(census["layout"], "v3_combined")
        self.assertEqual(census["prefix"], "TST")
        self.assertEqual(census["section_offsets"]["logic"], "0x0008")
        self.assertEqual(census["resources"]["logic"]["present"], 1)
        self.assertEqual(census["transform_counts"], {"direct": 1})

    def test_combined_directory_tail_beyond_byte_resource_range_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game = make_combined_game(Path(temp_dir))
            with (game / "TSTDIR").open("ab") as directory:
                directory.write(dir_entry(0, 0) * 300)
            census = census_game(game)

        self.assertEqual(census["resources"]["sound"]["entries"], 256)
        self.assertEqual(census["resources"]["sound"]["present"], 255)

    def test_build_census_deduplicates_explicit_and_root_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            game = make_split_game(root)
            census = build_census([game], root)

        self.assertEqual([entry["name"] for entry in census["games"]], ["SPLIT"])

    def test_markdown_format_lists_resource_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            game = make_combined_game(Path(temp_dir))
            markdown = format_markdown({"games": [census_game(game)]})

        self.assertIn("| `COMBINED` | Version 3.000.001 | v3_combined | `TST` |", markdown)
        self.assertIn("logic: 1/1", markdown)


if __name__ == "__main__":
    unittest.main()
