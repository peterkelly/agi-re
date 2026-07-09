#!/usr/bin/env python3
"""Clean-room helpers for restart-path state decisions."""

from __future__ import annotations


def gr_v3_restart_redraws_prompt_marker(*, accepted: bool, marker_was_visible: bool) -> bool:
    """Model the observed Gold Rush v3 prompt-marker redraw branch after restart confirmation."""
    return accepted or marker_was_visible
