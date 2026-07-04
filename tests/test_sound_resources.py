#!/usr/bin/env python3
"""Tests for clean-room sound resource parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_sound import parse_sound, sound_channel_offsets, sound_payload  # noqa: E402
from disassemble_logic import SQ2, read_dir_entries, read_volume_payload  # noqa: E402


class SoundResourceTests(unittest.TestCase):
    def test_sound_directory_has_renderable_entries(self) -> None:
        present = [sound_no for sound_no, entry in enumerate(read_dir_entries(SQ2 / "SNDDIR")) if entry is not None]
        self.assertEqual(len(present), 49)
        self.assertIn(1, present)

    def test_all_sound_resources_have_four_channel_offsets(self) -> None:
        for sound_no, entry in enumerate(read_dir_entries(SQ2 / "SNDDIR")):
            if entry is None:
                continue
            with self.subTest(sound=sound_no):
                payload = read_volume_payload(*entry)
                offsets = sound_channel_offsets(payload)
                self.assertEqual(offsets[0], 8)
                self.assertEqual(tuple(sorted(offsets)), offsets)
                self.assertTrue(all(offset < len(payload) for offset in offsets))

    def test_all_sound_channels_parse_to_terminators(self) -> None:
        event_count = 0
        for sound_no, entry in enumerate(read_dir_entries(SQ2 / "SNDDIR")):
            if entry is None:
                continue
            with self.subTest(sound=sound_no):
                payload = read_volume_payload(*entry)
                channels = parse_sound(payload)
                self.assertEqual(len(channels), 4)
                for channel in channels:
                    self.assertLess(channel.terminator_offset, len(payload))
                    event_count += len(channel.events)
        self.assertGreater(event_count, 200)

    def test_sound_one_offsets_and_first_event_match_source_record_shape(self) -> None:
        payload = sound_payload(1)
        channels = parse_sound(payload)
        self.assertEqual(sound_channel_offsets(payload), (8, 15, 22, 29))
        self.assertEqual(channels[0].events[0].duration, 0x0027)
        self.assertEqual(channels[0].events[0].tone_word, 0x8037)
        self.assertEqual(channels[0].events[0].control_byte, 0x9F)
        self.assertEqual(channels[0].events[0].attenuation, 0x0F)
        self.assertEqual(channels[0].terminator_offset, 13)


if __name__ == "__main__":
    unittest.main()
