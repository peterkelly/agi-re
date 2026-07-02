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

    Action/result: Created commit `6d55b73` with message
    `Document graphics decoding and fuzz tests`.

57. Reported: "I'll take the first step from that list: make the picture fuzz
    harness capable of running a bounded serial batch through QEMU, with
    machine-readable results and enough summary data to drive the next
    semantics fixes. I'm going to inspect the current harness shape, then I'll
    add the batch path and document the workflow."

    Action/result: Inspected `tools/picture_fuzz.py`,
    `tests/test_picture_fuzz.py`, the current compatibility-testing docs, and
    the working tree state. The only untracked directories before this pass
    were generated local artifacts under `build/` and `002962_ms_dos_622/`.

58. Reported: "I've got the shape now: `batch-qemu` will select only
    `safe_for_qemu` cases from the manifest, optionally filter by case
    id/category/max count, run them one at a time, and write a JSON report with
    each case's DOS directory, capture path, status, mismatch summary, and
    elapsed time. That should make QEMU a repeatable oracle instead of a
    one-case-at-a-time ritual."

    Action/result: Added the `batch-qemu` command, batch selection helpers,
    stable DOS directory naming, JSON report writing, and unit tests with a
    mocked QEMU run.

59. Reported: "Got it. I'll keep pushing through the full sequence rather than
    stopping after the batch harness: first verify and run the batch oracle,
    then use whatever it exposes to refine picture semantics, and then move the
    same QEMU-validation pattern toward view/cel drawing and object behavior."

    Action/result: `python3 -B -m unittest tests.test_picture_fuzz` passed with
    8 tests. Regenerated a smaller working corpus with
    `python3 -B tools/picture_fuzz.py generate --count 64 --seed 4097 --output build/picture-fuzz/corpus --clean`,
    producing 80 cases, 78 marked safe for QEMU. `git diff --check` passed.

60. Reported: "I've logged the verification and corpus regeneration. The next
    command may take a couple of minutes because it boots QEMU once per case and
    deliberately runs serially."

    Action/result: Ran a 14-case curated safe QEMU batch covering scanner,
    line, corner, fill, pattern, and bounded invalid cases. The batch wrote
    `build/picture-fuzz/batches/base_curated_001.json` and reported 14 matches,
    0 mismatches, and 0 errors.

61. Reported: "The base report is strong: all 14 curated safe cases matched,
    including scanner, absolute and relative lines, both corner path modes,
    control-only fill, visual-plus-control fill, both pattern modes, and a
    bounded truncated pair. I've selected the first 16 safe random cases from
    the regenerated corpus and am running them as the next batch."

    Action/result: Selected `rand_00000` through `rand_00015` from
    `build/picture-fuzz/corpus/manifest.json` for a random safe QEMU batch.

62. Reported: "The random QEMU batch is underway. If it comes back green, that
    gives us confidence in the current picture renderer across mixed command
    streams; if not, the report should point directly at the next disassembly
    target."

    Action/result: Ran
    `python3 -B tools/picture_fuzz.py batch-qemu --case rand_00000 ... --case rand_00015 --dos-prefix FR --output build/picture-fuzz/batches/random_00000_00015.json --boot-wait 5 --draw-wait 8`.
    The report showed 16 matches, 0 mismatches, and 0 errors.

63. Reported: "The random report confirms matches across line, corner, pattern,
    fill, and scanner categories. I'm patching the runner to print per-case
    progress during long batches, and I'm adding targeted base cases for
    bounded fill barriers and pattern edge placement so the next QEMU pass is
    less accidental."

    Action/result: Added per-case progress printing for `batch-qemu` and added
    new curated base cases for visual fill inside/outside a box, pattern
    lower-right edge clamping, rectangular pattern masks, and multiple
    pseudo-random pattern seeds.

64. Reported: "The new cases are in and the batch command will now report
    progress as it runs. I'm regenerating the corpus, running the focused tests,
    and then I'll send the new targeted cases through QEMU."

    Action/result: `python3 -B -m unittest tests.test_picture_fuzz` passed with
    8 tests. Regenerated the working corpus; it now has 85 cases, 83 marked
    safe for QEMU. `git diff --check` passed.

65. Reported: "The streaming status is already paying off: the first targeted
    fill-box case matched. The batch is now on the outside-box fill case."

    Action/result: The targeted batch continued; both fill cases matched.

66. Reported: "Good, the two bounded fill cases matched. The circular pattern
    edge case produced a small 5-pixel mismatch, so after the batch finishes
    I'll drill into that report and the pattern positioning logic."

    Action/result: The targeted batch finished with 3 matches, 2 mismatches,
    and 0 errors. `base_018_pattern_edge_circle` mismatched by 5 pixels and
    `base_019_pattern_edge_rectangle` mismatched by 14 pixels; both mismatches
    appeared at X `0` on lower screen rows.

67. Reported: "The mismatch is very precise: the original engine plots column
    160 from a lower-right pattern mask as the first pixel of the next scanline,
    while the Python renderer clipped it away. This is a pattern-specific edge
    behavior, not a general line-coordinate issue, so I'm going to model it in
    the pattern plot path and lock it with a test."

    Action/result: Inspected the targeted batch report and confirmed the
    out-of-bounds pattern column wraps through the linear picture buffer. Added
    `write_cell()` for linear buffer writes, changed pattern plotting to call it
    directly, added a regression test for lower-right rectangular pattern wrap,
    and documented the behavior in `graphics_object_pipeline.md`.

68. Reported: "The pattern-edge fix is in place and documented. I'm running the
    rendering tests and regenerating the corpus so the Python hashes reflect the
    corrected pattern behavior before rerunning the targeted QEMU batch."

    Action/result: `python3 -B -m unittest tests.test_graphics_rendering tests.test_picture_fuzz`
    passed with 32 tests. Regenerated the working corpus; it remained at 85
    cases, 83 safe for QEMU. `git diff --check` passed.

69. Reported: "The targeted rerun is underway with the corrected renderer. The
    first fill case still matches, and the run is progressing case by case with
    the new live output."

    Action/result: The rerun showed `base_016`, `base_017`, and the corrected
    `base_018_pattern_edge_circle` all matching. The later cases failed with
    DOS-image `Disk full` errors rather than renderer mismatches.

70. Reported: "Host disk space is fine; the 'Disk full' is inside the small DOS
    hard disk image. I also found the cause: rerunning a fixture copied its old
    `qemu_capture.ppm` back into DOS, wasting image space. I'm patching the copy
    step to exclude generated host captures, then I'll clear old fuzz
    directories from the DOS image."

    Action/result: Updated `copy_fixture_to_dos()` to skip generated `.ppm`
    files when copying a fixture into the DOS image.

71. Reported: "The DOS image is literally at 0 bytes free, and the root is full
    of generated fuzz directories (`FZ*`, `FB*`, `FR*`, `FT*`, `FU*`). I'm
    removing those disposable directories from the DOS image, leaving the base
    DOS install and original SQ2/validation fixture directories alone."

    Action/result: Removed generated fuzz directories from
    `build/dos622/dos622.img`. The DOS image root then showed about 56 MB free.

72. Reported: "The storage cleanup worked; the rerun is progressing normally
    and the first targeted case still matches. I'm waiting for the pattern edge
    cases now."

    Action/result: Reran the targeted fill/pattern batch as
    `targeted_fill_pattern_003.json`. All five cases matched with 0 mismatches
    and 0 errors.

73. Reported: "The targeted rerun is green: all five fill/pattern cases now
    match the original engine. I'm updating the docs with the batch harness,
    the DOS-image storage lesson, and the newly observed pattern linear-wrap
    behavior before moving on to view/cel validation."

    Action/result: Updated `AGENTS.md`, `compatibility_testing.md`,
    `clean_room_executable_notes.md`, and `graphics_object_pipeline.md` with
    batch-QEMU usage, current fuzz coverage, DOS-image cleanup notes, and the
    pattern X-160 linear-write behavior.

74. Reported: "The current capture comparator can already compose a rendered
    view over a picture, but it only reports a mismatch count. I'm going to
    upgrade it to report bounding boxes/samples and add a `view_batch.py` tool
    that builds picture-view fixtures, runs them through QEMU serially, and
    emits JSON reports like the picture fuzz runner."

    Action/result: Extended picture-capture comparison results with mismatch
    boxes and samples. Added `tools/view_batch.py` with base view/object cases,
    fixture generation, serial QEMU execution, and JSON report writing.

75. Reported: "The view batch tool is in place. I'm adding a small unit test
    around its case loading/report path before running it against QEMU, so the
    batch machinery itself has coverage independent of the emulator."

    Action/result: Added `tests/test_view_batch.py` covering base case coverage,
    JSON case loading, DOS directory naming, and report summary generation.

76. Reported: "The view-batch unit tests are added. I'm running the full local
    suite and mdBook now before using QEMU again."

    Action/result: `python3 -B -m unittest discover -s tests` passed with
    43 tests, `mdbook build docs` succeeded, and `git diff --check` passed.

77. Reported: "The verification result is logged. Starting the six-case view
    batch now: normal cel, mirrored cel, left/top clipping, and a low-priority
    object case."

    Action/result: Ran `python3 -B tools/view_batch.py --dos-prefix VB --output build/view-batch/batches/view_base_001.json --boot-wait 5 --draw-wait 8`.
    Five cases matched; `view_011_top_clip` mismatched in rows 0 through 4.

78. Reported: "The cached search found an exact match: the original output
    equals drawing the cel at `left=18`, `baseline_y=4` when the fixture
    requested `left=20`, `baseline_y=2`. In other words, when the computed top
    is `-2`, the overlay path shifts left by that negative top and clamps the
    top to row 0. I'm encoding that as a provisional `add_to_pic`/overlay
    placement rule and will rerun the view batch."

    Action/result: Updated object-frame composition to adjust `left` and
    `baseline_y` when the computed top is negative. Added a regression test and
    documented the QEMU-observed top-edge adjustment.

79. Reported: "The top-edge adjustment is modeled and tested locally. I'm
    running the relevant tests, then I'll rerun the view batch to verify the
    QEMU mismatch is gone."

    Action/result: `python3 -B -m unittest tests.test_graphics_rendering tests.test_view_batch`
    passed with 29 tests, and `git diff --check` passed.

80. Reported: "The test result is logged. Starting the QEMU rerun for the view
    batch with the corrected top-edge model."

    Action/result: Reran `tools/view_batch.py` as
    `build/view-batch/batches/view_base_002.json`. All six cases matched with
    0 mismatches and 0 errors.

81. Reported: "The corrected view batch is fully green: all six cases match,
    including the top-edge placement case. I'm documenting the view-batch
    harness and the observed object top-edge rule, then I'll do the full
    verification pass."

    Action/result: Updated `compatibility_testing.md` and
    `clean_room_executable_notes.md` with view-batch commands, coverage,
    results, and the top-edge object placement rule.

82. Reported: "That's a great optimization target. I'm going to pause the
    broader reverse-engineering loop and investigate QEMU host-directory options
    for DOS specifically; the likely candidate is QEMU's virtual FAT block
    device, which should appear to DOS as another drive. If that works, the next
    harness shape is 'boot once, run many prebuilt fixture directories from a
    shared drive.'"

    Action/result: Checked local QEMU version (`11.0.2`) and help output. DOS
    cannot use QEMU 9p/virtfs directly without a guest driver, so the practical
    candidate is a QEMU FAT-backed block device exposed as a secondary DOS disk.

83. Reported: "QEMU accepts the FAT-backed secondary drive syntax. Now I'm
    booting DOS with that share attached and sending a `DIR D:\` command, then
    I'll capture the VGA screen to confirm DOS can actually see the host file."

    Action/result: Booted QEMU with
    `-drive file=fat:rw:build/qemu-share,format=raw,if=ide,index=1,media=disk`.
    DOS saw the host directory as drive `D:` with volume label `QEMU VVFAT` and
    listed `HOST.TXT`.

84. Reported: "The screenshot confirms it: DOS sees the host directory as `D:`
    with volume label `QEMU VVFAT`, and `HOST.TXT` is visible. Next I'm testing
    the part that matters for our harness: running an AGI fixture directly from
    that shared `D:` drive without copying it into the DOS image."

    Action/result: Built `build/qemu-share/PIC001` and ran it from
    `D:\PIC001` in QEMU. The capture
    `build/qemu-share/from_share_pic001.ppm` compared against picture 1 with
    0 mismatches.

85. Reported: "Running from the shared drive works: the AGI fixture on
    `D:\PIC001` produced a capture with 0 mismatches against the local renderer.
    The remaining question for 'boot once' is whether the generated fixture
    returns to DOS after drawing; I'm testing that by sending another DOS
    command after the draw and capturing the screen."

    Action/result: Sending `DIR` after running `SIERRA` left the game screen
    visible. The generated fixture does not return to DOS, so multi-case
    no-boot runs need `loadvm`/reset or a different fixture script.

86. Reported: "A QEMU internal snapshot with `fat:rw:` fails because writable
    vvfat does not support live migration/snapshotting. That's not fatal: for
    test inputs we only need the host share read-only inside DOS, and we can put
    the boot disk on a qcow2 overlay that stores VM snapshots. I'm testing that
    combination next."

    Action/result: Created `build/dos622/dos622-test.qcow2` as a qcow2 overlay
    over the raw DOS disk. Read-only vvfat as an IDE disk still failed, but
    read-only vvfat as an IDE CD-ROM allowed `savevm`.

87. Reported: "Useful result: `fat:...` as a read-only IDE disk still fails,
    but exposing it as a read-only IDE CD-ROM allows QEMU `savevm`. Now I'm
    checking whether this DOS install can actually see that CD-ROM-style drive
    as `D:`; if not, we can still use snapshots with another share mechanism,
    but not this one directly."

    Action/result: DOS reported `Invalid drive specification` for the
    CD-ROM-style share because the current image has MSCDEX but no IDE/ATAPI
    CD-ROM driver configured.

88. Reported: "There’s MSCDEX, but no IDE/ATAPI CD-ROM driver in the DOS image.
    A better idea for a read-only, snapshot-compatible host directory is to
    expose the QEMU FAT share as a floppy, because DOS can see floppy drives
    without MSCDEX; I'm testing whether QEMU's vvfat floppy is large enough and
    visible."

    Action/result: Plain `if=floppy` produced invalid media. `fat:floppy:` was
    accepted only when the host directory fit FAT12 capacity. A nested full
    fixture directory appeared empty, and a root-level fixture exposed only a
    subset of files, making this path unsuitable for full AGI fixtures.

89. Reported: "The root-level floppy share is visible but not usable for full
    AGI fixtures: DOS only sees a small subset of the files. So the clean result
    is: host directory mounting works well as a secondary `D:` hard disk with
    `fat:rw:...`; snapshot-based no-reboot runs need either a DOS CD-ROM driver
    for read-only vvfat CD-ROM, or a generated qcow2/FAT test disk instead of a
    live host directory. I'm documenting the exact working and non-working
    combinations now."

    Action/result: Updated `AGENTS.md` and this evidence log with the working
    `fat:rw:` command, the successful run from `D:`, and the limitations around
    QEMU snapshots, CD-ROM drivers, and floppy-sized vvfat shares.

90. Reported: "I'll commit the source, tests, and docs from this pass, leaving
    the generated QEMU shares, captures, qcow overlay, `build/`, installer
    images, and `__pycache__` out of the commit. I'm checking the exact staged
    set first so the commit doesn't accidentally pick up emulator artifacts."

    Action/result: `git status --short --untracked-files=all` showed the
    expected generated artifacts under `build/`, the DOS installer images under
    `002962_ms_dos_622/`, and Python cache files. `git diff --check` passed.

91. Reported: "The staged set is exactly 12 source/docs/test files; generated
    artifacts remain untracked. I'm running the full tests, mdBook, and cached
    diff whitespace check before committing."

    Action/result: `python3 -B -m unittest discover -s tests` passed with
    44 tests, `mdbook build docs` succeeded, and `git diff --cached --check`
    passed.

92. Reported: "The final staged diff is clean. I'm committing it with a message
    that covers the two main pieces: QEMU validation batches and host-share
    investigation."

    Action/result: Created a commit with message
    `Add QEMU validation batches`; it was then amended to include this progress
    log entry.

93. Reported: "I'll build and test the qcow2 fixture-disk path end to end:
    create a normal FAT disk image with prebuilt AGI fixture directories, attach
    it as `D:`, verify DOS can see and run from it, then test `savevm/loadvm`
    around repeated fixture runs. If it works, I'll fold that into the
    harness/docs so we can stop paying the full boot cost per case."

    Action/result: Confirmed `mformat`, `mcopy`, `mdir`, `mmd`, `mdel`, `mrd`,
    `qemu-img`, and `qemu-system-i386` are installed. The working tree only had
    generated artifacts under `build/`, `002962_ms_dos_622/`, and
    `tools/__pycache__/` before this pass.

94. Reported: "DOS doesn't accept a partitionless FAT image as a hard disk, so
    we do need an MBR-style partition. I'm creating a raw disk with a simple
    FAT16 partition starting at sector 63, formatting that partition with
    mtools, then converting it to qcow2."

    Action/result: A partitioned secondary qcow2 fixture disk could be read by
    mtools, but DOS either treated sector 0 as a garbage FAT boot sector or
    reported `Not ready reading drive D`, even with DOS-like partition metadata
    and forced IDE CHS.

95. Reported: "Forcing IDE geometry didn't fix the second-disk case. I'm
    switching to the more robust variant: create a disposable qcow2 clone of the
    DOS boot disk with fixture directories preloaded onto `C:` itself. That
    still gives us the important property: one boot, `savevm` at the DOS prompt,
    then `loadvm` between fixture runs."

    Action/result: Copied `build/dos622/dos622.img` to a disposable raw image,
    copied `PIC001` and `VIEW11` fixture directories into its DOS partition,
    converted it to qcow2, booted once, saved VM state at the DOS prompt, ran
    `PIC001`, loaded the saved VM, ran `VIEW11`, and compared both captures.
    Both matched with 0 mismatches.

96. Reported: "The implementation pivot is clear: a generic helper will create
    a disposable qcow2 clone of the boot disk, preload DOS fixture directories
    with mtools, boot once, `savevm ready`, and `loadvm ready` between cases.
    Then `view_batch.py --snapshot` can use it without changing the comparison
    logic."

    Action/result: Added `tools/qemu_snapshot.py` for disposable boot-disk
    cloning, mtools fixture preloading, and one-boot snapshot QEMU execution.
    Added `tools/view_batch.py --snapshot` plus local unit coverage for the
    snapshot helper's fixture filtering, mtools image syntax, and monitor key
    names.

97. Reported: "The view/object snapshot smoke passed: all six cases matched
    with zero errors. I'm going to extend the same one-boot mode to the picture
    fuzz batch command too, because that is where the boot cost really hurts."

    Action/result: Ran
    `python3 -B tools/view_batch.py --snapshot --dos-prefix VS --output build/view-batch/batches/view_snapshot_smoke.json --boot-wait 5 --draw-wait 8`.
    QEMU booted once from the generated snapshot qcow2, restored the DOS prompt
    between the six built-in view/object cases, and all captures matched.
    Extended `tools/picture_fuzz.py batch-qemu` with `--snapshot`, using the
    shared qcow2 boot-disk snapshot helper. Added a mocked unit test proving
    snapshot-mode fuzz reports are compared and recorded through the existing
    batch-result path.

98. Reported: "The real fuzz snapshot smoke passed too: both synthetic picture
    cases matched the original engine with zero mismatches from one QEMU boot.
    I'm recording that result now and then I'll do one final status/check pass."

    Action/result: Ran
    `python3 -B tools/picture_fuzz.py batch-qemu --snapshot --case base_016_visual_fill_box --case base_019_pattern_edge_rectangle --dos-prefix FS --output build/picture-fuzz/batches/snapshot_smoke.json --boot-wait 5 --draw-wait 8`.
    QEMU booted once from the generated snapshot qcow2, restored the DOS prompt
    between the two cases, and both captures compared with 0 mismatches.

99. Reported: "I found a useful next lever: the fixture builder can currently
    combine a real SQ2 picture with a view, or a synthetic picture alone, but
    not a synthetic picture plus a view. Adding that combined fixture will let
    us create tiny controlled priority/control backgrounds and compare object
    overlay behavior against the original engine."

    Action/result: Began adding a synthetic-picture-plus-view fixture path and
    targeted object overlay probes so priority/control behavior can be tested
    against QEMU with controlled picture backgrounds.

100. Reported: "The first four priority threshold probes matched exactly,
     which is a strong signal that the basic `existing_priority <=
     object_priority` rule is right. I'm adding one more pair that targets the
     stranger part of the routine: when the destination cell has a low control
     nibble, it scans downward to find a real priority barrier."

     Action/result: Ran
     `python3 -B tools/object_overlay_probe.py --dos-prefix OP --output build/object-overlay-probes/batches/base_priority.json --boot-wait 5 --draw-wait 8`.
     The default-control priority 3/4 pair and full-screen-control-6 priority
     5/6 pair all matched QEMU with 0 mismatches. Added two scan-down cases
     that place control 2 at the object's top row and control 6 one row below.

101. Reported: "The QEMU result confirms both branches of the priority gate we
     cared about: direct high-priority comparison and low-control downward
     scanning. I'm folding that into the docs now as confirmed compatibility
     evidence rather than just a code hypothesis."

     Action/result: Ran
     `python3 -B tools/object_overlay_probe.py --dos-prefix OQ --output build/object-overlay-probes/batches/priority_scan_down.json --boot-wait 5 --draw-wait 8`.
     All six object overlay probes matched QEMU with 0 mismatches, including
     the two low-control scan-down cases. Updated the graphics/object pipeline,
     compatibility testing notes, clean-room executable notes, and AGENTS tool
     instructions.

102. Reported: "The `0x7a` path stages two nibbles into object byte `+0x24`:
     the sixth operand as the low nibble and the seventh as the high nibble. I'm
     adding two mismatch probes now to confirm which nibble controls visible
     overlay priority, because that matters for the spec."

     Action/result: Added two object overlay probes with intentionally
     different operand-6 and operand-7 values: priority `3`/control `6` on a
     default control-4 background, and priority `6`/control `3` on a
     control-6-filled background.

103. Reported: "The nibble-discriminator cases matched too. That confirms
     visible object priority comes from the low nibble staged by operand 6; the
     high nibble from operand 7 does not control whether the cel pixels draw in
     these probes."

     Action/result: Ran
     `python3 -B tools/object_overlay_probe.py --dos-prefix OR --output build/object-overlay-probes/batches/priority_nibbles.json --boot-wait 5 --draw-wait 8`.
     All eight object overlay probes matched QEMU with 0 mismatches. Updated the
     graphics/object pipeline, compatibility notes, and clean-room executable
     notes to describe the low-nibble visible-priority result.

104. Reported: "Two useful surprises came out. The right-edge case shows
     placement clamps the object's left coordinate to `160 - width` rather than
     just clipping pixels. The persistent `0x36` priority-byte case suggests the
     high nibble can affect persistent placement/control acceptance even though
     transient visible drawing uses the low nibble, so I'm tightening those
     models and adding one confirmation case."

     Action/result: The expanded object overlay run matched 16 of 18 cases.
     Added right-edge placement clamping to the local overlay model, changed the
     persistent `0x36` case to expect rejection under control 6, and added a
     `0x66` persistent priority-byte confirmation case.

105. Reported: "The right-edge behavior is not a simple clamp: the actual cel
     lands around `x=140`, `baseline_y=67`, so placement search adjusts both
     axes. The persistent `0x66` case is hidden too, which makes the safer
     current conclusion: persistent fixed priority bytes with a nonzero high
     nibble are not valid visible-priority inputs in these probes. I'm encoding
     those as observed expectations rather than pretending the simple model
     covers them generally."

     Action/result: Added per-case expected placement overrides for the
     right-edge probe and changed the persistent `0x66` probe to expect a hidden
     object under the controlled priority-6 picture.

106. Reported: "The full 19-case QEMU batch is clean: clipping, transparent
     variants, priority-table-derived priority, and persistent-object setup all
     matched. I'm updating the spec now, including the important caveat that
     right-edge placement is observed as a placement-search result, not a
     general formula yet."

     Action/result: Ran
     `python3 -B tools/object_overlay_probe.py --dos-prefix OG --output build/object-overlay-probes/batches/expanded_all5_final.json --boot-wait 5 --draw-wait 8`.
     All 19 cases matched QEMU with 0 mismatches. Updated compatibility notes,
     clean-room executable notes, and graphics/object pipeline documentation.

107. Reported: "I'm picking up from the movement-probe branch of the work. The
     first QEMU run showed the object stayed exactly at its activation
     coordinates, which is a useful failure: the current fixture loops inside
     one logic invocation, so I'm going to switch it to a once-only setup
     guarded by an engine flag and let the interpreter return to its per-cycle
     machinery."

     Action/result: Re-read `tools/qemu_fixture.py`,
     `tools/object_movement_probe.py`, the condition parser in
     `tools/disassemble_logic.py`, and the existing logic-bytecode docs.

108. Reported: "The local notes already have the important conditional-block
     semantics, but I'm checking them against the disassembler implementation
     before encoding fixtures by hand. This is one of those tiny-byte-layout
     spots where one wrong offset can make the engine do a completely different
     thing while still looking valid."

     Action/result: Confirmed the condition-list terminator carries a
     little-endian false delta after the `0xff` condition-list end byte.

109. Reported: "The real scripts make this simpler than the prose sounded: the
     condition-list terminator's two-byte delta skips the following then-body
     directly. I'm adding a tiny bytecode builder for run this setup once unless
     flag X is already set, then the logic ends normally each tick so the engine
     can advance motion."

     Action/result: Added reusable fixture helpers for logic-resource wrapping,
     `end`, `set_flag`, `not flag_set`, conditional blocks, and once-only logic.

110. Reported: "I found SQ2's own startup logic clearing broad high flag
     ranges, so I'm choosing an explicit fixture init flag and making it
     configurable per movement case. The generated logic will now look like:
     `if not flag_set(init_flag) { load picture, set up object, start move, set
     init_flag } end`."

     Action/result: Added `persistent_object_once_logic_payload()` and optional
     `init_flag` support to persistent object fixtures.

111. Reported: "The unit tests now cover the new byte sequences directly. I'm
     running the suite and a quick generated-logic disassembly check next; if
     those pass, I'll send the two movement cases through QEMU again and compare
     against the Python renderer."

     Action/result: Ran `python3 -B -m unittest discover -s tests`; 72 tests
     passed.

112. Reported: "QEMU ran cleanly, but both cases still mismatch. That's not a
     dead end; it means we now have captures from a better fixture, and I'm
     going to locate the object in those captures rather than assuming the
     target semantics."

     Action/result: Ran
     `python3 -B tools/object_movement_probe.py --dos-prefix MV --output build/object-movement-probes/batches/base_movement_once.json --boot-wait 5 --draw-wait 8`.
     Both one-shot movement cases mismatched.

113. Reported: "The new captures show the object moved, just not to the target
     I expected. The mismatch boxes are shifted far beyond the requested target,
     so I'm waiting on a brute-force position match to identify the actual final
     coordinates."

     Action/result: Best-position scan found exact matches at `(140,80)` for
     the horizontal one-shot case and `(20,167)` for the vertical one-shot case.

114. Reported: "The captures match perfectly at `(140,80)` for the horizontal
     case and `(20,167)` for the vertical case. That strongly suggests
     `move_object_to` is not treating the target X/Y operands as immediates in
     this action variant, so I'm going back to the action table metadata and
     real script usage before updating the model."

     Action/result: Rechecked `0x51`/`0x52` docs, action-table metadata, and
     local SQ2 script uses. The immediate-target interpretation remained
     consistent with the static handler analysis.

115. Reported: "The static handler docs still say immediate targets, so the
     mismatch is probably in the per-cycle movement semantics, not bytecode
     operands. The object appears to keep the initial direction until it hits a
     screen boundary, which means we need to verify where and when the arrived
     at target check runs."

     Action/result: Re-read movement-pass docs and concluded that scripts need
     to reissue `move_object_to` on later cycles so helper `0x1672` can observe
     that the current object position has reached the target.

116. Reported: "This clarifies the right fixture shape: setup should be
     once-only, but `move_object_to` itself has to be reissued on later cycles
     until its completion flag becomes set. I'm changing the movement fixture
     from start movement once to initialize once, then call movement each tick
     while completion flag is clear."

     Action/result: Added optional guarded per-cycle action blocks to
     `persistent_object_once_logic_payload()` and moved the probe's
     `0x51` action into that block.

117. Reported: "The suite is green at 73 tests and the diff has no whitespace
     issues. I'm running the revised QEMU probe now; this one should tell us
     whether repeated action issuance is the missing semantic."

     Action/result: Ran tests and `git diff --check`; both passed.

118. Reported: "That did it: both reissued-action movement probes match the
     Python expectation exactly. I'm going to fold this into the docs now, then
     expand the batch a bit with explicit boundary-style movement cases and add
     better mismatch observability so future failures tell us where did the
     object end up automatically."

     Action/result: Ran
     `python3 -B tools/object_movement_probe.py --dos-prefix MV --output build/object-movement-probes/batches/base_movement_reissued.json --boot-wait 5 --draw-wait 8`.
     Both target-arrival cases matched QEMU with 0 mismatches.

119. Reported: "I'm adding two screen-edge probes to the same harness and
     teaching mismatch reports to include a best-fit object position. That turns
     future failures from pixels differ into the engine placed the object at
     X/Y, which is much more useful for reverse engineering."

     Action/result: Added right-edge and bottom-edge movement cases plus
     `MovementComparison.best_position`.

120. Reported: "The mismatch-position test found an equivalent drawn placement
     at the very top edge, which is a nice reminder that clipped cels can alias.
     I'm moving the synthetic mismatch away from clipping so the inferred
     coordinate is unambiguous."

     Action/result: Adjusted the unit test to use an unclipped synthetic
     mismatch capture.

121. Reported: "The suite is green at 74 tests. I'm launching the four-case
     QEMU batch now: two target arrivals plus right and bottom edge completion
     cases."

     Action/result: Ran tests and launched
     `python3 -B tools/object_movement_probe.py --dos-prefix MV --output build/object-movement-probes/batches/base_movement_edges.json --boot-wait 5 --draw-wait 8`.

122. Reported: "All four QEMU movement cases matched, including the screen-edge
     stops. I'm documenting the clean-room evidence now: the important semantic
     is that scripts reissue targeted movement until the completion flag trips;
     a one-shot start keeps moving until boundary completion."

     Action/result: The four-case movement batch matched QEMU with 0
     mismatches.

123. Reported: "I'm updating four doc surfaces: the running progress log, the
     compatibility test recipe, the object/movement model, and the clean-room
     evidence notes. Keeping these in sync is a bit clerical, but it is what
     makes the later implementation work grounded instead of folkloric."

     Action/result: Updated `docs/src/compatibility_testing.md`,
     `docs/src/graphics_object_pipeline.md`, `docs/src/logic_bytecode.md`, and
     `docs/src/clean_room_executable_notes.md` with the targeted movement
     findings.

124. Reported: "I'm going to add one control-buffer acceptance case before
     wrapping: a synthetic picture whose control channel is filled with zero.
     The hypothesis from `0x56b8` is that proposed movement should be rejected,
     leaving the object at its start position even though the movement action
     keeps reissuing."

     Action/result: Added a fifth movement case using picture payload
     `f2 00 f8 00 00 ff` and an initial expectation that the object would
     remain at `(20,80)`.

125. Reported: "The control-zero hypothesis did not match, which is useful
     evidence. I'm inspecting the report's inferred position now; if it moved
     normally, control zero is not a simple blanket movement rejection in this
     setup."

     Action/result: Ran
     `python3 -B tools/object_movement_probe.py --dos-prefix MV --output build/object-movement-probes/batches/base_movement_control.json --boot-wait 5 --draw-wait 8`.
     The first four cases matched, but the control-zero case mismatched.
     `best_position` showed an exact match at `(50,80)`, meaning the object
     reached the target.

126. Reported: "The inferred position is exact at `(50,80)`: the object reached
     the target on a control-zero-filled synthetic picture. I'm changing that
     case from a rejected-move hypothesis into a confirmed acceptance probe,
     then I'll rerun the batch so the saved report is green."

     Action/result: Renamed the case to `move_allowed_on_control_zero` and
     changed its expected final position to `(50,80)`.

127. Reported: "The corrected five-case batch is green. I'm updating the docs
     one more time so they mention the control-zero acceptance result instead
     of only the four movement cases."

     Action/result: Ran
     `python3 -B tools/object_movement_probe.py --dos-prefix MV --output build/object-movement-probes/batches/base_movement_control_final.json --boot-wait 5 --draw-wait 8`.
     All five cases matched QEMU with 0 mismatches.

128. Reported: "I've got the source-backed movement model pinned down now, so
     I'm going to encode more edge cases around `0x16ed`: left/up, diagonal,
     non-divisible distances, zero step override, and already/near-target
     completion. Then I'll run them through QEMU and update the docs with what
     actually matches."

     Action/result: Added seven movement cases to `tools/object_movement_probe.py`.

129. Reported: "The movement corpus now has twelve cases, including the
     direction and tolerance cases I wanted. I'm updating the tests to lock in
     that expanded coverage before running QEMU."

     Action/result: Updated `tests/test_object_movement_probe.py`; local tests
     passed.

130. Reported: "The movement model matched 11 of 12; the only miss is the zero
     step override. I'm inspecting the report now, because that should tell us
     the existing default step size the engine actually used."

     Action/result: Ran
     `python3 -B tools/object_movement_probe.py --dos-prefix MX --output build/object-movement-probes/batches/expanded_movement_edges.json --boot-wait 5 --draw-wait 8`.
     The zero-step case's `best_position` was `(20,80)`, proving operand 3 value
     zero preserved the object's current zero step in this generated fixture.

131. Reported: "The zero-step case is illuminating: in this generated object,
     the existing step byte is zero, so operand `0` preserves zero and the
     object never moves. I'm changing that case to record zero preserves current
     step, with the current synthetic default being stationary."

     Action/result: Updated the zero-step expected final position to `(20,80)`.
     The rerun
     `python3 -B tools/object_movement_probe.py --dos-prefix MX --output build/object-movement-probes/batches/expanded_movement_edges_final.json --boot-wait 5 --draw-wait 8`
     matched all 12 cases with 0 mismatches.

132. Reported: "For object-object collision, the available clean fixture path
     is less direct than movement: object grouping is not exposed by a simple
     script action. I'm disassembling `0x4719` closely now so any QEMU probe we
     add is designed around what the helper really tests, not just a guess about
     overlap."

     Action/result: Disassembled `0x4719`; confirmed moving-object bit
     `0x0200`, candidate flags, grouping byte `+0x02`, horizontal overlap, and
     Y equality/crossing predicates.

133. Reported: "Good, the startup code initializes object byte `+0x02` to the
     object index, so object 0 and object 1 naturally have different collision
     groups. I'm adding two-object movement fixtures: one where object 0 is
     blocked by object 1, and one where setting bit `0x0200` on object 0 skips
     the collision and allows it through."

     Action/result: Added `set_object_bit_0200_action()` to
     `tools/qemu_fixture.py` and optional obstacle-object support to
     `tools/object_movement_probe.py`.

134. Reported: "QEMU is now running 14 cases, including the two-object collision
     checks. I expect the first 12 to stay green; the useful signal will be
     cases 13 and 14."

     Action/result: Ran
     `python3 -B tools/object_movement_probe.py --dos-prefix MC --output build/object-movement-probes/batches/movement_collision.json --boot-wait 5 --draw-wait 8`.
     All 14 cases matched with 0 mismatches. The blocked collision case stopped
     object 0 at `(25,80)` before touching object 1 at `(50,80)`, and the
     collision-skip bit case reached `(80,80)`.

135. Reported: "Before wrapping, I'm checking the autonomous modes
     (`0x53`/`0x54`) call sites so the docs can distinguish what we validated
     in QEMU from what remains source-only."

     Action/result: Scanned near call sites and disassembled helper `0x0563`.
     Documented the source-derived cycle ordering: `0x0563` calls dispatcher
     `0x067a` for active objects with countdown byte `+0x01 == 1`; `0x067a`
     dispatches mode `+0x22` value 1 to `0x3f5a`, value 2 to `0x0b36`, and
     value 3 to `0x1672`, before `0x0563` calls movement pass `0x150a`.

136. Reported: "One thing I'm catching before I wrap this: the current batch
     finished the targeted movement and collision parts cleanly, but the full
     steps brief also includes the other motion modes and broader suite shape.
     I'm going to inspect the existing fixture/probe helpers so I can extend
     that work instead of calling it done too early."

     Action/result: Reviewed `tools/qemu_fixture.py`,
     `tools/object_movement_probe.py`, and the existing docs for autonomous
     modes `0x53` and `0x54`.

137. Reported: "For mode 2, I can make the test deterministic: object 1
     approaches object 0, and the visual comparison includes both objects. I'm
     going to add it with an expected position, run QEMU, and if the real engine
     lands at a different near-band coordinate I'll correct the expectation and
     document that as evidence."

     Action/result: Added reusable fixture encoders for `assignn`,
     `set_object_field_1e_var`, `set_object_field_01_var`,
     `approach_first_object_until_near`, `start_random_motion`, and
     `stop_motion_mode`. Added one autonomous mode-2 probe case to
     `tools/object_movement_probe.py`.

138. Reported: "The fast suite is green with 78 tests. Now I'm sending the full
     movement batch through QEMU, including the new autonomous approach case;
     this is the slower but more interesting part."

     Action/result: Ran
     `python3 -B tools/object_movement_probe.py --dos-prefix MA --output build/object-movement-probes/batches/autonomous_modes_001.json --boot-wait 5 --draw-wait 8`.
     The first 14 cases matched. The new threshold-25 approach case mismatched;
     its best captured moving-object position was `(60,75)`, showing the probe
     had entered collision/stuck-recovery behavior near object 0 rather than
     cleanly isolating direct approach completion.

139. Reported: "The mismatch is informative: with a threshold of 25, the object
     appears to hit the collision/stuck-recovery path near the target instead of
     cleanly completing. I'm widening the near threshold so this probe isolates
     mode-2 completion rather than object-object collision recovery."

     Action/result: Changed the approach threshold to `35` and first expected
     boundary position to `(45,80)`. The rerun
     `python3 -B tools/object_movement_probe.py --dos-prefix MB --output build/object-movement-probes/batches/autonomous_modes_002.json --boot-wait 5 --draw-wait 8`
     still mismatched, with best position `(50,80)`.

140. Reported: "The second report gives a clearer source-derived correction:
     mode 2 completed at X 50, not 45. That suggests the near test is strict at
     the threshold boundary; I'm updating the expected result to the real-engine
     coordinate and rerunning once more for a clean green report."

     Action/result: Updated the expected approach position to `(50,80)`. The
     final run
     `python3 -B tools/object_movement_probe.py --dos-prefix MD --output build/object-movement-probes/batches/autonomous_modes_003.json --boot-wait 5 --draw-wait 8`
     matched all 15 cases with 0 mismatches.

141. Reported: "Great, the final QEMU batch is green: 15/15 exact matches,
     including autonomous approach mode. I'm updating the docs and progress log
     with the failed-threshold observation and the corrected passing run,
     because that intermediate result is useful clean-room evidence."

     Action/result: Updated the compatibility docs, object pipeline docs, and
     clean-room executable notes with the mode-2 QEMU evidence.

142. Reported: "I'll take these as an implementation batch: extend the QEMU
     probes, reverse the stuck/recovery path enough to document it, add
     object-field notes where source-backed, and start turning view/cycle
     behavior into the same compatibility harness style."

     Action/result: Reviewed the existing movement, fixture, overlay, and
     graphics docs before editing.

143. Reported: "The current harness can be extended without splitting tools:
     exact-position checks still work for deterministic modes, and I can add a
     property-based comparison for random motion where the engine is allowed to
     choose any final position as long as the object is rendered exactly
     somewhere valid."

     Action/result: Added `comparison_kind="any_position"` support to
     `tools/object_movement_probe.py`, plus `move_to_once_countdown_gated_completion`
     and `random_motion_visible_somewhere` cases.

144. Reported: "The movement harness now has the two new mode cases. I'm
     adding extra overlay cases for cel and group selection on view 11, which
     will exercise different frame dimensions and offsets through the real
     object drawing path."

     Action/result: Added view 11 group 0 frame 1, group 1 frame 0, and group 1
     frame 1 cases to `tools/object_overlay_probe.py`.

145. Reported: "Fast tests are clean. I'm going to run the expanded movement
     QEMU batch first; this will tell us whether countdown-gated mode 3
     completes as expected and whether the random-motion property check is
     robust."

     Action/result: Ran
     `python3 -B tools/object_movement_probe.py --dos-prefix ME --output build/object-movement-probes/batches/motion_modes_004.json --boot-wait 5 --draw-wait 8`.
     All 17 cases matched with 0 mismatches. The countdown-gated one-shot
     `0x51` case completed at `(50,80)`, and the random-motion property case
     matched exactly at final position `(140,112)`.

146. Reported: "The overlay batch is fully green, including all three new view
     11 cel/group selections. I'm going to update the docs now with the QEMU
     results, the mode-3 clarification, the random-motion property result, and
     the source-backed stuck-recovery details from `0x0b36`."

     Action/result: Ran
     `python3 -B tools/object_overlay_probe.py --dos-prefix OE --output build/object-overlay-probes/batches/view_cel_selection_002.json --boot-wait 5 --draw-wait 8`.
     All 22 cases matched with 0 mismatches.

147. Reported: "The label table now includes the mode dispatcher, which will
     help when we compare later interpreter versions with shifted addresses.
     I'm appending the new command log/results to the clean-room notes."

     Action/result: Added symbolic label `code.motion.dispatch_mode_step` for
     image offset `0x067a`; updated compatibility, logic bytecode,
     graphics/object pipeline, and clean-room notes with the new QEMU and
     disassembly evidence.

148. Reported: "One sanity check before I wrap: I covered cel/group selection,
     but cycling deserves at least a source-backed pass too. I'm checking the
     `+0x23` handlers/call sites now so I don't overstate that part."

     Action/result: Disassembled handlers `0x6b82..0x6c17` for actions
     `0x48..0x4b`. The handlers set object byte `+0x23`, object flag bits, and
     optional completion flag byte `+0x27`; this records the setup side only.
     Automatic frame-cycling runtime consumers remain a follow-up target.

## Logic interpreter opcode coverage and QEMU probes

149. Reported: "I'll pick this back up from the current workspace state: first
     I'm going to re-read the local instructions and inspect the new probe/doc
     changes, then I'll run the fast checks before putting QEMU back in the
     loop."

     Action/result: Re-read `AGENTS.md`, inspected the working tree, reviewed
     `tools/logic_interpreter_probe.py`, and checked the handoff chapter
     `docs/src/current_status.md`.

150. Reported: "The handoff page and AGENTS notes are consistent: the immediate
     gap is full logic opcode coverage plus executable-backed probes. I've also
     confirmed there's already a new QEMU logic probe in progress, so I'm going
     to stabilize that rather than starting a parallel harness."

     Action/result: Reviewed the rest of `tools/logic_interpreter_probe.py`,
     its unit tests, and the current `logic_bytecode.md` opcode entries.

151. Reported: "The docs already use paragraph-style opcode entries and the
     condition range is documented. One concrete audit miss remains from the
     earlier pass: action `0x00` is explained structurally but not yet
     represented as a normal action entry, and I'll fold that in while covering
     the rest."

     Action/result: Ran `python3 -B -m unittest discover -s tests`; all 84
     tests passed before the new edits.

152. Reported: "The Python suite is still green after the self-loop change. I'm
     starting the QEMU snapshot batch now; this is the meaningful check for
     whether the synthetic logic resources are exposing interpreter behavior
     cleanly."

     Action/result: Started
     `python3 -B tools/logic_interpreter_probe.py --dos-prefix LJ --output build/logic-interpreter-probes/batches/control_flow_002.json --boot-wait 5 --draw-wait 8`.

153. Reported: "QEMU has built the four fixture directories and is running them
     from the snapshot disk. While it runs, the specific uncertainty I'm testing
     is whether a one-shot transient draw has to be held in a live interpreter
     loop to be visible at screenshot time."

     Action/result: The QEMU batch completed with 4 matches, 0 mismatches, and
     0 errors. The passing cases were `jump_skips_first_draw`,
     `if_false_skips_then_draw`, `not_condition_runs_then_draw`, and
     `or_group_true_runs_then_draw`.

154. Reported: "Good, the QEMU batch now matches 4/4. That means the
     interpreter-control fixtures are viable, and the earlier failures were
     fixture lifetime artifacts rather than evidence against the jump/NOT/OR
     interpretation. Next I'm auditing every opcode label against the docs so
     the 'all opcodes' pass is explicit rather than vibes in a trench coat."

     Action/result: Ran an opcode-label audit comparing
     `tools/disassemble_logic.py` against `docs/src/logic_bytecode.md`.

155. Reported: "The existing `logic_bytecode.md` is already much further along
     than the handoff note implied: it has labels and observed behavior for the
     whole action range through `0xaf`, with only the structural `0x00` missing
     from the normal entry list. I'm going to make that coverage
     machine-checkable enough to trust."

     Action/result: Confirmed the action-name map has 176 entries and no range
     gaps from `0x00..0xaf`; the condition-name map has 19 entries and no gaps
     from `0x00..0x12`.

156. Reported: "The audit came back clean except for exactly one missing normal
     entry: `0x00` (`end`). The action label map covers every byte from `0x00`
     through `0xaf`; the condition label map covers every valid-looking
     condition entry from `0x00` through `0x12`."

     Action/result: Prepared documentation and unit-test edits to add the
     missing `0x00` entry and lock the coverage audit into the test suite.

157. Reported: "I'm going to make three small documentation/test edits now: add
     the missing `0x00` action entry, add a regression test that fails if any
     opcode label drops out of the docs, and record the QEMU control-flow probe
     plus the self-loop correction in the evidence/progress chapters."

     Action/result: Added the `0x00` (`end`) action entry and coverage audit to
     `logic_bytecode.md`, added `tests/test_logic_doc_coverage.py`, and
     documented the logic-interpreter QEMU probe in the compatibility/current
     status/progress chapters.

158. Reported: "One nuance I want to make explicit before calling this done:
     'all opcodes' should include the invalid/structural byte ranges too, not
     just the named action table. I'm adding a short dispatch-range note so
     future readers know what happens to bytes outside the valid
     action/condition catalogs."

     Action/result: Added dispatch-range paragraphs to `logic_bytecode.md` for
     action bytes `0x00`, `0x01..0xaf`, `0xb0..0xfb`, `0xfc`, `0xfd`, `0xfe`,
     and `0xff`, plus condition bytes `0x00..0x12`, `0x13..0x25`,
     `0x26..0xfb`, and structural markers `0xfc..0xff`.

159. Reported: "That range note is in place now: valid actions, invalid action
     bytes, structural bytes, valid condition predicates, reserved condition
     bytes, and condition markers are all spelled out separately. I'm adding
     that last update to the progress record and rerunning verification."

     Action/result: Verification rerun follows this documentation update.

160. Reported: "I'll take this as an implementation pass, not a proposal:
     expand the logic probe harness, add deterministic opcode-family cases,
     attach each case to docs/evidence levels, then verify with unit tests,
     mdBook, and QEMU where practical. First I'm reading the current harness
     and helper patterns so the new cases fit the existing machinery cleanly."

     Action/result: Reviewed `tools/logic_interpreter_probe.py`,
     `tools/qemu_fixture.py`, `tests/test_logic_interpreter_probe.py`, and the
     logic-bytecode/compatibility status docs.

161. Reported: "The probe design is promising: most arithmetic/flag/condition
     opcodes can be validated by doing the operation, then drawing the object
     only if a condition observes the expected state. If the interpreter
     disagrees, the screenshot stays blank and the comparison fails loudly."

     Action/result: Designed the expanded logic probe cases around guarded
     transient drawing through condition blocks.

162. Reported: "One wrinkle with self-looped fixtures: mutating opcodes like
     `inc` would keep changing state every cycle. I'm making each arithmetic
     case reset its inputs before the tested action, so the condition remains
     true on every interpreter pass and the transient draw is stable at capture
     time."

     Action/result: Added reset-before-test bytecode patterns for mutable
     variable, flag, and object-field probes.

163. Reported: "I'm editing the logic probe now: adding bytecode builders for
     variable, flag, comparison, and simple object-field checks, then folding
     those into the default QEMU batch so they run with the existing
     control-flow cases."

     Action/result: Expanded `tools/logic_interpreter_probe.py` to 27 default
     cases covering control flow, variable arithmetic, indirect variables,
     flags, comparison predicates, and selected object-field getters/setters.

164. Reported: "The default logic batch now includes control flow plus
     arithmetic, indirect-variable, flag, comparison, and three simple
     object-field probes. I'm running the fast unit tests first; then I'll send
     the expanded batch through QEMU and correct anything the original engine
     disagrees with."

     Action/result: Ran the logic probe unit tests successfully and confirmed
     the expanded default batch contains 27 unique cases.

165. Reported: "The expanded batch has 27 cases and the local probe tests pass.
     I'm launching QEMU now; the object-field cases are the most likely to teach
     us something because they touch engine object records without drawing
     persistent objects."

     Action/result: Started
     `python3 -B tools/logic_interpreter_probe.py --dos-prefix LK --output build/logic-interpreter-probes/batches/opcode_families_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`.

166. Reported: "QEMU has all 27 fixture directories loaded into the snapshot
     disk and is stepping through them. I used `--stop-on-failure` for this
     first pass, so if one case is wrong we get the earliest useful failure
     instead of a pile of downstream noise."

     Action/result: QEMU continued executing the one-boot snapshot batch.

167. Reported: "The expanded QEMU run is green: 27/27 exact visual matches.
     That gives us executable evidence for the core arithmetic opcodes,
     indirect variable forms, flag opcodes, comparison predicates, and a few
     simple object-field getter/setter pairs. Next I'm turning that into an
     evidence matrix so the docs distinguish 'QEMU validated' from
     'source-backed only.'"

     Action/result: Saved the matching report at
     `build/logic-interpreter-probes/batches/opcode_families_001.json`.

168. Reported: "I'm adding a small generator for the evidence matrix rather
     than hand-maintaining a 176-row table. The generator uses only the local
     dispatch table and our local opcode-label map, then annotates rows with the
     QEMU probes we have actually run."

     Action/result: Added `tools/logic_opcode_evidence.py`, linked the generated
     chapter from `SUMMARY.md`, and added a unit test that checks the generated
     evidence matrix is current.

169. Reported: "The generator is in place and linked into the book. I'm
     generating the evidence chapter now, then I'll wire the run result into the
     compatibility/evidence notes."

     Action/result: Generated `docs/src/logic_opcode_evidence.md` and verified
     it with `python3 -B tools/logic_opcode_evidence.py --check`.

170. Reported: "The generated matrix now covers every action row `0x00..0xaf`,
     all known condition rows `0x00..0x12`, and the invalid/structural byte
     ranges. I'm tightening the tests around the new probe cases so the
     expanded default batch doesn't accidentally shrink later."

     Action/result: Expanded `tests/test_logic_interpreter_probe.py` to assert
     representative variable, flag, comparison, arithmetic, control-flow, and
     object-field cases remain in the default batch.

171. Reported: "I'm updating the documentation trail with the exact QEMU batch
     name and the new evidence chapter. This is the clean-room receipt: what
     ran, what matched, and what remains source-backed rather than
     emulator-backed."

     Action/result: Updated compatibility, current-status, logic-bytecode, and
     progress docs with the expanded logic probe and evidence matrix.
