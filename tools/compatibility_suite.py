#!/usr/bin/env python3
"""Manifest and runner for the current clean-room compatibility suite."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_REPORT = Path("build/compatibility-suite/report.json")


@dataclass(frozen=True)
class SuiteCommand:
    name: str
    layer: str
    description: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class SuiteResult:
    name: str
    layer: str
    command: tuple[str, ...]
    returncode: int
    elapsed_seconds: float


def suite_commands() -> tuple[SuiteCommand, ...]:
    return (
        SuiteCommand(
            "local_unittest",
            "local",
            "Run all deterministic local parser/renderer/resource tests.",
            ("python3", "-B", "-m", "unittest", "discover", "-s", "tests"),
        ),
        SuiteCommand(
            "mdbook_build",
            "local",
            "Build the reverse-engineering evidence book.",
            ("mdbook", "build", "docs"),
        ),
        SuiteCommand(
            "mdbook_spec_build",
            "local",
            "Build the clean-room behavioral specification.",
            ("mdbook", "build", "spec"),
        ),
        SuiteCommand(
            "logic_opcode_evidence_check",
            "local",
            "Check generated opcode evidence chapter freshness.",
            ("python3", "-B", "tools/logic_opcode_evidence.py", "--check"),
        ),
        SuiteCommand(
            "parser_edges_qemu",
            "qemu-smoke",
            "Validate parsed-word exact, wildcard, and prefix terminator cases.",
            (
                "python3",
                "-B",
                "tools/logic_interpreter_probe.py",
                "--dos-prefix",
                "PW",
                "--output",
                "build/logic-interpreter-probes/batches/parser_edges_suite.json",
                "--boot-wait",
                "5",
                "--draw-wait",
                "8",
                "--stop-on-failure",
                "--case",
                "input_word_sequence_matches_two_words",
                "--case",
                "input_word_sequence_wildcard_matches_word",
                "--case",
                "input_word_sequence_terminator_accepts_prefix",
            ),
        ),
        SuiteCommand(
            "parser_unknown_terminator_qemu",
            "qemu-smoke",
            "Validate terminator-only match after an unknown parsed token.",
            (
                "python3",
                "-B",
                "tools/logic_interpreter_probe.py",
                "--dos-prefix",
                "PU",
                "--output",
                "build/logic-interpreter-probes/batches/parser_unknown_terminator_suite.json",
                "--boot-wait",
                "5",
                "--draw-wait",
                "8",
                "--stop-on-failure",
                "--case",
                "input_word_sequence_terminator_matches_unknown_word",
            ),
        ),
        SuiteCommand(
            "picture_fuzz_command_resume_qemu",
            "qemu-smoke",
            "Validate command-byte scanner resume cases for line, corner, and fill.",
            (
                "python3",
                "-B",
                "tools/picture_fuzz.py",
                "batch-qemu",
                "--snapshot",
                "--case",
                "base_030_line_pair_command_resume",
                "--case",
                "base_031_corner_command_resume",
                "--case",
                "base_032_fill_command_resume",
                "--dos-prefix",
                "FR",
                "--fixture-root",
                "build/picture-fuzz/fixtures",
                "--output",
                "build/picture-fuzz/batches/command_resume_suite.json",
                "--boot-wait",
                "5",
                "--draw-wait",
                "8",
                "--stop-on-failure",
            ),
        ),
        SuiteCommand(
            "picture_fuzz_raw_operand_qemu",
            "qemu-smoke",
            "Validate raw command-like operands for picture opcodes 0xf0, 0xf2, and 0xf9.",
            (
                "python3",
                "-B",
                "tools/picture_fuzz.py",
                "batch-qemu",
                "--snapshot",
                "--case",
                "base_033_raw_visual_operand",
                "--case",
                "base_034_raw_control_operand",
                "--case",
                "base_035_raw_pattern_mode_operand",
                "--dos-prefix",
                "RO",
                "--fixture-root",
                "build/picture-fuzz/fixtures",
                "--output",
                "build/picture-fuzz/batches/raw_operand_suite.json",
                "--boot-wait",
                "5",
                "--draw-wait",
                "8",
                "--stop-on-failure",
            ),
        ),
        SuiteCommand(
            "picture_fuzz_relative_underflow_qemu",
            "qemu-smoke",
            "Validate 8-bit relative-line underflow clamping for X and Y.",
            (
                "python3",
                "-B",
                "tools/picture_fuzz.py",
                "batch-qemu",
                "--snapshot",
                "--case",
                "base_036_relative_x_underflow_wraps",
                "--case",
                "base_037_relative_y_underflow_wraps",
                "--dos-prefix",
                "RU",
                "--fixture-root",
                "build/picture-fuzz/fixtures",
                "--output",
                "build/picture-fuzz/batches/relative_underflow_suite.json",
                "--boot-wait",
                "5",
                "--draw-wait",
                "8",
                "--stop-on-failure",
            ),
        ),
        SuiteCommand(
            "picture_carousel_broad_qemu",
            "qemu-broad",
            "Validate the eight-picture real-resource broad preset from one engine process.",
            (
                "python3",
                "-B",
                "tools/picture_carousel.py",
                "--preset",
                "broad",
                "--mode",
                "timed",
                "--poll",
                "--delay-cycles",
                "120",
                "--speed-value",
                "1",
                "--fixture-root",
                "build/picture-carousel/timed-broad-suite-fixtures",
                "--dos-dir",
                "PICSUITE",
                "--output",
                "build/picture-carousel/batches/picture_carousel_broad_suite.json",
                "--boot-wait",
                "5",
                "--first-wait",
                "3",
                "--poll-interval",
                "0.5",
                "--poll-timeout",
                "15",
            ),
        ),
        SuiteCommand(
            "view_carousel_stress_qemu",
            "qemu-broad",
            "Validate the current base-plus-stress view/object carousel.",
            (
                "python3",
                "-B",
                "tools/view_carousel.py",
                "--include-stress",
                "--fixture-root",
                "build/view-carousel/stress-suite-fixtures",
                "--dos-dir",
                "VCARSUIT",
                "--output",
                "build/view-carousel/batches/view_carousel_stress_suite.json",
                "--boot-wait",
                "5",
                "--first-wait",
                "3",
                "--delay-cycles",
                "120",
                "--speed-value",
                "1",
                "--poll-interval",
                "0.5",
                "--poll-timeout",
                "20",
            ),
        ),
        SuiteCommand(
            "gr_save_xor_extract_qemu",
            "qemu-v3",
            "Validate the Gold Rush v3 blank-prefix save extraction and third-block XOR transform.",
            (
                "python3",
                "-B",
                "tools/gr_v3_behavior_probe.py",
                "--probe",
                "save-xor-extract",
                "--game-dir",
                "games/GR",
                "--fixture-root",
                "build/gr-v3-behavior/save-xor-suite-fixtures",
                "--dos-prefix",
                "GSV",
                "--run-qemu",
                "--output",
                "build/gr-v3-behavior/save_xor_extract_suite.json",
                "--snapshot-raw",
                "build/gr-v3-behavior/snapshot/save_xor_extract_suite.raw",
                "--snapshot-qcow",
                "build/gr-v3-behavior/snapshot/save_xor_extract_suite.qcow2",
                "--post-run-raw",
                "build/gr-v3-behavior/snapshot/save_xor_extract_suite_after.raw",
                "--save-output",
                "build/gr-v3-behavior/SG_suite.1",
                "--boot-wait",
                "5",
                "--draw-wait",
                "8",
                "--path-prompt-wait",
                "2",
                "--slot-wait",
                "1",
                "--description-wait",
                "1",
                "--confirmation-wait",
                "1",
                "--key-delay",
                "0.08",
            ),
        ),
        SuiteCommand(
            "gr_signed_save_xor_extract_qemu",
            "qemu-v3",
            "Validate the Gold Rush v3 verifier prefix, GRSG save name, and third-block XOR transform.",
            (
                "python3",
                "-B",
                "tools/gr_v3_behavior_probe.py",
                "--probe",
                "save-xor-extract",
                "--verify-signature",
                "--game-dir",
                "games/GR",
                "--fixture-root",
                "build/gr-v3-behavior/save-xor-signed-suite-fixtures",
                "--dos-prefix",
                "GSG",
                "--run-qemu",
                "--output",
                "build/gr-v3-behavior/save_xor_extract_signed_suite.json",
                "--snapshot-raw",
                "build/gr-v3-behavior/snapshot/save_xor_extract_signed_suite.raw",
                "--snapshot-qcow",
                "build/gr-v3-behavior/snapshot/save_xor_extract_signed_suite.qcow2",
                "--post-run-raw",
                "build/gr-v3-behavior/snapshot/save_xor_extract_signed_suite_after.raw",
                "--save-output",
                "build/gr-v3-behavior/GRSG_suite.1",
                "--boot-wait",
                "5",
                "--draw-wait",
                "8",
                "--path-prompt-wait",
                "2",
                "--slot-wait",
                "1",
                "--description-wait",
                "1",
                "--confirmation-wait",
                "1",
                "--key-delay",
                "0.08",
            ),
        ),
        SuiteCommand(
            "gr_signed_restore_roundtrip_qemu",
            "qemu-v3",
            "Validate a Gold Rush v3 signed save restores state and returns through the restored logic stream.",
            (
                "python3",
                "-B",
                "tools/gr_v3_behavior_probe.py",
                "--probe",
                "signed-restore-roundtrip",
                "--game-dir",
                "games/GR",
                "--fixture-root",
                "build/gr-v3-behavior/signed-restore-suite-fixtures",
                "--dos-prefix",
                "GRT",
                "--run-qemu",
                "--output",
                "build/gr-v3-behavior/signed_restore_roundtrip_suite.json",
                "--snapshot-raw",
                "build/gr-v3-behavior/snapshot/signed_restore_roundtrip_suite.raw",
                "--snapshot-qcow",
                "build/gr-v3-behavior/snapshot/signed_restore_roundtrip_suite.qcow2",
                "--post-run-raw",
                "build/gr-v3-behavior/snapshot/signed_restore_roundtrip_suite_after.raw",
                "--save-output",
                "build/gr-v3-behavior/GRSG_restore_suite.1",
                "--boot-wait",
                "5",
                "--draw-wait",
                "8",
                "--path-prompt-wait",
                "2",
                "--slot-wait",
                "1",
                "--description-wait",
                "1",
                "--confirmation-wait",
                "1",
                "--key-delay",
                "0.08",
            ),
        ),
        SuiteCommand(
            "gr_restart_prompt_marker_qemu",
            "qemu-v3",
            "Validate Gold Rush v3 restart-cancel prompt-marker redraw behavior.",
            (
                "python3",
                "-B",
                "tools/gr_v3_behavior_probe.py",
                "--probe",
                "restart-prompt-marker",
                "--game-dir",
                "games/GR",
                "--fixture-root",
                "build/gr-v3-behavior/restart-prompt-suite-fixtures",
                "--dos-prefix",
                "GRP",
                "--run-qemu",
                "--output",
                "build/gr-v3-behavior/restart_prompt_marker_suite.json",
                "--snapshot-raw",
                "build/gr-v3-behavior/snapshot/restart_prompt_marker_suite.raw",
                "--snapshot-qcow",
                "build/gr-v3-behavior/snapshot/restart_prompt_marker_suite.qcow2",
                "--boot-wait",
                "5",
                "--draw-wait",
                "8",
            ),
        ),
        SuiteCommand(
            "gr_menu_gate_qemu",
            "qemu-v3",
            "Validate Gold Rush v3 opcode 0xb1 gating menu interaction.",
            (
                "python3",
                "-B",
                "tools/gr_v3_behavior_probe.py",
                "--probe",
                "menu-gate",
                "--game-dir",
                "games/GR",
                "--fixture-root",
                "build/gr-v3-behavior/menu-gate-suite-fixtures",
                "--dos-prefix",
                "GRG",
                "--run-qemu",
                "--output",
                "build/gr-v3-behavior/menu_gate_suite.json",
                "--snapshot-raw",
                "build/gr-v3-behavior/snapshot/menu_gate_suite.raw",
                "--snapshot-qcow",
                "build/gr-v3-behavior/snapshot/menu_gate_suite.qcow2",
                "--boot-wait",
                "5",
                "--draw-wait",
                "8",
            ),
        ),
        SuiteCommand(
            "gr_synthetic_picture_view_qemu",
            "qemu-v3",
            "Validate generated Gold Rush v3 picture-nibble and direct view fixture records.",
            (
                "python3",
                "-B",
                "tools/gr_v3_behavior_probe.py",
                "--probe",
                "synthetic-picture-view",
                "--game-dir",
                "games/GR",
                "--fixture-root",
                "build/gr-v3-behavior/synthetic-picture-view-suite-fixtures",
                "--dos-prefix",
                "GSP",
                "--run-qemu",
                "--output",
                "build/gr-v3-behavior/synthetic_picture_view_suite.json",
                "--snapshot-raw",
                "build/gr-v3-behavior/snapshot/synthetic_picture_view_suite.raw",
                "--snapshot-qcow",
                "build/gr-v3-behavior/snapshot/synthetic_picture_view_suite.qcow2",
                "--boot-wait",
                "5",
                "--draw-wait",
                "8",
            ),
        ),
    )


def selected_commands(
    *,
    names: Iterable[str] = (),
    include_qemu_smoke: bool = False,
    include_qemu_broad: bool = False,
    include_qemu_v3: bool = False,
) -> tuple[SuiteCommand, ...]:
    commands = suite_commands()
    wanted = set(names)
    if wanted:
        unknown = wanted - {command.name for command in commands}
        if unknown:
            raise ValueError(f"unknown suite command(s): {', '.join(sorted(unknown))}")
        return tuple(command for command in commands if command.name in wanted)

    layers = {"local"}
    if include_qemu_smoke:
        layers.add("qemu-smoke")
    if include_qemu_broad:
        layers.update({"qemu-smoke", "qemu-broad"})
    if include_qemu_v3:
        layers.add("qemu-v3")
    return tuple(command for command in commands if command.layer in layers)


def run_commands(commands: Iterable[SuiteCommand]) -> list[SuiteResult]:
    results: list[SuiteResult] = []
    for command in commands:
        start = time.monotonic()
        completed = subprocess.run(command.command, check=False)
        elapsed = time.monotonic() - start
        results.append(
            SuiteResult(
                command.name,
                command.layer,
                command.command,
                completed.returncode,
                elapsed,
            )
        )
        if completed.returncode != 0:
            break
    return results


def write_report(path: Path, commands: Iterable[SuiteCommand], results: Iterable[SuiteResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "commands": [asdict(command) for command in commands],
        "results": [asdict(result) for result in results],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="print the suite manifest as JSON and exit")
    parser.add_argument("--name", action="append", default=[], help="run only a named command; may be repeated")
    parser.add_argument("--include-qemu-smoke", action="store_true", help="include short QEMU validation batches")
    parser.add_argument("--include-qemu-broad", action="store_true", help="include broad QEMU resource sweeps")
    parser.add_argument("--include-qemu-v3", action="store_true", help="include opt-in v3 interpreter QEMU probes")
    parser.add_argument("--dry-run", action="store_true", help="print selected commands without executing them")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    commands = selected_commands(
        names=args.name,
        include_qemu_smoke=args.include_qemu_smoke,
        include_qemu_broad=args.include_qemu_broad,
        include_qemu_v3=args.include_qemu_v3,
    )
    if args.list or args.dry_run:
        print(json.dumps([asdict(command) for command in commands], indent=2, sort_keys=True))
        return

    results = run_commands(commands)
    write_report(args.report, commands, results)
    failed = [result for result in results if result.returncode != 0]
    if failed:
        raise SystemExit(failed[0].returncode)


if __name__ == "__main__":
    main()
