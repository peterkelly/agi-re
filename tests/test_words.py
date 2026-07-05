#!/usr/bin/env python3
"""Tests for the clean-room WORDS.TOK decoder."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from inspect_words import (  # noqa: E402
    WORDS,
    InputWordSequenceResult,
    decode_entries,
    input_word_sequence_matches,
    normalize_parser_text,
    parse_words,
    parser_ignored_bytes,
    parser_separator_bytes,
    u16be,
)


class WordsTokTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = WORDS.read_bytes()
        cls.entries = decode_entries(cls.data)
        cls.by_word = {entry.word: entry for entry in cls.entries}

    def test_letter_offset_table_is_big_endian_and_has_no_x_words(self) -> None:
        offsets = [u16be(self.data, index * 2) for index in range(26)]
        self.assertEqual(offsets[0], 0x0034)
        self.assertEqual(offsets[11], 0x0C6F)
        self.assertEqual(offsets[22], 0x1980)
        self.assertEqual(offsets[23], 0x0000)
        self.assertEqual(offsets[25], 0x1AA4)

    def test_local_words_tok_entry_count_and_known_ids(self) -> None:
        self.assertEqual(len(self.entries), 1099)
        self.assertEqual(self.by_word["anyword"].word_id, 0x0001)
        self.assertEqual(self.by_word["look"].word_id, 0x0002)
        self.assertEqual(self.by_word["get"].word_id, 0x0005)

    def test_prefix_compressed_phrases_decode_from_previous_word(self) -> None:
        self.assertEqual(self.by_word["look"].offset, 0x0DB4)
        self.assertEqual(self.by_word["look across"].prefix_len, 4)
        self.assertEqual(self.by_word["look across"].word_id, 0x00D5)
        self.assertEqual(self.by_word["look down"].prefix_len, 5)
        self.assertEqual(self.by_word["get inside"].prefix_len, 6)

    def test_parser_normalization_tables_match_local_data(self) -> None:
        self.assertEqual(parser_separator_bytes(), b" ,.?!();:[]{}")
        self.assertEqual(parser_ignored_bytes(), b"'`-\"")
        self.assertEqual(normalize_parser_text("  LOOK, get!!"), "LOOK get")
        self.assertEqual(normalize_parser_text("rock'n-roll"), "rocknroll")

    def test_parse_words_matches_case_insensitive_dictionary_ids(self) -> None:
        parsed = parse_words("  LOOK, get!!")
        self.assertEqual(parsed.normalized, "LOOK get")
        self.assertEqual(parsed.word_ids, (0x0002, 0x0005))
        self.assertEqual(parsed.word_texts, ("LOOK", "get"))
        self.assertEqual(parsed.parsed_count_or_error_position, 2)
        self.assertIsNone(parsed.unknown_word)
        self.assertTrue(parsed.flag2_value)

    def test_parse_words_ignores_zero_id_dictionary_words(self) -> None:
        parsed = parse_words("the look at the gem")
        self.assertEqual(parsed.word_ids, (0x0002, self.by_word["gem"].word_id))
        self.assertEqual(self.by_word["gem"].word_id, 0x0174)
        self.assertEqual(parsed.word_texts, ("look", "gem"))
        self.assertEqual(parsed.parsed_count_or_error_position, 2)
        self.assertTrue(parsed.flag2_value)

        empty = parse_words("the a i")
        self.assertEqual(empty.word_ids, ())
        self.assertEqual(empty.parsed_count_or_error_position, 0)
        self.assertFalse(empty.flag2_value)

    def test_parse_words_unknown_reports_output_slot_after_zero_id_words(self) -> None:
        parsed = parse_words("the flarble look")
        self.assertEqual(parsed.word_ids, ())
        self.assertEqual(parsed.unknown_word, "flarble")
        self.assertEqual(parsed.parsed_count_or_error_position, 1)
        self.assertTrue(parsed.flag2_value)

    def test_parse_words_stops_at_ten_output_words(self) -> None:
        parsed = parse_words(" ".join(["look"] * 12))
        self.assertEqual(parsed.word_ids, (0x0002,) * 10)
        self.assertEqual(parsed.parsed_count_or_error_position, 10)

    def test_input_word_sequence_matches_exact_and_wildcard_words(self) -> None:
        self.assertEqual(
            input_word_sequence_matches((0x0002, 0x0005), (0x0002, 0x0005)),
            InputWordSequenceResult(True, flag4_value=True, skipped_operand_words=0),
        )
        self.assertEqual(
            input_word_sequence_matches((0x0002, 0x0005), (0x0002, 0x0001)),
            InputWordSequenceResult(True, flag4_value=True, skipped_operand_words=0),
        )

    def test_input_word_sequence_terminator_accepts_prefix_and_skips_tail(self) -> None:
        self.assertEqual(
            input_word_sequence_matches((0x0002, 0x0005), (0x0002, 0x270F, 0x1234)),
            InputWordSequenceResult(True, flag4_value=True, skipped_operand_words=1),
        )

    def test_input_word_sequence_rejects_extra_nonterminator_or_short_operand(self) -> None:
        self.assertEqual(
            input_word_sequence_matches((0x0002,), (0x0002, 0x0005)),
            InputWordSequenceResult(False, flag4_value=False, skipped_operand_words=0),
        )
        self.assertEqual(
            input_word_sequence_matches((0x0002, 0x0005), (0x0002,)),
            InputWordSequenceResult(False, flag4_value=False, skipped_operand_words=0),
        )

    def test_input_word_sequence_obeys_parser_flags_and_prior_match_flag(self) -> None:
        self.assertEqual(
            input_word_sequence_matches((), (0x0002,), flag2_value=False),
            InputWordSequenceResult(False, flag4_value=False, skipped_operand_words=1),
        )
        self.assertEqual(
            input_word_sequence_matches((0x0002,), (0x0002,), flag4_value=True),
            InputWordSequenceResult(False, flag4_value=True, skipped_operand_words=1),
        )

    def test_input_word_sequence_terminator_can_match_unknown_parse_state(self) -> None:
        parsed = parse_words("flarble")
        self.assertEqual(parsed.word_ids, ())
        self.assertEqual(parsed.parsed_count_or_error_position, 1)
        self.assertTrue(parsed.flag2_value)
        self.assertEqual(
            input_word_sequence_matches(
                parsed.word_ids,
                (0x270F,),
                parsed_count_or_error_position=parsed.parsed_count_or_error_position,
                flag2_value=parsed.flag2_value,
            ),
            InputWordSequenceResult(True, flag4_value=True, skipped_operand_words=0),
        )


if __name__ == "__main__":
    unittest.main()
