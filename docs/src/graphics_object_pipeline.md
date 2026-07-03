# Graphics and object pipeline

This page is a higher-level synthesis of the interpreter code paths that load
picture and view-like resources, bind view data to 43-byte object records, and
drive the drawing/update lists. Names remain provisional where the disassembly
shows a stable mechanism but not yet a final user-level concept.

## Resource caches feeding graphics

The resource loaders described in [Resource Files](./resource_files.md) feed two
graphics-facing caches:

| Resource | Loader | Cache lookup | Directory accessor | Payload use |
| --- | --- | --- | --- | --- |
| View-like | `0x39f7` | `0x3979` | `0x43a5` | Stored on object records and parsed into subresource pointers. |
| Picture-like | `0x4a3b` | `0x49e8` | `0x43d9` | Stored globally at `[0x1377]` before picture decoding. |

Both caches use small linked records whose byte at `+0x02` is the resource
number and whose word at `+0x03` is the loaded payload pointer. The view cache is
rooted at `[0x0ffa]`; the picture cache has a first static record at `0x120e`
and a linked tail/root variable at `[0x1214]`.

Several loaders and mutating object actions wrap their work with:

```text
0x6a54: clear/flush update lists rooted at 0x16ff and 0x1703
0x6a8e: rebuild and process those lists
```

That wrapper pattern is the strongest current evidence that resource changes,
picture changes, and object field changes all participate in one redraw/update
pipeline.

## Picture flow

Logic action `0x18` (`load_picture_var`) enters at `0x4a16`. It reads the picture-like resource
number from `var[arg0]` and calls `0x4a3b`.

`0x4a3b` first checks the picture cache through `0x49e8`. On a miss it:

1. Calls `0x6a54`.
2. Records pair `(2, picture_number)` through `0x70b1`.
3. Allocates or uses a 5-byte cache record.
4. Calls picture directory accessor `0x43d9`.
5. Calls the generic volume reader through `0x4a90 -> 0x2e32`.
6. Stores the returned payload pointer at cache record `+0x03`.
7. Calls `0x6a8e` on successful load.

Logic action `0x19` (`prepare_picture_var`) enters at `0x4aaa`, reads the picture number from a
variable, and calls `0x4acf`. That helper requires the picture to be cached,
stores the payload pointer in global word `[0x1377]`, and then calls:

```text
0x6a54
0x6445
0x6a8e
```

Afterward it clears word `[0x1216]`.

Logic action `0x1a` (`show_picture_like`) enters at `0x4b82`. It clears flag 15 through `0x74d0`,
calls `0x1f2b(0)`, calls display helper `0x5546`, and sets word `[0x1216] = 1`.
The exact screen-visible distinction between actions `0x19` (`prepare_picture_var`) and
`0x1a` (`show_picture_like`) still
needs live confirmation, but statically `0x19` decodes the selected picture
payload into the graphics buffer and `0x1a` performs a later display/finalize
step.

Logic action `0x1c` (`overlay_picture_var`) also selects a cached picture-like
payload into `[0x1377]`, but its helper path calls decoder entry `0x6440`
instead of `0x6445`. Since `0x6445` first clears/fills the graphics/control
buffer and then falls into `0x6440`, `0x1c` appears to be the picture path that
draws without that extra clear step.

## Picture decoder

Picture decoding starts at `0x6445` or `0x6440`. The `0x6445` entry performs an
extra setup call:

```text
ax = 0x4f4f
call 0x5257
```

Both entries then reach `0x644e`, which initializes drawing globals:

```text
[0x1369] = 0
[0x15ee] = 0
byte [0x136d] = 0xff
byte [0x136e] = 0xff
call 0x6475
if [0x1130] == 2: call 0x9899
```

The command scanner at `0x6475` walks the payload pointer in `[0x1377]`. It
reads bytes until `0xff`, ignores bytes below `0xf0`, and dispatches command
bytes `0xf0..0xfa` through the table at `0x15d6`.

The current SQ2 table at `DS:0x15d6` is:

```text
0xf0 -> 0x6494
0xf1 -> 0x64b5
0xf2 -> 0x64c7
0xf3 -> 0x64ed
0xf4 -> 0x6612
0xf5 -> 0x6603
0xf6 -> 0x6646
0xf7 -> 0x665e
0xf8 -> 0x66ab
0xf9 -> 0x6524
0xfa -> 0x64ff
```

A local scan of all 74 valid SQ2 picture payloads found these command-byte
counts. The scan treats bytes `>= 0xf0` as command/sentinel bytes; picture data
bytes are accepted by the coordinate readers only when they are `<= 0xef`.

| Byte | Count |
| ---: | ---: |
| `0xf0` | 4746 |
| `0xf1` | 309 |
| `0xf2` | 1018 |
| `0xf3` | 425 |
| `0xf6` | 7736 |
| `0xf7` | 9282 |
| `0xf8` | 1447 |
| `0xf9` | 22 |
| `0xfa` | 701 |
| `0xff` | 74 |

No local SQ2 picture payload currently uses command `0xf4` or `0xf5`, even
though both handlers are present in the interpreter dispatch table.

**`0xf0` (`set_visual_draw_nibble`)**: Handler `0x6494` reads one byte, passes
it through display-dependent mapper `0x5685`, stores `AL` in `[0x136b]`, enables
the low nibble of draw word `[0x1369]`, and updates the even/odd masks
`[0x136d]` and `[0x136e]`. This is the low-nibble drawing channel used for
visible picture color in the current model.

**`0xf1` (`disable_visual_draw_nibble`)**: Handler `0x64b5` clears the low
nibble of `[0x1369]` and opens the low nibble in both write masks.

**`0xf2` (`set_control_draw_nibble`)**: Handler `0x64c7` reads one byte, shifts
it into the high nibble, stores it in `[0x136c]`, enables the high nibble of
`[0x1369]`, and updates both masks. This is the high-nibble drawing channel
later consumed by object movement/control tests.

**`0xf3` (`disable_control_draw_nibble`)**: Handler `0x64ed` clears the high
nibble of `[0x1369]` and opens the high nibble in both write masks.

**`0xf4` (`draw_corner_path_y_first`)**: Handler `0x6612` reads an initial
coordinate pair through `0x66b8`, plots it, then reads a Y coordinate through
`0x66d4` and draws a vertical segment through `0x52ab`. It then alternates with
X-coordinate reads and horizontal segments through `0x526f`. A byte above
`0xef` terminates the command and is left for the main scanner as the next
picture command byte.

**`0xf5` (`draw_corner_path_x_first`)**: Handler `0x6603` is the same corner
path family, but after the initial plotted coordinate it reads X first and
draws a horizontal segment before alternating to vertical segments.

**`0xf6` (`draw_absolute_lines`)**: Handler `0x6646` reads and plots an initial
coordinate pair, then repeatedly reads absolute coordinate pairs and draws a
line from the previous point to the new point through `0x66e1`.

**`0xf7` (`draw_relative_lines`)**: Handler `0x665e` reads and plots an initial
coordinate pair, then consumes relative-step bytes while they are `<= 0xef`.
Bits `0x70` encode an X delta magnitude shifted down four bits, bit `0x80`
chooses subtraction instead of addition for X, bits `0x07` encode a Y delta
magnitude, and bit `0x08` chooses subtraction instead of addition for Y. Each
decoded endpoint is clamped to `x <= 0x9f` and `y <= 0xa7`, then connected with
`0x66e1`.

**`0xf8` (`seed_fill`)**: Handler `0x66ab` repeatedly reads coordinate pairs
and calls helper `0x533b`. The helper chooses the expansion test channel by
priority: if the low visual draw nibble is enabled, it expands through cells
whose low nibble is `0xf`; otherwise, if the high control draw nibble is
enabled, it expands through cells whose high nibble is `0x4`. A selected visual
fill value of `0xf` or selected control fill value of `0x4` exits without
filling. Once a cell is accepted, the write itself still goes through the normal
active draw byte and odd/even masks, so both nibbles may be updated when both
channels are active.

The implementation is a horizontal span fill rather than a naive recursive
four-neighbor fill. It writes the seed row left and right until the selected
test channel no longer matches the target, then scans adjacent rows above and
below, pushing deferred span state on the CPU stack when branching is needed.
The current local renderer models the same expansion result with an explicit
queue over four-neighbor cells, but uses the observed channel-priority and
normal-pixel-write rules.

**`0xf9` (`set_pattern_mode`)**: Handler `0x6524` stores the next byte in
`[0x15ee]`. The low three bits select one of eight pattern masks through the
pointer table at `DS:0x1619`; bit `0x10` bypasses one mask test in the patterned
plotter; bit `0x20` makes command `0xfa` consume an additional byte into
`[0x15f8]` before each patterned draw.

**`0xfa` (`pattern_plot`)**: Handler `0x64ff` repeatedly reads coordinate
pairs, then calls helper `0x652a`. That helper clamps a small rectangle around
the coordinate, selects a pattern pointer from `DS:0x1619`, and conditionally
plots pixels through `0x52f9` using pattern words and the bit masks rooted at
`DS:0x15f9`.

The helper's observed algorithm is:

1. `radius = [0x15ee] & 0x07`.
2. Pattern row words are read from the pointer table at `DS:0x1619`; the local
   table has `2 * radius + 1` row words for each radius.
3. The X start is clipped from `(x * 2 - radius) / 2`, with a right-side clamp
   derived from `0x140 - radius * 2`. The inner loop draws `radius + 1`
   columns.
4. The Y start is clipped from `y - radius`, with a lower clamp derived from
   `0xa7 - radius * 2`. The outer loop draws `2 * radius + 1` rows.
5. Unless mode bit `0x10` is set, the current row word must overlap the current
   column mask. The column masks read from `DS:0x15f9 + column * 4` are
   `0x8000`, `0x2000`, `0x0800`, `0x0200`, `0x0080`, `0x0020`, `0x0008`,
   and `0x0002`.
6. When mode bit `0x20` is set, the byte in `[0x15f8]` is ORed with `1` and
   then advanced for every candidate pixel: shift right once, XOR with `0xb8`
   if the shifted-out carry was set, then draw only when bit 0 is clear and
   bit 1 is set.

Coordinate readers are shared across the command handlers. Helper `0x66c1`
reads X into `AH`, accepts bytes `<= 0xef`, clamps values above `0x9f` down to
`0x9f`, and returns carry set on a command/sentinel byte. Helper `0x66d4` does
the same for Y in `AL`, clamping above `0xa7`. Helper `0x66b8` reads a full
X/Y pair by calling those two helpers.

Pixel writes converge on helper `0x52f9`. It treats word `[0x150b]` as
`AH = x`, `AL = y`, computes `DI = y * 0xa0 + x`, selects masks from
`[0x136d]` or `[0x136e]` depending on the low bit of Y, ORs the active draw
bits from `[0x1369]`, ANDs with the selected mask, and stores the result in the
graphics buffer segment pointed to by `[0x136f]`. Helpers `0x526f` and `0x52ab`
are optimized horizontal and vertical line drawers that use the same active
draw byte and masks while restoring `[0x150b]` to the endpoint when done.
QEMU fuzz case `base_019_pattern_edge_rectangle` confirms that this store is
linear for pattern plotting: when the pattern mask computes X `160`, the byte is
written as X `0` on the next scanline instead of being clipped. The final
would-be wrap past the `0xa0 * 0xa8` buffer is not visible.

General line helper `0x66e1` first checks for horizontal and vertical special
cases and jumps to those optimized helpers. For diagonal lines, the caller has
already plotted the start point. The helper computes absolute X/Y deltas and
signed step bytes, picks the larger delta as the loop count, initializes the
minor-axis accumulator to half of the major delta, and then repeatedly advances
the Y accumulator followed by the X accumulator. Each accumulator that reaches
the major delta subtracts the major delta and advances that coordinate by its
signed step. The accumulators are byte-sized CPU registers, so each addition
and subtraction wraps to 8 bits before the compare/next step. The resulting
point is then written through `0x52f9`.

A synthetic absolute line from `(0,0)` to `(3,1)` plots `(0,0)`, `(1,0)`,
`(2,1)`, and `(3,1)`; the same points are produced by the packed relative byte
`0x31`. A screen-scale edge case from `(159,167)` to `(0,0)` proves the
byte-width accumulator behavior: the drawn line includes `(25,0)` and `(25,1)`
and does not include `(0,0)`. This was first exposed by QEMU fuzz cases
`base_004_clamped_absolute` and `base_005_exact_edge_absolute`, both of which
matched the local renderer after the accumulator wrap was modeled.

The constants in these helpers repeatedly point to a `0xa0` by `0xa8` style
coordinate space. For example, vertical stepping adds `0xa0`, bounds checks use
`0xa0` for the right edge and `0xa7` for the lower edge, and object placement
uses the same limits.

## Graphics and control buffer helpers

The graphics buffer segment is stored in word `[0x136f]`. Several helpers treat
that segment as a `0xa0` by `0xa8` byte grid, or `0x6900` bytes total.

Helper `0x5257` fills the buffer with the word in `AX`, writing `0x3480` words.
Picture decoding enters through `0x6445` with `AX = 0x4f4f`, while helper
`0x5528` clears through the same routine with `AX = 0x4040` before calling the
display overlay and rebuilding the priority/control table.

Helper `0x5666` converts packed coordinates to a buffer offset:

```text
input:  AL = y, AH = x
output: DI = y * 0xa0 + x
```

Helper `0x56a2` initializes the table rooted at `0x127a`. It writes 168 bytes,
one per Y coordinate. The default pattern is:

```text
y 0..47    -> 4
y 48..59   -> 5
y 60..71   -> 6
...
y 156..167 -> 14
```

Helper `0x4cbb(value)` maps a priority/control value back toward a Y row. In
the default-table mode it scans downward through the `0x127a` table looking for
the first row whose table value is below the requested value. When word
`[0x124a]` is nonzero it instead uses the direct formula
`(value - 5) * 12 + 0x30`. The table can also be rebuilt by helper `0x4d10`
from data supplied through a pointer, so the formula path may be a fast path for
the default table.

Helper `0x57cf(object)` connects object drawing to the same buffer. It derives
a table value from object Y, uses that value to fill the low nibble of object
byte `+0x24` if the low nibble is zero, calls object overlay draw entry
`0x9db6`, and then writes the high nibble of `+0x24` around the object's
footprint in the buffer while preserving existing low nibbles. This looks like
the path that leaves object footprint/control information for later movement
tests, but the exact user-facing meaning of the high nibble remains open.

## View resources and object records

Object records are 43 bytes each. The object table begins at `[0x096b]` and ends
at `[0x096d]`. The interpreter computes object addresses by multiplying an
object index by `0x2b` and adding `[0x096b]`.

The current observed field map is:

| Offset | Observed use |
| ---: | --- |
| `+0x00` | Reload value for the per-cycle countdown byte at `+0x01`. |
| `+0x01` | Per-cycle countdown/tick divider byte; set by action `0x50` (`set_object_field_01_var`). |
| `+0x02` | Object grouping/event byte used by collision and boundary-event code. |
| `+0x03` | X-like coordinate. |
| `+0x05` | Y-like coordinate. |
| `+0x07` | View-like resource number selected by `0x3ae7`. |
| `+0x08` | View-like resource payload pointer. |
| `+0x0a` | Selected top-level subresource index. |
| `+0x0b` | Count copied from payload byte `[payload+0x02]`. |
| `+0x0c` | Pointer to a selected subresource table. |
| `+0x0e` | Selected derived subresource/frame index. |
| `+0x0f` | Count read from `*([object+0x0c])`. |
| `+0x10` | Pointer required before object activation; updated by `0x3d6a`. |
| `+0x12` | Copy of `+0x10` made during activation. |
| `+0x14` | Pointer to a render/update node. |
| `+0x16` | Previous or saved X-like coordinate. |
| `+0x18` | Previous or saved Y-like coordinate; used by object crossing tests. |
| `+0x1a` | Width word from selected subresource; action `0x85` (`display_object_diagnostics_var`) prints it as `xsize`. |
| `+0x1c` | Height word from selected subresource; action `0x85` (`display_object_diagnostics_var`) prints it as `ysize`. |
| `+0x1e` | Step-size byte used by multiple motion actions; action `0x85` (`display_object_diagnostics_var`) prints it as `stepsize`. |
| `+0x1f` | Frame-timer reload byte set by action `0x4c` (`set_object_field_1f_var`). |
| `+0x20` | Current frame-timer countdown byte. Action `0x4c` copies `var[arg1]` here and to `+0x1f`; `code.object.frame_timer_update` decrements it before calling `code.object.advance_frame_by_mode`. |
| `+0x21` | Direction-like byte used by the per-cycle movement pass and actions `0x56` (`set_object_field_21_var`)/`0x57` (`get_object_field_21`). |
| `+0x22` | Motion/control mode byte used by actions `0x4d..0x55` (`clear_object_fields_21_22` through `stop_motion_mode`); value 1 is random autonomous motion, value 2 approaches the first object entry until near, and value 3 is targeted movement started by `0x51` (`move_object_to`) or `0x52` (`move_object_to_var`). |
| `+0x23` | Frame-cycling mode byte used by actions `0x48..0x4b` (`set_object_field_23_mode0` through `set_object_field_23_mode2`). |
| `+0x24` | Priority/control byte; can be fixed by actions `0x36` (`set_object_field_24`)/`0x37` (`set_object_field_24_var`) or derived from Y. Action `0x85` (`display_object_diagnostics_var`) prints this byte as `pri`. |
| `+0x25` | Word-sized flag field. |
| `+0x27..0x2a` | Motion/control parameters. For targeted movement, `+0x27`/`+0x28` are target X/Y, `+0x29` is the saved step size, and `+0x2a` is the completion flag. For random mode, `+0x27` is a reseeded countdown. For approach-first-object mode, `+0x27` is the near threshold, `+0x28` is the completion flag, and `+0x29` is a delay/sentinel byte used after stuck recovery. |

Observed flag bits in object word `+0x25` include:

| Bit | Observed use |
| ---: | --- |
| `0x0001` | Object is active in the graphics/update pipeline. |
| `0x0004` | Use object byte `+0x24` as a fixed priority/control value instead of deriving one from Y. |
| `0x0008` | Exempts the object from the horizon-like clamp against `[0x012d]`. |
| `0x0010` | Partitions active objects between the two update-list roots. |
| `0x0020` | Enables `code.object.frame_timer_update` to decrement object byte `+0x20` and run `code.object.advance_frame_by_mode` when it reaches zero. |
| `0x0040` | Required by both update-list callbacks and by the movement pass. |
| `0x0080` | Set when the next step would cross a script-configured rectangle boundary. |
| `0x0200` | Excludes an object from object-object collision/crossing tests. |
| `0x0400` | Marks an object as just positioned or otherwise dirty; the movement pass skips applying direction deltas for that cycle and then clears the bit. |
| `0x1000` | One-callback startup delay for frame modes set by actions `0x49` and `0x4b`; `code.object.advance_frame_by_mode` clears this bit and returns without changing frames. |
| `0x4000` | Set by `0x0488` when an object remains at its saved position on an update cadence; later autonomous-direction helpers use it as a stationary/stuck marker. |

A QEMU logic-interpreter probe validates the visible effect of clearing bit
`0x0004`: after action `0x36` fixes an object's priority/control byte to `5`,
action `0x38` makes placement derive the priority from baseline Y again. At
baseline `80`, the derived priority is `7`, and the object draws over a
synthetic control-6 background.

`code.object.frame_timer_update` (`0x0563`) is a separate per-cycle scan over
active object records. It considers objects whose flag word has `(flags &
0x0051) == 0x0051`. If bit `0x0020` is set and byte `+0x20` is nonzero, it
decrements `+0x20`; when the decrement reaches zero it calls
`code.object.advance_frame_by_mode` (`0x48b3`) and reloads `+0x20` from
`+0x1f`.

`code.object.advance_frame_by_mode` interprets byte `+0x23` as a frame-cycling
mode. Before dispatch, it checks bit `0x1000`; if set, the helper clears that
bit and returns without changing the selected frame. Otherwise it starts from
object byte `+0x0e` and the last valid frame index `+0x0f - 1`:

| Mode | Setup action | Static behavior |
| ---: | --- | --- |
| `0` | `0x48` | Increment frame and wrap from the last frame to frame 0. |
| `1` | `0x49` | Increment toward the last frame. On the callback that reaches the last frame, set flag `+0x27`, clear bit `0x0020`, clear direction byte `+0x21`, and reset mode `+0x23` to 0. |
| `2` | `0x4b` | Decrement toward frame 0. If the decrement reaches frame 0, or if the object was already at frame 0, set flag `+0x27`, clear bit `0x0020`, clear direction byte `+0x21`, and reset mode `+0x23` to 0. |
| `3` | `0x4a` | Decrement frame and wrap from frame 0 to the last frame. |

After choosing the frame, the helper calls `code.object.select_frame` to update
the object record's selected frame pointer and dimensions.

QEMU movement batch `frame_timer_001` validates this model for the visible
mode-1 path: action `0x4c` seeds the countdown, action `0x49` starts forward
completion mode, and view 11/group 0 advances from frame 0 to frame 1. The same
batch confirms that action `0x46` suppresses the frame advance by clearing bit
`0x0020`, while action `0x47` restores it.

QEMU movement batch `frame_timer_modes_002` validates the other visible frame
modes against this static model. From view 11/group 0/frame 1, action `0x48`
mode 0 wraps forward to frame 0. From frame 1, action `0x4b` mode 2 reaches
frame 0 and stops. From frame 0, action `0x4a` mode 3 wraps backward to the
last frame, frame 1. The looping-mode fixtures use a small bytecode guard that
reads object field `+0x0e` with action `0x32` and clears bit `0x0020` once the
expected frame appears, making the final capture deterministic.

In addition to absolute positioning through actions `0x25` (`set_object_pos`),
`0x26` (`set_object_pos_var`), `0x93` (`set_object_pos_dirty`), and
`0x94` (`set_object_pos_dirty_var`), action `0x28` (`add_object_pos_from_vars`)
performs relative placement. It treats two variable
values as signed X/Y deltas, adds them to object fields `+0x03` and `+0x05`,
clamps underflow at zero, sets dirty bit `0x0400`, and then calls placement
helper `0x593a`. This is used in local SQ2 logic for short scripted nudges
before subsequent subresource or motion changes.

Helper `0x3ae7(object, view_number)` binds a loaded view-like resource to an
object:

1. Finds the cache record through `0x3979`; error code 3 is reported if absent.
2. Stores the payload pointer from cache record `+0x03` into object field
   `+0x08`.
3. Stores the resource number in object byte `+0x07`.
4. Copies payload byte `+0x02` into object byte `+0x0b`.
5. Calls `0x3bb7` with the requested or clamped top-level subresource index.

Helper `0x3bb7` validates that object `+0x08` is nonzero and that the requested
subresource is within object byte `+0x0b`. It then calls `0x3c1b` to select a
subresource table and `0x3ccb` to select a derived entry under that table.

Helper `0x3ccb` validates the selected derived entry against object byte
`+0x0f`, calls `0x3d6a` to update object byte `+0x0e`, pointer `+0x10`, and
size fields, then clamps coordinates against the `0xa0`/`0xa7` bounds. When it
adjusts coordinates it sets object flag bit `0x0400`.

## View payload layout

The view-like payload layout is now partially pinned down by helpers `0x3ae7`,
`0x3c1b`, `0x3ccb`, and `0x3d6a`, and by local inspection with
`tools/inspect_view.py`.

Observed structure:

```text
payload + 0x00: unknown byte
payload + 0x01: unknown byte
payload + 0x02: group count
payload + 0x03: u16 preview/display string offset, relative to payload base
payload + 0x05: u16 group_offset[group_count], relative to payload base

group + 0x00: frame count
group + 0x01: u16 frame_offset[frame_count], relative to group base

frame + 0x00: width
frame + 0x01: height
frame + 0x02: control byte
frame + 0x03: row-terminated encoded pixel data
```

The payload offset arithmetic is visible in the object helpers:

- `0x3ae7` copies `payload[0x02]` to object byte `+0x0b`.
- `0x5edb`, used by view-resource preview actions, reads
  `u16(payload + 0x03)` and displays `payload + that_offset` through `0x1ce8`.
- `0x3c1b` reads `u16(payload + 0x05 + selected_group * 2)`, adds the payload
  base, and stores the resulting group pointer in object word `+0x0c`.
- `0x3c1b` reads the first byte at the selected group pointer and stores it in
  object byte `+0x0f`.
- `0x3d6a` reads `u16(group + 0x01 + selected_frame * 2)`, adds the group
  pointer, stores the resulting frame pointer in object word `+0x10`, then
  copies frame bytes `+0x00` and `+0x01` into object width/height fields
  `+0x1a` and `+0x1c`.

Local payload samples match the same layout. For example, view 11 has payload
header `01 01 02 00 00`, so the observed group count is 2. Group 0 starts at
offset `0x09`, has 2 frames, and its first frame starts at `0x0e` with size
`20x5` and control byte `0x01`. A full local scan also found nonzero
preview/display string offsets in views 220 through 239; the first was view 220
with offset `0x0249` inside a 707-byte payload.

QEMU overlay probes now validate multiple selected offsets within view 11. Group
0 frame 1, group 1 frame 0, and group 1 frame 1 all matched the local renderer
in the 22-case object overlay batch, extending the earlier group 0 frame 0
fixture beyond the first frame table entry.

The object overlay draw routine at `0x9db6 -> 0x9e35` provides the current
model for frame data. The draw entry receives an object pointer, loads the
selected frame pointer from object `+0x10`, and computes the top-left buffer
cell from object X and baseline Y:

```text
left = object[+0x03]
top = object[+0x05] - frame.height + 1
```

The frame stream is row-oriented:

- Frame byte `+0x00` is width.
- Frame byte `+0x01` is row count/height.
- Frame byte `+0x02` low nibble is the transparent or skip color.
- Encoded row data begins at frame byte `+0x03`.
- A zero byte ends the current row.
- A nonzero byte encodes one run: high nibble is a color-like value and low
  nibble is the run length.
- If the run color equals the transparent nibble, drawing advances by the run
  length without writing.

When the draw routine does write a run, it stores the object priority/control
low nibble from object `+0x24` into the destination byte's high nibble and the
frame run color into the destination byte's low nibble. Existing high-nibble
buffer values also gate drawing. If the existing high nibble is greater than
`0x20`, the routine compares it with the object's priority/control nibble and
skips the pixel when the existing value is higher. If the existing high nibble
is `0x20` or lower, it scans downward in the same column until it finds a
higher control/priority value or reaches the lower buffer limit, then uses that
value for the same comparison. This ties object drawing to the high-nibble
control data produced by picture decoding.

QEMU probes using controlled synthetic pictures validate both priority-gate
branches. On the default cleared picture buffer, whose high nibble is `4`, an
object with priority `3` is hidden while priority `4` draws. On a synthetic
picture filled to control priority `6`, priority `5` is hidden while priority
`6` draws. A third pair writes control `2` at the object's destination row and
control `6` one row below; priority `5` is hidden and priority `6` draws,
confirming that low-control destination cells use the downward scan before the
same less-than-or-equal comparison. Two additional probes intentionally used
different low/high nibbles in the transient object's staged priority/control
byte: low `3` with high `6` remained hidden on a control-4 background, and low
`6` with high `3` drew on a control-6 background. For visible overlay gating,
the draw routine therefore uses the low nibble of object byte `+0x24`.

Additional QEMU probes with a zero staged priority confirm that helper `0x57cf`
derives the low visible priority from the runtime priority table when the low
nibble of object byte `+0x24` is zero. With the default table and baseline
Y `80`, the derived priority is `7` and the object draws over a control-6
background. After action `0xae` rebuilds the priority table from row `100`, the
same baseline derives priority `4` and is hidden behind that control-6
background.

The local compatibility helper now models this object-frame composition at the
buffer level. It takes a decoded frame, a left X, a baseline Y, and a priority
nibble, computes `top = baseline_y - frame.height + 1`, skips pixels whose
color equals the frame's transparent low nibble, and writes
`(priority << 4) | color` only when the high-nibble priority gate permits it.
QEMU validation of `add_to_pic` top-edge placement showed one extra adjustment:
if `top` is negative, the overlay path adds that negative value to `left`, adds
its absolute value to `baseline_y`, and draws with `top = 0`. In the observed
case, view 11/group 0/frame 0 requested at left `20`, baseline `2` matched a
local draw at left `18`, baseline `4`.
Right-edge placement is not a simple pixel clip. A transient view 11/group 0/
frame 0 probe requested at left `154`, baseline `80`; QEMU matched a local draw
at left `140`, baseline `67`. This records the current observed result of
placement helper `0x593a`, but the general placement-search algorithm still
needs more boundary probes before it should be reduced to a formula.
This does not yet replace the full object-record/update-list pipeline, but it
captures the central `IBM_OBJS.OVL:0x9db6` pixel rule for focused tests.

The persistent object-table path has also been validated for static drawing.
A generated logic fixture using `load_view`, object resource/frame selection,
`set_object_pos`, `set_object_field_24`, and `activate_object` produced the
same view 11/group 0/frame 0 output as the local composition model. Persistent
fixed priority bytes with nonzero high nibbles behaved differently from the
transient staged byte: `0x63`, `0x36`, and `0x66` were hidden in the controlled
probes where ordinary low-byte priorities would have separated visible draw
from rejection. The current safe interpretation is that persistent fixed
priority arguments should be treated as normal `0..15` priority values until
movement/control acceptance is probed more directly.

If frame control byte bit `0x80` is set, helper `0x587d` may rewrite the frame
data in place before drawing. It compares bits `0x70` of frame byte `+0x02`,
shifted down four bits, with object byte `+0x0a`. When they differ, it stores
the object value back into bits `0x70` and rebuilds each encoded row into a
stack buffer before copying the rebuilt stream over the original.

The observed rewrite is a horizontal row mirror over the run-length stream:

1. Keep the low nibble of the control byte as the transparent color.
2. Skip explicit leading transparent runs while accumulating their width.
3. From the first nontransparent run through the row terminator, count the
   total encoded width and the number of run bytes.
4. Emit transparent runs for the row's original implicit trailing transparent
   width, chunked into runs no longer than 15 pixels.
5. Copy the counted run bytes in reverse order.
6. End the rebuilt row with a zero terminator.

The original leading transparent pixels therefore become implicit trailing
transparent pixels after the reversed run bytes. This matches a QEMU fixture
using view 0, group 1, frame 0: the on-disk frame has control byte `0x81`
with cached orientation bits `0`, while selecting group 1 rewrites the control
byte to `0x91` and mirrors the row pixels.

Local SQ2 resource scans found frame control bytes with many low-nibble
transparent values, including `0x0`, `0x1`, `0x2`, `0x3`, `0x5`, `0x6`, `0x7`,
`0x8`, `0x9`, `0xa`, `0xc`, `0xd`, `0xe`, and `0xf`, and with optional bit
`0x80`; no sampled on-disk frame used bits `0x10`, `0x20`, or `0x40` except
through the mutable `0x70` orientation/cache field. View 0 group 0 frame 0 is
one concrete bit-`0x80` sample: it has size `7x33`, control byte `0x81`, and
row-terminated encoded data beginning with `13 62 00 12 64 00 ...`.

QEMU probes now include additional transparent-color samples: view 21/group 0/
frame 0 with transparent color `3`, view 29/group 0/frame 0 with transparent
color `8` and size `45x47`, and view 10/group 0/frame 0 with bit `0x80` and
transparent color `10`. All matched the local renderer in the expanded object
overlay batch.

The exact meaning of the first two payload bytes remains open.

## Object activation and deactivation

Action `0x23` (`activate_object`) calls helper `0x0a06` for an object index. The helper:

1. Computes and validates the 43-byte object record address.
2. Errors if object word `+0x10` is zero.
3. Returns early if object flag bit `0x0001` is already set.
4. Sets object flag bit `0x0010`.
5. Calls placement helper `0x593a`.
6. Copies `+0x10 -> +0x12`, `+0x03 -> +0x16`, and `+0x05 -> +0x18`.
7. Flushes list root `0x16ff` through `0x0307`.
8. Sets object flag bit `0x0001`.
9. Rebuilds/processes one update list through `0x6a26 -> 0x045e`.
10. Calls render/update helper `0x5762(object)`.
11. Clears object flag bit `0x1000`.

Action `0x24` (`deactivate_object`) calls helper `0x0aab`. If object flag bit `0x0001` is set, it
flushes list root `0x16ff`, sometimes also flushes list root `0x1703`, clears
the active bit, rebuilds/processes the affected lists, and calls `0x5762`.

This supports the current interpretation that bit `0x0001` means an object is
active in the graphics/update pipeline, while bit `0x0010` controls which of the
two update-list paths is involved. The exact user-facing names remain pending.

## Placement and bounds

Helper `0x593a(object)` is called when activating an object and by actions that
directly set object coordinates. It enforces screen and horizon-like bounds,
then searches for an acceptable nearby position when the initial position fails
collision or control tests.

Its bounds helper `0x5a14(object)` returns success only when:

```text
object[+0x03] >= 0
object[+0x03] + object[+0x1a] <= 0xa0
object[+0x05] - object[+0x1c] >= -1
object[+0x05] <= 0xa7
if object flag 0x0008 is clear: object[+0x05] > [0x012d]
```

If the object is above or at `[0x012d]` and bit `0x0008` is clear, `0x593a`
first bumps the Y-like field to `[0x012d] + 1`. When the starting position is
not acceptable, the helper tries neighboring positions in a widening
left/right/up/down pattern until the bounds and additional tests pass.

QEMU horizon probes validate this path with `[0x012d] = 100`. With bit
`0x0008` clear, placing view 11 at baseline `80` clamps it to baseline `101`.
After action `0x3d` sets bit `0x0008`, the same placement stays at baseline
`80`. After action `0x3e` clears the bit again, the baseline clamps to `101`.

Actions `0x5a` (`set_rect_bounds_0131`) and `0x5b` (`clear_rect_bounds_0131`) configure a separate rectangle filter used by motion
helper `0x06d9`. Action `0x5a` (`set_rect_bounds_0131`) stores four bounds in globals:

```text
[0x0131] = left
[0x0133] = top
[0x0135] = right
[0x0137] = bottom
[0x013d] = 1
```

Helper `0x7be6(x, y)` returns true only when the point is strictly inside that
rectangle:

```text
[0x0131] < x < [0x0135]
[0x0133] < y < [0x0137]
```

When `[0x013d]` is nonzero, an object has bit `0x0002` clear, and its direction
byte `+0x21` is nonzero, helper `0x06d9` compares whether the current baseline
point and the next step point are on the same side of the configured rectangle.
The next point is computed from direction byte `+0x21` and step byte `+0x1e`.
If the inside/outside result changes, the helper sets object bit `0x0080`,
clears direction byte `+0x21`, and, for the first object record, clears global
byte `[0x000f]`. If the result does not change, it clears bit `0x0080`.

## Per-cycle object movement

Movement-related work is split across two nearby passes:

1. Helper `0x0563` scans active/update-eligible objects before the movement
   pass. For objects with byte `+0x01 == 1`, it calls `0x067a(object)`.
   Dispatcher `0x067a` uses motion/control byte `+0x22`: mode `1` calls random
   motion helper `0x3f5a`, mode `2` calls approach-first-object helper
   `0x0b36`, and mode `3` calls targeted-motion helper `0x1672`.
2. Helper `0x150a` then applies the current direction byte `+0x21` and step
   byte `+0x1e`, checks collision/control acceptance, records boundary events,
   and clears bit `0x0400`.

The movement pass at `0x150a` scans all 43-byte object records from `[0x096b]`
to `[0x096d]`. It processes only records whose flag word satisfies:

```text
(object[+0x25] & 0x0051) == 0x0051
```

For each selected object, byte `+0x01` acts as a countdown. If it is nonzero the
pass decrements it and skips the object unless the decrement reaches zero. When
the object is due to move, the pass reloads `+0x01` from byte `+0x00`.

Unless object flag bit `0x0400` is set, the pass computes a proposed position
from direction-like byte `+0x21`, step/speed byte `+0x1e`, and two signed-delta
tables at `0x0a61` and `0x0a73`. The proposed position is then clamped against
the same `0xa0` by `0xa8` coordinate space used by placement:

| Boundary | Clamp | Boundary code |
| --- | --- | ---: |
| Left edge | `x = 0` | 4 |
| Right edge | `x = 0xa0 - width` | 2 |
| Top edge | `y = height - 1` | 1 |
| Bottom edge | `y = 0xa7` | 3 |
| Horizon-like line, when bit `0x0008` is clear | `y = [0x012d] + 1` | 1 |

The pass writes the proposed coordinates to object fields `+0x03` and `+0x05`,
then accepts the move only if both later tests agree:

```text
0x4719(object) == 0
0x56b8(object) != 0
```

If either test fails, it restores the saved X/Y coordinates, clears the boundary
code, and calls placement search helper `0x593a(object)`.

When a boundary code survives, the pass records a boundary event in globals. If
object byte `+0x02` is zero it writes the code to byte `[0x000b]`. Otherwise it
writes object byte `+0x02` to `[0x000d]` and the boundary code to `[0x000e]`.
If object byte `+0x22` is 3, helper `0x16b9(object)` is called to end that
motion/control mode. The pass clears object flag bit `0x0400` before leaving an
object.

Helper `0x4719(object)` is an object-object collision or crossing test. It
returns zero immediately when the object has bit `0x0200` set. Otherwise it
scans all active/eligible objects, skipping candidates with bit `0x0200` and
skipping candidates whose byte `+0x02` matches the moving object's byte `+0x02`.
It then checks horizontal rectangle overlap from X and width, followed by a
current/previous Y crossing test using fields `+0x05` and `+0x18`.

QEMU probes now validate the default object-object case with two persistent
objects. Object table initialization gives object 0 and object 1 different
`+0x02` values, so the collision helper considers them. With object 0 moving
right from `(20,80)` toward `(80,80)` and object 1 parked at `(50,80)`, object
0 stops at left `25`: its next proposed step would make its right edge touch
object 1's left edge, and `0x4719` rejects the move. Setting bit `0x0200` on
object 0 with action `0x43` lets the same fixture reach `(80,80)`, confirming
that the moving-object skip bit bypasses this collision test. A follow-up QEMU
probe sets the same bit with `0x43`, immediately clears it with `0x44`, and
observes the original collision stop at `(25,80)` again; this validates that
`0x44` restores normal object-object collision testing.

Helper `0x56b8(object)` is a control/priority-buffer acceptance test. If object
bit `0x0004` is clear, it derives object byte `+0x24` from table `0x127a` using
the object's Y coordinate. It then computes the buffer offset for object X/Y,
uses the selected frame width from object `+0x10`, scans high nibbles from the
buffer segment at `[0x136f]`, and reacts to these classes:

| High nibble | Observed behavior in `0x56b8` |
| ---: | --- |
| `0x00` | Rejects the proposed move immediately. |
| `0x10` | Permits scanning to continue only when object flag bit `0x0002` is set. |
| `0x20` | Records that this class was encountered, then continues. |
| `0x30` | Continues without changing the tracked class state. |

After the scan, object flag bits `0x0100` and `0x0800` can reject the final
class state. For objects whose byte `+0x02` is zero, the helper also updates
global flags 3 and 0 through `0x74ee`/`0x74f4` based on the scan result. The
exact meaning of the nibble classes is still open, but the caller contract is
clear: nonzero permits the proposed move, zero rejects it.

QEMU movement probes refine this static reading:

- Priority/control byte `+0x24 == 0x0f` bypasses the `0x56b8` scan. Synthetic
  full-screen control classes `0`, `1`, `2`, and `3` should not be modeled as
  blanket movement rejection for fixed-priority-15 objects.
- With fixed priority/control `14`, a full control-class-1 picture leaves no
  visible object in the capture, even after `0x58` sets bit `0x0002`. This
  fixture validates the hidden/control-class behavior but is not the positive
  `0x58` movement oracle.
- The positive `0x58`/`0x59` oracle is the rectangle-boundary helper. With
  bounds `(30,70)..(60,90)` and countdown-gated movement from `(20,80)` to
  `(50,80)`, bit `0x0002` clear stops the object at `(30,80)`, `0x58` lets it
  reach `(50,80)`, and `0x59` restores the stop at `(30,80)`.
- With fixed priority/control `14`, `0x40` setting bit `0x0100` leaves the
  object visible at `(20,80)` on a full control-class-2 picture and prevents
  movement to `(50,80)`. `0x42` clears the bit and restores movement.
- With fixed priority/control `14`, `0x41` setting bit `0x0800` leaves the
  object visible at `(20,80)` on a full control-class-3 picture and prevents
  movement to `(50,80)`. `0x42` clears the bit and restores movement.

Targeted-motion helpers immediately after the movement pass add one more piece.
Actions `0x51` (`move_object_to`) and `0x52` (`move_object_to_var`) set
`+0x22 = 3`, store target X/Y in `+0x27`/`+0x28`, optionally replace step size
`+0x1e`, save the original step in `+0x29`, and store a completion flag in
`+0x2a`. Helper `0x1672(object)` computes a direction-like byte from the
object's current position to the target fields using the current step byte and
stores the result in `+0x21`. Helper `0x16b9(object)` restores `+0x1e` from
`+0x29`, sets flag `+0x2a`, and clears motion/control byte `+0x22`.

QEMU movement probes show an important script-level contract for this mode.
Calling `0x51` once starts the object moving in the initially computed
direction. If object byte `+0x01` is not arranged to trigger the pre-movement
dispatcher, script logic normally reissues `0x51` or `0x52` on each interpreter
cycle while the completion flag is clear. When the object is then at, or within
one step of, the target, helper `0x1672` returns the zero direction and
immediately calls `0x16b9`. With this repeated-call fixture, horizontal and
vertical target arrival matched QEMU exactly. Targets beyond the reachable
screen area complete at the movement clamp: view 11/group 0/frame 0 stopped at
left `140` for a rightward target and baseline `167` for a downward target.

The source's pre-movement mode-3 path through `0x067a` is also now validated.
It is gated by byte `+0x01 == 1`. A generated fixture that sets that byte and
calls `0x51` once, without reissuing it from script logic, reaches `(50,80)` and
sets the completion flag through the autonomous `0x067a -> 0x1672` path.

The same countdown-gated dispatcher is now validated for mode `2`. A generated
fixture initializes object 1, sets its step byte to `5`, sets countdown byte
`+0x01` to `1`, and starts action `0x53`
(`approach_first_object_until_near`) toward object 0 with near threshold `35`.
QEMU stops object 1 at `(50,80)` when object 0 is parked at `(80,80)`. An
earlier exploratory threshold `25` case fell into the collision/stuck-recovery
region near the target and ended at `(60,75)`, so the passing threshold-35 case
is the cleaner contract probe for direct mode-2 completion. The threshold-35
result also shows the near-band test does not complete at the exact boundary:
object 1 moved past the predicted boundary position `(45,80)` and completed at
`(50,80)`.

Disassembly of `0x0b36` explains the threshold-25 exploratory result. Mode 2
stores sentinel `0xff` in `+0x29`; on the first non-complete step the helper
changes that to `0`. If bit `0x4000` later says the object did not move, the
helper chooses a random nonzero direction, computes a delay from half the
Manhattan-like center/baseline distance plus one, and stores either the current
step size or a random value at least as large as the step in `+0x29`. While
`+0x29` is nonzero, the helper subtracts the step size from it each pass and
delays returning to the direct approach direction. That is the current
source-backed model for approach stuck recovery.

Random mode `0x54` has a property-style QEMU probe rather than an exact final
position assertion. A generated fixture sets step `5`, sets countdown byte
`+0x01` to `1`, starts random mode, and accepts any capture that exactly
matches the object at a valid final position. The recorded run ended at
`(140,112)`.

A focused QEMU probe validates the visible effect of action `0x4e` on this
motion byte. The fixture starts random motion on object 0 with `0x54`, then
immediately executes `0x4e`. During the subsequent update cycles, the object
remains at its starting position `(60,80)`, confirming that clearing `+0x22`
prevents the autonomous random-motion dispatcher from continuing.

The expanded movement probe set also confirms leftward and upward movement,
diagonal movement, already-at-target completion, and within-step completion. A
target X of `52` from starting X `20` with step `5` completes at X `50`, not
`52`, because the remaining distance is inside the step band. A zero step-size
operand does not invent a default speed; it preserves the current object step
byte. In the generated persistent-object fixture that byte is zero, so the
object remains stationary.

The direction lookup at `DS:0x0a85` maps relative target position to direction
bytes:

```text
target above:  8 1 2
target level:  7 0 3
target below:  6 5 4
               left near right
```

The zero center value means the target has been reached; `0x1672` then calls
`0x16b9` immediately.

## Update lists and rendering work

Two linked-list roots are central to the update pipeline:

| Root | Builder wrapper | Selection callback | Predicate |
| --- | --- | --- | --- |
| `0x16ff` | `0x6a26` | `0x69e4` | `(object[+0x25] & 0x0051) == 0x0051` |
| `0x1703` | `0x6a3d` | `0x6a05` | `(object[+0x25] & 0x0051) == 0x0041` |

The predicates show that bit `0x0010` partitions otherwise active/eligible
objects between the two roots. Helpers `0x6b44` and `0x6b62` clear and set that
bit respectively, wrapping the change with `0x6a54` and `0x6a8e` so the update
lists are rebuilt around the new membership.

The wrapper helpers around those roots are now distinct:

| Helper | Observed role |
| --- | --- |
| `0x6a54` | Calls `0x0307` for roots `0x16ff` and `0x1703`, restoring saved backing rectangles through `0x9db3` and freeing all nodes. |
| `0x6a71` | Calls `0x032d` for both roots, freeing nodes without the restore pass. |
| `0x6a8e` | Rebuilds and draws root `0x1703`, then rebuilds and draws root `0x16ff`, using `0x6a3d`/`0x6a26` followed by `0x045e`. |
| `0x6aab` | Calls `0x0488` for root `0x1703`, then root `0x16ff`, refreshing dirty rectangles and updating saved-position state. |

The shared builder `0x0358(root, callback)` scans all 43-byte object records,
selects records accepted by the callback, sorts them, and inserts render/update
nodes with `0x042f`. The sort key is either the object's Y-like field `+0x05`
or, when object flag bit `0x0004` is set, a value derived from object byte
`+0x24` through helper `0x4cbb`.

The list-processing helper `0x045e(root)` walks from the list tail backward. For
each node it calls `0x9db0(node)`, then calls `0x9db6` with the object pointer
stored at node `+0x04`.

The render/update node allocator at `0x9097` creates a 16-byte node and stores
its pointer back into object word `+0x14`.

Observed node layout:

| Offset | Observed use |
| ---: | --- |
| `+0x00` | Next pointer in the root's linked list. |
| `+0x02` | Previous pointer in the root's linked list. |
| `+0x04` | Object pointer. |
| `+0x06` | Left/X coordinate copied from object `+0x03`. |
| `+0x08` | Top/Y coordinate computed as `object[+0x05] - object[+0x1c] + 1`. |
| `+0x0a` | Width copied from object `+0x1a`. |
| `+0x0c` | Height copied from object `+0x1c`. |
| `+0x0e` | Pointer to an allocated backing buffer for the rectangle. |

When display mode word `[0x1130] == 2`, `0x9097` increases the backing-buffer
width calculation before allocating the buffer. The exact packed-pixel reason is
display-specific and remains to be tied to the HGC overlay.

The object overlay file `IBM_OBJS.OVL` is loaded at segment `0x09db`, so its
first bytes appear at near offset `0x9db0`. The three entry jumps in that
overlay line up with the main executable's calls:

| Near offset | Overlay entry | Observed role |
| --- | --- | --- |
| `0x9db0` | `jmp 0x9db9` | Save a screen rectangle into node backing buffer `+0x0e`. |
| `0x9db3` | `jmp 0x9df8` | Restore a screen rectangle from node backing buffer `+0x0e`. |
| `0x9db6` | `jmp 0x9e35` | Draw an object's selected frame data into the graphics buffer. |

Helper `0x0488(root)`, called by `0x6aab`, walks a render/update list after
drawing. For each node's object it first calls `0x5762(object)` to refresh the
dirty rectangle. It then compares object byte `+0x01` with reload byte `+0x00`;
only when those bytes match does it compare current X/Y `+0x03/+0x05` with
saved X/Y `+0x16/+0x18`. If position is unchanged it sets flag bit `0x4000`;
otherwise it copies current X/Y to saved X/Y and clears `0x4000`.

Two later autonomous-direction helpers consume `0x4000`:

- `0x3f5a(object)`, called from motion/control mode byte `+0x22 == 1`, chooses
  a new random direction through `0x3fa3` when its local countdown expires or
  when bit `0x4000` says the object stayed in place.
- The helper around `0x0bb3`, called from the `+0x22 == 2` path, also consults
  bit `0x4000` before replacing direction byte `+0x21` with a random nonzero
  direction. This looks like stuck recovery for a directed movement mode.

So `0x4000` is not just an optimization marker. It records that the object was
stationary at the last saved-position comparison, and the motion code uses that
fact to choose fresh directions.

The currently observed values of object byte `+0x22` are:

| Value | Started by | Per-cycle behavior |
| ---: | --- | --- |
| `0` | `0x55` (`stop_motion_mode`), completion helpers | No autonomous mode is active. |
| `1` | `0x54` (`start_random_motion`) | Helper `0x3f5a` picks direction `0..8` with helper `0x3fa3`, keeps a random countdown in `+0x27`, and reseeds when the countdown expires or the stationary bit `0x4000` is set. A QEMU property probe confirms the mode renders the object at a valid final position. |
| `2` | `0x53` (`approach_first_object_until_near`) | Helper `0x0b36` computes a direction from the object's center/Y toward the first object entry's center/Y using threshold `+0x27`; when the direction helper returns zero it clears the mode and sets completion flag `+0x28`. Stuck recovery temporarily chooses a random nonzero direction and stores a retry delay in `+0x29`. QEMU confirms direct completion at `(50,80)` in the threshold-35 fixture. |
| `3` | `0x51` (`move_object_to`), `0x52` (`move_object_to_var`) | Helper `0x1672` computes direction toward target X/Y in `+0x27/+0x28`; completion helper `0x16b9` restores saved step `+0x29`, sets completion flag `+0x2a`, and clears the mode. QEMU probes confirm both script-reissued setup and countdown-gated one-shot setup can complete. |

The render/update helpers around `0x5528..0x5762` bridge the interpreter's
logical graphics buffer to the selected graphics overlay:

- `0x5528` clears the logical graphics buffer with fill word `0x4040`, calls
  graphics-overlay entry `0x980f`, rebuilds the default priority/control table
  through `0x56a2`, and calls graphics-overlay entry `0x9800`.
- `0x5546` performs a full-screen refresh. If word `[0x1755]` has bit 0 set it
  first swaps the high and low nibbles of every byte in the logical graphics
  buffer, calls the HGC-only helper `0x9899` when display mode `[0x1130] == 2`,
  then calls graphics-overlay entry `0x980c` for the whole screen.
- `0x5624` converts the common coordinate tuple into a display-memory offset,
  using display-mode globals `[0x1130]` and `[0x112e]`.
- `0x5762(object)` is the object dirty-rectangle refresher. If word `[0x1216]`
  is zero it returns without display work. Otherwise it compares the object's
  current frame pointer `+0x10`, current X/Y `+0x03/+0x05`, saved frame pointer
  `+0x12`, and saved X/Y `+0x16/+0x18`; stores the current frame pointer into
  `+0x12`; computes the union rectangle covering both old and new frame
  footprints; and calls graphics-overlay entry `0x980c`.

The common rectangle arguments to graphics-overlay entries `0x980c` and
`0x9812` are:

```text
AH = left X
AL = bottom Y
BL = width
BH = height
```

Entry `0x980c` copies a rectangle from logical graphics buffer segment
`[0x136f]` to display memory segment `[0x1371]`. Entry `0x9812` fills a display
rectangle; in the EGA and VGA overlays the low byte of `DX` supplies the fill
value. The main executable's helper `0x5590` uses `0x9812` to draw/fill several
rectangular UI borders, while `0x560c` is a small wrapper around `0x980c`.

The EGA graphics overlay (`SQ2/EGA_GRAF.OVL`, loaded at `0x9800`) exposes this
entry table:

| Near offset | Overlay entry | Observed role |
| --- | --- | --- |
| `0x9800` | `jmp 0x9815` | Set graphics mode `0x0d`, configure palette/register state, and store video segment `0xa000` in `[0x1371]`. |
| `0x9803` | `jmp 0x9835` | Return to text mode, configure cursor/palette, and clear the text screen. |
| `0x9806` | `jmp 0x986f` | Reinitialize graphics mode, then call `0x5546` for a full refresh. |
| `0x9809` | `jmp 0x9884` | No-op entry in the EGA overlay. |
| `0x980c` | `jmp 0x9885` | Copy a rectangle from `[0x136f]` to EGA display memory. |
| `0x980f` | `jmp 0x9983` | Initialize row-offset table `0x137b` and clear a display-memory range. |
| `0x9812` | `jmp 0x9907` | Fill a rectangle in EGA display memory. |

## Transient and preview objects

Two logic-action families use the same view and object drawing machinery without
adding a normal persistent object-table entry.

Actions `0x7a` (`setup_transient_object`) and `0x7b` (`setup_transient_object_var`)
build a transient object-like record at fixed address
`0x0eb4`. Action `0x7a` (`setup_transient_object`) reads seven immediate operands; action `0x7b` (`setup_transient_object_var`) reads the
same seven values through variables. The values are staged in globals
`0x0eae..0x0eb3` before helper `0x2d52` interprets them:

| Staged byte | Observed role |
| ---: | --- |
| `0x0eae` | View-like resource number. |
| `0x0eaf` | Top-level subresource/group index. |
| `0x0eb0` | Derived subresource/frame index. |
| `0x0eb1` | X coordinate. |
| `0x0eb2` | Y coordinate. |
| `0x0eb3` low nibble | Visible overlay priority nibble. |
| `0x0eb3` high nibble | Staged control/secondary priority nibble; not used for visible overlay gating in the current QEMU probes. |

Helper `0x2d52` logs several staged pairs through `0x70b1`, then initializes
the record at `0x0eb4` through the normal view/object helpers:

```text
0x3ae7(0x0eb4, staged_view)
0x3bb7(0x0eb4, staged_group)
0x3ccb(0x0eb4, staged_frame)
```

It copies the selected frame pointer to saved-frame field `+0x12`, writes the
staged X/Y to both current and saved coordinate fields, sets object byte `+0x24`
from the staged priority/control byte, places the object through `0x593a`, then
wraps the actual draw/update path with:

```text
0x6a54
0x57cf(0x0eb4)
0x6a8e
0x5762(0x0eb4)
```

The fixed record's flag word is initialized as `0x020c` before placement, which
sets the observed fixed-priority bit `0x0004`, horizon-exempt bit `0x0008`, and
collision-skip bit `0x0200`. If the staged priority/control low nibble is zero,
the helper later replaces the flag word with `0x0008` before calling `0x57cf`.
That special case is stable in the code but its user-facing meaning remains
open.

Actions `0x81` (`display_view_resource_text_like`) and `0xa2` (`display_view_resource_text_like_var`)
display or preview a view-like resource using a
stack-local 43-byte record. Action `0x81` (`display_view_resource_text_like`) uses an immediate resource number;
action `0xa2` (`display_view_resource_text_like_var`) reads the resource number from a variable. Helper `0x5edb`:

1. Records whether the resource was already cached through `0x3979`.
2. Temporarily sets word `[0x0f18] = 1` while calling loader `0x39f7`.
3. Initializes a stack-local object record with group/frame zero through
   `0x3ae7`.
4. Centers it horizontally with `x = (0x9f - width) / 2`, sets `y = 0xa7`,
   sets fixed priority/control byte `+0x24 = 0x0f`, and sets grouping byte
   `+0x02 = 0xff`.
5. If enough memory is available, allocates a render/update node with `0x9097`,
   saves the backing rectangle through `0x9db0`, draws through `0x9db6`, and
   calls `0x5762`.
6. Displays a string pointer derived from the loaded payload through `0x1ce8`.
   The pointer is `payload + u16(payload + 0x03)`, which gives the first
   observed consumer of view payload bytes `+0x03..+0x04`.
7. If a backing rectangle was saved, restores it with `0x9db3`, calls `0x5762`,
   and frees the node with `0x910a`.
8. If the resource was not cached before the preview action, releases it through
   `0x3f0d`.

## Current system model

The graphics/interpreter path now looks like this:

1. Directory files and `VOL.*` records provide raw logic, picture, view, and
   sound payloads.
2. Logic bytecode actions request resource loads and mutate object records.
3. Picture actions select a cached picture payload, decode command bytes
   `0xf0..0xfa`, and write into the graphics buffer through shared pixel
   helpers.
4. View actions bind view-like payloads to 43-byte object records and derive
   object dimensions and frame pointers.
5. Transient display actions can build temporary object records and route them
   through the same placement/draw/update helpers.
6. Object activation and movement actions flush, rebuild, and process sorted
   update lists rooted at `0x16ff` and `0x1703`.
7. Render/update nodes capture backing rectangles, draw selected frame data from
   object field `+0x10`, and later restore old rectangles when lists are
   flushed.

The largest remaining unknowns in this area are the exact semantics of the two
update-list roots, the first two bytes of view-like payloads, most bits in the
frame control byte, and the display-specific packed-buffer variants.
