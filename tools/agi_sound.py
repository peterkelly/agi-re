#!/usr/bin/env python3
"""Clean-room helpers for SQ2 sound-like resources."""

from __future__ import annotations

from dataclasses import dataclass

from disassemble_logic import SQ2, read_dir_entries, read_volume_payload, u16le


@dataclass(frozen=True)
class SoundEvent:
    duration: int
    tone_word: int
    control_byte: int

    @property
    def attenuation(self) -> int:
        return self.control_byte & 0x0F


@dataclass(frozen=True)
class SoundChannel:
    index: int
    offset: int
    events: tuple[SoundEvent, ...]
    terminator_offset: int


@dataclass(frozen=True)
class SoundScheduledEvent:
    tick: int
    channel_index: int
    event_index: int
    event: SoundEvent


@dataclass(frozen=True)
class SoundChannelSchedule:
    channel_index: int
    events: tuple[SoundScheduledEvent, ...]
    terminator_tick: int


def sound_payload(sound_no: int) -> bytes:
    entries = read_dir_entries(SQ2 / "SNDDIR")
    entry = entries[sound_no]
    if entry is None:
        raise ValueError(f"sound resource {sound_no} is absent")
    return read_volume_payload(*entry)


def sound_channel_offsets(payload: bytes) -> tuple[int, int, int, int]:
    if len(payload) < 8:
        raise ValueError("sound payload is too short for four channel offsets")
    return tuple(u16le(payload, index * 2) for index in range(4))


def parse_sound_channel(payload: bytes, index: int) -> SoundChannel:
    offsets = sound_channel_offsets(payload)
    if not 0 <= index < 4:
        raise ValueError("sound channel index must be 0..3")
    pos = offsets[index]
    if pos >= len(payload):
        raise ValueError(f"sound channel {index} starts outside payload")
    events: list[SoundEvent] = []
    while True:
        if pos + 2 > len(payload):
            raise ValueError(f"sound channel {index} has no terminator")
        duration = u16le(payload, pos)
        pos += 2
        if duration == 0xFFFF:
            return SoundChannel(index, offsets[index], tuple(events), pos - 2)
        if pos + 3 > len(payload):
            raise ValueError(f"sound channel {index} has a truncated event")
        tone_word = u16le(payload, pos)
        control_byte = payload[pos + 2]
        pos += 3
        events.append(SoundEvent(duration, tone_word, control_byte))


def parse_sound(payload: bytes) -> tuple[SoundChannel, SoundChannel, SoundChannel, SoundChannel]:
    return tuple(parse_sound_channel(payload, index) for index in range(4))


def active_sound_channel_indices(hardware_selector: int) -> tuple[int, ...]:
    """Return channel indices advanced by the source driver for a hardware mode."""

    if hardware_selector in (0, 8):
        return (0,)
    return (0, 1, 2, 3)


def _countdown_delay(duration: int) -> int:
    return duration if duration != 0 else 0x10000


def schedule_sound_channel(channel: SoundChannel) -> SoundChannelSchedule:
    """Build the source-backed event-read schedule for one channel.

    Driver start initializes the countdown to 1, so the first event or
    terminator is read on the first tick. After an event is read, its duration
    is stored as the next 16-bit countdown value; a zero duration therefore
    wraps and delays the next read for 65536 ticks.
    """

    tick = 1
    scheduled: list[SoundScheduledEvent] = []
    for event_index, event in enumerate(channel.events):
        scheduled.append(SoundScheduledEvent(tick, channel.index, event_index, event))
        tick += _countdown_delay(event.duration)
    return SoundChannelSchedule(channel.index, tuple(scheduled), tick)


def sound_completion_tick(
    payload: bytes,
    *,
    hardware_selector: int = 2,
    sound_flag_9_set: bool = True,
) -> int:
    """Return the tick when the driver would stop and set the completion flag."""

    if not sound_flag_9_set:
        return 1
    schedules = {channel.index: schedule_sound_channel(channel) for channel in parse_sound(payload)}
    return max(schedules[index].terminator_tick for index in active_sound_channel_indices(hardware_selector))
