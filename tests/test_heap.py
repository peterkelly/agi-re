#!/usr/bin/env python3
"""Tests for source-modeled interpreter heap formulas."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_heap import (  # noqa: E402
    HeapAllocationFailure,
    HeapState,
    HeapStatusValues,
    allocate_heap,
    heap_free_memory_page_byte,
    heap_status_values,
    reset_dynamic_state,
    restore_temporary_mark,
    save_temporary_mark,
)


class HeapModelTests(unittest.TestCase):
    def test_allocate_returns_old_top_and_updates_free_byte(self) -> None:
        state = HeapState(
            base=0x1000,
            current=0x1200,
            limit=0x2000,
            room_reset_mark=0x1100,
            high_water=0x1250,
        )

        allocation = allocate_heap(state, 0x80)

        self.assertEqual(allocation.pointer, 0x1200)
        self.assertEqual(allocation.state.current, 0x1280)
        self.assertEqual(allocation.state.high_water, 0x1280)
        self.assertEqual(allocation.free_bytes, 0x0D80)
        self.assertEqual(allocation.free_memory_page_byte, 0x0D)

    def test_allocate_preserves_higher_high_water(self) -> None:
        state = HeapState(
            base=0x1000,
            current=0x1200,
            limit=0x2000,
            room_reset_mark=0x1100,
            high_water=0x1800,
        )

        self.assertEqual(allocate_heap(state, 0x80).state.high_water, 0x1800)

    def test_allocate_failure_is_modeled_as_nonrecoverable(self) -> None:
        state = HeapState(
            base=0x1000,
            current=0x1FF0,
            limit=0x2000,
            room_reset_mark=0x1100,
            high_water=0x1FF0,
        )

        with self.assertRaises(HeapAllocationFailure):
            allocate_heap(state, 0x20)

    def test_temporary_mark_restore_rewinds_when_mark_is_nonzero(self) -> None:
        state = HeapState(
            base=0x1000,
            current=0x1300,
            limit=0x2000,
            room_reset_mark=0x1100,
            high_water=0x1400,
        )

        marked = save_temporary_mark(state)
        advanced = HeapState(
            marked.base,
            0x1500,
            marked.limit,
            marked.room_reset_mark,
            marked.temporary_mark,
            marked.high_water,
        )
        restored = restore_temporary_mark(advanced)

        self.assertEqual(restored.current, 0x1300)
        self.assertEqual(restored.temporary_mark, 0)
        self.assertEqual(restored.high_water, 0x1400)

    def test_temporary_mark_restore_is_noop_when_mark_is_zero(self) -> None:
        state = HeapState(
            base=0x1000,
            current=0x1500,
            limit=0x2000,
            room_reset_mark=0x1100,
            temporary_mark=0,
            high_water=0x1600,
        )

        restored = restore_temporary_mark(state)

        self.assertEqual(restored.current, 0x1500)
        self.assertEqual(restored.temporary_mark, 0)
        self.assertEqual(restored.high_water, 0x1600)

    def test_reset_dynamic_state_rewinds_room_mark_and_clears_temp(self) -> None:
        state = HeapState(
            base=0x1000,
            current=0x1700,
            limit=0x2000,
            room_reset_mark=0x1234,
            temporary_mark=0x1600,
            high_water=0x1800,
        )

        reset = reset_dynamic_state(state)

        self.assertEqual(reset.current, 0x1234)
        self.assertEqual(reset.temporary_mark, 0)
        self.assertEqual(heap_free_memory_page_byte(reset), (0x2000 - 0x1234) >> 8)

    def test_heap_status_values_match_source_formulas(self) -> None:
        state = HeapState(
            base=0x1000,
            current=0x1300,
            limit=0x2000,
            room_reset_mark=0x1200,
            high_water=0x1800,
        )

        self.assertEqual(
            heap_status_values(state, event_pair_high_water=7),
            HeapStatusValues(
                heap_size=0x1000,
                current_use=0x0300,
                max_use=0x0800,
                room_reset_use=0x0200,
                event_pair_high_water=7,
            ),
        )


if __name__ == "__main__":
    unittest.main()
