#!/usr/bin/env python3
"""Inspect the local SQ2 WORDS.TOK file using the inferred parser format."""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from disassemble_logic import AGIDATA, SQ2


WORDS = SQ2 / "WORDS.TOK"


@dataclass(frozen=True)
class WordEntry:
    offset: int
    prefix_len: int
    word: str
    word_id: int


@dataclass(frozen=True)
class ParsedWords:
    normalized: str
    word_ids: tuple[int, ...]
    word_texts: tuple[str, ...]
    parsed_count_or_error_position: int
    unknown_word: str | None
    flag2_value: bool


@dataclass(frozen=True)
class InputWordSequenceResult:
    matched: bool
    flag4_value: bool
    skipped_operand_words: int


def u16be(data: bytes, offset: int) -> int:
    return (data[offset] << 8) | data[offset + 1]


def zero_terminated_bytes(data: bytes, offset: int) -> bytes:
    end = data.index(0, offset)
    return data[offset:end]


def parser_separator_bytes() -> bytes:
    return zero_terminated_bytes(AGIDATA.read_bytes(), 0x0C67)


def parser_ignored_bytes() -> bytes:
    return zero_terminated_bytes(AGIDATA.read_bytes(), 0x0C75)


def normalize_parser_text(text: str | bytes) -> str:
    source = text.encode("latin-1") if isinstance(text, str) else bytes(text)
    separators = set(parser_separator_bytes())
    ignored = set(parser_ignored_bytes())
    out = bytearray()
    pos = 0

    while pos < len(source) and (source[pos] in separators or source[pos] in ignored):
        pos += 1

    while pos < len(source) and source[pos] != 0:
        while pos < len(source) and source[pos] != 0 and source[pos] not in separators:
            if source[pos] not in ignored:
                out.append(source[pos])
            pos += 1
        if pos < len(source) and source[pos] != 0:
            out.append(0x20)
            while pos < len(source) and (source[pos] in separators or source[pos] in ignored):
                pos += 1

    if out.endswith(b" "):
        out.pop()
    return out.decode("latin-1")


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


def parse_words(text: str | bytes, *, max_words: int = 10) -> ParsedWords:
    normalized = normalize_parser_text(text)
    entries = decode_entries(WORDS.read_bytes())
    by_word = {entry.word: entry.word_id for entry in entries}
    word_ids: list[int] = []
    word_texts: list[str] = []
    unknown_word = None

    for token in normalized.split(" "):
        if not token:
            continue
        if len(word_ids) >= max_words:
            break
        word_id = by_word.get(token.lower())
        if word_id is None:
            unknown_word = token
            position = len(word_ids) + 1
            return ParsedWords(
                normalized,
                tuple(word_ids),
                tuple(word_texts),
                position,
                unknown_word,
                True,
            )
        if word_id == 0:
            continue
        word_ids.append(word_id)
        word_texts.append(token)

    count = len(word_ids)
    return ParsedWords(
        normalized,
        tuple(word_ids),
        tuple(word_texts),
        count,
        None,
        count > 0,
    )


def input_word_sequence_matches(
    parsed_word_ids: tuple[int, ...],
    operand_word_ids: tuple[int, ...],
    *,
    parsed_count_or_error_position: int | None = None,
    flag2_value: bool = True,
    flag4_value: bool = False,
    tail_terminator_enabled: bool = True,
) -> InputWordSequenceResult:
    parsed_count = (
        len(parsed_word_ids)
        if parsed_count_or_error_position is None
        else parsed_count_or_error_position
    )
    if parsed_count == 0 or flag4_value or not flag2_value:
        return InputWordSequenceResult(False, flag4_value, len(operand_word_ids))

    remaining_parsed = parsed_count
    parsed_index = 0
    for operand_index, operand_word_id in enumerate(operand_word_ids):
        remaining_operands = len(operand_word_ids) - operand_index - 1
        word_id = operand_word_id & 0xFFFF
        if tail_terminator_enabled and word_id == 0x270F:
            return InputWordSequenceResult(True, True, remaining_operands)
        if remaining_parsed == 0:
            return InputWordSequenceResult(False, flag4_value, remaining_operands)
        parsed_word_id = (
            parsed_word_ids[parsed_index]
            if parsed_index < len(parsed_word_ids)
            else 0
        ) & 0xFFFF
        if word_id != parsed_word_id and word_id != 0x0001:
            return InputWordSequenceResult(False, flag4_value, remaining_operands)
        parsed_index += 1
        remaining_parsed -= 1

    if remaining_parsed == 0:
        return InputWordSequenceResult(True, True, 0)
    return InputWordSequenceResult(False, flag4_value, 0)


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
