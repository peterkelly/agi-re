#!/usr/bin/env python3
"""Tests for the portable conformance result adapter."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from conformance_results import (  # noqa: E402
    EGA_PALETTE,
    artifact_filename,
    compare_bundles,
    export_reports,
    frame_observation,
    validate_bundle,
)


def write_scaled_ppm(path: Path, pixels: bytes) -> None:
    rgb = bytearray()
    for y in range(168):
        row = pixels[y * 160 : (y + 1) * 160]
        expanded = b"".join(bytes(EGA_PALETTE[pixel]) * 4 for pixel in row)
        rgb.extend(expanded)
        rgb.extend(expanded)
    path.write_bytes(b"P6\n640 336\n255\n" + rgb)


class ConformanceResultTests(unittest.TestCase):
    def test_artifact_filename_is_path_safe_and_collision_resistant(self) -> None:
        left = artifact_filename("probe/case")
        right = artifact_filename("probe:case")

        self.assertNotIn("/", left)
        self.assertNotEqual(left, right)

    def test_frame_observation_rejects_noncanonical_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "26880"):
            frame_observation(b"\x00")

    def test_export_and_compare_canonical_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            capture = root / "capture.ppm"
            pixels = bytes([3]) * (160 * 168)
            write_scaled_ppm(capture, pixels)
            report = root / "source.json"
            report.write_text(
                json.dumps({"results": [{"case_id": "sample", "status": "match", "capture": str(capture)}]}),
                encoding="ascii",
            )
            reference = root / "reference.json"
            export_reports([report], reference, root / "frames", "suite", "2.936", "original")
            bundle = json.loads(reference.read_text(encoding="ascii"))
            self.assertEqual(bundle["cases"][0]["status"], "ok")
            self.assertEqual((root / bundle["cases"][0]["frame"]["artifact"]).read_bytes(), pixels)

            comparison = compare_bundles(reference, reference)
            self.assertEqual(comparison["summary"], {"total": 1, "matches": 1, "failures": 0})

    def test_export_accepts_completed_v3_probe_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            capture = root / "capture.ppm"
            write_scaled_ppm(capture, bytes([5]) * (160 * 168))
            report = root / "probe.json"
            report.write_text(
                json.dumps(
                    {
                        "probe": "sample_probe",
                        "cases": [{"label": "control", "capture": str(capture)}],
                        "qemu": {"ran": True, "passed": True},
                    }
                ),
                encoding="ascii",
            )
            output = root / "result.json"
            bundle = export_reports(
                [report], output, root / "frames", "suite", "3.002.149", "original"
            )

        self.assertEqual(bundle["cases"][0]["id"], "sample_probe/control")
        self.assertEqual(bundle["cases"][0]["status"], "ok")

    def test_export_marks_known_failed_v3_probe_as_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            capture = root / "capture.ppm"
            write_scaled_ppm(capture, bytes(160 * 168))
            report = root / "probe.json"
            report.write_text(
                json.dumps(
                    {
                        "probe": "failed_probe",
                        "cases": [{"label": "case", "capture": str(capture)}],
                        "qemu": {"ran": True, "passed": False},
                    }
                ),
                encoding="ascii",
            )
            bundle = export_reports(
                [report], root / "result.json", root / "frames", "suite", "profile", "original"
            )

        self.assertEqual(bundle["cases"][0]["status"], "error")

    def test_compare_reports_pixel_difference_and_missing_case(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            left_pixels = bytearray(160 * 168)
            right_pixels = bytearray(left_pixels)
            right_pixels[161] = 7
            for name, pixels in (("left", left_pixels), ("right", right_pixels)):
                artifact = root / f"{name}.ega"
                artifact.write_bytes(pixels)
                bundle = {
                    "format": "agi-clean-room-conformance-results",
                    "format_version": 1,
                    "cases": [{"id": "sample", "status": "ok", "frame": frame_observation(bytes(pixels), artifact.name)}],
                }
                (root / f"{name}.json").write_text(json.dumps(bundle), encoding="ascii")
            comparison = compare_bundles(root / "left.json", root / "right.json")
            result = comparison["results"][0]
            self.assertEqual(result["status"], "mismatch")
            self.assertEqual(result["difference"]["mismatches"], 1)
            self.assertEqual(result["difference"]["mismatch_bbox"], [1, 1, 1, 1])

    def test_validation_rejects_duplicate_case_ids(self) -> None:
        bundle = {
            "format": "agi-clean-room-conformance-results",
            "format_version": 1,
            "cases": [{"id": "same", "status": "error"}, {"id": "same", "status": "error"}],
        }
        with self.assertRaisesRegex(ValueError, "duplicate case id"):
            validate_bundle(bundle, Path("duplicate.json"))

    def test_error_status_does_not_match_equal_frame_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            frame = bytes(160 * 168)
            observation = frame_observation(frame)
            base = {
                "format": "agi-clean-room-conformance-results",
                "format_version": 1,
                "cases": [{"id": "sample", "status": "ok", "frame": observation}],
            }
            candidate = json.loads(json.dumps(base))
            candidate["cases"][0]["status"] = "error"
            (root / "reference.json").write_text(json.dumps(base), encoding="ascii")
            (root / "candidate.json").write_text(json.dumps(candidate), encoding="ascii")
            comparison = compare_bundles(root / "reference.json", root / "candidate.json")
            self.assertEqual(comparison["results"][0]["status"], "error")


if __name__ == "__main__":
    unittest.main()
