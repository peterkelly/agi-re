#!/usr/bin/env python3
"""Small PPM helpers for generated renders and QEMU screenshots."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class PpmImage:
    width: int
    height: int
    max_value: int
    rgb: bytes

    @property
    def pixel_count(self) -> int:
        return self.width * self.height

    @property
    def digest(self) -> str:
        return sha256(self.rgb).hexdigest()


def _read_token(data: bytes, pos: int) -> tuple[bytes, int]:
    while pos < len(data) and data[pos] in b" \t\r\n":
        pos += 1
    if pos < len(data) and data[pos] == ord("#"):
        while pos < len(data) and data[pos] not in b"\r\n":
            pos += 1
        return _read_token(data, pos)
    start = pos
    while pos < len(data) and data[pos] not in b" \t\r\n":
        pos += 1
    return data[start:pos], pos


def read_ppm(path: Path) -> PpmImage:
    data = path.read_bytes()
    magic, pos = _read_token(data, 0)
    if magic != b"P6":
        raise ValueError(f"{path} is not a binary PPM")
    width_token, pos = _read_token(data, pos)
    height_token, pos = _read_token(data, pos)
    max_token, pos = _read_token(data, pos)
    if pos >= len(data) or data[pos] not in b" \t\r\n":
        raise ValueError(f"{path} has a malformed PPM header")
    pos += 1
    width = int(width_token)
    height = int(height_token)
    max_value = int(max_token)
    rgb = data[pos:]
    expected = width * height * 3
    if len(rgb) != expected:
        raise ValueError(f"{path} has {len(rgb)} RGB bytes, expected {expected}")
    return PpmImage(width, height, max_value, rgb)


def unique_colors(image: PpmImage) -> set[tuple[int, int, int]]:
    return {
        (image.rgb[i], image.rgb[i + 1], image.rgb[i + 2])
        for i in range(0, len(image.rgb), 3)
    }


def non_background_bbox(image: PpmImage, background: tuple[int, int, int] | None = None) -> tuple[int, int, int, int] | None:
    if background is None:
        background = (image.rgb[0], image.rgb[1], image.rgb[2])
    min_x = image.width
    min_y = image.height
    max_x = -1
    max_y = -1
    for y in range(image.height):
        row = y * image.width * 3
        for x in range(image.width):
            i = row + x * 3
            color = (image.rgb[i], image.rgb[i + 1], image.rgb[i + 2])
            if color == background:
                continue
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
    if max_x < 0:
        return None
    return min_x, min_y, max_x, max_y
