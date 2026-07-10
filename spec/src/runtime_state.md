# Core Runtime State

This chapter defines the portable state shared by the behavior in later
chapters. It describes values and lifetimes, not a required memory layout.

Unless a version profile says otherwise, the rules in this chapter currently
apply to the AGI 2.936 profile.

## Byte variables

The game has 256 variables, numbered `v0` through `v255`. Each stores an
unsigned 8-bit value.

The common numeric operations have these value rules:

- increment saturates at `255`;
- decrement saturates at `0`;
- addition and subtraction retain the low 8 bits;
- multiplication retains the low 8 bits of the product;
- division stores the unsigned 8-bit quotient; and
- indirect operations use a variable's value as the index of another
  variable.

Unsigned variable comparisons compare values in the range `0..255`.
Division by zero is outside the valid-bytecode contract until a defined
observable result is added to this specification.

Some variables also have engine-defined roles. Those roles do not change the
fact that scripts may read and write the same byte. In the current profile,
`v0` identifies the current room and `v10` controls cycle pacing.

## Flags

The game has 256 Boolean flags, numbered `f0` through `f255`. Operations may
set, clear, toggle, or test a flag directly, or use a byte variable as the flag
number.

Some flags also carry engine-defined state. For example, sound playback tests
`f9`, and room entry logic commonly tests a new-room flag. A subsystem chapter
defines the observable meaning whenever an engine operation assigns one.

## Strings and parsed words

The current profile exposes twelve string slots, numbered `s0` through `s11`.
Each slot has 40 bytes of storage. Operations that edit, copy, compare, or parse
a slot define their own truncation and normalization rules.

Parsed input is distinct from string storage. The parser produces at most ten
nonzero dictionary word identifiers, an optional unknown-word position, and
parser status flags. Words whose dictionary identifier is zero do not occupy a
parsed-word slot. Conditions that match parsed input consume this parsed state,
not the original string bytes.

## Logic activations

A loaded logic resource consists of bytecode, messages, and resumable execution
state. The engine tracks a current logic activation containing at least:

- the logic resource number;
- the bytecode start;
- the current instruction position; and
- the resource's message table.

Logic 0 is invoked once per top-level engine cycle. A logic may call another
logic. Nested calls preserve the caller's current activation and restore it
when the callee returns.

Loading and executing are separate operations. A logic may remain loaded after
execution, while a logic loaded only for a nested call may be discarded when
that call returns. Explicit resume-position operations may save the current
instruction position and later restore the logic's entry position.

## Resource lifecycle

Each resource family has an independent loaded-resource set keyed by resource
number. The portable lifecycle is:

| State | Meaning |
| --- | --- |
| Unloaded | The resource has no payload available to consumers. |
| Loaded | Directory lookup, volume reading, and expansion have produced the typed resource payload. |
| Selected | A logic activation, picture operation, object, or sound operation is using the loaded resource. |
| Discarded | The resource is no longer loaded; a later use requires another load. |

Loading an already loaded resource does not create a second game-visible
identity. Discarding or resetting a family invalidates later use until the
resource is loaded again.

Room changes clear transient resource and object state, load the destination
logic, update the current-room variables, and establish new-room state. The
resource-event replay used by restore is specified separately from ordinary
loading because replay must rebuild selected resources without recursively
recording the replay itself.

## Objects and inventory items

Persistent drawable objects are identified by an unsigned byte index. Their
portable state includes:

- current and previous position;
- selected view, loop, and cel;
- cel width and height;
- step size and direction;
- animation interval and animation mode;
- motion mode and mode-specific parameters;
- priority and control behavior;
- participation in update and draw processing; and
- collision, horizon, cycling, and direction-selection options.

The original storage representation is not part of this specification. Object
operations are defined in terms of the fields and transitions above.

Inventory items have an item number, display name, and one-byte location or
state value. Location value `0xff` means the item is carried for the inventory
selection operation.

## Logical graphics state

The full-EGA target uses a logical picture area 160 cells wide and 168 cells
high. Each cell has two independent four-bit values:

- a visual color in `0..15`; and
- a priority/control value in `0..15`.

Picture commands may modify either or both values. View cels contribute visual
color and object priority according to the drawing rules. Normal display output
shows the visual values; diagnostic priority display exposes the
priority/control values.

The logical resolution is the compatibility coordinate system. A display
backend may scale those cells to physical pixels as long as the resulting
logical image and input coordinate behavior are preserved.

## Top-level cycle order

One engine cycle has this observable order:

1. Process pending input, sound ticks, display maintenance, and cycle pacing.
2. Perform the pre-logic autonomous motion and configured-boundary pass for
   eligible objects.
3. Execute logic 0, including any nested logic calls made by that bytecode.
4. When object updating is enabled for the cycle, perform direction-based loop
   selection, animation timers, object movement, drawing, and dirty-region
   refresh.

`v10` is the cycle-speed value. The pacing stage waits until at least that many
timer increments have accumulated and then begins a new accumulation period.
Lower values therefore permit faster logic cycles. A host may use a different
clocking mechanism, but script-visible ordering and relative pacing must remain
equivalent.

Calling the current room logic is not an implicit fifth engine stage. Games
normally perform that dispatch from logic 0, commonly by calling the logic
whose number is stored in `v0`.
