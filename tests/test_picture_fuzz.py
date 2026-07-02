#!/usr/bin/env python3
"""Tests for synthetic picture-resource fuzz tooling."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_graphics import HEIGHT, PALETTE, WIDTH  # noqa: E402
from picture_fuzz import (  # noqa: E402
    base_cases,
    compare_capture,
    qemu_batch_dos_dir,
    cmd_run_qemu,
    generate_cases,
    render_payload,
    run_qemu_batch,
    select_batch_cases,
    write_corpus,
)


def write_scaled_capture(path: Path, nibbles: bytes) -> None:
    rgb = bytearray()
    black = bytes(PALETTE[0])
    for y in range(400):
        if y >= HEIGHT * 2:
            rgb.extend(black * 640)
            continue
        logical_y = y // 2
        row = nibbles[logical_y * WIDTH : (logical_y + 1) * WIDTH]
        for nibble in row:
            rgb.extend(bytes(PALETTE[nibble]) * 4)
    with path.open("wb") as f:
        f.write(b"P6\n640 400\n255\n")
        f.write(rgb)


class PictureFuzzTests(unittest.TestCase):
    def test_base_cases_include_invalid_and_safe_cases(self) -> None:
        cases = base_cases()
        self.assertGreaterEqual(len(cases), 10)
        self.assertTrue(any(case.category == "invalid" for case in cases))
        self.assertTrue(any(case.safe_for_qemu for case in cases))
        self.assertTrue(any(not case.safe_for_qemu for case in cases))

    def test_random_generation_is_deterministic(self) -> None:
        left = generate_cases(8, seed=1234, include_unsafe=True)
        right = generate_cases(8, seed=1234, include_unsafe=True)
        self.assertEqual(left, right)

    def test_write_corpus_records_python_render_results(self) -> None:
        cases = generate_cases(3, seed=1, include_unsafe=False)
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus = Path(temp_dir) / "corpus"
            write_corpus(cases, corpus, render_ppm=False)
            manifest = json.loads((corpus / "manifest.json").read_text(encoding="ascii"))
        self.assertEqual(len(manifest), len(cases))
        self.assertIn("python", manifest[0])
        self.assertIn("payload_sha256", manifest[0])

    def test_compare_capture_matches_synthetic_scaled_capture(self) -> None:
        cases = base_cases()
        case = next(item for item in cases if item.case_id == "base_003_visual_point")
        rendered = render_payload(case.payload)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            corpus = temp / "corpus"
            write_corpus([case], corpus, render_ppm=False)
            capture = temp / "capture.ppm"
            write_scaled_capture(capture, rendered.visual_nibbles)
            comparison = compare_capture(corpus, case.case_id, capture)
        self.assertTrue(comparison.matches)
        self.assertEqual(comparison.mismatches, 0)
        self.assertEqual(comparison.total, WIDTH * HEIGHT)

    def test_qemu_runner_rejects_cases_that_can_overread(self) -> None:
        case = next(item for item in base_cases() if not item.safe_for_qemu)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            corpus = temp / "corpus"
            write_corpus([case], corpus, render_ppm=False)
            args = type(
                "Args",
                (),
                {
                    "corpus": corpus,
                    "case": case.case_id,
                    "fixture_root": temp / "fixtures",
                    "picture": 0,
                    "dos_dir": "UNSAFE",
                    "capture": None,
                    "boot_wait": 0,
                    "draw_wait": 0,
                },
            )()
            with self.assertRaisesRegex(SystemExit, "not compatibility-spec evidence"):
                cmd_run_qemu(args)

    def test_batch_selection_filters_unsafe_and_category(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus = Path(temp_dir) / "corpus"
            write_corpus(base_cases(), corpus, render_ppm=False)
            selected = select_batch_cases(corpus, None, ["invalid"], None)
        self.assertEqual([case.case_id for case in selected], ["base_014_truncated_pair"])

    def test_batch_dos_dir_is_stable_short_name(self) -> None:
        self.assertEqual(qemu_batch_dos_dir("fuzzbatch", 7), "FUZ00007")
        self.assertEqual(qemu_batch_dos_dir("!!!", 12), "FZB00012")

    def test_run_qemu_batch_records_match_report(self) -> None:
        case = next(item for item in base_cases() if item.case_id == "base_003_visual_point")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            corpus = temp / "corpus"
            fixtures = temp / "fixtures"
            write_corpus([case], corpus, render_ppm=False)
            rendered = render_payload(case.payload)

            def fake_run_qemu(fixture: Path, _dos_dir: str, capture: Path, _boot_wait: float, _draw_wait: float) -> None:
                self.assertTrue((fixture / "VOL.3").exists())
                write_scaled_capture(capture, rendered.visual_nibbles)

            with mock.patch("picture_fuzz.run_qemu_fixture", side_effect=fake_run_qemu):
                results = run_qemu_batch(corpus, [case], fixtures, 0, 0.0, 0.0, "TB", True)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "match")
        self.assertEqual(results[0].comparison.mismatches, 0)


if __name__ == "__main__":
    unittest.main()
