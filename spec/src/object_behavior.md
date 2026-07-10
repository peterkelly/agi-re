# Object Behavior

This chapter defines persistent drawable-object lifecycle, placement,
animation, movement, collision, control acceptance, and drawing order. Cel
pixels and per-pixel priority composition are defined in
[View Resources and Cel Drawing](./view_resources.md).

## Object lifecycle

Each object has independent active, update-eligible, automatic-cycling, and
update-partition state.

Resetting an object for animation has no effect if it is already
update-eligible. Otherwise it:

- enables update eligibility and automatic cel cycling;
- selects the later-drawn update partition; and
- clears direction, autonomous motion mode, and cel-cycling mode.

Clearing all objects clears active and update-eligible state from every object.

Activation requires a selected cel. It places the object at an acceptable
position, snapshots its current cel and position, marks it active in the
later-drawn partition, rebuilds the affected drawing state, and refreshes its
visible area. Activating an already active object has no additional effect.

Deactivation restores/removes the object's drawn contribution, clears active
state, rebuilds the affected drawing state, and refreshes the exposed area.
Deactivating an inactive object has no additional effect.

## Priority and horizon

Unless fixed priority is enabled, an object's drawing priority is derived from
its baseline Y through a 168-entry table. The default table is:

| Baseline rows | Priority |
| --- | ---: |
| 0..47 | 4 |
| 48..59 | 5 |
| 60..71 | 6 |
| 72..83 | 7 |
| 84..95 | 8 |
| 96..107 | 9 |
| 108..119 | 10 |
| 120..131 | 11 |
| 132..143 | 12 |
| 144..155 | 13 |
| 156..167 | 14 |

The priority-table rebuild action replaces this mapping as described in the
logic action catalog. Fixed priority bypasses baseline derivation for drawing
and priority acceptance. A fixed value of `15` also bypasses the movement
control scan described below.

The default horizon is baseline Y `36`. A nonexempt object must have a baseline
strictly greater than the horizon. Placement first changes an initial baseline
at or above the horizon to `horizon + 1`. Horizon-exempt objects do not receive
that restriction.

## Placement search

A position is within geometric bounds when all of these are true:

```text
left >= 0
left + cel_width <= 160
baseline_y - cel_height >= -1
baseline_y <= 167
baseline_y > horizon, unless horizon-exempt
```

The third condition is equivalent to the cel's top row being at least zero.

Placement tests the requested position first. A candidate is accepted only if
it is geometrically valid, passes object-object collision, and passes the
priority/control footprint scan. If rejected, candidates are visited in this
widening spiral from the requested position:

```text
left 1, down 1, right 2, up 2,
left 3, down 3, right 4, up 4, ...
```

The first accepted candidate becomes the object's position. Valid game state
is expected to provide an acceptable candidate.

## Cycle ordering and cadence

Object work occurs in two phases around logic execution:

1. Before logic 0, eligible objects whose movement-cadence countdown is
   exactly `1` update their autonomous motion direction. The configured
   movement-rectangle transition check also runs in this phase.
2. After logic 0, eligible objects perform automatic loop selection and cel
   timing, then apply movement, redraw, and visible refresh.

The movement pass processes active, update-eligible objects in the later-drawn
partition. If an object's cadence countdown is nonzero, decrement it. Skip the
movement unless that decrement reaches zero. When movement is due, reload the
countdown from its cadence interval before applying the proposed step. A zero
countdown is already due.

A newly positioned object suppresses its direction delta for one due movement
pass and then clears the newly-positioned state.

## Direction and automatic loop selection

Direction values and coordinate deltas are:

| Value | Direction | X delta per step | Baseline-Y delta per step |
| ---: | --- | ---: | ---: |
| 0 | stationary | 0 | 0 |
| 1 | up | 0 | -step |
| 2 | up-right | +step | -step |
| 3 | right | +step | 0 |
| 4 | down-right | +step | +step |
| 5 | down | 0 | +step |
| 6 | down-left | -step | +step |
| 7 | left | -step | 0 |
| 8 | up-left | -step | -step |

When automatic loop selection is enabled and the cadence countdown is `1`,
the direction may select a loop before cel timing.

For views with two or three loops:

| Direction | Selected loop |
| ---: | ---: |
| 2, 3, 4 | 0 |
| 6, 7, 8 | 1 |
| 0, 1, 5 | no change |

For views with four or more loops:

| Direction | Selected loop |
| ---: | ---: |
| 2, 3, 4 | 0 |
| 6, 7, 8 | 1 |
| 5 | 2 |
| 1 | 3 |
| 0 | no change |

In profile 3.002.149, exactly-four-loop views always use the second table.
Views with more than four loops use it only while `f20` is set; otherwise the
selected loop does not change automatically. Profile 2.936 does not apply this
extra gate.

## Cel cycling

Automatic cel cycling has an independent interval and countdown. When cycling
is enabled and its countdown is nonzero, decrement it during the post-logic
object phase. When it reaches zero, perform the selected cycling mode and
reload the countdown from the interval.

| Mode | Transition |
| --- | --- |
| forward wrap | Increase the cel index; wrap after the last cel to cel 0. |
| forward completion | Increase toward the last cel. On reaching it, set the completion flag, disable cycling, clear direction, and return the mode to forward wrap. |
| backward wrap | Decrease the cel index; wrap before cel 0 to the last cel. |
| backward completion | Decrease toward cel 0. On reaching it, or when already at cel 0, set the completion flag, disable cycling, clear direction, and return the mode to forward wrap. |

Starting either completion mode installs a one-callback delay. The first
otherwise-due cycling callback clears that delay without changing the cel.
Explicitly selecting a cel removes the delay.

## Movement proposal and screen boundaries

When movement is due, add the direction delta to the current position, then
clamp the proposed position in this order-independent set of bounds:

| Boundary | Clamped coordinate | Code |
| --- | --- | ---: |
| top | `baseline_y = cel_height - 1` | 1 |
| horizon, when nonexempt | `baseline_y = horizon + 1` | 1 |
| right | `left = 160 - cel_width` | 2 |
| bottom | `baseline_y = 167` | 3 |
| left | `left = 0` | 4 |

The clamped proposal is then tested for object collision and footprint control
acceptance. If either rejects it, restore the prior coordinates, discard the
boundary code, and run placement search from the restored position.

If a boundary code survives for an object whose event identifier is zero,
store it in `v2`. Otherwise store the object's event identifier in `v4` and the
boundary code in `v5`. A target-motion object reaching a surviving screen
boundary completes its target motion.

## Object-object collision

Collision is bypassed when the moving object has collision exemption enabled.
Otherwise compare it with every active, update-eligible object that is not
collision-exempt and has a different event identifier.

The horizontal spans overlap unless either of these is true:

```text
moving_left + moving_width < other_left
moving_left > other_left + other_width
```

Equality therefore counts as overlap: objects are rejected before their edges
would touch under the conventional `left + width - 1` interpretation.

For horizontally overlapping objects, a collision occurs when any of these is
true:

- their current baselines are equal;
- the moving baseline is now greater than the other baseline and its saved
  baseline was strictly less than the other's saved baseline; or
- the moving baseline is now less than the other baseline and its saved
  baseline was strictly greater than the other's saved baseline.

Thus strict vertical-order reversal counts as crossing. Merely sharing a saved
baseline and then moving apart does not satisfy the crossing test.

## Footprint control acceptance

Unless priority is fixed, first derive it from the current baseline. Priority
`15` bypasses this entire scan and accepts the footprint.

Otherwise scan the logical priority/control values at the object's baseline
from left to right for exactly the cel width. Each cell replaces the current
classification state; classes encountered earlier are not latched.

| Cell value | Immediate effect and resulting state |
| ---: | --- |
| 0 | Reject immediately. |
| 1 | Reject immediately unless the object ignores movement-rectangle restrictions; when allowed, continue with both class-state flags clear. |
| 2 | Continue with class-state flag 3 set and flag 0 clear. |
| 3 | Continue with class-state flag 3 clear and flag 0 set. |
| 4..15 | Continue with both class-state flags clear. |

After the complete scan:

- the first optional post-scan gate rejects when class-state flag 0 is clear;
- the second optional post-scan gate rejects when class-state flag 0 is set;
- enabling both gates therefore rejects every non-bypassed complete scan; and
- for event-identifier-zero objects, script flags `f3` and `f0` receive the
  final class-state values.

The logic actions historically associated with control classes 2 and 3 enable
the first and second post-scan gates respectively. Their exact behavior is the
final-cell state rule above, not an encountered-anywhere test.

## Configured movement rectangle

The global movement rectangle classifies a baseline point `(x,y)` as inside
only when all comparisons are strict:

```text
left < x < right
top < y < bottom
```

During the pre-logic phase, an object with nonzero direction and rectangle
enforcement enabled compares its current baseline point with the next point
computed from direction and step size. If exactly one is inside, the object:

- records a rectangle-transition state;
- clears its direction; and
- if it is object 0, clears `v6`.

An object configured to ignore movement-rectangle restrictions skips this
transition check. The same option permits control value 1 during footprint
acceptance.

## Target motion

Starting target motion stores the target, saves the current step size, clears
the completion flag, and temporarily adopts a nonzero step override. A zero
override preserves the current step size.

Each target-direction calculation uses signed delta
`target_coordinate - current_coordinate`. For band `s`, classify a delta as
negative when `delta <= -s`, near only when `-s < delta < s`, and positive
when `delta >= s`. Exact equality with either band edge is therefore not near.
The X and Y classes select a direction from this grid:

| Target relation | left | within X step | right |
| --- | ---: | ---: | ---: |
| above | 8 | 1 | 2 |
| within Y step | 7 | 0 | 3 |
| below | 6 | 5 | 4 |

For target motion, `s` is the current step size. Direction zero completes the
mode immediately: restore the saved step size,
set the completion flag, clear the autonomous mode, and leave direction zero.
Movement need not land on the exact target when the remaining distance is
within one step.

The start action performs a target-direction calculation immediately.
Subsequent automatic recalculation occurs in the pre-logic phase only when the
object's movement-cadence countdown equals `1`. Without that cadence state, a
one-shot call leaves the initial direction active and the object can continue
past an internal target until another event, commonly a screen boundary,
stops it. Reissuing the start action while the completion flag is clear also
recalculates direction each script cycle.

## Approach and random motion

The rules below use `random_word()` as the profile's next unsigned random
value. The seed and generator timing are nondeterministic conformance inputs;
all reductions and rejection loops after obtaining a value are normative.

Approach motion aims the object's horizontal center and baseline toward object
0's center and baseline. It uses the action's near threshold as band `s` in
the strict target-direction calculation above. Direction zero clears the
motion mode and sets the completion flag.

The approach retry-delay byte starts at `255`. On the first noncomplete
direction update, replace `255` with zero and use the direct direction. On
later updates:

1. If the previous refresh marked the object stationary, repeatedly calculate
   `random_word() modulo 9` until the result is nonzero and use that as a
   temporary direction.
2. Calculate
   `distance = floor((abs(center_x_delta) + abs(baseline_y_delta)) / 2) + 1`.
3. If `distance <= step`, set retry delay to `step`. Otherwise repeatedly
   calculate `random_word() modulo distance` until the result is at least
   `step`, then use that result as the delay.
4. A stationary-recovery update returns with the temporary direction and new
   delay; it does not decrement the delay immediately.
5. On a later nonstationary update with nonzero delay, subtract the step as an
   eight-bit value. Keep the wrapped result when the signed eight-bit
   subtraction is greater than or equal to zero; otherwise replace it with
   zero. Keep the temporary direction for that update.
6. On a nonstationary update whose delay was already zero, replace the
   temporary direction with the newly calculated direct direction.

Random motion has its own byte countdown. On every eligible direction update,
save the old countdown and decrement it modulo 256. If the old value was
nonzero and the object was not marked stationary, retain the current direction
and decremented countdown. Otherwise:

1. Set direction to `random_word() modulo 9`, allowing stationary direction
   zero.
2. Repeatedly calculate `random_word() modulo 51` until the result is at least
   `6`, then store that value as the new countdown.

Both modes remain subject to cadence, screen bounds, collision, footprint
acceptance, and drawing rules elsewhere in this chapter.

## Drawing order and refresh

All objects in the earlier partition draw before every object in the later
partition. Within one partition, objects draw in ascending drawing-key order,
with object number breaking ties in ascending order. Later draws may cover
earlier equal-priority pixels under the cel composition rules.

For baseline-priority objects, the drawing key is baseline Y. In the promoted
2.936 table mode, a fixed priority of zero maps before row 0 and a positive
fixed priority maps to key 168, after ordinary baseline rows. No observed
2.936 state enables the alternate direct fixed-priority formula.

Before rebuilding a frame, prior object rectangles are restored. Objects are
then drawn in the order above. Visible refresh covers the union of each
object's previous and current cel rectangles, so changing position, dimensions,
or cel exposes the old area and presents the new one in the same update.
