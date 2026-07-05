#!/usr/bin/env python3
"""Source-modeled heap helper formulas for the SQ2 interpreter."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HeapState:
    base: int
    current: int
    limit: int
    room_reset_mark: int
    temporary_mark: int = 0
    high_water: int | None = None

    def __post_init__(self) -> None:
        if self.high_water is None:
            object.__setattr__(self, "high_water", self.current)


@dataclass(frozen=True)
class HeapAllocation:
    pointer: int
    state: HeapState
    free_bytes: int
    free_memory_page_byte: int


@dataclass(frozen=True)
class HeapStatusValues:
    heap_size: int
    current_use: int
    max_use: int
    room_reset_use: int
    event_pair_high_water: int


class HeapAllocationFailure(ValueError):
    """Raised by the source model for the interpreter's fatal heap overflow."""

    pass


def heap_free_bytes(state: HeapState) -> int:
    return (state.limit - state.current) & 0xFFFF


def heap_free_memory_page_byte(state: HeapState) -> int:
    return heap_free_bytes(state) >> 8


def allocate_heap(state: HeapState, size: int) -> HeapAllocation:
    if not 0 <= size <= 0xFFFF:
        raise ValueError("heap allocation size must fit in a 16-bit word")
    available = heap_free_bytes(state)
    if size > available:
        raise HeapAllocationFailure(
            f"requested {size} bytes with only {available} bytes available"
        )
    pointer = state.current
    current = (state.current + size) & 0xFFFF
    high_water = max(state.high_water or state.current, current)
    new_state = HeapState(
        state.base,
        current,
        state.limit,
        state.room_reset_mark,
        state.temporary_mark,
        high_water,
    )
    return HeapAllocation(
        pointer,
        new_state,
        heap_free_bytes(new_state),
        heap_free_memory_page_byte(new_state),
    )


def save_temporary_mark(state: HeapState) -> HeapState:
    return HeapState(
        state.base,
        state.current,
        state.limit,
        state.room_reset_mark,
        state.current,
        state.high_water,
    )


def restore_temporary_mark(state: HeapState) -> HeapState:
    current = state.temporary_mark if state.temporary_mark else state.current
    return HeapState(
        state.base,
        current,
        state.limit,
        state.room_reset_mark,
        0,
        state.high_water,
    )


def reset_dynamic_state(state: HeapState) -> HeapState:
    return HeapState(
        state.base,
        state.room_reset_mark,
        state.limit,
        state.room_reset_mark,
        0,
        state.high_water,
    )


def heap_status_values(state: HeapState, event_pair_high_water: int) -> HeapStatusValues:
    base = state.base
    return HeapStatusValues(
        heap_size=(state.limit - base) & 0xFFFF,
        current_use=(state.current - base) & 0xFFFF,
        max_use=((state.high_water or state.current) - base) & 0xFFFF,
        room_reset_use=(state.room_reset_mark - base) & 0xFFFF,
        event_pair_high_water=event_pair_high_water,
    )
