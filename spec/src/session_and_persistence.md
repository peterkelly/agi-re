# Rooms, Replay, and Persistence

This chapter defines room transitions, the resource replay sequence, restart,
save/restore selection, and the known save-file envelope. Save-state semantics
are normative where mapped. Reserved serialized portions are identified
explicitly and have defined initialization and preservation rules.

## Room transition

An immediate or variable-selected room switch performs this sequence:

1. Stop active sound.
2. Reset transient display/update work, parsed-input state, persistent-object
   participation, room-scoped resources, and the resource replay sequence.
3. Preserve the global logic needed by the next top-level cycle.
4. Reset the horizon to `36`, disable the configured movement rectangle, and
   reset ordinary object cadence, step, and cel-timer defaults to `1`.
5. Copy old `v0` to `v1`, store the destination in `v0`, and store object 0's
   selected view number in `v16`.
6. Clear `v4` and `v5`, then load the destination logic resource.
7. Apply the entry-boundary selector in `v2` to object 0 and clear `v2`.
8. Set new-room flag `f5` and redraw normal status/input presentation.
9. Abort the current logic continuation.

The next top-level pass starts logic 0 again. The room-switch operation does
not implicitly execute the destination room logic before that pass.

Entry-boundary values are:

| `v2` | Object 0 placement |
| ---: | --- |
| 1 | Baseline Y becomes `167`. |
| 2 | Left X becomes `0`. |
| 3 | Baseline Y becomes `37`. |
| 4 | Left X becomes `160 - cel width`. |

Profile 3.002.149 first maps immediate destinations `0x7e`, `0x7f`, and
`0x80` to room `0x49`. Other destinations and the common transition sequence
are unchanged.

## Resource replay sequence

The engine maintains an ordered sequence of two-byte `(kind, value)` pairs.
It records only operations needed to reconstruct room resource/display state;
it is not a general execution log.

Recording appends only while `f7` is clear and the internal recording gate is
enabled. Capacity is configured in pairs. Exceeding capacity is an engine
error; valid game execution must configure enough space.

The pair kinds are:

| Kind | Value | Replay operation |
| ---: | --- | --- |
| 0 | logic number | Load and retain the logic, then restore its saved resume metadata. |
| 1 | view number | Load or refresh the view. |
| 2 | picture number | Load the picture. |
| 3 | sound number | Load the sound. |
| 4 | picture number | Prepare/decode the already loaded picture after clearing logical picture state. |
| 5 | zero | Consume the next three pairs as transient-view parameters and reproduce the transient cel draw. |
| 6 | picture number | Discard the picture. |
| 7 | view number | Discard the view. |
| 8 | picture number | Overlay/decode the already loaded picture without clearing logical picture state. |

Kind 5 is a four-pair packet. After `(5,0)`, the next three pairs carry these
seven bytes in order:

```text
(view, loop)
(cel, left_x)
(baseline_y, packed_priority_control)
```

The final byte contains the staged priority/control nibbles used by transient
composition.

Replay stops sound, resets room resource caches, disables recording, executes
the sequence in order, and then re-enables recording before object view
bindings and normal display/input state are refreshed. Replayed operations
therefore do not append duplicates.

Replay kinds 6 and 7 use the ordinary ordered-discard rule. They remove the
named picture or view and every resource retained later in that same family.
Subsequent replay pairs may load those resources again, establishing a new
retention order before object bindings are restored.

Temporary view preview actions disable recording around their internal
load/display/discard work, so they never become persistent replay events.

## Replay checkpoints

The replay sequence tracks an active pair count. The checkpoint action saves
that count. The rollback action restores it and moves the append position to
the end of the restored prefix. Pairs after the checkpoint remain outside the
active sequence and are neither replayed nor included as active state.

## Save selector

Save and restore use a modal selector with up to 12 numbered slots.

On entry, the selector remembers whether the normal prompt marker was visible,
erases it, saves text/window state, stops sound, and switches to selector text
attributes. Every nonfatal exit restores text state and redraws the prompt
marker only when required by the profile and entry state.

If no save directory is already available, the selector prompts for one. Path
normalization:

- skips leading spaces;
- substitutes the current directory for an accepted empty string;
- removes one trailing slash or backslash from strings longer than one byte;
- accepts a single slash or backslash;
- checks two-character drive paths such as `A:` for drive availability; and
- otherwise requires the path to resolve as a directory.

Invalid/unavailable paths display the path or disk prompt and may repeat.
Escape cancels without file I/O.

The selector scans slots 1 through 12. Restore lists only files whose header
and signature prefix pass validation. Save may select an empty slot; doing so
opens a second editor for a description of at most 31 bytes. Enter accepts the
current row, Escape cancels, and movement values 1 and 5 move up/down with
wrap.

## Save names and signatures

The game signature action copies up to seven message bytes into the runtime
signature and verifies the profile's expected game identifier. The signature
is used in save filenames and in restore candidate validation.

The observed filename stem is the signature followed by `SG.` and the slot
number. For example, signatures `SQ2` and `GR` produce `SQ2SG.1` and `GRSG.1`.
An empty signature produces `SG.1`.

Restore candidate scanning reads the 31-byte header, skips the first block
length, and compares the first seven state bytes with the active signature
area before listing the slot.

## Save-file envelope

A save file has this framing:

```text
description_header[31]
repeat 5 times:
    block_length:u16le
    block_data[block_length]
```

The displayed description is the zero-terminated prefix of the 31-byte header.

The five conceptual blocks are:

1. global scalar, signature, string, parser, display, and session state;
2. persistent drawable-object state;
3. inventory and related object metadata;
4. the configured resource replay-pair storage;
5. variable-sized loaded-logic/cache resume state.

For profile 2.411, the observed KQ2 state uses lengths:

| Block | Length |
| ---: | ---: |
| 1 | 1503 (`0x05df`) |
| 2 | 731 (`0x02db`) |
| 3 | 598 (`0x0256`) |
| 4 | 120 (`0x0078`) |
| 5 | Variable. |

For profile 2.440, the observed LSL1 state uses lengths:

| Block | Length |
| ---: | ---: |
| 1 | 1503 (`0x05df`) |
| 2 | 731 (`0x02db`) |
| 3 | 308 (`0x0134`) |
| 4 | 288 (`0x0120`) |
| 5 | Variable. |

The observed BC data selects the mapped-equivalent 2.439/2.440 behavioral
rules with these separate dimensions:

| Block | Length |
| ---: | ---: |
| 1 | 1503 (`0x05df`) |
| 2 | 731 (`0x02db`) |
| 3 | 309 (`0x0135`) |
| 4 | 254 (`0x00fe`) |
| 5 | Variable. |

For the observed profile 2.936 game data, block lengths are:

| Block | Length |
| ---: | ---: |
| 1 | 1505 (`0x05e1`) |
| 2 | 903 (`0x0387`) |
| 3 | 328 (`0x0148`) |
| 4 | 200 (`0x00c8`) |
| 5 | Variable. |

For profile 2.917, the observed KQ1 state uses lengths:

| Block | Length |
| ---: | ---: |
| 1 | 1505 (`0x05e1`) |
| 2 | 774 (`0x0306`) |
| 3 | 328 (`0x0148`) |
| 4 | 200 (`0x00c8`) |
| 5 | Variable. |

For profile 2.917, the observed PQ1 state uses lengths:

| Block | Length |
| ---: | ---: |
| 1 | 1505 (`0x05e1`) |
| 2 | 860 (`0x035c`) |
| 3 | 366 (`0x016e`) |
| 4 | 500 (`0x01f4`) |
| 5 | Variable. |

The observed MG data selects the mapped-equivalent 2.915/2.917 behavioral
rules with lengths `0x05df`, `0x0387`, `0x0005`, `0x00dc`, and a variable
fifth block. The shorter first block is a selected-build persistence variant,
not a change to the shared gameplay core.

The observed SQ1.22 data uses profile 2.917 with lengths `0x05e1`, `0x0306`,
`0x0148`, `0x0064`, and a variable fifth block.

For profile 2.936, the observed KQ3 state uses lengths:

| Block | Length |
| ---: | ---: |
| 1 | 1505 (`0x05e1`) |
| 2 | 731 (`0x02db`) |
| 3 | 775 (`0x0307`) |
| 4 | 254 (`0x00fe`) |
| 5 | Variable. |

For profile 3.002.086, the observed full KQ4 state uses lengths:

| Block | Length |
| ---: | ---: |
| 1 | 1505 (`0x05e1`) |
| 2 | 1118 (`0x045e`) |
| 3 | 710 (`0x02c6`) |
| 4 | 500 (`0x01f4`) |
| 5 | Variable. |

For profile 3.002.149, the observed Gold Rush state uses lengths:

| Block | Length |
| ---: | ---: |
| 1 | 1028 (`0x0404`) |
| 2 | 989 (`0x03dd`) |
| 3 | 1811 (`0x0713`) |
| 4 | 100 (`0x0064`) |
| 5 | Observed initial saves use 12 (`0x000c`); the record grammar is variable. |

The envelope, lengths, signature prefix, and mapped subsystem effects are
normative. All five blocks in the observed profile 2.936 game data are mapped
below. Profile-specific reserved bytes remain explicitly identified.

All positions in the following tables are relative to the start of that block.
All multi-byte integers are little-endian. Reserved ranges are part of the file
contract even though valid game operations do not address them. A newly
initialized state uses the canonical bytes listed below. A save loaded for
binary interchange preserves the bytes it supplied and emits them unchanged.

## Profiles 2.411 and 2.440 observed early blocks

Both early profiles use the first `0x05df` bytes of the profile 2.936 block-1
partition. They include all fields through `display_bottom_row` and omit the
later two-byte saved replay-checkpoint count. Reserved ranges within that
prefix use the same canonical initialization and byte-preservation rules.

The selected KQ2 data uses 17 consecutive `0x2b`-byte object records in block
2. Its `0x0256`-byte block 3 contains 85 three-byte inventory entries followed
by a 343-byte zero-terminated display-name pool. It configures 60 replay pairs,
so block 4 is `0x0078` bytes.

The selected LSL1 data also uses 17 object records. Its `0x0134`-byte block 3
contains 21 three-byte inventory entries followed by a 245-byte display-name
pool. It configures 144 replay pairs, so block 4 is `0x0120` bytes.

Both profiles store block 3 directly without the v3 transform. Block 5 uses the
common variable-length logic-resume grammar.

## Profile 2.917 observed KQ1 blocks

The selected KQ1 data uses the profile 2.936 block-1 partition and reserved
state rules exactly. Block 1 is `0x05e1` bytes.

Block 2 contains 18 consecutive `0x2b`-byte object records with the record
partition specified below for profile 2.936. The decoded inventory metadata
header's maximum object index is 17, establishing that count.

Block 3 is `0x0148` bytes. Its first 81 bytes contain 27 three-byte inventory
entries and its remaining 247 bytes are the zero-terminated display-name pool.
The block is stored directly, without the v3 transform.

The selected game configures 100 replay-pair slots, so block 4 is `0x00c8`
bytes. Block 5 uses the common variable-length logic-resume grammar.

## Profile 2.917 observed PQ1 blocks

PQ1 uses the same `0x05e1` block-1 partition. Block 2 contains 20 consecutive
object records. Block 3 is `0x016e` bytes: 25 three-byte inventory entries
followed by a 291-byte display-name pool. The selected game configures 250
replay pairs, so block 4 is `0x01f4` bytes. Block 5 uses the common grammar.

## Profile 2.936 observed KQ3 blocks

KQ3 uses the same `0x05e1` block-1 partition. Block 2 contains 17 consecutive
object records. Block 3 is `0x0307` bytes: 55 three-byte inventory entries
followed by a 610-byte display-name pool. The selected game configures 127
replay pairs, so block 4 is `0x00fe` bytes. Block 5 uses the common grammar.

## Profile 3.002.086 observed full KQ4 blocks

The selected full KQ4 data uses the profile 2.936 block-1 partition and
reserved-state rules exactly. Block 1 is `0x05e1` bytes. The profile's menu
interaction gate and incrementing key-release gate are not fields in this
serialized block.

Block 2 contains 26 consecutive `0x2b`-byte object records. The decoded
inventory metadata header's maximum object index is 25, establishing that
count.

Block 3 is XOR-transformed on disk. Its decoded `0x02c6`-byte payload contains:

| Position | Size | Portable state |
| ---: | ---: | --- |
| `0x0000` | 135 | Forty-five three-byte inventory entries. |
| `0x0087` | 575 | Zero-terminated inventory display-name pool. |

The selected game configures 250 replay-pair slots, so block 4 is `0x01f4`
bytes. Block 5 uses the common variable-length logic-resume grammar.

## Profile 2.936 block 1

Block 1 is exactly `0x05e1` bytes. Its complete partition is:

| Position | Size | Portable state |
| ---: | ---: | --- |
| `0x0000` | 7 | Game/save signature area. |
| `0x0007` | 256 | Variables `v0` through `v255`. |
| `0x0107` | 32 | Packed flags `f0` through `f255`. |
| `0x0127` | 4 | Unsigned 32-bit timer tick count. |
| `0x012b` | 2 | Horizon baseline. |
| `0x012d` | 2 | Reserved word; canonical bytes are `00 00`. |
| `0x012f` | 2 | Movement rectangle left bound. |
| `0x0131` | 2 | Movement rectangle top bound. |
| `0x0133` | 2 | Movement rectangle right bound. |
| `0x0135` | 2 | Movement rectangle bottom bound. |
| `0x0137` | 2 | Object-0/global-direction coupling selector. |
| `0x0139` | 2 | Most recently prepared picture number. |
| `0x013b` | 2 | Movement rectangle enable value. |
| `0x013d` | 2 | Reserved word; canonical bytes are `0f 00`. |
| `0x013f` | 2 | Replay-pair capacity. |
| `0x0141` | 2 | Active replay-pair count. |
| `0x0143` | 156 | Thirty-nine key mappings, each `raw_key:u16le, status:u16le`. |
| `0x01df` | 40 | Ten inactive key-map records outside this profile's 39-entry capacity; canonical contents are all zero. |
| `0x0207` | 4 | Reserved pre-string padding; canonical contents are all zero. |
| `0x020b` | 480 | Twelve script string slots of 40 bytes each. |
| `0x03eb` | 480 | Twelve reserved 40-byte records outside the valid string-slot range; canonical contents are all zero. |
| `0x05cb` | 2 | Derived foreground text attribute. |
| `0x05cd` | 2 | Derived background text attribute. |
| `0x05cf` | 2 | Packed current text/window attribute. |
| `0x05d1` | 2 | Input-line enabled value. |
| `0x05d3` | 2 | Input text row. |
| `0x05d5` | 1 | Prompt-marker character. |
| `0x05d6` | 1 | Reserved byte before following word state; canonical value is zero. |
| `0x05d7` | 2 | Status-line enabled value. |
| `0x05d9` | 2 | Status text row. |
| `0x05db` | 2 | Display base row. |
| `0x05dd` | 2 | Display bottom row. |
| `0x05df` | 2 | Replay checkpoint count. |

The string region contains twelve addressable 40-byte slots. The following
480-byte reserved bank is not an additional set of script-visible slots.

## Profile 2.936 block 2

Block 2 is exactly 21 consecutive object records of `0x2b` bytes each. Object
index `n` occupies block positions `n * 0x2b` through
`n * 0x2b + 0x2a`. Each record has this complete partition:

| Record position | Size | Portable state |
| ---: | ---: | --- |
| `0x00` | 1 | Movement-cadence interval. |
| `0x01` | 1 | Movement-cadence countdown. |
| `0x02` | 1 | Boundary/collision event identifier. |
| `0x03` | 2 | Current left X coordinate. |
| `0x05` | 2 | Current baseline Y coordinate. |
| `0x07` | 1 | Selected view number. |
| `0x08` | 2 | Serialized view-reference token. |
| `0x0a` | 1 | Selected loop number. |
| `0x0b` | 1 | Loop count in the selected view. |
| `0x0c` | 2 | Serialized selected-loop-reference token. |
| `0x0e` | 1 | Selected cel number. |
| `0x0f` | 1 | Cel count in the selected loop. |
| `0x10` | 2 | Serialized selected-cel-reference token. |
| `0x12` | 2 | Serialized previous-cel-reference token. |
| `0x14` | 2 | Serialized render-list-reference token. |
| `0x16` | 2 | Previous or saved left X coordinate. |
| `0x18` | 2 | Previous or saved baseline Y coordinate. |
| `0x1a` | 2 | Selected cel width. |
| `0x1c` | 2 | Selected cel height. |
| `0x1e` | 1 | Movement step size. |
| `0x1f` | 1 | Cel-cycling interval. |
| `0x20` | 1 | Cel-cycling countdown. |
| `0x21` | 1 | Movement direction. |
| `0x22` | 1 | Autonomous motion mode. |
| `0x23` | 1 | Cel-cycling mode. |
| `0x24` | 1 | Priority/control byte. |
| `0x25` | 2 | Object state flags. |
| `0x27` | 4 | Mode-dependent motion parameters. |

The five reference tokens are serialized profile data, not portable object
identity. Successful restore keeps the selected view, loop, and cel numbers,
then reconstructs their references, loop/cel counts, and cel dimensions from
the loaded view resource. It reconstructs drawing-list participation from the
saved flags and then restores the saved flag word. The event identifier is
normalized to the object's table index. A clean runtime may organize these
associations differently; it must reproduce that rebuilt state and subsequent
behavior rather than expose the token values.

## Profile 2.936 block 3

Block 3 is the `runtime_inventory_data` from the game's decoded inventory
metadata file. Its length, item count, and name-pool boundary are therefore
game-data properties rather than universal constants of the interpreter
profile.

For the observed game data it is exactly `0x0148` bytes:

| Position | Size | Portable state |
| ---: | ---: | --- |
| `0x0000` | 120 | Forty three-byte inventory entries. |
| `0x0078` | 208 | Zero-terminated inventory display-name pool. |

Each three-byte entry contains `name_offset:u16le, location:u8`. The name offset
is relative to block 3 and must select a zero-terminated name in the name pool.
Multiple entries may share a name offset. Item number is the entry index.

The location byte is the mutable inventory state used by logic actions; `0xff`
means carried. The name offsets and name pool originate in the game metadata
and remain part of the serialized block. The block length is the decoded
inventory metadata file length minus its three-byte header.

## Profile 2.936 block 4

Block 4 is exactly 100 consecutive two-byte `(kind, value)` replay-pair slots.
The active count in block 1 selects the prefix that participates in replay.
Slots after that prefix are inactive capacity and must not be executed. The
checkpoint count in block 1 is also measured in pairs and identifies an earlier
active-prefix length.

The capacity value in block 1 and the block-4 byte length must agree for valid
profile state: `block_4_length = replay_capacity * 2`.

## Profile 2.936 block 5

Block 5 is a variable-length sequence of four-byte logic-resume records:

```text
logic_number:u16le
resume_offset:u16le
```

The block contains:

1. A leading cache-head record, observed as `(0, 0)`.
2. One record for each cached logic, in cache order.
3. A final record whose logic number is `0xffff`.

The terminator's second word is ignored and need not be zero. Block length is
therefore `(cached_logic_count + 2) * 4` bytes. Nonterminal logic numbers are
zero-extended 8-bit resource numbers. Resume offset is measured from the first
byte of that logic's bytecode, not from a process-specific reference.

This block does not decide which logic resources are restored. The replay
sequence does. Whenever replay loads a logic, restoration scans block 5 from
the beginning and uses the first record with that logic number. The resulting
resume position is:

```text
loaded_logic_bytecode_start + resume_offset
```

No matching record leaves the newly loaded logic at its normal bytecode entry.
Records for logics not loaded by replay have no effect. Duplicate logic numbers
are permitted; only the first match is effective. Consequently the observed
leading `(0, 0)` record would take precedence over a later cached-logic-0 record
if logic 0 were replay-loaded.

## Profile 3.002.102 observed KQ4D demo blocks

The selected KQ4D demo uses the same five-block envelope and the same block-1
positions as profile 2.936 through position `0x05e0`. It appends two v3 fields:

| Position | Size | Portable state |
| ---: | ---: | --- |
| `0x05e1` | 2 | Menu interaction gate. |
| `0x05e3` | 1 | Key-release enqueue gate. |

Block 1 is therefore `0x05e4` bytes. Its 39-entry key map, reserved key-map
tail, twelve valid string slots, reserved string bank, text fields, and replay
checkpoint use the profile 2.936 layout and reserved-state rules.

Block 2 is 16 consecutive object records of `0x2b` bytes each. Block 3 is
XOR-transformed on disk as described below. Its decoded five-byte payload is:

| Position | Size | Portable state |
| ---: | ---: | --- |
| `0x0000` | 3 | One inventory entry: `name_offset:u16le, location:u8`. |
| `0x0003` | 2 | Zero-terminated display-name pool containing `?`. |

The decoded inventory metadata header's maximum object index is 15, establishing
the 16 block-2 records. The selected demo sets replay-pair capacity to one, so
block 4 contains one two-byte `(kind, value)` slot. Block 5 uses the common
variable-length logic-resume grammar.

## Profile 3.002.149 observed Gold Rush blocks

Profile 3.002.149 uses the same five-block envelope and conceptual block roles.
The observed Gold Rush data changes capacities and applies the block-3
transform described below.

Block 1 is `0x0404` bytes in the observed Gold Rush saves. Its complete
partition is:

| Position | Size | Portable state |
| ---: | ---: | --- |
| `0x0000` | 7 | Game/save signature area; a valid signed save begins with `GR\0`. |
| `0x0007` | 256 | Variables `v0` through `v255`. |
| `0x0107` | 32 | Packed flags `f0` through `f255`. |
| `0x0127` | 4 | Unsigned 32-bit timer tick count. |
| `0x012b` | 2 | Horizon baseline. |
| `0x012d` | 2 | Reserved word; canonical bytes are `00 00`. |
| `0x012f` | 2 | Movement rectangle left bound. |
| `0x0131` | 2 | Movement rectangle top bound. |
| `0x0133` | 2 | Movement rectangle right bound. |
| `0x0135` | 2 | Movement rectangle bottom bound. |
| `0x0137` | 2 | Object-0/global-direction coupling selector. |
| `0x0139` | 2 | Most recently prepared picture number. |
| `0x013b` | 2 | Movement rectangle enable value. |
| `0x013d` | 2 | Reserved word; canonical bytes are `0f 00`. |
| `0x013f` | 2 | Replay-pair capacity; observed value is 50. |
| `0x0141` | 2 | Active replay-pair count. |
| `0x0143` | 196 | Forty-nine key mappings, each `raw_key:u16le, status:u16le`. |
| `0x0207` | 4 | Reserved pre-string padding; canonical contents are all zero. |
| `0x020b` | 480 | Twelve script string slots of 40 bytes each. |
| `0x03eb` | 2 | Derived foreground text attribute. |
| `0x03ed` | 2 | Derived background text attribute. |
| `0x03ef` | 2 | Packed current text/window attribute. |
| `0x03f1` | 2 | Input-line enabled value. |
| `0x03f3` | 2 | Input text row. |
| `0x03f5` | 1 | Prompt-marker character. |
| `0x03f6` | 1 | Reserved byte before following word state; canonical value is zero. |
| `0x03f7` | 2 | Status-line enabled value. |
| `0x03f9` | 2 | Status text row. |
| `0x03fb` | 2 | Display base row. |
| `0x03fd` | 2 | Display bottom row. |
| `0x03ff` | 2 | Replay checkpoint count. |
| `0x0401` | 2 | Menu interaction gate. |
| `0x0403` | 1 | Key-release enqueue gate. |

This profile keeps the same twelve string slots as profile 2.936. The expanded
49-slot key map consumes the ten inactive key-map records serialized by the
2.936 profile. The four reserved bytes at `0x0207..0x020a` remain before the
string slots.

Block 2 is 23 consecutive object records of `0x2b` bytes each. Each record uses
the same record layout specified for profile 2.936 block 2. The record count is
derived from the decoded Gold Rush object metadata header: maximum drawable
object index `22` means records for objects `0..22`.

Block 3 is transformed on disk. After applying the profile 3.002.149 transform,
the decoded block is exactly the runtime inventory payload from the decoded
Gold Rush `OBJECT` metadata file. Its decoded length is `0x0713` bytes:

| Position | Size | Portable state |
| ---: | ---: | --- |
| `0x0000` | 393 | One hundred thirty-one three-byte inventory entries. |
| `0x0189` | 1418 | Zero-terminated inventory display-name pool. |

Each three-byte entry has the same `name_offset:u16le, location:u8` format as
profile 2.936 block 3. Name offsets are relative to the decoded block.

Block 4 is 50 consecutive two-byte `(kind, value)` replay-pair slots. The
active count in block 1 selects the prefix that participates in replay, as in
profile 2.936.

Block 5 uses the same four-byte logic-resume record grammar as profile 2.936.
The observed initial Gold Rush saves contain three records: leading `(0, 0)`,
cached logic-0 `(0, 0)`, and terminator `(0xffff, 0)`. As with profile 2.936,
the replay-pair sequence decides which logic resources are loaded; block 5 is
only a resume-offset lookup consulted during replayed logic loads.

## V3 block-3 transform

Profiles 3.002.086, 3.002.102, and 3.002.149 XOR-transform block 3 on disk with
this repeating ASCII key:

```text
Avis Durgan
```

For byte index `i` within block 3:

```text
stored[i] = runtime[i] XOR key[i modulo 11]
```

Saving applies the transform for output and restores the in-memory bytes before
returning. Restoring applies the same transform after reading block 3. Applying
the operation twice returns the original data.

## Save action outcomes

After successful selection, save displays its confirmation state, creates the
slot file, writes the header and all five length-prefixed blocks, closes the
file, restores modal state, and continues after the save action.

Create failure is recoverable: display the directory-full/write-protected
message, restore modal state, and continue. A short write is also recoverable:
close and delete the partial file, display the disk-full message, restore
modal state, and continue.

The last selected/entered save-description buffer can be copied into a logic
string slot. That copy uses at most 31 bytes.

## Restore action outcomes

Cancel and file-open failure are recoverable and continue after the restore
action. A failure while reading any selected save block is fatal after the
restore-error dialog; it does not return to bytecode.

Successful restore:

1. Replaces scalar, parser, object, inventory, replay, logic-resume, display,
   and session state with saved values.
2. Resets transient caches and replays the saved resource sequence with
   recording disabled.
3. Rebinds object views and refreshes picture, objects, menu, status, and input
   presentation.
4. Aborts the current continuation.

Execution therefore resumes through restored logic state rather than from the
instruction following the restore action.

## Restart

Profile 2.411 always requests confirmation. In every other promoted profile,
`f16` skips the prompt and accepts restart immediately. Cancellation continues
after the action; sound has already stopped and normal prompt/input presentation
is restored.

Accepted restart:

- stops sound and erases active input;
- preserves the prior value of `f9` across reset;
- clears transient allocation, resource, replay, menu, object, parser, and
  display state to startup-compatible values;
- reruns initial object/inventory setup;
- sets restarted flag `f6`;
- clears the engine's two timing accumulators;
- reloads configured trace logic when present; and
- aborts the current logic continuation.

Profiles 3.002.086, 3.002.102, and 3.002.149 remember whether the prompt marker
was visible before confirmation. They redraw the marker after accepted restart
and after canceled restart only when it had been visible on entry.

## Process termination

Immediate exit terminates without confirmation. Confirmed exit, game-signature
failure, unrecoverable allocation failure, and restore read failure share the
cleanup path: close the log if open, restore input/timer hooks and the prior
display mode, and terminate with process exit code zero.

## Reserved-state rule

Every byte position in the observed 2.411, 2.440, 2.917, 2.936, 3.002.086,
3.002.102, and 3.002.149 save blocks has a portable field or a reserved-state
assignment.
Valid operations do not read or modify the reserved records and padding as game
state. A newly synthesized save uses their canonical values; restoring and
re-saving an existing save preserves its supplied reserved bytes. Other
interpreter/game profiles require independent save-layout maps before binary
interchange can be claimed.
