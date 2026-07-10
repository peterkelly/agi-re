# Sound and audio

This chapter describes the interpreter-visible sound contract observed so far.
It is intentionally scoped to resource parsing, playback scheduling, completion
flags, and driver output at the port-write boundary. It does not attempt to
specify analog waveform synthesis beyond the bytes and PC-speaker divisor the
interpreter emits.

Evidence for this chapter comes from the SQ2 executable disassembly, the
symbolic labels in [Symbolic Labels](./symbolic_labels.md), local resource
parsing helpers in `tools/agi_sound.py`, and regression tests in
`tests/test_sound_resources.py`.

## Sound resource payloads

A loaded sound payload begins with four little-endian words. Each word is a
payload-relative offset to one channel stream.

| Bytes | Meaning |
| --- | --- |
| `0x00..0x01` | Channel 0 stream offset. |
| `0x02..0x03` | Channel 1 stream offset. |
| `0x04..0x05` | Channel 2 stream offset. |
| `0x06..0x07` | Channel 3 stream offset. |

Each channel stream is a sequence of duration/tone/control records terminated
by the duration word `0xffff`.

| Field | Size | Meaning |
| --- | --- | --- |
| Duration | 16-bit little-endian | The countdown value loaded after this event is consumed. The value `0xffff` is a terminator and has no following tone/control bytes. |
| Tone word | 16-bit little-endian | Encoded tone/control value consumed by the hardware driver path. |
| Control byte | 8-bit | The low nibble is the observed attenuation/control value. `0x0f` is the silent value on the PC-speaker path. |

The local SQ2 corpus has 49 present sound resources. All present SQ2 sound
payloads observed so far have four sorted, in-bounds channel offsets and a
first channel offset of `8`, immediately after the four-word header. All four
channels in every present payload parse to a `0xffff` terminator.

One concrete parser check uses sound 1:

| Property | Observed value |
| --- | --- |
| Channel offsets | `(8, 15, 22, 29)` |
| Channel 0 first duration | `0x0027` |
| Channel 0 first tone word | `0x8037` |
| Channel 0 first control byte | `0x9f` |
| Channel 0 terminator offset | `13` |

## Load and playback actions

The logic bytecode exposes sound through three action opcodes.

| Opcode | Symbolic name | Source-backed behavior |
| --- | --- | --- |
| `0x62` | `load_sound` | Loads and caches a sound-like resource. The cache record stores the resource number and four derived channel stream pointers. |
| `0x63` | `start_sound_with_flag` | Stops any currently active sound state, stores the supplied completion flag number, clears that flag, finds the loaded sound resource, and starts the driver. |
| `0x64` | `stop_sound_or_clear_sound_state` | Stops active sound state if present. When a sound was active, the stop path silences the driver and sets the stored completion flag. |

The current symbolic labels for the source paths are:

| Label | SQ2 image address | Role |
| --- | --- | --- |
| `code.sound.load_resource` | `0x5126` | Sound resource loader/cache path. |
| `code.sound.find_loaded_resource` | `0x50d8` | Lookup used before playback start. |
| `code.sound.start_with_flag` | `0x51d3` | Action handler for opcode `0x63`. |
| `code.sound.stop_or_clear_state` | `0x5234` | Shared stop helper used by opcode `0x64` and before starting another sound. |
| `code.sound.driver_start` | `0x7f96` | Low-level playback initialization. |
| `code.sound.driver_tick` | `0x801c` | Timer-driven playback tick. |
| `code.sound.driver_stop_core` | `0x80c1` | Shared low-level stop/completion helper. |

`start_sound_with_flag` requires the sound to have been loaded first. In the
current QEMU dispatch probes, a generated logic script calls `load_sound` before
`start_sound_with_flag`, then observes that `stop_sound_or_clear_sound_state`
sets the expected completion flag.

## Runtime playback state

Driver start copies the four cached channel pointers into runtime state and
initializes each channel countdown to `1`. That means the first event, or the
first channel terminator, is read on the first active sound tick.

Important runtime globals are:

| Label | SQ2 data address | Meaning |
| --- | --- | --- |
| `data.sound.active_state` | `0x1258` | Nonzero while sound playback is active. |
| `data.sound.completion_flag` | `0x126a` | The flag number set by the stop/completion path. |
| `data.sound.channel_stream_pointers` | `0x1788..0x178f` | Current stream pointers for the four channels. |
| `data.sound.channel_countdowns` | `0x1790..0x1797` | Per-channel countdown words. |
| `data.sound.channel_active_words` | `0x1798..0x179f` | Per-channel active markers. |
| `data.sound.channel_attenuation` | `0x17a8..0x17af` | Per-channel low-nibble attenuation/control values. |
| `data.sound.active_channel_byte_limit` | `0x1804` | Tick-loop limit: `2` means channel 0 only, `8` means channels 0 through 3. |
| `data.sound.remaining_active_channels` | `0x1806` | Decremented when active channels terminate. Zero triggers completion. |

At the start of each tick, the driver tests flag 9. If flag 9 is clear, the
driver stops immediately and sets the stored completion flag. This is modeled by
`sound_completion_tick(..., sound_flag_9_set=False) == 1` in the local tests.

The active channel set depends on the hardware selector at data `0x112e`:

| Hardware selector | Active channels |
| --- | --- |
| `0` | Channel 0 only. |
| `8` | Channel 0 only. |
| Other observed values | Channels 0, 1, 2, and 3. |

After an event is read, its duration word becomes the next countdown. A duration
of zero wraps through the 16-bit countdown behavior and delays the next record
read for 65,536 ticks. The local SQ2 corpus has no zero-duration sound events,
but the behavior is source-modeled and covered with a synthetic unit test.

Natural completion occurs when every active channel reaches a `0xffff`
terminator. The stop/completion helper clears active state, silences the driver,
and sets the stored completion flag.

## Tone output boundary

The source-backed model stops at the driver output boundary. A replacement
engine does not need to reproduce port I/O internally, but it does need to
produce the same interpreter-visible scheduling, silence, and completion
behavior for valid resources.

For hardware selectors `0` and `8`, the driver uses a PC-speaker-style path.
An event whose attenuation nibble is `0x0f` disables the speaker gate. Otherwise
the tone word is converted to a PIT divisor:

```text
divisor = 12 * (((tone_word & 0x3f) << 4) + ((tone_word >> 8) & 0x0f))
```

The source writes mode byte `0xb6` to port `0x43`, writes the divisor low byte
then high byte to port `0x42`, and sets bits `0` and `1` at port `0x61`.
Silence clears those port `0x61` bits.

For other observed selectors, tone output writes encoded bytes to port `0xc0`.
The driver writes the high tone byte first. It writes the low tone byte too
unless the high byte has top bits `0xe0`, in which case the high byte alone is
written. The stop path writes the four silence bytes:

```text
0x9f 0xbf 0xdf 0xff
```

## Attenuation and envelope boundary

The non-PC-speaker attenuation path combines a channel mask with a low-nibble
attenuation value.

| Channel | Output mask |
| --- | --- |
| 0 | `0x90` |
| 1 | `0xb0` |
| 2 | `0xd0` |
| 3 | `0xf0` |

The default attenuation envelope table starts with:

```text
0xfe 0xfd 0xfe 0xff 0x00 0x00 0x01 0x01 ...
```

and ends with sentinel byte `0x80`.

While an envelope is active, the table byte is interpreted as a signed delta
from the event's base attenuation, not as a cumulative delta from the previous
envelope value. The result clamps into the attenuation range `0..0x0f`. When
the envelope sentinel `0x80` is reached, the helper disables the envelope and
copies the current envelope value back into the base attenuation.

Selector `2` has one additional observed adjustment: after the normal envelope
and global adjustment steps, a non-silent output attenuation below `8` is
increased by `2`.

## Compatibility evidence

Local parser/model evidence is in `tests/test_sound_resources.py`. That suite
checks the present SQ2 sound corpus, event parsing, active-channel selection,
duration scheduling, flag-9 early stop behavior, PC-speaker divisor generation,
non-PC tone byte writes, stop silence bytes, channel masks, and attenuation
envelope semantics.

QEMU evidence currently covers dispatch and completion-flag behavior for the
logic opcodes that load, start, and stop sound. The current compatibility
chapter records the commands for:

- `sound_load_stop_dispatch_smoke`
- `sound_start_stop_dispatch_smoke`
- `sound_stop_sets_completion_flag`

Optional future dynamic work could validate natural completion timing against
the original engine, but the current implementation-facing model is already
source-backed at the interpreter and driver-output boundary. Analog waveform
synthesis remains outside the present clean-room compatibility target.
