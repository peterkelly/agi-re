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

172. Reported: "I'll do these in order and keep the artifacts testable: first
     multi-logic call/resume fixtures, then variable-backed resource/object
     variants, then object predicates, then strings/messages, then
     inventory/table predicates. I'm going to inspect the current fixture
     builder and logic resource format first so the new probes extend the
     existing QEMU harness instead of becoming a separate one-off."

     Action/result: Reviewed the logic interpreter probe, QEMU fixture helper,
     tests, opcode evidence generator, and local logic resource documentation.

173. Reported: "The existing `logic_resource()` helper emits a minimal
     no-message resource, which is fine for the first three steps. For the
     string/message step I need to construct a real custom message table, so
     I'm checking the locally documented message format and existing logic
     parser before editing."

     Action/result: Re-read `docs/src/logic_resources.md`, confirming
     `code_length`, `message_count`, table offsets relative to table base, and
     XOR-encrypted text using the `Avis Durgan` key.

174. Reported: "I'm going to extend the single logic probe harness rather than
     create five tools. The key change is letting a case patch multiple logic
     resources into `VOL.3` and optionally give logic 0 a custom message table,
     which unlocks call/load and string/message probes cleanly."

     Action/result: Updated `tools/qemu_fixture.py` so `logic_resource()` can
     encode custom message tables.

175. Reported: "The fixture helper now supports encrypted custom logic messages
     using the locally documented XOR key and offset-table layout. Next I'm
     adding the multi-logic/resource patching and the new probe cases in
     sequence."

     Action/result: Added extra-logic metadata, message metadata, multi-logic
     `VOL.3` packing, and new logic probe cases for the five requested groups.

176. Reported: "I've got the new cases drafted; I spotted two fixture-shape
     issues before running them: a persistent-object var-resource case should
     not use the conditional transient-draw wrapper, and the NOT-always-false
     probe needs the marker before the condition byte. I'm tightening those now
     and then I'll run the local tests."

     Action/result: Corrected the persistent object case and the NOT marker
     ordering.

177. Reported: "Multi-resource fixture patching is in. I'm running the focused
     tests now; if they pass, I'll inspect a generated fixture byte layout
     before letting QEMU at the larger batch."

     Action/result: Ran focused logic probe and fixture tests; 28 tests passed.
     The default logic probe batch now contains 47 cases.

178. Reported: "The focused tests pass and the default batch is now 47 cases.
     I'm starting QEMU with stop-on-failure; this will validate the steps in
     sequence and stop at the first semantic mismatch so I can correct the
     model before continuing."

     Action/result: Started the all-case QEMU run
     `five_steps_001.json`.

179. Reported: "Because the batch is ordered, the first failing case will tell
     us which requested step needs attention. Cases 28-31 are call/load/resume,
     then the variable-backed object/resource cases, then object predicates,
     strings/messages, and inventory/table markers."

     Action/result: The all-case QEMU run did not reach execution. The snapshot
     disk filled while copying fixture directories, so the failure was a
     harness capacity limit rather than an interpreter mismatch.

180. Reported: "The first QEMU attempt did not reach execution: the snapshot
     boot disk filled up while copying 47 full SQ2 fixture directories. That's
     a harness capacity issue, not an interpreter mismatch. I'll run the new
     five-step cases as a smaller batch and add a case filter so future runs
     don't have to copy the entire corpus."

     Action/result: Added repeated `--case` filtering to
     `tools/logic_interpreter_probe.py`.

181. Reported: "The harness can now run named subsets with repeated `--case`
     flags. I'm going to validate the five requested steps in chunks: call/load
     /resume first, then variable-backed resources, then predicates,
     strings/messages, and inventory/table markers."

     Action/result: Started filtered QEMU validation.

182. Reported: "Starting step 1 now: `call_logic`, `load_logic` plus
     `call_logic`, `call_logic_var`, and the resume-action smoke probe."

     Action/result: Step 1 matched QEMU with 4 matches, 0 mismatches, and
     0 errors.

183. Reported: "Step 1 is green: all four call/load/resume probes matched. I'm
     moving to step 2, the variable-backed object/resource variants, including
     var-based transient drawing and immediate-completion `move_object_to_var`."

     Action/result: Step 2 matched QEMU with 4 matches, 0 mismatches, and
     0 errors.

184. Reported: "Step 2 is green too. The persistent object selected through
     variable-backed resource/group/frame actions matched view 11 group 1 frame
     1, and `0x7b` matched the same cel through all-variable operands. Next is
     object rectangle predicates."

     Action/result: Step 3 matched QEMU with 4 matches, 0 mismatches, and
     0 errors.

185. Reported: "Step 3 is green: all four object rectangle predicates matched.
     I'm moving to strings/messages now; this is the new custom-message-table
     path, so if anything breaks it will most likely be message encoding or
     parser state rather than drawing."

     Action/result: Step 4 matched QEMU with 2 matches, 0 mismatches, and
     0 errors.

186. Reported: "Step 4 is green. The custom message resource was accepted by
     the original loader, `0x72` copied message text into string slots, `0x0f`
     normalized and compared it, and `0x75` plus `0x0e` recognized `look`. Now
     I'm validating the inventory/object-table marker actions and predicates."

     Action/result: Started the inventory/table marker QEMU batch.

187. Reported: "The inventory/table step covers both predicates (`0x09`,
     `0x0a`) and the marker actions `0x5c..0x61`. I'm running them together
     because they're small and all use the same table entry."

     Action/result: Step 5 matched QEMU with 6 matches, 0 mismatches, and
     0 errors.

188. Reported: "QEMU is executing the six inventory/table cases now. If these
     match, all five requested steps will have QEMU-backed evidence, with the
     larger all-cases run split only because the DOS snapshot disk filled up."

     Action/result: Confirmed the six inventory/table cases matched.

189. Reported: "Step 5 is green. I'm updating tests and the evidence matrix
     annotations now so the new QEMU-backed opcodes show up as validated rather
     than source-only."

     Action/result: Updated regression tests and regenerated the opcode
     evidence matrix.

190. Reported: "The evidence matrix is regenerated with the newly validated
     opcodes. I'm documenting both the successful step runs and the one failed
     'all 47 at once' attempt, because the failure tells future us about
     snapshot disk capacity rather than AGI behavior."

     Action/result: Updated compatibility, current-status, clean-room notes,
     and progress docs.

191. Reported: "Checkpoint is `bbda90f`; only generated/local artifacts remain
     untracked. I'm starting the next pass by checking the existing object/view
     action notes and local view metadata so the new probes use expected values
     that are already derived from local evidence."

     Action/result: Reviewed object/view getter and bitfield notes in
     `logic_bytecode.md`, inspected view 11 with `tools/inspect_view.py`, and
     checked the current evidence matrix rows.

192. Reported: "For this pass I'm splitting the target actions into two
     evidence types: value probes where a getter/condition observes the
     expected state, and smoke probes for bitfield actions whose direct bit
     value is not exposed by an existing script predicate. That keeps the docs
     honest: 'this opcode executed and consumed operands under QEMU' is useful,
     but different from proving every downstream semantic."

     Action/result: Added value probes for object/view metadata getters,
     variable-backed field `+0x24`, inactive object-distance behavior, and
     `0x4d` clearing direction byte `+0x21`; added one dispatch smoke case for
     selected bitfield/helper actions.

193. Reported: "The new object/view cases are in: metadata getters,
     variable-backed field `+0x24`, inactive distance behavior, `0x4d` clearing
     direction, and a dispatch smoke case for the bitfield/helper actions with
     no direct script-visible getter. I'm running the focused tests now."

     Action/result: Ran `python3 -B -m unittest tests.test_logic_interpreter_probe`;
     6 tests passed, and the default logic probe set now contains 52 cases.

194. Reported: "The local tests pass and the default set is now 52 cases. I'm
     running just the five new object/view cases through QEMU so the snapshot
     disk stays small."

     Action/result: The first QEMU attempt under sandbox failed before
     execution because the VNC socket bind was not permitted.

195. Reported: "QEMU was blocked by the sandbox when binding the local VNC
     socket. I'm rerunning the same filtered batch with approval so the emulator
     can start; this is the same kind of local QEMU validation we've been
     using."

     Action/result: Reran the filtered object/view batch with approved
     escalation.

196. Reported: "QEMU is running the five filtered cases now. The first four are
     value probes; the fifth is intentionally a dispatch smoke probe for
     bitfield/helper actions that don't expose a simple script-visible bit
     readback."

     Action/result: The QEMU batch matched with 5 matches, 0 mismatches, and
     0 errors.

197. Reported: "The QEMU batch is green: five matches, zero mismatches. I'm
     updating the evidence matrix now, marking direct value probes as
     QEMU-validated and the remaining bitfield/helper actions as QEMU
     dispatch-smoke rather than overstating their full semantics."

     Action/result: Updated `tools/logic_opcode_evidence.py` and regenerated
     `docs/src/logic_opcode_evidence.md`.

198. Reported: "The generated matrix now has a separate `QEMU dispatch-smoke`
     evidence level. I'm documenting the new object/view batch and the
     distinction between value probes and smoke probes in the project notes."

     Action/result: Updated compatibility, current-status, clean-room notes,
     and progress docs with the object/view follow-up batch.

199. Reported: "I've got the shape of it now: mdBook is using its default narrow
     content column, and there's no project CSS override yet. I'm going to add a
     small theme stylesheet so wide reference tables can use more horizontal
     room and scroll inside themselves when they still overflow."

     Action/result: Inspected `docs/book.toml`, the generated mdBook CSS, and the
     current worktree state before adding the table-layout override.

200. Reported: "I found the progress log tail and confirmed the worktree is clean
     apart from the usual generated/untracked artifacts. Next I'm checking
     mdBook's generated selector names so the override lands on the actual
     content container instead of guessing."

     Action/result: Confirmed mdBook wraps generated tables in `.table-wrapper`
     and applies the page width through `--content-max-width`.

201. Reported: "The generated mdBook CSS confirms the hard cap is
     `--content-max-width: 750px`, applied to `.content main`. I can override
     that variable cleanly from an `additional-css` file and then give tables
     their own horizontal overflow behavior."

     Action/result: Added `docs/theme/wide-tables.css` to widen the content
     column and make wide tables scroll horizontally while preserving readable
     wrapping in the final detail column.

202. Reported: "mdBook already wraps tables in `.table-wrapper`, but only adds
     overflow; the table itself can still be squeezed by the 750px main column.
     I'm adding a source-controlled CSS file that widens the content column and
     keeps table columns readable before falling back to horizontal scrolling."

     Action/result: Updated `docs/book.toml` to load the new stylesheet via
     `additional-css`.

203. Reported: "I'll rework the logic bytecode chapter now that the book can
     handle wider tables. First I'm going to inspect the chapter structure and
     the current markdown patterns so the table conversion is deliberate rather
     than a blind format pass."

     Action/result: Read `docs/src/logic_bytecode.md`, checked the progress log
     tail, and confirmed the worktree state before editing.

204. Reported: "The chapter has several paragraph lists that are really
     reference tables: runtime metadata examples, main-stream byte ranges, the
     condition table/ranges/predicates, action entry examples, and decoded
     action families. I'm reading the rest of the file now so I don't miss
     another block that should be restored to table form."

     Action/result: Reviewed the remaining logic bytecode chapter sections and
     identified compact opcode catalogs versus longer semantic explanations.

205. Reported: "There are also long explanatory opcode entries where paragraphs
     are still the better shape, especially for movement, parsing, save/restore,
     and display behavior. I'm going to table the compact catalog-like material
     and leave the multi-paragraph semantic notes as prose."

     Action/result: Chose a mixed layout: tables for opcode facts and prose for
     state-machine or helper-flow details.

206. Reported: "The densest restored tables will be in the front half of the
     chapter and the local scan summary. For the long `decoded action families`
     section, I'm going section by section: compact opcode rows become tables,
     while explanatory helper blocks stay as explanatory blocks."

     Action/result: Collected line-numbered context for the runtime, condition,
     action, and scan-summary sections.

207. Reported: "I've separated `catalog data` from `semantic explanation`. The
     first patch is the high-value cleanup: dispatch/condition catalogs and the
     short arithmetic/flag/action summary rows go back into tables."

     Action/result: Converted metadata examples, main-stream byte ranges,
     condition entries/ranges/predicates, action examples, variable actions, and
     flag actions to Markdown tables.

208. Reported: "The first conversion is in. I'm moving through the action
     families next; these are especially useful as tables because implementers
     will scan by opcode, label, handler, and effect."

     Action/result: Inspected the object/view, resource-control, object-state,
     message/UI, and remaining-entry sections for table conversion.

209. Reported: "The remaining opcode blocks are large, but most are structurally
     regular. I'm going to table the resource/object/UI families now and keep
     the detailed movement subsections as prose where they explain per-cycle
     behavior."

     Action/result: Converted the object/view action and resource/interpreter
     control catalogs to `Opcode`, `Label`, `Handler`, and `Observed action`
     tables.

210. Reported: "I'm making the action-family tables broad but shallow: `Opcode`,
     `Label`, `Handler`, `Observed action`. The final action column can now wrap
     inside the wider mdBook layout, which is exactly what that CSS change was
     for."

     Action/result: Kept long behavior descriptions in the final table column so
     rows remain scan-friendly without losing evidence detail.

211. Reported: "The object/view and resource-control catalogs are tabled now.
     Next I'm doing the object-state, message/UI, and misc sections, then I'll
     build the book to catch Markdown table mistakes."

     Action/result: Converted additional object-state, post-movement, dirty
     position, and object-field-24 action summaries to tables.

212. Reported: "Object state is now much easier to scan. I'm converting the
     remaining compact UI/resource/session listings the same way; after that
     I'll make sure no `Count:` opcode paragraphs remain in the scan summary."

     Action/result: Converted message-display, menu/list, and text/input action
     catalogs to tables.

213. Reported: "Most of the chapter's UI/action catalogs are back in table form.
     I'm doing the final resource/session/misc groups now, plus the local SQ2
     frequency lists at the end."

     Action/result: Converted resource/table actions, session-control actions,
     miscellaneous actions, remaining table entries, and frequency summaries to
     tables.

214. Reported: "The conversion pass is complete. I'm checking for leftover
     paragraph-style opcode summaries and then I'll build the book; Markdown
     table syntax is fussy enough that I want mdBook to be the judge."

     Action/result: Initial leftover scan found only movement-mode opcode
     paragraphs; `mdbook build docs` succeeded.

215. Reported: "The only opcode paragraphs I expect to remain are the movement
     entries where the surrounding explanation matters. I'm rerunning the
     leftover scan with safer shell quoting and then building the mdBook."

     Action/result: Confirmed the remaining paragraph-style opcode summaries
     were `0x51..0x54` movement actions and the book still built successfully.

216. Reported: "The leftover scan found exactly the movement opcodes I
     intentionally left in prose. I'm going to improve those too by adding a
     compact movement-mode table, while keeping the multi-paragraph per-cycle
     details underneath."

     Action/result: Added a movement-mode entry-point table for opcodes
     `0x51..0x54` and rewrote the surrounding prose to avoid duplicate
     paragraph-style opcode summaries.

217. Reported: "That takes care of the movement outliers: they now have a table
     for the entry-point facts, with the state-machine details kept beneath it.
     I'm doing the final validation pass now."

     Action/result: Verified no paragraph-style opcode summary patterns remain,
     `mdbook build docs` succeeds, and `git diff --check` is clean.

218. Reported: "The book builds cleanly and `git diff --check` is clean. I'm
     adding the progress-log entries for this documentation pass, then I'll
     check the final status."

     Action/result: Recorded the logic-bytecode table conversion pass in this
     progress log.

219. Reported: "I'll pick the thread back up at the logic-interpreter probe
     expansion. I'm going to inspect the current probe harness, evidence
     matrix, and source-backed-only opcode rows so the next batch targets
     behaviors that can actually be observed in QEMU."

     Action/result: Inspected the current probe harness, evidence matrix, and
     documentation targets for additional runtime-visible opcodes.

220. Reported: "The current harness already has 52 default cases and a separate
     smoke level in the evidence matrix. The obvious next useful target is to
     turn some smoke/source-backed object field helpers into value probes where
     we can observe the effect through existing getters or visible drawing."

     Action/result: Identified object-state, random, and no-op action entries
     suitable for direct QEMU probes.

221. Reported: "I'm going to add a small batch of value/smoke probes that are
     low-risk and visible: object position variants `0x28`, `0x93`, `0x94`,
     deactivation/clear-all effects `0x24` and `0x22`, deterministic random
     `0x82` with equal bounds, and no-op/runtime-skip entries `0x7f`, `0x9b`,
     `0xaf`."

     Action/result: Added nine candidate cases to
     `tools/logic_interpreter_probe.py`.

222. Reported: "I'm picking up from the just-added probe batch. First I'll run
     the harness tests so we know whether the new cases are structurally sound
     before spending QEMU time on them."

     Action/result: Ran `python3 -B -m unittest tests.test_logic_interpreter_probe`;
     all six tests passed.

223. Reported: "The local probe tests pass, so the new cases are well-formed.
     I'm going to run them against the original engine now; this is the part
     that tells us which hypotheses deserve to graduate from static/source-backed
     notes into runtime evidence."

     Action/result: Started the nine-case QEMU probe batch; the sandbox blocked
     the initial VNC socket bind.

224. Reported: "As expected, the sandbox blocked QEMU's local VNC socket. I'll
     rerun the same batch with approval so the emulator can bind its display
     port."

     Action/result: Reran the nine-case batch with elevated QEMU permission.

225. Reported: "The QEMU batch is running from a snapshot now. While it works
     through the fixtures, I'll prep the evidence-matrix and docs context so
     the runtime results can be recorded cleanly once they land."

     Action/result: Reviewed `tools/logic_opcode_evidence.py` and relevant docs
     while QEMU was running.

226. Reported: "The docs context confirms these opcodes were previously mostly
     source-backed or smoke-only. If the batch passes, I'll promote the specific
     ones with observable outcomes into the generated evidence matrix instead
     of leaving them as 'we saw it in disassembly.'"

     Action/result: Confirmed target opcodes were suitable for evidence-level
     promotion pending QEMU results.

227. Reported: "Still waiting on QEMU; snapshot batches can be quiet until the
     report is written. I'm letting it finish rather than interrupting, because
     partial emulator runs are much less useful as evidence."

     Action/result: Continued waiting for the snapshot-backed QEMU batch.

228. Reported: "First two probes matched: `0x28` adds the variable deltas as
     expected, and `0x82` with equal bounds stores that bound. The no-op and
     object activation cases are next in the batch."

     Action/result: Observed the first two QEMU matches from the running batch.

229. Reported: "Good batch, with one interesting wrinkle: eight passed and
     `clear_all_object_bits_removes_persistent_draw` did not. I'm going to
     inspect that mismatch rather than paper over it; `0x22` may be clearing
     active/update bits but not removing an already-linked draw entry in the way
     my first fixture assumed."

     Action/result: Inspected the report
     `build/logic-interpreter-probes/batches/object_state_misc_001.json`; eight
     cases matched and the `0x22` fixture mismatched.

230. Reported: "The mismatch is exactly at the first object's footprint, so the
     original engine still draws the previously activated object after `0x22` in
     this same logic pass. I'm reading the harness shape now and will turn this
     into a positive probe for the behavior we actually observed: 'clear bits
     does not immediately unlink the already-active draw entry.'"

     Action/result: Confirmed the mismatch bounding box was the previously
     activated object's visible footprint.

231. Reported: "I'm going to make the probe harness a bit more expressive so a
     case can expect two rendered objects. That lets the `0x22` probe encode the
     observed behavior directly, instead of pretending the only valid outcome is
     a single sprite."

     Action/result: Began extending `LogicInterpreterCase` with optional
     additional expected sprites.

232. Reported: "The first patch missed because the constructor is still using
     positional arguments. I've got the exact spot now and will apply the
     narrower edit."

     Action/result: Added the optional `expected_extra_sprites` field and
     constructor plumbing.

233. Reported: "Now I'm changing the `0x22` case itself from a negative
     expectation into a positive one: expect the old persistent object plus the
     new transient draw. That will give us a sharper note for the spec."

     Action/result: Renamed the case to
     `clear_all_object_bits_keeps_current_draw_entry` and gave it two expected
     sprites.

234. Reported: "One more harness edit: comparison needs to render any extra
     expected sprites before it overlays the primary expected sprite. After that
     I'll rerun just the corrected `0x22` case."

     Action/result: Updated `compare_capture()` to compose extra expected
     sprites.

235. Reported: "I'll also update the unit-test coverage list so the newly
     promoted cases are tracked by name. Small bookkeeping, but it helps prevent
     accidental loss of these probes later."

     Action/result: Added explicit test coverage for the nine new probe case
     ids and raised the minimum case-count assertion.

236. Reported: "The probe catalog now names all nine new cases explicitly. I'm
     running the local tests and a quick capture comparison path check before
     asking QEMU to revalidate the corrected `0x22` fixture."

     Action/result: `python3 -B -m unittest tests.test_logic_interpreter_probe`
     passed again.

237. Reported: "Local tests are green. I'll rerun only the corrected `0x22`
     fixture now, which should be fast relative to the full nine-case sweep."

     Action/result: The sandbox again blocked the first QEMU VNC bind attempt.

238. Reported: "Same socket restriction on the single rerun; I'll rerun it with
     approval."

     Action/result: Reran the corrected `0x22` fixture with elevated QEMU
     permission.

239. Reported: "The corrected `0x22` probe matches. I'm going to promote the
     QEMU-backed opcodes in the evidence generator now, including the nuance
     that `0x22` clears bits without immediately removing the current draw
     entry."

     Action/result: Added QEMU evidence entries for `0x22`, `0x24`, `0x28`,
     `0x7f`, `0x82`, `0x93`, `0x94`, `0x9b`, and `0xaf`.

240. Reported: "The evidence map is updated. Next I'll regenerate the mdBook
     evidence chapter and run its consistency check, then I'll update the
     narrative notes with the exact commands and outcomes."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md` and ran
     `python3 -B tools/logic_opcode_evidence.py --check` successfully.

241. Reported: "The generated evidence chapter and its check both pass. I'm now
     recording the reverse-engineering trail: the failed first hypothesis for
     `0x22`, the corrected fixture, and which opcodes moved to runtime-backed
     evidence."

     Action/result: Updated clean-room notes, compatibility testing docs, and
     current status with the new probe evidence.

242. Reported: "Documentation is updated. I'm running the normal validation pass
     now: full Python tests, evidence check, mdBook build, and whitespace diff
     check."

     Action/result: The first full test run exposed that the documentation
     coverage test still recognized only the older paragraph-style opcode
     entries.

243. Reported: "The book, evidence check, and whitespace check passed, but the
     full test suite exposed a doc-coverage parser regression: it no longer
     recognizes the tabled opcode entries in `logic_bytecode.md`. I'm going to
     adjust that test to understand the current table format rather than
     weakening coverage."

     Action/result: Updated the coverage test to accept documented opcode rows
     in the current Markdown table format.

244. Reported: "The coverage test was still looking for the older bold
     paragraph heading pattern only. I'm updating it to accept both that
     historical format and the current Markdown table rows, while still
     requiring every opcode label to appear."

     Action/result: `tests/test_logic_doc_coverage.py` now accepts both
     paragraph headings and table rows.

245. Reported: "The coverage test now recognizes table rows as documented
     opcode entries. I'm rerunning the full validation pass to make sure that
     was the only failure."

     Action/result: `python3 -B -m unittest discover -s tests` passed 91 tests;
     `mdbook build docs` and `git diff --check` also passed.

246. Reported: "Everything now validates: 91 Python tests, mdBook build, and
     diff check are clean. I'm doing a final status/diff pass so the wrap-up is
     precise and doesn't hide generated debris."

     Action/result: Confirmed the modified tracked files and removed
     `tools/__pycache__/`.

247. Reported: "I'll continue from the freshly committed logic-probe work. I'm
     going to scan the evidence matrix for still source-backed opcodes and pick
     another cluster that can be validated through visible state or
     script-observable getters."

     Action/result: Confirmed the worktree only had the known generated/input
     directories and that the opcode evidence matrix was current.

248. Reported: "The worktree is clean except the known generated/input
     directories, and the evidence matrix is current. My first grep had shell
     quoting trouble around backticks, so I'm switching to a small local parse
     of the generated matrix."

     Action/result: Replaced the failing backtick-sensitive scan with simpler
     source-backed and dispatch-smoke matrix scans.

249. Reported: "The current harness already has good coverage for variables,
     strings, inventory markers, object positions, and several draw paths. I'm
     checking the remaining source-backed rows now with simpler shell quoting;
     likely next targets are object bitfield helpers or small global/object
     field actions that can be observed indirectly."

     Action/result: Identified `0x1f` and the object field `+0x23` family
     `0x48..0x4b` as practical next targets.

250. Reported: "The best near-term candidates are object/state opcodes, not
     UI/save/sound paths. I'm going to focus on opcodes around `0x2d..0x50`
     where disassembly says they change object bits or fields; some can be made
     visible via drawing, getters, or movement side effects."

     Action/result: Reviewed object-state docs and movement harness context for
     observable probe options.

251. Reported: "A useful small batch is emerging: variable-backed `load_view`
     (`0x1f`) can be validated by drawing the loaded view, while `0x49` and
     `0x4b` can at least be value-probed for their documented flag-clearing
     operand. I'll add those, plus dispatch-smoke cases for `0x48` and `0x4a`
     so the whole `+0x23` setup family has runtime coverage."

     Action/result: Chose a five-case follow-up batch covering `0x1f` and
     `0x48..0x4b`.

252. Reported: "I'm going to add a small bit of flexibility to the logic probe
     harness first: most cases preload view 11, but the `load_view_var` probe
     must start without that preload or it wouldn't prove anything. Then I'll
     add the five cases."

     Action/result: Added the optional `preload_view_no` hook to
     `tools/logic_interpreter_probe.py`.

253. Reported: "The preload hook is in. I'm adding a tiny local condition
     helper for 'flag is not set,' then the new runtime cases in the existing
     case catalog."

     Action/result: Added `not_flag_set_condition()`.

254. Reported: "Now I'm inserting the cases themselves: one `load_view_var`
     value probe, two `+0x23` mode actions that clear a flag as documented, and
     two dispatch-smoke cases for the no-flag mode variants."

     Action/result: Added `load_view_var_allows_following_draw`,
     `object_field_23_mode0_dispatch_smoke`,
     `object_field_23_mode1_clears_flag`,
     `object_field_23_mode3_dispatch_smoke`, and
     `object_field_23_mode2_clears_flag`.

255. Reported: "The new cases are in. I'm updating the unit test's named
     coverage list so these probes stay pinned in the default catalog."

     Action/result: Updated `tests/test_logic_interpreter_probe.py` to require
     the five new case ids.

256. Reported: "I'll run the local harness tests before QEMU. If any of these
     bytecode snippets are malformed, it's cheaper to catch it here."

     Action/result: `python3 -B -m unittest tests.test_logic_interpreter_probe`
     passed.

257. Reported: "Local tests pass. I'll run the five new cases against the
     original engine now; if the VNC bind hits the sandbox again I'll rerun with
     approval."

     Action/result: The first QEMU run was blocked by the sandbox VNC bind
     restriction.

258. Reported: "The sandbox blocked the VNC socket as expected. I'll rerun the
     same batch with QEMU permission."

     Action/result: Reran the five-case batch with elevated QEMU permission.

259. Reported: "The QEMU snapshot batch is running. While it does that, I'll
     prepare the evidence-map changes so they're ready if the cases match."

     Action/result: Reviewed the evidence generator and existing docs while the
     QEMU batch ran.

260. Reported: "The docs already have source notes for `0x1f` and `0x48..0x4b`;
     this batch is specifically trying to convert part of that into observed
     engine behavior. I'm checking the QEMU run now."

     Action/result: The batch
     `build/logic-interpreter-probes/batches/load_view_field23_001.json`
     matched all five cases with 0 mismatches and 0 errors.

261. Reported: "All five matched. I'll promote `0x1f`, `0x49`, and `0x4b` to
     QEMU-validated evidence, and mark `0x48`/`0x4a` as dispatch-smoke since
     those cases prove runtime execution and operand consumption but not the
     hidden `+0x23` byte value directly."

     Action/result: Updated `tools/logic_opcode_evidence.py` accordingly.

262. Reported: "The evidence generator is updated. I'm regenerating the matrix
     and checking it, then I'll record the commands and results in the
     clean-room docs."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md` and checked
     it successfully.

263. Reported: "The matrix regenerated cleanly. I'm updating the narrative docs
     now: compatibility commands, chronological clean-room notes, current
     status, and the progress log for the updates from this run."

     Action/result: Updated the clean-room notes, compatibility testing page,
     and current status.

264. Reported: "I'm appending a short dated evidence section and compatibility
     snippet for this batch. The key distinction in the docs will be
     'value-backed' for `0x1f`, `0x49`, `0x4b` versus 'dispatch-smoke' for
     `0x48`, `0x4a`."

     Action/result: Added the dated evidence section and compatibility command.

265. Reported: "The compatibility docs now have the replay command. I'm updating
     current status so the next session won't repeat this cluster."

     Action/result: Current status now mentions the `0x1f` and `0x48..0x4b`
     follow-up batch.

266. Reported: "I'm also adding a couple of concise notes in the opcode chapter
     itself, so readers of the spec see what was runtime-confirmed without
     having to jump to the evidence matrix."

     Action/result: Added concise QEMU evidence notes to
     `docs/src/logic_bytecode.md`.

267. Reported: "Docs are updated. I'm running the validation pass now: full
     tests, evidence consistency, mdBook build, and diff whitespace checks."

     Action/result: `python3 -B -m unittest discover -s tests` passed 91 tests;
     `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
     and `git diff --check` also passed.

268. Reported: "Everything validates: 91 tests, evidence check, mdBook, and
     whitespace checks are clean. I'm doing final status and diff review, then
     I'll wrap this pass."

     Action/result: Confirmed the diff is limited to logic-probe source,
     evidence generation, tests, and documentation; generated/input directories
     remain untracked.

269. Reported: "I'll continue with the object bit/control path I recommended:
     first I'm checking the current uncommitted pass so I can build on it
     cleanly rather than trampling the latest probe work."

     Action/result: Confirmed the previous variable-view/object-field probe
     pass was still uncommitted and read `AGENTS.md` for the project rules.

270. Reported: "The previous pass is still uncommitted, and I'm going to extend
     it rather than split the thread artificially. The most promising value
     probe is `0x44`: set the collision-skip bit with `0x43`, clear it with
     `0x44`, then prove collision blocking returns during movement."

     Action/result: Inspected the object movement harness and existing
     collision-skip evidence.

271. Reported: "The movement harness has exactly the shape we need, but it only
     has a 'set skip bit' helper. I'm adding the companion `0x44` encoder plus
     a filtered movement case that sets then clears the bit and should collide
     again."

     Action/result: Added `clear_object_bit_0200_action()` to
     `tools/qemu_fixture.py`.

272. Reported: "The raw encoder is in. Now I'm threading a clear-skip option
     through the movement case model and adding the concrete collision-restored
     case."

     Action/result: Added `moving_clear_skip_collision`, filtered `--case`
     support, and case `move_collision_clear_skip_bit_blocks_again` to
     `tools/object_movement_probe.py`.

273. Reported: "The tests now cover the new encoder, filtered movement case
     loading, and the new collision-restored case. I'll run the focused tests,
     then the single QEMU case."

     Action/result: Updated `tests/test_qemu_fixture.py` and
     `tests/test_object_movement_probe.py`; focused tests passed.

274. Reported: "Focused local tests pass. I'm running just the new movement
     probe in QEMU now; the new `--case` filter avoids rerunning the whole
     movement suite."

     Action/result: The first QEMU run was blocked by the sandbox VNC bind
     restriction.

275. Reported: "The QEMU VNC bind hit the sandbox restriction. I'll rerun the
     same single-case probe with permission."

     Action/result: Reran the single-case movement probe with elevated QEMU
     permission.

276. Reported: "The `0x44` probe matched: after setting and then clearing the
     collision-skip bit, the object is blocked by the obstacle again. I'm
     promoting `0x44` from dispatch-smoke to QEMU-validated evidence."

     Action/result: QEMU batch
     `build/object-movement-probes/batches/clear_skip_bit_001.json` matched
     with 1 match, 0 mismatches, and 0 errors.

277. Reported: "Evidence metadata is updated. I'll regenerate the generated
     matrix, then update the docs with the movement batch command and result."

     Action/result: Added `0x44` to QEMU-validated evidence and removed it from
     dispatch-smoke evidence.

278. Reported: "The matrix now treats `0x44` as QEMU-validated. I'm adding the
     clean-room evidence trail and a short spec note explaining what the new
     collision-restored probe proves."

     Action/result: Regenerated and checked `docs/src/logic_opcode_evidence.md`.

279. Reported: "I'm patching the docs in the same evidence-first style: one
     dated note in the clean-room log, one compatibility command, and one
     concise semantics sentence in the object/graphics model."

     Action/result: Updated `docs/src/graphics_object_pipeline.md` and
     `docs/src/logic_bytecode.md` with the `0x44` observation.

280. Reported: "The spec now records the behavior. I'm adding the reproducible
     QEMU command to the compatibility chapter next."

     Action/result: Added the `clear_skip_bit_001.json` QEMU command to
     `docs/src/compatibility_testing.md`.

281. Reported: "Compatibility has the new command. I'm updating current status
     and the clean-room notes with the exact batch result."

     Action/result: Updated `docs/src/current_status.md`.

282. Reported: "I'm adding a dated clean-room entry rather than folding this
     into the older movement section, because it's a new QEMU observation made
     in this pass."

     Action/result: Added the dated `0x44` clean-room section to
     `docs/src/clean_room_executable_notes.md`.

283. Reported: "The clean-room notes now include the exact `0x44` batch and
     result. I'm adding progress-log entries for this continuation before the
     final validation run."

     Action/result: Appended progress-log entries for the `0x44` probe pass.

284. Reported: "Progress log is updated. I'm running the full validation sweep
     now, including the movement tests touched by this pass."

     Action/result: `python3 -B -m unittest discover -s tests` passed 93 tests;
     `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
     and `git diff --check` also passed.

285. Reported: "Validation passed: 93 tests now, evidence check, mdBook build,
     and whitespace check are all clean. I'm doing a final status/diff pass and
     adding the validation note to the progress log."

     Action/result: Reviewed the final status and diff summary for the combined
     variable-view/object-field and `0x44` probe pass.

286. Reported: "I'll keep going in the same object-control lane. Since there's
     already a validated uncommitted batch, I'm going to look for one more
     nearby bit action that can be promoted from dispatch-smoke to value-backed
     evidence without dragging us into UI or save/restore behavior."

     Action/result: Reviewed remaining object/control bit documentation and the
     current uncommitted worktree.

287. Reported: "The next likely value-backed target is the horizon-exempt bit
     `0x0008`: docs say `0x3d` sets it and `0x3e` clears it, and the placement
     helper clamps objects against the horizon when the bit is clear. I'm going
     to add two small visible placement probes around that."

     Action/result: Chose horizon-like placement probes targeting `0x3d`,
     `0x3e`, and `0x3f`.

288. Reported: "I'm adding three horizon placement cases: default bit-clear
     clamping proves the horizon global is active, `0x3d` keeps the object
     above the horizon, and `0x3e` restores the clamp after the bit was set. If
     these pass, they give us clean value evidence for `0x3d`, `0x3e`, and
     `0x3f`."

     Action/result: Added `horizon_clamps_object_when_bit_clear`,
     `horizon_exempt_bit_keeps_object_above_horizon`, and
     `horizon_clear_exempt_bit_restores_clamp`.

289. Reported: "The horizon cases are in the probe catalog. I'll pin them in
     the local test list and run the focused harness tests before QEMU."

     Action/result: Updated `tests/test_logic_interpreter_probe.py` to require
     the three new case ids.

290. Reported: "I'll run the focused logic probe unit tests now. If those pass,
     the bytecode is at least structurally sane."

     Action/result: `python3 -B -m unittest tests.test_logic_interpreter_probe`
     passed.

291. Reported: "The focused unit tests pass. I'll run these three horizon cases
     in QEMU now; if the baseline expectation is wrong, the capture comparison
     should give us the actual position."

     Action/result: The first QEMU run was blocked by the sandbox VNC bind
     restriction.

292. Reported: "The usual QEMU VNC bind was blocked by the sandbox. I'll rerun
     the same three-case batch with permission."

     Action/result: Reran the horizon-bit batch with elevated QEMU permission.

293. Reported: "The horizon-bit batch is running from a snapshot. I'll let it
     complete and then either promote the opcodes or adjust the expected
     baseline if QEMU tells us the clamp differs."

     Action/result: Waited for the snapshot-backed QEMU run to complete.

294. Reported: "All three horizon probes matched. That gives us QEMU-backed
     behavior for `0x3f` setting the horizon, `0x3d` exempting the object from
     the clamp, and `0x3e` restoring the clamp. I'm updating the evidence matrix
     now."

     Action/result: QEMU batch
     `build/logic-interpreter-probes/batches/horizon_bits_001.json` matched
     with 3 matches, 0 mismatches, and 0 errors.

295. Reported: "Evidence metadata now promotes `0x3d`, `0x3e`, and `0x3f`.
     I'll regenerate the matrix and then patch the docs with the exact QEMU
     batch and behavior."

     Action/result: Updated `tools/logic_opcode_evidence.py` and regenerated
     `docs/src/logic_opcode_evidence.md`.

296. Reported: "The generated evidence matrix is current. I'm adding the
     horizon-bit observations to the prose docs now: the object pipeline, opcode
     chapter, compatibility command, current status, and the chronological
     clean-room notes."

     Action/result: Began documenting the horizon-bit QEMU observations.

297. Reported: "The placement text has slightly different wording than I
     expected. I've got the exact paragraph now and will insert the horizon QEMU
     note there."

     Action/result: Added the horizon clamp note to
     `docs/src/graphics_object_pipeline.md`.

298. Reported: "I'm adding the same observation to the opcode chapter beside
     the object-bit table, keeping it short and tied to the generated probe
     names."

     Action/result: Added the `0x3d`/`0x3e`/`0x3f` QEMU note to
     `docs/src/logic_bytecode.md`.

299. Reported: "Next I'm adding the exact horizon batch command to the
     compatibility chapter so the result can be replayed later."

     Action/result: Added the horizon-bit batch command to
     `docs/src/compatibility_testing.md`.

300. Reported: "Compatibility docs have the replay command. I'm updating
     current status so the horizon-bit evidence is visible in the 'where are we
     now' page."

     Action/result: Added the horizon-bit finding to `docs/src/current_status.md`.

301. Reported: "I'm adding the dated clean-room note for the horizon probes with
     the exact commands and observed match count."

     Action/result: Added the horizon-bit placement section to
     `docs/src/clean_room_executable_notes.md`.

302. Reported: "Progress log is updated for the horizon pass. I'm running the
     full suite and documentation checks now."

     Action/result: `python3 -B -m unittest discover -s tests` passed 93 tests;
     `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
     and `git diff --check` also passed.

303. Reported: "Everything validates again: 93 tests, evidence check, mdBook,
     and diff whitespace. I'm adding the final validation entry and doing one
     last status review."

     Action/result: Recorded the validation result for the horizon-bit pass.

304. Reported: "I'll keep going on the nearby object/control bits, using the
     same pattern as the horizon probes: make the object state visible in a tiny
     generated fixture, run it through QEMU, then promote only the behavior that
     actually matches."

     Action/result: Selected action `0x38` (`clear_object_bit_0004`) as the
     next target because its visible effect can be tested through priority
     derivation during object placement.

305. Reported: "The overlay tests give us a nice pattern for this one: put a
     control-6 background under a fixed-priority object, clear the fixed-priority
     bit, and see whether the original engine goes back to the Y-derived
     priority."

     Action/result: Planned a fixture that fixes object priority/control to
     `5`, clears bit `0x0004`, places the object at baseline `80`, and expects
     the Y-derived priority `7`.

306. Reported: "The harness now accepts custom picture payloads and expected
     priority values, which makes this fixed-priority probe small instead of
     needing a separate one-off tool."

     Action/result: Extended `tools/logic_interpreter_probe.py` to allow custom
     picture payloads and expected priority values in generated cases.

307. Reported: "The `0x38` probe is in. I'm running the focused unit test first
     so any fixture-building mistake shows up before we spend a QEMU run on it."

     Action/result: Added the
     `clear_fixed_priority_bit_uses_derived_priority` case and the matching
     unit-test expectation.

308. Reported: "The focused test passes. I'm moving to the original-engine run
     now; if QEMU agrees, `0x38` can move out of dispatch-smoke status."

     Action/result: Began the QEMU validation attempt for the one-case
     fixed-priority batch.

309. Reported: "I'll pick up from the fixed-priority probe that was interrupted
     by the sandboxed VNC bind. First I'm going to verify the current file
     state, then I'll rerun that one QEMU case with the needed permission and
     fold the result back into the docs."

     Action/result: Verified the working tree and confirmed `0x38` was still
     listed as dispatch-smoke evidence.

310. Reported: "The working tree matches the handoff summary, and the
     fixed-priority probe is already wired in but still listed only as
     dispatch-smoke evidence. I'm rerunning that single case now through QEMU so
     we can see whether `0x38` deserves promotion."

     Action/result: Reran the fixed-priority QEMU batch with elevated QEMU
     permission after the sandbox rejected the VNC bind.

311. Reported: "That matched cleanly: one QEMU case, zero mismatches. I'm going
     to promote `0x38` from 'dispatch returned' to 'behavior validated', then
     regenerate the evidence table and document exactly what the probe proved."

     Action/result: QEMU report
     `build/logic-interpreter-probes/batches/fixed_priority_bit_001.json`
     matched with 1 match, 0 mismatches, and 0 errors.

312. Reported: "Evidence metadata is patched. I'm regenerating the generated
     opcode evidence chapter next, then I'll make the prose changes around the
     same observation."

     Action/result: Promoted `0x38` in `tools/logic_opcode_evidence.py` and
     regenerated `docs/src/logic_opcode_evidence.md`.

313. Reported: "The generated evidence file is refreshed. I'm reading the exact
     local paragraphs now so the new fixed-priority note lands with the related
     object-bit and compatibility material instead of becoming a stray footnote."

     Action/result: Located the relevant sections in the opcode, object
     pipeline, compatibility, clean-room notes, and current status chapters.

314. Reported: "I found the doc anchors. The new note is intentionally narrow:
     `0x38` clears the fixed-priority bit, and the original engine then derives
     priority from Y, enough to draw over a control-6 synthetic background at
     baseline 80."

     Action/result: Updated `docs/src/logic_bytecode.md` with the
     QEMU-validated visible effect of `0x38`.

315. Reported: "Opcode prose is updated. I'm now tying the same behavior into
     the object pipeline chapter and the compatibility replay chapter."

     Action/result: Added the fixed-priority clear-bit note to
     `docs/src/graphics_object_pipeline.md`.

316. Reported: "The object pipeline now records the visible `0x38` effect next
     to the flag-bit map. I'm adding the exact one-case QEMU command to the
     compatibility chapter so it can be replayed later."

     Action/result: Added the fixed-priority batch command and summary to
     `docs/src/compatibility_testing.md`.

317. Reported: "The replay command is in. I'm adding the chronological
     clean-room note next, including the initial sandbox failure and the
     successful elevated QEMU run because both are part of the evidence trail."

     Action/result: Added the fixed-priority clear-bit QEMU section to
     `docs/src/clean_room_executable_notes.md`.

318. Reported: "The clean-room log now has the fixed-priority probe as a dated
     section. I'm updating the handoff status page so the latest confirmed
     object-bit behavior is visible at a glance."

     Action/result: Added the fixed-priority finding to
     `docs/src/current_status.md`.

319. Reported: "The progress log is caught up through the docs edits. I'm
     running the compatibility/unit checks, the generated evidence check, mdBook
     build, and whitespace check now."

     Action/result: `python3 -B -m unittest discover -s tests` passed 93 tests;
     `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
     and `git diff --check` also passed.

320. Reported: "All checks passed: 93 unit tests, evidence check, mdBook, and
     diff whitespace. I'm recording that validation in the progress log, then
     I'll do a final status/diff review."

     Action/result: Recorded the validation result for the fixed-priority
     clear-bit pass.

321. Reported: "I'll keep advancing the object-state opcode evidence, staying
     close to the current uncommitted work. The next useful pocket is the
     remaining bitfield actions that are still only dispatch-smoke: I'll inspect
     the harness support and pick ones whose effects can be made visible
     without inventing too much scaffolding."

     Action/result: Reviewed the current working tree, logic-interpreter probe
     cases, evidence metadata, and existing docs for the remaining
     dispatch-smoke object opcodes.

322. Reported: "The remaining smoke list splits into two kinds: bits that
     affect drawing/update-list behavior, and fields/modes that can be observed
     through existing getters or movement outcomes. I'm narrowing on the
     low-risk ones first: `0x4c`/`0x4e` and the bit toggles that have a visible
     movement or placement consequence."

     Action/result: Inspected existing logic and movement probe support to find
     observable paths for object-state opcodes.

323. Reported: "There are already getters for some fields, so we can convert
     several smoke cases into ordinary logic probes without touching the
     renderer. I'm going to add focused cases for `0x4c` and `0x4e`, and then
     look for a clean way to make `0x40..0x42` or `0x58..0x59` observable."

     Action/result: Confirmed that `0x4e` can be observed through motion
     behavior, while `0x4c` still lacks a direct visible assertion.

324. Reported: "`0x4e` has a natural visible test: start an autonomous mode,
     immediately clear mode byte `+0x22`, and confirm the object stays put
     during the later update cycles. I’m also reading the acceptance-test docs
     because bits `0x0100`, `0x0800`, and `0x0002` appear to influence movement
     against control pixels."

     Action/result: Read the movement pipeline and control/priority acceptance
     sections to confirm that `0x4e` can be validated with a focused movement
     fixture.

325. Reported: "The movement docs confirm a few of the remaining bits are not
     just hidden state; they sit inside the movement acceptance predicate. For
     this pass I'm going to add one focused `0x4e` movement case first, since it
     is straightforward and should either match or give us a precise
     correction."

     Action/result: Chose a one-case QEMU movement probe for `0x4e`.

326. Reported: "I'm going to make a small fixture addition rather than
     hand-assembling bytes in the movement harness. That keeps the evidence
     trail readable: `clear_object_field_22_and_global_action()` will map
     directly to opcode `0x4e`."

     Action/result: Added `clear_object_field_22_and_global_action()` to
     `tools/qemu_fixture.py`.

327. Reported: "The opcode helper is in place. Next I'm adding the movement
     case that starts random motion on object 0 and immediately applies `0x4e`,
     expecting the later QEMU capture to remain at the starting position."

     Action/result: Added movement case
     `clear_field_22_after_random_motion_stops_motion` and a new
     `random_motion_then_clear_4e` path in `tools/object_movement_probe.py`.

328. Reported: "The movement harness now has a `random_motion_then_clear_4e`
     path. I'm updating the tests so the new case and byte helper are pinned
     before I run QEMU."

     Action/result: Added the new case id to
     `tests/test_object_movement_probe.py`.

329. Reported: "The case list test is updated. I'm adding the direct byte-level
     fixture test for the new `0x4e` helper too, so the generated logic is
     self-checking."

     Action/result: Imported and tested
     `clear_object_field_22_and_global_action()` in
     `tests/test_qemu_fixture.py`.

330. Reported: "The helper test area already has the autonomous-motion byte
     encodings. I'm adding `0x4e` there beside the related motion-control
     opcodes."

     Action/result: Added the expected byte sequence `4e 02` to the autonomous
     motion fixture test.

331. Reported: "The fixture tests now pin the new action byte sequence. I'll
     run the focused unit tests before spending a QEMU run."

     Action/result: `python3 -B -m unittest tests.test_object_movement_probe
     tests.test_qemu_fixture` passed 33 tests, and
     `python3 -B -m unittest tests.test_logic_interpreter_probe` passed 6 tests.

332. Reported: "The focused tests pass. I'm running the single original-engine
     movement case now; if QEMU agrees, `0x4e` can move from dispatch-smoke to
     behavior validated for clearing the active motion mode."

     Action/result: Ran the focused `0x4e` movement probe through QEMU with
     elevated VNC permission.

333. Reported: "QEMU matched: the object stayed at its start after `0x4e`
     cleared the just-started random-motion mode. I'm promoting `0x4e` in the
     evidence matrix and then documenting the exact replay command and
     interpretation."

     Action/result: QEMU report
     `build/object-movement-probes/batches/clear_field_22_001.json` matched
     with 1 match, 0 mismatches, and 0 errors.

334. Reported: "`0x4e` is now marked as a QEMU-backed action in the evidence
     metadata. I'm regenerating the generated evidence chapter."

     Action/result: Promoted `0x4e` in `tools/logic_opcode_evidence.py` and
     regenerated `docs/src/logic_opcode_evidence.md`.

335. Reported: "The generated matrix is refreshed. I'm patching the prose docs
     now: opcode row note, movement pipeline note, compatibility replay command,
     clean-room chronology, and current status."

     Action/result: Began documenting the `0x4e` QEMU result in prose docs.

336. Reported: "The documentation shape is clear. I'm adding the `0x4e` result
     as 'motion-mode clearing is visible', while keeping the global side effect
     sourced to static analysis until we build a direct flag/global probe."

     Action/result: Updated `docs/src/logic_bytecode.md` with the
     QEMU-validated visible `0x4e` effect.

337. Reported: "The opcode row now names the exact QEMU-visible part of
     `0x4e`. I'm adding the same observation to the movement chapter near the
     mode-control description."

     Action/result: Began updating `docs/src/graphics_object_pipeline.md`.

338. Reported: "The random-motion section wording is a little different than
     the snippet I had in mind, so I've got the exact paragraph now and will
     insert the `0x4e` note there."

     Action/result: Added the `0x4e` random-motion stop note to
     `docs/src/graphics_object_pipeline.md`.

339. Reported: "The movement chapter now records the `0x4e` stop behavior. I'm
     adding the replay command to the compatibility chapter beside the existing
     single-case movement batches."

     Action/result: Located the single-case movement-batch section in
     `docs/src/compatibility_testing.md`.

340. Reported: "The compatibility chapter has a good slot right after the
     `0x44` single-case movement batch. I'm adding the `0x4e` replay command
     there."

     Action/result: Added the `0x4e` movement replay command and match summary
     to `docs/src/compatibility_testing.md`.

341. Reported: "The replay command is documented. I'm adding the chronological
     clean-room section for the new helper, harness case, QEMU run, and evidence
     promotion."

     Action/result: Added the `0x4e` clean-room evidence section to
     `docs/src/clean_room_executable_notes.md`.

342. Reported: "The dated evidence note is in. I'm updating the status page
     with the new confirmed motion-control behavior."

     Action/result: Added the `0x4e` finding to `docs/src/current_status.md`.

343. Reported: "The status page is current. I'm catching the progress log up
     for this continuation, including the QEMU result and evidence promotion,
     then I'll run the full validation suite."

     Action/result: Began appending the progress-log entries for this
     continuation.

344. Reported: "The progress log is up to date through the `0x4e` work. I'm
     running the full test suite, evidence check, mdBook build, and whitespace
     check now."

     Action/result: `python3 -B -m unittest discover -s tests` passed 93 tests;
     `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
     and `git diff --check` also passed.

345. Reported: "All four checks passed. I'm adding that validation note to the
     progress log, then I'll do the quick mdBook/whitespace rerun because the
     log itself changed."

     Action/result: Recorded the validation result for the `0x4e` motion-mode
     clearing pass.

346. Reported: "Got it: I'll keep going through the whole sequence and leave
     the commit for you."

     Action/result: Continued the movement/object-bit reverse-engineering pass
     without committing.

347. Reported: "The existing renderer gives us a direct way to make control
     classes visible. I'm going to target `0x58`/`0x59` first because the
     disassembly suggests they gate special control acceptance, then use QEMU
     only to confirm the visible result."

     Action/result: Chose synthetic control-screen movement probes for the
     object-bit handlers.

348. Reported: "I'm going to add explicit fixture helpers for the object-bit
     opcodes instead of hand-assembling bytes in the probe cases."

     Action/result: Added reusable logic-action helpers for `0x58`, `0x59`,
     `0x40`, `0x41`, `0x42`, and rectangle bounds `0x5a`.

349. Reported: "The `0x58`/`0x59` byte helpers are in, and I'm wiring the first
     movement cases around a synthetic control-screen fill."

     Action/result: Added initial object-movement probe cases for control-class
     acceptance.

350. Reported: "The movement cases are wired; I'm adding focused tests so the
     generated fixture bytes and case registry stay pinned down."

     Action/result: Added unit-test coverage for the new movement cases.

351. Reported: "Imports are updated. I'm adding assertions for the exact helper
     encodings before running the focused tests."

     Action/result: Added fixture-helper byte-encoding assertions.

352. Reported: "The tests now cover the helper bytes and the new case ids. I'm
     running those focused tests before touching QEMU."

     Action/result: Ran the focused helper/probe tests successfully.

353. Reported: "Focused tests pass. I'm running the three control-1 acceptance
     cases through QEMU now."

     Action/result: Began a targeted QEMU batch for the first control-class
     movement cases.

354. Reported: "The QEMU mismatch shows the full-screen control-1 fill is not
     the right oracle: the engine accepts the move when our expectation said it
     should block. I'm switching to the rectangle-boundary path the disassembly
     also points at for `0x58`/`0x59`."

     Action/result: Reclassified the initial result as a bad probe design and
     added rectangle-boundary cases.

355. Reported: "I added a helper for `0x5a` rectangle bounds and am replacing
     the weak control-fill assertions with boundary-crossing movement cases."

     Action/result: Added `0x5a` fixture support and rectangle-boundary
     movement fixtures.

356. Reported: "The movement harness now has both the corrected control-1
     observations and the rectangle-boundary cases. I'm pinning those names in
     tests."

     Action/result: Updated movement-probe tests for the revised case set.

357. Reported: "Tests are patched. I'm rerunning the focused unit tests before
     launching the corrected QEMU batch."

     Action/result: Re-ran the focused unit tests successfully.

358. Reported: "Focused tests pass. I'm rerunning QEMU with the corrected
     control-1 observations and the new rectangle-boundary cases."

     Action/result: Ran the revised QEMU batch.

359. Reported: "The corrected control-1 cases all matched, but the rectangle
     case still reached the target. I'm going back to static inspection of the
     boundary branch before trying another fixture tweak."

     Action/result: Paused the failed rectangle hypothesis and inspected the
     movement/boundary code path.

360. Reported: "Interesting: rectangle-boundary also reached the target, which
     means the bit probably gates a specific movement mode or countdown path
     rather than all object motion. I'm dumping the surrounding branch now."

     Action/result: Disassembled the surrounding movement branch.

361. Reported: "The static dump shows the boundary check is behind the
     pre-movement mode dispatcher and only for objects with direction active,
     active/update bits, and clear `0x0002`. I'll adapt the probe to that path."

     Action/result: Identified the gating conditions for the rectangle-boundary
     helper.

362. Reported: "Before moving on, I'm inspecting the actual branch target so the
     next fixture is based on code shape instead of another guess."

     Action/result: Continued static inspection of the rectangle-boundary
     target and object-field tests.

363. Reported: "Aha, the bit `0x0002` branch lives in the pre-movement mode
     dispatcher. I'm changing the rectangle-boundary cases to use the
     countdown-gated autonomous path that reaches that branch."

     Action/result: Reworked rectangle-boundary probes to drive the relevant
     update path.

364. Reported: "For the rectangle cases I'll reuse the existing one-shot
     autonomous mode machinery, because that already gives the object an active
     direction across cycles."

     Action/result: Connected the rectangle-boundary cases to the autonomous
     movement machinery.

365. Reported: "The rectangle cases now use countdown-gated motion and compare
     the final object position. I'm running the focused tests again."

     Action/result: Re-ran focused unit tests after the rectangle-case rewrite.

366. Reported: "Focused tests pass. I'm running the three rectangle-boundary
     cases through QEMU."

     Action/result: Ran the corrected rectangle-boundary QEMU batch.

367. Reported: "That worked: all three rectangle-boundary cases matched. I'm
     recording that as the positive evidence for `0x58`/`0x59`, then moving to
     the control-class bits `0x40`/`0x41`/`0x42`."

     Action/result: Promoted the rectangle-boundary result as QEMU evidence for
     `0x58`/`0x59`.

368. Reported: "The acceptance helper is clear enough now: control class 2
     checks bit `0x0100`, class 3 checks bit `0x0800`, and `0x42` clears both.
     I'm adding QEMU cases that follow that exact branch."

     Action/result: Added class-2/class-3 object-control cases for `0x40`,
     `0x41`, and `0x42`.

369. Reported: "The `0x40`/`0x41`/`0x42` helpers are in. I'm adding case
     coverage for control classes 2 and 3 with priority 14 so the scan actually
     runs."

     Action/result: Added fixture helpers and movement-probe cases for the
     control-class bits.

370. Reported: "The control-class cases are added; I'm expanding the tests to
     pin the helper encodings and case ids."

     Action/result: Updated unit tests for the control-class probes.

371. Reported: "Tests now include the new control-class cases. I'm running the
     focused suite before QEMU."

     Action/result: Ran the focused unit tests.

372. Reported: "Focused tests pass. I'm running the four control-class QEMU
     cases for `0x40`/`0x41`/`0x42`."

     Action/result: Started the control-class QEMU batch.

373. Reported: "The first `0x0100` case did not block, so I'm inspecting the
     acceptance path again instead of forcing the expected output."

     Action/result: Returned to static inspection after the QEMU mismatch.

374. Reported: "Found the missing piece: I used priority 15, and the code skips
     the control scan at that priority. I'm lowering these probes to priority
     14 and expecting rejection to leave the object visible but stationary."

     Action/result: Corrected the control-class probes to avoid the priority-15
     bypass.

375. Reported: "The control-class expectations are now tied to the priority-14
     scan path. I'm rerunning the focused tests before another QEMU pass."

     Action/result: Re-ran the focused unit tests.

376. Reported: "Focused tests pass again. I'm running the combined
     control/rectangle QEMU batch."

     Action/result: Ran a larger QEMU batch for control and rectangle behavior.

377. Reported: "The control-1 rejection now matches, but setting bit `0x0002`
     did not make the object visible or moving there. I'm going to document
     `0x58` via the rectangle-boundary evidence and keep the control-1 branch as
     a separate observed behavior."

     Action/result: Split the `0x58` positive evidence from the class-1
     control-screen observations.

378. Reported: "The `0x58` case also has no visible object under full
     control-1 fill, so I'm renaming those cases to describe what they actually
     prove rather than what I hoped they would prove."

     Action/result: Renamed the control-1 cases to reflect observed hidden/no
     movement behavior.

379. Reported: "Names and expectations now reflect the real class-1
     observation. I'm running a clean batch with the renamed cases and the
     control-class bits."

     Action/result: Prepared the corrected acceptance batch.

380. Reported: "The corrected acceptance batch is running. If it matches, I'll
     promote the class-2/class-3 results as evidence for `0x40`/`0x41`/`0x42`."

     Action/result: Ran the corrected control acceptance batch.

381. Reported: "Great: control-1 and rectangle matched; `0x0100` differs only
     because I expected a plain picture while the rejected object remains
     visible at the start point. I'm updating the oracle to the actual static
     branch result."

     Action/result: Corrected the class-2/class-3 rejection oracle to visible,
     stationary objects.

382. Reported: "For control class 2, `0x0100` blocks movement but leaves the
     object visible at its starting location. I'm mirroring that expectation for
     class 3 and rerunning the four-bit batch."

     Action/result: Updated both class-2 and class-3 blocked expectations.

383. Reported: "The class-2 and class-3 rejection cases now expect a stationary
     visible object. Focused tests pass, and I'm rerunning just those four QEMU
     cases."

     Action/result: Re-ran the focused unit tests and the four-case QEMU batch.

384. Reported: "The `0x40`/`0x41`/`0x42` batch matched exactly. I'm running the
     clean control-1 batch too so that observation has its own compact report."

     Action/result: Captured matching QEMU evidence for the class-2/class-3
     control-bit behavior.

385. Reported: "The control-class-1 clean report matched too. I'm promoting the
     QEMU evidence metadata for `0x40`, `0x41`, `0x42`, `0x58`, and `0x59` now."

     Action/result: Promoted the matching movement-probe batches in
     `tools/logic_opcode_evidence.py`.

386. Reported: "The opcode table is regenerated with those five opcodes marked
     as QEMU-backed. I'm patching the prose docs with the static branch and the
     matching batch names."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md` and began
     prose documentation updates.

387. Reported: "I'm going to document the control-screen acceptance helper,
     rectangle-boundary branch, and corrected probe results together so the
     earlier false starts are preserved as corrections."

     Action/result: Updated the opcode, movement pipeline, compatibility, and
     clean-room notes with the corrected evidence.

388. Reported: "I found exact doc locations. I'm applying the labels first, then
     the prose can refer to stable names rather than raw addresses."

     Action/result: Added symbolic labels for the control-acceptance and
     rectangle-boundary routines.

389. Reported: "Symbolic labels are updated. I'm patching the opcode chapter
     next with the verified summaries and evidence names."

     Action/result: Updated the logic-bytecode chapter rows for `0x40`,
     `0x41`, `0x42`, `0x58`, and `0x59`.

390. Reported: "The opcode rows now include the bit semantics and matching QEMU
     evidence. I'm updating the object pipeline chapter with the actual
     branch-level explanation."

     Action/result: Added the branch-level explanation to
     `docs/src/graphics_object_pipeline.md`.

391. Reported: "The object pipeline now describes priority-15 bypass,
     control-class bits, and rectangle-boundary gating. I'm adding replay
     commands to the compatibility chapter."

     Action/result: Added replay commands for the matched QEMU batches.

392. Reported: "Compatibility docs now have the three replay batches. I'm
     adding the chronological clean-room note with the false starts and
     corrections."

     Action/result: Added the detailed chronology to
     `docs/src/clean_room_executable_notes.md`.

393. Reported: "The clean-room notes now preserve the failed assumptions, the
     corrected static reading, and the matching batches. I'm updating the status
     page, then I'll continue to the remaining object animation/update opcodes."

     Action/result: Updated `docs/src/current_status.md` with the new
     control/priority finding.

394. Reported: "That batch is documented. I'm moving on to `0x46`-`0x4c`,
     starting from the handler offsets and the update loop before making any
     new QEMU cases."

     Action/result: Began static inspection of the object animation/update
     handlers.

395. Reported: "The handler offset mismatch is a useful warning: the table is
     image-relative, while the file has an MZ header. I'm normalizing that
     before trusting any handler disassembly."

     Action/result: Started checking the executable image/file-offset mapping.

396. Reported: "I found a compact visible probe for `0x46`/`0x47`/`0x49`/`0x4c`,
     but before running it I'm checking the code path that decrements frame
     counters and chooses the next cel."

     Action/result: Added draft animation probe cases but deferred QEMU pending
     static confirmation.

397. Reported: "You're right. The QEMU probes are valuable, but I let them
     become the search strategy instead of the cross-check. I'll course-correct:
     first inspect and label the disassembled routines, derive the behavior from
     those code paths, and use QEMU only for small validation probes after the
     static story is clear."

     Action/result: Changed the active methodology back to disassembly-first
     analysis at the user's direction.

398. Reported: "First I'm sorting out the offset convention so every handler
     label lands on the right bytes. Then I'll walk the `0x46`-`0x4c` handlers
     and the per-cycle update callback directly from the executable."

     Action/result: Began verifying MZ header/image-offset conventions before
     continuing handler disassembly.

399. Reported: "The progress log is caught up through the correction. I'm now
     normalizing the executable offsets: the opcode table gives loaded-image
     offsets, while `ndisasm -e` needs the MZ header included in the file
     offset."

     Action/result: Confirmed that handler table addresses are image-relative
     and map to file offsets by adding the MZ header size.

400. Reported: "The offset mapping checks out: handlers from `AGIDATA.OVL` are
     loaded-image addresses, and in the MZ file the bytes are at `image_offset +
     0x200`. I've confirmed that on the `0x5a`, `0x58`, and animation-control
     handlers."

     Action/result: Used focused `ndisasm` slices to verify the image/file
     mapping and handler starts.

401. Reported: "The static path is now much clearer. The per-cycle object
     updater at image `0x0563` scans active objects, decrements byte `+0x20`
     when bit `0x0020` is set, calls the frame-mode helper at `0x48b3` when
     that countdown reaches zero, then reloads `+0x20` from `+0x1f`."

     Action/result: Identified the frame-timer scan and its reload behavior
     from disassembly.

402. Reported: "The frame-mode helper at image `0x48b3` is the missing
     high-level piece: mode 0 loops frames forward, mode 1 advances forward and
     stops/sets a flag at the last frame, mode 2 steps backward and stops/sets
     a flag, and mode 3 loops backward. This gives us a spec-level model for
     `0x46`-`0x4c` before any emulator check."

     Action/result: Derived the frame-mode state machine from static
     disassembly.

403. Reported: "One important detail from the static path: actions `0x49` and
     `0x4b` set bit `0x1000`, and `code.object.advance_frame_by_mode` consumes
     that bit by clearing it and returning before the first frame change. So
     those modes have a one-callback startup delay; the docs need to say that
     explicitly."

     Action/result: Added the bit-`0x1000` startup-delay behavior to the static
     model.

404. Reported: "I've added stable labels for the frame timer scan and
     frame-mode dispatcher, so the rest of the prose can now talk about those
     routines symbolically rather than as loose addresses."

     Action/result: Added `code.object.frame_timer_update` and
     `code.object.advance_frame_by_mode` to `docs/src/symbolic_labels.md`.

405. Reported: "The opcode chapter now corrects `0x4c`: it does not clear
     `+0x20`; it copies the variable value into both `+0x1f` and `+0x20`. That
     was exactly the kind of thing the disassembly-first pass was meant to
     catch."

     Action/result: Corrected the `0x4c` opcode documentation and expanded the
     frame-timer explanation.

406. Reported: "I'm adding the static evidence trail now: table offsets, MZ
     offset convention, focused disassembly slices, and the corrected `0x4c`
     interpretation. Then I'll let the small QEMU probes validate the derived
     model rather than discover it."

     Action/result: Added the static frame-timer/frame-mode analysis section to
     `docs/src/clean_room_executable_notes.md`.

407. Reported: "The clean-room notes now include the course correction and the
     exact static evidence. I'm tightening the fixture tests for the new helper
     bytes before running the targeted animation validations."

     Action/result: Added helper-byte assertions for actions `0x46`, `0x47`,
     `0x49`, and `0x4c`.

408. Reported: "The helper-byte tests now cover `0x46`, `0x47`, `0x49`, and
     `0x4c`. I'm running the focused Python tests before I ask QEMU to validate
     the visible frame behavior."

     Action/result: Ran focused unit tests and the opcode evidence check; both
     passed.

409. Reported: "Focused tests passed. Now I'm running only the three
     frame-timer QEMU cases that follow from the static model: normal mode-1
     advance, `0x46` disabling the timer, and `0x47` restoring it."

     Action/result: Started the `frame_timer_001` QEMU validation batch.

410. Reported: "As expected, the sandbox blocked QEMU's local VNC bind. I'm
     rerunning the same narrow validation outside the sandbox so the emulator
     can open its monitor/display sockets."

     Action/result: Reran the same QEMU command with approved elevated
     permission for the object-movement probe.

411. Reported: "QEMU is running the snapshot batch now. While it works, I'm not
     adding more guesses; the next edits depend on whether those three cases
     match the disassembly-derived expectations."

     Action/result: Waited for the QEMU snapshot batch to complete.

412. Reported: "The frame-timer QEMU batch matched all three cases. That
     validates the static model's visible pieces: `0x4c` seeds the countdown,
     `0x46` suppresses the advance by clearing bit `0x0020`, and `0x47`
     restores it."

     Action/result: Recorded `frame_timer_001` as a matched QEMU batch.

413. Reported: "I'm promoting only the opcodes directly covered by that batch:
     `0x46`, `0x47`, and `0x4c`. `0x49` already had QEMU flag-clearing
     evidence, and this batch will be cited as additional frame-mode evidence in
     prose rather than overloading the metadata."

     Action/result: Updated `tools/logic_opcode_evidence.py` to promote
     `0x46`, `0x47`, and `0x4c` to QEMU behavior evidence.

414. Reported: "The evidence metadata now marks `0x46`, `0x47`, and `0x4c` as
     behavior-validated by `frame_timer_001` instead of dispatch-smoke. I'm
     regenerating the evidence chapter and then I'll document the QEMU result in
     prose."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

415. Reported: "The generated evidence chapter is refreshed. I'm adding the
     replay command and result summary to the compatibility and clean-room docs
     so the validation trail is reproducible."

     Action/result: Began documenting the frame-timer QEMU batch in prose docs.

416. Reported: "I found the compatibility section next to the movement batches.
     I'm placing `frame_timer_001` there and linking it to the exact opcodes it
     validates."

     Action/result: Added the `frame_timer_001` replay command to
     `docs/src/compatibility_testing.md`.

417. Reported: "The opcode and graphics chapters now include the QEMU-backed
     frame-timer result. I'm appending the exact batch command/result to the
     clean-room chronology next."

     Action/result: Added the `frame_timer_001` result to the logic-bytecode,
     graphics-object-pipeline, and clean-room notes.

418. Reported: "The clean-room chronology has the frame-timer validation and the
     sandbox failure/rerun recorded. I'm updating the current status so the
     'next step' no longer says this is unvalidated."

     Action/result: Updated `docs/src/current_status.md` to mark the frame timer
     model as QEMU-validated for visible mode-1 behavior.

419. Reported: "Current status is updated. I'm catching the progress log up
     through the static analysis, the QEMU validation, and the evidence
     promotion before running the full validation suite."

     Action/result: Appended progress-log entries for the frame-timer analysis
     and validation pass.

420. Reported: "The progress log is current. I'm running the full local
     compatibility suite, evidence check, mdBook build, and whitespace check
     now."

     Action/result: `python3 -B -m unittest discover -s tests` passed 97 tests;
     `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
     and `git diff --check` also passed.

421. Reported: "All four checks passed: 97 Python tests, evidence check, mdBook
     build, and `git diff --check`. I'm adding that validation note to the
     progress log, then I'll do the tiny final mdBook/whitespace rerun because
     the log changed."

     Action/result: Recorded the successful validation suite result.

422. Reported: "I'll proceed with the disassembly-first next slice: the object
     frame-mode family around `0x48`, `0x4a`, and `0x4b`. I'll use QEMU only
     after the static path says exactly what should happen."

     Action/result: Started a static-first pass over the frame-mode setup
     actions and the frame advance helper.

423. Reported: "I've refreshed the repo instructions and current notes. Next
     I'm reading the movement fixture code so any validation case mirrors the
     disassembled behavior instead of guessing from screenshots."

     Action/result: Re-read local harness files and AGENTS/project guidance.

424. Reported: "Before touching harness code, I'm re-reading the exact action
     handlers and the frame dispatcher bytes. The goal is to nail down where
     mode 2 actually completes, since that's the one most likely to hide an
     off-by-one misunderstanding."

     Action/result: Cut and disassembled focused executable slices around image
     offsets `0x48b3` and `0x6b82`.

425. Reported: "The static read turned up one correction: mode 2 doesn't just
     decrement once and stop. It keeps stepping backward and completes when it
     reaches frame 0, with an immediate-complete shortcut if it starts at frame
     0."

     Action/result: Corrected the frame-mode model before adding runtime probes.

426. Reported: "For looping modes, I don't want a flaky 'capture at just the
     right cycle' test. I'm going to make the logic fixture stop the timer after
     it observes the expected frame, using the already decoded `0x32` object
     frame read plus `0x46` to clear the timer bit."

     Action/result: Chose deterministic loop-stopping bytecode for mode 0 and
     mode 3 validation cases.

427. Reported: "I'm going to add tiny byte helpers for the exact opcodes the
     fixture needs, then keep the QEMU cases narrow: mode 0 wraps forward, mode
     2 reaches frame 0 and stops, mode 3 wraps backward."

     Action/result: Planned scoped fixture helper additions for actions `0x48`,
     `0x4a`, `0x4b`, and `0x32`.

428. Reported: "The fixture helpers are in. I'm wiring them into the movement
     probe as explicit animation modes rather than making a one-off custom
     fixture, so future frame-mode cases can reuse the same path."

     Action/result: Added helper encoders to `tools/qemu_fixture.py` and threaded
     animation mode selection through `tools/object_movement_probe.py`.

429. Reported: "The movement probe now has three new frame-mode cases. I'm
     adding unit coverage for the helper encodings and registry entries before I
     put the original engine through it."

     Action/result: Added tests for the new helper bytes and movement case IDs.

430. Reported: "The tests now cover the new byte helpers and all three cases.
     I'm running the focused Python tests first; if those pass, I'll run the
     QEMU batch against the original interpreter."

     Action/result: Ran focused unit tests for fixture helpers and movement
     probes.

431. Reported: "Focused tests passed. I'm running the QEMU validation batch now
     with the three frame-mode cases against the original engine."

     Action/result: Started `frame_timer_modes_002` through
     `tools/object_movement_probe.py`.

432. Reported: "QEMU has built the snapshot disk and is stepping through the
     cases now. So far the harness is using the same one-boot snapshot pattern
     as the earlier movement batches."

     Action/result: QEMU validation proceeded through the snapshot fixture
     harness.

433. Reported: "All three frame-mode cases matched QEMU: mode 0 forward wrap,
     mode 2 backward completion at frame 0, and mode 3 backward wrap. I'm
     promoting the opcode evidence and then I'll record the correction and
     replay command in the docs."

     Action/result: Confirmed `frame_timer_modes_002` with 3 matches, 0
     mismatches, and 0 errors.

434. Reported: "The evidence metadata is updated: `0x48` and `0x4a` are now
     behavior-backed instead of dispatch-smoke, and `0x4b` has both its flag
     side effect and visible mode-2 completion covered."

     Action/result: Updated `tools/logic_opcode_evidence.py`.

435. Reported: "The generated chapter is refreshed. I'm finding every place
     where the old 'mode 2 decrements once' wording survived so the docs don't
     carry a stale hypothesis."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md` and searched
     the docs for old frame-mode wording.

436. Reported: "I found the places where the older mode-2 wording lives. I'm
     correcting those and adding the exact QEMU command/result to the
     compatibility and clean-room notes."

     Action/result: Began patching prose docs for the corrected mode-2 behavior
     and `frame_timer_modes_002`.

437. Reported: "I'll pick this back up at the doc-integration step: the code
     and QEMU probe are in place, so I'm going to finish recording the evidence
     trail and then run the book/tests checks."

     Action/result: Resumed after context compaction and continued from the
     documentation integration step.

438. Reported: "The scan shows the new code and two doc chapters already
     changed, with the older mode-2 wording still present in the clean-room
     chronology and the compatibility/current-status pages not yet caught up.
     I'm going to patch those together so the evidence trail stays coherent."

     Action/result: Located remaining docs needing updates.

439. Reported: "I'm making the doc edits now: correcting the static mode-2 note,
     adding the exact new QEMU replay command/result, and updating the status
     page so `0x48`/`0x4a` are no longer described as smoke-only."

     Action/result: Updated compatibility testing, current status, clean-room
     notes, and logic-bytecode prose.

440. Reported: "The main docs are patched. I'm appending the progress-log
     entries next, including the short updates from this resumed turn so the
     historical record remains continuous."

     Action/result: Appended this progress-log block.

441. Reported: "All core checks passed: 97 tests, evidence check, mdBook build,
     and whitespace check. One search command tripped over shell backticks in
     the pattern, so I'm rerunning that search safely and then adding the
     validation note to the log."

     Action/result: `python3 -B -m unittest discover -s tests`,
     `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
     and `git diff --check` passed. The corrected safe search found only the
     historical progress-log mention of the old wording and the corrected
     clean-room sentence.

442. Reported: "The safe search only finds the historical progress note and the
     corrected sentence, so the stale wording is gone from the actual spec
     prose. I'm logging the validation result and then doing the small final
     doc/whitespace rerun because the log changed."

     Action/result: Added the validation result to this progress log.

443. Reported: "I'll continue from the post-frame-mode checkpoint. I'm going to
     re-open the current status and evidence matrix, pick the highest-value
     source-backed opcode cluster that is still weakly documented, and keep the
     progress log moving before substantial new work."

     Action/result: Reviewed current status, git state, recent progress, and
     evidence gaps after commit `a27928a`.

444. Reported: "The evidence scan also caught a stale sentence in
     `logic_bytecode.md` that still calls `0x48`/`0x4a` dispatch-smoke. I'll
     fix that as part of this pass, then dig into the next weak cluster: the
     object bitfield/refresh opcodes `0x3a..0x3c`, which currently have only
     smoke evidence."

     Action/result: Selected the `0x3a..0x3c` object bitfield/refresh action
     cluster for the next source-first investigation.

445. Reported: "The existing docs already know the direct field writes, but the
     high-value gap is semantics: bit `0x0010` partitions active objects between
     update-list roots. I'm reading the surrounding wrappers/list helpers now
     so the opcode names can graduate from 'bit twiddles' toward actual engine
     behavior."

     Action/result: Re-read the `0x3a..0x3c`, `0x6a54`, `0x6a8e`, `0x6aab`,
     `0x0307`, `0x0358`, `0x045e`, and `0x0488` source paths.

446. Reported: "The source read shows `0x3c` is broader than its old label
     implies: it computes the object address from the operand, but then runs
     the all-list flush, rebuild/draw, and dirty-rectangle refresh path. I'm
     checking whether that label is baked into tests before renaming it to
     something more accurate."

     Action/result: Found no test dependency on `refresh_object_helper`.

447. Reported: "There are no tests pinning the old `0x3c` label, so I can
     safely tighten the terminology. I'm going to treat `0x3a`/`0x3b` as
     list-membership partition toggles and `0x3c` as an all-object-list
     refresh/repaint action, then regenerate the evidence table from the local
     opcode names."

     Action/result: Planned the label change to `refresh_object_lists`.

448. Reported: "I'm going to edit the label and prose now, not the runtime
     behavior. The evidence level will stay as QEMU dispatch-smoke until we
     build a visible fixture, but the specification text can still record the
     static source semantics precisely."

     Action/result: Updated `tools/disassemble_logic.py`, `logic_bytecode.md`,
     and `graphics_object_pipeline.md` with `refresh_object_lists` semantics.

449. Reported: "Before editing, I checked the evidence generator: it derives
     summaries from the opcode labels, so a better `0x3c` label will
     automatically make the table less misleading. I'm applying that targeted
     terminology update plus the stale `0x48`/`0x4a` sentence fix."

     Action/result: Removed the stale `0x48`/`0x4a` smoke-only wording from
     `logic_bytecode.md`.

450. Reported: "The label/prose update is in. I'm regenerating the opcode
     evidence chapter now so the generated matrix uses `refresh_object_lists`
     consistently."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

451. Reported: "The regenerated matrix has the new label. One search command
     again interpreted backticks, but the useful result confirms the generated
     evidence row changed; I'll rerun searches with safe quoting when checking
     cleanup. Next I'm checking the symbolic label map so the update-list
     helpers have stable names for later interpreter-version comparisons."

     Action/result: Reviewed `docs/src/symbolic_labels.md` and confirmed the
     update-list wrapper helpers were not yet named there.

452. Reported: "The symbolic map does not yet name the update-list wrappers or
     the `0x0010` toggle helpers, even though those are exactly the kind of
     cross-version anchors you asked us to preserve. I'm adding stable labels
     for them and then I'll see whether there's a clean visible QEMU validation
     for the root-order effect."

     Action/result: Added symbolic labels for update-list builders, flush,
     rebuild, refresh, and bit-`0x0010` membership helpers.

453. Reported: "The symbolic labels are in. I'm reading the fixture builders
     now to find the least invasive way to validate the predicted draw-order
     effect from bit `0x0010`, preferably with two overlapping objects and a
     stable pixel/sample comparison."

     Action/result: Reviewed logic and object overlay probe fixture builders.

454. Reported: "A clean QEMU validation looks feasible: activate two
     overlapping objects, clear bit `0x0010` on one, then use the source-derived
     root order to predict which object draws on top. I'm checking the fixture
     helper defaults and view frames so the expected image is stable and
     distinguishable."

     Action/result: Confirmed view 11/group 0 frames 0 and 1 have overlapping
     nontransparent pixels with different colors.

455. Reported: "The probe framework can already compare multiple sprites by
     compositing extras first and the primary sprite last, which fits the
     predicted root-order test. I hit a small local attribute-name mismatch
     while checking frame transparency; I'm inspecting the rendered frame
     structure and then I'll add the case."

     Action/result: Confirmed frame transparency is `frame.control & 0x0f`.

456. Reported: "The frame renderer uses `control & 0x0f` as transparency; view
     11 frames 0 and 1 differ enough to reveal order. I'm adding one
     source-derived behavior case to the logic probe: object 11 is moved to the
     `0x1703` partition with `0x3a`, object 10 stays in `0x16ff`, and the
     expected composite has object 10 on top."

     Action/result: Prepared a visible root-order probe design.

457. Reported: "I can cover both toggles with two cases rather than overloading
     one: one where `0x3a` moves frame-1 behind a still-`0x16ff` frame-0 object,
     and one where `0x3b` moves frame-1 back over a `0x1703` frame-0 object.
     I'll include `0x3c` after the partitioning in both cases to validate that
     the global refresh preserves the predicted order."

     Action/result: Added two root-partition cases to `tools/logic_interpreter_probe.py`.

458. Reported: "The two behavior cases are in the probe list. I'm adding unit
     coverage for their registration before trying them under QEMU, so a typo
     in the case IDs or expected sprites gets caught locally first."

     Action/result: Added the new case IDs to
     `tests/test_logic_interpreter_probe.py`.

459. Reported: "I'm making the test registration check explicit for the two new
     root-partition cases. That keeps the probe catalogue honest as it grows."

     Action/result: Updated the base-case registration test.

460. Reported: "The catalogue test is updated. I'm running the focused
     logic-probe tests now, then I'll run the two new cases through QEMU if
     local composition passes."

     Action/result: `python3 -B -m unittest tests.test_logic_interpreter_probe
     tests.test_logic_doc_coverage` passed.

461. Reported: "Focused tests passed. I'm running the two new root-partition
     cases against the original engine now; this one needs QEMU/VNC access, so
     I'll request the same kind of permission as prior batches."

     Action/result: Ran `object_root_partition_001`; the first case mismatched.

462. Reported: "The first QEMU case mismatched, which is useful evidence rather
     than a dead end: my source-derived draw-order prediction is missing another
     ordering detail. I'm opening the report and capture samples now, then I'll
     go back to the list builder/sort code before adjusting the model."

     Action/result: Inspected mismatch samples and re-read the list builder and
     node traversal.

463. Reported: "The mismatch is not just 'opposite top sprite'; there are white
     pixels where the local expectation has object colors, so another
     object-state detail is in play. I'm comparing the capture against a few
     source-plausible composites before changing the probe, then I'll inspect
     the activation/list code around that detail."

     Action/result: Determined that activation-time placement/collision was
     affecting the first fixture design.

464. Reported: "The capture points to placement, not root order: activating two
     objects at exactly the same position lets the placement helper nudge one to
     avoid collision. I'm revising the fixtures to activate the second object
     elsewhere, then use the already decoded dirty position setter `0x93` to
     overlap it after activation, so the test isolates the `0x0010` partition
     effect."

     Action/result: Updated the fixture to activate object 11 at X 90, then move
     it to X 50 with `0x93`.

465. Reported: "The fixtures now avoid activation-time collision adjustment. I'm
     rerunning focused tests and then the same QEMU batch."

     Action/result: Focused tests passed, but `object_root_partition_002`
     mismatched.

466. Reported: "The revised case still mismatched, so the remaining issue is
     likely not placement. I'm going back to the render/list order carefully:
     the list builder inserts nodes at the head, and the processor walks from
     the tail, so I need to model that actual traversal instead of assuming root
     order alone determines topmost pixels."

     Action/result: Rechecked the source traversal and mismatch report.

467. Reported: "The second mismatch is identical, so `0x93` did not isolate the
     object from the placement/update behavior the way I hoped. I'm going to
     inspect the `0x93` handler before touching the fixture again; if it calls
     placement or refreshes through the same collision path, I'll avoid it for
     this validation."

     Action/result: Static read confirmed `0x93` calls placement helper
     `0x593a`.

468. Reported: "Confirmed: `0x93` calls placement helper `0x593a`, so it was
     still letting collision adjustment move the object. I'm switching the
     isolation step to `0x25`, which static docs say writes current and saved
     position fields directly without placement, then the explicit `0x3c`
     refresh will make the final overlap visible."

     Action/result: Replaced `0x93` with `0x25` in the root-partition fixtures.

469. Reported: "The fixture now uses `0x25` for direct overlap, with `0x3c`
     doing the refresh. I'm rerunning the focused unit test and QEMU batch
     again."

     Action/result: Focused tests passed, but `object_root_partition_003`
     mismatched.

470. Reported: "Still mismatching. At this point the fixture is no longer a
     quick validation, so I'm going to stop iterating by trial and inspect the
     actual captured shape and relevant draw code before deciding whether this
     is worth continuing now. The source trail matters more than forcing a
     probe."

     Action/result: The capture showed object 11 drawn at both X 50 and X 90.

471. Reported: "The capture reveals object 11 is still at its activation X
     (`90`), so the direct `0x25` write after activation is not enough to move
     the already-listed persistent object in this path. I'm disassembling the
     generated fixture and the `0x25`/activation code paths to understand why
     before deciding whether to keep or drop this QEMU case."

     Action/result: Confirmed the generated fixture contained `0x25 0b 32 50`
     and that `0x25` rewrites both current and saved coordinates.

472. Reported: "Now the behavior is clear: `0x25` updates the saved position
     too, so the restore pass no longer knows to erase the old object at X 90.
     The result is a deliberate ghost plus the new overlap. I'm checking whether
     modeling that ghost makes the QEMU capture match; if it does, this becomes
     a useful combined observation about `0x25` plus the list refresh."

     Action/result: Local comparison matched exactly when the stale X-90 drawing
     was included in the expected image.

473. Reported: "That matches exactly when I include the stale X-90 image left by
     `0x25`. I'm updating the expected composites to include that ghost
     explicitly, then I'll rerun both cases; the root-order part still cleanly
     validates at the overlapping X-50 pixels."

     Action/result: Updated the two root-partition cases to include the
     activation-position ghost sprite in expected output.

474. Reported: "The expected composites now include the observed stale image
     from the direct position rewrite. I'm rerunning focused tests and then the
     two-case QEMU batch."

     Action/result: Focused tests passed.

475. Reported: "Focused tests pass. I'm running the corrected QEMU batch; this
     should now distinguish the documented ghost from any actual root-order
     mismatch."

     Action/result: QEMU batch `object_root_partition_004` matched with 2
     matches, 0 mismatches, and 0 errors.

476. Reported: "Great, both root-partition cases matched the original engine.
     I'm promoting `0x3a`, `0x3b`, and `0x3c` from smoke to behavior evidence,
     then I'll document the source correction, the failed fixture attempts, and
     the final passing QEMU batch."

     Action/result: Promoted `0x3a`, `0x3b`, and `0x3c` in
     `tools/logic_opcode_evidence.py`.

477. Reported: "The evidence generator now treats the root-partition opcodes as
     behavior-validated. I'm regenerating the matrix and then I'll patch the
     prose docs around the exact command and result."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

478. Reported: "The matrix now shows `0x3a`, `0x3b`, and `0x3c` as
     QEMU-validated. I'm updating the prose docs next, including the important
     caveat that the fixture initially failed until we accounted for `0x25`
     preserving the stale saved rectangle."

     Action/result: Began updating compatibility, status, graphics, and opcode
     prose docs.

479. Reported: "I found two stale spots: the older view-load/field23
     compatibility paragraph still says `0x48`/`0x4a` are smoke-only, and
     current status still mentions generic bitfield smoke coverage. I'm
     patching those along with the new `object_root_partition_004` replay
     command."

     Action/result: Patched compatibility, current status, graphics pipeline,
     and logic bytecode prose.

480. Reported: "The compatibility, status, graphics, and opcode chapters are
     patched. I'm adding the chronological clean-room record now, including the
     mismatch sequence and why the final fixture needed to model the `0x25`
     stale image."

     Action/result: Added the object update-list partition section to
     `docs/src/clean_room_executable_notes.md`.

481. Reported: "The clean-room chronology now has the source commands, the
     three failed fixture variants, and the final passing QEMU evidence. I'm
     adding a compact current-status bullet so future resumption sees `0x0010`
     as confirmed behavior, not just next-work detail."

     Action/result: Added the root-partition summary to current status.

482. Reported: "Current status is updated. I'm appending the work log now so the
     intermediate false starts and the eventual source correction are preserved
     for the historical record."

     Action/result: Appended this progress-log block.

483. Reported: "The progress log is caught up. I'm running the full validation
     suite now: all Python tests, evidence check, mdBook build, whitespace
     check, and a stale-wording search."

     Action/result: `python3 -B -m unittest discover -s tests` passed 97 tests;
     `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
     and `git diff --check` passed. The stale-wording search found only
     historical command/log references plus an older chronology sentence.

484. Reported: "The validation suite passed. The stale search only found
     historical command/log references plus one old 'Current smoke rows'
     sentence from an earlier chronology section; I'm changing that sentence to
     make clear it was the state at the time, not the current evidence status."

     Action/result: Reworded the older clean-room chronology sentence to
     describe the smoke rows as historical.

485. Reported: "That historical sentence is corrected. I'm recording the
     validation result in the progress log, then doing a final mdBook and
     whitespace rerun because documentation changed after the checks."

     Action/result: Added this final validation note.

486. Reported: "I'll keep going from the uncommitted root-partition work. I'm
     going to scan the current evidence gaps and pick the next source-backed
     opcode cluster that can be upgraded without muddying the model."

     Action/result: Reviewed git status and the opcode evidence matrix after the
     root-partition pass.

487. Reported: "The evidence matrix has no remaining dispatch-smoke rows; the
     next good target is a source-backed-but-not-behavior-validated object bit.
     I'm going after `0x2d`/`0x2e` and bit `0x2000`, because it appears in the
     per-cycle frame/group selection path and should be possible to validate
     visibly."

     Action/result: Selected actions `0x2d` and `0x2e` for the next
     source-first investigation.

488. Reported: "I'll pick up from the `0x2000` object flag mismatch and start
     by reading the generated batch report/captures, then I'll go back to the
     disassembly before changing the model. The useful thing here is to
     separate 'our expected sprite is wrong' from 'the flag means something
     subtler than the static read suggested.'"

     Action/result: Inspected `object_bit_2000_001.json`; the mismatch was
     confined to the object pixels.

489. Reported: "The mismatch is tight: all differing pixels are exactly where
     the object is drawn, not a random screen-state problem. The captured colors
     look like a different cel/group than expected, so I'm going to inspect the
     fixture and renderer expectations before touching the opcode description."

     Action/result: Listed the fixture and inspected the capture metadata.

490. Reported: "The probe itself is doing what I intended: object 10 is
     initialized to view 11 group 0, direction 6, tick divider 1, then either
     clears or sets bit `0x2000`. Next I'm checking whether the engine picked a
     different group/frame or whether the group-selection pass is gated by
     another field I missed."

     Action/result: Re-read the probe setup code and the `0x0563` static
     frame-update slice.

491. Reported: "The static slice confirms the bit gate exactly at `0x0593`: if
     `0x2000` is set, it skips the direction-to-group lookup; if clear, it can
     call the group selector. I'm correcting a local import path for the
     comparison helper now so I can identify which cel the original engine
     actually drew."

     Action/result: Corrected the local helper invocation and tested alternate
     expected group/frame combinations.

492. Reported: "The miniature render dump is useful: group 0 cels are `20x5`,
     group 1 cels are `13x7`. The capture's mismatch bbox height spans seven
     rows, so the original engine likely selected group 1 but mirrored or used
     the opposite group-1 frame from my expectation."

     Action/result: Rendered compact view-11 cel dumps; this hypothesis was
     corrected by the subsequent exact-frame comparison.

493. Reported: "That explains the failed expectation: the engine drew group 0
     frame 0 exactly. The disassembly says the automatic lookup only runs when
     object byte `+0x0b` is `2`, `3`, or `>=4`; view 11 appears to leave that
     byte below the threshold, so it was a bad fixture for this flag."

     Action/result: Exact comparison showed the capture matched view 11 group 0
     frame 0. Later source review kept the result but corrected the reason to a
     fixture-lifecycle problem rather than the view's group count.

494. Reported: "The right fixture should use a view whose loaded metadata
     crosses that threshold. I'm going to generalize the helper from 'view 11
     only' to 'selected view,' use a four-group SQ2 view, and rerun the
     bit-`0x2000` pair against QEMU."

     Action/result: Inspected view resources and selected view 4 as a compact
     four-group fixture target.

495. Reported: "One important wrinkle just popped out: these probe logics loop,
     so a setup sequence inside the main body can keep reselecting group 0
     every cycle after the engine's update pass. I'm checking the loop shape
     now; the fix may be to guard initialization so the automatic selector has a
     later cycle where our script no longer resets the group."

     Action/result: Re-read `base_code` and `self_loop`.

496. Reported: "I need to revise my earlier loop thought: the fixture's
     `self_loop` is an infinite bytecode jump at the end, so the script body is
     not repeating, but it may also prevent the engine's later per-cycle object
     update from running. I'm going to make these two cases use an `end`-style
     logic so the engine can advance into the frame-timer pass, then freeze via
     the already-drawn persistent object state."

     Action/result: Compared the logic probe shape to the movement harness,
     which uses a normal `0x00` end action for per-cycle movement tests.

497. Reported: "The movement harness already has a pattern for this: initialize
     once, let per-cycle actions run until a flag, and end the logic instead of
     pinning the interpreter in a bytecode jump. I'm borrowing that structure
     conceptually for the logic opcode probe rather than inventing a separate
     tester."

     Action/result: Located the guarded one-time setup pattern in
     `tools/qemu_fixture.py`.

498. Reported: "Before editing, I'm going to keep the change small: add a
     reusable 'end after body' option to the logic probe case builder, add an
     arbitrary-view setup helper, and switch only the two `0x2000` cases to
     that mode. Then QEMU can tell us whether the static interpretation
     survives runtime."

     Action/result: Added `end_code`, arbitrary-view object setup, and an
     expected-view parameter to `tools/logic_interpreter_probe.py`.

499. Reported: "One more refinement before running it: an `end` case that
     redraws the picture every cycle would erase useful evidence, so I'm
     putting the load/show/setup sequence behind a one-time flag guard. That
     gives the engine normal cycles afterward without the script resetting the
     object or repainting the background each time."

     Action/result: Added guarded `one_time_code` support.

500. Reported: "I've added the guarded one-time execution path; now I'm wiring
     the two cases to it and using a loaded view whose group metadata should
     make the direction table path observable."

     Action/result: Reworked the `0x2000` cases to use view 4, direction 6, and
     one-time initialization flags.

501. Reported: "The probe now initializes view 4 exactly once, sets direction 6
     and the bit state once, then returns from logic each cycle. I'm running
     focused unit tests first so the generated fixture shape is sane before
     spending another QEMU cycle."

     Action/result: Focused unit tests passed.

502. Reported: "The focused tests passed. I accidentally launched a one-case
     QEMU run with zero waits while checking the command path; I'm letting it
     finish/close cleanly before starting the real two-case validation."

     Action/result: The zero-wait run produced a throwaway mismatch and exited.

503. Reported: "That zero-wait run produced the expected throwaway mismatch, so
     I'm ignoring it. Now I'm running the real two-case snapshot batch with the
     normal wait times."

     Action/result: QEMU batch `object_bit_2000_002` matched both cases.

504. Reported: "Good, the corrected `0x2000` pair matches the original engine:
     clear bit allows direction-based group selection, set bit suppresses it.
     I'm promoting those opcodes in the evidence table now and then I'll update
     the spec notes with the false start and the static addresses that explain
     it."

     Action/result: Added `0x2d` and `0x2e` to `QEMU_ACTIONS`.

505. Reported: "The docs already had the raw `0x2d`/`0x2e` bit writes, but not
     the higher-level meaning. I'm adding the two direction-to-group data tables
     and the frame-update helper labels so future version comparisons can key
     off names instead of SQ2 addresses."

     Action/result: Added symbolic labels for the two direction-to-group tables.

506. Reported: "The evidence generator now points `0x2d` and `0x2e` at the
     passing `object_bit_2000_002` batch. Next I'm adding the stable labels for
     the two small direction lookup tables in `AGIDATA.OVL`."

     Action/result: Continued symbol-map update.

507. Reported: "The symbol map is updated. I'm expanding the bytecode and
     graphics chapters so the higher-level behavior is visible where an
     implementer would look first, not only buried in the chronological notes."

     Action/result: Patched `logic_bytecode.md`.

508. Reported: "The opcode chapter now states both the raw field mutation and
     the runtime meaning. I'm doing the same in the object pipeline chapter,
     including the two actual table byte sequences so a clean implementation
     can reproduce the mapping."

     Action/result: Patched `graphics_object_pipeline.md`.

509. Reported: "The object pipeline chapter now has the implementation-level
     mapping and the QEMU replay name. I'm adding the chronological clean-room
     record next, including the first mismatching fixture and why it was wrong."

     Action/result: Added the clean-room chronology section for bit `0x2000`.

510. Reported: "The chronology now captures both the successful source model
     and the fixture correction. I'm updating the handoff/status and
     compatibility chapters so this is visible in the project dashboard too."

     Action/result: Updated current status.

511. Reported: "The compatibility patch missed because that chapter's wording
     has drifted a bit. I'm locating the nearby section and applying the same
     replay block against the current text."

     Action/result: Located the root-partition compatibility section.

512. Reported: "I found a stale compatibility sentence still calling the old
     bitfield batch 'dispatch smoke.' Since the evidence matrix no longer has
     smoke rows, I'm cleaning that wording while inserting the new `0x2000`
     replay command."

     Action/result: Patched compatibility testing with the new replay command
     and updated the stale smoke wording.

513. Reported: "The progress log is caught up through the docs edits. I'm
     regenerating the opcode evidence chapter now, then I'll run the full local
     validation set."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

514. Reported: "The evidence chapter regenerated cleanly. I noticed two long
     helper lines in the probe while reviewing the diff, so I'm wrapping those
     before the full validation run."

     Action/result: Wrapped helper code in `tools/logic_interpreter_probe.py`.

515. Reported: "The helper is tidied up. I'm running the full validation pass
     now: Python unit tests, regenerated evidence check, mdBook build, and
     whitespace checks."

     Action/result: `python3 -B -m unittest discover -s tests` passed 97
     tests; `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build
     docs`, and `git diff --check` passed.

516. Reported: "Validation passed: all 97 tests, evidence check, mdBook build,
     and `git diff --check`. I'm doing a quick stale-wording/status scan and
     then I'll record the validation result in the progress log."

     Action/result: Stale scan found only historical progress/chronology
     mentions and the still-supported generator/category prose, not current
     opcode evidence rows.

517. Reported: "I'll run this as a full pass rather than a proposal: first
     finish the automatic direction/group semantics, then trace the per-cycle
     scheduler, then use that to promote more source-backed opcode rows, and
     finally document the timing model plus the next less-visual families. I'm
     starting by reading the current evidence matrix and the relevant
     object/frame-update code so the next probes stay source-led."

     Action/result: Created the five-step task plan and read current status,
     opcode evidence, and probe code.

518. Reported: "The current `0x2000` validation covers the four-plus-groups
     table only. I'm going to add three focused cases now: one for the
     2/3-group table, one sentinel value that must leave the group alone, and
     one `+0x01 != 1` gate case that should block selection even when the table
     says to change."

     Action/result: Inspected view 5 as a visibly distinct three-group fixture
     and dumped the two direction tables from `SQ2/AGIDATA.OVL`.

519. Reported: "View 5 is a good 3-group target: group 0 and group 1 are
     visibly distinct mirror-like cels, so the 2/3-group table can be observed
     cleanly. I'm adding those cases to the existing logic probe list now."

     Action/result: Added three initial bit-`0x2000` follow-up cases.

520. Reported: "The three new fixtures are in: 3-group direction 6, 3-group
     sentinel direction 5, and the `+0x01` gate. I'm updating the case registry
     test, then I'll run the focused unit tests before QEMU."

     Action/result: Updated the logic probe registry test.

521. Reported: "The focused registry tests passed. I again started a zero-wait
     harness sanity run while checking fixture build behavior; I'll let that
     close and then run the real snapshot batch with normal timing."

     Action/result: The zero-wait dry run mismatched, as expected.

522. Reported: "The zero-wait dry run mismatched as expected because it captured
     before the engine had useful draw time. Now I'm running the actual
     three-case QEMU batch."

     Action/result: Started QEMU batch `object_bit_2000_003`.

523. Reported: "The QEMU batch is still running; it's in the snapshot execution
     phase. I'll wait for the result before deciding whether these fixtures are
     good enough or need the same kind of source-led correction as the previous
     one."

     Action/result: Batch `object_bit_2000_003` matched the table and sentinel
     cases but mismatched the initial `+0x01` gate expectation.

524. Reported: "Two of the three new cases matched: the 2/3-group table and
     sentinel value are confirmed. The `+0x01 != 1` case changed anyway, so I'm
     inspecting the capture and then tracing who decrements or rewrites `+0x01`;
     that may turn the 'gate' into a cadence condition rather than a permanent
     block."

     Action/result: Exact comparison showed the mismatching case eventually
     selected group 1.

525. Reported: "The capture shows the `+0x01 = 2` object eventually selected
     group 1. The source explains why: `code.object.frame_timer_update` checks
     `+0x01` before `code.motion.update_objects` decrements the countdown, so a
     one-shot `2` skips once, then becomes `1` for the next cycle. I'm changing
     this into two clearer probes: one for that countdown behavior, and one
     that rewrites `+0x01 = 2` every logic cycle to prove the gate itself."

     Action/result: Added a one-time setup plus per-cycle action fixture helper.

526. Reported: "I've added a reusable one-time-setup plus per-cycle-action
     fixture shape, which is exactly what we need for timing-sensitive engine
     behavior. Now I'm revising the `+0x01` case and adding the explicit 'keep
     forcing 2' gate probe."

     Action/result: Replaced the initial gate case with a countdown case and
     added a forced-gate case.

527. Reported: "The old gate case is now a countdown case, and the new gate
     case keeps setting `+0x01` to 2 before each engine update. I'm updating the
     tests and rerunning the targeted batch."

     Action/result: Updated the registry test for the renamed and new cases.

528. Reported: "I'm running the focused tests and then a four-case QEMU batch:
     the two table cases, the countdown case, and the forced-gate case. If the
     forced case holds, that completes the `0x2000` semantic set cleanly."

     Action/result: Focused tests passed and QEMU batch `object_bit_2000_004`
     started.

529. Reported: "The unit tests passed; QEMU is still running the four fixtures.
     This is the interesting one because it tests timing, not just final object
     state."

     Action/result: QEMU batch `object_bit_2000_004` matched all four cases.

530. Reported: "The four-case batch matched: both direction tables, sentinel
     behavior, countdown-to-1, and the forced `+0x01 != 1` gate are now
     validated. I'm moving to the scheduler trace next: who calls the
     frame/group update, motion update, logic execution, and redraw steps, and
     in what order."

     Action/result: Completed the automatic direction/group semantics plan
     item.

531. Reported: "The near-call scan found the key top-level calls:
     `code.object.frame_timer_update` is called at image `0x024b`, and a
     pre-pass at `0x0644` is called at `0x0198`. I'm disassembling that
     top-level range now to pin the cycle ordering rather than relying on old
     notes."

     Action/result: Disassembled image `0x0100..0x0270` and scanned direct calls
     in that range.

532. Reported: "The top-level loop is now visible at `0x0150`: it calls
     input/system helpers, a pre-motion pass, then repeatedly calls logic 0
     through `code.logic.call_logic`, and only after that reaches
     `code.object.frame_timer_update` at `0x024b`. I'm labeling that cycle and
     identifying the currently unknown calls well enough to document the
     ordering without over-naming uncertain helpers."

     Action/result: Read existing labels and call references around the
     top-level loop.

533. Reported: "A useful correction fell out of the scheduler trace: the
     pre-motion mode dispatcher is at image `0x0644`, not `0x0844`, and its
     rectangle helper is `0x06d9`, not `0x08d9`. The earlier docs had those
     labels shifted; I'm going to correct the symbolic map and prose before
     building on them."

     Action/result: Located all current references to the shifted labels.

534. Reported: "The scheduler correction also gives us an easy next promotion
     target: some resource/display opcodes are still source-backed but can be
     observed visually. After I patch the scheduler labels, I'll add narrow
     probes for view discard and picture overlay/priority display where
     possible."

     Action/result: Added `code.engine.main_cycle` and corrected motion helper
     labels in `docs/src/symbolic_labels.md`.

535. Reported: "The symbolic map now has the top-level
     `code.engine.main_cycle` label and corrected motion helper addresses. I'm
     fixing the object pipeline prose so the scheduler order matches the actual
     top-level call sites."

     Action/result: Updated per-cycle movement prose in the graphics/object
     pipeline chapter.

536. Reported: "The movement chapter now distinguishes the pre-logic
     motion-mode pass from the post-logic frame/group/movement pass. I'm
     scanning the evidence matrix for source-backed rows that can be promoted
     with small, deterministic visual probes."

     Action/result: Listed source-backed opcode rows from the generated matrix.

537. Reported: "The remaining source-backed rows are mostly UI/save/sound, but
     a few are still small and visual. The rectangle-boundary opcodes
     `0x5a`/`0x5b` already have movement semantics in the harness, so I'm
     checking whether they can be promoted from existing QEMU batches before
     writing new fixtures."

     Action/result: Confirmed existing movement cases exercise `0x5a`; `0x5b`
     still needed a focused case.

538. Reported: "The existing rectangle movement batch already exercises `0x5a`
     because it configures the crossing bounds. `0x5b` is not isolated yet, so
     I'm adding one movement case that sets the bounds and then clears them; the
     object should reach the target instead of stopping at the rectangle edge."

     Action/result: Located fixture helper and movement harness extension
     points.

539. Reported: "I need a tiny helper for action `0x5b` in the fixture layer,
     then I can add the movement case without special-casing the generated
     logic. This stays inside the existing object movement harness."

     Action/result: Added `clear_rect_bounds_action()`.

540. Reported: "I'm making the `0x5b` support as a simple bytecode helper, plus
     one boolean on the movement case. Then the case can share the same
     comparison and snapshot machinery as the existing rectangle-boundary
     probes."

     Action/result: Added `move_rect_boundary_clear_bounds_reaches_target`.

541. Reported: "The new `0x5b` movement case is in. I'm running focused tests,
     then I'll run the one-case QEMU batch for the clear-bounds behavior."

     Action/result: Focused fixture/movement tests passed; first QEMU attempt
     failed under the sandbox VNC bind restriction.

542. Reported: "The focused tests passed. The QEMU run hit the sandbox's VNC
     bind restriction, so I'm rerunning the exact same one-case batch with the
     required elevated permission."

     Action/result: Elevated QEMU batch `rect_bounds_clear_001` matched with 1
     match, 0 mismatches, and 0 errors.

543. Reported: "The `0x5b` QEMU probe matched: after `0x5a` sets rectangle
     bounds, `0x5b` clears them and the object reaches the target. I'm promoting
     `0x5a` and `0x5b` in the evidence matrix now: `0x5a` is covered by the
     existing rectangle-boundary batch, and `0x5b` by this new clear-bounds
     batch."

     Action/result: Promoted `0x5a` and `0x5b` in
     `tools/logic_opcode_evidence.py`.

544. Reported: "The evidence generator is updated. I'm adding the fixture helper
     test coverage so the new `0x5b` bytecode helper is protected like the
     other generated opcodes."

     Action/result: Located the relevant fixture and movement registry tests.

545. Reported: "I found the helper tests and the movement case registry test.
     I'm adding one assertion for the `0x5b` bytecode and one assertion that the
     new movement case is registered."

     Action/result: Updated `tests/test_qemu_fixture.py` and
     `tests/test_object_movement_probe.py`.

546. Reported: "The tests now cover the `0x5b` helper and case registration.
     I'm regenerating the opcode evidence matrix and running the focused
     fixture/movement tests once more."

     Action/result: Regenerated the evidence matrix; focused tests passed 48
     tests.

547. Reported: "The focused tests passed and the evidence matrix regenerated.
     I'm doing the documentation pass now: first the opcode/object chapters,
     then compatibility/current-status, then the chronological clean-room log
     with the exact commands and corrections."

     Action/result: Began documentation updates.

548. Reported: "A small checkpoint: steps 1 through 3 are now done in code and
     QEMU evidence. I'm currently on step 4, turning the scheduler/order
     findings into spec prose that a future implementation can follow."

     Action/result: Marked the first three plan items complete.

549. Reported: "The bytecode chapter text has slightly different surrounding
     lines, so I'm applying this as smaller patches: one new cycle-timing
     section, one replacement for the `0x2000` QEMU paragraph, and one table-row
     update for `0x5a`/`0x5b`."

     Action/result: Updated `docs/src/logic_bytecode.md`.

550. Reported: "The bytecode chapter now has the top-level timing model, the
     expanded `0x2000` behavior, and QEMU-backed `0x5a`/`0x5b` rows. I'm
     aligning the object pipeline chapter's `0x2000` paragraph with the new
     four-case batch."

     Action/result: Updated `docs/src/graphics_object_pipeline.md`.

551. Reported: "Next I'm adding replay commands to the compatibility chapter:
     the expanded `0x2000` batch and the `0x5b` clear-bounds movement batch.
     That keeps the QEMU evidence directly reproducible."

     Action/result: Updated `docs/src/compatibility_testing.md`.

552. Reported: "The compatibility chapter has the new replay commands. I'm
     updating the handoff/status page next so future sessions see these as
     completed findings, not just raw test reports."

     Action/result: Updated `docs/src/current_status.md`.

553. Reported: "The status page now reflects the completed scheduler and
     rectangle-boundary work. I'm adding the clean-room chronology next,
     including the correction that the `0x067a` mode dispatcher is reached from
     `0x0644`, not `0x0563`."

     Action/result: Corrected an older clean-room chronology paragraph.

554. Reported: "The historical correction is in place. I'm appending a new
     chronology section with the exact commands and results from this pass."

     Action/result: Added the expanded direction/scheduler/rectangle chronology
     section.

555. Reported: "The clean-room notes now have the new command trail and the
     corrected scheduler addresses. I'm adding the remaining-family survey so
     the 'what next' trail is explicit for UI/save/sound/text instead of
     vague."

     Action/result: Added the remaining source-backed family survey to current
     status.

556. Reported: "That completes the survey step in the handoff doc. I'm marking
     the last two plan items complete, then I'll update the progress log and
     run the full validation suite."

     Action/result: Marked all five requested steps complete in the task plan.

557. Reported: "The progress log is caught up. I'm running the full validation
     suite now: all Python tests, evidence check, mdBook build, and whitespace
     checking."

     Action/result: `python3 -B -m unittest discover -s tests` passed 97 tests;
     `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
     and `git diff --check` passed.

558. Reported: "The full validation suite passed: 97 tests, evidence check,
     mdBook build, and whitespace check. I'm doing a final stale-address scan
     for the corrected scheduler labels, then I'll record the validation
     result."

     Action/result: The stale-address scan found only deliberate historical
     correction entries and the intermediate `object_bit_2000_003` batch
     recorded in the chronology.

559. Reported: "I'm picking up from the resource-lifecycle probe mismatch. The
     useful clue from the disassembly is that `overlay_picture_var` appears to
     require the picture to already be loaded/cached, so I'm going to correct
     the synthetic bytecode around that rather than treating the black-box
     result as mysterious."

     Action/result: Re-read current probe and test changes around resource
     lifecycle fixtures.

560. Reported: "The failure now lines up with the code path: `0x1c` is not a
     load-and-overlay operation, it's an overlay of an already resident picture.
     I'm adjusting the probe to exercise that exact precondition, and I'll add
     a discard-picture lifecycle case while we're in this neighborhood."

     Action/result: Planned the `0x18` + `0x1c` fixture correction and a
     `0x1b` discard/reload case.

561. Reported: "I'm also checking the shared QEMU snapshot harness before
     adding input/text probes. If we can represent post-launch keystrokes as
     data on each fixture, the same runner can handle text prompts and
     menu/input cases without a separate one-off script."

     Action/result: Inspected `tools/qemu_snapshot.py` and related docs.

562. Reported: "There's already a clean place to put post-launch input:
     `SnapshotFixtureCase` can grow optional key text, and existing callers
     stay unchanged. That gives us the scaffolding for prompt/menu/save probes
     even before every UI path has a pixel-accurate comparator."

     Action/result: Chose a backward-compatible `post_launch_keys` /
     `post_launch_wait` fixture extension.

563. Reported: "The text/window work is going to be staged honestly: I can add
     the reusable capture/input plumbing now, but pixel-accurate text rendering
     is a separate model from the 160x168 graphics renderer. I'll document it
     as capture/scaffolding plus source assessment, not pretend a coarse
     screenshot proves the UI semantics."

     Action/result: Scoped UI work to deterministic input plumbing plus
     narrow visible-output probes.

564. Reported: "I've got the concrete additions now: resource lifecycle cases,
     text/input cases using delayed monitor keystrokes, and menu/sound
     dispatch-smoke cases. Next I'm making the fixture schema carry that
     post-launch input through to QEMU."

     Action/result: Began code edits in `tools/qemu_snapshot.py` and
     `tools/logic_interpreter_probe.py`.

565. Reported: "The QEMU runner can now type fixture-specific input after
     launch. I'm threading those fields into the logic probe cases and adding
     the new bytecode fixtures around the source-backed families."

     Action/result: Added post-launch input fields and logic-probe fixture
     cases.

566. Reported: "I'm keeping these probes visible-output driven where possible:
     they don't just run an opcode and hope; they make the original interpreter
     proceed to a known view draw only if the opcode path returns and the
     expected state was produced."

     Action/result: Added message, numeric input, menu, sound, and resource
     lifecycle cases that end in known draw comparisons.

567. Reported: "One little plumbing issue surfaced: `_draw_if_case` did not yet
     accept input fields, so I'm widening that helper too. This keeps the input
     cases as normal logic-probe fixtures instead of a special path."

     Action/result: Extended `_draw_if_case` to pass input settings through.

568. Reported: "The probe definitions are in place. I'm adding regression tests
     for the new case IDs and for the new snapshot input fields so this doesn't
     silently break later when we add more UI fixtures."

     Action/result: Updated logic-probe and QEMU snapshot unit tests.

569. Reported: "The static tests are next. If these pass, I'll run the new QEMU
     batches in smaller groups so a bad UI timing assumption doesn't obscure
     the resource-lifecycle results."

     Action/result: Ran focused unit tests and the opcode evidence check; they
     passed.

570. Reported: "The focused Python tests passed. I'm running the resource
     lifecycle batch first: logic-var load, picture overlay with the
     now-correct load precondition, discard/reload picture, and view
     discard/reload variants."

     Action/result: Started QEMU batch `resource_lifecycle_002`.

571. Reported: "The lifecycle batch is in QEMU now. It has built the snapshot
     disk and is stepping through the five fixtures from the saved DOS prompt."

     Action/result: Awaited the QEMU lifecycle batch.

572. Reported: "The corrected overlay precondition still mismatched, so I'm not
     going to paper over it. I'm reading the report and then I'll go back to the
     picture-handler code path to see whether the expected composition model is
     wrong, or whether another action such as show/finalize is needed after
     overlay."

     Action/result: Read `resource_lifecycle_002`; only overlay pixels were
     missing.

573. Reported: "The mismatch is narrower now: the view sprite is being drawn,
     but the overlaid picture pixels are not visible in the display capture.
     That fits the handler split: `0x1c` mutates the logical picture buffers,
     while `0x1a` is the full-screen display/finalization path, so I'm adding
     that explicit show step after the overlay."

     Action/result: Added `0x1a` after `0x1c` in overlay fixtures.

574. Reported: "I've corrected the overlay fixture to include the display
     finalization path. I'm rerunning the local tests for the probe shape, then
     the lifecycle batch again."

     Action/result: Focused unit tests passed.

575. Reported: "The local shape tests are still green. I'm rerunning the
     five-case lifecycle QEMU batch with the explicit `0x1a` finalization after
     overlay."

     Action/result: Started QEMU batch `resource_lifecycle_003`.

576. Reported: "QEMU is running the lifecycle batch again now. If this passes,
     I'll move on to the text/input/menu/sound group as separate batches
     because those touch blocking UI helpers."

     Action/result: Awaited lifecycle batch completion.

577. Reported: "The lifecycle batch passed all five cases. That validates the
     exact overlay nuance: `0x1c` composes into the logical picture state, and
     `0x1a` is needed to push that composition to the visible screen. Next I'm
     running the text/message and typed-input fixtures."

     Action/result: `resource_lifecycle_003` matched 5/5 and text/input QEMU
     batch was started.

578. Reported: "The text/input batch is running. These cases use the new
     post-launch keystroke path: Enter to dismiss message windows, then typed
     `look` and `42` for prompt handlers."

     Action/result: Awaited `text_input_001`.

579. Reported: "The three message-window cases passed; the typed string prompt
     did not reach the expected final draw. I'm inspecting the capture/report
     before deciding whether the typed input timing is wrong or the assumed
     parsed word id/condition is wrong."

     Action/result: Inspected `text_input_001`; `0x65`, `0x66`, and `0x97`
     matched, while the `0x73` string prompt did not.

580. Reported: "The mismatch region is exactly where the final sprite should
     be, so the script probably stayed on the prompt path or the condition was
     false. I'm going to inspect the screenshot visually and then decide
     whether to relax this to a prompt-capture case or fix the input
     timing/terminator."

     Action/result: Converted and viewed the prompt capture.

581. Reported: "The screenshot is helpful: the prompt displayed and `look` was
     typed, but it did not accept/advance before capture. I'm going to give
     prompt-style input an extra Enter; message windows accepted a single Enter,
     but this editor helper appears to need a less brittle dismissal sequence
     under QEMU monitor timing."

     Action/result: Retried the `0x73` prompt fixture with an extra Enter.

582. Reported: "The extra Enter still didn't advance the string prompt. I'm
     checking whether the second Enter is being ignored while the typed buffer
     remains active, which would mean this handler needs a different completion
     key or a more direct event injection strategy."

     Action/result: Confirmed the string prompt remained active; then ran the
     numeric prompt case separately.

583. Reported: "The numeric prompt case passed with the new key-input path, so
     the input scaffolding is real. The string-editor prompt still stays active
     after typed text; I'm removing that from the default compatibility suite
     for now and documenting it as an observed harness limitation/open item
     rather than leaving a known-failing default case."

     Action/result: Removed the failing `0x73` case from default probes and
     kept `0x76` as QEMU-validated input evidence.

584. Reported: "The default suite now contains only input cases we can make
     deterministic. I'm rerunning the text/input batch with the three message
     paths plus numeric prompt."

     Action/result: Started QEMU batch `text_input_002`.

585. Reported: "The trimmed text/input batch is running now. This should give
     us stable QEMU evidence for message display variants and one typed-input
     path without overclaiming the string editor behavior."

     Action/result: Awaited `text_input_002`.

586. Reported: "The text/input batch passed all four cases. I'm moving to the
     menu/list and sound dispatch-smoke probes next; these are deliberately
     narrower, proving handler execution and return-to-bytecode rather than full
     UI/audio semantics."

     Action/result: `text_input_002` matched 4/4 and menu/sound smoke batch was
     started.

587. Reported: "QEMU is running the menu/sound smoke batch now. If any of these
     fail, I'll treat it as a missing precondition and go back to the handler
     disassembly rather than weakening the result."

     Action/result: Awaited `menu_sound_001`.

588. Reported: "The menu/sound smoke batch passed. I'm updating the generated
     evidence matrix inputs next so the docs distinguish true pixel/value
     validation from dispatch-smoke coverage for menu and sound handlers."

     Action/result: Updated `tools/logic_opcode_evidence.py` and regenerated
     `docs/src/logic_opcode_evidence.md`.

589. Reported: "The evidence generator now knows about the new resource,
     text/input, menu, and sound probes. I'm regenerating the mdBook evidence
     chapter from that single source."

     Action/result: Regenerated the opcode evidence chapter.

590. Reported: "I'm turning the QEMU results into spec prose now: one pass in
     the bytecode reference for behavior, one in compatibility testing for
     replay commands, one in current status for handoff, and one chronological
     log with the failed string-prompt attempt included."

     Action/result: Updated bytecode, compatibility, current-status, and
     clean-room chronology docs.

591. Reported: "A small but important wording point for the spec: I'm
     documenting the overlay as a two-stage operation, because the failed
     capture proved that logical composition alone is not the same as a visible
     full-screen refresh."

     Action/result: Added the two-stage `0x1c` plus `0x1a` overlay note.

592. Reported: "The handoff docs now reflect which families moved from
     'source-backed' into QEMU-backed or smoke-tested. I'm appending the
     chronological evidence trail with the exact commands and the failed `0x73`
     attempt, because that negative result matters for future work."

     Action/result: Appended the clean-room chronology section for this pass.

593. Reported: "The chronological notes are updated. I'm catching up the
     progress log now with the user-facing updates from this run so the
     conversational history remains traceable."

     Action/result: Updated this progress log.

594. Reported: "I'll take the whole chain: start source-first at `0x0da9`, then
     adjust the input harness only where the disassembly says it should help,
     then use QEMU as validation rather than exploration."

     Action/result: Began the string editor and event-path pass.

595. Reported: "I'm gathering the local disassembly context first: existing
     notes, the `0x73` handler, the editor helper, and the event wait path."

     Action/result: Searched docs/tools for prior `0x73` and `0x0da9`
     evidence.

596. Reported: "The existing docs already have the high-level `0x73` shape, but
     not the completion key details. I'm reading raw disassembly around the
     helper now."

     Action/result: Confirmed the existing source-backed handler summary and
     prepared focused executable slices.

597. Reported: "The full disassembly file appears to be stale around this
     helper, so I'm making fresh focused slices from the decrypted executable
     with explicit image origins."

     Action/result: Generated and disassembled slices around image `0x0c20` and
     `0x4420`.

598. Reported: "The editor helper is now clear enough to read structurally:
     clamp length, copy current string to a local buffer, wait for events, then
     dispatch through a key table. I'm dumping the table bytes so we don't infer
     key names from control flow alone."

     Action/result: Dumped key dispatch bytes at file offset `0x1060`.

599. Reported: "The dispatch table is the important bit: Enter maps to the
     accept/copy-back path, Escape returns without copy, Backspace edits, and
     Ctrl-C/Ctrl-X clear. So QEMU should be able to complete `0x73`; the harness
     probably isn't delivering the right event shape or timing."

     Action/result: Identified `0x0d` as the accept key for
     `code.input.edit_string`.

600. Reported: "The disassembly says Enter really is a completion key, so I'm
     going to separate two questions in the probes: did the prompt return at
     all, and did it copy the edited string into the slot?"

     Action/result: Planned separate return-only and string-slot equality
     fixtures for `0x73`.

601. Reported: "I'm adding a per-fixture key delay now; text prompts are one of
     the few places where monitor keystroke timing can masquerade as interpreter
     behavior."

     Action/result: Added `post_launch_key_delay` to the QEMU fixture model.

602. Reported: "The input delay plumbing is in. Next I'm making the `0x73`
     cases explicit and keeping them out of the broad default batch until they
     pass on their own."

     Action/result: Added string prompt fixtures and kept them targeted.

603. Reported: "I'm also adding low-risk system/diagnostic probes while I'm in
     this file, because several remaining opcodes should only need an Enter
     acknowledgement plus a validation draw."

     Action/result: Added formatted text, input-line, text-window, and
     diagnostics fixture cases.

604. Reported: "The case registry tests need to learn about the new targeted
     cases, then I'll do a focused Python test pass before waking QEMU."

     Action/result: Updated unit tests for the new case registry and QEMU
     fixture defaults.

605. Reported: "The local code is ready for a sanity pass. I'm running focused
     Python tests for the logic probe definitions and snapshot runner."

     Action/result: Ran focused unit tests for `tools/logic_interpreter_probe.py`
     and `tools/qemu_snapshot.py`.

606. Reported: "Focused tests passed. I'm running two `0x73` probes first:
     return-after-Enter and stores-typed-word."

     Action/result: Started QEMU batch `prompt_string_001`.

607. Reported: "QEMU is running string prompt checks. This is the narrowest
     place to debug the key path before adding the larger text UI batch."

     Action/result: Awaited the first string-prompt QEMU run.

608. Reported: "The return-only `0x73` case still did not advance to the draw
     after typed `look` plus Enter, despite the source saying Enter should
     accept. I'm going to inspect the capture and then try sending the return
     key as a named key event rather than as a typed newline character."

     Action/result: Treated the mismatch as a harness/event-shape question.

609. Reported: "The capture is the same editor-active state, so the next probe
     change is to extend the key sender rather than change interpreter
     expectations."

     Action/result: Added support for named post-launch QEMU key events.

610. Reported: "I'm also separating type text from press named key in the
     fixture model, with a short wait between them. That gives the DOS keyboard
     path a cleaner event sequence."

     Action/result: Added `post_launch_after_text_wait` and
     `post_launch_key_names`.

611. Reported: "The `0x73` fixtures now type `look`, pause, then send a named
     `ret` key. I'm rerunning the focused unit tests before trying QEMU again."

     Action/result: Updated the string prompt fixtures for named Enter.

612. Reported: "The local schema tests passed with the named-key fields. I'm
     rerunning `0x73` now."

     Action/result: Started QEMU batch `prompt_string_002`.

613. Reported: "QEMU revised string prompt batch is running. If this still
     stalls, the next source check will be the event normalizer around `0x45d7`
     and `0x4634`."

     Action/result: Awaited `prompt_string_002`.

614. Reported: "Aha, the capture is more subtle: the typed prompt text is still
     on-screen, but the validation draw may be happening underneath it. I'm
     adding a full picture refresh after the prompt before comparing pixels."

     Action/result: Diagnosed the mismatch as text overlay persistence rather
     than editor non-completion.

615. Reported: "I've inserted the refresh after `0x73`. That should make the
     fixture prove string semantics instead of comparing against leftover text
     pixels."

     Action/result: Added `0x1a` before the validation draw in the `0x73`
     probes.

616. Reported: "The refreshed string-prompt batch is running now."

     Action/result: Started QEMU batch `prompt_string_003`.

617. Reported: "Nice, `0x73` is now validated: both the return-only case and
     the typed-word storage case matched. The earlier failure was a display
     cleanup artifact, not an editor completion failure."

     Action/result: `prompt_string_003` matched 2/2.

618. Reported: "I'm batching UI cases by risk: formatted messages and simple
     input-line/window state first, then diagnostics/system actions after those
     pass."

     Action/result: Started the text UI QEMU probe sequence.

619. Reported: "QEMU is running the text UI group now."

     Action/result: Started QEMU batch `text_ui_001`.

620. Reported: "The first formatted-message case mismatched, so I'm reading the
     capture pattern before changing anything. Given the `0x73` lesson, text
     overlay is the prime suspect."

     Action/result: Investigated the first formatted-message mismatch.

621. Reported: "The mismatch is exactly at the formatted message text location.
     I'm applying the same validation split: acknowledge the message, refresh
     the picture, then draw the object for comparison."

     Action/result: Added refresh-before-validation to formatted message cases.

622. Reported: "The formatted-message probes now separate text display from
     graphics validation. I'm rerunning the six-case text UI batch."

     Action/result: Started QEMU batch `text_ui_002`.

623. Reported: "QEMU revised text UI batch is running."

     Action/result: Awaited `text_ui_002`.

624. Reported: "Four of six text UI cases passed. The rectangle-clear probe is
     different: it deliberately changes top text rows, so I need to make the
     fixture prove it returns before drawing, not preserve the cleared rows."

     Action/result: Identified the text-rectangle clear comparison problem.

625. Reported: "The rectangle-clear case returned but intentionally cleared
     screen rows that the expected image assumed were normal. I'm inserting a
     refresh before the validation draw there too."

     Action/result: Added refresh-before-validation to text rectangle clear.

626. Reported: "The text rectangle probe is corrected. I'm running just the two
     remaining text-window cases first."

     Action/result: Started QEMU batch `text_clear_001`.

627. Reported: "The remaining text-clear/window cases passed. Now I'm rerunning
     the full six-case text UI batch to keep one clean evidence artifact."

     Action/result: `text_clear_001` matched 2/2 and `text_ui_003` was started.

628. Reported: "QEMU clean combined text UI batch is running."

     Action/result: Awaited `text_ui_003`.

629. Reported: "The combined text UI batch passed. I'm moving on to the
     diagnostic/system message group."

     Action/result: `text_ui_003` matched 6/6 and diagnostics were started.

630. Reported: "Diagnostics batch running now: pause, heap/status, interpreter
     version, plus low-risk global action dispatch smoke."

     Action/result: Started QEMU batch `diagnostics_system_001`.

631. Reported: "All QEMU batches passed. I'm updating the generated opcode
     evidence matrix so the docs reflect the new validated and dispatch-smoke
     rows."

     Action/result: `diagnostics_system_001` matched 4/4 and evidence metadata
     was updated.

632. Reported: "Generated evidence chapter refreshed. I'm doing the narrative
     docs now: bytecode semantics, compatibility replay commands, symbolic
     labels, current status, and the clean-room/progress logs."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md` and began
     the documentation update pass.

633. Reported: "I'll proceed source-first: re-read the opcode handlers and
     shared text/input helpers from the executable, then only use QEMU where it
     gives us a clean confirmation test."

     Action/result: Started the text/status configuration pass.

634. Reported: "The prior docs already have decent summaries for this family,
     but I'm going back to the bytes instead of trusting the summaries."

     Action/result: Created focused executable slices around image offsets
     `0x3400`, `0x7600`, `0x4c00`, and `0x0d60`.

635. Reported: "The slices are ready. I'm reading them now with explicit
     origins so the addresses line up with the existing symbolic map and later
     cross-version comparisons."

     Action/result: Disassembled the focused slices with `ndisasm`.

636. Reported: "The static read confirms the family is more about global
     text/display state than hidden game semantics: `0x70/0x71` are just
     status-line flag plus redraw/clear; `0x6f` stores row/config globals;
     `0x79` appends a 4-byte key mapping slot."

     Action/result: Decided to add narrow QEMU dispatch-smoke tests while
     keeping richer key-map semantics source-backed.

637. Reported: "Before editing, I'm checking the probe helper shapes so the new
     cases fit the existing harness instead of inventing a second style."

     Action/result: Reviewed `tools/logic_interpreter_probe.py`, evidence
     metadata, and case registry tests.

638. Reported: "I'm adding small, explicit smoke fixtures now: one for
     text-attribute mode setup/teardown, one for status line show/hide, one for
     prompt/config globals, one for key-map table insertion, and one for
     screen-shake return."

     Action/result: Added five targeted QEMU cases.

639. Reported: "The new cases are in the registry. I'm updating the case-list
     tests and the evidence generator so the metadata matches the harness."

     Action/result: Updated `tests/test_logic_interpreter_probe.py` and
     `tools/logic_opcode_evidence.py`.

640. Reported: "The metadata is patched. I'm running the focused Python tests
     before QEMU so any mistake in fixture definitions fails cheaply."

     Action/result: Focused Python tests passed.

641. Reported: "Focused tests passed. I'm going to run just the five new QEMU
     cases as a tight batch; that keeps this as confirmation evidence, not
     fishing around."

     Action/result: Started QEMU batch `text_status_001`.

642. Reported: "QEMU is running the five-case status/input batch from a
     snapshot now. If one of these fails, I'll treat it as a missing
     precondition and go back to the static path rather than broadening the
     test blindly."

     Action/result: Awaited `text_status_001`.

643. Reported: "The first two new cases matched: text-attribute setup/teardown
     and one-count screen shake both returned cleanly. The prompt/config case
     mismatched, so I'm inspecting that artifact before changing anything."

     Action/result: Inspected `text_status_001` JSON and the mismatching PPM.

644. Reported: "The mismatch is informative rather than mysterious: using
     `0x6f` with row/config byte `1` changes display-position state enough that
     the validation sprite appears at a different vertical offset than the local
     renderer expects."

     Action/result: Changed the `0x6f` smoke fixture to use first operand `0`.

645. Reported: "The fixture correction is deliberately narrow. I'm rerunning
     the Python sanity check, then I'll rerun the same five-case QEMU batch so
     we have one clean artifact."

     Action/result: Focused Python tests passed after the fixture correction.

646. Reported: "Focused tests are still green. The revised QEMU batch is
     starting now with the neutral `0x6f` row/config operand."

     Action/result: Started QEMU batch `text_status_002`.

647. Reported: "QEMU is running the corrected batch. The earlier failed run
     will go into the clean-room notes as a useful constraint on `0x6f`:
     operand 0 affects display offset state, so a later behavior probe can
     target that directly."

     Action/result: Awaited `text_status_002`.

648. Reported: "Four of five have matched in the corrected batch; only the
     key-event mapping smoke case is still running/awaiting capture."

     Action/result: Awaited the final key-event mapping case.

649. Reported: "The corrected batch matched 5/5. I'm regenerating the opcode
     evidence chapter next, then I'll write down the static source findings
     plus the QEMU confirmation and the one failed `0x6f` offset probe."

     Action/result: `text_status_002` matched 5/5 and
     `docs/src/logic_opcode_evidence.md` was regenerated.

650. Reported: "I'm updating the symbolic map first. These labels give us
     stable names for the status redraw, prompt marker, text attribute,
     input-line configuration, and key-map insertion helpers instead of tying
     future notes to raw offsets."

     Action/result: Updated `docs/src/symbolic_labels.md`.

651. Reported: "Next I'm folding the new source/QEMU distinction into the
     bytecode chapter: the handlers are now smoke-tested, but some deeper
     behavior, especially key-map event conversion and `0x6f` display offset
     effects, remains a separate target."

     Action/result: Updated `docs/src/logic_bytecode.md`.

652. Reported: "I'm adding the replay command to the compatibility chapter now,
     including the failed `text_status_001` lesson so future probes don't
     accidentally rediscover that offset issue."

     Action/result: Updated `docs/src/compatibility_testing.md`.

653. Reported: "I'm updating the handoff/status page so 'remaining
     source-backed text opcodes' doesn't keep pointing at work that now has at
     least dispatch-smoke coverage."

     Action/result: Updated `docs/src/current_status.md`.

654. Reported: "The main spec pages are updated. I'm appending the clean-room
     evidence trail with the exact disassembly slices, the QEMU mismatch, the
     corrected run, and what each result proves."

     Action/result: Updated `docs/src/clean_room_executable_notes.md`.

655. Reported: "I'll turn the `0x6f` observation into a real behavior case
     now: script draws the object at baseline `80`, but the expected capture
     baseline is `88` when `0x6f` operand 0 is `1`."

     Action/result: Began behavior-level probes for `0x6f`, `0x79`, and `0x74`.

656. Reported: "I’m going to quantify the offset rather than eyeballing it.
     The quick check is: compare the operand-1 capture against the same expected
     sprite at several baselines and see which one minimizes mismatches."

     Action/result: Compared the recreated operand-1 QEMU capture against
     expected baselines `70..90`; baseline `88` matched exactly.

657. Reported: "That resolved the ambiguity: the operand-1 capture matches
     exactly if the expected sprite baseline is moved from `80` to `88`."

     Action/result: Confirmed `0x6f` first operand `1` produces an
     eight-logical-row visible offset in the observed mode.

658. Reported: "Source check found the right path for `0x79`: condition `0x0d`
     does not use the mapping table, but the top-level input helper does."

     Action/result: Re-read condition `0x0d` and helper `0x4566`; identified
     condition `0x0c` as the observation point for mapped type-3 events.

659. Reported: "I’m adding two behavior-level cases now: one where
     `0x6f(1,...)` must move the visible baseline from 80 to 88, and one where
     `0x79` maps `x` to status byte 7 and a later cycle draws only after
     condition `0x0c 7` sees it."

     Action/result: Added `input_line_config_operand1_offsets_display_by_8` and
     `mapped_key_sets_status_byte`.

660. Reported: "The behavior cases are added. I’m updating tests and evidence
     metadata so `0x6f` and `0x79` can move from smoke evidence to behavior
     evidence if the batch matches."

     Action/result: Updated the case registry test and opcode evidence
     generator.

661. Reported: "The focused test caught a harness-shape mistake:
     `_draw_if_case` doesn’t take `init_once_flag`. I’m switching that
     mapped-key case to the lower-level `_custom_case`."

     Action/result: Reworked the mapped-key case as one-time setup plus
     per-cycle conditional draw.

662. Reported: "Focused tests are green. I’m running the two behavior
     confirmations now: `0x6f` offset and `0x79` mapped key to status byte."

     Action/result: Started QEMU batch `input_key_behaviour_001`.

663. Reported: "The `0x6f` behavior case matched: operand 1 produced the
     expected 8-row visible offset. The mapped-key case is still running."

     Action/result: First case of `input_key_behaviour_001` matched.

664. Reported: "Both behavior probes matched. I’m moving to `0x74` now: first
     I’ll inspect the table bytes around `0x0c8f`, then decide whether a
     fixture-local `AGIDATA.OVL` patch is a safe way to create a non-empty table
     entry for dynamic confirmation."

     Action/result: `input_key_behaviour_001` matched 2/2 and the `0x74` table
     area was inspected.

665. Reported: "`0x74` has a convenient zero-filled pocket right after the
     pointer table. I’m going to make the dynamic test explicit and synthetic:
     patch only the generated fixture’s `AGIDATA.OVL` so table entry 0 points
     to a local `look\\0` string."

     Action/result: Added fixture-local `AGIDATA.OVL` patch support and a
     synthetic `0x74` behavior case.

666. Reported: "The synthetic `AGIDATA` patch support is in. I need one small
     follow-up: thread that optional patch list through `_draw_if_case`, since
     the new `0x74` case uses that convenience wrapper."

     Action/result: Passed `agidata_patches` through `_draw_if_case`.

667. Reported: "The probe and evidence metadata are ready. I’m running focused
     tests again before the QEMU batch that combines `0x6f`, `0x79`, and
     synthetic `0x74`."

     Action/result: Focused Python tests passed.

668. Reported: "Focused tests passed. I’m running the three targeted QEMU cases
     now; the `0x74` one uses only a fixture-local `AGIDATA.OVL` patch, not a
     change to the SQ2 source files."

     Action/result: Started QEMU batch `input_key_string_behaviour_001`.

669. Reported: "QEMU is running the three-case behavior batch. This should give
     us one clean artifact covering the offset, mapped-key event path, and the
     patched pointer-table copy."

     Action/result: Awaited `input_key_string_behaviour_001`.

670. Reported: "The three targeted confirmations all matched. I’ll regenerate
     the evidence matrix and update the docs for these before moving on to the
     inventory/menu source pass, so the text/input family has a clean stopping
     point."

     Action/result: `input_key_string_behaviour_001` matched 3/3 and the
     opcode evidence chapter was regenerated.

671. Reported: "The evidence chapter is regenerated. I’m updating the narrative
     docs with the new distinction: `0x6f`, `0x79`, `0x74`, and condition
     `0x0c` now have behavior evidence, with `0x74` clearly marked as a
     synthetic table-entry fixture."

     Action/result: Updated bytecode, compatibility, and current-status docs.

672. Reported: "The user-facing docs now reflect the behavior batch. I’m
     appending the clean-room evidence trail with the exact commands, including
     the synthetic `AGIDATA` patch rationale for `0x74`."

     Action/result: Updated `docs/src/clean_room_executable_notes.md`.

673. Reported: "I’m picking up from the source-first inventory/menu pass. The
     text/key/string-table probes are in place; now I’m going to turn the
     inventory disassembly notes into a couple of focused behavior checks so the
     docs don’t just say 'looks like,' they have original-engine evidence behind
     them."

     Action/result: Re-read local harness, QEMU input helpers, test registry,
     symbolic labels, and the existing `0x7c` documentation.

674. Reported: "The local state already includes the static inventory
     description, and the symbolic label file has the core inventory table
     label. I’m checking the harness details before editing so the new probes
     use the same QEMU input path as the earlier text/editor cases."

     Action/result: Confirmed `post_launch_keys` and named-key support in
     `tools/qemu_snapshot.py`.

675. Reported: "The source-backed model for `0x7c` is tight enough to probe:
     flag 13 selects interactive mode, carried entries are the ones with marker
     `0xff`, Enter stores the selected index in variable `0x22`, and Escape
     stores `0xff`. I’m adding exactly those cases now."

     Action/result: Added initial inventory selection probes, later corrected
     the variable interpretation from bytecode variable `0x22` to absolute byte
     `DS:0x0022`.

676. Reported: "The three new inventory fixtures are deliberately small: one
     Enter path, one Escape path, and one noninteractive acknowledgement path.
     They all draw only after `0x7c` returns, so a match tells us the handler
     both accepted the key and resumed the bytecode stream."

     Action/result: Added probe registry tests for the three inventory cases.

677. Reported: "The harness-level tests are happy. Next I’m running the
     original engine batch; this is the useful part for compatibility because it
     checks the disassembly-derived interpretation against DOS/QEMU captures."

     Action/result: Focused Python tests passed; started QEMU batch
     `inventory_selection_001`.

678. Reported: "QEMU is in the snapshot batch now: it has prebuilt the three
     DOS fixture directories and is replaying them from one DOS prompt
     snapshot. If the Escape monitor key name is wrong, this run should make
     that obvious from the first mismatch."

     Action/result: Initial QEMU batch mismatched on the Enter case.

679. Reported: "The first inventory probe did not match, so I’m not going to
     paper over it. I’m going back to the generated fixture and capture to see
     whether the key timing, carried-entry setup, or my conditional draw
     expectation is the wrong piece."

     Action/result: Inspected the JSON report and generated capture; the handler
     returned but the validation condition was false.

680. Reported: "The capture is not an inventory screen; it is essentially a
     text-mode/DOS-looking bottom band, which means the probe did not make it
     through the intended visual path before the screenshot. I’m checking
     whether the fixture launched, whether the carried-object setup exposed a
     blocking text window, and whether the baseline expectation needs to account
     for text-mode cleanup."

     Action/result: Re-read the inventory disassembly and identified the
     absolute byte store at `DS:0x0022`.

681. Reported: "Found the issue, and it’s a good catch from the disassembly:
     the inventory handler writes absolute `DS:0x0022`, while byte variables are
     based at `DS:0x0009`. So the script-visible variable is `0x19`, not
     `0x22`. I’m correcting the probe and docs language rather than treating the
     failed QEMU run as noise."

     Action/result: Renamed and corrected the inventory Enter/Escape probes to
     check bytecode variable `0x19`.

682. Reported: "The corrected bytecode now checks variable `0x19`, matching the
     absolute store at `0x0022`. I’m rerunning the same original-engine batch
     with the corrected case IDs."

     Action/result: Focused tests passed; started the corrected QEMU batch.

683. Reported: "The batch is running again from a fresh snapshot disk. This
     should also tell us whether QEMU’s monitor `esc` key name is accepted by
     the DOS event loop for this interpreter path."

     Action/result: Corrected `inventory_selection_001` matched 3/3, including
     the named `esc` key path.

684. Reported: "Good, all three inventory probes match now. The failed run was
     useful: it exposed that the handler’s absolute byte store maps to script
     variable `0x19`, which is exactly the kind of cross-address detail we want
     nailed down before generalizing."

     Action/result: Prepared to promote `0x7c` in the opcode evidence matrix.

685. Reported: "I’m promoting `0x7c` in the evidence generator from
     source-only/smoke status to behavior-validated status now that the Enter,
     Escape, and acknowledgement paths have QEMU matches."

     Action/result: Updated `tools/logic_opcode_evidence.py` and regenerated
     `docs/src/logic_opcode_evidence.md`.

686. Reported: "I’m updating the written trail now: the bytecode chapter needs
     the corrected variable mapping, the compatibility chapter needs the replay
     command, and the clean-room notes need both the failed and successful runs
     because that failure changed the spec."

     Action/result: Updated the `0x7c` bytecode row.

687. Reported: "The `0x7c` table row now says 'absolute `DS:0x0022`, exposed as
     variable `0x19`,' which is the key correction. I’m also adding stable
     symbolic names for the inventory/list and menu routines so later
     interpreter-version comparisons have anchors beyond raw addresses."

     Action/result: Added inventory and menu labels to
     `docs/src/symbolic_labels.md`.

688. Reported: "The symbolic labels now include `code.inventory.*`,
     `code.menu.*`, and the selection result byte. I’m recording the QEMU replay
     batch in the compatibility chapter next."

     Action/result: Added the `inventory_selection_001` replay command and
     result to `docs/src/compatibility_testing.md`.

689. Reported: "The status and compatibility docs are updated. I’m appending
     the detailed evidence log now, including the initial mismatch because it
     documents the correction from 'variable `0x22`' to 'absolute `0x0022` /
     variable `0x19`.'"

     Action/result: Added the inventory selection source/QEMU pass to
     `docs/src/clean_room_executable_notes.md`.

690. Reported: "The documentation trail is caught up. I’m running the full
     verification set now: unit discovery, opcode evidence check, mdBook build,
     and whitespace diff check."

     Action/result: Started full validation.

691. Reported: "All verification passed: 99 unit tests, evidence check, mdBook
     build, and `git diff --check`. I’m doing one final diff/status pass so I
     can summarize exactly what changed without mixing generated build artifacts
     into the answer."

     Action/result: Verified final status and diff summary.

692. Reported: "I’ll work through the five families in order, source-first:
     menu interaction, view-resource display, system/dialogs, file-backed
     save/log behavior, then sound completion. I’ll keep QEMU probes narrow and
     only use them where the disassembly gives us a concrete side effect to
     validate."

     Action/result: Started the five-family follow-up pass.

693. Reported: "I’ve got the current open list. I’m going into the disassembly
     around the menu interaction, view-resource display, trace/system, file/log,
     and sound handlers before touching probes; there are a few places where an
     opcode’s visible result is indirect, so source context matters."

     Action/result: Created initial source slices.

694. Reported: "The slices are ready. I’m disassembling the target ranges now
     and looking for direct byte/flag side effects that can be observed by logic
     conditions, because those make much better compatibility tests than broad
     'screen changed' assertions."

     Action/result: Found the initial slices were misaligned for some targets.

695. Reported: "One correction from the tooling pass: these image offsets need
     the executable-file header adjustment when slicing (`file offset = image
     offset + 0x200`). I caught that because the first `0x5ebf` slice landed in
     DOS file wrappers instead of the documented view-display handler, so I’m
     regenerating the slices with the correct file offsets."

     Action/result: Regenerated aligned slices using image offset plus
     `0x200`.

696. Reported: "Now the slices are aligned to the image addresses used in the
     docs. I’m re-disassembling the corrected ranges and pulling out the
     control-flow facts we can turn into fixtures."

     Action/result: Re-disassembled menu, view-resource, save/restore, log,
     sound, trace, signature, and joystick ranges.

697. Reported: "The source pass is giving us several good anchors: menu Enter
     enqueues a type-3 event with the item id via `0x44a9`, `0x81/0xa2` share
     `0x5edb`, `0x90` appends to `logfile`, `0x95/0x96` are observable through
     trace-window globals, and `0x63` clears its completion flag before starting
     sound. I’m checking how those internal events surface back to logic
     bytecode so the probes can assert state instead of just 'the program
     didn’t hang.'"

     Action/result: Located event/status and helper paths for the planned
     probes.

698. Reported: "The menu source shows the interaction routine itself cleanly,
     but I still need the caller path: `0xa1` only sets `[0x1d22]`, and some
     top-level code must notice that and call `code.menu.interact`. I’m locating
     those references before writing the menu fixture."

     Action/result: Searched references to `[0x1d22]`.

699. Reported: "The caller reference is around file offset `0x358d`, which maps
     to image `0x338d`. I’m reading that neighborhood; it should tell us how to
     trigger the menu loop from script-level bytecode."

     Action/result: Confirmed the menu request word participates in the
     input/event path.

700. Reported: "I have enough source detail to add focused cases now. The
     probes I’m adding are intentionally small: menu Enter should surface as
     condition `0x0c` on the item id; view display and dialogs should return
     after acknowledgement/cancel; `0x90` should at least execute the DOS append
     path and return; and `0x63` should clear its completion flag operand as the
     source shows."

     Action/result: Added initial QEMU probe cases for menu, view-resource,
     system/dialog, file/log, and sound.

701. Reported: "The new cases are in the harness. I’m adding them to the
     registry test next so future edits don’t silently drop any of these
     coverage points."

     Action/result: Updated `tests/test_logic_interpreter_probe.py`.

702. Reported: "The registry test has the new cases. I’m running the focused
     Python tests before QEMU, because it’s much cheaper to catch bad bytecode
     construction here than after a DOS boot."

     Action/result: Focused tests passed.

703. Reported: "Focused tests pass. I’m running the probes in smaller QEMU
     batches by family, so if something mismatches we can tie it back to one
     source path instead of sorting through a mixed bag."

     Action/result: Started `menu_interaction_001`.

704. Reported: "The first menu attempt mismatched, which likely means either my
     trigger path is incomplete or Enter is arriving before the menu loop is
     actually waiting. I’m inspecting the capture/report before changing the
     fixture."

     Action/result: The menu validation sprite was present, but menu/status
     text polluted the comparison.

705. Reported: "This mismatch is just the menu/status text strip still visible
     at the top, not a missing validation sprite. That means the Enter path
     worked and set the item status byte; the fixture needs a picture refresh
     before the validation draw, just like the text-window probes."

     Action/result: Added `0x1a` before the menu validation draw.

706. Reported: "I updated the menu validation draw to refresh the picture
     first. The underlying behavior was already present; this just prevents the
     top text strip from polluting the graphics comparison."

     Action/result: Reran `menu_interaction_001`.

707. Reported: "Menu Enter is now QEMU-validated: opening through `0xa1`,
     pressing Enter, and observing condition `0x0c 7` all match. I’m running the
     view-resource pair next."

     Action/result: `menu_interaction_001` matched 1/1 and
     `view_resource_display_001` started.

708. Reported: "The view-resource batch is running. These cases are slightly
     heavier because `0x81/0xa2` load and temporarily render view resources
     before displaying their text-like payload."

     Action/result: `view_resource_display_001` matched 2/2.

709. Reported: "The immediate and variable view-resource display paths both
     match. I’m moving to the system/dialog group now: signature check,
     restart/confirmation cancel, joystick no-device, guarded display toggle,
     and trace-window configuration."

     Action/result: Started `system_dialog_001`.

710. Reported: "The system/dialog batch is underway. The risky ones here are
     the two confirmation prompts; if Escape timing is off, I’ll adjust those
     from the capture/report rather than changing the source interpretation."

     Action/result: Awaited system/dialog batch.

711. Reported: "Still running; this batch has six snapshot restores plus a
     couple of blocking prompts. I’m waiting for the result rather than starting
     anything else that could contend for the QEMU/VNC slot."

     Action/result: Continued waiting for QEMU.

712. Reported: "By 'QEMU-validated' I mean: we ran a generated mini-game/fixture
     inside the original SQ2 interpreter under DOS in QEMU, drove the needed
     input, captured the original engine’s screen, and compared that capture
     against the expected result from our local model."

     Action/result: Clarified evidence terminology for the user.

713. Reported: "The trace-window mismatch is similar in shape: the action
     deliberately draws a trace window, so the screen no longer matches the
     plain sprite expectation. I’m making that fixture source-observable
     instead: enable the trace window, then run `0x95` a second time, which
     should consume one extra byte when `[0x1d10]` is nonzero."

     Action/result: First system batch matched 5/6; trace drawing polluted the
     comparison.

714. Reported: "The screenshot confirms the trace action is doing exactly what
     the source says: it draws a boxed trace area. I’m changing the probe to
     validate the more interesting source detail, the second-call
     byte-consumption behavior, and then refresh the picture before the
     comparison."

     Action/result: Adjusted trace case, then found text-plane pixels still
     persisted.

715. Reported: "Continuing. I’ve converted the trace test from 'screen must stay
     plain' to 'exercise the second-call skip behavior, then clear the trace
     drawing before comparing,' which better matches the disassembly."

     Action/result: Reran focused tests and the system batch.

716. Reported: "Harness tests are clean. I’m rerunning just the system/dialog
     batch with the corrected trace case."

     Action/result: Started the corrected system run.

717. Reported: "The corrected six-case system batch is running. If the trace
     case still mismatches, it will tell us that `0x1a` doesn’t fully clear
     text-plane trace output, and I’ll move that case to a source-backed note
     instead of forcing a visual assertion."

     Action/result: Trace still mismatched after enabled drawing.

718. Reported: "The trace case still leaves text-plane pixels after the
     graphics refresh, so I’m splitting it out: the source notes will document
     its drawn-window and skip-byte behavior, while the QEMU-validated system
     batch will cover the five cases that compare cleanly. Next I’m running the
     file/log and sound cases."

     Action/result: Started `file_log_001`.

719. Reported: "The file/log batch is running. I expect the log append case to
     be clean; save/restore selector Escape is the part that may need key timing
     adjustment."

     Action/result: `file_log_001` matched 3/3.

720. Reported: "File/log paths matched: append returned after touching DOS file
     I/O, and save/restore selectors both cancel cleanly with Escape. I’m
     running the sound-completion flag case now."

     Action/result: Initial sound flag case mismatched.

721. Reported: "The sound flag case mismatched, so I’m inspecting whether the
     sound start failed before clearing the flag, whether the flag is later
     reset on immediate completion, or whether the captured screen simply
     includes audio-related text/state."

     Action/result: Capture showed no validation sprite.

722. Reported: "The sound case didn’t draw the validation sprite, so the
     condition was false. Looking back at the source, `0x63` clears the flag
     before starting, but the sound subsystem can quickly set it again if the
     selected sound completes or fails immediately. I’m adjusting this to a
     simpler source-backed dispatch validation for `0x63` rather than
     overclaiming stable completion-flag timing."

     Action/result: Replaced flag assertion with sound start/stop dispatch.

723. Reported: "I’m replacing the sound flag probe with a start-and-stop
     dispatch case. That still gives `0x63` QEMU coverage, while the exact
     completion flag lifetime stays documented from source until we can
     instrument a less racy sound resource."

     Action/result: Added `sound_start_stop_dispatch_smoke`.

724. Reported: "The sound case is now a start/stop dispatch-smoke. I’m updating
     the test registry and running that single QEMU batch again."

     Action/result: Sound start/stop still mismatched without a prior load.

725. Reported: "Even the start/stop sound dispatch case didn’t reach the
     validation draw, so this is not just flag timing. I’m inspecting the
     report/capture and then I’ll decide whether `0x63` needs a synthetic sound
     fixture instead of using SQ2 sound 1."

     Action/result: Determined `0x63` needs the sound resource loaded first.

726. Reported: "The capture shows the validation draw never happened, and the
     source explains why: `0x63` asks for an already available sound resource
     record and can route into the interpreter error path if it is not loaded.
     I’m adding the preceding `0x62` load before `0x63`, then stopping with
     `0x64`."

     Action/result: Added `0x62(1)` before `0x63(1,77)`.

727. Reported: "The sound start case now mirrors the resource lifecycle: load
     sound, start it with a completion flag, stop/clear state, then draw. I’m
     rerunning the focused test and sound batch."

     Action/result: Focused tests passed and `sound_completion_001` matched 1/1.

728. Reported: "The loaded-start sound case now matches. Before updating
     evidence/docs, I’m also tightening the trace fixture: the enabled trace
     window intentionally leaves text pixels, so the reusable QEMU case should
     be the no-flag gated path for `0x95/0x96`; the enabled-window behavior
     stays source-documented with the screenshot observation."

     Action/result: Narrowed trace case to the flag-clear gated path.

729. Reported: "Trace is now a gated no-op QEMU case, which is a clean dispatch
     check for `0x95/0x96`; the enabled drawing path will be described from
     source and the observed mismatch capture. I’m rerunning the system batch to
     get a clean report."

     Action/result: Started final `system_dialog_001` run.

730. Reported: "The corrected system batch is running again. After this I’ll
     update the evidence table and docs in one pass."

     Action/result: Awaited final system batch.

731. Reported: "The corrected system batch is running again. After this I’ll
     update the evidence table and docs in one pass."

     Action/result: Duplicate status update while waiting for QEMU.

732. Reported: "Great, the system/dialog report is clean now. I’m updating the
     opcode evidence generator to promote the newly matched cases, then I’ll
     regenerate the evidence chapter."

     Action/result: `system_dialog_001` matched 6/6; updated
     `tools/logic_opcode_evidence.py`.

733. Reported: "I’m promoting the cases according to what they actually prove:
     cancellation and menu/view behavior go into QEMU-validated evidence; trace,
     log append, and sound start are dispatch-smoke because their deeper side
     effects need a different assertion path."

     Action/result: Promoted QEMU evidence scopes accurately.

734. Reported: "The evidence mapping is updated. I’m regenerating the mdBook
     evidence chapter from it."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

735. Reported: "Evidence chapter regenerated. I’m updating the prose docs now
     with the exact scope of each batch, including the trace-window and sound
     caveats so the spec doesn’t overclaim."

     Action/result: Updated `docs/src/logic_bytecode.md`,
     `docs/src/current_status.md`, and `docs/src/compatibility_testing.md`.

736. Reported: "Compatibility docs now have the replay commands. I’m adding a
     few symbolic labels for the new anchors: menu trigger/status, trace
     globals, log file handle/name, and sound state."

     Action/result: Updated `docs/src/symbolic_labels.md`.

737. Reported: "Symbolic labels are updated for the new stable anchors. I’m
     appending the clean-room evidence notes with the source slices, failed
     intermediate probes, and final successful QEMU batches."

     Action/result: Appended the follow-up probe evidence to
     `docs/src/clean_room_executable_notes.md`.

738. Reported: "I’m going to pick this back up at the verification stage:
     first make sure the generated opcode evidence, unit suite, mdBook, and
     whitespace checks all agree with the new source-backed/QEMU-backed notes.
     After that I’ll inspect the diff so the final summary is concrete."

     Action/result: Ran the full unit suite, opcode evidence check, mdBook
     build, and whitespace check; all passed.

739. Reported: "The validation pass is clean: 99 tests, opcode evidence check,
     mdBook build, and diff whitespace all passed. I’m doing one quick
     diff/status pass now so I can give you a useful handoff rather than a
     vague 'it worked.'"

     Action/result: Checked `git status --short`, `git diff --stat`, and the
     progress log diff.

740. Reported: "There are two new progress updates from this resumed bit, so
     I’m adding those to the historical log before I wrap. Tiny bookkeeping,
     but it keeps the clean-room audit trail intact."

     Action/result: Added the resumed verification updates to this progress
     log.

741. Reported: "I’ll take these in the order we sketched: room transitions,
     priority screen, object diagnostics, menu edge behavior, then promotion
     of selected dispatch-smoke cases. I’m starting source-first by reading the
     existing handler notes and probe harness so the new tests line up with
     the interpreter rather than just poking at it."

     Action/result: Reviewed current status, opcode evidence, probe harness,
     and tests.

742. Reported: "The docs already summarize these handlers, but I’m going back
     to disassembly for the next changes. In particular I want the branch
     details for `0x1792`, `0x731b`, `0x72b5`, the menu interaction loop, and
     the file/log path before I add or promote probes."

     Action/result: Re-read focused disassembly for room switch, priority
     screen, object diagnostics, menu interaction, and log append paths.

743. Reported: "A few probe shapes are emerging cleanly from the source pass:
     room switching can be exposed through `var0`/`var1`, priority screen and
     object diagnostics can be tested as blocking UI actions that return after
     Enter, and menu disabled/Escape/navigation behavior can be asserted
     through status-byte conditions. The trace enabled path is still awkward
     for pixel comparison because it intentionally leaves text-plane artifacts,
     so I’m not going to overclaim that one."

     Action/result: Selected initial source-derived fixture designs.

744. Reported: "I’m going to add new harness cases now. The cases are
     intentionally narrow: each one turns a source-observed side effect into
     either a variable/status-byte assertion or a stable return-to-draw
     assertion, so the evidence level stays honest."

     Action/result: Added new logic probe cases for room attempts, priority
     screen, object diagnostics, menu edges, and sound stop flag.

745. Reported: "The first batch of new cases is in: immediate/variable room
     switch, priority screen return, object diagnostics return, menu
     Escape/disabled/re-enable/down-arrow, and a sound-stop completion-flag
     assertion. I’m wiring them into the registry test before I ask QEMU
     anything."

     Action/result: Updated `tests/test_logic_interpreter_probe.py`.

746. Reported: "Registry coverage is updated. I’ll run the cheap Python checks
     now; then I’ll run the new QEMU cases by family so any failure points
     back to a small source path."

     Action/result: Focused Python tests and opcode evidence check passed.

747. Reported: "The local tests are clean. I’m starting with the non-menu QEMU
     cases: room switch, priority display, object diagnostics, and sound stop
     flag. Those should tell us quickly whether the source-derived assertions
     are stable under the original engine."

     Action/result: Started `room_priority_diag_sound_001`; the first room
     case mismatched.

748. Reported: "The immediate room-switch case mismatched first, so I’m
     stopping there and inspecting the capture/report. This is useful: room
     switching is broad enough that one of the “obvious” assumptions, likely
     initial previous-room value or post-switch control flow, is off."

     Action/result: Report showed the validation sprite was absent; first
     previous-room assertion was rejected.

749. Reported: "The room switch did change control flow enough to clear the
     expected sprite, but the `var1 == 0` assertion was too specific. The
     source says `var1` receives the previous room byte, and the boot fixture
     appears not to start from zero there, so I’m narrowing the QEMU assertion
     to the stable source effect: `var0` becomes the target room."

     Action/result: Narrowed and renamed the room cases.

750. Reported: "Room switching still isn’t returning to logic 0 with a simple
     `var0` assertion, which is itself a useful correction. I’m adjusting the
     fixture to validate the destination-room execution path instead: after
     `0x12`/`0x13`, the target logic resource should be loaded/run and draw the
     marker."

     Action/result: Reworked room cases to draw from target logic.

751. Reported: "The target logic ran into another source-derived reset effect:
     room switching clears resource/object state, so the destination logic
     cannot rely on the preloaded view/picture from before the switch. I’m
     updating the destination logic to load/show picture 0 and load view 11
     before drawing."

     Action/result: Made target logic self-contained; room cases still
     mismatched.

752. Reported: "The room-switch fixture still doesn’t produce a stable draw,
     even with a self-contained destination logic. I’m going to treat
     `0x12/0x13` as source-backed for now and document the failed attempts;
     they probably need a fuller synthetic logic-0/current-room loop rather
     than a tiny one-shot fixture. I’m removing those failing cases from the
     reusable base registry and continuing with the other four steps."

     Action/result: Removed failing room cases from reusable probe registry.

753. Reported: "The failing room cases are out of the reusable suite. I’m
     running the remaining priority/diagnostics/sound family now; these still
     directly cover steps 2, 3, and part of step 5."

     Action/result: Started `priority_diag_sound_001`.

754. Reported: "The non-room batch is running with three stable assertions:
     `0x64` setting the completion flag, `0x1d` returning from priority
     display, and `0x85` returning from object diagnostics."

     Action/result: `priority_diag_sound_001` matched 3/3.

755. Reported: "Good: sound stop flag, priority screen, and object diagnostics
     all matched. I’m moving to the menu edge batch now: Escape, disabled item
     Enter, disable-then-enable, and down-arrow selection."

     Action/result: Started `menu_edges_001`.

756. Reported: "The menu edge cases are running. If one fails, the likely
     culprit is key timing or the exact QEMU key name for arrows, so I’ll
     separate timing problems from semantic problems by checking the
     capture/report."

     Action/result: Three menu edge cases matched; down-arrow case mismatched.

757. Reported: "Three of four menu edge cases matched. The down-arrow case
     mismatched, so I’m checking whether `down` was the wrong key name/timing
     or whether the menu interpreter uses a different event for vertical
     movement than I assumed."

     Action/result: Capture/report showed the down-arrow case did not reach
     the expected status-8 validation path.

758. Reported: "The failed arrow case may simply be the key sequence arriving
     too tightly while the menu is redrawing. I’m increasing the delay between
     Down and Enter and rerunning just that case once; if it still fails, I’ll
     keep arrow navigation as an attempted-but-not-promoted path."

     Action/result: Slower down-arrow retry still mismatched.

759. Reported: "The slower Down/Enter attempt still mismatched, so I’m taking
     that failed arrow fixture out of the reusable suite. We’ll keep the source
     mapping and failed capture as evidence, but not as a compatibility test
     until we can instrument the exact key/event conversion path."

     Action/result: Removed the down-arrow case from the reusable suite.

760. Reported: "The reusable menu suite now contains the three stable edge
     cases: Escape without status, disabled Enter without status, and
     disable-then-enable followed by Enter setting status. I’m rerunning that
     menu batch cleanly."

     Action/result: `menu_edges_002` matched 3/3.

761. Reported: "Menu edges are clean. For the dispatch-smoke promotion step,
     I’ve already got a stable sound completion-flag assertion; now I’m going
     to see if the `0x90` logfile content can be inspected from the post-run
     qcow image after a single-case run. If that works, we can promote log
     append beyond pixels."

     Action/result: Ran `log_file_contents_001`; visual comparison matched.

762. Reported: "The single log case matched visually. I’m converting that
     qcow back to a raw image and trying to pull `LOGFILE` out of the fixture
     directory with mtools, which will tell us whether file-content assertions
     are practical in this harness."

     Action/result: Converted the qcow image to raw and extracted
     `LF00000/LOGFILE`.

763. Reported: "Great, the converted post-run image contains `LOGFILE`, and
     mtools extracted it. I’m reading the bytes now so we can decide whether
     to formalize a file-content check in the harness or document it as a
     reproducible manual assertion."

     Action/result: File content decoded to two leading newlines, `Room 0`,
     empty `Input line: `, and `LOG`.

764. Reported: "The logfile content matches the source-derived format exactly:
     blank line, `Room 0`, `Input line: `, and the message `LOG`. I’m promoting
     only the parts now backed by stable evidence, while leaving room switching
     and enabled trace as source-backed or attempted."

     Action/result: Updated opcode evidence mapping.

765. Reported: "Evidence mapping is updated: priority display, object
     diagnostics, log append content, stable menu setup/toggle behavior, and
     sound stop flag are promoted; room switching and enabled trace stay out of
     the promoted set. I’m regenerating the evidence chapter."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

766. Reported: "Now I’m updating the prose docs with the exact scope: three
     successful menu edge cases, priority/diagnostics/sound flag successes,
     logfile extraction, and the failed room/down-arrow attempts as
     non-promoted evidence."

     Action/result: Updated `docs/src/logic_bytecode.md`.

767. Reported: "The logic bytecode chapter now records both the successful
     promotions and the failed room/down-arrow attempts. I’m adding replay
     commands for the new batches and logfile extraction to the compatibility
     chapter next."

     Action/result: Updated `docs/src/compatibility_testing.md`.

768. Reported: "I’m refreshing the current-status handoff so the next session
     starts from the real frontier: room switch still needs a fuller fixture,
     menu arrows still need better key/event instrumentation, but
     priority/diagnostics/log/sound/menu toggles moved forward."

     Action/result: Updated `docs/src/current_status.md`.

769. Reported: "I’m adding labels for the newly touched stable anchors: room
     switch helper, priority display flag/action, object diagnostics action,
     and updating existing menu/sound/log notes to mention the new evidence."

     Action/result: Updated `docs/src/symbolic_labels.md`.

770. Reported: "I’m appending a new clean-room note for this pass with the
     exact disassembly commands, successful QEMU batches, failed room/down-arrow
     attempts, and the logfile extraction bytes."

     Action/result: Updated `docs/src/clean_room_executable_notes.md`.

771. Reported: "I’m catching the progress log up with the actual updates from
     this run before doing final validation. This one is a little verbose
     because the room/menu failures are historically useful, not just noise."

     Action/result: Added these progress-log entries.

772. Reported: "The docs and progress log are caught up. I’m running the full
     validation pass now: unit suite, evidence check, mdBook build, and
     whitespace check."

     Action/result: Unit tests, evidence check, and mdBook build passed;
     whitespace check found one trailing space in a logfile code block.

773. Reported: "Validation is clean except for one trailing space in the
     literal logfile block. I’m fixing that formatting nit and rerunning the
     doc/whitespace checks."

     Action/result: Removed the trailing space and clarified that the input
     line buffer is empty.

774. Reported: "The trailing-space issue is fixed, and the prose now
     explicitly says the input-line buffer is empty so the code block can stay
     whitespace-clean. Rechecking the touched validation pieces."

     Action/result: mdBook build, whitespace check, and opcode evidence check
     passed.

775. Reported: "The rechecks are clean. I’m adding the last validation updates
     to the progress log, then I’ll inspect the final diff/status for the
     handoff."

     Action/result: Added final validation updates to this progress log.

776. Reported: "Commit `bc02913` is in place; only generated/untracked
     directories remain. I’m moving into the next pass now, starting with source
     around the room cycle and input event pipeline because those are the two
     places where tiny QEMU probes were too shallow."

     Action/result: Confirmed the previous commit and began a source-first
     pass over room switching and menu/input events.

777. Reported: "The existing notes already captured the earlier failed
     room-switch fixture shapes, which is useful because it tells us what not
     to trust yet. I’m going to build the next room probes around the concrete
     source effect the helper definitely performs: setting flag 5 and
     re-entering the logic cycle."

     Action/result: Re-read the room-switch helper and prepared a flag-5-based
     fixture shape.

778. Reported: "The disassembly confirms the room-switch wrapper itself
     returns zero after the helper, and `code.engine.main_cycle` immediately
     re-runs logic 0 while that zero return persists. That means a good fixture
     should expect logic 0 to re-enter after `0x12/0x13`, not expect the
     switched-to logic to execute automatically."

     Action/result: Confirmed wrapper return behavior and corrected the fixture
     hypothesis away from automatic target-logic execution.

779. Reported: "For menu arrows, the source shows a second event-type path
     rather than normal status-byte mapping. There is a fixed table at `0x16b3`
     mapping raw event words `0x4800/0x4900/0x4d00/0x5100/0x5000/0x4f00/0x4b00/0x4700`
     to menu movement codes `1..8`; `0x5000` is the down-arrow candidate."

     Action/result: Identified and recorded the menu-direction key table.

780. Reported: "I’m adding two room-switch probes that lean on the
     source-backed flag-5 effect rather than the earlier mistaken 'target logic
     should run automatically' assumption. I’ll also add a small down-arrow key
     mapping probe so we can separate 'QEMU produced the raw arrow event' from
     'the menu loop navigated.'"

     Action/result: Added temporary room-switch and down-arrow probe cases.

781. Reported: "The room-cycle source gives us a sharper correction: after
     logic 0 returns zero from the switch action, the engine clears a few
     variables and immediately invokes logic 0 again in the same top-level loop
     until it gets a nonzero interpreter return. That’s why the fixture must
     guard against repeated switching with its own init flag."

     Action/result: Added an init-flag guard to the temporary room fixtures.

782. Reported: "I’ve wired the new cases into the local registry test. Next
     I’m running just the Python suite, then I’ll take the new probes through
     QEMU in small batches."

     Action/result: Updated local registry tests and ran the unit suite; it
     passed before QEMU execution.

783. Reported: "The immediate room-switch probe still mismatched, so I’m
     stopping before treating it as evidence. I’m opening the report and the
     generated fixture bytes now; this is exactly the kind of case where the
     disassembly should explain why the synthetic control flow is still wrong."

     Action/result: `room_reentry_001` mismatched on the immediate room-switch
     case.

784. Reported: "The 'failed' room probe actually drew the validation sprite;
     the mismatch is priority/composition, not control flow. That is a good
     catch: the source-backed re-entry model appears right, but the fixture’s
     expected priority assumption is too strict after the room switch rebuilds
     display state."

     Action/result: Initially suspected a composition issue from the comparison
     sample, then inspected the screenshot and rejected that interpretation.

785. Reported: "One nuance: the report samples are from the downsampled logical
     buffer, while the raw screenshot inspection reports only two RGB colors in
     the VGA capture. I’m checking the actual image and the generated LOGIC
     resource bytes so I don’t misread a pixel-comparison artifact as engine
     behavior."

     Action/result: Converted and inspected the QEMU capture; it showed a blank
     white screen, confirming the validation sprite was not drawn.

786. Reported: "The fixture stores resources inside VOL files, so there are no
     standalone `LOGIC.*` files to inspect in that directory. I’ll use the
     probe’s Python objects for bytecode inspection and look at the screenshot
     directly."

     Action/result: Inspected generated case bytecode through the Python probe
     object rather than nonexistent standalone resource files.

787. Reported: "The screenshot confirms no sprite, so this is a real failed
     control-flow assertion. The most likely source-side explanation is that
     the room switch calls `0x10d0`, which I haven’t fully accounted for; if it
     clears script flags, my guard flag gets wiped and logic 0 keeps switching
     forever."

     Action/result: Re-read `0x10d0`; this did not prove flag clearing, so the
     investigation moved to logic resume pointers.

788. Reported: "The source points to a better explanation than 'flags got
     cleared': logic records carry a resume pointer. A room switch returns zero
     from the current action, so logic 0 may be called again from its saved
     post-switch instruction pointer unless the fixture explicitly restores the
     logic entry IP first. I’m going to fold opcode `0x92` into the synthetic
     switch path and rerun."

     Action/result: Added `0x92` before the temporary synthetic room-switch
     calls.

789. Reported: "That edit keeps the fixture narrow: it does not claim `0x12`
     itself resets logic 0, only that the switch helper sets flag 5 and the
     engine observes it after an explicit entry-IP restore. I’m running the
     targeted unit check and QEMU batch again."

     Action/result: Targeted unit test passed; QEMU `room_reentry_002`
     still mismatched.

790. Reported: "`0x92` did not change the outcome. I’m going back to the
     interpreter loop now, because the exact place it stores or reuses the
     logic IP is the source of truth for why logic 0 does not re-enter the way
     the synthetic fixture expects."

     Action/result: Re-read `code.logic.interpret_main` and
     `code.logic.call_logic`.

791. Reported: "The interpreter loop is clear: it starts from record `+0x06`,
     and `0x92` does set `+0x06` to the logic’s entry pointer. The remaining
     mismatch looks like display-state contamination around the tiny sprite
     area rather than a missing draw, so I’m zooming the capture and then I’ll
     rerun the two room cases without `--stop-on-failure` to see whether the
     variable-target case behaves the same."

     Action/result: Reran both room cases without stop-on-failure; both
     mismatched.

792. Reported: "Both room cases mismatch the same way, which is still useful
     evidence: the fixture reaches a stable screen but not the expected
     compatibility assertion. I’m going to keep these as attempted/non-promoted
     for now and move the validated work to the down-arrow event split."

     Action/result: Decided not to promote the room re-entry fixtures.

793. Reported: "I’m not going to leave failing room probes in the reusable case
     list. I’ll preserve the attempted evidence in docs instead, then keep only
     stable probes in the tool. First I’m checking whether the raw down-arrow
     status mapping is stable."

     Action/result: Ran `down_key_001`; it mismatched.

794. Reported: "The down-arrow mapping did not validate either, which tells us
     QEMU’s `sendkey down` is not currently arriving as the raw `0x5000` event
     that the source table expects, or it arrives outside the polling window.
     I’ll remove that from the reusable suite too and document it as an
     input-instrumentation gap rather than a behavior claim."

     Action/result: Removed temporary failing room and down-arrow cases from
     the reusable probe registry.

795. Reported: "The reusable suite is back to stable cases only. I’m adding
     symbolic labels for the event-direction table and the logic resume/entry-IP
     helpers, because those are exactly the cross-version anchors we’ll want
     when comparing other interpreter builds."

     Action/result: Added symbolic labels for logic resume helpers and the
     menu-direction event table.

796. Reported: "The docs already had most of the raw input machinery; I’m
     tightening it with two cross-version-friendly names: the type/value event
     enqueue helper and the menu-direction raw key map."

     Action/result: Added `code.input.enqueue_event` and
     `data.input.menu_direction_event_map` labels.

797. Reported: "I’m updating the bytecode chapter to make the important
     distinction explicit: source shows down-arrow maps to movement code 5
     inside the menu event path, but our current QEMU key injection has not
     produced that raw event reliably."

     Action/result: Updated `logic_bytecode.md` with down-arrow and room-switch
     evidence boundaries.

798. Reported: "The bytecode chapter now states the boundary between
     source-backed facts and failed QEMU instrumentation. I’m adding the
     detailed clean-room trail next: exact disassembly ranges, exact QEMU
     commands, and what each failed probe ruled out."

     Action/result: Added a clean-room notes section for this pass.

799. Reported: "I’m also updating current-status and compatibility notes so the
     next session doesn’t accidentally retry the same naive room/down-arrow
     fixtures without new instrumentation."

     Action/result: Updated `current_status.md` and `compatibility_testing.md`
     with attempted-but-not-promoted fixture details.

800. Reported: "Docs and logs are updated. I’m running the validation pass now:
     unit tests, opcode evidence check, mdBook build, and whitespace check."

     Action/result: `python3 -B -m unittest discover -s tests`,
     `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
     and `git diff --check` all passed.

801. Reported: "Validation is clean. I’m doing a final diff/status pass now so
     I can give you an accurate handoff without accidentally including
     generated artifacts."

     Action/result: Final status showed docs-only tracked changes plus the
     existing untracked `build/` and `002962_ms_dos_622/` directories.

802. Reported: "Got it: I’ll leave the current docs changes uncommitted and
     keep working on top of them. I’m starting with the real SQ2 logic
     resources, because that should tell us what the room-switch contract
     actually looks like before we spend more QEMU cycles."

     Action/result: Started a source-first pass over SQ2 logic resources.

803. Reported: "The repo already has a local logic disassembler and resource
     readers, so I can stay inside the clean-room tooling. I’m checking how
     much it currently prints before deciding whether to extend it for
     logic0/room-call analysis."

     Action/result: Re-read `tools/disassemble_logic.py` and disassembled
     logic 0.

804. Reported: "Logic 0 is the real 'director' script: it has early room
     switches during boot, then a flag-5 block that resets ego/object state and
     preloads resources for the current room. I’m narrowing on the opcodes that
     actually call room scripts and trigger room switches."

     Action/result: Searched SQ2 logic 0 for switch/load/call/resume actions.

805. Reported: "The pattern is already visible in real resources: many room
     logics begin with `if flag 5`, do room-entry setup, then continue to
     per-cycle behavior and end. Logic 0 does not call the current room by
     number as a var; instead the room resource itself is loaded by the switch
     helper and resumed/called as part of the linked logic cache behavior. I’m
     going to map that across room logics rather than infer from one example."

     Action/result: Checked room logic resources 1 through 4 and then broadened
     the scan; the next step corrected the initial inference.

806. Reported: "This corrects my last inference: logic 0 is not calling every
     room directly, but the loaded room logic clearly begins at offset 0 and
     handles `flag 5` as its entry block. I’m checking whether the engine calls
     loaded logics through a separate cache/list runner, because
     `code.engine.main_cycle` only has the obvious `call_logic(0)` call in the
     slice we already read."

     Action/result: Re-read nearby executable helpers and continued searching
     logic 0.

807. Reported: "Found it: logic 0 does call the current room, but later than
     the entry/menu block. At offset `0x053e` it does `call_logic_var(v0)`, so
     the room number in variable 0 is the dispatch key. That explains why
     synthetic room fixtures need a logic-0 loop with `call_logic_var(v0)`, not
     a target logic that magically runs after `switch_room`."

     Action/result: Identified SQ2 logic 0 bytecode offset `0x053e` as the
     current-room dispatch point.

808. Reported: "Now I have a better fixture shape: mimic logic 0’s real pattern
     by switching rooms, then having logic 0 call `call_logic_var(v0)` so the
     loaded room logic runs while flag 5 is still set. I’m adding that as a
     targeted compatibility probe instead of the earlier one-shot draw."

     Action/result: Temporarily added two logic-0-shaped room dispatch probes.

809. Reported: "The new cases are in the reusable suite, but only provisionally
     until QEMU agrees. I’m running the targeted local test and then the
     room-switch batch."

     Action/result: Targeted registry test passed; generated bytecode looked as
     intended.

810. Reported: "The bytecode shape looks right: logic 0 switches once, then
     uses `call_logic_var(v0)` to run the current room logic. I’m putting the
     two cases through QEMU now."

     Action/result: Started QEMU batch `room_dispatch_001`.

811. Reported: "Still mismatched, so I’m not promoting it. This time the
     fixture matches the real `call_logic_var(v0)` pattern, which tells us
     another part of real logic 0’s entry sequence is still required. I’m
     opening the capture/report and then I’ll pull these provisional cases back
     out."

     Action/result: `room_dispatch_001` mismatched with the same blank-screen
     signature as prior room attempts.

812. Reported: "The capture is the same blank screen signature. I’m checking
     fixture construction too, because if extra logic resources are not patched
     into `LOGDIR` correctly then `call_logic_var(v0)` would never reach the
     target logic no matter how good the script pattern is."

     Action/result: Inspected `LOGDIR` and `VOL.3`; the extra logic resource
     was patched at the expected offset.

813. Reported: "The fixture construction looks correct, including patched
     LOGDIR entries for logic 1 and 2. So this failure is now genuinely about
     the runtime room/logic lifecycle, not a missing resource patch. I’m
     removing the provisional cases again and documenting the stronger source
     finding: real logic 0 calls `call_logic_var(v0)` at offset `0x053e`, while
     room logics gate entry setup on flag 5."

     Action/result: Removed the temporary failing room-dispatch cases from the
     reusable probe registry.

814. Reported: "I’m updating the spec now with the real room-script structure:
     byte variable 0 is current room, byte variable 1 is previous room, byte
     variable 2 is entry boundary, and SQ2 logic 0 calls the current room via
     `call_logic_var(v0)` after the global entry/menu work."

     Action/result: Updated symbolic labels and logic bytecode prose with the
     room variable roles and logic-0 dispatch offset.

815. Reported: "The main bytecode chapter and labels now have the real SQ2
     room dispatch model. I’m adding the chronological command trail and the
     failed QEMU replay name, then I’ll run tests/docs."

     Action/result: Updated clean-room notes, current status, and compatibility
     testing with the real-SQ2 room dispatch source pass and failed QEMU batch.

816. Reported: "The temporary QEMU cases are back out, so the reusable test
     suite should remain stable. I’m doing a quick diff check on tools/tests
     now, then I’ll validate the docs and local suite."

     Action/result: Confirmed there was no remaining tracked diff in
     `tools/logic_interpreter_probe.py` or `tests/test_logic_interpreter_probe.py`.

817. Reported: "Progress log is caught up. I’m running the validation pass:
     unit suite, evidence check, mdBook, and whitespace."

     Action/result: Ran the local unit suite, opcode-evidence check, mdBook
     build, and diff whitespace check successfully after the room-dispatch
     documentation updates.

818. Reported: "Validation is clean. I’m checking final status now so I can
     hand off exactly what changed and what remains uncommitted."

     Action/result: Checked final Git status; the remaining worktree changes
     are documentation files, with generated `build/` artifacts and local DOS
     installer images still untracked.

819. Reported: "I’ll take the five-step list as the work queue: room lifecycle
     first, then input/menu, selection/system, sound, and labels/docs. I’m
     going source-first and will only use QEMU if a result needs confirmation
     or turns into a durable test."

     Action/result: Started a five-step source-first lifecycle pass and created
     a working plan.

820. Reported: "First I’m gathering the existing symbol map, notes, and helper
     scripts so I can extend the current evidence trail instead of creating a
     parallel one."

     Action/result: Read the symbol map, searched existing notes/tools/tests,
     and confirmed only generated/local directories were untracked.

821. Reported: "The current docs already have many labels, so this pass can be
     a tightening pass rather than a broad search. I’m opening the disassembly
     around the five target families now, especially the call sites that explain
     why the previous synthetic room fixture is too thin."

     Action/result: Opened real SQ2 logic 0 and the first broad disassembly
     windows for room, main-cycle, input, menu, save, and sound paths.

822. Reported: "One wrinkle: the raw full disassembly includes executable
     header bytes, so some addresses are offset from the “image” addresses in
     the docs. I’m checking the existing slice/disassembly workflow before
     trusting any raw line numbers."

     Action/result: Reconfirmed the documented convention that file offset is
     image offset plus `0x200` for `build/cleanroom/AGI.decrypted.exe`.

823. Reported: "The project’s convention is clear: file offset is image offset
     plus `0x200`. I’m using focused `ndisasm` windows with that correction for
     the room switch, main cycle, input/menu, save/restore, and sound paths."

     Action/result: Re-disassembled focused corrected windows for
     `0x175c`, `0x0150`, `0x4529`, and `0x93d1`.

824. Reported: "The first source pass already answers two useful questions:
     room switching deliberately returns zero to force the main cycle back into
     logic 0, and menu arrow navigation is driven by normalized type-2 events,
     not status bytes. I’m reading save/system and sound now."

     Action/result: Identified the room-switch zero return and menu type-2
     movement dispatch, then opened save, restore, selector, and sound windows.

825. Reported: "I’m going one layer down on the room reset calls now. The
     switch helper’s call list is compact, so mapping those callees should give
     us a higher-level lifecycle spec without guessing from QEMU symptoms."

     Action/result: Mapped reset/resource-event callees around `0x10d0`,
     `0x1485`, `0x7060`, and restore replay helper `0x681c`.

826. Reported: "The save/restore path is also cleaner now: the selector helper
     is responsible for prompt-mode setup, path validation, and preserving the
     input marker; the save/restore handlers do the actual block I/O after it
     returns a nonzero selection. I’m checking the event queue root next so the
     menu/input notes can name the globals."

     Action/result: Mapped event queue enqueue/dequeue helpers and identified
     queue storage `0x11ba`, write pointer `0x120a`, and read pointer `0x120c`.

827. Reported: "I spotted one bad byte dump: I asked `xxd` for the executable
     at the data-table offset, which is the wrong backing file for AGIDATA
     data. I’m correcting that against `SQ2/AGIDATA.OVL` before I document the
     menu table."

     Action/result: Discarded the executable dump and confirmed
     `DS:0x16b3`/`DS:0x16d7` movement tables from `SQ2/AGIDATA.OVL`.

828. Reported: "I have enough source-backed material to start editing: this
     will be mostly spec/label expansion, plus the progress log. I’m going to
     keep the wording careful: QEMU did not validate new behavior here, but the
     disassembly improves the model and narrows what future tests should
     target."

     Action/result: Prepared documentation-only edits with no new QEMU cases.

829. Reported: "I’m making the documentation edits now. The main additions are:
     the room switch’s exact return-to-main-cycle behavior, event queue/menu
     navigation roles, save/restore selector responsibilities, restore-time
     resource replay, and sound state labels."

     Action/result: Updated `docs/src/logic_bytecode.md` with refined room,
     menu/input, save/restore, and sound semantics.

830. Reported: "The bytecode chapter has the first wave of updates. I’m adding
     the stable labels next, including the event queue globals and room/save/sound
     helper roles that future version comparisons will need."

     Action/result: Added symbolic labels for heap reset, input event queue,
     menu drawing/navigation helpers, restore replay, sound helpers, and event
     queue globals.

831. Reported: "Labels are expanded. I’m adding the chronological clean-room
     notes for the commands and observations, then I’ll refresh the
     current-status page so the handoff reflects this pass."

     Action/result: Added a clean-room notes section for the source-first
     lifecycle pass.

832. Reported: "The clean-room note is in place. I’m checking its placement
     now; if I accidentally inserted it inside an older section instead of
     after it, I’ll move it so the chronology stays readable."

     Action/result: Found the new lifecycle note had split an older picture/view
     command list.

833. Reported: "Placement is good. I’m reading the following lines too just to
     make sure the older picture/view section still continues cleanly after the
     new note."

     Action/result: Confirmed the split was real because older picture/view
     commands continued after the new lifecycle note.

834. Reported: "Yep, one issue: the new section split an older picture/view
     command list. I’m moving the lifecycle note down below that older section
     so the historical record stays tidy."

     Action/result: Removed the misplaced lifecycle note from the middle of the
     picture/view command list.

835. Reported: "The accidental split is removed. I’m inserting the lifecycle
     pass after the picture/view section’s documented result now."

     Action/result: Reinserted the lifecycle pass after the picture/view
     documented result and before the next historical section.

836. Reported: "The note is back in chronological shape. I’m updating current
     status now: several “what’s next” items have changed from “map this” to
     “we have the source model; build targeted tests only where possible.”"

     Action/result: Updated `docs/src/current_status.md` with the refined room,
     menu, save/restore, and sound source models and next-test guidance.

837. Reported: "The main docs are updated. I’m recording the work-session
     updates in the progress log before running validation, so the historical
     trail includes the source pass and the small correction I made while
     editing."

     Action/result: Added progress-log entries for the source-first lifecycle
     pass, including the corrected AGIDATA table dump and the note-placement
     fix.

838. Reported: "Progress log is caught up through the documentation edits. I’m
     doing a quick read of the touched sections for continuity before
     validation."

     Action/result: Reviewed the edited bytecode and clean-room note sections
     for continuity.

839. Reported: "The touched sections read coherently now. I’m running the
     validation suite and docs build next; since these are documentation-only
     edits, the full local unit suite plus mdBook/diff checks should be enough."

     Action/result: Ran the full local unit suite, opcode evidence check,
     mdBook build, and diff whitespace check successfully.

840. Reported: "Validation is clean. I’m checking the final diff/status and
     then I’ll add the closing progress-log entries for the validation and
     handoff."

     Action/result: Checked final status and diff summary; the worktree has
     documentation changes only, plus expected untracked `build/` and
     `002962_ms_dos_622/` directories.

841. Reported: "I’m going to turn the room-switch finding into a fixture that
     mirrors the source-shaped lifecycle more closely: logic 0 performs the
     switch once, then on engine re-entry dispatches through
     `call_logic_var(v0)` into a target room logic that owns its own
     picture/view setup. Then I’ll let QEMU tell us whether that structure
     matches the original engine rather than treating a guess as fact."

     Action/result: Started a room-switch re-entry probe pass focused on
     source-shaped logic-0/current-room dispatch.

842. Reported: "The helper insertion point moved a little from what I had in
     my head, so I’m checking the exact neighborhood before patching. Small
     friction, but it’s useful because the harness has accumulated a lot of
     deliberately-shaped fixture helpers."

     Action/result: Re-read the probe helper area and call-logic case list in
     `tools/logic_interpreter_probe.py`.

843. Reported: "I’ve added explicit helper code for the re-entry shape, with
     the initialization flag set before the room switch because the switch path
     itself short-circuits the current logic invocation. That detail is exactly
     the kind of thing that made the earlier fixtures slippery."

     Action/result: Added room re-entry helper functions and initial immediate
     and variable-selected room-switch probe cases.

844. Reported: "I’m also pinning the new cases in the unit coverage list. It’s
     not deep verification by itself, but it prevents these probe definitions
     from quietly disappearing while we iterate on the harder QEMU behavior."

     Action/result: Added unit coverage assertions for
     `switch_room_reentry_dispatches_current_room` and
     `switch_room_v_reentry_dispatches_current_room`.

845. Reported: "The first unit pass caught a naming mismatch in the dataclass
     constructor, not a behavioral problem. I’m correcting that before moving
     on to QEMU so the probe harness stays internally clean."

     Action/result: Fixed the new case constructor to use
     `expected_group_no`, `expected_frame_no`, and `expected_baseline_y`.

846. Reported: "The dataclass fix is in. Next I’m doing the quick
     deterministic test run again, then I’ll run the two new fixtures through
     the original interpreter."

     Action/result: `python3 -B -m unittest tests.test_logic_interpreter_probe`
     passed: 7 tests OK.

847. Reported: "The local harness tests pass now. I’m moving to the important
     part: running just the new room-switch cases under QEMU so we have
     original-engine evidence before documenting them as validated."

     Action/result: First QEMU command attempted a bare `--snapshot` flag, but
     the harness only exposes snapshot image path options.

848. Reported: "This harness doesn’t have a `--snapshot` flag on the current
     branch; it only exposes the snapshot image paths. I’ll use its normal
     serial runner for the two-case check."

     Action/result: Re-ran the room-switch cases with the supported harness
     arguments.

849. Reported: "Both room-switch re-entry cases matched the original engine in
     QEMU, including the variable-selected room form. I’m going to run the
     project’s compatibility unit suite next, then I’ll update the docs with
     the evidence and the higher-level semantics."

     Action/result: QEMU batch `room_switch_reentry_001` matched 2/2 with 0
     errors and 0 mismatches.

850. Reported: "The full local compatibility suite is green. I’m documenting
     the new evidence now: the source-shaped model, what the QEMU cases prove,
     and why the target room logic has to perform its own resource setup after
     the switch."

     Action/result: `python3 -B -m unittest discover -s tests` passed: 99
     tests OK.

851. Reported: "The docs still correctly preserve the earlier failures, but
     now need a follow-up paragraph that supersedes their status. I’m also
     checking the opcode evidence generator so the evidence table doesn’t lag
     behind the new QEMU result."

     Action/result: Found `tools/logic_opcode_evidence.py` still marked
     action rows `0x12` and `0x13` as source-backed.

852. Reported: "The evidence generator still marks room switching as
     source-backed. Since the new QEMU cases match the original interpreter,
     I’m promoting only the tested behavior: zero-return re-entry plus
     current-room dispatch, not every side effect of the broad reset helper."

     Action/result: Updated the evidence generator to cite the two matched
     room-switch re-entry cases for action rows `0x12` and `0x13`.

853. Reported: "The generator is updated. I’m regenerating the opcode evidence
     chapter now so the book reflects the promoted room-switch cases."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

854. Reported: "I’m updating the handoff/status text so it no longer tells
     future us that the room-switch fixture still needs to be built. The older
     failed attempts stay in the record; the new matched case becomes the
     current evidence."

     Action/result: Updated `docs/src/current_status.md` with the validated
     room-switch re-entry fixture and revised next steps.

855. Reported: "I’m adjusting the logic bytecode chapter next. The key nuance
     is that QEMU validates the control-flow shape, while several internal
     reset effects are still grounded in disassembly rather than direct fixture
     assertions."

     Action/result: Updated `docs/src/logic_bytecode.md` to describe
     `room_switch_reentry_001` and separate QEMU-validated dispatch behavior
     from source-backed reset details.

856. Reported: "I’m adding the exact QEMU command to the compatibility chapter
     and marking the older failed room fixtures as superseded experiments, not
     current blockers."

     Action/result: Updated `docs/src/compatibility_testing.md` with the new
     room-switch re-entry batch and superseded-fixture notes.

857. Reported: "I’m appending the clean-room notes with the actual commands and
     observed result. This is the audit trail piece: future readers should be
     able to see exactly how the room-switch fixture went from failed attempts
     to a matched QEMU batch."

     Action/result: Added a clean-room notes section for the room-switch
     re-entry QEMU validation pass.

858. Reported: "The main docs are updated. I’m logging the intermediate
     progress updates now so the historical record includes the small test
     failure, the harness flag correction, and the successful QEMU validation."

     Action/result: Added progress-log entries for the room-switch re-entry
     fixture work and QEMU result.

859. Reported: "The progress log is caught up through the docs edits. I’m
     running validation now: the local unit suite again, mdBook build, and a
     quick diff/status pass."

     Action/result: Ran `python3 -B -m unittest discover -s tests` and
     `mdbook build docs`; both passed.

860. Reported: "Validation is clean. I’m checking the final diff now so I can
     give you the concise “what changed / what’s next” without making you sift
     through generated noise."

     Action/result: Checked `git status --short` and `git diff --stat`.

861. Reported: "The core validation passed. I’m doing one last whitespace check
     and a focused status read; then I’ll hand back the result and the next
     concrete reverse-engineering steps."

     Action/result: `git diff --check` passed with no whitespace errors; final
     status still includes pre-existing modified docs and untracked generated
     directories.

862. Reported: "The whitespace check is clean too. I’m adding the closing
     validation entries to the progress log so this turn’s record includes the
     green tests and book build."

     Action/result: Added closing progress-log entries for validation and
     handoff.

863. Reported: "I’ll start with the `v2` room-entry boundary probe,
     source-first. I’m going to re-read the switch helper and the existing probe
     helpers, then shape the QEMU cases so they validate the entry placement
     through ordinary logic bytecode rather than peeking at memory."

     Action/result: Re-read room-switch helper `0x1792`, probe helper code, and
     existing room-switch fixtures.

864. Reported: "The switch helper confirms the four `v2` cases in code: `1`
     writes object 0 Y to `0xa7`, `2` writes X to `0`, `3` writes Y to `0x25`,
     and `4` writes X to `0xa0 - object_width`, then clears `v2`. I’m shaping
     the cases so the destination logic reads object 0 with the normal getter
     and only draws if the expected field matches."

     Action/result: Added helper code for boundary-selector fixtures that use
     action `0x27` to read object 0 after room-switch re-entry.

865. Reported: "I’m going to cover all four boundary selectors. The fourth case
     depends on object width, so I’ll initialize object 0 with view 11 frame 0
     before the switch; the disassembly leaves width intact and uses it for
     `0xa0 - width`, which should give X `140` for that 20-pixel-wide cel."

     Action/result: Added four base cases for selectors 1 through 4 and pinned
     them in the logic probe unit test list.

866. Reported: "The cases are registered. I’m running the local unit test for
     the probe definitions first; if that’s clean, I’ll run just these four
     cases through QEMU."

     Action/result: Logic probe unit tests and `py_compile` passed.

867. Reported: "The definition tests pass. I’m launching the four
     boundary-selector fixtures in QEMU now; this will tell us whether the
     disassembled field writes line up with visible original-engine behavior."

     Action/result: Started QEMU batch `room_boundary_001`.

868. Reported: "The batch is running from one snapshot boot. It has built all
     four fixture directories and is now executing the captures."

     Action/result: `room_boundary_001` continued running under QEMU snapshot
     mode.

869. Reported: "The first boundary case mismatched, so I’m not promoting the
     set yet. I’m going to inspect the generated report and capture signature to
     see whether the validation draw never happened or whether one of the
     expected coordinates is wrong."

     Action/result: The first capture was all white; no validation draw
     occurred.

870. Reported: "The capture is a blank all-white screen, which means the
     destination room ran far enough to show its picture but the coordinate
     condition did not pass. I’m going back to the object-position getter and
     setup path in the disassembly before trying new hypotheses, because the
     field write may be right while my bytecode-level observation is reading a
     different or reset field."

     Action/result: Re-read object getter/setup-related disassembly.

871. Reported: "The getter path is byte-based and normal object fields are at
     `+0x03/+0x05`, as expected. The failure likely means the switch helper’s
     later refresh calls alter object 0 after the boundary write, or object 0’s
     special lifecycle differs from ordinary objects. I’m going to build a
     diagnostic fixture that encodes the observed value into a visible draw
     choice, still using bytecode and QEMU rather than debugger memory."

     Action/result: Generated a diagnostic under `build/` to test whether
     action `0x27` can observe object 0 after ordinary setup.

872. Reported: "Before guessing the boundary value, I’m checking the observation
     mechanism itself with a generated diagnostic case under `build/`: set
     object 0, read it back with action `0x27`, and draw only if the getter
     reports the fields we wrote. If that passes, the mismatch is specifically
     post-switch behavior."

     Action/result: Diagnostic object-0 getter case matched QEMU.

873. Reported: "The diagnostic getter case matched, so action `0x27` can
     observe object 0 normally. Now I’m generating a single visual diagnostic
     that draws different marker positions for several post-switch `(x,y)`
     hypotheses, plus a separate marker if `v2` was cleared. That should reveal
     which part of the condition is false."

     Action/result: Generated and ran the boundary marker-map diagnostic; it
     still produced an all-white capture.

874. Reported: "Aha, the diagnostic never drew even the `v2 == 0` marker
     because my pre-switch object setup bound view 11 without loading it first.
     That likely aborted before the switch. I’m fixing the fixture to load view
     11 before setting up object 0, then I’ll rerun the boundary batch."

     Action/result: Corrected boundary fixtures to load view 11 before binding
     object 0.

875. Reported: "The pre-switch setup now loads the view resource before binding
     object 0. I’m re-running the quick unit check and then the four-case QEMU
     batch."

     Action/result: Logic probe unit tests and `py_compile` passed again.

876. Reported: "The corrected boundary batch is executing now. If the
     disassembly-derived values are right, all four should draw their
     validation sprite after the re-entry dispatch."

     Action/result: QEMU batch `room_boundary_002` matched 4/4 with 0
     mismatches and 0 errors.

877. Reported: "Great, all four boundary selectors matched QEMU after fixing
     the pre-switch setup. I’m going to promote these as compatibility cases
     and update the docs with the exact distinction we just learned: object 0
     must have a loaded/bound view before the switch for the right-edge width
     case to be meaningful."

     Action/result: Promoted the four boundary-selector cases and began
     documentation updates.

878. Reported: "I’m checking the relevant doc sections and the evidence
     generator now so the probe list, opcode evidence, compatibility
     instructions, and clean-room notes all agree."

     Action/result: Found the evidence generator needed to mention the new
     boundary-selector cases for action `0x12`.

879. Reported: "I’m promoting the boundary coverage in the evidence generator
     and docs now. The wording will stay careful: the bytecode-visible
     entry-boundary placements are QEMU-validated; unrelated internals like
     resource-event recording are still source-backed."

     Action/result: Updated `tools/logic_opcode_evidence.py`.

880. Reported: "The generator is updated. I’m regenerating the opcode evidence
     chapter before editing the prose around it."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

881. Reported: "Next I’m editing the room-switch prose and compatibility
     instructions to include the four matched `v2` selectors and the pre-switch
     view-load lesson from the failed first attempt."

     Action/result: Updated `docs/src/logic_bytecode.md` and
     `docs/src/compatibility_testing.md`.

882. Reported: "The bytecode and compatibility chapters now include the
     boundary batch. I’m updating the handoff page so “entry boundary” moves out
     of the recommended next step and into validated room-switch behavior."

     Action/result: Updated `docs/src/current_status.md`.

883. Reported: "I have the concise switch-helper dump now. I’m appending a
     clean-room note section with the failed first batch, the diagnostic getter
     check, the corrected batch, and the resulting semantics."

     Action/result: Added the room entry-boundary selector QEMU validation
     section to `docs/src/clean_room_executable_notes.md`.

884. Reported: "I’ll take the next small, crisp room-switch probe: controlled
     previous-room updates. I’m going to make the fixture set `v0` to a known
     synthetic previous room before switching, then the destination room logic
     will assert `v0`, `v1`, and cleared `v2` through normal bytecode before
     drawing."

     Action/result: Started the current/previous-room variable validation pass.

885. Reported: "I’m checking the current dirty state and helper locations
     first, since we’re building on the uncommitted boundary-selector work from
     the last slice."

     Action/result: Confirmed the uncommitted boundary-selector changes were
     present and identified the room-switch helper insertion points.

886. Reported: "The existing helpers are a good fit. I’m adding a narrow
     previous-room helper now: pre-switch logic writes a synthetic old room into
     `v0`, switches to room 1, then the destination room draws only if
     `v0 == 1`, `v1 == old_room`, and `v2 == 0`."

     Action/result: Added helper code for current/previous-room validation
     fixtures.

887. Reported: "The helper is in. I’m registering both immediate and variable
     room-switch versions so `0x12` and `0x13` both get previous-room
     coverage."

     Action/result: Added `switch_room_sets_current_previous_and_clears_boundary`
     and `switch_room_v_sets_current_previous_and_clears_boundary`.

888. Reported: "The new cases are pinned in the registry tests. I’m running the
     local probe tests and Python compile check before QEMU."

     Action/result: `tests.test_logic_interpreter_probe` and `py_compile`
     passed.

889. Reported: "The local checks pass. I’m running the two previous-room cases
     in QEMU now."

     Action/result: QEMU batch `room_previous_001` matched 2/2 with 0 errors
     and 0 mismatches.

890. Reported: "Both previous-room cases matched QEMU. I’m updating the
     evidence generator and docs now so the room-switch section reflects
     `v0/v1/v2` as validated behavior, with the rest still source-backed."

     Action/result: Began promoting the current/previous-room evidence into
     docs.

891. Reported: "I’m going to regenerate the opcode evidence after adding the
     new case names, then fold the same result into the narrative docs."

     Action/result: Updated `tools/logic_opcode_evidence.py`.

892. Reported: "The evidence table is regenerated. I’m updating the
     room-switch prose and current-status page next."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

893. Reported: "I’m patching the docs now: `v1` moves from
     planned/source-backed to QEMU-validated, while resource replay and broader
     reset details remain next."

     Action/result: Updated `docs/src/logic_bytecode.md`,
     `docs/src/compatibility_testing.md`, and `docs/src/current_status.md`.

894. Reported: "The narrative docs are updated. I’m appending the clean-room
     note section for the `v1` validation run with the exact QEMU command and
     result."

     Action/result: Added the room current/previous variable QEMU validation
     section to `docs/src/clean_room_executable_notes.md`.

895. Reported: "I’ll proceed with the low-risk custom-logic path first: add the
     `0x13` variable-room versions of the four `v2` boundary selector tests.
     That gives us another clean behavioral brick before we reach for memory
     snapshots or patched instrumentation."

     Action/result: Started the variable-selected room boundary pass.

896. Reported: "I’m checking the committed baseline and the helper shape so I
     can add these as a small extension rather than duplicating the
     immediate-room boundary code."

     Action/result: Confirmed the working tree only had untracked generated
     directories and inspected room-switch helper definitions.

897. Reported: "The helper already takes an arbitrary switch action, so the
     change can stay tidy: parameterize the boundary case over immediate vs
     variable switch action, then add four `switch_room_v_boundary_*` cases."

     Action/result: Planned a small parameterization of `room_boundary_case`.

898. Reported: "I’m making `room_boundary_case` accept a switch action,
     defaulting to `0x12`, then using that for the four `0x13` variants."

     Action/result: Updated `room_boundary_case` to accept an optional
     caller-supplied switch action.

899. Reported: "The helper is parameterized. I’m inserting the four
     variable-room boundary cases next to the immediate boundary cases and
     using separate validation draw positions so mismatches are easy to
     identify."

     Action/result: Added four `switch_room_v_boundary_*` probe cases.

900. Reported: "The four `0x13` boundary cases are registered. I’m pinning them
     in the unit test list now."

     Action/result: Added unit assertions for the four variable-room boundary
     cases.

901. Reported: "I’m running the local probe tests and compile check before
     launching QEMU."

     Action/result: `tests.test_logic_interpreter_probe` and `py_compile`
     passed.

902. Reported: "Local checks pass. I’m running the four variable-room boundary
     cases under QEMU now."

     Action/result: Started QEMU batch `room_boundary_var_001`.

903. Reported: "The QEMU batch is running from one snapshot boot. It has built
     the fixtures and is executing the capture/compare loop now."

     Action/result: QEMU batch execution continued.

904. Reported: "All four variable-room boundary selectors matched. I’m
     updating the evidence table and docs now, then I’ll run the full
     validation suite."

     Action/result: QEMU batch `room_boundary_var_001` matched 4/4 with 0
     mismatches and 0 errors.

905. Reported: "First I’ll update the generated evidence source so `0x13`
     cites the boundary cases alongside the re-entry and previous-room cases,
     then regenerate the markdown."

     Action/result: Updated `tools/logic_opcode_evidence.py` and regenerated
     `docs/src/logic_opcode_evidence.md`.

906. Reported: "The evidence chapter is regenerated. I’m updating the
     room-switch prose, compatibility commands, current-status handoff,
     clean-room notes, and progress log."

     Action/result: Began docs updates for variable-room boundary validation.

907. Reported: "I’m patching those sections so they explicitly say both
     immediate and variable-selected room switches now share the same boundary
     behavior."

     Action/result: Updated `docs/src/logic_bytecode.md`,
     `docs/src/compatibility_testing.md`, and `docs/src/current_status.md`.

908. Reported: "I’m appending a clean-room note section for this run: exact
     command, matched result, and the fact that it completes the `v2` selector
     coverage for `0x13`."

     Action/result: Added the variable-room entry-boundary selector QEMU
     validation section to `docs/src/clean_room_executable_notes.md`.

909. Reported: "I’ll continue with room-switch object reset behavior using the
     unmodified interpreter first. I’m going to make a fixture where a
     persistent object is visible before the switch, then verify the destination
     room does not retain that draw state."

     Action/result: Began a targeted room-switch persistent-object reset probe.

910. Reported: "I’m reading the current helper and comparison code so the new
     case fits the existing QEMU snapshot harness instead of inventing a new
     path."

     Action/result: Inspected logic probe helpers and expected-render
     comparison behavior.

911. Reported: "The comparator can already catch 'extra survivor' sprites,
     which is perfect for this. I’m adding two cases now: immediate switch and
     variable-selected switch, both with a pre-switch active object."

     Action/result: Planned paired `0x12` and `0x13` object-reset fixtures.

912. Reported: "The object-reset fixture builder is in. It loads view 11,
     activates object 10 before the room switch, then expects only the
     destination-room validation sprite afterward."

     Action/result: Added `room_pre_switch_logic0_code` and
     `room_pre_switch_object_reset_case` to `tools/logic_interpreter_probe.py`.

913. Reported: "The cases are registered and the unit expectations know about
     them. I’m running the quick local tests and compile check before starting
     QEMU."

     Action/result: Added
     `switch_room_removes_preexisting_persistent_object` and
     `switch_room_v_removes_preexisting_persistent_object` plus unit coverage.

914. Reported: "Oops, I just noticed the plan still says the local checks are
     running; they actually passed. I’m correcting that and moving on to the
     QEMU validation."

     Action/result: Quick local unit test and `py_compile` checks passed.

915. Reported: "Local checks pass. I’m launching the two-case snapshot batch
     now; if the pre-switch object survives into room 1, the rendered output
     should mismatch as an extra sprite."

     Action/result: Started QEMU batch `room_object_reset_001`.

916. Reported: "Both object-reset cases matched. That validates the visible
     effect: an active persistent object from before the room switch is absent
     in the destination render for both `0x12` and `0x13`. I’m documenting that
     carefully as an observable rendering result, not a complete proof of every
     object-table field reset."

     Action/result: QEMU batch `room_object_reset_001` matched 2/2 with 0
     mismatches and 0 errors.

917. Reported: "I’ll add the two new case names to the generated opcode
     evidence, then regenerate the markdown so the action tables point to the
     new proof."

     Action/result: Updated `tools/logic_opcode_evidence.py` evidence rows for
     actions `0x12` and `0x13`.

918. Reported: "The evidence table is regenerated. I’m updating the
     higher-level bytecode notes, compatibility testing chapter, and current
     status with the precise scope of this result."

     Action/result: Regenerated `docs/src/logic_opcode_evidence.md` and began
     documentation updates.

919. Reported: "I’m updating these sections to add the 'persistent object
     removed' observable behavior without overstating it as a full object-field
     memory reset."

     Action/result: Updated `docs/src/logic_bytecode.md`,
     `docs/src/compatibility_testing.md`, and `docs/src/current_status.md`.

920. Reported: "Now I’ll add the new QEMU command and matched result into the
     compatibility chapter so the fixture can be rerun later."

     Action/result: Added the `room_object_reset_001` command and result to
     `docs/src/compatibility_testing.md`.

921. Reported: "I’m updating current status with the new observable and the
     remaining uncertainty around broader room-switch resource/object reset
     internals."

     Action/result: Refined `docs/src/current_status.md` room-lifecycle status.

922. Reported: "I’m appending the clean-room notes for this object-reset probe:
     the fixture shape, command, matched result, and the boundary of what it
     proves."

     Action/result: Added the room-switch persistent-object reset QEMU
     validation section to `docs/src/clean_room_executable_notes.md`.

923. Reported: "I’ll pick this back up at the object-reset documentation point
     and then run the full local checks. The useful result we already have is a
     small but solid one: pre-switch active object drawing does not visibly
     survive either immediate or variable room switches."

     Action/result: Resumed from the room-switch object-reset documentation
     handoff.

924. Reported: "The repo is exactly where the handoff said it was:
     variable-room boundary notes are already in place, and the object-reset
     result still needs its clean-room trail. I’m adding that trail now,
     including the QEMU command and the narrower interpretation of what the
     fixture proves."

     Action/result: Confirmed dirty files and appended the object-reset
     clean-room evidence section.

925. Reported: "That note is now in the executable log. Next I’m preserving the
     user-facing step log, then I’ll validate the code, generated evidence, and
     mdBook together so the docs don’t drift from the probes."

     Action/result: Added progress entries for the object-reset probe work.

926. Reported: "The historical log is caught up through this run. I’m running
     the usual verification set now: unit tests, mdBook build, and whitespace
     checks."

     Action/result: Ran `python3 -B -m unittest discover -s tests`,
     `mdbook build docs`, and `git diff --check`; all passed.

927. Reported: "All three checks are green. I’m cleaning up the generated
     Python cache and then I’ll take one last status/diff snapshot so I can give
     you a clean handoff."

     Action/result: Removed `tools/__pycache__` and checked status/stat output.

928. Reported: "The object-reset probe is validated and documented, so I’m
     going to keep moving rather than stop there. Next I’ll go back to the
     disassembly first and try to pin down which room-switch helper
     clears/initializes object state, then I’ll only use QEMU if there’s a
     specific observable to confirm."

     Action/result: Shifted from QEMU fixture work back to source-first
     disassembly analysis of room-switch reset helpers.

929. Reported: "I’ve got the current handoff notes in view. The next useful
     static target is `code.room.switch_state` at image `0x1792` and the dynamic
     reset helper at `0x1485`, because those are where the room switch seems to
     fan into object/resource cleanup."

     Action/result: Re-read current status and symbolic labels; searched for
     room-switch/reset references.

930. Reported: "One trap popped up in the search output: the whole-file
     disassembly includes the MZ header, so its printed offsets are not the same
     as the project’s image offsets. I’m using the focused `ndisasm -o
     image_offset -e image_offset+0x200` form now, which is the reliable one
     we’ve been documenting."

     Action/result: Rejected misleading whole-file offset readings and used
     focused image-offset disassembly.

931. Reported: "The room-switch body gives a very concrete object-record reset
     loop: it walks every 0x2b-byte object record and clears only selected
     fields/bits, while seeding several timing bytes to 1. I’m checking the
     adjacent helpers now so I can name the calls around that loop instead of
     leaving them as raw addresses."

     Action/result: Identified the room-switch object loop at `0x17b6..0x17e5`
     and inspected helpers around `0x10d0`, `0x30d6`, `0x4482`, and `0x4c23`.

932. Reported: "The static pass found a correction worth making: earlier prose
     says the room switch clears object bytes `+0x1e`, `+0x1f`, and `+0x20`,
     but the instructions keep `AL = 1` and store `1` into those three bytes.
     That matters for a portable spec, so I’m going to fix the docs and label
     the cache-reset helpers while I’m here."

     Action/result: Determined that room switch seeds object step/frame-timer
     bytes to `1` rather than clearing them.

933. Reported: "The object field map confirms those three bytes are step size
     and frame-timer reload/current counters. I’m checking whether there’s an
     existing bytecode getter we can use for a small QEMU confirmation, but the
     spec correction itself already comes straight from the room-switch
     instruction sequence."

     Action/result: Re-read object field documentation and opcode getter
     coverage; no direct bytecode getter exists for all three reset bytes.

934. Reported: "There’s a second correction in the same static pass: room
     switching does not wipe the whole logic cache root. The helper at `0x10f7`
     preserves the first logic cache record and unlinks later records, while
     separate helpers clear the view, picture, and sound cache roots."

     Action/result: Mapped helper `0x10d0`: `0x10f7` truncates the logic cache
     to its head, while `0x396d`, `0x50cc`, and `0x49dc` clear view, sound, and
     picture cache roots.

935. Reported: "I’m going to make this as a source-backed correction rather
     than invent a new behavioral claim: exact object bytes from
     `0x17b6..0x17e5`, exact cache reset calls from `0x10d0`, and the QEMU
     result only for the visible persistent-object disappearance."

     Action/result: Updated `docs/src/logic_bytecode.md` with the corrected
     object-reset and cache-reset source model.

936. Reported: "The bytecode chapter now reflects the corrected reset bytes and
     cache behavior. I’m adding the same source-backed cache distinction to the
     logic-resource chapter so future work doesn’t accidentally rebuild the
     older 'clear everything' model."

     Action/result: Added a room-switch cache reset section to
     `docs/src/logic_resources.md`.

937. Reported: "I’m assigning symbolic names for the newly clarified helpers,
     since these are exactly the kinds of routines that should carry across
     later interpreter builds even when addresses move."

     Action/result: Updated `docs/src/symbolic_labels.md` with labels for the
     logic-cache truncation helper, room-cache reset helper, cache-root clear
     helpers, input reset helper, and cache-root globals.

938. Reported: "The symbolic map is updated. I’m threading the correction into
     the status handoff now, so a later session starts from the refined source
     model instead of the older shorthand."

     Action/result: Updated `docs/src/current_status.md` with the corrected
     room-switch reset model.

939. Reported: "Before I write the clean-room note, I’m rerunning the key
     disassembly slices in short form. That gives the documentation a tidy
     command trail instead of relying on the oversized exploratory dumps."

     Action/result: Reran compact `ndisasm` slices for room-switch object reset,
     room cache reset, view/picture/sound cache root clear helpers, and input
     reset.

940. Reported: "The compact slices confirm the correction cleanly. I’m
     appending the source-pass note now: what changed, what commands support it,
     and what remains dynamic/QEMU-backed versus source-backed."

     Action/result: Added the room-switch object/cache reset source-correction
     section to `docs/src/clean_room_executable_notes.md`.

941. Reported: "Verification is green again. I’m doing one last scan for the
     old incorrect wording and then I’ll summarize where we landed."

     Action/result: Ran the final test/book/whitespace verification set; an
     initial wording-scan command failed because shell backticks in the search
     string were not quoted safely.

942. Reported: "That last scan command tripped over shell backticks in the
     search string, not over the repo. I’m rerunning the wording scan with safer
     quoting."

     Action/result: Reran the wording scan and found one older historical
     clean-room note that still said the room switch clears the logic cache
     root.

943. Reported: "The scan found one old historical note still saying 'clears the
     logic cache root.' Since that sentence is now known to be inaccurate, I’m
     correcting it in place and leaving the new source-correction section as the
     evidence trail for why."

     Action/result: Corrected the older clean-room note to say room switching
     resets caches through `0x10d0`, with the later correction identifying that
     it preserves the first logic cache record and clears view, sound, and
     picture cache roots.

944. Reported: "I’ll rerun the wording scan and the lightweight checks after
     that correction."

     Action/result: Reran the wording scan, `mdbook build docs`, and
     `git diff --check`. The checks passed; the only remaining scan hit is the
     intentional correction sentence describing the old wording.

945. Reported: "I’ll pick up the source-first thread: event/resource recording
     and restore replay, then connect it back to the logic opcodes and docs.
     I’ll keep QEMU on the shelf unless the disassembly leaves a behavior
     ambiguous enough to merit a probe."

     Action/result: Started a source-first pass over the resource-event
     recorder and restore replay path, using existing docs and disassembly
     rather than new QEMU probes.

946. Reported: "The event recorder shape is already clearer from the
     disassembly: it is a compact two-byte pair log, gated by both a
     recording-enable word and flag 7. I’m now chasing every call site so the
     docs tie the bytecode actions to the replayable resource events instead
     of treating the event buffer as a side note."

     Action/result: Disassembled `0x705e..0x714c` and the event call sites,
     mapping the pair buffer base/write/read/count globals, capacity, high-water
     word, recording gates, and all direct `code.event.record_pair` callers.

947. Reported: "One useful connection dropped out: event kind `5` is not a
     normal resource load at all. It records a four-pair packet for a
     temporary/display object path at `0x2d52`, then restore consumes the next
     three pairs as parameters before replaying that display operation."

     Action/result: Mapped restore replay dispatch at `0x681c` and helper
     `0x2d52`, identifying event kinds `0..8` and the special kind-5 transient
     object/display packet format.

948. Reported: "There is also a nice negative rule in the source: the
     view-resource text/display helper disables event recording while it loads
     and later discards a temporary view. So the replay log is intentionally
     about persistent room state, not every internal resource touch."

     Action/result: Disassembled `0x5edb`, confirming that actions `0x81` and
     `0xa2` disable event recording around their temporary load/display/discard
     sequence and re-enable recording before returning.

949. Reported: "I’m going to update the docs now: symbolic labels first, then
     the bytecode chapter’s higher-level resource-event model, then the
     chronological evidence log and status handoff. The edits are
     documentation-only; no generated artifacts should need to be committed."

     Action/result: Added symbolic code/data labels for the event recorder,
     replay cursors, action handlers, transient-display object helper, and
     temporary view-resource display helper.

950. Reported: "The bytecode chapter now has the high-level replay model in
     spec language: pair format, capacity/gates, event-kind meanings, and the
     special four-pair transient-object packet. I’m adding the clean-room
     command trail next so the claim remains auditable."

     Action/result: Updated `docs/src/logic_bytecode.md` with the replay-log
     model and appended this source-pass evidence trail to
     `docs/src/clean_room_executable_notes.md`.

951. Reported: "A source detail worth tightening before verification: restore
     replay disables event recording, and the replay routine itself does not
     show a matching re-enable call in the slice I read. I’m checking the
     caller path so the docs don’t overstate that lifecycle."

     Action/result: Disassembled the restore action caller, the save action
     for surrounding context, and all observed calls to `0x705e`, `0x706d`, and
     `0x681c`.

952. Reported: "The caller check confirms it: the only `0x706d` calls in the
     executable are room switch and the temporary view-display helper. Restore
     replay and display-mode rebuild call `0x681c`, which disables recording,
     and I don’t see a re-enable on those paths. That’s odd enough to document
     carefully rather than smooth over."

     Action/result: Corrected the replay documentation and symbolic label so
     they no longer imply automatic recording re-enable after restore replay.

953. Reported: "I’ve corrected the docs so they don’t imply replay turns
     recording back on. The current model is more honest: replay disables
     recording, duplicate prevention is clear, but the later lifecycle needs a
     targeted dynamic check or more source context."

     Action/result: Added the no-observed-re-enable finding to
     `docs/src/clean_room_executable_notes.md`, `docs/src/logic_bytecode.md`,
     `docs/src/symbolic_labels.md`, and `docs/src/current_status.md`.

954. Reported: "I'll take those in order: first settle the replay recording
     gate from source, then map the save/restore data it depends on, then add
     only the QEMU validation that gives us new confidence. I'll keep the docs
     updated as I go, since this is exactly the sort of trail future us will be
     grateful for."

     Action/result: Began a follow-up source-first pass over the replay log,
     save/restore blocks, and display-mode replay path.

955. Reported: "The first source pass is already showing a deeper wrinkle: the
     replay log's active count appears to be carried through the save/restore
     block around `[0x05e1]`, but replay itself reads `[0x0143]`. I'm tracing
     that carefully now, because it affects whether `0xab`/`0xac` are just
     script rollback helpers or part of the save/restore contract."

     Action/result: Re-examined the save/read block helpers and the memory
     ranges passed by the save and restore action handlers.

956. Reported: "One of those disassembly slices was shifted by the EXE header
     offset, so I'm rerunning the save/read helper slices with the correct
     `image offset + 0x200` file skip. This is exactly why keeping the command
     trail matters; the wrong slice was plausible-looking but not the helper we
     needed."

     Action/result: Corrected the image/file-offset relationship used for the
     whole-file disassembly and reran the relevant save/restore slices.

957. Reported: "The save-block dependency is now clearer: the first
     length-prefixed save block is not a tiny `[0x05e1]` block. It writes
     `0x05e1` bytes starting at `DS:0x0002`, which includes the pair count at
     `[0x0143]` and capacity at `[0x0141]`. The actual pair bytes are a later
     block from `[0x1707]`, and the recording gate `[0x170d]` is not in
     either."

     Action/result: Confirmed that save/restore persist replay capacity and
     active pair count in the first state block, persist pair bytes in a
     separate block, and do not persist the recording-enabled gate there.

958. Reported: "For dynamic validation, a full save/restore UI probe would be
     useful but expensive and brittle. A better first target is action `0x8c`:
     it calls the same replay routine without involving the save selector UI.
     If we can build a room-switch fixture that records events and then
     triggers `0x8c`, we get a replay validation path with much less
     machinery."

     Action/result: Chose display-mode replay as the first QEMU validation
     target because it reaches the same replay helper while avoiding the
     save-slot UI.

959. Reported: "I'll make the replay probe use the existing logic harness
     rather than a new tool. It can already patch `AGIDATA.OVL`, so if needed I
     can force the display-mode guard values for this fixture without changing
     the original DOS image."

     Action/result: Extended the logic snapshot harness to support per-case
     launch commands, needed for `SIERRA -p -c`, and added monitor key mapping
     for `-`.

960. Reported: "For the `0x8c` replay fixture, I want the guard to actually
     enter the replay branch. The source says it requires display hardware word
     `[0x112e] == 0` and mode word `[0x1130]` not `2` or `3`, so I'm checking
     whether our fixture overlay starts that way or whether we need a small
     `AGIDATA.OVL` patch."

     Action/result: Checked `SQ2/AGIDATA.OVL`; the words at `0x112e` and
     `0x1130` initialize to `0xffff`, so the QEMU fixture patches both words
     to zero and launches with `SIERRA -p -c`.

961. Reported: "I'm picking the replay thread back up from the source-first
     angle: finish the save/restore dependency map, add the least brittle
     dynamic check, then fold it back into the spec. I'll also preserve these
     working updates in the progress log before I make new substantive edits."

     Action/result: Reviewed current docs, harness state, and diffs before
     continuing the replay probe.

962. Reported: "The replay harness change is in place, and the regular unit
     suite passes. The first QEMU run is interesting in exactly the useful way:
     the engine reaches the display-mode replay fixture, but the visible
     background is still the second picture. I'm going back to source and
     memory state before assuming the replay model is wrong."

     Action/result: Initial QEMU display-mode replay probe produced a
     screenshot mismatch against the first-picture hypothesis, while confirming
     the fixture reached the expected visual state after `0x8c`.

963. Reported: "I'm adding a second replay case that uses flag 7 instead of
     `0xab`/`0xac`. If the source model is right, both should exclude the
     second picture from the event log; if the screen still shows the second
     picture, the missing piece is in display refresh rather than the log
     gates."

     Action/result: Added `display_mode_replay_skips_flag7_unrecorded_picture`
     beside the `0xab`/`0xac` rollback case.

964. Reported: "Both replay probes show the same visible result: the
     second-picture background remains. That narrows it nicely: either `0x8c`
     is not taking the replay branch under this launch mode, or the replay
     branch rebuilds resource state without clearing the currently visible CGA
     buffer. I’m checking memory around `[0x112e]`, `[0x1130]`, and the event
     buffer next."

     Action/result: Switched from screenshot comparison to a direct QEMU memory
     probe of display-mode words and replay-log state.

965. Reported: "The QEMU memory probe found the branch did execute: `[0x1130]`
     changed from 0 to 1 after `0x8c`. The event log also excludes the
     flag-7 picture as expected. So the surprising part is display-buffer
     behavior, not the replay-pair gate."

     Action/result: With `DS = 0x16a5`, reads showed `[0x112e] = 0`,
     `[0x1130] = 1`, capacity `0x32`, pair count `8`, and recording enabled
     again after the later script action.

966. Reported: "The pair buffer is wonderfully concrete: it has room-switch
     logic 1, picture 0 load/prepare, view 11 load, and the final transient
     object packet. No picture 1 event is present. I’m capturing one fresh
     screenshot from the same paused VM so we can tie the memory evidence to
     the visible mismatch."

     Action/result: Decoded the pair buffer as `(0,1)`, `(2,0)`, `(4,0)`,
     `(1,11)`, `(5,0)`, `(11,0)`, `(0,50)`, `(80,255)` and captured the same
     visible background as the earlier automated run.

967. Reported: "Fresh capture from the memory-probed VM has the same result:
     the log excludes picture 1, `0x8c` toggled display mode, but the screen
     still shows picture 1's color. I'm going to change the automated cases so
     they validate the observed screen behavior, while documenting the memory
     probe as the stronger evidence for replay-log semantics."

     Action/result: Updated the replay fixture expectations to compare against
     the visible second-picture background instead of the initial
     first-picture hypothesis.

968. Reported: "I'll pick this back up from the replay work and keep it
     source-first. I'm going to check the current diffs and the doc spots that
     need to be brought into line with the QEMU memory probe before I edit
     anything."

     Action/result: Reviewed the working tree, replay-related docs, and the
     code/test diffs for the launch-command and replay-fixture changes.

969. Reported: "The current tree has the replay probe code changes, but the
     docs still contain the earlier `no re-enable observed` wording. I also
     found the new progress section inserted into an old fuzz section; I’ll
     move that history to the chronological tail so the log stays readable."

     Action/result: Identified the stale replay lifecycle language and the
     misplaced progress section.

970. Reported: "I’m going to patch the docs in one pass: correct the replay
     lifecycle wording, add the memory-probe evidence, connect kind-4/kind-5
     replay back to graphics/object rendering, and move the misplaced progress
     section to the end with the new updates appended."

     Action/result: Started the documentation patch pass.

971. Reported: "I’m editing now. First pass is housekeeping: remove the replay
     section from the middle of the older fuzz chronology and append it after
     the current logic-interpreter entries with the newer replay-memory
     findings."

     Action/result: Removed the misplaced replay progress section from the
     synthetic picture fuzz chronology.

972. Reported: "That misplaced section is out of the fuzz chapter now. I’ll
     append it at the chronological end, keeping the earlier updates and the
     fresh observations together so the evidence trail reads in order."

     Action/result: Appended the replay follow-up progress entries here.

973. Reported: "The progress log now has the replay work in the right
     chronological spot. Next I’m tightening the spec language so it says what
     we actually know: replay-pair duplicate suppression is confirmed, but the
     later recording lifecycle and visible buffer behavior have sharper
     caveats."

     Action/result: Updated the replay model in `logic_bytecode.md`,
     `current_status.md`, and `symbolic_labels.md`.

974. Reported: "The compatibility chapter now separates the screen assertion
     from the memory-backed replay semantics. I’ll add the
     graphics/object pipeline connection next, since replay kind 4 and kind 5
     are where the resource log actually turns back into drawn pixels."

     Action/result: Linked replay event kinds `4`, `5`, and `8` to picture
     decode, overlay decode, and transient-object drawing in
     `graphics_object_pipeline.md`.

975. Reported: "The clean-room notes now have the corrected save layout and the
     QEMU memory probe. I’m going to scan for stale replay wording before
     running the executable checks."

     Action/result: Appended the save-block correction, static
     recording-gate scan, and display-mode memory probe to
     `clean_room_executable_notes.md`.

976. Reported: "The first wording scan accidentally let shell backticks run as
     commands, so that result is just a quoting miss. I’m rerunning it with
     single quotes and then I’ll move into tests."

     Action/result: Reran the scan safely; only intentional current caveats and
     historical correction wording remained.

977. Reported: "The unit suite is green and the whitespace check is clean. I’m
     running the two replay fixtures against the original engine now; this is
     the slowest check because it boots QEMU and captures the screenshots."

     Action/result: `python3 -B -m unittest discover -s tests` passed with
     99 tests, `git diff --check` passed, and the first QEMU replay batch
     started.

978. Reported: "The first replay fixture still mismatched, so I’m not going to
     paper over it. I’ll inspect the generated report and capture comparison to
     see whether the expected B background is mapped differently in this launch
     mode, or whether the local expected picture setup is still not matching
     the original screen."

     Action/result: The generated report showed the capture and expectation
     were not a plain first-picture or plain second-picture match.

979. Reported: "I misread the tuple direction from the report. In this harness,
     samples are `(x, y, captured, expected)`: QEMU is showing nibble 6 and the
     new expected payload is nibble 4. I’m checking the old manual capture and
     an A-vs-B local comparison now, because the fixture should follow the
     evidence rather than my earlier shorthand."

     Action/result: Compared the capture against both single-picture
     expectations and confirmed neither matched.

980. Reported: "Neither plain A nor plain B matches: row 0 looks like nibble 6,
     while row 1 and onward show nibble 4 in the sample set. That points to the
     display-mode toggle changing the screen interpretation or row mapping. I’m
     sampling the downsampled capture by row before changing the fixture
     expectation."

     Action/result: Downsampled row sampling showed an alternating pattern:
     even rows are nibble `6`, odd rows are nibble `4`.

981. Reported: "The capture is an alternating-row display: even logical rows
     are nibble 6, odd rows nibble 4. I’m changing the replay fixtures to
     expect that interleaved background, which matches the actual display-mode
     effect better than either single-picture hypothesis."

     Action/result: Added `alternating_row_picture_payload()` and changed both
     replay cases to use it as the expected background.

982. Reported: "The remaining 62 pixels are the validation sprite, not the
     replay background. Since these cases are about display-mode replay, I’m
     going to make them background-only instead of mixing in object-color
     behavior from the toggled display mode. The separate memory probe already
     covers the replay log."

     Action/result: Added `compare_view=False`, skipped the post-replay
     validation sprite in both replay fixtures, and taught `compare_capture()`
     to compare background-only cases.

983. Reported: "The current spec pages now say `row-interleaved` and note that
     the automated comparison is background-only. I’m correcting the clean-room
     note’s result wording too."

     Action/result: Replaced the earlier second-picture shorthand in current
     docs with the row-interleaved display observation.

984. Reported: "Unit tests are green at 100 tests and whitespace is clean. I’m
     rerunning the replay QEMU batch with the background-only row-interleaved
     expectation."

     Action/result: The corrected unit suite passed with 100 tests, and the
     replay QEMU batch was rerun.

985. Reported: "The first replay case now matches. QEMU is still running the
     second case from the same snapshot, so I’ll let it finish and then inspect
     the report."

     Action/result: Both replay cases matched QEMU with 2 matches,
     0 mismatches, and 0 errors.

986. Reported: "Both corrected replay cases match QEMU now. I’m recording that
     result in the compatibility and clean-room notes, then I’ll run mdBook."

     Action/result: Added the passing
     `build/logic-interpreter-probes/batches/replay_visible_001.json` result to
     `compatibility_testing.md` and `clean_room_executable_notes.md`.

987. Reported: "The compatibility chapter has the passing replay-batch result.
     I’m adding the same outcome to the clean-room entry beside the harness
     changes."

     Action/result: Completed the clean-room result note for the corrected
     replay batch.

988. Reported: "Clean-room notes have the successful batch result. I’m
     appending the latest working updates to the progress log so the failed
     hypothesis and correction are preserved rather than erased."

     Action/result: Added progress entries for the single-picture mismatch,
     row-interleaving discovery, background-only harness correction, and QEMU
     replay success.

989. Reported: "The progress log now records the failed single-picture
     hypothesis, the row-interleaving discovery, and the passing QEMU rerun.
     I’m building the mdBook now."

     Action/result: `mdbook build docs` succeeded and `git diff --check`
     passed.

990. Reported: "mdBook builds cleanly and whitespace is still clean. I’ll do
     one final wording scan and status check before wrapping this pass."

     Action/result: Checked replay wording, working-tree status, diff stat, and
     the corrected QEMU replay report.

991. Reported: "The final scan only finds historical progress-log text for the
     earlier working hypothesis plus the current row-interleaved wording. I’m
     logging the last verification steps, then I’ll rebuild mdBook once more
     because the progress log is itself a docs change."

     Action/result: Recorded this final progress-log update before the last
     docs build.

992. Reported: "That framing makes sense: I’ll treat the row-interleaving as a
     display-adapter/mode artifact, not as normative AGI semantics for the EGA
     path. I’m going source-first through the `0x8c` display refresh chain now,
     with QEMU only if the disassembly leaves a specific ambiguity worth
     checking."

     Action/result: Started a source-first pass over startup display-mode
     selection, `0x8c`, display refresh helpers, and graphics overlays.

993. Reported: "The source scan is already separating two things: the
     row-interleaving fixture deliberately forces hardware selector
     `[0x112e] == 0` and toggles mode `[0x1130]` from 0 to 1, which is not the
     normal full EGA path. I’m tracing where startup assigns EGA values and
     where the graphics overlay branches on those words."

     Action/result: Disassembled the command-line parser, display auto-detect,
     `0x8c`, cursor-save/restore helpers, and logical-buffer clear/display
     helpers.

994. Reported: "The static path is pretty telling: command-line `-c` sets
     `[0x1130]=0`, `-r` sets `[0x1130]=1`, and `-p` forces `[0x112e]=0`. The
     EGA-ish auto-detected/full-color path is elsewhere in startup and does not
     satisfy `0x8c`’s hardware guard, so I’m digging into the overlay entry
     that only runs for `[0x112e]==0`."

     Action/result: Disassembled the graphics overlay entry tables for EGA,
     CGA, VGA-like, and JR/Tandy-like overlays.

995. Reported: "There’s a better explanation than `old picture leaking
     through`: the CGA overlay’s color mapper returns two bytes in mode 1, so
     replaying recorded color 6 after `0x8c` can itself produce alternating
     visible colors. I’m checking the AGIDATA tables that the CGA overlay
     indexes now; that will tell us whether odd-row color 4 is actually the
     mode-1 mapping for color 6."

     Action/result: Inspected `AGIDATA.OVL:0x1d36` and confirmed the CGA
     overlay uses a three-byte-per-color table, with mode 1 returning a
     two-byte word.

996. Reported: "The CGA table backs that up: for `[0x112e]==0`, the color
     mapper indexes three bytes per color in `AGIDATA.OVL:0x1d36` and uses a
     two-byte mapping when `[0x1130]==1`. So the odd rows are more likely the
     recorded picture being redrawn under a different CGA mapping, not the
     unrecorded picture surviving. I’m checking the overlay selection code next
     so the docs can say why this is out of the EGA target path."

     Action/result: Confirmed from source that `0x5685` returns colors
     unchanged for non-CGA/EGA-target paths and delegates to the overlay mapper
     only for hardware selector `[0x112e] == 0` with modes other than `2` or
     `3`.

997. Reported: "The replay path also clears before drawing:
     `0x4acf -> 0x6445 -> 0x5257(0x4f4f)` resets the logical picture buffer,
     then decodes the recorded picture. That rules out a persistent
     unrecorded-picture buffer as the primary explanation. I’m updating the
     docs and labels to classify this as a CGA-only mode-toggle artifact,
     outside the EGA target semantics."

     Action/result: Updated the bytecode chapter, compatibility chapter,
     graphics pipeline, current status, harness descriptions, and symbolic
     labels to classify the row-interleaved fixture as CGA-only remapping.

998. Reported: "I’m making a small but important correction now: the fixture
     names still describe the event-log exclusion, but their descriptions and
     docs should say the visible rows come from CGA remapping of the replayed
     recorded picture, not from the second picture surviving."

     Action/result: Corrected the replay case descriptions in
     `tools/logic_interpreter_probe.py`.

999. Reported: "The bytecode and compatibility chapters now say this is
     CGA-only remapping, not replay leakage. I’ll add the source trail to the
     graphics pipeline chapter and symbolic labels."

     Action/result: Added the CGA color-map explanation to
     `graphics_object_pipeline.md`.

1000. Reported: "The graphics pipeline now explains the CGA mapper. I’m adding
      stable labels for the main color mapper, the CGA overlay mapper, and the
      data table so later interpreter-version comparisons can track this by
      role."

      Action/result: Added symbolic labels for `0x5685`, the CGA overlay
      mapper at near `0x9815`, and `AGIDATA.OVL:0x1d36`.

1001. Reported: "Symbolic labels are in. I’ll update the handoff status so the
      next session doesn’t treat the CGA row effect as an EGA compatibility
      requirement."

      Action/result: Updated `current_status.md` with the CGA-only/EGA-target
      distinction.

1002. Reported: "I’m adding the evidence trail now: startup flags, the `0x8c`
      guard, `0x5685`, CGA overlay `0x9815`, the `AGIDATA.OVL:0x1d36` color
      table, and the picture decode clear that rules out buffer leakage."

      Action/result: Appended the source-backed correction section to
      `clean_room_executable_notes.md`.

1003. Reported: "The clean-room notes now have the correction and command
      trail. I’m appending the progress-log entries for this turn, then I’ll
      run the normal checks."

      Action/result: Recorded this progress-log update before verification.

1004. Reported: "The documentation updates are in. I’ll scan for stale
      `unrecorded picture supplies odd rows` wording, then run tests, mdBook,
      and whitespace checks."

      Action/result: The stale-wording scan found only intended corrected
      wording and historical progress text. `python3 -B -m unittest discover
      -s tests` passed with 100 tests, `mdbook build docs` succeeded, and
      `git diff --check` passed.

1005. Reported: "The scan only finds the intended corrected wording and
      historical progress text. Tests, mdBook, and whitespace all passed; I’ll
      record that final verification in the progress log and do one last
      mdBook/whitespace pass because the log changed."

      Action/result: Recorded this final verification note before the last docs
      build.

1006. Reported: "I’ll take the recommended slice: source-first mapping of the
      event/replay/restore machinery, with QEMU only if the disassembly leaves
      a behavior question. I’ll update the historical progress log as I go so
      the trail stays intact."

      Action/result: Began the replay/restore source pass and checked current
      status, recent clean-room notes, labels, and git status.

1007. Reported: "The current docs already contain a decent first pass on event
      pairs, but there’s still a gap around exactly what save/restore writes
      back and where recording becomes enabled again. I’m narrowing onto those
      routines now, with the source addresses already named in the labels file."

      Action/result: Re-read the prior resource-event and save/restore notes
      plus the existing symbolic labels.

1008. Reported: "A useful correction is already staring at us: the save block
      explicitly excludes `data.event.recording_enabled`, and the static scan
      only found two enable calls. I’m going to re-read the raw routines around
      restore/replay and the callers, because the unresolved piece is probably
      not a hidden write but a control-flow path we haven’t named cleanly yet."

      Action/result: Re-disassembled the replay, event helper, restore, and
      display-toggle routines.

1009. Reported: "The disassembly confirms the replay routine starts by
      stopping/clearing runtime display state, disabling event recording, and
      then consuming the pair stream. The restore action then performs several
      display/menu refreshes after replay, but still no obvious re-enable in
      that immediate path. Next I’m checking the saved state helpers and the
      room-switch enable path so the spec can distinguish 'saved data' from
      'runtime-only gate.'"

      Action/result: Re-read logic-cache serialization, room-switch setup, and
      temporary view-resource display helpers.

1010. Reported: "Found the likely missing link. In the earlier replay
      disassembly, the jump table bytes caused `ndisasm` to misparse the
      instruction immediately after the table; if I start disassembly at the
      loop-exit target itself, the first instruction should be the re-enable
      call. I’m checking that precise target now before changing the docs."

      Action/result: Disassembled at image `0x6927` and confirmed `call
      0x706d`, the event-recording re-enable helper.

1011. Reported: "That resolves the dynamic/static mismatch: replay disables
      recording while rebuilding resources, then explicitly calls
      `code.event.enable_recording` at image `0x6927` after the replay-pair
      loop. The earlier static scan missed it because the jump table bytes
      swallowed the `E8 43 07` instruction when disassembled linearly."

      Action/result: Promoted the post-loop re-enable from hypothesis to
      source-backed behavior and updated the plan.

1012. Reported: "I’ve got enough to edit. The core change is not a new
      behavior, but a better source map: `0x681c` contains both the temporary
      recording disable and the post-loop re-enable at `0x6927`, with the
      event-kind jump table at `0x6915` sitting right before it."

      Action/result: Patched `logic_bytecode.md` with the corrected replay
      lifecycle.

1013. Reported: "The bytecode chapter now has the corrected replay lifecycle:
      disable during pair replay, re-enable at the post-table exit target, then
      rebuild visible state. Next I’m touching the labels and handoff docs so
      future cross-version work has the right anchors."

      Action/result: Updated symbolic labels for the re-enable helper, replay
      dispatch table, replay finish target, and replay entry.

1014. Reported: "Labels now include the replay jump table and the post-loop
      re-enable target. I’m updating the status/compatibility prose so the
      current project state no longer carries the older open question."

      Action/result: Updated `current_status.md`,
      `graphics_object_pipeline.md`, and `compatibility_testing.md`.

1015. Reported: "That patch missed because the status paragraph has slightly
      different wrapping. I’m reading that exact block and will patch it with
      the current text shape."

      Action/result: Re-read the status paragraph and applied the corrected
      patch.

1016. Reported: "The narrative docs now agree on the corrected replay gate
      lifecycle. I’m adding the evidence section to the chronological
      clean-room notes, including why the earlier scan failed."

      Action/result: Added the clean-room note section for the replay
      re-enable source correction.

1017. Reported: "The clean-room notes now preserve the command trail and the
      correction. I’m appending the matching progress-log entries for this
      turn, then I’ll scan for stale wording."

      Action/result: Recorded this progress-log batch before stale-wording
      scans and verification.

1018. Reported: "The stale scan found only the historical section that
      originally recorded the unresolved state. I’m going to annotate that old
      paragraph so readers immediately see it was corrected by the later source
      pass, while preserving the history."

      Action/result: Patched the earlier clean-room note to point to the
      `0x6927` correction instead of leaving a dangling unresolved statement.

1019. Reported: "That old note now points forward to the correction instead of
      leaving a dangling open question. I’ll rerun the stale-wording scan and
      then verification."

      Action/result: Reran the stale-wording scan and `git diff --check`; both
      were clean.

1020. Reported: "The stale scan is clean and whitespace checks pass. I’m
      running the mdBook build plus the local unit suite now; there were no
      decoder/parser code changes, but this is a useful sanity check after
      touching the spec around tests."

      Action/result: `mdbook build docs` succeeded and `python3 -B -m unittest
      discover -s tests` passed with 100 tests.

1021. Reported: "Both checks passed: mdBook built cleanly and the 100-test
      unittest suite is green. I’m recording that verification in the progress
      log, then I’ll rebuild once more because the log itself is part of the
      book."

      Action/result: Recorded this verification note before the final mdBook
      build.

1022. Reported: "Final verification pass is running now: mdBook after the
      progress-log update, plus a last whitespace/status check."

      Action/result: `mdbook build docs` and `git diff --check` passed; status
      showed only the intended modified docs plus the expected untracked
      `002962_ms_dos_622/` and `build/` directories.

1023. Reported: "The final build and whitespace pass are clean; only the
      intended docs are modified, with `build/` and the DOS images still
      untracked. I’m adding that last verification note to the log and doing
      one no-comment rebuild after it."

      Action/result: Recorded the final verification note before a no-comment
      mdBook rebuild.

1024. Reported: "I’ll build this as a living project dashboard rather than a
      throwaway checklist: opcode coverage plus broader engine areas, with
      explicit status labels and evidence pointers. I’ll read the current
      opcode docs/generator first so the names match what we already use."

      Action/result: Started the `PROGRESS.md` pass and checked the current
      git status, AGENTS instructions, and opcode evidence generator.

1025. Reported: "One search command tripped over unescaped backticks in the
      shell, so I’m ignoring that output and using the local opcode tables
      directly. The evidence generator imports the canonical `ACTION_NAMES` and
      `COND_NAMES`, which is exactly what we want for a no-drift progress file."

      Action/result: Used the local opcode-name and evidence tables from
      `tools/disassemble_logic.py` and `tools/logic_opcode_evidence.py`.

1026. Reported: "I’m going to generate the opcode checklist text from the
      existing clean-room tables rather than hand-copying 195 labels. That
      keeps `PROGRESS.md` aligned with `tools/disassemble_logic.py` and the
      evidence matrix."

      Action/result: Generated the action/condition opcode checklist from the
      local Python tables, writing only via `apply_patch`.

1027. Reported: "The generated checklist shows only a handful of opcode entries
      are still at dispatch-smoke or source-backed level; most action and
      condition rows have focused QEMU evidence. I’ll fold that into a broader
      dashboard so it’s useful for 'how close are we' at a glance, not just as
      an opcode dump."

      Action/result: Counted opcode evidence levels: 148 QEMU-validated action
      opcodes, one structural action opcode, 27 dispatch-smoke action opcodes,
      18 QEMU-validated condition opcodes, and one source-backed condition.

1028. Reported: "I’m creating `PROGRESS.md` now with a simple ASCII status
      legend: `[x]` for sufficiently specified/evidenced, `[~]` for partial or
      smoke/source-backed, and `[ ]` for not yet covered. The opcode section
      will stay compact, while the engine-area section will carry the real
      remaining-work list."

      Action/result: Added root `PROGRESS.md` with structural bytes, all action
      opcodes, all condition opcodes, subsystem coverage areas, and highest
      value remaining work.

1029. Reported: "`PROGRESS.md` is in place with all action opcodes, condition
      opcodes, structural bytes, and subsystem coverage areas. I’m updating
      `AGENTS.md` now so future work treats this as a maintained dashboard, not
      a one-time snapshot."

      Action/result: Updated `AGENTS.md` to require keeping `PROGRESS.md`
      aligned with opcode/status and subsystem progress.

1030. Reported: "The agent instructions now point future work at `PROGRESS.md`
      and define when it must be updated. I’m adding the corresponding
      progress-log entries, then I’ll run the book and whitespace checks."

      Action/result: Recorded this progress-log batch before validation.

1031. Reported: "Validation is running now. Since this is
      documentation/tracking rather than decoder code, the key checks are
      mdBook and whitespace; I’ll also run the existing unittest suite so we
      don’t unknowingly disturb the broader working set."

      Action/result: `mdbook build docs` succeeded, `git diff --check` passed,
      and `python3 -B -m unittest discover -s tests` passed with 100 tests.

1032. Reported: "All checks passed: mdBook, whitespace, and the 100-test
      suite. I’m recording that validation in the progress log and then doing
      one last mdBook/whitespace pass because the log changed."

      Action/result: Recorded the validation result before the final
      post-progress-log checks.

1033. Reported: "Final pass is just making sure the freshly updated progress
      log still renders cleanly and has no whitespace issues."

      Action/result: `mdbook build docs` and `git diff --check` passed. Status
      showed the expected modified docs and untracked `PROGRESS.md`, plus a
      generated `tools/__pycache__/` directory from the Python checks.

1034. Reported: "The final checks passed, and running the Python helpers left a
      generated `tools/__pycache__/` behind. I’m cleaning only that generated
      cache directory; the requested `PROGRESS.md` stays untracked until you
      decide whether to commit."

      Action/result: Removed generated `tools/__pycache__/`.

1035. Reported: "Cache cleanup is done. I’m recording the final
      verification/cleanup note and doing one last lightweight status/build
      check so the handoff is tidy."

      Action/result: Recorded the final cleanup note before the last status and
      mdBook checks.

1036. Reported: "I’ll treat this as a real work batch: first I’ll read the
      current tracker and harnesses, then I’ll promote only the opcode coverage
      that the probes or disassembly actually justify, add the raw-key
      condition probe, and update the docs/test suite as evidence lands."

      Action/result: Began the `Highest-Value Remaining Work` pass and set the
      active checklist for tracker, opcode, raw-key, graphics, state-machine,
      and verification work.

1037. Reported: "I’m reading the tracker and the probe/evidence scripts now so
      I can distinguish already-tested behavior from smoke coverage. That
      should keep the next edits from accidentally overstating what we know."

      Action/result: Read `PROGRESS.md`, `tools/logic_interpreter_probe.py`,
      `tests/test_logic_interpreter_probe.py`, and git status.

1038. Reported: "The tracker is current and the harness already has many cases;
      the fastest useful path is to add a raw-key condition case and promote
      only opcodes with existing behavior probes behind them. I’m narrowing in
      on the event/input helpers and the overlay cases now."

      Action/result: Searched the logic, picture, view, overlay, and docs
      harnesses for raw-key, dispatch-smoke, replay, sound, and graphics edge
      evidence.

1039. Reported: "I’m picking up exactly where the last pass left off: first I’m
      checking the existing opcode evidence mappings and the focused probe
      definitions so I can promote only things the disassembly/probes really
      support."

      Action/result: Re-read the relevant logic probe case definitions and
      opcode evidence maps.

1040. Reported: "The existing suite already has one strong replay case for
      `0xab`/`0xac`, and a sound completion case that observes the 0x63/0x64
      flag path rather than just 'it returned.' I’m checking the disassembly
      notes around the raw-key predicate before I add a probe for it."

      Action/result: Reviewed raw-event queue documentation, symbolic labels,
      and source-backed notes for condition `0x0d`.

1041. Reported: "The raw-key predicate is source-mapped well enough to make a
      tight test: it calls the raw event helper directly, so the probe should
      press a plain key and draw only after `0x0d` sees the nonzero low byte.
      Next I’m making that case and adding a couple of valid edge-render cases
      that are cheap to keep in the compatibility suite."

      Action/result: Identified the raw-key probe shape and the view/object
      edge cases to add.

1042. Reported: "I have enough context to edit now. I’m going to keep the code
      changes narrow: one raw-key condition helper/case, a small `--case`
      filter for the overlay batch so focused QEMU runs are practical, two clip
      cases, and then the evidence/docs tracker updates that tie those to the
      clean-room record."

      Action/result: Began code edits in the logic and object overlay probe
      harnesses.

1043. Reported: "Before editing, I also found that the overlay harness always
      ran its entire base set. I’m adding the same repeated `--case` filtering
      the logic harness already has, because it will make future
      original-engine graphics checks much faster and less noisy."

      Action/result: Added selected-case loading and CLI filtering to
      `tools/object_overlay_probe.py`.

1044. Reported: "One subtle evidence point: I’m not going to claim the whole
      sound system is specified. The existing `sound_stop_sets_completion_flag`
      case does validate the opcode-level contract for `load sound`, `start
      sound with completion flag`, and `stop sound sets that flag`, so I’ll
      promote those opcode rows while leaving audio playback semantics as
      partial."

      Action/result: Scoped the sound opcode promotion to load/start/stop
      completion-flag behavior only.

1045. Reported: "I’m applying the code edits now. After this I’ll run the
      focused raw-key probe under QEMU; if it matches, the last condition opcode
      can move from source-backed to QEMU-validated."

      Action/result: Added `raw_key_event_available_condition()` and the
      `raw_key_event_available_draws_after_typed_key` logic probe case.

1046. Reported: "The raw-key probe is in place. I’m adding the focused overlay
      filtering and the missing left/top clip cases next, so graphics
      compatibility can grow without needing a full 20-plus-case run every
      time."

      Action/result: Added focused overlay cases for left-edge and top-edge
      placement.

1047. Reported: "The overlay harness now has `--case`, matching the logic
      harness. I’m tightening the tests around those new IDs and the filter
      behavior before I do any emulator runs."

      Action/result: Added unit assertions for the raw-key case, overlay case
      IDs, overlay filtering, and top-edge expected-position override.

1048. Reported: "The logic test now tracks the new raw-key case. Next I’m
      adding overlay test assertions for left/top clipping and proving the new
      case filter keeps its ordering and rejects unknown IDs."

      Action/result: Completed overlay test updates.

1049. Reported: "The tests now cover the new fixture selectors. I’m updating
      the opcode evidence generator next so the docs and `PROGRESS.md` don’t
      drift from the actual harness cases."

      Action/result: Promoted `0x62`, `0x63`, `0xab`, `0xac`, and condition
      `0x0d` in `tools/logic_opcode_evidence.py`, pending dynamic validation of
      the new raw-key case.

1050. Reported: "The focused unit tests pass. I’m running the raw-key case in
      the original interpreter now; this is the piece that decides whether
      condition `0x0d` can be promoted rather than just source-described."

      Action/result: Ran
      `python3 -B tools/logic_interpreter_probe.py --dos-prefix RK ... --case raw_key_event_available_draws_after_typed_key`;
      it matched QEMU with 1 match and 0 mismatches.

1051. Reported: "The raw-key probe matched under QEMU: one typed `x` was enough
      for condition `0x0d` to trigger the validation draw, without any key
      mapping. I’m doing the small overlay clip run now so the new graphics
      cases have original-engine evidence too."

      Action/result: Started the two-case object overlay QEMU batch.

1052. Reported: "The overlay run hit the sandbox’s VNC socket restriction, the
      same one we’ve seen before. I’m rerunning the identical command with
      escalation so QEMU can bind its local VNC display."

      Action/result: The first overlay run failed with QEMU VNC bind permission
      error; the escalated rerun matched QEMU with 2 matches and 0 mismatches.

1053. Reported: "The clip batch matched both cases in the original interpreter.
      I’m regenerating the opcode evidence chapter now, then I’ll fold the new
      QEMU results into the spec, tracker, and progress log."

      Action/result: Ran `python3 -B tools/logic_opcode_evidence.py`.

1054. Reported: "The generated evidence matrix is current. I’m editing the
      human-readable chapters next: raw-key behavior, the promoted sound/replay
      opcodes, the graphics clip captures, and concise state machines for
      implementation work."

      Action/result: Began documentation updates across bytecode,
      compatibility, graphics, runtime model, clean-room notes, and tracker.

1055. Reported: "One small cleanup before documenting: the new left-edge
      fixture is really 'flush against the left edge,' not a negative-X clip,
      because script operands are bytes. I’m correcting that wording so the
      case name doesn’t smuggle in a false interpretation."

      Action/result: Corrected the `left_clip_view11_priority15` description.

1056. Reported: "I’m converting the results into implementation-facing docs
      now. The key change is to separate 'validated observable contract' from
      'everything about the subsystem': sound load/start/stop has opcode-level
      flag evidence, while actual playback/audio timing remains explicitly
      partial."

      Action/result: Updated `logic_bytecode.md` with raw-key, sound, and
      replay rollback evidence.

1057. Reported: "The bytecode chapter now records the raw-key match and the
      sound/replay promotions. I’m adding the graphics edge-capture notes and
      the state-machine summaries next."

      Action/result: Updated `graphics_object_pipeline.md` with the
      `clip_edges_001` result.

1058. Reported: "The graphics chapter now names the new clip batch. I’m putting
      the subsystem state machines in `runtime_model.md`, where future
      implementers or agents will naturally look for the language-neutral
      model."

      Action/result: Added resource lifecycle, object drawing lifecycle, and
      motion/animation state-machine tables to `runtime_model.md`.

1059. Reported: "The state-machine section is in place. I’m updating the
      compatibility chapter so the commands somebody reruns later include the
      new raw-key and overlay-filter cases, not just the older broad batches."

      Action/result: Updated `compatibility_testing.md` with raw-key,
      clip-edge, sound, and replay-rollback validation notes.

1060. Reported: "The compatibility docs now point at the focused replayable
      commands. I’m updating `PROGRESS.md` to reflect what actually moved: four
      action opcodes promoted, the final condition opcode validated, and the
      high-value list revised to the next frontier."

      Action/result: Updated opcode counts, condition status, subsystem
      evidence, and highest-value remaining work in `PROGRESS.md`.

1061. Reported: "`PROGRESS.md` is updated. I’m adding the clean-room evidence
      trail now, including the failed sandboxed QEMU attempt and the successful
      escalated rerun so the history stays reproducible."

      Action/result: Added the raw-key/edge-render evidence section to
      `docs/src/clean_room_executable_notes.md`.

1062. Reported: "The clean-room notes have the new command evidence. I’m
      appending the user-facing progress updates now, then I’ll run the full
      test and book checks."

      Action/result: Appended this progress-log batch before validation.

1063. Reported: "The documentation pass is complete. I’m running the full local
      suite, the generated evidence check, the mdBook build, and whitespace
      checks now."

      Action/result: Ran `python3 -B -m unittest discover -s tests`,
      `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
      and `git diff --check`.

1064. Reported: "All four checks passed: 102 unit tests, evidence matrix
      `--check`, mdBook, and `git diff --check`. I’m recording that validation
      in the progress log and then I’ll do a final lightweight status/whitespace
      check because the log changed."

      Action/result: Recorded the successful validation result before final
      status and whitespace checks.

1065. Reported: "Final mdBook and whitespace checks still pass after the
      validation log entry. I’m doing the last internal wrap-up now: marking the
      checklist complete and preparing the concise summary with the exact QEMU
      batches and checks that passed."

      Action/result: Final mdBook and whitespace checks had passed; the plan
      was marked complete before this final log correction.

1066. Reported: "I just sent one more status update, so I’m adding that to the
      progress log too before the final checks. Tiny bookkeeping, but it keeps
      the historical trail honest."

      Action/result: Added this final progress-log correction before rerunning
      final mdBook and whitespace checks.

1067. Reported: "I’ll commit the finished reverse-engineering batch now,
      staging only the tracked source/docs/test changes and leaving the
      generated `build/` and DOS installer images alone."

      Action/result: Began the requested commit pass and confirmed only tracked
      source/docs/test files would be staged.

1068. Reported: "I added the commit-prep update to the progress log, so the
      evidence trail still matches what you saw. I’m doing the quick
      doc/whitespace check for that tiny log change and then I’ll create the
      commit."

      Action/result: Added the final commit-prep progress note before
      re-running mdBook and whitespace checks.

1069. Reported: "I’ll take the next slice from `PROGRESS.md`: first I’ll read
      the current remaining-work list and partial opcode rows, then pick a
      source-backed target that can be turned into concrete probes or
      implementation-ready docs without overclaiming."

      Action/result: Started the next PROGRESS-driven work pass.

1070. Reported: "The tracker is pointing pretty clearly at text/input UI now:
      most remaining partial opcodes are in that cluster, and the current
      screenshot harness is weak for text-plane state. I’m checking the QEMU
      harness shape to see whether a small memory-observation probe would let
      us validate those globals directly instead of only 'it returned.'"

      Action/result: Read `PROGRESS.md`, QEMU snapshot helpers, text/input docs,
      and partial opcode evidence.

1071. Reported: "There’s one good quick win in the remaining list: `0xaa`
      copies the save-description buffer into a string slot, and we can validate
      it cleanly by patching only the fixture’s `AGIDATA.OVL` buffer to `look`
      and comparing it against a normal message-backed string slot. I’m going
      to add that probe, then use this same pass to add a text/input UI
      state-machine summary."

      Action/result: Selected an initial `0xaa` probe candidate and a
      text/input state-machine documentation target.

1072. Reported: "The `0xaa` case is nice because it exercises
      saved-state-adjacent behavior without needing a memory probe or BIOS text
      rendering. I’m making it a normal draw-if fixture so it can live in the
      reusable compatibility suite."

      Action/result: Added a provisional `0xaa` draw-if fixture and evidence
      mapping.

1073. Reported: "The new `0xaa` fixture and evidence mapping are in place. I’m
      running the focused unit test and regenerating the opcode matrix before
      booting QEMU for the new case."

      Action/result: Focused logic-probe tests passed and the opcode matrix was
      regenerated.

1074. Reported: "The focused test passes and the evidence matrix regenerated
      cleanly. I’m running the original-engine QEMU case now to check that
      `0xaa` really copies the patched save-description buffer into the script
      string slot."

      Action/result: Ran the provisional `0xaa` QEMU fixture; it mismatched.

1075. Reported: "The first `0xaa` run did not match, so I’m treating that as
      useful evidence rather than forcing the promotion. I’m going back to the
      disassembled handler and the generated fixture bytes to find whether the
      source buffer address, slot operand, or string terminator assumption is
      off."

      Action/result: Inspected the QEMU report, generated `AGIDATA.OVL` bytes
      around `0x0e72`, and the `0xaa` handler disassembly.

1076. Reported: "That mismatch is actually informative: the validation view
      did not draw, so the runtime `0x0e72` buffer was not equal to the patched
      file bytes by the time the script ran. I’m not going to promote `0xaa` on
      that. I’m looking for another remaining opcode whose state change can be
      observed through existing object or logic behavior, and I’ll either pivot
      or keep this as an attempted-but-not-promoted note."

      Action/result: Removed the `0xaa` promotion plan and searched for a
      better visible-state target among remaining partial opcodes.

1077. Reported: "I’m pivoting to `0x84` instead: the handler’s source says it
      clears object 0’s motion mode, and the movement harness already has a
      clean random-motion stop oracle for the sibling `0x4e`. I’ll add a
      parallel movement case for `0x84`, and remove the unpromoted `0xaa`
      fixture from the reusable base set."

      Action/result: Removed the provisional `0xaa` base case/evidence and
      added the `0x84` movement-probe plan.

1078. Reported: "The helper insert missed the exact location because the action
      helpers are packed a little differently than I remembered. I’m locating
      that block and applying the small helper patch against the actual file
      shape."

      Action/result: Located the object-action helper block in
      `tools/qemu_fixture.py`.

1079. Reported: "Found it. I’m inserting the `0x84` helper alongside the nearby
      object-motion helpers now."

      Action/result: Added
      `set_global_0139_and_clear_object0_field_22_action()`.

1080. Reported: "The movement case is added. It starts random motion on object
      0, immediately runs action `0x84`, and expects the object to remain at
      its starting position, matching the source claim that `0x84` clears
      object 0’s motion byte."

      Action/result: Added
      `action_84_after_random_motion_stops_motion` to the movement harness and
      tests.

1081. Reported: "Local tests pass for the movement and fixture changes, and the
      evidence chapter is regenerated. I’m running the focused QEMU movement
      case now; this should either promote `0x84` or give us another boundary
      note."

      Action/result: Focused movement/logic/fixture tests passed and the
      `0x84` QEMU batch started.

1082. Reported: "The `0x84` QEMU case matched, so that one can move from
      dispatch-smoke to behavior evidence. I’m updating the docs/tracker now,
      and I’ll record the `0xaa` attempt as deliberately not promoted because
      the runtime buffer did not retain the fixture-file patch."

      Action/result: QEMU batch `action_84_motion_001` matched with 1 match and
      0 mismatches.

1083. Reported: "I’m updating the human docs around `0x84` in three places: the
      opcode chapter, the movement compatibility commands, and the runtime
      model. The key wording is that QEMU validates the object-0 motion-byte
      effect; the broader `[0x0139]` role remains source-backed."

      Action/result: Updated `logic_bytecode.md` and
      `graphics_object_pipeline.md` for the `0x84` movement effect.

1084. Reported: "I found the compatibility movement section; I’ll add `0x84`
      beside the existing `0x4e` single-case stop probe because they share the
      same observable motion-byte contract."

      Action/result: Added the `action_84_motion_001` command and result to
      `compatibility_testing.md`.

1085. Reported: "`PROGRESS.md` now reflects the one-opcode promotion. I’m also
      adding the failed `0xaa` experiment to the 'attempted but not promoted'
      record, because it tells future us not to assume file-patching that buffer
      is enough."

      Action/result: Updated action coverage to 154 of 176 and recorded the
      unpromoted `0xaa` probe in compatibility docs.

1086. Reported: "The compatibility docs now keep the failed `0xaa` probe out of
      the registry while preserving why it failed. I’m appending the clean-room
      command/results section next."

      Action/result: Added the clean-room notes section for the `0xaa` attempt,
      `0x84` movement probe, and text/input lifecycle model.

1087. Reported: "The clean-room notes have the new command trail. I’m adding
      this turn’s progress updates to `progress_log.md`, then I’ll run the full
      test/book checks."

      Action/result: Appended this progress-log batch before validation.

1088. Reported: "The progress log is caught up. I’m running the full unit
      suite, evidence-matrix check, mdBook build, and whitespace check now."

      Action/result: Ran `python3 -B -m unittest discover -s tests`,
      `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
      and `git diff --check`.

1089. Reported: "All four validations passed: 102 tests, opcode evidence
      `--check`, mdBook, and whitespace. I’m recording that result in the
      progress log, then I’ll do the final status/diff pass."

      Action/result: Recorded the validation result before final status and
      diff checks.

1090. Reported: "One final mdBook/whitespace check is needed because I just
      updated the progress log with the validation result. After that I’ll give
      you the short handoff."

      Action/result: Added the final validation-log note before rerunning
      mdBook and whitespace checks.

1091. Reported: "I added that last update to the log; now I’m doing the actual
      final check without more commentary unless something fails."

      Action/result: Added the final progress-log bookkeeping note before the
      final check.

1092. Reported: "That was the last bookkeeping loop; running final checks now."

      Action/result: Added the final short bookkeeping note before final
      mdBook, whitespace, status, and diff checks.

1093. Reported: "I’ll commit the current PROGRESS-driven batch now, staging the
      tracked docs/tools/tests changes and leaving generated `build/` plus
      installer images untracked."

      Action/result: Began the requested commit pass and confirmed the intended
      tracked change set.

1094. Reported: "The docs still build and whitespace is clean after the
      commit-log note. The tracked change set is staged; I’m creating the
      commit now."

      Action/result: Recorded the final commit-status update before committing.

1095. Reported: "I’ll pick up from `PROGRESS.md`, find the next highest-value
      open items, and keep the trail in the docs as I go. First I’m going to
      re-read the current progress map and status so I don’t step on anything
      already changed."

      Action/result: Read `PROGRESS.md`, current git status, recent progress
      log entries, and searched the remaining-work markers.

1096. Reported: "The tracker is clean after the last commit, and the open work
      is concentrated in the remaining partial action opcodes plus subsystem
      writeups. I’m going to read the rest of `PROGRESS.md` and then choose a
      small batch that can be grounded in disassembly first, with QEMU only as
      confirmation."

      Action/result: Read the engine coverage and highest-value remaining work
      sections, then searched the partial text/input/system opcodes.

1097. Reported: "There are 22 partial actions left. The quickest useful batch
      looks like the text/input cluster: several opcodes already have
      source-backed handlers, and we can turn at least the geometry/status/prompt
      cases into observable QEMU probes instead of mere 'it returned' checks."

      Action/result: Inspected existing text/input logic probe cases and
      fixture helpers.

1098. Reported: "The current harness compares rendered pixels, so behavior-level
      promotion is easiest when an opcode changes where or whether a known
      object appears. I’m checking how the comparator derives expected frames
      before I add cases, because a sloppy probe here would only look stronger
      than it is."

      Action/result: Read the logic probe comparator and existing runtime text
      model.

1099. Reported: "Before editing probes, I’m re-reading the actual handler
      disassembly for the candidate opcodes and nearby helpers. The goal is to
      make each new fixture test one source-derived state transition, not just
      discover behavior by poking at the executable."

      Action/result: Re-read disassembly around text/status/input handlers,
      including `0x34bd`, `0x3726`, `0x76ca`, and `0x78cb`.

1100. Reported: "One promising non-UI target is `0x8e`: the disassembly says it
      changes the resource-event pair capacity, which should have visible
      consequences during display-mode replay. I’m reading that event buffer
      code now because it may give us a cleaner QEMU validation than trying to
      model BIOS text glyphs first."

      Action/result: Re-read resource-event helpers around `0x705e` and
      `0x716a`, plus existing replay docs and tests.

1101. Reported: "`0x8e` does reset capacity, but overflowing the pair buffer
      calls the interpreter’s error path, so I’m treating that as a risky
      validation target for now. I’m looking for cases where changing the
      capacity resets or narrows a replay log without causing the original
      engine to walk off into error handling."

      Action/result: Reviewed existing display-mode replay fixtures and kept
      `0x8e` as a later target.

1102. Reported: "A better first promotion is the rectangle-clear pair
      `0x69`/`0x9a`: the source says they clear text regions through BIOS
      scroll/clear helpers, and existing message probes already show formatted
      text can remain on the captured surface unless we refresh the picture.
      I’m going to add cases that display text, clear only via those actions,
      and then compare the clean graphics result."

      Action/result: Chose the text rectangle clear pair as the focused
      behavior-promotion target.

1103. Reported: "I’m making the probe change now: two cases, one for the
      row-clear wrapper and one for explicit rectangle bounds. Both start from
      source-derived operands and deliberately avoid the `0x1a` picture refresh
      that would mask leftover text."

      Action/result: Added initial `text_rect_clear_rows_removes_formatted_text`
      and `text_rect_clear_bounds_removes_formatted_text` probe cases.

1104. Reported: "The fixture cases are in place. I’m adding small unit coverage
      so the case catalog keeps these behavior probes from silently disappearing
      during later refactors."

      Action/result: Inspected and prepared updates to
      `tests/test_logic_interpreter_probe.py`.

1105. Reported: "The catalog test already has a good 'known case ids' check, so
      I’m just extending that list for the two new behavior probes."

      Action/result: Added the two text-rectangle behavior case ids to the
      probe catalog test.

1106. Reported: "Next I’m running the local unit check for the probe catalog,
      then I’ll run just the two new cases under QEMU. If either case mismatches,
      I’ll treat that as feedback on my operand assumptions rather than forcing
      the docs to fit."

      Action/result: Ran `python3 -B -m unittest tests.test_logic_interpreter_probe`
      successfully and reviewed the focused diff.

1107. Reported: "The local probe tests pass. I’m starting a two-case QEMU batch
      now; this should tell us whether the row and bounded clears really remove
      the formatted-message residue in the original engine."

      Action/result: Started `text_rect_clear_behaviour_001`; the first command
      used an invalid bare `--snapshot` option.

1108. Reported: "Small harness wrinkle: this probe runner does not have a bare
      `--snapshot` flag, only explicit snapshot image paths. I’m rerunning the
      same two cases through the normal batch path."

      Action/result: Reran the two-case text rectangle batch without the invalid
      option.

1109. Reported: "QEMU is running both cases from a generated snapshot disk now.
      I’ll wait for the captures and then inspect any mismatch instead of
      assuming the rectangle operands are right."

      Action/result: Waited for the QEMU snapshot batch.

1110. Reported: "The row-clear case mismatched, so I’m treating that as a useful
      correction. I’m inspecting the report and capture now to see whether the
      clear bounds were wrong, the formatted helper draws somewhere else, or the
      action is clearing in text coordinates that don’t line up with the
      assumed row."

      Action/result: Inspected `text_rect_clear_behaviour_001`; the mismatch
      showed a black band at logical Y 40..55.

1111. Reported: "The mismatch is actually informative: `0x69` did clear exactly
      rows 5-6, but to black text-background pixels, while my expected image
      assumed the white picture remained. I’m updating the comparator to let a
      probe declare expected screen rectangles, which is the right model for
      text clears that alter the display surface rather than the picture
      resource."

      Action/result: Decided to model expected display-surface rectangles in
      the logic probe comparator.

1112. Reported: "I’ll keep the rectangle expectation local to the fixture
      comparator: it changes only the low visual nibble over an expected
      text-cell rectangle, preserving the picture/control half of the cell.
      That matches the source-level split between text display effects and the
      picture/control buffers."

      Action/result: Inspected `agi_graphics.py` structures to patch the
      expected visual nibbles without changing picture decoding.

1113. Reported: "The case schema now carries optional expected rectangles. I’m
      wiring those rectangles into comparison and setting the two text-clear
      cases to the source-derived text-cell coordinates."

      Action/result: Added `expected_visual_rects` to the logic probe case
      schema and initial expected rectangles.

1114. Reported: "I’m patching the probe model now so the expected image can
      include 'display-only' visual rectangles. This keeps the picture renderer
      itself clean while letting text/UI probes assert the observable screen
      state."

      Action/result: Began adding the display-rectangle application helper.

1115. Reported: "The patch anchor was off by a function name, so I’m locating
      the fixture builder and applying the comparison helper at the actual
      spot."

      Action/result: Located `build_logic_fixture` and `compare_capture`.

1116. Reported: "Found it. I’m inserting the rectangle helper just before
      `compare_capture` and then rerunning the local tests."

      Action/result: Added `apply_expected_visual_rects()` and called it from
      `compare_capture`.

1117. Reported: "The expected-rectangle support is wired in. I’m running the
      unit tests again, then the QEMU batch with the corrected expectations."

      Action/result: Ran the focused unit tests and py_compile successfully.

1118. Reported: "The probe code still compiles and the catalog tests pass. I’m
      rerunning the two original-engine captures now; this time the expected
      image includes the black text-clear rectangles."

      Action/result: Started `text_rect_clear_behaviour_002`.

1119. Reported: "QEMU is through fixture build and running the snapshot batch.
      I’m waiting on the two captures now."

      Action/result: Waited for the second QEMU text rectangle batch.

1120. Reported: "The row-clear case now matches; the bounded-rectangle case
      still mismatches, so I’m narrowing that one. The first result already
      gives us a solid `0x69` behavior probe."

      Action/result: Inspected `text_rect_clear_behaviour_002` and saw the
      bounded case expected X range was wrong.

1121. Reported: "The bounded clear did run, but the X mapping corrected my
      assumption: column 5 maps to logical X 20, not 40. I’m checking the BIOS
      wrapper helper before updating the expected rectangle so the docs describe
      the coordinate scale correctly."

      Action/result: Re-read `code.text.clear_bounds` and `code.text.clear_rows`
      disassembly.

1122. Reported: "The helper confirms the documented argument order: top, left,
      bottom, right, attribute. The remaining surprise is how QEMU’s graphics
      text grid maps columns onto logical pixels, so I’m measuring the capture
      row directly rather than guessing from the mismatch summary."

      Action/result: Measured the bounded-clear capture directly and found black
      ranges X 20..83 for rows 64..71.

1123. Reported: "Measured directly: `0x9a(8,5,8,20,0)` clears logical X 20-83
      over Y 64-71. That matches a 40-column text grid: column units are four
      logical pixels wide and row units are eight logical pixels tall. I’m
      correcting the expected rectangle."

      Action/result: Corrected the bounded expected rectangle to X 20..83/Y
      64..71.

1124. Reported: "The bounded case expectation is fixed. I’m adding a test
      assertion for those exact expected rectangles so this coordinate mapping
      stays visible in the test suite."

      Action/result: Added test assertions for the expected display-surface
      rectangles.

1125. Reported: "The unit test now pins the text-clear rectangle mapping. I’m
      running the focused tests and then the two-case QEMU batch one more time."

      Action/result: Ran the focused unit tests and py_compile successfully.

1126. Reported: "The focused local tests pass with the new rectangle
      expectations. I’m rerunning the original-engine comparison now."

      Action/result: Started `text_rect_clear_behaviour_003`.

1127. Reported: "The QEMU batch is running from its snapshot disk again;
      waiting for both comparisons to finish."

      Action/result: Waited for the final two-case QEMU text rectangle batch.

1128. Reported: "Both text-clear probes now match the original engine. I’m
      promoting `0x69` and `0x9a` in the evidence matrix, then I’ll regenerate
      the generated opcode evidence chapter and update the human docs/progress
      trail."

      Action/result: Confirmed `text_rect_clear_behaviour_003` matched 2/2 and
      prepared evidence promotion.

1129. Reported: "With the generated evidence refreshed, I’m updating the
      human-facing docs: progress counts, opcode descriptions, compatibility
      command/results, and the clean-room notes about the source helper plus
      the QEMU correction from the first mismatch."

      Action/result: Inspected the relevant docs and symbolic labels before
      documentation updates.

1130. Reported: "I’m updating `tools/logic_opcode_evidence.py` so the generated
      matrix treats `0x69` and `0x9a` as QEMU-validated by the new behavior
      probes instead of smoke-only."

      Action/result: Promoted `0x69` and `0x9a` in the evidence registry and
      removed them from smoke-only actions.

1131. Reported: "The evidence registry is updated. I’m checking the generator
      options and then regenerating the opcode evidence chapter from the
      registry."

      Action/result: Checked `tools/logic_opcode_evidence.py --help` and script
      behavior.

1132. Reported: "The generator writes the mdBook chapter by default. I’m
      regenerating that file now."

      Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

1133. Reported: "I don’t see stable labels for the clear helpers yet, so I’m
      adding them to `symbolic_labels.md` while I’m touching this subsystem.
      That will make later cross-version comparisons easier than referring to
      raw `0x2b78`/`0x2bc4` everywhere."

      Action/result: Checked existing text labels in `symbolic_labels.md`.

1134. Reported: "I’m adding the helper labels right beside the other text
      labels, with the observed QEMU coordinate mapping in the notes."

      Action/result: Added `code.text.clear_rows` and
      `code.text.clear_bounds` symbolic labels.

1135. Reported: "Now I’m updating `PROGRESS.md`: two more action opcodes are
      covered at behavior level, so the covered count moves from 154 to 156 and
      partial actions drop from 22 to 20."

      Action/result: Updated `PROGRESS.md` counts and marked `0x69`/`0x9a` as
      QEMU-validated.

1136. Reported: "I’m tightening the opcode chapter next: the handler rows now
      mention the display-surface coordinate mapping, and the QEMU paragraph
      changes from smoke-only to behavior-level evidence for the two clear
      operations."

      Action/result: Updated `docs/src/logic_bytecode.md` for `0x69`, `0x9a`,
      and the new behavior fixture.

1137. Reported: "I’m also adding a short implementation-facing note in the
      runtime model: these clears are display-surface operations, not
      picture-resource edits. That distinction matters for a clean-room engine."

      Action/result: Added text-rectangle clear semantics to
      `docs/src/runtime_model.md`.

1138. Reported: "Next I’m adding the exact QEMU command/result to
      `compatibility_testing.md`, including the corrected first failed run so
      the evidence trail shows why the expected rectangles were added."

      Action/result: Added `text_rect_clear_behaviour_003` command/results and
      the earlier mismatch correction to compatibility docs.

1139. Reported: "I’m appending the clean-room notes section now with the
      disassembly commands, QEMU commands, the mismatch correction, and the
      exact behavior promoted."

      Action/result: Prepared the clean-room executable notes update.

1140. Reported: "I’m adding the new section after the `0x84` section, so the
      chronology stays intact."

      Action/result: Appended the 2026-07-04 text rectangle clear behavior
      section to `clean_room_executable_notes.md`.

1141. Reported: "I’ve got the substantive docs updated. I’m doing the
      progress-log bookkeeping now, then I’ll run the full validation suite for
      the changed probe/tool/docs set."

      Action/result: Began appending this progress-log batch before final
      validation.

1142. Reported: "The progress log is caught up through the documentation pass.
      I’m running the full validation set now: unit tests, generated evidence
      check, mdBook build, whitespace, and status."

      Action/result: Ran `python3 -B -m unittest discover -s tests`,
      `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
      and `git diff --check`.

1143. Reported: "All four validations passed: 103 unit tests, evidence
      `--check`, mdBook, and whitespace. I’m adding that validation result to
      the progress log and then doing a final status/diff pass."

      Action/result: Recorded the successful validation result before final
      status and diff checks.

1144. Reported: "Because the progress log changed after validation, I’m
      rerunning the lightweight doc/whitespace checks and then I’ll give you the
      concise handoff."

      Action/result: Reran `mdbook build docs`, `git diff --check`, status, and
      diff-stat checks.

1145. Reported: "The final checks are clean, and I spotted a generated
      `tools/__pycache__/` from the Python runs. I’m removing that disposable
      cache and recording this last validation/status update so the handoff is
      tidy."

      Action/result: Removed generated `tools/__pycache__/` and confirmed the
      tracked change set plus existing untracked generated/input directories.

1146. Reported: "Last log entry is in. I’ll do one quiet final check now."

      Action/result: Reran mdBook, whitespace, and status checks; this note was
      added because that status update itself is part of the historical log.

1147. Reported: "One final bookkeeping note got added by my own update, so I’m
      recording that too and then I’ll stop the commentary loop."

      Action/result: Recorded the final bookkeeping note before the truly quiet
      final mdBook, whitespace, and status checks.

1148. Reported: "I’ll continue from the current PROGRESS.md map and keep the
      work focused on the remaining partial opcodes. I’m going to re-check the
      tracker, evidence matrix, and working tree first so the next probe batch
      lands cleanly."

      Action/result: Re-read `PROGRESS.md`, `git status --short`, the end of
      this progress log, and the opcode evidence/current tracker references.

1149. Reported: "The remaining partial list is still mostly text/input and a
      few VM-global toggles. I’m going to look for the next source-backed state
      change that can be made observable without inventing a glyph renderer;
      status/input clears and global motion/input gates look like the best
      candidates."

      Action/result: Re-read the text/input opcode notes, disassembled around
      action `0x83`, and inspected existing logic-interpreter probe cases.

1150. Reported: "I’m resuming at the partial text/status/input opcodes and
      will start with the ones whose source clearly funnels into row-clearing
      code. That should let us promote a couple of opcodes with source-backed,
      QEMU-validated behavior instead of just dispatch smoke."

      Action/result: Re-read the probe catalog, unit tests, evidence mapping,
      and text opcode chapter around the input/status handlers.

1151. Reported: "The source path is lining up: both status-hide and
      input-disable appear to use the same cleared text-row primitive that we
      already validated for rectangle clears. I’m checking the exact dispatch
      targets now so the new probes can cite the code path rather than just the
      visual outcome."

      Action/result: Searched docs for `0x70`, `0x71`, `0x77`, and input/status
      labels; inspected the relevant probe cases and disassembly ranges.

1152. Reported: "One minor wrinkle: direct `ndisasm` with manual skips landed
      midstream in one range, so I’m switching to the existing full disassembly
      artifact for address-aligned evidence. That keeps the notes tied to the
      same address map the rest of the project uses."

      Action/result: Checked the full disassembly artifact and existing notes
      for the status/input helper address map.

1153. Reported: "The previous notes already captured the core handlers; I’m
      adding narrowly-scoped probes now. The fixture will configure the target
      row, run the hide/disable opcode, then draw the usual validation object,
      so any leftover text-row state shows up as a capture mismatch."

      Action/result: Inspected the aligned source snippets and test helper
      assertions before editing.

1154. Reported: "I’m going to make the row clears visible by first drawing a
      short formatted message on the same text row, then running the opcode
      under test. That turns a global/UI side effect into an ordinary screen
      comparison: if the source interpretation is wrong, the text remnants
      should remain."

      Action/result: Confirmed existing text clear evidence and planned the two
      row-clear fixtures.

1155. Reported: "I’m about to edit the probe catalog and its unit assertions.
      I’ll keep the new cases small: one for `0x71` clearing the configured
      status row, one for `0x77` clearing the configured input row."

      Action/result: Added `input_line_disable_clears_configured_row` and
      `status_line_hide_clears_configured_row` to
      `tools/logic_interpreter_probe.py`.

1156. Reported: "The two probe cases are in place. I’m wiring the catalog
      tests next so future edits don’t silently drop the behavior coverage."

      Action/result: Added unit assertions for the two new case ids and their
      expected visual clear rectangles.

1157. Reported: "The static catalog checks are updated. I’m running the
      focused unit test before invoking QEMU, since that catches bad fixture
      metadata cheaply."

      Action/result: Ran the two focused
      `tests.test_logic_interpreter_probe.LogicInterpreterProbeTests` methods;
      both passed.

1158. Reported: "The unit checks passed. I’m running the two new cases through
      the original interpreter now; this is the point where the clean-room
      hypothesis either earns behavior-level evidence or gets revised."

      Action/result: Started QEMU snapshot batch
      `text_hide_clear_behaviour_001` with the two new cases.

1159. Reported: "QEMU is running both fixtures from a snapshot batch now. The
      build phase completed and the interpreter is executing the cases, so I’m
      waiting on the captures/comparisons."

      Action/result: Waited for the running QEMU batch to finish.

1160. Reported: "Both QEMU cases matched:
      `0x77` and `0x71` now have visible row-clear behavior, not just
      'returns safely.' I’m updating the evidence matrix and docs so the
      tracker reflects that promotion."

      Action/result: Promoted action opcodes `0x71` and `0x77` from smoke to
      QEMU-validated in `tools/logic_opcode_evidence.py`.

1161. Reported: "The evidence script supports direct regeneration, so I’m
      letting it rewrite the opcode evidence chapter from the source-of-truth
      mapping rather than hand-editing the table."

      Action/result: Ran `python3 -B tools/logic_opcode_evidence.py` to
      regenerate `docs/src/logic_opcode_evidence.md`.

1162. Reported: "The generated evidence table is refreshed. I’m updating
      `PROGRESS.md` next: the action coverage count moves up by two, and the
      remaining partial list loses `0x71` and `0x77`."

      Action/result: Updated `PROGRESS.md` to 158/176 action opcodes at `[x]`
      level, with 18 partial action opcodes remaining.

1163. Reported: "`PROGRESS.md` is updated. I’m scanning for stale counts or
      old 'dispatch-smoke' references before touching the narrative docs."

      Action/result: Started a stale-reference scan; the first command failed
      because a literal backtick confused the shell quoting.

1164. Reported: "That scan tripped on a shell quote in the literal backtick
      pattern, so I’m rerunning it with simpler text patterns. No state
      changed."

      Action/result: Reran the stale-reference scan and found only historical
      notes from earlier work.

1165. Reported: "The stale hits are historical notes from earlier runs, not
      current trackers. I’m adding a new dated notes section rather than
      rewriting that history."

      Action/result: Re-read symbolic labels, opcode docs, runtime model, and
      compatibility text to prepare focused updates.

1166. Reported: "I’m also adding a symbolic label for the single-row clear
      helper used by both handlers. That gives later cross-version comparisons
      a stable name instead of just another absolute address."

      Action/result: Disassembled `code.text.clear_row` at image `0x2ba6` and
      added it to `docs/src/symbolic_labels.md`.

1167. Reported: "The symbolic label is added. I’m tightening the opcode chapter
      now, with the implementation detail that `0x2ba6` is the single-row
      wrapper around the broader text-row clear helper."

      Action/result: Updated opcode rows for `0x71` and `0x77` in
      `docs/src/logic_bytecode.md`.

1168. Reported: "The opcode rows now carry the behavioral evidence. I’m adding
      the batch summary near the other text/UI QEMU notes so readers see
      exactly how those two opcodes were promoted."

      Action/result: Added the `text_hide_clear_behaviour_001` narrative to the
      logic bytecode chapter.

1169. Reported: "I’m adding the higher-level runtime contract too: these
      handlers are 'visible text surface' operations, not changes to the
      picture resource. That distinction is useful for a future
      implementation."

      Action/result: Added status/input single-row clear semantics to
      `docs/src/runtime_model.md`.

1170. Reported: "The runtime model has the visible-surface contract now. I’m
      adding the exact QEMU command and result to the compatibility chapter."

      Action/result: Added the `text_hide_clear_behaviour_001` command and
      result to `docs/src/compatibility_testing.md`.

1171. Reported: "The compatibility chapter has the new batch. I’m appending the
      clean-room notes section with the disassembly command, fixture changes,
      QEMU result, and tracker updates."

      Action/result: Added the dated clean-room notes section for the
      status/input single-row clear behavior probes.

1172. Reported: "The main docs are updated. I’m doing the progress-log
      bookkeeping now, including the short status messages from before and
      after the context handoff so the historical trail stays continuous."

      Action/result: Appended this progress-log batch before final validation.

1173. Reported: "The progress log is caught up through the doc edits. I’m
      running the full validation pass now: unit suite, generated evidence
      check, mdBook build, and whitespace check."

      Action/result: Ran `python3 -B -m unittest discover -s tests`,
      `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
      and `git diff --check`.

1174. Reported: "All four validations passed: 103 unit tests, evidence
      `--check`, mdBook, and whitespace. I’m recording that validation result
      and then I’ll do a final diff/status pass."

      Action/result: Recorded the successful validation result before final
      diff and status inspection.

1175. Reported: "Because the progress log changed after validation, I’m
      rerunning the lightweight doc/whitespace checks and grabbing the final
      status/diff summary."

      Action/result: Reran `mdbook build docs`,
      `python3 -B tools/logic_opcode_evidence.py --check`, `git diff --check`,
      `git status --short`, and `git diff --stat`.

1176. Reported: "The second mdBook/evidence/whitespace pass is clean. Final
      status shows the expected tracked edits plus the existing untracked DOS
      installer/images under `002962_ms_dos_622/` and generated `build/`."

      Action/result: Recorded the final validation/status summary after the
      second lightweight check pass.

1177. Reported: "I’ll commit the current row-clear/evidence work first, leaving
      the existing generated `build/` and DOS installer directory untracked.
      After that I’ll pick up the next highest-value partial opcode from
      `PROGRESS.md` and keep the new work uncommitted until you ask again."

      Action/result: Re-read status, diff stat, and `PROGRESS.md` before
      staging the completed row-clear work.

1178. Reported: "The commit candidate is exactly the 11 modified files from
      the row-clear work. I’m staging only those tracked files now; `build/`
      and `002962_ms_dos_622/` stay out of the commit."

      Action/result: Staged the 11 tracked files from the status/input
      row-clear validation pass.

1179. Reported: "Staging succeeded. I’m committing this as the status/input
      row-clear behavior validation, then I’ll continue from the next partial
      opcode cluster."

      Action/result: Attempted `git commit -m "Validate status and input row
      clears"`.

1180. Reported: "The sandbox blocked the commit while trying to create
      `.git/index.lock`, so I’m rerunning the same commit with escalation."

      Action/result: Reran the commit with escalation. Commit `aa55bda`
      (`Validate status and input row clears`) succeeded with 11 files changed.

1181. Reported: "Commit `aa55bda` is in. I’m back on the tracker now, and the
      next likely wins are still in the text/input group: `0x70` status redraw,
      `0x78` input redraw, and the refresh/erase helpers. I’ll read the source
      path first and only use QEMU once there’s a precise behavior hypothesis
      to validate."

      Action/result: Confirmed the post-commit status and re-read the relevant
      source-backed text/input opcode notes and disassembly.

1182. Reported: "The committed tree is clean aside from the long-standing
      untracked input/generated directories. I’m noticing the same address-map
      trap as before: one disassembly artifact is file-offset oriented, while
      the docs use image-oriented labels, so I’m cross-checking against byte
      patterns before naming any new behavior."

      Action/result: Searched for byte patterns and reran image-oriented
      `ndisasm` commands around the status, input, and text-attribute handlers.

1183. Reported: "Two behavior probes look worth trying from the disassembly:
      `0x78` should redraw/clear the configured input row, and `0x6a` should
      enter alternate text mode and clear the visible text surface through
      `code.text.clear_rows`. I’m adding both as screen comparisons, with QEMU
      as confirmation rather than discovery."

      Action/result: Began adding `input_line_enable_clears_configured_row` and
      `text_attribute_enable_clears_visible_surface` to the probe catalog.

1184. Reported: "That patch missed one nearby context block, so I’m reopening
      the exact probe catalog slice and applying the additions in smaller
      pieces."

      Action/result: Re-read the probe catalog slice around the existing
      text/input cases.

1185. Reported: "I’ve got the exact insertion points now. I’m adding the
      `0x78` row-redraw case and the `0x6a` visible-surface clear case
      separately."

      Action/result: Added the `0x78` input-line enable row-clear probe.

1186. Reported: "The `0x78` case is in. I’m adding the `0x6a` full
      visible-surface clear check right after the existing text-attribute smoke
      case."

      Action/result: Added the initial `0x6a` visible-surface clear probe.

1187. Reported: "Both new probe definitions are in place. I’m updating the unit
      assertions now so the catalog and expected rectangles stay pinned down."

      Action/result: Re-read the unit-test catalog and expected-rectangle
      assertions.

1188. Reported: "The test file already has the recent row-clear assertions; I’m
      extending that same check for `0x78` and the full-surface `0x6a` case."

      Action/result: Added unit assertions for the two new case ids and
      expected visual rectangles.

1189. Reported: "The catalog tests are updated. I’m running the focused unit
      checks before taking the two hypotheses to QEMU."

      Action/result: Ran the two focused logic-interpreter probe unit tests;
      both passed.

1190. Reported: "The focused checks passed. I’m running the new `0x78` and
      `0x6a` cases through the original engine as a two-case QEMU snapshot
      batch now."

      Action/result: Started QEMU batch `text_enable_attr_behaviour_001`.

1191. Reported: "The `0x78` input-line enable case matched. The `0x6a`
      full-surface case is still running, so I’m waiting for that capture
      before updating evidence."

      Action/result: Waited for the second case in
      `text_enable_attr_behaviour_001`.

1192. Reported: "The batch split neatly: `0x78` matched, while my `0x6a`
      full-black expectation was too blunt. I’m inspecting the mismatch before
      deciding whether to revise that case or leave `0x6a` as source-backed
      smoke for now."

      Action/result: Inspected the QEMU report, the `0x6a` PPM capture, and
      text-attribute helper disassembly.

1193. Reported: "The `0x6a` mismatch is interesting rather than bad: the
      capture is entirely black, so the surface clear happened, but the later
      transient-object validation draw did not appear while alternate text mode
      was active. I’m adjusting the harness carefully so this case can compare
      the visible surface without requiring the usual object draw."

      Action/result: Re-read the probe helper and comparator paths for
      `compare_view` handling.

1194. Reported: "I’m going to keep the `0x6a` probe, but make the expected
      result match what the original actually does in this mode: black visible
      surface, no composed validation object. That means adding a small
      `compare_view` switch to the shared case helper instead of special-casing
      the comparator."

      Action/result: Added a `compare_view` parameter to `_custom_case` and set
      the `0x6a` case to `compare_view=False`.

1195. Reported: "The harness now supports a no-composed-view expectation for
      special display states, and the `0x6a` case uses it. I’m pinning that in
      the unit test before rerunning QEMU."

      Action/result: Added a unit assertion that the `0x6a` case does not
      compare the usual composed view.

1196. Reported: "The unit expectation now records that `0x6a` is a surface-only
      comparison. I’m rerunning the focused tests and then the two QEMU cases."

      Action/result: Reran the focused unit tests and started QEMU batch
      `text_enable_attr_behaviour_002`.

1197. Reported: "The focused tests passed again and QEMU has re-confirmed the
      `0x78` case. I’m waiting on the revised `0x6a` comparison."

      Action/result: Waited for the second case in
      `text_enable_attr_behaviour_002`.

1198. Reported: "The revised QEMU batch matched both cases. I’m promoting
      `0x78` and `0x6a` in the generated evidence map now, while leaving
      `0x6c`, `0x6b`, and `0x6d` at their current partial levels."

      Action/result: Re-read evidence, symbolic-label, opcode, compatibility,
      and clean-room note context before promotion.

1199. Reported: "The evidence source now promotes `0x6a` and `0x78`. I’m
      regenerating the evidence chapter and updating the progress counts from
      158 to 160 covered action opcodes."

      Action/result: Updated `tools/logic_opcode_evidence.py` and regenerated
      `docs/src/logic_opcode_evidence.md`.

1200. Reported: "The generated evidence chapter is refreshed. I’m aligning
      `PROGRESS.md` with two more `[x]` promotions: `0x6a` and `0x78`."

      Action/result: Updated `PROGRESS.md` to 160/176 action opcodes at `[x]`
      level, with 16 partial action opcodes remaining.

1201. Reported: "I’m updating the narrative docs next. The key wording is:
      `0x78` is a normal input-row redraw/clear, while `0x6a` is alternate
      text-attribute mode, where the visible surface clears and the usual
      composed object check is intentionally not expected."

      Action/result: Updated `docs/src/logic_bytecode.md` rows and behavior
      fixture narrative for `0x6a` and `0x78`.

1202. Reported: "The opcode chapter is updated with the new behavior fixture.
      I’m adding the same command/result to the compatibility chapter and
      adjusting the runtime model’s state-machine notes."

      Action/result: Updated `docs/src/compatibility_testing.md` and
      `docs/src/runtime_model.md`.

1203. Reported: "I’m also tightening the symbolic-label notes for the two
      helpers implicated here, so later cross-version work has the behavioral
      evidence attached to the label map."

      Action/result: Updated `docs/src/symbolic_labels.md` entries for
      `code.text.enter_attr_mode` and `code.input.redraw_input_line`.

1204. Reported: "I’m correcting one older compatibility paragraph too, so it
      remains historically true without implying `0x6a` and `0x78` are still
      only smoke-covered."

      Action/result: Revised the text/status smoke-batch wording in
      `docs/src/compatibility_testing.md`.

1205. Reported: "The compatibility history is now clearer. I’m appending the
      clean-room notes for the `0x78`/`0x6a` disassembly-backed QEMU pass,
      including the first failed expectation for `0x6a`."

      Action/result: Added the clean-room notes section for
      `text_enable_attr_behaviour_001` and `text_enable_attr_behaviour_002`.

1206. Reported: "The clean-room notes now have the command/result trail. I’m
      doing a consistency scan for stale counts and smoke labels before the
      final validation pass."

      Action/result: Ran stale-reference scans, checked `PROGRESS.md`,
      `docs/src/logic_opcode_evidence.md`, status, and diff stat.

1207. Reported: "The current stale-count hits are only historical notes from
      the just-committed previous section, so I’m leaving them intact. I’m
      appending the progress-log entries for this commit-and-continue pass now,
      then I’ll run validation."

      Action/result: Began appending this progress-log batch.

1208. Reported: "I’m adding a fairly long progress-log batch because this turn
      included the requested commit, a sandbox retry, a failed hypothesis for
      `0x6a`, and the corrected validation. This is exactly the sort of trail
      future-us will be grateful not to reconstruct."

      Action/result: Appended this progress-log batch before final validation.

1209. Reported: "The progress log is caught up through the corrected
      `0x6a`/`0x78` work. I’m running the full validation set now: unit tests,
      evidence check, mdBook, and whitespace."

      Action/result: Ran `python3 -B -m unittest discover -s tests`,
      `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
      and `git diff --check`.

1210. Reported: "All four validations passed: 103 unit tests, evidence
      `--check`, mdBook, and whitespace. I’m recording that and then doing a
      final status/diff pass."

      Action/result: Recorded the successful validation result before final
      status and diff inspection.

1211. Reported: "Because the progress log changed after validation, I’m
      rerunning the lightweight checks and grabbing the final status summary."

      Action/result: Reran `mdbook build docs`,
      `python3 -B tools/logic_opcode_evidence.py --check`, `git diff --check`,
      `git status --short`, and `git diff --stat`.

1212. Reported: "One last log entry was added for the lightweight rerun, so I’m
      doing a quiet final check now and then I’ll stop the commentary loop."

      Action/result: Recorded the final bookkeeping note before quiet final
      validation and status checks.
