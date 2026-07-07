#!/usr/bin/env python3
"""Shared local path parameters for clean-room AGI tooling."""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FREEDOS_IMAGE = Path("build/freedos/freedos.img")
_CLI_GAME_DIR: Path | None = None


def _consume_game_dir_option() -> Path | None:
    """Consume the project-wide --game-dir option before script parsers run."""
    global _CLI_GAME_DIR
    if _CLI_GAME_DIR is not None:
        return _CLI_GAME_DIR

    argv = sys.argv
    for index, item in enumerate(list(argv[1:]), start=1):
        if item == "--game-dir":
            if index + 1 >= len(argv):
                raise SystemExit("error: --game-dir requires a path")
            _CLI_GAME_DIR = Path(argv[index + 1]).expanduser()
            del argv[index : index + 2]
            return _CLI_GAME_DIR
        if item.startswith("--game-dir="):
            _CLI_GAME_DIR = Path(item.split("=", 1)[1]).expanduser()
            del argv[index]
            return _CLI_GAME_DIR
    return None


def game_dir() -> Path:
    """Return the active local game directory.

    No game is selected by default. Pass --game-dir PATH to any local tool that
    imports this helper, or set AGI_GAME_DIR in the environment.
    """
    cli_value = _consume_game_dir_option()
    if cli_value is not None:
        return cli_value
    configured = os.environ.get("AGI_GAME_DIR")
    if configured:
        return Path(configured).expanduser()
    raise SystemExit("error: game directory required; pass --game-dir PATH or set AGI_GAME_DIR")


def dos_image() -> Path:
    configured = os.environ.get("AGI_DOS_IMAGE")
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_FREEDOS_IMAGE
