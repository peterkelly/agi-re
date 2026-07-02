#!/usr/bin/env python3
"""Compare a QEMU original-engine picture capture with the local renderer."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from agi_graphics import (
    HEIGHT,
    PALETTE,
    WIDTH,
    compose_frame_on_picture,
    render_picture,
    render_view_frame,
)
from ppm_tools import PpmImage, read_ppm


@dataclass(frozen=True)
class PictureCaptureComparison:
    picture_no: int
    mismatches: int
    total: int
    mismatch_bbox: tuple[int, int, int, int] | None = None
    samples: list[tuple[int, int, int, int]] | None = None

    @property
    def matches(self) -> bool:
        return self.mismatches == 0


def nearest_palette_nibble(rgb: tuple[int, int, int]) -> int:
    return min(
        range(len(PALETTE)),
        key=lambda idx: sum((rgb[channel] - PALETTE[idx][channel]) ** 2 for channel in range(3)),
    )


def downsample_qemu_picture_nibbles(
    image: PpmImage,
    x_offset: int = 0,
    y_offset: int = 0,
    x_scale: int = 4,
    y_scale: int = 2,
) -> bytes:
    if image.width < x_offset + WIDTH * x_scale:
        raise ValueError("image is too narrow for requested picture downsample")
    if image.height < y_offset + HEIGHT * y_scale:
        raise ValueError("image is too short for requested picture downsample")

    indexed = [
        nearest_palette_nibble((image.rgb[i], image.rgb[i + 1], image.rgb[i + 2]))
        for i in range(0, len(image.rgb), 3)
    ]
    out = bytearray()
    for y in range(HEIGHT):
        block_y = y_offset + y * y_scale
        for x in range(WIDTH):
            block_x = x_offset + x * x_scale
            counts: Counter[int] = Counter()
            for yy in range(block_y, block_y + y_scale):
                row = yy * image.width
                for xx in range(block_x, block_x + x_scale):
                    counts[indexed[row + xx]] += 1
            out.append(counts.most_common(1)[0][0])
    return bytes(out)


def compare_picture_capture(
    picture_no: int,
    capture_path: Path,
    x_offset: int = 0,
    y_offset: int = 0,
    x_scale: int = 4,
    y_scale: int = 2,
    view: tuple[int, int, int, int, int, int] | None = None,
) -> PictureCaptureComparison:
    image = read_ppm(capture_path)
    captured = downsample_qemu_picture_nibbles(image, x_offset, y_offset, x_scale, y_scale)
    rendered_picture = render_picture(picture_no)
    if view is not None:
        view_no, group_no, frame_no, left, baseline_y, priority = view
        rendered_frame = render_view_frame(view_no, group_no, frame_no)
        rendered_picture = compose_frame_on_picture(
            rendered_picture,
            rendered_frame,
            left,
            baseline_y,
            priority,
        )
    rendered = rendered_picture.visual_nibbles
    mismatch_samples: list[tuple[int, int, int, int]] = []
    min_x = WIDTH
    min_y = HEIGHT
    max_x = -1
    max_y = -1
    mismatches = 0
    for idx, (left, right) in enumerate(zip(captured, rendered)):
        if left == right:
            continue
        mismatches += 1
        x = idx % WIDTH
        y = idx // WIDTH
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)
        if len(mismatch_samples) < 16:
            mismatch_samples.append((x, y, left, right))
    bbox = None if mismatches == 0 else (min_x, min_y, max_x, max_y)
    return PictureCaptureComparison(picture_no, mismatches, len(rendered), bbox, mismatch_samples)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("picture", type=int)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--x-offset", type=int, default=0)
    parser.add_argument("--y-offset", type=int, default=0)
    parser.add_argument("--x-scale", type=int, default=4)
    parser.add_argument("--y-scale", type=int, default=2)
    parser.add_argument("--view", nargs=3, type=int, metavar=("VIEW", "GROUP", "FRAME"))
    parser.add_argument("--view-x", type=int)
    parser.add_argument("--view-baseline-y", type=int)
    parser.add_argument("--view-priority", type=int)
    args = parser.parse_args()
    view = None
    if args.view is not None:
        if args.view_x is None or args.view_baseline_y is None or args.view_priority is None:
            parser.error("--view requires --view-x, --view-baseline-y, and --view-priority")
        view = (*args.view, args.view_x, args.view_baseline_y, args.view_priority)

    comparison = compare_picture_capture(
        args.picture,
        args.capture,
        args.x_offset,
        args.y_offset,
        args.x_scale,
        args.y_scale,
        view,
    )
    print(f"picture: {comparison.picture_no}")
    print(f"mismatches: {comparison.mismatches}")
    print(f"total: {comparison.total}")
    print(f"match: {comparison.matches}")


if __name__ == "__main__":
    main()
