# Sound Resources and Playback

This chapter currently defines the sound behavior of the AGI 2.936 profile.
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

The device-selection values corresponding to the single-channel profile are
`0` and `8` in the 2.936 profile. Other observed device-selection values use
all four channels.

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
word. It also emits the low byte unless the high byte has its top three bits
set. In that case, only the high byte is emitted.

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

The exact four-channel attenuation-envelope initialization and transition
contract is not yet complete in this revision. Until that contract is added,
this chapter supports resource parsing, event timing, tone command order,
silence, and completion conformance, but not a claim of complete
four-channel amplitude-envelope equivalence.

## Output boundary

Exact analog waveform synthesis is outside the specification. Compatibility is
defined by resource interpretation, participating channels, event order,
timing, tone values or divisors, silence transitions, active state, and
completion flags.
