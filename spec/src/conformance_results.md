# Conformance Results

This chapter defines a portable result format for comparing an implementation
with reference observations. It is a test interchange convention, not a
requirement on an implementation's internal renderer, state layout, or test
framework.

## Bundle envelope

A result bundle is a UTF-8 JSON object with these fields:

| Field | Meaning |
|---|---|
| `format` | The literal `agi-clean-room-conformance-results`. |
| `format_version` | Integer `1` for this format. |
| `suite_id` | Stable identifier for the selected case set. |
| `profile` | Interpreter behavior profile claimed by the producer. |
| `producer` | Human-readable identifier for the producing engine or oracle. |
| `cases` | Array of case result objects. |

Each case has a stable string `id`, a `status`, and zero or more observations.
Status `ok` means the producer completed the case and emitted all required
observations. A producer may use `error` when execution or observation failed;
an error does not constitute a behavioral mismatch and cannot satisfy the
case.

Case identifiers are unique within a bundle. A comparison requires every
reference case. A missing case, an unexpected additional case, an error, or a
different deterministic observation is a failed comparison.

## Canonical visual frame

The `frame` observation represents the visible game area after the case's
specified synchronization point. It has these fields:

| Field | Required value |
|---|---|
| `width` | `160` |
| `height` | `168` |
| `pixel_format` | `ega16-indexed-row-major` |
| `sha256` | Lowercase hexadecimal SHA-256 digest of the canonical bytes. |
| `artifact` | Optional path, relative to the bundle, containing those bytes. |

The artifact contains exactly 26,880 bytes with no header. Each byte is one
EGA palette index in the range 0 through 15. Bytes proceed left to right, then
top to bottom. Coordinate `(0, 0)` is the upper-left pixel of the 160 by 168
game area. The format contains logical pixels, independent of host window
size, display scaling, aspect-ratio correction, or RGB palette calibration.

The digest is sufficient for an exact match. When both bundles provide valid
artifacts, a comparator may additionally report the number and bounding box of
differing logical pixels. Producers must verify that an artifact's digest
matches its declared `sha256` before comparing it.

## Nondeterministic cases

Only cases with one required deterministic observation belong in a strict
digest-based suite. Behavior that permits multiple outcomes requires a case
specific acceptance rule or a controlled input such as a supplied random
choice. An exploratory observation must not be converted into a deterministic
failure merely by recording one reference run.

For example, autonomous random motion permits a stationary result when the
selected direction is zero. Such an unconstrained run is not part of the
strict visual-frame suite. A test that supplies the random choice, or that
tests a deterministic transition such as clearing random motion before the
next movement update, may be included.

An implementation in any language conforms to the interchange convention when
it emits the fields and canonical frame bytes defined above. No particular
adapter, executable, or test framework is required.
