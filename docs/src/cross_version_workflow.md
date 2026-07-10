# Cross-Version Workflow

This project currently maps the Space Quest 2 interpreter build. Later AGI
games or releases should be treated as new local inputs, not as external
documentation. The goal of a cross-version pass is to map the same symbolic
labels to new addresses, record behavioral deltas, and run the compatibility
suite against the new original engine when possible.

## Evidence Package

For each new interpreter/game pair, preserve these local observations under a
version-specific `build/` subdirectory:

| Artifact | Purpose |
| --- | --- |
| Decrypted executable image | Stable bytes for disassembly and function matching. |
| Full disassembly | Searchable baseline for routines, dispatch tables, and call sites. |
| Directory/resource census | Counts and edge cases for logic, picture, view, sound, words, and object data. |
| Symbolic label map delta | Address associations from existing labels to the new build. |
| Compatibility report | Local suite and selected QEMU smoke/broad results. |

Start each broad comparison pass with the read-only census tool:

```bash
python3 -B tools/game_census.py --games-root games \
  --format markdown \
  --output build/cross-version/game_census.md
```

or pass selected inputs explicitly:

```bash
python3 -B tools/game_census.py \
  --game-dir games/SQ2 \
  --game-dir games/GR \
  --format json \
  --output build/cross-version/selected_census.json
```

The tool requires explicit paths, treats game files as read-only evidence,
detects split v2 and combined v3 resource layouts, records version strings from
local interpreter data, counts directory entries and readable records, and
keeps per-record errors in the generated report. Treat record errors as
hypotheses for later source inspection, not as engine semantics.

Do not collapse these observations into the SQ2 notes without naming the source
build. Addresses are build-specific; labels and behavior are the portable
concepts.

## Label Mapping

Start with labels in [Symbolic Labels](./symbolic_labels.md). For each label,
look for structural anchors rather than exact byte offsets:

| Label Type | Matching Anchors |
| --- | --- |
| Dispatch tables | Opcode count, entry stride, handler order, nearby table references. |
| Resource loaders | Directory accessor calls, cache-record layout, volume-reader call, event-record pair. |
| Parser helpers | Separator/ignored-character tables, `WORDS.TOK` lookup pattern, parsed ID/count globals. |
| Picture decoder | Command dispatch table, scanner loop, raw operand reads, coordinate-reader carry behavior. |
| Object/view pipeline | 43-byte object record accesses, view frame pointer selection, overlay entry jumps. |
| Save/restore | Five length-prefixed blocks, selector strings, filename-format helper, resource-event replay. |
| Sound driver | Channel pointer table, countdown loop, port-output helpers, completion flag path. |

When a routine matches, add the new address to the working notes and keep the
symbolic label unchanged. When behavior differs, record the difference as a
version-specific observation before deciding whether the portable spec needs a
variant rule.

## Recommended Pass Order

1. Decrypt or otherwise prepare the executable image using only local tooling.
2. Generate a whole-image disassembly and identify the action/condition
   dispatch tables.
3. Map core labels first: main cycle, logic interpreter, resource loaders,
   heap helpers, room switch, picture scanner, object overlay, parser, save
   selector, and sound tick.
4. Run static resource parsers over the new game data and record counts,
   missing resources, invalid directory entries, and unusually large payloads.
5. Run `python3 -B tools/compatibility_suite.py --dry-run --include-qemu-smoke`
   and decide which smoke batches apply without modification.
6. Add version-specific fixture support only after the static label map explains
   the relevant routine.
7. Run QEMU smoke tests, then broad picture/view carousel sweeps if the fixture
   format and interpreter behavior match the SQ2 assumptions.
8. Update `PROGRESS.md`, `docs/src/symbolic_labels.md`, and the clean-room
   notes with both matches and differences.

## Compatibility Tiers

Use the suite runner as the common entry point:

```bash
python3 -B tools/compatibility_suite.py --dry-run
python3 -B tools/compatibility_suite.py --dry-run --include-qemu-smoke
python3 -B tools/compatibility_suite.py --dry-run --include-qemu-broad
```

The default local tier should pass before any dynamic comparison. QEMU smoke
tests are for behavior already explained by disassembly. Broad sweeps are for
renderer/resource parity once loaders, paths, and fixture assumptions have been
mapped for the new version.

## Delta Recording

Each cross-version observation should answer four questions:

| Question | Example |
| --- | --- |
| Which symbolic label or subsystem changed? | `code.picture.command_scan` moved and gained one dispatch entry. |
| What local evidence proves the change? | Disassembly slice, table bytes, QEMU capture, or parser census. |
| Is this behavior observable for valid resources? | Yes for a new picture opcode; no for an unreachable error string. |
| Does the portable spec need a variant? | Add variant only when valid data can observe the difference. |

If a difference can only be reached through malformed data that makes the
original engine interpret unrelated memory, treat it as out of scope for the
behavioral spec unless the user explicitly asks for security research.
