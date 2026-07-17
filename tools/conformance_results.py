#!/usr/bin/env python3
"""Export and compare portable AGI conformance result bundles."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import re
from pathlib import Path

from ppm_tools import read_ppm


FORMAT_NAME = "agi-clean-room-conformance-results"
FORMAT_VERSION = 2
FRAME_WIDTH = 160
FRAME_HEIGHT = 168
PIXEL_FORMAT = "ega16-indexed-row-major"
EGA_PALETTE = (
    (0x00, 0x00, 0x00), (0x00, 0x00, 0xAA), (0x00, 0xAA, 0x00), (0x00, 0xAA, 0xAA),
    (0xAA, 0x00, 0x00), (0xAA, 0x00, 0xAA), (0xAA, 0x55, 0x00), (0xAA, 0xAA, 0xAA),
    (0x55, 0x55, 0x55), (0x55, 0x55, 0xFF), (0x55, 0xFF, 0x55), (0x55, 0xFF, 0xFF),
    (0xFF, 0x55, 0x55), (0xFF, 0x55, 0xFF), (0xFF, 0xFF, 0x55), (0xFF, 0xFF, 0xFF),
)
OBSERVATION_FIELDS = ("frame", "values")


def nearest_ega_index(rgb: tuple[int, int, int]) -> int:
    return min(
        range(16),
        key=lambda index: sum((rgb[channel] - EGA_PALETTE[index][channel]) ** 2 for channel in range(3)),
    )


def canonical_frame_from_ppm(path: Path) -> bytes:
    image = read_ppm(path)
    x_scale, y_scale = 4, 2
    if image.width < FRAME_WIDTH * x_scale or image.height < FRAME_HEIGHT * y_scale:
        raise ValueError(f"{path}: image is too small for the canonical game area")
    color_indexes: dict[tuple[int, int, int], int] = {}
    indexed = bytearray(image.pixel_count)
    for pixel, offset in enumerate(range(0, len(image.rgb), 3)):
        color = (image.rgb[offset], image.rgb[offset + 1], image.rgb[offset + 2])
        palette_index = color_indexes.get(color)
        if palette_index is None:
            palette_index = nearest_ega_index(color)
            color_indexes[color] = palette_index
        indexed[pixel] = palette_index
    frame = bytearray()
    for y in range(FRAME_HEIGHT):
        for x in range(FRAME_WIDTH):
            counts: Counter[int] = Counter()
            for source_y in range(y * y_scale, (y + 1) * y_scale):
                row = source_y * image.width
                for source_x in range(x * x_scale, (x + 1) * x_scale):
                    counts[indexed[row + source_x]] += 1
            frame.append(counts.most_common(1)[0][0])
    return bytes(frame)


def canonical_ppm_bytes(frame: bytes) -> bytes:
    """Encode one canonical indexed frame as a viewable binary PPM."""

    if len(frame) != FRAME_WIDTH * FRAME_HEIGHT or any(pixel > 15 for pixel in frame):
        raise ValueError("canonical frame must contain 26,880 EGA palette indexes")
    rgb = b"".join(bytes(EGA_PALETTE[pixel]) for pixel in frame)
    return f"P6\n{FRAME_WIDTH} {FRAME_HEIGHT}\n255\n".encode("ascii") + rgb


def canonical_frame_from_artifact_ppm(path: Path) -> bytes:
    """Decode a canonical PPM, requiring exact dimensions and EGA colors."""

    image = read_ppm(path)
    if (image.width, image.height, image.max_value) != (FRAME_WIDTH, FRAME_HEIGHT, 255):
        raise ValueError(f"{path}: noncanonical PPM dimensions or maximum value")
    palette_indexes = {color: index for index, color in enumerate(EGA_PALETTE)}
    frame = bytearray()
    for offset in range(0, len(image.rgb), 3):
        color = tuple(image.rgb[offset : offset + 3])
        if color not in palette_indexes:
            raise ValueError(f"{path}: canonical PPM contains a non-EGA color {color}")
        frame.append(palette_indexes[color])
    return bytes(frame)


def frame_observation(frame: bytes, artifact: str | None = None) -> dict[str, object]:
    if len(frame) != FRAME_WIDTH * FRAME_HEIGHT:
        raise ValueError(f"canonical frame must contain {FRAME_WIDTH * FRAME_HEIGHT} pixels")
    observation: dict[str, object] = {
        "width": FRAME_WIDTH,
        "height": FRAME_HEIGHT,
        "pixel_format": PIXEL_FORMAT,
        "sha256": hashlib.sha256(frame).hexdigest(),
    }
    if artifact is not None:
        observation["artifact"] = artifact
    return observation


def validate_portable_value(value: object, path: str = "values") -> None:
    if value is None or type(value) in (bool, int, str):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_portable_value(item, f"{path}/{index}")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: object keys must be strings")
            escaped = key.replace("~", "~0").replace("/", "~1")
            validate_portable_value(item, f"{path}/{escaped}")
        return
    raise ValueError(f"{path}: values must use null, Boolean, integer, string, array, or object")


def values_observation(values: dict[str, object]) -> dict[str, object]:
    if not isinstance(values, dict):
        raise ValueError("values observation must be an object")
    validate_portable_value(values)
    return values


def artifact_filename(case_id: str) -> str:
    stem = "".join(character if character.isalnum() else "_" for character in case_id).strip("_")
    stem = stem[:80] or "case"
    suffix = hashlib.sha256(case_id.encode("utf-8")).hexdigest()[:12]
    return f"{stem}_{suffix}.ppm"


def resolve_source_capture(report_path: Path, value: str) -> Path | None:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate if candidate.is_file() else None
    if candidate.is_file():
        return candidate
    adjacent = report_path.parent / candidate
    return adjacent if adjacent.is_file() else None


def export_reports(
    report_paths: list[Path],
    output: Path,
    artifact_dir: Path,
    suite_id: str,
    profile: str,
    producer: str,
) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, object]] = []
    seen: set[str] = set()

    for report_path in report_paths:
        report = json.loads(report_path.read_text(encoding="ascii"))
        if isinstance(report.get("results"), list):
            source_cases = [
                (
                    source_case,
                    source_case.get("case_id"),
                    source_case.get("status") in ("match", "ok"),
                )
                for source_case in report["results"]
            ]
        elif isinstance(report.get("cases"), list) and isinstance(report.get("probe"), str):
            qemu = report.get("qemu") if isinstance(report.get("qemu"), dict) else {}
            completed = qemu.get("ran") is True and qemu.get("passed") is not False
            source_cases = [
                (source_case, f"{report['probe']}/{source_case.get('label')}", completed)
                for source_case in report["cases"]
            ]
        else:
            raise ValueError(f"{report_path}: unsupported source report shape")

        for source_case, case_id, completed in source_cases:
            if not isinstance(case_id, str) or not case_id:
                raise ValueError(f"{report_path}: result lacks a nonempty case_id")
            if case_id in seen:
                raise ValueError(f"duplicate case_id across reports: {case_id}")
            seen.add(case_id)

            exported: dict[str, object] = {
                "id": case_id,
                "source_report": os.path.relpath(report_path, output.parent),
            }
            capture_value = source_case.get("capture")
            capture_path = (
                resolve_source_capture(report_path, capture_value)
                if isinstance(capture_value, str)
                else None
            )
            canonical_value = source_case.get("canonical_ppm")
            canonical_path = (
                resolve_source_capture(report_path, canonical_value)
                if isinstance(canonical_value, str)
                else None
            )
            if canonical_path is not None:
                frame = canonical_frame_from_artifact_ppm(canonical_path)
                declared_digest = source_case.get("canonical_sha256")
                actual_digest = hashlib.sha256(frame).hexdigest()
                if declared_digest is not None and declared_digest != actual_digest:
                    raise ValueError(f"{canonical_path}: canonical frame digest mismatch")
                artifact_path = artifact_dir / artifact_filename(case_id)
                artifact_path.write_bytes(canonical_ppm_bytes(frame))
                exported["frame"] = frame_observation(
                    frame,
                    os.path.relpath(artifact_path, output.parent),
                )
            elif capture_path is not None:
                frame = canonical_frame_from_ppm(capture_path)
                artifact_path = artifact_dir / artifact_filename(case_id)
                artifact_path.write_bytes(canonical_ppm_bytes(frame))
                exported["frame"] = frame_observation(
                    frame,
                    os.path.relpath(artifact_path, output.parent),
                )
            values = source_case.get("values")
            if values is not None:
                exported["values"] = values_observation(values)
            has_observation = any(field in exported for field in OBSERVATION_FIELDS)
            exported["status"] = "ok" if completed and has_observation else "error"
            if not has_observation:
                exported["error"] = source_case.get("error") or "portable observation unavailable"
            elif not completed:
                exported["error"] = source_case.get("error") or "source case did not complete"
            cases.append(exported)

    result = {
        "format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
        "suite_id": suite_id,
        "profile": profile,
        "producer": producer,
        "cases": cases,
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="ascii")
    return result


def validate_bundle(bundle: dict[str, object], path: Path) -> None:
    if bundle.get("format") != FORMAT_NAME or bundle.get("format_version") != FORMAT_VERSION:
        raise ValueError(f"{path}: unsupported conformance result format")
    if not isinstance(bundle.get("cases"), list):
        raise ValueError(f"{path}: cases must be a list")
    seen: set[str] = set()
    for case in bundle["cases"]:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not case["id"]:
            raise ValueError(f"{path}: every case must have a nonempty string id")
        if case["id"] in seen:
            raise ValueError(f"{path}: duplicate case id {case['id']}")
        seen.add(case["id"])
        frame = case.get("frame")
        values = case.get("values")
        if case.get("status") not in ("ok", "error"):
            raise ValueError(f"{path}: case {case['id']} has an invalid status")
        if case.get("status") == "ok" and not any(field in case for field in OBSERVATION_FIELDS):
            raise ValueError(f"{path}: successful case {case['id']} lacks an observation")
        if frame is not None and not isinstance(frame, dict):
            raise ValueError(f"{path}: case {case['id']} frame observation must be an object")
        if isinstance(frame, dict):
            if (
                frame.get("width") != FRAME_WIDTH
                or frame.get("height") != FRAME_HEIGHT
                or frame.get("pixel_format") != PIXEL_FORMAT
            ):
                raise ValueError(f"{path}: case {case['id']} has a noncanonical frame description")
            digest = frame.get("sha256")
            if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
                raise ValueError(f"{path}: case {case['id']} has an invalid frame digest")
        if values is not None:
            if not isinstance(values, dict):
                raise ValueError(f"{path}: case {case['id']} values observation must be an object")
            validate_portable_value(values, f"case/{case['id']}/values")


def load_artifact(bundle_path: Path, case: dict[str, object]) -> bytes | None:
    frame = case.get("frame")
    if not isinstance(frame, dict):
        return None
    artifact = frame.get("artifact")
    if not isinstance(artifact, str):
        return None
    artifact_path = bundle_path.parent / artifact
    data = canonical_frame_from_artifact_ppm(artifact_path)
    expected = frame.get("sha256")
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"{bundle_path}: decoded frame digest mismatch for {case.get('id')}")
    return data


def frame_difference(left: bytes, right: bytes) -> dict[str, object]:
    if len(left) != FRAME_WIDTH * FRAME_HEIGHT or len(right) != len(left):
        raise ValueError("frame artifacts do not have canonical dimensions")
    mismatches = 0
    min_x, min_y = FRAME_WIDTH, FRAME_HEIGHT
    max_x = max_y = -1
    for index, (left_pixel, right_pixel) in enumerate(zip(left, right)):
        if left_pixel == right_pixel:
            continue
        mismatches += 1
        x, y = index % FRAME_WIDTH, index // FRAME_WIDTH
        min_x, min_y = min(min_x, x), min(min_y, y)
        max_x, max_y = max(max_x, x), max(max_y, y)
    return {
        "mismatches": mismatches,
        "total": len(left),
        "mismatch_bbox": None if mismatches == 0 else [min_x, min_y, max_x, max_y],
    }


def value_differences(left: object, right: object, path: str = "") -> list[dict[str, object]]:
    if type(left) is not type(right):
        return [{"path": path or "/", "status": "different", "expected": left, "actual": right}]
    if isinstance(left, dict):
        differences: list[dict[str, object]] = []
        for key in sorted(set(left) | set(right)):
            child_path = f"{path}/{key.replace('~', '~0').replace('/', '~1')}"
            if key not in right:
                differences.append({"path": child_path, "status": "missing", "expected": left[key]})
            elif key not in left:
                differences.append({"path": child_path, "status": "unexpected", "actual": right[key]})
            else:
                differences.extend(value_differences(left[key], right[key], child_path))
        return differences
    if isinstance(left, list):
        differences = []
        for index in range(max(len(left), len(right))):
            child_path = f"{path}/{index}"
            if index >= len(right):
                differences.append({"path": child_path, "status": "missing", "expected": left[index]})
            elif index >= len(left):
                differences.append({"path": child_path, "status": "unexpected", "actual": right[index]})
            else:
                differences.extend(value_differences(left[index], right[index], child_path))
        return differences
    if left != right:
        return [{"path": path or "/", "status": "different", "expected": left, "actual": right}]
    return []


def compare_bundles(reference_path: Path, candidate_path: Path) -> dict[str, object]:
    reference = json.loads(reference_path.read_text(encoding="ascii"))
    candidate = json.loads(candidate_path.read_text(encoding="ascii"))
    validate_bundle(reference, reference_path)
    validate_bundle(candidate, candidate_path)
    reference_cases = {case["id"]: case for case in reference["cases"]}
    candidate_cases = {case["id"]: case for case in candidate["cases"]}
    results: list[dict[str, object]] = []

    for case_id in sorted(reference_cases):
        left = reference_cases[case_id]
        right = candidate_cases.get(case_id)
        if right is None:
            results.append({"id": case_id, "status": "missing"})
            continue
        if left.get("status") != "ok" or right.get("status") != "ok":
            results.append({"id": case_id, "status": "error", "error": "case did not complete successfully"})
            continue
        observation_results: dict[str, object] = {}
        matched = True
        left_frame = left.get("frame")
        if isinstance(left_frame, dict):
            right_frame = right.get("frame")
            if not isinstance(right_frame, dict):
                matched = False
                observation_results["frame"] = {"status": "missing"}
            elif left_frame.get("sha256") == right_frame.get("sha256"):
                observation_results["frame"] = {"status": "match", "mismatches": 0}
            else:
                matched = False
                left_data = load_artifact(reference_path, left)
                right_data = load_artifact(candidate_path, right)
                difference = (
                    None if left_data is None or right_data is None else frame_difference(left_data, right_data)
                )
                observation_results["frame"] = {"status": "mismatch", "difference": difference}

        left_values = left.get("values")
        if isinstance(left_values, dict):
            right_values = right.get("values")
            if not isinstance(right_values, dict):
                matched = False
                observation_results["values"] = {"status": "missing"}
            else:
                differences = value_differences(left_values, right_values)
                if differences:
                    matched = False
                    observation_results["values"] = {
                        "status": "mismatch",
                        "differences": differences,
                    }
                else:
                    observation_results["values"] = {"status": "match"}

        result: dict[str, object] = {
            "id": case_id,
            "status": "match" if matched else "mismatch",
            "observations": observation_results,
        }
        frame_result = observation_results.get("frame")
        if isinstance(frame_result, dict):
            if frame_result.get("status") == "match":
                result["mismatches"] = 0
            elif frame_result.get("status") == "mismatch":
                result["difference"] = frame_result.get("difference")
        results.append(result)

    for case_id in sorted(set(candidate_cases) - set(reference_cases)):
        results.append({"id": case_id, "status": "unexpected"})

    return {
        "format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
        "reference": str(reference_path),
        "candidate": str(candidate_path),
        "summary": {
            "total": len(results),
            "matches": sum(result["status"] == "match" for result in results),
            "failures": sum(result["status"] != "match" for result in results),
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    export_parser = subparsers.add_parser("export")
    export_parser.add_argument("reports", nargs="+", type=Path)
    export_parser.add_argument("--output", type=Path, required=True)
    export_parser.add_argument("--artifact-dir", type=Path, required=True)
    export_parser.add_argument("--suite-id", required=True)
    export_parser.add_argument("--profile", required=True)
    export_parser.add_argument("--producer", required=True)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("reference", type=Path)
    compare_parser.add_argument("candidate", type=Path)
    compare_parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.command == "export":
        result = export_reports(
            args.reports, args.output, args.artifact_dir, args.suite_id, args.profile, args.producer
        )
        print(f"cases: {len(result['cases'])}")
        print(f"result: {args.output}")
        return
    result = compare_bundles(args.reference, args.candidate)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="ascii")
    print(rendered, end="")
    if result["summary"]["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
