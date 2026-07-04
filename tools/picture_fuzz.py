#!/usr/bin/env python3
"""Generate and validate synthetic picture-resource fuzz cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from agi_graphics import HEIGHT, PALETTE, WIDTH, PictureRenderer, RenderedPicture, write_ppm
from compare_picture_capture import downsample_qemu_picture_nibbles
from ppm_tools import read_ppm
from qemu_fixture import build_synthetic_picture_fixture
from qemu_snapshot import SnapshotFixtureCase, build_snapshot_boot_disk, run_snapshot_qemu_cases


DEFAULT_CORPUS = Path("build/picture-fuzz/corpus")
DEFAULT_FIXTURES = Path("build/picture-fuzz/fixtures")
DEFAULT_BATCH_RESULTS = Path("build/picture-fuzz/batches")
DEFAULT_SNAPSHOT_RAW = Path("build/picture-fuzz/snapshot/picture_fuzz.raw")
DEFAULT_SNAPSHOT_QCOW = Path("build/picture-fuzz/snapshot/picture_fuzz.qcow2")
DOS_IMAGE = Path("build/dos622/dos622.img")
DOS_IMAGE_OFFSET = "32256"


@dataclass(frozen=True)
class PictureFuzzCase:
    case_id: str
    description: str
    payload_hex: str
    category: str
    safe_for_qemu: bool = True

    @property
    def payload(self) -> bytes:
        return bytes.fromhex(self.payload_hex)


@dataclass(frozen=True)
class PythonRenderResult:
    status: str
    visual_sha256: str | None
    control_sha256: str | None
    error: str | None


@dataclass(frozen=True)
class CaptureComparison:
    case_id: str
    status: str
    mismatches: int | None
    total: int | None
    error: str | None
    mismatch_bbox: tuple[int, int, int, int] | None = None
    samples: list[tuple[int, int, int, int]] | None = None

    @property
    def matches(self) -> bool:
        return self.status == "match"


@dataclass(frozen=True)
class BatchCaseResult:
    case_id: str
    category: str
    safe_for_qemu: bool
    status: str
    dos_dir: str
    capture: str
    elapsed_seconds: float
    comparison: CaptureComparison | None
    error: str | None


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_payload(payload: bytes, picture_no: int = -1) -> RenderedPicture:
    return PictureRenderer(payload).render(picture_no)


def render_result(payload: bytes) -> PythonRenderResult:
    try:
        rendered = render_payload(payload)
    except Exception as exc:  # noqa: BLE001 - fuzz harness records exact local exception.
        return PythonRenderResult("error", None, None, f"{type(exc).__name__}: {exc}")
    return PythonRenderResult(
        "ok",
        sha256(rendered.visual_nibbles),
        sha256(rendered.control_nibbles),
        None,
    )


def _case(case_id: str, description: str, payload: bytes, category: str, safe: bool = True) -> PictureFuzzCase:
    return PictureFuzzCase(case_id, description, payload.hex(), category, safe)


def base_cases() -> list[PictureFuzzCase]:
    return [
        _case("base_000_stop_only", "Immediate terminator.", b"\xff", "terminator"),
        _case("base_001_ignored_data", "Low data bytes before terminator are ignored.", bytes([0, 1, 0xEF, 0xFF]), "scanner"),
        _case("base_002_unknown_commands", "Unknown command bytes 0xfb..0xfe before terminator.", bytes([0xFB, 0xFC, 0xFD, 0xFE, 0xFF]), "scanner"),
        _case("base_003_visual_point", "Set visual color and draw a one-pixel absolute line.", bytes([0xF0, 0x0C, 0xF6, 20, 20, 20, 20, 0xFF]), "line"),
        _case("base_004_clamped_absolute", "Absolute line coordinates at 0xef probe right/lower-edge clamping.", bytes([0xF0, 2, 0xF6, 0xEF, 0xEF, 0, 0, 0xFF]), "line"),
        _case("base_005_exact_edge_absolute", "Absolute line from exact right/lower edge to origin.", bytes([0xF0, 2, 0xF6, 0x9F, 0xA7, 0, 0, 0xFF]), "line"),
        _case("base_006_relative_mixed", "Relative line bytes exercise signed X/Y nibbles.", bytes([0xF0, 3, 0xF7, 10, 10, 0x31, 0x89, 0x72, 0xFF]), "line"),
        _case("base_007_corner_y_first", "Y-first corner path.", bytes([0xF0, 4, 0xF4, 5, 5, 20, 30, 8, 0xFF]), "corner"),
        _case("base_008_corner_x_first", "X-first corner path.", bytes([0xF0, 5, 0xF5, 5, 5, 30, 20, 8, 0xFF]), "corner"),
        _case("base_009_control_fill", "Control-only seed fill from the default high-nibble target.", bytes([0xF2, 2, 0xF8, 0, 0, 0xFF]), "fill"),
        _case("base_010_visual_control_fill", "Visual fill with control also active writes both nibbles.", bytes([0xF2, 2, 0xF0, 1, 0xF8, 0, 0, 0xFF]), "fill"),
        _case("base_011_pattern_mask", "Pattern plot with table-selected mask.", bytes([0xF0, 6, 0xF9, 3, 0xFA, 80, 80, 0xFF]), "pattern"),
        _case("base_012_pattern_random", "Pattern plot with pseudo-random mode byte and seed.", bytes([0xF0, 7, 0xF9, 0x23, 0xFA, 0x55, 80, 80, 0xFF]), "pattern"),
        _case("base_013_truncated_set_visual", "Set-visual command without an operand.", bytes([0xF0]), "invalid", False),
        _case("base_014_truncated_pair", "Absolute-line command with an incomplete coordinate pair.", bytes([0xF0, 1, 0xF6, 10, 0xFF]), "invalid", True),
        _case("base_015_no_terminator", "Valid-looking commands without a picture terminator.", bytes([0xF0, 2, 0xF6, 0, 0, 30, 4]), "invalid", False),
        _case("base_016_visual_fill_box", "Visual fill bounded by a drawn rectangular outline.", bytes([0xF0, 2, 0xF4, 10, 10, 20, 20, 10, 10, 0xF0, 3, 0xF8, 15, 15, 0xFF]), "fill"),
        _case("base_017_visual_fill_outside_box", "Visual fill outside a drawn rectangular outline.", bytes([0xF0, 2, 0xF4, 10, 10, 20, 20, 10, 10, 0xF0, 3, 0xF8, 0, 0, 0xFF]), "fill"),
        _case("base_018_pattern_edge_circle", "Pattern plot clamps a circular mask at the lower-right edge.", bytes([0xF0, 8, 0xF9, 7, 0xFA, 159, 167, 0xFF]), "pattern"),
        _case("base_019_pattern_edge_rectangle", "Pattern plot clamps a rectangular mask at the lower-right edge.", bytes([0xF0, 9, 0xF9, 0x17, 0xFA, 159, 167, 0xFF]), "pattern"),
        _case("base_020_pattern_random_sequence", "Two pseudo-random pattern plots with different seeds.", bytes([0xF0, 10, 0xF9, 0x25, 0xFA, 0x01, 50, 50, 0xE1, 52, 52, 0xFF]), "pattern"),
        _case("base_021_visual_fill_full_height_barrier", "Visual seed fill stopped by a full-height one-pixel barrier.", bytes([0xF0, 2, 0xF6, 80, 0, 80, 167, 0xF0, 3, 0xF8, 10, 10, 0xFF]), "fill"),
        _case("base_022_visual_fill_multi_seed_boxes", "One seed-fill command fills two isolated boxed regions.", bytes([0xF0, 2, 0xF4, 10, 10, 20, 20, 10, 10, 0xF4, 30, 10, 20, 40, 10, 30, 0xF0, 3, 0xF8, 15, 15, 35, 15, 0xFF]), "fill"),
        _case("base_023_control_fill_ignores_visual_barrier", "Control seed fill crosses a visual-only barrier because control is the test channel.", bytes([0xF0, 2, 0xF6, 80, 0, 80, 167, 0xF1, 0xF2, 6, 0xF8, 10, 10, 0xFF]), "fill"),
        _case("base_024_pattern_bypass_mask", "Pattern mode bit 0x10 bypasses the row/column mask test.", bytes([0xF0, 11, 0xF9, 0x13, 0xFA, 80, 80, 0xFF]), "pattern"),
        _case("base_025_interleaved_line_fill_pattern", "Rectangle outline, seed fill, line, and pattern plot in one valid stream.", bytes([0xF0, 2, 0xF4, 20, 20, 40, 40, 20, 20, 0xF0, 3, 0xF8, 30, 30, 0xF0, 4, 0xF6, 20, 30, 40, 30, 0xF0, 5, 0xF9, 0x14, 0xFA, 30, 30, 0xFF]), "pattern"),
        _case("base_026_pattern_random_bypass_sequence", "Two pattern plots with both bypass-mask and pseudo-random bits set.", bytes([0xF0, 12, 0xF9, 0x35, 0xFA, 0x7D, 70, 70, 0x22, 75, 72, 0xFF]), "pattern"),
        _case("base_027_pattern_visual_control_channels", "Pattern plotting with both visual and control channels active writes both nibbles.", bytes([0xF2, 5, 0xF0, 3, 0xF9, 0x12, 0xFA, 40, 40, 0xFF]), "pattern"),
        _case("base_028_pattern_visual_disabled_control_only", "Pattern plotting after visual disable updates only the control channel.", bytes([0xF0, 6, 0xF1, 0xF2, 5, 0xF9, 0x12, 0xFA, 40, 40, 0xFF]), "pattern"),
        _case("base_029_pattern_control_disabled_visual_only", "Pattern plotting after control disable updates only the visual channel.", bytes([0xF2, 5, 0xF3, 0xF0, 6, 0xF9, 0x12, 0xFA, 40, 40, 0xFF]), "pattern"),
    ]


def random_case(case_index: int, rng: random.Random, allow_unsafe: bool) -> PictureFuzzCase:
    payload = bytearray()
    category = rng.choice(["scanner", "line", "corner", "fill", "pattern", "invalid"])
    safe = True

    def color() -> int:
        return rng.randrange(16)

    def coord() -> int:
        return rng.randrange(0xF0)

    for _ in range(rng.randint(1, 8)):
        command = rng.choice([0xF0, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFE])
        payload.append(command)
        if command == 0xF0:
            payload.append(color())
        elif command == 0xF2:
            payload.append(color())
        elif command in (0xF4, 0xF5):
            payload.extend([coord(), coord()])
            for _segment in range(rng.randint(0, 4)):
                payload.append(coord())
        elif command == 0xF6:
            payload.extend([coord(), coord()])
            for _point in range(rng.randint(0, 4)):
                payload.extend([coord(), coord()])
        elif command == 0xF7:
            payload.extend([coord(), coord()])
            for _step in range(rng.randint(0, 6)):
                payload.append(rng.randrange(0xF0))
        elif command == 0xF8:
            for _point in range(rng.randint(0, 3)):
                payload.extend([coord(), coord()])
        elif command == 0xF9:
            payload.append(rng.randrange(0x40))
        elif command == 0xFA:
            for _point in range(rng.randint(1, 4)):
                if payload and any(byte == 0xF9 and (payload[idx + 1] & 0x20) for idx, byte in enumerate(payload[:-1])):
                    payload.append(rng.randrange(0xF0))
                payload.extend([coord(), coord()])

    if category == "invalid" and allow_unsafe and rng.choice([True, False]):
        safe = False
    else:
        payload.append(0xFF)

    return _case(
        f"rand_{case_index:05d}",
        f"Deterministic random {category} picture fuzz case {case_index}.",
        bytes(payload),
        category,
        safe,
    )


def generate_cases(count: int, seed: int, include_unsafe: bool) -> list[PictureFuzzCase]:
    cases = base_cases()
    rng = random.Random(seed)
    for idx in range(count):
        cases.append(random_case(idx, rng, include_unsafe))
    return cases


def write_case_files(case: PictureFuzzCase, corpus: Path, render_ppm: bool) -> dict[str, object]:
    case_dir = corpus / case.case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    payload = case.payload
    (case_dir / "picture.pic").write_bytes(payload)
    result = render_result(payload)
    metadata: dict[str, object] = {
        **asdict(case),
        "payload_sha256": sha256(payload),
        "payload_length": len(payload),
        "python": asdict(result),
    }
    (case_dir / "case.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="ascii")
    if render_ppm and result.status == "ok":
        rendered = render_payload(payload)
        write_ppm(case_dir / "python_visual.ppm", WIDTH, HEIGHT, rendered.visual_nibbles)
        write_ppm(case_dir / "python_control.ppm", WIDTH, HEIGHT, rendered.control_nibbles)
    return metadata


def write_corpus(cases: list[PictureFuzzCase], corpus: Path, render_ppm: bool) -> None:
    corpus.mkdir(parents=True, exist_ok=True)
    manifest = [write_case_files(case, corpus, render_ppm) for case in cases]
    (corpus / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="ascii")


def load_manifest(corpus: Path) -> list[dict[str, object]]:
    return json.loads((corpus / "manifest.json").read_text(encoding="ascii"))


def metadata_to_case(metadata: dict[str, object]) -> PictureFuzzCase:
    return PictureFuzzCase(
        str(metadata["case_id"]),
        str(metadata["description"]),
        str(metadata["payload_hex"]),
        str(metadata["category"]),
        bool(metadata["safe_for_qemu"]),
    )


def load_case(corpus: Path, case_id: str) -> PictureFuzzCase:
    metadata = json.loads((corpus / case_id / "case.json").read_text(encoding="ascii"))
    return metadata_to_case(metadata)


def select_batch_cases(
    corpus: Path,
    case_ids: list[str] | None,
    categories: list[str] | None,
    max_cases: int | None,
) -> list[PictureFuzzCase]:
    if case_ids:
        candidates = [load_case(corpus, case_id) for case_id in case_ids]
    else:
        candidates = [metadata_to_case(metadata) for metadata in load_manifest(corpus)]
    if categories:
        category_set = set(categories)
        candidates = [case for case in candidates if case.category in category_set]
    selected = [case for case in candidates if case.safe_for_qemu]
    if max_cases is not None:
        selected = selected[:max_cases]
    return selected


def qemu_batch_dos_dir(prefix: str, index: int) -> str:
    clean = "".join(character for character in prefix.upper() if character.isalnum()) or "FZB"
    return f"{clean[:3]}{index:05d}"[:8]


def build_fixture(corpus: Path, case_id: str, fixture_root: Path, picture_no: int) -> Path:
    case = load_case(corpus, case_id)
    fixture = fixture_root / case_id
    build_synthetic_picture_fixture(case.payload, fixture, picture_no=picture_no)
    return fixture


def compare_capture(corpus: Path, case_id: str, capture: Path) -> CaptureComparison:
    case = load_case(corpus, case_id)
    try:
        rendered = render_payload(case.payload)
        captured = downsample_qemu_picture_nibbles(read_ppm(capture))
    except Exception as exc:  # noqa: BLE001 - fuzz harness records exact mismatch cause.
        return CaptureComparison(case_id, "error", None, None, f"{type(exc).__name__}: {exc}")
    expected = rendered.visual_nibbles
    mismatch_samples: list[tuple[int, int, int, int]] = []
    min_x = WIDTH
    min_y = HEIGHT
    max_x = -1
    max_y = -1
    mismatches = 0
    for idx, (left, right) in enumerate(zip(captured, expected)):
        if left == right:
            continue
        mismatches += 1
        x = idx % WIDTH
        y = idx // WIDTH
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)
        if len(mismatch_samples) < 16:
            mismatch_samples.append((x, y, left, right))
    bbox = None if mismatches == 0 else (min_x, min_y, max_x, max_y)
    return CaptureComparison(
        case_id,
        "match" if mismatches == 0 else "mismatch",
        mismatches,
        len(expected),
        None,
        bbox,
        mismatch_samples,
    )


def dos_key_name(character: str) -> str:
    if character == "\\":
        return "backslash"
    if character == " ":
        return "spc"
    if character == "\n":
        return "ret"
    return character.lower()


def monitor_type(proc: subprocess.Popen[str], text: str, delay: float = 0.03) -> None:
    assert proc.stdin is not None
    for character in text:
        if proc.poll() is not None:
            raise RuntimeError(f"qemu exited before monitor input completed: {proc.returncode}")
        proc.stdin.write(f"sendkey {dos_key_name(character)}\n")
        proc.stdin.flush()
        time.sleep(delay)


def copy_fixture_to_dos(fixture: Path, dos_dir: str) -> None:
    image = f"{DOS_IMAGE}@@{DOS_IMAGE_OFFSET}"
    created = subprocess.run(
        ["mmd", "-i", image, f"::/{dos_dir}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if created.returncode != 0 and "already exists" not in (created.stderr + created.stdout).lower():
        existing = subprocess.run(
            ["mdir", "-i", image, f"::/{dos_dir}"],
            check=False,
            capture_output=True,
            text=True,
        )
        if existing.returncode != 0:
            raise RuntimeError(created.stderr + created.stdout + existing.stderr + existing.stdout)
    files = [str(path) for path in fixture.iterdir() if path.is_file() and path.suffix.lower() != ".ppm"]
    subprocess.run(["mcopy", "-o", "-i", image, *files, f"::/{dos_dir}"], check=True)


def run_qemu_fixture(fixture: Path, dos_dir: str, capture: Path, boot_wait: float, draw_wait: float) -> None:
    copy_fixture_to_dos(fixture, dos_dir)
    capture.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "qemu-system-i386",
        "-m",
        "16",
        "-boot",
        "c",
        "-drive",
        "file=build/dos622/dos622.img,format=raw,if=ide,index=0,media=disk",
        "-display",
        "vnc=127.0.0.1:5",
        "-monitor",
        "stdio",
    ]
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        time.sleep(boot_wait)
        monitor_type(proc, f"cd \\{dos_dir}\n")
        time.sleep(0.5)
        monitor_type(proc, "SIERRA\n")
        time.sleep(draw_wait)
        assert proc.stdin is not None
        proc.stdin.write(f"screendump {capture}\n")
        proc.stdin.flush()
        time.sleep(1.0)
        proc.stdin.write("quit\n")
        proc.stdin.flush()
        proc.wait(timeout=10)
        if proc.returncode != 0:
            output = proc.stdout.read() if proc.stdout is not None else ""
            raise RuntimeError(f"qemu exited with {proc.returncode}:\n{output}")
    except Exception as exc:
        output = proc.stdout.read() if proc.stdout is not None else ""
        if output:
            raise RuntimeError(f"{exc}\nqemu output:\n{output}") from exc
        raise
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=10)


def run_qemu_batch(
    corpus: Path,
    cases: list[PictureFuzzCase],
    fixture_root: Path,
    picture_no: int,
    boot_wait: float,
    draw_wait: float,
    dos_prefix: str,
    stop_on_failure: bool,
    progress: bool = False,
) -> list[BatchCaseResult]:
    results: list[BatchCaseResult] = []
    for index, case in enumerate(cases):
        dos_dir = qemu_batch_dos_dir(dos_prefix, index)
        fixture = fixture_root / case.case_id
        capture = fixture / "qemu_capture.ppm"
        started = time.monotonic()
        comparison: CaptureComparison | None = None
        error: str | None = None
        status = "error"
        if progress:
            print(f"[{index + 1}/{len(cases)}] {case.case_id} -> {dos_dir}", file=sys.stderr, flush=True)
        try:
            build_synthetic_picture_fixture(case.payload, fixture, picture_no=picture_no)
            run_qemu_fixture(fixture, dos_dir, capture, boot_wait, draw_wait)
            comparison = compare_capture(corpus, case.case_id, capture)
            status = comparison.status
            error = comparison.error
        except Exception as exc:  # noqa: BLE001 - batch harness records exact local exception.
            error = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.monotonic() - started, 3)
        results.append(
            BatchCaseResult(
                case.case_id,
                case.category,
                case.safe_for_qemu,
                status,
                dos_dir,
                str(capture),
                elapsed,
                comparison,
                error,
            )
        )
        if progress:
            detail = "" if comparison is None else f" mismatches={comparison.mismatches}"
            print(f"[{index + 1}/{len(cases)}] {case.case_id} {status}{detail}", file=sys.stderr, flush=True)
        if stop_on_failure and status != "match":
            break
    return results


def run_qemu_snapshot_batch(
    corpus: Path,
    cases: list[PictureFuzzCase],
    fixture_root: Path,
    picture_no: int,
    boot_wait: float,
    draw_wait: float,
    dos_prefix: str,
    stop_on_failure: bool,
    snapshot_raw: Path,
    snapshot_qcow: Path,
    progress: bool = False,
) -> list[BatchCaseResult]:
    qemu_cases: list[SnapshotFixtureCase] = []
    started_at: dict[str, float] = {}
    for index, case in enumerate(cases):
        dos_dir = qemu_batch_dos_dir(dos_prefix, index)
        fixture = fixture_root / case.case_id
        capture = fixture / "qemu_capture.ppm"
        started_at[case.case_id] = time.monotonic()
        if progress:
            print(f"[{index + 1}/{len(cases)}] build {case.case_id} -> {dos_dir}", file=sys.stderr, flush=True)
        build_synthetic_picture_fixture(case.payload, fixture, picture_no=picture_no)
        qemu_cases.append(SnapshotFixtureCase(dos_dir, fixture, capture))

    if progress:
        print(f"building snapshot disk: {snapshot_qcow}", file=sys.stderr, flush=True)
    build_snapshot_boot_disk(qemu_cases, snapshot_raw, snapshot_qcow)
    if progress:
        print(f"running {len(qemu_cases)} cases from one QEMU snapshot", file=sys.stderr, flush=True)
    run_snapshot_qemu_cases(snapshot_qcow, qemu_cases, boot_wait, draw_wait)

    results: list[BatchCaseResult] = []
    for index, (case, qemu_case) in enumerate(zip(cases, qemu_cases)):
        comparison: CaptureComparison | None = None
        error: str | None = None
        status = "error"
        try:
            comparison = compare_capture(corpus, case.case_id, qemu_case.capture)
            status = comparison.status
            error = comparison.error
        except Exception as exc:  # noqa: BLE001 - batch harness records exact local exception.
            error = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.monotonic() - started_at[case.case_id], 3)
        results.append(
            BatchCaseResult(
                case.case_id,
                case.category,
                case.safe_for_qemu,
                status,
                qemu_case.dos_dir,
                str(qemu_case.capture),
                elapsed,
                comparison,
                error,
            )
        )
        if progress:
            detail = "" if comparison is None else f" mismatches={comparison.mismatches}"
            print(f"[{index + 1}/{len(cases)}] {case.case_id} {status}{detail}", file=sys.stderr, flush=True)
        if stop_on_failure and status != "match":
            break
    return results


def write_batch_report(results: list[BatchCaseResult], output: Path) -> dict[str, object]:
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "total": len(results),
        "matches": sum(1 for result in results if result.status == "match"),
        "mismatches": sum(1 for result in results if result.status == "mismatch"),
        "errors": sum(1 for result in results if result.status == "error"),
    }
    report = {
        "summary": summary,
        "results": [asdict(result) for result in results],
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="ascii")
    return report


def cmd_generate(args: argparse.Namespace) -> None:
    if args.clean and args.output.exists():
        shutil.rmtree(args.output)
    cases = generate_cases(args.count, args.seed, args.include_unsafe)
    write_corpus(cases, args.output, args.render_ppm)
    safe_count = sum(1 for case in cases if case.safe_for_qemu)
    print(f"cases: {len(cases)}")
    print(f"safe_for_qemu: {safe_count}")
    print(f"manifest: {args.output / 'manifest.json'}")


def cmd_build_fixture(args: argparse.Namespace) -> None:
    fixture = build_fixture(args.corpus, args.case, args.output, args.picture)
    print(fixture)


def cmd_compare_capture(args: argparse.Namespace) -> None:
    comparison = compare_capture(args.corpus, args.case, args.capture)
    print(json.dumps(asdict(comparison), indent=2, sort_keys=True))
    if comparison.status != "match":
        raise SystemExit(1)


def cmd_run_qemu(args: argparse.Namespace) -> None:
    case = load_case(args.corpus, args.case)
    if not case.safe_for_qemu:
        raise SystemExit(
            f"{case.case_id} is marked unsafe for QEMU: it may make the original "
            "interpreter read outside the synthetic resource. Such cases are not "
            "compatibility-spec evidence."
        )
    fixture = build_fixture(args.corpus, args.case, args.fixture_root, args.picture)
    dos_dir = args.dos_dir or f"FZ{args.case[-6:].upper()}"[:8]
    capture = args.capture or fixture / "qemu_capture.ppm"
    run_qemu_fixture(fixture, dos_dir, capture, args.boot_wait, args.draw_wait)
    comparison = compare_capture(args.corpus, args.case, capture)
    print(json.dumps(asdict(comparison), indent=2, sort_keys=True))
    if comparison.status != "match":
        raise SystemExit(1)


def cmd_batch_qemu(args: argparse.Namespace) -> None:
    cases = select_batch_cases(args.corpus, args.case, args.category, args.max_cases)
    if not cases:
        raise SystemExit("no safe fuzz cases selected")
    output = args.output or DEFAULT_BATCH_RESULTS / f"batch_{time.strftime('%Y%m%d_%H%M%S')}.json"
    if args.snapshot:
        results = run_qemu_snapshot_batch(
            args.corpus,
            cases,
            args.fixture_root,
            args.picture,
            args.boot_wait,
            args.draw_wait,
            args.dos_prefix,
            args.stop_on_failure,
            args.snapshot_raw,
            args.snapshot_qcow,
            True,
        )
    else:
        results = run_qemu_batch(
            args.corpus,
            cases,
            args.fixture_root,
            args.picture,
            args.boot_wait,
            args.draw_wait,
            args.dos_prefix,
            args.stop_on_failure,
            True,
        )
    report = write_batch_report(results, output)
    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    print(f"report: {output}")
    if report["summary"]["mismatches"] or report["summary"]["errors"]:
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate")
    generate.add_argument("--count", type=int, default=256)
    generate.add_argument("--seed", type=int, default=0xA61)
    generate.add_argument("--output", type=Path, default=DEFAULT_CORPUS)
    generate.add_argument("--include-unsafe", action="store_true")
    generate.add_argument("--render-ppm", action="store_true")
    generate.add_argument("--clean", action="store_true")
    generate.set_defaults(func=cmd_generate)

    build = subparsers.add_parser("build-fixture")
    build.add_argument("case")
    build.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    build.add_argument("--output", type=Path, default=DEFAULT_FIXTURES)
    build.add_argument("--picture", type=int, default=0)
    build.set_defaults(func=cmd_build_fixture)

    compare = subparsers.add_parser("compare-capture")
    compare.add_argument("case")
    compare.add_argument("capture", type=Path)
    compare.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    compare.set_defaults(func=cmd_compare_capture)

    run_qemu = subparsers.add_parser("run-qemu")
    run_qemu.add_argument("case")
    run_qemu.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    run_qemu.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURES)
    run_qemu.add_argument("--picture", type=int, default=0)
    run_qemu.add_argument("--dos-dir")
    run_qemu.add_argument("--capture", type=Path)
    run_qemu.add_argument("--boot-wait", type=float, default=5.0)
    run_qemu.add_argument("--draw-wait", type=float, default=8.0)
    run_qemu.set_defaults(func=cmd_run_qemu)

    batch_qemu = subparsers.add_parser("batch-qemu")
    batch_qemu.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    batch_qemu.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURES)
    batch_qemu.add_argument("--picture", type=int, default=0)
    batch_qemu.add_argument("--case", action="append")
    batch_qemu.add_argument("--category", action="append")
    batch_qemu.add_argument("--max-cases", type=int)
    batch_qemu.add_argument("--dos-prefix", default="FZB")
    batch_qemu.add_argument("--output", type=Path)
    batch_qemu.add_argument("--boot-wait", type=float, default=5.0)
    batch_qemu.add_argument("--draw-wait", type=float, default=8.0)
    batch_qemu.add_argument("--stop-on-failure", action="store_true")
    batch_qemu.add_argument("--snapshot", action="store_true")
    batch_qemu.add_argument("--snapshot-raw", type=Path, default=DEFAULT_SNAPSHOT_RAW)
    batch_qemu.add_argument("--snapshot-qcow", type=Path, default=DEFAULT_SNAPSHOT_QCOW)
    batch_qemu.set_defaults(func=cmd_batch_qemu)

    args = parser.parse_args()
    try:
        args.func(args)
    except BrokenPipeError:
        sys.exit(1)


if __name__ == "__main__":
    main()
