#!/usr/bin/env python3
"""Print simple facts about a binary PPM image."""

from __future__ import annotations

import argparse
from pathlib import Path

from ppm_tools import non_background_bbox, read_ppm, unique_colors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    args = parser.parse_args()

    image = read_ppm(args.image)
    bbox = non_background_bbox(image)
    print(f"path: {args.image}")
    print(f"geometry: {image.width}x{image.height}")
    print(f"max_value: {image.max_value}")
    print(f"sha256_rgb: {image.digest}")
    print(f"unique_colors: {len(unique_colors(image))}")
    print(f"non_background_bbox: {bbox}")


if __name__ == "__main__":
    main()
