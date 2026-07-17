#!/usr/bin/env python3
"""Tests for paired original-interpreter picture screen capture plumbing."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from agi_resources import read_volume_record  # noqa: E402
from conformance_results import EGA_PALETTE  # noqa: E402
from picture_screen_capture import (  # noqa: E402
    PendingCapture,
    PictureSource,
    canonical_ppm_bytes,
    capture_case_id,
    capture_dos_dir,
    detect_launch_command,
    enumerate_picture_sources,
    materialize_results,
    validate_preflight,
)
from ppm_tools import read_ppm  # noqa: E402
from qemu_fixture import (  # noqa: E402
    build_original_picture_channel_fixture,
    build_synthetic_picture_channel_fixture,
    logic_resource,
    original_picture_record_bytes,
    picture_priority_logic_payload,
    v3_picture_volume_record,
    v3_volume_record,
    volume_record,
)


def directory_entry(volume: int, offset: int) -> bytes:
    return bytes(
        [
            (volume << 4) | ((offset >> 16) & 0x0F),
            (offset >> 8) & 0xFF,
            offset & 0xFF,
        ]
    )


def make_v2_source(root: Path) -> tuple[Path, bytes]:
    source = root / "v2-source"
    source.mkdir()
    payload = bytes([0xF0, 0x02, 0xF6, 0, 0, 1, 1, 0xFF])
    for name in ("LOGDIR", "VIEWDIR", "SNDDIR"):
        (source / name).write_bytes(b"\xff\xff\xff")
    (source / "PICDIR").write_bytes(directory_entry(0, 0))
    (source / "VOL.0").write_bytes(volume_record(payload, volume=0))
    (source / "SIERRA.COM").write_bytes(b"launcher")
    return source, payload


def make_v3_source(root: Path) -> tuple[Path, bytes]:
    source = root / "v3-source"
    source.mkdir()
    logic = v3_volume_record(logic_resource(b"\x00"), volume=1)
    payload = bytes([0xF0, 0x03, 0xF6, 0, 0, 1, 1, 0xFF])
    picture = v3_picture_volume_record(payload, volume=1)
    directory = bytearray(bytes([8, 0, 11, 0, 14, 0, 17, 0]))
    directory.extend(directory_entry(1, 0))
    directory.extend(directory_entry(1, len(logic)))
    directory.extend(b"\xff\xff\xff")
    directory.extend(b"\xff\xff\xff")
    (source / "GRDIR").write_bytes(directory)
    (source / "GRVOL.1").write_bytes(logic + picture)
    (source / "SIERRA.COM").write_bytes(b"launcher")
    return source, payload


def write_qemu_ppm(path: Path, pixel: int) -> None:
    rgb_pixel = bytes(EGA_PALETTE[pixel])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"P6\n640 400\n255\n" + rgb_pixel * (640 * 400))


class PictureScreenCaptureTests(unittest.TestCase):
    def test_case_names_are_stable_and_dos_safe(self) -> None:
        self.assertEqual(capture_case_id(45, "priority"), "picture_045/priority")
        self.assertEqual(capture_dos_dir(255, "visual"), "PC0FFV")
        self.assertLessEqual(len(capture_dos_dir(255, "priority")), 8)

    def test_launch_command_prefers_sierra_and_detects_single_com(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "KQ4.COM").write_bytes(b"")
            self.assertEqual(detect_launch_command(root), "KQ4")
            (root / "SIERRA.COM").write_bytes(b"")
            self.assertEqual(detect_launch_command(root), "SIERRA")

    def test_priority_logic_enters_action_1d_after_show(self) -> None:
        payload = picture_priority_logic_payload(7)
        code_length = int.from_bytes(payload[:2], "little")
        code = payload[2 : 2 + code_length]
        self.assertIn(bytes([0x1A, 0x1D, 0xFE, 0xFD, 0xFF]), code)

    def test_enumeration_reports_valid_and_absent_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source, _payload = make_v2_source(Path(temp_dir))
            sources, count, present_count = enumerate_picture_sources(source, [0, 1])

        self.assertEqual(count, 1)
        self.assertEqual(present_count, 1)
        self.assertEqual(sources[0].status, "valid")
        self.assertEqual(sources[0].transform, "direct")
        self.assertEqual(sources[1].status, "absent")

    def test_v2_channel_fixture_preserves_stored_picture_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source, payload = make_v2_source(root)
            before = {path.name: path.read_bytes() for path in source.iterdir()}
            fixture = build_original_picture_channel_fixture(
                0,
                "priority",
                root / "fixture",
                game_dir=source,
            )

            self.assertEqual(read_volume_record(fixture, "picture", 0).payload, payload)
            self.assertEqual(
                original_picture_record_bytes(fixture, 0),
                original_picture_record_bytes(source, 0),
            )
            self.assertEqual(before, {path.name: path.read_bytes() for path in source.iterdir()})

    def test_v3_channel_fixture_preserves_compressed_picture_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source, payload = make_v3_source(root)
            fixture = build_original_picture_channel_fixture(
                0,
                "visual",
                root / "fixture",
                game_dir=source,
            )

            picture = read_volume_record(fixture, "picture", 0)
            self.assertEqual(picture.payload, payload)
            self.assertEqual(picture.transform, "picture_nibble")
            self.assertEqual(
                original_picture_record_bytes(fixture, 0),
                original_picture_record_bytes(source, 0),
            )

    def test_synthetic_channel_fixture_uses_selected_layout_transform(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source, _payload = make_v3_source(root)
            fixture = build_synthetic_picture_channel_fixture(
                0,
                "priority",
                bytes([0xFF]),
                root / "fixture",
                game_dir=source,
                volume=1,
            )

            picture = read_volume_record(fixture, "picture", 0)
            self.assertEqual(picture.payload, bytes([0xFF]))
            self.assertEqual(picture.transform, "picture_nibble")

    def test_canonical_ppm_has_logical_dimensions(self) -> None:
        pixels = bytes([6]) * (160 * 168)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "canonical.ppm"
            path.write_bytes(canonical_ppm_bytes(pixels))
            image = read_ppm(path)

        self.assertEqual((image.width, image.height), (160, 168))
        self.assertEqual(image.rgb[:3], bytes(EGA_PALETTE[6]))

    def test_materialize_results_writes_only_canonical_ppm(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            capture = root / "raw" / "picture_000_visual.ppm"
            write_qemu_ppm(capture, 3)
            source = PictureSource(0, "valid", 0, 0, 6, 6, "direct", "0" * 64, None)
            pending = [
                PendingCapture(
                    "picture_000/visual",
                    0,
                    "visual",
                    source,
                    root / "fixture",
                    capture,
                    0.1,
                    None,
                )
            ]
            results = materialize_results(
                pending,
                root / "manifest.json",
                root / "canonical",
                None,
            )

            result = results[0]
            self.assertEqual(result["status"], "ok")
            canonical = root / result["canonical_ppm"]
            self.assertTrue(canonical.is_file())
            self.assertNotIn("canonical_artifact", result)
            image = read_ppm(canonical)
            self.assertEqual((image.width, image.height), (160, 168))
            self.assertEqual(image.rgb[:3], bytes(EGA_PALETTE[3]))

    def test_preflight_requires_blank_visual_and_default_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            results = []
            for channel, pixel in (("visual", 15), ("priority", 4)):
                artifact = root / f"{channel}.ppm"
                artifact.write_bytes(canonical_ppm_bytes(bytes([pixel]) * (160 * 168)))
                results.append(
                    {
                        "picture_no": 0,
                        "channel": channel,
                        "status": "ok",
                        "canonical_ppm": artifact.name,
                    }
                )

            validation = validate_preflight(results, root)

        self.assertTrue(validation["passed"])
        self.assertEqual(validation["observed_palette_indexes"], {"visual": [15], "priority": [4]})


if __name__ == "__main__":
    unittest.main()
