# Picture Resources and Rendering

This chapter defines the full-EGA picture command stream and its effect on the
logical graphics state. It applies after any container-level expansion
described in [Resource Containers](./resource_containers.md). The resulting
bytes are interpreted identically for the promoted 2.936 and 3.002.149
profiles.

## Picture lifecycle

Loading, preparing, overlaying, and showing a picture are distinct operations:

1. Loading makes the picture payload available but does not decode or display
   it.
2. Preparing resets every logical cell to visual color `15` and
   priority/control value `4`, resets the picture-command state, and decodes
   the selected payload.
3. Overlaying preserves the existing logical cells, resets the
   picture-command state, and decodes the selected payload over them.
4. Showing presents the current logical visual surface. Preparing or
   overlaying does not, by itself, require the visible display to change.

At the start of either decoding operation, both drawing channels are disabled
and the pattern mode is zero.

## Command stream

The decoder processes bytes until `0xff`. At command boundaries, bytes below
`0xf0` are ignored. Bytes `0xf0..0xfa` select commands. A valid command stream
does not use `0xfb..0xfe` at a command boundary.

Most command data is read by a guarded data reader. It accepts only bytes
`0x00..0xef`. A byte `0xf0` or greater terminates the current command without
being consumed, so the main scanner processes that byte next.

There are three exceptions. The operand immediately following `0xf0`, `0xf2`,
or `0xf9` is a raw byte: it is consumed even when its value is `0xf0` or
greater.

A coordinate pair consists of guarded X and Y bytes. X is clamped to `159` and
Y is clamped to `167`. If X is accepted but Y is a command byte, the partial
pair produces no drawing and the command byte remains pending.

## Drawing channels

Each logical cell contains a visual nibble and a priority/control nibble.
Commands independently enable or disable writes to those channels:

| Command | Operands | Effect |
| --- | --- | --- |
| `0xf0` | raw color byte | Enable visual drawing and select the operand's low nibble as the visual color. |
| `0xf1` | none | Disable visual drawing. |
| `0xf2` | raw value byte | Enable priority/control drawing and select the operand's low nibble as the priority/control value. |
| `0xf3` | none | Disable priority/control drawing. |

A pixel write replaces every enabled channel with its selected value and
preserves every disabled channel. If neither channel is enabled, drawing
commands leave the logical cells unchanged.

## Path commands

All line segments include both endpoints. Horizontal and vertical segments
visit every coordinate between their endpoints regardless of endpoint order.

| Command | Data sequence | Effect |
| --- | --- | --- |
| `0xf4` | initial X,Y; then Y,X,Y,X,... | Plot the initial point, then draw alternating vertical and horizontal segments. |
| `0xf5` | initial X,Y; then X,Y,X,Y,... | Plot the initial point, then draw alternating horizontal and vertical segments. |
| `0xf6` | initial X,Y; then zero or more X,Y pairs | Plot the initial point, then connect each previous point to the next absolute point. |
| `0xf7` | initial X,Y; then zero or more packed deltas | Plot the initial point, then connect each previous point to the endpoint encoded by the next delta byte. |

For a packed relative delta byte `b`:

- X magnitude is `(b & 0x70) >> 4`; bit `0x80` selects subtraction and a clear
  bit selects addition.
- Y magnitude is `b & 0x07`; bit `0x08` selects subtraction and a clear bit
  selects addition.
- Each addition or subtraction is performed modulo 256. The resulting X is
  then clamped down to `159` if it exceeds `159`; Y is similarly clamped down
  to `167`.

This is an upper clamp, not a signed lower clamp. For example, subtracting one
from X `0` first produces `255`, which is then clamped to X `159`.

### General line rasterization

Diagonal segments use the following exact integer algorithm. It is normative
because other common line algorithms choose different cells.

Let `dx` and `dy` be the absolute coordinate differences, and let `xstep` and
`ystep` be `+1` or `-1` toward the endpoint. The caller has already plotted
the start point.

- If `dx >= dy`, set `major = dx`, `xerror = 0`, and
  `yerror = floor(dx / 2)`.
- Otherwise set `major = dy`, `xerror = floor(dy / 2)`, and `yerror = 0`.
- Repeat `major` times:
  1. Set `yerror = (yerror + dy) modulo 256`. If `yerror >= major`, subtract
     `major` modulo 256 and advance Y by `ystep`.
  2. Set `xerror = (xerror + dx) modulo 256`. If `xerror >= major`, subtract
     `major` modulo 256 and advance X by `xstep`.
  3. Plot the resulting point.

For example, the segment from `(0,0)` to `(3,1)` plots `(0,0)`, `(1,0)`,
`(2,1)`, and `(3,1)`. The modulo-256 accumulators also affect long edge-to-edge
segments; they must not be replaced with wider arithmetic.

## Seed fill

Command `0xf8` reads zero or more coordinate-pair seeds. Each seed performs a
four-connected fill under these rules:

1. If visual drawing is enabled, connectivity is determined solely by the
   visual channel and the target value is visual color `15`.
2. Otherwise, if priority/control drawing is enabled, connectivity is
   determined by that channel and the target value is `4`.
3. If neither channel is enabled, the seed has no effect.
4. A visual fill whose selected visual value is `15`, or a priority/control
   fill whose selected value is `4`, has no effect.
5. The seed must have the target value in the selected connectivity channel.
   Otherwise it has no effect.
6. Every cell in the seed's four-connected target-valued region is written
   using the normal drawing-channel rule.

When both channels are enabled, visual values determine connectivity but both
channels are written. The traversal order and temporary storage strategy are
not observable for valid finite pictures; the final connected region is the
required result.

## Pattern mode and plots

Command `0xf9` consumes one raw mode byte. Its fields are:

- bits `0..2`: radius `r` in `0..7`;
- bit `0x10`: bypass the geometric pattern mask when set; and
- bit `0x20`: before each plotted coordinate, consume one guarded seed byte
  used for stippling.

Command `0xfa` repeatedly consumes an optional seed byte followed by an X,Y
pair. The seed is required for every pair when mode bit `0x20` is set. Each
complete pair performs one pattern plot.

### Plot geometry

For radius `r`, a plot examines `2r + 1` rows and `r + 1` columns. Its starting
coordinates are:

```text
doubled_x = clamp(2 * x - r, 0, 320 - 2 * r)
start_x   = floor(doubled_x / 2)
start_y   = clamp(y - r, 0, 167 - 2 * r)
```

Rows are visited from top to bottom and columns from left to right. Unless mode
bit `0x10` is set, a candidate exists only when the current row word has at
least one bit in common with the current column mask.

The column masks for columns `0..7` are:

```text
8000 2000 0800 0200 0080 0020 0008 0002
```

The row words for each radius are:

| Radius | Row words, top to bottom |
| ---: | --- |
| 0 | `8000` |
| 1 | `e000 e000 e000` |
| 2 | `7000 f800 f800 f800 7000` |
| 3 | `3800 7c00 fe00 fe00 fe00 7c00 3800` |
| 4 | `1c00 7f00 ff80 ff80 ff80 ff80 ff80 7f00 1c00` |
| 5 | `0e00 3f80 7fc0 7fc0 ffe0 ffe0 ffe0 7fc0 7fc0 3f80 1f00` |
| 6 | `0f80 3fe0 7ff0 7ff0 fff8 fff8 fff8 fff8 fff8 7ff0 7ff0 3fe0 0f80` |
| 7 | `07c0 1ff0 3ff8 7ffc 7ffc fffe fffe fffe fffe fffe 7ffc 7ffc 3ff8 1ff0 07c0` |

### Stipple sequence

When mode bit `0x20` is set, initialize an eight-bit state to `seed | 1` at the
start of each plot. For every candidate that passes the geometric mask, update
the state before deciding whether to write:

1. Save bit 0 as `carry` and shift the state right once.
2. If `carry` was set, XOR the state with `0xb8`.
3. Write the candidate only when state bit 0 is clear and state bit 1 is set.

The sequence is restarted from that plot's seed for every coordinate pair.

### Linear right-edge behavior

Pattern candidates are addressed as a linear array index
`row * 160 + column`, after adding the calculated starts. A candidate whose
calculated X is `160` therefore writes logical X `0` of the following row when
that linear index remains within the 160 by 168 surface. A candidate beyond the
end of the entire surface has no visible effect. Implementations using a
two-dimensional pixel API must reproduce this result rather than clipping each
pattern candidate at X `159`.

Every accepted pattern candidate uses the normal drawing-channel write rule.

## Valid-data boundary

This chapter specifies complete command streams ending in `0xff`, with complete
raw operands, coordinate pairs, and pattern seed/coordinate groups. Resource
truncation and unsupported command bytes `0xfb..0xfe` are malformed-data
behavior and are outside the conformance target.
