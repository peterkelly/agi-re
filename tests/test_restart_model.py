#!/usr/bin/env python3
"""Tests for source-backed restart path helper models."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_restart import gr_v3_restart_redraws_prompt_marker  # noqa: E402


class RestartModelTests(unittest.TestCase):
    def test_gr_v3_prompt_marker_redraw_truth_table(self) -> None:
        self.assertFalse(
            gr_v3_restart_redraws_prompt_marker(accepted=False, marker_was_visible=False)
        )
        self.assertTrue(
            gr_v3_restart_redraws_prompt_marker(accepted=False, marker_was_visible=True)
        )
        self.assertTrue(
            gr_v3_restart_redraws_prompt_marker(accepted=True, marker_was_visible=False)
        )
        self.assertTrue(
            gr_v3_restart_redraws_prompt_marker(accepted=True, marker_was_visible=True)
        )


if __name__ == "__main__":
    unittest.main()
