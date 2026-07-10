# Scope and Conformance

## Behavioral boundary

This specification describes behavior that can be observed by valid AGI game
data, by a player providing input, or through an engine-produced artifact such
as rendered output, sound events, or a saved game.

The behavioral contract includes, where applicable:

- accepted resource and bytecode formats;
- game-visible variables, flags, strings, objects, and inventory state;
- ordering and timing of state transitions;
- logic control flow and operation results;
- picture, view, text, menu, and status-line output;
- keyboard and text-input behavior;
- object movement, animation, collision, and priority behavior;
- sound-event scheduling and completion behavior;
- room changes, restart, save, and restore behavior; and
- observable differences between interpreter versions.

The behavioral contract does not include the original interpreter's addresses,
register use, instruction sequences, overlays, DOS memory organization, heap
layout, routine boundaries, or inferred source-code structure. A conforming
engine may organize its implementation in any way that preserves the specified
observations.

## Current compatibility target

The primary display target is the full 16-color EGA behavior exercised by valid
local game data. Other display adapters and modes are specified only when they
are deliberately added as compatibility targets.

Behavior caused by malformed data escaping a resource and causing the original
interpreter to read or execute unrelated memory is outside this specification.
Bounded malformed input may be specified when its effects remain within the
normal resource-processing contract.

Hardware-specific implementation effects are included only to the extent that
games or players can observe a required result. For example, a sound scheduler
and its completion event can be normative without requiring an implementation
to reproduce the original hardware driver's instruction sequence.

## Versioned behavior

AGI is a family of interpreter versions rather than one immutable program. The
specification identifies a common contract and records version-specific
variants when valid game data can observe a difference.

An implementation claiming compatibility with a particular version must follow
the common rules plus every variant assigned to that version. Differences that
exist only in the original implementation but cannot affect valid observable
behavior do not create specification variants.

## Conformance

Given the same valid game resources, initial state, player input sequence, and
specified timing conditions, a conforming implementation must produce the same
game-visible state transitions and externally observable results described by
this book.

When the specification permits nondeterminism, conformance means producing a
result within the stated set or distribution constraints rather than matching
one recorded run exactly. When timing is expressed in interpreter cycles, an
implementation may use a different real-time mechanism as long as the
game-visible ordering and rate requirements are preserved.

Compatibility tests are supporting oracles for these contracts. They do not
replace the written specification, and test implementation details are not
normative unless the corresponding behavior is stated in this book.
