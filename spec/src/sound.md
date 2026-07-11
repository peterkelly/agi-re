# Sound Resources and Playback

This chapter defines the sound behavior shared by the promoted profiles.
Version 3 containers may compress the payload before loading; after expansion,
the sound payload has the format below.

## Payload format

A sound payload begins with four little-endian 16-bit offsets. Each offset is
relative to the beginning of the payload and identifies one channel stream.

| Bytes | Channel |
| ---: | --- |
| `0..1` | Channel 0. |
| `2..3` | Channel 1. |
| `4..5` | Channel 2. |
| `6..7` | Channel 3. |

Each channel is an independent sequence of events:

| Field | Size | Meaning |
| --- | ---: | --- |
| Duration | 2 bytes | Unsigned little-endian countdown until the next record. |
| Tone | 2 bytes | Device-profile tone value. |
| Control | 1 byte | Its low nibble is attenuation; `0x0f` is silent. |

Duration `0xffff` terminates the channel and has no following tone or control
field. A valid stream reaches a terminator without reading outside the payload.

## Logic operations

Sound is controlled by three action opcodes:

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0x62` | sound number | Load the sound resource. |
| `0x63` | sound number, completion flag | Stop any active sound, select the loaded sound, remember and clear the supplied flag, then begin playback. |
| `0x64` | none | Stop active playback. If a sound was active, silence it and set its remembered completion flag. |

Starting a sound requires that resource to have been loaded. Starting a new
sound first completes the stop behavior for the old active sound, including its
old completion flag, before installing and clearing the new completion flag.

## Tick schedule

Playback advances in sound ticks. Starting a sound gives every participating
channel a countdown of `1`, so its first event or terminator is consumed on
tick 1.

When an event is consumed, its duration becomes that channel's next 16-bit
countdown. The countdown decreases once per sound tick. The next record is
consumed when the countdown reaches its event-read point. Equivalently, if an
event is read at tick `T`, the following record is read at:

```text
T + duration                    when duration is nonzero
T + 65536                       when duration is zero
```

The zero case follows 16-bit countdown wraparound.

Playback completes naturally when every participating channel reaches its
terminator. Completion silences the selected sound profile, marks playback
inactive, and sets the remembered completion flag.

Flag `f9` is a playback gate. If it is clear at the beginning of an active
sound tick, playback stops and completes on that tick without consuming more
channel events.

## Channel profiles

The single-channel sound profile advances channel 0 only. The four-channel
profile advances channels 0 through 3 and completes at the latest terminator
among them. Channels that terminate earlier remain silent while the others
continue.

In profiles 2.411 and 2.440, device selector `0` selects the single-channel
profile and every nonzero value selects all four channels. In profiles 2.917,
2.936, 3.002.086, 3.002.102, and 3.002.149, selectors `0` and `8` select the
single-channel profile; other values select all four channels.

## PC-speaker output

The single-channel PC-speaker profile uses the event's attenuation low nibble
as its gate. Attenuation `0x0f` is silence. Any other value enables the tone
whose integer divisor is:

```text
12 * (((tone & 0x003f) << 4) + ((tone >> 8) & 0x000f))
```

Stopping or completing the sound disables the speaker. A conforming backend
does not need to reproduce the original hardware operations, but its note and
silence sequence must follow the same divisors and tick schedule.

## Four-channel command output

For the four-channel profile, a tone event emits the high byte of the tone
word. Profile 2.411 always emits the low byte as well. Every other promoted
profile emits the low byte unless the high byte has its top three bits set; in
that case, only the high byte is emitted.

Stopping or completing playback emits this silence sequence:

```text
9f bf df ff
```

Attenuation commands combine a channel selector with a low-nibble attenuation:

| Channel | Selector |
| ---: | ---: |
| 0 | `0x90` |
| 1 | `0xb0` |
| 2 | `0xd0` |
| 3 | `0xf0` |

### Profiles 2.411 and 2.440

The early profiles have no attenuation-envelope state. They emit an
attenuation command when consuming an event or channel terminator, but do not
change attenuation on intervening countdown ticks.

For a consumed event, add the runtime global attenuation adjustment to the
control byte's low nibble and clamp the result to `0x0f`. Preserve the control
byte's high channel-selector nibble and combine it with that result. There is no
additional device-2 adjustment. A terminator emits attenuation `0x0f` for its
channel.

### Profiles 2.917 and later

Each participating channel has three attenuation-envelope state fields:

| Field | Initial value when playback starts | Meaning |
| --- | ---: | --- |
| Base attenuation | Event-defined | The low nibble from the most recently consumed event, or `0x0f` after channel termination. |
| Envelope index | Disabled | The current position in the envelope table. |
| Envelope value | Unspecified until first envelope step | The last clamped envelope result. |

Playback start disables the envelope index for every channel. When a channel
consumes a new event, channels 0, 1, and 2 reset their envelope index to zero
before storing the event's base attenuation. Channel 3 preserves its current
envelope index across event boundaries. This channel-3 persistence is part of
the 2.936 profile.

On each attenuation output for a non-silent base attenuation, an enabled
envelope index consumes one byte from the default envelope table:

```text
fe fd fe ff 00 00 01 01 01 01 02 02 02 02 02 02
02 02 03 03 03 03 03 03 03 04 04 04 04 05 05 05
05 06 06 06 06 06 07 07 07 07 08 08 08 08 09 09
09 09 0a 0a 0a 0a 0b 0b 0b 0b 0b 0b 0c 0c 0c 0c
0c 0c 0d 80
```

Table byte `0x80` disables the envelope and copies the previous envelope value
into the base attenuation. Any other table byte is treated as an 8-bit signed
delta from the current event's base attenuation, not from the previous
envelope output. The result is clamped to `0..0x0f`, stored as the new envelope
value, and then used as the emitted attenuation for that output.

After envelope processing, the runtime global attenuation adjustment is added
and clamped to `0x0f`. The four-channel profile selected by device value `2`
then increases any non-silent attenuation below `8` by `2`. Finally, the
channel selector byte is combined with the low-nibble attenuation and emitted.

If the base attenuation is already `0x0f`, no envelope step, global
adjustment, or device-2 adjustment occurs; the channel emits its selector byte
combined with `0x0f`.

## Output boundary

Exact analog waveform synthesis is outside the specification. Compatibility is
defined by resource interpretation, participating channels, event order,
timing, tone values or divisors, attenuation command bytes, silence
transitions, active state, and completion flags.
