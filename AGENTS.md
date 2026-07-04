# AGENTS.md

## Summary

This is a project to perform a clean room reverse engineering of AGI (Adventure Game Interpreter), a game engine created by Sierra on-line in the 1980s.

This effort uses the game Space Quest 2 (located in the SQ2 directory).

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
- Run the local compatibility suite with `python3 -B -m unittest discover -s tests` when changing decoders, renderers, or resource parsers.

## Clean-room workflow

- Use only local project files, locally installed tools, and observations produced during this project.
- Do not consult external AGI documentation, AGI source code, online walkthroughs, or prior AGI reverse-engineering material.
- When using general-purpose tool documentation or emulator help, avoid AGI-specific resources.
- Prefer evidence from the SQ2 files, disassembly, debugger/emulator traces, generated screenshots, and locally written analysis tools.
- Mark uncertain interpretations as hypotheses until verified by another observation.

## Local inputs and generated artifacts

- The game files are in `SQ2/`.
- MS-DOS 6.22 installer floppy images are in `002962_ms_dos_622/`.
- Generated artifacts belong under `build/`.
- Generated render/test fixtures belong under `build/rendered/` unless the user explicitly asks to preserve them elsewhere.
- The installed DOS hard disk image is `build/dos622/dos622.img`.
- Treat `build/` as disposable/generated unless the user explicitly asks to preserve or commit artifacts from it.

## Static analysis tools

- Available DOS/reverse-engineering tools include `nasm`, `ndisasm`, `rizin`, and `radare2`.
- Use `ndisasm`, `rizin`, `radare2`, `xxd`, `hexdump`, and local scripts for executable/resource inspection.
- Existing local scripts in `tools/` are part of the clean-room evidence trail. Reuse and extend them when appropriate.
- When adding analysis scripts, make them deterministic and document what local files and offsets they use.

## Dynamic analysis with QEMU

- QEMU may be used for dynamic checks of the DOS executable and interpreter behavior.
- The DOS image at `build/dos622/dos622.img` is bootable and has SQ2 copied to `C:\SQ2`.
- Use this command for monitor-driven runs and screenshots:

```bash
qemu-system-i386 -m 16 -boot c \
  -drive file=build/dos622/dos622.img,format=raw,if=ide,index=0,media=disk \
  -display vnc=127.0.0.1:5 -monitor stdio
```

- In the QEMU monitor, use `sendkey` to type DOS commands and `screendump path.ppm` to capture VGA output.
- Convert screenshots with ImageMagick, for example `magick build/dos622/screen.ppm build/dos622/screen.png`.
- Inspect PPM screenshots and generated renders with `python3 -B tools/inspect_ppm.py path.ppm`.
- QEMU can expose a host directory to DOS as a secondary writable FAT hard disk:

```bash
qemu-system-i386 -m 16 -boot c \
  -drive file=build/dos622/dos622.img,format=raw,if=ide,index=0,media=disk \
  -drive file=fat:rw:build/qemu-share,format=raw,if=ide,index=1,media=disk \
  -display vnc=127.0.0.1:5 -monitor stdio
```

- With that command DOS sees the host directory as `D:`. A fixture under `build/qemu-share/PIC001` can be run with `D:`, `cd \PIC001`, `SIERRA`.
- Caveat: QEMU `savevm` does not work with writable vvfat (`fat:rw:`), and the generated AGI fixtures do not return to DOS after drawing. For true no-reboot batches, use a QEMU snapshot at the DOS prompt and a disposable qcow2 clone of `build/dos622/dos622.img` with prebuilt fixtures copied into the boot partition. The secondary `D:` qcow2/FAT-disk probe was not usable from DOS; preloading fixtures onto disposable `C:` qcow2 did work.
- Build and run a one-boot view/object snapshot batch with `python3 -B tools/view_batch.py --snapshot --dos-prefix VS --output build/view-batch/batches/view_snapshot.json --boot-wait 5 --draw-wait 8`.
- Run targeted object overlay priority/clipping/persistent-object probes with `python3 -B tools/object_overlay_probe.py --dos-prefix OP --output build/object-overlay-probes/batches/name.json --boot-wait 5 --draw-wait 8`.
- Generate original-engine fixture game directories with `python3 -B tools/qemu_fixture.py picture N --output build/qemu-fixtures/picture_NNN`.
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

- The DOS partition starts at sector 63, so the mtools byte offset is `32256`.
- List the DOS root with:

```bash
mdir -i build/dos622/dos622.img@@32256 ::
```

- Copy files into the image with `mcopy -i build/dos622/dos622.img@@32256 ...`.
- Create directories with `mmd -i build/dos622/dos622.img@@32256 ::/NAME`.
- SQ2 can be launched inside DOS with:

```bat
cd \SQ2
SIERRA
```
