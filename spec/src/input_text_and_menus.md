# Input, Text, Menus, and Inventory

This chapter defines string parsing, keyboard/event handling, text-surface
state, menu interaction, and inventory selection. These systems share input
events but retain distinct script-visible state.

## Dictionary file

The dictionary file begins with 26 unsigned big-endian offsets, one for each
lowercase initial letter `a` through `z`. An offset of zero means that initial
has no entries.

Entries in each initial-letter sequence are prefix-compressed:

```text
prefix_length:u8
encoded_suffix:u8[]
word_id:u16be
```

`prefix_length` characters are copied from the preceding decoded word. For
each suffix byte, `(byte & 0x7f) ^ 0x7f` is the lowercase character. Bit `0x80`
marks the final suffix byte. The following two bytes are the word identifier in
big-endian order.

Dictionary lookup is case-insensitive for ASCII letters.

## String slots

The promoted profiles expose twelve 40-byte string slots `s0..s11`. Slot
operations use zero-terminated byte strings within that fixed capacity.

- Copying a logic message or normalized parsed word copies no more than 40
  bytes into the destination slot.
- Prompted editing clears the destination first. Its storage limit is
  `min(requested_maximum + 1, 40)` bytes including the terminator.
- Parsing ignores slot numbers outside `0..11`.
- Numeric prompting accepts at most four decimal characters and stores the low
  eight bits of the resulting unsigned value.

Direct string-slot comparison has its own normalization. It removes space,
tab, `.`, `,`, `;`, `:`, apostrophe, `!`, and `-`; lowercases ASCII `A..Z`;
and then requires exact equality through both zero terminators. It does not use
the dictionary or parsed-word state.

## Parser normalization

Parsing begins by clearing `f2` (parsed input ready), `f4` (parsed input already
matched), the parsed word identifiers, and their normalized-token references.

The source slot is normalized into a temporary zero-terminated buffer:

- space and `, . ? ! ( ) ; : [ ] { }` are separators;
- apostrophe, backtick, hyphen, and double quote are dropped without creating
  a separator;
- separator runs collapse to one space;
- a trailing space is removed; and
- ASCII dictionary matching ignores letter case.

The normalized buffer is split into tokens and looked up in the dictionary.
At most ten nonzero word identifiers are retained.

## Parser results

Recognized dictionary entries with word ID zero are ignored. They do not occupy
a parsed-word slot or increase the reported parsed position.

Recognized nonzero identifiers are appended in token order. Their normalized
token text remains available for the action that copies a parsed word into a
string slot.

At the first unknown token:

1. Store its normalized-token reference in the next output position.
2. Set the parser count/error position to
   `retained_nonzero_identifier_count + 1`.
3. Store the same one-based position in `v9`.
4. Set `f2` and stop parsing later tokens.

If parsing reaches the end with at least one retained nonzero identifier, set
the parser count to that number and set `f2`. If the input contains only
recognized zero-ID words, leave `f2` clear.

## Parsed-word matching

The variable-length word-sequence condition can run only when `f2` is set, the
parser count/error position is nonzero, and `f4` is clear.

Pattern identifiers are compared with retained parsed identifiers in order:

- `0x0001` matches exactly one parsed identifier;
- `0x270f` terminates the pattern successfully without requiring all remaining
  parsed identifiers to be consumed; and
- every other value requires exact equality.

A full exact match also succeeds. Success sets `f4`, preventing another
word-sequence condition from matching the same parsed input. Failure leaves
`f4` clear.

A terminator-only pattern can succeed after an unknown-token parse because the
nonzero parser error position satisfies the input-presence check even when no
dictionary identifier precedes the unknown token.

## Event queue

Input consumers share a circular queue with 20 physical event slots. Enqueueing
fails when advancing the write position would equal the read position, so at
most 19 events can be pending at once.

Each event has a type and a 16-bit value:

| Type | Meaning |
| ---: | --- |
| 1 | Raw key word. |
| 2 | Movement/navigation value. |
| 3 | Script-mapped status number. |

For a key whose ASCII byte is nonzero, the raw key word contains that byte as
its value. For an extended key whose ASCII byte is zero, the scan-code word is
retained.

The following extended key words are converted directly to type-2 direction
events:

| Key word | Value |
| ---: | ---: |
| `0x4800` | 1 |
| `0x4900` | 2 |
| `0x4d00` | 3 |
| `0x5100` | 4 |
| `0x5000` | 5 |
| `0x4f00` | 6 |
| `0x4b00` | 7 |
| `0x4700` | 8 |

Some input paths normalize key words `0x0101` and `0x0301` to Enter
`0x000d`, and `0x0201` and `0x0401` to Escape `0x001b`.

Profiles 2.411, 2.440, 2.917, 2.936, 3.002.086, and 3.002.102 hold 39
`(raw_key_word, status_number)` entries; profile 3.002.149 holds 49. A matching
type-1 event becomes type 3 with the configured status number. Processing that
event makes the matching status condition true.

## Raw-key condition

The raw-key condition first checks `v19`. If it is nonzero, the condition is
true without consuming another event.

Otherwise it dequeues until one of these occurs:

- the queue is empty, producing false;
- a type-1 event with nonzero value is found, storing its low byte in `v19` and
  producing true;
- a type-1 event with zero value is found, producing false; or
- a non-type-1 event is discarded, after which polling continues.

Mapped status and movement events are therefore not returned by the raw-key
condition.

## Tracked key release

Selected extended keys have a pressed latch. A corresponding release clears
the latch. When the profile's release-event gate is nonzero, that release also
enqueues type-2 value zero.

In profiles 2.917, 2.936, and 3.002.086, action `0xad` increments the byte gate
modulo 256. Profiles 2.411 and 2.440 do not expose that action. In profiles
3.002.102 and 3.002.149, `0xad` sets the gate to one and `0xb5` clears it.

## Text geometry and surfaces

The full-EGA text grid has 40 columns and 25 rows. One text column spans four
logical picture pixels; one text row spans eight logical picture rows.

Text rectangle operations use inclusive top/bottom and left/right text-cell
bounds. Full-width row clearing covers columns 0 through 39. These operations
overwrite the visible text surface; they do not alter a loaded picture payload
or re-decode picture commands.

The input/status configuration selects a display base row, input row, and
status row. In the normal EGA presentation, display base value `n` adds
`8 * n` logical rows to later picture/object presentation. The input and status
rows independently choose the eight-logical-row bands used by those text
surfaces.

Disabling the input line clears its configured row and prevents ordinary input
redraw. Enabling it clears/redraws that row, then draws the prompt marker and
input text when present. The prompt marker is the first byte of its selected
message; a zero byte suppresses it. Erasing input sends repeated backspace
behavior until the visible edit length reaches zero. Refreshing the input line
uses the most recently accepted input, not unaccepted live-edit characters.

The status line similarly has enabled and disabled states. Enabling redraws its
configured row; disabling clears that row.

## Modal text and alternate text mode

A modal message saves the covered visible rectangle, draws and formats its
text window, waits for acknowledgement, and restores the prior rectangle when
closed. Opening another saved window first closes the current one.

Configured modal-message actions can supply temporary row, column, and width
overrides. The width is the maximum formatted text width; a zero width means
30. Row and column override the default centered placement for that single
message. Without an override, row is centered within the current display text
area and column is centered within the 40-column text surface from the
formatted line width.

Entering alternate text-attribute mode suppresses normal object graphics
updates and clears/fills the visible full-screen surface using the configured
text foreground/background pair. Leaving restores normal graphics presentation
and redraws configured status/input areas.

The exact 8-by-8 glyph bitmaps are platform-font inputs, not a portable core
interpreter requirement. Text placement, row/column geometry, modal blocking,
and save/restore behavior remain normative.

## Inventory selection

Each inventory item has a display name and one-byte location. Location `0xff`
means carried. The inventory action lists only carried items, in item-number
order, using two columns when necessary.

When inventory interaction is enabled, Enter stores the selected item number
in `v25` and Escape stores `0xff`. When interaction is disabled, the same list
is acknowledgement-only and does not produce a selection result. With no
carried items, the UI displays its empty-inventory text.

## Menu construction

Menu setup creates ordered headings and ordered items under the current
heading. Each item has display text, a script-visible status number, and an
enabled state.

Setup remains mutable until finalization. Finalization disables headings with
no items, chooses the root heading and its first item as the current selection,
and prevents later heading/item additions from changing the established menu.
Enable and disable actions can still change an existing item by status number.

Menu state remembers the current item separately for each heading. A later
menu opening resumes from the remembered heading/item state.

## Menu interaction

The menu-request action requests interaction only while `f14` is set. The v3
profiles add a separate menu interaction gate: a zero value set by `0xb1`
prevents a pending request from opening the modal menu; a nonzero value permits
it.

While open, raw Enter selects only an enabled current item. Selection enqueues
a type-3 event carrying that item's status number. Enter on a disabled item
does nothing and continues waiting. Escape closes without selection.

Type-2 navigation values have these meanings:

| Value | Menu movement |
| ---: | --- |
| 1 | Previous item. |
| 2 | First item. |
| 3 | Next enabled heading. |
| 4 | Last item. |
| 5 | Next item. |
| 6 | Last heading. |
| 7 | Previous enabled heading. |
| 8 | Root heading. |

Item movement follows the ordered circular item list and does not skip disabled
items. Heading-left/right movement skips disabled headings. Leaving a heading
stores its current item. Exit restores the saved visible menu rectangle,
redraws or clears the status row as configured, and clears the interaction
request.

## Font boundary

Message substitution and ordinary window layout are specified by their action
effects and observed modal geometry. Exact glyph shapes remain a platform-font
concern, so full bitmap-identical text-presentation claims must provide a font
input. This does not make parser, event, menu, or inventory state provisional.
