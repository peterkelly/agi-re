# Version Profiles

AGI compatibility is defined against an interpreter profile. A profile selects
the common rules in this book and any explicitly listed variants. Version
numbers identify observed families; they do not imply that every build with a
similar number has identical behavior.

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

The selected KQ1 data supplies the binary-save dimensions listed in the
persistence chapter. Those counts and lengths are game-data properties, not
universal constants for every 2.917 game.

## AGI 2.936 profile

The 2.936 profile is currently the most complete profile in this specification.
Unless a chapter says otherwise, promoted logic, state, graphics, object,
input, persistence, and sound rules currently refer to this profile.

Its resource container uses four separate directory files and direct resource
records as specified in [Resource Containers](./resource_containers.md).

The valid action opcode range is `0x00..0xaf`. The valid condition opcode range
is `0x00..0x12`, in addition to the structural condition markers described by
the logic-bytecode specification.

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

Immediate room-switch action `0x12` maps destination values `0x7e`, `0x7f`,
and `0x80` to room `0x49` before performing the ordinary room change. Other
destination values are unchanged.

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

## Other observed versions

Other versions have been identified, but they do not yet have normative
profiles in this book. Similarity to a profile above must not be assumed
until observable differences have been checked and promoted into the
specification.
