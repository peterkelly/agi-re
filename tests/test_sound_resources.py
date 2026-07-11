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
    SoundAttenuationState,
    SoundEvent,
    SoundToneOutput,
    active_sound_channel_indices,
    default_attenuation_envelope,
    early_sound_attenuation_output,
    pc_speaker_divisor,
    pc_speaker_event_enabled,
    parse_sound,
    schedule_sound_channel,
    sound_attenuation_output,
    sound_channel_offsets,
    sound_channel_output_mask,
    sound_completion_tick,
    sound_payload,
    sound_stop_silence_output,
    sound_tone_output,
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

    def test_pc_speaker_divisor_matches_source_shift_add(self) -> None:
        payload = sound_payload(1)
        event = parse_sound(payload)[0].events[0]
        self.assertEqual(pc_speaker_divisor(event.tone_word), 10560)
        self.assertFalse(pc_speaker_event_enabled(event))
        self.assertTrue(pc_speaker_event_enabled(SoundEvent(1, 0x1234, 0x90)))

    def test_tone_output_models_pc_speaker_and_non_pc_port_bytes(self) -> None:
        silent = sound_tone_output(SoundEvent(1, 0x8037, 0x9F), hardware_selector=0)
        self.assertEqual(silent, SoundToneOutput((), None, False))

        enabled = sound_tone_output(SoundEvent(1, 0x8037, 0x90), hardware_selector=0)
        self.assertEqual(enabled, SoundToneOutput((), 10560, True))

        non_pc = sound_tone_output(SoundEvent(1, 0x8037, 0x90), hardware_selector=2)
        self.assertEqual(non_pc, SoundToneOutput((0x80, 0x37), None, None))

        high_suppresses_low = sound_tone_output(SoundEvent(1, 0xE037, 0x90), hardware_selector=2)
        self.assertEqual(high_suppresses_low, SoundToneOutput((0xE0,), None, None))

    def test_early_tone_and_selector_variants_match_source_profiles(self) -> None:
        event = SoundEvent(1, 0xE037, 0x90)
        kq2 = sound_tone_output(
            event,
            hardware_selector=2,
            always_write_low_byte=True,
        )
        self.assertEqual(kq2, SoundToneOutput((0xE0, 0x37), None, None))

        selector_8 = sound_tone_output(
            event,
            hardware_selector=8,
            selector_8_is_pc_speaker=False,
        )
        self.assertEqual(selector_8, SoundToneOutput((0xE0,), None, None))

    def test_stop_silence_output_matches_source_stop_core(self) -> None:
        self.assertEqual(sound_stop_silence_output(hardware_selector=0), SoundToneOutput((), None, False))
        self.assertEqual(
            sound_stop_silence_output(hardware_selector=2),
            SoundToneOutput((0x9F, 0xBF, 0xDF, 0xFF), None, None),
        )

    def test_attenuation_envelope_and_channel_masks_match_source_tables(self) -> None:
        envelope = default_attenuation_envelope()
        self.assertEqual(envelope[:8], (0xFE, 0xFD, 0xFE, 0xFF, 0x00, 0x00, 0x01, 0x01))
        self.assertEqual(envelope[-1], 0x80)
        self.assertEqual(
            [sound_channel_output_mask(index) for index in range(4)],
            [0x90, 0xB0, 0xD0, 0xF0],
        )

    def test_attenuation_output_silence_and_selector_adjustment(self) -> None:
        silent = sound_attenuation_output(
            0,
            SoundAttenuationState(base_attenuation=0x0F, envelope_index=0xFFFF, envelope_value=0),
            hardware_selector=2,
        )
        self.assertEqual(silent.port_byte, 0x9F)

        adjusted = sound_attenuation_output(
            0,
            SoundAttenuationState(base_attenuation=3, envelope_index=0xFFFF, envelope_value=0),
            hardware_selector=2,
        )
        self.assertEqual(adjusted.port_byte, 0x95)

        unadjusted = sound_attenuation_output(
            0,
            SoundAttenuationState(base_attenuation=3, envelope_index=0xFFFF, envelope_value=0),
            hardware_selector=1,
        )
        self.assertEqual(unadjusted.port_byte, 0x93)

    def test_early_attenuation_has_no_envelope_or_selector_adjustment(self) -> None:
        self.assertEqual(early_sound_attenuation_output(0x93), 0x93)
        self.assertEqual(early_sound_attenuation_output(0x93, global_adjust=2), 0x95)
        self.assertEqual(early_sound_attenuation_output(0x9E, global_adjust=2), 0x9F)

    def test_attenuation_envelope_delta_is_from_base_value(self) -> None:
        first = sound_attenuation_output(
            0,
            SoundAttenuationState(base_attenuation=5, envelope_index=0, envelope_value=5),
            hardware_selector=1,
        )
        self.assertEqual(first.port_byte, 0x93)
        self.assertEqual(first.state, SoundAttenuationState(5, 1, 3))

        second = sound_attenuation_output(0, first.state, hardware_selector=1)
        self.assertEqual(second.port_byte, 0x92)
        self.assertEqual(second.state, SoundAttenuationState(5, 2, 2))

    def test_attenuation_envelope_clamps_and_terminates(self) -> None:
        negative = sound_attenuation_output(
            0,
            SoundAttenuationState(base_attenuation=1, envelope_index=0, envelope_value=1),
            hardware_selector=1,
        )
        self.assertEqual(negative.port_byte, 0x90)
        self.assertEqual(negative.state, SoundAttenuationState(1, 1, 0))

        positive = sound_attenuation_output(
            0,
            SoundAttenuationState(base_attenuation=14, envelope_index=0, envelope_value=14),
            hardware_selector=1,
            envelope_table=(2,),
        )
        self.assertEqual(positive.port_byte, 0x9F)
        self.assertEqual(positive.state, SoundAttenuationState(14, 1, 15))

        stopped = sound_attenuation_output(
            0,
            SoundAttenuationState(base_attenuation=6, envelope_index=0, envelope_value=4),
            hardware_selector=1,
            envelope_table=(0x80,),
        )
        self.assertEqual(stopped.port_byte, 0x94)
        self.assertEqual(stopped.state, SoundAttenuationState(4, 0xFFFF, 4))

    def test_driver_channel_count_depends_on_hardware_selector(self) -> None:
        self.assertEqual(active_sound_channel_indices(0), (0,))
        self.assertEqual(active_sound_channel_indices(8), (0,))
        self.assertEqual(active_sound_channel_indices(2), (0, 1, 2, 3))
        self.assertEqual(
            active_sound_channel_indices(8, selector_8_is_pc_speaker=False),
            (0, 1, 2, 3),
        )

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
