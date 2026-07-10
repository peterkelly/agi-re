# Version Profiles

AGI compatibility is defined against an interpreter profile. A profile selects
the common rules in this book and any explicitly listed variants. Version
numbers identify observed families; they do not imply that every build with a
similar number has identical behavior.

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
transform. The exact save envelope and transform bytes will be specified in the
persistence chapter before save-file conformance is claimed for this profile.

Input-width actions `0xa3` and `0xa4` have no effect in this profile. Normal
EGA text input remains available without those width-control branches.

## Other observed versions

Other versions have been identified, but they do not yet have normative
profiles in this book. Similarity to either profile above must not be assumed
until observable differences have been checked and promoted into the
specification.
