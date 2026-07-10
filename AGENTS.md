# AGENTS.md

## Commit Message Style

We follow the guidelines from:

[https://cbea.ms/git-commit/](https://cbea.ms/git-commit/)

The seven rules:

1. Separate subject from body with a blank line.
2. Limit the subject line to ~50 characters.
3. When using a `<keyword>: <subject>` format, capitalize the first
   word after the colon rather than the keyword itself (for example
   `chore: Make change`).
4. Do not end the subject line with a period.
5. Use the imperative mood (“Add feature”, not “Added feature”).
6. Wrap the body at ~72 characters.
7. Explain what and why, not how.

Each time you make a commit, include a detailed explanation. Include rationale
and be verbose.

## Summary

This is a project to perform a clean room reverse engineering of AGI (Adventure Game Interpreter), a game engine created by Sierra on-line in the 1980s.

The current evidence set was built primarily from Space Quest 2, but game files
are private local inputs under `games/` or another path supplied explicitly to
the tools. Do not assume SQ2 as a default; AGI games and interpreter versions
will be compared across separate directories such as `games/SQ2`, `games/LSL1`,
or `games/KQ4`.

While others have reverse engineered AGI before and there is plenty of documentation and source code available online, in this project we are explicitly not consulting any existing materials. This is an experiment to explore the reverse engineering capabilities of Codex, and using existing documentation or source code would work against that goal.

The output of this project is a human-readable spec that contains sufficient information to use another AI agent to do a clean-room implementation of AGI.

## Rules

- Do not make use of external documentation, source code, or your own training data about AGI
- Every step in the reverse engineering process must be documented, as proof that this is clean-room

## Documentation

- Use mdBook for project documentation.
- The mdBook project lives in `docs/`.
- Source markdown belongs under `docs/src/`.
- Keep `docs/src/SUMMARY.md` updated when adding, moving, or removing chapters.
- Build/check the book with `mdbook build docs`.
- Record reverse-engineering actions, observations, commands, offsets, hypotheses, and corrections in the documentation, especially `docs/src/clean_room_executable_notes.md`.
- Preserve user-facing progress updates in `docs/src/progress_log.md` with a brief concrete action/result note for each update. If a user asks for historical tracking, update this log before continuing substantial new work.
- Maintain `PROGRESS.md` as the high-level completion tracker. Update it whenever an opcode changes evidence/status, a subsystem moves forward, or new remaining work is identified. Keep opcode names aligned with `tools/disassemble_logic.py` and `docs/src/logic_opcode_evidence.md`; use it as a dashboard, not as a replacement for detailed evidence notes.
- Maintain `docs/src/symbolic_labels.md` as the stable cross-version map for interpreter routines, tables, overlay entry points, and globals. Treat addresses as build-specific observations and prefer symbolic labels in prose once a label exists.
- When assigning or revising a symbolic label, update `docs/src/symbolic_labels.md` with the observed SQ2 address association and record the supporting evidence or uncertainty in the notes.
- Grow the compatibility test suite alongside the written spec. Prefer deterministic local tests under `tests/` and reusable tools under `tools/`; record what each test proves and what remains provisional in `docs/src/compatibility_testing.md`.
- Run the local compatibility suite with `python3 -B -m unittest discover -s tests` when changing decoders, renderers, or resource parsers. The higher-level suite manifest/runner is `python3 -B tools/compatibility_suite.py`; it runs local tests, mdBook, and opcode-evidence checks by default, with QEMU smoke/broad sweeps available through explicit flags.

## Clean-room workflow

- Use only local project files, locally installed tools, and observations produced during this project.
- Do not consult external AGI documentation, AGI source code, online walkthroughs, or prior AGI reverse-engineering material.
- When using general-purpose tool documentation or emulator help, avoid AGI-specific resources.
- Prefer evidence from explicitly selected local game files, disassembly,
  debugger/emulator traces, generated screenshots, and locally written analysis
  tools.
- Mark uncertain interpretations as hypotheses until verified by another observation.

## Local inputs and generated artifacts

- Game files are not committed. Keep private local copies under `games/` or
  another ignored path and pass the selected copy with `--game-dir PATH` or
  `AGI_GAME_DIR=PATH`.
- Treat `games/` as immutable evidence input. Generated fixtures must copy the
  selected game into `build/` and patch that writable copy; never point a
  fixture builder at a directory under `games/`.
- Do not use a default game directory in scripts. SQ2 is one local evidence
  input, not the project default.
- Generated artifacts belong under `build/`.
- Generated render/test fixtures belong under `build/rendered/` unless the user explicitly asks to preserve them elsewhere.
- The reproducible FreeDOS hard disk image is generated at
  `build/freedos/freedos.img` by `python3 -B tools/setup_freedos_image.py`.
- Treat `build/` as disposable/generated unless the user explicitly asks to preserve or commit artifacts from it.

## Static analysis tools

- Available DOS/reverse-engineering tools include `nasm`, `ndisasm`, `rizin`, and `radare2`.
- Use `ndisasm`, `rizin`, `radare2`, `xxd`, `hexdump`, and local scripts for executable/resource inspection.
- Existing local scripts in `tools/` are part of the clean-room evidence trail. Reuse and extend them when appropriate.
- When adding analysis scripts, make them deterministic and document what local files and offsets they use.
- Scripts that inspect game resources must require `--game-dir PATH` or
  `AGI_GAME_DIR=PATH`. Do not add implicit `games/SQ2` or `SQ2/` fallbacks.

## Dynamic analysis with QEMU

- QEMU may be used for dynamic checks of the DOS executable and interpreter behavior.
- Build the local FreeDOS image with
  `python3 -B tools/setup_freedos_image.py --force`. To copy a private game
  for manual runs, add `--copy-game --game-dir games/SQ2 --dos-game-dir SQ2`
  or choose another game path/name explicitly.
- The default QEMU image for harnesses is `build/freedos/freedos.img`; override
  it with `AGI_DOS_IMAGE=/path/to/image.img` when needed.
- Use this command for monitor-driven runs and screenshots:

```bash
qemu-system-i386 -m 16 -boot c \
  -drive file=build/freedos/freedos.img,format=raw,if=ide,index=0,media=disk \
  -display vnc=127.0.0.1:5 -monitor stdio
```

- In the QEMU monitor, use `sendkey` to type DOS commands and `screendump path.ppm` to capture VGA output.
- Convert screenshots with ImageMagick, for example `magick build/qemu/screen.ppm build/qemu/screen.png`.
- Inspect PPM screenshots and generated renders with `python3 -B tools/inspect_ppm.py path.ppm`.
- QEMU can expose a host directory to DOS as a secondary writable FAT hard disk:

```bash
qemu-system-i386 -m 16 -boot c \
  -drive file=build/freedos/freedos.img,format=raw,if=ide,index=0,media=disk \
  -drive file=fat:rw:build/qemu-share,format=raw,if=ide,index=1,media=disk \
  -display vnc=127.0.0.1:5 -monitor stdio
```

- With that command DOS sees the host directory as `D:`. A fixture under `build/qemu-share/PIC001` can be run with `D:`, `cd \PIC001`, `SIERRA`.
- Caveat: QEMU `savevm` does not work with writable vvfat (`fat:rw:`), and the generated AGI fixtures do not return to DOS after drawing. For true no-reboot batches, use a QEMU snapshot at the DOS prompt and a disposable qcow2 clone of `build/freedos/freedos.img` with prebuilt fixtures copied into the boot partition. The secondary `D:` qcow2/FAT-disk probe was not usable from DOS; preloading fixtures onto disposable `C:` qcow2 did work.
- Build and run a one-boot view/object snapshot batch with `python3 -B tools/view_batch.py --snapshot --dos-prefix VS --output build/view-batch/batches/view_snapshot.json --boot-wait 5 --draw-wait 8`.
- Build and run a one-boot real-picture snapshot batch with `python3 -B tools/picture_batch.py --snapshot --dos-prefix PB --output build/picture-batch/batches/picture_base_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`.
- Run the broader representative real-picture snapshot preset with `python3 -B tools/picture_batch.py --preset broad --snapshot --dos-prefix PB --output build/picture-batch/batches/picture_broad_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`.
- Run the full present-picture snapshot preset with `python3 -B tools/picture_batch.py --preset all --snapshot --fixture-root build/picture-batch/all-fixtures --dos-prefix PA --output build/picture-batch/batches/picture_all_001.json --boot-wait 5 --draw-wait 8 --stop-on-failure`.
- `tools/picture_batch.py` uses packed picture fixtures: each fixture copies only the minimal engine/support files and places generated `LOGIC.0` plus the tested picture payload in that fixture's `VOL.3`. This keeps all-present SQ2 picture batches within the 64 MB DOS image.
- Run a dynamic original-engine save-write probe with `python3 -B tools/save_roundtrip_probe.py --output build/save-roundtrip/save_roundtrip_010.json --capture build/save-roundtrip/qemu_capture_010.ppm --snapshot-raw build/save-roundtrip/snapshot/save_roundtrip_010.raw --snapshot-qcow build/save-roundtrip/snapshot/save_roundtrip_010.qcow2 --post-run-raw build/save-roundtrip/snapshot/save_roundtrip_after_010.raw --save-output build/save-roundtrip/SQ2SG_010.1 --boot-wait 5 --draw-wait 8 --path-prompt-wait 2 --slot-wait 1 --description-wait 1 --confirmation-wait 1 --key-delay 0.08`. The fixture calls `0x8f verify_game_signature` with message `SQ2`, so the save-name prefix/global signature at `DS:0x0002` is initialized and the original engine writes `SQ2SG.1`.
- Validate restore from that generated save with `python3 -B tools/save_roundtrip_probe.py --mode restore --save-input build/save-roundtrip/SQ2SG_010.1 --output build/save-roundtrip/restore_roundtrip_sq2stem_006.json --fixture build/save-roundtrip/restore-fixture-signed --dos-dir RST6 --capture build/save-roundtrip/restore_capture_sq2stem_006.ppm --snapshot-raw build/save-roundtrip/snapshot/restore_roundtrip_sq2stem_006.raw --snapshot-qcow build/save-roundtrip/snapshot/restore_roundtrip_sq2stem_006.qcow2 --boot-wait 5 --draw-wait 8 --path-prompt-wait 8 --path-keys $'\n\n' --slot-wait 2 --slot-keys $'\n\n' --confirmation-wait 1 --confirmation-keys $'\n\n' --key-delay 0.12`. The restore fixture starts with an unrestored X=90 marker but branches to an X=50 draw only after the saved flag and variables are restored, so a visual match proves restored state rather than mere continuation after `0x7e`.
- Capture the representative restore-read failure UI with `python3 -B tools/save_roundtrip_probe.py --mode restore-read-error --output build/save-roundtrip/restore_read_error_002.json --fixture build/save-roundtrip/restore-read-error-fixture --dos-dir RERR --capture build/save-roundtrip/restore_read_error_002.ppm --snapshot-raw build/save-roundtrip/snapshot/restore_read_error_002.raw --snapshot-qcow build/save-roundtrip/snapshot/restore_read_error_002.qcow2 --boot-wait 5 --draw-wait 8 --path-prompt-wait 8 --path-keys $'\n' --slot-wait 2 --slot-keys $'\n' --confirmation-wait 1 --confirmation-keys $'\n' --key-delay 0.12`. Use exactly one Enter at the directory prompt, one at slot selection, and one at confirmation; redundant Enters advance through the fatal error dialog and leave the final capture at DOS. The synthetic save is 40 bytes: a 31-byte description, declared first-block length `0x05e1`, and the seven-byte `SQ2` signature prefix, so the selector lists it before the actual restore read fails.
- For high-throughput resource sweeps across many games or interpreter versions, prefer timed polling carousel fixtures when the resources can be shown by one generated logic script. The fixture keeps one engine process running, sets byte variable `v10` (`DS:0x0013`) to a fast cycle speed, displays each resource after a timer/cycle delay, and lets the QEMU harness poll `screendump` output until the expected image appears. Keep the isolated one-process-per-case snapshot harness as the simpler reference oracle.
- Current picture carousel command for broad real-picture evidence: `python3 -B tools/picture_carousel.py --preset broad --mode timed --poll --delay-cycles 120 --speed-value 1 --fixture-root build/picture-carousel/timed-broad-poll-fast-fixtures --dos-dir PICPOLL --output build/picture-carousel/batches/picture_carousel_broad_timed_poll_fast_001.json --boot-wait 5 --first-wait 3 --poll-interval 0.5 --poll-timeout 15`. This matched the eight-picture broad preset from one engine process. `delay-cycles 60` was too short and missed intermediate pictures.
- For all-present SQ2 picture carousel evidence, use chunked timed polling: `python3 -B tools/picture_carousel.py --preset all --mode timed --poll --chunk-size 16 --delay-cycles 120 --speed-value 1 --fixture-root build/picture-carousel/timed-all-poll-chunk16-fixtures --dos-dir PICALL --output build/picture-carousel/batches/picture_carousel_all_timed_poll_chunk16_001.json --boot-wait 5 --first-wait 3 --poll-interval 0.5 --poll-timeout 20`. This matched all 74 present pictures. A single 74-picture carousel matched the first 19 pictures, then the original engine showed a disk prompt over picture 19 despite an intact generated `VOL.3`, so use chunks for large sweeps.
- Current timed polling view/object carousel evidence: `python3 -B tools/view_carousel.py --include-stress --fixture-root build/view-carousel/stress-fixtures --dos-dir VCARSTR --output build/view-carousel/batches/view_carousel_stress_001.json --boot-wait 5 --first-wait 3 --delay-cycles 120 --speed-value 1 --poll-interval 0.5 --poll-timeout 20`. This matched all 19 current base-plus-stress view cases from one engine process. The simpler per-case snapshot oracle remains `tools/view_batch.py`.
- The older key/status-byte carousel path remains useful as a prototype but is not broad-suite evidence: mapped function-key base smoke matched two pictures, while broader key-driven sweeps stalled or left input/UI artifacts.
- If future multi-game/interpreter batches need more DOS space, create a
  larger formatted bootable DOS test image or purpose-built large fixture
  image; simply appending bytes to an existing FAT image is not enough because
  the partition/filesystem geometry must also change.
- Run targeted object overlay priority/clipping/persistent-object probes with `python3 -B tools/object_overlay_probe.py --dos-prefix OP --output build/object-overlay-probes/batches/name.json --boot-wait 5 --draw-wait 8`.
- Generate original-engine fixture game directories with `python3 -B tools/qemu_fixture.py picture N --output build/qemu-fixtures/picture_NNN`.
- Generate basic v3 direct-record logic fixtures with
  `python3 -B tools/qemu_fixture.py v3-logic payload.bin --game-dir games/GR --logic 0 --output build/qemu-fixtures/gr_logic_000`.
  This copies the selected v3 game under `build/`, appends an uncompressed
  logic record to the existing prefixed volume, and patches the combined
  directory.
- Generate v3 synthetic picture fixtures with
  `python3 -B tools/qemu_fixture.py v3-synthetic-picture payload.pic --game-dir games/GR --picture 0 --volume 1 --output build/qemu-fixtures/gr_picture_000`.
  The payload is expanded picture bytecode ending in `0xff`; the fixture writer
  stores it with the observed v3 picture-nibble transform.
- Generate v3 synthetic picture/view fixtures with
  `python3 -B tools/qemu_fixture.py v3-synthetic-picture-view payload.pic 0 0 0 0 20 80 15 --view-payload payload.view --game-dir games/GR --volume 1 --output build/qemu-fixtures/gr_picture_view_000`.
  The optional view payload is stored as a direct v3 record. The writer does
  not implement the v3 dictionary compressor; use direct records for controlled
  generated fixtures and the existing resource reader for original compressed
  local game resources.
- Run the current v3 synthetic picture/view fixture compatibility probe with
  `python3 -B tools/gr_v3_behavior_probe.py --probe synthetic-picture-view --game-dir games/GR --fixture-root build/gr-v3-behavior/synthetic-picture-view-suite-fixtures --dos-prefix GSP --run-qemu --output build/gr-v3-behavior/synthetic_picture_view_suite.json --snapshot-raw build/gr-v3-behavior/snapshot/synthetic_picture_view_suite.raw --snapshot-qcow build/gr-v3-behavior/snapshot/synthetic_picture_view_suite.qcow2 --boot-wait 5 --draw-wait 8`.
  It compares a blank control, a generated picture-nibble picture fixture, and
  a generated picture-plus-direct-view fixture. The promoted suite report is
  `build/compatibility-suite/qemu_v3_synthetic_picture_view_001.json`.
- Run the current Gold Rush v3 room-remap behavior probe with
  `python3 -B tools/gr_v3_behavior_probe.py --game-dir games/GR --picture 1 --run-qemu --output build/gr-v3-behavior/room_remap_all_qemu_pic001_001.json`.
  This compares direct room target `0x49` with alias targets `0x7e`, `0x7f`,
  and `0x80` using nonblank original-engine captures. Keep this probe
  source-first: update it from disassembly observations, then use QEMU as
  confirmation.
- Run the current Gold Rush v3 key-map capacity probe with
  `python3 -B tools/gr_v3_behavior_probe.py --probe key-map-capacity --game-dir games/GR --picture 1 --fixture-root build/gr-v3-behavior/key-map-capacity-fixtures --dos-prefix GRK --run-qemu --output build/gr-v3-behavior/key_map_capacity_qemu_pic001_002.json --boot-wait 5 --draw-wait 8`.
  It fills 48 dummy key-map slots, maps `x` in final GR slot 48, compares the
  keyed capture with a direct picture draw, and confirms the no-key control
  remains blank.
- Run the current Gold Rush v3 signed save/restore round-trip probe with
  `python3 -B tools/gr_v3_behavior_probe.py --probe signed-restore-roundtrip --game-dir games/GR --fixture-root build/gr-v3-behavior/signed-restore-suite-fixtures --dos-prefix GRT --run-qemu --output build/gr-v3-behavior/signed_restore_roundtrip_suite.json --snapshot-raw build/gr-v3-behavior/snapshot/signed_restore_roundtrip_suite.raw --snapshot-qcow build/gr-v3-behavior/snapshot/signed_restore_roundtrip_suite.qcow2 --post-run-raw build/gr-v3-behavior/snapshot/signed_restore_roundtrip_suite_after.raw --save-output build/gr-v3-behavior/GRSG_restore_suite.1 --boot-wait 5 --draw-wait 8 --path-prompt-wait 2 --slot-wait 1 --description-wait 1 --confirmation-wait 1 --key-delay 0.08`.
  It uses the original GR interpreter to write `GRSG.1`, restores that save in
  a second generated fixture, and compares the restored capture with direct
  saved/unrestored controls.
- Run the current Gold Rush v3 restart prompt-marker probe with
  `python3 -B tools/gr_v3_behavior_probe.py --probe restart-prompt-marker --game-dir games/GR --fixture-root build/gr-v3-behavior/restart-prompt-suite-fixtures --dos-prefix GRP --run-qemu --output build/gr-v3-behavior/restart_prompt_marker_suite.json --snapshot-raw build/gr-v3-behavior/snapshot/restart_prompt_marker_suite.raw --snapshot-qcow build/gr-v3-behavior/snapshot/restart_prompt_marker_suite.qcow2 --boot-wait 5 --draw-wait 8`.
  It compares hidden/visible prompt-marker controls with Escape-canceled
  restart cases and confirms the canceled branch's redraw condition.
- Run the current Gold Rush v3 menu interaction gate probe with
  `python3 -B tools/gr_v3_behavior_probe.py --probe menu-gate --game-dir games/GR --fixture-root build/gr-v3-behavior/menu-gate-suite-fixtures --dos-prefix GRG --run-qemu --output build/gr-v3-behavior/menu_gate_suite.json --snapshot-raw build/gr-v3-behavior/snapshot/menu_gate_suite.raw --snapshot-qcow build/gr-v3-behavior/snapshot/menu_gate_suite.qcow2 --boot-wait 5 --draw-wait 8`.
  It compares a blocked marker control with `0xb1(0)` and `0xb1(1)` menu
  requests; zero matches the blocked control, while nonzero enters the modal
  menu path and produces a distinct capture.
- Compare original-engine picture captures with the local renderer using `python3 -B tools/compare_picture_capture.py N capture.ppm`.
- Generate synthetic picture fuzz corpora with `python3 -B tools/picture_fuzz.py generate --count 1024 --seed 4097 --output build/picture-fuzz/corpus --clean`.
- Run one synthetic picture fuzz case through the original engine with `python3 -B tools/picture_fuzz.py run-qemu CASE_ID --dos-dir DOSNAME --boot-wait 5 --draw-wait 8`.
- Run a bounded serial QEMU fuzz batch with `python3 -B tools/picture_fuzz.py batch-qemu --case CASE_ID --case OTHER_ID --dos-prefix FZB --output build/picture-fuzz/batches/name.json --boot-wait 5 --draw-wait 8`.
- Prefer snapshot mode for larger known-ahead fuzz batches: `python3 -B tools/picture_fuzz.py batch-qemu --snapshot --case CASE_ID --case OTHER_ID --dos-prefix FS --output build/picture-fuzz/batches/name.json --boot-wait 5 --draw-wait 8`.
- Treat `safe_for_qemu: false` fuzz cases as out of scope for compatibility evidence. They may make the original interpreter read outside the synthetic resource and enter exploit/garbage-memory behavior; do not model that as AGI semantics.
- Run QEMU fuzz cases serially. The harness copies fixtures into the shared DOS image and QEMU binds a single local VNC display socket.
- Keep generated `.ppm` captures out of DOS-image fixture copies; they can fill the small DOS image and are not input to the interpreter.
- Shut QEMU down with the monitor command `quit` when finished.
- For deeper debugging, QEMU's GDB stub may be considered, but document all setup and observations before relying on them.

## Working with the DOS image

- The generated FreeDOS image may use a different partition offset from older
  local images. Use `tools/qemu_snapshot.py` helpers or
  `tools/setup_freedos_image.py --print-mtools-image` to get the correct mtools
  target.
- List the DOS root with:

```bash
mdir -i "$(python3 -B tools/setup_freedos_image.py --print-mtools-image --output build/freedos/freedos.img)" ::
```

- Copy files into the image with `mcopy -i IMAGE_TARGET ...`.
- Create directories with `mmd -i IMAGE_TARGET ::/NAME`.
- If a game was copied to `C:\SQ2`, it can be launched inside DOS with:

```bat
cd \SQ2
SIERRA
```
