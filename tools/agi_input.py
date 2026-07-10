#!/usr/bin/env python3
"""Clean-room helpers for source-backed input/keyboard state decisions."""

from __future__ import annotations

from dataclasses import dataclass, replace


TRACKED_RELEASE_SCAN_FIRST = 0x47
TRACKED_RELEASE_SCAN_LAST = 0x51
TRACKED_RELEASE_SCAN_COUNT = TRACKED_RELEASE_SCAN_LAST - TRACKED_RELEASE_SCAN_FIRST + 1
KEY_RELEASE_BIT = 0x80
KEY_RELEASE_EVENT = (2, 0)


@dataclass(frozen=True)
class KeyReleaseIrqState:
    """Portable model of the tracked-key latch/gate state in the IRQ hook."""

    enabled: tuple[bool, ...] = (True,) * TRACKED_RELEASE_SCAN_COUNT
    pressed_latches: tuple[bool, ...] = (False,) * TRACKED_RELEASE_SCAN_COUNT
    gate: int = 0

    def __post_init__(self) -> None:
        if len(self.enabled) != TRACKED_RELEASE_SCAN_COUNT:
            raise ValueError("enabled table length must match tracked scan range")
        if len(self.pressed_latches) != TRACKED_RELEASE_SCAN_COUNT:
            raise ValueError("pressed latch table length must match tracked scan range")
        if not 0 <= self.gate <= 0xFF:
            raise ValueError("gate is modeled as an unsigned byte")


@dataclass(frozen=True)
class KeyReleaseIrqResult:
    state: KeyReleaseIrqState
    enqueued_event: tuple[int, int] | None


def sq2_action_ad_increment_gate(state: KeyReleaseIrqState) -> KeyReleaseIrqState:
    """Model SQ2 action 0xad, `inc byte [0x1530]`."""

    return replace(state, gate=(state.gate + 1) & 0xFF)


def gr_v3_action_ad_set_gate(state: KeyReleaseIrqState) -> KeyReleaseIrqState:
    """Model GR action 0xad, `mov byte [0x0405], 1`."""

    return replace(state, gate=1)


def gr_v3_action_b5_clear_gate(state: KeyReleaseIrqState) -> KeyReleaseIrqState:
    """Model GR action 0xb5, `mov byte [0x0405], 0`."""

    return replace(state, gate=0)


def process_tracked_key_irq_scan(state: KeyReleaseIrqState, scan_byte: int) -> KeyReleaseIrqResult:
    """Apply the source-backed tracked-key portion of the keyboard IRQ hook.

    The disassembled SQ2 and GR hooks share this latch shape after relocation:
    scan codes 0x47..0x51 are tracked, keydown clears all tracked latches and
    sets the selected latch, and key release enqueues event (type=2, value=0)
    only if the selected latch was set and the gate byte is nonzero.
    """

    if not 0 <= scan_byte <= 0xFF:
        raise ValueError("scan byte must fit in one byte")

    scan_code = scan_byte & ~KEY_RELEASE_BIT
    index = scan_code - TRACKED_RELEASE_SCAN_FIRST
    if index < 0 or index >= TRACKED_RELEASE_SCAN_COUNT:
        return KeyReleaseIrqResult(state, None)
    if not state.enabled[index]:
        return KeyReleaseIrqResult(state, None)

    latches = list(state.pressed_latches)
    if scan_byte & KEY_RELEASE_BIT:
        if not latches[index]:
            return KeyReleaseIrqResult(state, None)
        latches[index] = False
        event = KEY_RELEASE_EVENT if state.gate != 0 else None
        return KeyReleaseIrqResult(replace(state, pressed_latches=tuple(latches)), event)

    if latches[index]:
        return KeyReleaseIrqResult(state, None)

    latches = [False] * TRACKED_RELEASE_SCAN_COUNT
    latches[index] = True
    return KeyReleaseIrqResult(replace(state, pressed_latches=tuple(latches)), None)
