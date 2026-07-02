#!/usr/bin/env python3
"""Render local SQ2 picture resources to simple PPM images."""

from __future__ import annotations

import argparse
from pathlib import Path

from agi_graphics import picture_to_ppm, render_picture


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("picture", type=int)
    parser.add_argument("--channel", choices=["visual", "control"], default="visual")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rendered = render_picture(args.picture)
    output = args.output or Path("build/rendered") / f"picture_{args.picture:03d}_{args.channel}.ppm"
    picture_to_ppm(output, rendered, args.channel)
    print(output)


if __name__ == "__main__":
    main()
