#!/usr/bin/env python3
"""Reproduce the AGI image transform performed by SQ2/SIERRA.COM.

Clean-room basis:

- SIERRA.COM loads SQ2/AGI into memory.
- The routine reached from loader file offset 0x07fc calls a transform routine
  at file offset 0x08f4.
- That transform uses a 128-byte evolving key table at loader memory offset
  0x0141, which corresponds to SIERRA.COM file offset 0x0041.
- Each source byte is XORed in place with the current key byte.
- Each key byte is then rotated right through carry. Carry is preserved across
  bytes and across 128-byte source chunks; if carry is set after a full key
  pass, the high bit of the first key byte is forced on.

This script applies only that locally observed transform.
"""

from __future__ import annotations

import argparse
from pathlib import Path


KEY_FILE_OFFSET = 0x41
KEY_SIZE = 0x80
CHUNK_SIZE = 0x80


def transform(loader: bytes, payload: bytes) -> bytes:
    key = bytearray(loader[KEY_FILE_OFFSET : KEY_FILE_OFFSET + KEY_SIZE])
    if len(key) != KEY_SIZE:
        raise ValueError("loader is too small to contain the observed key table")

    out = bytearray(payload)
    carry = 0

    for base in range(0, len(out), CHUNK_SIZE):
        for index in range(CHUNK_SIZE):
            pos = base + index
            if pos >= len(out):
                break

            value = key[index]
            out[pos] ^= value

            next_carry = value & 1
            key[index] = ((carry << 7) | (value >> 1)) & 0xFF
            carry = next_carry

        if carry:
            key[0] |= 0x80

    return bytes(out)


def read_word(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 2], "little")


def describe_mz(data: bytes) -> list[str]:
    if data[:2] != b"MZ":
        return ["MZ header: not present"]

    fields = [
        ("last_page_bytes", 0x02),
        ("pages", 0x04),
        ("relocations", 0x06),
        ("header_paragraphs", 0x08),
        ("minalloc", 0x0A),
        ("maxalloc", 0x0C),
        ("initial_ss", 0x0E),
        ("initial_sp", 0x10),
        ("checksum", 0x12),
        ("initial_ip", 0x14),
        ("initial_cs", 0x16),
        ("relocation_table", 0x18),
        ("overlay_number", 0x1A),
    ]

    lines = ["MZ header: present"]
    for name, offset in fields:
        lines.append(f"{name}: 0x{read_word(data, offset):04x}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loader", default="SQ2/SIERRA.COM")
    parser.add_argument("--payload", default="SQ2/AGI")
    parser.add_argument("--output", default="build/cleanroom/AGI.decrypted.exe")
    args = parser.parse_args()

    loader = Path(args.loader).read_bytes()
    payload = Path(args.payload).read_bytes()
    decoded = transform(loader, payload)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(decoded)

    print(f"wrote: {output}")
    print(f"bytes: {len(decoded)}")
    print("first_64:", decoded[:64].hex(" "))
    for line in describe_mz(decoded):
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
