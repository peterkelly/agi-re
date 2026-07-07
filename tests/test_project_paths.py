#!/usr/bin/env python3
"""Tests for project-wide local path parameter handling."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import project_paths  # noqa: E402


class ProjectPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old_argv = list(sys.argv)
        self._old_env = os.environ.get("AGI_GAME_DIR")
        project_paths._CLI_GAME_DIR = None

    def tearDown(self) -> None:
        sys.argv[:] = self._old_argv
        if self._old_env is None:
            os.environ.pop("AGI_GAME_DIR", None)
        else:
            os.environ["AGI_GAME_DIR"] = self._old_env
        project_paths._CLI_GAME_DIR = None

    def test_game_dir_requires_explicit_parameter(self) -> None:
        sys.argv[:] = ["tool"]
        os.environ.pop("AGI_GAME_DIR", None)
        with self.assertRaises(SystemExit):
            project_paths.game_dir()

    def test_game_dir_uses_environment_parameter(self) -> None:
        sys.argv[:] = ["tool"]
        os.environ["AGI_GAME_DIR"] = "games/KQ4"
        self.assertEqual(project_paths.game_dir(), Path("games/KQ4"))

    def test_game_dir_consumes_global_cli_parameter(self) -> None:
        sys.argv[:] = ["tool", "--game-dir", "games/LSL1", "--other"]
        os.environ.pop("AGI_GAME_DIR", None)
        self.assertEqual(project_paths.game_dir(), Path("games/LSL1"))
        self.assertEqual(sys.argv, ["tool", "--other"])


if __name__ == "__main__":
    unittest.main()
