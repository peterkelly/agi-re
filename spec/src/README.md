# AGI Behavioral Specification

This book specifies the externally observable behavior of the Adventure Game
Interpreter family examined by the clean-room project. Its intended reader is
an independent implementer who has not seen the original interpreter,
disassembly, or reverse-engineering evidence.

The specification defines what a compatible engine must do. It does not
prescribe a programming language, architecture, memory layout, operating
system, internal data structure, or algorithm unless a choice has an observable
effect that game data can depend on.

## Clean-room role

The reverse-engineering evidence is maintained separately under `docs/`. That
book records how behavior was discovered and may discuss the original DOS
implementation. This book contains only the resulting portable behavioral
contracts.

An implementation team should be able to work from this book alone. It should
not need the original game interpreter, the evidence book, local analysis
scripts, or knowledge of the original machine-code organization.

## Status

This specification is under construction. The evidence project already covers
many AGI subsystems, but those findings must be deliberately restated here in
implementation-independent terms before they become part of the clean-room
deliverable.

Incomplete or uncertain findings remain in the evidence book. Their absence
from this book means they are not yet a normative compatibility requirement.
