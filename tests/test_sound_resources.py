#!/usr/bin/env python3
"""Tests for clean-room sound resource parsing."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_sound import (  # noqa: E402
    SoundChannel,
    SoundEvent,
    active_sound_channel_indices,
    parse_sound,
    schedule_sound_channel,
    sound_channel_offsets,
    sound_completion_tick,
    sound_payload,
)
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

    def test_driver_channel_count_depends_on_hardware_selector(self) -> None:
        self.assertEqual(active_sound_channel_indices(0), (0,))
        self.assertEqual(active_sound_channel_indices(8), (0,))
        self.assertEqual(active_sound_channel_indices(2), (0, 1, 2, 3))

    def test_sound_one_schedule_matches_source_countdown_rule(self) -> None:
        payload = sound_payload(1)
        channels = parse_sound(payload)
        channel_0 = schedule_sound_channel(channels[0])
        channel_3 = schedule_sound_channel(channels[3])
        self.assertEqual([event.tick for event in channel_0.events], [1])
        self.assertEqual(channel_0.terminator_tick, 40)
        self.assertEqual([event.tick for event in channel_3.events], [1, 4, 7, 10, 13, 22, 25, 28, 31, 34])
        self.assertEqual(channel_3.terminator_tick, 40)
        self.assertEqual(sound_completion_tick(payload, hardware_selector=0), 40)
        self.assertEqual(sound_completion_tick(payload, hardware_selector=2), 40)

    def test_multi_channel_completion_depends_on_active_channels(self) -> None:
        payload = sound_payload(60)
        self.assertEqual(sound_completion_tick(payload, hardware_selector=0), 3403)
        self.assertEqual(sound_completion_tick(payload, hardware_selector=2), 3404)

    def test_zero_duration_wraps_countdown_before_next_record(self) -> None:
        channel = SoundChannel(0, 8, (SoundEvent(0, 0x1234, 0x90),), 13)
        schedule = schedule_sound_channel(channel)
        self.assertEqual([event.tick for event in schedule.events], [1])
        self.assertEqual(schedule.terminator_tick, 65537)

    def test_flag_9_clear_completes_on_first_tick(self) -> None:
        self.assertEqual(sound_completion_tick(sound_payload(60), sound_flag_9_set=False), 1)


if __name__ == "__main__":
    unittest.main()
