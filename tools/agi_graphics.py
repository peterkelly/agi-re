#!/usr/bin/env python3
"""Clean-room picture and view rendering helpers for local SQ2 resources.

The routines here implement only behavior derived in this repository. They are
intended to become the executable compatibility oracle for picture/view work:
first as deterministic local renderers, later as inputs to comparisons against
QEMU captures from the original interpreter.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from disassemble_logic import AGIDATA, SQ2, read_dir_entries, read_volume_payload, u16le


WIDTH = 0xA0
HEIGHT = 0xA8
DEFAULT_CELL = 0x4F


PALETTE = [
    (0x00, 0x00, 0x00),
    (0x00, 0x00, 0xAA),
    (0x00, 0xAA, 0x00),
    (0x00, 0xAA, 0xAA),
    (0xAA, 0x00, 0x00),
    (0xAA, 0x00, 0xAA),
    (0xAA, 0x55, 0x00),
    (0xAA, 0xAA, 0xAA),
    (0x55, 0x55, 0x55),
    (0x55, 0x55, 0xFF),
    (0x55, 0xFF, 0x55),
    (0x55, 0xFF, 0xFF),
    (0xFF, 0x55, 0x55),
    (0xFF, 0x55, 0xFF),
    (0xFF, 0xFF, 0x55),
    (0xFF, 0xFF, 0xFF),
]


@lru_cache(maxsize=1)
def agidata_bytes() -> bytes:
    return AGIDATA.read_bytes()


def pattern_column_mask(column: int) -> int:
    return u16le(agidata_bytes(), 0x15F9 + column * 4)


def pattern_row_words(radius: int) -> list[int]:
    data = agidata_bytes()
    pointer = u16le(data, 0x1619 + radius * 2)
    return [u16le(data, pointer + row * 2) for row in range(radius * 2 + 1)]


@dataclass(frozen=True)
class RenderedPicture:
    picture_no: int
    cells: bytes

    @property
    def visual_nibbles(self) -> bytes:
        return bytes(cell & 0x0F for cell in self.cells)

    @property
    def control_nibbles(self) -> bytes:
        return bytes((cell >> 4) & 0x0F for cell in self.cells)


@dataclass(frozen=True)
class RenderedFrame:
    view_no: int
    group_no: int
    frame_no: int
    width: int
    height: int
    control: int
    pixels: bytes


def resource_payload(dir_name: str, resource_no: int) -> bytes:
    entries = read_dir_entries(SQ2 / dir_name)
    entry = entries[resource_no]
    if entry is None:
        raise ValueError(f"{dir_name} resource {resource_no} is absent")
    return read_volume_payload(*entry)


def iter_valid_resources(dir_name: str) -> Iterable[tuple[int, bytes]]:
    entries = read_dir_entries(SQ2 / dir_name)
    for resource_no, entry in enumerate(entries):
        if entry is None:
            continue
        try:
            payload = read_volume_payload(*entry)
        except ValueError:
            continue
        yield resource_no, payload


def picture_payload(picture_no: int) -> bytes:
    return resource_payload("PICDIR", picture_no)


def view_payload(view_no: int) -> bytes:
    return resource_payload("VIEWDIR", view_no)


class PictureRenderer:
    def __init__(self, payload: bytes, clear: bool = True):
        self.payload = payload
        self.pos = 0
        self.cells = bytearray([DEFAULT_CELL if clear else 0 for _ in range(WIDTH * HEIGHT)])
        self.draw_state = 0
        self.visual_value = 0
        self.control_value = 0
        self.odd_y_mask = 0xFF
        self.even_y_mask = 0xFF
        self.pattern_mode = 0
        self.pattern_seed = 0

    def render(self, picture_no: int = -1) -> RenderedPicture:
        while self.pos < len(self.payload):
            command = self.payload[self.pos]
            self.pos += 1
            if command == 0xFF:
                break
            if command < 0xF0:
                continue
            handler = {
                0xF0: self.set_visual,
                0xF1: self.disable_visual,
                0xF2: self.set_control,
                0xF3: self.disable_control,
                0xF4: self.draw_corner_y_first,
                0xF5: self.draw_corner_x_first,
                0xF6: self.draw_absolute_lines,
                0xF7: self.draw_relative_lines,
                0xF8: self.seed_fill_command,
                0xF9: self.set_pattern_mode,
                0xFA: self.pattern_plot_command,
            }.get(command)
            if handler is not None:
                handler()
        return RenderedPicture(picture_no, bytes(self.cells))

    def peek(self) -> int | None:
        if self.pos >= len(self.payload):
            return None
        return self.payload[self.pos]

    def read_data_byte(self) -> int | None:
        value = self.peek()
        if value is None or value > 0xEF:
            return None
        self.pos += 1
        return value

    def read_coord_pair(self) -> tuple[int, int] | None:
        x = self.read_data_byte()
        if x is None:
            return None
        y = self.read_data_byte()
        if y is None:
            return None
        return min(x, 0x9F), min(y, 0xA7)

    def set_visual(self) -> None:
        value = self.read_data_byte()
        if value is None:
            return
        mapped_low = value & 0x0F
        mapped_even = mapped_low
        self.visual_value = mapped_low
        self.draw_state |= 0x0F
        self.odd_y_mask = (self.odd_y_mask & 0xF0) | mapped_low
        self.even_y_mask = (self.even_y_mask & 0xF0) | mapped_even

    def disable_visual(self) -> None:
        self.draw_state &= 0xF0
        self.odd_y_mask |= 0x0F
        self.even_y_mask |= 0x0F

    def set_control(self) -> None:
        value = self.read_data_byte()
        if value is None:
            return
        high = (value << 4) & 0xF0
        self.control_value = high
        self.draw_state |= 0xF0
        self.odd_y_mask = (self.odd_y_mask & 0x0F) | high
        self.even_y_mask = (self.even_y_mask & 0x0F) | high

    def disable_control(self) -> None:
        self.draw_state &= 0x0F
        self.odd_y_mask |= 0xF0
        self.even_y_mask |= 0xF0

    def write_pixel(self, x: int, y: int) -> None:
        if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
            return
        idx = y * WIDTH + x
        mask = self.odd_y_mask if (y & 1) else self.even_y_mask
        self.cells[idx] = (self.cells[idx] | self.draw_state) & mask

    def draw_horizontal(self, x0: int, y: int, x1: int) -> None:
        if x0 > x1:
            x0, x1 = x1, x0
        for x in range(x0, x1 + 1):
            self.write_pixel(x, y)

    def draw_vertical(self, x: int, y0: int, y1: int) -> None:
        if y0 > y1:
            y0, y1 = y1, y0
        for y in range(y0, y1 + 1):
            self.write_pixel(x, y)

    def draw_line(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        x, y = start
        x1, y1 = end
        if x == x1:
            self.draw_vertical(x, y, y1)
            return
        if y == y1:
            self.draw_horizontal(x, y, x1)
            return

        dx = abs(x1 - x)
        x_step = 1 if x1 >= x else -1
        dy = abs(y1 - y)
        y_step = 1 if y1 >= y else -1
        if dx >= dy:
            count = dx
            major = dx
            y_error = dx >> 1
            x_error = 0
        else:
            count = dy
            major = dy
            x_error = dy >> 1
            y_error = 0

        for _ in range(count):
            y_error = (y_error + dy) & 0xFF
            if y_error >= major:
                y_error = (y_error - major) & 0xFF
                y += y_step
            x_error = (x_error + dx) & 0xFF
            if x_error >= major:
                x_error = (x_error - major) & 0xFF
                x += x_step
            self.write_pixel(x, y)

    def draw_corner_y_first(self) -> None:
        point = self.read_coord_pair()
        if point is None:
            return
        self.write_pixel(*point)
        x, y = point
        vertical_next = True
        while True:
            value = self.read_data_byte()
            if value is None:
                return
            if vertical_next:
                new_y = min(value, 0xA7)
                self.draw_vertical(x, y, new_y)
                y = new_y
            else:
                new_x = min(value, 0x9F)
                self.draw_horizontal(x, y, new_x)
                x = new_x
            vertical_next = not vertical_next

    def draw_corner_x_first(self) -> None:
        point = self.read_coord_pair()
        if point is None:
            return
        self.write_pixel(*point)
        x, y = point
        horizontal_next = True
        while True:
            value = self.read_data_byte()
            if value is None:
                return
            if horizontal_next:
                new_x = min(value, 0x9F)
                self.draw_horizontal(x, y, new_x)
                x = new_x
            else:
                new_y = min(value, 0xA7)
                self.draw_vertical(x, y, new_y)
                y = new_y
            horizontal_next = not horizontal_next

    def draw_absolute_lines(self) -> None:
        point = self.read_coord_pair()
        if point is None:
            return
        self.write_pixel(*point)
        while True:
            next_point = self.read_coord_pair()
            if next_point is None:
                return
            self.draw_line(point, next_point)
            point = next_point

    def draw_relative_lines(self) -> None:
        point = self.read_coord_pair()
        if point is None:
            return
        self.write_pixel(*point)
        x, y = point
        while True:
            value = self.read_data_byte()
            if value is None:
                return
            dx = (value & 0x70) >> 4
            if value & 0x80:
                dx = -dx
            dy = value & 0x07
            if value & 0x08:
                dy = -dy
            new_point = (min(max(x + dx, 0), 0x9F), min(max(y + dy, 0), 0xA7))
            self.draw_line((x, y), new_point)
            x, y = new_point

    def seed_fill_command(self) -> None:
        while True:
            point = self.read_coord_pair()
            if point is None:
                return
            self.seed_fill(*point)

    def seed_fill(self, x: int, y: int) -> None:
        if self.draw_state & 0x0F:
            if self.visual_value == 0x0F:
                return
            mask = 0x0F
            target = 0x0F
        elif self.draw_state & 0xF0:
            if self.control_value == 0x40:
                return
            mask = 0xF0
            target = 0x40
        else:
            return

        if (self.cells[y * WIDTH + x] & mask) != target:
            return
        queue: deque[tuple[int, int]] = deque([(x, y)])
        seen: set[tuple[int, int]] = set()
        while queue:
            px, py = queue.popleft()
            if (px, py) in seen or not (0 <= px < WIDTH and 0 <= py < HEIGHT):
                continue
            seen.add((px, py))
            idx = py * WIDTH + px
            if (self.cells[idx] & mask) != target:
                continue
            self.write_pixel(px, py)
            queue.extend(((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)))

    def set_pattern_mode(self) -> None:
        value = self.read_data_byte()
        if value is not None:
            self.pattern_mode = value

    def pattern_plot_command(self) -> None:
        while True:
            if self.pattern_mode & 0x20:
                value = self.read_data_byte()
                if value is None:
                    return
                self.pattern_seed = value
            point = self.read_coord_pair()
            if point is None:
                return
            self.pattern_plot(*point)

    def pattern_plot(self, x: int, y: int) -> None:
        radius = self.pattern_mode & 0x07
        doubled_x = x * 2 - radius
        if doubled_x < 0:
            doubled_x = 0
        max_doubled_x = 0x140 - radius * 2
        if doubled_x >= max_doubled_x:
            doubled_x = max_doubled_x
        start_x = doubled_x // 2

        start_y = y - radius
        if start_y < 0:
            start_y = 0
        max_start_y = 0xA7 - radius * 2
        if start_y >= max_start_y:
            start_y = max_start_y

        random_byte = self.pattern_seed | 0x01
        for row, pattern_word in enumerate(pattern_row_words(radius)):
            py = start_y + row
            for column in range(radius + 1):
                if not (self.pattern_mode & 0x10):
                    if not (pattern_word & pattern_column_mask(column)):
                        continue
                if self.pattern_mode & 0x20:
                    carry = random_byte & 0x01
                    random_byte >>= 1
                    if carry:
                        random_byte ^= 0xB8
                    if random_byte & 0x01:
                        continue
                    if not (random_byte & 0x02):
                        continue
                self.write_pixel(start_x + column, py)


def render_picture(picture_no: int, clear: bool = True) -> RenderedPicture:
    return PictureRenderer(picture_payload(picture_no), clear=clear).render(picture_no)


def iter_view_frames(payload: bytes) -> Iterable[tuple[int, int, int]]:
    group_count = payload[2]
    for group_no in range(group_count):
        group_offset = u16le(payload, 5 + group_no * 2)
        frame_count = payload[group_offset]
        for frame_no in range(frame_count):
            frame_offset = group_offset + u16le(payload, group_offset + 1 + frame_no * 2)
            yield group_no, frame_no, frame_offset


def _mirror_view_row_runs(row: list[int], width: int, transparent: int) -> list[int]:
    transparent_high = (transparent & 0x0F) << 4
    first_visible_run = None
    for idx, value in enumerate(row):
        if value & 0xF0 != transparent_high:
            first_visible_run = idx
            break
    if first_visible_run is None:
        return []

    tail = row[first_visible_run:]
    used_width = sum(value & 0x0F for value in row)
    leading_transparent_width = max(0, width - used_width)
    mirrored: list[int] = []
    while leading_transparent_width > 0:
        run = min(0x0F, leading_transparent_width)
        mirrored.append(transparent_high | run)
        leading_transparent_width -= run
    mirrored.extend(reversed(tail))
    return mirrored


def _orient_view_rows(
    rows: list[list[int]],
    width: int,
    control: int,
    group_no: int,
) -> tuple[int, list[list[int]]]:
    if not (control & 0x80):
        return control, rows
    cached_group = (control & 0x70) >> 4
    if cached_group == group_no:
        return control, rows

    rewritten_control = (control & 0x8F) | ((group_no << 4) & 0x70)
    transparent = control & 0x0F
    return rewritten_control, [
        _mirror_view_row_runs(row, width, transparent)
        for row in rows
    ]


def render_view_frame(view_no: int, group_no: int, frame_no: int) -> RenderedFrame:
    payload = view_payload(view_no)
    group_offset = u16le(payload, 5 + group_no * 2)
    frame_offset = group_offset + u16le(payload, group_offset + 1 + frame_no * 2)
    width = payload[frame_offset]
    height = payload[frame_offset + 1]
    control = payload[frame_offset + 2]
    rows: list[list[int]] = []
    pos = frame_offset + 3
    for _y in range(height):
        row: list[int] = []
        while pos < len(payload):
            value = payload[pos]
            pos += 1
            if value == 0:
                break
            row.append(value)
        rows.append(row)

    control, rows = _orient_view_rows(rows, width, control, group_no)
    transparent = control & 0x0F
    pixels = bytearray([transparent for _ in range(width * height)])
    for y, row in enumerate(rows):
        x = 0
        for value in row:
            color = (value >> 4) & 0x0F
            run = value & 0x0F
            if color != transparent:
                for step in range(run):
                    if x + step < width:
                        pixels[y * width + x + step] = color
            x += run
    return RenderedFrame(view_no, group_no, frame_no, width, height, control, bytes(pixels))


def write_ppm(path: Path, width: int, height: int, nibbles: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        f.write(f"P6\n{width} {height}\n255\n".encode("ascii"))
        for nibble in nibbles:
            f.write(bytes(PALETTE[nibble & 0x0F]))


def picture_to_ppm(path: Path, rendered: RenderedPicture, channel: str = "visual") -> None:
    if channel == "visual":
        nibbles = rendered.visual_nibbles
    elif channel == "control":
        nibbles = rendered.control_nibbles
    else:
        raise ValueError("channel must be 'visual' or 'control'")
    write_ppm(path, WIDTH, HEIGHT, nibbles)


def frame_to_ppm(path: Path, rendered: RenderedFrame) -> None:
    write_ppm(path, rendered.width, rendered.height, rendered.pixels)


def _priority_gate_allows(cells: bytearray, x: int, y: int, object_priority: int) -> bool:
    idx = y * WIDTH + x
    existing = cells[idx] & 0xF0
    if existing > 0x20:
        return existing <= object_priority

    scan = idx
    found = 0
    while scan < 0x6860:
        scan += WIDTH
        if scan >= len(cells):
            break
        found = cells[scan] & 0xF0
        if found > 0x20:
            break
    if found <= 0x20:
        found = 0
    return found <= object_priority


def draw_frame_on_buffer(
    cells: bytearray,
    frame: RenderedFrame,
    left: int,
    baseline_y: int,
    priority: int,
) -> None:
    top = baseline_y - frame.height + 1
    transparent = frame.control & 0x0F
    object_priority = (priority & 0x0F) << 4
    for row in range(frame.height):
        y = top + row
        if not (0 <= y < HEIGHT):
            continue
        for column in range(frame.width):
            x = left + column
            if not (0 <= x < WIDTH):
                continue
            color = frame.pixels[row * frame.width + column] & 0x0F
            if color == transparent:
                continue
            if not _priority_gate_allows(cells, x, y, object_priority):
                continue
            cells[y * WIDTH + x] = object_priority | color


def compose_frame_on_picture(
    rendered_picture: RenderedPicture,
    frame: RenderedFrame,
    left: int,
    baseline_y: int,
    priority: int,
) -> RenderedPicture:
    cells = bytearray(rendered_picture.cells)
    draw_frame_on_buffer(cells, frame, left, baseline_y, priority)
    return RenderedPicture(rendered_picture.picture_no, bytes(cells))
