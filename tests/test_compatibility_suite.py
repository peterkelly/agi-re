#!/usr/bin/env python3
"""Tests for the compatibility suite manifest/runner."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from compatibility_suite import (  # noqa: E402
    selected_commands,
    suite_commands,
    run_commands,
    write_report,
)


class CompatibilitySuiteTests(unittest.TestCase):
    def test_manifest_includes_local_smoke_and_broad_layers(self) -> None:
        commands = suite_commands()
        by_name = {command.name: command for command in commands}

        self.assertEqual(by_name["local_unittest"].layer, "local")
        self.assertEqual(by_name["mdbook_build"].layer, "local")
        self.assertEqual(by_name["logic_opcode_evidence_check"].layer, "local")
        self.assertEqual(by_name["parser_edges_qemu"].layer, "qemu-smoke")
        self.assertEqual(by_name["parser_unknown_terminator_qemu"].layer, "qemu-smoke")
        self.assertEqual(by_name["picture_fuzz_command_resume_qemu"].layer, "qemu-smoke")
        self.assertEqual(by_name["picture_fuzz_raw_operand_qemu"].layer, "qemu-smoke")
        self.assertEqual(by_name["picture_fuzz_relative_underflow_qemu"].layer, "qemu-smoke")
        self.assertEqual(by_name["picture_carousel_broad_qemu"].layer, "qemu-broad")
        self.assertEqual(by_name["view_carousel_stress_qemu"].layer, "qemu-broad")
        self.assertEqual(by_name["gr_save_xor_extract_qemu"].layer, "qemu-v3")
        self.assertEqual(by_name["gr_signed_save_xor_extract_qemu"].layer, "qemu-v3")
        self.assertEqual(by_name["gr_signed_restore_roundtrip_qemu"].layer, "qemu-v3")
        self.assertEqual(by_name["gr_restart_prompt_marker_qemu"].layer, "qemu-v3")

    def test_default_selection_is_local_only(self) -> None:
        commands = selected_commands()
        self.assertEqual({command.layer for command in commands}, {"local"})

    def test_qemu_selection_levels_are_explicit(self) -> None:
        smoke = selected_commands(include_qemu_smoke=True)
        broad = selected_commands(include_qemu_broad=True)
        v3 = selected_commands(include_qemu_v3=True)

        self.assertIn("qemu-smoke", {command.layer for command in smoke})
        self.assertNotIn("qemu-broad", {command.layer for command in smoke})
        self.assertNotIn("qemu-v3", {command.layer for command in smoke})
        self.assertIn("qemu-broad", {command.layer for command in broad})
        self.assertNotIn("qemu-v3", {command.layer for command in broad})
        self.assertIn("qemu-v3", {command.layer for command in v3})

    def test_name_selection_rejects_unknown_names(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown suite command"):
            selected_commands(names=["missing"])

    def test_run_commands_stops_after_first_failure(self) -> None:
        commands = selected_commands(names=["local_unittest", "mdbook_build"])

        with mock.patch(
            "compatibility_suite.subprocess.run",
            side_effect=[
                subprocess.CompletedProcess(commands[0].command, 7),
                subprocess.CompletedProcess(commands[1].command, 0),
            ],
        ) as run_mock:
            results = run_commands(commands)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "local_unittest")
        self.assertEqual(results[0].returncode, 7)
        self.assertEqual(run_mock.call_count, 1)

    def test_write_report_records_commands_and_results(self) -> None:
        commands = selected_commands(names=["local_unittest"])
        with mock.patch(
            "compatibility_suite.subprocess.run",
            return_value=subprocess.CompletedProcess(commands[0].command, 0),
        ):
            results = run_commands(commands)

        with tempfile.TemporaryDirectory() as temp_dir:
            report = Path(temp_dir) / "report.json"
            write_report(report, commands, results)
            payload = json.loads(report.read_text(encoding="ascii"))

        self.assertEqual(payload["commands"][0]["name"], "local_unittest")
        self.assertEqual(payload["results"][0]["returncode"], 0)


if __name__ == "__main__":
    unittest.main()
