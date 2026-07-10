#!/usr/bin/env python3
"""Tests for source-backed input/keyboard helper models."""

from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_input import (  # noqa: E402
    KEY_RELEASE_EVENT,
    KEY_RELEASE_BIT,
    TRACKED_RELEASE_SCAN_COUNT,
    TRACKED_RELEASE_SCAN_FIRST,
    KeyReleaseIrqState,
    gr_v3_action_ad_set_gate,
    gr_v3_action_b5_clear_gate,
    process_tracked_key_irq_scan,
    sq2_action_ad_increment_gate,
)


class InputModelTests(unittest.TestCase):
    def press(self, state: KeyReleaseIrqState, scan_code: int) -> KeyReleaseIrqState:
        return process_tracked_key_irq_scan(state, scan_code).state

    def release(self, state: KeyReleaseIrqState, scan_code: int):
        return process_tracked_key_irq_scan(state, scan_code | KEY_RELEASE_BIT)

    def test_sq2_action_ad_increments_byte_gate_for_release_events(self) -> None:
        scan = TRACKED_RELEASE_SCAN_FIRST + 1
        state = self.press(KeyReleaseIrqState(), scan)
        self.assertIsNone(self.release(state, scan).enqueued_event)

        state = sq2_action_ad_increment_gate(KeyReleaseIrqState())
        self.assertEqual(state.gate, 1)
        state = self.press(state, scan)
        result = self.release(state, scan)

        self.assertEqual(result.enqueued_event, KEY_RELEASE_EVENT)
        self.assertFalse(result.state.pressed_latches[1])

    def test_sq2_action_ad_wraps_like_an_unsigned_byte(self) -> None:
        state = sq2_action_ad_increment_gate(KeyReleaseIrqState(gate=0xFF))

        self.assertEqual(state.gate, 0)

    def test_gr_v3_actions_set_and_clear_release_gate(self) -> None:
        scan = TRACKED_RELEASE_SCAN_FIRST + 2
        state = gr_v3_action_ad_set_gate(KeyReleaseIrqState(gate=0xFE))
        self.assertEqual(state.gate, 1)

        state = gr_v3_action_b5_clear_gate(state)
        self.assertEqual(state.gate, 0)
        self.assertIsNone(self.release(self.press(state, scan), scan).enqueued_event)

        state = gr_v3_action_ad_set_gate(state)
        self.assertEqual(self.release(self.press(state, scan), scan).enqueued_event, KEY_RELEASE_EVENT)

    def test_new_tracked_key_press_clears_other_latches(self) -> None:
        first = TRACKED_RELEASE_SCAN_FIRST
        second = TRACKED_RELEASE_SCAN_FIRST + 1
        state = KeyReleaseIrqState(gate=1)
        state = self.press(state, first)
        state = self.press(state, second)

        self.assertIsNone(self.release(state, first).enqueued_event)
        self.assertEqual(self.release(state, second).enqueued_event, KEY_RELEASE_EVENT)

    def test_disabled_and_out_of_range_scans_do_not_enqueue(self) -> None:
        disabled = (False,) + (True,) * (TRACKED_RELEASE_SCAN_COUNT - 1)
        state = KeyReleaseIrqState(enabled=disabled, gate=1)
        self.assertIsNone(self.release(self.press(state, TRACKED_RELEASE_SCAN_FIRST), TRACKED_RELEASE_SCAN_FIRST).enqueued_event)

        state = replace(KeyReleaseIrqState(gate=1), pressed_latches=(True,) * TRACKED_RELEASE_SCAN_COUNT)
        self.assertIsNone(process_tracked_key_irq_scan(state, TRACKED_RELEASE_SCAN_FIRST - 1).enqueued_event)
        self.assertIsNone(process_tracked_key_irq_scan(state, TRACKED_RELEASE_SCAN_FIRST - 1 | KEY_RELEASE_BIT).enqueued_event)

    def test_state_validates_table_lengths_and_gate_range(self) -> None:
        with self.assertRaises(ValueError):
            KeyReleaseIrqState(enabled=(True,))
        with self.assertRaises(ValueError):
            KeyReleaseIrqState(pressed_latches=(False,))
        with self.assertRaises(ValueError):
            KeyReleaseIrqState(gate=0x100)
        with self.assertRaises(ValueError):
            process_tracked_key_irq_scan(KeyReleaseIrqState(), 0x100)


if __name__ == "__main__":
    unittest.main()
