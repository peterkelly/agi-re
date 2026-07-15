#!/usr/bin/env python3
"""Clean-room helpers for SQ2 sound-like resources."""

from __future__ import annotations

from dataclasses import dataclass

from disassemble_logic import AGIDATA, SQ2, read_dir_entries, read_volume_payload, u16le


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


@dataclass(frozen=True)
class SoundAttenuationState:
    base_attenuation: int
    envelope_index: int
    envelope_value: int


@dataclass(frozen=True)
class SoundAttenuationOutput:
    port_byte: int
    state: SoundAttenuationState


@dataclass(frozen=True)
class SoundToneOutput:
    port_bytes: tuple[int, ...]
    pc_speaker_divisor: int | None
    pc_speaker_enabled: bool | None


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


def active_sound_channel_indices(
    hardware_selector: int,
    *,
    selector_8_is_pc_speaker: bool = True,
) -> tuple[int, ...]:
    """Return channel indices advanced by the source driver for a hardware mode."""

    if hardware_selector == 0 or (selector_8_is_pc_speaker and hardware_selector == 8):
        return (0,)
    return (0, 1, 2, 3)


def pc_speaker_divisor(tone_word: int) -> int:
    """Return the PIT divisor computed by the source PC-speaker path."""

    low_component = (tone_word & 0x3F) << 4
    high_component = (tone_word >> 8) & 0x0F
    return (low_component + high_component) * 12


def pc_speaker_event_enabled(event: SoundEvent) -> bool:
    """Return whether a source event leaves the PC speaker gate enabled."""

    return event.attenuation != 0x0F


def sound_tone_output(
    event: SoundEvent,
    *,
    hardware_selector: int = 2,
    selector_8_is_pc_speaker: bool = True,
    always_write_low_byte: bool = False,
) -> SoundToneOutput:
    """Model source helper 0x80f3 at the tone-output boundary."""

    if hardware_selector == 0 or (selector_8_is_pc_speaker and hardware_selector == 8):
        enabled = pc_speaker_event_enabled(event)
        divisor = pc_speaker_divisor(event.tone_word) if enabled else None
        return SoundToneOutput((), divisor, enabled)

    high = (event.tone_word >> 8) & 0xFF
    low = event.tone_word & 0xFF
    port_bytes = (
        (high, low)
        if always_write_low_byte or (high & 0xE0) != 0xE0
        else (high,)
    )
    return SoundToneOutput(port_bytes, None, None)


def sound_stop_silence_output(
    *,
    hardware_selector: int = 2,
    selector_8_is_pc_speaker: bool = True,
) -> SoundToneOutput:
    """Return the source stop-core silence output for a hardware selector."""

    if hardware_selector == 0 or (selector_8_is_pc_speaker and hardware_selector == 8):
        return SoundToneOutput((), None, False)
    return SoundToneOutput((0x9F, 0xBF, 0xDF, 0xFF), None, None)


def default_attenuation_envelope() -> tuple[int, ...]:
    """Return the source attenuation delta table including its 0x80 sentinel."""

    data = AGIDATA.read_bytes()
    pos = 0x17B8
    values: list[int] = []
    while True:
        value = data[pos]
        values.append(value)
        pos += 1
        if value == 0x80:
            return tuple(values)


def sound_channel_output_mask(channel_index: int) -> int:
    """Return the high-nibble channel mask used by the port-0xc0 path."""

    if not 0 <= channel_index < 4:
        raise ValueError("sound channel index must be 0..3")
    return AGIDATA.read_bytes()[0x17FC + channel_index * 2] & 0xF0


def signed_byte(value: int) -> int:
    value &= 0xFF
    return value - 0x100 if value & 0x80 else value


def early_sound_attenuation_output(
    control_byte: int,
    *,
    global_adjust: int = 0,
) -> int:
    """Return the pre-envelope 2.411/2.440 attenuation command byte."""

    attenuation = (control_byte & 0x0F) + (global_adjust & 0xFF)
    if attenuation > 0x0F:
        attenuation = 0x0F
    return (control_byte & 0xF0) | attenuation


def early_20xx_device2_control_adjust(control_byte: int, hardware_selector: int) -> int:
    """Apply the 2.089/2.230/2.272 device-2 pre-output adjustment."""

    output = control_byte & 0xFF
    if hardware_selector == 2 and (output & 0x90) == 0x90 and (output & 0x0F) < 8:
        output = (output & 0xF0) | ((output & 0x0F) + 3)
    return output


def sq1_2089_sound_control_output(
    control_byte: int,
    *,
    hardware_selector: int = 1,
) -> int:
    """Return the 2.089 four-channel control byte for a consumed event."""

    return early_20xx_device2_control_adjust(control_byte, hardware_selector)


def xmas_2272_sound_control_output(
    control_byte: int,
    *,
    global_adjust: int = 0,
    hardware_selector: int = 1,
) -> int:
    """Return the 2.272 whole-byte adjustment and signed-clamp result."""

    output = early_20xx_device2_control_adjust(control_byte, hardware_selector)
    output = (output + (global_adjust & 0xFF)) & 0xFF
    if signed_byte(output) > 0x0F:
        output = 0x0F
    return output


def sound_attenuation_output(
    channel_index: int,
    state: SoundAttenuationState,
    *,
    hardware_selector: int = 2,
    global_adjust: int = 0,
    envelope_table: tuple[int, ...] | None = None,
) -> SoundAttenuationOutput:
    """Model source helper 0x8162 for the non-PC-speaker port byte.

    The helper is called on event reads, countdown ticks, and channel
    termination.  It preserves the event's base attenuation while an envelope is
    active; the table value at ``envelope_index`` is a per-tick delta from that
    base, not a cumulative delta from the previous envelope value.
    """

    base_attenuation = state.base_attenuation & 0xFF
    envelope_index = state.envelope_index & 0xFFFF
    envelope_value = state.envelope_value & 0xFF
    output_attenuation = base_attenuation

    if output_attenuation != 0x0F:
        if envelope_index != 0xFFFF:
            table = default_attenuation_envelope() if envelope_table is None else envelope_table
            if envelope_index >= len(table):
                raise ValueError("sound attenuation envelope index is outside the table")
            delta = table[envelope_index]
            if delta == 0x80:
                envelope_index = 0xFFFF
                base_attenuation = envelope_value
                output_attenuation = envelope_value
            else:
                envelope_index = (envelope_index + 1) & 0xFFFF
                candidate = (base_attenuation + delta) & 0xFF
                if candidate & 0x80:
                    candidate = 0
                if candidate > 0x0F:
                    candidate = 0x0F
                envelope_value = candidate
                output_attenuation = (candidate & 0x0F) + (global_adjust & 0xFF)
                if output_attenuation > 0x0F:
                    output_attenuation = 0x0F
        if hardware_selector == 2 and output_attenuation < 8:
            output_attenuation += 2

    port_byte = sound_channel_output_mask(channel_index) | (output_attenuation & 0x0F)
    return SoundAttenuationOutput(
        port_byte,
        SoundAttenuationState(base_attenuation, envelope_index, envelope_value),
    )


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
    selector_8_is_pc_speaker: bool = True,
) -> int:
    """Return the tick when the driver would stop and set the completion flag."""

    if not sound_flag_9_set:
        return 1
    schedules = {channel.index: schedule_sound_channel(channel) for channel in parse_sound(payload)}
    return max(
        schedules[index].terminator_tick
        for index in active_sound_channel_indices(
            hardware_selector,
            selector_8_is_pc_speaker=selector_8_is_pc_speaker,
        )
    )
