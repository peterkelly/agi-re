# Rooms, Replay, and Persistence

This chapter defines room transitions, the resource replay sequence, restart,
save/restore selection, and the known save-file envelope. Save-state semantics
are normative where mapped; opaque serialized portions are identified
explicitly rather than described through an original memory layout.

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

For profile 2.936, observed block lengths are:

| Block | Length |
| ---: | ---: |
| 1 | 1505 (`0x05e1`) |
| 2 | 903 (`0x0387`) |
| 3 | 328 (`0x0148`) |
| 4 | 200 (`0x00c8`) |
| 5 | Variable. |

For profile 3.002.149, the observed Gold Rush state uses lengths `1028`,
`989`, `1811`, `100`, and `12`.

The envelope, lengths, signature prefix, and mapped subsystem effects are
normative. A field-by-field portable encoding for every byte inside blocks 1
through 5 is not yet complete; binary interchange claims must not treat the
conceptual list above as a byte-offset map.

## Profile 3.002.149 block transform

Profile 3.002.149 XOR-transforms block 3 on disk with this repeating 59-byte
key:

```text
1e 2a e4 01 46 fc eb 4f 8a 44 1e 2a e4 01 46 fc
8a 44 1e 2a e4 01 46 fa eb 3d 8a 44 1e 2a e4 29
46 fc eb ec 8a 44 1e 2a e4 29 46 fc eb 29 8a 44
1e 2a e4 29 46 fc eb b2 48 3d 07
```

For byte index `i` within block 3:

```text
stored[i] = runtime[i] XOR key[i modulo 59]
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

Restart may request confirmation unless `f16` skips it. Cancellation continues
after the action; sound has already stopped and normal prompt/input
presentation is restored.

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

Profile 3.002.149 remembers whether the prompt marker was visible before
confirmation. It redraws the marker after accepted restart and after canceled
restart only when it had been visible on entry.

## Process termination

Immediate exit terminates without confirmation. Confirmed exit, game-signature
failure, unrecoverable allocation failure, and restore read failure share the
cleanup path: close the log if open, restore input/timer hooks and the prior
display mode, and terminate with process exit code zero.

## Remaining persistence gap

To claim complete binary save compatibility, each byte in all five state blocks
must be mapped to portable state, including padding and profile-specific
fields. Current conformance can cover selector behavior, envelope parsing,
known lengths, signatures, replay reconstruction, the v3 block transform, and
observable restore/restart state transitions, but not arbitrary save exchange
with an independently organized implementation.
