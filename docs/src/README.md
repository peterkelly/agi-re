# AGI Clean-Room Reverse Engineering

This book collects clean-room reverse engineering notes for the Space Quest 2
AGI interpreter files in this repository.

The project rules are:

- Use only local files and locally observed behavior.
- Do not consult external AGI documentation, source code, or prior AGI-specific
  knowledge.
- Document each reverse engineering step as evidence for the clean-room process.

Current documentation:

- The chronological evidence trail is in
  [Clean-Room Executable Notes](./clean_room_executable_notes.md).
- The current readable decompilation of the loader is in
  [SIERRA.COM Loader](./loader_decompilation.md).
- Notes on the decrypted interpreter executable, startup, and overlay loading
  are in [Decrypted AGI Executable](./agi_executable.md).
- Stable symbolic names for routines, tables, and globals are tracked in
  [Symbolic Labels](./symbolic_labels.md), so later interpreter versions can be
  compared without relying on matching offsets.
- Notes on directory and volume resource files are in
  [Resource Files](./resource_files.md).
- A higher-level implementation model of the observed runtime data types and
  operation families is in [Runtime Model](./runtime_model.md).
