#!/usr/bin/env python3
"""Render local SQ2 view frames to simple PPM images."""

from __future__ import annotations

import argparse
from pathlib import Path

from agi_graphics import frame_to_ppm, render_view_frame


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("view", type=int)
    parser.add_argument("group", type=int)
    parser.add_argument("frame", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rendered = render_view_frame(args.view, args.group, args.frame)
    output = args.output or (
        Path("build/rendered")
        / f"view_{args.view:03d}_{args.group:02d}_{args.frame:02d}.ppm"
    )
    frame_to_ppm(output, rendered)
    print(output)


if __name__ == "__main__":
    main()
