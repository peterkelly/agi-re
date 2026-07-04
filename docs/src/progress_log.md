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

1213. Reported: "I’ll commit the current `0x6a`/`0x78` behavior work first,
      keeping `build/` and the DOS installer images untracked. Then I’ll
      continue with the next partial opcodes from `PROGRESS.md`, again starting
      from the disassembled source and using QEMU only to validate a concrete
      hypothesis."

      Action/result: Re-read status, diff stat, and the remaining partial
      opcode list in `PROGRESS.md`.

1214. Reported: "The uncommitted set is the expected 11 tracked files from the
      `0x6a`/`0x78` pass. I’m staging just those tracked files now and leaving
      generated inputs alone."

      Action/result: Staged the tracked `0x6a`/`0x78` behavior-validation
      files.

1215. Reported: "Staging succeeded. I’m committing the
      input-enable/text-attribute behavior validation now; commit writes to
      `.git`, so I’m using escalation for that part."

      Action/result: Created commit `1229d68` (`Validate input enable and text
      attribute mode`).

1216. Reported: "Commit `1229d68` is in. I’m continuing from the remaining 16
      partial action opcodes; next I’m looking for another source-backed
      visible text/input behavior, especially status redraw `0x70`, prompt
      marker `0x6c`, and the `0x89`/`0x8a` refresh/erase pair."

      Action/result: Confirmed the post-commit status and re-read the remaining
      text/input partial opcode notes and disassembly.

1217. Reported: "The disassembly suggests a clean way to validate `0x6c`
      without implementing font glyphs: set a non-empty prompt marker, then set
      it to an empty message and redraw the input row. If `0x6c` really stores
      the first message byte, the redraw stays all black; otherwise a marker
      glyph appears and the capture mismatches."

      Action/result: Re-read prompt-marker and input-line helper notes,
      existing cases, and focused disassembly around `0x38b4` and `0x37f7`.

1218. Reported: "I’m adding two targeted cases now: one for `0x6c` clearing a
      previously non-empty prompt marker by loading an empty message, and one
      for `0x6b` leaving alternate text mode so the normal picture/object draw
      becomes visible again. Both are small enough to be decisive."

      Action/result: Added `text_attribute_disable_restores_picture_draw` and
      `input_prompt_empty_message_suppresses_marker` to the probe catalog.

1219. Reported: "The two new probe cases are in the catalog. I’m adding unit
      assertions for their presence and the `0x6c` expected row-clear
      rectangle."

      Action/result: Updated `tests/test_logic_interpreter_probe.py` for the
      two new case ids and expected rectangle.

1220. Reported: "The unit assertions are updated. I’m running the focused
      catalog tests, then I’ll run the two new cases through QEMU if those
      pass."

      Action/result: Ran the two focused logic-interpreter probe unit tests;
      both passed.

1221. Reported: "The focused tests passed. I’m running these two cases against
      the original interpreter now; if they match, they should promote `0x6b`
      and `0x6c` from smoke to behavior-level coverage."

      Action/result: Started QEMU batch `text_prompt_attr_behaviour_001`.

1222. Reported: "The `0x6b` case matched: leaving alternate text mode restores
      the normal picture/object draw path. I’m waiting on the `0x6c`
      prompt-marker suppression case now."

      Action/result: Waited for the second case in
      `text_prompt_attr_behaviour_001`.

1223. Reported: "Both cases matched in QEMU, so `0x6b` and `0x6c` can move up
      to behavior-level evidence. I’m updating the generated evidence map and
      the tracker, then I’ll add the source/QEMU notes."

      Action/result: Re-read evidence, opcode, compatibility, runtime, and
      symbolic-label context before promotion.

1224. Reported: "I’m promoting `0x6b` and `0x6c` in the evidence source now.
      The docs will distinguish the `0x6c` evidence as an empty-message
      prompt-marker behavior, not a full glyph-rendering spec."

      Action/result: Updated `tools/logic_opcode_evidence.py`.

1225. Reported: "The evidence source is updated. I’m regenerating the evidence
      chapter and moving the tracker to 162 covered action opcodes."

      Action/result: Regenerated `docs/src/logic_opcode_evidence.md` and
      updated `PROGRESS.md` to 162/176 action opcodes at `[x]` level.

1226. Reported: "`PROGRESS.md` now reflects 162 covered actions and 14
      partials. I’m updating the opcode chapter and runtime docs with the
      specific contracts we just validated."

      Action/result: Updated `docs/src/logic_bytecode.md`.

1227. Reported: "The opcode chapter now names the new QEMU fixture and narrows
      the remaining smoke list. I’m adding the compatibility command/result and
      then updating the runtime/symbolic summaries."

      Action/result: Updated `docs/src/compatibility_testing.md`.

1228. Reported: "The compatibility chapter has the new
      `text_prompt_attr_behaviour_001` batch. I’m adding the
      implementation-facing notes now."

      Action/result: Updated `docs/src/runtime_model.md`.

1229. Reported: "The runtime model now captures prompt-marker suppression and
      text-mode exit. I’m attaching the same evidence to the stable
      symbolic-label map."

      Action/result: Updated `docs/src/symbolic_labels.md`.

1230. Reported: "I’m appending the clean-room notes for the prompt-marker and
      text-mode-exit probes, including the source commands and the exact QEMU
      batch."

      Action/result: Added the dated clean-room notes section for
      `text_prompt_attr_behaviour_001`.

1231. Reported: "The clean-room notes are updated. I’m adding the progress-log
      batch for this turn now, covering the commit, the two new probes, the
      QEMU results, and the documentation updates."

      Action/result: Began appending this progress-log batch.

1232. Reported: "I’m keeping the log concise but complete: every progress
      update gets an entry, while command details live in the clean-room notes.
      After this I’ll run the full validation suite."

      Action/result: Appended this progress-log batch before final validation.

1233. Reported: "The progress log is caught up through the `0x6b`/`0x6c` work.
      I’m running the full validation pass now: unit suite, generated evidence
      check, mdBook, and whitespace."

      Action/result: Ran `python3 -B -m unittest discover -s tests`,
      `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
      and `git diff --check`.

1234. Reported: "All four validations passed: 103 unit tests, evidence
      `--check`, mdBook, and whitespace. I’m recording that result and then
      doing the final status/diff pass."

      Action/result: Recorded the successful validation result before final
      status and diff inspection.

1235. Reported: "The progress log changed after validation, so I’m rerunning
      the lightweight checks and collecting the final status summary."

      Action/result: Reran `mdbook build docs`,
      `python3 -B tools/logic_opcode_evidence.py --check`, `git diff --check`,
      `git status --short`, `git diff --stat`, and `git log -2 --oneline`.

1236. Reported: "The lightweight checks are clean and the final status shows
      the expected uncommitted `0x6b`/`0x6c` work plus the existing untracked
      generated/input directories. I’m recording that last status note and
      doing one quiet final check."

      Action/result: Recorded the final status note before quiet final
      validation and status checks.

1237. Reported: "One last note was appended, so I’ll run the final quiet check
      now and then hand this back without another progress-log loop."

      Action/result: Recorded the final bookkeeping note before quiet final
      validation and status checks.

1238. Reported: "I’ll commit the current `0x6b`/`0x6c` validation work, keeping
      the generated `build/` artifacts and DOS installer images untracked. I’ll
      add a tiny progress-log note for this commit turn, then stage only the
      tracked project files."

      Action/result: Re-read status, diff stat, and the tail of this progress
      log before staging the commit.

1239. Reported: "The commit candidate is the expected 11 tracked files, and the
      previous validation is already recorded. I’m appending the commit-turn log
      entry, then I’ll do a lightweight check and commit."

      Action/result: Appended the commit-turn progress-log entries before
      final lightweight checks and staging.

1240. Reported: "I’ll continue from the freshly committed state and target the
      remaining partial opcodes in PROGRESS.md. I’ll start by rereading the
      tracker and source notes, then look for the next behavior that can be
      proven from disassembly and validated with a narrow QEMU fixture."

      Action/result: Re-read repository status, `PROGRESS.md`, and current
      opcode/probe references.

1241. Reported: "I’m going to take the next partial opcode that looks most
      tractable from the disassembly: `0x6d`, the text attribute pair setter.
      The goal is to turn it from “dispatch-smoked” into a small behavior spec
      with an original-engine confirmation, then update the tracker and docs."

      Action/result: Selected `0x6d` as the next promotion target.

1242. Reported: "The first pass confirms the remaining tracker entries are
      mostly “partial because we only proved dispatch.” I’m drilling into the
      existing probe harness now so the next test is shaped like the engine
      code, not just a random observation."

      Action/result: Re-read the logic interpreter probe harness and existing
      text-attribute cases.

1243. Reported: "The existing notes already identify the helper chain
      (`0x77d5` -> `0x7803`/`0x78a1`/`0x78ad`). I’m going back to that
      disassembly now to pin down which operand combinations should produce a
      visible, stable EGA result."

      Action/result: Re-read disassembly around `0x76ca`, `0x77af`, and
      `0x77d5`.

1244. Reported: "The disassembly supports a good controlled case: set the pair
      to foreground `0`, background-ish operand `1`, then enter attribute mode.
      Because `0x6a` recomputes with `[0x1757] = 1`, the fill attribute should
      become `0xf0`, which ought to show as a full white background in the EGA
      capture."

      Action/result: Added planned case
      `text_attribute_pair_changes_attr_mode_clear_color`.

1245. Reported: "I’ve added that as a real fixture case rather than a one-off
      script. Now I’m wiring the unit expectations around it, then I’ll let
      QEMU tell us whether the source-derived `0xf0` prediction matches the
      original engine."

      Action/result: Updated `tools/logic_interpreter_probe.py` and
      `tests/test_logic_interpreter_probe.py`.

1246. Reported: "The fixture is in place with an explicit “no sprite expected”
      comparison, since active attribute mode hides the normal validation draw.
      I’m running the local probe tests before spending a QEMU boot on it."

      Action/result: Ran the focused unit tests for case coverage and expected
      visual rectangles; both passed.

1247. Reported: "The harness tests are clean. Next I’m running just this new
      `0x6d` case through the original interpreter; if it matches, we can
      promote the opcode’s evidence level instead of leaving it as
      dispatch-only."

      Action/result: Ran the one-case QEMU batch
      `text_attr_pair_behaviour_001`.

1248. Reported: "QEMU matched exactly: the original engine clears the whole
      visible surface to color `15` after `0x6d(0,1)` followed by `0x6a`. I’m
      updating the evidence tables and prose now so the source-derived helper
      behavior and the dynamic confirmation line up."

      Action/result: Confirmed the original-engine capture matched the local
      expected full-screen color-15 surface.

1249. Reported: "The match gives us a nice high-level rule: `0x6d` stores the
      logical pair, and `0x6a` reinterprets that saved pair as a packed text
      attribute once attr mode is enabled. I’m promoting `0x6d` in the
      generated evidence source, then I’ll regenerate the mdBook page from it."

      Action/result: Moved `0x6d` from dispatch-smoke to behavior-level
      evidence in `tools/logic_opcode_evidence.py` and regenerated the
      evidence chapter.

1250. Reported: "The generated opcode matrix now marks `0x6d` as
      behavior-level QEMU evidence. I’m folding the same result into PROGRESS
      and the implementation-oriented text sections so the tracker, opcode
      chapter, and compatibility notes all tell the same story."

      Action/result: Began updating tracker and documentation prose.

1251. Reported: "One small bookkeeping wrinkle: `docs/src/progress_log.md` is
      long enough that a narrow `sed` range landed in an older section, so I’m
      using the tail for the current append point. The substantive `0x6d`
      changes are straightforward."

      Action/result: Located the current progress-log append point.

1252. Reported: "I found the append point. Before final validation I’ll add
      the current-turn progress entries there, including the QEMU result and
      the docs updates, so the historical log stays complete."

      Action/result: Prepared to append the current-turn progress-log entries.

1253. Reported: "`PROGRESS.md` is bumped to 163/176 action opcodes at full
      coverage, with 13 partials left. I’m updating the opcode prose next so
      implementers can see the exact pair-to-attribute behavior we proved."

      Action/result: Updated `PROGRESS.md` and `docs/src/logic_bytecode.md`.

1254. Reported: "The opcode row now carries both the storage globals and the
      visible consequence. I’m adding the same rule to the runtime model
      because this is really part of the text-surface state machine, not just a
      bytecode footnote."

      Action/result: Updated `docs/src/runtime_model.md`.

1255. Reported: "Runtime prose is updated. I’m attaching the new case name and
      the `0xf0` observation to the symbolic label map, since that file is the
      cross-version anchor we’ll need when addresses move in other AGI builds."

      Action/result: Updated `docs/src/symbolic_labels.md`.

1256. Reported: "The symbolic map now links `code.text.set_attribute_pair` to
      the new validation case. I’m adding the reproducible QEMU command/result
      to the compatibility chapter so future runs can replay this exact check."

      Action/result: Updated `docs/src/compatibility_testing.md`.

1257. Reported: "Compatibility docs have the exact `TA` batch command and
      result. I’m appending the clean-room notes section now with the
      disassembly evidence, unit/QEMU commands, and what changed in the model."

      Action/result: Updated `docs/src/clean_room_executable_notes.md`.

1258. Reported: "The notes already have the previous text-mode batches, so I’m
      appending this as a small follow-on section rather than rewriting
      history. That keeps the trail readable: source helper, new fixture, QEMU
      match, tracker promotion."

      Action/result: Appended the dated clean-room notes section for the
      `0x6d` text-attribute-pair behavior probe.

1259. Reported: "The clean-room notes now include the `0x6d` pass. I’m
      catching the progress log up through this point before validation; after
      the checks run, I’ll append a short validation-result entry too."

      Action/result: Appended the current progress-log batch before validation.

1260. Reported: "The progress log is caught up through the documentation work.
      I’m running the full validation pass now: unit suite, generated evidence
      check, mdBook build, and whitespace check."

      Action/result: Ran `python3 -B -m unittest discover -s tests`,
      `python3 -B tools/logic_opcode_evidence.py --check`, `mdbook build docs`,
      and `git diff --check`.

1261. Reported: "All four validations passed: 103 unit tests, evidence
      `--check`, mdBook, and whitespace. Because I’m adding that validation
      note to the log, I’ll rerun the lightweight docs/evidence checks
      afterward so the final state is clean."

      Action/result: Recorded the successful validation result before
      lightweight final checks.

1262. Reported: "The validation result is recorded. I’m doing the final
      lightweight pass now: rebuild the book after the log edit, confirm
      generated evidence is still current, and inspect the final diff/status."

      Action/result: Ran final lightweight checks and inspected the uncommitted
      diff/status.

1263. Reported: "I spotted one more user-facing update from this validation
      loop that needs to be logged. I’m adding that final progress-log entry
      and rerunning the docs/evidence/whitespace checks once more, quietly
      after this."

      Action/result: Recorded the final progress-log update before quiet
      validation checks.

1264. Reported: "I’ll keep moving from the current uncommitted `0x6d` state
      and choose the next partial opcode(s) from `PROGRESS.md`. I’ll keep the
      updates concise, but I’ll work in a longer continuous pass and only stop
      if validation fails in a way that needs a decision."

      Action/result: Resumed from the uncommitted text-attribute state and
      selected the next partial opcodes from `PROGRESS.md`.

1265. Reported: "I’m looking at the remaining partial list now. The next best
      candidate looks like the input-line pair `0x89`/`0x8a`, because the
      disassembly already exposes visible buffer globals and there may be a
      narrow display-surface probe hiding in the existing text harness."

      Action/result: Chose `0x89`/`0x8a` as the next behavior-level probe
      target.

1266. Reported: "The input-line path is a little more awkward than `0x6d`:
      proving it exactly would require either text glyph rendering or a
      targeted predicate comparison. I’m checking the helper code first to
      avoid building a test that merely “sees something changed” without
      knowing why."

      Action/result: Re-read input-line helpers before designing a fixture.

1267. Reported: "The helper confirms a useful exact sequence: `0x8a`
      repeatedly sends backspace through the same input character helper until
      visible length reaches zero, while `0x89` repopulates visible buffer
      `0x0fa4` from source buffer `0x0fce`. I’m going to add focused
      typed-input cases plus a small rectangle-signal comparator for the one
      path where exact glyph pixels are not yet modeled."

      Action/result: Planned typed-input probes and a bounded rectangle
      comparator for UI text rows.

1268. Reported: "I’m editing the probe harness in a contained way: exact
      full-frame comparisons stay the default, and the new rectangle checks are
      only for UI text rows where the source behavior is known but glyph
      rendering is not part of the local expected renderer yet."

      Action/result: Added optional rectangle checks without changing default
      exact frame comparison behavior.

1269. Reported: "The new cases separate three things: a baseline that typed
      input really appears, `0x8a` making that row black again, and `0x8a`
      followed by `0x89` bringing the typed buffer back. I’m adding the
      rectangle-check evaluator now so only the baseline/refresh glyph-bearing
      cases use it."

      Action/result: Added typed-input baseline, erase, and refresh candidate
      cases.

1270. Reported: "Rectangle checks are now a narrow alternate comparison path:
      they count specific colors inside a bounded logical row and return a
      normal match/mismatch report. I’m wiring unit tests around the new cases
      and the comparator before running QEMU."

      Action/result: Implemented `compare_rect_checks` and began focused unit
      coverage.

1271. Reported: "The unit tests now assert the new cases exist and that
      rectangle checks both match and fail when they should. I’m running the
      focused probe tests before the original-engine batch."

      Action/result: Added unit assertions for the new cases and comparator.

1272. Reported: "Focused tests pass. Next I’m running a four-case QEMU batch:
      status show, typed-input baseline, `0x8a` erase, and `0x8a` plus `0x89`
      refresh."

      Action/result: Focused unit tests passed and the first mixed QEMU batch
      was launched.

1273. Reported: "The batch is running from a single DOS snapshot now. It built
      the selected cases in base-case order, which is fine; I’m waiting for
      QEMU to finish and then I’ll inspect any mismatch rather than guessing."

      Action/result: Waited for the snapshot-based input/status QEMU run.

1274. Reported: "QEMU matched the typed-input baseline and the `0x8a` erase
      case, so that part is solid. The `0x8a`+`0x89` refresh case mismatched,
      which likely means my assumed source-buffer persistence is wrong or the
      refresh timing/path differs; I’m inspecting the report and capture before
      changing the model."

      Action/result: First QEMU run matched baseline/erase and exposed a
      refresh mismatch.

1275. Reported: "The mismatch is informative: `0x8a` and `0x8a`+`0x89`
      produce the same black-row capture, so the refresh did not restore from
      the source buffer as I predicted. I’m doing a small pixel-count check on
      the captured rows now to distinguish “text glyph” from “whole-row/
      background color.”"

      Action/result: Inspected the failed refresh capture and began row color
      counts.

1276. Reported: "That quick row-count script is still running a moment longer
      than expected, so I’m polling it instead of starting another image read."

      Action/result: Waited for the row-count inspection to complete.

1277. Reported: "The row counts explain the failure: before Enter, typed
      characters live in the visible/edit buffer, not the source string that
      `0x89` replays from. I’m correcting the `0x89` case to type `look` plus
      Enter first, so the source buffer at `0x0fce` should be populated before
      refresh."

      Action/result: Corrected the refresh fixture to use accepted input rather
      than unaccepted live-edit text.

1278. Reported: "The case is corrected to use the entered-command path instead
      of the live edit buffer. I’m rerunning the focused tests and then a
      smaller QEMU batch for the three input-line cases."

      Action/result: Renamed/corrected the `0x89` case and reran focused tests.

1279. Reported: "The corrected input batch is running. If it passes, `0x8a` is
      exact-row validated and `0x89` is validated as a source-buffer repaint,
      with the entered-command detail documented."

      Action/result: Launched the corrected input-line QEMU batch.

1280. Reported: "The corrected input batch passed: baseline visible typed text,
      `0x8a` erasing to a black row, and `0x89` repainting after Enter all
      matched. I’m running the status-line show case separately now, since the
      first mixed batch stopped before it."

      Action/result: Corrected input-line batch matched and the status-line
      QEMU case was launched.

1281. Reported: "With those matches, I can promote `0x70`, `0x89`, and
      `0x8a`: `0x70` as a status-row draw signal, `0x8a` as an exact typed-row
      erase, and `0x89` as repainting from the entered source buffer. I’m
      updating the evidence generator and tracker first."

      Action/result: Promoted `0x70`, `0x89`, and `0x8a` in the evidence plan.

1282. Reported: "The generator now points those opcodes at their behavior cases
      instead of smoke cases. I’m regenerating the opcode evidence page and
      then updating `PROGRESS.md` counts."

      Action/result: Updated `tools/logic_opcode_evidence.py` and regenerated
      `docs/src/logic_opcode_evidence.md`.

1283. Reported: "The generated evidence page is refreshed. I’m changing the
      tracker from 163 to 166 covered action opcodes, leaving 10 partial action
      rows."

      Action/result: Prepared the `PROGRESS.md` coverage-count update.

1284. Reported: "`PROGRESS.md` is updated. I’m tightening the opcode prose
      next, including the correction that `0x89` replays the entered command
      buffer, not the unaccepted live edit buffer."

      Action/result: Updated `PROGRESS.md` for 166/176 action opcode coverage.

1285. Reported: "The opcode chapter now records both the successful cases and
      the failed pre-Enter hypothesis for `0x89`. I’m adding that higher-level
      distinction to the runtime model so an implementation knows which input
      buffer is replayed."

      Action/result: Updated `docs/src/logic_bytecode.md` for `0x70`, `0x89`,
      and `0x8a`.

1286. Reported: "The runtime model now distinguishes live edit text from the
      entered source buffer. I’m updating the symbolic label map with the newly
      validated input/status helpers and their SQ2 addresses."

      Action/result: Updated `docs/src/runtime_model.md` with the live/source
      input-buffer distinction.

1287. Reported: "The symbolic map has new stable labels for the input
      character helper, erase, refresh, and source-to-visible append helper.
      I’m adding the QEMU batch commands/results to the compatibility chapter
      now."

      Action/result: Updated `docs/src/symbolic_labels.md` with input/status
      helper labels.

1288. Reported: "The compatibility chapter has the earlier text batches in the
      right spot, so I’m inserting the new input-refresh/status-show evidence
      alongside them and marking the old smoke batch as superseded for three
      more opcodes."

      Action/result: Added input-refresh and status-show QEMU commands/results
      to `docs/src/compatibility_testing.md`.

1289. Reported: "Compatibility docs now have both new batch commands and the
      failed `0x89` pre-Enter correction. I’m checking for any older “still
      smoke-only” wording that needs to be superseded."

      Action/result: Searched for stale smoke-only wording.

1290. Reported: "I found two stale “dispatch-smoke” summaries that predate the
      new behavior cases. I’m revising them to say which parts are now
      superseded instead of letting the docs contradict the tracker."

      Action/result: Revised stale text/status smoke summaries.

1291. Reported: "The stale summaries now point forward to the focused behavior
      probes. I’m making the high-level progress areas a little less stale as
      well, especially the input/text subsystem summary."

      Action/result: Updated high-level subsystem tracker wording in
      `PROGRESS.md`.

1292. Reported: "The subsystem tracker now reflects that visible input-line
      refresh/erase is no longer just smoke coverage. I’m appending the
      clean-room evidence section with the exact failed and successful QEMU
      batches, since the failed pre-Enter hypothesis is part of the useful
      history."

      Action/result: Prepared the clean-room notes append for input/status.

1293. Reported: "The notes file ends with the `0x6d` section, so I’m appending
      a new dated input/status section after it. This will preserve the
      row-count correction and the final promotion result."

      Action/result: Appended the input-line refresh/erase and status-line show
      notes section.

1294. Reported: "I’m going to keep pushing into the remaining partials. The
      trace-window pair `0x95`/`0x96` looks like the next feasible source-first
      target: the existing smoke case deliberately leaves flag 10 clear, but
      the disassembly says setting flag 10 should draw a boxed trace area."

      Action/result: Selected trace-window enable/configure as the next partial
      opcode pair.

1295. Reported: "I’m picking up exactly where the trace-window disassembly
      left off. The key thing I’m checking now is whether the visible effect of
      `0x95` can be validated without getting tangled in the trace pause
      mechanism that may intercept the very next opcode."

      Action/result: Resumed trace-window validation after context compaction.

1296. Reported: "The static trace code confirms two separate responsibilities:
      `0x96` only writes trace configuration globals, while `0x95` consults
      flag 10 and then draws the window through the normal boxed-text helper.
      I’m going to make the QEMU case line up with that split rather than
      treating it as a generic “some pixels changed” test."

      Action/result: Re-read trace docs/source and planned a focused enabled
      trace-window case.

1297. Reported: "There’s already an older note saying an enabled trace attempt
      showed a box but wasn’t in the comparison suite. I’m turning that into a
      repeatable case now, with a bounded rectangle predicate attached to the
      exact configured rows."

      Action/result: Located the prior trace-window attempt and began converting
      it into a stable fixture.

1298. Reported: "The case should end right after enabling trace, or use a
      one-shot branch, because the disassembly says an already-active `0x95`
      consumes an extra byte. That extra-byte behavior is precisely the kind of
      footgun I want the test to avoid while we’re validating the window draw
      itself."

      Action/result: Chose a one-shot trace fixture shape to avoid repeated
      active-state byte consumption.

1299. Reported: "I’ve confirmed the fixture harness can already express this
      cleanly: `compare_view=False` plus a rectangle check lets us validate the
      trace text/window pixels without pretending we have a full glyph model.
      Next I’m adding the enabled-trace case and a unit assertion for its
      expected bounds."

      Action/result: Prepared to add the trace case and unit assertion.

1300. Reported: "For the trace window’s vertical position, I’m using the source
      formula directly: top row is the configured input/status base row plus
      the trace row offset plus one. With `0x6f(0,0,5)` and `0x96(...,1,2)`,
      the box should land around logical rows 48..63."

      Action/result: Formed an initial trace rectangle hypothesis.

1301. Reported: "Small correction from the source formula: the trace vertical
      base is the first `0x6f` operand (`[0x05dd]`), not the status-row
      operand. I’m setting that deliberately in the fixture so the expected
      rectangle is derived from the actual globals the handler reads."

      Action/result: Corrected the vertical-position hypothesis before adding
      the fixture.

1302. Reported: "I’m making the trace case one-shot and omitting the validation
      sprite, because the trace dispatcher can pause before later bytecode. The
      observable we need is the boxed trace area itself, so the case will
      compare that surface directly."

      Action/result: Added `trace_window_enable_draws_box_when_flag10_set` and
      a unit assertion for its initial rectangle checks.

1303. Reported: "The fixture and unit assertion are in place. I’m running the
      focused tests first, then I’ll let QEMU tell us whether the exact row
      window is right or whether the text helper’s border math needs a tighter
      bound."

      Action/result: Ran focused unit tests for the trace fixture and rectangle
      comparator.

1304. Reported: "Focused tests pass. I’m running the enabled trace-window case
      through the original engine now; this one may pause inside the trace UI,
      but that’s acceptable because the screenshot is the evidence we need."

      Action/result: Focused tests passed and QEMU trace batch
      `trace_window_enable_001` was launched.

1305. Reported: "The enabled trace case matched on the first pass, so the
      source-derived row band is correct enough for automation. I’m inspecting
      the capture/report anyway before promoting the opcodes, because a match
      count alone doesn’t tell us whether we’re seeing the border, trace text,
      or both."

      Action/result: First trace QEMU run matched and report/capture inspection
      began.

1306. Reported: "The report path points to the fixture capture rather than the
      batch directory; I asked the quick inspector for the wrong copy. I’m
      rerunning that inspection against the actual saved PPM now, then I’ll
      update the evidence mappings."

      Action/result: Re-ran capture inspection against the correct fixture PPM.

1307. Reported: "The capture is stranger than a small bordered box: most of the
      upper logical rows are white, with a few trace-text/background pixels
      inside. That may be the boxed text helper filling a large text area, so
      I’m checking the image visually and then I’ll keep the automated predicate
      honest by describing exactly what it proves."

      Action/result: Inspected downsample color counts and prepared visual
      inspection.

1308. Reported: "The image viewer could not read that PPM directly, so I’m
      converting a PNG copy under `build/` for inspection. This is just for
      local sanity checking; the test continues to use the saved PPM."

      Action/result: Converted the trace PPM capture to PNG for visual
      inspection.

1309. Reported: "The visual check is useful: the helper draws a red-bordered,
      white-filled trace box with black trace text like `0: 12(94)`. I’m
      tightening the check to look for both the white fill and red border, so
      it’s less likely to pass on an unrelated white screen."

      Action/result: Identified the visible trace-window components from the
      capture.

1310. Reported: "The visual mapping says my first rectangle was broad enough
      but not ideal: the red border is around logical row 5 in the downsampled
      frame, while the white fill spans below it. I’m checking the local
      disassembly helpers briefly before tightening the predicate, because the
      helper’s coordinate system clearly is not the same as the 8-pixel
      text-row helpers."

      Action/result: Compared observed trace-window pixel rows against the
      source-derived coordinate expectations.

1311. Reported: "I’m revising the predicate into three signals: red border
      pixels, a large white fill area, and black trace text inside it. That
      matches the observed UI without requiring exact glyph reproduction."

      Action/result: Tightened the trace rectangle checks to require red,
      white, and black visible signals.

1312. Reported: "The trace predicate is now tighter. I’m rerunning the focused
      tests and then the same original-engine capture to make sure the stricter
      checks still pass."

      Action/result: Re-ran focused unit tests after tightening the predicate.

1313. Reported: "The stricter unit checks pass. I’m rerunning the QEMU trace
      case; if it matches again, I’ll promote `0x95` and `0x96` from
      dispatch-smoke to QEMU-validated in the evidence and tracker."

      Action/result: Launched final trace QEMU batch
      `trace_window_enable_002`.

1314. Reported: "The stricter QEMU trace capture matched. I’m updating the
      generated evidence mapping now so the opcode table points at the enabled
      trace-window case instead of the older flag-clear smoke case."

      Action/result: Final trace QEMU batch matched and evidence mapping update
      began.

1315. Reported: "`0x95` and `0x96` are moving out of the smoke bucket together:
      the enabled case exercises `0x96`’s stored row/height configuration and
      `0x95`’s flag-gated draw path in the original interpreter."

      Action/result: Updated `tools/logic_opcode_evidence.py` to map `0x95` and
      `0x96` to the enabled trace case.

1316. Reported: "The evidence generator is patched. I’m regenerating the opcode
      evidence chapter, then I’ll update `PROGRESS.md` from 166 to 168 covered
      action opcodes."

      Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

1317. Reported: "The generated evidence page is refreshed. I’m updating the
      tracker counts and the two trace rows now, then I’ll put the new behavior
      in the opcode/runtime/compatibility notes."

      Action/result: Prepared the `PROGRESS.md` promotion update.

1318. Reported: "The tracker still only has eight partial action opcodes after
      this promotion: `0x6e`, `0x83`, `0x8e`, `0xa3`, `0xa4`, `0xa9`, `0xaa`,
      and `0xad`. I’m making that count explicit in `PROGRESS.md`."

      Action/result: Updated `PROGRESS.md` to 168/176 action opcode coverage.

1319. Reported: "I’m updating the spec prose carefully here: the table still
      needs the disassembled control-flow details, while the paragraph below
      can carry the QEMU-visible result: red border, white fill, black trace
      text, and the pause-before-next-action behavior."

      Action/result: Began updating the trace opcode prose.

1320. Reported: "That patch missed the paragraph because the file has slightly
      different wrapping after earlier edits. I’m rereading the local section
      and applying the update against the exact text."

      Action/result: Re-read the exact `docs/src/logic_bytecode.md` trace block
      after a patch-context miss.

1321. Reported: "I found the exact block. The update also fixes wording from
      “input-line row” to “input-line base row,” which matches the `0x6f`
      storage we just rechecked."

      Action/result: Updated `docs/src/logic_bytecode.md` for the trace-window
      behavior and wording correction.

1322. Reported: "The opcode chapter now carries both the source-backed
      internals and the new QEMU-visible trace behavior. I’m adding the same
      higher-level interpretation to the runtime model: this is developer
      tracing state, not ordinary game logic state."

      Action/result: Updated `docs/src/runtime_model.md`.

1323. Reported: "The runtime model is updated. I’m refreshing the symbolic
      labels next so the cross-version map says the enabled draw path is now
      validated, not merely observed as a one-off mismatch."

      Action/result: Updated `docs/src/symbolic_labels.md` trace entries.

1324. Reported: "The symbolic map now points to the new trace batch. I’m adding
      the exact QEMU command/result to the compatibility chapter and marking
      the older trace smoke entry as superseded for `0x95`/`0x96`."

      Action/result: Updated `docs/src/compatibility_testing.md`.

1325. Reported: "The compatibility chapter has the old system batch grouped
      with several follow-ups. I’m adding a small focused trace subsection
      immediately after it, so future runs can reproduce the promotion without
      rerunning unrelated dialog cases."

      Action/result: Inserted the focused enabled trace-window command/result
      in the compatibility chapter.

1326. Reported: "Compatibility evidence is now reproducible. I’m appending a
      clean-room notes section with the source locations, the QEMU command, and
      the observed pixel/UI shape, then I’ll update the progress log."

      Action/result: Prepared the enabled trace-window notes section.

1327. Reported: "The notes section will include the failed/awkward history too:
      older enabled trace attempts were excluded because they polluted the
      validation sprite, but the new rectangle-check path lets us validate the
      trace UI directly."

      Action/result: Appended the enabled trace-window validation section to
      `docs/src/clean_room_executable_notes.md`.

1328. Reported: "I’m catching the historical progress log up now before doing
      more opcode work. This will be a longer append because it needs to
      preserve both the input/status work from before compaction and the
      trace-window work from this pass."

      Action/result: Appended progress-log entries for the input/status and
      trace-window work through this point.

1329. Reported: "The progress log is caught up through the trace promotion.
      I’m moving on to the remaining eight partial action opcodes now,
      starting by rereading their current descriptions so the next probe is
      driven by disassembly rather than trial-and-error."

      Action/result: Reviewed the remaining partial opcode descriptions.

1330. Reported: "Of the remaining eight, `0xa9` looks like the best next
      target: it has a visible restore path through the same saved-rectangle
      helper used by text windows, so we may be able to validate it with a
      modal message/window setup and an exact surface check."

      Action/result: Selected `0xa9` as the next validation candidate.

1331. Reported: "`0xa9` may not be easiest after all: ordinary message-display
      actions close their own text-window state before the following opcode,
      so a plain “show message then `0xa9`” would still only cover the inactive
      path. I’m checking the `0x0d0f`/input helper path because `0xa9` also
      clears that flag unconditionally, which may give us a cleaner behavior
      probe and cover `0xa3`/`0xa4` at the same time."

      Action/result: Redirected the probe design toward the input-width flag
      path shared by `0xa3`, `0xa4`, and `0xa9`.

1332. Reported: "The source gives a promising behavioral hook:
      `code.input.handle_input_char` caps visible input length at `0x24` when
      `[0x0d0f]` is set, but otherwise uses `0x28 - len(string_slot_0)`. I’m
      adding long-input probes that make that cap visible, which should cover
      `0xa3`, `0xa4`, and the unconditional `0xa9` clear path."

      Action/result: Began adding long-input probes based on the disassembled
      input-width calculation.

1333. Reported: "The three long-input cases are in the harness. I’m adding
      unit assertions for their presence and expected color-count thresholds
      before trying them in QEMU."

      Action/result: Added the initial `0xa3`/`0xa4`/`0xa9` input-width cases
      to the probe harness.

1334. Reported: "The unit assertions are in place. I’m running the focused
      tests now; if those pass, I’ll run a three-case QEMU batch to tune the
      row-count thresholds against the real interpreter."

      Action/result: Added focused unit tests for the input-width cases.

1335. Reported: "Focused tests pass. I’m running the original-engine batch for
      `0xa3`, `0xa4`, and `0xa9` now; this will tell us whether the
      source-derived input-width effect is visible enough for stable
      compatibility checks."

      Action/result: Started the first QEMU input-width validation batch.

1336. Reported: "The three-case batch is running from one snapshot. I’m
      waiting for QEMU to finish rather than launching anything else, since
      the harness owns the shared VNC/socket while it runs."

      Action/result: Waited on the snapshot QEMU batch.

1337. Reported: "The `0xa3` case matched, but the `0xa4` case did not:
      clearing the flag didn’t reduce visible text as much as my first
      threshold expected. I’m inspecting the capture and counts before deciding
      whether this is a threshold issue or a wrong model of when the long slot
      is consulted."

      Action/result: Identified the first input-width mismatch and began
      inspecting capture counts.

1338. Reported: "The mismatch is large: the `0xa4` case still has 548 white
      pixels in the input row. That suggests the long string in slot 0 may not
      be affecting the cap because slot 0 is being cleared or not the same
      slot `0x3652` measures; I’m waiting for the detailed row-count script and
      then I’ll adjust based on the source path."

      Action/result: Captured the large row-count mismatch for the first
      `0xa4` attempt.

1339. Reported: "The row counts show `0xa3` and `0xa4` looked identical
      because my long slot-0 string was visible prompt text, not just an
      invisible cap. I’m switching that slot to a long run of spaces: same
      length for the source formula, but no glyph pixels from the prefix
      itself."

      Action/result: Changed the fixture string slot to long blank prompt text.

1340. Reported: "The fixtures now use a long blank string slot, so any white
      pixels on the row should come from typed live input rather than the
      slot-0 prefix. I’m rerunning the focused tests, then the same three-case
      QEMU batch."

      Action/result: Prepared the second input-width batch.

1341. Reported: "The focused tests still pass. I’m rerunning the input-width
      QEMU batch without changing the thresholds yet, so the original engine
      tells us whether the long-blank-slot model is right."

      Action/result: Started the second QEMU input-width batch.

1342. Reported: "The rerun is still inside QEMU. I’m polling it rather than
      starting another disassembly pass, since these cases depend on the shared
      snapshot harness completing cleanly."

      Action/result: Waited on the second snapshot QEMU batch.

1343. Reported: "Now the `0xa3` case is the one that mismatched, which is good
      evidence the prompt pollution is gone. I’m checking the exact row count;
      if it’s just below the threshold we can tune it, but if it is near zero
      then the blank slot may be suppressing typed input differently than
      expected."

      Action/result: Observed that the long blank prompt moved the visible
      effect rather than removing it.

1344. Reported: "The source model is still useful, but the visible signal is
      one row lower: the long blank prefix moves the typed characters into the
      next text row, so `0xa3` shows glyphs at logical Y 48..55. I’m retargeting
      the checks there; `0xa4`/`0xa9` should keep that wrapped row empty if
      they clear the flag."

      Action/result: Retargeted input-width checks to the wrapped text row.

1345. Reported: "The expected checks now target the wrapped row. I’m rerunning
      the focused unit test and then the three-case QEMU batch again, this time
      with all three cases able to exercise the same wrapped-row predicate."

      Action/result: Started the third validation attempt.

1346. Reported: "The unit check passes. I’m rerunning the QEMU batch; this one
      should distinguish `0xa3` from both clearing paths if the
      disassembly-derived cap model is correct."

      Action/result: Began another snapshot QEMU run for the retargeted checks.

1347. Reported: "The batch is running. This pass is a good example of QEMU as
      confirmation rather than discovery: the key distinction came from
      `0x3652`; QEMU is just helping pin down the visible row where the effect
      lands."

      Action/result: Waited on the retargeted QEMU batch.

1348. Reported: "`0xa3` now matches on the wrapped row, but `0xa4` still shows
      wrapped-row pixels. That means either `0xa4` is not being reached before
      typing, or the long-slot cap is not recomputed the way I expected after
      the flag clear. I’m checking the report and source-flow details before
      changing the fixture again."

      Action/result: Investigated the remaining wrapped-row mismatch.

1349. Reported: "The `0xa4` mismatch is actually a full white wrapped row,
      which looks like the blank prefix itself wrapped and painted as a white
      text rectangle, not necessarily typed characters. I’m waiting on the row
      breakdown and then I’ll avoid relying on wrapped text rows for this flag
      test."

      Action/result: Distinguished white row fill from typed glyph pixels.

1350. Reported: "A memory-backed check is probably the right tool for these
      tiny globals. Before adding anything, I’m reading the existing QEMU
      snapshot helper to see if we can extend it narrowly with monitor `xp`
      reads instead of building a separate debugger harness."

      Action/result: Considered, but did not need, a monitor-backed memory
      check for this flag.

1351. Reported: "There is a usable visible signal after all, but it’s the
      inverse of my first check: the wrapped row is white fill in both paths,
      while only the `0xa3` path contains black glyph pixels from accepted
      typed characters. I’m changing the cases to compare black glyph pixels,
      which aligns with the source distinction and the captures."

      Action/result: Changed the predicate from white fill to black glyph
      pixels.

1352. Reported: "The harness now checks for black glyph pixels in the wrapped
      row. I’m updating the unit expectations to match that corrected signal,
      then I’ll rerun all three original-engine cases."

      Action/result: Updated the harness and test expectations.

1353. Reported: "The unit expectation is corrected. I’m running the focused
      unit test and then a final QEMU pass for `0xa3`, `0xa4`, and `0xa9` with
      the black-glyph predicate."

      Action/result: Started focused tests for the corrected predicate.

1354. Reported: "The focused unit test passes. I’m rerunning the three-case
      QEMU batch; this should also exercise the `0xa9` clearing path now that
      `0xa4` is expected to pass."

      Action/result: Started the final QEMU input-width batch.

1355. Reported: "The batch is running again. If it passes, I’ll promote
      `0xa3` and `0xa4` for the input-width flag behavior, and `0xa9` for the
      unconditional flag clear while leaving its active saved-rectangle restore
      source-backed."

      Action/result: Waited on the final input-width batch.

1356. Reported: "The corrected input-width batch passed all three cases. I’m
      promoting `0xa3`, `0xa4`, and `0xa9` now, with the caveat documented that
      `0xa9`’s active saved-rectangle restore remains source-backed while its
      unconditional `[0x0d0f]` clear is QEMU-validated."

      Action/result: Promoted `0xa3`, `0xa4`, and `0xa9`.

1357. Reported: "I’m updating the evidence generator first so the generated
      opcode evidence table agrees with the new QEMU batch before I touch the
      prose tracker."

      Action/result: Updated `tools/logic_opcode_evidence.py`.

1358. Reported: "The generator now points at the input-width behavior cases.
      I’m regenerating the evidence page and then bumping the tracker to
      171/176 covered action opcodes."

      Action/result: Regenerated the logic opcode evidence chapter.

1359. Reported: "The evidence chapter is regenerated. I’m updating
      `PROGRESS.md`; after this, the only partial action opcodes left should be
      `0x6e`, `0x83`, `0x8e`, `0xaa`, and `0xad`."

      Action/result: Prepared the tracker update.

1360. Reported: "The tracker is updated to 171/176. I’m revising the opcode
      prose next so it explains the actual high-level behavior: `[0x0d0f]`
      changes the live input width calculation, and `0xa9` always clears that
      flag even without an active text window."

      Action/result: Updated the opcode prose for input-width state.

1361. Reported: "The row updates need a smaller patch because one of the
      surrounding summaries has been rewrapped by earlier edits. I’m applying
      the opcode-row changes first, then I’ll adjust the two stale summary
      paragraphs against their exact text."

      Action/result: Split the opcode chapter patch after a context miss.

1362. Reported: "I’ve got the exact paragraphs. I’m replacing the opcode rows
      and then cleaning the old “smoke-only” summaries so the chapter doesn’t
      contradict the new QEMU evidence."

      Action/result: Removed stale smoke-only wording for promoted opcodes.

1363. Reported: "The opcode chapter is now consistent. I’m updating the
      runtime model’s text/alternate-mode state row so implementers see why
      `[0x0d0f]` matters outside a one-line opcode description."

      Action/result: Updated the runtime model.

1364. Reported: "I accidentally triggered an empty web search while switching
      tools; no external material was consulted or used. I’m continuing with
      the local runtime-model edit."

      Action/result: Recorded that the accidental empty search produced no
      external source material.

1365. Reported: "The runtime model now includes the input-width state. I’m
      updating the symbolic label map with stable labels for the input-width
      flag and the small `0xa3`/`0xa4` action handlers, so future interpreter
      versions can be compared by role rather than raw address."

      Action/result: Began updating symbolic labels for input-width state.

1366. Reported: "The symbol map already had `code.text.close_window_state`;
      I’m expanding it and adding the flag/action labels in the same Text/Input
      section."

      Action/result: Added and expanded text/input symbolic labels.

1367. Reported: "The symbolic labels now include the width flag and its
      handlers. I’m adding the successful `input_width_flag_004` batch to the
      compatibility chapter, with a short note about what the black-glyph
      predicate proves."

      Action/result: Prepared compatibility evidence for the input-width batch.

1368. Reported: "The compatibility chapter’s text/input section is the right
      home for this, so I’m placing the input-width batch between the
      prompt/text-attribute probes and the older text/status smoke batch."

      Action/result: Inserted the input-width compatibility evidence.

1369. Reported: "The compatibility chapter now has the reproducible successful
      batch. I’m appending the clean-room notes with the failed threshold/string
      attempts too, because those corrections explain why the final black-glyph
      predicate is the right one."

      Action/result: Added the input-width observations and corrections to the
      clean-room notes.

1370. Reported: "The input-width work is documented. I’m continuing into the
      last five partials now. The next likely candidate is `0x83`, because it
      writes global `[0x0139]`, and that same global is touched by first-object
      motion helpers, so there may be a source-driven movement probe available."

      Action/result: Started the `0x83` investigation from disassembly.

1371. Reported: "`0x83` itself is extremely small in the disassembly: it only
      writes zero to `[0x0139]`. I’m looking at consumers of that word now; if
      no existing script-visible condition depends on it, I’ll keep it
      source-backed rather than inventing a brittle visual test."

      Action/result: Confirmed that the action body only clears `[0x0139]`.

1372. Reported: "The consumer is the main cycle’s direction mirror between
      object 0 byte `+0x21` and global byte `[0x000f]`. I’m reading that small
      source block directly; if `0x83` flips which side wins, we may be able to
      observe it with an existing object field getter and a conditional draw."

      Action/result: Identified the main-cycle direction-mirror consumer for
      `[0x0139]`.

1373. Reported: "I’ll keep moving from `PROGRESS.md` and avoid waiting for
      repeated “continue” prompts. First I’m catching the progress log up with
      the recent input-width and `0x83` investigation updates, then I’ll
      continue from the disassembly-backed direction-mirror probe."

      Action/result: Resumed the `PROGRESS.md` task stream and prepared to
      update the historical progress log.

1374. Reported: "The tracker confirms the remaining partial action opcodes are
      `0x6e`, `0x83`, `0x8e`, `0xaa`, and `0xad`. I’m adding the recent updates
      to the historical log now, then I’ll build the `0x83` probe around the
      main-cycle object0 direction mirror."

      Action/result: Confirmed the partial opcode list and appended prior
      progress-log entries through the input-width work.

1375. Reported: "The progress log is caught up. Now I’m reading the existing
      object-field probe helpers so the `0x83` case can reuse established
      fixture patterns instead of adding a one-off script shape."

      Action/result: Reviewed object field setter/getter fixture helpers.

1376. Reported: "The existing harness already has clean helpers for setting and
      reading object byte `+0x21`, which is exactly what the `0x83` consumer
      needs. I’m checking the fixture builder now so the new case can span
      multiple interpreter cycles without relying on timing guesswork."

      Action/result: Confirmed `0x56`/`0x57` helper coverage and inspected
      multi-cycle fixture support.

1377. Reported: "The case can be cycle-structured with two flags: phase 0 seeds
      object0 direction and clears `[0x0139]`; phase 1 lets the main loop copy
      that into global `[0x000f]`, then sets `[0x0139]`; phase 2 verifies the
      global value was copied back into object0. I’m checking the exact helper
      bytes for nested `if` and flag conditions before patching it in."

      Action/result: Designed the first attempted `0x83` multi-cycle fixture.

1378. Reported: "The phase plan is sound: it observes `0x83` indirectly
      through `0x84` and `0x57`, after the main loop has had a full cycle to
      perform each mirror direction. I’m going to add this as a narrowly named
      compatibility case, then run it alone under QEMU."

      Action/result: Began adding the attempted `0x83` compatibility case.

1379. Reported: "I found a useful detail: the existing object helpers normally
      use object 10, but the main-loop mirror is specifically object 0. The new
      fixture will initialize object 0 as a normal object entry, then use the
      same `+0x21` setter/getter to observe the global mirror."

      Action/result: Adjusted the attempted fixture to target object 0.

1380. Reported: "One subtlety: if phase 0 simply sets a flag, phase 1 would run
      later in the same logic pass. I’m using an explicit `end` inside each
      successful phase so the handoff happens at the next main cycle, where the
      disassembled mirror code actually runs."

      Action/result: Added phase-ending `end` actions to the attempted fixture
      design.

1381. Reported: "The probe case is in the harness. I’m adding a unit assertion
      for it now, plus a small structural test that its bytecode includes the
      phase-ending `end` actions and both `0x83`/`0x84`, so future edits do not
      accidentally collapse it back into a same-cycle test."

      Action/result: Added temporary unit assertions for the attempted fixture.

1382. Reported: "The focused structural test is added. I’m running just the
      probe tests that cover the case list and this new multi-cycle shape
      before I let QEMU execute it."

      Action/result: Ran focused unit tests for the attempted fixture; they
      passed.

1383. Reported: "The unit checks pass. I’m running the single `0x83`
      original-engine case now; if it matches, we’ll have a behavior-level
      validation of the selector bit rather than only a dispatch smoke."

      Action/result: Started QEMU batch `object0_direction_mirror_001`.

1384. Reported: "That command bounced because this particular harness doesn’t
      use a boolean `--snapshot`; it has snapshot image path options and
      otherwise runs its snapshot path by default. I’m rerunning with the
      harness’s actual CLI."

      Action/result: Corrected the logic probe command after the ambiguous
      `--snapshot` option.

1385. Reported: "The first QEMU run completed but did not match. I’m reading
      the generated comparison report and capture summary before changing
      anything; the key question is whether the phase logic failed to reach
      phase 2 or whether the mirror copied a different value than expected."

      Action/result: Inspected QEMU report `object0_direction_mirror_001`.

1386. Reported: "The mismatch is interesting, not a total failure: the
      validation sprite did draw, but its pixels are a different cel than the
      default expected one. That suggests the probe reached phase 2 and changed
      the object/direction state, but the transient validation draw is being
      influenced by direction-related selection. I’m going to identify the
      actual cel before deciding whether the behavioral check should expect
      that variant."

      Action/result: Compared the capture against local view/cel renders.

1387. Reported: "The mismatch is only inside the validation sprite, which is
      reassuring: the draw condition fired. I’m going to use a quick local
      comparison against available view/group/frame combinations to identify
      what the real engine drew."

      Action/result: Determined that an exact transient/persistent marker was
      not a clean signal.

1388. Reported: "The real engine drew view 11 frame 7, even though the
      validation helper requested frame 0, because the transient draw path is
      also seeing the direction state. That is useful evidence, but for this
      opcode probe I want the pass/fail signal to be just the object0 mirror,
      so I’m switching the conditional marker to a persistent object with
      explicit setup instead of the transient validation helper."

      Action/result: Reworked the attempted fixture marker to use a persistent
      object.

1389. Reported: "The marker now uses object 10 with bit `0x2000` set, so its
      cel choice should stay fixed while the condition still depends on object0
      byte `+0x21`. I’m rerunning the focused structural test, then the same
      single QEMU case."

      Action/result: Ran the updated attempted fixture; it still mismatched.

1390. Reported: "It still reaches a mismatch, so I’m inspecting the new report.
      If this is another cel/priority difference we can correct the expected
      marker; if there is no marker, the phase logic needs adjustment."

      Action/result: Inspected `object0_direction_mirror_002`.

1391. Reported: "Still mismatched. I’m checking whether `0x46` actually
      stabilizes the marker in this setup or whether persistent-object
      activation sets the animation bit after the clear."

      Action/result: Investigated persistent marker frame advancement.

1392. Reported: "The remaining mismatch is animation timing: the persistent
      marker advances to frame 7 during the draw wait. Since this probe is
      about `0x83`, I’m using the already-documented `0x46` action to clear the
      animation bit on the marker so the expected cel stays frame 0."

      Action/result: Added `0x46` to the attempted marker setup.

1393. Reported: "The marker now suppresses automatic group selection and frame
      cycling before activation. I’m doing one more focused unit check and QEMU
      run for `0x83`."

      Action/result: Ran focused unit check and QEMU batch
      `object0_direction_mirror_003`; it still mismatched.

1394. Reported: "Still mismatched. I’m checking whether `0x46` actually
      stabilizes the marker in this setup or whether persistent-object
      activation sets the animation bit after the clear."

      Action/result: Confirmed the marker still advanced.

1395. Reported: "The marker still advances to frame 7, so activation probably
      sets the animation bit after my clear. I’m moving `0x46` after
      activation; that should leave the marker active but non-advancing during
      the subsequent frame update."

      Action/result: Reordered the marker actions.

1396. Reported: "I’ve reordered the marker actions. I’m rerunning the single
      QEMU case; if this still advances, I’ll just set the expected frame to
      the observed stable frame and document why."

      Action/result: Ran QEMU batch `object0_direction_mirror_004`; it still
      mismatched.

1397. Reported: "The marker remains animated, so an exact-frame comparison is
      the wrong assertion for this probe. I’m switching the case to a rectangle
      predicate that only asks “did the conditional marker place non-background
      sprite pixels here?”, which keeps the test about the `0x83` mirror
      instead of frame timing."

      Action/result: Reconsidered the validation predicate after confirming the
      capture had no marker.

1398. Reported: "The capture shows no marker at all, so the phase condition is
      false. I’m generating a disposable diagnostic fixture under `build/` that
      draws a marker at different X positions for object0 direction values
      `0..8`; this will tell us what `0x57` reads after the mirror sequence
      without adding a speculative permanent test."

      Action/result: Generated disposable diagnostic
      `manual_direction_value_cases.json`.

1399. Reported: "The disposable case is generated. I’m running it through QEMU
      with comparison against a blank picture, so any drawn marker will show up
      as a mismatch bbox and we can map that X position back to the value."

      Action/result: Ran `object0_direction_value_diag_001`; it matched blank,
      showing no value marker in `0..8`.

1400. Reported: "The value diagnostic stayed blank, which means either phase 2
      is not being reached or `+0x21` is outside `0..8`. I’m generating one
      more disposable variant with an unconditional phase-2 marker, so we can
      separate phase-control failure from an unexpected direction byte."

      Action/result: Generated disposable diagnostic
      `manual_direction_phase_cases.json`.

1401. Reported: "The second diagnostic uses high-numbered flags as well, just
      in case the earlier phase flags were touched by interpreter/game state.
      I’m running it now."

      Action/result: Ran `object0_direction_phase_diag_001`.

1402. Reported: "The phase-2 marker did draw, so the multi-cycle flag
      scaffolding is fine. I’m reading the bbox and pixel locations now to
      infer which value-specific marker, if any, appeared alongside the
      unconditional one."

      Action/result: Mapped the value marker to direction value `0`.

1403. Reported: "The phase-2 getter reads direction `0`, not `6`. That
      suggests the first object entry’s direction is being cleared before the
      next top-of-cycle mirror can seed `[0x000f]`, likely because the object is
      inactive/stationary. I’m testing a source-driven variant that activates
      object 0 during the seed phase so its direction byte survives long enough
      to be mirrored."

      Action/result: Generated active-object disposable diagnostic.

1404. Reported: "The active-object diagnostic is generated. I’m running it now;
      the value marker should tell us whether activation preserves the seed
      direction."

      Action/result: Ran `object0_direction_active_diag_001`.

1405. Reported: "The active-object diagnostic produced a marker. I’m extracting
      the X buckets now to map it back to the direction value."

      Action/result: The active-object variant still mapped to direction value
      `0`.

1406. Reported: "Activating object 0 still yields value `0`, so the issue is
      not just inactive-object cleanup. I’m going back to the disassembly
      references for `[0x0139]` and `[0x000f]`; something after the action may
      be restoring the selector or clearing the global before the next cycle."

      Action/result: Re-read references to `[0x0139]` and `[0x000f]`.

1407. Reported: "The main-cycle source explains the failed fixture: after
      logic returns, the cycle writes global `[0x000f]` back into object0
      `+0x21` unconditionally. So a script-set object0 direction after the
      top-of-cycle mirror is clobbered before the next cycle. I’m reading the
      neighboring code and references now to document `0x83` precisely rather
      than forcing a misleading QEMU test."

      Action/result: Identified the cycle-end global-to-object restore.

1408. Reported: "At this point the clean result is source-backed, not
      QEMU-promoted: `0x83` is a selector write whose effect occurs before
      logic, while our script-level attempts happen after that point and are
      clobbered by the cycle-end global-to-object copy. I’m going to document
      that timing explicitly and mark `0x83` covered as source-backed rather
      than pretending the failed fixture was a useful compatibility test."

      Action/result: Decided to promote `0x83` as source-backed.

1409. Reported: "I’m updating the evidence generator so `0x83` is recorded as
      source-backed with a timing caveat, not as a QEMU smoke. Then I’ll update
      the opcode prose and progress tracker to reduce the partial list to
      four."

      Action/result: Prepared the evidence-generator update.

1410. Reported: "Since the script-level `0x83` fixture does not prove the
      selector behavior, I’m removing it from the reusable probe registry
      rather than leaving a misleading failing case around. The failed attempts
      will stay documented in the notes as evidence about cycle timing."

      Action/result: Removed the attempted reusable helper from
      `tools/logic_interpreter_probe.py`.

1411. Reported: "The helper is removed. I’m removing the corresponding registry
      entry and unit assertions next, then the evidence generator will carry
      `0x83` as source-backed."

      Action/result: Removed the attempted base-case entry.

1412. Reported: "The failing `0x83` registry case is gone. I’m cleaning up the
      unit test references that were only there to protect that abandoned
      fixture."

      Action/result: Removed the temporary unit assertions.

1413. Reported: "The abandoned fixture is cleaned out. I’m running the
      case-list unit test once to make sure the registry is back to a
      consistent shape before changing the docs."

      Action/result: The case-list unit test passed.

1414. Reported: "The registry test passes. I’m changing the generated evidence
      matrix so `0x83` has its own source-backed note about the main-cycle
      mirror and the failed script-level probe timing."

      Action/result: Added `SOURCE_BACKED_ACTIONS` evidence for `0x83`.

1415. Reported: "The generator now treats `0x83` as a source-backed timing
      primitive rather than a smoke. I’m regenerating the evidence chapter."

      Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

1416. Reported: "The evidence chapter is regenerated. I’m updating
      `PROGRESS.md` now: `0x83` is covered as source-backed, leaving `0x6e`,
      `0x8e`, `0xaa`, and `0xad` partial."

      Action/result: Updated `PROGRESS.md` to 172/176 covered action opcodes.

1417. Reported: "The tracker is updated. I’m expanding the opcode prose next,
      because implementers need the timing rule: `0x83` affects the next
      cycle’s pre-logic mirror, but logic-script attempts to seed object0
      direction after that point are overwritten at cycle end."

      Action/result: Began updating `docs/src/logic_bytecode.md`.

1418. Reported: "The top-level cycle section already mentions the mirror, but
      it doesn’t say which branch corresponds to `[0x0139] == 0` or mention the
      cycle-end copy. I’m adding that there and in the `0x83` opcode row."

      Action/result: Added branch direction and cycle-end restore prose.

1419. Reported: "I found two older smoke summaries that still list opcodes
      we’ve since promoted or source-backed. I’m cleaning those alongside the
      `0x83` timing prose so the book stays internally consistent."

      Action/result: Updated old smoke summaries in the bytecode chapter.

1420. Reported: "The logic bytecode chapter now carries the exact branch
      direction and the failed-probe timing reason. I’m updating the
      compatibility chapter’s old smoke summary to stop claiming `0x83` is only
      smoke-covered."

      Action/result: Updated `docs/src/compatibility_testing.md`.

1421. Reported: "Compatibility notes are consistent now. I’m adding the same
      high-level timing rule to the runtime model’s motion/object lifecycle,
      since that’s where an implementer is likely to look when modeling object0
      direction and keyboard/global direction state."

      Action/result: Added an object0/global direction mirror row to
      `docs/src/runtime_model.md`.

1422. Reported: "The runtime model now has the special mirror row. I’m updating
      the symbolic label map with stable data labels for `[0x0139]` and
      `[0x000f]`, plus a clearer main-cycle note for cross-version comparison."

      Action/result: Began updating `docs/src/symbolic_labels.md`.

1423. Reported: "The label file already has the first-object pointer, so I’m
      placing the direction mirror globals in that same data section and
      sharpening the main-cycle description."

      Action/result: Added `data.motion.global_direction_000f` and
      `data.motion.direction_mirror_selector_0139`.

1424. Reported: "The symbolic labels now include the two mirror globals. I’m
      appending a clean-room notes section with the disassembly commands, the
      failed/diagnostic QEMU attempts, and the conclusion that `0x83` is
      source-backed because its branch point is outside script control."

      Action/result: Prepared the clean-room notes section.

1425. Reported: "The notes currently end at the input-width promotion, so I’m
      adding a new dated section immediately after it for the `0x83`
      source pass and diagnostics."

      Action/result: Appended the `0x83` direction-mirror timing section to
      `docs/src/clean_room_executable_notes.md`.

1426. Reported: "The clean-room notes now capture the `0x83` investigation.
      I’m catching the progress log up again before moving to the next
      remaining partial opcode, since this pass had several diagnostic detours
      worth preserving."

      Action/result: Prepared to append the `0x83` investigation progress-log
      entries.

1427. Reported: "The progress log is caught up through the `0x83` source-backed
      promotion. I’m moving on to the four remaining partials now; I’ll start
      with `0xad` because it is small, source-local, and likely another
      timing/global side effect we can either document cleanly or validate with
      a narrow probe."

      Action/result: Began the `0xad` source pass.

1428. Reported: "`0xad` is a tiny handler too: `inc byte [0x1530]` and return.
      I’m reading the keyboard-interrupt consumer around `0x6036` because that
      byte is only useful if we can explain when the nonzero value changes
      observable behavior."

      Action/result: Disassembled the action body and keyboard IRQ consumer.

1429. Reported: "The consumer is clearer now: `[0x1530]` is a nonzero gate in
      the keyboard IRQ path. On tracked key release, if the per-key pressed
      latch was set and `[0x1530]` is nonzero, the ISR calls the same event
      enqueue/display-input helper path. I’m checking where the tracked-key
      table is initialized before turning this into a source-backed spec row."

      Action/result: Identified the tracked-key release gate behavior.

1430. Reported: "The only static hits for `[0x1530]` are the action increment
      and the keyboard ISR test, so this looks like an enable/count gate rather
      than ordinary game state. I’m checking the existing event-helper labels
      so the docs can name the called helper symbolically instead of using a
      raw address."

      Action/result: Reused `code.input.enqueue_event` as the symbolic helper
      name for the IRQ enqueue call.

1431. Reported: "I’m treating `0xad` as source-backed: the action body and the
      only observed consumer are both local and compact, while building a QEMU
      fixture around raw IRQ key-release timing would be brittle. I’m updating
      the evidence matrix and docs to call it a key-release enqueue gate."

      Action/result: Decided to promote `0xad` as source-backed.

1432. Reported: "The generator has a specific source-backed entry for `0xad`.
      I’m removing it from the smoke-only set and regenerating the evidence
      page."

      Action/result: Added `0xad` to source-backed evidence and prepared to
      remove its smoke classification.

1433. Reported: "`0xad` is no longer classified as smoke in the generator. I’m
      regenerating the matrix now."

      Action/result: Regenerated `docs/src/logic_opcode_evidence.md`.

1434. Reported: "The evidence page is regenerated. I’m updating `PROGRESS.md`
      so `0xad` is covered as source-backed, leaving only `0x6e`, `0x8e`, and
      `0xaa` partial."

      Action/result: Updated `PROGRESS.md` to 173/176 covered action opcodes.

1435. Reported: "The tracker is updated. I’m expanding the raw event queue
      section and the `0xad` opcode row so the source-backed status has real
      semantics, not just “increments a byte.”"

      Action/result: Updated `docs/src/logic_bytecode.md` for the IRQ
      release-event gate.

1436. Reported: "The bytecode chapter now links `0xad` to the IRQ release path.
      I’m updating the compatibility chapter so the old diagnostics batch is
      clearly just smoke for `0x8e`/`0xaa`, while `0xad` is source-backed."

      Action/result: Updated `docs/src/compatibility_testing.md`.

1437. Reported: "The compatibility chapter is consistent. I’m adding the
      key-release gate to the runtime model’s input/event lifecycle so
      implementation readers know `0xad` is an input subsystem detail."

      Action/result: Prepared the runtime-model update.

1438. Reported: "The event/edit loop row is the right place for this; I’m
      extending its contract rather than adding another separate section."

      Action/result: Updated `docs/src/runtime_model.md`.

1439. Reported: "The runtime model now mentions the release-event gate. I’m
      adding symbolic labels for the IRQ hook and its small data tables so
      future version comparisons can find this feature without relying on raw
      addresses."

      Action/result: Prepared symbolic-label additions for the IRQ hook and
      tables.

1440. Reported: "The input data table section already has the queue and key-map
      entries, so the release-tracking tables fit cleanly there. I’m patching
      both code and data labels together."

      Action/result: Added `code.input.keyboard_irq_hook` and related data
      labels.

1441. Reported: "The symbol map now names the IRQ hook and its latch/gate
      tables. I’m appending a short clean-room note for `0xad`, including the
      disassembly evidence and why it stays source-backed instead of
      QEMU-validated."

      Action/result: Appended the `0xad` key-release enqueue gate section to
      `docs/src/clean_room_executable_notes.md`.

1442. Reported: "The `0xad` clean-room note is in place. I’m logging the
      `0xad` work in `progress_log.md` before moving on to the last three
      partial opcodes."

      Action/result: Appended the `0xad` progress-log entries.

1443. Reported: "`0xad` is logged. I’m moving to `0x8e` next, since it sits in
      the resource-event replay system we already documented; the goal is to
      tighten its exact capacity/reset behavior from disassembly and see
      whether existing replay probes already cover the observable contract."

      Action/result: Began the `0x8e` source pass.

1444. Reported: "`0x8e` is already well supported by the resource-event source
      pass: it writes `data.event.pair_capacity`, wraps
      `code.event.reset_pair_buffer` with flush/rebuild helpers, and the reset
      helper’s capacity/count semantics are documented. I’m going to promote it
      as source-backed rather than manufacture a replay fixture that would
      mostly re-test the larger `0x8c` replay machinery."

      Action/result: Decided to promote `0x8e` as source-backed.

1445. Reported: "That patch missed because the smoke table has already
      collapsed to a shorter shape after the previous edits. I’m re-reading the
      exact generator block and applying a narrower patch."

      Action/result: Re-read `tools/logic_opcode_evidence.py` after a
      patch-context miss.

1446. Reported: "The generator block is straightforward. I’m adding `0x8e` to
      the source-backed map and leaving only `0x6e` in the smoke map."

      Action/result: Updated the evidence generator for `0x8e`.

1447. Reported: "`0x8e` is now source-backed in the generator. I’m regenerating
      the evidence page and updating the tracker to 174/176."

      Action/result: Regenerated the logic opcode evidence chapter.

1448. Reported: "The evidence page is regenerated. I’m updating `PROGRESS.md`;
      after this only `0x6e` and `0xaa` remain partial in the action table."

      Action/result: Updated `PROGRESS.md` to 174/176 covered action opcodes.

1449. Reported: "The tracker now leaves two partial actions. I’m expanding the
      `0x8e` row and cleaning the old smoke paragraph so it no longer treats
      event capacity reset as merely dispatch-smoked."

      Action/result: Updated `docs/src/logic_bytecode.md`.

1450. Reported: "The bytecode chapter now treats `0x8e` as the source-backed
      event log capacity reset. I’m updating the compatibility chapter’s
      diagnostics summary to leave only `0xaa` as smoke-covered."

      Action/result: Updated `docs/src/compatibility_testing.md`.

1451. Reported: "Compatibility notes now align with the source-backed
      promotion. I’m checking the runtime model’s resource-event section; it
      likely already has the necessary capacity/reset contract, but I’ll add a
      line if it’s missing."

      Action/result: Reviewed the runtime model resource lifecycle.

1452. Reported: "The resource lifecycle table mentions replay/recording but not
      the capacity reset itself. I’m adding a small paragraph after the table so
      `0x8e` is visible in the high-level model."

      Action/result: Updated `docs/src/runtime_model.md`.

1453. Reported: "The runtime model now has a direct `0x8e` capacity-reset
      paragraph. I’m tightening the existing symbolic label note for
      `code.event.set_pair_capacity_action` with the same semantics."

      Action/result: Updated `docs/src/symbolic_labels.md`.

1454. Reported: "The symbolic map is updated. I’m adding a short `0x8e`
      clean-room note that ties the handler, reset helper, and existing replay
      evidence together."

      Action/result: Appended the `0x8e` event-pair capacity reset section to
      `docs/src/clean_room_executable_notes.md`.

1455. Reported: "`0x8e` is documented. I’m moving to `0xaa`, the
      save-description copy action. There was an earlier failed attempt to
      force the buffer; I’ll re-read the save selector/source path first so we
      can decide whether it is cleanly source-backed or worth a new QEMU
      fixture."

      Action/result: Began the `0xaa` source pass.

1456. Reported: "The `0xaa` source path is compact and the earlier QEMU attempt
      patched the wrong layer: the action copies from the interpreter’s runtime
      buffer at `DS:0x0e72`, not from the fixture’s static AGIDATA bytes. I’m
      going to promote this as source-backed and document that proper dynamic
      validation would need to drive the save/restore selector to populate that
      runtime buffer."

      Action/result: Decided to promote `0xaa` as source-backed.

1457. Reported: "The generator now has source-backed evidence for `0xaa`. I’m
      regenerating the matrix and updating the tracker; after this, only the
      screen-shake-like `0x6e` remains partial."

      Action/result: Updated the evidence generator and regenerated the matrix.

1458. Reported: "The evidence matrix is regenerated. I’m bumping `PROGRESS.md`
      to 175/176 covered action opcodes."

      Action/result: Updated `PROGRESS.md` to 175/176 covered action opcodes.

1459. Reported: "The tracker now leaves only `0x6e` partial. I’m updating the
      `0xaa` opcode prose and retiring the last old “dispatch-smoke” wording in
      the diagnostics/system paragraph."

      Action/result: Updated `docs/src/logic_bytecode.md`.

1460. Reported: "The bytecode chapter now explains the static-patch failure
      correctly. I’m updating the compatibility chapter’s save-description
      section so it records that failed QEMU attempt as a fixture-shape issue,
      not an unresolved opcode."

      Action/result: Updated `docs/src/compatibility_testing.md`.

1461. Reported: "The compatibility note now distinguishes static fixture bytes
      from the runtime buffer. I’m adding a brief runtime-model note under
      save/restore so `0xaa` shows up at the subsystem level too."

      Action/result: Checked for an existing save/restore runtime section.

1462. Reported: "The runtime model doesn’t yet have a save/restore subsection,
      so I’m adding a compact one rather than scattering `0xaa` into unrelated
      text/input state."

      Action/result: Added a save/restore data model table to
      `docs/src/runtime_model.md`.

1463. Reported: "The runtime model now has a save/restore data model and names
      the `0xaa` contract. I’m adding symbolic labels for the action handler
      and runtime description buffer."

      Action/result: Prepared save-description symbolic labels.

1464. Reported: "The save code labels are grouped already. I’m placing `0xaa`
      there and adding the buffer in the data section near other runtime
      globals."

      Action/result: Added `code.save.copy_description_to_string_action` and
      `data.save.description_buffer`.

1465. Reported: "The symbol map now includes the `0xaa` handler and runtime
      save-description buffer. I’m appending a clean-room note for `0xaa` so
      the failed static-patch QEMU attempt and the source-backed conclusion are
      both in the evidence trail."

      Action/result: Appended the `0xaa` save-description buffer copy section
      to `docs/src/clean_room_executable_notes.md`.

1466. Reported: "`0xaa` is now source-backed and logged in the notes. I’m
      turning to the final partial action, `0x6e`, the screen-shake-like
      handler; I’ll inspect the disassembly first and decide whether a visual
      QEMU validation is practical or whether the effect is
      hardware-timing-specific."

      Action/result: Began the `0x6e` source pass.

1467. Reported: "The first disassembly window caught the neighboring input-line
      config code, not the shake handler. The opcode table says `0x6e` starts
      around `0x7a00`, so I’m reading that exact region next."

      Action/result: Re-read the exact `0x6e` handler region.

1468. Reported: "`0x6e` is the last partial and the source is now clear. It is
      a hardware/display timing effect: for normal EGA-like modes it walks a
      small byte table and writes CRT controller registers `0x02` and `0x07`,
      waiting one timer tick between offsets; other display modes delegate to
      overlay helpers. A screenshot-after-return fixture can only prove
      dispatch, so I’m promoting this as source-backed."

      Action/result: Decided to promote `0x6e` as source-backed.

1469. Reported: "The generator now treats `0x6e` as source-backed with a note
      that QEMU only dispatch-smoked it. I’m regenerating the evidence matrix
      and then the opcode table will be complete."

      Action/result: Updated the evidence generator and regenerated the
      matrix.

1470. Reported: "The evidence matrix is regenerated. I’m updating `PROGRESS.md`
      to show all 176 action opcodes covered at the current spec target."

      Action/result: Updated `PROGRESS.md` to all 176 action opcodes covered.

1471. Reported: "The action opcode tracker is now complete. I’m checking the
      remaining-work section to make sure it no longer implies opcode coverage
      is still the highest-value gap."

      Action/result: Reviewed `PROGRESS.md` remaining-work section.

1472. Reported: "The highest-value list still has the old “promote remaining
      dispatch-smoke opcodes” item. I’m replacing that with the next useful
      opcode-adjacent work: hardening source-backed edge cases and moving back
      into subsystem specs/tests."

      Action/result: Updated `PROGRESS.md` highest-value remaining work.

1473. Reported: "The remaining-work list now reflects that opcode coverage is
      complete at the current target. I’m expanding the `0x6e` row with the
      exact normal-path register loop and display-mode branch behavior."

      Action/result: Updated the `0x6e` opcode prose.

1474. Reported: "The opcode row now has the source-level shake loop. I’m
      updating the text/status compatibility section so it says QEMU smoke only
      proves return, while the shake semantics are source-backed."

      Action/result: Updated `docs/src/compatibility_testing.md`.

1475. Reported: "The compatibility chapter now classifies `0x6e` correctly. I’m
      adding a small display-hardware note to the runtime model because this
      opcode is really a hardware timing operation, not a logical surface
      mutation."

      Action/result: Prepared the runtime-model display note.

1476. Reported: "There’s a short miscellaneous action list at the end of the
      runtime model, so I’m adding `0x6e` there with its “transient register
      effect” contract."

      Action/result: Updated `docs/src/runtime_model.md`.

1477. Reported: "The runtime model now states the portable contract for shake:
      short display offset animation, no persistent buffer change. I’m adding
      labels for the shake handler and its offset table/base bytes."

      Action/result: Prepared symbolic labels for the shake path.

1478. Reported: "The display labels are grouped near the graphics helpers and
      display globals. I’m adding the `0x6e` action label there, plus the three
      data globals/table it uses in the normal CRT path."

      Action/result: Added `code.display.shake_screen_action` and related
      display data labels.

1479. Reported: "The symbol map now has the shake action and data labels. I’m
      adding the final clean-room note for `0x6e`, then I’ll run the
      verification suite."

      Action/result: Appended the `0x6e` screen-shake source pass section to
      `docs/src/clean_room_executable_notes.md`.

1480. Reported: "I’ve picked the thread back up at the verification stage.
      First I’m going to finish checking the opcode-coverage edits, then I’ll
      roll straight into the next `PROGRESS.md` item instead of waiting for
      another nudge."

      Action/result: Resumed from the opcode-coverage verification pass.

1481. Reported: "`mdbook build docs` is clean. I’m doing the last mechanical
      checks now, including whitespace/diff hygiene and a quick scan for stale
      “partial opcode” wording before moving on."

      Action/result: Confirmed `mdbook build docs` succeeds and started final
      hygiene checks.

1482. Reported: "The verification pass surfaced only expected historical
      mentions of earlier “173/174/175” milestones, not current stale status.
      I also see two probe/test files modified, so I’m going to inspect those
      before deciding whether they are intentional work to carry forward or
      leftovers from the opcode push."

      Action/result: Inspected the probe and unit-test diffs.

1483. Reported: "I’m going to preserve these updates in the historical progress
      log now. The extra probe edits look aligned with the next `PROGRESS.md`
      item, namely text/input UI semantics, so I’ll treat them as in-flight work
      to validate and document rather than discard."

      Action/result: Began documenting the verification handoff and selected
      text/input UI semantics as the next workstream.

1484. Reported: "Text/input coverage is more advanced than the high-level
      tracker implies: the newer batches all report `match` with zero
      mismatches. I’m going to tighten the tracker around that and then use the
      next gap in the same area, menu navigation, as the next source-first
      target."

      Action/result: Checked recorded QEMU batch outputs for the text/input
      cases and selected menu navigation as the next gap.

1485. Reported: "There is already a menu label cluster and a couple of QEMU
      probes, but the “remaining” risk is navigation behavior. I’m rereading
      the menu interaction routine at `0x93d1` and the event normalizer paths
      around `0x4529..0x46e8` so the next test cases come from the control flow
      rather than guesswork."

      Action/result: Re-read `code.menu.interact` and the shared input/event
      helpers from disassembly.

1486. Reported: "The navigation table is clear in the disassembly: movement
      values `1..8` jump to eight small branches at `0x9492`, `0x94a6`,
      `0x94b2`, `0x94cb`, `0x94da`, `0x94e5`, `0x94f6`, and `0x9509`. I’m
      going to inspect the menu node construction now so I can name those
      branches correctly in terms of next/previous item and heading movement."

      Action/result: Decoded the menu movement dispatch table and inspected
      menu node construction.

1487. Reported: "The menu construction confirms both heading and item lists are
      circular doubly-linked lists: offset `+0` is next and `+2` is previous;
      headings point at their item list at `+0c`, and item enable/selection id
      live at `+0a`/`+0c`. I’m going to add a compact source-backed navigation
      table to the docs and tracker, then consider whether a non-keyboard
      event-injection probe is worth adding."

      Action/result: Prepared source-backed menu navigation documentation.

1488. Reported: "I’m making a source-backed documentation pass now: correcting
      the old “enabled item navigation” wording, adding the exact movement-code
      table, and recording the branch targets as symbolic labels so this
      survives future interpreter-version comparisons."

      Action/result: Added the menu navigation source table and updated
      symbolic labels, runtime model, compatibility notes, clean-room notes,
      and `PROGRESS.md`.

1489. Reported: "That patch didn’t apply because the clean-room note heading
      text has drifted slightly. No files were changed by that failed patch; I’m
      locating the exact anchors and I’ll apply it in smaller chunks."

      Action/result: Located the exact clean-room and progress-log anchors.

1490. Reported: "I found the exact anchors. I’m applying the menu-navigation
      docs in smaller patches now so each change has a clean landing point."

      Action/result: Applied the logic-bytecode menu navigation table.

1491. Reported: "The logic bytecode chapter now has the exact movement table
      and the corrected disabled-item semantics. I’m carrying the same model
      into the runtime overview and symbolic label map."

      Action/result: Updated the runtime model and symbolic label map.

1492. Reported: "The runtime model now has a portable menu state description,
      and the symbol map has separate root/current pointers plus the navigation
      jump table. Next I’m updating the tracker and compatibility notes so the
      remaining gap is accurately framed as dynamic movement-event validation,
      not unknown semantics."

      Action/result: Updated `PROGRESS.md` and compatibility notes.

1493. Reported: "The tracker now says menu navigation is source-backed and names
      the remaining validation gap precisely. I’m adding the clean-room evidence
      note and progress-log entries for this source pass."

      Action/result: Appended the menu-navigation clean-room section and this
      progress-log catch-up.

1494. Reported: "The menu source pass is documented. I’m going to run the quick
      verification checks now, then I’ll move into the next `PROGRESS.md` item:
      picture/view renderer compatibility, using the existing renderer and QEMU
      captures as confirmation tools."

      Action/result: Ran mdBook, diff whitespace, and full unittest checks.

1495. Reported: "Verification is clean: mdBook builds, whitespace checks pass,
      and the full unittest suite still runs green. I’m switching into the
      picture/view renderer area now and reading the current renderer/test
      coverage before picking a narrow edge case."

      Action/result: Began reviewing renderer, view-batch, and graphics tests.

1496. Reported: "The graphics test file I guessed at doesn’t exist; the renderer
      coverage is split across other test modules. I’m locating the actual
      graphics tests and then I’ll pick an edge case that lines up with both the
      disassembly and the current harness."

      Action/result: Located `tests/test_graphics_rendering.py` and related
      overlay/movement tests.

1497. Reported: "The renderer surface is clearer now: picture tests live in
      `tests/test_graphics_rendering.py`, while object-overlay and movement
      probes exercise composed view cels. I’m reading the remaining edge docs
      around transparent/mirroring/clipping to choose a useful, source-backed
      next probe."

      Action/result: Reviewed graphics object-pipeline notes and object overlay
      case coverage.

1498. Reported: "A good next edge is the object placement/search helper around
      `0x593a`, especially the weird right-edge result that currently lives as
      an observation. I’m going to read that disassembly before adding any new
      QEMU probes, because the existing behavior probably explains itself in
      the placement code."

      Action/result: Disassembled `code.object.place` and
      `code.object.control_acceptance`.

1499. Reported: "The placement helper explains the odd right-edge capture:
      `0x593a` first tries the requested position, then does a spiral search
      with growing segment lengths: left 1, down 1, right 2, up 2, left 3, down
      3, and so on. I’m checking the current prose because it may already have
      part of this but not the full search contract."

      Action/result: Found the existing placement prose and identified the
      missing exact spiral contract.

1500. Reported: "I’m going to codify the spiral search locally rather than keep
      right-edge placement as a magic expected coordinate. First I’m checking
      the derived sequence against the known QEMU result; if it lands on
      `(140,67)`, that gives us a much better compatibility oracle."

      Action/result: Simulated the source sequence and confirmed it reaches
      `(140, 67)` for the known right-edge case.

1501. Reported: "The derived spiral lands exactly on the known right-edge QEMU
      placement `(140,67)`, which is a nice little moment. I’m going to turn
      that into a reusable helper and unit tests, then update the object-overlay
      comparison to use the source-derived placement instead of hard-coded
      coordinates where possible."

      Action/result: Prepared the placement-search helper and tests.

1502. Reported: "I’m editing the local graphics model now: adding a
      `0x593a`-style placement search helper, switching the overlay comparison
      to use it for ordinary bounds adjustment, and replacing the old
      hard-coded edge-position tests with source-derived expectations."

      Action/result: Added `search_object_placement()` and updated overlay
      comparisons/tests.

1503. Reported: "The placement helper is in place and the edge cases now derive
      their expected positions from that source model. I’m running the focused
      graphics/object-overlay tests before I touch the docs."

      Action/result: Ran focused graphics, object-overlay, and view-batch tests
      successfully.

1504. Reported: "The focused Python tests pass. Before running a fresh emulator
      batch, I’m checking the existing QEMU captures for the top/right edge
      cases against the new source-derived placement model; that gives a quick
      original-engine sanity check without burning another boot."

      Action/result: Existing top/right QEMU captures matched the new
      source-derived placement model with 0 mismatches.

1505. Reported: "The existing top/right QEMU captures both match with the new
      source-derived placement helper. I’m documenting the exact spiral search
      now and tightening the compatibility notes so future work treats this as
      a modeled routine, not a one-off captured coordinate."

      Action/result: Began updating the object-placement documentation.

1506. Reported: "The docs anchor moved again in that paragraph, so I’m doing the
      same smaller-patch treatment here. No changes landed from that failed
      patch."

      Action/result: Located exact placement documentation anchors.

1507. Reported: "I’ve got the exact paragraphs. I’m applying the placement-search
      documentation separately now."

      Action/result: Added the exact `0x593a` spiral and acceptance tests to
      the graphics object-pipeline chapter.

1508. Reported: "The placement section now states the exact spiral and
      acceptance tests. I’m replacing the older “weird right edge” prose with
      the source-derived explanation."

      Action/result: Rewrote the top/right edge placement explanation.

1509. Reported: "The object-pipeline chapter now treats the top/right placements
      as outputs of the `0x593a` spiral. I’m updating the compatibility and
      tracker notes, plus the symbol map, to match the new model."

      Action/result: Updated compatibility notes, symbolic labels, and
      `PROGRESS.md`.

1510. Reported: "The compatibility/tracker docs are aligned. I’m adding the
      clean-room evidence entry for the placement-source pass and logging the
      recent work updates."

      Action/result: Appended the object-placement source-pass notes and this
      progress-log catch-up.

1511. Reported: "Full verification is clean: 109 tests now pass, opcode
      evidence check passes, mdBook builds, and diff whitespace is clean. I’ll
      continue with renderer compatibility; next I’m looking for picture-fuzz
      or view-corpus gaps that are still only lightly covered."

      Action/result: Verified the full local suite, opcode-evidence check,
      mdBook build, and whitespace check, then moved to renderer-compatibility
      gaps.

1512. Reported: "The next picture-side risk the docs call out is seed-fill
      traversal: the local renderer uses a queue, while the original appears to
      have its own stack/span helper. I’m going to inspect the seed-fill routine
      around `0x533b` and see whether the observable contract can be made more
      implementation-ready without overfitting internals."

      Action/result: Began source-first inspection of picture seed fill around
      `code.picture.seed_fill` (`0x533b`).

1513. Reported: "I’m picking up at the seed-fill source pass. I’ll first write
      the two recent progress updates into the log, then tighten the docs around
      the span-stack fill behavior before deciding whether new compatibility
      cases are worth adding."

      Action/result: Resumed from the seed-fill source pass and checked current
      tracker/docs state.

1514. Reported: "The repo is in the expected in-progress state, with the object
      placement pass already documented and tested. I’ve found the outstanding
      picture-renderer note: seed fill is documented as span-based, but the
      exact source-derived contract can be sharper."

      Action/result: Identified seed-fill traversal documentation as the next
      high-value picture-renderer refinement.

1515. Reported: "I’m going back to the actual `0x533b` disassembly rather than
      just polishing prose from memory. The goal is to describe what the
      original routine commits to observably, and keep implementation guidance
      portable."

      Action/result: Re-read the seed-fill helper disassembly and the current
      picture-renderer compatibility notes.

1516. Reported: "The seed-fill routine confirms the docs’ broad statement, and
      adds useful specifics: it chooses exactly one expansion channel, rejects
      no-op fills before scanning, writes spans with the normal odd/even masks,
      and uses stack-pushed span state for branches. I’m turning that into a
      clearer spec paragraph now."

      Action/result: Prepared a source-backed seed-fill contract update for
      the graphics pipeline documentation.

1517. Reported: "I’m going to keep the seed-fill labels conservative: the
      scratch bytes around `0x126c` clearly form span state, but several fields
      change roles during branch handling. A single “span scratch block” label
      is more honest than naming every byte too confidently."

      Action/result: Reviewed existing picture symbolic labels and chose a
      conservative scratch-block label strategy for seed-fill state.

1518. Reported: "There’s already an older seed-fill refinement note, so I’m not
      going to pretend this is a first discovery. This pass will add the
      missing traversal details and separate “observable behavior” from “how
      SQ2’s executable happens to organize its stack state.”"

      Action/result: Compared the older seed-fill notes with the new
      disassembly pass to avoid duplicating or overstating evidence.

1519. Reported: "`PROGRESS.md` points next at picture/view compatibility and
      then implementation-ready subsystem state machines. I’ll finish the
      seed-fill spec cleanup as part of that renderer work, then use the
      tracker to choose the next concrete gap rather than wandering."

      Action/result: Re-read the high-value tracker section and kept the next
      work item aligned to renderer compatibility.

1520. Reported: "I’m editing the picture pipeline chapter now. The important
      distinction is: original traversal order is source-backed, but clean
      implementations can use a different flood-fill algorithm if they preserve
      target selection and pixel-write semantics on valid resources."

      Action/result: Updated the `0xf8` seed-fill section with explicit channel
      selection, early exits, span-stack traversal, and portable final-buffer
      semantics.

1521. Reported: "The main seed-fill chapter now separates channel selection,
      no-op rejection, span traversal, and the portable observable contract.
      I’m adding the scratch-block label and evidence note so future
      cross-version work has something stable to map."

      Action/result: Added `data.picture.seed_fill_span_scratch` to the
      symbolic label map.

1522. Reported: "The compatibility notes still say the traversal itself is an
      open risk. I’m narrowing that: traversal class is now source-backed; what
      still needs broader proof is edge-case parity across barriers, masks, and
      multiple seeds."

      Action/result: Reframed the seed-fill compatibility risk around expanded
      parity coverage instead of unknown traversal class.

1523. Reported: "I’m appending the clean-room evidence entry for this seed-fill
      pass, including the commands that were useful and the small correction to
      the previous “queue versus span” uncertainty."

      Action/result: Appended the picture seed-fill span-stack source-pass note
      to the clean-room evidence log.

1524. Reported: "The evidence note will also capture a minor tooling lesson:
      one of the broad disassembly windows was noisy, but the useful evidence
      is still the focused helper body and the existing renderer tests."

      Action/result: Recorded the noisy broad disassembly as limited evidence
      and documented the source-backed result.

1525. Reported: "I’m updating `PROGRESS.md` now so the tracker reflects the
      narrower seed-fill status: source-backed traversal, still needing broader
      parity cases. That should make the next renderer step clearer."

      Action/result: Updated the picture-decoding tracker with source-backed
      seed-fill span traversal and the remaining coverage targets.

1526. Reported: "The tracker currently treats picture decoding as one broad
      bucket. I’ll add the seed-fill evidence there without marking the whole
      renderer done; the remaining work is still real, just better bounded."

      Action/result: Kept picture decoding at partial status while adding the
      refined seed-fill evidence.

1527. Reported: "I noticed one wording detail worth tightening before moving
      on: the control fill value lives as high-nibble `4`, which appears as
      `0x40` in the buffer byte. I’m making that explicit so a future
      implementation doesn’t compare the wrong byte value."

      Action/result: Clarified the control-channel seed-fill target and no-op
      value as high-nibble `4` / buffer byte `0x40`.

1528. Reported: "The seed-fill docs and tracker now agree: traversal is
      source-backed, final-buffer equivalence remains the portable contract,
      and the remaining risk is coverage depth. I’m going to run the
      lightweight checks for these doc-only changes before choosing the next
      `PROGRESS.md` task."

      Action/result: Started verification for the seed-fill documentation pass.

1529. Reported: "The doc build and whitespace check are clean after the
      seed-fill update. Next I’m going to turn that remaining seed-fill coverage
      list into concrete valid synthetic picture cases, then decide whether a
      small original-engine QEMU batch is worthwhile."

      Action/result: Verified the seed-fill documentation changes and began
      adding curated picture fuzz cases.

1530. Reported: "The fuzz base list already has two seed-fill cases, but they
      don’t cover multiple seeds or a narrow barrier shape. I’m reading the
      local renderer shape helpers before adding cases, so the fixtures stay
      valid and intentional."

      Action/result: Reviewed picture renderer command handling and existing
      seed-fill tests before adding new valid cases.

1531. Reported: "The local renderer’s `write_cell()` already models the
      odd/even row mask path, so a good seed-fill case can exercise that
      without new renderer machinery. I’m adding a few curated safe base cases
      rather than relying on random generation to stumble into them."

      Action/result: Chose curated seed-fill fixture shapes for deterministic
      fuzz coverage.

1532. Reported: "For QEMU screenshots, visual-channel cases are the most useful
      because the batch comparator sees the rendered EGA image. I’ll still
      include one control-channel case in local tests, but the curated QEMU
      candidates should mostly produce visible differences."

      Action/result: Balanced visible QEMU cases with one local control-channel
      semantic test.

1533. Reported: "I’m making three small curated fixtures: a full-height
      one-pixel visual barrier, two separate boxes filled by one multi-seed
      command, and a control-channel fill that crosses a visual-only barrier.
      They each target a specific seed-fill edge without malformed data."

      Action/result: Added `base_021`, `base_022`, and `base_023` to
      `tools/picture_fuzz.py`.

1534. Reported: "The new base cases are in the fuzz catalog. I’m adding direct
      renderer assertions next, because these cases encode semantics that are
      clearer to test as cell values than as screenshot hashes alone."

      Action/result: Added local renderer tests for the full-height barrier,
      multi-seed boxes, and control-channel barrier-crossing case.

1535. Reported: "The local semantic tests are in place. I’m running the
      renderer and fuzz-tool tests now; if they pass, I’ll regenerate a small
      corpus and consider a targeted QEMU batch for the visible fill cases."

      Action/result: Ran targeted renderer/fuzz tests and generated a small
      corpus containing the new curated cases.

1536. Reported: "The new tests pass, and a small regenerated corpus reports 24
      curated base cases plus randoms. I’m checking the batch command path
      before running QEMU so I use the snapshot harness correctly and don’t
      waste a boot cycle."

      Action/result: Confirmed the new cases render locally and are marked safe
      for QEMU.

1537. Reported: "I’m going to run the three new safe seed-fill fixtures through
      the original engine using the snapshot batch harness. The first two
      should validate visible fill geometry; the third is mostly a guard that
      control-only fill does not disturb the visible barrier."

      Action/result: Started a QEMU snapshot batch for `base_021`, `base_022`,
      and `base_023`.

1538. Reported: "The snapshot batch built its disk, then QEMU was blocked by
      the sandbox from binding the local VNC socket. That’s a permissions issue
      rather than a renderer result, so I’m rerunning the same harness with
      escalation."

      Action/result: Re-ran the same seed-fill QEMU batch with permission to
      bind the local VNC socket.

1539. Reported: "The escalated QEMU batch is running now from the snapshot
      disk. I’ll wait for the JSON summary, then fold the result into the
      compatibility docs and tracker."

      Action/result: Waited for the original-engine seed-fill batch to finish.

1540. Reported: "The original-engine batch matched all three new seed-fill
      cases with 0 mismatches. That gives us QEMU-backed coverage for the
      full-height barrier, multi-seed fill, and the visible side of the
      control-channel barrier case."

      Action/result: Captured the successful QEMU report at
      `build/picture-fuzz/batches/seed_fill_edges_001.json`.

1541. Reported: "I’m updating the compatibility chapter with the new corpus
      count and the seed-fill batch result. I’ll be careful to say the
      control-only case’s screenshot validates visible stability, while the
      local cell test validates the control-channel crossing behavior."

      Action/result: Began documenting the new seed-fill fuzz cases and QEMU
      results.

1542. Reported: "The docs currently say there are 21 curated base cases and
      that QEMU coverage stops at `base_020`. I’m bumping that to 24 and adding
      the `seed_fill_edges_001` batch as the new evidence point."

      Action/result: Updated the compatibility chapter with the new curated
      case count and QEMU seed-fill batch result.

1543. Reported: "I’m also revising the “remaining risk” paragraph so it
      doesn’t keep asking for cases we just added. Multi-seed and
      narrow-barrier coverage are now present; broader mask and pattern
      interactions still remain."

      Action/result: Narrowed the remaining picture-renderer risk to broader
      mask, pattern, and interleaved operation coverage.

1544. Reported: "I’m adding the clean-room note for the new fuzz cases now,
      including the failed non-escalated QEMU attempt as a permissions artifact
      and the successful escalated run as the evidence."

      Action/result: Appended the seed-fill fuzz expansion note to
      `docs/src/clean_room_executable_notes.md`.

1545. Reported: "`PROGRESS.md` needs the same refinement: seed-fill now has
      specific QEMU-backed edge fixtures, while broader pattern/fill
      combinations remain open. I’m updating that tracker line next."

      Action/result: Updated the picture-decoding tracker with the new
      QEMU-backed seed-fill edge fixtures.

1546. Reported: "The tracker is updated. I’m regenerating the standard
      1,024-random corpus once so the documented counts are backed by the
      actual command, then I’ll run the local suite/checks."

      Action/result: Regenerated the standard picture fuzz corpus and reran
      targeted renderer/fuzz tests.

1547. Reported: "The standard corpus command now confirms the documented
      numbers: 1,048 total cases and 1,046 safe for QEMU. The targeted
      renderer/fuzz tests still pass after adding the three curated cases."

      Action/result: Confirmed the documented fuzz corpus counts and targeted
      test pass.

1548. Reported: "I’ve folded the verified standard corpus count into the
      evidence note. Next I’ll run the broader project checks, then continue to
      the next renderer gap if everything is clean."

      Action/result: Updated the clean-room evidence note with the verified
      standard corpus generation command.

1549. Reported: "I’m running the usual verification set now: full unit tests,
      opcode-evidence consistency, mdBook build, and diff whitespace. After
      that I’ll continue with the next `PROGRESS.md` item instead of stopping."

      Action/result: Ran the full verification set after the seed-fill fuzz
      expansion.

1550. Reported: "Verification is clean: 112 tests pass, opcode evidence is
      consistent, mdBook builds, and diff whitespace is clean. I’m moving to
      the next renderer gap in `PROGRESS.md`: view/cel drawing coverage,
      especially mirroring and transparent-color edges."

      Action/result: Began the view/cel drawing coverage pass.

1551. Reported: "The view docs already mention more transparent-color samples
      than the tracker summary remembered, so I’m checking the actual coverage
      before adding duplicate cases. The next useful step looks like selecting
      a few largest or unusual cels from the local corpus and validating them
      through the existing view batch harness."

      Action/result: Scanned existing view docs, tests, and the local view
      corpus for large, mirrored, and transparent-color candidate cels.

1552. Reported: "The corpus scan gives good candidates: large cels with
      transparent colors not yet emphasized by the small default view batch,
      plus a tall 129-row cel. I’m checking the view-batch tests before
      deciding whether to expand the built-in batch or keep these as a separate
      stress list."

      Action/result: Reviewed `tests/test_view_batch.py` and candidate cel
      dimensions/control bytes.

1553. Reported: "I’m going to add an optional stress suite to `view_batch.py`
      rather than making every default run heavier. It will be reusable for
      compatibility work while the default six-case smoke stays quick."

      Action/result: Chose an optional stress-suite design for view validation.

1554. Reported: "The stress suite will deliberately cover transparent colors
      `0,1,2,5,6,7,8,10,13,14,15` and a bit-`0x80` transparent-10 frame. That
      complements the existing smaller probe set without changing the default
      batch."

      Action/result: Selected eleven stress cases from the local SQ2 view
      corpus.

1555. Reported: "The stress cases are defined. I’m wiring them into the CLI as
      `--include-stress`, so scripted runs can opt in without breaking quick
      smoke runs or JSON case loading."

      Action/result: Added `stress_cases()` and `--include-stress` to
      `tools/view_batch.py`.

1556. Reported: "The CLI flag is in. I’m extending the view-batch unit tests to
      lock down that the stress suite stays optional and actually includes the
      broader transparent-color coverage."

      Action/result: Added unit coverage for optional stress-case loading.

1557. Reported: "The optional stress suite is covered by tests. I’m running the
      view-batch unit tests and a quick local frame render check for those
      stress cases before involving QEMU."

      Action/result: Verified stress cases render locally and fit on screen;
      targeted view tests passed.

1558. Reported: "The stress suite renders locally and all placements fit the
      screen. I’m running the base plus stress view batch through QEMU snapshot
      mode now; this is the compatibility check that matters for the new
      cases."

      Action/result: Started the 17-case original-engine view stress batch.

1559. Reported: "The 17-case view stress batch is running from a single QEMU
      snapshot now. It includes the six existing smoke cases plus eleven
      larger/transparent/mirrored cels."

      Action/result: Waited for the view stress QEMU batch to complete.

1560. Reported: "The view batch is still running; no result lines yet, which is
      normal while the snapshot harness drives each DOS fixture and captures
      screens. I’m waiting it out rather than interrupting the emulator."

      Action/result: Continued waiting for QEMU snapshot results.

1561. Reported: "Still waiting on QEMU. This longer run is expected for 17
      cases, but it should return a compact match/mismatch summary once the
      harness finishes."

      Action/result: Continued waiting for QEMU snapshot results.

1562. Reported: "The emulator batch is taking its time but is still alive. I’m
      letting it continue, since stopping here would throw away the
      original-engine evidence we’re trying to collect."

      Action/result: Continued waiting for QEMU snapshot results.

1563. Reported: "Still no output from the harness, which means it’s inside the
      snapshot-run loop rather than comparison/report writing. I’ll give it
      another interval before deciding whether to inspect for a stuck QEMU
      process."

      Action/result: Continued waiting; the batch later returned result lines.

1564. Reported: "Good, results are coming back: the first 13 view cases all
      match, including several large transparent-color samples and the tall
      129-row cel. I’m waiting for the last four and the JSON summary."

      Action/result: Observed the first 13 view stress cases matching QEMU.

1565. Reported: "The full 17-case view batch matched with 0 mismatches and 0
      errors. I’m reading the report, then I’ll document the optional stress
      suite and update the view coverage tracker."

      Action/result: Completed QEMU view stress validation with all cases
      matching.

1566. Reported: "The QEMU report confirms every stress case matched. I noticed
      the new test import line is a bit ungainly, so I’m tidying that before
      documenting the result."

      Action/result: Read `view_stress_001.json` and formatted the test import
      cleanly.

1567. Reported: "I’m updating the docs in two places: command examples for the
      optional stress suite, and the compatibility evidence list showing the
      17-case `view_stress_001` result."

      Action/result: Updated the compatibility-testing chapter with the stress
      command and QEMU result.

1568. Reported: "The compatibility chapter now has the stress command and
      result. I’m adding a shorter note in the graphics pipeline chapter near
      the view layout section so readers see that the row/transparent model has
      broader QEMU coverage now."

      Action/result: Added the view stress result to the graphics object
      pipeline chapter.

1569. Reported: "I’m appending the clean-room evidence for the view stress
      batch, including the corpus scan that selected the cases and the QEMU
      report path."

      Action/result: Appended the optional view stress batch expansion note to
      the clean-room executable notes.

1570. Reported: "The evidence note is in. I’m updating `PROGRESS.md` so the
      view area no longer lists broad transparent-color coverage as an
      untouched gap; the remaining view work is more about clipping,
      priority/control combinations, and animation state."

      Action/result: Updated the view coverage tracker in `PROGRESS.md`.

1571. Reported: "I’m catching the progress log up for the view stress work
      before running another verification pass. The log is long, but it’s doing
      its job as the clean-room trail."

      Action/result: Recorded the view stress work in the progress log.

1572. Reported: "The progress log is caught up. I’m running the full checks
      again after the view-batch code/docs changes, then I’ll keep moving to
      the next tracker item if it’s clean."

      Action/result: Ran the full verification set after the view stress pass.

1573. Reported: "Verification is clean again: 113 tests pass, opcode evidence
      is consistent, mdBook builds, and whitespace is clean. I’m checking
      `PROGRESS.md` for the next highest-value gap now; likely candidates are
      right/bottom clipping or interleaved picture line/fill/pattern cases."

      Action/result: Re-read `PROGRESS.md` and selected picture pattern/
      interleaving coverage as the next renderer task.

1574. Reported: "`PROGRESS.md` now points me back to picture renderer coverage:
      interleaved line/fill/pattern streams and broader pattern modes. I’m
      going to add a few valid curated pattern cases next and run them through
      the same fuzz/QEMU path."

      Action/result: Began adding pattern-focused curated picture fuzz cases.

1575. Reported: "The existing pattern source notes already cover bits `0x10`
      and `0x20`, but the curated QEMU cases don’t isolate `0x10` or mix
      fill/line/pattern in one stream. I’m adding those as safe base cases."

      Action/result: Reviewed pattern source notes and existing fuzz coverage
      before adding new cases.

1576. Reported: "I’ll add three pattern cases: `0x10` mask bypass alone, an
      interleaved rectangle-fill-line-pattern stream, and a combined
      `0x10|0x20` pseudo-random pattern sequence. The local tests will assert
      the first two at the pixel level."

      Action/result: Added `base_024`, `base_025`, and `base_026` to
      `tools/picture_fuzz.py`.

1577. Reported: "The new pattern cases are in the fuzz catalog. I’m adding
      renderer assertions for mask-bypass geometry and the interleaved
      operation order so these aren’t just anonymous hashes."

      Action/result: Added local pixel-level tests for pattern mask-bypass and
      interleaved operation ordering.

1578. Reported: "The pixel-level pattern tests are in. I’m running the targeted
      renderer/fuzz tests and regenerating the standard corpus so the base-case
      counts stay truthful."

      Action/result: Targeted renderer/fuzz tests passed and the standard
      corpus regenerated with 1,051 cases, 1,049 safe for QEMU.

1579. Reported: "The local pattern tests pass, and the standard corpus now
      reports 1,051 total cases with 1,049 safe for QEMU. I’m running the three
      new pattern fixtures through the original engine next."

      Action/result: Started the `pattern_interleaved_001` QEMU snapshot batch.

1580. Reported: "The pattern QEMU batch is running from the snapshot disk. These
      cases should tell us whether the local renderer’s mask-bypass and mixed
      operation ordering match the original engine."

      Action/result: Waited for the original-engine pattern batch to finish.

1581. Reported: "The original-engine pattern batch matched all three new cases
      with 0 mismatches. I’m documenting the result and updating the
      remaining-picture-work wording so interleaved line/fill/pattern coverage
      is no longer listed as missing."

      Action/result: Read `pattern_interleaved_001.json` and began documenting
      the successful QEMU result.

1582. Reported: "The compatibility chapter still has the pre-pattern counts.
      I’m bumping it to 27 curated base cases, adding `pattern_interleaved_001`,
      and narrowing the remaining picture risk again."

      Action/result: Updated compatibility-testing counts and pattern QEMU
      evidence.

1583. Reported: "I’m appending the clean-room evidence entry for the pattern
      additions now, including the source-note check, local tests, corpus
      regeneration, and QEMU report."

      Action/result: Appended the pattern/interleaved picture fuzz expansion
      note.

1584. Reported: "The pattern evidence note is in. I’m updating the picture
      tracker so the remaining renderer work focuses on odd/even-mask variation
      and broader real-resource parity rather than the interleaved cases we
      just validated."

      Action/result: Updated `PROGRESS.md` for the new pattern/interleaving
      coverage.

1585. Reported: "I’m catching the progress log up for the pattern-fuzz pass,
      then I’ll run the full verification set again. After that, I’ll keep
      going into the next remaining gap."

      Action/result: Recorded the pattern-fuzz work in the progress log.

1586. Reported: "The progress log is current again. I’m running the full check
      set after the pattern-fuzz changes: unit tests, opcode evidence, mdBook,
      and whitespace."

      Action/result: Ran the full verification set after pattern-fuzz changes.

1587. Reported: "Verification is clean: 115 tests pass, opcode evidence is
      consistent, mdBook builds, and whitespace is clean. I’m moving next to
      the object placement/search gap, specifically what happens when collision
      or control rejection makes the spiral continue past the first
      bounds-acceptable spot."

      Action/result: Began a source-first pass on placement-search rejection
      predicates.

1588. Reported: "My first disassembly window landed on the familiar MZ-offset
      trap, so I’m rerunning the helper slices with the corrected file skip.
      I’ll use the existing docs as guardrails and only refine what the source
      clearly supports."

      Action/result: Re-ran `0x4719` and `0x56b8` disassembly with corrected
      file offsets.

1589. Reported: "The corrected source slices confirm the caller contract
      already in the docs: placement tests bounds, object-object collision,
      then control acceptance at every spiral candidate. I’m going to make the
      local placement helper’s `accept` hook explicit and tested, so
      collision/control rejection can be modeled without hard-coding only
      bounds cases."

      Action/result: Prepared a local placement-helper clarification and test.

1590. Reported: "I’m editing the helper and tests now: the source-backed spiral
      remains the same, but the test will prove an external collision/control
      predicate can reject early candidates and force the same spiral onward."

      Action/result: Began adding placement-helper documentation and coverage.

1591. Reported: "The helper already had the hook; this is mostly documentation
      and coverage, not new behavior. That’s the right kind of small change for
      a source-confirmed routine."

      Action/result: Added a docstring to `search_object_placement()`.

1592. Reported: "The helper docstring is in. I’m adding a regression test that
      rejects the first few otherwise-valid candidates and verifies the next
      accepted point follows the exact source spiral order."

      Action/result: Added the placement accept-hook regression test.

1593. Reported: "The accept-hook test now pins the first rejected-candidate
      sequence: `(20,80)`, `(19,80)`, `(19,81)`, `(20,81)`, then `(21,81)`. I’m
      reflecting that in the placement docs."

      Action/result: Updated the graphics pipeline placement documentation.

1594. Reported: "I’m recording this as a small source-model refinement, not as
      new original-engine dynamic evidence: the source shows the later
      predicates are applied at each candidate, and the local helper now
      exposes/tests that structure."

      Action/result: Appended the placement-search predicate-hook evidence
      note.

1595. Reported: "The evidence note is in. I’m updating the object-pipeline
      tracker to say the local placement model now has a tested predicate hook,
      while full object-record collision/control fixtures remain future work."

      Action/result: Updated `PROGRESS.md` for the placement-search predicate
      hook.

1596. Reported: "I’m checking the symbol map before verification; if the
      collision helper already has a label, I’ll leave it alone, and if not
      I’ll add one so future version comparisons can map both placement
      predicates."

      Action/result: Found the control helper label but no collision helper
      label.

1597. Reported: "The control helper has a label, but the object-object
      collision helper doesn’t. I’m adding `code.object.collision_test` at
      `0x4719` so the placement predicate pair is complete in the symbol map."

      Action/result: Added `code.object.collision_test` to the symbolic label
      map.

1598. Reported: "The symbol map now has both placement predicates named. I’m
      adding that to the evidence note, then I’ll run the targeted and full
      checks."

      Action/result: Updated the placement evidence note with the new symbolic
      label.

1599. Reported: "I’m running the focused graphics tests first for the
      placement-hook change. If those pass, I’ll run the full project checks
      again."

      Action/result: Ran focused graphics tests for placement changes.

1600. Reported: "The focused graphics tests pass, including the new placement
      predicate hook case. I’m running the full verification set now, then I’ll
      keep going from the tracker."

      Action/result: Ran the full verification set after the placement-hook
      change.

1601. Reported: "Full verification is clean again: 116 tests pass, opcode
      evidence is consistent, mdBook builds, and whitespace is clean. I’m
      logging the placement-hook work, then I’ll move to the next highest-value
      non-graphics gap: text/input UI semantics."

      Action/result: Confirmed the full suite and prepared to move to text/input
      UI semantics.

1602. Reported: "I’m shifting into the text/input UI area now. First I’m
      auditing what is already QEMU-backed versus what is only dispatch-smoked
      so I don’t spend time duplicating evidence."

      Action/result: Began auditing text/input coverage against the tracker and
      existing probes.

1603. Reported: "`0xa9`’s active saved-window path may not be reachable cleanly
      from the existing simple fixtures, but the source check is still useful:
      it tells us exactly which state bit gates the restore call and which
      globals are cleared afterward."

      Action/result: Re-read action `0xa9` and identified the saved-window
      restore gate and cleanup writes.

1604. Reported: "The remaining text/input gap is narrower than PROGRESS.md
      says. Most of the input-line, prompt, mapped-key, raw-key, status, and
      width-mode behavior already has focused QEMU coverage; I’m updating the
      tracker to name the real gap instead of the stale broad one."

      Action/result: Narrowed the `PROGRESS.md` text/input remaining-work entry.

1605. Reported: "I’m adding a short evidence note for this text/input audit so
      the tracker change has a source trail. After that I’ll pick the next
      partial subsystem rather than overfitting a brittle `0xa9` fixture."

      Action/result: Added the text/input tracker audit note.

1606. Reported: "With the text/input tracker narrowed, I’m moving to another
      partially covered subsystem from PROGRESS.md: sound. I’ll start from the
      load/start/stop source that the current QEMU probes already touch, then
      see how much of the resource format falls directly out of the code."

      Action/result: Started the source-first sound-resource pass.

1607. Reported: "The first sound disassembly window was actually
      joystick/picture code, so I corrected the address window and landed on the
      sound cache lookup/load/start/stop cluster. The loader is doing something
      pleasantly concrete: reading four little-endian offsets from the payload
      into the cache record."

      Action/result: Corrected the sound disassembly window and identified the
      four-channel offset setup.

1608. Reported: "The sound loader source is clear on the resource container,
      and a quick SQ2 corpus scan says all present sound resources follow the
      same four-offset header shape. I’m reading the driver-start/tick routines
      next to see what each channel stream record contains."

      Action/result: Scanned SQ2 sound resources and moved to the playback
      start/tick source.

1609. Reported: "I’m going to add a small sound-resource parser, but only for
      the source-confirmed container/event fields: four channel offsets, then
      duration/tone/control records ending in `0xffff`. Pitch and timing can
      stay provisional until the driver code is better understood."

      Action/result: Added `tools/agi_sound.py`.

1610. Reported: "The parser is added. I’m adding tests that scan every present
      SQ2 sound resource so the format claim is pinned to the local corpus, not
      just sound 1."

      Action/result: Added `tests/test_sound_resources.py`.

1611. Reported: "The sound tests are in. I’m running them now, then I’ll update
      the subsystem docs and tracker if the corpus scan stays clean."

      Action/result: Ran targeted sound-resource tests.

1612. Reported: "The sound parser tests pass across all 49 SQ2 sound resources:
      every channel offset is sorted/in-bounds, every channel reaches an
      in-payload `0xffff` terminator, and sound 1 matches the first event shape
      from the source pass. I’m checking the symbol map for the sound channel
      globals before documenting this."

      Action/result: Confirmed the targeted sound-resource tests and prepared
      sound symbol-map updates.

1613. Reported: "The symbol map already names the main sound code paths, but it
      didn’t yet name the channel pointer/countdown/state globals that
      `0x7f96` initializes. I’m adding those data labels so later interpreter
      versions can be mapped by role instead of address."

      Action/result: Prepared sound channel data labels.

1614. Reported: "The sound label block has a slightly different neighbor order
      than I expected, so I’m patching it at the existing sound section rather
      than moving unrelated labels around."

      Action/result: Added the sound data labels in the existing sound symbol
      section.

1615. Reported: "I found the sound block and added the channel stream pointer,
      countdown, active-word, and attenuation labels. Next I’ll finish the docs
      for the sound resource shape and run the full verification set before the
      next commit point."

      Action/result: Completed the symbol-map update and queued sound
      documentation/verification work.

1616. Reported: "I’ll get the current work into a clean commit. First I’m
      checking the tree and the recent docs/test state so I don’t accidentally
      freeze an unfinished evidence trail."

      Action/result: Checked git status, diff stats, and the tail of the
      progress log.

1617. Reported: "The tree is large but coherent: opcode/probe work, graphics
      fuzz/view validation, placement modeling, and the new sound parser. I
      found the progress log stops just before the text/input and sound updates,
      so I’m going to patch that evidence gap and the sound docs before
      committing."

      Action/result: Decided to finish missing progress-log and sound-doc
      updates before staging.

1618. Reported: "The sound parser itself is small and the source-backed shape
      is clear: loader builds four channel pointers from the payload header, and
      the tick routine consumes duration/tone/control records. I’m adding that
      to the model and compatibility docs so the commit tells the full story."

      Action/result: Added sound-resource shape documentation to the runtime,
      opcode, compatibility, progress, and evidence notes.

1619. Reported: "Before editing, I’m keeping the patches scoped to
      documentation and one tiny test cleanup. No new reverse-engineering claim
      here without a source or test hook behind it."

      Action/result: Kept the commit-prep edits scoped to evidence and
      verification support.

1620. Reported: "The documentation gap is patched. I’m running the project’s
      full pre-commit checks now: unit tests, opcode evidence consistency,
      mdBook build, and whitespace scan."

      Action/result: Ran the full pre-commit verification set.

1621. Reported: "All four checks passed cleanly, and the full test suite is now
      120 tests with the sound parser included. I’m recording that verification
      result in the progress log, then I’ll stage only the tracked project files
      plus the new sound parser/tests, leaving generated DOS/build artifacts
      alone."

      Action/result: Confirmed `python3 -B -m unittest discover -s tests`
      passed with 120 tests, opcode evidence check passed, mdBook built, and
      `git diff --check` passed.

1622. Reported: "The intended files are staged and the generated `build/` and
      DOS installer directory are still untracked. I’m doing one staged diff
      sanity check, then I’ll write the commit."

      Action/result: Verified staged status and staged diff summary before the
      commit.

1623. Reported: "I added the final staging update to the historical log as
      well, so the record stays complete. Now I’m restaging that one log file
      and committing."

      Action/result: Restaged the progress log before committing.

1624. Reported: "Staged whitespace is clean and the only unstaged items are the
      expected generated directories. I’m committing this batch now."

      Action/result: Committed the staged reverse-engineering, documentation,
      and compatibility-test updates.

1625. Reported: "I’ll pick up from the tracker and avoid committing. First I’m
      rereading `PROGRESS.md` and the current tree so I can choose the next
      highest-value source-first work instead of wandering."

      Action/result: Re-read the progress tracker, git status, progress log,
      and remaining-work references.

1626. Reported: "The tracker points to sound playback and implementation-ready
      subsystem text as a good next seam. I’m going source-first there: re-read
      the sound driver/tick code around the parser I just added, then turn any
      concrete timing/state behavior into docs and tests."

      Action/result: Began a source-first pass over the sound playback driver.

1627. Reported: "The first pass exposed a useful state machine: in the
      one-channel path the tick loop only advances channel 0, while the
      four-channel path advances BX offsets 0,2,4,6. I’m checking the gate call
      at `0x7502` and the timer hook now so the docs don’t accidentally imply
      every tick always advances audio."

      Action/result: Identified active-channel selection and moved to the flag
      gate and timer-hook source.

1628. Reported: "The tick gate is flag 9: if that flag is clear, the sound tick
      stops playback immediately and sets the configured completion flag. I’m
      scanning the SQ2 sound corpus for duration edge cases before writing a
      schedule helper, because duration zero would have a very non-obvious
      16-bit countdown consequence."

      Action/result: Confirmed the flag-9 gate and scanned sound-event
      durations.

1629. Reported: "The SQ2 corpus has 3,619 sound events and no zero-duration
      events, but the source would treat duration zero as a 16-bit countdown
      wrap before the next record. I’m adding a small schedule helper that
      captures the source timing rule without pretending to synthesize actual
      audio."

      Action/result: Added source-backed sound scheduling helpers.

1630. Reported: "The helper now models three source-backed things: which
      channels tick for the hardware selector, the initial one-tick delay before
      the first record, and the 16-bit countdown wrap. I’m adding tests against
      SQ2 sound 1, a longer multi-channel sound, and a synthetic zero-duration
      edge."

      Action/result: Added sound scheduling tests.

1631. Reported: "The targeted sound tests pass: the schedule helper matches
      sound 1’s tick-40 termination, distinguishes sound 60’s one-channel
      versus four-channel completion, and pins the zero-duration wrap. I’m
      folding this into the mdBook and the symbolic map now."

      Action/result: Ran `python3 -B -m unittest tests.test_sound_resources`;
      all 9 targeted sound tests passed.

1632. Reported: "The source also ties natural completion to the timer interrupt
      hook, not script bytecode: the IRQ calls the tick only while `[0x1258]` is
      active, and the tick sets the completion flag when the last active channel
      terminates. I’m making that distinction explicit in the docs and tracker."

      Action/result: Documented sound tick scheduling, channel selection,
      flag-9 gating, natural completion, and remaining hardware-output gaps.

1633. Reported: "The sound docs and labels are updated. I’m running the cheap
      checks for this slice now, then I’ll move to the next tracker item rather
      than stopping."

      Action/result: Ran the targeted sound tests, mdBook build, whitespace
      check, and status check; the checks passed, with only expected modified
      project files and generated/untracked directories present.

1634. Reported: "The sound slice is clean: targeted tests, book build, and
      whitespace check all passed. Next I’m tackling the remaining `0xa9`
      active saved-window path from source by finding every writer of the
      saved-window globals before deciding whether a dynamic probe is worth
      building."

      Action/result: Began the text-window source pass and searched references
      to the saved-window globals and helpers.

1635. Reported: "The active `0xa9` path is clearer now: message-window setup at
      `0x1d96` closes any prior saved window, computes two packed rectangle
      coordinates, draws/saves through `0x5590`, sets `[0x0d1d]=1`, and later
      `0xa9` restores via `0x560c`. This looks source-complete even if it’s
      awkward to isolate dynamically."

      Action/result: Identified the modal saved-window producer at `0x1d96`,
      the boxed draw/save helper at `0x5590`, the restore helper at `0x560c`,
      and the close consumer at `0x1f2b`.

1636. Reported: "I’m picking up from the active text-window restore pass and
      the tracker, with the source-first constraint in mind. I’ll close out the
      `0xa9` saved-window evidence cleanly, then move to the next highest-value
      item in `PROGRESS.md` without touching git."

      Action/result: Re-read git status, the progress tracker, the relevant
      opcode/runtime/symbolic-label sections, and the recent progress log.

1637. Reported: "The log is current through the sound documentation update, so
      I’m adding the missing verification and text-window source-pass entries
      before I edit the book. That keeps the historical trail aligned with what
      already happened rather than retrofitting it at the end."

      Action/result: Prepared to record the missing verification and active
      text-window source-pass progress-log entries.

1638. Reported: "I’m going to patch the text-window sections now: symbolic
      labels first, then the opcode/runtime prose, then the tracker and
      executable notes. The main change is to promote the active `0xa9` path
      from \"helper calls seen\" to a traced open/restore lifecycle with the
      producer at `0x1d96` and the close path at `0x1f2b`."

      Action/result: Added symbolic labels for the modal message-window opener,
      boxed draw/save helper, restore helper, active flag, and packed rectangle
      words; then updated the opcode, runtime, tracker, and executable notes.

1639. Reported: "The symbolic map now has stable names for the modal window
      opener, draw helper, restore helper, active flag, and packed
      restore-coordinate words. Next I’m tightening the spec prose so readers
      see the lifecycle rather than a pile of addresses."

      Action/result: Tightened the `0xa9` and modal text-window lifecycle prose
      in `docs/src/logic_bytecode.md` and `docs/src/runtime_model.md`.

1640. Reported: "The `0xa9` docs now describe both sides of the saved-window
      lifecycle: where the rectangle is created and where it is restored. I’m
      updating the historical log with those intermediate reports next, then
      I’ll run the book/whitespace checks and continue to the next tracker
      item."

      Action/result: Updated the historical progress log for the sound
      verification and active text-window restore documentation pass.

1641. Reported: "I’m running the lightweight verification for the text-window
      documentation now. If that passes, the next likely target is save/restore
      path semantics from the tracker, since the `0xa9` gap is now
      source-backed."

      Action/result: Ran `mdbook build docs` and `git diff --check`; both
      passed. A first search for old `0xa9` wording had a harmless shell
      quoting error from backticks in the pattern.

1642. Reported: "The book build and whitespace check passed. I tripped a
      harmless shell quoting issue while searching for the old `0xa9` wording,
      so I’ll re-run that search safely and then start the save/restore path
      pass from disassembly."

      Action/result: Re-ran the search with safe quoting and confirmed only
      historical progress-log wording still contained the old phrase.

1643. Reported: "The tracker’s new top practical item is save/restore path
      selection and state transitions. I’m re-reading the existing save docs
      plus the handler and selector disassembly now, looking for concrete
      data-flow we can promote into a higher-level spec."

      Action/result: Re-read the existing save/restore mdBook sections,
      symbolic labels, progress tracker entries, and source windows for the
      save, restore, and selector handlers.

1644. Reported: "The selector helper is richer than the current docs show:
      `0x85e5` is mostly orchestration, with subhelpers at `0x8705` for path
      prompting/validation, `0x86a3` for drive/path availability messages,
      `0x8814` for enumerating/selecting slots, and `0x8794` for the modal text
      edit field. I’m narrowing those subhelpers from the disassembly file now
      so I can document them without guessing from UI behavior."

      Action/result: Identified the save selector's major subhelpers and moved
      to bounded disassembly windows for each one.

1645. Reported: "I noticed the prebuilt whole-file disassembly is not using the
      same image-offset origin as these helper windows, so I’m avoiding it for
      exact save-selector addresses. I’ll use bounded `ndisasm | sed` windows
      from the decrypted executable instead, where the origin/skip convention
      matches the earlier notes."

      Action/result: Used bounded `ndisasm` windows for `0x85e5`, `0x8794`,
      `0x8814`, and `0x8b9f` rather than relying on the stale origin in the
      prebuilt disassembly file.

1646. Reported: "The save selector splits cleanly now: it returns zero for
      cancel/no valid choice, otherwise returns a 1-based-ish file selector
      that gets formatted into `0x1c8c`. The save-mode special case is also
      visible: when saving into an empty-description slot, it prompts for a
      description into `0x1c6c` before creating the file."

      Action/result: Mapped selector return behavior, selected filename
      formatting, and the save-mode empty-description prompt.

1647. Reported: "There are real SQ2 save files in the local game directory,
      which is perfect for deterministic parser tests. I’m going to inspect
      their block lengths and headers, then add a small save-file parser under
      `tools/` if the files match the source-derived layout."

      Action/result: Scanned `SQ2/SQ2SG.*` and found 11 local saves matching a
      31-byte header plus five length-prefixed blocks.

1648. Reported: "Good catch from the real files: the existing save-block table
      had the first block backward. The source writes a 1,505-byte block
      starting at data address `0x0002`, not a 2-byte block starting near
      `0x05e1`; all local SQ2 saves confirm the five block lengths `[1505,
      903, 328, 200, variable]`. I’m adding a parser/test so this correction is
      pinned."

      Action/result: Corrected the first save-block interpretation and added a
      plan to pin it with parser tests.

1649. Reported: "I’m adding a tiny parser rather than a full save emulator. Its
      job is deliberately narrow: prove the file envelope the source writes and
      reads, keep block offsets/lengths explicit, and fail on truncation so
      future compatibility work has a trustworthy fixture reader."

      Action/result: Added `tools/agi_save.py` with `parse_save`/`load_save`
      and save block dataclasses; added `tests/test_save_resources.py`.

1650. Reported: "The save parser and tests are in place. I’m running the new
      save tests now, then I’ll fold the corrected block layout and selector
      flow into the mdBook and tracker."

      Action/result: Ran `python3 -B -m unittest tests.test_save_resources`;
      all four save parser tests passed.

1651. Reported: "The new save tests pass and they pin the source correction.
      I’m updating the docs now: first the exact save block envelope, then the
      selector state machine, then the compatibility/tracker notes."

      Action/result: Began updating the executable, opcode, runtime,
      compatibility, progress, and symbolic-label documentation for the
      corrected save-file and selector model.

1652. Reported: "I’m also naming the selector subhelpers in the symbol map.
      That matters for later cross-version work: the addresses will move, but
      the pattern of `select_slot_or_path -> prompt_path -> list_slots ->
      read_slot_summary` should be recognizable."

      Action/result: Prepared symbolic labels for the selector subhelper chain.

1653. Reported: "The executable chapter now has the corrected block table and
      selector flow. I’m mirroring the same model into the opcode chapter,
      keeping it concise enough that `0x7d`/`0x7e` remain readable."

      Action/result: Updated `docs/src/agi_executable.md` and then
      `docs/src/logic_bytecode.md` with the save-block envelope and selector
      flow.

1654. Reported: "The opcode chapter now says exactly what goes on disk and how
      the slot selector exits. I’m turning that into a small
      implementation-facing save/restore data model next."

      Action/result: Updated the save/restore data model in
      `docs/src/runtime_model.md`.

1655. Reported: "The runtime model is updated. I’m adding the save selector’s
      subroutine/data labels now so future version comparisons can look for
      behavior, not just the SQ2 addresses."

      Action/result: Added symbolic labels for selector subhelpers and
      save/path/header/filename buffers.

1656. Reported: "The symbol map has the save selector broken into reusable
      labels. I’m adding the new save parser tests to the compatibility chapter
      and then I’ll mark the tracker’s save/file work as more advanced, with
      the remaining gaps narrowed."

      Action/result: Documented `tests.test_save_resources` in
      `docs/src/compatibility_testing.md` and updated `PROGRESS.md`.

1657. Reported: "The tracker now narrows the save/file gap to round trips,
      error paths, and path-validation edges. I’m adding the clean-room evidence
      note for this pass with the exact commands and the save-file block
      correction, then I’ll run the relevant checks."

      Action/result: Added the clean-room executable notes section for the
      save-file selector and block-envelope source pass.

1658. Reported: "I’m bringing the progress log up to date with the text-window
      verification and save-selector work before running the next check batch.
      The log is getting long, but it’s doing exactly what the project asks:
      leaving a breadcrumb trail for the clean-room story."

      Action/result: Updated the historical progress log through the
      save-selector documentation and parser-test work.

1659. Reported: "The cleanup search is clean. Next I’m taking the tracker’s
      heap/allocation item source-first, because the disassembly should tell us
      whether this is a true free-list allocator, a bump allocator, or some
      hybrid tied to room/resource lifetimes."

      Action/result: Ran broad cleanup searches after the save-selector pass.
      A first search pattern accidentally used shell-expanded backticks in a
      double-quoted command, then the safe single-quoted searches found no
      stale save-block wording. Began source-first heap/allocation analysis.

1660. Reported: "The heap source pass is already yielding a compact model: this
      is a bump allocator with marks, not a general free list. I’m following
      each mark helper now so we can describe which lifetimes are temporary,
      room-scoped, or diagnostic-only."

      Action/result: Identified the current-top, limit, temporary-mark,
      room/reset-mark, and high-water heap globals around `0x0a55..0x0a5f`.

1661. Reported: "The allocator helpers are now source-clear enough to document
      as a normative model. One important detail: allocation failure does not
      look recoverable here; it displays the out-of-memory text and enters the
      restart/exit helper."

      Action/result: Documented `0x13d6` as a bump allocation helper with a
      fatal out-of-memory path and high-water/free-memory updates.

1662. Reported: "The startup path confirms one key lifecycle anchor: after
      initial object/inventory setup and logic 0 load, the engine stores the
      room/reset heap mark with `0x1476`. That makes the later room-switch
      cleanup much less mysterious."

      Action/result: Connected startup's `0x1476` call to the room/reset mark
      consumed by room switch, restart, and restore cleanup helper `0x1485`.

1663. Reported: "The logic-resources chapter now describes the heap as a
      mark-and-rewind bump allocator. I’m mirroring that into the runtime model
      next, because implementers should not have to reconstruct lifetime
      semantics from a helper table."

      Action/result: Added the heap helper table and diagnostic formulas to
      `docs/src/logic_resources.md`.

1664. Reported: "The runtime model has the heap lifecycle table now. I’m adding
      the same labels to the symbolic map, including the individual globals, so
      this remains useful when we compare another interpreter build with moved
      addresses."

      Action/result: Added the implementation-facing heap/allocation lifecycle
      table to `docs/src/runtime_model.md`.

1665. Reported: "That patch missed because the data labels have shifted. I’m
      reopening the exact symbol-map sections and applying it in smaller
      pieces instead of guessing at the surrounding text."

      Action/result: Re-read the symbol-map sections before applying the heap
      label updates.

1666. Reported: "I’ll pick up from the heap/allocation pass that was in flight,
      finish wiring that evidence into the tracker and docs, then keep moving
      down `PROGRESS.md` until there’s a real blocker."

      Action/result: Re-read `PROGRESS.md`, the symbol map, the progress log,
      and the current executable notes to resume from the in-progress heap work.

1667. Reported: "I found the in-progress state: the heap model is already
      written into two chapters, but the symbol map and tracker still have the
      older compressed allocator note. I’m tightening those now so the
      cross-version map has names for the allocator routines instead of one
      catch-all heap label."

      Action/result: Replaced the catch-all heap label with individual routine
      labels for allocation, current-top lookup, direct rewind, temporary mark
      save/restore, room/reset mark save, reset, free-memory update, and
      heap-status display.

1668. Reported: "The allocator routines are now individually labeled. Next I’m
      adding the matching heap globals, because those names are what will make
      later “same source, different address” comparisons less brittle."

      Action/result: Added symbolic labels for heap current top, base,
      room/reset mark, limit, temporary mark, and high-water globals.

1669. Reported: "One small documentation cleanup: the allocator docs now refer
      to the free-memory byte by name, but that byte variable did not have a
      symbol row yet. I’m adding that before updating `PROGRESS.md`, so the
      references resolve cleanly."

      Action/result: Added `data.vars.free_memory_pages_0011` to the symbol
      map.

1670. Reported: "The heap symbol map is complete enough for this pass. I’m
      marking the memory/allocation tracker as source-backed now, with the
      remaining work narrowed to initial heap setup and any observable
      out-of-memory UI edge we actually care about."

      Action/result: Updated `PROGRESS.md` to describe the source-backed
      bump-heap model and narrow remaining memory/allocation work.

1671. Reported: "The tracker now reflects the allocator as a mark-and-rewind
      bump heap instead of an unknown free-list. I’m adding the evidence note
      with the disassembly commands and the exact helper behavior, then I’ll
      run the book checks before choosing the next `PROGRESS.md` item."

      Action/result: Added the heap allocation and mark/rewind source-pass
      section to `docs/src/clean_room_executable_notes.md`.

1672. Reported: "I’m catching up the progress log now, including the allocator
      updates I reported before the context handoff and the shorter updates
      from this resumed pass. It’s a bit bookkeeping-heavy, but it keeps the
      clean-room timeline intact."

      Action/result: Updated this progress log through the resumed heap
      documentation pass.

1673. Reported: "The heap pass is now recorded across docs, tracker, symbols,
      and the progress log. I’m running the lightweight checks now; after that
      I’ll continue with the next high-value item, most likely restore/restart
      transitions from the source."

      Action/result: Ran `mdbook build docs`, `git diff --check`, and targeted
      save/sound unit tests; all passed.

1674. Reported: "The heap docs build cleanly, whitespace check is clean, and
      the targeted save/sound tests still pass. I’m moving to restore/restart
      transitions next and starting by rereading the existing source-backed
      notes so I don’t duplicate old ground."

      Action/result: Re-read existing save/restore, replay, restart, and
      symbol-map notes.

1675. Reported: "The existing notes already cover replay well, so I’m aiming
      this pass at the narrower gap: restart confirmation and restart-state
      cleanup. I’m going back to the handlers and their shared fatal/restart
      helper before changing prose."

      Action/result: Began source-first restart/termination disassembly pass.

1676. Reported: "One of the disassembly commands was too broad because
      `ndisasm -e` is a skip offset, not an end address. I caught that before
      using it as evidence; I’m switching to the existing full disassembly and
      bounded `sed` slices so the addresses I document are reliable."

      Action/result: Discarded the broad exploratory output and switched to
      bounded slices with the project image/file-offset convention.

1677. Reported: "The address convention is the EXE image address, with the file
      slice starting 0x200 bytes later. I’m using that convention now:
      `-o image_address` and `-e image_address+0x200`, then small bounded
      slices."

      Action/result: Used corrected `ndisasm` commands for handlers `0x02ae`,
      `0x027f`, `0x2472`, `0x2512`, `0x2753`, and shutdown helpers.

1678. Reported: "The restart/restore slice confirms one important thing
      already: the fatal helper at `0x02ae` calls cleanup and exits via the
      lower-level termination helper; restore read failure closes the file,
      displays the error message, and then enters that same helper. I’m mapping
      the confirm/restart action handlers next."

      Action/result: Identified `code.system.exit_with_cleanup` and confirmed
      restore read failure is not recoverable in the observed source.

1679. Reported: "The existing opcode chapter has good handler summaries; I’m
      verifying them against the slices so I can promote restart transitions
      into the runtime model without just restating the opcode table."

      Action/result: Verified `0x80`, `0x86`, `0x7e`, and `0x7d` source slices
      against the opcode chapter.

1680. Reported: "The restart path has a clearer shape now: `0x80` is an
      in-engine reset that returns zero to stop the current logic stream, while
      `0x86(1)` and restore read failure go through `0x02ae`, which performs
      shutdown/exit instead of a room-style reset. I’m checking that shutdown
      helper before naming it."

      Action/result: Traced `0x02ae` into `0x8275` and DOS termination wrapper
      `0x00ae`.

1681. Reported: "Shutdown cleanup is not just “exit”: `0x8275` closes the log
      file if it is open, then calls an interrupt/vector cleanup helper and a
      final display/driver helper before DOS termination. I’m documenting it at
      that level unless a later test needs each vector detail."

      Action/result: Mapped shutdown cleanup through log close helper `0x838c`,
      interrupt-vector restore helper `0x849f`, and BIOS video-mode helper
      `0x5a5e`.

1682. Reported: "I’m adding symbolic names for the restart and termination
      helpers now. The key distinction I want the docs to preserve is “reset
      game state and keep running” versus “cleanup and terminate DOS process.”"

      Action/result: Added restart, termination, shutdown cleanup, interrupt
      hook, and video-mode labels to `docs/src/symbolic_labels.md`.

1683. Reported: "The symbol map now separates restart, fatal exit, shutdown
      cleanup, and interrupt restoration. I’m turning that into a short runtime
      lifecycle table so implementers can model the behavior without copying
      the interpreter’s exact globals."

      Action/result: Began adding a restart/termination lifecycle table to
      `docs/src/runtime_model.md`.

1684. Reported: "That insert missed because the next heading text is slightly
      different than I remembered. I’m reopening that small section and
      patching against the exact lines."

      Action/result: Re-read the save/restore and object-lifecycle boundary in
      `docs/src/runtime_model.md`.

1685. Reported: "The runtime model already has a good object lifecycle
      immediately after save/restore, so I’m placing restart/termination
      between those. That keeps all whole-session transitions together."

      Action/result: Added the restart and termination lifecycle table to
      `docs/src/runtime_model.md`.

1686. Reported: "The runtime model now has explicit rows for accepted restart,
      canceled restart, restore success, restore read failure, and fatal exit.
      I’m updating `PROGRESS.md` so restart polish is no longer listed as an
      open gap."

      Action/result: Updated the room/restart/save/restore tracker entry and
      highest-value remaining work in `PROGRESS.md`.

1687. Reported: "The tracker now reflects the restart distinction. I’m
      recording the source pass in the evidence log, including the corrected
      `ndisasm` address convention, so the trail is reproducible."

      Action/result: Added the restart, restore-failure, and shutdown cleanup
      source-pass section to `docs/src/clean_room_executable_notes.md`.

1688. Reported: "The evidence log is updated. I’m catching the progress log up
      for the restart pass, then I’ll run checks and continue into the next item
      rather than stopping here."

      Action/result: Updated this progress log through the restart/termination
      documentation pass.

1689. Reported: "The restart checks passed. For the save/restore item, I’m
      going source-first but adding a small compatibility-facing tool
      improvement too: if we can reserialize the parsed save envelope
      byte-for-byte, future tests can mutate or generate save files without
      hand-writing binary glue."

      Action/result: Began the save/restore round-trip pass by inspecting the
      current save parser, save tests, compatibility docs, executable notes,
      tracker entry, and DOS wrapper disassembly.

1690. Reported: "I’ll pick up exactly where the context left off: the
      save/restore round-trip item. I’m going to add a byte-for-byte save
      serializer and fold the DOS file-wrapper source notes into the docs so
      this moves from “we can parse saves” to “we can preserve and generate the
      exact envelope.”"

      Action/result: Confirmed the next implementation target after context
      compaction and re-read the relevant parser, tests, docs, and tracker
      sections.

1691. Reported: "The current save helper is intentionally minimal, so the next
      edit will stay small: serialize the same five-block envelope the parser
      already accepts, then test every checked-in SQ2 save for exact byte
      preservation. That gives us a useful compatibility primitive without
      pretending we’ve modeled every in-memory field yet."

      Action/result: Prepared the save serializer/test edit scope.

1692. Reported: "The serializer is now in place and deliberately validates the
      same structural promises the parser relies on: exact 31-byte header,
      exactly five blocks, matching block order, and matching length prefixes.
      Next I’m expanding the save tests so we prove every local `SQ2SG.*` file
      round-trips byte-for-byte."

      Action/result: Added `serialize_save`, `u16le_bytes`, and `write_save` to
      `tools/agi_save.py`.

1693. Reported: "The save tests now cover exact serialization plus validation
      failures for malformed in-memory save objects. I’m running the focused
      test module before I touch the prose, so the docs describe something
      we’ve actually checked."

      Action/result: Added byte-for-byte round-trip coverage for all local
      `SQ2SG.*` files and serializer structural mismatch tests.

1694. Reported: "The focused save tests pass: 6 checks, including
      byte-for-byte reserialization of all 11 checked-in saves. I’m documenting
      that as structural compatibility evidence, while keeping the dynamic
      original-engine restore path marked as separate remaining work."

      Action/result: Ran `python3 -B -m unittest tests.test_save_resources`,
      which passed 6 tests.

1695. Reported: "The compatibility chapter now distinguishes “container
      envelope is exact” from “the engine successfully restores a generated
      scenario.” I’m making the same distinction in the executable notes so
      future readers don’t overread the static test."

      Action/result: Updated `docs/src/compatibility_testing.md` and
      `docs/src/agi_executable.md` with save envelope serialization evidence.

1696. Reported: "While checking the DOS wrapper pass, I found an older
      symbol-map problem that’s worth fixing immediately: several DOS wrapper
      labels after `open_file` were shifted to the wrong addresses. The
      disassembly is clear here, so I’m correcting the label map before I write
      more prose against those names."

      Action/result: Rechecked the DOS wrapper disassembly and found the
      correct post-open wrapper map beginning at `0x5cef`.

1697. Reported: "That patch missed because the surrounding lines had already
      shifted slightly. I’m reopening the small symbol-table window and applying
      the correction against the exact current text."

      Action/result: Re-read the current DOS wrapper rows in
      `docs/src/symbolic_labels.md`.

1698. Reported: "The stale rows are isolated. I’m replacing just that DOS
      wrapper block, so the rest of the resource/event labels stay untouched."

      Action/result: Corrected the DOS wrapper symbolic labels and added
      labels for handle duplication, current-directory/drive helpers,
      find-first/find-next, drive probing, file-time reads, and the shared
      pre-call helper.

1699. Reported: "The DOS symbol map is corrected now. I’m recording the
      correction in the evidence trail too, because stale labels are exactly
      the kind of thing that would cause pain when we compare another
      interpreter build later."

      Action/result: Added the save-envelope round-trip and DOS wrapper
      correction section to `docs/src/clean_room_executable_notes.md`.

1700. Reported: "The evidence notes now have the serializer result and the
      corrected DOS wrapper table. I’m catching up the progress log with these
      intermediate updates, then I’ll run the docs/tests checks and move on to
      the next PROGRESS item."

      Action/result: Updated this progress log through the save-envelope and
      DOS-wrapper correction pass.

1701. Reported: "One more small tracker tweak: since the wrapper map was
      corrected, I’m adding that explicitly to `PROGRESS.md` so the dashboard
      reflects the source-backed DOS helper names too."

      Action/result: Added the corrected DOS wrapper symbolic-label map to the
      DOS file I/O tracker evidence.

1702. Reported: "The tracker is caught up. I’m running the focused save tests,
      mdBook build, and whitespace checks now; after that I’ll continue down
      the remaining high-value list instead of stopping here."

      Action/result: Ran focused save tests, `mdbook build docs`, and
      `git diff --check`; all passed.

1703. Reported: "Checks are clean: save tests pass, mdBook builds, and
      `git diff --check` is quiet. Next I’m staying on the save/restore item,
      but shifting back to the disassembly to map the actual read/write helper
      failure paths rather than inferring them from the file format."

      Action/result: Started source inspection of the save and restore handler
      failure paths around image offsets `0x2512`, `0x26b0`, `0x2753`, and
      `0x28c6`.

1704. Reported: "The source pass confirms the error split: save write failures
      are recoverable after closing and deleting the partial file, while
      restore block-read failures go through fatal cleanup. I’m checking the
      local strings around those message offsets so the docs name the
      observable prompts more clearly."

      Action/result: Inspected `AGIDATA.OVL` strings around `0x0d34..0x0e46`
      and confirmed the save/restore confirmation and error messages.

1705. Reported: "The strings confirm the observable messages: restore read
      failure says “Error in restoring game” and then quits, while save
      create/write problems are “directory full/write-protected” or “disk full”
      style continue prompts. I’m adding a concise failure-path table to the
      implementation-facing docs."

      Action/result: Prepared runtime-model save/restore failure lifecycle
      update.

1706. Reported: "The runtime model already had restore success/failure, but it
      didn’t distinguish recoverable save/open failures from fatal restore
      reads. I’m extending that lifecycle table so an implementer can model the
      continuation behavior directly."

      Action/result: Added save create failure, save write failure, and restore
      open failure rows to `docs/src/runtime_model.md`.

1707. Reported: "The lifecycle table now captures save create failure, save
      write failure, restore open failure, restore success, and restore read
      failure as separate transitions. I’m adding the lower-level call/return
      details to the executable chapter next."

      Action/result: Updated `docs/src/agi_executable.md` with write/read
      helper return rules and save/restore failure continuations.

1708. Reported: "The executable chapter now has the helper-level behavior. I’m
      also tightening the opcode rows, because `0x7d` and `0x7e` are where most
      readers will first look for save/restore continuation semantics."

      Action/result: Updated the `0x7d` and `0x7e` rows in
      `docs/src/logic_bytecode.md` with create/open/write/read failure
      behavior.

1709. Reported: "The opcode rows now include the recoverable versus fatal
      failure distinction too. I’m recording this source pass in the clean-room
      notes with the exact disassembly/string probes that support it."

      Action/result: Added the save/restore file-error source-pass section to
      `docs/src/clean_room_executable_notes.md`.

1710. Reported: "The clean-room notes now have the save/restore error-path
      pass. I’m updating the progress log, then I’ll run checks and continue to
      the next highest-value area in `PROGRESS.md`."

      Action/result: Updated this progress log through the save/restore
      file-error documentation pass.

1711. Reported: "Since the source-backed file error paths are now documented,
      I’m narrowing the tracker wording. The remaining save work is mainly
      dynamic round-trip and representative UI probes, not basic source
      mapping."

      Action/result: Narrowed the save/restore and DOS file I/O remaining-work
      text in `PROGRESS.md`.

1712. Reported: "The tracker now reflects that the source mapping is done and
      the dynamic/UI side remains. I’m running checks for the doc changes, then
      I’ll inspect the existing QEMU logic probe harness to see whether a
      save/restore round-trip case can be added cleanly without inventing a
      one-off path."

      Action/result: Ran focused save tests, `mdbook build docs`, and
      `git diff --check`; all passed. Searched the logic probe harness for
      save/restore cases and input support.

1713. Reported: "The harness search shows existing save/restore coverage is
      mostly Escape/cancel smoke, not a full file round-trip. I’m reading the
      probe generator now to see how it handles post-launch keys and fixture
      DOS directories before deciding whether to add a dynamic save case or
      leave it as a larger follow-up."

      Action/result: Re-read `tools/logic_interpreter_probe.py` helpers, case
      definitions, and snapshot runner.

1714. Reported: "A full save/restore round trip through the UI is probably more
      involved than a single new case, but the harness can patch
      `AGIDATA.OVL`. I’m checking the selector source to see whether a
      prefilled path/description buffer lets us trigger a representative
      open/create error without brittle key navigation."

      Action/result: Disassembled the save/restore selector around
      `0x85e5..0x8814` and inspected save-related initial data.

1715. Reported: "The selector does have a noninteractive path when `[0x0e72]`
      is already nonzero, but it still goes through slot matching/formatting
      rather than simply trusting `0x1c8c`. I’m reading that branch before I
      decide whether a patched fixture will be stable enough for QEMU evidence."

      Action/result: Inspected the noninteractive slot-matching branch around
      `0x894e..0x8b99` and the filename formatter/path validator helpers.

1716. Reported: "This selector path is not quite a clean one-liner: the
      prefilled-buffer branch still scans slot summaries and may fall back
      through UI-like selection logic. Rather than force a brittle dynamic save
      probe, I’m going to document that constraint and move to the next
      high-value item, the picture/view renderer compatibility work, where we
      have more direct harnesses."

      Action/result: Deferred a dynamic save/restore probe as a larger focused
      task and moved to the picture/view compatibility tracker items.

1717. Reported: "The picture/view tracker points to two practical gaps: valid
      picture edge semantics and broader view clipping. I’m starting with the
      view batch because the test already says base coverage includes mirror
      and top/left clipping, but `PROGRESS.md` still calls out right/bottom
      clipping as remaining."

      Action/result: Inspected picture/view progress entries, view-batch tests,
      picture fuzz tests, and related docs.

1718. Reported: "The object-overlay harness already has right and bottom edge
      cases, but the simpler picture-plus-view batch only has left/top. I’m
      going to broaden that base batch with right/bottom clipping cases and add
      local tests so the coverage is visible before any QEMU run."

      Action/result: Re-read `tools/view_batch.py`, object-overlay clip cases,
      and clipping-related docs/tests.

1719. Reported: "View 11’s frame is 20 by 5, so clean right and bottom cases
      are straightforward: request left `150` to exercise right clamping to
      `140`, and baseline `170` to exercise bottom clipping past the 168-row
      logical screen. I’m adding those to the base view batch and tests."

      Action/result: Added `view_011_right_clip` and `view_011_bottom_clip` to
      the base view-batch registry.

1720. Reported: "The local frame type names the raw control byte rather than
      `transparent_color`, so that quick dimension probe tripped on an
      attribute name. I’m rerunning it with the actual fields and checking the
      compose clipping function before adding cases."

      Action/result: Confirmed view 11/group 0/frame 0 dimensions as 20x5 with
      control byte `0x01`, and reran view-batch tests.

1721. Reported: "The base view batch now includes right and bottom clipping.
      I’m updating the tests so they assert all four clip directions explicitly
      and keep the expected base/stress counts honest."

      Action/result: Updated `tests/test_view_batch.py` for four edge case IDs
      and the new base count.

1722. Reported: "The local coverage tests are updated. I’m running the
      view-batch tests now, then I’ll decide whether to run a small QEMU
      snapshot for the two new cases or the full base batch."

      Action/result: Ran `python3 -B -m unittest tests.test_view_batch`; all 5
      tests passed.

1723. Reported: "The view tests pass. To run just the two new QEMU cases
      cleanly, I’m adding the same repeated `--case` filter that the other
      probe harnesses already have, instead of creating an ad hoc JSON fixture
      file."

      Action/result: Added repeated `--case` filtering to `tools/view_batch.py`.

1724. Reported: "The view harness has the filter now. I’m adding a small unit
      test for selected-case loading, including the unknown-case error, so the
      CLI behavior is covered before I use it."

      Action/result: Added view-batch case-filtering tests.

1725. Reported: "The filter test is in place. I’m running the view-batch unit
      tests again; if they pass, I’ll launch just the two new clipping cases
      through QEMU snapshot mode."

      Action/result: Ran `python3 -B -m unittest tests.test_view_batch`; all 6
      tests passed.

1726. Reported: "The view-batch tests pass with the new filter. I’m running a
      two-case QEMU snapshot batch for `view_011_right_clip` and
      `view_011_bottom_clip` now, which should give us original-engine evidence
      without running the whole suite."

      Action/result: Ran `clip_right_bottom_001`; QEMU produced a mismatch for
      `view_011_right_clip`.

1727. Reported: "The right-edge QEMU case mismatched, so that’s useful rather
      than bad: our simple local composition model is missing an observable
      placement rule for this path. I’m inspecting the report and generated
      capture to see whether this is the same spiral placement behavior already
      seen in object-overlay probes or a separate view-batch fixture issue."

      Action/result: Inspected the failed report and capture; the mismatch
      bbox aligned with placement-search behavior rather than a decode failure.

1728. Reported: "The mismatch is the same placement-search rule already
      documented for `add_to_pic`: a right-edge request for view 11 at left
      `150`, baseline `80` lands at left `140`, baseline `67`, not at a simple
      clamped baseline `80`. I’m going to make the view-batch case model allow
      expected placement overrides, then rerun right and bottom together."

      Action/result: Rechecked object-overlay clip cases and placement-search
      tests for comparison.

1729. Reported: "The object-overlay helper already has a source-derived
      fallback for the right-edge placement. I’m reusing that idea in the
      simpler view batch by adding optional expected position fields, rather
      than changing the renderer’s direct composition primitive."

      Action/result: Inspected `ObjectOverlayCase` and its
      `search_object_placement`-based comparison path.

1730. Reported: "Actually the better reuse is the existing
      `search_object_placement` helper from `agi_graphics`, which already
      models the bounds-only spiral search. I’m wiring view-batch comparison
      through that helper by default, with optional overrides for future odd
      cases."

      Action/result: Re-read the placement-search helper and computed candidate
      placements for the new view requests.

1731. Reported: "The placement search predicts the new requests as `(150,80)
      -> (140,71)` and `(20,170) -> (23,167)`. I’m updating `view_batch.py` so
      QEMU comparisons use this source-derived placement search, matching how
      object-overlay probes already handle `add_to_pic`."

      Action/result: Added `expected_view_tuple` and source-derived placement
      comparison to `tools/view_batch.py`.

1732. Reported: "The view comparison now runs requested placements through
      `search_object_placement` unless a case provides an explicit expected
      override. I’m adding unit checks for the predicted right and bottom
      placements so the behavior is pinned locally too."

      Action/result: Added placement expectation tests for the right and bottom
      view-batch cases.

1733. Reported: "The placement expectations are now explicit in tests. I’m
      running the view-batch tests, then I’ll rerun the two-case QEMU batch."

      Action/result: Ran `python3 -B -m unittest tests.test_view_batch`; all 7
      tests passed.

1734. Reported: "The local view tests pass, including the source-derived
      placement expectations. I’m rerunning the same two QEMU cases now to see
      whether right and bottom clipping line up with the original engine."

      Action/result: Ran `clip_right_bottom_002`; both right and bottom cases
      matched with 0 mismatches.

1735. Reported: "The rerun matched both cases: right and bottom clipping are
      now QEMU-validated in the view batch using the placement-search
      expectation. I’m updating the docs and tracker with both the failed first
      run and the corrected source-derived result so the evidence trail stays
      honest."

      Action/result: Began documentation updates for the view-batch
      right/bottom placement validation.

1736. Reported: "I’m updating the compatibility chapter now: the base view
      registry has grown from the original six to eight, and the new
      right/bottom cases have a focused QEMU report with 2 matches. The older
      six-case/stress notes stay as historical runs rather than being rewritten
      as if we reran everything."

      Action/result: Updated `docs/src/compatibility_testing.md` with the
      focused right/bottom view-batch command, initial mismatch note, and
      corrected match result.

1737. Reported: "The compatibility notes now record the initial mismatch and
      the corrected two-case QEMU match. I’m adding the same placement details
      to the graphics pipeline chapter so the implementation model and test
      evidence stay connected."

      Action/result: Updated `docs/src/graphics_object_pipeline.md` with the
      new right/bottom placement-search evidence.

1738. Reported: "The graphics chapter now ties the new view-batch evidence to
      the existing `0x593a` placement model. I’m narrowing `PROGRESS.md` so
      right/bottom clipping is no longer listed as an open view-renderer gap."

      Action/result: Updated the view resource tracker in `PROGRESS.md`.

1739. Reported: "The tracker is narrowed. I’m recording the view-batch
      source/test/QEMU pass in the evidence notes, including the failed first
      comparison because it explains why the harness now uses placement search."

      Action/result: Added the view-batch right/bottom placement validation
      section to `docs/src/clean_room_executable_notes.md`.

1740. Reported: "The evidence notes now have the right/bottom view placement
      pass. I’m catching the progress log up with the save-probe decision and
      the view-batch work before I run the broader checks."

      Action/result: Updated this progress log through the view-batch
      right/bottom placement validation pass.

1741. Reported: "Focused checks are clean. I’m staying in picture/view
      compatibility now, since `PROGRESS.md` still calls out valid-picture edge
      semantics and broader renderer comparisons as a high-value open area."

      Action/result: Returned to the picture/view compatibility tracker after
      the view-batch validation pass.

1742. Reported: "The picture fuzz base already has both corner commands and the
      lower-right edge behavior pinned. I’m looking for the next useful
      source-backed gap: either a compact real-resource batch or a focused
      priority/control interaction, and I’ll choose the one with the cleanest
      evidence path."

      Action/result: Reviewed existing picture fuzz and view/object coverage to
      avoid duplicating already-covered edge cases.

1743. Reported: "There isn’t a reusable real-picture batch harness yet, only
      one-off fixture generation and comparison. I’m going to add that first so
      we can keep growing original-engine parity checks without rebuilding the
      plumbing each time."

      Action/result: Started a reusable real-picture QEMU batch harness.

1744. Reported: "Before picking real-picture batch seeds, I’m scanning the
      local picture directory for a couple of useful representatives: first
      present resource, largest payload, and pattern-command coverage."

      Action/result: Scanned the local SQ2 picture corpus to choose small base
      cases for the real-picture batch.

1745. Reported: "Picture 45 is still the largest payload in this local corpus,
      and picture 1 gives us an early resource with pattern plotting. I’m using
      those as the initial real-picture batch so the first run is meaningful
      but not huge."

      Action/result: Selected picture 1 and picture 45 as the first reusable
      real-picture parity cases.

1746. Reported: "The new picture-batch harness is in place. It can run either
      serially or through the existing QEMU snapshot path, and it writes the
      same kind of JSON summary we use for the fuzz/view batches."

      Action/result: Added `tools/picture_batch.py`.

1747. Reported: "The picture-batch tests are written for case loading,
      filtering, DOS directory naming, and report summaries. I’m running them
      alongside the view-batch tests before using QEMU."

      Action/result: Added `tests/test_picture_batch.py`.

1748. Reported: "The local picture/view batch tests pass. I’m running the
      two-case real-picture batch in QEMU snapshot mode now."

      Action/result: Ran the local picture/view batch unit tests successfully.

1749. Reported: "The picture batch built its fixtures, but QEMU couldn’t bind
      the local VNC port from the sandbox, so it failed before the game ran.
      I’m rerunning that exact harness with the existing escalation path rather
      than changing the evidence target."

      Action/result: Recorded the unprivileged QEMU/VNC bind failure as a
      sandbox execution issue, not interpreter behavior.

1750. Reported: "The real-picture QEMU batch passed: picture 1 and picture 45
      both matched with 0 mismatches. I’m adding this reusable command to
      `AGENTS.md`, then I’ll update the compatibility docs and progress
      tracker."

      Action/result: Ran `picture_base_001`; both real-picture cases matched.

1751. Reported: "AGENTS now includes the real-picture batch command. I’m adding
      the compatibility report details next: the base batch covers the first
      present picture and the largest valid picture payload, both matched
      against the original engine."

      Action/result: Added the real-picture batch command to `AGENTS.md`.

1752. Reported: "That doc patch missed on the later provisional paragraph
      because it has shifted wording. I’m reopening the exact sections and
      applying the update in smaller pieces."

      Action/result: Re-opened the compatibility sections and applied the
      real-picture batch documentation in smaller patches.

1753. Reported: "The evidence trail is caught up for the real-picture batch.
      I’m running the focused unit tests and doc build now; if those are clean,
      I’ll use `PROGRESS.md` to choose the next reverse-engineering chunk rather
      than stopping at bookkeeping."

      Action/result: Ran focused picture/view/save tests, mdBook build, and
      whitespace checks successfully.

1754. Reported: "Focused verification passed: picture/view/save tests, mdBook,
      and whitespace checks are clean. I’m moving to the next open
      `PROGRESS.md` item now, with a source-first pass and QEMU only if it gives
      us a durable compatibility test."

      Action/result: Re-read the high-value remaining-work list and selected
      picture/view renderer compatibility as the next source-first target.

1755. Reported: "The next tracker items overlap: picture/view parity and
      implementation-ready object drawing. Since the user has explicitly pushed
      for source-first work, I’m going to inspect the picture drawing routines
      around the mask/pattern paths before adding more QEMU cases."

      Action/result: Began a picture pattern/mask disassembly pass.

1756. Reported: "The source map already has labels for the picture command
      scanner and pattern data tables, so I’m narrowing onto the pattern-plot
      routine itself. The aim is to turn “odd/even mask interactions” from a
      tracker phrase into exact behavior we can encode and test."

      Action/result: Re-read the pattern plot documentation, local renderer,
      and disassembly windows around picture command dispatch and pixel writes.

1757. Reported: "The first disassembly window landed in the middle of adjacent
      code and table bytes, so I’m realigning from the known scanner entry and
      following the dispatch target into `0xfa`. This is exactly the sort of
      place where labels help but raw source still needs a careful re-read."

      Action/result: Realigned disassembly to the command scanner, pattern
      handler, coordinate readers, and common pixel writer.

1758. Reported: "One useful correction surfaced immediately: the picture
      routine labels in the docs are loaded-image offsets, while `ndisasm -e`
      is reading file offsets. For this executable that creates a 0x200-byte
      difference in this region, so I’m keeping the existing symbolic labels
      but recording file-offset windows explicitly in the evidence notes."

      Action/result: Kept existing symbolic labels and recorded the file-offset
      detail in the clean-room notes.

1759. Reported: "The disassembly confirms pattern plotting does not have its
      own channel semantics: it stores candidate coordinates in the normal
      picture pixel register and calls the same pixel writer as lines and
      fills. The odd/even behavior therefore lives in the color-enable commands
      and `pixel_write`, so I’m reading the color mapper next."

      Action/result: Inspected the common pixel writer and EGA color-mapper
      path.

1760. Reported: "For full 16-color EGA, the mapper returns the same nibble in
      `AL` and `AH`, so odd/even masks exist but do not diverge for visual
      colors. A good next compatibility step is to add valid synthetic pattern
      cases that cross multiple rows with visual-only, control-only, and
      visual+control active, proving the shared pixel writer’s channel-mask
      behavior through QEMU."

      Action/result: Chose three safe pattern-channel fuzz cases based on the
      source-backed common pixel-writer path.

1761. Reported: "I’m going to add three curated valid picture-fuzz cases:
      visual+control pattern writes, visual-disabled/control-only pattern
      writes, and control-disabled/visual-only pattern writes. The local tests
      will assert both nibbles; the QEMU batch will validate the visible EGA
      surface for these streams against the original engine."

      Action/result: Added `base_027`, `base_028`, and `base_029` to
      `tools/picture_fuzz.py`, plus renderer tests for channel-mask behavior.

1762. Reported: "The curated fuzz cases and local channel assertions are in.
      I’m adding a small harness test too, so the new case IDs stay part of the
      stable base corpus rather than quietly drifting."

      Action/result: Added a base-case ID assertion to `tests/test_picture_fuzz.py`.

1763. Reported: "The local assertions now distinguish visible and control
      nibbles for pattern plotting. I’m running the focused renderer/fuzz tests
      before regenerating the corpus and asking QEMU to confirm the visible
      surface."

      Action/result: First focused test run failed, revealing that the sample
      control class used in the both-active case matched the default control
      nibble and therefore did not show as a control change.

1764. Reported: "The new tests caught something useful before QEMU: my
      assumptions about the sample payload were off, not the executable. The
      cell values show the command stream I chose is not isolating the intended
      channel state, so I’m inspecting the renderer command stepping and then
      I’ll adjust the fixtures to match the source semantics."

      Action/result: Probed the three sample payloads locally and identified
      default control nibble `4` as the reason one assertion was wrong.

1765. Reported: "Found the issue: the default control nibble is already `4`, so
      using control color 4 made “changed control pixels” look unchanged. I’m
      switching the both-active case to control 5 and adjusting the
      control-disabled expectation to preserve the default high nibble."

      Action/result: Changed `base_027` to control class `5` and corrected the
      control-disabled expected cell value.

1766. Reported: "The channel tests now use a non-default control class when
      they need to observe a control change. I’m rerunning the focused tests and
      regenerating the small corpus so the manifest matches the patched cases."

      Action/result: Focused renderer/fuzz tests passed; regenerated the small
      pattern-channel corpus with 38 cases and 36 safe-for-QEMU cases.

1767. Reported: "The local renderer and corpus tests are clean. I’m running the
      three new valid pattern-channel cases through the original engine now;
      this only validates the visible EGA output, while the control-nibble part
      stays source-backed and locally tested."

      Action/result: Started QEMU snapshot batch `pattern_channel_masks_001`.

1768. Reported: "QEMU is running the three-case snapshot batch now. It has
      built all fixtures and booted the shared snapshot disk; I’m waiting on
      the captures/comparisons."

      Action/result: Waited for the running QEMU snapshot batch.

1769. Reported: "The QEMU batch matched all three new cases with zero
      mismatches. I’m documenting the source result and the visible-surface
      confirmation now, including the caveat that QEMU screenshots do not
      expose the control buffer directly."

      Action/result: Began updating compatibility, graphics pipeline, progress,
      and clean-room evidence notes for the pattern channel-mask pass.

1770. Reported: "The old compatibility paragraph still says there are 27
      curated base cases. With the three new channel-mask cases, that needs to
      become 30; I’m updating the docs and then I’ll regenerate the standard
      corpus so the recorded count is true."

      Action/result: Updated compatibility docs and `PROGRESS.md` for the
      three new pattern-channel cases and the narrowed EGA odd/even-mask gap.

1771. Reported: "The compatibility chapter and tracker now describe the
      channel-mask cases and narrow the odd/even visual-mask gap to non-EGA
      behavior. I’m regenerating the standard deterministic corpus next so the
      docs’ 1,054/1,052 counts match the current base-case set."

      Action/result: Regenerated the standard fuzz corpus; it reported 1,054
      total cases and 1,052 safe-for-QEMU cases.

1772. Reported: "The regenerated corpus reports 1,054 total cases and 1,052
      safe-for-QEMU cases, as expected. I’m recording the exact source windows,
      tests, corpus generation, and QEMU result in the clean-room notes now."

      Action/result: Added the pattern channel-mask source/QEMU evidence section
      to `docs/src/clean_room_executable_notes.md`.

1773. Reported: "The evidence notes are updated with the source-first
      channel-mask pass. I’m catching the progress log up now, then I’ll run the
      relevant checks and decide the next `PROGRESS.md` item."

      Action/result: Updated this progress log through the pattern channel-mask
      pass.

1774. Reported: "The progress log is caught up through the channel-mask pass.
      I’m running focused checks now; if they pass, I’ll keep going into the
      next open item instead of stopping."

      Action/result: Ran focused picture/fuzz/picture-batch/view/save tests,
      mdBook build, and whitespace checks successfully.

1775. Reported: "Focused checks are clean after the channel-mask work. The next
      useful picture task is broader real-resource parity, so I’m scanning the
      local picture corpus for representative resources instead of simply
      picking room numbers by hand."

      Action/result: Scanned all valid local `PICDIR` payloads and ranked them
      by payload size, pattern count, fill count, and command-family diversity.

1776. Reported: "The corpus scan gives a better broad-picture set than just
      “more numbers”: picture 46 is pattern-heavy, 44 is fill-heavy, 17
      exercises all command families with several pattern-mode changes, and
      43/45 are large dense resources. I’m extending the real-picture batch
      harness with `base`, `broad`, and `all` presets, then I’ll run the broad
      preset in QEMU."

      Action/result: Added `broad_cases`, `all_present_cases`, and preset
      selection to `tools/picture_batch.py`.

1777. Reported: "The harness now has a dynamic `all` preset plus a curated
      `broad` preset. I’m running its unit tests before taking the broad set to
      QEMU."

      Action/result: Added preset/discovery tests and ran
      `python3 -B -m unittest tests.test_picture_batch`; all 8 tests passed.

1778. Reported: "The picture-batch tests pass. I’m running the broad
      eight-picture preset through the original engine with one QEMU snapshot
      now; this should give us a much stronger real-resource parity sample
      without committing to a full 74-picture run yet."

      Action/result: Started QEMU snapshot batch `picture_broad_001`.

1779. Reported: "The broad real-picture run has built all eight fixtures and
      is executing from the snapshot disk. I’m waiting for the captures and
      comparisons; if one fails, the report should stop at the first mismatch
      because this is a parity run."

      Action/result: Waited for the broad real-picture QEMU batch.

1780. Reported: "Still waiting on the broad QEMU batch; the larger real
      pictures take longer to render/capture than the tiny synthetic cases. The
      run is still active, so I’m leaving it alone and polling."

      Action/result: Continued polling the running broad QEMU batch.

1781. Reported: "Five of the eight broad real-picture cases have matched so
      far, including the dense/fill-heavy ones. I’m waiting on the remaining
      largest/pattern-heavy cases now."

      Action/result: Observed the first five broad cases matching during the
      running QEMU batch.

1782. Reported: "The broad real-picture batch passed: all eight representative
      resources matched the original engine with zero mismatches. I’m adding
      the preset command/result to the docs and progress tracker now."

      Action/result: Recorded `picture_broad_001` as 8 matches, 0 mismatches,
      and 0 errors.

1783. Reported: "The broad batch evidence is now in the compatibility chapter
      and tracker. I’m adding the broad preset command to `AGENTS.md` too, so a
      future agent can rerun the representative real-resource check directly."

      Action/result: Added the broad picture-batch command to `AGENTS.md`.

1784. Reported: "`AGENTS.md` has the broad real-picture command now. I’m
      recording the corpus-selection scan, harness preset changes, tests, and
      QEMU result in the clean-room notes before running the verification suite
      again."

      Action/result: Added the broad real-picture preset parity section to
      `docs/src/clean_room_executable_notes.md`.

1785. Reported: "The progress log is current through the broad real-picture
      batch. I’m running the focused checks plus mdBook and diff whitespace
      again; after that I’ll move to the next remaining item."

      Action/result: Ran focused picture-batch, graphics-rendering,
      picture-fuzz, view-batch, and save tests plus mdBook and whitespace
      checks; all passed.

1786. Reported: "Checks are clean. Since the broad preset passed, the natural
      next step is a full present-picture parity batch; the harness now
      supports it, and this would retire most of the remaining “broader
      real-resource parity” risk if the DOS image has enough room. I’m checking
      the snapshot-disk constraints before launching a long run."

      Action/result: Inspected snapshot helper behavior, all-present case count,
      fixture sizes, and current DOS snapshot image size/free space.

1787. Reported: "The full 74-picture run would likely exceed the 64 MB DOS
      snapshot image because each fixture directory carries a full runnable game
      copy, and 74 copies would be around 70 MB before filesystem overhead. I’m
      checking whether we can shrink picture fixtures or whether the practical
      next step should be a few preset batches rather than one giant disk."

      Action/result: Compared full-tree fixture contents and confirmed repeated
      original volumes/save files dominated picture-batch fixture size.

1788. Reported: "There’s a better way around the full-corpus disk problem: pack
      each tested picture payload into that fixture’s `VOL.3` alongside the
      generated `LOGIC.0`, and copy only the small engine/support files. That
      should make a 74-picture snapshot feasible while preserving the original
      picture data being tested. I’m going to implement this as a packed
      fixture path for `picture_batch.py` and validate it against the
      already-passing broad preset before attempting all pictures."

      Action/result: Designed the packed picture fixture approach.

1789. Reported: "I’m adding a new packed picture-fixture builder rather than
      changing the older one-off fixture generator. That keeps historical
      commands stable while letting batch runs use the smaller, purpose-built
      layout."

      Action/result: Added `copy_minimal_picture_tree` and
      `build_packed_picture_fixture` to `tools/qemu_fixture.py`.

1790. Reported: "`picture_batch.py` now uses packed picture fixtures, while
      `qemu_fixture.py picture` remains the older full-tree generator. I’m
      adding a unit check that the packed fixture actually omits the big
      original volumes and repoints `PICDIR` into `VOL.3`."

      Action/result: Updated `tools/picture_batch.py` and added packed-fixture
      structural coverage to `tests/test_qemu_fixture.py`.

1791. Reported: "There is already a qemu-fixture test module, so I’m putting
      the packed-fixture structural check there instead of squeezing it into
      picture-batch tests."

      Action/result: Integrated the packed-fixture test with existing
      qemu-fixture tests.

1792. Reported: "The packed fixture structure test is in. I’m running the
      qemu-fixture and picture-batch unit tests now; after that I’ll validate
      the packed layout with a small QEMU run before considering all 74
      pictures."

      Action/result: Ran `tests.test_qemu_fixture` and `tests.test_picture_batch`;
      all 37 tests passed. A local size probe showed packed picture fixtures are
      about 72 KB of input files.

1793. Reported: "The packed fixture is tiny now, about 72 KB per picture
      instead of roughly 1.7 MB. Unit tests pass, so I’m running the two-picture
      base QEMU batch with the packed layout to make sure the original engine
      is happy with the trimmed fixture set."

      Action/result: Ran `picture_base_packed_001`; pictures 1 and 45 matched
      with 0 mismatches.

1794. Reported: "The packed base QEMU run matched both pictures, so the
      trimmed fixture set is valid. I’m launching the full 74-picture present
      resource batch now with packed fixtures; this may run for a while, but it
      should fit on the snapshot image."

      Action/result: Started QEMU snapshot batch `picture_all_001` using
      `--preset all` and packed fixtures.

1795. Reported: "The full-picture batch built all 74 packed fixtures and is now
      running in QEMU from one snapshot. I’ll keep polling; this is the long
      parity pass."

      Action/result: Confirmed the full QEMU batch had entered the capture
      phase.

1796. Reported: "No comparison output yet; QEMU is still active. The first
      batch output usually appears after the initial cases have rendered and
      screendumped, so I’m continuing to wait."

      Action/result: Continued polling the active QEMU process.

1797. Reported: "Still no per-case results from the full-picture run, but the
      QEMU process has not exited. I’m letting it continue; with 74 cases the
      snapshot setup and early captures can be a little quiet."

      Action/result: Continued waiting on the full-picture QEMU batch.

1798. Reported: "A quick note on the silence: `picture_batch.py` compares only
      after `run_snapshot_qemu_cases` finishes all captures, so it won’t print
      per-picture matches during the QEMU phase. This is expected for the full
      run."

      Action/result: Clarified the batch harness output behavior while the run
      continued.

1799. Reported: "The full QEMU run is still active. I’m continuing to poll and
      will report the summary once the capture phase completes."

      Action/result: Continued polling the active QEMU process.

1800. Reported: "This is taking long enough that I’m checking the capture
      directory from the host side while QEMU continues, just to make sure files
      are being produced and we’re not waiting on a dead run."

      Action/result: Counted 19 generated captures, proving the full run was
      progressing.

1801. Reported: "Host-side check shows 19 captures have already been written,
      so the full-picture batch is progressing normally. I’m letting it keep
      running."

      Action/result: Continued the full-picture QEMU batch.

1802. Reported: "The full QEMU capture phase is still running. I’m staying with
      it; once QEMU exits the script will compare all generated screenshots in
      one pass."

      Action/result: Continued polling the active QEMU process.

1803. Reported: "Another quick progress check from the filesystem side: I’m
      checking how many captures have landed so far."

      Action/result: Counted 26 generated captures.

1804. Reported: "We’re at 26 captures out of 74, so the run is moving steadily.
      No action needed beyond waiting."

      Action/result: Continued the full-picture QEMU batch.

1805. Reported: "The full-picture parity run is still in the capture phase. I’m
      continuing to let QEMU work through the list."

      Action/result: Continued polling the active QEMU process.

1806. Reported: "Polling the capture count again so we have a rough sense of
      progress."

      Action/result: Counted 33 generated captures.

1807. Reported: "33 of 74 captures are present now. The run is almost halfway
      through the QEMU phase."

      Action/result: Continued the full-picture QEMU batch.

1808. Reported: "Still running; I’m continuing to poll. The silence from the
      script is expected until all 74 screenshots have been captured."

      Action/result: Continued polling the active QEMU process.

1809. Reported: "Checking capture count again."

      Action/result: Counted 40 generated captures.

1810. Reported: "40 of 74 captures are in. The packed fixture approach is
      paying off; the disk is not the bottleneck now, just the per-case
      draw/capture loop."

      Action/result: Continued the full-picture QEMU batch.

1811. Reported: "The full-picture run is still active. I’m waiting on the
      remaining capture loop."

      Action/result: Continued polling the active QEMU process.

1812. Reported: "When asked about using input to cycle through resources:
      \"Yes, absolutely, and it’s a good idea. The current snapshot harness
      optimizes away DOS boot, but it still starts a fresh engine process per
      case so every capture is isolated and easy to reason about...\""

      Action/result: Identified carousel-style resource sweeps as a useful
      future throughput optimization while keeping the current isolated harness
      as a reference oracle.

1813. Reported: "The current full-picture batch is still running in the slower
      per-process snapshot style. I’m going to let it finish for this run, then
      I can add a carousel mode as a follow-up because it fits exactly the
      bottleneck we’re hitting."

      Action/result: Continued the existing full-picture batch rather than
      interrupting it to change harness strategy mid-run.

1814. Reported: "Good call. Simply growing the raw file would not help by
      itself because the DOS partition/FAT geometry inside it would still
      describe the old 64 MB volume; we’d need a larger formatted/bootable DOS
      test image or a purpose-built large fixture image. For the current run the
      packed fixtures avoid the limit, so I’m letting it finish, but I’ll note
      the larger-image path in the docs and can build one if the carousel/all-
      in-one fixture starts wanting more room."

      Action/result: Confirmed that packed fixtures solved the current DOS image
      limit and documented the need for a properly formatted larger image if
      future batches need more space.

1815. Reported: "The long run is still active, so I’m checking capture progress
      again while it continues."

      Action/result: Counted 56 generated captures.

1816. Reported: "56 of 74 captures are present. We’re through most of the
      current batch; after it finishes I’ll document both your carousel idea and
      the DOS-image-size note, then decide whether to implement carousel mode
      next."

      Action/result: Continued the full-picture QEMU batch.

1817. Reported: "Agreed. Once this run finishes, I’m going to treat batch
      throughput as part of the reverse-engineering infrastructure, not just a
      convenience: carousel-style scripts for picture/view sweeps, larger or
      purpose-built DOS test images where needed, and keeping the isolated
      per-case harness as the slow but simple reference path. That will matter
      a lot when we start comparing interpreter versions across games."

      Action/result: Promoted high-throughput batch infrastructure to an
      explicit future work item for cross-game/interpreter comparison.

1818. Reported: "The run is still alive. I’m checking the capture count again;
      if it completes cleanly, the next infrastructure task is clearly a faster
      in-engine resource sweep mode rather than just adding more one-shot
      batches."

      Action/result: Counted 64 generated captures.

1819. Reported: "64 of 74 captures are present. We’re on the final stretch of
      this slower full-picture pass."

      Action/result: Continued the full-picture QEMU batch.

1820. Reported: "Still running; I’m letting QEMU finish the last ten-ish cases."

      Action/result: Continued polling the active QEMU process.

1821. Reported: "Polling capture count one more time as it nears the end."

      Action/result: Counted 71 generated captures.

1822. Reported: "71 of 74 captures are in. The capture phase should finish
      soon, then the script will compare all 74 against the local renderer."

      Action/result: Continued the full-picture QEMU batch.

1823. Reported: "The capture phase finished and comparisons have started. First
      two pictures matched; I’m waiting for the full comparison summary."

      Action/result: Observed the first two full-picture comparisons matching.

1824. Reported: "The comparison pass is moving quickly now: the first 30
      present pictures have matched. Continuing to poll for the rest."

      Action/result: Observed the first 30 full-picture comparisons matching.

1825. Reported: "60 of 74 comparisons have matched. The full corpus parity
      result is looking very good; waiting on the final fourteen."

      Action/result: Observed 60 full-picture comparisons matching.

1826. Reported: "Full present-picture parity passed: all 74 valid SQ2 pictures
      matched the original engine with 0 mismatches. I’m going to document that
      result, plus the packed-fixture optimization and your carousel/larger-
      image notes, then I’ll run the full checks."

      Action/result: Recorded `picture_all_001` as 74 matches, 0 mismatches, and
      0 errors.

1827. Reported: "I’m updating the docs now in two layers: first the factual
      result (74/74 pictures matched), then the infrastructure lesson (packed
      fixtures solved the 64 MB pressure, and carousel/input-driven sweeps
      should be added for future multi-game work)."

      Action/result: Updated compatibility docs and the progress tracker with
      the full present-picture parity result.

1828. Reported: "The report gives us a strong milestone: every valid local SQ2
      picture resource now matches pixel-for-pixel against the original EGA
      engine. I’m making sure the tracker reflects that this piece is no longer
      merely “broader parity pending.”"

      Action/result: Updated `PROGRESS.md` to move full-corpus SQ2 picture
      parity from remaining work to evidence.

1829. Reported: "I’ve added the full-picture command and the packed-fixture
      note to the reusable instructions. I’m adding the detailed evidence note
      next, including the throughput lesson from this long run and the future
      carousel strategy."

      Action/result: Added `AGENTS.md` commands/notes and the packed
      picture/full-parity clean-room evidence section.

1830. Reported: "The clean-room evidence now records both the full 74-picture
      result and the infrastructure lesson. I’m also going to put the carousel
      recommendation into `AGENTS.md`, because it is exactly the kind of
      future-agent context that should not be buried only in the long notes."

      Action/result: Added the carousel-style high-throughput recommendation to
      `AGENTS.md`.

1831. Reported: "`AGENTS.md` now flags carousel-style fixtures as the preferred
      future direction for high-throughput sweeps. I’m updating the progress log
      with this longer run and the two throughput discussions, then I’ll verify
      everything."

      Action/result: Updated the progress log through the full-picture parity
      run and infrastructure discussion.

1832. Reported: "The log is current through the full parity run and the
      infrastructure notes. Before starting a new harness feature, I’m running
      the verification suite once, so any later carousel work starts from a
      clean baseline."

      Action/result: Ran all 146 tests, opcode evidence check, mdBook build,
      and whitespace checks successfully.

1833. Reported: "Full verification is clean: all 146 tests, opcode evidence
      check, mdBook, and diff whitespace. I’m going to prototype the carousel
      mode now, starting from existing bytecode helpers rather than inventing a
      separate control path."

      Action/result: Began implementing a picture carousel harness.

1834. Reported: "I’m going to implement the carousel as a separate batch tool
      rather than modifying the existing picture-batch semantics. That gives us
      a fast path for sweeps while keeping the one-case-per-engine-run harness
      intact as the simple reference oracle."

      Action/result: Added carousel bytecode helpers and packed carousel
      fixture generation to `tools/qemu_fixture.py`.

1835. Reported: "The bytecode side of the carousel is now in
      `qemu_fixture.py`: it shows the first picture once, advances on raw key
      events, and discards the previous picture after showing the next one so
      cache growth doesn’t become the new bottleneck. I’m adding structural
      tests for that generated fixture now."

      Action/result: Started adding carousel fixture tests.

1836. Reported: "The test file has shifted a little from my expected context,
      so I’m reopening the import block and helper-test section and applying
      the carousel tests in smaller patches."

      Action/result: Reopened `tests/test_qemu_fixture.py` and split the test
      patch into smaller edits.

1837. Reported: "The smaller patches are straightforward: imports first, then
      the condition helper assertions, then the packed carousel fixture tests
      near the existing packed-picture test."

      Action/result: Added carousel-related imports, helper assertions, and
      fixture layout tests.

1838. Reported: "Imports are updated. I’m adding the assertions for the
      raw-key condition bytes and the carousel fixture layout next."

      Action/result: Added raw-key and carousel fixture assertions.

1839. Reported: "The fixture tests are in. I’m adding the runner tool now:
      build one packed carousel fixture, start the engine once, capture picture
      0, send a key to advance, capture picture 1, and so on."

      Action/result: Added `tools/picture_carousel.py`.

1840. Reported: "The carousel runner tool is in place. I’m adding lightweight
      unit tests around its report and orchestration path with mocks, then I’ll
      do a short QEMU smoke run to validate the raw-key advance behavior in the
      actual engine."

      Action/result: Added `tests/test_picture_carousel.py`.

1841. Reported: "The unit tests cover the carousel’s naming/reporting and that
      it builds one fixture while comparing each capture separately. I’m running
      these plus the qemu-fixture tests now."

      Action/result: Ran carousel/qemu-fixture tests successfully and confirmed
      a two-picture carousel fixture is about 77 KB.

1842. Reported: "The carousel unit tests pass and the two-picture carousel
      fixture is tiny, about 77 KB. I’m running the two-picture carousel against
      QEMU now; this is the important proof that raw-key advancement works in
      the original engine."

      Action/result: First unprivileged QEMU carousel attempt failed at VNC
      bind before the engine ran.

1843. Reported: "As expected, the first carousel QEMU run failed at the sandbox
      VNC bind, before the engine ran. I’m rerunning the exact command with the
      same escalation pattern we’ve used for the other QEMU harnesses."

      Action/result: Reran with approved `tools/picture_carousel.py` prefix; the
      first picture matched but the second mismatched.

1844. Reported: "The carousel ran under QEMU, but only the first picture
      matched; the second capture mismatched. That means the packed carousel
      fixture boots and captures correctly, but the raw-key advance either
      didn’t fire or didn’t settle before capture. I’m inspecting the report and
      capture rather than treating this as a renderer problem."

      Action/result: Compared the second capture and found it was closest to
      picture 1 with a visible UI/text damage rectangle.

1845. Reported: "The failed carousel smoke is behaving like the key is being
      handled by the normal input path, not by our advance condition. There’s
      already a validated key-mapping/status-byte path for logic probes, so I’m
      switching the carousel advance trigger from raw key condition to
      `map_key_event` plus status byte condition. That should consume `x` as a
      mapped event instead of typed parser input."

      Action/result: Investigated status-byte mapping as a possible carousel
      trigger.

1846. Reported: "That search command had a quoting mistake. I’m rerunning a
      simpler search for the status-byte table and then I’ll patch the carousel
      trigger."

      Action/result: Re-ran the status-byte search successfully.

1847. Reported: "The status-byte path would need either explicit status
      clearing or many one-shot mapped statuses, so I’m trying the lighter
      source-backed fix first: disable the normal input line in the carousel
      setup. The failed capture looked like the typed key was affecting normal
      input UI, so keeping input-line processing out of the sweep may let the
      raw-key predicate own the advance event cleanly."

      Action/result: Added input-line disable action to carousel setup.

1848. Reported: "The carousel setup now disables the normal input line before
      drawing the first picture. I’m rerunning the structural tests and then the
      QEMU two-picture carousel smoke."

      Action/result: Tests passed; QEMU base carousel still mismatched the
      second picture.

1849. Reported: "Disabling the input line did not fix the carousel advance:
      first picture still matches, second still mismatches. I’m checking whether
      the second capture is still basically picture 1 with UI damage, or
      whether the advance happened but the display state carried over."

      Action/result: Confirmed the second capture remained closest to picture 1
      with the same UI/text mismatch area.

1850. Reported: "The second capture is still closest to picture 1, with a
      mismatch rectangle that looks like UI/text damage. So the raw-key advance
      is not the right trigger as currently wired. I’m trying a non-printing key
      next; if it fires the raw-key predicate without typing into the parser UI,
      it may be enough for carousel advancement."

      Action/result: Tried `f1` as the raw-key advance key; it still mismatched.

1851. Reported: "`f1` also failed to advance. I’m going to stop treating this
      as a quick harness tweak and inspect the generated bytecode plus the known
      event/update ordering; the carousel tool can stay, but it needs a better
      advance mechanism before we mark it validated."

      Action/result: Re-read the earlier validated raw-key logic probe.

1852. Reported: "The first two attempts prove something useful but not
      complete: “press a key and check raw-key condition” is not enough in this
      carousel setting, because the normal command/input path is still producing
      visible UI changes while the picture index stays put. I’m reading the
      earlier validated raw-key probe to see what setup difference made that one
      work."

      Action/result: Compared carousel logic against the existing raw-key probe
      setup.

1853. Reported: "Aha, found the likely bug in my carousel bytecode: raw-key
      caches at absolute byte `[0x001c]`, while AGI variable actions are offset
      from `[0x0009]`. I used variable index `0x1c`, which clears `[0x0025]`;
      the correct variable slot for absolute `[0x001c]` is `0x13`. That would
      let one key event advance twice in the same logic pass and wrap back to
      picture 1. I’m patching that now."

      Action/result: Corrected the raw-key cache clear to script variable
      `v19`.

1854. Reported: "The raw-key cache clear is corrected to variable slot `0x13`.
      I’m tightening the test so this exact off-by-base mistake is pinned."

      Action/result: Added a regression assertion for `assignn(v19, 0)`.

1855. Reported: "The regression check now looks for `assignn(v19, 0)`, which is
      the bytecode way to clear absolute `[0x001c]`. I’m rerunning tests and
      then the QEMU carousel smoke."

      Action/result: Tests passed; QEMU base carousel `picture_carousel_base_003`
      matched both pictures.

1856. Reported: "The carousel tests pass with the corrected raw-key slot. I’m
      rerunning the QEMU base carousel; this should tell us whether the fast
      path is genuinely usable."

      Action/result: Confirmed the corrected two-picture raw-key carousel
      passed with 2 matches.

1857. Reported: "The corrected carousel smoke passed: one engine process, two
      pictures, two matches, zero mismatches. I’m going to try the eight-picture
      broad preset next, which is the real speed comparison against the
      snapshot-per-case approach."

      Action/result: Started broad raw-key carousel run.

1858. Reported: "The broad carousel run is active. It should complete much
      faster than the old eight-process-style snapshot batch if the per-key
      advance remains stable."

      Action/result: Broad raw-key carousel matched first three pictures, then
      mismatched five later captures.

1859. Reported: "The broad carousel advanced correctly through the first three
      pictures, then mismatched on the larger resources. That smells like
      capture timing, not bytecode: the larger pictures need more time to
      decode/draw after the key. I’m rerunning broad with a longer per-advance
      wait."

      Action/result: Reran broad raw-key carousel with `--advance-wait 8`.

1860. Reported: "The longer-wait broad carousel run is in progress. If this
      passes, we’ll have a usable fast mode with an explicit wait-time knob for
      heavier resources."

      Action/result: Waited on the longer broad carousel run.

1861. Reported: "The longer broad carousel run is still active. It captures and
      compares after the run finishes, so silence here just means it is stepping
      through the eight resources."

      Action/result: Longer broad raw-key carousel failed at the same boundary.

1862. Reported: "The longer wait did not change the failure boundary: pictures
      1, 6, and 17 match, then the larger packed resources fail. I’m checking
      whether capture 4 is the wrong picture, a partially rendered picture, or
      a bad resource-load effect."

      Action/result: Found captures 4 onward were exactly picture 17.

1863. Reported: "The broad failure is now clearer: after picture 17, every
      later capture is still exactly picture 17. So the carousel is not
      misrendering big pictures; it stops advancing after the third displayed
      picture. I’m going to probe whether that is tied to picture 17, the third
      index, or repeated key delivery."

      Action/result: Created and ran a manual four-picture carousel probe.

1864. Reported: "That combined command included a small inline Python
      file-write before the carousel run, so the approved prefix didn’t cover
      the QEMU segment cleanly. The case file is written now; I’m rerunning just
      the carousel command."

      Action/result: Reran the manual four-picture carousel command.

1865. Reported: "The four-picture manual carousel is running now. This should
      tell us whether the stall is “third advance” generally or something about
      picture 17/broad ordering."

      Action/result: Manual raw-key carousel also stalled after the third
      displayed picture.

1866. Reported: "The manual four-picture run also stalls after the third
      displayed picture, so it’s not picture 17 or large-resource decode. The
      next likely culprit is my persistent index variable: I used a high
      scratch-style variable (`v249`), which may be fine for immediate operands
      but not safe as per-cycle state. I’m moving the carousel index to a lower
      dedicated variable and retesting."

      Action/result: Changed the carousel index variable from `v249` to `v32`.

1867. Reported: "The carousel index now uses `v32` instead of `v249`. I’m
      updating the tests to assert the new state variable, then I’ll rerun the
      manual four-picture carousel."

      Action/result: Updated tests for `v32`.

1868. Reported: "The test now pins the lower carousel index variable. I’m
      running the structural tests and the same four-picture QEMU probe again."

      Action/result: Tests passed; the four-picture raw-key carousel still
      stalled after the third displayed picture.

1869. Reported: "The structural tests pass with `v32`. I’m rerunning the
      four-picture carousel to see whether the third-advance stall disappears."

      Action/result: Confirmed the lower index variable did not fix the stall.

1870. Reported: "The lower index variable didn’t change the stall, so the
      script state is probably fine. The remaining suspect is QEMU/DOS key
      delivery for repeated identical monitor keys. I’m teaching the runner to
      accept a comma-separated key cycle, then I’ll try `x,y,z` so each advance
      is a distinct key event."

      Action/result: Added comma-separated key cycling to the carousel runner.

1871. Reported: "The runner can now cycle through a comma-separated key list.
      I’m adding a tiny test for rejecting an empty key list, then I’ll rerun
      the four-picture QEMU probe with `x,y,z`."

      Action/result: Added empty advance-key validation test.

1872. Reported: "The empty-key guard test is in. I’m running the carousel tests
      and then the distinct-key four-picture QEMU probe."

      Action/result: Tests passed; distinct printable keys still stalled after
      the third displayed picture.

1873. Reported: "The distinct-key carousel run is active. If this still stalls
      after the third capture, the key-repeat theory is out and we’ll need a
      different advance event source."

      Action/result: Confirmed the key-repeat theory did not explain the stall.

1874. Reported: "The raw-key route is too flaky for long carousels. I’m
      switching the carousel to the interpreter’s already QEMU-validated
      mapped-key/status-byte mechanism: setup maps each advance key to a unique
      status byte, each transition tests “current index and that status,” and
      the carousel does not wrap. That avoids needing to clear status bytes and
      fits representative sweeps well."

      Action/result: Reworked carousel bytecode to use mapped keys and status
      byte conditions.

1875. Reported: "The carousel logic now uses mapped status events and has one
      transition per key, no wrap. I need to update the tests from “raw key
      advance” to “mapped key/status advance.”"

      Action/result: Updated qemu-fixture tests for mapped-key carousel logic.

1876. Reported: "The tests now expect mapped-key bytecode. I’m wiring the key
      list through the runner so the fixture maps the same keys that QEMU
      sends."

      Action/result: Passed advance key words through `tools/picture_carousel.py`
      into the generated carousel fixture.

1877. Reported: "The runner now defaults to a long mapped-key list and errors
      if there are not enough keys for the selected carousel. I’m running the
      tests, then the four-picture and broad QEMU probes again."

      Action/result: Mapped-key tests passed.

1878. Reported: "Tests pass with mapped-key carousel bytecode. I’m rerunning
      the four-picture QEMU probe using the default key list."

      Action/result: Four-picture printable-key carousel matched two pictures,
      then showed picture 20 with UI/text artifact and stalled.

1879. Reported: "The mapped-key four-picture carousel is running. If this
      passes, I’ll move straight to the broad mapped-key run."

      Action/result: The mapped-key four-picture carousel did not pass.

1880. Reported: "Mapped keys improved the repeated-key issue differently but
      still stalls, now after the second displayed picture. I’m checking the
      captured image identity again; this will tell us whether status-byte
      triggering is only firing once."

      Action/result: Found the third capture was mostly picture 20 with a
      visible UI/text mismatch, and the fourth capture remained the same.

1881. Reported: "The second transition did draw picture 20, but with a small
      UI/text mismatch, and then subsequent captures stayed there. So mapped
      status events are advancing, but the normal input UI still leaves visible
      damage after the transition. For a fast oracle, we either need to
      suppress/repair that UI or compare only after a clean picture refresh."

      Action/result: Localized the mismatch rectangle to the same visible
      text/window area.

1882. Reported: "The mismatch rectangle is the same visible text/window area,
      so printable mapped keys are still being interpreted by the command
      parser. I’m adding support for non-printing function keys (`f1`, `f2`,
      …) as mapped advance keys; those should produce key events without putting
      text into the input/parser path."

      Action/result: Added function-key BIOS word mapping to
      `tools/picture_carousel.py`.

1883. Reported: "Function-key names now map to BIOS key words for the fixture
      and are sent to QEMU as the same key names. I’m fixing the carousel
      bytecode validation to allow those 16-bit key words."

      Action/result: Updated carousel bytecode validation for 16-bit mapped
      keys.

1884. Reported: "The fixture generator now accepts 16-bit mapped key words. I’m
      running the carousel tests, then the four-picture QEMU run with the
      function-key defaults."

      Action/result: Tests passed; function-key four-picture carousel still
      stalled after the second displayed picture.

1885. Reported: "Tests pass with function-key support. I’m running the
      four-picture QEMU carousel with the default `f1,f2,f3,...` advance keys
      now."

      Action/result: Ran the function-key four-picture carousel.

1886. Reported: "The function-key carousel run is active. This is the cleanest
      version of the idea so far: mapped non-printing keys, one engine process,
      no raw-key cache juggling."

      Action/result: The function-key four-picture run still failed after two
      displayed pictures.

1887. Reported: "Function keys still stall after the second displayed picture,
      so the problem is not only printable input. I’m going to stop short of
      marking carousel validated beyond the two-picture smoke and document this
      as a partially working prototype: useful direction, but it needs a better
      event/ack strategy before replacing snapshot batches."

      Action/result: Decided to document carousel as prototype infrastructure
      rather than broad compatibility evidence.

1888. Reported: "Before documenting the limitation, I’m running the two-picture
      base carousel once more with the current mapped function-key
      implementation. That gives us a clean “validated for two-step smoke, not
      yet broad sweep” boundary."

      Action/result: Ran `picture_carousel_base_mapped_fkey_001`; it matched
      both base pictures with 0 mismatches.

1889. Reported: "The current carousel implementation is validated for the
      two-picture base smoke: 2 matches, 0 mismatches. The four/broad sweeps
      still stall after two displayed pictures, so I’m recording it as a
      prototype with a clear limitation rather than overclaiming it."

      Action/result: Updated compatibility docs, `PROGRESS.md`, and `AGENTS.md`
      with the carousel smoke status and limitation.

1890. Reported: "I’m updating the docs with the precise carousel status: why it
      exists, what passed, what failed, and what a future fix needs to solve."

      Action/result: Added carousel status to `docs/src/compatibility_testing.md`.

1891. Reported: "The compatibility chapter and progress tracker now mark
      carousel as a two-picture smoke prototype, not a broad oracle. I’m
      updating `AGENTS.md` with the same caveat so future runs don’t
      accidentally treat it as production-grade."

      Action/result: Added carousel caveat to `AGENTS.md`.

1892. Reported: "`AGENTS.md` now carries the caveat. I’m adding the detailed
      carousel evidence trail to the clean-room notes, including the raw-key
      cache bug and the failed broader runs."

      Action/result: Added the picture carousel prototype section to
      `docs/src/clean_room_executable_notes.md`.

1893. Reported: "Absolutely. I’m going to treat the current carousel work as a
      throughput prototype rather than a side experiment: first I’ll make sure
      the docs/log reflect what we learned, then I’ll verify the repo, and if
      there’s a clean next improvement for resource iteration I’ll make it
      rather than leaving it as a vague note."

      Action/result: Confirmed the progress log contains the carousel evidence
      trail through entry 1892 and began promoting cross-game resource
      iteration throughput into the tracker.

1894. Reported: "Good catch. I’m not currently using the interpreter’s speed
      setting in the harness; the QEMU waits so far are conservative wall-clock
      sleeps, and the new timed carousel I’m wiring up uses interpreter cycles
      but has not yet set the engine speed."

      Action/result: Searched local docs, SQ2 logic messages, and disassembly
      for speed/cycle handling.

1895. Reported: "Answer to the direct question: no, not yet. I’ve been using
      conservative `--draw-wait`/`--advance-wait` sleeps and QEMU snapshotting,
      not an explicit “fastest” interpreter speed setting."

      Action/result: Confirmed no obvious SQ2 script message for speed and
      moved the investigation to the executable.

1896. Reported: "Found it. The cycle throttle is right at `0x7f78`: it reads
      byte `[0x0013]`, which is script variable `v10` if variables start at
      `[0x0009]`, then spins until timer/counter word `[0x1784]` reaches that
      value and clears `[0x1784]`."

      Action/result: Added a symbolic label and fixture support for setting
      the speed variable in timed carousel scripts.

1897. Reported: "For the actual timed QEMU run, I’m not going to use speed `0`
      for the first probe because it can advance all pictures before the first
      `screendump`; I’ll use `v10 = 1` with a larger cycle hold so each picture
      remains visible long enough to capture."

      Action/result: Timed two-picture carousel
      `picture_carousel_base_timed_001` matched 2/2.

1898. Reported: "Nice, the timed two-picture carousel matched 2/2 with one
      engine process. I’m trying the broad eight-picture version with the same
      speed/hold settings; this is the real test of whether the timed approach
      avoids the key-event stall."

      Action/result: The first fixed-sleep broad timed run matched 2/8; identity
      checks showed wrong-picture cadence misses.

1899. Reported: "The identity check is revealing: after picture 1, the carousel
      jumped to picture 17 and then stayed there. That means timing alone is
      not the whole story; the timed script is losing or corrupting its
      carousel state after the second transition."

      Action/result: Moved carousel state back to high scratch variables and
      confirmed that did not fix the fixed-sleep broad cadence.

1900. Reported: "The two-picture `17 -> 43` case passes, so picture 43 is fine.
      The broad stall is likely inside the transition bookkeeping."

      Action/result: Reordered timed/key carousel transition bytecode to update
      carousel state before discarding the old picture.

1901. Reported: "The reorder changed the failure shape: picture 76 now matches,
      so state is advancing through the sequence. The remaining broad
      mismatches are cadence alignment, not a hard stall."

      Action/result: Cached identity check showed captures landing on exact
      renders for other broad-preset pictures.

1902. Reported: "The identity pass shows clean cadence drift: captures saw
      `1,17,43,44,46,76,76,76`, so the carousel is advancing roughly twice as
      fast as the capture interval."

      Action/result: Tried `delay-cycles 240`; this aligned picture 6 but still
      drifted later.

1903. Reported: "The calibrated run shows why fixed sleeps will be brittle
      across games: picture load/draw time changes the cadence. I’m going to
      add a polling mode for timed carousels instead."

      Action/result: Added `--poll`, `--poll-interval`, and `--poll-timeout` to
      `tools/picture_carousel.py`.

1904. Reported: "Good news: the polling timed carousel has matched the first
      six broad pictures in sequence. It’s still waiting/capturing the last two,
      so I’m letting that finish."

      Action/result: `picture_carousel_broad_timed_poll_001` matched all 8
      broad pictures with `delay-cycles 240`.

1905. Reported: "The faster polling run passed 8/8 in one engine process. I’m
      trying one more shorter hold (`delay_cycles=60`) to find a practical
      lower bound; if it passes, that becomes the better recommendation."

      Action/result: `picture_carousel_broad_timed_poll_fast_001` matched all
      8 broad pictures with `delay-cycles 120`; `delay-cycles 60` missed
      intermediate pictures and is not recommended.

1906. Reported: "The `60` hold was too short and missed almost everything, so
      the practical default is `delay_cycles=120`, `speed_value=1`, polling
      every half-second. I’m making the CLI defaults reflect that stable
      setting and documenting the faster carousel path now."

      Action/result: Updated CLI defaults, `AGENTS.md`, compatibility docs,
      `PROGRESS.md`, symbolic labels, logic bytecode notes, and clean-room
      notes with the timed polling carousel evidence.
