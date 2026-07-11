# Version Profiles

AGI compatibility is defined against an interpreter profile. A profile selects
the common rules in this book and any explicitly listed variants. Version
numbers identify observed families; they do not imply that every build with a
similar number has identical behavior.

## AGI 2.411 profile

The 2.411 profile is specified for full-EGA valid-data gameplay. It uses four
split resource directories and direct five-byte-header volume records. Its
valid action range is `0x00..0xa9`; conditions remain `0x00..0x12`.

Configured-message actions `0x97` and `0x98` consume the same four operands as
later profiles: message selector, row, column, and width. Restart action `0x80`
always presents its confirmation prompt; `f16` does not bypass it. The heap
diagnostic omits the later `rm.0, etc.` line.

Picture commands `0xf9` and `0xfa` use the early point-plot profile. Command
`0xf9` consumes and ignores one raw byte. Command `0xfa` reads coordinate pairs
without seed bytes and writes one ordinary pixel per complete pair. It does not
draw shaped or stippled brushes. Other full-EGA picture, view, object, motion,
collision, composition, and refresh behavior follows the common contracts.
Automatic direction-based loop selection uses the four-loop table only for
views with exactly four loops.

The early sound profile has no attenuation-envelope evolution between events.
Only device selector `0` uses one channel and PC-speaker divisor output; every
nonzero selector advances all four channels. Four-channel tone output always
emits both bytes of the tone word. Event attenuation adds the global adjustment
and clamps to `0x0f`, but receives no envelope or device-2 adjustment.

The selected KQ2 data supplies the binary-save dimensions listed in the
persistence chapter.

## AGI 2.440 profile

The 2.440 profile shares the 2.411 resource container, action range, condition
range, configured-message encoding, exact-four-loop selection, early sound
channel selection, absence of attenuation envelopes, and shortened save block
1.

It adds the shaped and stippled `0xf9`/`0xfa` pattern behavior specified in the
picture chapter. Restart action `0x80` proceeds without displaying confirmation
when `f16` is set. Four-channel tone output emits the high tone byte and
suppresses the low byte when the high byte's top three bits are all set. Its
heap diagnostic still omits the later `rm.0, etc.` line.

The selected LSL1 data supplies the binary-save dimensions listed in the
persistence chapter.

The observed 2.439 build has the same action and condition contracts as 2.440.
Every uniquely mapped full-EGA renderer, object, motion, restart, save,
picture-pattern, and sound routine has the same behavior after relocation.
It therefore selects the 2.440 behavioral rules for those domains. Its
selected game data supplies different save dimensions.

## AGI 2.917 profile

The 2.917 profile is specified for full-EGA valid-data gameplay. It uses the
same split v2 resource container as 2.936. Its valid action range is
`0x00..0xad`; opcodes `0xae` and `0xaf` are not available. Conditions
`0x00..0x12` and every shared action follow the common contracts.

Its picture, view, object, input, sound, room, replay, and primary full-EGA
rendering behavior follow the common core. Automatic direction-based loop
selection uses the two-loop and three-loop tables as specified in the object
chapter, and uses the four-loop table only for a view with exactly four loops.
A view with more than four loops does not receive automatic direction-based
loop selection in this profile.

The selected KQ1 and PQ1 data supply separate binary-save dimensions listed in
the persistence chapter. Those counts and lengths are game-data properties,
not universal constants for every 2.917 game.

The observed 2.915 build has the same action and condition contracts and the
same uniquely mapped full-EGA subsystem behavior as 2.917. The observed second
2.917 build differs from the selected KQ1 interpreter only in its embedded
game signature. Both therefore select this profile, with separate game-data
dimensions.

## AGI 2.936 profile

The 2.936 profile is currently the most complete profile in this specification.
Unless a chapter says otherwise, promoted logic, state, graphics, object,
input, persistence, and sound rules currently refer to this profile.

Its resource container uses four separate directory files and direct resource
records as specified in [Resource Containers](./resource_containers.md).

The valid action opcode range is `0x00..0xaf`. The valid condition opcode range
is `0x00..0x12`, in addition to the structural condition markers described by
the logic-bytecode specification.

The selected SQ2 and KQ3 data supply separate binary-save dimensions listed in
the persistence chapter.

## AGI 3.002.086 profile

The 3.002.086 profile is specified for full-EGA valid-data gameplay from the
full KQ4 release. It uses the combined and compressed v3 resource container.
Its valid action range is `0x00..0xb1`; conditions remain `0x00..0x12`.

Action `0xb0` consumes one ignored byte and otherwise has no effect. Action
`0xb1` sets the menu interaction gate. Shared action `0xad` increments the
key-release event gate modulo 256, as in the v2 profiles. The script key map
holds 39 entries. Immediate room destinations are not remapped, and input-width
actions `0xa3` and `0xa4` retain their v2 effects.

Its inventory-selector temporary state, block-3 save transform, restart
prompt-marker handling, and motion-mode-4 preservation follow the later v3
profiles. Its automatic direction-based loop selection follows 2.936: every
view with four or more loops uses the four-direction table without an `f20`
gate.

This profile has one screen-boundary variant. A due movement proposal whose
left X coordinate is exactly zero is clamped to zero and reports left-boundary
code 4. Later promoted profiles accept exact zero without reporting a boundary;
both behaviors clamp negative proposals to zero and report code 4.

The selected full KQ4 data supplies the binary-save dimensions listed in the
persistence chapter. Present-looking directory entries whose selected volume
files are absent are outside this valid-data profile.

## AGI 3.002.149 profile

The 3.002.149 profile uses the combined and compressed v3 resource container.
Expanded logic, picture, view, and sound payloads retain the same resource
families as the 2.936 profile.

This profile accepts action slots through `0xb5`. Slots `0xb0`, `0xb2`,
`0xb3`, and `0xb4` consume their declared operands and otherwise have no
effect. The additional observable actions are:

| Opcode | Operands | Behavior |
| ---: | --- | --- |
| `0xb1` | one immediate byte | Set the menu interaction gate. Zero prevents a pending menu request from entering modal menu interaction; nonzero permits it. |
| `0xb5` | none | Clear the key-release event gate. |

For this profile, shared action `0xad` sets the key-release event gate instead
of incrementing it. The script key-map holds 49 entries rather than 39.

Immediate room-switch action `0x12` normally passes its destination to the
ordinary room-change operation unchanged. The observed Gold Rush build adds a
game-specific alias: destination values `0x7e`, `0x7f`, and `0x80` select room
`0x49`. The observed MH2 build has the same 3.002.149 core but does not apply
these aliases. A conformance claim must identify which build variant it uses.

The object-and-inventory portion of a saved game uses a profile-specific XOR
transform. The save envelope and transform bytes are specified in the
persistence chapter. The observed Gold Rush save block layout is byte-mapped
there, including canonical and byte-preserving rules for reserved serialized
state.

Input-width actions `0xa3` and `0xa4` have no effect in this profile. Normal
EGA text input remains available without those width-control branches. Action
`0xa9` still restores active saved-window state but has no input-width override
to clear.

For automatic direction-based loop selection, exactly-four-loop views retain
the 2.936 four-or-more-loop behavior. Views with more than four loops apply
that selection table only while `f20` is set.

## AGI 3.002.102 profile

The 3.002.102 profile is specified for full-EGA valid-data gameplay. Its
expanded picture and view formats, picture command execution, logical raster
rules, view/cel composition, object update lists, placement, collision,
movement, animation, and refresh ordering follow the common behavioral core.
Alternate display-mode branches remain outside the current target.

This profile uses the combined and compressed v3 resource container and accepts
action slots through `0xb5`. Its extra slots `0xb0..0xb5` have the same operand
contracts and effects specified above for 3.002.149, including the menu gate
and release-gate clear action. Shared action `0xad` sets the release gate to one.

Unlike 3.002.149, its script key map holds 39 entries, immediate room-switch
destinations are not remapped, and input-width actions `0xa3` and `0xa4` retain
their 2.936 effects. Closing text-window state also clears the input-width
override. Its restart prompt-marker branch, object motion-mode-4 preservation,
inventory-selector temporary state, and block-3 save transform follow the
3.002.149 variants.

Automatic direction-based loop selection follows the 3.002.149 rule: exactly
four loops use the direction table unconditionally, while views with more than
four loops require `f20`.

The selected KQ4D demo data supplies the save dimensions listed in the
persistence chapter. Those dimensions are game data, not universal constants
for every 3.002.102 game.

The observed 3.002.107 build has the same action and condition contracts as
3.002.102. Every currently mapped full-EGA core routine has the same behavior
after relocation. Unmapped startup and alternate paths remain outside that
equivalence statement.

## AGI 2.089 partial profile

The observed 2.089 build uses the split direct-resource container, but stores
its inventory metadata file in expanded plain form instead of applying the
later repeating-key transform. It accepts actions `0x00..0x9a` and conditions
`0x00..0x12`.

Action `0x86` consumes no operand. It stops active sound, performs process
shutdown cleanup, and terminates without asking for confirmation. Actions
`0x9b` and later are unavailable.

Position actions `0x25` and `0x26` first change the object's current position.
If the object is currently drawn, they remove its old rendered state, then
copy the new coordinates into its previous-position snapshot. This differs in
ordering from 2.272.

The earlier-drawn object partition is composed in ascending object-number
order, regardless of baseline or fixed-priority drawing key. The later-drawn
partition is composed in ascending drawing-key order with object number as the
tie breaker. This is the ordering exception defined in the object chapter;
2.272 sorts both partitions.

Pictures support commands only through seed fill `0xf8`. Automatic
direction-loop selection is evaluated on every eligible post-logic pass and
uses the four-direction table only for exactly four loops. The profile exposes
six string slots. Its word-sequence condition requires an exact operand/parser
count and does not give `0x270f` tail-terminator meaning.

Showing a prepared picture presents it and marks it shown, but does not clear
`f15` or close an active text window. Object-distance action `0x45` stores the
low byte of the center-X-plus-baseline-Y distance; values above `255` wrap
instead of saturating at `254`. Target-motion actions `0x51` and `0x52` defer
their first direction calculation and already-satisfied completion until the
next eligible target-motion update.

Action `0x4d` clears direction but leaves autonomous-motion mode unchanged.
For object 0 it also clears `v6` and selects object-to-`v6` coupling. Action
`0x4e` leaves both direction and autonomous-motion mode unchanged. For object
0 it clears `v6`, selects `v6`-to-object coupling, and clears the remembered
navigation event used by the old movement pass.

The inventory display action always shows an acknowledgement-only carried-item
list. It does not inspect the inventory-interaction flag and does not modify
`v25`.

Sound event scheduling and channel participation follow the early profile in
the sound chapter. Four-channel events emit both tone bytes and use the 2.089
control-byte rule, including its device-2 adjustment. The selected SQ1 data uses 17 runtime object records:
this profile treats the metadata header's object value as a count, not as a
maximum index. Saves use the four-block 2.089 envelope specified in the
persistence chapter. Other domains are not yet broad enough for a full 2.089
gameplay-conformance claim.

## AGI 2.272 partial profile

The observed 2.272 build uses the split direct-resource container and stores
inventory metadata in expanded plain form. It accepts actions `0x00..0xa0`
and conditions `0x00..0x12`.

Action `0x86` consumes one selector byte. Selector `1` terminates immediately;
other values display a confirmation request and terminate only when accepted.
Action `0x9b` consumes two bytes without changing state. Actions `0x9c` through
`0xa0` consume the same operands as the later menu actions but otherwise do
nothing; this profile parses menu-construction bytecode without constructing a
menu.

Position actions `0x25` and `0x26` write both current and previous-position
coordinates directly and do not first remove an already drawn object.

Pictures support commands only through `0xf8`. Automatic direction-loop
selection is evaluated independently of cadence and uses the four-direction
table only for exactly four loops. The profile exposes six string slots and
already recognizes `0x270f` as the word-sequence tail terminator.

Showing a prepared picture, object-distance overflow, and initial target-motion
calculation follow the same early rules as profile 2.089. Action `0x4d` has the
later behavior of clearing both direction and autonomous-motion mode. Action
`0x4e` clears autonomous-motion mode while retaining direction.

Inventory display is acknowledgement-only and leaves `v25` unchanged, as in
profile 2.089. The interactive inventory selector is not available.

Both object partitions are composed in ascending drawing-key order, with
object number breaking ties. Early sound scheduling uses one channel only for
device selector zero and otherwise advances all four. Four-channel events emit
both tone bytes and use the device-2 plus whole-byte adjustment rule in the
sound chapter. The selected XMAS data uses 18 runtime object records and the
five-block 2.272 save envelope. Other domains are not yet broad enough for a
full 2.272 gameplay-conformance claim.

## Other observed versions

Other versions have been identified, but they do not yet have normative
profiles in this book. Similarity to a profile above must not be assumed until
observable differences have been checked and promoted into the specification.
