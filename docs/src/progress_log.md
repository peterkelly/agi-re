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
