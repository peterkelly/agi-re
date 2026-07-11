# View Resources and Cel Drawing

Views contain the animated images used by drawable objects and by transient
preview operations. This chapter defines the payload structure, cel pixels,
orientation behavior, and composition into the logical picture surface.

## Payload structure

All multi-byte offsets are unsigned little-endian values.

| Payload location | Meaning |
| --- | --- |
| bytes 0 and 1 | Reserved by the promoted profiles. |
| byte 2 | Number of loops. |
| bytes 3 and 4 | Offset of an embedded zero-terminated display string, relative to the payload start. |
| byte 5 onward | One two-byte loop offset per loop, relative to the payload start. |

Each loop begins with a one-byte cel count followed by one two-byte cel offset
per cel. A cel offset is relative to the start of its loop, not to the payload
start.

Each cel has this structure:

| Cel location | Meaning |
| --- | --- |
| byte 0 | Width in logical pixels. |
| byte 1 | Height in logical pixels. |
| byte 2 | Control byte: transparent color and orientation state. |
| byte 3 onward | Row-terminated run data. |

The low nibble of the control byte is the transparent color. Bit `0x80` marks
a cel whose row stream can be mirrored. Bits `0x70` hold the loop number whose
orientation the current row stream represents.

Loop and cel selection is zero-based. Selecting a loop or cel updates the
object's selected dimensions and decoded image state before it can be drawn.

## Row decoding

The cel contains exactly `height` encoded rows. Each row ends with byte `0`.
Every nonzero byte is one run:

- the high nibble is a color in `0..15`; and
- the low nibble is the run length in logical pixels.

Decoding starts at X `0` for every row. A run advances X by its length. If its
color is not the transparent color, its pixels receive that color; otherwise
the run only advances X. Unwritten pixels through the declared width are
transparent, including any implicit space after the encoded runs.

Pixels generated beyond the declared width are not part of the decoded cel.
The next source byte is still interpreted as part of the same row until the
zero terminator appears.

## Stateful mirroring

When control bit `0x80` is clear, selecting the cel does not change its row
stream. When it is set, compare control bits `0x70` with the selected loop
number masked to three bits:

- If they match, the row stream already has the requested orientation.
- If they differ, mirror every row and replace bits `0x70` with the selected
  loop number.

The orientation field and mirrored row stream are mutable loaded-resource
state. This matters when loop entries share the same cel data: a later
selection compares against the cel's current orientation, not necessarily its
original file bytes.

For each row, mirroring operates on runs as follows:

1. Find the first run whose color is not transparent.
2. If no such run exists, encode the mirrored row as only its zero terminator.
3. Discard explicit transparent runs before that first visible run, but include
   their lengths when calculating the row's total encoded width.
4. Compute the implicit trailing transparent width as
   `cel width - total encoded run length`.
5. Emit that implicit width as transparent runs before the mirrored visible
   data, splitting it into runs no longer than 15 pixels.
6. Emit every original run from the first visible run onward in reverse byte
   order, preserving each run byte unchanged.
7. Emit the zero row terminator.

Thus original leading transparent pixels become implicit trailing
transparency, while original implicit trailing transparency becomes explicit
leading runs. Explicit transparent runs after the first visible run participate
in the reversed sequence.

## Baseline placement

A cel is positioned by a left X coordinate and a baseline Y coordinate. Its
initial top row is:

```text
top = baseline_y - height + 1
```

The low-level composition operation applies these adjustments in order:

1. If `top < 0`, add `top` to left X, subtract `top` from baseline Y, and set
   top to zero. For example, top `-1` shifts left X one pixel left and baseline
   Y one pixel down; this is a position adjustment, not simple top clipping.
2. If `left + width > 160`, set left to `160 - width`.
3. During pixel composition, skip destination coordinates outside the 160 by
   168 logical surface. This clips a negative left edge and rows below the
   bottom edge.

Higher-level object placement normally searches for an in-bounds position
before invoking this operation. That search is specified with object behavior;
the rules above define the composition primitive itself.

## Transparency and priority composition

Transparent source pixels never modify the destination. Every nontransparent
source pixel is independently tested against the logical priority/control
surface. Rejection of one pixel does not reject the remainder of its run.

Let `p` be the drawing object's priority in `0..15`, and let `q` be the
destination cell's priority/control value:

1. If `q` is greater than `2`, use it directly as the comparison value.
2. If `q` is `0`, `1`, or `2`, scan downward in the same logical X column,
   starting one row below the destination. Use the first value greater than
   `2`.
3. If the scan reaches the bottom without finding such a value, use comparison
   value `0`.
4. Draw the pixel when the comparison value is less than or equal to `p`.
   Otherwise leave the destination unchanged.

An accepted pixel replaces the destination visual color with the cel color and
replaces its priority/control value with `p`. Equal priorities therefore allow
drawing. Even priority `0` can draw when a downward scan finds no value above
`2`.

## Embedded display string

View-preview operations use the header offset at bytes 3 and 4 as a pointer to
a zero-terminated string within the payload. Such an operation temporarily
shows loop 0, cel 0 centered at the bottom of the logical picture area at
priority `15`, displays the embedded string modally, and then restores the
previous picture contents. Whether the view remains loaded afterward depends
on whether it was already loaded before the preview.

## Profile applicability

All promoted profiles use the same expanded view payload and cel behavior.
Container storage may differ by profile, but container decoding finishes
before this chapter's rules are applied.

## Valid-data boundary

The conformance target requires offsets to select complete structures inside
the expanded payload, all declared rows to have terminators, and encoded widths
to permit the mirror calculation above. Out-of-range offsets, truncated rows,
and arithmetic underflow from an encoded row wider than its declared cel are
malformed-data behavior and are outside this specification.
