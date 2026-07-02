# Progress Log

This chapter records user-facing progress updates from the assistant, with the
concrete action or result behind each update. It complements
`clean_room_executable_notes.md`: the evidence log records commands,
observations, offsets, and corrections, while this chapter preserves the
narrative trail of what was reported while the work was happening.

Exact progress-update logging starts with the synthetic picture fuzzing work
below. Earlier project work is documented in detail in
[Clean-Room Executable Notes](./clean_room_executable_notes.md), but the exact
wording of every earlier transient assistant update is not fully available in
the current thread context, so this log does not invent those verbatim messages.

## Prior Work Summary

Before this progress log was created, the project had already:

- Established the mdBook documentation layout under `docs/`.
- Built clean-room notes for the loader, executable, logic interpreter,
  resource formats, graphics/object pipeline, and symbolic labels.
- Set up a bootable DOS 6.22 QEMU hard disk image at `build/dos622/dos622.img`.
- Added local graphics/rendering helpers under `tools/`.
- Built QEMU fixture support for custom `LOGIC.0` scripts.
- Validated original-engine output against local Python rendering for:
  - picture 45;
  - picture 1 with view 11/group 0/frame 0;
  - picture 1 with view 0/group 1/frame 0, including the bit-`0x80`
    row-orientation rewrite.

The detailed command evidence for those milestones is in
`docs/src/clean_room_executable_notes.md`.

## Synthetic Picture Fuzzing Framework

User request:

> Write a fuzz testing framework that generates a large set of synthetic
> picture resources, including some with invalid commands/data, and use that to
> compare the behaviour of the original engine with the python code you've
> written. I want to capture edge cases so we can model the semantics with a
> high degree of accuracy

Progress updates and outcomes:

1. Reported: "I'll build this as a reusable harness, not a one-off pile of
   samples: synthetic picture payload generation, fixture construction that
   swaps in a custom picture resource, Python rendering with error capture, and
   QEMU capture/compare hooks. I'll start by reading the current
   fixture/rendering tools so the new code plugs into the existing path
   cleanly."

   Action/result: Read `tools/qemu_fixture.py`,
   `tools/compare_picture_capture.py`, `tools/agi_graphics.py`, and the current
   test list.

2. Reported: "I've got the shape now. The important design point is to patch
   `PICDIR` and `LOGDIR` together inside a copied fixture, with `VOL.3` holding
   both the custom `LOGIC.0` and the synthetic picture payload. That lets the
   original engine run synthetic pictures without touching the real SQ2 files."

   Action/result: Read `tests/test_qemu_fixture.py`, `AGENTS.md`, and
   `docs/src/SUMMARY.md` to align the fixture changes with existing tests and
   docs.

3. Reported: "I'm going to extend the fixture builder first: one generic
   directory-entry patcher, then a synthetic-picture fixture that writes
   `LOGIC.0` and the fuzzed picture into the same `VOL.3`. That keeps the fuzz
   runner small and makes the patching testable."

   Action/result: Updated `tools/qemu_fixture.py` with `patch_dir_entry()`,
   `build_synthetic_picture_fixture()`, and a `synthetic-picture` CLI command.

4. Reported: "The synthetic fixture builder is in place. Next I'm adding the
   fuzz corpus tool: it will generate deterministic valid and invalid picture
   payloads, render each with the Python model, write manifests/PPMs, build
   QEMU fixtures, and compare captures back to a selected fuzz case."

   Action/result: Added `tools/picture_fuzz.py` with deterministic base cases,
   random case generation, corpus manifests, Python render hashing, fixture
   building, QEMU execution, and capture comparison.

5. Reported: "The corpus tool is added. I'm adding tests around the new pieces
   now: directory entry patching, synthetic fixture layout, deterministic
   corpus generation, and a synthetic scaled-capture comparison path that
   doesn't need QEMU."

   Action/result: Expanded `tests/test_qemu_fixture.py` for generic directory
   patching and synthetic fixture layout.

6. Reported: "The fixture tests are patched. I'm adding a dedicated fuzz-tool
   test file next, including a scaled fake QEMU screenshot so the compare logic
   is exercised without booting DOS during unit tests."

   Action/result: Added `tests/test_picture_fuzz.py`.

7. Reported: "Tests are in place. I'm running them now; if the generator
   exposes any rough edges, I'll tighten it before doing the QEMU sample run."

   Action/result: Ran `python3 -B -m unittest discover -s tests`, which passed
   33 tests. Generated an initial 79-case corpus from 15 curated cases plus 64
   random cases.

8. Reported: "The unit tests pass, and a 79-case corpus is generated from 15
   curated cases plus 64 deterministic random ones. I'm going to use the new
   QEMU runner on a tiny visual-point case first, because that validates the
   end-to-end plumbing without risking an unsafe malformed-resource hang."

   Action/result: Ran the new QEMU runner on `base_003_visual_point`; QEMU
   exited early with a broken pipe because the harness hid the emulator output.

9. Reported: "The first automated QEMU run exited early, and the runner had
   hidden QEMU's output too aggressively. I'm adjusting it to surface early-exit
   diagnostics so failures are evidence instead of a mystery."

   Action/result: Updated `tools/picture_fuzz.py` to detect early QEMU exit
   before monitor input and to retain QEMU output on nonzero exit.

10. Reported: "The runner now checks for early QEMU exit before each monitor
    keystroke and preserves monitor output on nonzero exit. I'm rerunning the
    same smoke case."

    Action/result: The rerun still failed early and revealed that another
    diagnostic path was needed.

11. Reported: "QEMU is exiting with status 1 before DOS input. I still need the
    actual QEMU message, so I'm adding one more diagnostic path to read the
    monitor output when the early-exit check trips."

    Action/result: Added exception wrapping that includes QEMU monitor output.

12. Reported: "One more smoke run; now if QEMU bails, the runner should show
    why."

    Action/result: QEMU reported `Failed to bind socket: Operation not
    permitted`, showing that Python-launched QEMU needed escalation for the VNC
    socket.

13. Reported: "The runner is fine; the sandbox blocked QEMU's VNC bind when
    launched from Python. I'm rerunning that same framework command with
    escalation so the harness can actually start the emulator."

    Action/result: With escalation, `base_003_visual_point` matched the
    original engine with 0 mismatches out of 26,880 logical pixels.

14. Reported: "The first original-engine fuzz comparison matched. I'm going to
    expand the corpus to a genuinely large deterministic set now, then run a
    small representative QEMU slice across scanner, line, fill, pattern, and
    invalid-but-safe cases."

    Action/result: Generated a 1,039-case corpus from curated cases plus 1,024
    deterministic random cases. The generator marked 1,037 cases safe for QEMU.

15. Reported: "The corpus now has 1,039 synthetic picture resources, including
    1,037 marked safe for automated QEMU. I'm running five more original-engine
    comparisons against curated edge cases."

    Action/result: Ran QEMU for `base_002_unknown_commands`; it matched with 0
    mismatches.

16. Reported: "Unknown commands `0xfb..0xfe` matched the current Python
    behavior for that fixture: no visible changes before `0xff`. Continuing
    through the line/clamp and fill/pattern cases."

    Action/result: Ran QEMU for `base_004_clamped_absolute`; it produced 312
    mismatches, the first fuzz-discovered semantics gap in this pass.

17. Reported: "Good, the clamped-coordinate case found a real mismatch: 312
    logical pixels. That's exactly the kind of edge this harness is meant to
    expose, so I'm keeping that as evidence and continuing the sample sweep
    before drilling in."

    Action/result: Ran QEMU for the visual/control seed-fill case; it matched
    with 0 mismatches.

18. Reported: "The combined visual/control fill case matched, which reinforces
    the seed-fill channel-priority model. Next I'm checking pseudo-random
    pattern plotting and the truncated coordinate pair case."

    Action/result: Ran QEMU for the pseudo-random pattern case and the
    truncated coordinate-pair case; both matched with 0 mismatches.

19. Reported: "The pattern and truncated-pair cases matched; the only mismatch
    in the curated slice is the clamp edge case using coordinate byte `0xef`.
    I'm adding mismatch bounding boxes and sample pixels to the comparison
    output so we can immediately see what kind of semantic gap a fuzz case
    found."

    Action/result: Extended `CaptureComparison` in `tools/picture_fuzz.py` with
    `mismatch_bbox` and sample mismatch tuples.

20. Reported: "The comparison output now includes a compact mismatch bbox and
    sample pixel tuples. I'm rerunning the comparison against the already
    captured clamp case, no new QEMU boot needed."

    Action/result: The captured clamp case reported mismatch bbox
    `(0, 0, 149, 155)` and sample pixels showing displaced diagonal-line
    output.

21. Reported: "The mismatch samples show this is probably not just
    'coordinate clamp'; it is a steep diagonal line edge. The original is
    drawing a visible line displaced from the Python line for a
    `(159,167) -> (0,0)` style segment, so I'm going back to the line helper
    with this new targeted case."

    Action/result: Re-disassembled around `code.picture.draw_line`
    (`0x66e1`) and compared captured versus expected colored point sets. Both
    had 168 colored points ending at `(159,167)`, but the original began near
    `(25,0)` while Python began at `(0,0)`.

22. Reported: "The mismatch is very specific: both outputs draw 168 colored
    pixels ending at `(159,167)`, but the original starts the top of the line
    around `(25,0)` while Python starts at `(0,0)`. I'm checking the fixture
    bytes to make sure this is a real semantic signal and not a stale DOS-copy
    issue."

    Action/result: Inspected `VOL.3`, `PICDIR`, and the corpus case metadata.
    The fixture correctly contained payload `f0 02 f6 ef ef 00 00 ff` and
    patched `PICDIR[0]` to the synthetic picture in `VOL.3`.

23. Reported: "To isolate whether this is the line algorithm or the coordinate
    clamp, I'm adding an exact-boundary version of the same test using
    `(0x9f,0xa7) -> (0,0)`. If that matches, the gap is in out-of-range
    coordinate handling; if it mismatches the same way, the diagonal line model
    needs correction."

    Action/result: Added a new curated base case for exact-edge absolute-line
    drawing and renumbered subsequent curated base cases.

24. User requested: "keep a log of every intermediate step that you're
    reporting to me. it's super interesting and i want to keep track of it for
    historical record" and "including everything you've done so far".

    Action/result: Created this progress log and updated the project rules so
    future progress updates are logged as part of the clean-room history.

25. Reported: "The progress log now contains the current fuzzing session from
    the first update through the exact-edge test I was adding when you asked.
    I'm wiring it into the book and adding a standing instruction so I keep
    appending to it as I go."

    Action/result: Added `progress_log.md` to `docs/src/SUMMARY.md`, linked it
    from `docs/src/README.md`, and updated `AGENTS.md` with an instruction to
    preserve user-facing progress updates.

26. Reported: "I'll keep that log live from here on. Next I'm regenerating the
    corpus after the new exact-edge case and running the exact-edge QEMU
    comparison to separate coordinate clamping from diagonal line drawing."

    Action/result: Regenerated the corpus after adding the exact-edge case.
    The corpus now has 1,040 cases, with 1,038 marked safe for QEMU. The local
    unit suite still passed with 33 tests, and `mdbook build docs` succeeded.

27. Reported: "The regenerated corpus has 1,040 cases now, with 1,038 marked
    safe for QEMU; tests and mdBook still build cleanly. I'm running the
    exact-edge fixture through the original engine now."

    Action/result: QEMU comparison for `base_005_exact_edge_absolute` produced
    the same 312 mismatches and mismatch bbox `(0, 0, 149, 155)` as
    `base_004_clamped_absolute`.

28. Reported: "The exact-boundary case mismatched identically, so the gap is
    in the diagonal line helper, not out-of-range coordinate clamping. I'm
    updating the log, then I'll correct the Python line algorithm against the
    disassembly and rerun the two line fuzz cases."

    Action/result: Began revisiting the disassembled line helper at
    `0x66e1`.

29. Reported: "The likely bug is subtle but promising: the executable keeps
    the line accumulators in 8-bit registers, so long steep diagonals can wrap
    before the compare. My Python model used unbounded integers, which is fine
    for short lines but wrong at the screen-scale edge."

    Action/result: Simulated the disassembled algorithm with 8-bit accumulator
    wrap. The wrapped model reproduced the QEMU edge-case shape: at `y=0` the
    exact-edge line lands at `x=25`, not `x=0`.

30. Reported: "A quick simulation of the disassembled 8-bit accumulator
    reproduces the original-engine edge case exactly: at `y=0` the line lands
    at `x=25`, not `x=0`. I'm applying that change to the renderer and adding
    a regression test so this edge stays pinned."

    Action/result: Updated `PictureRenderer.draw_line()` to wrap diagonal
    line accumulators to 8 bits after addition and subtraction.

31. Reported: "The renderer now uses byte-width accumulator arithmetic for
    diagonal lines. I'm adding the focused test before rerunning the corpus and
    QEMU comparisons."

    Action/result: Located the existing split absolute-line and relative-line
    tests in `tests/test_graphics_rendering.py`.

32. Reported: "The existing line tests were split into separate absolute and
    relative cases, so I'm inserting the long-edge regression beside those
    instead of replacing anything."

    Action/result: Added `test_long_diagonal_uses_byte_width_line_accumulators`
    to `tests/test_graphics_rendering.py`.

33. Reported: "The long-edge regression is in. I'm running the unit suite now;
    if hashes changed in real SQ2 pictures, I'll treat that as a signal and
    verify against the existing QEMU captures before updating expected values."

    Action/result: The local unit suite passed with 34 tests.

34. Reported: "The unit suite passes with 34 tests, so no existing SQ2 picture
    hash moved. I'm regenerating the corpus with the corrected renderer
    metadata and then comparing the two edge-line captures again."

    Action/result: Regenerated the corpus. The corrected renderer matched the
    previously captured `base_004_clamped_absolute` QEMU output with 0
    mismatches. The exact-edge recompare failed because the regenerated corpus
    did not contain the expected `base_005_exact_edge_absolute` metadata path,
    so the base-case list needed inspection.

35. Reported: "The corrected renderer now matches the previous clamped-edge
    QEMU capture with zero mismatches. The exact-edge recompare failed because
    regenerating the corpus wiped the captured fixture metadata path before
    that case existed in the manifest, so I'm checking the base-case list and
    will rebuild/rerun that exact-edge capture cleanly."

    Action/result: Verified that `base_005_exact_edge_absolute` is present in
    the base-case list and regenerated corpus. The failed compare was caused by
    running corpus regeneration and capture comparison in parallel.

36. Reported: "The exact-edge case is present; the failed compare was a race
    from running corpus regeneration and comparison in parallel. I'm rerunning
    the exact-edge QEMU comparison now, sequentially."

    Action/result: Reran `base_005_exact_edge_absolute` through QEMU. It
    matched the corrected renderer with 0 mismatches.

37. Reported: "The exact-edge QEMU case now matches too. I'm rerunning the
    representative fuzz slice under the corrected renderer using the new case
    IDs, then I'll document the framework, the line-accumulator correction, and
    the current fuzz results."

    Action/result: Attempted to run three QEMU fuzz cases in parallel. This
    was rejected as a bad probe: QEMU's VNC socket was blocked without
    escalation, and concurrent mtools/QEMU fixture copying caused a DOS-image
    directory-copy failure for one case.

38. Reported: "That parallel QEMU slice was the wrong move: QEMU needs the VNC
    socket and the DOS image copy steps should be serialized. I'm recording
    that as a failed probe, then I'll run the remaining cases one at a time
    with the harness command approved/escalated as needed."

    Action/result: Updated `copy_fixture_to_dos()` to surface `mmd` failures
    unless the directory already exists.

39. Reported: "The harness now surfaces `mmd` failures unless they're the
    harmless 'already exists' case. I'm running the remaining representative
    QEMU cases sequentially now."

    Action/result: The user interrupted the run and then granted full access.
    No QEMU or fuzz harness process was left running. Inspection showed that
    `FZFILL2` already existed in the DOS image and that `mmd` returned a
    nonzero status with no diagnostic text for an existing directory. A probe
    directory `FZNEW99` was created while checking mtools behavior.

40. Reported: "Full access received. I'll pick up from the aborted QEMU run,
    first checking whether any emulator process or partial DOS-image copy was
    left behind, then I'll fix the mtools error reporting and continue the
    serialized fuzz comparisons."

    Action/result: Verified no QEMU process was running and identified the
    quiet `mmd` existing-directory case.

41. Reported: "No QEMU process is left behind. The interrupted run stopped
    before launching QEMU; the remaining issue is mtools returning a nonzero
    `mmd` status with no useful message, likely because the DOS directory
    already exists. I'm checking the DOS root and then I'll make the copy step
    robust by verifying the directory exists when `mmd` is quiet."

    Action/result: Confirmed `FZFILL2` already existed and `mmd` returned
    status 1 with no output for that directory.

42. Reported: "Confirmed: `FZFILL2` already exists and `mmd` reports that with
    an empty error stream. I also created `FZNEW99` as a harmless
    root-directory probe while checking mtools behavior. I'm patching the
    harness to validate existing directories explicitly instead of trusting the
    error text."

    Action/result: Updated `copy_fixture_to_dos()` so a quiet `mmd` failure is
    accepted only if `mdir` can read the requested directory.

43. Reported: "The harness now treats a quiet `mmd` failure as okay only if
    `mdir` can read the target directory. I'm logging that, then I'll run the
    remaining QEMU cases sequentially with fresh directory names to keep the
    DOS image tidy-ish."

    Action/result: Ran `base_010_visual_control_fill` through QEMU in DOS
    directory `FZFIL3`; it matched with 0 mismatches.

44. Reported: "The visual/control fill fuzz case still matches under the
    corrected renderer. I'm moving on to the pseudo-random pattern case, also
    serialized."

    Action/result: Ran `base_012_pattern_random` through QEMU in DOS directory
    `FZPAT3`; it matched with 0 mismatches.

45. Reported: "The pseudo-random pattern case matches too. I'm running the
    safe truncated-coordinate case now; this one checks that an incomplete pair
    terminates the command without visible garbage."

    Action/result: Ran `base_014_truncated_pair` through QEMU in DOS directory
    `FZTRN3`; it matched with 0 mismatches.

46. Reported: "The representative fuzz slice is green now after the
    line-accumulator fix. I'm updating the spec/docs with the fuzz framework,
    the QEMU results, and the 8-bit accumulator correction, then I'll run final
    verification."

    Action/result: Updated `graphics_object_pipeline.md`,
    `compatibility_testing.md`, `clean_room_executable_notes.md`, and
    `AGENTS.md`. The docs now describe the fuzz framework, the representative
    QEMU pass, the failed probes, and the 8-bit line accumulator correction.

47. Reported: "The evidence log now has the fuzz pass with command-level detail
    and the failed probes. I'm adding a short AGENTS.md note so future agents
    know how to use the fuzz harness and why QEMU fuzz runs should stay
    serialized."

    Action/result: Added fuzz-harness command notes to `AGENTS.md`.

48. Reported: "Docs and AGENTS are updated. I'm running the full local
    verification now: tests, mdBook build, whitespace check, and a final compare
    on the edge-line captures."

    Action/result: `python3 -B -m unittest discover -s tests` passed with 34
    tests; `mdbook build docs` succeeded; `git diff --check` succeeded; and
    `base_004_clamped_absolute` compared with 0 mismatches.

49. Reported: "Verification is clean so far. I'm also checking the exact-edge
    capture and the three representative post-fix cases from their saved
    outputs, then I'll summarize the final state."

    Action/result: Saved captures for `base_005_exact_edge_absolute`,
    `base_010_visual_control_fill`, `base_012_pattern_random`, and
    `base_014_truncated_pair` all compared with 0 mismatches.

50. Reported: "All saved fuzz captures compare cleanly now. I'm doing one last
    status/diff overview and updating the progress log entry from “pending” to
    the actual verification results."

    Action/result: `git status --short` showed the expected modified tracked
    docs plus untracked generated/tool/test files. The saved fuzz captures
    present under `build/picture-fuzz/fixtures/` include the representative
    scanner, line, fill, pattern, and truncated-data cases.

51. Reported: "The diff overview only shows tracked-file deltas, so the new
    fuzz/test/tool files are still listed as untracked in `git status`; that
    matches the repo's current uncommitted state. I'm closing the progress log
    with the final verification results now."

    Action/result: This entry completes the current fuzzing pass log.

52. Reported: "That boundary is important, and I'm going to write it down in
    the project docs so the fuzz harness treats 'malformed but bounded'
    differently from 'malformed enough to make the interpreter run off into
    unrelated memory.' The former can teach us parser edge cases; the latter
    belongs in a security notes bucket, not the compatibility spec."

    Action/result: Updated `compatibility_testing.md`,
    `clean_room_executable_notes.md`, and `AGENTS.md` to define
    `safe_for_qemu: false` cases as out of scope for the behavioral model.
    Updated `tools/picture_fuzz.py run-qemu` to refuse those cases before
    launching QEMU, and added a regression test for that guard. Verified with
    `python3 -B -m unittest tests.test_picture_fuzz`, `mdbook build docs`, and
    `git diff --check`; a follow-up full run of
    `python3 -B -m unittest discover -s tests` passed with 35 tests.

53. Reported: "I'll commit the source, tests, and docs changes, while leaving
    generated build outputs and installer/disk-image artifacts out of the commit
    unless the repo is already tracking them. First I'm checking the ignore
    rules and the exact file list so the commit stays tidy."

    Action/result: `git status --short --untracked-files=all` showed a large
    untracked generated set under `build/` plus DOS installer images under
    `002962_ms_dos_622/`. `AGENTS.md` already documents `build/` as disposable
    generated output, so these artifacts were not staged.

54. Reported: "The noisy untracked set is almost entirely generated: DOS
    installer images, the DOS hard disk image, screenshots, rendered PPM/PNG
    files, and copied SQ2 fixture directories. I'm staging only the project
    files that define the tooling, tests, and documentation, then I'll review
    the staged diff before committing."

    Action/result: Staged 18 source, documentation, and test files. The staged
    diff stat reported 3,571 insertions and 11 deletions, with no generated
    `build/` or `002962_ms_dos_622/` artifacts included.

55. Reported: "The progress log now records what I staged and why. I'm staging
    that log addition too, then running the same verification set before the
    commit."

    Action/result: `git diff --cached --check` passed,
    `python3 -B -m unittest discover -s tests` passed with 35 tests, and
    `mdbook build docs` succeeded.

56. Reported: "Everything staged looks right: 18 files, with generated
    artifacts still untracked. I'm creating the commit now."

    Action/result: Created commit `3fe576a` with message
    `Document graphics decoding and fuzz tests`.
