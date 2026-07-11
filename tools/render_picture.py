#!/usr/bin/env python3
"""Render a selected game's picture resources to simple PPM images."""

from __future__ import annotations

import argparse
from pathlib import Path

from agi_graphics import picture_to_ppm, render_picture


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("picture", type=int)
    parser.add_argument("--channel", choices=["visual", "control"], default="visual")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--no-pattern-brushes",
        action="store_true",
        help="ignore patterned brush stamps when their interpreter tables are unknown",
    )
    args = parser.parse_args()

    rendered = render_picture(
        args.picture,
        pattern_brushes=not args.no_pattern_brushes,
    )
    output = args.output or Path("build/rendered") / f"picture_{args.picture:03d}_{args.channel}.ppm"
    picture_to_ppm(output, rendered, args.channel)
    print(output)


if __name__ == "__main__":
    main()
