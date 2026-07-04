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
