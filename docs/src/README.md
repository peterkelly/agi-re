# AGI Clean-Room Reverse Engineering

Project repository: [https://github.com/peterkelly/agi-re](https://github.com/peterkelly/agi-re)

This book is the reverse-engineering evidence record. It collects local-file
observations, disassembly, addresses, commands, hypotheses, corrections, and
compatibility-test results for the AGI interpreters being examined. Private
game files are selected locally and are not part of the repository.

This evidence book is not the clean-room deliverable presented to an
implementation team. The separate `spec/` mdBook contains the portable
behavioral specification. Facts discovered here are promoted there only after
they can be expressed as externally observable behavior without relying on
Sierra's DOS implementation details.

The project rules are:

- Use only local files and locally observed behavior.
- Do not consult external AGI documentation, source code, or prior AGI-specific
  knowledge.
- Document each reverse engineering step as evidence for the clean-room process.
- Keep implementation-independent behavioral requirements in the separate
  specification rather than treating this evidence book as the final spec.

Current documentation:

- The chronological evidence trail is in
  [Clean-Room Executable Notes](./clean_room_executable_notes.md).
- User-facing progress updates and their immediate outcomes are preserved in
  [Progress Log](./progress_log.md).
- The current readable decompilation of the loader is in
  [SIERRA.COM Loader](./loader_decompilation.md).
- Notes on the decrypted interpreter executable, startup, and overlay loading
  are in [Decrypted AGI Executable](./agi_executable.md).
- Stable symbolic names for routines, tables, and globals are tracked in
  [Symbolic Labels](./symbolic_labels.md), so later interpreter versions can be
  compared without relying on matching offsets.
- Version-specific differences between local interpreter/game inputs are tracked
  in [Versions](./versions.md).
- Notes on directory and volume resource files are in
  [Resource Files](./resource_files.md).
- A higher-level implementation model of the observed runtime data types and
  operation families is in [Runtime Model](./runtime_model.md).
- The growing executable compatibility suite and current graphics-render
  commands are described in [Compatibility Testing](./compatibility_testing.md).
