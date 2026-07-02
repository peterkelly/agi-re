#!/usr/bin/env python3
"""Inspect the local SQ2 WORDS.TOK file using the inferred parser format."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORDS = ROOT / "SQ2" / "WORDS.TOK"


@dataclass(frozen=True)
class WordEntry:
    offset: int
    prefix_len: int
    word: str
    word_id: int


def u16be(data: bytes, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def decode_entries(data: bytes) -> list[WordEntry]:
    offsets = [u16be(data, i * 2) for i in range(26)]
    starts = sorted(off for off in offsets if off)
    first_start = min(starts)
    out: list[WordEntry] = []
    previous = ""
    off = first_start
    while off + 3 < len(data):
        entry_off = off
        prefix_len = data[off]
        off += 1
        if prefix_len > len(previous):
            raise ValueError(
                f"entry at {entry_off:#x} has prefix {prefix_len}, "
                f"previous word length {len(previous)}"
            )

        chars: list[str] = []
        while True:
            encoded = data[off]
            off += 1
            chars.append(chr((encoded & 0x7F) ^ 0x7F))
            if encoded & 0x80:
                break

        word_id = u16be(data, off)
        off += 2
        previous = previous[:prefix_len] + "".join(chars)
        out.append(WordEntry(entry_off, prefix_len, previous, word_id))

    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--prefix", default="")
    parser.add_argument("--id", type=lambda s: int(s, 0), default=None)
    args = parser.parse_args()

    data = WORDS.read_bytes()
    offsets = [u16be(data, i * 2) for i in range(26)]
    entries = decode_entries(data)

    print(f"WORDS.TOK bytes={len(data)} entries={len(entries)}")
    for i, off in enumerate(offsets):
        letter = chr(ord("a") + i)
        print(f"  {letter}: {off:#04x}")

    shown = 0
    for entry in entries:
        if args.prefix and not entry.word.startswith(args.prefix):
            continue
        if args.id is not None and entry.word_id != args.id:
            continue
        print(
            f"{entry.offset:04x} prefix={entry.prefix_len:2d} "
            f"id={entry.word_id:04x} word={entry.word}"
        )
        shown += 1
        if shown >= args.limit:
            break


if __name__ == "__main__":
    main()
